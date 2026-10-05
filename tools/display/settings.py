"""Display settings: brightness, and how Windows looks.

Brightness goes through WMI (windows/display.py); adaptive brightness is a
power-plan setting; the theme and transparency settings are per-user registry
values that Windows applies the moment it is told they changed. None needs
administrator rights.
"""

from __future__ import annotations

from typing import Any

from engine.tool import Parameter, Preview, Safety, Tool, ToolResult
from tools.power.plan_settings import _ChoiceTool
from tools.registry_choice import RegistryChoiceTool
from windows import display, powercfg
from windows import winsettings as ws

_COLORS = "Settings, then Personalisation, then Colours"


class BrightnessTool(Tool):
    name = "display.brightness"
    category = "display"
    description = "How bright the built-in screen is"
    result_title = "Screen Brightness"
    safety = Safety.MUTATING
    requires_admin = False
    parameters = [
        # Not 0: on many laptops 0% looks like the screen is off, and someone
        # who cannot see the screen cannot undo the change.
        Parameter("percent", int,
                  "Brightness as a percentage. The lowest Atlas allows is 10.",
                  minimum=10, maximum=100),
    ]
    keywords = [
        "brightness", "bright", "brighter", "dim", "dimmer", "darker",
        "too dark", "too bright", "hurts", "eyes", "glare", "screen", "light",
    ]

    def read_current(self) -> dict[str, Any]:
        return {"percent": display.read_brightness()}

    def _adaptive_note(self) -> list[str]:
        try:
            v = powercfg.read_plan_value("SUB_VIDEO", "ADAPTBRIGHT")
        except Exception:                                  # noqa: BLE001
            return []
        if v.ac or v.dc:
            return ["adaptive brightness is on, so Windows may change this "
                    "again by itself. 'atlas set display.adaptive_brightness "
                    "off' stops that."]
        return []

    def preview(self, **kwargs: Any) -> Preview:
        args = self.validate(**kwargs)
        new = args["percent"]
        cur = self.read_current()["percent"]
        word = "brighter" if new > cur else "dimmer"
        summary = f"The screen becomes {word}: {new}% instead of {cur}%."
        for w in self._adaptive_note():
            summary += f" Note: {w}"
        return Preview(
            summary=summary,
            command=display.brightness_command(new),
            current_value=f"{cur}%",
            new_value=f"{new}%",
            reversible=True,
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        args = self.validate(**kwargs)
        new = args["percent"]
        prior = self.read_current()["percent"]
        command = display.write_brightness(new)
        explanation = (
            f"This was already {new}%, so nothing changed." if prior == new else
            f"The screen is now at {new}% brightness; it was {prior}%. The "
            "brightness keys and the quick settings slider still work as "
            "normal. 'undo' puts it back."
        )
        return ToolResult(
            title=self.result_title,
            data={"Was": f"{prior}%", "Now": f"{new}%"},
            explanation=explanation,
            warnings=self._adaptive_note(),
            command_run=command,
            reversible=True,
        )

    def undo(self, prior: dict[str, Any]) -> ToolResult:
        percent = int(prior["percent"])
        before = self.read_current()["percent"]
        command = display.write_brightness(percent)
        return ToolResult(
            title=f"{self.result_title} — reverted",
            data={"Restored to": f"{percent}%", "Was": f"{before}%"},
            explanation=f"Put back the way it was: {percent}% brightness.",
            command_run=command,
            reversible=False,
        )


class AdaptiveBrightnessTool(_ChoiceTool):
    name = "display.adaptive_brightness"
    category = "display"
    description = ("Whether Windows changes screen brightness by itself "
                   "based on the light around you")
    result_title = "Adaptive brightness"
    subgroup, setting, arg = "SUB_VIDEO", "ADAPTBRIGHT", "enabled"
    where = "\"Display\", then \"Enable adaptive brightness\""
    labels = {
        0: ("off", "off (brightness only changes when you change it)"),
        1: ("on", "on (Windows adjusts brightness to the room)"),
    }
    choice_hint = "Whether Windows may adjust brightness on its own."
    keywords = [
        "brightness", "changes", "changing", "by itself", "on its own",
        "keeps", "automatic", "auto", "adaptive", "sensor", "flickers",
        "dims", "dimming",
    ]

    def meaning(self, index: int) -> str:
        if index == 0:
            return "This stops the screen getting brighter or dimmer on its own."
        return ("This only has an effect if the computer has a light sensor. "
                "Many do not.")


class AppThemeTool(RegistryChoiceTool):
    name = "display.app_theme"
    category = "display"
    description = "Whether apps and windows use dark mode or light mode"
    result_title = "App colour mode"
    setting = ws.APPS_LIGHT
    labels = {0: ("dark", "dark"), 1: ("light", "light")}
    choice_hint = "Dark or light, for apps such as Settings and File Explorer."
    where = _COLORS
    keywords = [
        "dark mode", "dark", "light mode", "light", "theme", "white",
        "black", "night", "eyes", "glare", "apps", "explorer", "colour",
        "color",
    ]

    def meaning(self, raw: int) -> str:
        return ("Apps that follow Windows switch now; a few update only when "
                "you next open them.")


class WindowsThemeTool(RegistryChoiceTool):
    name = "display.windows_theme"
    category = "display"
    description = "Whether the taskbar, Start menu and notifications are dark or light"
    result_title = "Taskbar and Start colour mode"
    setting = ws.SYSTEM_LIGHT
    labels = {0: ("dark", "dark"), 1: ("light", "light")}
    choice_hint = "Dark or light, for the taskbar, Start and notifications."
    where = _COLORS
    keywords = [
        "taskbar", "start menu", "start", "notifications", "dark", "light",
        "theme", "mode", "colour", "color", "white", "black",
    ]


class TransparencyTool(RegistryChoiceTool):
    name = "display.transparency"
    category = "display"
    description = ("Whether the taskbar, Start and some windows are "
                   "see-through")
    result_title = "Transparency effects"
    setting = ws.TRANSPARENCY
    labels = {0: ("off", "off (solid)"), 1: ("on", "on (see-through)")}
    choice_hint = "See-through effects on or off."
    where = _COLORS
    keywords = [
        "transparency", "transparent", "see through", "blur", "blurry",
        "hard to read", "glass", "effects", "battery", "slow",
    ]

    def meaning(self, raw: int) -> str:
        if raw == 0:
            return ("Solid backgrounds are easier to read against and use "
                    "slightly less battery.")
        return ""


ALL_DISPLAY_TOOLS = [
    BrightnessTool, AdaptiveBrightnessTool, AppThemeTool, WindowsThemeTool,
    TransparencyTool,
]
