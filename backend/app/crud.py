from sqlalchemy.orm import Session

from app.models import Topic, Chat, Message, PdfDocument


def get_topics(db: Session, user_id: int) -> list[Topic]:
    return db.query(Topic).filter(Topic.user_id == user_id).order_by(Topic.updated_at.desc()).all()


def create_topic(db: Session, user_id: int, title: str) -> Topic:
    topic = Topic(user_id=user_id, title=title)
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


def get_chats(db: Session, topic_id: int) -> list[Chat]:
    return db.query(Chat).filter(Chat.topic_id == topic_id).order_by(Chat.updated_at.desc()).all()


def create_chat(db: Session, topic_id: int, title: str) -> Chat:
    chat = Chat(topic_id=topic_id, title=title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


def delete_chat(db: Session, chat_id: int) -> bool:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        return False
    db.delete(chat)
    db.commit()
    return True


def get_messages(db: Session, chat_id: int) -> list[Message]:
    return db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at).all()


def save_message(db: Session, chat_id: int, role: str, content: str) -> Message:
    msg = Message(chat_id=chat_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def save_pdf_document(db: Session, chat_id: int, filename: str, original_name: str, text_content: str) -> PdfDocument:
    doc = PdfDocument(chat_id=chat_id, filename=filename, original_name=original_name, text_content=text_content)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_pdf_texts(db: Session, chat_id: int) -> list[PdfDocument]:
    return db.query(PdfDocument).filter(PdfDocument.chat_id == chat_id).all()
