"""Test fixtures.

The power tools are tested against a fake powercfg so the suite runs on any
machine, including CI, and so `undo` can be proven to restore the exact prior
value without needing a real Windows box.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.journal import Journal          # noqa: E402
from engine.registry import Registry        # noqa: E402
from windows import powercfg           # noqa: E402
from windows import winsettings as ws  # noqa: E402
from tools.power.timeouts import (        # noqa: E402
    MonitorTimeoutTool, StandbyTimeoutTool,
)
from tools.power.plan_settings import ALL_PLAN_TOOLS   # noqa: E402
from tools.display.settings import ALL_DISPLAY_TOOLS  # noqa: E402
from tools.network.settings import ALL_NETWORK_TOOLS  # noqa: E402
from tools.storage.settings import ALL_STORAGE_TOOLS  # noqa: E402
from tools.system.system_info import SystemInfoTool   # noqa: E402
from tools.accessibility.settings import (             # noqa: E402
    DoubleClickSpeedTool, PointerSizeTool, PointerSpeedTool,
    TextCursorThicknessTool, TextSizeTool,
)


class FakeRegistry:
    """Stands in for the per-user Windows registry and SystemParametersInfo."""

    def __init__(self):
        self.values = {
            (ws.POINTER_SIZE.key, ws.POINTER_SIZE.name): 32,
            (ws.DOUBLE_CLICK_SPEED.key, ws.DOUBLE_CLICK_SPEED.name): 500,
            (ws.POINTER_SPEED.key, ws.POINTER_SPEED.name): 10,
            (ws.CARET_WIDTH.key, ws.CARET_WIDTH.name): 1,
            (ws.TEXT_SCALE.key, ws.TEXT_SCALE.name): 100,
            (ws.APPS_LIGHT.key, ws.APPS_LIGHT.name): 0,
            (ws.SYSTEM_LIGHT.key, ws.SYSTEM_LIGHT.name): 0,
            (ws.TRANSPARENCY.key, ws.TRANSPARENCY.name): 1,
            (ws.PROXY_ENABLE.key, ws.PROXY_ENABLE.name): 0,
            (ws.STORAGE_SENSE.key, ws.STORAGE_SENSE.name): 1,
            (ws.STORAGE_SENSE_SCHEDULE.key, ws.STORAGE_SENSE_SCHEDULE.name): 0,
            (ws.STORAGE_SENSE_TEMP.key, ws.STORAGE_SENSE_TEMP.name): 1,
            # Recycle Bin days deliberately absent: the Windows default.
        }
        self.texts = {}          # (key, name) -> str, for REG_SZ values
        self.writes = []

    def read_text(self, key, name):
        return self.texts.get((key, name))

    def read_state(self, setting):
        """(value, exists). An absent value means the Windows default."""
        k = (setting.key, setting.name)
        if k not in self.values:
            return setting.default, False
        return int(self.values[k]), True

    def read_value(self, setting):
        return self.read_state(setting)[0]

    def delete_value(self, setting):
        self.values.pop((setting.key, setting.name), None)
        cmd = f"removed HKCU\\{setting.key}\\{setting.name}"
        self.writes.append(cmd)
        return cmd

    def write_value(self, setting, value):
        self.values[(setting.key, setting.name)] = int(value)
        cmd = f"HKCU\\{setting.key}\\{setting.name} = {value}"
        self.writes.append(cmd)
        return cmd


class FakeOS:
    """Stands in for the machine. Records every command it was asked to run."""

    def __init__(self, monitor_ac=10, monitor_dc=5, standby_ac=30, standby_dc=15):
        self.state = {
            "monitor": {"ac": monitor_ac, "dc": monitor_dc},
            "standby": {"ac": standby_ac, "dc": standby_dc},
        }
        self.commands: list[str] = []

    def read_timeouts(self, kind):
        s = self.state[kind]
        return powercfg.Timeouts(ac=s["ac"], dc=s["dc"])

    def write_timeout(self, kind, minutes, on_battery=False):
        self.state[kind]["dc" if on_battery else "ac"] = minutes
        cmd = " ".join(powercfg.change_command(kind, minutes, on_battery))
        self.commands.append(cmd)
        return cmd


BALANCED = "381b4222-f694-41f0-9685-ff5bb260df2e"
HIGH_PERF = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
CUSTOM = "11111111-2222-3333-4444-555555555555"


class FakePlans:
    """Stands in for the settings inside each power plan, and the plan list.

    Values are stored per plan, so a test can prove that undo writes back to
    the plan a value came from even if the active plan changed in between.
    """

    def __init__(self):
        self.active = BALANCED
        self.names = {BALANCED: "Balanced", HIGH_PERF: "High performance",
                      CUSTOM: "My custom plan"}
        defaults = {
            ("SUB_BUTTONS", "LIDACTION"): (1, 1),
            ("SUB_BUTTONS", "PBUTTONACTION"): (1, 1),
            ("SUB_SLEEP", "RTCWAKE"): (1, 0),
            ("SUB_SLEEP", "HIBERNATEIDLE"): (0, 10800),
            ("2a737441-1930-4402-8d77-b2bebba308a3",
             "48e6b7a6-50f5-4782-a5d4-53bb8f07e226"): (1, 1),
            ("19cbb8fa-5279-450e-9fac-8a3d5fedd0c1",
             "12bbebe6-58d6-4636-95bb-3217ef867c1a"): (0, 2),
            ("SUB_PROCESSOR", "PROCTHROTTLEMAX"): (100, 100),
            ("SUB_BATTERY", "BATACTIONCRIT"): (2, 2),
            ("SUB_BATTERY", "BATLEVELCRIT"): (5, 5),
            ("SUB_BATTERY", "BATLEVELLOW"): (10, 10),
            ("SUB_DISK", "DISKIDLE"): (1200, 600),
            ("SUB_VIDEO", "ADAPTBRIGHT"): (0, 0),
        }
        self.values = {
            plan: {k: list(v) for k, v in defaults.items()}
            for plan in (BALANCED, HIGH_PERF)
        }
        self.commands: list[str] = []

    def read_plan_value(self, subgroup, setting):
        try:
            ac, dc = self.values[self.active][(subgroup, setting)]
        except KeyError:
            raise powercfg.PowercfgError(
                "This computer's power plan does not have that setting.")
        return powercfg.PlanValue(scheme=self.active, ac=ac, dc=dc)

    def write_plan_value(self, subgroup, setting, *, ac=None, dc=None,
                         scheme="SCHEME_CURRENT"):
        plan = self.active if scheme == "SCHEME_CURRENT" else scheme
        slot = self.values[plan][(subgroup, setting)]
        if ac is not None:
            slot[0] = ac
        if dc is not None:
            slot[1] = dc
        cmd = powercfg.join_commands(powercfg.plan_value_commands(
            subgroup, setting, ac=ac, dc=dc, scheme=scheme))
        self.commands.append(cmd)
        return cmd

    def list_plans(self):
        return [powercfg.Plan(g, n, g == self.active)
                for g, n in self.names.items() if g in self.values or g == CUSTOM]

    def set_active_plan(self, guid):
        self.active = guid
        self.values.setdefault(guid, {k: list(v) for k, v in
                                      self.values[BALANCED].items()})
        cmd = " ".join(powercfg.set_active_command(guid))
        self.commands.append(cmd)
        return cmd


@pytest.fixture
def fake_plans(monkeypatch):
    fake = FakePlans()
    for fn in ("read_plan_value", "write_plan_value", "list_plans",
               "set_active_plan"):
        monkeypatch.setattr(powercfg, fn, getattr(fake, fn))
    return fake


@pytest.fixture
def fake_os(monkeypatch):
    fake = FakeOS()
    monkeypatch.setattr(powercfg, "read_timeouts", fake.read_timeouts)
    monkeypatch.setattr(powercfg, "write_timeout", fake.write_timeout)
    return fake


@pytest.fixture
def fake_registry(monkeypatch):
    fake = FakeRegistry()
    monkeypatch.setattr(ws, "read_state", fake.read_state)
    monkeypatch.setattr(ws, "read_value", fake.read_value)
    monkeypatch.setattr(ws, "write_value", fake.write_value)
    monkeypatch.setattr(ws, "delete_value", fake.delete_value)
    monkeypatch.setattr(ws, "read_text", fake.read_text)
    return fake


@pytest.fixture
def journal(tmp_path):
    return Journal(tmp_path / "journal.jsonl")


@pytest.fixture
def monitor():
    return MonitorTimeoutTool()


@pytest.fixture
def registry():
    r = Registry()
    r.register_all([
        SystemInfoTool(), MonitorTimeoutTool(), StandbyTimeoutTool(),
        PointerSizeTool(), DoubleClickSpeedTool(), PointerSpeedTool(),
        TextCursorThicknessTool(), TextSizeTool(),
        *(cls() for cls in ALL_PLAN_TOOLS),
        *(cls() for cls in ALL_DISPLAY_TOOLS),
        *(cls() for cls in ALL_NETWORK_TOOLS),
        *(cls() for cls in ALL_STORAGE_TOOLS),
    ])
    return r


@pytest.fixture
def always_yes():
    return lambda *_args: True


@pytest.fixture
def always_no():
    return lambda *_args: False
