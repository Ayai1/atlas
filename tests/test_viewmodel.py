"""The UI's logic, tested without a display.

Everything the window can do is exercised here. If these pass, the only thing
left that can break in app.py is the drawing.
"""

import pytest

from ui.viewmodel import ViewModel


@pytest.fixture
def vm(registry, journal, fake_os):
    return ViewModel(registry=registry, journal=journal)


class TestSearch:
    def test_plain_english_finds_the_tool(self, vm):
        matches = vm.search("my screen keeps going dark")
        assert matches
        assert matches[0].name == "power.monitor_timeout"
        assert matches[0].badge == "changes a setting"
        assert 0 < matches[0].confidence <= 100

    def test_read_only_tools_are_badged_differently(self, vm):
        assert vm.search("how much memory")[0].badge == "read only"

    def test_nonsense_returns_nothing(self, vm):
        assert vm.search("qwertyuiop asdfgh") == []

    def test_empty_query_returns_nothing(self, vm):
        assert vm.search("") == []

    def test_all_tools_lists_everything(self, vm, registry):
        assert len(vm.all_tools()) == len(registry)


class TestOpeningATool:
    def test_shows_the_current_value(self, vm, fake_os):
        view = vm.open_tool("power.monitor_timeout")
        assert view.current_value == str(fake_os.state["monitor"]["ac"])
        assert view.argument_name == "minutes"
        assert (view.minimum, view.maximum) == (0, 300)
        assert view.error is None

    def test_read_only_tool_has_no_current_value(self, vm):
        view = vm.open_tool("system.info")
        assert view.is_mutating is False
        assert view.current_value == ""

    def test_unreadable_setting_surfaces_an_error_not_a_crash(
        self, vm, monkeypatch
    ):
        from windows import powercfg
        def explode(_kind):
            raise powercfg.PowercfgError("powercfg is a Windows tool")
        monkeypatch.setattr(powercfg, "read_timeouts", explode)
        view = vm.open_tool("power.monitor_timeout")
        assert view.error and "Windows" in view.error


class TestBadInputNeverReachesTheMachine:
    @pytest.mark.parametrize("bad,expected", [
        ("abc", "not a whole number"),
        ("", "Enter a value"),
        ("-5", "below minimum"),
        ("9999", "above maximum"),
        ("3.5", "not a whole number"),
    ])
    def test_rejected_with_a_readable_message(self, vm, fake_os, bad, expected):
        preview, error = vm.build_preview("power.monitor_timeout", bad)
        assert preview is None
        assert expected in error
        assert fake_os.commands == []

    def test_error_message_does_not_leak_the_tool_name(self, vm):
        _preview, error = vm.build_preview("power.monitor_timeout", "-5")
        assert "power.monitor_timeout" not in error

    def test_good_input_produces_a_card(self, vm):
        preview, error = vm.build_preview("power.monitor_timeout", "30")
        assert error is None
        assert preview.command == "powercfg /change monitor-timeout-ac 30"
        assert preview.current_value == "10 minutes"
        assert preview.new_value == "30 minutes"


class TestApplying:
    def test_applies_and_reports(self, vm, fake_os):
        preview, _ = vm.build_preview("power.monitor_timeout", "30")
        outcome = vm.apply("power.monitor_timeout", "30", preview)
        assert outcome.ok
        assert fake_os.state["monitor"]["ac"] == 30
        assert outcome.command == "powercfg /change monitor-timeout-ac 30"
        assert outcome.undo_available
        assert "30 minutes" in outcome.explanation

    def test_stale_card_is_refused(self, vm, fake_os):
        """If the setting moves between drawing the card and pressing Apply,
        the change must not go through silently."""
        preview, _ = vm.build_preview("power.monitor_timeout", "30")
        fake_os.state["monitor"]["ac"] = 45      # changed behind our back
        outcome = vm.apply("power.monitor_timeout", "30", preview)
        assert outcome.ok is False
        assert "changed on your computer" in outcome.explanation
        assert fake_os.state["monitor"]["ac"] == 45   # left alone

    def test_os_refusal_is_reported_not_raised(self, vm, monkeypatch):
        from windows import powercfg
        preview, _ = vm.build_preview("power.monitor_timeout", "30")
        def refuse(*_a, **_k):
            raise powercfg.PowercfgError("Windows refused: needs administrator")
        monkeypatch.setattr(powercfg, "write_timeout", refuse)
        outcome = vm.apply("power.monitor_timeout", "30", preview)
        assert outcome.ok is False
        assert "administrator" in outcome.explanation

    def test_unexpected_crash_is_contained(self, vm, monkeypatch):
        from windows import powercfg
        preview, _ = vm.build_preview("power.monitor_timeout", "30")
        monkeypatch.setattr(
            powercfg, "write_timeout",
            lambda *a, **k: (_ for _ in ()).throw(OSError("disk on fire")),
        )
        outcome = vm.apply("power.monitor_timeout", "30", preview)
        assert outcome.ok is False
        assert "Nothing was changed" in outcome.explanation


class TestUndo:
    def test_undo_from_the_ui_restores_the_value(self, vm, fake_os):
        original = fake_os.state["monitor"]["ac"]
        preview, _ = vm.build_preview("power.monitor_timeout", "30")
        vm.apply("power.monitor_timeout", "30", preview)
        assert vm.has_undo()

        outcome = vm.undo_last()
        assert outcome.ok
        assert fake_os.state["monitor"]["ac"] == original
        assert vm.has_undo() is False

    def test_undo_with_nothing_done_is_a_message_not_a_crash(self, vm):
        outcome = vm.undo_last()
        assert outcome.ok is False
        assert "nothing to undo" in outcome.explanation.lower()


class TestHistory:
    def test_empty_at_first(self, vm):
        assert vm.history() == []

    def test_records_change_then_undo_newest_first(self, vm, fake_os):
        preview, _ = vm.build_preview("power.monitor_timeout", "30")
        vm.apply("power.monitor_timeout", "30", preview)
        vm.undo_last()

        rows = vm.history()
        assert rows[0].is_undo_record is True        # newest first
        assert rows[1].what == "Monitor Timeout"
        assert rows[1].detail == "10 -> 30"
        assert rows[1].undone is True


class TestSystemInfo:
    def test_returns_rows_and_an_explanation(self, vm):
        outcome = vm.system_info()
        assert outcome.ok
        assert outcome.rows
        assert outcome.explanation
        assert outcome.undo_available is False
