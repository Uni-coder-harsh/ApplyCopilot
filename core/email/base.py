"""
Abstract base class for all email adapters.
IMAP is the v1 implementation. Gmail OAuth slots in as v2
without touching any other code — just swap the adapter.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RawEmail:
    """Minimal structure returned by any adapter before parsing."""
    message_id: str
    subject: str
    sender: str
    recipients: list[str]
    body_text: str
    body_html: str
    timestamp: datetime
    thread_id: Optional[str] = None
    snippet: Optional[str] = None
    raw_headers: dict = field(default_factory=dict)


class EmailAdapter(ABC):
    """
    Base class all email adapters must implement.
    Core engine only depends on this interface — never on a concrete adapter.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish connection and authenticate."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Clean up connection."""
        ...

    @abstractmethod
    def fetch_emails(
        self,
        max_count: int = 200,
        since_days: int = 365,
    ) -> list[RawEmail]:
        """
        Fetch up to max_count emails going back since_days days.
        Returns a list of RawEmail — order is newest first.
        """
        ...

    @abstractmethod
    def test_connection(self) -> bool:
        """Return True if credentials are valid and server is reachable."""
        ...

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
