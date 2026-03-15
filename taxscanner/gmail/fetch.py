"""Download full messages and attachments from Gmail."""

import base64

from googleapiclient.errors import HttpError
from tqdm import tqdm

from taxscanner.utils.cache import Cache
from taxscanner.utils.logging import get_logger

logger = get_logger(__name__)


def _decode_body(data: str) -> str:
    """Decode base64url-encoded body data to UTF-8 text."""
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")


def _get_header(headers: list[dict], name: str) -> str:
    """Get a header value by name from Gmail message headers."""
    for header in headers:
        if header["name"].lower() == name.lower():
            return header["value"]
    return ""


def _extract_parts(parts: list[dict], service, message_id: str) -> tuple[str, str, list[dict]]:
    """Recursively extract body text and attachments from message parts."""
    html_body = ""
    plain_body = ""
    attachments = []

    for part in parts:
        mime_type = part.get("mimeType", "")
        filename = part.get("filename", "")

        # Recurse into multipart
        if mime_type.startswith("multipart/") and "parts" in part:
            h, p, a = _extract_parts(part["parts"], service, message_id)
            html_body += h
            plain_body += p
            attachments.extend(a)
            continue

        body = part.get("body", {})

        # Attachment
        if filename and body.get("attachmentId"):
            att_data = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=body["attachmentId"])
                .execute()
            )
            data = base64.urlsafe_b64decode(att_data["data"])
            attachments.append({
                "filename": filename,
                "mime_type": mime_type,
                "data": data,
            })
        # Body content
        elif body.get("data"):
            decoded = _decode_body(body["data"])
            if mime_type == "text/html":
                html_body += decoded
            elif mime_type == "text/plain":
                plain_body += decoded

    return html_body, plain_body, attachments


def fetch_single_message(service, message_id: str) -> dict:
    """Fetch a single Gmail message with full content and attachments."""
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )

    headers = msg.get("payload", {}).get("headers", [])
    subject = _get_header(headers, "Subject")
    sender = _get_header(headers, "From")
    date = _get_header(headers, "Date")

    # Extract body and attachments
    payload = msg.get("payload", {})
    html_body = ""
    plain_body = ""
    attachments = []

    if "parts" in payload:
        html_body, plain_body, attachments = _extract_parts(
            payload["parts"], service, message_id
        )
    elif payload.get("body", {}).get("data"):
        decoded = _decode_body(payload["body"]["data"])
        mime_type = payload.get("mimeType", "text/plain")
        if mime_type == "text/html":
            html_body = decoded
        else:
            plain_body = decoded

    return {
        "id": message_id,
        "subject": subject,
        "from": sender,
        "date": date,
        "html_body": html_body,
        "plain_body": plain_body,
        "attachments": attachments,
    }


def fetch_messages(service, message_ids: list[str], cache: Cache, config) -> list[dict]:
    """Fetch all messages, using cache where available."""
    messages = []
    to_fetch = []

    for mid in message_ids:
        cached = cache.get_message(mid)
        if cached:
            messages.append(cached)
        else:
            to_fetch.append(mid)

    logger.info(f"Cache hits: {len(messages)}, to fetch: {len(to_fetch)}")

    for mid in tqdm(to_fetch, desc="Fetching emails"):
        try:
            msg = fetch_single_message(service, mid)
            # Cache without binary attachment data (store metadata only)
            cache_msg = {
                k: v for k, v in msg.items() if k != "attachments"
            }
            cache_msg["attachment_names"] = [
                a["filename"] for a in msg.get("attachments", [])
            ]
            cache.save_message(mid, cache_msg)
            messages.append(msg)
        except (HttpError, TimeoutError, ConnectionError) as e:
            logger.warning(f"Failed to fetch message {mid}: {e}")

    return messages
