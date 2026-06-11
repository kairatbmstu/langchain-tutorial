from pydantic import BaseModel
from typing import Optional
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
