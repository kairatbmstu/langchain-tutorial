import hashlib

from app.config import (
    OPENSEARCH_HOST, OPENSEARCH_PORT, OPENSEARCH_USE_SSL,
    OPENSEARCH_USER, OPENSEARCH_PASSWORD, SEARCH_LANGUAGE_FIELDS,
)
from app.module.knowledgebase.search import get_os_client

FILE_INDEX = "fileindex"


def _build_index_body():
    lang_fields = [f"content.{lang}" for lang in SEARCH_LANGUAGE_FIELDS.split(",") if lang.strip()]
    properties = {
        "content": {"type": "text", "fields": {}},
        "session_id": {"type": "keyword"},
        "file_id": {"type": "keyword"},
        "chunk_index": {"type": "integer"},
        "token_count": {"type": "integer"},
        "created_at": {"type": "date"},
    }
    for lang in SEARCH_LANGUAGE_FIELDS.split(","):
        lang = lang.strip()
        if lang:
            properties["content"]["fields"][lang] = {"type": "text", "analyzer": lang}
    return {"settings": {"number_of_shards": 1, "number_of_replicas": 0}, "mappings": {"properties": properties}}


def ensure_file_index():
    os_client = get_os_client()
    if os_client is None:
        return False
    if not os_client.indices.exists(index=FILE_INDEX):
        os_client.indices.create(index=FILE_INDEX, body=_build_index_body())
    return True


def index_file_chunks(session_id: str, file_id: str, chunks: list[dict]):
    os_client = get_os_client()
    if os_client is None:
        return
    ensure_file_index()
    for chunk in chunks:
        doc = {
            "content": chunk["content"],
            "session_id": session_id,
            "file_id": file_id,
            "chunk_index": chunk["chunk_index"],
            "token_count": chunk.get("token_count", 0),
            "content_hash": hashlib.md5(chunk["content"].encode()).hexdigest(),
        }
        os_client.index(index=FILE_INDEX, body=doc)


def search_file_chunks(
    query: str,
    session_id: str | None = None,
    k: int = 5,
) -> list[dict]:
    os_client = get_os_client()
    if os_client is None:
        return []

    must = [{"multi_match": {"query": query, "fields": ["content", "content.english", "content.arabic"], "type": "best_fields"}}]
    if session_id:
        must.append({"term": {"session_id": session_id}})

    resp = os_client.search(index=FILE_INDEX, body={"size": k, "query": {"bool": {"must": must}}})
    return [{"id": h["_id"], "score": h["_score"], **h["_source"]} for h in resp["hits"]["hits"]]


def delete_file_chunks(session_id: str, file_id: str | None = None):
    os_client = get_os_client()
    if os_client is None:
        return
    must = [{"term": {"session_id": session_id}}]
    if file_id:
        must.append({"term": {"file_id": file_id}})
    os_client.delete_by_query(index=FILE_INDEX, body={"query": {"bool": {"must": must}}})
