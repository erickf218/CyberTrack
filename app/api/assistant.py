"""
Ruta del asistente: POST /api/assistant/ask

Recibe una pregunta del usuario, lee el inventario actual de la base
de datos, y se lo pasa a ai/assistant/assistant.py (Groq) para que
responda qué piezas sirven, cuáles faltan, y recomendaciones.
"""
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.services import inventory_service, conversation_service
from app.models.schemas import AssistantMessageOut

# ai/ vive un nivel arriba de backend/, mismo patrón que detect.py
AI_DIR = Path(__file__).resolve().parents[3] / "ai"
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from assistant.assistant import ask  # noqa: E402

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class AssistantMessage(BaseModel):
    role: str  # "user" o "assistant"
    content: str


class AssistantRequest(BaseModel):
    question: str
    history: list[AssistantMessage] = []


class AssistantResponse(BaseModel):
    answer: str


@router.post("/ask", response_model=AssistantResponse)
def ask_assistant(request: AssistantRequest, db: Session = Depends(get_db)):
    parts = inventory_service.list_parts(db)
    inventory = [
        {
            "name": p.name,
            "code": p.code,
            "category": p.category,
            "quantity": p.quantity,
            "is_low_stock": p.quantity <= p.low_stock_threshold,
        }
        for p in parts
    ]

    history = [{"role": m.role, "content": m.content} for m in request.history]

    try:
        answer = ask(request.question, inventory, history=history)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error del asistente: {error}")

    # Se guarda DESPUÉS de que Groq respondió bien — si algo falla arriba,
    # no queremos una pregunta huérfana en el historial sin su respuesta.
    conversation_service.save_message(db, "user", request.question)
    conversation_service.save_message(db, "assistant", answer)

    return {"answer": answer}


@router.get("/history", response_model=list[AssistantMessageOut])
def get_history(db: Session = Depends(get_db)):
    return conversation_service.list_messages(db)


@router.delete("/history", status_code=204)
def delete_history(db: Session = Depends(get_db)):
    conversation_service.clear_messages(db)
