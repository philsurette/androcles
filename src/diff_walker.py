#!/usr/bin/env python3
"""Walk diff tuples and emit structured diff events."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from diff_context import DiffContext
from diff_event import DiffEvent


@dataclass
class DiffWalker:
    context: DiffContext

    def __iter__(self) -> Iterator[DiffEvent]:
        diffs = self.context.diffs
        exp_idx = 0
        act_idx = 0
        i = 0
        while i < len(diffs):
            op, text = diffs[i]
            count = len(text)
            if op == 0:
                yield DiffEvent(
                    op="match",
                    expected=self.context.expected_slice(exp_idx, count),
                    actual=self.context.actual_slice(act_idx, count),
                    expected_index=exp_idx,
                    actual_index=act_idx,
                )
                exp_idx += count
                act_idx += count
                i += 1
                continue
            if op == -1 and i + 1 < len(diffs) and diffs[i + 1][0] == 1:
                insert_count = len(diffs[i + 1][1])
                yield DiffEvent(
                    op="replace",
                    expected=self.context.expected_slice(exp_idx, count),
                    actual=self.context.actual_slice(act_idx, insert_count),
                    expected_index=exp_idx,
                    actual_index=act_idx,
                )
                exp_idx += count
                act_idx += insert_count
                i += 2
                continue
            if op == 1 and i + 1 < len(diffs) and diffs[i + 1][0] == -1:
                delete_count = len(diffs[i + 1][1])
                yield DiffEvent(
                    op="replace",
                    expected=self.context.expected_slice(exp_idx, delete_count),
                    actual=self.context.actual_slice(act_idx, count),
                    expected_index=exp_idx,
                    actual_index=act_idx,
                )
                exp_idx += delete_count
                act_idx += count
                i += 2
                continue
            if op == -1:
                yield DiffEvent(
                    op="delete",
                    expected=self.context.expected_slice(exp_idx, count),
                    actual=None,
                    expected_index=exp_idx,
                    actual_index=None,
                )
                exp_idx += count
                i += 1
                continue
            if op == 1:
                yield DiffEvent(
                    op="insert",
                    expected=None,
                    actual=self.context.actual_slice(act_idx, count),
                    expected_index=exp_idx,
                    actual_index=act_idx,
                )
                act_idx += count
                i += 1
                continue
            raise RuntimeError(f"Unexpected diff opcode: {op}")
