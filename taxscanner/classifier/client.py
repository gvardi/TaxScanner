"""Anthropic SDK wrapper for expense classification."""

import json

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from taxscanner.classifier.models import ClassificationResult
from taxscanner.classifier.prompts import build_system_prompt, build_user_prompt
from taxscanner.config import AppConfig
from taxscanner.extraction.models import ExtractedInvoice
from taxscanner.utils.cache import Cache
from taxscanner.utils.logging import get_logger

logger = get_logger(__name__)


def _build_result(inv: ExtractedInvoice, raw: dict) -> ClassificationResult:
    """Build a ClassificationResult from an invoice and raw API response dict."""
    return ClassificationResult(
        message_id=inv.message_id,
        subject=inv.subject,
        sender=inv.sender,
        date=inv.date,
        gmail_link=inv.gmail_link,
        source=inv.source,
        expense_type=raw.get("expense_type", "uncertain"),
        business=raw.get("business", ""),
        category=raw.get("category", "Other"),
        vendor=raw.get("vendor", "Unknown"),
        amount=raw.get("amount", "Unknown"),
        invoice_date=raw.get("invoice_date", "Unknown"),
        confidence=float(raw.get("confidence", 0.5)),
        reasoning=raw.get("reasoning", ""),
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=60))
def _classify_batch(
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int,
    system_prompt: str,
    invoices: list[ExtractedInvoice],
) -> list[dict]:
    """Send a batch of invoices to Claude for classification."""
    user_prompt = build_user_prompt(invoices)

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    response_text = response.content[0].text.strip()

    # Extract JSON from response (handle markdown code blocks)
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        # Remove first and last lines (``` markers)
        json_lines = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```") and not in_block:
                in_block = True
                continue
            elif line.strip() == "```" and in_block:
                break
            elif in_block:
                json_lines.append(line)
        response_text = "\n".join(json_lines)

    results = json.loads(response_text)

    if not isinstance(results, list):
        raise ValueError(f"Expected JSON array, got {type(results)}")

    return results


def classify_invoices(
    invoices: list[ExtractedInvoice],
    cache: Cache,
    config: AppConfig,
) -> list[ClassificationResult]:
    """Classify all invoices using Claude AI in batches."""
    client = anthropic.Anthropic()
    model = config.classifier.model
    max_tokens = config.classifier.max_tokens
    batch_size = config.classifier.batch_size
    system_prompt = build_system_prompt(config)

    results: list[ClassificationResult] = []
    to_classify: list[ExtractedInvoice] = []

    # Check cache first
    for inv in invoices:
        cached = cache.get_classification(inv.message_id)
        if cached:
            results.append(ClassificationResult.from_dict(cached))
        else:
            to_classify.append(inv)

    logger.info(f"Classification cache hits: {len(results)}, to classify: {len(to_classify)}")

    # Process in batches
    from tqdm import tqdm

    for i in tqdm(range(0, len(to_classify), batch_size), desc="Classifying"):
        batch = to_classify[i : i + batch_size]

        try:
            raw_results = _classify_batch(client, model, max_tokens, system_prompt, batch)

            for raw in raw_results:
                idx = raw.get("index", 0)
                if idx >= len(batch):
                    logger.warning(f"Classification index {idx} out of range, skipping")
                    continue

                inv = batch[idx]
                classification = _build_result(inv, raw)

                cache.save_classification(inv.message_id, classification.to_dict())
                results.append(classification)

        except (json.JSONDecodeError, anthropic.APIError, ValueError, KeyError) as e:
            logger.error(f"Batch classification failed: {e}")
            # Create uncertain results for failed batch
            for inv in batch:
                classification = _build_result(inv, {
                    "confidence": 0.0,
                    "reasoning": f"Classification failed: {e}",
                })
                results.append(classification)

    return results
