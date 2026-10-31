import os
import tempfile
import unittest
from fastapi.testclient import TestClient
from backend.main import app, questionnaire, REFERENCE

class FormTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir='backend')
        os.environ['FORM_DB']=self.tmp.name+'/test.sqlite3'
        self.client=TestClient(app)
        schema=questionnaire(84,2)
        self.body={'versao':schema['versao'],'perfil':{'apelido':'Exemplo','idade_meses':84,'ano_escolar':2,'vinculo':'Responsável','prioridades':'Participar das brincadeiras','perda_habilidades':'nao'},'respostas':{q['id']:{'resposta':'nao_sei'} for d in schema['dominios'] for q in d['perguntas']},'dominios':{d['id']:{'nao_sei':True} for d in schema['dominios']},'consentimento':True}
    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop('FORM_DB',None)
    def test_all_ages_have_14_domains_and_no_future_milestones(self):
        for age in range(132):
            s=questionnaire(age,None)
            self.assertEqual(len(s['dominios']),14)
            self.assertTrue(all(q['faixa_meses']<=age for d in s['dominios'] for q in d['perguntas']))
    def test_school_previous_year(self):
        d=next(d for d in questionnaire(108,3)['dominios'] if d['id']=='COG')
        self.assertEqual(d['faixa_referencia_meses'],84)
    def test_submission_and_evidence(self):
        r=self.client.post('/api/formularios',json=self.body)
        self.assertEqual(r.status_code,201,r.text)
        self.assertEqual(r.json()['status'],'aguardando_agente')
        self.assertEqual(len(r.json()['dominios']),14)
        self.assertTrue(all(d['classificacao'] is None for d in r.json()['dominios']))
    def test_invalid_submission(self):
        for key,value in [('consentimento',False),('versao','old'),('respostas',{}),('dominios',{})]:
            r=self.client.post('/api/formularios',json={**self.body,key:value})
            self.assertIn(r.status_code,[409,422])
    def test_invalid_ages(self):
        for age in [-1,132,'abc']:
            self.assertEqual(self.client.get('/api/questionario',params={'idade_meses':age}).status_code,422)

if __name__=='__main__':unittest.main()
