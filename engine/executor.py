"""The safe-execution pipeline.

This is ARCHITECTURE.md section 6 in code. Every mutation goes through here,
in this order, with no shortcuts:

    validate -> read current -> preview -> confirm -> journal -> execute

The journal write happens BEFORE execute, so a crash halfway through still
leaves a revert path. There is deliberately no way to call a mutating tool
and skip these steps other than reaching past this module.
"""

from __future__ import annotations

import sys
from typing import Any, Callable

from engine.journal import Journal
from engine.registry import Registry
from engine.renderer import render_preview
from engine.tool import Preview, Tool, ToolResult


class Cancelled(Exception):
    """The user declined the change. Nothing was touched."""


class NeedsConfirmation(Exception):
    """A mutating tool was called without a way to ask the user."""


def _ask_terminal(preview: Preview, tool: Tool) -> bool:
    print(render_preview(preview, tool.name))
    if not sys.stdin.isatty():
        raise NeedsConfirmation(
            "This change needs confirmation but there is nothing to type into. "
            "Re-run in a terminal, or pass --yes if you are certain."
        )
    answer = input("Apply this change? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def run(
    tool: Tool,
    args: dict[str, Any] | None = None,
    journal: Journal | None = None,
    assume_yes: bool = False,
    confirm: Callable[[Preview, Tool], bool] | None = None,
) -> ToolResult:
    """Run a tool through the full contract."""
    args = args or {}

    # 1. validate before anything else touches the machine
    clean = tool.validate(**args)

    # read-only tools skip the rest; there is nothing to confirm or undo
    if not tool.is_mutating:
        return tool.execute(**clean)

    journal = journal or Journal()

    # 2 + 3. read the current value, then say what will happen
    prior = tool.read_current()
    preview = tool.preview(**clean)

    # 4. confirm  (P5 — mandatory even though a model cannot invent commands)
    # The callback receives the Preview itself, not rendered text, so a GUI
    # can display it its own way and still go through this same gate.
    if not assume_yes:
        asker = confirm or _ask_terminal
        if not asker(preview, tool):
            raise Cancelled("No changes were made.")

    # 5. journal the old value BEFORE changing anything  (P3)
    token = journal.record(
        tool=tool.name, args=clean, prior=prior, command=preview.command
    )

    # 6. do it
    try:
        result = tool.execute(**clean)
    except Exception:
        # The journal entry stays. It is a record of an attempt, and the
        # prior value in it is still the truth about how to get back.
        raise

    result.undo_token = token
    return result


def undo_last(
    registry: Registry, journal: Journal | None = None
) -> ToolResult:
    """Revert the most recent change Atlas made."""
    journal = journal or Journal()
    entry = journal.last_undoable()
    if entry is None:
        raise LookupError("There is nothing to undo.")

    tool = registry.get(entry.tool)
    result = tool.undo(entry.prior)
    journal.mark_undone(entry.id)
    journal.record_undo(entry.id, entry.tool, result.command_run)
    return result


def undo_entry(
    registry: Registry, entry_id: str, journal: Journal | None = None
) -> ToolResult:
    """Revert one specific change by its id."""
    journal = journal or Journal()
    entry = journal.get(entry_id)
    if entry is None:
        raise LookupError(f"No change with id '{entry_id}'.")
    if entry.undone:
        raise LookupError(f"Change '{entry_id}' was already undone.")
    if not entry.prior:
        raise LookupError(f"Change '{entry_id}' has no recorded prior value.")

    tool = registry.get(entry.tool)
    result = tool.undo(entry.prior)
    journal.mark_undone(entry.id)
    journal.record_undo(entry.id, entry.tool, result.command_run)
    return result
