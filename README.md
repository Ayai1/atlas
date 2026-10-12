# Local First AI Operating System Companion

Helping people understand, manage and control their computers.

**Status:** Early development — the safety framework, thirty-one working tools, a command line and a window.

---

## What this is

Windows has hundreds of settings, and to find one you must already know its name. Nothing tells you what a setting actually does. Almost nothing records the old value, so you cannot reliably put it back.

This is a library of **safe, reversible, self-explaining operations** on your own computer, with a small local language model on top that translates plain English into a call to one of them.

The library is the product. The model is a convenience layer, and it is swappable. Right now there is no model at all, by design — see `ROADMAP.md`.

## What it is not

It is not an assistant that does things to your computer while you watch. It never acts without showing you the exact command first, and it never makes a change it cannot undo.

**The language model can never touch your operating system.** It only selects which of our tested functions to call and fills in the arguments. Every command that runs is one we wrote and tested. A small model running locally on a cheap laptop is not reliable enough to author system commands, and being wrong damages the only computer somebody owns.

## Principles

The full list is in `ARCHITECTURE.md`. The four that matter most:

1. **Never a black box.** Every operation explains what it did, in text we wrote.
2. **The model never generates commands.** It routes; it does not author.
3. **Reversible by construction.** A tool that changes something must read the old value first, or it does not ship.
4. **Nothing changes without you saying yes**, having seen the exact command.

## Try it

```bash
pip install -r requirements.txt
python run_ui.py          # the window
python main.py info       # or the command line
```

Optionally, register a shorter command:

```bash
pip install -e .
atlas info
```

```
atlas info                                  what this computer is
atlas run network.status                    any read-only report
atlas list [category]                       every setting it can change
atlas find "I keep losing the mouse pointer"  which setting matches that
atlas show accessibility.pointer_size       what a setting does and takes
atlas set accessibility.pointer_size 64     change it (asks first)
atlas undo                                  put the last change back
atlas history                               everything that has been changed
atlas gui                                   open the window
```

A change looks like this:

```
================================================================
                   About to change a setting
================================================================
The mouse pointer becomes bigger — 64 pixels instead of 32.
Windows uses 32 by default.

setting               : accessibility.pointer_size
currently             : 32 pixels
will become           : 64 pixels
exact command         : HKCU\Control Panel\Cursors\CursorBaseSize = 64
reversible            : yes, with atlas undo
----------------------------------------------------------------
Apply this change? [y/N]
```

## What it can change

Thirty-one tools: twenty-eight reversible changes and three read-only reports. **None requires administrator rights.**

Most of the power settings are ones Windows 11's Settings app does not show at all; they live in Control Panel's *Change advanced power settings* dialog. Each can be changed for plugged in, on battery, or both (`when=on_battery`).

| Setting | What it does |
|---|---|
| `accessibility.pointer_size` | Mouse pointer size, 32–256 px |
| `accessibility.text_size` | Text scale across Windows, 100–225% |
| `accessibility.double_click_speed` | Gap allowed between clicks, 200–900 ms |
| `accessibility.pointer_speed` | Pointer speed, 1–20 |
| `accessibility.text_cursor_thickness` | Typing caret width, 1–20 px |
| `power.monitor_timeout` | Screen off after N minutes |
| `power.sleep_timeout` | Sleep after N minutes |
| `power.lid_close_action` | Do nothing / sleep / hibernate / shut down when the lid closes |
| `power.power_button_action` | What the physical power button does |
| `power.wake_timers` | Whether scheduled tasks may wake the PC from sleep |
| `power.usb_selective_suspend` | Stop Windows powering down idle USB devices |
| `power.wifi_power_saving` | How hard the Wi-Fi adapter is throttled on battery |
| `power.hibernate_after` | Hibernate after N minutes asleep |
| `power.max_processor_state` | Cap processor speed, 50–100%, for heat and fan noise |
| `power.critical_battery_action` | Sleep / hibernate / shut down at critical battery |
| `power.low_battery_level` | Battery % for the low-battery warning |
| `power.disk_timeout` | Spin down an idle hard disk after N minutes |
| `power.plan` | Switch power plan (Windows 11 removed this from Settings) |
| `display.brightness` | Built-in screen brightness, 10–100% (never low enough to hide the undo) |
| `display.adaptive_brightness` | Stop brightness changing by itself |
| `display.app_theme` | Dark or light mode for apps |
| `display.windows_theme` | Dark or light taskbar, Start and notifications |
| `display.transparency` | See-through effects on or off |
| `network.status` | Read-only: is it this computer, the router, or the internet? |
| `network.proxy` | Switch an existing manual proxy off or back on |
| `storage.disk_usage` | Read-only: how full each drive is, and whether that matters |
| `storage.storage_sense` | Windows' automatic cleanup on or off |
| `storage.storage_sense_schedule` | How often it runs |
| `storage.temp_files_cleanup` | Whether it removes leftover temporary files |
| `storage.recycle_bin_cleanup` | How long deleted files stay in the Recycle Bin |

Deliberately missing: Storage Sense's "delete old files from Downloads". The setting is reversible but the deletions are not, so Atlas will not offer it.
| `system.info` | Reads hardware and explains it in plain language |

## Tests

```bash
pip install pytest
python -m pytest tests/ -q
```

270 tests. The Windows-specific tools are tested against a fake registry and a fake `powercfg`, so the suite runs anywhere and `undo` can be proven to restore the exact prior value without needing a real Windows machine. The window is driven headlessly against a fake tkinter that rejects any widget option real tkinter would reject.

## Layout

```
engine/     the contract: tool, tool_result, registry, journal, executor, renderer
windows/    the only place the operating system is actually touched
tools/      what it can do — system, power, accessibility
ui/         viewmodel.py (all the logic) + app.py (thin tkinter view)
main.py     CLI dispatcher, nothing else
run_ui.py   launches the window
tests/
```

The UI is split so everything except the drawing is testable without a display: `ui/viewmodel.py` has no tkinter import at all.

## Where this is going

No language model yet, by design — see `ROADMAP.md`. The library of safe, tested operations comes first; routing plain English onto it is the next phase.

Read `MANIFESTO.md` for why this exists.
