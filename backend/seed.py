"""Dados de demonstração do banco local.

    python -m backend.seed            # cria (se ainda não existir) a família de demonstração
    python -m backend.seed --zerar    # apaga o banco local e recria

Família criada:
- Ana Souza (mãe), ana@demo.primeirospassos
- Lia, 3a2m: formulário enviado + perfil APROVADO (relatório real gerado pelo agente,
  src/agente_perfil/exemplos/avaliacao_lia_aprovada.json) + 2 semanas de registros.
  Serve para testar painel e chat na hora, sem esperar o agente.
- Nina, 3a2m: só cadastro. Serve para rodar a jornada completa (formulário → agente → aprovação);
  no formulário, use "Preencher com exemplo".
- Prof. Carla (Creche Municipal Sol, turma Maternal II), com a Lia na turma.
"""
import argparse
import json
from datetime import date, datetime, timedelta, timezone

from src.agente_perfil import config, repositorio as repo

EMAIL_DEMO = "ana@demo.primeirospassos"
EXEMPLOS = config.ROOT / "src/agente_perfil/exemplos"


def _quando(dias_atras: float, hora: int = 18) -> str:
    d = datetime.now(timezone.utc) - timedelta(days=dias_atras)
    return d.replace(hour=hora, minute=0, second=0, microsecond=0).isoformat()


def _nascimento(meses: int) -> str:
    return (date.today() - timedelta(days=int(meses * 30.44) + 5)).isoformat()


def semear_demo() -> dict:
    existente = next(iter(repo._todos("SELECT * FROM responsavel WHERE email = ?", (EMAIL_DEMO,))), None)
    if existente:
        return existente
    from backend.main import Submission, submit

    ana = repo.criar_responsavel("Ana Souza", EMAIL_DEMO, "(21) 90000-0000")
    carla = repo.criar_professor("Carla Mendes", "carla@demo.primeirospassos", "Creche Municipal Sol", "Maternal II")
    turma = repo._todos("SELECT id FROM turma WHERE professor_id = ?", (carla["id"],))[0]["id"]

    lia = repo.criar_crianca("Lia", _nascimento(38), ["dinossauros", "água", "música", "quebra-cabeça"],
                             ana["id"], "Mãe", turma_id=turma)
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
