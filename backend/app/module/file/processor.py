import hashlib
import os

from sqlalchemy.orm import Session

from app import models
from app.tools import UPLOAD_DIR
from app.module.file.parser.factory import parse_file
from app.module.file.chunker import chunk_document
from app.module.file.search import index_file_chunks


def process_upload(
    db: Session,
    file_bytes: bytes,
    filename: str,
    original_name: str,
    chat_id: int,
) -> dict:
    text = parse_file(file_bytes, original_name)

    content_hash = hashlib.sha256(text.encode()).hexdigest()

    existing = db.query(models.PdfDocument).filter(
        models.PdfDocument.chat_id == chat_id,
        models.PdfDocument.text_content.isnot(None),
    ).all()
    for doc in existing:
        if doc.text_hash == content_hash:
            return {"filename": doc.filename, "original_name": doc.original_name, "text_length": len(text), "deduped": True}

    filepath = os.path.join(UPLOAD_DIR, filename)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(file_bytes)

    doc = models.PdfDocument(
        chat_id=chat_id,
        filename=filename,
        original_name=original_name,
        text_content=text,
        text_hash=content_hash,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    if text.strip():
        chunks = chunk_document(text, metadata={
            "session_id": str(chat_id),
            "file_id": str(doc.id),
        })
        for c in chunks:
            chunk_row = models.FileChunk(
                chat_id=chat_id,
                file_id=doc.id,
                chunk_index=c["chunk_index"],
                content=c["content"],
                token_count=c.get("token_count"),
            )
            db.add(chunk_row)
        db.commit()

        try:
            index_file_chunks(session_id=str(chat_id), file_id=str(doc.id), chunks=chunks)
        except Exception:
            pass

    return {"filename": filename, "original_name": original_name, "text_length": len(text), "deduped": False}
