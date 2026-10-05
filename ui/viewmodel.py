"""Everything the window does, with no window involved.

The tkinter layer in app.py is deliberately thin: it draws what this returns
and calls these methods. All state, formatting, and error handling lives here
so it can be tested without a display, which is also what makes the UI easy
to replace later (ROADMAP Phase 3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine import executor
from engine.journal import Journal
from engine.registry import Registry, build_default_registry
from engine.tool import Preview, Safety, Tool, ToolResult
from windows.powercfg import PowercfgError


@dataclass
class Match:
    """One search hit, ready to be drawn as a row."""
    name: str
    description: str
    badge: str          # "changes a setting" | "read only"
    is_mutating: bool
    confidence: int     # 0-100


@dataclass
class ToolView:
    """A tool opened for editing."""
    name: str
    description: str
    is_mutating: bool
    current_value: str = ""
    argument_name: str = ""
    argument_hint: str = ""
    minimum: int | None = None
    maximum: int | None = None
    choices: list[str] | None = None
    error: str | None = None


@dataclass
class Outcome:
    """The result of trying to do something. Never raises at the UI."""
    ok: bool
    title: str
    explanation: str
    rows: dict[str, Any] = field(default_factory=dict)
    command: str | None = None
    undo_available: bool = False


@dataclass
class HistoryRow:
    id: str
    when: str
    what: str
    detail: str
    undone: bool
    is_undo_record: bool


class StalePreview(Exception):
    """The machine changed between showing the card and pressing Apply."""


class ViewModel:
    def __init__(
        self,
        registry: Registry | None = None,
        journal: Journal | None = None,
    ) -> None:
        self.registry = registry or build_default_registry()
        self.journal = journal or Journal()

    # ---- searching -------------------------------------------------
    def search(self, query: str, limit: int = 6) -> list[Match]:
        return [
            Match(
                name=tool.name,
                description=tool.description,
                badge="changes a setting" if tool.is_mutating else "read only",
                is_mutating=tool.is_mutating,
                confidence=round(score * 100),
            )
            for tool, score in self.registry.shortlist(query, limit=limit)
        ]

    def all_tools(self) -> list[Match]:
        return [
            Match(
                name=t.name, description=t.description,
                badge="changes a setting" if t.is_mutating else "read only",
                is_mutating=t.is_mutating, confidence=0,
            )
            for t in self.registry.all()
        ]

    # ---- opening a tool --------------------------------------------
    def open_tool(self, name: str) -> ToolView:
        tool = self.registry.get(name)
        view = ToolView(
            name=tool.name,
            description=tool.description,
            is_mutating=tool.is_mutating,
        )
        if tool.parameters:
            p = tool.parameters[0]
            view.argument_name = p.name
            view.argument_hint = p.description
            view.minimum = None if p.minimum is None else int(p.minimum)
            view.maximum = None if p.maximum is None else int(p.maximum)
            view.choices = None if p.choices is None else [str(c) for c in p.choices]

        if tool.is_mutating:
            try:
                current = tool.read_current()
                view.current_value = str(current.get(view.argument_name, ""))
            except PowercfgError as exc:
                view.error = str(exc)
            except Exception as exc:                       # noqa: BLE001
                view.error = f"Could not read the current value: {exc}"
        return view

    # ---- the confirmation card -------------------------------------
    def build_preview(self, name: str, raw_value: str) -> tuple[Preview | None, str | None]:
        """Return (preview, error). Never raises."""
        tool = self.registry.get(name)
        args, error = self._coerce(tool, raw_value)
        if error:
            return None, error
        try:
            return tool.preview(**args), None
        except PowercfgError as exc:
            return None, str(exc)
        except ValueError as exc:
            return None, str(exc)
        except Exception as exc:                           # noqa: BLE001
            return None, f"Could not work out what would happen: {exc}"

    def apply(self, name: str, raw_value: str, approved: Preview) -> Outcome:
        """Apply a change the user approved on the card.

        The confirm callback re-checks that the machine still looks the way
        it did when the card was drawn. If something changed underneath us in
        the meantime, the change is refused rather than applied to a state
        the user never actually saw.
        """
        tool = self.registry.get(name)
        args, error = self._coerce(tool, raw_value)
        if error:
            return Outcome(False, "That value will not work", error)

        def confirm(fresh: Preview, _tool: Tool) -> bool:
            if fresh != approved:
                raise StalePreview(
                    "This setting changed on your computer while the "
                    "confirmation was open, so nothing was applied. "
                    "Close this and try again to see the current value."
                )
            return True

        try:
            result = executor.run(tool, args, journal=self.journal, confirm=confirm)
        except StalePreview as exc:
            return Outcome(False, "Nothing was changed", str(exc))
        except executor.Cancelled as exc:
            return Outcome(False, "Nothing was changed", str(exc))
        except PowercfgError as exc:
            return Outcome(False, "Windows would not allow that", str(exc))
        except ValueError as exc:
            return Outcome(False, "That value will not work", str(exc))
        except Exception as exc:                           # noqa: BLE001
            return Outcome(
                False, "Something went wrong",
                f"Nothing was changed on your computer. The error was: {exc}",
            )
        return self._outcome(result)

    # ---- read-only tools -------------------------------------------
    def run_read_only(self, name: str) -> Outcome:
        tool = self.registry.get(name)
        if tool.safety is not Safety.READ_ONLY:
            return Outcome(False, "That tool changes things",
                           "Open it properly so you can see what it will do.")
        try:
            return self._outcome(executor.run(tool, journal=self.journal))
        except Exception as exc:                           # noqa: BLE001
            return Outcome(False, "Could not read that", str(exc))

    def system_info(self) -> Outcome:
        return self.run_read_only("system.info")

    # ---- undo and history ------------------------------------------
    def undo_last(self) -> Outcome:
        try:
            return self._outcome(executor.undo_last(self.registry, self.journal))
        except LookupError as exc:
            return Outcome(False, "Nothing to undo", str(exc))
        except PowercfgError as exc:
            return Outcome(False, "Could not undo that", str(exc))
        except Exception as exc:                           # noqa: BLE001
            return Outcome(False, "Could not undo that", str(exc))

    def undo(self, entry_id: str) -> Outcome:
        try:
            return self._outcome(
                executor.undo_entry(self.registry, entry_id, self.journal)
            )
        except LookupError as exc:
            return Outcome(False, "Nothing to undo", str(exc))
        except Exception as exc:                           # noqa: BLE001
            return Outcome(False, "Could not undo that", str(exc))

    def has_undo(self) -> bool:
        return self.journal.last_undoable() is not None

    def history(self, limit: int = 25) -> list[HistoryRow]:
        rows: list[HistoryRow] = []
        for e in reversed(self.journal.history(limit)):
            when = e.ts.replace("T", "  ")
            if e.kind == "undo":
                rows.append(HistoryRow(
                    id=e.id, when=when, what="Reverted an earlier change",
                    detail=e.command or "", undone=False, is_undo_record=True,
                ))
                continue
            # Prefer the value the person typed over bookkeeping such as the
            # power plan GUID, which only undo needs.
            shared = [k for k in e.args if k in e.prior]
            was = ", ".join(f"{e.prior[k]}" for k in shared) or                 ", ".join(f"{v}" for v in e.prior.values())
            now = ", ".join(f"{v}" for v in e.args.values())
            rows.append(HistoryRow(
                id=e.id, when=when,
                what=e.tool.split(".")[-1].replace("_", " ").title(),
                detail=f"{was} -> {now}", undone=e.undone, is_undo_record=False,
            ))
        return rows

    # ---- helpers ---------------------------------------------------
    def _coerce(self, tool: Tool, raw: str) -> tuple[dict[str, Any], str | None]:
        """Turn the text in the box into typed arguments."""
        if not tool.parameters:
            return {}, None
        p = tool.parameters[0]
        raw = (raw or "").strip()
        if not raw:
            return {}, f"Enter a value for {p.name}."
        if p.type is int:
            try:
                value: Any = int(raw)
            except ValueError:
                return {}, f"'{raw}' is not a whole number."
        else:
            value = raw
        try:
            return tool.validate(**{p.name: value}), None
        except ValueError as exc:
            # Strip the tool-name prefix; the UI already shows which tool.
            return {}, str(exc).split(": ", 1)[-1]

    @staticmethod
    def _outcome(result: ToolResult) -> Outcome:
        return Outcome(
            ok=True,
            title=result.title,
            explanation=result.explanation,
            rows=result.data,
            command=result.command_run,
            undo_available=bool(result.reversible and result.undo_token),
        )
