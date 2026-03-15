"""Image OCR via Claude Vision (multimodal API)."""

import base64

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from taxscanner.utils.logging import get_logger

logger = get_logger(__name__)

# Map file extensions to media types
MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
def _call_vision_api(client: anthropic.Anthropic, model: str, image_b64: str, media_type: str) -> str:
    """Call Claude Vision API with retry."""
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract all text from this image. This is likely an invoice, "
                            "receipt, or billing document. Include all amounts, dates, "
                            "vendor names, line items, and any other relevant information. "
                            "Return the extracted text in a structured format."
                        ),
                    },
                ],
            }
        ],
    )
    return response.content[0].text


def extract_from_image(
    image_data: bytes, filename: str, config, *, client: anthropic.Anthropic | None = None
) -> str | None:
    """Extract text from an image using Claude Vision.

    Returns extracted text or None if extraction fails.
    """
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    media_type = MEDIA_TYPES.get(ext)
    if not media_type:
        logger.debug(f"Unsupported image format: {filename}")
        return None

    try:
        client = client or anthropic.Anthropic()
        model = (
            config.classifier.vision_model
            if hasattr(config, "classifier") and hasattr(config.classifier, "vision_model")
            else config.get("classifier", {}).get("vision_model", "claude-sonnet-4-20250514")
        )
        image_b64 = base64.standard_b64encode(image_data).decode("utf-8")

        result = _call_vision_api(client, model, image_b64, media_type)
        logger.debug(f"OCR extracted {len(result)} chars from {filename}")
        return result

    except anthropic.APIError as e:
        logger.warning(f"Vision OCR failed for {filename}: {e}")
        return None
