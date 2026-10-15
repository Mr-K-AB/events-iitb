# Event Management Platform

## Proposed plan / Design doc

A full-stack event management app, containerized for one-command deployment:

- **Backend:** FastAPI + PostgreSQL (SQLAlchemy), JWT auth, Google OAuth?
- **Frontend:** Streamlit (talks to the API over HTTP)
- **Proxy:** nginx/ngrok — single public entrypoint, ready to scale

## Roles

Role is contextual, not a fixed choice at signup:

- **Admin** — approves (or rejects) organizer requests, can promote/demote other admins, sees every
  account. The emails added to a specific list can be auto-promoted to admin the moment they sign in.
- **Organizer** — anyone with admin-approved organizer permission. Creates events, approves/rejects
  participant requests (respecting a capacity cap), invites volunteers by email, views live attendance,
  and marks volunteer attendance. New users request this permission from their dashboard; it sits in a
  `pending` status until an admin approves or rejects it.
- **Participant** — any signed-in user can request to join an event. Once approved, a unique QR code
  appears in "My Registrations" for that event.
- **Volunteer** — an organizer invites an existing user (by email) to volunteer for their event. Once
  the invitee accepts, they get a QR-scanning screen for that event to check participants in.

## Sign-in

Can limit the signups so that only **@iitb.ac.in** accounts can use the platform:

- **Google sign-in**?
- **Email/password**

## How it works

<!-- TODO: Further discussion and finalize -->

## Project layout

```
<!-- TODO: Update upon every change in directory. -->
```
