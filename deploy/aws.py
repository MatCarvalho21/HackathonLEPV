#!/usr/bin/env python3
"""Deploy do AjudaP.ai numa máquina EC2, com boto3.

Uma máquina só (t3.small: 2 vCPU, 2 GB de RAM + 2 GB de swap) rodando dois containers:
  web → Caddy: serve o front e faz HTTPS automático em https://<ip-com-traços>.sslip.io
  api → FastAPI + agente + RAG em CPU. O banco continua no Supabase (DATABASE_URL).

Uso, a partir da raiz do repositório:
  .venv/bin/pip install -r deploy/requirements.txt
  .venv/bin/python deploy/aws.py subir             # cria tudo (se preciso) e coloca o código no ar
                                                   # rode de novo a cada mudança no código
  .venv/bin/python deploy/aws.py soft-kill         # desliga a máquina; guarda disco, imagens e IP
  .venv/bin/python deploy/aws.py subir --so-ligar  # volta do soft kill em ~1 min, sem rebuild
  .venv/bin/python deploy/aws.py hard-kill         # apaga tudo; cobrança zero
  .venv/bin/python deploy/aws.py status | logs [api|web] | ssh

Credenciais: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY e AWS_REGION no .env da raiz.
Elas NUNCA vão para o servidor: o .env do servidor leva só as variáveis da aplicação.
"""
from __future__ import annotations

import argparse
import io
import os
import shlex
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASTA_SSH = RAIZ / "deploy/.ssh"
CHAVE = PASTA_SSH / "ajudapai.pem"
KNOWN_HOSTS = PASTA_SSH / "known_hosts"

NOME = "ajudapai"
TAGS = [{"Key": "Projeto", "Value": NOME}]
FILTRO = [{"Name": "tag:Projeto", "Values": [NOME]}]
AMI_UBUNTU = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
DISCO_GB = 25

# Pastas que não precisam ir para o servidor (PDFs originais, protótipo antigo, markdown da indexação).
FORA_DO_PACOTE = ("pdfs/", "frontend/", "data/", "deploy/.ssh/")

USER_DATA = """#!/bin/bash
set -eux
# 2 GB de swap: o build da imagem (torch) e o modelo de embedding apertam 2 GB de RAM.
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y docker.io docker-compose-v2 docker-buildx || (curl -fsSL https://get.docker.com | sh)
systemctl enable --now docker
usermod -aG docker ubuntu
mkdir -p /home/ubuntu/app && chown ubuntu:ubuntu /home/ubuntu/app
"""


# ---------------------------------------------------------------- .env

def ler_env() -> dict[str, str]:
    """Lê o .env da raiz (aceita `CHAVE = valor`, aspas e comentários)."""
    valores: dict[str, str] = {}
    caminho = RAIZ / ".env"
    if not caminho.exists():
        return valores
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valores[chave.strip()] = valor.strip().strip('"').strip("'")
    return valores


ENV = ler_env()
for _k, _v in ENV.items():
    if _k.startswith("AWS_"):
        os.environ.setdefault(_k, _v)

REGIAO = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
TIPO = ENV.get("EC2_TIPO") or os.getenv("EC2_TIPO") or "t3.small"


def env_do_servidor(site: str) -> str:
    """O .env que vai para a máquina: tudo menos as credenciais da AWS e as configs do deploy."""
    linhas = [f"{k}={v}" for k, v in ENV.items() if not k.startswith(("AWS_", "EC2_"))]
    linhas.append(f"SITE_ADDRESS={site}")
    return "\n".join(linhas) + "\n"


# ---------------------------------------------------------------- AWS

def clientes():
    try:
        import boto3
    except ImportError:
        sys.exit("Falta o boto3. Rode: .venv/bin/pip install -r deploy/requirements.txt")
    sessao = boto3.Session(region_name=REGIAO)
    if sessao.get_credentials() is None:
        sys.exit("Sem credenciais da AWS. Coloque AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY no .env da raiz.")
    return sessao.client("ec2"), sessao.client("ssm")


def erro_aws(e: Exception) -> str:
    return getattr(e, "response", {}).get("Error", {}).get("Code", "")


def instancia(ec2) -> dict | None:
    r = ec2.describe_instances(Filters=FILTRO + [
        {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]}])
    for res in r["Reservations"]:
        for inst in res["Instances"]:
            return inst
    return None


def ip_fixo(ec2) -> dict | None:
    r = ec2.describe_addresses(Filters=FILTRO)
    return r["Addresses"][0] if r["Addresses"] else None


def meu_ip() -> str:
    with urllib.request.urlopen("https://checkip.amazonaws.com", timeout=10) as r:
        return r.read().decode().strip()


def garantir_chave(ec2) -> None:
    existe_na_aws = bool(ec2.describe_key_pairs(Filters=[{"Name": "key-name", "Values": [NOME]}])["KeyPairs"])
    if existe_na_aws and CHAVE.exists():
        return
    if existe_na_aws:  # a chave existe na AWS mas o arquivo .pem sumiu daqui: recria
        print("Chave SSH sem o arquivo local; recriando.")
        ec2.delete_key_pair(KeyName=NOME)
    PASTA_SSH.mkdir(parents=True, exist_ok=True)
    r = ec2.create_key_pair(KeyName=NOME, KeyType="ed25519",
                            TagSpecifications=[{"ResourceType": "key-pair", "Tags": TAGS}])
    CHAVE.write_text(r["KeyMaterial"])
    CHAVE.chmod(0o600)
    print(f"Chave SSH salva em {CHAVE.relative_to(RAIZ)}")


def vpc_padrao(ec2) -> str:
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])["Vpcs"]
    if not vpcs:
        sys.exit(f"A região {REGIAO} não tem VPC padrão. No console: VPC → Actions → Create default VPC.")
    return vpcs[0]["VpcId"]


def garantir_firewall(ec2, vpc: str) -> str:
    nome = f"{NOME}-sg"
    r = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [nome]},
                                              {"Name": "vpc-id", "Values": [vpc]}])
    if r["SecurityGroups"]:
        return r["SecurityGroups"][0]["GroupId"]
    sg = ec2.create_security_group(GroupName=nome, Description="AjudaP.ai: HTTP/HTTPS publico, SSH so do seu IP",
                                   VpcId=vpc, TagSpecifications=[{"ResourceType": "security-group", "Tags": TAGS}])
    sg_id = sg["GroupId"]
    ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=[
        {"IpProtocol": "tcp", "FromPort": p, "ToPort": p,
         "IpRanges": [{"CidrIp": "0.0.0.0/0"}], "Ipv6Ranges": [{"CidrIpv6": "::/0"}]}
        for p in (80, 443)])
    print(f"Firewall criado: {sg_id} (portas 80 e 443 abertas)")
    return sg_id


def liberar_ssh(ec2, sg_id: str) -> None:
    """Deixa a porta 22 aberta só para o IP atual (troca a regra antiga se você mudou de rede)."""
    ip = meu_ip()
    sg = ec2.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0]
    regras_22 = [p for p in sg["IpPermissions"] if p.get("FromPort") == 22]
    if any(r.get("CidrIp") == f"{ip}/32" for p in regras_22 for r in p.get("IpRanges", [])):
        return
    if regras_22:
        ec2.revoke_security_group_ingress(GroupId=sg_id, IpPermissions=regras_22)
    ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=[{
        "IpProtocol": "tcp", "FromPort": 22, "ToPort": 22,
        "IpRanges": [{"CidrIp": f"{ip}/32", "Description": "SSH do deploy"}]}])
    print(f"SSH liberado para o seu IP ({ip})")


def sg_da_instancia(inst: dict) -> str:
    return inst["SecurityGroups"][0]["GroupId"]


def ip_publico(ec2, inst: dict) -> str:
    end = ip_fixo(ec2)
    if end and end.get("InstanceId") == inst["InstanceId"]:
        return end["PublicIp"]
    if inst.get("PublicIpAddress"):
        return inst["PublicIpAddress"]
    sys.exit("A máquina está sem IP público. Rode `deploy/aws.py subir --so-ligar`.")


def endereco(ip: str, https: bool = True) -> tuple[str, str]:
    """(SITE_ADDRESS para o Caddy, URL pública). sslip.io resolve 1-2-3-4.sslip.io para 1.2.3.4."""
    if not https:
        return ":80", f"http://{ip}"
    host = ip.replace(".", "-") + ".sslip.io"
    return host, f"https://{host}"


# ---------------------------------------------------------------- SSH

def ssh_args(ip: str, *extra: str) -> list[str]:
    return ["ssh", "-i", str(CHAVE), "-o", "StrictHostKeyChecking=accept-new",
            "-o", f"UserKnownHostsFile={KNOWN_HOSTS}", "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=30", *extra, f"ubuntu@{ip}"]


def ssh(ip: str, comando: str, entrada: str | None = None, checar: bool = True) -> int:
    r = subprocess.run(ssh_args(ip) + [comando], input=entrada, text=True)
    if checar and r.returncode != 0:
        sys.exit(f"Comando remoto falhou (código {r.returncode}).")
    return r.returncode


def esperar_ssh(ip: str, limite_s: int = 300) -> None:
    print("Esperando o SSH responder...", end="", flush=True)
    fim = time.time() + limite_s
    while time.time() < fim:
        r = subprocess.run(ssh_args(ip, "-o", "BatchMode=yes") + ["true"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if r.returncode == 0:
            print(" ok")
            return
        print(".", end="", flush=True)
        time.sleep(5)
    sys.exit("\nO SSH não respondeu. Veja se a máquina está ligada (`status`) e tente de novo.")


# ---------------------------------------------------------------- comandos

def cmd_criar(args) -> None:
    ec2, ssm = clientes()
    inst = instancia(ec2)
    if inst:
        print(f"Já existe uma máquina ({inst['InstanceId']}, {inst['State']['Name']}). Use `deploy` ou `status`.")
        return
    garantir_chave(ec2)
    vpc = vpc_padrao(ec2)
    sg_id = garantir_firewall(ec2, vpc)
    ami = ssm.get_parameter(Name=AMI_UBUNTU)["Parameter"]["Value"]
    disco = ec2.describe_images(ImageIds=[ami])["Images"][0]["RootDeviceName"]

    base = dict(
        ImageId=ami, InstanceType=TIPO, KeyName=NOME, MinCount=1, MaxCount=1,
        UserData=USER_DATA,
        BlockDeviceMappings=[{"DeviceName": disco, "Ebs": {
            "VolumeSize": DISCO_GB, "VolumeType": "gp3", "DeleteOnTermination": True}}],
        MetadataOptions={"HttpTokens": "required"},
        TagSpecifications=[{"ResourceType": t, "Tags": TAGS + [{"Key": "Name", "Value": NOME}]}
                           for t in ("instance", "volume")],
    )
    # Nem toda zona da região tem todo tipo de máquina: tenta subnet por subnet.
    subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]},
                                            {"Name": "default-for-az", "Values": ["true"]}])["Subnets"]
    inst_id = None
    for sn in sorted(subnets, key=lambda s: s["AvailabilityZone"]):
        try:
            r = ec2.run_instances(**base, NetworkInterfaces=[{
                "DeviceIndex": 0, "SubnetId": sn["SubnetId"], "Groups": [sg_id],
                "AssociatePublicIpAddress": True}])
            inst_id = r["Instances"][0]["InstanceId"]
            print(f"Máquina {inst_id} ({TIPO}, Ubuntu 24.04) criada em {sn['AvailabilityZone']}")
            break
        except Exception as e:  # noqa: BLE001
            if erro_aws(e) in ("Unsupported", "InsufficientInstanceCapacity"):
                continue
            raise
    if not inst_id:
        sys.exit(f"Nenhuma zona de {REGIAO} aceitou {TIPO}. Tente EC2_TIPO=t3a.small no .env.")

    print("Esperando ligar...")
    ec2.get_waiter("instance_running").wait(InstanceIds=[inst_id])

    end = ip_fixo(ec2) or ec2.allocate_address(
        Domain="vpc", TagSpecifications=[{"ResourceType": "elastic-ip", "Tags": TAGS}])
    ec2.associate_address(InstanceId=inst_id, AllocationId=end["AllocationId"])
    ip = end["PublicIp"]
    print(f"IP fixo: {ip}")

    KNOWN_HOSTS.unlink(missing_ok=True)  # máquina nova no mesmo IP tem outra identidade SSH
    liberar_ssh(ec2, sg_id)
    esperar_ssh(ip)
    print("Instalando Docker na máquina (1 a 3 minutos)...")
    ssh(ip, "sudo cloud-init status --wait > /dev/null; sudo docker --version && sudo docker compose version")
    if args.comando == "criar":
        print("\nMáquina pronta. Agora rode: .venv/bin/python deploy/aws.py subir")
    print(f"O site vai ficar em: {endereco(ip)[1]}")


def empacotar() -> bytes:
    """tar.gz com os arquivos versionados + novos não ignorados (o .env e os venvs ficam de fora)."""
    saida = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=RAIZ,
                           capture_output=True, check=True).stdout.decode()
    arquivos = [f for f in saida.split("\0") if f and not f.startswith(FORA_DO_PACOTE) and (RAIZ / f).is_file()]
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for f in arquivos:
            tar.add(RAIZ / f, arcname=f)
    return buf.getvalue()


def checar_env() -> None:
    faltando = [k for k in ("DATABASE_URL",) if not ENV.get(k)]
    if not (ENV.get("API_KEY") or ENV.get("FEATHERLESS_API_KEY")):
        faltando.append("API_KEY")
    if faltando:
        sys.exit(f"Falta no .env: {', '.join(faltando)}. Sem DATABASE_URL o servidor usaria um SQLite "
                 "dentro do container, que some a cada deploy.")


def cmd_deploy(args) -> None:
    checar_env()
    ec2, _ = clientes()
    inst = instancia(ec2)
    if not inst:
        sys.exit("Nenhuma máquina. Rode: deploy/aws.py subir")
    if inst["State"]["Name"] != "running":
        sys.exit(f"A máquina está {inst['State']['Name']}. Rode: deploy/aws.py subir")
    ip = ip_publico(ec2, inst)
    site, url = endereco(ip, https=not args.sem_https)
    liberar_ssh(ec2, sg_da_instancia(inst))
    esperar_ssh(ip)

    pacote = empacotar()
    print(f"Enviando o código ({len(pacote) / 1e6:.1f} MB)...")
    with tempfile.NamedTemporaryFile(suffix=".tgz") as tmp:
        tmp.write(pacote)
        tmp.flush()
        r = subprocess.run(["scp", "-q", "-i", str(CHAVE), "-o", "StrictHostKeyChecking=accept-new",
                            "-o", f"UserKnownHostsFile={KNOWN_HOSTS}", tmp.name, f"ubuntu@{ip}:/home/ubuntu/app.tgz"])
        if r.returncode != 0:
            sys.exit("Falha ao enviar o código.")

    ssh(ip, "set -e; sudo cloud-init status --wait > /dev/null; mkdir -p ~/app && cd ~/app && "
            "find . -mindepth 1 -maxdepth 1 -exec rm -rf {} + && tar xzf ~/app.tgz && rm ~/app.tgz && "
            "umask 077 && cat > .env", entrada=env_do_servidor(site))

    print("Construindo e subindo os containers (o 1º deploy leva ~5-10 min; os próximos, bem menos)...")
    ssh(ip, "set -e; cd ~/app && sudo docker compose up -d --build --remove-orphans && sudo docker image prune -f > /dev/null")

    print("Esperando a API responder", end="", flush=True)
    fim = time.time() + 300
    while time.time() < fim:
        if saude(url):
            print(f" ok\n\nNo ar: {url}")
            return
        print(".", end="", flush=True)
        time.sleep(5)
    print(f"\nA API ainda não respondeu em {url}/api/health. Veja os logs: deploy/aws.py logs")
    if not args.sem_https:
        print("Se o problema for o certificado HTTPS, rode `deploy/aws.py subir --sem-https` (fica em http://IP).")


def saude(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/api/health", timeout=8) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def cmd_status(args) -> None:
    ec2, _ = clientes()
    inst = instancia(ec2)
    if not inst:
        print("Nenhuma máquina criada.")
        return
    estado = inst["State"]["Name"]
    print(f"Máquina: {inst['InstanceId']} ({inst['InstanceType']}) — {estado}")
    end = ip_fixo(ec2)
    if end:
        print(f"IP fixo: {end['PublicIp']}")
    if estado == "running":
        ip = ip_publico(ec2, inst)
        for https in (True, False):
            url = endereco(ip, https)[1]
            print(f"{url}  →  {'API ok' if saude(url) else 'sem resposta'}")


def cmd_logs(args) -> None:
    ec2, _ = clientes()
    inst = instancia(ec2) or sys.exit("Nenhuma máquina.")
    liberar_ssh(ec2, sg_da_instancia(inst))
    servico = shlex.quote(args.servico) if args.servico else ""
    ssh(ip_publico(ec2, inst), f"cd ~/app && sudo docker compose logs -f --tail 200 {servico}", checar=False)


def cmd_ssh(args) -> None:
    ec2, _ = clientes()
    inst = instancia(ec2) or sys.exit("Nenhuma máquina.")
    liberar_ssh(ec2, sg_da_instancia(inst))
    os.execvp("ssh", ssh_args(ip_publico(ec2, inst)))


def cmd_parar(args) -> None:
    ec2, _ = clientes()
    inst = instancia(ec2) or sys.exit("Nenhuma máquina.")
    ec2.stop_instances(InstanceIds=[inst["InstanceId"]])
    print("Soft kill: desligando. Para de cobrar a hora da máquina; disco (com as imagens prontas) e IP fixo\n"
          "continuam (~US$ 0,20/dia). Para voltar: deploy/aws.py subir --so-ligar")


def cmd_ligar(args) -> None:
    ec2, _ = clientes()
    inst = instancia(ec2) or sys.exit("Nenhuma máquina.")
    ec2.start_instances(InstanceIds=[inst["InstanceId"]])
    ec2.get_waiter("instance_running").wait(InstanceIds=[inst["InstanceId"]])
    ip = ip_publico(ec2, instancia(ec2))
    print(f"Ligada. Os containers sobem sozinhos em ~1 min: {endereco(ip)[1]}")


def cmd_destruir(args) -> None:
    ec2, _ = clientes()
    if not args.sim:
        if input(f"HARD KILL: apagar máquina, disco, IP fixo, firewall e chave. O próximo `subir` refaz tudo\n"
                 f"do zero (~10 min) e o endereço muda. Digite {NOME} para confirmar: ").strip() != NOME:
            sys.exit("Cancelado.")
    inst = instancia(ec2)
    if inst:
        ec2.terminate_instances(InstanceIds=[inst["InstanceId"]])
        print("Apagando a máquina...")
        ec2.get_waiter("instance_terminated").wait(InstanceIds=[inst["InstanceId"]])
    end = ip_fixo(ec2)
    if end:
        ec2.release_address(AllocationId=end["AllocationId"])
        print(f"IP fixo {end['PublicIp']} liberado.")
    for sg in ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [f"{NOME}-sg"]}])["SecurityGroups"]:
        ec2.delete_security_group(GroupId=sg["GroupId"])
        print("Firewall apagado.")
    if ec2.describe_key_pairs(Filters=[{"Name": "key-name", "Values": [NOME]}])["KeyPairs"]:
        ec2.delete_key_pair(KeyName=NOME)
    CHAVE.unlink(missing_ok=True)
    KNOWN_HOSTS.unlink(missing_ok=True)
    print("Hard kill concluído: tudo apagado, sem cobrança deste projeto. Para recriar: deploy/aws.py subir")


def cmd_subir(args) -> None:
    """Faz o que faltar para o site ficar no ar: cria a máquina, liga se estiver em soft kill, e faz o deploy."""
    checar_env()
    ec2, _ = clientes()
    inst = instancia(ec2)
    if not inst:
        cmd_criar(args)
    elif inst["State"]["Name"] in ("stopped", "stopping"):
        if inst["State"]["Name"] == "stopping":
            ec2.get_waiter("instance_stopped").wait(InstanceIds=[inst["InstanceId"]])
        cmd_ligar(args)
    if args.so_ligar and inst:
        return
    cmd_deploy(args)


def main() -> None:
    p = argparse.ArgumentParser(
        description="Deploy do AjudaP.ai na AWS (EC2)",
        epilog="Ciclo normal: subir → (apresentação) → soft-kill → subir --so-ligar → ... → hard-kill")
    sub = p.add_subparsers(dest="comando", required=True)
    s = sub.add_parser("subir", help="TUDO de uma vez: cria (se preciso), liga (se em soft kill) e faz o deploy")
    s.add_argument("--sem-https", action="store_true", help="serve só por HTTP no IP (se o HTTPS der problema)")
    s.add_argument("--so-ligar", action="store_true",
                   help="volta de um soft kill sem reenviar o código (sobe em ~1 min, com as imagens já prontas)")
    s.set_defaults(f=cmd_subir)
    sub.add_parser("soft-kill", aliases=["parar"],
                   help="desliga a máquina: para de cobrar a hora, mas guarda disco, imagens prontas e IP"
                   ).set_defaults(f=cmd_parar)
    hk = sub.add_parser("hard-kill", aliases=["destruir"],
                        help="apaga TUDO (máquina, disco, IP, firewall, chave): cobrança zero")
    hk.add_argument("--sim", action="store_true", help="não pede confirmação")
    hk.set_defaults(f=cmd_destruir)
    sub.add_parser("status", help="estado da máquina e saúde da API").set_defaults(f=cmd_status)
    lg = sub.add_parser("logs", help="logs dos containers (Ctrl+C para sair)")
    lg.add_argument("servico", nargs="?", choices=["api", "web"])
    lg.set_defaults(f=cmd_logs)
    sub.add_parser("ssh", help="abre um terminal na máquina").set_defaults(f=cmd_ssh)
    # Passos avulsos (o `subir` já chama cada um quando precisa)
    sub.add_parser("criar", help="só cria máquina, IP fixo, firewall e chave SSH").set_defaults(f=cmd_criar)
    d = sub.add_parser("deploy", help="só reenvia o código e reconstrói os containers")
    d.add_argument("--sem-https", action="store_true", help="serve só por HTTP no IP")
    d.set_defaults(f=cmd_deploy)
    sub.add_parser("ligar", help="só liga a máquina (após um soft kill)").set_defaults(f=cmd_ligar)
    args = p.parse_args()
    print(f"Região: {REGIAO}")
    try:
        args.f(args)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:  # noqa: BLE001
        codigo = erro_aws(e)
        if codigo in ("AuthFailure", "InvalidClientTokenId", "SignatureDoesNotMatch"):
            sys.exit(f"A AWS recusou as chaves ({codigo}). Confira AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY no .env.")
        if codigo in ("UnauthorizedOperation", "AccessDenied", "AccessDeniedException"):
            msg = getattr(e, "response", {}).get("Error", {}).get("Message", str(e)).split(" Encoded")[0]
            if "service control policy" in msg:
                sys.exit(f"A organização dona desta conta AWS bloqueia isso na região {REGIAO} (SCP):\n  {msg}\n"
                         "Não adianta mexer no IAM. Tente outra região em AWS_REGION no .env (nesta conta, us-east-2 funciona).")
            sys.exit(f"As chaves funcionam, mas falta permissão ao usuário IAM ({codigo}):\n  {msg}\n"
                     "No console: IAM → Users → seu usuário → Add permissions → Attach policies directly →\n"
                     "  AmazonEC2FullAccess e AmazonSSMReadOnlyAccess.")
        if codigo == "OptInRequired":
            sys.exit("A conta ainda não está ativada para EC2 (verificação de cartão pendente). Espere o e-mail da AWS.")
        raise


if __name__ == "__main__":
    main()
