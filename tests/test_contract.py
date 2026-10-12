"""The safety contract must hold. These are the tests that matter most."""

import pytest

from engine.registry import Registry
from engine.tool import Safety, Tool, ToolResult


class TestExplanationIsMandatory:
    """P1 — a tool that cannot explain itself must not be constructible."""

    def test_result_without_explanation_is_rejected(self):
        with pytest.raises(ValueError, match="no explanation"):
            ToolResult(title="Something", data={"a": 1}, explanation="")

    def test_whitespace_explanation_is_rejected(self):
        with pytest.raises(ValueError, match="no explanation"):
            ToolResult(title="Something", explanation="   \n  ")

    def test_real_explanation_is_accepted(self):
        r = ToolResult(title="Fine", explanation="This is what happened.")
        assert r.explanation


class TestValidationRejectsBadArguments:
    """Bounds live in the tool, so they apply to humans, tests, and models."""

    def test_below_minimum(self, monitor):
        with pytest.raises(ValueError, match="below minimum"):
            monitor.validate(minutes=-5)

    def test_above_maximum(self, monitor):
        with pytest.raises(ValueError, match="above maximum"):
            monitor.validate(minutes=99999)

    def test_wrong_type(self, monitor):
        with pytest.raises(ValueError, match="must be int"):
            monitor.validate(minutes="30")

    def test_bool_is_not_an_int(self, monitor):
        # bool subclasses int in Python; True must not silently mean 1
        with pytest.raises(ValueError, match="got bool"):
            monitor.validate(minutes=True)

    def test_missing_required(self, monitor):
        with pytest.raises(ValueError, match="missing required"):
            monitor.validate()

    def test_unknown_argument(self, monitor):
        with pytest.raises(ValueError, match="unknown argument"):
            monitor.validate(minutes=30, sudo=True)

    def test_valid_input_passes_through(self, monitor):
        assert monitor.validate(minutes=30) == {"minutes": 30}

    def test_boundaries_are_inclusive(self, monitor):
        assert monitor.validate(minutes=0) == {"minutes": 0}
        assert monitor.validate(minutes=300) == {"minutes": 300}


class TestRegistryEnforcesTheContract:
    """P3 — the registry refuses tools that cannot be undone."""

    def test_mutating_tool_without_undo_is_refused(self):
        class Careless(Tool):
            name = "bad.tool"
            category = "bad"
            description = "changes things with no way back"
            safety = Safety.MUTATING

            def execute(self, **kw):
                return ToolResult(title="x", explanation="did something")

        with pytest.raises(TypeError, match="does not implement"):
            Registry().register(Careless())

    def test_read_only_tool_needs_no_undo(self):
        class Harmless(Tool):
            name = "ok.tool"
            category = "ok"
            description = "just looks"
            safety = Safety.READ_ONLY

            def execute(self, **kw):
                return ToolResult(title="x", explanation="looked at something")

        assert Registry().register(Harmless()).name == "ok.tool"

    def test_duplicate_names_refused(self, registry):
        from tools.system.system_info import SystemInfoTool
        with pytest.raises(ValueError, match="Duplicate"):
            registry.register(SystemInfoTool())

    def test_unknown_tool_raises(self, registry):
        with pytest.raises(KeyError, match="No tool named"):
            registry.get("power.nonexistent")

    def test_short_name_resolves(self, registry):
        assert registry.get("monitor_timeout").name == "power.monitor_timeout"
