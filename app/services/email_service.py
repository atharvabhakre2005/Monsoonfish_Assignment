"""
Automated email delivery service.

Sends the three processed image files as attachments via SMTP/TLS.
All credentials come from environment variables (see app.config).
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

from app.config import RECIPIENT_EMAIL, SENDER_EMAIL, SMTP_PASSWORD, SMTP_HOST, SMTP_PORT

logger = logging.getLogger(__name__)


def _validate_email_config() -> None:
    """Raise RuntimeError if any required email setting is missing."""
    missing = []
    if not RECIPIENT_EMAIL:
        missing.append("RECIPIENT_EMAIL")
    if not SENDER_EMAIL:
        missing.append("SENDER_EMAIL")
    if not SMTP_PASSWORD:
        missing.append("SMTP_PASSWORD")
    if missing:
        raise RuntimeError(
            f"Email configuration incomplete — missing env vars: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in your credentials."
        )


def _attach_file(msg: MIMEMultipart, filepath: Path) -> None:
    """Read a file from disk and attach it to the MIME message."""
    with open(filepath, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())

    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f"attachment; filename={filepath.name}",
    )
    msg.attach(part)


def send_results_email(output_paths: dict[str, Path]) -> str:
    """
    Send all processed images as email attachments.

    Parameters
    ----------
    output_paths : dict
        Keys are transformation names, values are Path objects to the
        generated PNG files.

    Returns
    -------
    str
        "sent" on success, or an error description string.
    """
    _validate_email_config()

    # ── Build the message ────────────────────────────────────────────────
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = "Processed Logo Output Results"

    body = (
        "Hello,\n\n"
        "Your logo has been processed. Please find the following outputs attached:\n\n"
        "  • silhouette.png  — Solid filled shape of the logo\n"
        "  • border.png      — Edge / outline extraction\n"
        "  • grayscale.png   — Grayscale conversion\n\n"
        "This email was sent automatically by the Logo Processing Service.\n"
    )
    msg.attach(MIMEText(body, "plain"))

    # ── Attach each output file ──────────────────────────────────────────
    for name, filepath in output_paths.items():
        if not filepath.exists():
            logger.warning("Output file missing, skipping attachment: %s", filepath)
            continue
        _attach_file(msg, filepath)
        logger.info("Attached %s → %s", name, filepath.name)

    # ── Send via SMTP/TLS ────────────────────────────────────────────────
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDER_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info("Email sent successfully to %s", RECIPIENT_EMAIL)
        return "sent"

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed — check SENDER_EMAIL and SMTP_PASSWORD")
        return "failed: authentication error"
    except smtplib.SMTPException as exc:
        logger.error("SMTP error: %s", exc)
        return f"failed: {exc}"
    except Exception as exc:
        logger.error("Unexpected email error: %s", exc)
        return f"failed: {exc}"
