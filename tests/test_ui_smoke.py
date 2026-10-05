"""Drive the whole window headlessly against a fake tkinter.

This cannot tell you the UI looks good. It does tell you every button runs,
every screen builds, and every widget option is one real tkinter accepts.
"""

import importlib
import sys

import pytest

from tests import faketk


@pytest.fixture
def app(registry, journal, fake_os):
    restore = faketk.install()
    for mod in [m for m in list(sys.modules) if m.startswith("ui")]:
        del sys.modules[mod]

    from ui.viewmodel import ViewModel
    app_mod = importlib.import_module("ui.app")

    window = app_mod.AtlasApp(ViewModel(registry=registry, journal=journal))
    window._app_mod = app_mod
    yield window

    for mod in [m for m in list(sys.modules) if m.startswith("ui")]:
        del sys.modules[mod]
    restore()


def _buttons(widget, out=None):
    out = [] if out is None else out
    if type(widget).__name__ == "Button":
        out.append(widget)
    for child in widget.winfo_children():
        _buttons(child, out)
    return out


def _texts(widget, out=None):
    out = [] if out is None else out
    t = widget.options.get("text")
    if isinstance(t, str) and t:
        out.append(t)
    for child in widget.winfo_children():
        _texts(child, out)
    return out


class TestItBuilds:
    def test_window_opens_on_the_welcome_screen(self, app):
        blob = " ".join(_texts(app))
        assert "Settings Companion" in blob
        assert "Ask in your own words" in blob

    def test_every_screen_builds_without_error(self, app):
        app.show_welcome()
        app.show_all_tools()
        app.show_history()
        app.show_system_info()
        app.show_results("nothing at all like a real query", [])

    def test_every_button_on_every_screen_is_wired(self, app):
        for screen in (app.show_welcome, app.show_all_tools,
                       app.show_history, app.show_system_info):
            screen()
            found = _buttons(app)
            assert found, f"{screen.__name__} produced no buttons"
            for b in found:
                assert callable(b.options.get("command")), \
                    f"dead button {b.options.get('text')!r} on {screen.__name__}"


class TestSearchFlow:
    def test_typing_and_finding_shows_the_tool(self, app):
        app.entry.set_text("my screen keeps going dark")
        app.on_search()
        blob = " ".join(_texts(app))
        assert "power.monitor_timeout" in blob
        assert "changes a setting" in blob

    def test_empty_search_does_nothing(self, app):
        app.entry.set_text("   ")
        app.on_search()          # must not raise

    def test_no_match_offers_a_way_out(self, app):
        app.entry.set_text("zxcvbnm qwerty")
        app.on_search()
        assert "Nothing matched that" in " ".join(_texts(app))

    def test_suggestion_chips_run(self, app):
        app.show_welcome()
        for b in _buttons(app):
            if b.options.get("text") == "Try this":
                b.invoke()
                break
        else:
            pytest.fail("no suggestion button found")
        blob = " ".join(_texts(app)).lower()
        assert any(c in blob for c in ("accessibility.", "power.", "system.")), \
            "clicking a suggestion should show at least one matching setting"


class TestChangingASetting:
    def _open(self, app):
        app.open_tool("power.monitor_timeout")

    def test_opening_shows_the_current_value(self, app, fake_os):
        self._open(app)
        blob = " ".join(_texts(app))
        assert f"{fake_os.state['monitor']['ac']} minutes" in blob

    def test_bad_value_shows_an_error_and_changes_nothing(self, app, fake_os):
        self._open(app)
        app.value_entry.set_text("abc")
        app.on_preview("power.monitor_timeout")
        assert "not a whole number" in app.error_label.options.get("text", "")
        assert fake_os.commands == []

    def test_out_of_range_is_refused(self, app, fake_os):
        self._open(app)
        app.value_entry.set_text("9999")
        app.on_preview("power.monitor_timeout")
        assert "above maximum" in app.error_label.options.get("text", "")
        assert fake_os.commands == []

    def test_cancelling_the_dialog_changes_nothing(self, app, fake_os, monkeypatch):
        before = dict(fake_os.state["monitor"])
        monkeypatch.setattr(
            app._app_mod, "ConfirmDialog",
            lambda *a, **k: type("D", (), {"approved": False})(),
        )
        self._open(app)
        app.value_entry.set_text("30")
        app.on_preview("power.monitor_timeout")
        assert fake_os.state["monitor"] == before
        assert fake_os.commands == []
        assert "Cancelled" in app.status.options["text"]

    def test_approving_applies_and_offers_undo(self, app, fake_os, monkeypatch):
        monkeypatch.setattr(
            app._app_mod, "ConfirmDialog",
            lambda *a, **k: type("D", (), {"approved": True})(),
        )
        self._open(app)
        app.value_entry.set_text("30")
        app.on_preview("power.monitor_timeout")

        assert fake_os.state["monitor"]["ac"] == 30
        blob = " ".join(_texts(app))
        assert "powercfg /change monitor-timeout-ac 30" in blob
        assert "Undo this" in blob

    def test_the_undo_button_actually_reverts(self, app, fake_os, monkeypatch):
        original = fake_os.state["monitor"]["ac"]
        monkeypatch.setattr(
            app._app_mod, "ConfirmDialog",
            lambda *a, **k: type("D", (), {"approved": True})(),
        )
        self._open(app)
        app.value_entry.set_text("30")
        app.on_preview("power.monitor_timeout")

        for b in _buttons(app):
            if b.options.get("text") == "Undo this":
                b.invoke()
                break
        else:
            pytest.fail("no undo button offered after a change")
        assert fake_os.state["monitor"]["ac"] == original


class TestConfirmDialogItself:
    def test_it_shows_the_exact_command_and_both_choices(self, app):
        preview, error = app.vm.build_preview("power.monitor_timeout", "30")
        assert error is None
        dialog = app._app_mod.ConfirmDialog(app, preview, "power.monitor_timeout")
        blob = " ".join(_texts(dialog))
        assert "powercfg /change monitor-timeout-ac 30" in blob
        assert "10 minutes" in blob and "30 minutes" in blob
        assert "Apply this change" in blob and "Cancel" in blob
        assert dialog.approved is False        # defaults to not applying

    def test_apply_sets_approved(self, app):
        preview, _ = app.vm.build_preview("power.monitor_timeout", "30")
        dialog = app._app_mod.ConfirmDialog(app, preview, "power.monitor_timeout")
        for b in _buttons(dialog):
            if b.options.get("text") == "Apply this change":
                b.invoke()
        assert dialog.approved is True

    def test_cancel_leaves_it_false(self, app):
        preview, _ = app.vm.build_preview("power.monitor_timeout", "30")
        dialog = app._app_mod.ConfirmDialog(app, preview, "power.monitor_timeout")
        for b in _buttons(dialog):
            if b.options.get("text") == "Cancel":
                b.invoke()
        assert dialog.approved is False


class TestHistoryScreen:
    def test_shows_changes_and_an_undo_button(self, app, fake_os, monkeypatch):
        monkeypatch.setattr(
            app._app_mod, "ConfirmDialog",
            lambda *a, **k: type("D", (), {"approved": True})(),
        )
        app.open_tool("power.monitor_timeout")
        app.value_entry.set_text("30")
        app.on_preview("power.monitor_timeout")

        app.show_history()
        blob = " ".join(_texts(app))
        assert "Monitor Timeout" in blob
        assert "10 -> 30" in blob
        assert any(b.options.get("text") == "Undo" for b in _buttons(app))

    def test_empty_history_says_so(self, app):
        app.show_history()
        assert "Nothing has been changed yet" in " ".join(_texts(app))


class TestErrorsAreShownNotRaised:
    def test_unreadable_setting_renders_a_message(self, app, monkeypatch):
        from windows import powercfg
        monkeypatch.setattr(
            powercfg, "read_timeouts",
            lambda k: (_ for _ in ()).throw(
                powercfg.PowercfgError("powercfg is a Windows tool")
            ),
        )
        app.open_tool("power.monitor_timeout")
        assert "Could not read this setting" in " ".join(_texts(app))
