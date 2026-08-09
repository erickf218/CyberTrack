"""
Servicio del asistente con Groq.
"""
import os
from typing import List, Dict, Any

try:
    from groq import Groq
except ImportError:
    print("⚠️  groq no instalado. Ejecuta: pip install groq")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

SYSTEM_PROMPT = """Eres un asistente técnico especializado en robótica y electrónica.
Tienes acceso al inventario actual del taller. Responde en español.
Sé conciso pero útil. Si el usuario pregunta qué necesita para un proyecto,
revisa el inventario y dile qué tiene y qué le falta."""


def ask(question: str, inventory: List[Dict[str, Any]], history: List[Dict[str, str]] = None) -> str:
    if not GROQ_API_KEY:
        return "Error: GROQ_API_KEY no configurada. Contacta al administrador."

    if history is None:
        history = []

    inventory_text = "\n".join([
        f"- {p['name']} ({p['code']}): {p['quantity']} unidades"
        for p in inventory
    ]) if inventory else "Inventario vacío."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Inventario actual:\n{inventory_text}"},
    ]

    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": question})

    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        return response.choices[0].message.content
    except Exception as error:
        return f"Error al consultar al asistente: {error}"
