from fastapi import Form, HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from config import settings

csrf_serializer = URLSafeTimedSerializer(settings.CSRF_SECRET)


class AuthRedirect(Exception):
    """Redirect used by auth dependencies."""

    def __init__(self, url: str = "/login"):
        self.url = url


def get_session_user(request: Request) -> dict | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return {
        "id": user_id,
        "username": request.session.get("username"),
        "role": request.session.get("role"),
    }


def require_login(request: Request) -> dict:
    user = get_session_user(request)
    if not user:
        raise AuthRedirect("/login")
    return user


def require_manager(request: Request) -> dict:
    user = require_login(request)
    if user["role"] != "manager":
        raise AuthRedirect("/operator")
    return user


def generate_csrf(user_id: str) -> str:
    return csrf_serializer.dumps(user_id)


def validate_csrf(token: str, user_id: str) -> bool:
    try:
        data = csrf_serializer.loads(token, max_age=3600)
        return data == user_id
    except (BadSignature, SignatureExpired):
        return False


def require_csrf(request: Request, csrf_token: str = Form(...)) -> None:
    user = get_session_user(request)
    user_id = str(user["id"]) if user else ""

    if not validate_csrf(csrf_token, user_id):
        raise HTTPException(status_code=403, detail="CSRF token invalid")


def is_valid_csrf_for_request(request: Request, token: str | None) -> bool:
    if not token:
        return False
    user = get_session_user(request)
    user_id = str(user["id"]) if user else ""
    return validate_csrf(token, user_id)


def flash(request: Request, message: str, category: str = "info") -> None:
    msgs = request.session.get("_flash", [])
    msgs.append({"message": message, "category": category})
    request.session["_flash"] = msgs


def get_flash(request: Request) -> list:
    msgs = request.session.get("_flash", [])
    request.session["_flash"] = []
    return msgs