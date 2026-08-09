"""
Asistente técnico de CyberTrack, basado en Groq (razonamiento, no visión).

POR QUÉ GROQ AQUÍ Y GEMINI EN LA DETECCIÓN:
La detección de fotos necesita "ver" — ahí Gemini gana porque reconoce
piezas específicas de robótica sin entrenamiento. Este asistente solo
necesita "pensar" a partir de texto (tu inventario + tu pregunta) —
tarea puramente de razonamiento, sin nada visual. Ahí es donde Groq es
la mejor opción: su hardware (LPU) está diseñado específicamente para
inferencia rápida, así que las respuestas del asistente se sienten
casi instantáneas en vez de tardar varios segundos.

Esta sigue el mismo patrón que ai/inference/detector.py: es la ÚNICA
parte del proyecto que sabe que existe Groq. El backend solo conoce la
función `ask()` y su formato de entrada/salida — así que cambiar de
proveedor de IA en el futuro (si algún día quieres probar otro) sigue
siendo un cambio de un solo archivo.

REQUIERE:
Una variable de entorno GROQ_API_KEY. Consigue una gratis (sin
tarjeta) en https://console.groq.com/keys y ponla en backend/.env
(ver backend/.env.example).
"""
import os

from groq import Groq

DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

SYSTEM_PROMPT = (
    "Eres el asistente técnico de CyberTrack, un sistema de inventario para "
    "un taller de robótica FRC. Se te da el inventario actual del taller "
    "(piezas reales, con cantidad y categoría) y una pregunta o petición del "
    "usuario, normalmente sobre qué necesita para construir algo.\n\n"
    "Tu trabajo:\n"
    "1. Identifica qué piezas del inventario le sirven al usuario para lo que "
    "quiere construir.\n"
    "2. Señala claramente qué le falta (piezas típicas para ese tipo de "
    "proyecto que NO están en el inventario, o que están pero en cantidad "
    "insuficiente).\n"
    "3. Da recomendaciones breves y prácticas — qué comprar, qué alternativas "
    "hay con lo que ya tiene.\n\n"
    "Reglas importantes:\n"
    "- USA SOLO el inventario real que se te da. No inventes que el usuario "
    "tiene piezas que no están en la lista.\n"
    "- Si el inventario no tiene nada relevante para la pregunta, dilo "
    "claramente en vez de inventar.\n"
    "- Sé conciso — respuestas cortas y accionables, no ensayos. Usa listas "
    "cuando ayude a la claridad.\n"
    "- Responde siempre en español."
)


def _get_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta la variable de entorno GROQ_API_KEY. Consigue una gratis "
            "en https://console.groq.com/keys y ponla en backend/.env "
            "(ver backend/.env.example)."
        )
    return Groq(api_key=api_key)


def _format_inventory(parts: list[dict]) -> str:
    """
    Convierte la lista de piezas (tal como la devuelve inventory_service)
    en texto legible para el prompt. No mandamos el JSON crudo porque el
    modelo entiende y sigue mejor instrucciones con texto plano estructurado.
    """
    if not parts:
        return "(El inventario está vacío — no hay ninguna pieza registrada todavía.)"

    by_category: dict[str, list[dict]] = {}
    for part in parts:
        by_category.setdefault(part["category"], []).append(part)

    lines = []
    for category, items in sorted(by_category.items()):
        lines.append(f"{category}:")
        for item in items:
            flag = " [STOCK BAJO]" if item.get("is_low_stock") else ""
            lines.append(f"  - {item['name']} ({item['code']}): {item['quantity']} unidades{flag}")

    return "\n".join(lines)


def ask(question: str, inventory: list[dict], history: list[dict] | None = None) -> str:
    """
    Responde una pregunta del usuario usando el inventario actual como
    contexto. `history` es opcional: lista de mensajes previos de la
    conversación (formato [{"role": "user"|"assistant", "content": "..."}])
    para que el asistente recuerde el hilo si el frontend se lo manda.
    """
    client = _get_client()
    inventory_text = _format_inventory(inventory)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({
        "role": "system",
        "content": f"Inventario actual del taller:\n{inventory_text}",
    })
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        temperature=0.4,
    )

    return response.choices[0].message.content
