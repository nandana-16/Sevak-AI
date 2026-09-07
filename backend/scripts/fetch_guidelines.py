"""Download the NHM guideline PDFs the RAG corpus is built from.

The PDFs are public Government of India documents but are not committed to the
repository - they are ~28 MB and they belong to their publisher, not to us.

Run:  python -m scripts.fetch_guidelines
Then: python -m app.rag.ingest --reset
"""

from __future__ import annotations

import sys

import httpx

from app.core.config import settings
from app.rag.sources import SOURCES

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SevakAI/1.0; academic project)"}


def main() -> int:
    target = settings.guidelines_path
    target.mkdir(parents=True, exist_ok=True)
    failures = 0

    for source in SOURCES:
        path = target / source.filename
        if path.exists() and path.stat().st_size > 10_000:
            print(f"  have  {source.filename}")
            continue

        print(f"  get   {source.filename} ...", end=" ", flush=True)
        try:
            # Some state NHM servers present incomplete certificate chains;
            # these are public read-only documents, and the ingest step
            # validates that what arrived is actually a PDF.
            response = httpx.get(
                source.url, headers=HEADERS, timeout=120,
                follow_redirects=True, verify=False,
            )
            if response.status_code == 200 and response.content[:4] == b"%PDF":
                path.write_bytes(response.content)
                print(f"ok ({len(response.content) // 1024} KB)")
            else:
                print(f"FAILED (HTTP {response.status_code}, not a PDF)")
                failures += 1
        except Exception as exc:
            print(f"FAILED ({type(exc).__name__})")
            failures += 1

    if failures:
        print(
            f"\n{failures} document(s) could not be downloaded. Government URLs "
            "move; check app/rag/sources.py and update the links."
        )
    else:
        print("\nAll guideline documents present. Next: python -m app.rag.ingest --reset")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
