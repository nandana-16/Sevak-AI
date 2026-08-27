"""ChromaDB-backed RAG store over the NHM protocol knowledge base (Agent 2).

Uses Chroma's built-in local embedding function (ONNX MiniLM, downloaded once on
first use) so this runs fully offline/free — no OpenAI/Gemini embedding key needed.
"""
import chromadb

from app.core.config import settings
from app.rag.nhm_protocols import NHM_PROTOCOLS

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection

    _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    _collection = _client.get_or_create_collection(name="nhm_protocols")

    if _collection.count() == 0:
        _collection.add(
            ids=[p["id"] for p in NHM_PROTOCOLS],
            documents=[f"{p['title']}. {p['content']}" for p in NHM_PROTOCOLS],
            metadatas=[{"title": p["title"], "category": p["category"]} for p in NHM_PROTOCOLS],
        )
    return _collection


def query_protocols(query_text: str, n_results: int = 4) -> list[dict]:
    collection = _get_collection()
    results = collection.query(query_texts=[query_text], n_results=n_results)
    out = []
    for i, doc_id in enumerate(results["ids"][0]):
        out.append({
            "id": doc_id,
            "title": results["metadatas"][0][i]["title"],
            "category": results["metadatas"][0][i]["category"],
            "content": results["documents"][0][i],
            "distance": results["distances"][0][i] if results.get("distances") else None,
        })
    return out
