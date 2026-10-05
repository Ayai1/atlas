"""Tool registry and shortlist retrieval.

The shortlist step deliberately contains no AI. It narrows a large tool set
to ~10 candidates by keyword overlap, and only that shortlist is ever shown
to a model (ARCHITECTURE.md section 7). Flat routing over hundreds of tools
degrades badly on the small local models we target, so this layer exists
from day one even though the model layer does not yet.
"""

from __future__ import annotations

import re
from typing import Iterable

from engine.tool import Tool

# Words too common to carry signal when matching a request to a tool.
_STOPWORDS = {
    "a", "an", "the", "my", "me", "i", "is", "it", "to", "of", "on", "off",
    "for", "and", "in", "at", "be", "do", "does", "how", "what", "can", "you",
    "please", "want", "would", "like", "make", "set", "change", "get", "keep",
    "keeps", "so", "that", "this", "when", "not", "no", "too", "very", "up",
    "are", "am", "was", "were", "been", "have", "has", "had", "will", "should",
    "could", "there", "here", "from", "with", "about", "into", "than", "then",
    "some", "any", "all", "out", "if", "or", "but", "as", "by", "we", "us",
}

# A word the tool author chose as a keyword is a stronger signal than a word
# that happens to appear in its prose description.
_STRONG = 1.0
_WEAK = 0.4
_PREFIX = 0.5


def _tokens(text: str) -> list[str]:
    return [
        w for w in re.findall(r"[a-z0-9]+", text.lower())
        if w not in _STOPWORDS and len(w) > 1
    ]


class Registry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        if not tool.name:
            raise ValueError(f"{type(tool).__name__} has no name")
        if tool.name in self._tools:
            raise ValueError(f"Duplicate tool name: {tool.name}")
        if tool.is_mutating:
            # Enforce the safety contract at registration, not at runtime.
            for required in ("preview", "undo", "read_current"):
                if getattr(type(tool), required) is getattr(Tool, required):
                    raise TypeError(
                        f"{tool.name} is MUTATING but does not implement "
                        f"{required}(). See ARCHITECTURE.md principle P3."
                    )
        self._tools[tool.name] = tool
        return tool

    def register_all(self, tools: Iterable[Tool]) -> None:
        for t in tools:
            self.register(t)

    # ---- lookup ----------------------------------------------------
    def get(self, name: str) -> Tool:
        if name in self._tools:
            return self._tools[name]
        # forgive a missing namespace: "monitor_timeout" -> "power.monitor_timeout"
        matches = [n for n in self._tools if n.split(".")[-1] == name]
        if len(matches) == 1:
            return self._tools[matches[0]]
        if len(matches) > 1:
            raise KeyError(f"'{name}' is ambiguous: {', '.join(sorted(matches))}")
        raise KeyError(f"No tool named '{name}'")

    def all(self) -> list[Tool]:
        return [self._tools[n] for n in sorted(self._tools)]

    def categories(self) -> list[str]:
        return sorted({t.category for t in self._tools.values()})

    def by_category(self, category: str) -> list[Tool]:
        return [t for t in self.all() if t.category == category]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    # ---- retrieval (no model involved) -----------------------------
    def shortlist(self, query: str, limit: int = 10) -> list[tuple[Tool, float]]:
        """Rank tools by keyword overlap with the user's phrasing.

        Returns (tool, score) sorted best first, scores normalised 0..1.
        Only tools with a non-zero score are returned.
        """
        q = _tokens(query)
        if not q:
            return []

        scored: list[tuple[Tool, float]] = []
        for tool in self.all():
            # Words the author curated, versus words that merely occur in prose.
            strong = set(_tokens(
                f"{tool.name.replace('.', ' ')} {tool.category} "
                f"{' '.join(tool.keywords)}"
            ))
            weak = set(_tokens(tool.description)) - strong
            if not strong and not weak:
                continue

            total = 0.0
            for w in q:
                if w in strong:
                    total += _STRONG
                elif w in weak:
                    total += _WEAK
                elif len(w) >= 5 and any(
                    h.startswith(w[:4]) or w.startswith(h[:4])
                    for h in strong if len(h) >= 4
                ):
                    # "darker" should still reach the keyword "dark"
                    total += _PREFIX

            if total:
                # Normalise so a short precise query cannot be beaten purely
                # by a long one that happened to overlap more words.
                scored.append((tool, min(1.0, total / len(q))))

        scored.sort(key=lambda pair: (-pair[1], pair[0].name))
        return scored[:limit]


# The default registry, populated on import of tools
registry = Registry()


def build_default_registry() -> Registry:
    """Import and register every built-in tool."""
    from tools.accessibility.settings import (
        DoubleClickSpeedTool, PointerSizeTool, PointerSpeedTool,
        TextCursorThicknessTool, TextSizeTool,
    )
    from tools.display.settings import ALL_DISPLAY_TOOLS
    from tools.network.settings import ALL_NETWORK_TOOLS
    from tools.power.plan_settings import ALL_PLAN_TOOLS
    from tools.storage.settings import ALL_STORAGE_TOOLS
    from tools.power.timeouts import MonitorTimeoutTool, StandbyTimeoutTool
    from tools.system.system_info import SystemInfoTool

    if len(registry) == 0:
        registry.register_all([
            SystemInfoTool(),
            MonitorTimeoutTool(),
            StandbyTimeoutTool(),
            PointerSizeTool(),
            DoubleClickSpeedTool(),
            PointerSpeedTool(),
            TextCursorThicknessTool(),
            TextSizeTool(),
            *(cls() for cls in ALL_PLAN_TOOLS),
            *(cls() for cls in ALL_DISPLAY_TOOLS),
            *(cls() for cls in ALL_NETWORK_TOOLS),
            *(cls() for cls in ALL_STORAGE_TOOLS),
        ])
    return registry
