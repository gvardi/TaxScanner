"""Gmail query builder and paginated search."""

from taxscanner.utils.logging import get_logger

logger = get_logger(__name__)

GMAIL_PAGE_SIZE = 100


def build_query(year: int, keywords: list[str] | None = None) -> str:
    """Build a Gmail search query for invoice-related emails in a given year."""
    if keywords is None:
        keywords = [
            "invoice",
            "receipt",
            "payment confirmation",
            "order confirmation",
            "billing statement",
            "shipping confirmation",
            "your order",
            "subscription",
            "renewal",
            "purchase",
            "transaction",
        ]

    keyword_clause = " OR ".join(
        f'"{kw}"' if " " in kw else kw for kw in keywords
    )

    query = f"({keyword_clause}) after:{year}/01/01 before:{year + 1}/01/01"
    return query


def search_emails(service, year: int, config) -> list[str]:
    """Search Gmail for invoice-related emails and return message IDs."""
    keywords = (
        config.gmail.search_keywords
        if hasattr(config, "gmail") and hasattr(config.gmail, "search_keywords")
        else None
    )
    query = build_query(year, keywords)
    max_results = (
        config.gmail.max_results
        if hasattr(config, "gmail") and hasattr(config.gmail, "max_results")
        else config.get("gmail", {}).get("max_results", 500)
    )

    logger.info(f"Gmail query: {query}")

    message_ids = []
    page_token = None

    while True:
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=min(max_results - len(message_ids), GMAIL_PAGE_SIZE),
                pageToken=page_token,
            )
            .execute()
        )

        messages = results.get("messages", [])
        message_ids.extend(msg["id"] for msg in messages)

        logger.debug(f"Fetched page with {len(messages)} results (total: {len(message_ids)})")

        page_token = results.get("nextPageToken")
        if not page_token or len(message_ids) >= max_results:
            break

    return message_ids[:max_results]
