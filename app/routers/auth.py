from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from auth import flash, generate_csrf, get_flash, get_session_user, require_csrf
from database import get_db
from services.user_service import UserService
from template_utils import templates

router = APIRouter()


@router.get("/login")
def login_page(request: Request):
    if get_session_user(request):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "flash_messages": get_flash(request),
        "current_user": None,
        "csrf_token": generate_csrf(""),
    })


@router.post("/login")
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
):
    user = UserService(db).authenticate(username, password)
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "flash_messages": [{"message": "Nume de utilizator sau parolă incorectă", "category": "danger"}],
            "current_user": None,
            "csrf_token": generate_csrf(""),
        })

    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role

    if user.role == "operator":
        return RedirectResponse("/operator", status_code=302)
    return RedirectResponse("/dashboard", status_code=302)


@router.post("/logout")
def logout(
    request: Request,
    _: None = Depends(require_csrf),
):
    request.session.clear()
    flash(request, "Te-ai deconectat cu succes", "info")
    return RedirectResponse("/login", status_code=302)