
import imaplib
import email
import os
import re
import time

from email.header import decode_header
from dotenv import load_dotenv

load_dotenv()

GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993


def connect_to_gmail():
    """Connect to Gmail using IMAP."""

    if not GMAIL_EMAIL or not GMAIL_APP_PASSWORD:
        raise ValueError("Gmail credentials missing in .env")

    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)

    return mail


def get_last_email_uid():
    """Get the latest email UID before OTP is requested."""

    mail = connect_to_gmail()

    try:
        status, _ = mail.select("INBOX")

        if status != "OK":
            raise RuntimeError("Unable to open Gmail inbox")

        status, data = mail.uid("search", None, "ALL")

        if status != "OK":
            raise RuntimeError("Unable to search Gmail inbox")

        uids = data[0].split()

        return int(uids[-1]) if uids else 0

    finally:
        mail.logout()


def decode_header_value(value):
    """Decode email headers."""

    if not value:
        return ""

    decoded_parts = []

    for content, encoding in decode_header(value):
        if isinstance(content, bytes):
            decoded_parts.append(
                content.decode(encoding or "utf-8", errors="replace")
            )
        else:
            decoded_parts.append(content)

    return "".join(decoded_parts)


def get_email_body(message):
    """Extract readable email content."""

    body_parts = []

    if message.is_multipart():

        for part in message.walk():

            if part.get_content_type() not in (
                "text/plain",
                "text/html"
            ):
                continue

            if part.get_content_disposition() == "attachment":
                continue

            payload = part.get_payload(decode=True)

            if payload:
                charset = part.get_content_charset() or "utf-8"

                body_parts.append(
                    payload.decode(charset, errors="replace")
                )

    else:
        payload = message.get_payload(decode=True)

        if payload:
            charset = message.get_content_charset() or "utf-8"

            body_parts.append(
                payload.decode(charset, errors="replace")
            )

    return "\n".join(body_parts)


def extract_otp(text):
    """Extract a six-digit OTP."""

    patterns = [
        r"(?:OTP|verification code|verification OTP|security code)"
        r"\D{0,40}(\d{6})",

        r"(\d{6})\D{0,40}"
        r"(?:OTP|verification code|security code)"
    ]

    for pattern in patterns:

        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return match.group(1)

    match = re.search(r"(?<!\d)\d{6}(?!\d)", text)

    return match.group(0) if match else None


def wait_for_otp(
    after_uid,
    timeout=120,
    poll_interval=5,
    sender_contains=None,
    subject_contains=None
):
    """Wait for a new OTP email and return its code."""

    start_time = time.monotonic()
    next_uid = after_uid + 1

    while time.monotonic() - start_time < timeout:

        mail = connect_to_gmail()

        try:
            status, _ = mail.select("INBOX")

            if status != "OK":
                raise RuntimeError("Unable to open Gmail inbox")

            status, data = mail.uid(
                "search",
                None,
                f"UID {next_uid}:*"
            )

            if status != "OK":
                raise RuntimeError("Gmail email search failed")

            uids = data[0].split()

            for uid in uids:

                uid_number = int(uid)

                if uid_number < next_uid:
                    continue

                next_uid = uid_number + 1

                status, message_data = mail.uid(
                    "fetch",
                    uid,
                    "(BODY.PEEK[])"
                )

                if status != "OK":
                    continue

                raw_email = next(
                    (
                        item[1]
                        for item in message_data
                        if isinstance(item, tuple)
                    ),
                    None
                )

                if not raw_email:
                    continue

                message = email.message_from_bytes(raw_email)

                sender = decode_header_value(
                    message.get("From", "")
                )

                subject = decode_header_value(
                    message.get("Subject", "")
                )

                if (
                    sender_contains
                    and sender_contains.lower() not in sender.lower()
                ):
                    continue

                if (
                    subject_contains
                    and subject_contains.lower() not in subject.lower()
                ):
                    continue

                body = get_email_body(message)

                otp = extract_otp(body)

                if otp:
                    print("OTP email received successfully.")
                    return otp

        finally:
            mail.logout()

        time.sleep(poll_interval)

    raise TimeoutError(
        f"OTP not received within {timeout} seconds."
    )
