from jose import jwt
from datetime import datetime, timedelta
from core.config import settings

ALG = "HS256"

def sign_state(payload: dict, ttl_seconds: int = 600) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=ttl_seconds)
    body = {"iat": now, "exp": exp, **payload}
    return jwt.encode(body, settings.app_secret, algorithm=ALG)

def verify_state(token: str) -> dict:
    return jwt.decode(token, settings.app_secret, algorithms=[ALG])
