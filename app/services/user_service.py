from fastapi import HTTPException
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, username: str, password: str, role: str) -> User:
        if len(password) < 6:
            raise HTTPException(400, "Parola trebuie să aibă minimum 6 caractere")
        if self.db.query(User).filter_by(username=username).first():
            raise HTTPException(400, "Numele de utilizator există deja")
        if role not in ("manager", "operator"):
            raise HTTPException(400, "Rol invalid")

        user = User(
            username=username,
            password_hash=pwd_context.hash(password),
            role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user_id: int, username: str, role: str, current_user_id: int) -> User:
        user = self._get_or_404(user_id)
        if user_id == current_user_id and user.role != role:
            raise HTTPException(400, "Nu îți poți schimba propriul rol")
        if role not in ("manager", "operator"):
            raise HTTPException(400, "Rol invalid")

        existing = self.db.query(User).filter_by(username=username).first()
        if existing and existing.id != user_id:
            raise HTTPException(400, "Numele de utilizator există deja")

        user.username = username
        user.role = role
        self.db.commit()
        self.db.refresh(user)
        return user

    def deactivate(self, user_id: int) -> User:
        if user_id in (1, 2):
            raise HTTPException(400, "Conturile de sistem nu pot fi dezactivate")
        user = self._get_or_404(user_id)
        user.is_active = False
        self.db.commit()
        return user

    def authenticate(self, username: str, password: str) -> User | None:
        user = self.db.query(User).filter_by(username=username, is_active=True).first()
        if not user:
            return None
        if not pwd_context.verify(password, user.password_hash):
            return None
        return user

    def _get_or_404(self, user_id: int) -> User:
        user = self.db.query(User).filter_by(id=user_id).first()
        if not user:
            raise HTTPException(404, "Utilizatorul nu există")
        return user
