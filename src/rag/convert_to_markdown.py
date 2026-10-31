import argparse
import json
import logging
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from tqdm import tqdm

from src.rag.config import PDFS_DIR, MARKDOWN_DIR, DEVICE

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def sanitize_filename(name: str) -> str:
    """Converte o nome do arquivo para um slug limpo e seguro."""
    stem = Path(name).stem
    stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    stem = re.sub(r"[^\w\-_.]", "_", stem).lower()
    return stem


def convert_pdf_with_docling(pdf_path: Path) -> tuple[str, int]:
    """
    Converte um PDF em Markdown estruturado utilizando o IBM Docling
    (com reconhecimento visual de layout, tabelas e ordem de leitura).
    """
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice

    # Configuração de Aceleração por GPU
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True

    if DEVICE.startswith("cuda"):
        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=4,
            device=AcceleratorDevice.CUDA
        )
    else:
        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=4,
            device=AcceleratorDevice.CPU
        )

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    conv_result = converter.convert(str(pdf_path))
    markdown_content = conv_result.document.export_to_markdown()
    total_pages = len(conv_result.document.pages) if hasattr(conv_result.document, "pages") else 1

    return markdown_content, total_pages


def convert_pdf_with_pypdf_fallback(pdf_path: Path) -> tuple[str, int]:
    """
    Fallback leve caso o docling ainda não esteja instalado ou falhe em um arquivo corrompido.
    Extrai texto básico e demarca páginas.
    """
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    md_parts = [f"# {pdf_path.name}\n"]

    for idx, page in enumerate(reader.pages, start=1):
        txt = (page.extract_text() or "").strip()
        if txt:
            md_parts.append(f"\n<!-- page: {idx} -->\n## Página {idx}\n\n{txt}\n")

    return "\n".join(md_parts), total_pages


def process_single_pdf(
    pdf_path: Path,
    output_dir: Path = MARKDOWN_DIR,
    force: bool = False,
    use_fallback: bool = False
) -> Optional[Path]:
    """Processa um PDF individual e salva seu correspondente .md e .meta.json."""
    slug = sanitize_filename(pdf_path.name)
    md_output_path = output_dir / f"{slug}.md"
    meta_output_path = output_dir / f"{slug}.meta.json"

    if md_output_path.exists() and meta_output_path.exists() and not force:
        return md_output_path

    converter_used = "docling"
    md_content = ""
    total_pages = 0

    if not use_fallback:
        try:
            md_content, total_pages = convert_pdf_with_docling(pdf_path)
        except ImportError:
            logger.warning("Docling não encontrado no ambiente. Usando extrator fallback (pypdf).")
            converter_used = "pypdf_fallback"
            md_content, total_pages = convert_pdf_with_pypdf_fallback(pdf_path)
        except Exception as e:
            logger.error(f"Docling falhou em '{pdf_path.name}' ({e}). Usando fallback.")
            converter_used = "pypdf_fallback"
            md_content, total_pages = convert_pdf_with_pypdf_fallback(pdf_path)
    else:
        converter_used = "pypdf_fallback"
        md_content, total_pages = convert_pdf_with_pypdf_fallback(pdf_path)

    # Escreve o Markdown
    md_output_path.write_text(md_content, encoding="utf-8")

    # Salva os Metadados
    metadata = {
        "source": pdf_path.name,
        "slug": slug,
        "pdf_path": str(pdf_path.resolve()),
        "md_path": str(md_output_path.resolve()),
        "total_pages": int(total_pages),
        "converter": converter_used,
        "char_count": len(md_content),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    meta_output_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    return md_output_path


def run_conversion(
    pdf_filter: Optional[str] = None,
    force: bool = False,
    limit: Optional[int] = None,
    use_fallback: bool = False
):
    """Executa a conversão em lote de todos os PDFs para Markdown."""
    if not PDFS_DIR.exists():
        logger.error(f"Pasta de PDFs não encontrada: {PDFS_DIR}")
        return

    all_pdfs = sorted(list(PDFS_DIR.glob("*.pdf")))
    if pdf_filter:
        all_pdfs = [p for p in all_pdfs if pdf_filter.lower() in p.name.lower()]

    if limit and limit > 0:
        all_pdfs = all_pdfs[:limit]

    total_files = len(all_pdfs)
    logger.info("=" * 70)
    logger.info(f"CONVERSÃO DE PDFs PARA MARKDOWN ESTRUTURADO")
    logger.info(f"Dispositivo: {DEVICE.upper()} | Total de arquivos: {total_files}")
    logger.info(f"Diretório de saída: {MARKDOWN_DIR}")
    logger.info("=" * 70)

    start_time = time.time()
    converted_count = 0

    with tqdm(all_pdfs, desc="Convertendo PDFs", unit="doc") as pbar:
        for pdf_file in pbar:
            pbar.set_postfix_str(pdf_file.name[:25])
            try:
                res = process_single_pdf(
                    pdf_path=pdf_file,
                    output_dir=MARKDOWN_DIR,
                    force=force,
                    use_fallback=use_fallback
                )
                if res:
                    converted_count += 1
            except Exception as e:
                logger.error(f"Erro ao processar {pdf_file.name}: {e}")

    elapsed = time.time() - start_time
    logger.info("=" * 70)
    logger.info(f"CONVERSÃO CONCLUÍDA EM {elapsed:.2f}s")
    logger.info(f"Arquivos processados com sucesso: {converted_count}/{total_files}")
    logger.info(f"Markdowns estruturados salvos em: {MARKDOWN_DIR}")
    logger.info("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Conversor de PDFs para Markdown Estruturado (Docling / GPU)")
    parser.add_argument("--filter", type=str, default=None, help="Filtra PDFs por parte do nome")
    parser.add_argument("--force", action="store_true", help="Força reprocessamento de arquivos já convertidos")
    parser.add_argument("--limit", type=int, default=None, help="Limita a quantidade de PDFs a converter")
    parser.add_argument("--fallback", action="store_true", help="Força uso do extrator simples pypdf")
    args = parser.parse_args()

    run_conversion(
        pdf_filter=args.filter,
        force=args.force,
        limit=args.limit,
        use_fallback=args.fallback
    )
