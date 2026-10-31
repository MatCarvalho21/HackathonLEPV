# Organização da Base de PDFs e Extração para Markdown Selecionável

Analisei minuciosamente os 29 arquivos na pasta [`pdfs/`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/pdfs) e criei as ferramentas automatizadas na pasta [`src/tools/`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/tools). 

Como solicitado, **nenhum arquivo foi modificado ou apagado**, e **nenhum script foi executado**. Todo o código está preparado e pronto para rodar quando você desejar.

---

## 1. Mapeamento Completo e Diagnóstico dos PDFs

Abaixo está o mapeamento exato de cada PDF com seu conteúdo real identificado e o novo nome semântico proposto:

### 🔹 Triagem Pediátrica SWYC (Survey of Well-being of Young Children - Tufts Medical Center)
| Nome Atual | Conteúdo Real Identificado | Novo Nome Padronizado |
| :--- | :--- | :--- |
| `1.pdf` | BPSC: Instruções de Pontuação (Baby Pediatric Symptom Checklist) | `swyc_bpsc_instrucoes_pontuacao.pdf` |
| `2.pdf` | BPSC: Questionário para bebês de 1 a 18 meses | `swyc_bpsc_questionario_1a18m.pdf` |
| `3.pdf` | PPSC: Questionário pré-escolar de 18 a 65 meses | `swyc_ppsc_questionario_18a65m.pdf` |
| `4.pdf` | PPSC: Instruções de Pontuação pré-escolar | `swyc_ppsc_instrucoes_pontuacao.pdf` |
| `5.pdf` | POSI: Questionário de Interação Social precoce (18 a 34 meses) | `swyc_posi_questionario_18a34m.pdf` |
| `6.pdf` | POSI: Instruções de Pontuação de Interação Social | `swyc_posi_instrucoes_pontuacao.pdf` |
| `7.pdf` | Questionário Familiar SWYC (fatores ambientais e psicossociais) | `swyc_questionario_familiar_1a65m.pdf` |
| `8.pdf` | Referências científicas e validações do questionário familiar | `swyc_referencias_perguntas_familiares.pdf` |
| **`9.pdf`** | **DUPLICADO:** Arquivo com hash SHA-256 e conteúdo 100% idêntico ao `5.pdf` | ❌ **Será apagado** |
| **`10.pdf`**| **DUPLICADO:** Arquivo com hash SHA-256 e conteúdo 100% idêntico ao `6.pdf` | ❌ **Será apagado** |

---

### 🔹 OMS / Organização Mundial da Saúde (Caregiver Skills Training - CST)
| Nome Atual | Conteúdo Real Identificado | Novo Nome Padronizado |
| :--- | :--- | :--- |
| `9789240048911-eng.pdf` | OMS CST: Manual de Treinamento de Habilidades para Cuidadores | `oms_cst_manual_cuidadores_treinamento.pdf` |
| `9789240048973-eng.pdf` | OMS CST: Guia de Visitas Domiciliares e Definição de Metas | `oms_cst_guia_visitas_domiciliares.pdf` |

---

### 🔹 Pyramid Model / NCPMI - Backpack Connection (Estratégias Práticas para Pais e Professores)
| Nome Atual | Conteúdo Real Identificado | Novo Nome Padronizado |
| :--- | :--- | :--- |
| `BackpackConnection_behavior_biting_PR.pdf` | Guia: Como Ajudar seu Filho a Parar de Morder | `ncpmi_comportamento_parar_de_morder.pdf` |
| `BackpackConnection_behavior_hitting_PR.pdf` | Guia: Como Ajudar seu Filho a Parar de Bater e Empurrar | `ncpmi_comportamento_bater_e_empurrar.pdf` |
| `BackpackConnection_behavior_meltdown_PR.pdf`| Guia: Como Ajudar seu Filho a Evitar Crises (Tantrums/Meltdowns) | `ncpmi_comportamento_evitar_crises.pdf` |
| `BackpackConnection_emotions_label_PR.pdf` | Guia: Como Ajudar seu Filho a Nomear as Emoções | `ncpmi_emocoes_nomear_sentimentos.pdf` |
| `BackpackConnection_emotions_language_PR.pdf`| Guia: Como Usar a Linguagem Positiva com Crianças | `ncpmi_comportamento_linguagem_positiva.pdf` |

---

### 🔹 Legislação Brasileira (Educação Especial Inclusiva, PEI, PAEE e Apoio sem Laudo)
| Nome Atual | Conteúdo Real Identificado | Novo Nome Padronizado |
| :--- | :--- | :--- |
| `D12686.pdf` | Decreto Federal nº 12.686/2025: Política Nacional de Ed. Especial | `legislacao_decreto_12686_2025_politica_educacao_especial.pdf` |
| `D12773.pdf` | Decreto Federal nº 12.773/2025: Alterações e obrigatoriedade do PEI e PAEE | `legislacao_decreto_12773_2025_alteracao_politica_educacao_especial.pdf` |
| `PORTARIA MEC No 421, DE 15 DE MAIO DE 2026.pdf` | Portaria MEC nº 421/2026: Diretrizes pedagógicas para estudo de caso e PEI | `legislacao_portaria_mec_421_2026_diretrizes_pei.pdf` |

---

### 🔹 EEF - Education Endowment Foundation (Evidências Científicas Pedagógicas)
| Nome Atual | Conteúdo Real Identificado | Novo Nome Padronizado |
| :--- | :--- | :--- |
| `EEF_Special_Educational_Needs_in_Mainstream_Schools_Guidance_Report.pdf` | Relatório: Necessidades Educacionais Especiais na Escola Comum | `eef_relatorio_necessidades_especiais_escola_comum.pdf` |
| `EEF_Maths_EY_KS1_Guidance_Report.pdf` | Relatório: Matemática na Primeira Infância (3 a 7 anos) | `eef_relatorio_matematica_inicial_3a7anos.pdf` |
| `Literacy_KS1_Guidance_Report_2020.pdf` | Relatório: Alfabetização nos Anos Iniciais (5 a 7 anos) | `eef_relatorio_alfabetizacao_ks1_5a7anos.pdf` |
| `EEF-Improving-literacy-in-key-stage-2-report-Second-edition.pdf` | Relatório: Alfabetização nos Anos Finais do Fundamental I (7 a 11 anos) | `eef_relatorio_alfabetizacao_ks2_7a11anos.pdf` |

---

### 🔹 Ministério da Saúde e Desenvolvimento Infantil
| Nome Atual | Conteúdo Real Identificado | Novo Nome Padronizado |
| :--- | :--- | :--- |
| `caderneta_crianca_menina_passaporte_cidadania_7edrev.pdf` | Caderneta da Criança (Menina - 7ª edição revisada) | `ministerio_saude_caderneta_crianca_menina_7ed.pdf` |
| `caderneta_crianca_menino_6ed.pdf` | Caderneta da Criança (Menino - 6ª edição) | `ministerio_saude_caderneta_crianca_menino_6ed.pdf` |
| `milestonesPT.pdf` | Marcos do Desenvolvimento Infantil - CDC (Versão em Português) | `cdc_marcos_desenvolvimento_portugues.pdf` |
| `milestones.pdf` | Marcos do Desenvolvimento Infantil - CDC (Versão em Inglês) | `cdc_marcos_desenvolvimento_ingles.pdf` |
| `Enhancing-and-Practicing-Executive-Function-Skills-with-Children-from-Infancy-to-Adolescence-1.pdf` | Harvard: Guia Prático de Funções Executivas da Infância à Adolescência | `harvard_guia_funcoes_executivas_infancia_adolescencia.pdf` |

---

## 2. Scripts Criados

Foram criados 3 scripts modulares e independentes:

1. [`src/tools/organize_pdfs.py`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/tools/organize_pdfs.py):
   - Calcula o hash SHA-256 de todos os arquivos para detectar duplicatas exatas.
   - Deleta os arquivos repetidos (`9.pdf` e `10.pdf`).
   - Renomeia todos os arquivos para os nomes padronizados e semânticos.
   - Possui modo de segurança `--dry-run` por padrão (simula sem alterar nada).

2. [`src/tools/extract_to_markdown.py`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/tools/extract_to_markdown.py):
   - Extrai o texto digital selecionável de todas as páginas de cada PDF usando `pypdf`.
   - Limpa quebras de linhas desnecessárias e hifenizações.
   - Salva cada documento como um arquivo `.md` independente na pasta `docs_markdown/`.
   - Adiciona índice de páginas (`## Página 1`, `## Página 2`...), contagem de caracteres e metadados no topo de cada arquivo.
   - Cria um catálogo geral em `docs_markdown/INDEX.md` com links para cada documento.

3. [`src/tools/verify_text_selectability.py`](file:///home/matheus-carvalho/Documentos/HackathonLEPV/src/tools/verify_text_selectability.py):
   - Analisa cada PDF para verificar se ele já tem camada de texto selecionável ou se alguma página é puramente imagem escaneada.

---

## 3. Como Rodar os Scripts

Ative o seu ambiente virtual Python na raiz do projeto:

```bash
source venv/bin/activate
```

### Passo 1: Organizar e Renomear os PDFs

Para fazer uma simulação prévia sem alterar nenhum arquivo:
```bash
python3 -m src.tools.organize_pdfs
```

Para aplicar as alterações reais (renomear e apagar os duplicados):
```bash
python3 -m src.tools.organize_pdfs --apply
```

---

### Passo 2: Extrair os PDFs para Markdown Selecionável

Para converter todos os PDFs da base para arquivos Markdown estruturados:
```bash
python3 -m src.tools.extract_to_markdown
```

Os arquivos serão gerados na pasta:
```
docs_markdown/
├── INDEX.md (catálogo geral com resumo e links)
├── cdc_marcos_desenvolvimento_portugues.md
├── ministerio_saude_caderneta_crianca_menino_6ed.md
├── oms_cst_manual_cuidadores_treinamento.md
└── ...
```

---

### Passo 3: Verificar a Selecionabilidade do Texto

Para rodar uma checagem rápida de quais páginas contêm texto digital direto:
```bash
python3 -m src.tools.verify_text_selectability
```

> **Dica sobre OCR:** Se houver algum documento futuro que seja 100% escaneado (imagem pura sem camada de texto), você pode deixá-lo selecionável com o comando Linux:
> ```bash
> sudo apt-get install tesseract-ocr tesseract-ocr-por ocrmypdf
> ocrmypdf --skip-text input.pdf output_searchable.pdf
> ```
