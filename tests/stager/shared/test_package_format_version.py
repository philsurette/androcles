from __future__ import annotations

import pytest

from stager.shared.package_format_version import (
    FormatVersionDecision,
    PackageFormatVersion,
)


def test_parse_package_format_version() -> None:
    version = PackageFormatVersion.parse("1.2.3")

    assert version.major == 1
    assert version.minor == 2
    assert version.patch == 3
    assert str(version) == "1.2.3"


@pytest.mark.parametrize("value", ["1", "1.2", "1.2.3.4", "v1.2.3", "1.02.3"])
def test_parse_rejects_invalid_package_format_versions(value: str) -> None:
    with pytest.raises(ValueError):
        PackageFormatVersion.parse(value)


def test_manifest_format_version_takes_precedence() -> None:
    version = PackageFormatVersion.from_manifest({"schema_version": 1, "format_version": "1.4.0"})

    assert version == PackageFormatVersion(1, 4, 0)


def test_manifest_schema_version_maps_to_initial_format_version() -> None:
    version = PackageFormatVersion.from_manifest({"schema_version": 1})

    assert version == PackageFormatVersion(1, 0, 0)


def test_manifest_missing_version_rejects() -> None:
    with pytest.raises(ValueError):
        PackageFormatVersion.from_manifest({})


@pytest.mark.parametrize(
    ("package", "supported", "decision"),
    [
        (PackageFormatVersion(1, 0, 0), PackageFormatVersion(1, 0, 0), FormatVersionDecision.ACCEPT),
        (PackageFormatVersion(1, 0, 1), PackageFormatVersion(1, 0, 0), FormatVersionDecision.ACCEPT),
        (PackageFormatVersion(1, 1, 0), PackageFormatVersion(1, 0, 0), FormatVersionDecision.WARN),
        (PackageFormatVersion(2, 0, 0), PackageFormatVersion(1, 0, 0), FormatVersionDecision.REJECT),
        (PackageFormatVersion(0, 9, 0), PackageFormatVersion(1, 0, 0), FormatVersionDecision.REJECT),
    ],
)
def test_format_version_compatibility_decision(
    package: PackageFormatVersion,
    supported: PackageFormatVersion,
    decision: FormatVersionDecision,
) -> None:
    assert package.compatibility_with(supported) == decision
