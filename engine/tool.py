"""The tool contract — the core of the project.

Every capability is a Tool. A Tool knows how to explain itself, how to preview
what it is about to do, and — if it changes anything — how to put it back.

See ARCHITECTURE.md. The principles referenced as P1..P7 are the
non-negotiables; the code here is what enforces them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from engine.tool_result import ToolResult

__all__ = ["Safety", "Parameter", "Preview", "Tool", "ToolResult"]


class Safety(Enum):
    """How dangerous a tool is. Drives whether confirmation is required."""

    READ_ONLY = "read_only"   # cannot change machine state
    MUTATING = "mutating"     # changes state; needs confirm + undo (P3, P5)


@dataclass
class Preview:
    """Shown to the user before a mutation runs (P5).

    Carries both the plain-English summary and the literal command, because
    the user is entitled to see exactly what will touch their machine.
    """

    summary: str          # "Your screen will turn off after 30 minutes"
    command: str          # "powercfg /change monitor-timeout-ac 30"
    current_value: str    # what it is right now (P4)
    new_value: str
    reversible: bool = True


@dataclass
class Parameter:
    """A typed, bounded argument.

    Bounds live here rather than in a prompt, so they apply to every caller
    equally: a human, a test, or a language model that hallucinated -5.
    """

    name: str
    type: type
    description: str
    required: bool = True
    minimum: float | None = None
    maximum: float | None = None
    choices: list[Any] | None = None
    default: Any = None

    def describe(self) -> str:
        bits = [f"{self.name} ({self.type.__name__})"]
        if self.choices is not None:
            bits.append("one of: " + ", ".join(str(c) for c in self.choices))
        elif self.minimum is not None or self.maximum is not None:
            lo = "" if self.minimum is None else str(int(self.minimum))
            hi = "" if self.maximum is None else str(int(self.maximum))
            bits.append(f"range {lo}-{hi}")
        if not self.required:
            bits.append(f"optional, default {self.default}")
        return "  ".join(bits)


class Tool(ABC):
    """Base class for every tool.

    Every tool must be able to execute an action and explain what it did.
    A tool that changes something must additionally be able to preview the
    change, read the current value, and undo it.
    """

    name: str = ""                     # "accessibility.pointer_size"
    category: str = ""                 # "accessibility"
    description: str = ""              # used for routing and shortlisting
    safety: Safety = Safety.READ_ONLY
    parameters: list[Parameter] = []
    keywords: list[str] = []           # extra phrasings for retrieval
    requires_admin: bool = False

    # ---- required of every tool ------------------------------------
    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """Do the thing. Must return a ToolResult with an explanation."""

    # ---- required of MUTATING tools only ---------------------------
    def preview(self, **kwargs: Any) -> Preview:
        raise NotImplementedError(
            f"{self.name} is MUTATING but has no preview(); "
            "a mutating tool must be able to say what it will do first."
        )

    def undo(self, prior: dict[str, Any]) -> ToolResult:
        raise NotImplementedError(
            f"{self.name} is MUTATING but has no undo(); "
            "see principle P3 in ARCHITECTURE.md."
        )

    def read_current(self) -> dict[str, Any]:
        """Read present state before changing it (P4).

        Mutating tools must implement this — it is what makes undo possible.
        """
        raise NotImplementedError

    # ---- validation: never trust the caller ------------------------
    def validate(self, **kwargs: Any) -> dict[str, Any]:
        """Return cleaned arguments or raise ValueError.

        Runs for every caller, always, before anything reaches the OS.
        """
        known = {p.name for p in self.parameters}
        for supplied in kwargs:
            if supplied not in known:
                raise ValueError(
                    f"{self.name}: unknown argument '{supplied}'. "
                    f"Accepts: {', '.join(sorted(known)) or 'nothing'}"
                )

        clean: dict[str, Any] = {}
        for p in self.parameters:
            if p.name not in kwargs or kwargs[p.name] is None:
                if p.required:
                    raise ValueError(f"{self.name}: missing required '{p.name}'")
                if p.default is not None:
                    clean[p.name] = p.default
                continue

            v = kwargs[p.name]

            # bool is a subclass of int in Python; don't let True mean 1
            if p.type is int and isinstance(v, bool):
                raise ValueError(f"{self.name}: '{p.name}' must be int, got bool")
            if not isinstance(v, p.type):
                raise ValueError(
                    f"{self.name}: '{p.name}' must be "
                    f"{p.type.__name__}, got {type(v).__name__}"
                )
            if p.choices is not None and v not in p.choices:
                raise ValueError(
                    f"{self.name}: '{p.name}' must be one of {p.choices}, got {v!r}"
                )
            if p.minimum is not None and v < p.minimum:
                raise ValueError(
                    f"{self.name}: '{p.name}' is {v}, below minimum {int(p.minimum)}"
                )
            if p.maximum is not None and v > p.maximum:
                raise ValueError(
                    f"{self.name}: '{p.name}' is {v}, above maximum {int(p.maximum)}"
                )
            clean[p.name] = v
        return clean

    # ---- helpers ---------------------------------------------------
    @property
    def is_mutating(self) -> bool:
        return self.safety is Safety.MUTATING

    def search_text(self) -> str:
        return " ".join(
            [self.name.replace(".", " "), self.category, self.description,
             " ".join(self.keywords)]
        ).lower()

    def __repr__(self) -> str:
        return f"<Tool {self.name} {self.safety.value}>"
