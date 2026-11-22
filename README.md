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

