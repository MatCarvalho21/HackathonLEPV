import os
import tempfile
os.environ.setdefault('SENHA_ITERACOES', '1000')
from backend.banco_teste import BancoTeste  # SQLite por padrão; Supabase com TESTE_PG=1
import unittest
from fastapi.testclient import TestClient
from backend.main import app, questionnaire, REFERENCE

class FormTests(unittest.TestCase):
    banco=BancoTeste()
    @classmethod
    def setUpClass(cls): cls.banco.preparar()
    @classmethod
    def tearDownClass(cls): cls.banco.encerrar()
    def setUp(self):
        self.banco.limpar()
        self.client=TestClient(app)
        j=self.client.post('/api/auth/cadastro',json={'tipo':'responsavel','nome':'Rui','email':'rui@x.com','senha':'segredo1'}).json()
        self.h={'Authorization':f"Bearer {j['token']}"}
        cid=self.client.post('/api/criancas',headers=self.h,json={'nome':'Exemplo','data_nascimento':'2019-10-01'}).json()['crianca']['id']
        schema=questionnaire(84,2)
        self.body={'versao':schema['versao'],'perfil':{'apelido':'Exemplo','idade_meses':84,'ano_escolar':2,'vinculo':'Responsável','prioridades':'Participar das brincadeiras','perda_habilidades':'nao'},'respostas':{q['id']:{'resposta':'nao_sei'} for d in schema['dominios'] for q in d['perguntas']},'dominios':{d['id']:{'nao_sei':True} for d in schema['dominios']},'consentimento':True,'crianca_id':cid}
    def tearDown(self):
        self.banco.depois()
    def test_all_ages_have_14_domains_and_no_future_milestones(self):
        for age in range(132):
            s=questionnaire(age,None)
            self.assertEqual(len(s['dominios']),14)
            self.assertTrue(all(q['faixa_meses']<=age for d in s['dominios'] for q in d['perguntas']))
    def test_school_previous_year(self):
        d=next(d for d in questionnaire(108,3)['dominios'] if d['id']=='COG')
        self.assertEqual(d['faixa_referencia_meses'],84)
    def test_submission_and_evidence(self):
        self.assertEqual(self.client.post('/api/formularios',json=self.body).status_code,401)
        r=self.client.post('/api/formularios',headers=self.h,json=self.body)
        self.assertEqual(r.status_code,201,r.text)
        self.assertEqual(r.json()['status'],'aguardando_agente')
        self.assertEqual(len(r.json()['dominios']),14)
        self.assertTrue(all(d['classificacao'] is None for d in r.json()['dominios']))
        # aos 84 meses algumas fontes vêm em lista (era o Erro 500 ao gerar o mapeamento)
        from src.agente_perfil import repositorio
        from src.agente_perfil.dossie import montar_dossie
        self.assertEqual(len(montar_dossie(repositorio.obter_formulario(r.json()['id']))['dominios']),14)
    def test_invalid_submission(self):
        for key,value in [('consentimento',False),('versao','old'),('respostas',{}),('dominios',{})]:
            r=self.client.post('/api/formularios',headers=self.h,json={**self.body,key:value})
            self.assertIn(r.status_code,[409,422])
    def test_invalid_ages(self):
        for age in [-1,132,'abc']:
            self.assertEqual(self.client.get('/api/questionario',params={'idade_meses':age}).status_code,422)

if __name__=='__main__':unittest.main()
