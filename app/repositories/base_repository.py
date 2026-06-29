"""
Repository Pattern — STUB (directii viitoare de implementare).
"""
from sqlalchemy.orm import Session


class BaseRepository:
    """Abstract interface for all repositories."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, id: int):
        raise NotImplementedError

    def get_all(self) -> list:
        raise NotImplementedError

    def save(self, entity):
        raise NotImplementedError

    def delete(self, id: int) -> None:
        raise NotImplementedError
