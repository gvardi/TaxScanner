"""Tests for classifier modules."""

import pytest
from taxscanner.classifier.models import ClassificationResult
from taxscanner.classifier.prompts import build_system_prompt, build_user_prompt
from taxscanner.extraction.models import ExtractedInvoice


class TestClassificationResult:
    def test_round_trip(self):
        cr = ClassificationResult(
            message_id="msg123",
            subject="AWS Invoice",
            sender="aws@amazon.com",
            date="2025-03-01",
            gmail_link="https://mail.google.com/mail/u/0/#inbox/msg123",
            source="pdf:invoice.pdf",
            expense_type="business",
            business="Software/IT",
            category="Cloud & Hosting",
            vendor="Amazon Web Services",
            amount="$150.00",
            invoice_date="2025-03-01",
            confidence=0.95,
            reasoning="AWS is a cloud hosting provider used for software business",
        )
        d = cr.to_dict()
        restored = ClassificationResult.from_dict(d)
        assert restored.message_id == cr.message_id
        assert restored.expense_type == "business"
        assert restored.business == "Software/IT"
        assert restored.confidence == 0.95


class TestPrompts:
    @pytest.fixture
    def config(self):
        return {
            "businesses": [
                {"name": "Real Estate", "code": "RE", "description": "Property management"},
                {"name": "Software/IT", "code": "SW", "description": "Software development"},
            ],
            "categories": [
                "Software & Subscriptions",
                "Cloud & Hosting",
                "Property Maintenance & Repairs",
            ],
        }

    def test_system_prompt_includes_businesses(self, config):
        prompt = build_system_prompt(config)
        assert "Real Estate" in prompt
        assert "Software/IT" in prompt
        assert "Property management" in prompt

    def test_system_prompt_includes_categories(self, config):
        prompt = build_system_prompt(config)
        assert "Software & Subscriptions" in prompt
        assert "Cloud & Hosting" in prompt

    def test_system_prompt_includes_json_format(self, config):
        prompt = build_system_prompt(config)
        assert "expense_type" in prompt
        assert "JSON array" in prompt

    def test_user_prompt_includes_invoice_data(self, config):
        invoices = [
            ExtractedInvoice(
                message_id="id1",
                subject="Your AWS Invoice",
                sender="aws@amazon.com",
                date="2025-01-15",
                text="Total: $150.00",
                source="body",
                gmail_link="https://mail.google.com/mail/u/0/#inbox/id1",
            ),
        ]
        prompt = build_user_prompt(invoices)
        assert "Your AWS Invoice" in prompt
        assert "aws@amazon.com" in prompt
        assert "$150.00" in prompt
