"""Load configuration from config.yaml and .env files."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass
class GmailConfig:
    max_results: int = 500
    batch_size: int = 50
    search_keywords: list[str] = field(default_factory=lambda: [
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
    ])


@dataclass
class ClassifierConfig:
    model: str = "claude-sonnet-4-20250514"
    vision_model: str = "claude-sonnet-4-20250514"
    batch_size: int = 10
    max_tokens: int = 4096


@dataclass
class ReportConfig:
    output_dir: str = "reports"


@dataclass
class BusinessConfig:
    name: str = ""
    code: str = ""
    description: str = ""


@dataclass
class AppConfig:
    businesses: list[BusinessConfig] = field(default_factory=list)
    categories: list[str] = field(default_factory=lambda: [
        "Software & Subscriptions",
        "Cloud & Hosting",
        "Office Supplies",
        "Equipment & Hardware",
        "Professional Services",
        "Property Maintenance & Repairs",
        "Property Insurance",
        "Utilities",
        "Travel & Transportation",
        "Advertising & Marketing",
        "Education & Training",
        "Meals",
        "Other",
    ])
    gmail: GmailConfig = field(default_factory=GmailConfig)
    classifier: ClassifierConfig = field(default_factory=ClassifierConfig)
    report: ReportConfig = field(default_factory=ReportConfig)

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like access for backward compatibility during migration."""
        return getattr(self, key, default)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _build_config(data: dict) -> AppConfig:
    """Build an AppConfig from a raw dict."""
    businesses = [
        BusinessConfig(**biz) if isinstance(biz, dict) else biz
        for biz in data.get("businesses", [])
    ]

    gmail_data = data.get("gmail", {})
    gmail = GmailConfig(
        max_results=gmail_data.get("max_results", 500),
        batch_size=gmail_data.get("batch_size", 50),
        search_keywords=gmail_data.get("search_keywords", GmailConfig().search_keywords),
    )

    classifier_data = data.get("classifier", {})
    classifier = ClassifierConfig(
        model=classifier_data.get("model", "claude-sonnet-4-20250514"),
        vision_model=classifier_data.get("vision_model", "claude-sonnet-4-20250514"),
        batch_size=classifier_data.get("batch_size", 10),
        max_tokens=classifier_data.get("max_tokens", 4096),
    )

    report_data = data.get("report", {})
    report = ReportConfig(
        output_dir=report_data.get("output_dir", "reports"),
    )

    categories = data.get("categories", AppConfig().categories)

    return AppConfig(
        businesses=businesses,
        categories=categories,
        gmail=gmail,
        classifier=classifier,
        report=report,
    )


DEFAULT_CONFIG_DICT = {
    "businesses": [],
    "categories": [
        "Software & Subscriptions",
        "Cloud & Hosting",
        "Office Supplies",
        "Equipment & Hardware",
        "Professional Services",
        "Property Maintenance & Repairs",
        "Property Insurance",
        "Utilities",
        "Travel & Transportation",
        "Advertising & Marketing",
        "Education & Training",
        "Meals",
        "Other",
    ],
    "gmail": {
        "max_results": 500,
        "batch_size": 50,
    },
    "classifier": {
        "model": "claude-sonnet-4-20250514",
        "vision_model": "claude-sonnet-4-20250514",
        "batch_size": 10,
        "max_tokens": 4096,
    },
    "report": {
        "output_dir": "reports",
    },
}


def load_config(config_path: str | None = None) -> AppConfig:
    """Load configuration from config.yaml, merging with defaults.

    Also loads .env file for environment variables.
    """
    load_dotenv()

    config_dict = DEFAULT_CONFIG_DICT.copy()

    # Try to find config file
    if config_path is None:
        for candidate in ["config.yaml", "config.yml"]:
            if Path(candidate).exists():
                config_path = candidate
                break

    if config_path and Path(config_path).exists():
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f) or {}
        config_dict = _deep_merge(config_dict, user_config)

    # Validate required env vars
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set. Add it to .env or set as environment variable."
        )

    return _build_config(config_dict)
