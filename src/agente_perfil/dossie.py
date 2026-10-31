"""Pré-análise determinística do formulário (regras em código, não no prompt).

Recebe o pacote salvo por POST /api/formularios e produz um "dossiê" compacto:
- semáforo calculado para os domínios por idade (o modelo NÃO pode alterá-lo);
- contagens, lacunas de informação e alertas;
- o conjunto de IDs de evidência que o relatório pode citar.

As regras de cor seguem prompts/matheus/05 e 07 e ainda precisam de validação
profissional. Como o formulário só pergunta a faixa de referência da idade
(não a faixa anterior), o vermelho aqui usa proporção de "ainda não".
"""
from __future__ import annotations

import json

from src.agente_perfil.config import ROOT

REFERENCIA = json.loads((ROOT / "prompts/matheus/07/ouput.json").read_text(encoding="utf-8-sig"))

POR_IDADE = list(REFERENCIA["dominios_por_idade"])          # COM_R ... AUT
FUNCIONAIS = list(REFERENCIA["dominios_funcionais"])        # REG ATE SEN
CONTEXTUAIS = list(REFERENCIA["dominios_sem_classificacao"])  # SAU CTX
TODOS = POR_IDADE + FUNCIONAIS + CONTEXTUAIS

STATUS_VALIDOS = {"verde", "amarelo", "vermelho", "cinza"}
RESPOSTAS_CONHECIDAS = {"sim", "as_vezes", "nao"}
CAMPOS_RELATO = ["relato", "pontos_fortes", "desafios", "apoios", "observacoes"]

LEGENDA_STATUS = {
    "verde": "Dentro do esperado para a idade",
    "amarelo": "Pede atenção e estímulo",
    "vermelho": "Vale conversar com um profissional",
    "cinza": "Informação insuficiente",
    "contextual": "Informação de contexto (sem cor)",
}


def idade_por_extenso(meses: int) -> str:
    anos, resto = divmod(meses, 12)
    partes = []
    if anos:
        partes.append(f"{anos} ano" + ("s" if anos > 1 else ""))
    if resto or not anos:
        partes.append(f"{resto} " + ("mês" if resto == 1 else "meses"))
    return " e ".join(partes)


def status_por_idade(respostas: list[str]) -> tuple[str, str]:
    """Regra do semáforo para domínios por idade. Devolve (status, regra aplicada)."""
    if not respostas:
        return "cinza", "Não há marcos de referência para esta idade/ano escolar."
    conhecidas = [r for r in respostas if r in RESPOSTAS_CONHECIDAS]
    if len(conhecidas) * 2 < len(respostas):
        return "cinza", "Mais da metade dos marcos com 'não sei' ou 'não se aplica'."
    nao = conhecidas.count("nao")
    as_vezes = conhecidas.count("as_vezes")
    if nao >= 2 and nao * 2 >= len(conhecidas):
        return "vermelho", f"{nao} de {len(conhecidas)} marcos da faixa ainda não alcançados."
    if nao >= 1 or as_vezes >= 2:
        return "amarelo", f"{nao} marco(s) 'ainda não' e {as_vezes} 'às vezes/com ajuda'."
    return "verde", "Marcos da faixa alcançados (no máximo um 'às vezes')."


def _relato(ctx: dict) -> dict:
    return {k: ctx[k].strip() for k in CAMPOS_RELATO if (ctx.get(k) or "").strip()}


def montar_dossie(formulario: dict) -> dict:
    perfil = formulario["perfil"]
    dominios = []
    evidencias: set[str] = set()
    lacunas = []

    for d in formulario["dominios"]:
        cod = d["id"]
        ctx = d.get("contexto_responsavel") or {}
        relato = _relato(ctx)
        itens = [{"id": q["id"], "marco": q["texto"], "resposta": q["resposta"],
                  **({"exemplo": q["exemplo"]} if q.get("exemplo") else {})}
                 for q in d.get("perguntas", [])]
        evidencias.update(i["id"] for i in itens)
        if relato:
            evidencias.add(f"ctx:{cod}")

        tipo = "por_idade" if cod in POR_IDADE else "funcional" if cod in FUNCIONAIS else "contextual"
        entrada = {
            "codigo": cod, "nome": d["nome"], "tipo": tipo,
            "faixa_referencia_meses": d.get("faixa_referencia_meses"),
            "itens": itens,
            "relato_responsavel": relato or None,
            "onde_observado": ctx.get("contexto", "nao_sei"),
            "responsavel_marcou_nao_sei": bool(ctx.get("nao_sei")),
            # `fonte` vem como texto ou como lista de referências, conforme o marco
            "fontes_referencia": sorted({f for q in d.get("perguntas", []) for f in
                                         (q["fonte"] if isinstance(q.get("fonte"), list) else [q.get("fonte")]) if f}),
        }
        if tipo == "por_idade":
            entrada["status_calculado"], entrada["regra_aplicada"] = status_por_idade([i["resposta"] for i in itens])
            if entrada["status_calculado"] == "cinza":
                lacunas.append(cod)
        elif tipo == "funcional":
            entrada["status_calculado"] = None  # o agente propõe, com justificativa
            entrada["regra_aplicada"] = ("Propor cor pelo impacto no dia a dia: frequência, duração e número de "
                                         "contextos (casa/escola). Vermelho só com impacto frequente (ex.: crises 3+ "
                                         "vezes/semana) em mais de um contexto. Sem relato suficiente → cinza.")
            sem_info = not relato and all(i["resposta"] not in RESPOSTAS_CONHECIDAS for i in itens)
            if sem_info:
                lacunas.append(cod)
        else:
            entrada["status_calculado"] = "contextual"
            entrada["regra_aplicada"] = "Domínio de contexto: sem cor, apenas pontos de atenção."
        dominios.append(entrada)

    alertas = []
    if perfil.get("perda_habilidades") == "sim":
        alertas.append({"tipo": "perda_habilidades",
                        "texto": "O responsável relatou perda de habilidade que a criança já tinha. "
                                 "Isso sempre justifica orientar avaliação profissional (pediatra) em breve."})
    if perfil.get("prematuridade") == "sim":
        alertas.append({"tipo": "prematuridade",
                        "texto": "Prematuridade relatada; idade corrigida NÃO foi calculada. Interpretar os marcos "
                                 "com cautela (até ~24 meses) e sugerir confirmação com o pediatra."})
    vermelhos = [d["codigo"] for d in dominios if d.get("status_calculado") == "vermelho"]
    if len(vermelhos) >= 3:
        alertas.append({"tipo": "multiplos_dominios",
                        "texto": f"Vários domínios em vermelho ({', '.join(vermelhos)}): orientar avaliação "
                                 "com pediatra/equipe multiprofissional, sem sugerir diagnóstico."})

    crianca = {
        "apelido": perfil["apelido"],
        "idade_meses": perfil["idade_meses"],
        "idade": idade_por_extenso(perfil["idade_meses"]),
        "ano_escolar": perfil.get("ano_escolar"),
        "quem_respondeu": perfil.get("vinculo"),
        "idiomas": perfil.get("idiomas") or None,
        "interesses": perfil.get("interesses") or None,
        "prioridades_da_familia": perfil.get("prioridades"),
        "prematuridade": perfil.get("prematuridade"),
        "perda_de_habilidades": perfil.get("perda_habilidades"),
        "condicoes_relatadas_pela_familia": perfil.get("condicoes_relatadas") or [],
        "outra_condicao": perfil.get("outra_condicao") or None,
        "documento_comprobatorio": perfil.get("documento_comprobatorio"),
        "observacoes_saude": perfil.get("observacoes_saude") or None,
    }
    return {
        "formulario_id": formulario.get("id"),
        "versao_questionario": formulario.get("versao"),
        "crianca": crianca,
        "alertas_calculados": alertas,
        "dominios_com_informacao_insuficiente": lacunas,
        "dominios": dominios,
        "_evidencias_validas": sorted(evidencias),  # uso interno do validador
    }


def dossie_para_prompt(dossie: dict) -> str:
    """Versão enviada ao modelo (sem campos internos)."""
    publico = {k: v for k, v in dossie.items() if not k.startswith("_")}
    return json.dumps(publico, ensure_ascii=False, indent=1)
