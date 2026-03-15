"""Shared test fixtures for TaxScanner."""

import pytest
from taxscanner.classifier.models import ClassificationResult
from taxscanner.config import AppConfig, ReportConfig
from taxscanner.extraction.models import ExtractedInvoice


@pytest.fixture
def sample_invoice():
    return ExtractedInvoice(
        message_id="abc123",
        subject="Your Invoice",
        sender="vendor@example.com",
        date="2025-01-15",
        text="Invoice text here",
        source="body",
        gmail_link="https://mail.google.com/mail/u/0/#inbox/abc123",
    )


@pytest.fixture
def sample_invoices():
    return [
        ExtractedInvoice(
            message_id="id1",
            subject="AWS Invoice",
            sender="aws@amazon.com",
            date="2025-01-15",
            text="Total: $150.00",
            source="body",
            gmail_link="https://mail.google.com/mail/u/0/#inbox/id1",
        ),
        ExtractedInvoice(
            message_id="id2",
            subject="Home Depot Receipt",
            sender="homedepot@email.com",
            date="2025-04-15",
            text="Total: $89.50\nItems: Lumber, nails",
            source="pdf:receipt.pdf",
            gmail_link="https://mail.google.com/mail/u/0/#inbox/id2",
        ),
    ]


@pytest.fixture
def sample_classifications():
    return [
        ClassificationResult(
            message_id="msg1",
            subject="AWS Invoice",
            sender="aws@amazon.com",
            date="2025-03-01",
            gmail_link="https://mail.google.com/mail/u/0/#inbox/msg1",
            source="pdf:invoice.pdf",
            expense_type="business",
            business="Software/IT",
            category="Cloud & Hosting",
            vendor="Amazon Web Services",
            amount="$150.00",
            invoice_date="2025-03-01",
            confidence=0.95,
            reasoning="AWS hosting",
        ),
        ClassificationResult(
            message_id="msg2",
            subject="Home Depot Receipt",
            sender="homedepot@email.com",
            date="2025-04-15",
            gmail_link="https://mail.google.com/mail/u/0/#inbox/msg2",
            source="body",
            expense_type="business",
            business="Real Estate",
            category="Property Maintenance & Repairs",
            vendor="Home Depot",
            amount="$89.50",
            invoice_date="2025-04-15",
            confidence=0.88,
            reasoning="Home improvement supplies for rental property",
        ),
        ClassificationResult(
            message_id="msg3",
            subject="Netflix Subscription",
            sender="info@netflix.com",
            date="2025-02-01",
            gmail_link="https://mail.google.com/mail/u/0/#inbox/msg3",
            source="body",
            expense_type="personal",
            business="",
            category="Software & Subscriptions",
            vendor="Netflix",
            amount="$15.99",
            invoice_date="2025-02-01",
            confidence=0.98,
            reasoning="Personal entertainment subscription",
        ),
        ClassificationResult(
            message_id="msg4",
            subject="Amazon Order",
            sender="orders@amazon.com",
            date="2025-05-10",
            gmail_link="https://mail.google.com/mail/u/0/#inbox/msg4",
            source="body",
            expense_type="uncertain",
            business="",
            category="Other",
            vendor="Amazon",
            amount="$45.00",
            invoice_date="2025-05-10",
            confidence=0.35,
            reasoning="Could be personal or business, unclear from description",
        ),
    ]


@pytest.fixture
def app_config():
    return AppConfig(report=ReportConfig(output_dir="test_reports"))
