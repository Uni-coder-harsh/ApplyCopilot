"""
IMAP email adapter — v1 implementation.
Works with Gmail (app password), Outlook, Yahoo, ProtonMail Bridge,
and any standard IMAP server.
"""

import email
import imaplib
import logging
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from typing import Optional

from imapclient import IMAPClient

from core.email.base import EmailAdapter, RawEmail

logger = logging.getLogger(__name__)


def _decode_header_value(raw: str) -> str:
    """Safely decode RFC2047-encoded email headers."""
    if not raw:
        return ""
    parts = decode_header(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                decoded.append(part.decode("utf-8", errors="replace"))
        else:
            decoded.append(str(part))
    return " ".join(decoded).strip()


def _extract_body(msg: email.message.Message) -> tuple[str, str]:
    """Extract plain text and HTML body from a parsed email message."""
    text_body = ""
    html_body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition:
                continue
            charset = part.get_content_charset() or "utf-8"
            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                decoded = payload.decode(charset, errors="replace")
                if content_type == "text/plain" and not text_body:
                    text_body = decoded
                elif content_type == "text/html" and not html_body:
                    html_body = decoded
            except Exception:
                continue
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                content_type = msg.get_content_type()
                decoded = payload.decode(charset, errors="replace")
                if content_type == "text/html":
                    html_body = decoded
                else:
                    text_body = decoded
        except Exception:
            pass

    return text_body, html_body


class IMAPAdapter(EmailAdapter):
    """
    Connects to any IMAP server and fetches emails in batches.

    Usage:
        adapter = IMAPAdapter(
            host="imap.gmail.com",
            port=993,
            email="you@gmail.com",
            password="app-password",
        )
        with adapter:
            emails = adapter.fetch_emails(max_count=200, since_days=365)
    """

    # Common IMAP hosts — auto-detected from email domain
    KNOWN_HOSTS = {
        "gmail.com":     ("imap.gmail.com", 993),
        "googlemail.com":("imap.gmail.com", 993),
        "outlook.com":   ("outlook.office365.com", 993),
        "hotmail.com":   ("outlook.office365.com", 993),
        "live.com":      ("outlook.office365.com", 993),
        "yahoo.com":     ("imap.mail.yahoo.com", 993),
        "icloud.com":    ("imap.mail.me.com", 993),
        "protonmail.com":("127.0.0.1", 1143),   # ProtonMail Bridge
    }

    def __init__(
        self,
        host: str,
        port: int,
        email_address: str,
        password: str,
        ssl: bool = True,
        folder: str = "INBOX",
    ):
        self.host = host
        self.port = port
        self.email_address = email_address
        self.password = password
        self.ssl = ssl
        self.folder = folder
        self._client: Optional[IMAPClient] = None

    @classmethod
    def from_email(cls, email_address: str, password: str) -> "IMAPAdapter":
        """Auto-detect IMAP settings from email domain."""
        domain = email_address.split("@")[-1].lower()
        host, port = cls.KNOWN_HOSTS.get(domain, ("", 993))
        if not host:
            raise ValueError(
                f"Unknown email domain '{domain}'. "
                f"Please provide host and port manually."
            )
        return cls(host=host, port=port, email_address=email_address, password=password)

    def connect(self) -> None:
        logger.info(f"Connecting to {self.host}:{self.port}")
        self._client = IMAPClient(self.host, port=self.port, ssl=self.ssl)
        self._client.login(self.email_address, self.password)
        logger.info(f"Authenticated as {self.email_address}")

    def disconnect(self) -> None:
        if self._client:
            try:
                self._client.logout()
            except Exception:
                pass
            self._client = None

    def test_connection(self) -> bool:
        try:
            self.connect()
            self.disconnect()
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def fetch_emails(
        self,
        max_count: int = 200,
        since_days: int = 365,
    ) -> list[RawEmail]:
        if not self._client:
            raise RuntimeError("Not connected. Use `with adapter:` or call connect() first.")

        self._client.select_folder(self.folder, readonly=True)

        since_date = (datetime.now(timezone.utc) - timedelta(days=since_days)).date()
        since_str = since_date.strftime("%d-%b-%Y")

        # Search for all messages since the cutoff date
        uids = self._client.search(["SINCE", since_str])
        logger.info(f"Found {len(uids)} emails since {since_str}")

        # Take the most recent max_count (UIDs are oldest-first)
        uids_to_fetch = uids[-max_count:] if len(uids) > max_count else uids
        uids_to_fetch = list(reversed(uids_to_fetch))  # newest first

        if not uids_to_fetch:
            return []

        # Fetch in chunks to avoid overwhelming the server
        chunk_size = 50
        raw_emails: list[RawEmail] = []

        for i in range(0, len(uids_to_fetch), chunk_size):
            chunk = uids_to_fetch[i:i + chunk_size]
            messages = self._client.fetch(chunk, ["RFC822", "INTERNALDATE"])

            for uid, data in messages.items():
                try:
                    raw = self._parse_imap_message(uid, data)
                    if raw:
                        raw_emails.append(raw)
                except Exception as e:
                    logger.warning(f"Failed to parse message UID {uid}: {e}")
                    continue

        logger.info(f"Successfully fetched {len(raw_emails)} emails")
        return raw_emails

    def _parse_imap_message(self, uid: int, data: dict) -> Optional[RawEmail]:
        """Convert a raw IMAP fetch result into a RawEmail."""
        raw_bytes = data.get(b"RFC822")
        if not raw_bytes:
            return None

        msg = email.message_from_bytes(raw_bytes)
        internal_date = data.get(b"INTERNALDATE")

        # Parse timestamp
        if internal_date and hasattr(internal_date, "replace"):
            timestamp = internal_date.replace(tzinfo=timezone.utc)
        else:
            date_str = msg.get("Date", "")
            try:
                from email.utils import parsedate_to_datetime
                timestamp = parsedate_to_datetime(date_str)
            except Exception:
                timestamp = datetime.now(timezone.utc)

        # Parse headers
        message_id = msg.get("Message-ID", f"uid-{uid}").strip()
        subject = _decode_header_value(msg.get("Subject", "(no subject)"))
        sender = _decode_header_value(msg.get("From", ""))
        thread_id = msg.get("X-GM-THRID") or msg.get("References", "").split()[-1] if msg.get("References") else None

        # Parse recipients
        recipients = []
        for header in ["To", "Cc"]:
            val = msg.get(header, "")
            if val:
                recipients.extend([r.strip() for r in val.split(",") if r.strip()])

        # Extract body
        text_body, html_body = _extract_body(msg)

        # Build snippet from text body
        snippet = text_body[:200].replace("\n", " ").strip() if text_body else ""

        return RawEmail(
            message_id=message_id,
            subject=subject,
            sender=sender,
            recipients=recipients,
            body_text=text_body,
            body_html=html_body,
            timestamp=timestamp,
            thread_id=str(thread_id) if thread_id else None,
            snippet=snippet,
            raw_headers=dict(msg.items()),
        )

    def list_folders(self) -> list[str]:
        """List all available IMAP folders."""
        if not self._client:
            raise RuntimeError("Not connected.")
        return [f.decode() if isinstance(f, bytes) else str(f)
                for _, _, f in self._client.list_folders()]
