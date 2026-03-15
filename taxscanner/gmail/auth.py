"""OAuth2 authentication flow and token management for Gmail API."""

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def authenticate(
    credentials_path: str | None = None,
    token_path: str | None = None,
) -> object:
    """Authenticate with Gmail API and return service object.

    On first run, opens a browser for OAuth consent.
    Subsequent runs use the cached token.
    """
    credentials_path = credentials_path or os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
    token_path = token_path or os.getenv("GMAIL_TOKEN_PATH", "token.json")

    creds = None

    # Load existing token
    if Path(token_path).exists():
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except (ValueError, KeyError, json.JSONDecodeError):
            creds = None

    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not Path(credentials_path).exists():
                raise FileNotFoundError(
                    f"Gmail credentials file not found: {credentials_path}\n"
                    "Download it from Google Cloud Console → APIs & Services → Credentials"
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for future runs
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)
