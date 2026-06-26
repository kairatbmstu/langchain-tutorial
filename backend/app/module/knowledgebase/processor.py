import hashlib
import os
import uuid

from sqlalchemy.orm import Session

from app import models
from app.tools import UPLOAD_DIR
from app.module.file.parser.factory import parse_file
from app.module.file.chunker import chunk_document
from app.module.knowledgebase.embedding import embed_texts
from app.module.knowledgebase.search import index_kb_records


def import_file_to_knowledgebase(
    db: Session,
    kb_id: int,
    file_bytes: bytes,
    original_name: str,
    user_id: int,
) -> dict:
    text = parse_file(file_bytes, original_name)
    if not text.strip():
        return {"status": "error", "error": "No text could be extracted"}

    content_hash = hashlib.sha256(text.encode()).hexdigest()

    existing = db.query(models.KnowledgebaseFile).filter(
        models.KnowledgebaseFile.knowledgebase_id == kb_id,
        models.KnowledgebaseFile.content_hash == content_hash,
    ).first()
    if existing:
        return {"status": "skipped", "reason": "duplicate", "file_id": existing.id}

    kb = db.query(models.Knowledgebase).filter(models.Knowledgebase.id == kb_id).first()
    if not kb:
        return {"status": "error", "error": "Knowledgebase not found"}

    ext = os.path.splitext(original_name)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, stored_name)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(file_bytes)

    kb_file = models.KnowledgebaseFile(
        knowledgebase_id=kb_id,
        filename=stored_name,
        original_name=original_name,
        content_type=ext.lstrip("."),
        file_size=len(file_bytes),
        storage_path=filepath,
        content_hash=content_hash,
        status="processing",
    )
    db.add(kb_file)
    db.commit()
    db.refresh(kb_file)

    try:
        chunks = chunk_document(text)
        texts = [c["content"] for c in chunks]
        embeddings = embed_texts(texts, model=kb.embedding_model) if kb.index_method == "semantic" else [[] for _ in chunks]

        records = []
        for i, chunk in enumerate(chunks):
            record = models.KnowledgebaseRecord(
                knowledgebase_id=kb_id,
                file_id=kb_file.id,
                record_type="chunk",
                content_text=chunk["content"],
                chunk_index=chunk["chunk_index"],
                token_count=chunk.get("token_count"),
                is_public=kb.is_public,
                allowed_user_ids=kb.allowed_user_ids,
                allowed_group_ids=kb.allowed_group_ids,
            )
            db.add(record)
            db.flush()
            db.refresh(record)
            records.append({
                "record_id": record.id,
                "content_text": chunk["content"],
                "embedding": embeddings[i] if embeddings and len(embeddings) > i else [],
                "chunk_index": chunk["chunk_index"],
                "token_count": chunk.get("token_count", 0),
                "is_public": kb.is_public,
                "allowed_user_ids": kb.allowed_user_ids,
                "allowed_group_ids": kb.allowed_group_ids,
                "file_id": kb_file.id,
            })

        try:
            index_kb_records(kb_id, records)
        except Exception as e:
            print(f"[WARN] OpenSearch indexing failed for KB {kb_id}: {e}")

        kb_file.status = "completed"
        db.commit()

        return {"status": "completed", "file_id": kb_file.id, "chunks": len(chunks)}

    except Exception as e:
        kb_file.status = "failed"
        kb_file.error_message = str(e)
        db.commit()
        return {"status": "error", "error": str(e)}
