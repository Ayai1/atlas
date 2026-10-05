"""Append-only undo journal.

Written BEFORE a mutation runs, never after, so that a crash mid-operation
still leaves a revert path (ARCHITECTURE.md section 9).

Nothing here is ever rewritten or deleted. Undoing an action appends a new
entry marking the old one undone. This file is also the honest answer to
"what has Atlas actually done to my computer?"
"""

from __future__ import annotations

import json
import os
import platform
import secrets
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


def default_journal_path() -> Path:
    """%LOCALAPPDATA%\\Atlas on Windows, ~/.atlas elsewhere."""
    if platform.system() == "Windows":
        base = os.environ.get("LOCALAPPDATA")
        root = Path(base) / "Atlas" if base else Path.home() / ".atlas"
    else:
        root = Path(os.environ.get("ATLAS_HOME", Path.home() / ".atlas"))
    return root / "journal.jsonl"


@dataclass
class Entry:
    id: str
    ts: str
    tool: str
    args: dict[str, Any]
    prior: dict[str, Any]
    command: str | None
    undone: bool = False
    kind: str = "change"          # "change" | "undo"
    reverts: str | None = None    # id of the entry this undo reverts

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Entry":
        return cls(
            id=d["id"], ts=d["ts"], tool=d["tool"],
            args=d.get("args", {}), prior=d.get("prior", {}),
            command=d.get("command"), undone=d.get("undone", False),
            kind=d.get("kind", "change"), reverts=d.get("reverts"),
        )


class Journal:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else default_journal_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ---- writing ---------------------------------------------------
    def record(
        self,
        tool: str,
        args: dict[str, Any],
        prior: dict[str, Any],
        command: str | None = None,
    ) -> str:
        """Record intent to change. Call this BEFORE execute()."""
        entry = Entry(
            id=secrets.token_hex(3),
            ts=datetime.now().isoformat(timespec="seconds"),
            tool=tool, args=args, prior=prior, command=command,
        )
        self._append(entry)
        return entry.id

    def record_undo(self, reverts_id: str, tool: str, command: str | None) -> str:
        entry = Entry(
            id=secrets.token_hex(3),
            ts=datetime.now().isoformat(timespec="seconds"),
            tool=tool, args={}, prior={}, command=command,
            kind="undo", reverts=reverts_id,
        )
        self._append(entry)
        return entry.id

    def mark_undone(self, entry_id: str) -> None:
        """Rewrite the log with one entry flagged. Content is never removed."""
        entries = list(self.entries())
        found = False
        for e in entries:
            if e.id == entry_id:
                e.undone = True
                found = True
        if not found:
            raise KeyError(f"No journal entry with id {entry_id}")
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for e in entries:
                fh.write(json.dumps(asdict(e)) + "\n")
        tmp.replace(self.path)

    def _append(self, entry: Entry) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(entry)) + "\n")

    # ---- reading ---------------------------------------------------
    def entries(self) -> Iterator[Entry]:
        if not self.path.exists():
            return iter(())
        out: list[Entry] = []
        with self.path.open("r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(Entry.from_dict(json.loads(line)))
                except (json.JSONDecodeError, KeyError) as exc:
                    print(
                        f"warning: skipping corrupt journal line {line_no}: {exc}",
                        file=sys.stderr,
                    )
        return iter(out)

    def last_undoable(self) -> Entry | None:
        candidates = [
            e for e in self.entries()
            if e.kind == "change" and not e.undone and e.prior
        ]
        return candidates[-1] if candidates else None

    def get(self, entry_id: str) -> Entry | None:
        for e in self.entries():
            if e.id == entry_id:
                return e
        return None

    def history(self, limit: int = 20) -> list[Entry]:
        return list(self.entries())[-limit:]
