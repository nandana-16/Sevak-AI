"""ChromaDB-backed retrieval over the NHM guideline corpus.

Chunks are page-anchored: a citation shown to a worker names the document and
the page it came from, so a supervisor can open the real PDF and check it.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.rag.sources import BY_FILENAME

log = logging.getLogger("sevakai.rag")

COLLECTION = "nhm_guidelines"


@dataclass
class Citation:
    text: str
    title: str
    page: int
    url: str
    score: float

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "title": self.title,
            "page": self.page,
            "url": self.url,
            "score": round(self.score, 4),
        }


_client: chromadb.ClientAPI | None = None


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(settings.chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
        )
    return _client


def get_collection():
    return get_client().get_or_create_collection(
        name=COLLECTION, metadata={"hnsw:space": "cosine"}
    )


def count() -> int:
    try:
        return get_collection().count()
    except Exception:
        return 0


def _clean(text: str) -> str:
    # These PDFs use Wingdings/Symbol bullets, which extract as Unicode
    # private-use characters. They are noise to an embedding model and blow up
    # on a Windows console, so drop the whole PUA block along with the usual
    # bullet and replacement glyphs.
    text = re.sub("[-•￼�]", " ", text)
    # Rejoin words hyphenated across a line break.
    text = re.sub(r"-\n(?=\w)", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_page(text: str, *, size: int = 900, overlap: int = 150) -> list[str]:
    """Sentence-aware chunking with overlap, so a danger-sign list is not cut
    in half between two chunks."""
    text = _clean(text)
    if len(text) <= size:
        return [text] if len(text) > 80 else []

    sentences = re.split(r"(?<=[.!?;:])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= size:
            current = f"{current} {sentence}".strip()
        else:
            if len(current) > 80:
                chunks.append(current)
            tail = current[-overlap:] if overlap and current else ""
            current = f"{tail} {sentence}".strip()
    if len(current) > 80:
        chunks.append(current)
    return chunks


def search(
    query: str,
    *,
    k: int = 5,
    topics: list[str] | None = None,
    min_score: float = 0.0,
) -> list[Citation]:
    """Retrieve guideline passages. `topics` biases toward the relevant
    document set (ANC docs for a pregnancy, IMNCI for a sick child) but does
    not exclude others, because danger signs cut across documents."""
    collection = get_collection()
    if collection.count() == 0:
        return []

    # Chroma metadata values must be scalars, so topics live as a delimited
    # string and cannot be filtered server-side. Instead we over-fetch and
    # re-rank below with a topic boost, which keeps cross-cutting danger-sign
    # passages reachable from any patient category.
    try:
        result = collection.query(
            query_texts=[query],
            n_results=min(k * 3 if topics else k, 40),
        )
    except Exception as exc:
        log.warning("Retrieval failed: %s", exc)
        return []

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    citations: list[Citation] = []
    for text, meta, distance in zip(documents, metadatas, distances):
        score = 1.0 - float(distance)
        if score < min_score:
            continue
        boost = 0.0
        if topics:
            chunk_topics = set((meta.get("topics") or "").split("|"))
            overlap = chunk_topics & set(topics)
            boost = 0.06 * len(overlap)
        citations.append(
            Citation(
                text=text,
                title=str(meta.get("title", "NHM guideline")),
                page=int(meta.get("page", 0)),
                url=str(meta.get("url", "")),
                score=score + boost,
            )
        )

    citations.sort(key=lambda c: c.score, reverse=True)
    return citations[:k]


def source_summary() -> list[dict]:
    """What is actually indexed, for the /api/guidelines endpoint."""
    collection = get_collection()
    if collection.count() == 0:
        return []
    records = collection.get(include=["metadatas"])
    counts: dict[str, int] = {}
    for meta in records.get("metadatas", []):
        counts[str(meta.get("filename", "?"))] = counts.get(str(meta.get("filename", "?")), 0) + 1
    out = []
    for filename, chunks in sorted(counts.items()):
        source = BY_FILENAME.get(filename)
        out.append(
            {
                "filename": filename,
                "title": source.title if source else filename,
                "publisher": source.publisher if source else "",
                "year": source.year if source else "",
                "url": source.url if source else "",
                "chunks": chunks,
            }
        )
    return out
