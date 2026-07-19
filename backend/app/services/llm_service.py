"""
LLM service para redacción natural de respuestas sobre reabastecimiento.
Utiliza Google Gemini API. Si falla, retorna None para que el llamador use fallback.
"""

import json
import urllib.request
import urllib.error
from ..config import GEMINI_API_KEY, GEMINI_MODEL

SYSTEM_PROMPT = """Eres un asistente experto en gestión de inventarios y reabastecimiento.
Tu tarea es redactar respuestas claras y profesionales en español basándote ÚNICAMENTE en los datos numéricos y contexto que se te proporciona.

REGLA CRÍTICA: Nunca inventes, recalcules ni modifiques ningún número. Solo reformula con los datos exactos que recibes.

Tu respuesta debe ser:
- Concisa y profesional
- En tono conversacional pero informativo
- Citando explícitamente los valores exactos del contexto (cantidades, fechas, prioridades)
- Sin especulaciones ni recomendaciones más allá de los datos proporcionados
"""


def get_llm_response(context: str, user_message: str) -> str | None:
    """
    Llama a Google Gemini API para redactar una respuesta natural.

    Args:
        context: Datos estructurados (números, recomendaciones) del sistema
        user_message: Pregunta del usuario

    Returns:
        Respuesta redactada por Gemini, o None si falla (para usar fallback)
    """
    if not GEMINI_API_KEY:
        return None

    try:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        params = {"key": GEMINI_API_KEY}
        full_url = f"{endpoint}?key={GEMINI_API_KEY}"

        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"CONTEXTO DEL SISTEMA:\n{context}\n\nPREGUNTA DEL USUARIO:\n{user_message}"
                        }
                    ]
                }
            ],
        }

        req = urllib.request.Request(
            full_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))

        if "candidates" in result and result["candidates"]:
            candidate = result["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                if parts and "text" in parts[0]:
                    return parts[0]["text"].strip()

        return None

    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError, TypeError, TimeoutError):
        return None
    except Exception:
        return None
