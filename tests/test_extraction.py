"""Tests for extraction modules."""

import pytest
from taxscanner.extraction.body import extract_from_body, _html_to_text
from taxscanner.extraction.models import ExtractedInvoice


class TestHtmlToText:
    def test_basic_html(self):
        html = "<html><body><p>Hello</p><p>World</p></body></html>"
        result = _html_to_text(html)
        assert "Hello" in result
        assert "World" in result

    def test_removes_scripts(self):
        html = "<html><body><script>alert('xss')</script><p>Content</p></body></html>"
        result = _html_to_text(html)
        assert "alert" not in result
        assert "Content" in result

    def test_removes_styles(self):
        html = "<html><body><style>.red{color:red}</style><p>Content</p></body></html>"
        result = _html_to_text(html)
        assert "red" not in result
        assert "Content" in result


class TestExtractFromBody:
    def test_prefers_html(self):
        msg = {
            "html_body": "<p>Invoice #123 - $50.00</p>",
            "plain_body": "Plain text fallback",
        }
        result = extract_from_body(msg)
        assert "Invoice #123" in result
        assert "$50.00" in result

    def test_falls_back_to_plain(self):
        msg = {
            "html_body": "",
            "plain_body": "Invoice #456 - Amount: $75.00",
        }
        result = extract_from_body(msg)
        assert "Invoice #456" in result

    def test_returns_none_for_short_body(self):
        msg = {"html_body": "", "plain_body": "Hi"}
        result = extract_from_body(msg)
        assert result is None

    def test_returns_none_for_empty(self):
        msg = {"html_body": "", "plain_body": ""}
        result = extract_from_body(msg)
        assert result is None

    def test_truncates_long_body(self):
        msg = {"html_body": "", "plain_body": "x" * 10000}
        result = extract_from_body(msg)
        assert len(result) < 6000
        assert "[truncated]" in result


class TestExtractedInvoice:
    def test_round_trip(self):
        inv = ExtractedInvoice(
            message_id="abc123",
            subject="Your Invoice",
            sender="vendor@example.com",
            date="2025-01-15",
            text="Invoice text here",
            source="body",
            gmail_link="https://mail.google.com/mail/u/0/#inbox/abc123",
        )
        d = inv.to_dict()
        restored = ExtractedInvoice.from_dict(d)
        assert restored.message_id == inv.message_id
        assert restored.subject == inv.subject
        assert restored.text == inv.text
