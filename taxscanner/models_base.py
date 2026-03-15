"""Shared base mixin for dataclass serialization."""

from dataclasses import asdict


class DictMixin:
    """Mixin providing to_dict/from_dict for dataclasses."""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DictMixin":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
