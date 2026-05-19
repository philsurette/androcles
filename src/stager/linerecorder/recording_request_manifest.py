from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any


@dataclass
class RecordingRequestMetadata:
    id: str
    kind: str
    created_at: str
    created_by: str = "stager"
    notes: str | None = None
    production_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "created_at": self.created_at,
            "created_by": self.created_by,
        }
        if self.production_version is not None:
            data["production_version"] = self.production_version
        if self.notes is not None:
            data["notes"] = self.notes
        return data


@dataclass
class RecordingRequestPlay:
    id: str
    title: str
    version: str | None = None
    buildId: str | None = None
    buildTimestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "id": self.id,
            "title": self.title,
        }
        if self.version is not None:
            data["version"] = self.version
        if self.buildId is not None:
            data["buildId"] = self.buildId
        if self.buildTimestamp is not None:
            data["buildTimestamp"] = self.buildTimestamp
        return data


@dataclass
class RecordingRequestRole:
    id: str
    display_name: str
    actor_id: str | None = None
    actor_display_name: str | None = None
    actor_email: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "display_name": self.display_name,
        }
        if self.actor_id is not None:
            actor: dict[str, Any] = {"id": self.actor_id}
            if self.actor_display_name is not None:
                actor["display_name"] = self.actor_display_name
            if self.actor_email is not None:
                actor["email"] = self.actor_email
            data["actor"] = actor
        return data


@dataclass
class RecordingRequestProduction:
    source: str
    version: str | None = None
    sequence: int | None = None
    publication_id: str | None = None
    parent_version: str | None = None
    published_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"source": self.source}
        if self.version is not None:
            data["version"] = self.version
        if self.sequence is not None:
            data["sequence"] = self.sequence
        if self.publication_id is not None:
            data["publication_id"] = self.publication_id
        if self.parent_version is not None:
            data["parent_version"] = self.parent_version
        if self.published_at is not None:
            data["published_at"] = self.published_at
        return data


@dataclass
class RecordingPreferences:
    preferred_sample_rate_hz: int = 48000
    preferred_channels: int = 1
    source_format: str = "wav"

    def to_dict(self) -> dict[str, Any]:
        return {
            "preferred_sample_rate_hz": self.preferred_sample_rate_hz,
            "preferred_channels": self.preferred_channels,
            "source_format": self.source_format,
        }


@dataclass
class RecordingRequestBlocking:
    id: str
    targets: list[str]
    text: str
    placement: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "targets": list(self.targets),
            "text": self.text,
            "placement": self.placement,
        }


@dataclass
class RecordingRequestItem:
    id: str
    line_id: str
    block_id: str
    segment_id: str
    sequence: int
    display_text: str
    segment_text: str
    output_path: str
    line_content_hash: str | None = None
    segment_content_hash: str | None = None
    cue_text: str | None = None
    cue_speaker: str | None = None
    previous_text: str | None = None
    previous_speaker: str | None = None
    next_text: str | None = None
    next_speaker: str | None = None
    section_id: str | None = None
    section_title: str | None = None
    scene_heading: str | None = None
    stage_directions: list[str] = field(default_factory=list)
    blocking: list[RecordingRequestBlocking] = field(default_factory=list)
    reason: str | None = None
    notes: str | None = None
    previous_recording: str | None = None
    cue_audio: str | None = None
    changed: bool | None = None
    target_duration_ms: int | None = None
    target_hesitation_ms: int | None = None
    simultaneous: bool = False

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "line_id": self.line_id,
            "block_id": self.block_id,
            "segment_id": self.segment_id,
            "sequence": self.sequence,
            "display_text": self.display_text,
            "segment_text": self.segment_text,
            "output_path": self.output_path,
        }
        self._put_optional(data, "line_content_hash", self.line_content_hash)
        self._put_optional(data, "segment_content_hash", self.segment_content_hash)
        self._put_optional(data, "cue_text", self.cue_text)
        self._put_optional(data, "cue_speaker", self.cue_speaker)
        self._put_optional(data, "previous_text", self.previous_text)
        self._put_optional(data, "previous_speaker", self.previous_speaker)
        self._put_optional(data, "next_text", self.next_text)
        self._put_optional(data, "next_speaker", self.next_speaker)
        self._put_optional(data, "section_id", self.section_id)
        self._put_optional(data, "section_title", self.section_title)
        self._put_optional(data, "scene_heading", self.scene_heading)
        if self.stage_directions:
            data["stage_directions"] = list(self.stage_directions)
        if self.blocking:
            data["blocking"] = [blocking.to_dict() for blocking in self.blocking]
        self._put_optional(data, "reason", self.reason)
        self._put_optional(data, "notes", self.notes)
        self._put_optional(data, "previous_recording", self.previous_recording)
        self._put_optional(data, "cue_audio", self.cue_audio)
        self._put_optional(data, "changed", self.changed)
        self._put_optional(data, "target_duration_ms", self.target_duration_ms)
        self._put_optional(data, "target_hesitation_ms", self.target_hesitation_ms)
        if self.simultaneous:
            data["simultaneous"] = True
        return data

    def _put_optional(self, data: dict[str, Any], key: str, value: Any) -> None:
        if value is not None:
            data[key] = value


@dataclass
class RecordingRequestManifest:
    request: RecordingRequestMetadata
    play: RecordingRequestPlay
    role: RecordingRequestRole
    recording: RecordingPreferences
    items: list[RecordingRequestItem]
    production: RecordingRequestProduction
    schema_version: int = 1
    format_version: str = "1.0.0"
    package_type: str = "recording_request"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "format_version": self.format_version,
            "package_type": self.package_type,
            "request": self.request.to_dict(),
            "play": self.play.to_dict(),
            "production": self.production.to_dict(),
            "role": self.role.to_dict(),
            "recording": self.recording.to_dict(),
            "items": [item.to_dict() for item in self.items],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=False) + "\n"
