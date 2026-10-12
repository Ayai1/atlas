"""Turning results into text.

All presentation lives here so that main.py stays a dispatcher and the
formatting is not copy-pasted into every future tool. The box layout is the
one from the original main.py, kept deliberately.
"""

from __future__ import annotations

import textwrap

from engine.tool import Preview, ToolResult

WIDTH = 64
KEY_WIDTH = 22


def _rule(char: str = "=") -> str:
    return char * WIDTH


def _heading(title: str) -> list[str]:
    return [_rule(), f"{title:^{WIDTH}}", _rule()]


def _wrap(text: str, indent: str = "") -> list[str]:
    out: list[str] = []
    for para in text.strip().split("\n"):
        para = para.strip()
        if not para:
            out.append("")
            continue
        out.extend(
            textwrap.wrap(
                para, width=WIDTH, initial_indent=indent, subsequent_indent=indent
            )
        )
    return out


def _rows(data: dict) -> list[str]:
    lines: list[str] = []
    for key, value in data.items():
        label = str(key)
        if isinstance(value, (list, tuple)):
            if not value:
                lines.append(f"{label:<{KEY_WIDTH}}: -")
                continue
            lines.append(f"{label:<{KEY_WIDTH}}: {value[0]}")
            for item in value[1:]:
                lines.append(f"{'':{KEY_WIDTH}}  {item}")
        else:
            lines.append(f"{label:<{KEY_WIDTH}}: {value}")
    return lines


def _command_lines(label: str, command: str) -> list[str]:
    """One command per line, so a multi-step change can be read step by step."""
    parts = command.split(" && ")
    lines = [f"{label:<{KEY_WIDTH}}: {parts[0]}"]
    lines += [f"{'':{KEY_WIDTH}}  {p}" for p in parts[1:]]
    return lines


def render(result: ToolResult) -> str:
    """Format a ToolResult for the terminal."""
    lines = _heading(result.title)
    if result.data:
        lines += _rows(result.data)
    if result.command_run:
        lines += [""] + _command_lines("command run", result.command_run)
    lines += [""]
    lines += _wrap(result.explanation)
    for warning in result.warnings:
        lines += [""] + _wrap(f"Note: {warning}")
    if result.reversible and result.undo_token:
        lines += ["", f"Reversible. Run 'atlas undo' to put this back "
                      f"(change {result.undo_token})."]
    return "\n".join(lines)


def render_preview(preview: Preview, tool_name: str) -> str:
    """Format the confirmation card shown before a mutation.

    This is the whole product rendered as text: plain English, the literal
    command, and where the value is moving from and to.
    """
    lines = _heading("About to change a setting")
    lines += _wrap(preview.summary)
    lines += [""]
    lines += [
        f"{'setting':<{KEY_WIDTH}}: {tool_name}",
        f"{'currently':<{KEY_WIDTH}}: {preview.current_value}",
        f"{'will become':<{KEY_WIDTH}}: {preview.new_value}",
        *_command_lines("exact command", preview.command),
        f"{'reversible':<{KEY_WIDTH}}: "
        f"{'yes, with atlas undo' if preview.reversible else 'NO'}",
    ]
    lines += [_rule("-")]
    return "\n".join(lines)


def render_tool_list(tools: list, show_category: bool = True) -> str:
    if not tools:
        return "No tools found."
    lines: list[str] = []
    current = None
    for tool in tools:
        if show_category and tool.category != current:
            current = tool.category
            lines += ["", f"{current.upper()}"]
        flag = "changes settings" if tool.is_mutating else "read only"
        lines.append(f"  {tool.name:<30} {tool.description}")
        lines.append(f"  {'':<30} ({flag})")
    return "\n".join(lines).lstrip("\n")


def render_tool_detail(tool) -> str:
    lines = _heading(tool.name)
    lines += _wrap(tool.description)
    lines += [
        "",
        f"{'category':<{KEY_WIDTH}}: {tool.category}",
        f"{'safety':<{KEY_WIDTH}}: {tool.safety.value}",
        f"{'needs admin':<{KEY_WIDTH}}: {'yes' if tool.requires_admin else 'no'}",
    ]
    if tool.parameters:
        lines += ["", "Arguments:"]
        for p in tool.parameters:
            lines.append(f"  {p.describe()}")
            lines += _wrap(p.description, indent="      ")
    else:
        lines += ["", "Takes no arguments."]
    return "\n".join(lines)


def render_history(entries: list) -> str:
    if not entries:
        return "Nothing has been changed on this computer yet."
    lines = _heading("What has been changed")
    for e in entries:
        if e.kind == "undo":
            lines.append(f"  {e.ts}  {e.id}  reverted change {e.reverts}")
            continue
        status = "undone" if e.undone else "active"
        prior = ", ".join(f"{k}={v}" for k, v in e.prior.items())
        args = ", ".join(f"{k}={v}" for k, v in e.args.items())
        lines.append(f"  {e.ts}  {e.id}  {e.tool}  {prior} -> {args}  [{status}]")
    return "\n".join(lines)
