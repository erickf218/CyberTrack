"""
Ruta de detección: POST /api/detect

Recibe una foto, la manda a Gemini (Google AI) usando el nuevo SDK
google.genai, y devuelve las piezas de robótica que reconoció.
"""
import os
import json
import tempfile
import base64
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

# NUEVO SDK: google.genai (reemplaza google.generativeai)
from google import genai
from google.genai import types

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

router = APIRouter(prefix="/api/detect", tags=["detect"])

ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/webp",
    "image/heic", "image/heif",
}
HEIC_TYPES = {"image/heic", "image/heif"}


class DetectionItem(BaseModel):
    label: str
    category: str
    code: str
    confidence: float
    box: Optional[dict] = None


class DetectionResponse(BaseModel):
    model: str
    count: int
    detections: List[DetectionItem]


DETECTION_PROMPT = """
Analiza esta imagen e identifica todas las piezas de robótica, electrónica o mecanismos que veas.

Para CADA pieza que detectes, devuélveme un objeto JSON con ESTE formato exacto:
{
    "label": "nombre descriptivo de la pieza en minúsculas",
    "category": "categoría general (ej: Motores, Sensores, Estructura, Electrónica, Herramientas)",
    "code": "código corto tipo SKU en MAYÚSCULAS, máx 10 caracteres",
    "confidence": 0.95
}

REGLAS IMPORTANTES:
- Si hay 3 motores iguales, devuelve 3 objetos separados.
- Si NO hay piezas de robótica, devuelve una lista vacía [].
- Responde SOLO con el JSON array, sin markdown, sin explicaciones.
- confidence debe ser un número entre 0.0 y 1.0.
- NO incluyas el campo "box".

Ejemplo:
[
    {"label": "motor dc", "category": "Motores", "code": "MTR-DC01", "confidence": 0.92},
    {"label": "sensor ultrasónico", "category": "Sensores", "code": "SEN-US01", "confidence": 0.88}
]
"""


@router.post("", response_model=DetectionResponse)
async def detect_objects(file: UploadFile = File(...)):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY no configurada.")
    
    # Safari a veces manda content_type raro o None
    # Intentamos detectar por la extensión del archivo
    actual_type = file.content_type or ""
    
    # Si Safari no mandó content_type, inferimos por extensión
    if not actual_type or actual_type == "application/octet-stream":
        ext = Path(file.filename or "").suffix.lower()
        type_map = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp",
            ".heic": "image/heic", ".heif": "image/heif",
        }
        actual_type = type_map.get(ext, "")
    
    if actual_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Formato no soportado: '{actual_type}' (filename: {file.filename}). Usa JPG, PNG, WEBP o HEIC.",
        )
    
    # ... resto del código igual, pero usa actual_type en vez de file.content_type

    suffix = Path(file.filename or "").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    converted_path = None
    try:
        detect_path = tmp_path

        # Convertir HEIC a JPG
        if file.content_type in HEIC_TYPES:
            try:
                converted_path = tmp_path + "_converted.jpg"
                Image.open(tmp_path).convert("RGB").save(converted_path, "JPEG", quality=90)
                detect_path = converted_path
            except Exception as error:
                raise HTTPException(
                    status_code=422,
                    detail=f"No se pudo leer la foto HEIC: {error}. Prueba exportarla como JPG.",
                )

        # Leer imagen como bytes y convertir a base64
        with open(detect_path, "rb") as img_file:
            image_bytes = img_file.read()

        mime_type = "image/jpeg" if actual_type in HEIC_TYPES else actual_type

        # ============================================
        # NUEVO SDK google.genai
        # ============================================
        try:
            # Crear cliente (nueva forma, no más genai.configure)
            client = genai.Client(api_key=GEMINI_API_KEY)

            # Codificar imagen a base64 para enviar inline
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')

            # Llamar a Gemini con el nuevo formato
            response = client.models.generate_content(
                model='gemini-3.5-flash-lite',  # ← Modelo actual gratuito
                contents=[
                    types.Part.from_text(text=DETECTION_PROMPT),
                    types.Part.from_bytes(
                        data=image_bytes,  # ← bytes crudos, no base64
                        mime_type=mime_type
                    ),
                ]
            )

            raw_text = response.text.strip()

            # Limpiar markdown si viene envuelto
            if raw_text.startswith("```"):
                parts = raw_text.split("```")
                raw_text = parts[1] if len(parts) > 1 else raw_text
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()

            detections_raw = json.loads(raw_text)

            if not isinstance(detections_raw, list):
                raise ValueError("La respuesta no es una lista JSON")

        except json.JSONDecodeError as error:
            raise HTTPException(
                status_code=500,
                detail=f"Gemini devolvió respuesta inválida: {error}. Texto: {raw_text[:300]}"
            )
        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=f"Error con Gemini: {error}"
            )

        # Normalizar detecciones
        detections = []
        for det in detections_raw:
            if not isinstance(det, dict):
                continue

            detections.append(DetectionItem(
                label=str(det.get("label", "desconocido")).lower(),
                category=str(det.get("category", "General")),
                code=str(det.get("code", "")).upper(),
                confidence=float(det.get("confidence", 0.5)),
                box=None
            ))

    finally:
        Path(tmp_path).unlink(missing_ok=True)
        if converted_path:
            Path(converted_path).unlink(missing_ok=True)

    return DetectionResponse(
        model="gemini-3.5-flash-lite",
        count=len(detections),
        detections=detections,
    )