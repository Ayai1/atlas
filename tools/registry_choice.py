"""A per-user registry setting with named options instead of a number.

The display, network and storage settings that are on/off or pick-one-of
share this. It follows the same contract as the accessibility tools: read the
value and whether Windows had it stored at all, show the exact write, and on
undo either restore the old value or remove the one we created.
"""

from __future__ import annotations

from typing import Any

from engine.tool import Parameter, Preview, Safety, Tool, ToolResult
from windows import winsettings as ws


class RegistryChoiceTool(Tool):
    safety = Safety.MUTATING
    requires_admin = False

    setting: ws.Setting
    labels: dict[int, tuple[str, str]] = {}   # raw value -> (key, plain words)
    allowed: list[str] | None = None          # narrower than labels if needed
    choice_hint: str = ""
    result_title: str = ""
    where: str = ""                           # where to see it in Windows

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        if cls.labels:
            allowed = cls.allowed or [k for k, _ in cls.labels.values()]
            cls.parameters = [Parameter("value", str, cls.choice_hint,
                                        choices=allowed)]

    # ---- translation ------------------------------------------------
    def to_raw(self, key: str) -> int:
        for raw, (k, _) in self.labels.items():
            if k == key:
                return raw
        raise ValueError(f"{self.name}: unknown option {key!r}")

    def key_of(self, raw: int) -> str:
        return self.labels.get(raw, (f"value_{raw}", ""))[0]

    def describe(self, raw: int) -> str:
        return self.labels.get(raw, ("", f"a value Atlas does not know ({raw})"))[1]

    # ---- per-setting hooks ------------------------------------------
    def check(self, raw: int) -> None:
        """Reject a change that would not work on this machine."""

    def meaning(self, raw: int) -> str:
        return ""

    def warnings_for(self, raw: int) -> list[str]:
        return []

    # ---- contract ---------------------------------------------------
    def read_current(self) -> dict[str, Any]:
        raw, existed = ws.read_state(self.setting)
        return {"value": self.key_of(raw), "raw": raw, "existed": existed}

    def _command(self, raw: int) -> str:
        return f"HKCU\\{self.setting.key}\\{self.setting.name} = {raw}"

    def preview(self, **kwargs: Any) -> Preview:
        args = self.validate(**kwargs)
        new = self.to_raw(args["value"])
        self.check(new)
        cur = self.read_current()
        note = "" if cur["existed"] else "  (Windows default)"
        summary = f"{self.result_title}: {self.describe(new)}. {self.meaning(new)}".strip()
        for w in self.warnings_for(new):
            summary += f" Note: {w}"
        return Preview(
            summary=summary,
            command=self._command(new),
            current_value=self.describe(cur["raw"]) + note,
            new_value=self.describe(new),
            reversible=True,
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        args = self.validate(**kwargs)
        new = self.to_raw(args["value"])
        self.check(new)
        prior = self.read_current()["raw"]
        command = ws.write_value(self.setting, new)
        if prior == new:
            explanation = (f"This was already {self.describe(new)}, so nothing "
                           "actually changed on your computer.")
        else:
            explanation = " ".join(filter(None, [
                f"{self.result_title} is now {self.describe(new)}; it was "
                f"{self.describe(prior)}.",
                self.meaning(new),
                f"You can see it yourself in {self.where}." if self.where else "",
                "'undo' puts it back exactly.",
            ]))
        return ToolResult(
            title=self.result_title,
            data={"Was": self.describe(prior), "Now": self.describe(new)},
            explanation=explanation,
            warnings=self.warnings_for(new),
            command_run=command,
            reversible=True,
        )

    def undo(self, prior: dict[str, Any]) -> ToolResult:
        raw = int(prior["raw"])
        before = self.read_current()["raw"]
        if prior.get("existed", True):
            command = ws.write_value(self.setting, raw)
            explanation = f"Put back the way it was: {self.describe(raw)}."
        else:
            command = ws.delete_value(self.setting)
            explanation = (
                f"Put back the way it was: {self.describe(raw)}. Windows had no "
                "value stored here before, so ours was removed rather than "
                "left behind."
            )
        return ToolResult(
            title=f"{self.result_title} — reverted",
            data={"Restored to": self.describe(raw), "Was": self.describe(before)},
            explanation=explanation,
            command_run=command,
            reversible=False,
        )
