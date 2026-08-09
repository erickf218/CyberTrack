"""
Ruta del asistente: POST /api/assistant/ask
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.services import inventory_service, conversation_service
from app.services.assistant_service import ask
from app.models.schemas import AssistantMessageOut

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class AssistantMessage(BaseModel):
    role: str
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

    conversation_service.save_message(db, "user", request.question)
    conversation_service.save_message(db, "assistant", answer)

    return {"answer": answer}


@router.get("/history", response_model=list[AssistantMessageOut])
def get_history(db: Session = Depends(get_db)):
    return conversation_service.list_messages(db)


@router.delete("/history", status_code=204)
def delete_history(db: Session = Depends(get_db)):
    conversation_service.clear_messages(db)
