# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is TaxScanner

TaxScanner scans Gmail for invoice/receipt emails, extracts data from email bodies, PDFs, and images (via OCR), classifies expenses as business/personal using Claude AI, and generates Excel reports. It targets small business owners who need to categorize a year's worth of email receipts for tax filing.

## Commands

```bash
# Use the venv Python — system Python does not have dependencies installed
venv/Scripts/python.exe -m pytest tests/ -v          # run all tests (35 tests)
venv/Scripts/python.exe -m pytest tests/test_classifier.py -v  # single test file
venv/Scripts/python.exe -m pytest tests/ -k "test_round_trip"  # single test by name

# CLI usage
venv/Scripts/python.exe -m taxscanner.cli auth              # OAuth2 flow
venv/Scripts/python.exe -m taxscanner.cli scan --year 2025   # full pipeline
venv/Scripts/python.exe -m taxscanner.cli report --year 2025 # regenerate from cache
```

No build step, linter, or formatter is configured.

## Architecture

The pipeline runs as a linear sequence: **Gmail auth → search → fetch → extract → classify → report**.

`cli.py` orchestrates this pipeline in `cmd_scan()`. Each stage is a separate subpackage:

- **`gmail/`** — OAuth2 auth (`auth.py`), query building + paginated search (`search.py`), message fetching with attachment handling (`fetch.py`). Auth supports 3-tier credential resolution: user file → env var path → embedded OAuth2 client config.
- **`extraction/`** — Three extraction strategies tried per message: HTML/plain-text body parsing (`body.py`), PDF text extraction via pdfplumber (`pdf.py`), image OCR via Claude vision API (`ocr.py`). Results combined into `ExtractedInvoice` dataclass.
- **`classifier/`** — Sends batches of invoices to Claude API with a structured system prompt (`prompts.py`) that includes user-configured businesses and categories. Expects JSON array responses. Uses tenacity for retry logic. Output: `ClassificationResult` with expense_type (business/personal/uncertain), category, vendor, amount, confidence score.
- **`report/`** — Generates multi-sheet Excel workbook via openpyxl with separate sheets for business, personal, uncertain, and skipped items.
- **`utils/cache.py`** — JSON file cache under `.cache/` directory with subdirs for messages, extractions, and classifications. Keyed by Gmail message ID. Enables resume after interruption and report regeneration without re-scanning.

## Key design patterns

- **Dataclasses + `DictMixin`** (`models_base.py`): All data models (`ExtractedInvoice`, `ClassificationResult`) use dataclasses with a shared `to_dict()`/`from_dict()` mixin for cache serialization. `from_dict` silently ignores extra keys.
- **Config**: `config.py` loads from `config.yaml` (merged over defaults) + `.env` for `ANTHROPIC_API_KEY`. The `AppConfig` dataclass tree mirrors the YAML structure. `auth` command bypasses the ANTHROPIC_API_KEY check.
- **Lazy imports**: `cli.py` uses local imports inside command functions to keep startup fast and avoid import errors when optional dependencies aren't needed.

## Environment variables

- `ANTHROPIC_API_KEY` (required for scan/classify, not for auth)
- `GMAIL_CREDENTIALS_PATH` — override path to OAuth2 credentials JSON
- `GMAIL_TOKEN_PATH` — override path to cached OAuth2 token
