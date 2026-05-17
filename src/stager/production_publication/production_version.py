from __future__ import annotations

from dataclasses import dataclass
import secrets


_PUBLICATION_ID_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"
_PUBLICATION_ID_LENGTH = 12
_PUBLICATION_ID_BITS = 60


@dataclass(frozen=True, order=True)
class ProductionVersion:
    sequence: int
    publication_id: str

    @classmethod
    def parse(cls, value: str) -> "ProductionVersion":
        raw_value = value.strip()
        if raw_value.startswith("v") and raw_value[1:].isdigit():
            raise ValueError(f"Legacy production version is not supported: {value}")
        sequence_text, separator, publication_id = raw_value.partition("@")
        if separator != "@":
            raise ValueError(f"Production version must use '<sequence>@<publication-id>': {value}")
        if not sequence_text.isdigit():
            raise ValueError(f"Production version sequence must be a positive integer: {value}")
        sequence = int(sequence_text)
        if sequence <= 0:
            raise ValueError(f"Production version sequence must be a positive integer: {value}")
        if not publication_id:
            raise ValueError(f"Production version publication id is required: {value}")
        if not publication_id.replace("-", "").isalnum():
            raise ValueError(f"Production version publication id must be alphanumeric or hyphenated: {value}")
        return cls(sequence=sequence, publication_id=publication_id)

    @classmethod
    def next_after(cls, parent: "ProductionVersion | None", publication_id: str) -> "ProductionVersion":
        sequence = 1 if parent is None else parent.sequence + 1
        return cls(sequence=sequence, publication_id=publication_id)

    @property
    def history_directory_name(self) -> str:
        return f"{self.sequence:04d}-{self.publication_id}"

    def is_successor_of(self, parent: "ProductionVersion") -> bool:
        return self.sequence == parent.sequence + 1

    def same_sequence_different_publication_id(self, other: "ProductionVersion") -> bool:
        return self.sequence == other.sequence and self.publication_id != other.publication_id

    def __str__(self) -> str:
        return f"{self.sequence}@{self.publication_id}"


class PublicationIdGenerator:
    def generate(self) -> str:
        value = secrets.randbits(_PUBLICATION_ID_BITS)
        chars: list[str] = []
        for _ in range(_PUBLICATION_ID_LENGTH):
            chars.append(_PUBLICATION_ID_ALPHABET[value & 31])
            value >>= 5
        return "".join(reversed(chars))
