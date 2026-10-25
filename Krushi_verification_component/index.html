import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
TEXT_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip() or "openrouter/free"
VISION_MODEL = (
    os.getenv("OPENROUTER_VISION_MODEL", "").strip()
    or TEXT_MODEL
)

API_URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT = 90


def _extract_error_message(response):
    """Extract a readable error message from an OpenRouter response."""
    try:
        data = response.json()
        error_data = data.get("error", {})
        if isinstance(error_data, dict):
            return str(error_data.get("message") or error_data)
        return str(error_data)
    except (ValueError, AttributeError):
        return (response.text or "")[:500]


def _request_ai(messages, model=None):
    """Send a chat-completions request and return a consistent result dictionary."""
    if not API_KEY:
        return {
            "success": False,
            "answer": (
                "OpenRouter API key is missing. Add OPENROUTER_API_KEY "
                "to your .env file, then restart Streamlit."
            ),
        }

    selected_model = (model or TEXT_MODEL).strip()
    payload = {
        "model": selected_model,
        "messages": messages,
        "temperature": 0.5,
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Krushi Mitra AI",
    }

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=TIMEOUT,
        )

        if not response.ok:
            details = _extract_error_message(response)
            return {
                "success": False,
                "answer": f"OpenRouter HTTP {response.status_code}: {details}",
            }

        result = response.json()
        choices = result.get("choices") or []
        if not choices:
            return {
                "success": False,
                "answer": "OpenRouter returned no choices. Please try another model.",
            }

        message = choices[0].get("message") or {}
        answer = message.get("content", "")

        # Some multimodal providers return content as a list of text blocks.
        if isinstance(answer, list):
            answer = "\n".join(
                str(item.get("text", ""))
                for item in answer
                if isinstance(item, dict) and item.get("text")
            )

        if not isinstance(answer, str):
            answer = str(answer) if answer is not None else ""

        answer = answer.strip()
        if not answer:
            refusal = message.get("refusal")
            return {
                "success": False,
                "answer": (
                    f"The AI did not provide a text answer. {refusal}"
                    if refusal
                    else "The AI returned an empty response. Please try again."
                ),
            }

        return {"success": True, "answer": answer}

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "answer": "AI request timed out. Please try again.",
        }
    except requests.exceptions.RequestException as error:
        return {
            "success": False,
            "answer": f"AI network request failed: {error}",
        }
    except (ValueError, KeyError, IndexError, TypeError) as error:
        return {
            "success": False,
            "answer": f"Could not read the AI response: {error}",
        }


def chat_with_ai(messages, language="English"):
    """Answer an agricultural question in the requested language."""
    system_message = {
        "role": "system",
        "content": (
            "You are Krushi Mitra AI, a helpful agricultural assistant. "
            f"Answer in the requested language: {language}. "
            "Use clear, practical explanations and ask a brief clarifying "
            "question when important details are missing. For crop diseases, "
            "describe visible or reported symptoms, possible causes, uncertainty, "
            "and safe next steps. Do not claim certainty from insufficient "
            "information. Do not invent live weather, market prices, or "
            "laboratory results. For pesticide use, follow the product label "
            "and consult a qualified local agricultural officer."
        ),
    }

    # Keep the supplied conversation history intact after the system prompt.
    return _request_ai([system_message] + list(messages))


def analyze_image(
    image_bytes,
    mime_type="image/jpeg",
    question="",
    language="English",
):
    """Analyze a crop or plant image using the configured vision model."""
    if not image_bytes:
        return {
            "success": False,
            "answer": "No image data was provided. Please upload an image and try again.",
        }

    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/jpeg"

    encoded_image = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (question or "").strip() or (
        "Examine this agricultural image. Describe only visible symptoms, "
        "possible causes, uncertainty, and safe next steps. Do not claim a "
        "definite diagnosis from the image alone."
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are an agricultural image-analysis assistant. "
                f"Respond in {language}. Separate direct visual observations "
                "from possible explanations. Never invent details that cannot "
                "be seen. Do not prescribe a pesticide or dosage from an image "
                "alone; recommend checking local agricultural guidance."
            ),
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{encoded_image}"
                    },
                },
            ],
        },
    ]

    return _request_ai(messages, model=VISION_MODEL)
