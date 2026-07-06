"""
Email notifications, sent via smtplib over a standard SMTP connection
(e.g. Gmail with an App Password — see .env.example).

These are called from FastAPI BackgroundTasks, so a slow or failing SMTP
call never blocks or breaks the actual API response. Failures are logged,
not raised, for the same reason: a user's registration or login shouldn't
fail just because the notification email didn't go out.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def _send(to_email: str, subject: str, html_body: str):
    if not settings.smtp_username or not settings.smtp_password:
        logger.warning(
            "SMTP not configured (SMTP_USERNAME/SMTP_PASSWORD missing) — "
            "skipping email to %s: %s",
            to_email,
            subject,
        )
        return

    from_email = settings.smtp_from_email or settings.smtp_username

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(from_email, [to_email], msg.as_string())
    except Exception:
        logger.exception("Failed to send email to %s", to_email)


def send_verification_email(to_email: str, code: str):
    subject = "Verify your Docsift account"
    html = f"""
    <div style="font-family: sans-serif; max-width: 480px;">
      <h2>Verify your email</h2>
      <p>Enter this code to finish creating your Docsift account:</p>
      <p style="font-size: 32px; font-weight: 700; letter-spacing: 6px;">{code}</p>
      <p style="color: #666; font-size: 13px;">
        This code expires in {settings.verification_code_expire_minutes} minutes.
        If you didn't request this, you can ignore this email.
      </p>
    </div>
    """
    _send(to_email, subject, html)


def send_login_notification_email(
    to_email: str, device_name: str, location: str, ip_address: str, timestamp: str
):
    subject = "New login to your Docsift account"
    html = f"""
    <div style="font-family: sans-serif; max-width: 480px;">
      <h2>New login detected</h2>
      <p>Your Docsift account was just signed in to:</p>
      <table style="font-size: 14px; color: #333;">
        <tr><td style="padding: 4px 12px 4px 0; color: #888;">Device</td><td>{device_name}</td></tr>
        <tr><td style="padding: 4px 12px 4px 0; color: #888;">Location</td><td>{location}</td></tr>
        <tr><td style="padding: 4px 12px 4px 0; color: #888;">IP address</td><td>{ip_address}</td></tr>
        <tr><td style="padding: 4px 12px 4px 0; color: #888;">Time</td><td>{timestamp}</td></tr>
      </table>
      <p style="color: #666; font-size: 13px;">
        If this wasn't you, change your password immediately.
      </p>
    </div>
    """
    _send(to_email, subject, html)
