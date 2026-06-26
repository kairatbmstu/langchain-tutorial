from pydantic import BaseModel
from typing import Optional, Any
import datetime


class TopicCreate(BaseModel):
    title: str = "New Topic"


class TopicOut(BaseModel):
    id: int
    title: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


class ChatCreate(BaseModel):
    topic_id: int
    title: str = "New Chat"


class ChatOut(BaseModel):
    id: int
    topic_id: int
    title: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class SendMessage(BaseModel):
    content: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    captcha_id: str
    captcha_answer: int


class LoginRequest(BaseModel):
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    id_token: str


class AuthResponse(BaseModel):
    token: str
    user_id: int
    email: str


class KnowledgebaseCreate(BaseModel):
    name: str
    description: str = ""
    index_method: str = "semantic"
    retrieval_mode: str = "hybrid"
    embedding_model: str = "text-embedding-3-large"
    is_public: bool = False


class KnowledgebaseOut(BaseModel):
    id: int
    user_id: int
    name: str
    description: str
    index_method: str
    retrieval_mode: str
    embedding_model: str
    is_public: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


class KnowledgebaseFileOut(BaseModel):
    id: int
    knowledgebase_id: int
    original_name: str
    content_type: str | None
    file_size: int | None
    status: str
    summary: str | None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    filename: str
    original_name: str
    text_length: int
    deduped: bool = False


class KnowledgebaseImportResponse(BaseModel):
    status: str
    file_id: int | None = None
    chunks: int | None = None
    error: str | None = None
