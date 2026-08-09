"""
Lógica de inventario.

Las rutas (api/inventory.py) no deberían saber nada de SQLAlchemy.
Su trabajo es recibir el request y devolver el response. Este archivo
es el que realmente sabe cómo leer y escribir en la base de datos.
Esto es lo que nos permite, más adelante, cambiar de SQLite a
PostgreSQL sin tocar ni una sola ruta.
"""
from sqlalchemy.orm import Session
from app.models.part import Part
from app.models.schemas import PartCreate, PartUpdate


def list_parts(db: Session) -> list[Part]:
    return db.query(Part).order_by(Part.category, Part.name).all()


def get_part(db: Session, part_id: int) -> Part | None:
    return db.query(Part).filter(Part.id == part_id).first()


def create_part(db: Session, data: PartCreate) -> Part:
    part = Part(**data.model_dump())
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


def update_part(db: Session, part_id: int, data: PartUpdate) -> Part | None:
    part = get_part(db, part_id)
    if part is None:
        return None

    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(part, field, value)

    db.commit()
    db.refresh(part)
    return part


def delete_part(db: Session, part_id: int) -> bool:
    part = get_part(db, part_id)
    if part is None:
        return False
    db.delete(part)
    db.commit()
    return True


def seed_if_empty(db: Session) -> None:
    """
    Si la base de datos está vacía (primera vez que corre el proyecto),
    la llenamos con las piezas de ejemplo que ya veníamos usando en el
    frontend. Así v0.2 arranca mostrando lo mismo que v0.1, pero ahora
    viene de la base de datos real.
    """
    if db.query(Part).count() > 0:
        return

    sample_parts = [
        Part(name="NEO Vortex", code="MTR-NV", category="Motores", quantity=2, low_stock_threshold=2),
        Part(name="Kraken X60", code="MTR-KX", category="Motores", quantity=1, low_stock_threshold=2),
        Part(name="Spark MAX", code="CTL-SM", category="Controladores", quantity=3, low_stock_threshold=2),
        Part(name="Ultrasónico", code="SNS-US", category="Sensores", quantity=4, low_stock_threshold=2),
        Part(name="Tornillo M4", code="SCR-M4", category="Tornillería", quantity=18, low_stock_threshold=5),
        Part(name="Batería REV", code="BAT-RV", category="Tornillería", quantity=2, low_stock_threshold=3),
    ]
    db.add_all(sample_parts)
    db.commit()
