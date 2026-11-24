# Event Management Platform

A full-stack event management app:

- **Backend:** FastAPI + PostgreSQL (SQLAlchemy), JWT auth
- **Frontend:** Streamlit (talks to the API over HTTP)
- **Proxy:** ngrok — single public entrypoint, ready to scale

## Roles

Role is contextual, not a fixed choice at signup:

- **Admin** — approves (or rejects) organizer requests, can promote/demote other admins, sees every
  account. Emails listed in `ADMIN_EMAILS` are auto-promoted to admin the moment they sign up or log in.
- **Organizer** — anyone with admin-approved organizer permission. Creates events, approves/rejects
  participant requests (respecting a capacity cap), invites volunteers by email, views live attendance,
  and marks volunteer attendance. New users request this permission from their dashboard; it sits
  `pending` until an admin approves or rejects it.
- **Participant** — any signed-in user can request to join an event. Once approved, a unique QR code
  appears in "My Registrations" for that event.
- **Volunteer** — an organizer invites an existing user (by email) to volunteer for their event. Once
  the invitee accepts, they get a QR-scanning screen for that event to check participants in.

## Sign-in

Email/password only, restricted to **@iitb.ac.in** addresses (configurable via `ALLOWED_EMAIL_DOMAIN`,
set it to `""` to disable the restriction). Emails are normalized to lowercase on both signup and login,
so sign-in works regardless of capitalization.

## How it works

1. Admin(s) are configured via `ADMIN_EMAILS` before anyone else — the first thing to set up. Sign up
   with one of those emails and you land as admin immediately, no extra steps.
2. A new user signs up and lands with no organizer permission.
3. They click "Request organizer access" from the Organizer Dashboard -> status `pending`.
4. An admin reviews it from the Admin Dashboard -> approves or rejects.
5. Once approved, they can create events with an optional `capacity`.
6. Participants browse events and click "Request to join" -> status `pending`.
7. Organizer approves/rejects each request; approval is blocked once `capacity` is reached.
8. Approved participants get a QR code (unique per-registration token) under "My Registrations".
9. Organizer invites volunteers by email; invitees accept/decline from "Volunteer Dashboard".
10. Accepted volunteers (and the organizer) get a scanner — webcam capture decoded with OpenCV, plus
    a manual-entry fallback — that marks attendance instantly and idempotently.
11. Organizer marks volunteers themselves present/absent from the same dashboard.

## Project layout

```
event_platform/
├── backend/
│   ├── main.py            # FastAPI app, mounts routers, creates tables, admin bootstrap
│   ├── config.py          # env-driven settings (secret, domain restriction, admin emails)
│   ├── database.py        # SQLAlchemy engine/session
│   ├── models.py          # ORM models (User, Event, EventRegistration, EventVolunteer)
│   ├── schemas.py         # Pydantic request/response models
│   ├── security.py        # password hashing, JWT, role-check dependencies
│   ├── routers/
│   │   ├── auth.py            # signup / login / me
│   │   ├── users.py           # self-service organizer permission requests
│   │   ├── admin.py           # approve/reject organizer requests, manage admins
│   │   ├── events.py          # create/list/update events (organizer-gated)
│   │   ├── registrations.py   # request/approve/reject + QR image endpoint
│   │   ├── volunteers.py      # invite/accept/decline + volunteer attendance
│   │   └── attendance.py      # QR scan endpoint + attendance list
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .dockerignore
│   └── example.env         # for running the backend standalone (no Docker)
├── frontend/
│   ├── app.py              # Streamlit UI (all views/roles)
│   ├── api_client.py       # thin requests wrapper around the API
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .dockerignore
│   └── example.env         # for running the frontend standalone (no Docker)
├── docker-compose.yml
├── .gitignore
├── README.md
└── example.env          
```

## Deploying with Docker

```bash
cp example.env .env
```

Edit `.env`:
- `SECRET_KEY` — generate with `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`
- `ADMIN_EMAILS` — at least one `@iitb.ac.in` email that should start as admin
- `POSTGRES_PASSWORD` — set a real password

```bash
docker compose up -d --build
```

- `http://localhost:8000` → the FastAPI backend (interactive docs at `/docs`)
- `http://localhost:8501` → the Streamlit app

Sign up with an `ADMIN_EMAILS` account first — you land as admin immediately and can approve other
organizers from the Admin Dashboard.

This runs one instance each of Postgres, the backend, and the frontend — sized for a single department's
or fest's worth of traffic. If it ever needs to handle much more load, the backend is already stateless
(JWT auth, no server-side sessions) so it could be scaled horizontally behind a load balancer later
without any code changes — just not something this setup needs today.

### Logs / troubleshooting

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose ps
```

## Running without Docker (local dev)

### 1. Postgres

```bash
docker run -d --name event_platform_db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=eventdb -p 5432:5432 postgres:16
```

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in SECRET_KEY, ADMIN_EMAILS
uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```