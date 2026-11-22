from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from security import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/me/request-organizer", response_model=schemas.UserOut)
def request_organizer_access(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    if current_user.is_admin or current_user.organizer_status == models.OrganizerStatus.approved:
        raise HTTPException(status_code=400, detail="You already have organizer permission")
    if current_user.organizer_status == models.OrganizerStatus.pending:
        raise HTTPException(status_code=400, detail="Your request is already pending review")

    current_user.organizer_status = models.OrganizerStatus.pending
    current_user.organizer_requested_at = datetime.utcnow()
    current_user.organizer_decided_at = None
    db.commit()
    db.refresh(current_user)
    return current_user
