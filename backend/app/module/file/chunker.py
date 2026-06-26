import tiktoken
from app.config import CHUNK_SIZE, CHUNK_OVERLAP


def _num_tokens(text: str, model: str = "text-embedding-3-large") -> int:
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def chunk_document(
    text: str,
    metadata: dict | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict]:
    chunk_size = chunk_size or CHUNK_SIZE
    chunk_overlap = chunk_overlap or CHUNK_OVERLAP
    metadata = metadata or {}

    separators = ["\n\n", "\n", ". ", " ", ""]
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
            best_sep = None
            for sep in separators:
                pos = text.rfind(sep, start, end)
                if pos != -1:
                    best_sep = pos + len(sep)
                    break
            if best_sep:
                end = best_sep

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({
                "content": chunk_text,
                "token_count": _num_tokens(chunk_text),
                "chunk_index": len(chunks),
                **metadata,
            })

        start = end - chunk_overlap if end < text_len else text_len

    return chunks
