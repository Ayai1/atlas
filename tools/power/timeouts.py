"""Idle timeout settings: when the screen turns off, when the PC sleeps.

These are the first MUTATING tools, and they exist to prove the whole safety
contract end to end: read the current value, show the exact command, ask,
record the old value, change it, and be able to put it back.

Chosen deliberately. Both are impossible to damage a machine with, revert
perfectly, and are visible in the Windows Settings UI so a user can verify
with their own eyes that Atlas did what it said.
"""

from __future__ import annotations

from typing import Any

from engine.tool import Parameter, Preview, Safety, Tool, ToolResult
from windows import powercfg


def _describe_minutes(minutes: int) -> str:
    if minutes == 0:
        return "never"
    if minutes == 1:
        return "1 minute"
    if minutes < 60:
        return f"{minutes} minutes"
    hours = minutes / 60
    if hours == int(hours):
        return f"{int(hours)} hour" + ("s" if hours > 1 else "")
    return f"{minutes} minutes"


class _TimeoutTool(Tool):
    """Shared behaviour for the AC-power idle timeouts."""

    kind: str = ""            # "monitor" | "standby"
    safety = Safety.MUTATING
    requires_admin = False

    parameters = [
        Parameter(
            name="minutes",
            type=int,
            description=(
                "How many minutes of no activity to wait. Use 0 for never."
            ),
            required=True,
            minimum=0,
            maximum=300,
        )
    ]

    # ---- P4: read before write -------------------------------------
    def read_current(self) -> dict[str, Any]:
        current = powercfg.read_timeouts(self.kind)
        return {"minutes": current.ac}

    # ---- P5: say what you are about to do --------------------------
    def preview(self, **kwargs: Any) -> Preview:
        args = self.validate(**kwargs)
        minutes = args["minutes"]
        current = self.read_current()["minutes"]
        cmd = " ".join(powercfg.change_command(self.kind, minutes))
        label = powercfg.TIMEOUTS[self.kind]["label"]
        return Preview(
            summary=(
                f"While plugged in, {label} will wait "
                f"{_describe_minutes(minutes)} of no activity instead of "
                f"{_describe_minutes(current)}."
            ),
            command=cmd,
            current_value=_describe_minutes(current),
            new_value=_describe_minutes(minutes),
            reversible=True,
        )

    # ---- do it -----------------------------------------------------
    def execute(self, **kwargs: Any) -> ToolResult:
        args = self.validate(**kwargs)
        minutes = args["minutes"]
        prior = self.read_current()["minutes"]
        command = powercfg.write_timeout(self.kind, minutes)
        label = powercfg.TIMEOUTS[self.kind]["label"]

        if prior == minutes:
            explanation = (
                f"This was already set to {_describe_minutes(minutes)}, so "
                "nothing actually changed on your computer."
            )
        else:
            explanation = (
                f"While plugged in, {label} now waits "
                f"{_describe_minutes(minutes)} of no activity. It used to be "
                f"{_describe_minutes(prior)}. Only this one setting changed. "
                "Your battery settings were left alone, and you can check this "
                "yourself in Settings, under System then Power."
            )

        return ToolResult(
            title=self.result_title,
            data={"Was": _describe_minutes(prior),
                  "Now": _describe_minutes(minutes),
                  "When plugged in": "yes"},
            explanation=explanation,
            command_run=command,
            reversible=True,
        )

    # ---- P3: put it back -------------------------------------------
    def undo(self, prior: dict[str, Any]) -> ToolResult:
        minutes = int(prior["minutes"])
        before_undo = self.read_current()["minutes"]
        command = powercfg.write_timeout(self.kind, minutes)
        label = powercfg.TIMEOUTS[self.kind]["label"]
        return ToolResult(
            title=f"{self.result_title} — reverted",
            data={"Restored to": _describe_minutes(minutes),
                  "Was": _describe_minutes(before_undo)},
            explanation=(
                f"Put back the way it was: {label} waits "
                f"{_describe_minutes(minutes)} again."
            ),
            command_run=command,
            reversible=False,
        )


class MonitorTimeoutTool(_TimeoutTool):
    kind = "monitor"
    name = "power.monitor_timeout"
    category = "power"
    description = "How long before the screen turns off when you are not using it"
    result_title = "Screen Timeout"
    keywords = [
        "screen", "display", "monitor", "turns off", "goes dark", "goes black",
        "blank", "dim", "sleeps", "screen off", "stay on", "stays on",
        "keeps turning off", "while reading", "timeout", "idle", "going",
    ]


class StandbyTimeoutTool(_TimeoutTool):
    kind = "standby"
    name = "power.sleep_timeout"
    category = "power"
    description = "How long before the whole computer goes to sleep when idle"
    result_title = "Sleep Timeout"
    keywords = [
        "sleep", "sleeping", "suspend", "standby", "goes to sleep", "hibernate",
        "shuts down", "locks", "idle", "timeout", "stay awake", "stays awake",
        "keeps sleeping", "going to sleep",
    ]
