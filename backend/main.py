from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
import models  # noqa: F401  (ensures models are registered before create_all)
from routers import auth, events, registrations, volunteers, attendance, users, admin
from config import ADMIN_EMAILS
from database import SessionLocal

Base.metadata.create_all(bind=engine)


def _sync_admin_bootstrap():
    """On startup, promote any existing users whose email is in ADMIN_EMAILS."""
    if not ADMIN_EMAILS:
        return
    db = SessionLocal()
    try:
        existing = db.query(models.User).filter(models.User.email.in_(ADMIN_EMAILS)).all()
        for u in existing:
            u.is_admin = True
            if u.organizer_status != models.OrganizerStatus.approved:
                u.organizer_status = models.OrganizerStatus.approved
        if existing:
            db.commit()
    finally:
        db.close()


_sync_admin_bootstrap()

app = FastAPI(title="Event Management Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(events.router)
app.include_router(registrations.router)
app.include_router(volunteers.router)
app.include_router(attendance.router)
app.include_router(users.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "event-management-api"}
