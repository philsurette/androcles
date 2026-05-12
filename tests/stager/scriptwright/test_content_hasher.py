from __future__ import annotations

from stager.scriptwright.content_hasher import ContentHasher


def test_hash_ignores_insignificant_whitespace() -> None:
    hasher = ContentHasher()

    first = hasher.hash_line("role", "I will never submit.", ["CAPTAIN"])
    second = hasher.hash_line("role", "I will   never\nsubmit.", ["CAPTAIN"])

    assert first == second
    assert first.startswith("sha256:")


def test_hash_changes_when_meaningful_content_changes() -> None:
    hasher = ContentHasher()

    first = hasher.hash_segment("speech", "I will never submit.", "CAPTAIN")
    second = hasher.hash_segment("speech", "I will always submit.", "CAPTAIN")
    third = hasher.hash_segment("speech", "I will never submit.", "MEGAERA")

    assert first != second
    assert first != third
