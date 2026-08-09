"""
Modelo de un mensaje del chat del asistente.

Cada fila es UN mensaje (de usuario o del asistente), no una
conversación completa — así se puede reconstruir el hilo completo
ordenando por fecha, y es trivial agregar "conversaciones separadas"
más adelante si se necesita (solo habría que sumar una columna
conversation_id).
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database.db import Base


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, nullable=False)  # "user" o "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
