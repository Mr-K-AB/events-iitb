from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict

from models import RegistrationStatus, VolunteerStatus, OrganizerStatus


# ---------- Auth / Users ----------
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    is_admin: bool
    organizer_status: OrganizerStatus


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Admin / organizer approval ----------
class OrganizerRequestDecision(BaseModel):
    approve: bool


class AdminSetAdmin(BaseModel):
    is_admin: bool


# ---------- Events ----------
class EventCreate(BaseModel):
    title: str
    description: str = ""
    location: str = ""
    start_time: datetime
    end_time: datetime
    capacity: Optional[int] = None
    registration_deadline: Optional[datetime] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    capacity: Optional[int] = None
    registration_deadline: Optional[datetime] = None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organizer_id: int
    title: str
    description: str
    location: str
    start_time: datetime
    end_time: datetime
    capacity: Optional[int]
    registration_deadline: Optional[datetime]
    approved_count: int = 0
    my_registration_status: Optional[RegistrationStatus] = None


# ---------- Registrations ----------
class RegistrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_id: int
    participant_id: int
    participant_name: Optional[str] = None
    participant_email: Optional[str] = None
    status: RegistrationStatus
    applied_at: datetime
    decided_at: Optional[datetime]
    checked_in: bool
    checked_in_at: Optional[datetime]


class RegistrationDecision(BaseModel):
    status: RegistrationStatus  # approved / rejected / waitlisted


# ---------- Volunteers ----------
class VolunteerInvite(BaseModel):
    email: EmailStr


class VolunteerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_id: int
    user_id: int
    name: Optional[str] = None
    email: Optional[str] = None
    status: VolunteerStatus
    invited_at: datetime
    responded_at: Optional[datetime]
    attendance_marked: bool
    attendance_marked_at: Optional[datetime]


class VolunteerRespond(BaseModel):
    accept: bool


class VolunteerAttendanceMark(BaseModel):
    present: bool = True


# ---------- Attendance / Scan ----------
class ScanRequest(BaseModel):
    token: str


class ScanResult(BaseModel):
    success: bool
    message: str
    participant_name: Optional[str] = None
    participant_email: Optional[str] = None
    already_checked_in: bool = False
