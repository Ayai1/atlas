"""Accessibility settings — the ones people most often need and least often find.

Every tool here follows the same contract as the power tools: read the current
value, show the exact change, record the old value, apply, and be able to put
it back. None of them requires administrator rights.
"""

from __future__ import annotations

from typing import Any

from engine.tool import Parameter, Preview, Safety, Tool, ToolResult
from windows import winsettings as ws


class _RegistryTool(Tool):
    """Shared behaviour for a single per-user Windows setting."""

    safety = Safety.MUTATING
    requires_admin = False
    setting: ws.Setting
    unit: str = ""
    result_title: str = ""

    def describe(self, value: int) -> str:
        return f"{value}{self.unit}"

    # P4 — read before write
    def read_current(self) -> dict[str, Any]:
        value, existed = ws.read_state(self.setting)
        return {"value": value, "existed": existed}

    # P5 — say what will happen
    def preview(self, **kwargs: Any) -> Preview:
        args = self.validate(**kwargs)
        new = args["value"]
        state = self.read_current()
        current = state["value"]
        note = "" if state.get("existed", True) else "  (Windows default)"
        return Preview(
            summary=self.summary(current, new),
            command=f"HKCU\\{self.setting.key}\\{self.setting.name} = {new}",
            current_value=self.describe(current) + note,
            new_value=self.describe(new),
            reversible=True,
        )

    def summary(self, current: int, new: int) -> str:
        return (f"{self.result_title} changes from {self.describe(current)} "
                f"to {self.describe(new)}.")

    def execute(self, **kwargs: Any) -> ToolResult:
        args = self.validate(**kwargs)
        new = args["value"]
        prior = self.read_current()["value"]
        command = ws.write_value(self.setting, new)
        if prior == new:
            explanation = (f"This was already {self.describe(new)}, so nothing "
                           "actually changed on your computer.")
        else:
            explanation = self.explain(prior, new)
        return ToolResult(
            title=self.result_title,
            data={"Was": self.describe(prior), "Now": self.describe(new)},
            explanation=explanation,
            command_run=command,
            reversible=True,
        )

    def explain(self, prior: int, new: int) -> str:
        return (f"{self.result_title} is now {self.describe(new)}; it was "
                f"{self.describe(prior)}. Only this one setting changed, and "
                "'undo' puts it back exactly.")

    # P3 — put it back
    def undo(self, prior: dict[str, Any]) -> ToolResult:
        value = int(prior["value"])
        before = self.read_current()["value"]

        if prior.get("existed", True):
            command = ws.write_value(self.setting, value)
            explanation = f"Put back the way it was: {self.describe(value)}."
        else:
            # Windows had no value here before we wrote one. Restoring the
            # registry exactly means removing it again, not leaving ours behind.
            command = ws.delete_value(self.setting)
            explanation = (
                f"Put back the way it was: {self.describe(value)}. Windows had "
                "no setting stored here before, so it was removed rather than "
                "left behind."
            )

        return ToolResult(
            title=f"{self.result_title} — reverted",
            data={"Restored to": self.describe(value),
                  "Was": self.describe(before)},
            explanation=explanation,
            command_run=command,
            reversible=False,
        )


class PointerSizeTool(_RegistryTool):
    name = "accessibility.pointer_size"
    category = "accessibility"
    description = "How big the mouse pointer is on screen"
    result_title = "Mouse Pointer Size"
    unit = " pixels"
    setting = ws.POINTER_SIZE
    keywords = ["mouse", "pointer", "cursor", "arrow", "bigger", "larger",
                "small", "tiny", "cant find", "cannot find", "lose", "losing",
                "hard to see", "visible", "size"]
    parameters = [Parameter("value", int,
        "Pointer size in pixels. 32 is the Windows default; 64 is large.",
        minimum=32, maximum=256)]

    def summary(self, current: int, new: int) -> str:
        word = "bigger" if new > current else "smaller"
        return (f"The mouse pointer becomes {word} — {new} pixels instead of "
                f"{current}. Windows uses 32 by default.")

    def explain(self, prior: int, new: int) -> str:
        return (f"The mouse pointer is now {new} pixels across; it was {prior}. "
                "It should be easier to spot on screen. Nothing else changed, "
                "and 'undo' puts it back exactly.")


class DoubleClickSpeedTool(_RegistryTool):
    name = "accessibility.double_click_speed"
    category = "accessibility"
    description = "How quickly you must click twice for it to count as a double-click"
    result_title = "Double-Click Speed"
    unit = " ms"
    setting = ws.DOUBLE_CLICK_SPEED
    keywords = ["double", "click", "clicking", "twice", "too fast", "slow down",
                "opening", "folders", "not opening", "hands", "shaky", "speed"]
    parameters = [Parameter("value", int,
        "Milliseconds allowed between the two clicks. 500 is the Windows "
        "default; 900 is much more forgiving.",
        minimum=200, maximum=900)]

    def summary(self, current: int, new: int) -> str:
        word = "more time" if new > current else "less time"
        return (f"You get {word} between the two clicks — {new} milliseconds "
                f"instead of {current}. Windows uses 500 by default.")

    def explain(self, prior: int, new: int) -> str:
        easier = "more forgiving" if new > prior else "stricter"
        return (f"Double-clicking is now {easier}: you have {new} milliseconds "
                f"between clicks instead of {prior}. If double-clicking has "
                "been failing, this is usually the reason. 'undo' puts it back.")


class PointerSpeedTool(_RegistryTool):
    name = "accessibility.pointer_speed"
    category = "accessibility"
    description = "How far the pointer travels when you move the mouse"
    result_title = "Pointer Speed"
    setting = ws.POINTER_SPEED
    keywords = ["mouse", "pointer", "speed", "fast", "slow", "sensitive",
                "moves", "too quick", "jumpy", "control", "steady"]
    parameters = [Parameter("value", int,
        "Pointer speed from 1 (slowest) to 20 (fastest). 10 is the Windows "
        "default.", minimum=1, maximum=20)]

    def describe(self, value: int) -> str:
        return f"{value} of 20"

    def summary(self, current: int, new: int) -> str:
        word = "faster" if new > current else "slower and easier to control"
        return (f"The pointer becomes {word} — speed {new} of 20 instead of "
                f"{current}. Windows uses 10 by default.")


class TextCursorThicknessTool(_RegistryTool):
    name = "accessibility.text_cursor_thickness"
    category = "accessibility"
    description = "How thick the blinking text cursor is when typing"
    result_title = "Text Cursor Thickness"
    unit = " pixels"
    setting = ws.CARET_WIDTH
    keywords = ["text", "cursor", "caret", "blinking", "line", "typing",
                "where am i", "lose my place", "thicker", "thin", "writing"]
    parameters = [Parameter("value", int,
        "Thickness in pixels. 1 is the Windows default; 5 is easy to spot.",
        minimum=1, maximum=20)]

    def summary(self, current: int, new: int) -> str:
        return (f"The blinking cursor you type at becomes {new} pixels wide "
                f"instead of {current}. Windows uses 1 by default.")


class TextSizeTool(_RegistryTool):
    name = "accessibility.text_size"
    category = "accessibility"
    description = "How large text appears across Windows"
    result_title = "Text Size"
    unit = "%"
    setting = ws.TEXT_SCALE
    keywords = ["text", "font", "size", "bigger", "larger", "small", "reading",
                "read", "eyes", "squinting", "magnify", "zoom", "scale",
                "cant read", "cannot read", "too small"]
    parameters = [Parameter("value", int,
        "Text size as a percentage. 100 is normal; 150 is noticeably larger.",
        minimum=100, maximum=225)]

    def summary(self, current: int, new: int) -> str:
        word = "larger" if new > current else "smaller"
        return (f"Text across Windows becomes {word} — {new}% instead of "
                f"{current}%. 100% is normal size.")

    def explain(self, prior: int, new: int) -> str:
        return (f"Text is now shown at {new}% of normal size; it was {prior}%. "
                "This affects menus, settings and most applications. Nothing "
                "else changed, and 'undo' puts it back exactly.")
