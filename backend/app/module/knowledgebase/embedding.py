from app.config import (
    OPENAI_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIM,
    OLLAMA_BASE_URL, OLLAMA_EMBEDDING_MODEL, LLM_MODEL,
)

_dimension: int | None = None
_ollama_cache: dict[str, "OllamaEmbeddings"] = {}


def _get_ollama_embeddings(model: str):
    if model not in _ollama_cache:
        from langchain_ollama import OllamaEmbeddings
        _ollama_cache[model] = OllamaEmbeddings(base_url=OLLAMA_BASE_URL, model=model)
    return _ollama_cache[model]


def _try_embed(texts: list[str], model: str) -> list[list[float]] | None:
    try:
        ol = _get_ollama_embeddings(model)
        return [ol.embed_query(t) if t.strip() else [0.0] * _get_dimension() for t in texts]
    except Exception:
        return None


def _get_dimension() -> int:
    global _dimension
    if _dimension is not None:
        return _dimension
    if OPENAI_API_KEY:
        _dimension = EMBEDDING_DIM
        return _dimension
    for model in [OLLAMA_EMBEDDING_MODEL, LLM_MODEL]:
        try:
            ol = _get_ollama_embeddings(model)
            test = ol.embed_query("test")
            _dimension = len(test)
            return _dimension
        except Exception:
            continue
    _dimension = EMBEDDING_DIM
    return _dimension


def embed_texts(texts: list[str], model: str | None = None) -> list[list[float]]:
    if OPENAI_API_KEY:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        model = model or EMBEDDING_MODEL
        batch = []
        for i in range(0, len(texts), 20):
            resp = client.embeddings.create(model=model, input=texts[i:i + 20])
            batch.extend([d.embedding for d in resp.data])
        return batch

    dim = _get_dimension()
    for m in ([model, OLLAMA_EMBEDDING_MODEL, LLM_MODEL] if model else [OLLAMA_EMBEDDING_MODEL, LLM_MODEL]):
        result = _try_embed(texts, m)
        if result is not None:
            return result
    return [[0.0] * dim for _ in texts]


def embed_query(text: str, model: str | None = None) -> list[float]:
    if OPENAI_API_KEY:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        model = model or EMBEDDING_MODEL
        resp = client.embeddings.create(model=model, input=[text])
        return resp.data[0].embedding

    for m in ([model, OLLAMA_EMBEDDING_MODEL, LLM_MODEL] if model else [OLLAMA_EMBEDDING_MODEL, LLM_MODEL]):
        try:
            ol = _get_ollama_embeddings(m)
            return ol.embed_query(text)
        except Exception:
            continue
    return []
