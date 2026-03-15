"""JSON-based cache for resume/re-run support."""

import json
from pathlib import Path

from taxscanner.utils.logging import get_logger

logger = get_logger(__name__)

CACHE_DIR = ".cache"


class Cache:
    """Simple JSON file cache organized by data type."""

    def __init__(self, cache_dir: str = CACHE_DIR):
        self.base = Path(cache_dir)
        self.messages_dir = self.base / "messages"
        self.extractions_dir = self.base / "extractions"
        self.classifications_dir = self.base / "classifications"
        self.meta_dir = self.base / "meta"

        for d in [self.messages_dir, self.extractions_dir, self.classifications_dir, self.meta_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _read(self, path: Path) -> dict | None:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _write(self, path: Path, data: dict):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    # Messages
    def get_message(self, message_id: str) -> dict | None:
        return self._read(self.messages_dir / f"{message_id}.json")

    def save_message(self, message_id: str, data: dict):
        self._write(self.messages_dir / f"{message_id}.json", data)

    # Extractions
    def get_extraction(self, message_id: str) -> dict | None:
        return self._read(self.extractions_dir / f"{message_id}.json")

    def save_extraction(self, message_id: str, data: dict):
        self._write(self.extractions_dir / f"{message_id}.json", data)

    # Classifications
    def get_classification(self, message_id: str) -> dict | None:
        return self._read(self.classifications_dir / f"{message_id}.json")

    def save_classification(self, message_id: str, data: dict):
        self._write(self.classifications_dir / f"{message_id}.json", data)

    def get_all_classifications(self) -> list[dict]:
        results = []
        for f in self.classifications_dir.glob("*.json"):
            data = self._read(f)
            if data:
                results.append(data)
        return results

    # Skipped
    def get_skipped(self) -> list[dict] | None:
        return self._read(self.meta_dir / "skipped.json")

    def save_skipped(self, data: list[dict]):
        self._write(self.meta_dir / "skipped.json", data)
