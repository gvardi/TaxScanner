"""Prompt templates for Claude AI classification."""

from taxscanner.extraction.models import ExtractedInvoice

MAX_INVOICE_TEXT_LENGTH = 3000


def build_system_prompt(config) -> str:
    """Build the system prompt for expense classification."""
    businesses = config.businesses if hasattr(config, "businesses") else config.get("businesses", [])
    categories = config.categories if hasattr(config, "categories") else config.get("categories", [])

    business_descriptions = ""
    for biz in businesses:
        name = biz.name if hasattr(biz, "name") else biz["name"]
        code = biz.code if hasattr(biz, "code") else biz["code"]
        desc = biz.description if hasattr(biz, "description") else biz["description"]
        business_descriptions += f"\n- **{name}** ({code}): {desc}"

    category_list = "\n".join(f"- {cat}" for cat in categories)

    return f"""You are an expert accountant and expense classifier. Your job is to analyze invoice/receipt data extracted from emails and classify each one as a business expense, personal expense, or uncertain.

## Businesses
The user operates the following businesses:{business_descriptions}

## Expense Categories
{category_list}

## Classification Rules
1. Determine if the expense is **business** or **personal** or **uncertain**
2. If business: assign it to the correct business (or "Shared" if it benefits both)
3. Pick the most appropriate category from the list above
4. Extract the vendor name, total amount, and invoice date
5. Provide a confidence score (0.0 to 1.0) and brief reasoning

## Important Notes
- Shipping confirmations and order updates count as expenses — the email confirms a purchase was made
- Look for amounts in the text; if no clear amount is found, set amount to "Unknown"
- If the date is ambiguous, use the email date
- Personal purchases (clothing, food delivery, entertainment, personal Amazon orders) should be classified as "personal"
- When uncertain, err on the side of "uncertain" rather than guessing

## Output Format
Respond with a JSON array. Each element must have exactly these fields:
```json
{{
  "index": 0,
  "expense_type": "business|personal|uncertain",
  "business": "Real Estate|Software/IT|Shared|",
  "category": "category name from list",
  "vendor": "vendor name",
  "amount": "$XX.XX or Unknown",
  "invoice_date": "YYYY-MM-DD or Unknown",
  "confidence": 0.85,
  "reasoning": "Brief explanation"
}}
```

Respond ONLY with the JSON array, no other text."""


def build_user_prompt(invoices: list[ExtractedInvoice]) -> str:
    """Build the user prompt with invoice data for classification."""
    parts = []
    for i, inv in enumerate(invoices):
        parts.append(
            f"--- Invoice {i} ---\n"
            f"Subject: {inv.subject}\n"
            f"From: {inv.sender}\n"
            f"Date: {inv.date}\n"
            f"Source: {inv.source}\n\n"
            f"{inv.text[:MAX_INVOICE_TEXT_LENGTH]}"
        )

    return "\n\n" + "\n\n".join(parts)
