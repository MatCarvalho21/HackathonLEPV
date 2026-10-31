"""Ferramentas do agente (formato function calling da OpenAI)."""
from __future__ import annotations

import copy
import logging

from src.agente_perfil import config
from src.agente_perfil.dossie import TODOS
from src.agente_perfil.relatorio import Relatorio, RelatorioReavaliacao

logger = logging.getLogger(__name__)


def _sem_refs(schema: dict) -> dict:
    """Resolve $ref/$defs do pydantic: alguns templates de modelos abertos não lidam com referências."""
    defs = schema.pop("$defs", {})

    def resolve(no):
        if isinstance(no, dict):
            if "$ref" in no:
                return resolve(copy.deepcopy(defs[no["$ref"].split("/")[-1]]))
            return {k: resolve(v) for k, v in no.items() if k != "title"}
        if isinstance(no, list):
            return [resolve(v) for v in no]
        return no

    return resolve(schema)


BUSCAR_BASE = {
    "type": "function",
    "function": {
        "name": "consultar_base_conhecimento",
        "description": (
            "Busca trechos na base oficial de desenvolvimento infantil (Caderneta da Criança/MS, CDC, OMS "
            "Caregiver Skills Training, EEF, Harvard funções executivas, Pyramid Model/NCPMI, SWYC, legislação "
            "de educação especial e PEI). Use para fundamentar dicas e metas dos domínios prioritários. "
            "Escreva a consulta em português, específica (domínio + idade + situação)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "consulta": {"type": "string",
                             "description": "Ex.: 'estratégias para ampliar vocabulário de criança de 3 anos em casa'"},
                "dominio": {"type": "string", "enum": TODOS, "description": "Domínio relacionado"},
            },
            "required": ["consulta"],
        },
    },
}

SOLICITAR_INFORMACOES = {
    "type": "function",
    "function": {
        "name": "solicitar_informacoes_responsavel",
        "description": (
            "Pausa a avaliação e envia perguntas complementares ao responsável. Use SOMENTE quando a falta de "
            "informação mudaria a cor de um domínio funcional, a escolha do foco ou a segurança da criança "
            f"(ex.: perda de habilidade sem detalhes). No máximo {config.MAX_PERGUNTAS_POR_RODADA} perguntas, "
            "curtas, concretas e sem jargão. O responsável pode não responder."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "motivo": {"type": "string", "description": "Uma frase para o responsável: por que perguntamos"},
                "perguntas": {
                    "type": "array", "minItems": 1, "maxItems": config.MAX_PERGUNTAS_POR_RODADA,
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Identificador curto, ex.: q1"},
                            "dominio": {"type": "string", "enum": TODOS},
                            "pergunta": {"type": "string"},
                            "tipo": {"type": "string", "enum": ["texto", "escolha"]},
                            "opcoes": {"type": "array", "items": {"type": "string"},
                                       "description": "Obrigatório quando tipo = escolha"},
                        },
                        "required": ["id", "dominio", "pergunta", "tipo"],
                    },
                },
            },
            "required": ["motivo", "perguntas"],
        },
    },
}

ENTREGAR_RELATORIO = {
    "type": "function",
    "function": {
        "name": "entregar_relatorio",
        "description": "Entrega o relatório final de mapeamento de perfil. Ele será validado; se houver erros, corrija e chame de novo.",
        "parameters": _sem_refs(Relatorio.model_json_schema()),
    },
}


ENTREGAR_REAVALIACAO = {
    "type": "function",
    "function": {
        "name": "entregar_relatorio",
        "description": ("Entrega a NOVA versão do perfil (reavaliação), com o balanço da evolução em `evolucao`. "
                        "Ela será validada; se houver erros, corrija e chame de novo."),
        "parameters": _sem_refs(RelatorioReavaliacao.model_json_schema()),
    },
}


def ferramentas_disponiveis(buscas_feitas: int, rodadas_perguntas: int, reavaliacao: bool = False) -> list[dict]:
    tools = []
    if not config.RAG_DESATIVADO and buscas_feitas < config.MAX_BUSCAS_RAG:
        tools.append(BUSCAR_BASE)
    if rodadas_perguntas < config.MAX_RODADAS_PERGUNTAS:
        tools.append(SOLICITAR_INFORMACOES)
    tools.append(ENTREGAR_REAVALIACAO if reavaliacao else ENTREGAR_RELATORIO)
    return tools


# ---------------------------------------------------------------- RAG
_busca = None


def _funcao_busca():
    """Carrega o retriever (bge-m3 + reranker) só na primeira busca."""
    global _busca
    if _busca is None:
        from src.rag.retriever import get_retriever
        _busca = get_retriever().search
    return _busca


def buscar_base(consulta: str, proximo_id: int, top_k: int = 4) -> tuple[str, dict[str, dict]]:
    """Executa a busca e devolve (texto para o modelo, {kb:N: metadados da fonte})."""
    try:
        resultados = _funcao_busca()(query=consulta, top_k=top_k)
    except Exception as e:  # base indisponível não derruba a avaliação
        logger.exception("Falha na busca RAG")
        return f"Base de conhecimento indisponível agora ({type(e).__name__}). Continue sem ela.", {}
    # Trechos com nota baixa do reranker não sustentam nada: melhor não citar do que citar errado.
    resultados = [r for r in resultados if (r.get("rerank_score") or 0) >= config.RAG_MIN_RELEVANCIA]
    if not resultados:
        return "Nenhum trecho relevante encontrado. Tente outra consulta ou siga sem citar a base.", {}
    blocos, fontes = [], {}
    for i, r in enumerate(resultados):
        kid = f"kb:{proximo_id + i}"
        fontes[kid] = {"documento": r["source"], "pagina": r["page"], "secao": r["section"],
                       "consulta": consulta, "relevancia": r.get("rerank_score")}
        blocos.append(f"[{kid}] {r['source']} (p. {r['page']}, seção: {r['section']})\n{r['text'][:1500]}")
    return "\n\n---\n\n".join(blocos), fontes
