"""
Rutas de inventario: /api/inventory
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.schemas import PartCreate, PartUpdate, PartOut
from app.services import inventory_service

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def _to_out(part) -> PartOut:
    return PartOut(
        id=part.id,
        name=part.name,
        code=part.code,
        category=part.category,
        quantity=part.quantity,
        low_stock_threshold=part.low_stock_threshold,
        is_low_stock=part.quantity <= part.low_stock_threshold,
    )


@router.get("", response_model=list[PartOut])
def get_inventory(db: Session = Depends(get_db)):
    parts = inventory_service.list_parts(db)
    return [_to_out(p) for p in parts]


@router.post("", response_model=PartOut, status_code=201)
def add_part(data: PartCreate, db: Session = Depends(get_db)):
    try:
        part = inventory_service.create_part(db, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f'Ya existe una pieza con el código "{data.code}".',
        )
    return _to_out(part)


@router.patch("/{part_id}", response_model=PartOut)
def edit_part(part_id: int, data: PartUpdate, db: Session = Depends(get_db)):
    part = inventory_service.update_part(db, part_id, data)
    if part is None:
        raise HTTPException(status_code=404, detail="Pieza no encontrada")
    return _to_out(part)


@router.delete("/{part_id}", status_code=204)
def remove_part(part_id: int, db: Session = Depends(get_db)):
    deleted = inventory_service.delete_part(db, part_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Pieza no encontrada")
