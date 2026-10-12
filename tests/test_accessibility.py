"""The accessibility settings — the demo path.

Tested against a fake registry so the whole flow can be proven without a
Windows machine.
"""

import pytest

from engine import executor
from tools.accessibility.settings import (
    DoubleClickSpeedTool, PointerSizeTool, PointerSpeedTool,
    TextCursorThicknessTool, TextSizeTool,
)

ALL = [
    (PointerSizeTool, 32, 64),
    (DoubleClickSpeedTool, 500, 900),
    (PointerSpeedTool, 10, 6),
    (TextCursorThicknessTool, 1, 5),
    (TextSizeTool, 100, 150),
]


class TestEverySettingRoundTrips:
    @pytest.mark.parametrize("cls,start,target", ALL)
    def test_change_then_undo_restores_exactly(
        self, cls, start, target, journal, fake_registry, always_yes
    ):
        tool = cls()
        assert tool.read_current()["value"] == start

        result = executor.run(tool, {"value": target}, journal, confirm=always_yes)
        assert tool.read_current()["value"] == target
        assert result.explanation and result.command_run

        tool.undo(journal.last_undoable().prior)
        assert tool.read_current()["value"] == start

    @pytest.mark.parametrize("cls,start,target", ALL)
    def test_preview_matches_what_runs(self, cls, start, target, fake_registry):
        tool = cls()
        preview = tool.preview(value=target)
        assert preview.reversible
        assert str(target) in preview.command
        assert preview.summary and preview.current_value and preview.new_value


class TestBoundsAreEnforced:
    @pytest.mark.parametrize("cls,bad", [
        (PointerSizeTool, 5000), (PointerSizeTool, 0),
        (DoubleClickSpeedTool, 50), (DoubleClickSpeedTool, 100000),
        (PointerSpeedTool, 0), (PointerSpeedTool, 99),
        (TextSizeTool, 10), (TextSizeTool, 1000),
        (TextCursorThicknessTool, 0), (TextCursorThicknessTool, 500),
    ])
    def test_out_of_range_never_reaches_the_registry(
        self, cls, bad, fake_registry, journal, always_yes
    ):
        with pytest.raises(ValueError):
            executor.run(cls(), {"value": bad}, journal, confirm=always_yes)
        assert fake_registry.writes == []

    def test_text_is_not_a_number(self, fake_registry):
        with pytest.raises(ValueError, match="must be int"):
            PointerSizeTool().validate(value="big")


class TestNothingHappensWithoutConsent:
    def test_declining_leaves_the_registry_untouched(
        self, journal, fake_registry, always_no
    ):
        with pytest.raises(executor.Cancelled):
            executor.run(PointerSizeTool(), {"value": 96}, journal, confirm=always_no)
        assert fake_registry.writes == []
        assert fake_registry.read_value(PointerSizeTool().setting) == 32

    def test_a_setting_moved_behind_our_back_is_refused(
        self, journal, fake_registry, always_yes
    ):
        """The confirmation card showed 32 -> 64. If something else changes the
        value first, applying would act on a state the user never approved."""
        tool = PointerSizeTool()
        approved = tool.preview(value=64)
        fake_registry.values[(tool.setting.key, tool.setting.name)] = 48

        def confirm(fresh, _tool):
            return fresh == approved          # the executor re-previews first

        with pytest.raises(executor.Cancelled):
            executor.run(tool, {"value": 64}, journal, confirm=confirm)
        assert fake_registry.writes == []


class TestPlainEnglishFindsTheRightSetting:
    @pytest.mark.parametrize("said,expected", [
        ("I keep losing the mouse pointer", "accessibility.pointer_size"),
        ("the cursor is too small to see", "accessibility.pointer_size"),
        ("make the arrow bigger", "accessibility.pointer_size"),
        ("double clicking never works for me", "accessibility.double_click_speed"),
        ("folders do not open when I click twice", "accessibility.double_click_speed"),
        ("the text is too small to read", "accessibility.text_size"),
        ("make the font bigger everywhere", "accessibility.text_size"),
        ("the mouse moves too fast", "accessibility.pointer_speed"),
        ("I lose my place when typing", "accessibility.text_cursor_thickness"),
    ])
    def test_real_phrasings(self, registry, said, expected):
        matches = registry.shortlist(said)
        assert matches, f"nothing matched {said!r}"
        assert matches[0][0].name == expected, (
            f"{said!r} -> {matches[0][0].name}, expected {expected}"
        )


class TestExplanationsAreHumanReadable:
    @pytest.mark.parametrize("cls,target", [(c, t) for c, _s, t in ALL])
    def test_explanation_avoids_jargon(self, cls, target, fake_registry):
        text = cls().execute(value=target).explanation
        assert len(text) > 40
        for jargon in ("HKCU", "registry", "DWORD", "SPI_", "None", "Traceback"):
            assert jargon not in text, f"{cls.__name__} leaks '{jargon}'"


class TestSettingsWindowsHasNotStoredYet:
    """Windows omits these values until they are changed once. An absent value
    means the documented default, not an error."""

    def test_absent_value_reads_as_the_windows_default(self, fake_registry):
        tool = TextSizeTool()
        fake_registry.values.pop((tool.setting.key, tool.setting.name))
        state = tool.read_current()
        assert state == {"value": 100, "existed": False}

    def test_preview_says_it_is_the_default(self, fake_registry):
        tool = TextSizeTool()
        fake_registry.values.pop((tool.setting.key, tool.setting.name))
        assert "Windows default" in tool.preview(value=150).current_value

    def test_it_can_still_be_changed(self, fake_registry, journal, always_yes):
        tool = TextSizeTool()
        fake_registry.values.pop((tool.setting.key, tool.setting.name))
        executor.run(tool, {"value": 150}, journal, confirm=always_yes)
        assert tool.read_current()["value"] == 150

    def test_undo_removes_the_value_rather_than_leaving_ours(
        self, fake_registry, journal, always_yes
    ):
        tool = TextSizeTool()
        key = (tool.setting.key, tool.setting.name)
        fake_registry.values.pop(key)

        executor.run(tool, {"value": 150}, journal, confirm=always_yes)
        assert key in fake_registry.values

        result = tool.undo(journal.last_undoable().prior)
        assert key not in fake_registry.values, \
            "undo must remove a value Windows never had, not leave ours behind"
        assert "removed" in result.command_run
        assert tool.read_current()["value"] == 100

    def test_an_existing_value_is_restored_not_removed(
        self, fake_registry, journal, always_yes
    ):
        tool = PointerSizeTool()
        key = (tool.setting.key, tool.setting.name)
        assert key in fake_registry.values          # exists at 32

        executor.run(tool, {"value": 96}, journal, confirm=always_yes)
        tool.undo(journal.last_undoable().prior)
        assert fake_registry.values[key] == 32
