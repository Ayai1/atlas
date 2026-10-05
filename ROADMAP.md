# Atlas — Roadmap

Phases are ordered by dependency, not by excitement. Each one ends in something demonstrable.

The guiding sequence: **build the safe operation library first, add the AI last.** The library is the product and it is testable without a model. If the local-model layer disappoints, Atlas is still a working tool.

---

## Phase 0 — Foundation
**Goal:** one read-only tool and one mutating tool, both running through the full safety contract.
**Estimate:** 1–2 days
**Demo sentence:** "It changed a real Windows setting, told me exactly what it ran, and undid it."

- [ ] `engine/tool.py` — `Safety`, `Parameter`, `ToolResult`, `Preview`, `Tool` ABC with `validate()`
- [ ] `engine/registry.py` — register tools, look up by name, list by category
- [ ] `engine/renderer.py` — move the formatting loop out of `main.py`
- [ ] `engine/journal.py` — append-only JSONL, `record()` / `last()` / `mark_undone()`
- [ ] Port `SystemInfoTool` onto the new base (`READ_ONLY`)
- [ ] `os/windows/powercfg.py` — read and write helpers with parsing
- [ ] First `MUTATING` tool: `power.monitor_timeout` with `preview()`, `execute()`, `undo()`
- [ ] CLI: `atlas info`, `atlas set <tool> <args>`, `atlas undo`, `atlas history`
- [ ] Repo hygiene: `CHANGELOG.md` is currently a copy of `README.md`; delete stray `main,py.txt`; pin `psutil` in `requirements.txt` and fill `pyproject.toml`

**Exit criteria:** you can change the monitor timeout, verify it changed in Windows Settings, and revert it — with no AI involved anywhere.

---

## Phase 1 — The settings library (still no model)
**Goal:** enough breadth that the tool is useful on its own merits.
**Estimate:** 3–5 weeks
**Demo sentence:** "Thirty Windows settings, every one explained, every one reversible."

- [ ] **Power** — monitor timeout, sleep timeout, active plan, hibernate, USB selective suspend, lid-close action
- [ ] **Display** — brightness, resolution, refresh rate, scaling, night light
- [ ] **Network** — list adapters, DNS servers, flush cache, metered connection, Wi-Fi profiles
- [ ] **Privacy** — telemetry level, ad ID, location, app permissions, activity history
- [ ] **Performance** — startup programs, visual effects, background apps, storage sense
- [ ] **Storage** — disk usage breakdown, temp file cleanup, recycle bin
- [ ] `undo()` implemented and *tested* for every mutating tool — no exceptions
- [ ] Authored "what this setting actually does" text per tool (feeds P1 and P7)
- [ ] Test suite: every tool's `validate()` rejects bad input; every `undo()` restores exactly
- [ ] Elevation handling: detect when admin is required, explain why, request once

**Exit criteria:** a non-technical person can be handed the CLI, given a cheat sheet, and fix six real annoyances without help.

---

## Phase 2 — Local intent router
**Goal:** plain English in, correct tool call out.
**Estimate:** 2–3 weeks
**Demo sentence:** "I typed 'my screen keeps going dark while I read' and it found the right setting."

- [ ] Ollama / `llama.cpp` integration behind a swappable interface
- [ ] Tool-calling prompt built from registry schemas
- [ ] Shortlist retrieval: user phrasing → ~10 candidate tools (no LLM in this step)
- [ ] Confidence scoring; below threshold, present three options instead of acting
- [ ] Phrasing test set — 100+ real sentences with expected tool, measure routing accuracy
- [ ] Graceful degradation: no model installed → full CLI functionality, clear message
- [ ] Benchmark on 8 GB RAM / no GPU. If the floor model cannot hit target accuracy, the answer is a better shortlist, not a bigger model.

**Exit criteria:** ≥85% correct tool selection on the phrasing test set, with the floor-tier model, on low-end hardware.

---

## Phase 3 — GUI
**Goal:** the surface the actual target user touches. Our user would never open a terminal.
**Estimate:** 3–4 weeks
**Demo sentence:** "This is what my mum could use."

- [ ] Single window: one plain-language input box
- [ ] **Action preview card** — plain English, the exact command, current → new value, Confirm / Cancel. This card is the product's whole thesis rendered on screen.
- [ ] History panel with per-action Undo
- [ ] "Explain this" expander on every action
- [ ] System info dashboard (Phase 0's read-only tool, made visual)
- [ ] Framework decision: Tauri, or Python-native (PySide/Flet). Weigh install size and RAM against P6.

**Exit criteria:** a user who has never seen a terminal completes three settings changes unaided, and can say afterwards what Atlas did.

---

## Phase 4 — The rest of the manifesto
Each of these is a phase-1-sized project. Sequence by how much pain it removes per week of work.

- [ ] **Search that works** — indexed local file search, because Windows search failing is the single most universal complaint
- [ ] **Environment doctor** — detect PATH problems, Python version conflicts, library mismatches; explain and offer fixes
- [ ] **File organization** — suggest folder structures, propose destinations for downloads. Suggest-then-confirm, never silent (P5)
- [ ] **Hardware reality check** — honest read on what the machine can and cannot run, and what would actually help

---

## Phase 5 — Shipping
**Estimate:** 2–3 weeks

- [ ] Packaged installer, no Python install required
- [ ] Code signing (unsigned binaries that edit system settings will be flagged, and should be)
- [ ] First-run explanation of what Atlas can and cannot do
- [ ] Uninstall that reverts nothing silently but offers to revert everything
- [ ] User docs written for the target demographic, not for developers
- [ ] Public repo, license, contribution guide

---

## Deferred — high value, high risk
Not abandoned. Blocked on the safety framework being mature and proven.

- **BIOS/UEFI assistance** — the most emotionally resonant idea in the manifesto. Start read-only: explain what each setting in *your* BIOS does, in plain language. Writes come much later, if ever.
- **Guest handover mode** — "let them use my laptop, without my accounts, passwords, or history." Separate product, touches credential stores and browser profiles.

---

## Definition of shipping-worthy

Atlas is ready for strangers when all of these are true:

1. Every mutating operation has a tested `undo()`.
2. No operation runs without the user seeing the exact command first.
3. It runs on 8 GB RAM with no dedicated GPU.
4. It works fully offline, with no account.
5. Uninstalling leaves the machine in a known state.
6. A non-technical person can use it without a developer nearby.
7. Nothing in the codebase lets a language model reach the OS directly.

Item 7 is the one that will be tempting to bend under deadline pressure. Do not.
