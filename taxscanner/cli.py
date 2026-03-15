"""CLI entry point for TaxScanner."""

import argparse
import sys
from pathlib import Path

from taxscanner import __version__
from taxscanner.config import load_config, AppConfig
from taxscanner.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


def cmd_auth(args, config):
    """Run OAuth2 authentication flow."""
    from taxscanner.gmail.auth import authenticate

    logger.info("Starting Gmail OAuth2 authentication...")
    service = authenticate()
    logger.info("Authentication successful! Token saved.")


def cmd_scan(args, config):
    """Run the full scan pipeline."""
    from taxscanner.gmail.auth import authenticate
    from taxscanner.gmail.search import search_emails
    from taxscanner.gmail.fetch import fetch_messages
    from taxscanner.extraction.body import extract_from_body
    from taxscanner.extraction.pdf import extract_from_pdf
    from taxscanner.extraction.ocr import extract_from_image
    from taxscanner.extraction.models import ExtractedInvoice
    from taxscanner.classifier.client import classify_invoices
    from taxscanner.report.excel import generate_report
    from taxscanner.utils.cache import Cache
    from tqdm import tqdm

    year = args.year
    logger.info(f"Starting scan for tax year {year}")

    # Step 1: Authenticate
    logger.info("Authenticating with Gmail...")
    service = authenticate()

    # Step 2: Search
    logger.info("Searching for invoice-related emails...")
    message_ids = search_emails(service, year, config)
    logger.info(f"Found {len(message_ids)} matching emails")

    if not message_ids:
        logger.info("No emails found. Nothing to do.")
        return

    # Step 3: Fetch messages
    cache = Cache()
    logger.info("Fetching email messages...")
    messages = fetch_messages(service, message_ids, cache, config)
    logger.info(f"Fetched {len(messages)} messages")

    # Step 4: Extract invoice data
    logger.info("Extracting invoice data...")
    invoices: list[ExtractedInvoice] = []
    skipped: list[dict] = []

    import anthropic
    anthropic_client = anthropic.Anthropic()

    for msg in tqdm(messages, desc="Extracting"):
        cached = cache.get_extraction(msg["id"])
        if cached:
            invoices.append(ExtractedInvoice.from_dict(cached))
            continue

        extracted = _extract_invoice(msg, config, anthropic_client=anthropic_client)
        if extracted:
            cache.save_extraction(msg["id"], extracted.to_dict())
            invoices.append(extracted)
        else:
            skipped.append({
                "id": msg["id"],
                "subject": msg.get("subject", ""),
                "from": msg.get("from", ""),
                "date": msg.get("date", ""),
                "reason": "No extractable invoice data",
            })

    logger.info(f"Extracted {len(invoices)} invoices, skipped {len(skipped)}")

    # Step 5: Classify
    logger.info("Classifying expenses with Claude AI...")
    classifications = classify_invoices(invoices, cache, config)
    logger.info(f"Classified {len(classifications)} invoices")

    # Step 6: Generate report
    logger.info("Generating Excel report...")
    report_path = generate_report(classifications, skipped, year, config)
    logger.info(f"Report saved to: {report_path}")

    # Summary
    business = [c for c in classifications if c.expense_type == "business"]
    personal = [c for c in classifications if c.expense_type == "personal"]
    uncertain = [c for c in classifications if c.expense_type == "uncertain"]

    print(f"\n{'='*50}")
    print(f"  TaxScanner Results — Tax Year {year}")
    print(f"{'='*50}")
    print(f"  Emails scanned:      {len(messages)}")
    print(f"  Invoices extracted:  {len(invoices)}")
    print(f"  Business expenses:   {len(business)}")
    print(f"  Personal expenses:   {len(personal)}")
    print(f"  Uncertain:           {len(uncertain)}")
    print(f"  Skipped:             {len(skipped)}")
    print(f"  Report:              {report_path}")
    print(f"{'='*50}\n")


def cmd_report(args, config):
    """Regenerate report from cached data."""
    from taxscanner.utils.cache import Cache
    from taxscanner.classifier.models import ClassificationResult
    from taxscanner.report.excel import generate_report

    cache = Cache()
    year = args.year

    logger.info(f"Loading cached classifications for year {year}...")
    cached_classifications = cache.get_all_classifications()

    if not cached_classifications:
        logger.error("No cached classifications found. Run 'scan' first.")
        sys.exit(1)

    classifications = [ClassificationResult.from_dict(c) for c in cached_classifications]
    skipped = cache.get_skipped() or []

    logger.info(f"Loaded {len(classifications)} classifications from cache")

    report_path = generate_report(classifications, skipped, year, config)
    logger.info(f"Report saved to: {report_path}")
    print(f"Report generated: {report_path}")


def _valid_year(value: str) -> int:
    """Validate year argument is in reasonable range."""
    try:
        year = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid year: {value!r}")
    if not (2000 <= year <= 2100):
        raise argparse.ArgumentTypeError(f"year must be between 2000 and 2100, got {year}")
    return year


def _extract_invoice(msg: dict, config, anthropic_client=None) -> "ExtractedInvoice | None":
    """Extract invoice data from a message using all available methods."""
    from taxscanner.extraction.body import extract_from_body
    from taxscanner.extraction.pdf import extract_from_pdf
    from taxscanner.extraction.ocr import extract_from_image
    from taxscanner.extraction.models import ExtractedInvoice

    texts = []
    source_parts = []

    # Extract from email body
    body_text = extract_from_body(msg)
    if body_text:
        texts.append(body_text)
        source_parts.append("body")

    # Extract from PDF attachments
    for attachment in msg.get("attachments", []):
        filename = attachment.get("filename", "").lower()
        data = attachment.get("data")
        if not data:
            continue

        if filename.endswith(".pdf"):
            pdf_text = extract_from_pdf(data, filename)
            if pdf_text:
                texts.append(pdf_text)
                source_parts.append(f"pdf:{filename}")
        elif filename.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            ocr_text = extract_from_image(data, filename, config, client=anthropic_client)
            if ocr_text:
                texts.append(ocr_text)
                source_parts.append(f"image:{filename}")

    if not texts:
        return None

    combined_text = "\n\n---\n\n".join(texts)

    return ExtractedInvoice(
        message_id=msg["id"],
        subject=msg.get("subject", ""),
        sender=msg.get("from", ""),
        date=msg.get("date", ""),
        text=combined_text,
        source=", ".join(source_parts),
        gmail_link=f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
    )


def main():
    parser = argparse.ArgumentParser(
        prog="taxscanner",
        description="Scan Gmail for invoices and classify business expenses",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # auth command
    subparsers.add_parser("auth", help="Run Gmail OAuth2 authentication")

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan Gmail and classify expenses")
    scan_parser.add_argument("--year", type=_valid_year, required=True, help="Tax year to scan")

    # report command
    report_parser = subparsers.add_parser("report", help="Regenerate report from cache")
    report_parser.add_argument("--year", type=_valid_year, required=True, help="Tax year")
    report_parser.add_argument("--from-cache", action="store_true", default=True)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    setup_logging(verbose=args.verbose)

    try:
        config = load_config(args.config)
    except EnvironmentError as e:
        if args.command == "auth":
            config = AppConfig()
        else:
            logger.error(str(e))
            sys.exit(1)

    commands = {
        "auth": cmd_auth,
        "scan": cmd_scan,
        "report": cmd_report,
    }

    commands[args.command](args, config)


if __name__ == "__main__":
    main()
