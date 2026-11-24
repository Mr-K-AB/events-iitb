import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/eventdb")

# Restrict sign-ups to this email domain. Set to "" to disable the restriction.
ALLOWED_EMAIL_DOMAIN = os.getenv("ALLOWED_EMAIL_DOMAIN", "iitb.ac.in").strip().lower()

# Comma-separated emails that are auto-promoted to admin (and auto-approved as organizers)
# the moment they sign up or log in, e.g. "dean@iitb.ac.in,fest.head@iitb.ac.in"
ADMIN_EMAILS = {
    e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()
}


def is_allowed_email(email: str) -> bool:
    if not ALLOWED_EMAIL_DOMAIN:
        return True
    return email.strip().lower().endswith("@" + ALLOWED_EMAIL_DOMAIN)
