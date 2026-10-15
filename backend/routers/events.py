from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
import schemas
from database import get_db
from security import get_current_user, get_current_organizer

router = APIRouter(prefix="/events", tags=["events"])


def _to_event_out(event: models.Event, db: Session, current_user: Optional[models.User]) -> schemas.EventOut:
    approved_count = (
        db.query(func.count(models.EventRegistration.id))
        .filter(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.status == models.RegistrationStatus.approved,
        )
        .scalar()
    )
    my_status = None
    if current_user:
        reg = (
            db.query(models.EventRegistration)
            .filter(
                models.EventRegistration.event_id == event.id,
                models.EventRegistration.participant_id == current_user.id,
            )
            .first()
        )
        if reg:
            my_status = reg.status

    out = schemas.EventOut.model_validate(event)
    out.approved_count = approved_count or 0
    out.my_registration_status = my_status
    return out


@router.post("", response_model=schemas.EventOut)
def create_event(
    payload: schemas.EventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_organizer),
):
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    event = models.Event(organizer_id=current_user.id, **payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return _to_event_out(event, db, current_user)


@router.get("", response_model=List[schemas.EventOut])
def list_events(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    events = db.query(models.Event).order_by(models.Event.start_time.asc()).all()
    return [_to_event_out(e, db, current_user) for e in events]


@router.get("/mine", response_model=List[schemas.EventOut])
def my_events(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    events = (
        db.query(models.Event)
        .filter(models.Event.organizer_id == current_user.id)
        .order_by(models.Event.start_time.asc())
        .all()
    )
    return [_to_event_out(e, db, current_user) for e in events]


@router.get("/{event_id}", response_model=schemas.EventOut)
def get_event(event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return _to_event_out(event, db, current_user)


@router.patch("/{event_id}", response_model=schemas.EventOut)
def update_event(
    event_id: int,
    payload: schemas.EventUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the organizer can update this event")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return _to_event_out(event, db, current_user)
