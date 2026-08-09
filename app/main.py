"""
CyberTrack API — v1.0-beta "Asistente" (Gemini + Groq)

Levanta el servidor con:
    uvicorn app.main:app --reload

La API queda en http://localhost:8000
Documentación automática en http://localhost:8000/docs
El frontend (frontend/index.html) se sirve DESDE ESTE MISMO backend en
http://localhost:8000/ — ya no hace falta un segundo servidor
(python3 -m http.server) para el frontend. Esto también es lo que
permite desplegarlo como un solo servicio en producción, sin líos de
CORS entre dos URLs distintas.

Requiere GEMINI_API_KEY para que /api/detect funcione, y GROQ_API_KEY
para que /api/assistant/ask funcione (ver backend/.env.example, o las
variables de entorno del servicio en producción).
"""
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # lee backend/.env antes de que se importe nada que use las API keys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database.db import Base, engine, SessionLocal
from app.api import inventory, detect, assistant
from app.services.inventory_service import seed_if_empty

# Crea las tablas si no existen todavía.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CyberTrack API", version="1.0.0-beta")

# Con frontend y backend en el mismo origen (misma URL) ya no haría
# falta CORS abierto, pero lo dejamos permisivo por si en el futuro
# alguien prueba el frontend desde otra URL/puerto durante desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "https://tusuario.github.io",  # ← tu GitHub Pages
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Las rutas /api/* se registran ANTES de montar los archivos estáticos
# — así FastAPI las resuelve primero, y todo lo demás (/, /index.html,
# /css/..., /js/...) cae al frontend servido como archivos estáticos.
app.include_router(inventory.router)
app.include_router(detect.router)
app.include_router(assistant.router)


@app.on_event("startup")
def startup():
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "project": "CyberTrack", "version": "1.0.0-beta"}


# frontend/ vive un nivel arriba de backend/ — mismo patrón que ai/
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
