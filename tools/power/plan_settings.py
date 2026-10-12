"""Power settings Windows hides.

Windows 11's Settings app shows the screen and sleep timeouts and little else.
Everything below lives in Control Panel's "Change advanced power settings"
dialog, five clicks deep, behind a link most people never notice — and two of
them (USB selective suspend, wireless power saving) are the usual cause of
"my mouse keeps disconnecting" and "my Wi-Fi keeps dropping". The power plan
picker itself is gone from Settings entirely.

They are ordered roughly by how often someone needs them and fails to find
them.

Every tool reads both the plugged-in and on-battery values before changing
anything, records which power plan they belong to, and on undo writes both
back to that same plan. That way a plan switch between change and undo cannot
send the old value to the wrong place.
"""

from __future__ import annotations

from typing import Any

from engine.tool import Parameter, Preview, Safety, Tool, ToolResult
from windows import powercfg

ADVANCED = ("Control Panel, Power Options, \"Change plan settings\", then "
            "\"Change advanced power settings\"")

WHEN = Parameter(
    name="when",
    type=str,
    description="Plugged in, on battery, or both. Defaults to both.",
    required=False,
    choices=["both", "plugged_in", "on_battery"],
    default="both",
)

_SCOPE = {
    "both": "plugged in and on battery",
    "plugged_in": "while plugged in",
    "on_battery": "on battery",
}


class _PlanSettingTool(Tool):
    """One setting inside the active power plan."""

    safety = Safety.MUTATING
    requires_admin = False
    category = "power"

    subgroup: str = ""          # alias or GUID, as powercfg accepts it
    setting: str = ""
    arg: str = ""               # name of the main parameter
    result_title: str = ""
    where: str = ""             # where a person would find it themselves
    battery_only: bool = False  # the value only matters on battery

    # ---- per-setting translation, overridden below ------------------
    def to_index(self, value: Any) -> int:
        return int(value)

    def from_index(self, index: int) -> Any:
        return index

    def describe(self, index: int) -> str:
        return str(index)

    def check(self, index: int) -> None:
        """Reject combinations a single parameter's bounds cannot express."""

    def meaning(self, index: int) -> str:
        """One sentence on what the new value means in practice."""
        return ""

    def warnings_for(self, index: int) -> list[str]:
        return []

    # ---- shared behaviour -------------------------------------------
    def _state(self, ac: int, dc: int) -> str:
        if self.battery_only or ac == dc:
            return self.describe(dc if self.battery_only else ac)
        return (f"{self.describe(ac)} when plugged in, "
                f"{self.describe(dc)} on battery")

    def _targets(self, args: dict[str, Any], index: int) -> tuple[int | None, int | None]:
        """Which of AC/DC to write. None means leave that one alone."""
        if self.battery_only:
            return None, index
        when = args.get("when", "both")
        return (index if when in ("both", "plugged_in") else None,
                index if when in ("both", "on_battery") else None)

    def _plan(self, kwargs: dict[str, Any]):
        args = self.validate(**kwargs)
        index = self.to_index(args[self.arg])
        self.check(index)
        current = self.read_current()
        new_ac, new_dc = self._targets(args, index)
        after_ac = current["ac"] if new_ac is None else new_ac
        after_dc = current["dc"] if new_dc is None else new_dc
        scope = "on battery" if self.battery_only else _SCOPE[args.get("when", "both")]
        return args, index, current, new_ac, new_dc, after_ac, after_dc, scope

    # P4 — read before write
    def read_current(self) -> dict[str, Any]:
        v = powercfg.read_plan_value(self.subgroup, self.setting)
        shown = v.dc if self.battery_only else v.ac
        return {self.arg: self.from_index(shown),
                "ac": v.ac, "dc": v.dc, "scheme": v.scheme}

    # P5 — say what will happen
    def preview(self, **kwargs: Any) -> Preview:
        _, index, cur, new_ac, new_dc, after_ac, after_dc, scope = self._plan(kwargs)
        cmds = powercfg.plan_value_commands(
            self.subgroup, self.setting, ac=new_ac, dc=new_dc, scheme=cur["scheme"]
        )
        before = self._state(cur["ac"], cur["dc"])
        after = self._state(after_ac, after_dc)
        summary = (f"{self.result_title}, {scope}: {self.describe(index)}. "
                   f"{self.meaning(index)}").strip()
        for w in self.warnings_for(index):
            summary += f" Note: {w}"
        return Preview(
            summary=summary,
            command=powercfg.join_commands(cmds),
            current_value=before,
            new_value=after,
            reversible=True,
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        _, index, cur, new_ac, new_dc, after_ac, after_dc, scope = self._plan(kwargs)
        command = powercfg.write_plan_value(
            self.subgroup, self.setting, ac=new_ac, dc=new_dc, scheme=cur["scheme"]
        )
        before = self._state(cur["ac"], cur["dc"])
        after = self._state(after_ac, after_dc)

        if (after_ac, after_dc) == (cur["ac"], cur["dc"]):
            explanation = (f"This was already {after}, so nothing actually "
                           "changed on your computer.")
        else:
            explanation = (
                f"{self.result_title} is now {after}; it was {before}. "
                f"{self.meaning(index)} Only this one setting in your current "
                f"power plan changed. You can see it yourself in {ADVANCED}, "
                f"under {self.where}."
            ).replace("  ", " ")

        return ToolResult(
            title=self.result_title,
            data={"Was": before, "Now": after, "Applies": scope},
            explanation=explanation,
            warnings=self.warnings_for(index),
            command_run=command,
            reversible=True,
        )

    # P3 — put both values back, in the plan they came from
    def undo(self, prior: dict[str, Any]) -> ToolResult:
        ac, dc = int(prior["ac"]), int(prior["dc"])
        scheme = prior.get("scheme", "SCHEME_CURRENT")
        before = self.read_current()
        command = powercfg.write_plan_value(
            self.subgroup, self.setting, ac=ac, dc=dc, scheme=scheme
        )
        restored = self._state(ac, dc)
        return ToolResult(
            title=f"{self.result_title} — reverted",
            data={"Restored to": restored,
                  "Was": self._state(before["ac"], before["dc"])},
            explanation=f"Put back the way it was: {restored}.",
            command_run=command,
            reversible=False,
        )


class _ChoiceTool(_PlanSettingTool):
    """A setting with named options rather than a number.

    `labels` names every index Windows might report, so any current value can
    be described. `allowed` is the subset Atlas will set; it can be narrower
    when an option is a trap (see CriticalBatteryActionTool).
    """

    labels: dict[int, tuple[str, str]] = {}   # index -> (key, plain words)
    allowed: list[str] | None = None

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        if not cls.labels:
            return
        allowed = cls.allowed or [key for key, _ in cls.labels.values()]
        main = Parameter(
            name=cls.arg, type=str,
            description=cls.choice_hint,
            choices=allowed,
        )
        cls.parameters = [main] if cls.battery_only else [main, WHEN]

    choice_hint: str = ""

    def to_index(self, value: Any) -> int:
        for index, (key, _) in self.labels.items():
            if key == value:
                return index
        raise ValueError(f"{self.name}: unknown option {value!r}")

    def from_index(self, index: int) -> Any:
        return self.labels.get(index, (f"option_{index}", ""))[0]

    def describe(self, index: int) -> str:
        return self.labels.get(index, ("", f"an option Atlas does not know ({index})"))[1]


# ---- buttons and lid -------------------------------------------------

_BUTTON = {
    0: ("do_nothing", "do nothing"),
    1: ("sleep", "sleep"),
    2: ("hibernate", "hibernate"),
    3: ("shut_down", "shut down"),
}

_HIBERNATE_NOTE = (
    "hibernate only works if hibernation is turned on for this computer. "
    "'powercfg /a' lists it if it is."
)


class LidCloseActionTool(_ChoiceTool):
    name = "power.lid_close_action"
    description = "What a laptop does when you close the lid"
    result_title = "Closing the lid"
    subgroup, setting, arg = "SUB_BUTTONS", "LIDACTION", "action"
    where = "\"Power buttons and lid\", then \"Lid close action\""
    labels = _BUTTON
    choice_hint = "What happens when the lid is closed."
    keywords = [
        "lid", "close", "closing", "closed", "laptop", "fold", "shut",
        "external monitor", "docked", "clamshell",
        "turns off when i close",
    ]

    def meaning(self, index: int) -> str:
        if index == 0:
            return ("The laptop keeps running with the lid shut, which is what "
                    "you want when using an external monitor.")
        return ""

    def warnings_for(self, index: int) -> list[str]:
        notes = [_HIBERNATE_NOTE] if index == 2 else []
        if index == 0:
            notes.append("a closed laptop that keeps running in a bag can get "
                         "hot. Shut it down or sleep it from the Start menu "
                         "before packing it away.")
        return notes


class PowerButtonActionTool(_ChoiceTool):
    name = "power.power_button_action"
    description = "What pressing the physical power button does"
    result_title = "Pressing the power button"
    subgroup, setting, arg = "SUB_BUTTONS", "PBUTTONACTION", "action"
    where = "\"Power buttons and lid\", then \"Power button action\""
    labels = {**_BUTTON, 4: ("turn_off_display", "turn off the screen")}
    choice_hint = "What happens when the power button is pressed."
    keywords = [
        "power button", "button", "press", "pressing", "physical",
        "accidentally", "shuts down", "shut down", "turns off",
    ]

    def meaning(self, index: int) -> str:
        if index == 3:
            return ("Holding the button for several seconds still forces the "
                    "computer off, whatever this is set to.")
        return ""

    def warnings_for(self, index: int) -> list[str]:
        return [_HIBERNATE_NOTE] if index == 2 else []


# ---- waking and sleeping --------------------------------------------

class WakeTimersTool(_ChoiceTool):
    name = "power.wake_timers"
    description = ("Whether scheduled tasks such as updates may wake the "
                   "computer from sleep")
    result_title = "Wake timers"
    subgroup, setting, arg = "SUB_SLEEP", "RTCWAKE", "allow"
    where = "\"Sleep\", then \"Allow wake timers\""
    labels = {
        0: ("off", "off (nothing scheduled can wake it)"),
        1: ("on", "on (scheduled tasks can wake it)"),
        2: ("important_only", "important only (only urgent tasks can wake it)"),
    }
    choice_hint = "Whether scheduled tasks may wake the computer."
    keywords = [
        "wakes up", "wake up", "waking", "wakes", "turns on", "night",
        "by itself", "on its own", "middle of the night", "randomly",
        "timer", "timers", "scheduled", "updates",
    ]

    def meaning(self, index: int) -> str:
        if index == 0:
            return ("Windows Update can still install updates; it just waits "
                    "until you next use the computer.")
        return ""


class HibernateAfterTool(_PlanSettingTool):
    name = "power.hibernate_after"
    description = ("How long the computer sleeps before switching to "
                   "hibernate, which uses no battery")
    result_title = "Hibernate after"
    subgroup, setting, arg = "SUB_SLEEP", "HIBERNATEIDLE", "minutes"
    where = "\"Sleep\", then \"Hibernate after\""
    parameters = [
        Parameter("minutes", int,
                  "Minutes asleep before hibernating. 0 means never.",
                  minimum=0, maximum=1440),
        WHEN,
    ]
    keywords = [
        "hibernate", "hibernation", "battery drain", "battery dies",
        "dead battery", "overnight", "asleep", "drains", "draining",
    ]

    def to_index(self, value: Any) -> int:
        return int(value) * 60          # powercfg stores seconds

    def from_index(self, index: int) -> Any:
        return powercfg._seconds_to_minutes(index)

    def describe(self, index: int) -> str:
        return _minutes(powercfg._seconds_to_minutes(index))

    def meaning(self, index: int) -> str:
        if index == 0:
            return "The computer stays in sleep until you wake it."
        return ("After that long asleep the computer saves everything to disk "
                "and powers off fully, so the battery stops draining. Waking "
                "takes a little longer than from sleep.")

    def warnings_for(self, index: int) -> list[str]:
        return [_HIBERNATE_NOTE] if index else []


# ---- devices that disconnect ----------------------------------------

class UsbSelectiveSuspendTool(_ChoiceTool):
    name = "power.usb_selective_suspend"
    description = ("Whether Windows powers down idle USB devices to save "
                   "energy")
    result_title = "USB selective suspend"
    # This subgroup has no powercfg alias; the GUIDs are fixed by Windows.
    subgroup = "2a737441-1930-4402-8d77-b2bebba308a3"
    setting = "48e6b7a6-50f5-4782-a5d4-53bb8f07e226"
    arg = "enabled"
    where = "\"USB settings\", then \"USB selective suspend setting\""
    labels = {
        0: ("off", "off (USB devices always stay powered)"),
        1: ("on", "on (idle USB devices may be powered down)"),
    }
    choice_hint = "Whether idle USB devices may be powered down."
    keywords = [
        "usb", "mouse", "keyboard", "disconnects", "disconnecting",
        "disconnect", "drops", "stops working", "unplugged", "webcam",
        "external drive", "dongle", "not recognised", "not recognized",
    ]

    def meaning(self, index: int) -> str:
        if index == 0:
            return ("This is the usual fix for a USB mouse, keyboard or "
                    "drive that disconnects after a few idle minutes. It "
                    "costs a little battery life on a laptop.")
        return ""


class WifiPowerSavingTool(_ChoiceTool):
    name = "power.wifi_power_saving"
    description = ("How hard Windows throttles the Wi-Fi adapter to save "
                   "battery")
    result_title = "Wi-Fi power saving"
    subgroup = "19cbb8fa-5279-450e-9fac-8a3d5fedd0c1"
    setting = "12bbebe6-58d6-4636-95bb-3217ef867c1a"
    arg = "mode"
    where = "\"Wireless Adapter Settings\", then \"Power Saving Mode\""
    labels = {
        0: ("maximum_performance", "maximum performance (no power saving)"),
        1: ("low_saving", "low power saving"),
        2: ("medium_saving", "medium power saving"),
        3: ("maximum_saving", "maximum power saving"),
    }
    choice_hint = "How much the Wi-Fi adapter may save power."
    keywords = [
        "wifi", "wi fi", "wireless", "internet", "drops", "dropping",
        "disconnects", "slow", "lag", "connection", "network", "laggy",
        "ping",
    ]

    def meaning(self, index: int) -> str:
        if index == 0:
            return ("This often fixes Wi-Fi that drops out or lags on battery. "
                    "It uses more battery while the Wi-Fi is busy.")
        return ""


# ---- heat and battery -----------------------------------------------

class MaxProcessorStateTool(_PlanSettingTool):
    name = "power.max_processor_state"
    description = ("The most of its speed the processor may use; lowering it "
                   "makes a hot laptop cooler and quieter")
    result_title = "Maximum processor speed"
    subgroup, setting, arg = "SUB_PROCESSOR", "PROCTHROTTLEMAX", "percent"
    where = ("\"Processor power management\", then \"Maximum processor "
             "state\"")
    parameters = [
        # Below half speed the computer becomes frustrating to use, and a
        # user who set it by mistake might not connect the slowness to it.
        Parameter("percent", int,
                  "Highest share of full speed allowed, as a percentage.",
                  minimum=50, maximum=100),
        WHEN,
    ]
    keywords = [
        "hot", "heat", "overheating", "overheats", "fan", "fans", "loud",
        "noisy", "temperature", "thermal", "cpu", "processor", "throttle",
        "cooler", "quieter", "turbo", "boost",
    ]

    def describe(self, index: int) -> str:
        return f"{index}%"

    def meaning(self, index: int) -> str:
        if index == 100:
            return "The processor may run at full speed, including turbo boost."
        if index == 99:
            return ("99% switches off turbo boost on most processors, which "
                    "removes most of the heat for a small loss of speed.")
        return ("The processor is held below full speed: cooler and quieter, "
                "but noticeably slower at heavy work.")


class CriticalBatteryActionTool(_ChoiceTool):
    name = "power.critical_battery_action"
    description = "What a laptop does when the battery is almost empty"
    result_title = "When the battery is critical"
    subgroup, setting, arg = "SUB_BATTERY", "BATACTIONCRIT", "action"
    where = "\"Battery\", then \"Critical battery action\""
    battery_only = True
    labels = {
        0: ("do_nothing", "do nothing"),
        1: ("sleep", "sleep"),
        2: ("hibernate", "hibernate"),
        3: ("shut_down", "shut down"),
    }
    # "do nothing" lets the battery run flat with unsaved work open. Atlas will
    # describe it if it finds it, and undo will restore it, but will not set it.
    allowed = ["sleep", "hibernate", "shut_down"]
    choice_hint = "What happens when the battery reaches the critical level."
    keywords = [
        "battery", "critical", "empty", "dies", "runs out", "flat",
        "lost work", "suddenly", "shuts off", "low battery",
    ]

    def meaning(self, index: int) -> str:
        if index == 2:
            return ("Hibernate saves everything you have open before the "
                    "battery runs out, so nothing is lost.")
        if index == 1:
            return ("Sleep still uses a little battery; if it runs out while "
                    "asleep, unsaved work is lost.")
        return ""

    def warnings_for(self, index: int) -> list[str]:
        return [_HIBERNATE_NOTE] if index == 2 else []


class LowBatteryLevelTool(_PlanSettingTool):
    name = "power.low_battery_level"
    description = "At what battery percentage Windows warns you it is low"
    result_title = "Low battery warning"
    subgroup, setting, arg = "SUB_BATTERY", "BATLEVELLOW", "percent"
    where = "\"Battery\", then \"Low battery level\""
    battery_only = True
    parameters = [
        Parameter("percent", int,
                  "Battery percentage at which to warn.",
                  minimum=5, maximum=50),
    ]
    keywords = [
        "battery", "warning", "warn", "low", "percent", "percentage",
        "notification", "alert", "earlier", "dies without warning",
    ]

    def describe(self, index: int) -> str:
        return f"{index}%"

    def check(self, index: int) -> None:
        crit = powercfg.read_plan_value("SUB_BATTERY", "BATLEVELCRIT").dc
        if index <= crit:
            raise ValueError(
                f"{self.name}: the warning has to come before the battery is "
                f"critical, which on this computer is {crit}%. Choose more "
                f"than {crit}."
            )

    def meaning(self, index: int) -> str:
        return f"Windows will warn you when the battery drops to {index}%."


# ---- storage --------------------------------------------------------

class DiskTimeoutTool(_PlanSettingTool):
    name = "power.disk_timeout"
    description = ("How long before an idle hard disk spins down; matters "
                   "for spinning and external drives, not SSDs")
    result_title = "Hard disk turn-off"
    subgroup, setting, arg = "SUB_DISK", "DISKIDLE", "minutes"
    where = "\"Hard disk\", then \"Turn off hard disk after\""
    parameters = [
        Parameter("minutes", int,
                  "Minutes idle before the disk spins down. 0 means never.",
                  minimum=0, maximum=300),
        WHEN,
    ]
    keywords = [
        "hard disk", "hard drive", "disk", "drive", "spins down", "spin",
        "external drive", "clicking", "pause", "freezes", "hdd",
    ]

    def to_index(self, value: Any) -> int:
        return int(value) * 60

    def from_index(self, index: int) -> Any:
        return powercfg._seconds_to_minutes(index)

    def describe(self, index: int) -> str:
        return _minutes(powercfg._seconds_to_minutes(index))

    def meaning(self, index: int) -> str:
        return ("A drive that has spun down takes a second or two to wake, "
                "which can feel like a short freeze.")


# ---- the plan itself ------------------------------------------------

# Windows' built-in plans have fixed GUIDs on every machine.
PLANS = {
    "balanced": ("381b4222-f694-41f0-9685-ff5bb260df2e", "Balanced"),
    "high_performance": ("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c", "High performance"),
    "power_saver": ("a1841308-3541-4fab-bc81-f71556f20b4a", "Power saver"),
}


class PowerPlanTool(Tool):
    name = "power.plan"
    category = "power"
    description = ("Which power plan is active: balanced, high performance "
                   "or power saver")
    result_title = "Power plan"
    safety = Safety.MUTATING
    requires_admin = False
    parameters = [
        Parameter("plan", str, "Which plan to switch to.",
                  choices=list(PLANS)),
    ]
    keywords = [
        "power plan", "plan", "high performance", "performance", "balanced",
        "power saver", "battery saver", "faster", "slow", "scheme", "mode",
    ]

    def read_current(self) -> dict[str, Any]:
        active = next(p for p in powercfg.list_plans() if p.active)
        key = next((k for k, (g, _) in PLANS.items() if g == active.guid),
                   active.name)
        return {"plan": key, "scheme": active.guid, "name": active.name}

    def _target(self, plan: str):
        guid, label = PLANS[plan]
        available = powercfg.list_plans()
        if not any(p.guid == guid for p in available):
            names = ", ".join(p.name for p in available)
            raise ValueError(
                f"{self.name}: this computer does not have the {label} plan. "
                f"It has: {names}. Many newer laptops only offer Balanced, and "
                "use the power mode slider in Settings instead."
            )
        return guid, label

    def preview(self, **kwargs: Any) -> Preview:
        args = self.validate(**kwargs)
        guid, label = self._target(args["plan"])
        current = self.read_current()
        return Preview(
            summary=(f"Switch the power plan from {current['name']} to {label}. "
                     "Each plan keeps its own screen, sleep and other "
                     "settings, so those may change with it."),
            command=" ".join(powercfg.set_active_command(guid)),
            current_value=current["name"],
            new_value=label,
            reversible=True,
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        args = self.validate(**kwargs)
        guid, label = self._target(args["plan"])
        prior = self.read_current()
        command = powercfg.set_active_plan(guid)
        if prior["scheme"] == guid:
            explanation = (f"{label} was already the active plan, so nothing "
                           "changed.")
        else:
            explanation = (
                f"The {label} plan is now active; it was {prior['name']}. "
                "Windows 11 no longer shows this choice in Settings. You can "
                "see it in Control Panel, under Power Options."
            )
        return ToolResult(
            title=self.result_title,
            data={"Was": prior["name"], "Now": label},
            explanation=explanation,
            command_run=command,
            reversible=True,
        )

    def undo(self, prior: dict[str, Any]) -> ToolResult:
        before = self.read_current()
        command = powercfg.set_active_plan(prior["scheme"])
        return ToolResult(
            title=f"{self.result_title} — reverted",
            data={"Restored to": prior["name"], "Was": before["name"]},
            explanation=f"Put back the way it was: {prior['name']} is active again.",
            command_run=command,
            reversible=False,
        )


def _minutes(m: int) -> str:
    if m == 0:
        return "never"
    if m % 60 == 0:
        h = m // 60
        return f"{h} hour" + ("s" if h > 1 else "")
    return f"{m} minute" + ("s" if m != 1 else "")


ALL_PLAN_TOOLS = [
    LidCloseActionTool, PowerButtonActionTool, WakeTimersTool,
    UsbSelectiveSuspendTool, WifiPowerSavingTool, HibernateAfterTool,
    MaxProcessorStateTool, CriticalBatteryActionTool, LowBatteryLevelTool,
    DiskTimeoutTool, PowerPlanTool,
]
