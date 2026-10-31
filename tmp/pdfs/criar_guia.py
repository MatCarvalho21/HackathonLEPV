from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT
import pypdfium2 as pdfium
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/pdf/base_de_conhecimento_infantil.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
c = canvas.Canvas(str(OUT), pagesize=(595.28,841.89))
c.setTitle('Base de conhecimento infantil - fontes e PDFs')
c.setAuthor('HackathonLEPV')
style = ParagraphStyle('body', fontName='Helvetica', fontSize=10.5, leading=15, textColor=HexColor('#26374A'))
y = 0
def text(s, size=10.5, color='#26374A', gap=8):
    global y
    st = ParagraphStyle('p', parent=style, fontSize=size, leading=size*1.4, textColor=HexColor(color))
    p = Paragraph(s,st)
    _,h=p.wrap(491,740)
    p.drawOn(c,52,y-h)
    y-=h+gap
def page(n,title,sub):
    global y
    c.setFillColor(HexColor('#123749'));c.rect(0,785,596,57,fill=1,stroke=0)
    c.setFillColor(HexColor('#FFFFFF'));c.setFont('Helvetica-Bold',11);c.drawString(52,808,'HACKATHONLEPV  /  BIBLIOTECA DE REFERÊNCIAS')
    y=755
    text(title,24,'#123749',12);text(sub,11,'#587080',20)
    c.setFont('Helvetica',8);c.setFillColor(HexColor('#587080'))
    c.drawString(52,31,'Seleção inicial para discussão da equipe | 30/10/2026')
    c.drawRightString(543,31,str(n))
def doc(title,meta,body,url,note):
    text(title,14,'#123749',5)
    text(meta,9,'#587080',7)
    text(body)
    text(f'<link href="{url}" color="#007F85"><u>Abrir PDF original</u></link>',10.5)
    text('<b>Uso no projeto:</b> '+note,10,gap=19)

page(1,'PDFs para começar','Documentos para formar uma base consultável pelo chatbot de apoio a pais e professores.')
text('Recorte do projeto: crianças de até 10 anos. Esta seleção reúne referências de desenvolvimento e educação; não é uma base de prontuários nem um conjunto para diagnóstico automático.',11,gap=17)
doc('1. OMS - Caregiver Skills Training: participantes','2022 | Inglês | Famílias de crianças de 2 a 9 anos',
    'Guia de sessões para cuidadores de crianças com atrasos ou deficiências no desenvolvimento. Aborda estratégias de interação, comunicação e participação no cotidiano.',
    'https://iris.who.int/bitstream/handle/10665/353582/9789240048911-eng.pdf',
    'Extrair orientações e exemplos para revisão profissional. Faz parte de um programa estruturado; uma resposta de chatbot não equivale à aplicação do programa.')
doc('2. OMS - Caregiver Skills Training: facilitadores','2022 | Inglês | Famílias de crianças de 2 a 9 anos',
    'Manual de apoio à condução das sessões 1 a 9, com estratégias, exemplos e exercícios. A OMS informa que seu uso exige treinamento e supervisão.',
    'https://iris.who.int/bitstream/handle/10665/353580/9789240048935-eng.pdf',
    'Ajudar a equipe a compreender o contexto e os limites das estratégias antes de adaptá-las. Não apresentar o manual como um curso já oferecido pelo produto.')
doc('3. Ministério da Saúde - Caderneta da Criança','2024 | Português | Nascimento até 9 anos | Versão menina, 7ª edição',
    'Documento brasileiro para registro e acompanhamento da saúde, do crescimento e do desenvolvimento infantil.',
    'https://bvsms.saude.gov.br/bvs/publicacoes/caderneta_crianca_menina_passaporte_cidadania_7ed.pdf',
    'Referência para campos do perfil e registros da linha do tempo. Usar a caderneta em branco como fonte; os registros individuais pertencem ao histórico de cada criança.')
c.showPage()
page(2,'Aprendizagem e inclusão','Materiais pedagógicos complementares. Conferir o público de cada trecho antes de incorporar.')
doc('4. EEF - Preparing for Literacy','2018 | Inglês | Foco em crianças de 3 a 5 anos',
    'Guia de recomendações sobre comunicação, linguagem e preparação para leitura e escrita na educação infantil.',
    'https://d2tic4wvo1iusb.cloudfront.net/production/eef-guidance-reports/literacy-early-years/Preparing_Literacy_Guidance_2018.pdf',
    'Organizar fichas sobre interação, histórias e habilidades iniciais de linguagem. Preservar a faixa etária e o contexto educacional.')
doc('5. IES/WWC - Intervenções comportamentais em sala','2024 | Inglês | K-5; abrange também estudantes acima de 10 anos',
    'Guia de práticas para professores, com recomendações sobre expectativas claras, lembretes, escolhas e participação nas atividades de sala.',
    'https://ies.ed.gov/ncee/WWC/Docs/PracticeGuide/behavioral-interventions-practice-guide_v3a_508a.pdf',
    'Selecionar apenas o conteúdo aplicável até 10 anos. Orientações para casa ou viagens devem aparecer como adaptações, quando a fonte trata de escola.')
doc('6. Instituto Rodrigo Mendes - Inclusão escolar','2024 | Português | Famílias de crianças e adolescentes com deficiência',
    'Guia de educação inclusiva, relação entre família e escola e participação das famílias na vida escolar.',
    'https://diversa.org.br/guia-familias/pdf',
    'Apoiar a linguagem e a colaboração entre família e escola. Selecionar o recorte infantil; informações sobre direitos precisam de verificação atual antes do uso.')
text('Prioridade sugerida',14,'#123749')
text('Começar pelo guia de participantes da OMS, pela Caderneta da Criança e pelo guia da EEF. Acrescentar as demais referências conforme as perguntas que a demonstração precisa responder.')
c.showPage()
page(3,'Como organizar a base','A biblioteca de documentos deve manter a origem de cada orientação visível.')
text('Uma ficha por trecho selecionado',14,'#123749')
text('Guardar: título, instituição/autores, ano, URL, página, idioma, faixa etária, tema, público (pais/professores), contexto (casa/escola), trecho de apoio, limitações, licença e data de revisão.')
text('Fluxo sugerido',14,'#123749')
text('1. Selecionar e revisar os PDFs.<br/>2. Extrair o texto, preservando páginas e seções.<br/>3. Dividir em trechos e cadastrar os metadados.<br/>4. Buscar trechos compatíveis com idade, necessidade e contexto.<br/>5. Gerar sugestões com fontes e revisão humana.<br/>6. Registrar o retorno no histórico individual da criança.')
text('Onde ampliar a pesquisa',14,'#123749')
bases=[('PubMed/MEDLINE','https://pubmed.ncbi.nlm.nih.gov/'),('APA PsycNet / PsycINFO','https://psycnet.apa.org/'),('ERIC','https://eric.ed.gov/'),('SciELO','https://scielo.org/'),('BVS','https://bvsalud.org/'),('ScienceDirect','https://www.sciencedirect.com/'),('Periódicos CAPES','https://www.periodicos.capes.gov.br/'),('BDTD','https://bdtd.ibict.br/'),('Campbell - Educação','https://www.campbellcollaboration.org/education/'),('ECTA - famílias','https://ectacenter.org/decrp/type-pgfamily.asp'),('IRIS - recursos','https://iris.peabody.vanderbilt.edu/resources/iris-resource-locator/'),('EEF - Evidence Store','https://educationendowmentfoundation.org.uk/early-years/evidence-store'),('DIVERSA','https://diversa.org.br/'),('What Works Clearinghouse','https://ies.ed.gov/ncee/wwc/'),('Europe PMC - API','https://dev.europepmc.org/RestfulWebService'),('CORE - API','https://core.ac.uk/services/api'),('OpenAlex - API','https://help.openalex.org/api/')]
for i in range(0,len(bases),3):
    text(' &nbsp; | &nbsp; '.join(f'<link href="{u}" color="#007F85"><u>{t}</u></link>' for t,u in bases[i:i+3]),9,gap=6)
text('Limites de incorporação',14,'#123749',6)
text('Acesso gratuito não significa autorização irrestrita de reutilização. Os guias da OMS consultados indicam licença CC BY-NC-SA 3.0 IGO; avaliar as condições antes de uso comercial. Verificar separadamente as licenças das demais fontes. Não inferir diagnóstico a partir dos relatos.',9.5)
c.save()
r=PdfReader(str(OUT))
assert len(r.pages)==3
assert sum(len(p.get('/Annots',[])) for p in r.pages)>=23
pdf=pdfium.PdfDocument(str(OUT))
for i,p in enumerate(pdf):
    p.render(scale=1.1).to_pil().save(ROOT/f'tmp/pdfs/guia-{i+1}.png')
print(str(OUT))
print('3 pages; links checked; previews rendered')
