from langchain_core.tools import tool

from app.module.file.search import search_file_chunks
from app.module.knowledgebase.tool_adapter import search_knowledgebase, get_adjacent_chunks
from app.models import Knowledgebase
from app.database import SessionLocal


@tool
def search_session_files(query: str, chat_id: int) -> str:
    """Search uploaded files in the current chat session using BM25 full-text search. Use this when the user asks about content in their uploaded documents."""
    try:
        results = search_file_chunks(query=query, session_id=str(chat_id), k=5)
        if not results:
            return "No relevant content found in the uploaded files."
        parts = []
        for r in results:
            parts.append(f"[Score: {r['score']:.3f}]\n{r.get('content', '')[:2000]}")
        return "\n\n---\n\n".join(parts)
    except Exception as e:
        return f"Search failed: {e}"


@tool
def search_knowledgebase_tool(query: str, kb_id: int) -> str:
    """Search a knowledge base using hybrid (BM25 + vector) search. Use this when the user asks about content in a specific knowledge base."""
    try:
        db = SessionLocal()
        kb = db.query(Knowledgebase).filter(Knowledgebase.id == kb_id).first()
        mode = kb.retrieval_mode if kb else "hybrid"
        db.close()
        results = search_knowledgebase(kb_id=kb_id, query=query, retrieval_mode=mode, k=5)
        if not results:
            return "No relevant content found in the knowledge base."
        parts = []
        for r in results:
            content = r.get("content", "")
            score = r.get("rrf_score", r.get("score", 0))
            parts.append(f"[Relevance: {score:.3f}]\n{content[:2000]}")
        return "\n\n---\n\n".join(parts)
    except Exception as e:
        return f"Knowledge base search failed: {e}"


@tool
def fetch_adjacent_chunks(kb_id: int, record_id: str, chunk_index: int) -> str:
    """Fetch chunks adjacent to a given chunk for expanded context. Use this when a retrieved chunk seems cut off or incomplete."""
    try:
        results = get_adjacent_chunks(kb_id=kb_id, record_id=record_id, chunk_index=chunk_index, window=1)
        parts = []
        for r in results:
            parts.append(f"[Chunk {r.get('chunk_index', '?')}]\n{r.get('content', '')[:2000]}")
        return "\n\n---\n\n".join(parts) if parts else "No adjacent chunks found."
    except Exception as e:
        return f"Failed to fetch adjacent chunks: {e}"
