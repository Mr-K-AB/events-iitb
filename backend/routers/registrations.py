from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import io
import qrcode

import models
import schemas
from database import get_db
from security import get_current_user

router = APIRouter(tags=["registrations"])


def _reg_out(reg: models.EventRegistration) -> schemas.RegistrationOut:
    out = schemas.RegistrationOut.model_validate(reg)
    out.participant_name = reg.participant.name
    out.participant_email = reg.participant.email
    return out


@router.post("/events/{event_id}/register", response_model=schemas.RegistrationOut)
def register_for_event(
    event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.registration_deadline and datetime.utcnow() > event.registration_deadline:
        raise HTTPException(status_code=400, detail="Registration deadline has passed")

    existing = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.event_id == event_id,
            models.EventRegistration.participant_id == current_user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already registered/requested for this event")

    reg = models.EventRegistration(event_id=event_id, participant_id=current_user.id)
    db.add(reg)
    db.commit()
    db.refresh(reg)
    return _reg_out(reg)


@router.get("/registrations/mine", response_model=List[schemas.RegistrationOut])
def my_registrations(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    regs = (
        db.query(models.EventRegistration)
        .filter(models.EventRegistration.participant_id == current_user.id)
        .all()
    )
    return [_reg_out(r) for r in regs]


@router.get("/events/{event_id}/registrations", response_model=List[schemas.RegistrationOut])
def list_registrations(
    event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the organizer can view registrations")

    regs = db.query(models.EventRegistration).filter(models.EventRegistration.event_id == event_id).all()
    return [_reg_out(r) for r in regs]


@router.patch("/registrations/{registration_id}/decision", response_model=schemas.RegistrationOut)
def decide_registration(
    registration_id: int,
    payload: schemas.RegistrationDecision,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    reg = db.query(models.EventRegistration).filter(models.EventRegistration.id == registration_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    event = reg.event
    if event.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the organizer can decide on registrations")

    if payload.status == models.RegistrationStatus.approved and event.capacity is not None:
        approved_count = (
            db.query(func.count(models.EventRegistration.id))
            .filter(
                models.EventRegistration.event_id == event.id,
                models.EventRegistration.status == models.RegistrationStatus.approved,
            )
            .scalar()
        )
        if approved_count >= event.capacity:
            raise HTTPException(status_code=400, detail="Event capacity reached")

    reg.status = payload.status
    reg.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(reg)
    return _reg_out(reg)


@router.get("/registrations/{registration_id}/qr")
def get_registration_qr(
    registration_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    reg = db.query(models.EventRegistration).filter(models.EventRegistration.id == registration_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.participant_id != current_user.id:
        raise HTTPException(status_code=403, detail="This is not your registration")
    if reg.status != models.RegistrationStatus.approved:
        raise HTTPException(status_code=400, detail="QR is only available once your registration is approved")

    img = qrcode.make(reg.qr_token)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
