from fastapi import Request
from fastapi.templating import Jinja2Templates
from auth import get_session_user, generate_csrf, get_flash

templates = Jinja2Templates(directory="templates")


def tmpl(request: Request, template_name: str, **kwargs):
    """Render a template with common context variables injected."""
    user = get_session_user(request)
    ctx = {
        "request": request,
        "current_user": user,
        "csrf_token": generate_csrf(str(user["id"]) if user else ""),
        "flash_messages": get_flash(request),
        **kwargs,
    }
    return templates.TemplateResponse(template_name, ctx)
