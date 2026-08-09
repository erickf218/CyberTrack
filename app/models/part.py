"""
Modelo de una pieza dentro del inventario.

Cada fila de la tabla `parts` es una pieza distinta (no una unidad):
"Spark MAX" es una fila con quantity=3, no tres filas.
"""
from sqlalchemy import Column, Integer, String
from app.database.db import Base


class Part(Base):
    __tablename__ = "parts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)
    category = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    low_stock_threshold = Column(Integer, nullable=False, default=2)
