from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PublishedLine:
    id: str
    kind: str
    text: str
    line_no: int
    content_hash: str
    roles: tuple[str, ...] = ()
    targets: tuple[str, ...] = ()
    speech_hash: str | None = None
    context_hash: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "text": self.text,
            "line_no": self.line_no,
            "content_hash": self.content_hash,
            **({"roles": list(self.roles)} if self.roles else {}),
            **({"targets": list(self.targets)} if self.targets else {}),
            **({"speech_hash": self.speech_hash} if self.speech_hash is not None else {}),
            **({"context_hash": self.context_hash} if self.context_hash is not None else {}),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PublishedLine":
        return cls(
            id=data["id"],
            kind=data["kind"],
            text=data["text"],
            line_no=data["line_no"],
            content_hash=data["content_hash"],
            roles=tuple(data.get("roles", [])),
            targets=tuple(data.get("targets", [])),
            speech_hash=data.get("speech_hash"),
            context_hash=data.get("context_hash"),
        )
