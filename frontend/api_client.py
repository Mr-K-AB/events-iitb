import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def _headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _handle(resp: requests.Response):
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise RuntimeError(detail)
    if resp.headers.get("content-type", "").startswith("application/json"):
        return resp.json()
    return resp.content


# ---------- Auth ----------
def signup(name, email, password):
    r = requests.post(f"{API_BASE_URL}/auth/signup", json={"name": name, "email": email, "password": password})
    return _handle(r)


def login(email, password):
    r = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": email, "password": password},
    )
    return _handle(r)


def me():
    r = requests.get(f"{API_BASE_URL}/auth/me", headers=_headers())
    return _handle(r)


# ---------- Organizer requests (self-service) ----------
def request_organizer_access():
    r = requests.post(f"{API_BASE_URL}/users/me/request-organizer", headers=_headers())
    return _handle(r)


# ---------- Admin ----------
def admin_list_organizer_requests(status="pending"):
    r = requests.get(f"{API_BASE_URL}/admin/organizer-requests", params={"status": status}, headers=_headers())
    return _handle(r)


def admin_decide_organizer_request(user_id, approve):
    r = requests.patch(
        f"{API_BASE_URL}/admin/organizer-requests/{user_id}", json={"approve": approve}, headers=_headers()
    )
    return _handle(r)


def admin_list_users():
    r = requests.get(f"{API_BASE_URL}/admin/users", headers=_headers())
    return _handle(r)


def admin_set_admin(user_id, is_admin):
    r = requests.patch(
        f"{API_BASE_URL}/admin/users/{user_id}/admin", json={"is_admin": is_admin}, headers=_headers()
    )
    return _handle(r)


# ---------- Events ----------
def create_event(payload):
    r = requests.post(f"{API_BASE_URL}/events", json=payload, headers=_headers())
    return _handle(r)


def list_events():
    r = requests.get(f"{API_BASE_URL}/events", headers=_headers())
    return _handle(r)


def my_events():
    r = requests.get(f"{API_BASE_URL}/events/mine", headers=_headers())
    return _handle(r)


def get_event(event_id):
    r = requests.get(f"{API_BASE_URL}/events/{event_id}", headers=_headers())
    return _handle(r)