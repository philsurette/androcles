from __future__ import annotations

import pytest

from stager.scriptwright.production_script import ProductionEntryKind
from stager.scriptwright.production_script_parser import ProductionScriptParser
from stager.shared.paths import PathConfig


def test_parse_locked_production_markdown():
    script = ProductionScriptParser().parse_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
## I.1-0 SCENE I
I.1-1 @description: A dusty Roman road.
I.1-2 CAPTAIN: I will go (_draws sword_) if I must.
I.1-3 CAPTAIN, MEGAERA: Together.
I.1-4 @direction: The soldiers move aside.
I.1-5 /CAPTAIN: crosses downstage.
"""
    )

    assert script.locked
    assert [entry.kind for entry in script.entries] == [
        ProductionEntryKind.HEADING,
        ProductionEntryKind.HEADING,
        ProductionEntryKind.DESCRIPTION,
        ProductionEntryKind.ROLE,
        ProductionEntryKind.ROLE,
        ProductionEntryKind.DIRECTION,
        ProductionEntryKind.BLOCKING,
    ]
    assert script.entries[1].production_id == "I.1-0"
    assert script.entries[3].roles == ("CAPTAIN",)
    assert script.entries[4].roles == ("CAPTAIN", "MEGAERA")
    assert script.entries[6].targets == ("CAPTAIN",)


def test_parse_markdown_list_production_entries():
    script = ProductionScriptParser().parse_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I

- I-1 @description: A dusty Roman road.
- I-2 CAPTAIN: I will go.
- I-3 /CAPTAIN: crosses downstage.
"""
    )

    assert [entry.production_id for entry in script.entries] == ["I-0", "I-1", "I-2", "I-3"]
    assert [entry.kind for entry in script.entries] == [
        ProductionEntryKind.HEADING,
        ProductionEntryKind.DESCRIPTION,
        ProductionEntryKind.ROLE,
        ProductionEntryKind.BLOCKING,
    ]


def test_parse_inline_blocking_targets():
    script = ProductionScriptParser().parse_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

I-1 CAPTAIN: I will go (_/MEGAERA, CAPTAIN: clasp hands_) if I must.
"""
    )

    assert script.entries[0].roles == ("CAPTAIN",)


def test_parse_draft_production_markdown_without_ids():
    script = ProductionScriptParser().parse_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: draft

# ACT I
@description: A dusty Roman road.
CAPTAIN: I will never submit.
"""
    )

    assert not script.locked
    assert script.entries[0].production_id is None
    assert script.entries[1].production_id is None
    assert script.entries[2].roles == ("CAPTAIN",)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (
            """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# ACT I
""",
            "missing a production id",
        ),
        (
            """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
I-0 @direction: duplicate
""",
            "Duplicate production id",
        ),
        (
            """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

I-1 CAPTAIN: I will go (_now.
""",
            "Unclosed inline direction",
        ),
        (
            """// script_format: quince-production-v1
// source_kind: production
// production_ids: frozen

# I-0 ACT I
""",
            "Unknown production_ids value",
        ),
        (
            """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

p-0 PROLOGUE
""",
            "Malformed production id",
        ),
        (
            """// script_format: quince-production-v1
// source_kind: production
// production_ids: draft

CAPTAIN: One line.
  continued line.
""",
            "Multiline script entries are not supported",
        ),
        (
            """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

I-1 /CAPTAIN, *: bad target list.
""",
            "Blocking wildcard cannot be combined",
        ),
    ],
)
def test_reject_malformed_production_markdown(text, message):
    with pytest.raises(RuntimeError, match=message):
        ProductionScriptParser().parse_text(text)


def test_parse_named_structural_production_ids():
    script = ProductionScriptParser().parse_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# INT-0 INTERLUDE
INT-1 CHORUS: Between the acts.
E-1 CHORUS: The end.
"""
    )

    assert [entry.production_id for entry in script.entries] == ["INT-0", "INT-1", "E-1"]


def test_parse_generated_androcles_production_markdown():
    script = ProductionScriptParser(PathConfig("androcles").production_markdown).parse_path()

    assert script.locked
    assert script.entries[0].production_id == "P-0"
    assert any(entry.production_id == "I-3" and entry.roles == ("CENTURION",) for entry in script.entries)
