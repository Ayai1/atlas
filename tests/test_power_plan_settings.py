"""The hidden power settings — every one must round-trip exactly.

Run against a fake powercfg that stores values per power plan, plus parser
tests on output captured from a real Windows 11 machine.
"""

import pytest

from engine import executor
from tests.conftest import BALANCED, CUSTOM, HIGH_PERF
from tools.power.plan_settings import (
    ALL_PLAN_TOOLS, CriticalBatteryActionTool, HibernateAfterTool,
    LidCloseActionTool, LowBatteryLevelTool, MaxProcessorStateTool,
    PowerButtonActionTool, PowerPlanTool, UsbSelectiveSuspendTool,
    WakeTimersTool, WifiPowerSavingTool, DiskTimeoutTool,
)
from windows import powercfg

# (tool, a value different from the fake's starting value)
SETTINGS = [
    (LidCloseActionTool, "do_nothing"),
    (PowerButtonActionTool, "shut_down"),
    (WakeTimersTool, "off"),
    (UsbSelectiveSuspendTool, "off"),
    (WifiPowerSavingTool, "maximum_performance"),
    (HibernateAfterTool, 60),
    (MaxProcessorStateTool, 99),
    (CriticalBatteryActionTool, "shut_down"),
    (LowBatteryLevelTool, 20),
    (DiskTimeoutTool, 0),
]


def _raw(fake, tool):
    return tuple(fake.values[fake.active][(tool.subgroup, tool.setting)])


class TestEverySettingRoundTrips:
    @pytest.mark.parametrize("cls,target", SETTINGS)
    def test_change_then_undo_restores_both_values(
        self, cls, target, fake_plans, journal, always_yes
    ):
        tool = cls()
        before = _raw(fake_plans, tool)

        result = executor.run(tool, {tool.arg: target}, journal, confirm=always_yes)
        assert _raw(fake_plans, tool) != before
        assert result.explanation and result.command_run and result.undo_token

        tool.undo(journal.last_undoable().prior)
        assert _raw(fake_plans, tool) == before

    @pytest.mark.parametrize("cls,target", SETTINGS)
    def test_preview_shows_exactly_what_execute_runs(
        self, cls, target, fake_plans
    ):
        tool = cls()
        preview = tool.preview(**{tool.arg: target})
        result = tool.execute(**{tool.arg: target})
        assert preview.command == result.command_run
        assert preview.reversible
        assert preview.summary and preview.current_value and preview.new_value

    @pytest.mark.parametrize("cls,target", SETTINGS)
    def test_change_is_reapplied_so_it_takes_effect_now(
        self, cls, target, fake_plans
    ):
        tool = cls()
        cmd = tool.execute(**{tool.arg: target}).command_run
        assert cmd.endswith("powercfg /setactive SCHEME_CURRENT")

    def test_every_tool_is_listed_in_the_registry(self, registry):
        for cls in ALL_PLAN_TOOLS:
            assert cls.name in registry


class TestPluggedInVersusBattery:
    def test_default_changes_both(self, fake_plans):
        tool = LidCloseActionTool()
        tool.execute(action="do_nothing")
        assert _raw(fake_plans, tool) == (0, 0)

    def test_battery_only_leaves_plugged_in_alone(self, fake_plans):
        tool = LidCloseActionTool()
        cmd = tool.execute(action="shut_down", when="on_battery").command_run
        assert _raw(fake_plans, tool) == (1, 3)
        assert "setacvalueindex" not in cmd

    def test_plugged_in_only_leaves_battery_alone(self, fake_plans):
        tool = WakeTimersTool()
        tool.execute(allow="important_only", when="plugged_in")
        assert _raw(fake_plans, tool) == (2, 0)

    def test_undo_restores_values_that_differed(self, fake_plans, journal, always_yes):
        tool = WifiPowerSavingTool()          # starts at 0 plugged in, 2 on battery
        executor.run(tool, {"mode": "maximum_saving"}, journal, confirm=always_yes)
        assert _raw(fake_plans, tool) == (3, 3)
        tool.undo(journal.last_undoable().prior)
        assert _raw(fake_plans, tool) == (0, 2)

    def test_differing_values_are_described_separately(self, fake_plans):
        preview = WakeTimersTool().preview(allow="off")
        assert "plugged in" in preview.current_value
        assert "battery" in preview.current_value

    def test_battery_only_tools_take_no_when(self, fake_plans):
        with pytest.raises(ValueError):
            LowBatteryLevelTool().validate(percent=20, when="both")


class TestUndoFindsTheRightPlan:
    def test_undo_after_switching_plan_restores_the_original_plan(
        self, fake_plans, journal, always_yes
    ):
        tool = LidCloseActionTool()
        executor.run(tool, {"action": "shut_down"}, journal, confirm=always_yes)
        fake_plans.set_active_plan(HIGH_PERF)      # user switches plan

        tool.undo(journal.last_undoable().prior)

        lid = (tool.subgroup, tool.setting)
        assert fake_plans.values[BALANCED][lid] == [1, 1]
        assert fake_plans.values[HIGH_PERF][lid] == [1, 1]   # untouched

    def test_writes_name_the_plan_rather_than_whatever_is_current(self, fake_plans):
        cmd = UsbSelectiveSuspendTool().execute(enabled="off").command_run
        assert f"/setacvalueindex {BALANCED}" in cmd


class TestBoundsAndTraps:
    @pytest.mark.parametrize("cls,bad", [
        (MaxProcessorStateTool, 10),       # below 50: unusably slow
        (MaxProcessorStateTool, 101),
        (HibernateAfterTool, -1),
        (HibernateAfterTool, 5000),
        (LowBatteryLevelTool, 2),
        (DiskTimeoutTool, 1000),
        (LidCloseActionTool, "explode"),
        (WakeTimersTool, "maybe"),
    ])
    def test_out_of_range_never_reaches_powercfg(
        self, cls, bad, fake_plans, journal, always_yes
    ):
        tool = cls()
        with pytest.raises(ValueError):
            executor.run(tool, {tool.arg: bad}, journal, confirm=always_yes)
        assert fake_plans.commands == []
        assert journal.last_undoable() is None

    def test_critical_battery_will_not_be_set_to_do_nothing(self, fake_plans):
        with pytest.raises(ValueError):
            CriticalBatteryActionTool().validate(action="do_nothing")

    def test_but_an_existing_do_nothing_is_described_and_restored(
        self, fake_plans, journal, always_yes
    ):
        key = ("SUB_BATTERY", "BATACTIONCRIT")
        fake_plans.values[BALANCED][key] = [0, 0]
        tool = CriticalBatteryActionTool()
        assert tool.read_current()["action"] == "do_nothing"

        executor.run(tool, {"action": "hibernate"}, journal, confirm=always_yes)
        tool.undo(journal.last_undoable().prior)
        assert fake_plans.values[BALANCED][key] == [0, 0]

    def test_low_battery_warning_must_come_before_critical(
        self, fake_plans, journal, always_yes
    ):
        fake_plans.values[BALANCED][("SUB_BATTERY", "BATLEVELCRIT")] = [15, 15]
        with pytest.raises(ValueError, match="critical"):
            executor.run(LowBatteryLevelTool(), {"percent": 12}, journal,
                         confirm=always_yes)
        assert journal.last_undoable() is None

    def test_hibernate_choices_carry_a_warning(self, fake_plans):
        result = LidCloseActionTool().execute(action="hibernate")
        assert any("hibernat" in w for w in result.warnings)


class TestUnits:
    def test_hibernate_minutes_are_written_as_seconds(self, fake_plans):
        tool = HibernateAfterTool()
        tool.execute(minutes=90)
        assert _raw(fake_plans, tool) == (5400, 5400)
        assert tool.read_current()["minutes"] == 90

    def test_disk_timeout_reads_back_in_minutes(self, fake_plans):
        assert DiskTimeoutTool().read_current()["minutes"] == 20


class TestPowerPlan:
    def test_switch_and_undo(self, fake_plans, journal, always_yes):
        tool = PowerPlanTool()
        executor.run(tool, {"plan": "high_performance"}, journal, confirm=always_yes)
        assert fake_plans.active == HIGH_PERF
        tool.undo(journal.last_undoable().prior)
        assert fake_plans.active == BALANCED

    def test_undo_returns_to_a_custom_plan(self, fake_plans, journal, always_yes):
        fake_plans.set_active_plan(CUSTOM)
        fake_plans.commands.clear()
        tool = PowerPlanTool()
        assert tool.read_current()["plan"] == "My custom plan"

        executor.run(tool, {"plan": "balanced"}, journal, confirm=always_yes)
        tool.undo(journal.last_undoable().prior)
        assert fake_plans.active == CUSTOM

    def test_missing_plan_is_refused_with_an_explanation(
        self, fake_plans, journal, always_yes
    ):
        with pytest.raises(ValueError, match="does not have the Power saver"):
            executor.run(PowerPlanTool(), {"plan": "power_saver"}, journal,
                         confirm=always_yes)
        assert fake_plans.commands == []


# ---- parsing real powercfg output -----------------------------------

LID_QH = """\
Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced)
  GUID Alias: SCHEME_BALANCED
  Subgroup GUID: 4f971e89-eebd-4455-a8de-9e59040e7347  (Power buttons and lid)
    GUID Alias: SUB_BUTTONS
    Power Setting GUID: 5ca83367-6e45-459f-a27b-476b1d01c936  (Lid close action)
      GUID Alias: LIDACTION
      Possible Setting Index: 000
      Possible Setting Friendly Name: Do nothing
      Possible Setting Index: 001
      Possible Setting Friendly Name: Sleep
      Possible Setting Index: 002
      Possible Setting Friendly Name: Hibernate
      Possible Setting Index: 003
      Possible Setting Friendly Name: Shut down
    Current AC Power Setting Index: 0x00000001
    Current DC Power Setting Index: 0x00000003
"""

PROC_QH = """\
Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced)
  GUID Alias: SCHEME_BALANCED
  Subgroup GUID: 54533251-82be-4824-96c1-47b60b740d00  (Processor power management)
    GUID Alias: SUB_PROCESSOR
    Power Setting GUID: bc5038f7-23e0-4960-96da-33abaf5935ec  (Maximum processor state)
      GUID Alias: PROCTHROTTLEMAX
      Minimum Possible Setting: 0x00000000
      Maximum Possible Setting: 0x00000064
      Possible Settings increment: 0x00000001
      Possible Settings units: %
    Current AC Power Setting Index: 0x00000064
    Current DC Power Setting Index: 0x00000063
"""

# What /query (not /qh) prints for a hidden setting: the scheme, then nothing.
HIDDEN_QUERY = """\
Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced)
  GUID Alias: SCHEME_BALANCED
"""

PLAN_LIST = """\

Existing Power Schemes (* Active)
-----------------------------------
Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced) *
Power Scheme GUID: 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c  (High performance)
Power Scheme GUID: 11111111-2222-3333-4444-555555555555  (Plan (copy))
"""


class TestParsing:
    def test_choice_setting(self):
        v = powercfg.parse_plan_value(LID_QH)
        assert (v.scheme, v.ac, v.dc) == (BALANCED, 1, 3)

    def test_numeric_setting(self):
        v = powercfg.parse_plan_value(PROC_QH)
        assert (v.ac, v.dc) == (100, 99)

    @pytest.mark.parametrize("sample", [LID_QH, PROC_QH])
    def test_non_english_falls_back_to_position(self, sample):
        german = (sample.replace("Current AC Power Setting Index",
                                 "Index der aktuellen Wechselstromeinstellung")
                        .replace("Current DC Power Setting Index",
                                 "Index der aktuellen Gleichstromeinstellung"))
        assert powercfg.parse_plan_value(german) == powercfg.parse_plan_value(sample)

    def test_absent_setting_says_so_instead_of_blaming_the_language(self):
        with pytest.raises(powercfg.PowercfgError, match="does not have that setting"):
            powercfg.parse_plan_value(HIDDEN_QUERY)

    def test_plan_list(self):
        plans = powercfg.parse_plan_list(PLAN_LIST)
        assert [p.name for p in plans] == ["Balanced", "High performance", "Plan (copy)"]
        assert [p.active for p in plans] == [True, False, False]

    def test_commands_only_write_what_changes(self):
        cmds = powercfg.plan_value_commands("SUB_SLEEP", "RTCWAKE", dc=0)
        assert [c[1] for c in cmds] == ["/setdcvalueindex", "/setactive"]
