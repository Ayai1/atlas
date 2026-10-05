# Demo script — Mid-Term Review

**Runtime: 5 minutes.** Built around accessibility settings, because the pain is real, the effect is visible from the back of the room, and every change is reversible.

**The framing sentence, say it early:** *"We are demonstrating the guarantee, not the catalogue."*

---

## How to run it at all

You never run `settings.py`, or any file inside `engine/`, `tools/`, `windows/` or `ui/`. Those are modules the program imports. There are exactly two entry points, both in the project root:

```
python main.py     the command line
python run_ui.py   the window
```

**Do this once before the demo** so you can type `atlas` instead of `python main.py` — it reads far better on screen:

```
cd C:\Projects\Atlas
pip install -e .
```

That registers `atlas` as a real command, and every line in this script works verbatim. Without it, replace `atlas` with `python main.py` everywhere.

Quick check that it worked:

```
atlas list accessibility
```

---

## Before you start — 15 minutes of setup

- [ ] **Test every step on the actual machine.** These are registry and system-parameter changes; I could not test them on Windows. Run the whole script twice before you rely on it.
- [ ] **Set text scaling back to 100%** and pointer size to 32 so the "before" is normal.
- [ ] Open **Windows Settings → Accessibility → Mouse pointer and touch** in a second window. You will switch to it to prove the change is real.
- [ ] Increase your terminal font size so it reads from the back.
- [ ] **Record the whole run as a video.** The guidelines list a demo video as a recommended deliverable, and lab machines fail.
- [ ] Take screenshots of each step as a still fallback.

**If a setting has never been changed on this machine**, Windows stores no value for it. That is handled: it reads as the documented default and the card says "(Windows default)". Undo then *removes* the value rather than leaving ours behind, so the registry ends up exactly as it started. Worth mentioning if a panel asks how careful the reverting is.

---

## Act 1 — The failure it fixes  *(45 seconds)*

Open Windows Settings. In its search box, type:

> **I keep losing the mouse pointer**

It finds nothing useful. Let that sit for a second.

> *"This is the actual problem. My grandmother knows exactly what is wrong. She does not know it is called 'pointer size', so Windows cannot help her."*

Now the same sentence in ours:

```
atlas find "I keep losing the mouse pointer"
```

It returns `accessibility.pointer_size` as the top match.

> *"Same sentence. No AI involved yet — this is keyword matching over descriptions we wrote. The local model will choose from this shortlist later."*

---

## Act 2 — The confirmation card  *(45 seconds)*

```
atlas set accessibility.pointer_size 64
```

Stop on the confirmation card. Point at it while you talk.

> *"Before anything happens: what it will do in plain English, the exact registry value it will write, what it is now, what it becomes, and that it can be undone. Nothing has changed yet."*

Press `y`.

The pointer visibly doubles in size on screen. **This is your best visual moment — pause and let people see it.**

---

## Act 3 — Prove it is real  *(30 seconds)*

Switch to the Windows Settings window you left open. Show the pointer size slider has moved.

> *"This is Windows' own settings page, not ours. The change is real."*

This matters more than it sounds. Panels quietly assume a student demo is a mock. This kills that.

---

## Act 4 — Undo  *(30 seconds)*

```
atlas undo
```

Pointer returns to normal. Switch to Windows Settings again — slider is back.

> *"One step. The old value was recorded before the change was applied, not after, so a crash halfway through still leaves a way back."*

---

## Act 5 — Try to break it  *(60 seconds)*

**This is the part nobody else will do. Do not skip it.**

```
atlas set accessibility.pointer_size 5000
```
> Rejected: *'value' is 5000, above maximum 256.* Nothing was touched.

```
atlas set accessibility.text_size big
```
> Rejected: *'value' needs to be a whole number.*

> *"Those limits live in the tool itself, not in a prompt. So they apply to me, to a test, and to the language model equally. If the model hallucinates a pointer size of 5000, it gets an error, not a broken machine."*

**Then the good one.** Start a change but do not confirm it:

```
atlas set accessibility.double_click_speed 900
```

Leave the prompt open. Switch to Windows Settings and change double-click speed manually. Come back and press `y`.

> It refuses. Nothing is applied.

> *"The card you approved said 500 to 900. The machine no longer matches what you agreed to, so it abandons the change rather than applying it to a state you never saw."*

---

## Act 6 — The architecture refuses bad code  *(45 seconds)*

Open `atlas/tools/accessibility/settings.py` in the editor. Comment out the `undo` method on `_RegistryTool`. Run anything:

```
atlas list
```

> `TypeError: accessibility.pointer_size is MUTATING but does not implement undo().`

> *"Reversibility is not a promise we are making. The registry refuses to load a setting that cannot be undone, so the guarantee holds for every setting we add from here."*

Uncomment it. **Practise this — do not fumble in the editor live.**

---

## Act 7 — The audit trail and the tests  *(45 seconds)*

```
atlas history
```

> *"Every change ever made to this computer, with its old value. No tool in our literature review can answer 'what has this software done to my machine?'"*

Then:

```
python -m pytest tests/ -q
```

> 127 tests, green, in under a second.

> *"About a third of the code is tests, because our claim is that changes are always reversible. One of these kills the program mid-change and proves the way back still exists."*

---

## Closing line

> *"Two mutating settings would have been thin. What we are showing is not the number of settings — it is that not one of them can exist without a tested undo. Adding the next thirty is work, not research."*

---

## The settings you now have

Seven reversible changes, one read-only report. None require administrator rights.

| Command | What it changes | Why an older user needs it |
|---|---|---|
| `accessibility.pointer_size` | Mouse pointer size, 32–256 px | Losing the pointer on screen |
| `accessibility.text_size` | Text scale, 100–225% | Text too small to read |
| `accessibility.double_click_speed` | Gap allowed between clicks, 200–900 ms | Double-click fails with shaky hands |
| `accessibility.pointer_speed` | Pointer speed, 1–20 | Pointer moves too fast to control |
| `accessibility.text_cursor_thickness` | Typing caret width, 1–20 px | Losing your place when typing |
| `power.monitor_timeout` | Screen off after N minutes | Screen darkens while reading |
| `power.sleep_timeout` | Sleep after N minutes | Computer sleeps mid-task |
| `system.info` | Reads hardware, explains it | Read-only, nothing to undo |

---

## If something fails live

- **A setting will not read** → it does not exist in the registry yet. Say so, change it once in Windows Settings, move on. The error message is deliberately clear; that *is* the product working.
- **The change does not appear on screen** → some values need a sign-out. Say it honestly, then show `atlas history` proving the value was written and journaled.
- **Anything else** → switch to the recorded video. Do not debug in front of a panel.

## Do not

- Do not demo the AI. It does not exist yet. This is the one thing that could actually damage you.
- Do not claim breadth. Seven settings is a foundation, not a library. Say so first.
- Do not run as administrator. Part of the point is that none of this needs it.
