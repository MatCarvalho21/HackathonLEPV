import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.rag.config import CHUNK_SIZE, CHUNK_OVERLAP, PRESERVE_TABLES_WHOLE


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    metadata: Dict[str, Any]


def sanitize_id(text: str) -> str:
    """Gera um slug limpo para identificadores únicos no ChromaDB."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\-_.]", "_", text)
    return text.lower()


def is_markdown_table_row(line: str) -> bool:
    """Verifica se uma linha pertence a uma tabela Markdown."""
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and len(s) > 2


def extract_page_marker(text: str) -> Optional[int]:
    """Extrai marcações de página injetadas durante o parsing (ex: <!-- page: 12 -->)."""
    match = re.search(r"<!--\s*page:\s*(\d+)\s*-->", text)
    if match:
        return int(match.group(1))
    return None


def split_table_respectfully(
    table_lines: List[str],
    max_chunk_size: int = CHUNK_SIZE
) -> List[str]:
    """
    Divide tabelas muito grandes sem quebrar linhas individuais,
    repetindo o cabeçalho da tabela em cada fatia para manter o contexto das colunas.
    """
    if not table_lines:
        return []

    # Se a tabela cabe inteira, retorna como bloco único
    full_table = "\n".join(table_lines)
    if len(full_table) <= max_chunk_size or PRESERVE_TABLES_WHOLE:
        return [full_table]

    # Identifica cabeçalho (primeiras 2 linhas típicas de Markdown | th | e | --- |)
    header_rows = table_lines[:2] if len(table_lines) >= 2 and "---" in table_lines[1] else []
    data_rows = table_lines[len(header_rows):]

    chunks = []
    current_rows = list(header_rows)
    current_len = sum(len(r) + 1 for r in current_rows)

    for row in data_rows:
        row_len = len(row) + 1
        if current_len + row_len > max_chunk_size and len(current_rows) > len(header_rows):
            chunks.append("\n".join(current_rows))
            current_rows = list(header_rows)
            current_len = sum(len(r) + 1 for r in current_rows)

        current_rows.append(row)
        current_len += row_len

    if len(current_rows) > len(header_rows):
        chunks.append("\n".join(current_rows))

    return chunks


def split_text_into_chunks(
    text: str,
    max_chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
) -> List[str]:
    """
    Divide um bloco de texto por parágrafos e frases de forma limpa,
    respeitando os limites de caracteres e sobreposição.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chunk_size:
        return [text]

    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_len = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_len = len(para) + 2

        if current_len + para_len > max_chunk_size and current_chunk:
            combined = "\n\n".join(current_chunk).strip()
            if combined:
                chunks.append(combined)

            # Sobreposição pegando os últimos parágrafos que cabem no overlap
            overlap_parts = []
            overlap_len = 0
            for prev in reversed(current_chunk):
                if overlap_len + len(prev) + 2 <= chunk_overlap:
                    overlap_parts.insert(0, prev)
                    overlap_len += len(prev) + 2
                else:
                    break

            current_chunk = overlap_parts
            current_len = overlap_len

        # Se um único parágrafo for gigante, quebra por frases
        if len(para) > max_chunk_size:
            sentences = re.split(r"(?<=[.!?]) +", para)
            for sentence in sentences:
                sent_len = len(sentence) + 1
                if current_len + sent_len > max_chunk_size and current_chunk:
                    combined = "\n\n".join(current_chunk).strip()
                    if combined:
                        chunks.append(combined)
                    current_chunk = []
                    current_len = 0
                current_chunk.append(sentence)
                current_len += sent_len
        else:
            current_chunk.append(para)
            current_len += para_len

    if current_chunk:
        combined = "\n\n".join(current_chunk).strip()
        if combined:
            chunks.append(combined)

    return chunks


def parse_and_chunk_markdown(
    markdown_content: str,
    source_filename: str,
    default_page: int = 1,
    max_chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
) -> List[DocumentChunk]:
    """
    Lê o Markdown estruturado, reconhece cabeçalhos (#, ##, ###), tabelas e
    seções, gerando blocos semanticamente ricos com hierarquia nos metadados.
    """
    lines = markdown_content.splitlines()
    doc_slug = sanitize_id(Path(source_filename).stem)

    chunks: List[DocumentChunk] = []
    header_stack: List[str] = []  # Pilha para rastrear "Capítulo > Seção > Subseção"
    current_section_lines: List[str] = []
    current_page = default_page
    in_table = False
    current_table_lines: List[str] = []

    def flush_section(lines_to_flush: List[str], is_table: bool = False):
        nonlocal chunks, current_page
        if not lines_to_flush:
            return

        section_breadcrumb = " > ".join(header_stack) if header_stack else "Conteúdo Geral"

        if is_table:
            table_chunks = split_table_respectfully(lines_to_flush, max_chunk_size=max_chunk_size)
            for t_idx, t_text in enumerate(table_chunks):
                chunk_id = f"{doc_slug}_p{current_page}_tbl{len(chunks)}_{t_idx}"
                # Injeta cabeçalho de contexto na tabela para facilitar retrieval
                enriched_text = f"### [Tabela] {section_breadcrumb}\n\n{t_text}"
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        text=enriched_text,
                        metadata={
                            "source": source_filename,
                            "section": section_breadcrumb,
                            "page": int(current_page),
                            "is_table": True,
                            "chunk_index": len(chunks),
                            "char_count": len(enriched_text),
                        }
                    )
                )
        else:
            block_text = "\n".join(lines_to_flush).strip()
            if not block_text:
                return

            sub_splits = split_text_into_chunks(
                text=block_text,
                max_chunk_size=max_chunk_size,
                chunk_overlap=chunk_overlap
            )
            for s_idx, split_text in enumerate(sub_splits):
                chunk_id = f"{doc_slug}_p{current_page}_sec{len(chunks)}_{s_idx}"
                # Injeta a hierarquia da seção no topo do bloco de texto
                header_prefix = f"### {section_breadcrumb}\n\n" if header_stack else ""
                enriched_text = f"{header_prefix}{split_text}"

                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        text=enriched_text,
                        metadata={
                            "source": source_filename,
                            "section": section_breadcrumb,
                            "page": int(current_page),
                            "is_table": False,
                            "chunk_index": len(chunks),
                            "char_count": len(enriched_text),
                        }
                    )
                )

    for line in lines:
        # Verifica se há marcador de página
        page_detected = extract_page_marker(line)
        if page_detected:
            current_page = page_detected

        # Linha de tabela Markdown
        if is_markdown_table_row(line):
            if not in_table:
                # Transição: texto normal -> tabela
                flush_section(current_section_lines, is_table=False)
                current_section_lines = []
                in_table = True
            current_table_lines.append(line)
            continue
        elif in_table:
            # Transição: tabela acabou -> texto normal
            flush_section(current_table_lines, is_table=True)
            current_table_lines = []
            in_table = False

        # Verifica se é cabeçalho Markdown (# H1, ## H2, etc.)
        header_match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if header_match:
            # Salva o conteúdo da seção anterior antes de mudar o tópico
            flush_section(current_section_lines, is_table=False)
            current_section_lines = []

            level = len(header_match.group(1))
            title = header_match.group(2).strip()

            # Ajusta a pilha para o nível correspondente
            if len(header_stack) >= level:
                header_stack = header_stack[: level - 1]
            header_stack.append(title)
            continue

        current_section_lines.append(line)

    # Processa restos ao final do arquivo
    if in_table and current_table_lines:
        flush_section(current_table_lines, is_table=True)
    elif current_section_lines:
        flush_section(current_section_lines, is_table=False)

    return chunks
