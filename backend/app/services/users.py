from sqlalchemy.orm import Session

from app import models
from app.schemas import UserCreate


def create_user(payload: UserCreate, db: Session) -> models.User:
    user = models.User(name=payload.name, wallet_name=payload.wallet_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[models.User]:
    return db.query(models.User).order_by(models.User.id).all()
