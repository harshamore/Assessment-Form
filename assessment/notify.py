"""Optional: email the handoff note to the Cisco PAM. Off unless secrets say otherwise."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .auth import secret


def enabled() -> bool:
    return bool(secret("send_email", False)) and bool(secret("smtp_host"))


def send_handoff(note: str, to_email: str, customer: str) -> tuple[bool, str]:
    """Returns (sent, message). Never raises: a failed send must not lose a registration."""
    if not enabled():
        return False, "Email sending is off."
    msg = EmailMessage()
    msg["Subject"] = f"Identity & AI assessment registration · {customer}"
    msg["From"] = secret("smtp_from") or secret("smtp_user")
    msg["To"] = to_email
    msg.set_content(note)
    try:
        with smtplib.SMTP(secret("smtp_host"), int(secret("smtp_port", 587) or 587), timeout=20) as smtp:
            smtp.starttls()
            user, password = secret("smtp_user"), secret("smtp_password")
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
    except Exception as exc:  # pragma: no cover - depends on a live SMTP server
        return False, f"Couldn't send the note: {exc}"
    return True, f"Handoff note emailed to {to_email}."
