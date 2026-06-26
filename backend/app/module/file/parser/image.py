import base64
import mimetypes

from app.config import OPENAI_API_KEY


def parse_image(file_bytes: bytes, detail: str = "auto") -> str:
    if not OPENAI_API_KEY:
        return ""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        b64 = base64.b64encode(file_bytes).decode("utf-8")
        mime = mimetypes.guess_type("image.png")[0] or "image/png"

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image in detail, including all visible text, objects, people, and their relationships."},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": detail}},
                    ],
                }
            ],
            max_tokens=2048,
        )
        return resp.choices[0].message.content or ""
    except Exception:
        return ""
