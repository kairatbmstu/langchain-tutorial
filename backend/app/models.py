import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), default="New Topic")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="topics")
    chats = relationship("Chat", back_populates="topic", cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), default="New Chat")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    topic = relationship("Topic", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    google_id = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    topics = relationship("Topic", back_populates="user", cascade="all, delete-orphan")


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(255), nullable=False, index=True)
    checkpoint_data = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class DriveToken(Base):
    __tablename__ = "drive_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")


class PdfDocument(Base):
    __tablename__ = "pdf_documents"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    text_content = Column(Text, nullable=False)
    text_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    chat = relationship("Chat")


class FileChunk(Base):
    __tablename__ = "file_chunks"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(Integer, ForeignKey("pdf_documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Knowledgebase(Base):
    __tablename__ = "knowledgebases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    index_method = Column(String(50), default="semantic")
    retrieval_mode = Column(String(50), default="hybrid")
    embedding_model = Column(String(255), default="text-embedding-3-large")
    is_public = Column(Boolean, default=False)
    allowed_user_ids = Column(JSON, default=list)
    allowed_group_ids = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User")
    files = relationship("KnowledgebaseFile", back_populates="knowledgebase", cascade="all, delete-orphan")
    records = relationship("KnowledgebaseRecord", back_populates="knowledgebase", cascade="all, delete-orphan")


class KnowledgebaseFile(Base):
    __tablename__ = "knowledgebase_files"

    id = Column(Integer, primary_key=True, index=True)
    knowledgebase_id = Column(Integer, ForeignKey("knowledgebases.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    category = Column(String(50), default="document")
    storage_path = Column(String(512), nullable=True)
    content_hash = Column(String(64), nullable=True)
    summary = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    knowledgebase = relationship("Knowledgebase", back_populates="files")


class KnowledgebaseRecord(Base):
    __tablename__ = "knowledgebase_records"

    id = Column(Integer, primary_key=True, index=True)
    knowledgebase_id = Column(Integer, ForeignKey("knowledgebases.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(Integer, ForeignKey("knowledgebase_files.id", ondelete="SET NULL"), nullable=True)
    record_type = Column(String(50), default="chunk")
    content_text = Column(Text, nullable=False)
    structured_payload = Column(JSON, nullable=True)
    chunk_index = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    is_public = Column(Boolean, default=False)
    allowed_user_ids = Column(JSON, default=list)
    allowed_group_ids = Column(JSON, default=list)
    record_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    knowledgebase = relationship("Knowledgebase", back_populates="records")


class KnowledgebaseSource(Base):
    __tablename__ = "knowledgebase_sources"

    id = Column(Integer, primary_key=True, index=True)
    knowledgebase_id = Column(Integer, ForeignKey("knowledgebases.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String(50), nullable=False)
    config = Column(JSON, default=dict)
    sync_enabled = Column(Boolean, default=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class KnowledgebaseAuditEntry(Base):
    __tablename__ = "knowledgebase_audit"

    id = Column(Integer, primary_key=True, index=True)
    knowledgebase_id = Column(Integer, ForeignKey("knowledgebases.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)
    query_text = Column(Text, nullable=True)
    retrieval_mode = Column(String(50), nullable=True)
    result_count = Column(Integer, nullable=True)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
