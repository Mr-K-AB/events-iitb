from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from security import get_current_admin

router = APIRouter(prefix="/admin", tags=["admin"])



@router.get("/users", response_model=List[schemas.UserOut])
def list_all_users(db: Session = Depends(get_db), current_admin: models.User = Depends(get_current_admin)):
    return db.query(models.User).order_by(models.User.created_at.asc()).all()


@router.patch("/users/{user_id}/admin", response_model=schemas.UserOut)
def set_admin_status(
    user_id: int,
    payload: schemas.AdminSetAdmin,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin),
):
    if user_id == current_admin.id and not payload.is_admin:
        raise HTTPException(status_code=400, detail="You can't remove your own admin access")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_admin = payload.is_admin
    if payload.is_admin and user.organizer_status != models.OrganizerStatus.approved:
        user.organizer_status = models.OrganizerStatus.approved
        user.organizer_decided_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user
