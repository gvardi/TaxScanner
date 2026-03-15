"""Data models for extracted invoice data."""

from dataclasses import dataclass

from taxscanner.models_base import DictMixin


@dataclass
class ExtractedInvoice(DictMixin):
    """Represents invoice data extracted from an email message."""

    message_id: str
    subject: str
    sender: str
    date: str
    text: str
    source: str  # e.g., "body", "pdf:invoice.pdf", "image:scan.png"
    gmail_link: str
