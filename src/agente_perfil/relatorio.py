"""Esquema do relatório de perfil e validação em código.

O modelo entrega o relatório chamando a ferramenta `entregar_relatorio`. Se a
validação falhar, os erros voltam como resultado da ferramenta e o modelo corrige.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from src.agente_perfil.dossie import FUNCIONAIS, POR_IDADE, TODOS


class Evidenciado(BaseModel):
    texto: str = Field(min_length=3)
    evidencias: list[str] = Field(default_factory=list,
                                  description="IDs: marco (ex. M36_FAL_1), ctx:COD, extra:ID, kb:N")


class Dominio(BaseModel):
    codigo: str
    status: Literal["verde", "amarelo", "vermelho", "cinza", "contextual"]
    justificativa_status: str = Field(min_length=3, description="Por que esta cor, em linguagem simples")
    o_que_observamos: str = Field(min_length=10)
    pontos_fortes: list[Evidenciado] = Field(default_factory=list)
    pontos_de_atencao: list[Evidenciado] = Field(default_factory=list)


class Foco(BaseModel):
    dominio: str
    por_que: str = Field(min_length=10)


class EscalaGAS(BaseModel):
    """Goal Attainment Scaling: -2 (situação atual) ... +2 (muito além do esperado)."""
    menos_2: str
    menos_1: str
    zero: str = Field(description="Resultado esperado no prazo")
    mais_1: str
    mais_2: str


class Meta(BaseModel):
    id: str
    horizonte: Literal["curto", "medio", "longo"]
    dominio: str
    texto: str = Field(min_length=10, description="Meta observável, no positivo")
    prazo_semanas: int = Field(ge=1, le=104)
    como_acompanhar: str = Field(min_length=5, description="Indicador observável que o responsável registra")
    quem_participa: list[str] = Field(min_length=1)
    gas: EscalaGAS
    evidencias: list[str] = Field(default_factory=list)


class Dica(BaseModel):
    dominio: str
    titulo: str
    por_que_ajuda: str
    como_fazer: list[str] = Field(min_length=1, max_length=6)
    momento_do_dia: str = Field(description="Em que rotina encaixar (banho, refeição, caminho da escola...)")
    usa_interesse_da_crianca: bool = False
    fontes: list[str] = Field(default_factory=list, description="IDs kb:N das buscas na base")


class Alerta(BaseModel):
    tipo: str
    texto: str
    recomendacao: str


class Relatorio(BaseModel):
    resumo: str = Field(min_length=80, description="3 a 6 frases, acolhedoras, para o responsável")
    caracteristicas: list[str] = Field(min_length=1, description="Como a criança é: jeito, interesses, preferências")
    pontos_fortes_gerais: list[Evidenciado] = Field(min_length=1)
    dominios: list[Dominio]
    foco_prioritario: list[Foco] = Field(min_length=1, max_length=3)
    metas: list[Meta]
    dicas: list[Dica] = Field(min_length=2, max_length=8)
    alertas: list[Alerta] = Field(default_factory=list)
    proximos_passos: list[str] = Field(min_length=1)
    limitacoes: str = Field(min_length=20, description="O que este mapeamento não é e o que faltou saber")


# Afirmações que soam como diagnóstico. Condições relatadas pela família podem ser
# mencionadas como relato ("a família contou que..."), por isso o filtro é por frase.
PADROES_PROIBIDOS = [
    r"\b(é|seja) autista\b", r"\btem (autismo|tea|tdah)\b", r"\bapresenta (autismo|tea|tdah)\b",
    r"\bé hiperativ[oa]\b", r"\bidade mental\b", r"\bidade de desenvolvimento\b", r"\bretardo\b",
    r"\bQI\b", r"\b(sugere|indica|sinais de|compatível com) (autismo|tea|tdah|transtorno|deficiência)",
    r"\bdiagnostic(o|amos|ar) (de|com)\b", r"\bdiagnóstico (de|é)\b",
]


def _textos(rel: Relatorio):
    """Tudo o que o responsável vai ler, exceto `limitacoes` (pode dizer 'não é diagnóstico')."""
    yield rel.resumo
    yield from rel.caracteristicas
    for e in rel.pontos_fortes_gerais:
        yield e.texto
    for d in rel.dominios:
        yield from [d.justificativa_status, d.o_que_observamos]
        yield from (e.texto for e in d.pontos_fortes + d.pontos_de_atencao)
    for f in rel.foco_prioritario:
        yield f.por_que
    for m in rel.metas:
        yield m.texto
    for d in rel.dicas:
        yield from [d.titulo, d.por_que_ajuda, *d.como_fazer]
    for a in rel.alertas:
        yield from [a.texto, a.recomendacao]


def validar(dados: dict, dossie: dict, evidencias_extras: set[str], kb_ids: set[str]) -> tuple[Relatorio | None, list[str]]:
    """Valida o relatório. Devolve (relatório, erros). Com erros, o modelo tenta de novo."""
    try:
        rel = Relatorio.model_validate(dados)
    except ValidationError as e:
        return None, [f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()[:15]]

    erros: list[str] = []
    calculado = {d["codigo"]: d["status_calculado"] for d in dossie["dominios"]}
    validas = set(dossie["_evidencias_validas"]) | evidencias_extras | kb_ids

    codigos = [d.codigo for d in rel.dominios]
    faltando = set(TODOS) - set(codigos)
    if faltando or len(codigos) != len(TODOS):
        erros.append(f"`dominios` deve ter exatamente os 14 códigos, um cada. Faltando: {sorted(faltando)}; "
                     f"recebidos: {codigos}")
    for d in rel.dominios:
        if d.codigo not in calculado:
            erros.append(f"Domínio desconhecido: {d.codigo}")
            continue
        if d.codigo in POR_IDADE and d.status != calculado[d.codigo]:
            erros.append(f"{d.codigo}: status deve ser '{calculado[d.codigo]}' (calculado pelas regras), não '{d.status}'.")
        if d.codigo in FUNCIONAIS and d.status == "contextual":
            erros.append(f"{d.codigo}: domínio funcional precisa de verde/amarelo/vermelho/cinza.")
        if d.codigo in ("SAU", "CTX") and d.status != "contextual":
            erros.append(f"{d.codigo}: status deve ser 'contextual'.")
        for e in d.pontos_fortes + d.pontos_de_atencao:
            for ev in e.evidencias:
                if ev not in validas:
                    erros.append(f"{d.codigo}: evidência inexistente '{ev}'.")

    for f in rel.foco_prioritario:
        if f.dominio not in calculado:
            erros.append(f"foco_prioritario: domínio desconhecido {f.dominio}")

    horizontes = [m.horizonte for m in rel.metas]
    for h, (mn, mx) in {"curto": (1, 3), "medio": (1, 3), "longo": (1, 2)}.items():
        if not mn <= horizontes.count(h) <= mx:
            erros.append(f"metas: são necessárias de {mn} a {mx} metas de horizonte '{h}' (há {horizontes.count(h)}).")
    if len({m.id for m in rel.metas}) != len(rel.metas):
        erros.append("metas: ids repetidos.")
    for m in rel.metas:
        if m.dominio not in calculado:
            erros.append(f"meta {m.id}: domínio desconhecido {m.dominio}")
        if m.horizonte == "curto" and m.prazo_semanas > 6:
            erros.append(f"meta {m.id}: curto prazo deve ter até 6 semanas.")
        if m.horizonte == "longo" and m.prazo_semanas < 16:
            erros.append(f"meta {m.id}: longo prazo deve ter pelo menos 16 semanas.")
    for d in rel.dicas:
        if d.dominio not in calculado:
            erros.append(f"dica '{d.titulo}': domínio desconhecido {d.dominio}")
        for f in d.fontes:
            if f not in kb_ids:
                erros.append(f"dica '{d.titulo}': fonte '{f}' não veio de uma busca na base.")

    for texto in _textos(rel):
        for padrao in PADROES_PROIBIDOS:
            if re.search(padrao, texto, flags=re.IGNORECASE):
                erros.append(f"Linguagem diagnóstica proibida ('{padrao}') em: \"{texto[:120]}\"")

    return (rel if not erros else None), erros
