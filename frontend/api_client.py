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
