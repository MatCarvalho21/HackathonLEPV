import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = json.loads((ROOT / 'prompts/matheus/07/ouput.json').read_text(encoding='utf-8-sig'))
NAMES = dict(zip(
    ['COM_R','COM_E','FAL','SOC','BRI','COG','MOT_A','MOT_F','AUT','REG','ATE','SEN','SAU','CTX'],
    ['Compreensão','Comunicação expressiva','Fala e verbalização','Interação social','Brincadeira','Cognição e aprendizagem','Motor amplo','Motor fino','Autonomia e autocuidado','Regulação e comportamento','Atenção e funções executivas','Processamento sensorial','Saúde e corpo','Contexto e participação']))
CONTEXT = {
    'REG': 'O que costuma causar desconforto ou frustração? O que ajuda a criança a se acalmar?',
    'ATE': 'Como a criança participa de uma atividade de que gosta? Que apoios ajudam a manter sua participação?',
    'SEN': 'Como reage a sons, luzes, cheiros, texturas e movimento? Há situações que evita ou procura?',
    'SAU': 'Como estão sono e alimentação? Há informações de saúde, visão, audição ou acompanhamentos que deseja compartilhar?',
    'CTX': 'Como é a rotina em casa e na escola? Quem oferece apoio e quais barreiras dificultam a participação?'
}
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(_app):
    from backend.avaliacoes import aquecer_rag
    aquecer_rag()  # carrega a base vetorial em segundo plano
    yield

app = FastAPI(title='Primeiros Passos — formulário inicial', version='0.1.0', lifespan=lifespan)

from backend.avaliacoes import router as avaliacoes_router  # noqa: E402
app.include_router(avaliacoes_router)
from backend.plataforma import router as plataforma_router  # noqa: E402
app.include_router(plataforma_router)

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Profile(Strict):
    apelido: str = Field(min_length=1, max_length=60)
    idade_meses: int = Field(ge=0, le=131)
    ano_escolar: int | None = Field(default=None, ge=1, le=5)
    vinculo: str = Field(min_length=1, max_length=60)
    interesses: str = Field(default='', max_length=2000)
    prioridades: str = Field(min_length=1, max_length=2000)
    idiomas: str = Field(default='', max_length=200)
    prematuridade: Literal['sim','nao','nao_sei'] = 'nao_sei'
    perda_habilidades: Literal['sim','nao','nao_sei']
    condicoes_relatadas: list[Literal['tea','tdah','down','deficiencia_intelectual','atraso_global','linguagem_aprendizagem','motora','genetica_outra','em_investigacao','prefiro_nao_informar']] = Field(default_factory=list, max_length=10)
    outra_condicao: str = Field(default='', max_length=500)
    documento_comprobatorio: Literal['sim','nao','nao_sei'] = 'nao_sei'
    tipo_documento: str = Field(default='', max_length=100)
    observacoes_saude: str = Field(default='', max_length=2000)

class Observation(Strict):
    resposta: Literal['sim','as_vezes','nao','nao_sei','nao_aplicavel']
    exemplo: str = Field(default='', max_length=2000)

class DomainContext(Strict):
    relato: str = Field(default='', max_length=4000)
    pontos_fortes: str = Field(default='', max_length=2000)
    desafios: str = Field(default='', max_length=2000)
    apoios: str = Field(default='', max_length=2000)
    observacoes: str = Field(default='', max_length=2000)
    nao_sei: bool = False
    contexto: Literal['casa','escola','ambos','outro','nao_sei'] = 'nao_sei'

class Submission(Strict):
    versao: str
    informante: Literal['responsavel','professor'] = 'responsavel'
    perfil: Profile
    respostas: dict[str, Observation]
    dominios: dict[str, DomainContext]
    consentimento: Literal[True]
    crianca_id: str | None = None   # criança cadastrada na plataforma (sem ela, uma é criada a partir do perfil)
    autor_id: str | None = None     # id do responsável ou professor que preencheu

def questionnaire(age: int, school: int | None):
    domains = []
    for code, name in NAMES.items():
        candidates = [m for m in REFERENCE['marcos'] if m['dominio'] == code and m['faixa_meses'] <= age]
        if age >= 72 and code in REFERENCE['regua_6_10']['dominios_por_ano_escolar']:
            # Curriculum refers to end of previous school year, not chronological age.
            cap = 60 if school == 1 else (school + 4) * 12 if school else None
            candidates = [m for m in candidates if cap is not None and m['faixa_meses'] <= cap]
        band = max((m['faixa_meses'] for m in candidates), default=None)
        selected = [m for m in candidates if m['faixa_meses'] == band]
        domains.append({'id': code, 'nome': name, 'faixa_referencia_meses': band,
                        'perguntas': selected, 'pergunta_contexto': CONTEXT.get(code, 'Conte um exemplo do cotidiano: o que a criança gosta de fazer, consegue fazer e em que precisa de apoio?'),
                        'natureza': 'contextual' if code in ['SAU','CTX'] else 'relato_observacional'})
    return {'versao': REFERENCE['versao'], 'idade_meses': age, 'dominios': domains,
            'opcoes': {**REFERENCE['respostas'], 'nao_aplicavel':'Não se aplica / não teve oportunidade'}}

@app.get('/api/health')
def health():
    return {'status':'ok'}

@app.get('/api/questionario')
def get_questionnaire(idade_meses: int = Query(ge=0,le=131), ano_escolar: int | None = Query(default=None,ge=1,le=5)):
    return questionnaire(idade_meses, ano_escolar)

@app.post('/api/formularios', status_code=201)
def submit(data: Submission):
    if data.versao != REFERENCE['versao']:
        raise HTTPException(409, 'O questionário foi atualizado. Reabra as perguntas.')
    schema = questionnaire(data.perfil.idade_meses, data.perfil.ano_escolar)
    expected = {q['id'] for d in schema['dominios'] for q in d['perguntas']}
    if set(data.respostas) != expected or set(data.dominios) != set(NAMES):
        raise HTTPException(422, 'Responda os itens correspondentes à idade e aos 14 domínios.')
    for code, ctx in data.dominios.items():
        if not any(value.strip() for value in [ctx.relato, ctx.pontos_fortes, ctx.desafios, ctx.apoios, ctx.observacoes]) and not ctx.nao_sei:
            raise HTTPException(422, f'Inclua um relato ou marque não sei em {NAMES[code]}.')
    if not data.perfil.apelido.strip() or not data.perfil.prioridades.strip() or not data.perfil.vinculo.strip():
        raise HTTPException(422, 'Preencha apelido, vínculo e prioridades.')
    payload = {'id':str(uuid4()), 'criado_em':datetime.now(timezone.utc).isoformat(),
               'status':'aguardando_agente', 'versao':data.versao, 'informante':data.informante,
               'perfil':data.perfil.model_dump(), 'consentimento':True, 'dominios':[],
               'orientacoes_agente': ['Os dados são relatos do responsável, não avaliação clínica validada.',
                   'Condições, laudos e documentos são informações relatadas pela família; não confirmar diagnóstico nem inferir habilidades, prognóstico ou necessidade de apoio a partir de rótulos.',
                   'Não aceitar nem armazenar arquivo médico neste protótipo; usar apenas dados sintéticos e o resumo mínimo necessário.',
                   'Não atribuir diagnóstico, idade de desenvolvimento, escore ou cores automáticas.',
                   'Não sei e não aplicável significam informação insuficiente, não dificuldade.',
                   'Preservar contexto, fontes, pontos fortes e incertezas; SAU e CTX são contextuais.',
                   'Metas e plano devem ser rascunhos revisáveis, com responsável, prazo e indicador observável.',
                   'Prematuridade foi relatada; idade corrigida não foi calculada. Pedir revisão profissional quando pertinente.',
                   'Validar referências antes de conclusões; perda de habilidades relatada exige orientação para avaliação profissional.']}
    for d in schema['dominios']:
        payload['dominios'].append({**d, 'contexto_responsavel':data.dominios[d['id']].model_dump(),
            'perguntas':[{**q, **data.respostas[q['id']].model_dump()} for q in d['perguntas']],
            'classificacao':None})
    from src.agente_perfil import repositorio
    if data.crianca_id and not repositorio.obter_crianca(data.crianca_id):
        raise HTTPException(404, 'Criança não encontrada.')
    repositorio.salvar_formulario(payload, data.crianca_id, data.autor_id)  # banco local: tabela formulario
    return payload
