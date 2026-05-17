from __future__ import annotations

import pytest

from stager.production_publication.production_version import ProductionVersion, PublicationIdGenerator


def test_parse_production_version() -> None:
    version = ProductionVersion.parse("7@k9f4p2x8m1qd")

    assert version.sequence == 7
    assert version.publication_id == "k9f4p2x8m1qd"
    assert str(version) == "7@k9f4p2x8m1qd"
    assert version.history_directory_name == "0007-k9f4p2x8m1qd"


def test_create_next_version_after_parent() -> None:
    parent = ProductionVersion.parse("6@h7p2v9c4t6ra")

    version = ProductionVersion.next_after(parent, "k9f4p2x8m1qd")

    assert str(version) == "7@k9f4p2x8m1qd"


def test_create_initial_version() -> None:
    version = ProductionVersion.next_after(None, "k9f4p2x8m1qd")

    assert str(version) == "1@k9f4p2x8m1qd"


def test_lineage_helpers() -> None:
    parent = ProductionVersion.parse("6@h7p2v9c4t6ra")
    child = ProductionVersion.parse("7@k9f4p2x8m1qd")
    fork = ProductionVersion.parse("7@z8n3d5q1w6te")

    assert child.is_successor_of(parent)
    assert child.same_sequence_different_publication_id(fork)
    assert not child.same_sequence_different_publication_id(child)


@pytest.mark.parametrize(
    "value",
    [
        "v0007",
        "7",
        "0@k9f4p2x8m1qd",
        "x@k9f4p2x8m1qd",
        "7@",
        "7@bad id",
    ],
)
def test_parse_rejects_invalid_or_legacy_versions(value: str) -> None:
    with pytest.raises(ValueError):
        ProductionVersion.parse(value)


def test_publication_id_generator_returns_short_base32_token() -> None:
    generated = PublicationIdGenerator().generate()

    assert len(generated) == 12
    assert generated.isalnum()
    assert generated == generated.lower()
