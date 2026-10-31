import re
from pathlib import Path
from typing import List, Dict, Any
from pypdf import PdfReader


def clean_text(text: str) -> str:
    """Limpa e normaliza o texto extraído de páginas de PDF."""
    if not text:
        return ""
    # Remove caracteres nulos e caracteres de controle
    text = text.replace("\x00", " ")
    # Substitui quebras de linha com traço (hifenização de fim de linha)
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
    # Normaliza múltiplos espaços em branco e quebras consecutivas
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def extract_pages_from_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extrai o texto de cada página de um arquivo PDF junto com seus metadados.
    
    Retorna uma lista de dicionários no formato:
    [
        {
            "text": "conteúdo da página...",
            "source": "nome_do_arquivo.pdf",
            "page": 1,
            "total_pages": 42,
            "path": "/caminho/completo/nome_do_arquivo.pdf"
        },
        ...
    ]
    """
    pages_data = []
    try:
        reader = PdfReader(str(pdf_path))
        total_pages = len(reader.pages)

        for page_num, page in enumerate(reader.pages, start=1):
            try:
                raw_text = page.extract_text() or ""
                cleaned = clean_text(raw_text)
                
                # Só inclui páginas que possuem texto legível extraído
                if cleaned:
                    pages_data.append({
                        "text": cleaned,
                        "source": pdf_path.name,
                        "page": page_num,
                        "total_pages": total_pages,
                        "path": str(pdf_path.resolve())
                    })
            except Exception as e:
                print(f"[Aviso] Falha ao extrair página {page_num} de '{pdf_path.name}': {e}")
                continue

    except Exception as e:
        print(f"[Erro] Falha ao carregar o PDF '{pdf_path.name}': {e}")

    return pages_data
