import re
import unicodedata
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    metadata: Dict[str, Any]


def sanitize_id(text: str) -> str:
    """Gera um slug seguro para identificadores únicos no ChromaDB."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\-_.]", "_", text)
    return text.lower()


def split_text_recursive(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
    separators: List[str] = None
) -> List[str]:
    """
    Divide o texto recursivamente procurando os melhores separadores naturais
    (parágrafos, frases e palavras) respeitando o limite de caracteres e sobreposição.
    """
    if separators is None:
        separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", " ", ""]

    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    # Encontra o primeiro separador que está presente no texto
    chosen_separator = ""
    for sep in separators:
        if sep == "":
            chosen_separator = ""
            break
        if sep in text:
            chosen_separator = sep
            break

    # Divide pelo separador escolhido
    if chosen_separator:
        parts = text.split(chosen_separator)
    else:
        parts = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size - chunk_overlap)]
        return [p.strip() for p in parts if p.strip()]

    chunks = []
    current_chunk = []
    current_length = 0

    for part in parts:
        part_len = len(part) + len(chosen_separator)
        if current_length + part_len > chunk_size and current_chunk:
            combined = chosen_separator.join(current_chunk).strip()
            if combined:
                chunks.append(combined)

            # Mantém sobreposição pegando os últimos elementos que cabem no chunk_overlap
            overlap_parts = []
            overlap_len = 0
            for prev_part in reversed(current_chunk):
                if overlap_len + len(prev_part) + len(chosen_separator) <= chunk_overlap:
                    overlap_parts.insert(0, prev_part)
                    overlap_len += len(prev_part) + len(chosen_separator)
                else:
                    break

            current_chunk = overlap_parts
            current_length = overlap_len

        # Se a parte sozinha for maior que o chunk_size, divide recursivamente com os próximos separadores
        if len(part) > chunk_size:
            sub_separators = separators[separators.index(chosen_separator) + 1 :] if chosen_separator in separators else [""]
            sub_chunks = split_text_recursive(part, chunk_size, chunk_overlap, sub_separators)
            chunks.extend(sub_chunks)
        else:
            current_chunk.append(part)
            current_length += part_len

    if current_chunk:
        combined = chosen_separator.join(current_chunk).strip()
        if combined:
            chunks.append(combined)

    return chunks


def chunk_pages(
    pages_data: List[Dict[str, Any]],
    chunk_size: int = 800,
    chunk_overlap: int = 150
) -> List[DocumentChunk]:
    """
    Recebe os dados das páginas extraídas de um documento e converte em blocos (chunks)
    com metadados enriquecidos para o banco vetorial.
    """
    document_chunks = []

    for page_data in pages_data:
        text = page_data["text"]
        source = page_data["source"]
        page_num = page_data["page"]
        doc_slug = sanitize_id(Path(source).stem)

        text_splits = split_text_recursive(
            text=text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        for chunk_idx, split_text in enumerate(text_splits):
            chunk_id = f"{doc_slug}_p{page_num}_c{chunk_idx}"
            
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                text=split_text,
                metadata={
                    "source": source,
                    "page": int(page_num),
                    "total_pages": int(page_data.get("total_pages", 0)),
                    "chunk_index": int(chunk_idx),
                    "char_count": len(split_text)
                }
            )
            document_chunks.append(chunk)

    return document_chunks
