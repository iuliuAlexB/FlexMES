from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from auth import require_csrf, require_manager, flash
from models import User
from services.user_service import UserService
from template_utils import tmpl

router = APIRouter()


@router.get("/users")
def users_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_manager),
):
    # Exclude mqtt_system (id=1) from the management UI
    users = db.query(User).filter(User.id != 1).order_by(User.created_at).all()
    return tmpl(request, "users.html", users=users)


@router.post("/users")
def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
    current_user: dict = Depends(require_manager),
):
    try:
        UserService(db).create(username, password, role)
        flash(request, f"Utilizatorul '{username}' a fost creat", "success")
    except Exception as e:
        flash(request, str(e.detail if hasattr(e, "detail") else e), "danger")
    return RedirectResponse("/users", status_code=302)


@router.post("/users/{user_id}/update")
def update_user(
    user_id: int,
    request: Request,
    username: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
    current_user: dict = Depends(require_manager),
):
    try:
        UserService(db).update(user_id, username, role, current_user["id"])
        flash(request, "Utilizator actualizat cu succes", "success")
    except Exception as e:
        flash(request, str(e.detail if hasattr(e, "detail") else e), "danger")
    return RedirectResponse("/users", status_code=302)


@router.post("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(require_csrf),
    current_user: dict = Depends(require_manager),
):
    try:
        UserService(db).deactivate(user_id)
        flash(request, "Utilizator dezactivat", "success")
    except Exception as e:
        flash(request, str(e.detail if hasattr(e, "detail") else e), "danger")
    return RedirectResponse("/users", status_code=302)