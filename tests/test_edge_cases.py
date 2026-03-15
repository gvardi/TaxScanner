"""Edge-case and integration tests."""

import json
from unittest.mock import MagicMock, patch

import pytest
from taxscanner.classifier.models import ClassificationResult, ExpenseType
from taxscanner.extraction.models import ExtractedInvoice
from taxscanner.config import AppConfig, _build_config
from taxscanner.report.excel import _parse_amount


class TestExpenseTypeEnum:
    def test_valid_values(self):
        assert ExpenseType("business") == ExpenseType.BUSINESS
        assert ExpenseType("personal") == ExpenseType.PERSONAL
        assert ExpenseType("uncertain") == ExpenseType.UNCERTAIN

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError, match="Invalid expense_type"):
            ClassificationResult(
                message_id="x", subject="x", sender="x", date="x",
                gmail_link="x", source="x", expense_type="invalid",
                business="", category="", vendor="", amount="",
                invoice_date="", confidence=0.5, reasoning="",
            )

    def test_confidence_out_of_range(self):
        with pytest.raises(ValueError, match="confidence must be between"):
            ClassificationResult(
                message_id="x", subject="x", sender="x", date="x",
                gmail_link="x", source="x", expense_type="business",
                business="", category="", vendor="", amount="",
                invoice_date="", confidence=1.5, reasoning="",
            )

    def test_negative_confidence_raises(self):
        with pytest.raises(ValueError, match="confidence must be between"):
            ClassificationResult(
                message_id="x", subject="x", sender="x", date="x",
                gmail_link="x", source="x", expense_type="business",
                business="", category="", vendor="", amount="",
                invoice_date="", confidence=-0.1, reasoning="",
            )


class TestFromDictEdgeCases:
    def test_extra_keys_ignored(self):
        data = {
            "message_id": "id1", "subject": "s", "sender": "s",
            "date": "d", "text": "t", "source": "body",
            "gmail_link": "g", "extra_field": "should_be_ignored",
        }
        inv = ExtractedInvoice.from_dict(data)
        assert inv.message_id == "id1"
        assert not hasattr(inv, "extra_field")

    def test_missing_key_raises(self):
        data = {"message_id": "id1", "subject": "s"}
        with pytest.raises(TypeError):
            ExtractedInvoice.from_dict(data)

    def test_classification_extra_keys_ignored(self):
        data = {
            "message_id": "id1", "subject": "s", "sender": "s",
            "date": "d", "gmail_link": "g", "source": "body",
            "expense_type": "business", "business": "b", "category": "c",
            "vendor": "v", "amount": "$10", "invoice_date": "d",
            "confidence": 0.8, "reasoning": "r", "unknown": "val",
        }
        cr = ClassificationResult.from_dict(data)
        assert cr.vendor == "v"


class TestParseAmount:
    def test_normal_amount(self):
        assert _parse_amount("$150.00") == 150.0

    def test_amount_with_commas(self):
        assert _parse_amount("$1,234.56") == 1234.56

    def test_amount_no_dollar(self):
        assert _parse_amount("89.50") == 89.50

    def test_malformed_amount(self):
        assert _parse_amount("Unknown") is None

    def test_empty_string(self):
        assert _parse_amount("") is None

    def test_none_returns_none(self):
        assert _parse_amount(None) is None


class TestConfig:
    def test_empty_config(self):
        config = _build_config({})
        assert config.classifier.model == "claude-sonnet-4-20250514"
        assert config.gmail.max_results == 500
        assert config.report.output_dir == "reports"
        assert len(config.categories) > 0

    def test_partial_override(self):
        config = _build_config({"classifier": {"model": "custom-model"}})
        assert config.classifier.model == "custom-model"
        assert config.classifier.batch_size == 10  # default preserved

    def test_businesses_parsed(self):
        config = _build_config({
            "businesses": [
                {"name": "Test", "code": "T", "description": "desc"},
            ]
        })
        assert len(config.businesses) == 1
        assert config.businesses[0].name == "Test"


class TestClassifyInvoicesMock:
    """Test classify_invoices with mocked Anthropic API."""

    def test_classify_invoices_success(self, sample_invoices):
        from taxscanner.classifier.client import classify_invoices

        mock_cache = MagicMock()
        mock_cache.get_classification.return_value = None

        api_response = [
            {
                "index": 0,
                "expense_type": "business",
                "business": "Software/IT",
                "category": "Cloud & Hosting",
                "vendor": "AWS",
                "amount": "$150.00",
                "invoice_date": "2025-01-15",
                "confidence": 0.95,
                "reasoning": "Cloud hosting",
            },
            {
                "index": 1,
                "expense_type": "business",
                "business": "Real Estate",
                "category": "Property Maintenance & Repairs",
                "vendor": "Home Depot",
                "amount": "$89.50",
                "invoice_date": "2025-04-15",
                "confidence": 0.88,
                "reasoning": "Supplies for rental",
            },
        ]

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(api_response))]

        config = AppConfig()

        with patch("taxscanner.classifier.client.anthropic.Anthropic") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.messages.create.return_value = mock_response

            results = classify_invoices(sample_invoices, mock_cache, config)

        assert len(results) == 2
        assert results[0].vendor == "AWS"
        assert results[0].expense_type == "business"
        assert results[1].vendor == "Home Depot"
        assert mock_cache.save_classification.call_count == 2

    def test_classify_invoices_with_cache_hit(self, sample_invoices):
        from taxscanner.classifier.client import classify_invoices

        cached_data = {
            "message_id": "id1", "subject": "AWS Invoice",
            "sender": "aws@amazon.com", "date": "2025-01-15",
            "gmail_link": "https://mail.google.com/mail/u/0/#inbox/id1",
            "source": "body", "expense_type": "business",
            "business": "Software/IT", "category": "Cloud & Hosting",
            "vendor": "AWS", "amount": "$150.00",
            "invoice_date": "2025-01-15", "confidence": 0.95,
            "reasoning": "cached",
        }

        mock_cache = MagicMock()
        mock_cache.get_classification.side_effect = [cached_data, None]

        api_response = [{
            "index": 0, "expense_type": "business", "business": "RE",
            "category": "Repairs", "vendor": "HD", "amount": "$89.50",
            "invoice_date": "2025-04-15", "confidence": 0.88, "reasoning": "test",
        }]

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(api_response))]

        config = AppConfig()

        with patch("taxscanner.classifier.client.anthropic.Anthropic") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.messages.create.return_value = mock_response

            results = classify_invoices(sample_invoices, mock_cache, config)

        assert len(results) == 2
        assert results[0].reasoning == "cached"  # from cache
        assert results[1].vendor == "HD"  # from API


class TestSpecialCharacters:
    def test_invoice_with_special_chars(self):
        inv = ExtractedInvoice(
            message_id="sp1",
            subject="Invoice — «test» & <html>",
            sender="vendör@example.com",
            date="2025-01-15",
            text="Amount: ¥1,000 • Tax: 10%",
            source="body",
            gmail_link="https://mail.google.com/mail/u/0/#inbox/sp1",
        )
        d = inv.to_dict()
        restored = ExtractedInvoice.from_dict(d)
        assert restored.subject == "Invoice — «test» & <html>"
        assert "¥1,000" in restored.text
