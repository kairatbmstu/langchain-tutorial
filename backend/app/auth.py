import random
import datetime
import requests

import bcrypt
import jwt
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.config import SECRET_KEY, GOOGLE_CLIENT_ID

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 72

security = HTTPBearer(auto_error=False)

# In-memory CAPTCHA store (captcha_id -> answer)
_captcha_store: dict[str, int] = {}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_token(user_id: int, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def get_current_user(request: Request):
    auth: HTTPAuthorizationCredentials = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = auth.split(" ", 1)[1]
    try:
        return decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


def generate_captcha() -> dict:
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    op = random.choice(["+", "-"])
    if op == "-":
        a, b = max(a, b), min(a, b)
    answer = a + b if op == "+" else a - b
    captcha_id = random.randint(100000, 999999)
    _captcha_store[str(captcha_id)] = answer
    return {
        "captcha_id": str(captcha_id),
        "question": f"What is {a} {op} {b}?",
    }


def verify_captcha(captcha_id: str, answer: int) -> bool:
    stored = _captcha_store.pop(captcha_id, None)
    if stored is None:
        return False
    return stored == answer


def verify_google_token(token: str) -> dict | None:
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(500, "Google OAuth is not configured. Set GOOGLE_CLIENT_ID in .env")
    try:
        info = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        if info.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            return None
        return info
    except ValueError:
        return None
