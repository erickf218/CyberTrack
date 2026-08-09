"""
CyberTrack API — v1.0-beta "Asistente" (Gemini + Groq)
"""
import os

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.db import Base, engine, SessionLocal
from app.api import inventory, detect, assistant
from app.services.inventory_service import seed_if_empty

# Crear tablas (funciona tanto en SQLite como PostgreSQL)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CyberTrack API", version="1.0.0-beta")

# CORS: permitir GitHub Pages y localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "https://erickf218.github.io",
        "https://erickf218.github.io/CyberTrack",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
