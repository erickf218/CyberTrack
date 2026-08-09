"""
Identificador de piezas basado en Gemini (multimodal), no YOLO.

CAMBIO DE ARQUITECTURA (de YOLO a Gemini):
YOLO necesitaba entrenamiento con fotos propias para reconocer piezas
específicas de robótica — sin eso, solo reconocía las 80 clases
genéricas de COCO. Gemini ya "sabe" qué es un Spark MAX o una llave
Allen sin que le enseñemos nada, porque vio muchísimas fotos e
información de ese tipo durante su entrenamiento. A cambio, perdemos
dos cosas que YOLO sí daba: coordenadas exactas de cada objeto en la
imagen (bounding boxes) y conteo confiable de cuántas piezas hay. Por
eso el flujo ahora es: Gemini dice QUÉ tipo de pieza ve, y el usuario
escribe manualmente CUÁNTAS hay al agregarla al inventario.

Esta sigue siendo la ÚNICA parte del proyecto que sabe cómo se llama
el proveedor de IA que se está usando. El resto del backend y el
frontend solo conocen la función `detect()` y su formato de salida
—por eso este cambio no tocó ni una línea de main.py, detect.py (la
ruta) ni la mayor parte de app.js.

REQUIERE:
Una variable de entorno GEMINI_API_KEY. Consigue una gratis (sin
tarjeta) en https://aistudio.google.com/apikey y ponla en
backend/.env (ver backend/.env.example).
"""
import json
import os
from pathlib import Path

from google import genai
from google.genai import types

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

PROMPT = (
    "Eres un asistente de un taller de robótica FRC. Observa la foto e "
    "identifica cada TIPO distinto de pieza o herramienta de robótica "
    "que puedas reconocer con confianza razonable (no cuentes cuántas "
    "unidades hay de cada una, solo identifica los tipos distintos que "
    "ves). Para cada una, da:\n"
    "- label: nombre corto y reconocible en el mundo FRC, ej. 'Motor NEO', "
    "'Motor Kraken', 'Spark MAX', 'Llave Allen', 'Tornillo M4', "
    "'Batería REV', 'Destornillador', 'Multímetro', 'Sensor ultrasónico'.\n"
    "- category: una categoría corta en español para agrupar inventario, "
    "ej. 'Motores', 'Controladores', 'Sensores', 'Tornillería', "
    "'Herramientas', 'Baterías'. Usa una palabra o dos, consistente si "
    "detectas varias piezas del mismo tipo general.\n"
    "- code: un código corto tipo SKU (mayúsculas, 3-8 caracteres, sin "
    "espacios, ej. 'MTR-NEO', 'SPK-MAX', 'ALN-25'), inventado por ti de "
    "forma que sea reconocible y distinto entre piezas diferentes.\n"
    "- confidence: valor entre 0 y 1.\n"
    "Si ves algo que no es una pieza de robótica reconocible, ignóralo — "
    "no listes objetos genéricos sin relación con un taller."
)

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "pieces": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "label": {"type": "STRING"},
                    "category": {"type": "STRING"},
                    "code": {"type": "STRING"},
                    "confidence": {"type": "NUMBER"},
                },
                "required": ["label", "category", "code", "confidence"],
            },
        }
    },
    "required": ["pieces"],
}

DEFAULT_CONFIDENCE_THRESHOLD = 0.4


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta la variable de entorno GEMINI_API_KEY. Consigue una gratis "
            "en https://aistudio.google.com/apikey y ponla en backend/.env "
            "(ver backend/.env.example)."
        )
    return genai.Client(api_key=api_key)


def _mime_type_for(path: Path) -> str:
    return MIME_TYPES.get(path.suffix.lower(), "image/jpeg")


def detect(image_path: str, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> list[dict]:
    """
    Manda la foto a Gemini y regresa una lista de piezas identificadas.

    A diferencia de la versión con YOLO, esto:
      - NO cuenta cuántas unidades hay (el usuario lo escribe a mano)
      - NO da coordenadas exactas (box siempre viene como None) —
        el frontend ya no dibuja cajas sobre la imagen, solo lista
        los resultados debajo.
    """
    client = _get_client()
    path = Path(image_path)
    image_bytes = path.read_bytes()

    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=[
            PROMPT,
            types.Part.from_bytes(data=image_bytes, mime_type=_mime_type_for(path)),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=RESPONSE_SCHEMA,
        ),
    )

    try:
        payload = json.loads(response.text)
    except (json.JSONDecodeError, TypeError) as error:
        raise RuntimeError(f"Gemini no devolvió JSON válido: {error}")

    detections = []
    for piece in payload.get("pieces", []):
        confidence = float(piece.get("confidence", 0))
        if confidence < confidence_threshold:
            continue
        detections.append({
            "label": piece.get("label", "desconocido"),
            "category": piece.get("category", "General"),
            "code": piece.get("code", ""),
            "confidence": round(confidence, 3),
            "box": None,
        })

    return detections
