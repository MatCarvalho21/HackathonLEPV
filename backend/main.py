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
app = FastAPI(title='Primeiros Passos — formulário inicial', version='0.1.0')

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

class Observation(Strict):
    resposta: Literal['sim','as_vezes','nao','nao_sei','nao_aplicavel']
    exemplo: str = Field(default='', max_length=2000)

class DomainContext(Strict):
    relato: str = Field(default='', max_length=4000)
    nao_sei: bool = False
    contexto: Literal['casa','escola','ambos','outro','nao_sei'] = 'nao_sei'

class Submission(Strict):
    versao: str
    perfil: Profile
    respostas: dict[str, Observation]
    dominios: dict[str, DomainContext]
    consentimento: Literal[True]

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
        if not ctx.relato.strip() and not ctx.nao_sei:
            raise HTTPException(422, f'Inclua um relato ou marque não sei em {NAMES[code]}.')
    if not data.perfil.apelido.strip() or not data.perfil.prioridades.strip() or not data.perfil.vinculo.strip():
        raise HTTPException(422, 'Preencha apelido, vínculo e prioridades.')
    payload = {'id':str(uuid4()), 'criado_em':datetime.now(timezone.utc).isoformat(),
               'status':'aguardando_agente', 'versao':data.versao, 'informante':'responsavel',
               'perfil':data.perfil.model_dump(), 'consentimento':True, 'dominios':[],
               'orientacoes_agente': ['Os dados são relatos do responsável, não avaliação clínica validada.',
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
    dbpath = Path(os.getenv('FORM_DB', str(ROOT/'backend/data/forms.sqlite3')))
    dbpath.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(dbpath) as db:
        db.execute('CREATE TABLE IF NOT EXISTS submissions (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        db.execute('INSERT INTO submissions VALUES (?,?)', (payload['id'], json.dumps(payload, ensure_ascii=False)))
    return payload
