from app.module.knowledgebase.search import search_kb_lexical, search_kb_vector
from app.module.knowledgebase.embedding import embed_query
from app.models import KnowledgebaseAuditEntry
from app.database import SessionLocal


RRF_K = 60


def rrf_merge(lexical_results: list[dict], vector_results: list[dict], k: int = RRF_K) -> list[dict]:
    scores: dict[str, dict] = {}

    for rank, doc in enumerate(lexical_results):
        doc_id = doc["id"]
        if doc_id not in scores:
            scores[doc_id] = {**doc, "rrf_score": 0}
        scores[doc_id]["rrf_score"] += 1 / (k + rank + 1)

    for rank, doc in enumerate(vector_results):
        doc_id = doc["id"]
        if doc_id not in scores:
            scores[doc_id] = {**doc, "rrf_score": 0}
        scores[doc_id]["rrf_score"] += 1 / (k + rank + 1)

    return sorted(scores.values(), key=lambda x: -x["rrf_score"])


def search_knowledgebase(
    kb_id: int,
    query: str,
    retrieval_mode: str = "hybrid",
    user_id: int | None = None,
    group_ids: list[str] | None = None,
    k: int = 10,
) -> list[dict]:
    results = []

    if retrieval_mode in ("fulltext", "hybrid"):
        lexical = search_kb_lexical(kb_id, query, user_id, group_ids, k)
        results = lexical

    if retrieval_mode in ("vector", "hybrid"):
        vec = embed_query(query)
        if vec:
            vector_results = search_kb_vector(kb_id, vec, user_id, group_ids, k)
            if retrieval_mode == "vector":
                results = vector_results
            elif retrieval_mode == "hybrid":
                results = rrf_merge(results, vector_results)

    results = results[:k]

    db = SessionLocal()
    try:
        db.add(KnowledgebaseAuditEntry(
            knowledgebase_id=kb_id,
            user_id=user_id,
            action="search",
            query_text=query,
            retrieval_mode=retrieval_mode,
            result_count=len(results),
        ))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

    return results


def get_adjacent_chunks(kb_id: int, record_id: str, chunk_index: int, window: int = 1, k: int = 5) -> list[dict]:
    from app.module.knowledgebase.search import get_os_client
    os_client = get_os_client()
    if os_client is None:
        return []
    index_name = f"knowledgebase_{kb_id}"
    resp = os_client.search(
        index=index_name,
        body={
            "size": k,
            "query": {
                "bool": {
                    "must": [
                        {"term": {"file_id": record_id}},
                        {"range": {"chunk_index": {"gte": chunk_index - window, "lte": chunk_index + window}}},
                    ]
                }
            },
            "sort": [{"chunk_index": {"order": "asc"}}],
        },
    )
    return [{"id": h["_id"], **h["_source"]} for h in resp["hits"]["hits"]]
