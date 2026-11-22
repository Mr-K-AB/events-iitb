from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from security import get_current_user

router = APIRouter(tags=["attendance"])


def _ensure_active_volunteer(db: Session, event_id: int, user_id: int):
    vol = (
        db.query(models.EventVolunteer)
        .filter(
            models.EventVolunteer.event_id == event_id,
            models.EventVolunteer.user_id == user_id,
        )
        .first()
    )
    if not vol or vol.status != models.VolunteerStatus.accepted:
        raise HTTPException(
            status_code=403,
            detail="You must be an accepted volunteer for this event to scan attendance",
        )


@router.post("/events/{event_id}/scan", response_model=schemas.ScanResult)
def scan_qr(
    event_id: int,
    payload: schemas.ScanRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Organizers can also scan on their own event; otherwise must be an accepted volunteer
    if event.organizer_id != current_user.id:
        _ensure_active_volunteer(db, event_id, current_user.id)

    reg = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event_id,
            models.EventRegistration.qr_token == payload.token,
        )
        .first()
    )
    if not reg:
        return schemas.ScanResult(success=False, message="QR code not recognized for this event")

    if reg.status != models.RegistrationStatus.approved:
        return schemas.ScanResult(
            success=False,
            message=f"Registration is not approved (status: {reg.status.value})",
            participant_name=reg.participant.name,
            participant_email=reg.participant.email,
        )

    if reg.checked_in:
        return schemas.ScanResult(
            success=True,
            message="Already checked in",
            participant_name=reg.participant.name,
            participant_email=reg.participant.email,
            already_checked_in=True,
        )

    reg.checked_in = True
    reg.checked_in_at = datetime.utcnow()
    reg.checked_in_by = current_user.id
    db.commit()

    return schemas.ScanResult(
        success=True,
        message="Attendance recorded",
        participant_name=reg.participant.name,
        participant_email=reg.participant.email,
    )


@router.get("/events/{event_id}/attendance", response_model=List[schemas.RegistrationOut])
def event_attendance(
    event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    is_organizer = event.organizer_id == current_user.id
    if not is_organizer:
        _ensure_active_volunteer(db, event_id, current_user.id)

    regs = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event_id,
            models.EventRegistration.status == models.RegistrationStatus.approved,
        )
        .all()
    )
    out = []
    for r in regs:
        item = schemas.RegistrationOut.model_validate(r)
        item.participant_name = r.participant.name
        item.participant_email = r.participant.email
        out.append(item)
    return out
