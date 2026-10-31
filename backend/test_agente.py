import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
        # As rotas 202 disparam o agente numa thread com o LLM real; nos testes o loop roda à mão com LLM falso.
        trava = mock.patch("backend.avaliacoes.threading")
        trava.start()
        self.addCleanup(trava.stop)
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
                     {**A, "tipo": "feedback_estrategia", "estrategia": "A"}, {**A, "tipo": "conquista"}]:
            self.assertEqual(self.client.post(base, json=body).status_code, 422, body)
        self.assertEqual(self.client.post(base, json={"autor": "professor", "autor_id": prof["id"], "tipo": "saude",
                                                      "texto": "x"}).status_code, 403)
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

    def _crianca_com_perfil(self):
        """Responsável + professor + criança com perfil vigente (via agente falso)."""
        ana = self.client.post("/api/responsaveis", json={"nome": "Ana", "email": "ana@x.com"}).json()
        prof = self.client.post("/api/professores", json={"nome": "Carla", "email": "c@x.com", "escola": "Sol", "turma": "M2"}).json()
        cid = self.client.post("/api/criancas", json={"nome": "Lia", "data_nascimento": "2023-08-20", "responsavel_id": ana["id"]}).json()["crianca"]["id"]
        corpo = {**json.loads(EXEMPLO.read_text(encoding="utf-8")), "crianca_id": cid, "autor_id": ana["id"]}
        fid = self.client.post("/api/formularios", json=corpo).json()["id"]
        res = agente.iniciar(fid, LLMRoteiro([("entregar_relatorio", relatorio_valido(self.dossie))]))
        self.client.post(f"/api/avaliacoes/{res['avaliacao_id']}/aprovar", json={"responsavel_id": ana["id"]})
        self.client.post(f"/api/criancas/{cid}/turma", json={"professor_id": prof["id"]})
        return ana, prof, cid, res["avaliacao_id"]

    def test_permissoes_do_professor(self):
        ana, prof, cid, av_id = self._crianca_com_perfil()
        outro = self.client.post("/api/professores", json={"nome": "Beto", "email": "b@x.com", "escola": "Lua", "turma": "M1"}).json()
        P = {"autor": "professor", "autor_id": prof["id"]}
        base = f"/api/criancas/{cid}/registros"
        for tipo in ("atividade", "comportamento", "conquista", "observacao"):
            self.assertEqual(self.client.post(base, json={**P, "tipo": tipo, "texto": "ok"}).status_code, 201, tipo)
        for body in [{**P, "tipo": "checkin_meta", "meta_id": "m1", "dados": {"nivel_gas": 0}},
                     {**P, "tipo": "feedback_perfil", "texto": "mudar foco"},
                     {"autor": "professor", "autor_id": outro["id"], "tipo": "observacao", "texto": "x"},  # outra turma
                     {"autor": "responsavel", "autor_id": prof["id"], "tipo": "observacao", "texto": "x"}]:  # se passando por responsável
            self.assertEqual(self.client.post(base, json=body).status_code, 403, body)
        self.assertEqual(self.client.post(f"/api/criancas/{cid}/chat", json={**{"autor_id": outro["id"]}, "autor": "professor", "texto": "oi"}).status_code, 403)
        # perfil, metas e avaliações: só o responsável
        corpo = {**json.loads(EXEMPLO.read_text(encoding="utf-8")), "crianca_id": cid, "autor_id": prof["id"], "informante": "professor"}
        self.assertEqual(self.client.post("/api/formularios", json=corpo).status_code, 403)
        self.assertEqual(self.client.post(f"/api/criancas/{cid}/reavaliacoes", json={"responsavel_id": prof["id"]}).status_code, 403)
        self.assertEqual(self.client.post(f"/api/avaliacoes/{av_id}/ajustes", json={"comentario": "mudar tudo", "responsavel_id": prof["id"]}).status_code, 403)
        self.assertEqual(self.client.post(f"/api/avaliacoes/{av_id}/aprovar", json={"responsavel_id": prof["id"]}).status_code, 403)
        # professor vê a criança vinculada
        lista = self.client.get(f"/api/professores/{prof['id']}/criancas").json()
        self.assertEqual([c["etapa"] for c in lista], ["vigente"])

    def test_erro_de_validacao_em_portugues(self):
        r = self.client.post("/api/professores", json={"nome": "Carla", "email": "carla@gmail", "escola": "Sol", "turma": ""})
        self.assertEqual(r.status_code, 422)
        self.assertIn("E-mail inválido", r.json()["detail"])
        self.assertIn("Turma: não pode ficar vazio", r.json()["detail"])
        self.assertNotIn("pattern", r.json()["detail"])

    def test_reavaliacao_com_pergunta_ajuste_e_evolucao(self):
        from src.agente_perfil.reavaliacao import montar_dossie_reavaliacao
        ana, prof, cid, av_id = self._crianca_com_perfil()
        R, P = {"autor": "responsavel", "autor_id": ana["id"]}, {"autor": "professor", "autor_id": prof["id"]}
        base = f"/api/criancas/{cid}/registros"
        conquista = self.client.post(base, json={**P, "tipo": "conquista", "texto": "Pediu água falando na escola", "dominios": ["FAL"], "local": "escola"}).json()
        self.client.post(base, json={**R, "tipo": "checkin_meta", "meta_id": "m1", "dados": {"nivel_gas": 0}})
        reg = f"reg:{conquista['id'][:8]}"

        # sem perfil vigente não há reavaliação; com ele, a sessão nasce com o dossiê de registros
        r = self.client.post(f"/api/criancas/{cid}/reavaliacoes", json={"responsavel_id": ana["id"], "comentario": "Quero focar no sono"})
        self.assertEqual(r.status_code, 202, r.text)
        sessao = repo.obter_sessao(r.json()["sessao_id"])
        self.assertEqual(sessao["tipo"], "reavaliacao")
        self.assertIn(reg, sessao["dossie"]["_evidencias_validas"])
        self.assertTrue(any("Carla (professor(a))" in linha for linha in sessao["dossie"]["registros_desde_a_ultima_avaliacao"]))
        self.assertEqual(self.client.get(f"/api/criancas/{cid}/estado").json()["reavaliacao"]["etapa"], "analise")
        self.assertEqual(self.client.post(f"/api/criancas/{cid}/reavaliacoes", json={"responsavel_id": ana["id"]}).status_code, 409)

        dossie = montar_dossie_reavaliacao(cid, repo.avaliacao_vigente(cid), "Quero focar no sono")
        rel = relatorio_valido(dossie)
        for d in rel["dominios"]:
            d["status"] = next(x["status_anterior"] for x in dossie["dominios"] if x["codigo"] == d["codigo"])
        rel["dominios"][2]["status"] = "amarelo"  # FAL: vermelho → amarelo
        rel["dominios"][2]["pontos_fortes"] = [{"texto": "Pediu água falando", "evidencias": [reg]}]
        meta_nova = {**rel["metas"][0], "id": "meta_r2_1"}
        rel["metas"] = [meta_nova, *rel["metas"][1:]]
        sem_balanco = {**rel, "evolucao": {"resumo": "Lia avançou na fala: já pede água com palavras em casa e na escola. " * 2,
                                           "metas_anteriores": []}}
        valido = {**rel, "evolucao": {
            "resumo": "Lia avançou na fala: já pede água com palavras em casa e na escola. " * 2,
            "conquistas": [{"texto": "Pediu água falando na escola", "evidencias": [reg, "inventada"]}],
            "areas": [{"codigo": "FAL", "antes": "verde", "depois": "verde", "o_que_mudou": "Passou a pedir com palavras", "evidencias": [reg]}],
            "metas_anteriores": [
                {"meta_id": "m1", "situacao": "alcancada", "comentario": "Chegou ao nível 0", "destino": "concluida"},
                {"meta_id": "m2", "situacao": "sem_dados", "comentario": "Sem registros", "destino": "mantida"},
                {"meta_id": "m3", "situacao": "em_progresso", "comentario": "Segue", "destino": "mantida"}],
            "o_que_funcionou": ["Esperar com o copo na mão"]}}
        perguntar = ("solicitar_informacoes_responsavel", {"motivo": "Metas sem registro", "perguntas": [
            {"id": "q", "dominio": "FAL", "pergunta": "Como está a meta m2?", "tipo": "texto"}]})
        llm = LLMRoteiro([perguntar, ("entregar_relatorio", sem_balanco), ("entregar_relatorio", valido)])
        res = agente.executar(sessao, llm)
        self.assertEqual(res["status"], "aguardando_responsavel")
        self.assertEqual(res["tipo"], "reavaliacao")
        res = agente.retomar(res["sessao_id"], {"r1q1": "Ainda não começamos"}, llm)
        self.assertEqual(res["status"], "concluida", res.get("erro"))
        self.assertIn("entregar_relatorio", llm.recebidas[-1])
        sessao = repo.obter_sessao(res["sessao_id"])
        self.assertTrue(any("Faltando" in m.get("content", "") for m in sessao["mensagens"] if m["role"] == "tool"))

        av = self.client.get(f"/api/avaliacoes/{res['avaliacao_id']}").json()
        self.assertEqual((av["tipo"], av["status"]), ("reavaliacao", "proposta"))
        cmp = av["perfil"]["reavaliacao"]
        self.assertEqual(cmp["base_id"], av_id)
        self.assertEqual(cmp["registros"], {"total": 2, "por_tipo": {"conquista": 1, "checkin_meta": 1}, "por_responsavel": 1, "por_professor": 1})
        fal = next(a for a in cmp["areas"] if a["codigo"] == "FAL")
        self.assertEqual((fal["antes"], fal["depois"], fal["direcao"]), ("vermelho", "amarelo", "melhorou"))
        m1 = next(m for m in cmp["metas"] if m["id"] == "m1")
        self.assertEqual((m1["niveis"], m1["continua"]), ([0], False))
        area = av["perfil"]["relatorio"]["evolucao"]["areas"][0]
        self.assertEqual((area["antes"], area["depois"]), ("vermelho", "amarelo"))  # corrigido em código
        self.assertEqual(av["perfil"]["relatorio"]["evolucao"]["conquistas"][0]["evidencias"], [reg])
        self.assertEqual(av["evidencias_legiveis"][reg]["tipo"], "registro")
        self.assertEqual(self.client.get(f"/api/criancas/{cid}/estado").json()["reavaliacao"]["etapa"], "proposta")

        # ajuste da reavaliação continua sendo reavaliação, comparada com a mesma base
        aj = self.client.post(f"/api/avaliacoes/{av['id']}/ajustes", json={"comentario": "Mantenha a meta do sono", "responsavel_id": ana["id"]})
        self.assertEqual(aj.status_code, 202, aj.text)
        s2 = repo.obter_sessao(aj.json()["sessao_id"])
        self.assertEqual(s2["tipo"], "reavaliacao")
        res2 = agente.executar(s2, LLMRoteiro([("entregar_relatorio", valido)]))
        self.assertEqual(res2["status"], "concluida", res2.get("erro"))
        self.assertEqual(repo.obter_avaliacao(av["id"])["status"], "descartada")

        r = self.client.post(f"/api/avaliacoes/{res2['avaliacao_id']}/aprovar", json={"responsavel_id": ana["id"]})
        self.assertEqual(r.json()["status"], "vigente")
        self.assertEqual(repo.obter_avaliacao(av_id)["status"], "substituida")
        estado = self.client.get(f"/api/criancas/{cid}/estado").json()
        self.assertEqual((estado["etapa"], estado["versoes_aprovadas"], estado["reavaliacao"]), ("vigente", 2, None))
        versoes = self.client.get(f"/api/criancas/{cid}/painel").json()["avaliacoes"]
        self.assertEqual([v["niveis"]["FAL"] for v in versoes if v["status"] != "descartada"], ["vermelho", "amarelo"])

    def test_seed_demo(self):
        r = self.client.post("/api/demo/entrar").json()
        self.assertEqual(self.client.post("/api/demo/entrar").json()["responsavel"]["id"], r["responsavel"]["id"])
        etapas = {c["crianca"]["nome"]: c["etapa"] for c in r["criancas"]}
        self.assertEqual(etapas, {"Lia": "vigente", "Nina": "formulario"})
        prof = self.client.post("/api/demo/entrar-professor").json()
        self.assertEqual(sorted(c["crianca"]["nome"] for c in prof["criancas"]), ["Lia", "Nina"])

    def test_rotas_404(self):
        self.assertEqual(self.client.get("/api/avaliacoes/nao-existe").status_code, 404)
        self.assertEqual(self.client.post("/api/avaliacoes/sessoes/x/respostas", json={}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
