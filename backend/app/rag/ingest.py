"""Build the guideline index from the PDFs in data/guidelines.

Run:  python -m app.rag.ingest [--reset]
"""

from __future__ import annotations

import argparse
import logging
import sys
import warnings

from pypdf import PdfReader

from app.core.config import settings
from app.rag.sources import SOURCES
from app.rag.store import COLLECTION, chunk_page, get_client, get_collection

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("ingest")

# pypdf is noisy about embedded font quirks in government PDFs.
warnings.filterwarnings("ignore")
logging.getLogger("pypdf").setLevel(logging.ERROR)


def ingest(reset: bool = False) -> int:
    if reset:
        try:
            get_client().delete_collection(COLLECTION)
            log.info("Cleared existing index")
        except Exception:
            pass

    collection = get_collection()
    total = 0
    missing: list[str] = []

    for source in SOURCES:
        path = settings.guidelines_path / source.filename
        if not path.exists():
            missing.append(source.filename)
            continue

        reader = PdfReader(str(path))
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []
        skipped_pages = 0

        for page_number, page in enumerate(reader.pages, start=1):
            try:
                raw = page.extract_text() or ""
            except Exception:
                raw = ""
            if len(raw.strip()) < 120:
                # Almost certainly a scanned image or a cover page. Without OCR
                # there is nothing here worth indexing.
                skipped_pages += 1
                continue

            for index, chunk in enumerate(chunk_page(raw)):
                ids.append(f"{source.filename}:{page_number}:{index}")
                documents.append(chunk)
                metadatas.append(
                    {
                        "filename": source.filename,
                        "title": source.title,
                        "publisher": source.publisher,
                        "year": source.year,
                        "url": source.url,
                        "page": page_number,
                        "topics": "|".join(source.topics),
                    }
                )

        if not documents:
            log.warning("  %-46s no extractable text", source.filename)
            continue

        # Chroma embeds locally; batch to keep memory flat on a laptop.
        for start in range(0, len(documents), 200):
            end = start + 200
            collection.upsert(
                ids=ids[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
            )

        total += len(documents)
        log.info(
            "  %-46s %4d chunks from %3d pages (%d image-only pages skipped)",
            source.filename,
            len(documents),
            len(reader.pages) - skipped_pages,
            skipped_pages,
        )

    if missing:
        log.warning("Missing PDFs (run scripts/fetch_guidelines.py): %s", ", ".join(missing))

    log.info("Indexed %d chunks total; collection now holds %d", total, collection.count())
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="rebuild from scratch")
    args = parser.parse_args()
    log.info("Ingesting NHM guideline corpus...")
    if ingest(reset=args.reset) == 0:
        sys.exit(1)
