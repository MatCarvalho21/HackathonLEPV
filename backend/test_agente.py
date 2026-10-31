import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ["RAG_DESATIVADO"] = "1"

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
        self.tmp = tempfile.TemporaryDirectory(dir="backend")
        os.environ["FORM_DB"] = self.tmp.name + "/t.sqlite3"
        self.client = TestClient(app)
        r = self.client.post("/api/formularios", json=json.loads(EXEMPLO.read_text(encoding="utf-8")))
        self.assertEqual(r.status_code, 201, r.text)
        self.form_id = r.json()["id"]
        self.dossie = montar_dossie(repo.obter_formulario(self.form_id))

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("FORM_DB", None)

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

        self.assertEqual(self.client.get(f"/api/avaliacoes/sessoes/{res['sessao_id']}").json()["status"],
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

        r = self.client.post(f"/api/avaliacoes/{res2['avaliacao_id']}/aprovar")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["status"], "vigente")
        self.assertEqual(self.client.post(f"/api/avaliacoes/{res2['avaliacao_id']}/aprovar").status_code, 409)

    def test_jornada_da_plataforma_registros_e_painel(self):
        ana = self.client.post("/api/responsaveis", json={"nome": "Ana", "email": "ana@x.com"}).json()
        prof = self.client.post("/api/professores", json={"nome": "Carla", "email": "c@x.com", "escola": "Sol", "turma": "M2"}).json()
        c = self.client.post("/api/criancas", json={"nome": "Lia", "data_nascimento": "2023-08-20", "interesses": ["dino"],
                                                    "responsavel_id": ana["id"], "parentesco": "Mãe"}).json()
        cid = c["crianca"]["id"]
        self.assertEqual(c["etapa"], "formulario")
        corpo = {**json.loads(EXEMPLO.read_text(encoding="utf-8")), "crianca_id": cid, "autor_id": ana["id"]}
        fid = self.client.post("/api/formularios", json=corpo).json()["id"]
        self.assertEqual(self.client.get(f"/api/criancas/{cid}/estado").json()["etapa"], "formulario_enviado")
        res = agente.iniciar(fid, LLMRoteiro([("entregar_relatorio", relatorio_valido(self.dossie))]))
        self.assertEqual(self.client.get(f"/api/criancas/{cid}/estado").json()["etapa"], "proposta")
        self.client.post(f"/api/avaliacoes/{res['avaliacao_id']}/aprovar")
        self.assertEqual(self.client.get(f"/api/responsaveis/{ana['id']}/criancas").json()[0]["etapa"], "vigente")
        self.client.post(f"/api/criancas/{cid}/turma", json={"professor_id": prof["id"]})
        self.assertEqual(len(self.client.get(f"/api/professores/{prof['id']}/criancas").json()), 1)

        base = f"/api/criancas/{cid}/registros"
        A = {"autor": "responsavel", "autor_id": ana["id"]}
        ok = [
            {**A, "tipo": "conquista", "texto": "Falou água", "dominios": ["FAL"]},
            {**A, "tipo": "comportamento", "dados": {"antecedente": "tablet", "comportamento": "chorou"},
             "estrategia": "A", "resultado": "funcionou", "local": "casa"},
            {**A, "tipo": "saude", "texto": "Consulta", "dados": {"categoria": "Consulta"}},
            {**A, "tipo": "checkin_meta", "meta_id": "m1", "dados": {"nivel_gas": -1}},
            {"autor": "professor", "autor_id": prof["id"], "tipo": "feedback_estrategia", "estrategia": "A", "resultado": "parcial"},
        ]
        for body in ok:
            self.assertEqual(self.client.post(base, json=body).status_code, 201, body)
        for body in [{**A, "tipo": "checkin_meta", "meta_id": "m1", "dados": {"nivel_gas": 5}},
                     {**A, "tipo": "feedback_estrategia", "estrategia": "A"}, {**A, "tipo": "conquista"},
                     {"autor": "professor", "autor_id": prof["id"], "tipo": "saude", "texto": "x"}]:
            self.assertEqual(self.client.post(base, json=body).status_code, 422, body)
        p = self.client.get(f"/api/criancas/{cid}/painel").json()
        self.assertEqual(p["avaliacao_vigente"]["status"], "vigente")
        self.assertIn("M36_FAL_1", p["avaliacao_vigente"]["evidencias_legiveis"])
        self.assertEqual(len(p["registros"]), 5)
        self.assertEqual(p["checkins_metas"]["m1"][0]["nivel"], -1)
        self.assertEqual({(e["estrategia"], e["funcionou"], e["parcial"]) for e in p["estrategias"]}, {("A", 1, 0), ("A", 0, 1)})

        # chat: contexto inclui perfil e registros; ferramenta de registros funciona
        from src.agente_perfil import chat
        ctx = chat.contexto_crianca(cid)
        self.assertIn("Semáforo", ctx)
        self.assertIn("Falou água", ctx)
        llm = LLMChat([("buscar_registros", {"tipo": "saude"}), "Na consulta, foi isso."])
        r = chat.responder(cid, "O que a pediatra disse?", "responsavel", ana["id"], llm=llm)
        self.assertEqual(r["mensagem_assistente"]["conteudo"], "Na consulta, foi isso.")
        self.assertIn("Consulta", llm.mensagens[-1]["content"])  # resultado da ferramenta chegou ao modelo
        conv = r["conversa"]["id"]
        chat.responder(cid, "E agora?", "responsavel", ana["id"], conv, llm=LLMChat(["Ok."]))
        msgs = self.client.get(f"/api/conversas/{conv}/mensagens").json()
        self.assertEqual([m["papel"] for m in msgs], ["usuario", "assistente", "usuario", "assistente"])
        self.assertEqual(len(self.client.get(f"/api/criancas/{cid}/conversas").json()), 1)

    def test_seed_demo(self):
        r = self.client.post("/api/demo/entrar").json()
        self.assertEqual(self.client.post("/api/demo/entrar").json()["responsavel"]["id"], r["responsavel"]["id"])
        etapas = {c["crianca"]["nome"]: c["etapa"] for c in r["criancas"]}
        self.assertEqual(etapas, {"Lia": "vigente", "Nina": "formulario"})

    def test_rotas_404(self):
        self.assertEqual(self.client.get("/api/avaliacoes/nao-existe").status_code, 404)
        self.assertEqual(self.client.post("/api/avaliacoes/sessoes/x/respostas", json={}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
