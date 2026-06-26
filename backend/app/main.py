import os
import uuid

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import engine, get_db, Base
from app import models, schemas, crud
from app.agent import build_graph
from app.tools import UPLOAD_DIR
from app.auth import (
    hash_password,
    verify_password,
    create_token,
    decode_token,
    generate_captcha,
    verify_captcha,
    verify_google_token,
)
from app.drive import get_auth_url, exchange_code, make_drive_tools
from app.module.file.processor import process_upload
from app.module.knowledgebase.processor import import_file_to_knowledgebase

os.makedirs(UPLOAD_DIR, exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ChatGPT Clone with Llama 3.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


def require_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    try:
        return decode_token(authorization.split(" ", 1)[1])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")


# ─── Auth endpoints ───────────────────────────────────────────────


@app.get("/api/captcha")
def get_captcha():
    return generate_captcha()


@app.post("/api/register", response_model=schemas.AuthResponse)
def register(body: schemas.RegisterRequest, db: Session = Depends(get_db)):
    if not verify_captcha(body.captcha_id, body.captcha_answer):
        raise HTTPException(400, "Incorrect captcha answer")

    existing = db.query(models.User).filter(models.User.email == body.email).first()
    if existing:
        raise HTTPException(409, "Email already registered")

    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    user = models.User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id, user.email)
    return {"token": token, "user_id": user.id, "email": user.email}


@app.post("/api/login", response_model=schemas.AuthResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")

    token = create_token(user.id, user.email)
    return {"token": token, "user_id": user.id, "email": user.email}


@app.get("/api/me")
def me(current_user: dict = Depends(require_user)):
    return {"user_id": current_user["user_id"], "email": current_user["email"]}


@app.get("/api/drive/auth")
def drive_auth(current_user: dict = Depends(require_user)):
    url, state_id = get_auth_url(current_user["user_id"])
    return {"auth_url": url}


@app.get("/api/drive/callback")
def drive_callback(code: str, state: str, db: Session = Depends(get_db)):
    tokens = exchange_code(code, state)
    user_id = tokens["user_id"]
    existing = db.query(models.DriveToken).filter(
        models.DriveToken.user_id == user_id
    ).first()
    if existing:
        existing.access_token = tokens["access_token"]
        existing.refresh_token = tokens["refresh_token"]
    else:
        db.add(models.DriveToken(
            user_id=user_id,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
        ))
    db.commit()

    from fastapi.responses import RedirectResponse
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    return RedirectResponse(f"{frontend_url}?drive=connected")


@app.get("/api/drive/status")
def drive_status(current_user: dict = Depends(require_user), db: Session = Depends(get_db)):
    token_row = db.query(models.DriveToken).filter(
        models.DriveToken.user_id == current_user["user_id"]
    ).first()
    return {"connected": token_row is not None}


@app.post("/api/auth/google", response_model=schemas.AuthResponse)
def google_auth(body: schemas.GoogleAuthRequest, db: Session = Depends(get_db)):
    info = verify_google_token(body.id_token)
    if info is None:
        raise HTTPException(401, "Invalid Google token")

    email = info.get("email")
    google_id = info.get("sub")
    if not email or not google_id:
        raise HTTPException(400, "Google account missing email")

    user = db.query(models.User).filter(
        (models.User.email == email) | (models.User.google_id == google_id)
    ).first()

    if user:
        if not user.google_id:
            user.google_id = google_id
            db.commit()
    else:
        user = models.User(email=email, google_id=google_id, password_hash=None)
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_token(user.id, user.email)
    return {"token": token, "user_id": user.id, "email": user.email}


# ─── Chat endpoints (protected) ────────────────────────────────────


@app.get("/api/topics", response_model=list[schemas.TopicOut])
def list_topics(current_user: dict = Depends(require_user), db: Session = Depends(get_db)):
    return crud.get_topics(db, current_user["user_id"])


@app.post("/api/topics", response_model=schemas.TopicOut)
def add_topic(body: schemas.TopicCreate, current_user: dict = Depends(require_user), db: Session = Depends(get_db)):
    return crud.create_topic(db, current_user["user_id"], title=body.title)


@app.delete("/api/topics/{topic_id}")
def remove_topic(topic_id: int, current_user: dict = Depends(require_user), db: Session = Depends(get_db)):
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id, models.Topic.user_id == current_user["user_id"]).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    db.delete(topic)
    db.commit()
    return {"ok": True}


@app.get("/api/topics/{topic_id}/chats", response_model=list[schemas.ChatOut])
def list_chats(topic_id: int, current_user: dict = Depends(require_user), db: Session = Depends(get_db)):
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id, models.Topic.user_id == current_user["user_id"]).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    return crud.get_chats(db, topic_id)


@app.post("/api/chats", response_model=schemas.ChatOut)
def add_chat(body: schemas.ChatCreate, current_user: dict = Depends(require_user), db: Session = Depends(get_db)):
    topic = db.query(models.Topic).filter(models.Topic.id == body.topic_id, models.Topic.user_id == current_user["user_id"]).first()
    if not topic:
        raise HTTPException(404, "Topic not found")
    return crud.create_chat(db, topic_id=body.topic_id, title=body.title)


@app.delete("/api/chats/{chat_id}")
def remove_chat(chat_id: int, current_user: dict = Depends(require_user), db: Session = Depends(get_db)):
    chat = db.query(models.Chat).join(models.Topic).filter(
        models.Chat.id == chat_id,
        models.Topic.user_id == current_user["user_id"],
    ).first()
    if not chat:
        raise HTTPException(404, "Chat not found")
    db.delete(chat)
    db.commit()
    return {"ok": True}


@app.get("/api/chats/{chat_id}/messages", response_model=list[schemas.MessageOut])
def list_messages(chat_id: int, current_user: dict = Depends(require_user), db: Session = Depends(get_db)):
    chat = db.query(models.Chat).join(models.Topic).filter(
        models.Chat.id == chat_id,
        models.Topic.user_id == current_user["user_id"],
    ).first()
    if not chat:
        raise HTTPException(404, "Chat not found")
    return crud.get_messages(db, chat_id)


@app.post("/api/upload", response_model=schemas.UploadResponse)
def upload_file(
    file: UploadFile = File(...),
    chat_id: int = Form(None),
    current_user: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename)[1].lower()
    allowed = {".pdf", ".docx", ".pptx", ".html", ".htm", ".csv", ".xls", ".xlsx", ".json", ".txt", ".md", ".png", ".jpg", ".jpeg", ".gif", ".webp"}
    if ext not in allowed:
        raise HTTPException(400, f"File type '{ext}' is not supported. Supported: {', '.join(allowed)}")

    if chat_id:
        chat = db.query(models.Chat).join(models.Topic).filter(
            models.Chat.id == chat_id,
            models.Topic.user_id == current_user["user_id"],
        ).first()
        if not chat:
            raise HTTPException(404, "Chat not found")

    stored_name = f"{uuid.uuid4().hex}{ext}"
    raw = file.file.read()

    if len(raw) > 50 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 50MB)")

    result = process_upload(db, raw, stored_name, file.filename, chat_id) if chat_id else {"filename": stored_name, "original_name": file.filename, "text_length": 0, "deduped": False}

    if not chat_id:
        filepath = os.path.join(UPLOAD_DIR, stored_name)
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(raw)

    return {
        "filename": result["filename"],
        "original_name": result["original_name"],
        "url": f"/uploads/{result['filename']}",
        "text_length": result["text_length"],
        "deduped": result.get("deduped", False),
    }


@app.post("/api/chats/{chat_id}/messages")
def send_message(
    chat_id: int,
    body: schemas.SendMessage,
    kb_id: int = Query(None, description="Knowledgebase ID for RAG"),
    current_user: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    chat = db.query(models.Chat).join(models.Topic).filter(
        models.Chat.id == chat_id,
        models.Topic.user_id == current_user["user_id"],
    ).first()
    if not chat:
        raise HTTPException(404, "Chat not found")

    user_msg = crud.save_message(db, chat_id, "user", body.content)
    history = crud.get_messages(db, chat_id)

    has_docs = db.query(models.PdfDocument).filter(models.PdfDocument.chat_id == chat_id).first() is not None
    rag_enabled = has_docs or kb_id is not None

    langchain_messages = []

    if has_docs or kb_id:
        from langchain_core.messages import SystemMessage
        parts = []
        if has_docs:
            parts.append("You have access to uploaded files in this chat. Use the search_session_files tool to find relevant content.")
        if kb_id:
            parts.append(f"You also have access to knowledge base #{kb_id}. Use search_knowledgebase_tool(kb_id={kb_id}, query=...) to search it.")
        langchain_messages.append(SystemMessage(content=" ".join(parts)))

    for m in history:
        if m.role == "user":
            from langchain_core.messages import HumanMessage
            langchain_messages.append(HumanMessage(content=m.content))
        else:
            from langchain_core.messages import AIMessage
            langchain_messages.append(AIMessage(content=m.content))

    token_row = db.query(models.DriveToken).filter(
        models.DriveToken.user_id == current_user["user_id"]
    ).first()
    drive_tools = make_drive_tools(token_row) if token_row else None
    graph = build_graph(rag_enabled=rag_enabled, extra_tools=drive_tools)

    thread_id = f"chat-{chat_id}"
    config = {"configurable": {"thread_id": thread_id}}

    result = graph.invoke(
        {"messages": langchain_messages},
        config=config,
    )

    ai_content = result["messages"][-1].content
    ai_msg = crud.save_message(db, chat_id, "assistant", ai_content)

    tool_calls = []
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "tool": tc.get("name", "unknown"),
                    "args": tc.get("args", {}),
                })
        elif msg.type == "tool":
            if tool_calls and "result" not in tool_calls[-1]:
                content = msg.content[:500] if msg.content else ""
                tool_calls[-1]["result"] = content.strip()[:200]

    if chat.title == "New Chat":
        title_text = body.content[:50]
        if len(body.content) > 50:
            title_text += "..."
        chat.title = title_text
        db.commit()

    return {
        "user_message": {
            "id": user_msg.id,
            "chat_id": user_msg.chat_id,
            "role": user_msg.role,
            "content": user_msg.content,
            "created_at": user_msg.created_at.isoformat(),
        },
        "assistant_message": {
            "id": ai_msg.id,
            "chat_id": ai_msg.chat_id,
            "role": ai_msg.role,
            "content": ai_msg.content,
            "created_at": ai_msg.created_at.isoformat(),
        },
        "tool_calls": tool_calls if tool_calls else None,
    }


# ─── Knowledgebase endpoints ─────────────────────────────────────


@app.post("/api/knowledgebases", response_model=schemas.KnowledgebaseOut)
def create_knowledgebase(body: schemas.KnowledgebaseCreate, current_user: dict = Depends(require_user), db: Session = Depends(get_db)):
    kb = models.Knowledgebase(
        user_id=current_user["user_id"],
        name=body.name,
        description=body.description,
        index_method=body.index_method,
        retrieval_mode=body.retrieval_mode,
        embedding_model=body.embedding_model,
        is_public=body.is_public,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


@app.get("/api/knowledgebases", response_model=list[schemas.KnowledgebaseOut])
def list_knowledgebases(current_user: dict = Depends(require_user), db: Session = Depends(get_db)):
    return db.query(models.Knowledgebase).filter(
        models.Knowledgebase.user_id == current_user["user_id"]
    ).order_by(models.Knowledgebase.updated_at.desc()).all()


@app.get("/api/knowledgebases/{kb_id}", response_model=schemas.KnowledgebaseOut)
def get_knowledgebase(kb_id: int, current_user: dict = Depends(require_user), db: Session = Depends(get_db)):
    kb = db.query(models.Knowledgebase).filter(
        models.Knowledgebase.id == kb_id,
        models.Knowledgebase.user_id == current_user["user_id"],
    ).first()
    if not kb:
        raise HTTPException(404, "Knowledgebase not found")
    return kb


@app.delete("/api/knowledgebases/{kb_id}")
def delete_knowledgebase(kb_id: int, current_user: dict = Depends(require_user), db: Session = Depends(get_db)):
    kb = db.query(models.Knowledgebase).filter(
        models.Knowledgebase.id == kb_id,
        models.Knowledgebase.user_id == current_user["user_id"],
    ).first()
    if not kb:
        raise HTTPException(404, "Knowledgebase not found")
    from app.module.knowledgebase.search import delete_kb_index
    delete_kb_index(kb_id)
    db.delete(kb)
    db.commit()
    return {"ok": True}


@app.post("/api/knowledgebases/{kb_id}/import", response_model=schemas.KnowledgebaseImportResponse)
def import_to_knowledgebase(
    kb_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    kb = db.query(models.Knowledgebase).filter(
        models.Knowledgebase.id == kb_id,
        models.Knowledgebase.user_id == current_user["user_id"],
    ).first()
    if not kb:
        raise HTTPException(404, "Knowledgebase not found")

    raw = file.file.read()
    if len(raw) > 50 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 50MB)")

    result = import_file_to_knowledgebase(db, kb_id, raw, file.filename, current_user["user_id"])
    return result


@app.get("/api/knowledgebases/{kb_id}/files", response_model=list[schemas.KnowledgebaseFileOut])
def list_kb_files(kb_id: int, current_user: dict = Depends(require_user), db: Session = Depends(get_db)):
    kb = db.query(models.Knowledgebase).filter(
        models.Knowledgebase.id == kb_id,
        models.Knowledgebase.user_id == current_user["user_id"],
    ).first()
    if not kb:
        raise HTTPException(404, "Knowledgebase not found")
    return db.query(models.KnowledgebaseFile).filter(
        models.KnowledgebaseFile.knowledgebase_id == kb_id
    ).order_by(models.KnowledgebaseFile.created_at.desc()).all()
