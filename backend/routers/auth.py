from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from security import hash_password, verify_password, create_access_token, get_current_user
from config import ADMIN_EMAILS, ALLOWED_EMAIL_DOMAIN, is_allowed_email

router = APIRouter(prefix="/auth", tags=["auth"])


def _apply_admin_bootstrap(user: models.User) -> None:
    """If this email is in ADMIN_EMAILS, promote to admin + auto-approve as organizer."""
    if user.email.lower() in ADMIN_EMAILS:
        user.is_admin = True
        if user.organizer_status != models.OrganizerStatus.approved:
            user.organizer_status = models.OrganizerStatus.approved
            user.organizer_decided_at = datetime.utcnow()


@router.post("/signup", response_model=schemas.Token)
def signup(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()

    if not is_allowed_email(email):
        raise HTTPException(
            status_code=400,
            detail=f"Only @{ALLOWED_EMAIL_DOMAIN} email addresses can sign up.",
        )

    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    user = models.User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
    )
    _apply_admin_bootstrap(user)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))


@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form_data.username.strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token({"sub": str(user.id)})
    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
