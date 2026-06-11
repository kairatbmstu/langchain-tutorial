import os
import uuid

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from pypdf import PdfReader

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


@app.post("/api/upload")
def upload_pdf(
    file: UploadFile = File(...),
    chat_id: int = Form(None),
    current_user: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    if chat_id:
        chat = db.query(models.Chat).join(models.Topic).filter(
            models.Chat.id == chat_id,
            models.Topic.user_id == current_user["user_id"],
        ).first()
        if not chat:
            raise HTTPException(404, "Chat not found")

    ext = os.path.splitext(file.filename)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, stored_name)

    raw = file.file.read()
    with open(filepath, "wb") as f:
        f.write(raw)

    text = ""
    try:
        import io
        reader = PdfReader(io.BytesIO(raw))
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    except Exception as e:
        text = f"[PDF text extraction failed: {e}]"

    if chat_id:
        crud.save_pdf_document(db, chat_id, stored_name, file.filename, text)

    return {
        "filename": stored_name,
        "original_name": file.filename,
        "url": f"/uploads/{stored_name}",
        "text_length": len(text),
    }


@app.post("/api/chats/{chat_id}/messages")
def send_message(
    chat_id: int,
    body: schemas.SendMessage,
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

    pdf_texts = crud.get_pdf_texts(db, chat_id)
    pdf_context = ""
    if pdf_texts:
        sections = []
        for doc in pdf_texts:
            sections.append(f"--- Content of {doc.original_name} ---\n{doc.text_content}")
        pdf_context = "\n\n".join(sections)

    langchain_messages = []
    if pdf_context:
        from langchain_core.messages import SystemMessage
        langchain_messages.append(SystemMessage(
            content=f"DO NOT call search_web or any other tool. The PDF content is right here \u2014 use it directly to answer.\n\n{pdf_context}"
        ))

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
    graph = build_graph(extra_tools=drive_tools)

    thread_id = f"chat-{chat_id}"
    config = {"configurable": {"thread_id": thread_id}}

    result = graph.invoke(
        {"messages": langchain_messages},
        config=config,
    )

    ai_content = result["messages"][-1].content
    ai_msg = crud.save_message(db, chat_id, "assistant", ai_content)

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
    }
