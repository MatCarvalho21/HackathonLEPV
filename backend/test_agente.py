import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ["RAG_DESATIVADO"] = "1"
os.environ["SENHA_ITERACOES"] = "1000"  # hash de senha rápido nos testes

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402
from src.agente_perfil import agente, repositorio as repo  # noqa: E402
from src.agente_perfil.dossie import TODOS, montar_dossie, status_por_idade  # noqa: E402
from src.agente_perfil.relatorio import validar  # noqa: E402

EXEMPLO = Path(__file__).resolve().parents[1] / "src/agente_perfil/exemplos/formulario_lia_38m.json"


def relatorio_valido(dossie, **extra):
    status = {d["codigo"]: d["status_calculado"] or "amarelo" for d in dossie["dominios"]}
    gas = {k: "x" for k in ["menos_2", "menos_1", "zero", "mais_1", "mais_2"]}
    meta = lambda i, h, s: {"id": i, "horizonte": h, "dominio": "FAL", "texto": "Pedir água com uma palavra",
                            "prazo_semanas": s, "como_acompanhar": "contar por semana", "quem_participa": ["mãe"], "gas": gas}
    rel = {
        "resumo": "Lia é uma criança carinhosa, que adora dinossauros e quebra-cabeças. " * 2,
        "caracteristicas": ["Carinhosa"],
        "pontos_fortes_gerais": [{"texto": "Quebra-cabeças", "evidencias": ["ctx:COG"]}],
        "dominios": [{"codigo": c, "status": status[c], "justificativa_status": "ok ok",
                      "o_que_observamos": "Observamos algo relevante.",
                      "pontos_fortes": [], "pontos_de_atencao": []} for c in TODOS],
        "foco_prioritario": [{"dominio": "FAL", "por_que": "Prioridade da família"}],
        "metas": [meta("m1", "curto", 4), meta("m2", "medio", 12), meta("m3", "longo", 30)],
        "dicas": [{"dominio": "FAL", "titulo": t, "por_que_ajuda": "x", "como_fazer": ["a"],
                   "momento_do_dia": "banho"} for t in ("A", "B")],
        "proximos_passos": ["Conversar com a pediatra"],
        "limitacoes": "Este mapeamento não substitui avaliação profissional.",
    }
    rel.update(extra)
    return rel


class LLMRoteiro:
    """Devolve, em ordem, chamadas de ferramenta pré-definidas."""

    def __init__(self, passos):
        self.passos = list(passos)
        self.recebidas = []

    def completar(self, mensagens, ferramentas):
        self.recebidas.append([f["function"]["name"] for f in ferramentas])
        nome, args = self.passos.pop(0)
        return {"role": "assistant", "content": "", "uso": {},
                "tool_calls": [{"id": f"c{len(self.recebidas)}", "type": "function",
                                "function": {"name": nome, "arguments": json.dumps(args)}}]}


class LLMChat:
    """Roteiro para o chat: tuplas (ferramenta, args) ou texto final."""

    def __init__(self, passos):
        self.passos = list(passos)
        self.mensagens = []

    def completar(self, mensagens, ferramentas):
        self.mensagens = list(mensagens)
        p = self.passos.pop(0)
        if isinstance(p, str):
            return {"role": "assistant", "content": p, "uso": {}}
        return {"role": "assistant", "content": "", "uso": {}, "tool_calls": [
            {"id": "t1", "type": "function", "function": {"name": p[0], "arguments": json.dumps(p[1])}}]}


class AgenteTests(unittest.TestCase):
    def setUp(self):
        # As rotas 202 disparam o agente numa thread com o LLM real; nos testes o loop roda à mão com LLM falso.
        trava = mock.patch("backend.avaliacoes.threading")
        trava.start()
        self.addCleanup(trava.stop)
        self.tmp = tempfile.TemporaryDirectory(dir="backend")
        os.environ["FORM_DB"] = self.tmp.name + "/t.sqlite3"
        self.client = TestClient(app)
        self.ana = self.conta("responsavel", "Ana", "ana@x.com", vinculo="Avó")
        self.cid = self.client.post("/api/criancas", headers=self.ana["h"], json={
            "nome": "Lia", "data_nascimento": "2023-08-20", "interesses": ["dino"], "parentesco": "Avó"}).json()["crianca"]["id"]
        r = self.client.post("/api/formularios", headers=self.ana["h"], json=self.formulario())
        self.assertEqual(r.status_code, 201, r.text)
        self.form_id = r.json()["id"]
        self.dossie = montar_dossie(repo.obter_formulario(self.form_id))

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("FORM_DB", None)

    # ---------------------------------------------------------------- ajudantes
    def conta(self, tipo, nome, email, **extra):
        r = self.client.post("/api/auth/cadastro", json={"tipo": tipo, "nome": nome, "email": email, "senha": "segredo1", **extra})
        self.assertEqual(r.status_code, 201, r.text)
        j = r.json()
        return {"h": {"Authorization": f"Bearer {j['token']}"}, "id": j["perfis"][0]["id"], "email": email}

    def formulario(self, **extra):
        return {**json.loads(EXEMPLO.read_text(encoding="utf-8")), "crianca_id": self.cid, **extra}

    def compartilhar(self, acomp, funcao="professor"):
        cp = self.client.post(f"/api/criancas/{self.cid}/compartilhamentos", headers=self.ana["h"],
                              json={"email": acomp["email"], "funcao": funcao})
        self.assertEqual(cp.status_code, 201, cp.text)
        self.assertEqual(self.client.post(f"/api/compartilhamentos/{cp.json()['id']}/aceitar", headers=acomp["h"]).status_code, 200)
        return cp.json()

    def perfil_aprovado(self):
        res = agente.iniciar(self.form_id, LLMRoteiro([("entregar_relatorio", relatorio_valido(self.dossie))]))
        r = self.client.post(f"/api/avaliacoes/{res['avaliacao_id']}/aprovar", headers=self.ana["h"])
        self.assertEqual(r.status_code, 200, r.text)
        return res["avaliacao_id"]

    # ---------------------------------------------------------------- regras do agente
    def test_regras_semaforo(self):
        self.assertEqual(status_por_idade(["sim", "sim", "as_vezes"])[0], "verde")
        self.assertEqual(status_por_idade(["sim", "nao"])[0], "amarelo")
        self.assertEqual(status_por_idade(["nao", "nao", "sim"])[0], "vermelho")
        self.assertEqual(status_por_idade(["nao_sei", "nao_sei", "sim"])[0], "cinza")
        self.assertEqual(status_por_idade([])[0], "cinza")
        st = {d["codigo"]: d["status_calculado"] for d in self.dossie["dominios"]}
        self.assertEqual(st["FAL"], "vermelho")
        self.assertEqual(st["COM_R"], "verde")
        self.assertEqual(st["SAU"], "contextual")
        self.assertIsNone(st["REG"])

    def test_validador_bloqueia_diagnostico_e_metas(self):
        rel = relatorio_valido(self.dossie, resumo="Os sinais indicam que Lia tem autismo, por isso precisa de apoio. " * 2)
        _, erros = validar(rel, self.dossie, set(), set())
        self.assertTrue(any("diagnóstica" in e for e in erros))
        rel = relatorio_valido(self.dossie)
        rel["metas"] = rel["metas"][:1]
        _, erros = validar(rel, self.dossie, set(), set())
        self.assertTrue(any("medio" in e for e in erros))

    def test_fluxo_completo_com_pausa_ajuste_e_aprovacao(self):
        perguntar = ("solicitar_informacoes_responsavel", {"motivo": "Entender as crises", "perguntas": [
            {"id": "x", "dominio": "REG", "pergunta": "Quantas crises por semana?", "tipo": "texto"}]})
        invalido = relatorio_valido(self.dossie)
        invalido["dominios"][2]["status"] = "verde"  # FAL calculado = vermelho → corrigido em código
        invalido["dominios"][0]["pontos_fortes"] = [{"texto": "Entende", "evidencias": ["M30_COM_R_1", "inventado"]}]
        invalido["metas"] = invalido["metas"][:2]   # falta longo → modelo precisa corrigir
        valido = relatorio_valido(self.dossie, pontos_fortes_gerais=[{"texto": "Crises", "evidencias": ["extra:r1q1"]}])
        llm = LLMRoteiro([perguntar, ("entregar_relatorio", invalido), ("entregar_relatorio", valido)])

        res = agente.iniciar(self.form_id, llm)
        self.assertEqual(res["status"], "aguardando_responsavel")
        self.assertEqual(res["perguntas"][0]["id"], "r1q1")
        self.assertEqual(self.client.get(f"/api/avaliacoes/sessoes/{res['sessao_id']}", headers=self.ana["h"]).json()["status"],
                         "aguardando_responsavel")
        res = agente.retomar(res["sessao_id"], {"r1q1": "5 por semana"}, llm)
        self.assertEqual(res["status"], "concluida", res.get("erro"))
        self.assertNotIn("solicitar_informacoes_responsavel", llm.recebidas[-1])  # só 1 rodada de perguntas
        av = res["avaliacao"]
        self.assertEqual(av["niveis"]["FAL"], "vermelho")
        self.assertEqual(av["status"], "proposta")
        self.assertIn("extra:r1q1", av["perfil"]["respostas_complementares"])
        sessao = repo.obter_sessao(res["sessao_id"])
        self.assertTrue(any("evidências removidas" in a for a in sessao["ajustes_automaticos"]))

        res2 = agente.ajustar(av["id"], "Quero focar no sono", LLMRoteiro([("entregar_relatorio", valido)]))
        self.assertEqual(res2["status"], "concluida")
        self.assertEqual(repo.obter_avaliacao(av["id"])["status"], "descartada")
        self.assertEqual(res2["avaliacao"]["avaliacao_anterior_id"], av["id"])

        r = self.client.post(f"/api/avaliacoes/{res2['avaliacao_id']}/aprovar", headers=self.ana["h"])
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "vigente")
        self.assertEqual(self.client.post(f"/api/avaliacoes/{res2['avaliacao_id']}/aprovar", headers=self.ana["h"]).status_code, 409)

    # ---------------------------------------------------------------- login
    def test_login_sessao_e_perfis(self):
        self.assertEqual(self.client.get(f"/api/criancas/{self.cid}/painel").status_code, 401)  # sem token
        self.assertEqual(self.client.get("/api/auth/eu", headers={"Authorization": "Bearer inventado"}).status_code, 401)
        dup = self.client.post("/api/auth/cadastro", json={"tipo": "responsavel", "nome": "X", "email": "ANA@x.com", "senha": "segredo1"})
        self.assertEqual(dup.status_code, 409)
        self.assertEqual(self.client.post("/api/auth/entrar", json={"email": "ana@x.com", "senha": "errada"}).status_code, 401)
        r = self.client.post("/api/auth/entrar", json={"email": "Ana@X.com", "senha": "segredo1"})
        self.assertEqual(r.status_code, 200, r.text)
        h = {"Authorization": f"Bearer {r.json()['token']}"}
        self.assertEqual([p["papel"] for p in self.client.get("/api/auth/eu", headers=h).json()["perfis"]], ["responsavel"])
        # a mesma conta ganha o perfil de acompanhante (ex.: avó que também acompanha outra criança)
        r = self.client.post("/api/auth/perfis", headers=h, json={"tipo": "acompanhante", "funcao": "familiar"})
        self.assertEqual([p["papel"] for p in r.json()["perfis"]], ["responsavel", "professor"])
        self.assertEqual(self.client.post("/api/auth/perfis", headers=h, json={"tipo": "acompanhante"}).status_code, 409)
        self.client.post("/api/auth/sair", headers=h)
        self.assertEqual(self.client.get("/api/auth/eu", headers=h).status_code, 401)
        self.assertEqual(self.client.get("/api/auth/eu", headers=self.ana["h"]).status_code, 200)  # outra sessão segue válida

    def test_erro_de_validacao_em_portugues(self):
        r = self.client.post("/api/auth/cadastro", json={"tipo": "acompanhante", "nome": "", "email": "carla@gmail", "senha": "123"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("E-mail inválido", r.json()["detail"])
        self.assertIn("Nome: não pode ficar vazio", r.json()["detail"])
        self.assertIn("Senha: escreva pelo menos 6 caracteres", r.json()["detail"])
        self.assertNotIn("pattern", r.json()["detail"])

    # ---------------------------------------------------------------- compartilhamento e papéis
    def test_compartilhamento_convite_aceite_e_revogacao(self):
        # convite para quem ainda não tem conta: fica pendente pelo e-mail
        cp = self.client.post(f"/api/criancas/{self.cid}/compartilhamentos", headers=self.ana["h"],
                              json={"email": "Rafa@x.com", "funcao": "medico"}).json()
        self.assertEqual((cp["status"], cp["professor_id"]), ("pendente", None))
        self.assertEqual(self.client.post(f"/api/criancas/{self.cid}/compartilhamentos", headers=self.ana["h"],
                                          json={"email": "rafa@x.com", "funcao": "medico"}).status_code, 409)
        rafa = self.conta("acompanhante", "Rafael", "rafa@x.com", funcao="medico")
        intruso = self.conta("acompanhante", "Beto", "beto@x.com")
        convites = self.client.get("/api/eu/convites", headers=rafa["h"]).json()
        self.assertEqual([(c["crianca_nome"], c["funcao_rotulo"], c["responsavel_nome"]) for c in convites], [("Lia", "Médico(a)", "Ana")])
        self.assertEqual(self.client.get(f"/api/criancas/{self.cid}/painel", headers=rafa["h"]).status_code, 403)  # antes de aceitar
        self.assertEqual(self.client.post(f"/api/compartilhamentos/{cp['id']}/aceitar", headers=intruso["h"]).status_code, 403)
        self.assertEqual(self.client.post(f"/api/compartilhamentos/{cp['id']}/aceitar", headers=rafa["h"]).status_code, 200)
        lista = self.client.get("/api/eu/criancas?papel=professor", headers=rafa["h"]).json()
        self.assertEqual([(c["crianca"]["nome"], c["funcao_rotulo"]) for c in lista], [("Lia", "Médico(a)")])
        self.assertEqual(self.client.get(f"/api/criancas/{self.cid}/estado", headers=rafa["h"]).status_code, 200)
        # só o responsável vê e muda quem tem acesso
        self.assertEqual(self.client.get(f"/api/criancas/{self.cid}/compartilhamentos", headers=rafa["h"]).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/compartilhamentos/{cp['id']}", headers=rafa["h"]).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/compartilhamentos/{cp['id']}", headers=self.ana["h"]).status_code, 200)
        self.assertEqual(self.client.get(f"/api/criancas/{self.cid}/painel", headers=rafa["h"]).status_code, 403)
        self.assertEqual(self.client.get("/api/eu/criancas?papel=professor", headers=rafa["h"]).json(), [])

    def test_permissoes_do_acompanhante(self):
        av_id = self.perfil_aprovado()
        carla = self.conta("acompanhante", "Carla", "c@x.com", funcao="pedagogo", instituicao="Escola Sol")
        outro = self.conta("acompanhante", "Beto", "b@x.com")
        self.compartilhar(carla, "pedagogo")
        base = f"/api/criancas/{self.cid}/registros"
        for tipo in ("atividade", "comportamento", "conquista", "observacao"):
            self.assertEqual(self.client.post(base, headers=carla["h"], json={"tipo": tipo, "texto": "ok"}).status_code, 201, tipo)
        for body in [{"tipo": "checkin_meta", "meta_id": "m1", "dados": {"nivel_gas": 0}},
                     {"tipo": "feedback_perfil", "texto": "mudar foco"}, {"tipo": "saude", "texto": "x"}]:
            self.assertEqual(self.client.post(base, headers=carla["h"], json=body).status_code, 403, body)
        # o corpo não decide o papel: mandar autor=responsavel não muda nada
        r = self.client.post(base, headers=carla["h"], json={"tipo": "saude", "texto": "x", "autor": "responsavel"})
        self.assertIn(r.status_code, (403, 422))
        self.assertEqual(self.client.post(base, headers=outro["h"], json={"tipo": "observacao", "texto": "x"}).status_code, 403)
        self.assertEqual(self.client.post(f"/api/criancas/{self.cid}/chat", headers=outro["h"], json={"texto": "oi"}).status_code, 403)
        # perfil, metas e avaliações: só o responsável
        self.assertEqual(self.client.post("/api/formularios", headers=carla["h"], json=self.formulario()).status_code, 403)
        self.assertEqual(self.client.post(f"/api/criancas/{self.cid}/reavaliacoes", headers=carla["h"], json={}).status_code, 403)
        self.assertEqual(self.client.post(f"/api/avaliacoes/{av_id}/ajustes", headers=carla["h"], json={"comentario": "mudar tudo"}).status_code, 403)
        self.assertEqual(self.client.post(f"/api/avaliacoes/{av_id}/aprovar", headers=carla["h"]).status_code, 403)
        self.assertEqual(self.client.get(f"/api/criancas/{self.cid}/formulario-atual", headers=carla["h"]).status_code, 403)
        # leitura liberada; registros mostram a função de quem registrou
        p = self.client.get(f"/api/criancas/{self.cid}/painel", headers=carla["h"]).json()
        self.assertEqual(p["meu_papel"], "professor")
        self.assertEqual({r["autor_funcao"] for r in p["registros"]}, {"pedagogo"})

    def test_jornada_registros_painel_e_chat(self):
        self.assertEqual(self.client.get(f"/api/criancas/{self.cid}/estado", headers=self.ana["h"]).json()["etapa"], "formulario_enviado")
        res = agente.iniciar(self.form_id, LLMRoteiro([("entregar_relatorio", relatorio_valido(self.dossie))]))
        self.assertEqual(self.client.get(f"/api/criancas/{self.cid}/estado", headers=self.ana["h"]).json()["etapa"], "proposta")
        self.client.post(f"/api/avaliacoes/{res['avaliacao_id']}/aprovar", headers=self.ana["h"])
        minhas = self.client.get("/api/eu/criancas?papel=responsavel", headers=self.ana["h"]).json()
        self.assertEqual([(c["crianca"]["nome"], c["etapa"]) for c in minhas], [("Lia", "vigente")])
        carla = self.conta("acompanhante", "Carla", "c@x.com")
        self.compartilhar(carla)

        base = f"/api/criancas/{self.cid}/registros"
        ok = [
            (self.ana, {"tipo": "conquista", "texto": "Falou água", "dominios": ["FAL"]}),
            (self.ana, {"tipo": "comportamento", "dados": {"antecedente": "tablet", "comportamento": "chorou"},
                        "estrategia": "A", "resultado": "funcionou", "local": "casa"}),
            (self.ana, {"tipo": "saude", "texto": "Consulta", "dados": {"categoria": "Consulta"}}),
            (self.ana, {"tipo": "checkin_meta", "meta_id": "m1", "dados": {"nivel_gas": -1}}),
            (carla, {"tipo": "feedback_estrategia", "estrategia": "A", "resultado": "parcial"}),
        ]
        for quem, body in ok:
            self.assertEqual(self.client.post(base, headers=quem["h"], json=body).status_code, 201, body)
        for body in [{"tipo": "checkin_meta", "meta_id": "m1", "dados": {"nivel_gas": 5}},
                     {"tipo": "feedback_estrategia", "estrategia": "A"}, {"tipo": "conquista"}]:
            self.assertEqual(self.client.post(base, headers=self.ana["h"], json=body).status_code, 422, body)
        p = self.client.get(f"/api/criancas/{self.cid}/painel", headers=self.ana["h"]).json()
        self.assertEqual(p["avaliacao_vigente"]["status"], "vigente")
        self.assertIn("M36_FAL_1", p["avaliacao_vigente"]["evidencias_legiveis"])
        self.assertEqual(len(p["registros"]), 5)
        self.assertEqual(p["checkins_metas"]["m1"][0]["nivel"], -1)
        self.assertEqual({(e["estrategia"], e["funcionou"], e["parcial"]) for e in p["estrategias"]}, {("A", 1, 0), ("A", 0, 1)})
        self.assertEqual({(e["nome"], e["funcao"]) for e in p["equipe"]}, {("Ana", "Avó"), ("Carla", "professor")})

        # chat com IA: contexto inclui perfil e registros; cada pessoa vê só as próprias conversas
        from src.agente_perfil import chat
        ctx = chat.contexto_crianca(self.cid)
        self.assertIn("Semáforo", ctx)
        self.assertIn("Falou água", ctx)
        llm = LLMChat([("buscar_registros", {"tipo": "saude"}), "Na consulta, foi isso."])
        r = chat.responder(self.cid, "O que a pediatra disse?", "responsavel", self.ana["id"], llm=llm)
        self.assertEqual(r["mensagem_assistente"]["conteudo"], "Na consulta, foi isso.")
        self.assertIn("Consulta", llm.mensagens[-1]["content"])  # resultado da ferramenta chegou ao modelo
        conv = r["conversa"]["id"]
        chat.responder(self.cid, "E agora?", "responsavel", self.ana["id"], conv, llm=LLMChat(["Ok."]))
        msgs = self.client.get(f"/api/conversas/{conv}/mensagens", headers=self.ana["h"]).json()
        self.assertEqual([m["papel"] for m in msgs], ["usuario", "assistente", "usuario", "assistente"])
        self.assertEqual(len(self.client.get(f"/api/criancas/{self.cid}/conversas", headers=self.ana["h"]).json()), 1)
        self.assertEqual(self.client.get(f"/api/criancas/{self.cid}/conversas", headers=carla["h"]).json(), [])
        self.assertEqual(self.client.get(f"/api/conversas/{conv}/mensagens", headers=carla["h"]).status_code, 403)

    def test_canal_da_crianca(self):
        carla = self.conta("acompanhante", "Carla", "c@x.com")
        fora = self.conta("acompanhante", "Beto", "b@x.com")
        self.compartilhar(carla)
        url = f"/api/criancas/{self.cid}/canal"
        m1 = self.client.post(url, headers=self.ana["h"], json={"texto": "Oi, Carla!"}).json()
        self.client.post(url, headers=carla["h"], json={"texto": "Oi, Ana! Hoje ela brincou no tanque de areia."})
        self.assertEqual(self.client.post(url, headers=fora["h"], json={"texto": "x"}).status_code, 403)
        self.assertEqual(self.client.get(url, headers=fora["h"]).status_code, 403)
        visto = self.client.get(url, headers=carla["h"]).json()
        self.assertEqual([(m["autor_nome"], m["funcao_rotulo"], m["minha"]) for m in visto["mensagens"]],
                         [("Ana", "Responsável", False), ("Carla", "Professor(a)", True)])
        self.assertEqual(len(visto["equipe"]), 2)
        novas = self.client.get(url, headers=self.ana["h"], params={"depois": m1["criado_em"]}).json()["mensagens"]
        self.assertEqual([m["autor_nome"] for m in novas], ["Carla"])

    def test_notificacoes_da_equipe(self):
        carla = self.conta("acompanhante", "Carla", "c@x.com")
        rafa = self.conta("acompanhante", "Rafael", "r@x.com", funcao="medico")
        fora = self.conta("acompanhante", "Beto", "b@x.com")
        # convite para quem já tem conta gera notificação; aceite avisa o responsável
        cp = self.client.post(f"/api/criancas/{self.cid}/compartilhamentos", headers=self.ana["h"], json={"email": "c@x.com"}).json()
        self.assertEqual([n["tipo"] for n in self.client.get("/api/eu/notificacoes", headers=carla["h"]).json()["notificacoes"]], ["convite"])
        self.client.post(f"/api/compartilhamentos/{cp['id']}/aceitar", headers=carla["h"])
        self.compartilhar(rafa, "medico")
        nana = self.client.get("/api/eu/notificacoes", headers=self.ana["h"]).json()
        self.assertEqual(sorted(n["tipo"] for n in nana["notificacoes"]), ["acesso", "acesso"])
        self.client.post("/api/eu/notificacoes/ler-todas", headers=self.ana["h"], json={})
        self.client.post("/api/eu/notificacoes/ler-todas", headers=carla["h"], json={})
        self.client.post("/api/eu/notificacoes/ler-todas", headers=rafa["h"], json={})

        # registro de um acompanhante: avisa o responsável e o outro acompanhante, não quem registrou
        reg = self.client.post(f"/api/criancas/{self.cid}/registros", headers=carla["h"],
                               json={"tipo": "conquista", "texto": "Pediu água falando na escola"}).json()
        n_ana = self.client.get("/api/eu/notificacoes", headers=self.ana["h"]).json()
        self.assertEqual(n_ana["nao_lidas"], 1)
        n = n_ana["notificacoes"][0]
        self.assertEqual((n["tipo"], n["ref_id"], n["crianca_nome"]), ("registro", reg["id"], "Lia"))
        self.assertIn("Carla, professor(a), registrou uma conquista sobre Lia", n["titulo"])
        self.assertEqual(self.client.get("/api/eu/notificacoes", headers=rafa["h"]).json()["nao_lidas"], 1)
        self.assertEqual(self.client.get("/api/eu/notificacoes", headers=carla["h"]).json()["nao_lidas"], 0)
        self.assertEqual(self.client.get("/api/eu/notificacoes", headers=fora["h"]).json()["nao_lidas"], 0)
        # ler e apagar: só as próprias
        self.assertEqual(self.client.post(f"/api/notificacoes/{n['id']}/lida", headers=rafa["h"]).status_code, 404)
        self.assertEqual(self.client.post(f"/api/notificacoes/{n['id']}/lida", headers=self.ana["h"]).json()["nao_lidas"], 0)
        self.assertEqual(self.client.get("/api/eu/notificacoes", headers=self.ana["h"]).json()["notificacoes"][0]["lida_em"] is not None, True)
        self.assertEqual(self.client.delete(f"/api/notificacoes/{n['id']}", headers=self.ana["h"]).status_code, 200)
        self.assertNotIn(n["id"], [x["id"] for x in self.client.get("/api/eu/notificacoes", headers=self.ana["h"]).json()["notificacoes"]])

        # canal: avisa a equipe; abrir o canal marca como lidas as mensagens daquela criança
        self.client.post(f"/api/criancas/{self.cid}/canal", headers=self.ana["h"], json={"texto": "Oi, equipe!"})
        self.assertEqual(self.client.get("/api/eu/notificacoes", headers=carla["h"]).json()["nao_lidas"], 1)
        self.client.get(f"/api/criancas/{self.cid}/canal", headers=carla["h"])
        self.assertEqual(self.client.get("/api/eu/notificacoes", headers=carla["h"]).json()["nao_lidas"], 0)

        # perfil aprovado: avisa só os acompanhantes
        antes = self.client.get("/api/eu/notificacoes", headers=self.ana["h"]).json()["nao_lidas"]
        self.perfil_aprovado()
        self.assertEqual([x["tipo"] for x in self.client.get("/api/eu/notificacoes", headers=rafa["h"]).json()["notificacoes"]
                          if x["lida_em"] is None], ["perfil", "canal", "registro"])
        self.assertEqual(self.client.get("/api/eu/notificacoes", headers=self.ana["h"]).json()["nao_lidas"], antes)
        # quem perde o acesso deixa de ser avisado
        self.client.post("/api/eu/notificacoes/ler-todas", headers=carla["h"], json={})
        self.client.delete(f"/api/compartilhamentos/{cp['id']}", headers=self.ana["h"])
        self.client.post(f"/api/criancas/{self.cid}/registros", headers=self.ana["h"], json={"tipo": "observacao", "texto": "x"})
        self.assertEqual(self.client.get("/api/eu/notificacoes", headers=carla["h"]).json()["nao_lidas"], 0)

    def test_resumo_pdf(self):
        r = self.client.get(f"/api/criancas/{self.cid}/resumo.pdf", headers=self.ana["h"])  # ainda sem perfil: ficha básica
        self.assertEqual(r.status_code, 200)
        self.perfil_aprovado()
        carla = self.conta("acompanhante", "Carla", "c@x.com")
        self.compartilhar(carla)
        for quem in (self.ana, carla):
            r = self.client.get(f"/api/criancas/{self.cid}/resumo.pdf", headers=quem["h"])
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.headers["content-type"], "application/pdf")
            self.assertTrue(r.content.startswith(b"%PDF"))
            self.assertIn("resumo-lia-", r.headers["content-disposition"])
        fora = self.conta("acompanhante", "Beto", "b@x.com")
        self.assertEqual(self.client.get(f"/api/criancas/{self.cid}/resumo.pdf", headers=fora["h"]).status_code, 403)

    # ---------------------------------------------------------------- reavaliação
    def test_reavaliacao_com_pergunta_ajuste_e_evolucao(self):
        from src.agente_perfil.reavaliacao import montar_dossie_reavaliacao
        av_id = self.perfil_aprovado()
        carla = self.conta("acompanhante", "Carla", "c@x.com")
        self.compartilhar(carla)
        base = f"/api/criancas/{self.cid}/registros"
        conquista = self.client.post(base, headers=carla["h"], json={"tipo": "conquista", "texto": "Pediu água falando na escola",
                                                                     "dominios": ["FAL"], "local": "escola"}).json()
        self.client.post(base, headers=self.ana["h"], json={"tipo": "checkin_meta", "meta_id": "m1", "dados": {"nivel_gas": 0}})
        reg = f"reg:{conquista['id'][:8]}"

        r = self.client.post(f"/api/criancas/{self.cid}/reavaliacoes", headers=self.ana["h"], json={"comentario": "Quero focar no sono"})
        self.assertEqual(r.status_code, 202, r.text)
        sessao = repo.obter_sessao(r.json()["sessao_id"])
        self.assertEqual(sessao["tipo"], "reavaliacao")
        self.assertIn(reg, sessao["dossie"]["_evidencias_validas"])
        self.assertTrue(any("Carla (professor(a))" in linha for linha in sessao["dossie"]["registros_desde_a_ultima_avaliacao"]))
        self.assertIsNone(sessao["dossie"]["formulario_atualizado"])
        self.assertEqual(self.client.get(f"/api/criancas/{self.cid}/estado", headers=self.ana["h"]).json()["reavaliacao"]["etapa"], "analise")
        self.assertEqual(self.client.post(f"/api/criancas/{self.cid}/reavaliacoes", headers=self.ana["h"], json={}).status_code, 409)

        dossie = montar_dossie_reavaliacao(self.cid, repo.avaliacao_vigente(self.cid), "Quero focar no sono")
        rel = relatorio_valido(dossie)
        for d in rel["dominios"]:
            d["status"] = next(x["status_anterior"] for x in dossie["dominios"] if x["codigo"] == d["codigo"])
        rel["dominios"][2]["status"] = "amarelo"  # FAL: vermelho → amarelo
        rel["dominios"][2]["pontos_fortes"] = [{"texto": "Pediu água falando", "evidencias": [reg]}]
        rel["metas"] = [{**rel["metas"][0], "id": "meta_r2_1"}, *rel["metas"][1:]]
        evolucao = lambda **kw: {"resumo": "Lia avançou na fala: já pede água com palavras em casa e na escola. " * 2, **kw}
        sem_balanco = {**rel, "evolucao": evolucao(metas_anteriores=[])}
        valido = {**rel, "evolucao": evolucao(
            conquistas=[{"texto": "Pediu água falando na escola", "evidencias": [reg, "inventada"]}],
            areas=[{"codigo": "FAL", "antes": "verde", "depois": "verde", "o_que_mudou": "Passou a pedir com palavras", "evidencias": [reg]}],
            metas_anteriores=[
                {"meta_id": "m1", "situacao": "alcancada", "comentario": "Chegou ao nível 0", "destino": "concluida"},
                {"meta_id": "m2", "situacao": "sem_dados", "comentario": "Sem registros", "destino": "mantida"},
                {"meta_id": "m3", "situacao": "em_progresso", "comentario": "Segue", "destino": "mantida"}],
            o_que_funcionou=["Esperar com o copo na mão"])}
        perguntar = ("solicitar_informacoes_responsavel", {"motivo": "Metas sem registro", "perguntas": [
            {"id": "q", "dominio": "FAL", "pergunta": "Como está a meta m2?", "tipo": "texto"}]})
        llm = LLMRoteiro([perguntar, ("entregar_relatorio", sem_balanco), ("entregar_relatorio", valido)])
        res = agente.executar(sessao, llm)
        self.assertEqual((res["status"], res["tipo"]), ("aguardando_responsavel", "reavaliacao"))
        self.assertEqual(self.client.post(f"/api/avaliacoes/sessoes/{res['sessao_id']}/respostas", headers=carla["h"],
                                          json={"respostas": {}}).status_code, 403)  # acompanhante não responde
        res = agente.retomar(res["sessao_id"], {"r1q1": "Ainda não começamos"}, llm)
        self.assertEqual(res["status"], "concluida", res.get("erro"))
        sessao = repo.obter_sessao(res["sessao_id"])
        self.assertTrue(any("Faltando" in m.get("content", "") for m in sessao["mensagens"] if m["role"] == "tool"))

        av = self.client.get(f"/api/avaliacoes/{res['avaliacao_id']}", headers=self.ana["h"]).json()
        self.assertEqual((av["tipo"], av["status"]), ("reavaliacao", "proposta"))
        cmp = av["perfil"]["reavaliacao"]
        self.assertEqual((cmp["base_id"], cmp["formulario_atualizado"]), (av_id, False))
        self.assertEqual(cmp["registros"], {"total": 2, "por_tipo": {"conquista": 1, "checkin_meta": 1}, "por_responsavel": 1, "por_professor": 1})
        fal = next(a for a in cmp["areas"] if a["codigo"] == "FAL")
        self.assertEqual((fal["antes"], fal["depois"], fal["direcao"]), ("vermelho", "amarelo", "melhorou"))
        m1 = next(m for m in cmp["metas"] if m["id"] == "m1")
        self.assertEqual((m1["niveis"], m1["continua"]), ([0], False))
        area = av["perfil"]["relatorio"]["evolucao"]["areas"][0]
        self.assertEqual((area["antes"], area["depois"]), ("vermelho", "amarelo"))  # corrigido em código
        self.assertEqual(av["perfil"]["relatorio"]["evolucao"]["conquistas"][0]["evidencias"], [reg])
        self.assertEqual(av["evidencias_legiveis"][reg]["tipo"], "registro")

        aj = self.client.post(f"/api/avaliacoes/{av['id']}/ajustes", headers=self.ana["h"], json={"comentario": "Mantenha a meta do sono"})
        self.assertEqual(aj.status_code, 202, aj.text)
        s2 = repo.obter_sessao(aj.json()["sessao_id"])
        self.assertEqual(s2["tipo"], "reavaliacao")
        res2 = agente.executar(s2, LLMRoteiro([("entregar_relatorio", valido)]))
        self.assertEqual(res2["status"], "concluida", res2.get("erro"))
        self.assertEqual(repo.obter_avaliacao(av["id"])["status"], "descartada")

        r = self.client.post(f"/api/avaliacoes/{res2['avaliacao_id']}/aprovar", headers=self.ana["h"])
        self.assertEqual(r.json()["status"], "vigente")
        self.assertEqual(repo.obter_avaliacao(av_id)["status"], "substituida")
        estado = self.client.get(f"/api/criancas/{self.cid}/estado", headers=self.ana["h"]).json()
        self.assertEqual((estado["etapa"], estado["versoes_aprovadas"], estado["reavaliacao"]), ("vigente", 2, None))
        versoes = self.client.get(f"/api/criancas/{self.cid}/painel", headers=self.ana["h"]).json()["avaliacoes"]
        self.assertEqual([v["niveis"]["FAL"] for v in versoes if v["status"] != "descartada"], ["vermelho", "amarelo"])

    def test_reavaliacao_com_formulario_atualizado(self):
        av_id = self.perfil_aprovado()
        atual = self.client.get(f"/api/criancas/{self.cid}/formulario-atual", headers=self.ana["h"]).json()
        self.assertEqual(atual["respostas"]["M36_FAL_1"]["resposta"], self.formulario()["respostas"]["M36_FAL_1"]["resposta"])
        # a família atualiza o formulário: agora todos os marcos de fala acontecem
        fal = [i["id"] for d in self.dossie["dominios"] if d["codigo"] == "FAL" for i in d["itens"]]
        novo = self.formulario()
        novo["respostas"] = {k: ({"resposta": "sim", "exemplo": "fala frases"} if k in fal else v) for k, v in novo["respostas"].items()}
        fid = self.client.post("/api/formularios", headers=self.ana["h"], json=novo).json()["id"]
        r = self.client.post(f"/api/criancas/{self.cid}/reavaliacoes", headers=self.ana["h"], json={"formulario_id": fid})
        self.assertEqual(r.status_code, 202, r.text)
        sessao = repo.obter_sessao(r.json()["sessao_id"])
        st = {d["codigo"]: d["status_calculado"] for d in sessao["dossie"]["dominios"]}
        self.assertEqual((st["FAL"], st["REG"], st["SAU"]), ("verde", None, "contextual"))  # recalculado pelas respostas novas
        self.assertIsNotNone(sessao["dossie"]["formulario_atualizado"])
        self.assertEqual(sessao["formulario_id"], fid)

        rel = relatorio_valido(sessao["dossie"])
        for d in rel["dominios"]:
            d["status"] = st[d["codigo"]] or next(x["status_anterior"] for x in sessao["dossie"]["dominios"] if x["codigo"] == d["codigo"])
        rel["dominios"][2]["status"] = "amarelo"  # o modelo erra a cor calculada → código corrige para verde
        balanco = [{"meta_id": m, "situacao": "em_progresso", "comentario": "Segue bem", "destino": "mantida"} for m in ("m1", "m2", "m3")]
        rel["evolucao"] = {"resumo": "Lia passou a falar frases, como a família contou no formulário atualizado. " * 2,
                           "areas": [{"codigo": "FAL", "antes": "vermelho", "depois": "verde", "o_que_mudou": "Agora fala frases curtas",
                                      "evidencias": [fal[0]]}], "metas_anteriores": balanco}
        res = agente.executar(sessao, LLMRoteiro([("entregar_relatorio", rel)]))
        self.assertEqual(res["status"], "concluida", res.get("erro"))
        av = repo.obter_avaliacao(res["avaliacao_id"])
        self.assertEqual((av["niveis"]["FAL"], av["formulario_id"]), ("verde", fid))
        self.assertTrue(av["perfil"]["reavaliacao"]["formulario_atualizado"])
        self.assertEqual(av["perfil"]["reavaliacao"]["base_id"], av_id)

    # ---------------------------------------------------------------- demo e rotas
    def test_seed_demo(self):
        r = self.client.post("/api/demo/entrar").json()
        h = {"Authorization": f"Bearer {r['token']}"}
        self.assertEqual(r["conta"]["email"], "ana@demo.primeirospassos")
        self.assertEqual(self.client.post("/api/demo/entrar").json()["conta"]["id"], r["conta"]["id"])  # idempotente
        etapas = {c["crianca"]["nome"]: c["etapa"] for c in self.client.get("/api/eu/criancas", headers=h).json()}
        self.assertEqual(etapas, {"Lia": "vigente", "Nina": "formulario"})
        entrada = self.client.post("/api/auth/entrar", json={"email": "carla@demo.primeirospassos", "senha": "demo1234"})
        self.assertEqual(entrada.status_code, 200)
        hp = {"Authorization": f"Bearer {self.client.post('/api/demo/entrar-professor').json()['token']}"}
        self.assertEqual(sorted(c["crianca"]["nome"] for c in self.client.get("/api/eu/criancas?papel=professor", headers=hp).json()),
                         ["Lia", "Nina"])
        lia = next(c["crianca"]["id"] for c in self.client.get("/api/eu/criancas", headers=h).json() if c["crianca"]["nome"] == "Lia")
        canal = self.client.get(f"/api/criancas/{lia}/canal", headers=hp).json()
        self.assertEqual(len(canal["mensagens"]), 4)
        self.assertEqual(sorted(e["funcao_rotulo"] for e in canal["equipe"]), ["Mãe", "Médico(a)", "Professor(a)"])

    def test_rotas_404_e_401(self):
        self.assertEqual(self.client.get("/api/avaliacoes/nao-existe", headers=self.ana["h"]).status_code, 404)
        self.assertEqual(self.client.get("/api/avaliacoes/nao-existe").status_code, 401)
        self.assertEqual(self.client.post("/api/avaliacoes/sessoes/x/respostas", headers=self.ana["h"], json={}).status_code, 404)
        self.assertEqual(self.client.get("/api/criancas/x/painel", headers=self.ana["h"]).status_code, 404)


if __name__ == "__main__":
    unittest.main()
