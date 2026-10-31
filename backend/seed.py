"""Dados de demonstração do banco local.

    python -m backend.seed            # cria (se ainda não existir) a família de demonstração
    python -m backend.seed --zerar    # apaga o banco local e recria

Família criada (senha de todas as contas: demo1234):
- Ana Souza (mãe), ana@demo.primeirospassos — responsável pelo perfil da Lia e da Nina
- Lia, 3a2m: formulário enviado + perfil APROVADO (relatório real gerado pelo agente,
  src/agente_perfil/exemplos/avaliacao_lia_aprovada.json) + 2 semanas de registros.
  Serve para testar painel e chat na hora, sem esperar o agente.
- Nina, 3a2m: só cadastro. Serve para rodar a jornada completa (formulário → agente → aprovação);
  no formulário, use "Preencher com exemplo".
- Acompanhantes (a Ana compartilhou os perfis com eles):
  - Prof. Carla Mendes, carla@demo.primeirospassos — professora da Lia e da Nina (Creche Municipal Sol)
  - Dr. Rafael Lima, rafael@demo.primeirospassos — pediatra da Lia
  Entre por "Entrar como professora" para ver o lado do acompanhante (registra, conversa no canal e com a
  IA; não altera o perfil nem as metas).
- Canal da Lia com algumas mensagens entre a família, a professora e o pediatra.

Bancos criados antes do login ganham as contas, os compartilhamentos e o canal ao chamar semear_demo().
"""
import argparse
import json
from datetime import date, datetime, timedelta, timezone

from src.agente_perfil import config, repositorio as repo

EMAIL_DEMO = "ana@demo.primeirospassos"
EMAIL_PROFESSORA = "carla@demo.primeirospassos"
EMAIL_PEDIATRA = "rafael@demo.primeirospassos"
SENHA_DEMO = "demo1234"
EXEMPLOS = config.ROOT / "src/agente_perfil/exemplos"


def _quando(dias_atras: float, hora: int = 18) -> str:
    d = datetime.now(timezone.utc) - timedelta(days=dias_atras)
    return d.replace(hour=hora, minute=0, second=0, microsecond=0).isoformat()


def _nascimento(meses: int) -> str:
    return (date.today() - timedelta(days=int(meses * 30.44) + 5)).isoformat()


def semear_demo() -> dict:
    existente = next(iter(repo._todos("SELECT * FROM responsavel WHERE email = ?", (EMAIL_DEMO,))), None)
    if existente:
        _garantir_login_e_equipe(existente)
        return existente
    ana = _semear_familia()
    _garantir_login_e_equipe(ana)
    return ana


def _conta_demo(nome: str, email: str) -> dict:
    from backend.auth import hash_senha
    return repo.obter_conta_por_email(email) or repo.criar_conta(nome, email, hash_senha(SENHA_DEMO))


def _garantir_login_e_equipe(ana: dict) -> None:
    """Idempotente: contas com senha, compartilhamentos ativos, pediatra e canal da Lia."""
    conta_ana = _conta_demo("Ana Souza", EMAIL_DEMO)
    if not ana.get("conta_id"):
        repo.ligar_perfil("responsavel", ana["id"], conta_ana["id"])
    carla = repo._um("SELECT * FROM professor WHERE email = ?", (EMAIL_PROFESSORA,))
    conta_carla = _conta_demo("Carla Mendes", EMAIL_PROFESSORA)
    if not carla.get("conta_id"):
        repo.ligar_perfil("professor", carla["id"], conta_carla["id"])
    rafael = repo._um("SELECT * FROM professor WHERE email = ?", (EMAIL_PEDIATRA,))
    if not rafael:
        conta_rafael = _conta_demo("Dr. Rafael Lima", EMAIL_PEDIATRA)
        rafael = repo.criar_acompanhante("Dr. Rafael Lima", EMAIL_PEDIATRA, "medico", "UBS Jardim", conta_rafael["id"])

    criancas = {c["nome"]: c for c in repo.criancas_do_responsavel(ana["id"])}
    for nome, prof, funcao in [("Lia", carla, "professor"), ("Nina", carla, "professor"), ("Lia", rafael, "medico")]:
        c = criancas.get(nome)
        if c and not repo._um("SELECT 1 AS ok FROM compartilhamento WHERE crianca_id = ? AND professor_id = ?",
                              (c["id"], prof["id"])):
            cp = repo.criar_compartilhamento(c["id"], prof["email"], funcao, ana["id"])
            repo.responder_compartilhamento(cp["id"], prof["id"], "ativo")

    lia = criancas.get("Lia")
    if lia and not repo.listar_canal(lia["id"], limite=1):
        mensagens = [
            (6.2, "responsavel", ana["id"], "Oi, Carla e Dr. Rafael! Criei este canal para a gente combinar as coisas da Lia. "
                                          "Em casa estamos usando o aviso de 5 e 2 minutos antes de trocar de atividade."),
            (5.9, "professor", carla["id"], "Que ótimo, Ana! Vou usar o mesmo aviso aqui na creche, com a música de guardar. "
                                            "Ela gosta muito quando cantamos."),
            (4, "professor", rafael["id"], "Ana, recebi o pedido da audiometria. Assim que tiver o resultado, me avise por aqui "
                                           "para combinarmos o retorno com a fonoaudióloga."),
            (1, "responsavel", ana["id"], "Combinado! A audiometria ficou para a semana que vem."),
        ]
        for dias, papel, autor, texto in mensagens:
            m = repo.inserir_mensagem_canal(lia["id"], papel, autor, texto)
            with repo.conexao() as db:
                hora = (datetime.now(timezone.utc) - timedelta(days=dias)).replace(microsecond=0).isoformat()
                db.execute("UPDATE canal_mensagem SET criado_em = ? WHERE id = ?", (hora, m["id"]))


def _semear_familia() -> dict:
    from backend.main import Submission, submit

    ana = repo.criar_responsavel("Ana Souza", EMAIL_DEMO, "(21) 90000-0000")
    carla = repo.criar_professor("Carla Mendes", EMAIL_PROFESSORA, "Creche Municipal Sol", "Maternal II")

    # o acesso da professora vem do compartilhamento (ver _garantir_login_e_equipe), não da turma
    lia = repo.criar_crianca("Lia", _nascimento(38), ["dinossauros", "água", "música", "quebra-cabeça"], ana["id"], "Mãe")
    repo.criar_crianca("Nina", _nascimento(38), ["bichos", "massinha", "histórias"], ana["id"], "Mãe")

    corpo = json.loads((EXEMPLOS / "formulario_lia_38m.json").read_text(encoding="utf-8"))
    form = submit(Submission.model_validate({**corpo, "crianca_id": lia["id"], "autor_id": ana["id"]}))

    modelo = json.loads((EXEMPLOS / "avaliacao_lia_aprovada.json").read_text(encoding="utf-8"))
    av_id = repo.novo_id()
    repo.inserir_avaliacao({
        "id": av_id, "crianca_id": lia["id"], "formulario_id": form["id"], "sessao_id": None,
        "avaliacao_anterior_id": None, "tipo": "inicial", "status": "vigente",
        "respostas_formulario": modelo["respostas_formulario"], "perfil": modelo["perfil"],
        "niveis": modelo["niveis"], "metas": modelo["metas"], "comentario_responsavel": None,
        "criado_em": _quando(15, 10), "aceita_em": _quando(15, 11),
    })

    dicas = [d["titulo"] for d in modelo["perfil"]["relatorio"]["dicas"]]
    aviso, calma, espere = dicas[3], dicas[4], dicas[1]
    R, P = {"responsavel_id": ana["id"]}, {"professor_id": carla["id"]}
    registros = [
        (14, R, dict(tipo="saude", texto="Pediatra encaminhou para fonoaudióloga e pediu audiometria.",
                     dados={"categoria": "Consulta", "profissional": "Pediatra da UBS", "retorno": (date.today() + timedelta(days=20)).isoformat()})),
        (13, R, dict(tipo="comportamento", local="casa", dominios=["REG"], estrategia=aviso, resultado="nao_funcionou",
                     dados={"antecedente": "Pedi para desligar o tablet", "comportamento": "Chorou e jogou o tablet no sofá",
                            "consequencia": "Dei colo, demorou para acalmar", "intensidade": 4, "duracao_min": 15},
                     texto="Avisei só uma vez, em cima da hora.")),
        (12, P, dict(tipo="observacao", local="escola", dominios=["SOC", "REG"],
                     texto="Na entrada chorou uns 15 minutos. Depois brincou perto das outras crianças no tanque de areia.")),
        (11, R, dict(tipo="atividade", local="casa", dominios=["FAL", "BRI"], texto="Brincadeira de dinossauros narrando as ações",
                     dados={"duracao_min": 15, "nivel_ajuda": "pouca", "engajamento": "adorou"})),
        (10, R, dict(tipo="feedback_estrategia", local="casa", dominios=["FAL"], estrategia=espere, resultado="funcionou",
                     texto="Esperei com o copo na mão e ela disse 'água'!")),
        (9, R, dict(tipo="checkin_meta", meta_id="meta_1", dominios=["COM_E"], dados={"nivel_gas": -1},
                    texto="Pediu com palavra 1 ou 2 vezes por dia.")),
        (8, R, dict(tipo="comportamento", local="casa", dominios=["REG"], estrategia=aviso, resultado="parcial",
                    dados={"antecedente": "Hora de sair do banho", "comportamento": "Reclamou e chorou um pouco",
                           "consequencia": "Usei o aviso de 5 e de 2 minutos com música", "intensidade": 2, "duracao_min": 6})),
        (7, P, dict(tipo="conquista", local="escola", dominios=["COM_E", "SOC"],
                    texto="Apontou e disse 'dino' para mostrar o livro a um colega.")),
        (5, R, dict(tipo="comportamento", local="casa", dominios=["REG"], estrategia=calma, resultado="funcionou",
                    dados={"antecedente": "Liquidificador ligado", "comportamento": "Tapou os ouvidos e chorou",
                           "consequencia": "Fomos para o cantinho com música, acalmou", "intensidade": 3, "duracao_min": 5})),
        (4, R, dict(tipo="conquista", local="casa", dominios=["FAL"], texto="Juntou duas palavras pela primeira vez: 'mais água'!")),
        (3, R, dict(tipo="checkin_meta", meta_id="meta_1", dominios=["COM_E"], dados={"nivel_gas": 0},
                    texto="Já pede com palavra em 3 de 5 pedidos.")),
        (3, R, dict(tipo="checkin_meta", meta_id="meta_2", dominios=["REG"], dados={"nivel_gas": -1},
                    texto="Trocas melhores com aviso, mas ainda leva uns 10 min.")),
        (2, P, dict(tipo="comportamento", local="escola", dominios=["REG", "ATE"],
                    dados={"antecedente": "Fim do parquinho", "comportamento": "Sentou no chão e não quis entrar",
                           "consequencia": "Cantei a música de guardar e ela veio", "intensidade": 2, "duracao_min": 4})),
        (1, R, dict(tipo="saude", texto="Dormiu às 22h15 com a rotina nova (banho, pijama, música).",
                    dados={"categoria": "Sono"})),
    ]
    for dias, autor, reg in registros:
        repo.inserir_registro({"crianca_id": lia["id"], "avaliacao_id": av_id, "ocorrido_em": _quando(dias), **autor, **reg})

    # Uma conversa anterior no chat, para a aba não começar vazia
    conv = repo.criar_conversa(lia["id"], "responsavel", ana["id"], "Crises na hora do tablet")
    repo.inserir_mensagem(conv["id"], "usuario", "O aviso antes de desligar o tablet não funcionou ontem. O que eu faço?")
    repo.inserir_mensagem(conv["id"], "assistente",
                          "Que bom que você tentou e registrou! Pelo registro, o aviso veio uma vez só, em cima da hora. "
                          "Vale tentar a versão completa da dica: **aviso aos 5 e aos 2 minutos**, com um timer que ela veja, "
                          "e oferecer o que vem depois (\"agora é banho com o dino\"). Registre de novo para compararmos.")
    return ana


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--zerar", action="store_true", help="Apaga o banco local antes de semear")
    a = ap.parse_args()
    if a.zerar and repo.caminho_banco().exists():
        repo.caminho_banco().unlink()
        print(f"Banco apagado: {repo.caminho_banco()}")
    ana = semear_demo()
    print(f"Banco local: {repo.caminho_banco()}")
    print(f"Responsável de demonstração: {ana['nome']} <{ana['email']}> id={ana['id']}")
