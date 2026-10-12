import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Enum, Boolean, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship

from database import Base


class RegistrationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    waitlisted = "waitlisted"


class VolunteerStatus(str, enum.Enum):
    invited = "invited"
    accepted = "accepted"
    declined = "declined"


class OrganizerStatus(str, enum.Enum):
    none = "none"          # never requested organizer permission
    pending = "pending"    # requested, awaiting admin decision
    approved = "approved"  # admin approved — can create events
    rejected = "rejected"  # admin rejected — can request again


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    is_admin = Column(Boolean, default=False, nullable=False)
    organizer_status = Column(
        Enum(OrganizerStatus), default=OrganizerStatus.none, nullable=False
    )
    organizer_requested_at = Column(DateTime, nullable=True)
    organizer_decided_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    events_organized = relationship("Event", back_populates="organizer")
    registrations = relationship(
        "EventRegistration", back_populates="participant", foreign_keys="EventRegistration.participant_id"
    )
    volunteer_assignments = relationship("EventVolunteer", back_populates="user")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    location = Column(String, default="")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    capacity = Column(Integer, nullable=True)  # None = unlimited
    registration_deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organizer = relationship("User", back_populates="events_organized")
    registrations = relationship(
        "EventRegistration", back_populates="event", cascade="all, delete-orphan"
    )
    volunteers = relationship(
        "EventVolunteer", back_populates="event", cascade="all, delete-orphan"
    )


class EventRegistration(Base):
    __tablename__ = "event_registrations"
    __table_args__ = (UniqueConstraint("event_id", "participant_id", name="uq_event_participant"),)

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(RegistrationStatus), default=RegistrationStatus.pending, nullable=False)
    qr_token = Column(String, unique=True, default=lambda: uuid.uuid4().hex, nullable=False)
    applied_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)
    checked_in = Column(Boolean, default=False)
    checked_in_at = Column(DateTime, nullable=True)
    checked_in_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    event = relationship("Event", back_populates="registrations")
    participant = relationship("User", back_populates="registrations", foreign_keys=[participant_id])
    checked_in_by_user = relationship("User", foreign_keys=[checked_in_by])


class EventVolunteer(Base):
    __tablename__ = "event_volunteers"
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_event_volunteer"),)

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(VolunteerStatus), default=VolunteerStatus.invited, nullable=False)
    invited_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)
    attendance_marked = Column(Boolean, default=False)  # organizer marks volunteer present
    attendance_marked_at = Column(DateTime, nullable=True)

    event = relationship("Event", back_populates="volunteers")
    user = relationship("User", back_populates="volunteer_assignments")
