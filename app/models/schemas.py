"""
Esquemas Pydantic.

Estos NO son la tabla de la base de datos (eso es `part.py`).
Son la forma que tienen los datos cuando entran o salen por la API.
Separarlos evita, por ejemplo, que alguien pueda mandar un `id` desde
el frontend e inventarse una pieza con un id que no le corresponde.
"""
from pydantic import BaseModel, Field
from datetime import datetime


class PartBase(BaseModel):
    name: str
    code: str
    category: str
    quantity: int = Field(ge=0, default=0)
    low_stock_threshold: int = Field(ge=0, default=2)


class PartCreate(PartBase):
    """Lo que se necesita para crear una pieza nueva."""
    pass


class PartUpdate(BaseModel):
    """Actualización parcial: todos los campos son opcionales."""
    name: str | None = None
    quantity: int | None = Field(default=None, ge=0)
    low_stock_threshold: int | None = Field(default=None, ge=0)


class PartOut(PartBase):
    """Lo que la API devuelve al frontend."""
    id: int
    is_low_stock: bool

    class Config:
        from_attributes = True


class AssistantMessageOut(BaseModel):
    """Un mensaje guardado del historial del chat."""
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
