"""End-to-end: the pipeline, and undo restoring the exact prior value."""

import pytest

from engine import executor
from engine.executor import Cancelled


class TestConfirmationGate:
    """P5 — nothing mutates without the user saying yes."""

    def test_declining_changes_nothing(self, monitor, journal, fake_os, always_no):
        before = dict(fake_os.state["monitor"])
        with pytest.raises(Cancelled):
            executor.run(monitor, {"minutes": 45}, journal, confirm=always_no)
        assert fake_os.state["monitor"] == before
        assert fake_os.commands == []
        assert list(journal.entries()) == []

    def test_accepting_applies_the_change(self, monitor, journal, fake_os, always_yes):
        executor.run(monitor, {"minutes": 45}, journal, confirm=always_yes)
        assert fake_os.state["monitor"]["ac"] == 45

    def test_preview_command_matches_what_runs(self, monitor, journal, fake_os, always_yes):
        preview = monitor.preview(minutes=45)
        result = executor.run(monitor, {"minutes": 45}, journal, confirm=always_yes)
        assert preview.command == result.command_run == fake_os.commands[-1]

    def test_invalid_input_is_rejected_before_the_os_is_touched(
        self, monitor, journal, fake_os, always_yes
    ):
        with pytest.raises(ValueError):
            executor.run(monitor, {"minutes": -1}, journal, confirm=always_yes)
        assert fake_os.commands == []
        assert list(journal.entries()) == []


class TestUndo:
    """P3 — the prior value comes back exactly."""

    def test_undo_restores_exact_prior_value(
        self, registry, journal, fake_os, always_yes
    ):
        tool = registry.get("power.monitor_timeout")
        original = fake_os.state["monitor"]["ac"]

        executor.run(tool, {"minutes": 90}, journal, confirm=always_yes)
        assert fake_os.state["monitor"]["ac"] == 90

        executor.undo_last(registry, journal)
        assert fake_os.state["monitor"]["ac"] == original

    def test_battery_setting_is_never_touched(
        self, registry, journal, fake_os, always_yes
    ):
        dc_before = fake_os.state["monitor"]["dc"]
        tool = registry.get("power.monitor_timeout")
        executor.run(tool, {"minutes": 90}, journal, confirm=always_yes)
        executor.undo_last(registry, journal)
        assert fake_os.state["monitor"]["dc"] == dc_before

    def test_undo_twice_refuses_the_second_time(
        self, registry, journal, fake_os, always_yes
    ):
        tool = registry.get("power.monitor_timeout")
        executor.run(tool, {"minutes": 90}, journal, confirm=always_yes)
        executor.undo_last(registry, journal)
        with pytest.raises(LookupError, match="nothing to undo"):
            executor.undo_last(registry, journal)

    def test_undo_with_nothing_done_is_a_clean_error(self, registry, journal):
        with pytest.raises(LookupError, match="nothing to undo"):
            executor.undo_last(registry, journal)

    def test_undo_unwinds_several_changes_in_reverse(
        self, registry, journal, fake_os, always_yes
    ):
        monitor = registry.get("power.monitor_timeout")
        sleep = registry.get("power.sleep_timeout")
        start = (fake_os.state["monitor"]["ac"], fake_os.state["standby"]["ac"])

        executor.run(monitor, {"minutes": 25}, journal, confirm=always_yes)
        executor.run(sleep, {"minutes": 120}, journal, confirm=always_yes)
        assert (fake_os.state["monitor"]["ac"], fake_os.state["standby"]["ac"]) == (25, 120)

        executor.undo_last(registry, journal)     # undoes sleep
        assert fake_os.state["standby"]["ac"] == start[1]
        executor.undo_last(registry, journal)     # undoes monitor
        assert fake_os.state["monitor"]["ac"] == start[0]

    def test_undo_specific_id(self, registry, journal, fake_os, always_yes):
        monitor = registry.get("power.monitor_timeout")
        original = fake_os.state["monitor"]["ac"]
        result = executor.run(monitor, {"minutes": 77}, journal, confirm=always_yes)
        executor.undo_entry(registry, result.undo_token, journal)
        assert fake_os.state["monitor"]["ac"] == original


class TestJournalOrdering:
    """The old value is recorded before the change, not after."""

    def test_prior_value_is_journaled_even_if_execute_explodes(
        self, monitor, journal, fake_os, always_yes, monkeypatch
    ):
        def boom(**kwargs):
            raise RuntimeError("powercfg fell over")

        monkeypatch.setattr(monitor, "execute", boom)
        with pytest.raises(RuntimeError):
            executor.run(monitor, {"minutes": 45}, journal, confirm=always_yes)

        entry = journal.last_undoable()
        assert entry is not None, "a crash must still leave a revert path"
        assert entry.prior == {"minutes": 10}


class TestReadOnlyToolsSkipTheGate:
    def test_system_info_needs_no_confirmation(self, registry, journal):
        result = executor.run(registry.get("system.info"), journal=journal)
        assert result.explanation
        assert result.undo_token is None
        assert list(journal.entries()) == []      # reading is not recorded
