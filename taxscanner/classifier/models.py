"""Data models for classification results."""

from dataclasses import dataclass
from enum import StrEnum

from taxscanner.models_base import DictMixin


class ExpenseType(StrEnum):
    BUSINESS = "business"
    PERSONAL = "personal"
    UNCERTAIN = "uncertain"


@dataclass
class ClassificationResult(DictMixin):
    """Result of classifying an extracted invoice.

    Carries forward extraction metadata fields (message_id, subject, sender,
    date, gmail_link, source) so that each classification is self-contained
    for reporting without needing to join back to the original invoice.
    """

    message_id: str
    subject: str
    sender: str
    date: str
    gmail_link: str
    source: str

    # Classification fields
    expense_type: str  # "business", "personal", "uncertain"
    business: str  # "Real Estate", "Software/IT", "Shared", "" (if personal)
    category: str
    vendor: str
    amount: str  # Keep as string — may include currency symbol
    invoice_date: str  # Date from invoice (may differ from email date)
    confidence: float  # 0.0 to 1.0
    reasoning: str

    def __post_init__(self):
        # Coerce and validate expense_type
        try:
            self.expense_type = ExpenseType(self.expense_type)
        except ValueError:
            raise ValueError(
                f"Invalid expense_type '{self.expense_type}'. "
                f"Must be one of: {', '.join(e.value for e in ExpenseType)}"
            )
        # Validate confidence range
        self.confidence = float(self.confidence)
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {self.confidence}"
            )
