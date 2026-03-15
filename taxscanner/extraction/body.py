"""HTML/plain-text email body parsing."""

from bs4 import BeautifulSoup

from taxscanner.utils.logging import get_logger

logger = get_logger(__name__)

MIN_BODY_LENGTH = 20
MAX_BODY_LENGTH = 5000


def _html_to_text(html: str) -> str:
    """Convert HTML to clean text using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for element in soup(["script", "style", "head"]):
        element.decompose()

    text = soup.get_text(separator="\n")

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    text = "\n".join(line for line in lines if line)

    return text


def extract_from_body(msg: dict) -> str | None:
    """Extract meaningful text from email body.

    Prefers HTML (converted to text) over plain text for better structure.
    Returns extracted text or None if body is empty/uninformative.
    """
    html_body = msg.get("html_body", "")
    plain_body = msg.get("plain_body", "")

    text = ""
    if html_body:
        text = _html_to_text(html_body)
    elif plain_body:
        text = plain_body.strip()

    if not text or len(text) < MIN_BODY_LENGTH:
        return None

    if len(text) > MAX_BODY_LENGTH:
        text = text[:MAX_BODY_LENGTH] + "\n... [truncated]"

    return text
