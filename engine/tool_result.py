"""What every tool returns.

Keeps the fields this project already used — success, warnings — and adds the
ones the safety contract needs: the exact command that ran, whether it can be
reversed, and the journal entry that reverses it.

`explanation` is mandatory and is written by us, in Python, never by a language
model. A tool that cannot explain itself is not allowed to exist.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Return type for tools."""

    title: str
    data: Any = field(default_factory=dict)
    explanation: str = ""

    success: bool = True
    warnings: list[str] = field(default_factory=list)

    command_run: str | None = None   # the exact command, shown to the user
    reversible: bool = False
    undo_token: str | None = None    # journal entry that undoes this

    def __post_init__(self) -> None:
        if not str(self.explanation).strip():
            raise ValueError(
                f"ToolResult '{self.title}' has no explanation. "
                "Every result must explain itself to the user."
            )
