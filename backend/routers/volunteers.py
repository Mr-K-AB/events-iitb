from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from security import get_current_user

router = APIRouter(tags=["volunteers"])


def _vol_out(vol: models.EventVolunteer) -> schemas.VolunteerOut:
    out = schemas.VolunteerOut.model_validate(vol)
    out.name = vol.user.name
    out.email = vol.user.email
    return out


@router.post("/events/{event_id}/volunteers/invite", response_model=schemas.VolunteerOut)
def invite_volunteer(
    event_id: int,
    payload: schemas.VolunteerInvite,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the organizer can invite volunteers")

    invitee = db.query(models.User).filter(models.User.email == payload.email).first()
    if not invitee:
        raise HTTPException(status_code=404, detail="No user found with that email. They need to sign up first.")

    existing = (
        db.query(models.EventVolunteer)
        .filter(models.EventVolunteer.event_id == event_id, models.EventVolunteer.user_id == invitee.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="This user is already invited/assigned as a volunteer")

    vol = models.EventVolunteer(event_id=event_id, user_id=invitee.id)
    db.add(vol)
    db.commit()
    db.refresh(vol)
    return _vol_out(vol)


@router.get("/events/{event_id}/volunteers", response_model=List[schemas.VolunteerOut])
def list_volunteers(
    event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the organizer can view volunteers")

    vols = db.query(models.EventVolunteer).filter(models.EventVolunteer.event_id == event_id).all()
    return [_vol_out(v) for v in vols]


@router.get("/volunteers/mine", response_model=List[schemas.VolunteerOut])
def my_volunteer_assignments(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    vols = db.query(models.EventVolunteer).filter(models.EventVolunteer.user_id == current_user.id).all()
    return [_vol_out(v) for v in vols]


@router.patch("/volunteers/{volunteer_id}/respond", response_model=schemas.VolunteerOut)
def respond_to_invite(
    volunteer_id: int,
    payload: schemas.VolunteerRespond,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    vol = db.query(models.EventVolunteer).filter(models.EventVolunteer.id == volunteer_id).first()
    if not vol:
        raise HTTPException(status_code=404, detail="Volunteer invite not found")
    if vol.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="This invite is not yours")

    vol.status = models.VolunteerStatus.accepted if payload.accept else models.VolunteerStatus.declined
    vol.responded_at = datetime.utcnow()
    db.commit()
    db.refresh(vol)
    return _vol_out(vol)


@router.patch("/events/{event_id}/volunteers/{volunteer_id}/attendance", response_model=schemas.VolunteerOut)
def mark_volunteer_attendance(
    event_id: int,
    volunteer_id: int,
    payload: schemas.VolunteerAttendanceMark,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the organizer can mark volunteer attendance")

    vol = (
        db.query(models.EventVolunteer)
        .filter(models.EventVolunteer.id == volunteer_id, models.EventVolunteer.event_id == event_id)
        .first()
    )
    if not vol:
        raise HTTPException(status_code=404, detail="Volunteer not found for this event")

    vol.attendance_marked = payload.present
    vol.attendance_marked_at = datetime.utcnow()
    db.commit()
    db.refresh(vol)
    return _vol_out(vol)
