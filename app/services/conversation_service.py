"""
Historial de conversación del asistente: guardarlo y leerlo de la
base de datos.
"""
from sqlalchemy.orm import Session
from app.models.message import AssistantMessage

# Cuántos mensajes como máximo se muestran/mandan de contexto. Sin
# límite, una conversación muy larga podría volverse lenta o cara al
# mandarse completa a Groq cada vez que se pregunta algo nuevo.
MAX_HISTORY_MESSAGES = 200


def save_message(db: Session, role: str, content: str) -> AssistantMessage:
    message = AssistantMessage(role=role, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def list_messages(db: Session, limit: int = MAX_HISTORY_MESSAGES) -> list[AssistantMessage]:
    return (
        db.query(AssistantMessage)
        .order_by(AssistantMessage.created_at.asc())
        .limit(limit)
        .all()
    )


def clear_messages(db: Session) -> None:
    db.query(AssistantMessage).delete()
    db.commit()
