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
#organizer dashboard
elif page == "Organizer Dashboard":
    st.header("Organizer Dashboard")

    organizer_status = user.get("organizer_status", "none")
    is_organizer = user.get("is_admin") or organizer_status == "approved"

    if not is_organizer:
        if organizer_status == "pending":
            st.warning(
                "Your request for organizer permission is pending admin review. "
                "You'll be able to create events once it's approved."
            )
        elif organizer_status == "rejected":
            st.error("Your previous organizer request was declined.")
            if st.button("Request organizer access again"):
                try:
                    st.session_state.user = api.request_organizer_access()
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        else:
            st.info("You need organizer permission (approved by an admin) to create and manage events.")
            if st.button("Request organizer access", type="primary"):
                try:
                    st.session_state.user = api.request_organizer_access()
                    st.success("Request submitted — an admin will review it.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        st.stop()

    with st.expander("➕ Create a new event"):
        with st.form("create_event_form"):
            title = st.text_input("Title")
            description = st.text_area("Description")
            location = st.text_input("Location")
            c1, c2 = st.columns(2)
            with c1:
                start_date = st.date_input("Start date", value=date.today())
                start_time_ = st.time_input("Start time", value=dtime(9, 0))
            with c2:
                end_date = st.date_input("End date", value=date.today())
                end_time_ = st.time_input("End time", value=dtime(17, 0))
            capacity = st.number_input("Capacity (0 = unlimited)", min_value=0, value=0)
            deadline_date = st.date_input("Registration deadline (optional)", value=None)

            submitted = st.form_submit_button("Create event", use_container_width=True)
            if submitted:
                payload = {
                    "title": title,
                    "description": description,
                    "location": location,
                    "start_time": datetime.combine(start_date, start_time_).isoformat(),
                    "end_time": datetime.combine(end_date, end_time_).isoformat(),
                    "capacity": int(capacity) if capacity > 0 else None,
                    "registration_deadline": datetime.combine(deadline_date, dtime(23, 59)).isoformat()
                    if deadline_date
                    else None,
                }
                try:
                    api.create_event(payload)
                    st.success("Event created!")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    st.divider()
    st.subheader("My Events")
    try:
        my_evts = api.my_events()
    except Exception as e:
        st.error(f"Could not load your events: {e}")
        my_evts = []

    if not my_evts:
        st.info("You haven't created any events yet.")

    for ev in my_evts:
        with st.expander(f"🎪 {ev['title']}  —  {fmt_dt(ev['start_time'])}"):
            cap_txt = f"{ev['approved_count']}/{ev['capacity']}" if ev["capacity"] else f"{ev['approved_count']} (no cap)"
            st.caption(f"Approved participants: {cap_txt}")

            tab_regs, tab_vols, tab_att = st.tabs(["Participant Requests", "Volunteers", "Live Attendance"])

            # ---- Participant requests ----
            with tab_regs:
                try:
                    regs = api.list_registrations(ev["id"])
                except Exception as e:
                    st.error(str(e))
                    regs = []

                pending = [r for r in regs if r["status"] == "pending"]
                others = [r for r in regs if r["status"] != "pending"]

                st.write(f"**Pending requests ({len(pending)})**")
                for r in pending:
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.write(f"{r['participant_name']} ({r['participant_email']})")
                    if c2.button("Approve", key=f"appr_{r['id']}"):
                        try:
                            api.decide_registration(r["id"], "approved")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                    if c3.button("Reject", key=f"rej_{r['id']}"):
                        try:
                            api.decide_registration(r["id"], "rejected")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

                if others:
                    st.write("**Decided requests**")
                    for r in others:
                        st.write(
                            f"- {r['participant_name']} ({r['participant_email']}): **{r['status']}**"
                            + (" — checked in ✅" if r["checked_in"] else "")
                        )

            # ---- Volunteers ----
            with tab_vols:
                with st.form(f"invite_vol_{ev['id']}"):
                    v_email = st.text_input("Volunteer's email (must already have an account)", key=f"vemail_{ev['id']}")
                    inv_submit = st.form_submit_button("Invite volunteer")
                    if inv_submit and v_email:
                        try:
                            api.invite_volunteer(ev["id"], v_email)
                            st.success("Volunteer invited!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

                try:
                    vols = api.list_volunteers(ev["id"])
                except Exception as e:
                    st.error(str(e))
                    vols = []

                for v in vols:
                    c1, c2, c3 = st.columns([3, 1.5, 1.5])
                    c1.write(f"{v['name']} ({v['email']}) — status: **{v['status']}**")
                    present_label = "Present ✅" if v["attendance_marked"] else "Mark present"
                    if c2.button(present_label, key=f"volatt_{v['id']}", disabled=v["attendance_marked"]):
                        try:
                            api.mark_volunteer_attendance(ev["id"], v["id"], True)
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                    if v["attendance_marked"] and c3.button("Undo", key=f"volundo_{v['id']}"):
                        try:
                            api.mark_volunteer_attendance(ev["id"], v["id"], False)
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

            # ---- Attendance ----
            with tab_att:
                try:
                    att = api.event_attendance(ev["id"])
                except Exception as e:
                    st.error(str(e))
                    att = []
                checked_in = [a for a in att if a["checked_in"]]
                st.metric("Checked in", f"{len(checked_in)} / {len(att)}")
                for a in att:
                    mark = "✅" if a["checked_in"] else "⬜"
                    st.write(f"{mark} {a['participant_name']} ({a['participant_email']})")

                st.divider()
                st.write("**Scan a participant's QR (organizers can also scan)**")
                cam_img = st.camera_input("Scan QR", key=f"organizer_scan_{ev['id']}")
                manual_token = st.text_input("...or paste QR token manually", key=f"manual_{ev['id']}")
                token_to_use = None
                if cam_img is not None:
                    token_to_use = decode_qr_from_image(Image.open(cam_img))
                    if not token_to_use:
                        st.warning("Couldn't read a QR code in that image, try again.")
                if manual_token:
                    token_to_use = manual_token.strip()
                if token_to_use and st.button("Submit scan", key=f"submit_scan_{ev['id']}"):
                    try:
                        result = api.scan_qr(ev["id"], token_to_use)
                        if result["success"]:
                            st.success(f"{result['message']}: {result.get('participant_name', '')}")
                        else:
                            st.error(result["message"])
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

# VOLUNTEER DASHBOARD
elif page == "Volunteer Dashboard":
    st.header("Volunteer Dashboard")

    try:
        assignments = api.my_volunteer_assignments()
    except Exception as e:
        st.error(f"Could not load your volunteer assignments: {e}")
        assignments = []

    invited = [a for a in assignments if a["status"] == "invited"]
    accepted = [a for a in assignments if a["status"] == "accepted"]

    if invited:
        st.subheader("Pending Invitations")
        for a in invited:
            try:
                ev = api.get_event(a["event_id"])
                title = ev["title"]
            except Exception:
                title = f"Event #{a['event_id']}"
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"You've been invited to volunteer for **{title}**")
            if c2.button("Accept", key=f"acc_{a['id']}"):
                try:
                    api.respond_to_invite(a["id"], True)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
            if c3.button("Decline", key=f"dec_{a['id']}"):
                try:
                    api.respond_to_invite(a["id"], False)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    st.divider()
    st.subheader("Your Events — Scan Attendance")
    if not accepted:
        st.info("You don't have any accepted volunteer assignments yet.")

    for a in accepted:
        try:
            ev = api.get_event(a["event_id"])
            title = ev["title"]
        except Exception:
            title = f"Event #{a['event_id']}"

        with st.expander(f"🙋 {title}"):
            cam_img = st.camera_input("Scan participant's QR code", key=f"vol_scan_{a['id']}")
            manual_token = st.text_input("...or paste QR token manually", key=f"vol_manual_{a['id']}")

            token_to_use = None
            if cam_img is not None:
                token_to_use = decode_qr_from_image(Image.open(cam_img))
                if not token_to_use:
                    st.warning("Couldn't read a QR code in that image, try again.")
            if manual_token:
                token_to_use = manual_token.strip()

            if token_to_use and st.button("Submit scan", key=f"vol_submit_{a['id']}"):
                try:
                    result = api.scan_qr(a["event_id"], token_to_use)
                    if result["success"]:
                        st.success(f"{result['message']}: {result.get('participant_name', '')}")
                    else:
                        st.error(result["message"])
                except Exception as e:
                    st.error(str(e))

            st.divider()
            st.write("**Attendance so far**")
            try:
                att = api.event_attendance(a["event_id"])
                checked_in = [x for x in att if x["checked_in"]]
                st.metric("Checked in", f"{len(checked_in)} / {len(att)}")
                for x in att:
                    mark = "✅" if x["checked_in"] else "⬜"
                    st.write(f"{mark} {x['participant_name']}")
            except Exception as e:
                st.error(str(e))
# ADMIN DASHBOARD
elif page == "Admin Dashboard":
    st.header("Admin Dashboard")

    tab_requests, tab_users = st.tabs(["Organizer Requests", "All Users"])

    with tab_requests:
        st.subheader("Pending organizer requests")
        try:
            pending = api.admin_list_organizer_requests(status="pending")
        except Exception as e:
            st.error(str(e))
            pending = []

        if not pending:
            st.info("No pending requests.")

        for u in pending:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{u['name']}** — {u['email']}")
            if c2.button("Approve", key=f"admin_appr_{u['id']}"):
                try:
                    api.admin_decide_organizer_request(u["id"], True)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
            if c3.button("Reject", key=f"admin_rej_{u['id']}"):
                try:
                    api.admin_decide_organizer_request(u["id"], False)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    with tab_users:
        st.subheader("All users")
        try:
            all_users = api.admin_list_users()
        except Exception as e:
            st.error(str(e))
            all_users = []

        for u in all_users:
            c1, c2, c3 = st.columns([3, 1.5, 1.5])
            badges = []
            if u["is_admin"]:
                badges.append("👑 admin")
            badges.append(f"organizer: {u['organizer_status']}")
            c1.write(f"**{u['name']}** — {u['email']}  \n_{', '.join(badges)}_")

            if u["id"] != user["id"]:
                if not u["is_admin"]:
                    if c2.button("Make admin", key=f"mkadmin_{u['id']}"):
                        try:
                            api.admin_set_admin(u["id"], True)
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                else:
                    if c2.button("Remove admin", key=f"rmadmin_{u['id']}"):
                        try:
                            api.admin_set_admin(u["id"], False)
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
            else:
                c2.caption("(you)")


