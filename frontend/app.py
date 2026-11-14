import io
from datetime import datetime, date, time as dtime

import streamlit as st
from PIL import Image
import numpy as np
import cv2

import api_client as api

st.set_page_config(page_title="Event Management Platform", page_icon="🎪", layout="wide")

# ---------------- Session bootstrap ----------------
for key, default in [("token", None), ("user", None)]:
    if key not in st.session_state:
        st.session_state[key] = default


def logout():
    st.session_state.token = None
    st.session_state.user = None
    st.rerun()


def require_login():
    if not st.session_state.token:
        st.info("Please log in or sign up from the sidebar to continue.")
        st.stop()


def decode_qr_from_image(image: Image.Image) -> str | None:
    arr = np.array(image.convert("RGB"))
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(bgr)
    return data or None


def fmt_dt(iso_str: str) -> str:
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "")).strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return iso_str


# ---------------- Sidebar: auth ----------------
st.sidebar.title("🎪 Event Platform")

if not st.session_state.token:
    st.sidebar.caption("Only @iitb.ac.in email addresses can sign in or sign up.")

    tab_login, tab_signup = st.sidebar.tabs(["Log in", "Sign up"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in", use_container_width=True)
            if submitted:
                try:
                    result = api.login(email, password)
                    st.session_state.token = result["access_token"]
                    st.session_state.user = result["user"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")

    with tab_signup:
        with st.form("signup_form"):
            name = st.text_input("Full name")
            s_email = st.text_input("Email", key="signup_email")
            s_password = st.text_input("Password", type="password", key="signup_password")
            submitted = st.form_submit_button("Create account", use_container_width=True)
            if submitted:
                try:
                    result = api.signup(name, s_email, s_password)
                    st.session_state.token = result["access_token"]
                    st.session_state.user = result["user"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Signup failed: {e}")

    st.title("Welcome 👋")
    st.write(
        "This is the IIT Bombay event management platform. Sign up with your **@iitb.ac.in** email "
        "to register for events, and request organizer access from your dashboard to create and run "
        "your own events. Volunteers are invited by event organizers."
    )
    st.stop()

# Logged in
user = st.session_state.user
st.sidebar.success(f"Logged in as **{user['name']}**\n\n{user['email']}")
if st.sidebar.button("Log out", use_container_width=True):
    logout()

page_options = [
    "Browse & Register",
    "My Registrations",
    "Organizer Dashboard",
    "Volunteer Dashboard",
]
if user.get("is_admin"):
    page_options.append("Admin Dashboard")

page = st.sidebar.radio("Navigate", page_options)

# BROWSE & REGISTER (Participant view)

if page == "Browse & Register":
    st.header("Browse Events")
    try:
        events = api.list_events()
    except Exception as e:
        st.error(f"Could not load events: {e}")
        events = []

    if not events:
        st.info("No events yet.")

    for ev in events:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(ev["title"])
                st.write(ev["description"] or "_No description_")
                st.caption(
                    f"📍 {ev['location'] or 'TBD'}  |  🗓️ {fmt_dt(ev['start_time'])} → {fmt_dt(ev['end_time'])}"
                )
                cap_txt = f"{ev['approved_count']}/{ev['capacity']}" if ev["capacity"] else f"{ev['approved_count']} (no cap)"
                st.caption(f"Approved participants: {cap_txt}")
            with col2:
                status = ev.get("my_registration_status")
                if ev["organizer_id"] == user["id"]:
                    st.info("You organize this event")
                elif status is None:
                    if st.button("Request to join", key=f"reg_{ev['id']}", use_container_width=True):
                        try:
                            api.register_for_event(ev["id"])
                            st.success("Requested! Awaiting organizer approval.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                elif status == "pending":
                    st.warning("Request pending")
                elif status == "approved":
                    st.success("You're approved ✅")
                elif status == "rejected":
                    st.error("Request rejected")
                elif status == "waitlisted":
                    st.warning("Waitlisted")

# MY REGISTRATIONS (Participant view + QR)
elif page == "My Registrations":
    st.header("My Registrations")
    try:
        regs = api.my_registrations()
    except Exception as e:
        st.error(f"Could not load registrations: {e}")
        regs = []

    if not regs:
        st.info("You haven't requested to join any events yet. Go to 'Browse & Register'.")

    for reg in regs:
        try:
            ev = api.get_event(reg["event_id"])
        except Exception:
            ev = None

        with st.container(border=True):
            title = ev["title"] if ev else f"Event #{reg['event_id']}"
            st.subheader(title)
            st.caption(f"Status: **{reg['status'].upper()}**")

            if reg["status"] == "approved":
                if reg["checked_in"]:
                    st.success(f"Checked in at {fmt_dt(reg['checked_in_at'])} ✅")
                else:
                    st.info("Show this QR code to a volunteer at the event to check in.")
                    try:
                        qr_bytes = api.get_registration_qr_bytes(reg["id"])
                        st.image(io.BytesIO(qr_bytes), width=220)
                    except Exception as e:
                        st.error(f"Could not load QR: {e}")
