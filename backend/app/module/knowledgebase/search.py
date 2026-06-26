from opensearchpy import OpenSearch

from app.config import (
    OPENSEARCH_HOST, OPENSEARCH_PORT, OPENSEARCH_USE_SSL,
    OPENSEARCH_USER, OPENSEARCH_PASSWORD, SEARCH_LANGUAGE_FIELDS,
)
from app.module.knowledgebase.embedding import _get_dimension

_os_client: OpenSearch | None = None


def get_os_client() -> OpenSearch | None:
    global _os_client
    if _os_client is not None:
        return _os_client

    kwargs = {"hosts": [{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}], "timeout": 30}
    if OPENSEARCH_USE_SSL:
        kwargs["use_ssl"] = True
        kwargs["verify_certs"] = False
    if OPENSEARCH_USER and OPENSEARCH_PASSWORD:
        kwargs["http_auth"] = (OPENSEARCH_USER, OPENSEARCH_PASSWORD)

    try:
        _os_client = OpenSearch(**kwargs)
        _os_client.info()
        return _os_client
    except Exception:
        _os_client = None
        return None


def _kb_index_name(kb_id: int) -> str:
    return f"knowledgebase_{kb_id}"


def _build_kb_mappings():
    lang_fields = {lang: {"type": "text", "analyzer": lang}
                   for lang in SEARCH_LANGUAGE_FIELDS.split(",") if lang.strip()}
    properties = {
        "content": {"type": "text", "fields": lang_fields},
        "embedding": {
            "type": "knn_vector",
            "dimension": _get_dimension(),
            "method": {"name": "hnsw", "space_type": "cosinesimil", "engine": "lucene"},
        },
        "record_id": {"type": "keyword"},
        "file_id": {"type": "keyword"},
        "chunk_index": {"type": "integer"},
        "token_count": {"type": "integer"},
        "is_public": {"type": "boolean"},
        "allowed_user_ids": {"type": "keyword"},
        "allowed_group_ids": {"type": "keyword"},
    }
    return {"properties": properties}


def ensure_kb_index(kb_id: int):
    os_client = get_os_client()
    if os_client is None:
        return False
    index_name = _kb_index_name(kb_id)
    if not os_client.indices.exists(index=index_name):
        body = {
            "settings": {
                "index": {"knn": True},
                "number_of_shards": 1,
                "number_of_replicas": 0,
            },
            "mappings": _build_kb_mappings(),
        }
        os_client.indices.create(index=index_name, body=body)
    return True


def index_kb_records(kb_id: int, records: list[dict]):
    os_client = get_os_client()
    if os_client is None:
        return
    ensure_kb_index(kb_id)
    index_name = _kb_index_name(kb_id)
    for rec in records:
        doc = {
            "content": rec["content_text"] if "content_text" in rec else rec["content"],
            "embedding": rec["embedding"],
            "record_id": str(rec.get("record_id", "")),
            "file_id": str(rec.get("file_id", "")),
            "chunk_index": rec.get("chunk_index", 0),
            "token_count": rec.get("token_count", 0),
            "is_public": rec.get("is_public", False),
            "allowed_user_ids": rec.get("allowed_user_ids", []),
            "allowed_group_ids": rec.get("allowed_group_ids", []),
        }
        os_client.index(index=index_name, body=doc)


def _build_acl_filter(user_id: int | None = None, group_ids: list[str] | None = None):
    if user_id is None and not group_ids:
        return {"match_all": {}}
    should = [{"term": {"is_public": True}}]
    if user_id is not None:
        should.append({"term": {"allowed_user_ids": str(user_id)}})
    if group_ids:
        for g in group_ids:
            should.append({"term": {"allowed_group_ids": g}})
    return {"bool": {"should": should, "minimum_should_match": 1}}


def search_kb_lexical(
    kb_id: int,
    query: str,
    user_id: int | None = None,
    group_ids: list[str] | None = None,
    k: int = 10,
):
    os_client = get_os_client()
    if os_client is None:
        return []

    lang_fields = [f"content.{lang}" for lang in SEARCH_LANGUAGE_FIELDS.split(",") if lang.strip()]
    query_body = {
        "multi_match": {
            "query": query,
            "fields": ["content"] + lang_fields,
            "type": "best_fields",
        }
    }
    acl = _build_acl_filter(user_id, group_ids)
    full_query = {"bool": {"must": [query_body], "filter": [acl]}}
    resp = os_client.search(index=_kb_index_name(kb_id), body={"size": k, "query": full_query})
    return [{"id": h["_id"], "score": h["_score"], **h["_source"]} for h in resp["hits"]["hits"]]


def search_kb_vector(
    kb_id: int,
    embedding: list[float],
    user_id: int | None = None,
    group_ids: list[str] | None = None,
    k: int = 10,
):
    os_client = get_os_client()
    if os_client is None:
        return []

    acl = _build_acl_filter(user_id, group_ids)
    query = {
        "knn": {
            "embedding": {
                "vector": embedding,
                "k": k,
                "filter": acl,
            }
        }
    }
    resp = os_client.search(index=_kb_index_name(kb_id), body={"size": k, "query": query})
    return [{"id": h["_id"], "score": h["_score"], **h["_source"]} for h in resp["hits"]["hits"]]


def delete_kb_index(kb_id: int):
    os_client = get_os_client()
    if os_client is None:
        return
    index_name = _kb_index_name(kb_id)
    if os_client.indices.exists(index=index_name):
        os_client.indices.delete(index=index_name)
