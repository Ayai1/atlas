# Changelog

## [0.2.0] — Unreleased

Accessibility settings, and the safety framework that makes them reversible.

### Added
- **Display** (`tools/display/settings.py`) — brightness (WMI, `windows/display.py`;
  floor of 10% so the screen can never be dimmed past seeing the undo),
  adaptive brightness, app and taskbar dark/light mode, transparency. Theme
  changes broadcast `WM_SETTINGCHANGE` so they apply immediately.
- **Network** (`tools/network/settings.py`) — `network.status`, a read-only
  report built on typed PowerShell output that says whether a problem is the
  computer, the router or the internet; and `network.proxy`, which switches an
  existing manual proxy off or on but never sets an address.
- **Storage** (`tools/storage/settings.py`) — `storage.disk_usage` (read-only),
  and Storage Sense on/off, schedule, temp-file cleanup and Recycle Bin
  retention. "Delete old Downloads" is deliberately not offered: the setting
  is reversible, the deletions are not.
- `tools/registry_choice.py` — shared base for per-user settings with named
  options; undo removes values Windows never had.
- `atlas run <tool>` for any read-only report.
- **Hidden power settings** (`tools/power/plan_settings.py`) — eleven settings
  that Windows 11's Settings app does not expose: lid close action, power
  button action, wake timers, USB selective suspend, Wi-Fi power saving,
  hibernate-after, maximum processor state, critical battery action, low
  battery warning level, hard disk timeout, and the active power plan. Each
  can target plugged in, on battery, or both. None needs administrator rights.
- **Generic power-plan adapter** (`windows/powercfg.py`) — read and write any
  setting inside a plan. Reads use `/qh`, because `/query` silently prints
  nothing for settings Windows marks hidden. Writes name the plan GUID the
  value was read from, so undo cannot land on the wrong plan if the user
  switches plans in between.
- **Accessibility settings** (`tools/accessibility/settings.py`) — pointer size,
  text scale, double-click speed, pointer speed and text-cursor thickness.
  All are per-user values, so **none requires administrator rights**.
- **Per-user settings adapter** (`windows/winsettings.py`) — registry read and
  write, plus `SystemParametersInfoW` so a change takes effect immediately
  rather than after sign-out. Only SPI constants verified against Microsoft's
  documentation are used.
- **Power settings** (`tools/power/timeouts.py`) — screen and sleep timeouts.
- **powercfg adapter** (`windows/powercfg.py`) — handles hex-seconds versus
  minutes, and falls back to positional parsing on non-English Windows.
- **Safe execution pipeline** (`engine/executor.py`) — validate, read current,
  preview, confirm, journal, execute. In that order, no shortcuts.
- **Undo journal** (`engine/journal.py`) — append-only JSONL, written *before*
  a change is applied so a crash still leaves a revert path.
- **Registry with shortlist retrieval** (`engine/registry.py`) — keyword
  narrowing, no model. Refuses to register a mutating tool that lacks
  `preview()`, `undo()` or `read_current()`.
- **Renderer** (`engine/renderer.py`) — all presentation moved out of `main.py`.
- **Window** (`ui/`) — plain-language input, confirmation card, history and
  one-step undo. Logic lives in `viewmodel.py` with no tkinter import, so it is
  testable without a display.
- **CLI** — `info`, `list`, `find`, `show`, `set`, `undo`, `history`, `gui`.
- 270 tests, covering argument rejection, revert correctness, journal ordering
  under failure, retrieval accuracy on real phrasings, and the full window flow.

### Changed
- `engine/tool.py` — `Tool` now carries a safety level, typed and bounded
  parameters, and `preview()` / `undo()` / `read_current()` for anything that
  changes state. `validate()` runs for every caller, so bounds apply equally to
  a human, a test, and a language model.
- `engine/tool_result.py` — keeps `success` and `warnings`; adds `command_run`,
  `reversible` and `undo_token`. A `ToolResult` can no longer be constructed
  without an explanation.
- `tools/system/system_info.py` — keeps the original CPU-from-registry and
  GPU-from-PowerShell detection, and adds a plain-language reading of what the
  numbers mean for the person using the machine.
- `pyproject.toml` — declares packages explicitly. Without this, setuptools'
  flat-layout discovery sees every top-level folder and refuses to build.

### Fixed
- The non-English `powercfg` fallback needed five hex values, which only
  numeric settings print. Choice settings (lid action, wake timers, ...) print
  two, so it now takes the last two in every case.
- Result warnings were never shown in the terminal; they now are. Multi-step
  commands are shown one per line.
- A setting Windows has never stored no longer reads as an error. An absent
  value means the documented default (pointer 32 px, text 100%, double-click
  500 ms, pointer speed 10, caret 1 px), and the confirmation card labels it
  as such. Undo removes a value we created rather than leaving ours behind, so
  the registry returns to exactly its prior state.

### Notes
- No language model yet, by design. The library is built and tested first;
  routing is the next phase in `ROADMAP.md`.
- `powercfg` output parsing is locale-dependent. Handled with a fallback, but
  the typed PowerShell route is the real fix before shipping.

## [0.1.0]

Initial scaffolding: `Tool`, `ToolResult`, and a system information tool.
