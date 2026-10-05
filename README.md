## Summary

Builds Atlas from a single read-only tool into a library of **31 safe, reversible operations** on Windows, with the safety framework that enforces it, a command line, a window, and 271 tests. None of the operations needs administrator rights.

### Commits
1. **Safety framework and settings library**: tool contract, registry, undo journal, executor, renderer, Windows adapters, all 31 tools, CLI
2. **Window**: tkinter UI with confirmation card and history; all logic in a display-free viewmodel
3. **Test suite**: 271 tests against fake `powercfg`, registry and tkinter
4. **Docs**: architecture, roadmap, changelog, capstone documents

### Operations (28 reversible changes + 3 read-only reports)
| Category | Tools |
|---|---|
| Power (13) | screen/sleep timeouts, lid close, power button, wake timers, USB selective suspend, Wi-Fi power saving, hibernate after, max processor state, critical battery action, low battery warning, disk timeout, power plan |
| Accessibility (5) | pointer size, pointer speed, double-click speed, text cursor thickness, text size |
| Display (5) | brightness, adaptive brightness, app theme, taskbar theme, transparency |
| Network (2) | connection status (read-only), proxy on/off |
| Storage (5) | disk usage (read-only), Storage Sense on/off, schedule, temp files, Recycle Bin retention |
| System (1) | hardware info (read-only) |

### Safety decisions
- Every change goes through: validate → read current value → preview with the exact command → confirm → **journal the old value** → execute.
- The registry refuses to load a state-changing tool that lacks `preview()`, `undo()` or `read_current()`.
- Power-plan writes name the plan's GUID, so undo cannot write to the wrong plan if the user switches plans in between.
- Deliberately not offered: auto-deleting old Downloads (the setting is reversible, the deletions are not), setting critical battery to "do nothing", brightness below 10%, processor cap below 50%.

## Test plan
- [x] `python -m pytest tests -q`: 271 passed
- [x] Real change → verify with Windows' own tools → undo → verify, on Windows 11:
  - `display.brightness` 20% → 40% → 20%
  - `display.app_theme` dark → light → dark
  - `storage.storage_sense_schedule` low-space → weekly → low-space
  - `power.max_processor_state` 100% → 99% → 100%
- [x] The real run caught a bug that the fakes missed (wrong WMI argument types for brightness). It is fixed, with a regression test.
- [ ] Not yet tested on real hardware: `power.plan` (test machine has only Balanced), `network.proxy` (no proxy configured), and physical lid/battery behaviour

🤖 Generated with [Claude Code](https://claude.com/claude-code)
