"""
Conexión a la base de datos.

Empezamos con SQLite porque es un solo archivo, no requiere instalar
nada extra y es perfecto para desarrollo. El día que CyberTrack necesite
soportar varios talleres al mismo tiempo, aquí es lo único que cambia:
la URL de conexión pasa a apuntar a PostgreSQL.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./cybertrack.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # necesario solo para SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependencia de FastAPI: abre una sesión de base de datos por
    request y la cierra automáticamente al terminar, incluso si hay
    un error.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
