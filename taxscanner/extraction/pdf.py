"""PDF text extraction using pdfplumber."""

import io

import pdfplumber

from taxscanner.utils.logging import get_logger

logger = get_logger(__name__)


def extract_from_pdf(pdf_data: bytes, filename: str) -> str | None:
    """Extract text from a PDF attachment.

    Returns extracted text or None if extraction fails.
    """
    try:
        with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text.strip())

            if pages_text:
                result = "\n\n".join(pages_text)
                logger.debug(f"Extracted {len(result)} chars from {filename}")
                return result

        logger.debug(f"No text extracted from {filename} (may be image-based PDF)")
        return None

    except Exception as e:
        logger.warning(f"PDF extraction failed for {filename}: {e}")
        return None
