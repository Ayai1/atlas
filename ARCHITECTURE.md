# Atlas — Architecture

A local-first AI operating system companion.

**Status:** Early development
**Platform target:** Windows 10/11 first. Linux and macOS later, behind the same tool interface.

---

## 1. What Atlas is

Atlas is a library of safe, reversible, self-explaining operations on your own computer, with a small local language model on top that translates plain English into a call to one of them.

The library is the product. The model is a convenience layer and is swappable.

## 2. Who it is for

Atlas is not built for developers or system administrators. It is built for the person who:

- uses their computer heavily and hits real friction with it
- is smart enough to know something is wrong and could be better
- does not trust themselves to change a setting correctly
- finds BIOS and registry editing frightening, not merely confusing
- blames themselves when Windows search fails
- owns one mid-spec machine, cannot upgrade it, and sometimes has to lend it to someone else
- has no IT department and nobody to ask

The product Atlas sells this person is **not automation. It is confidence.** They do not want a computer that acts without them. They want to stop being afraid of their own machine.

Every design decision below follows from that sentence.

## 3. Non-negotiable principles

These are constraints on the codebase, not aspirations. If a feature cannot be built without breaking one of these, the feature does not ship.

**P1 — Never a black box.**
Every operation returns a human-readable explanation of what it did and why, authored by us in Python. The user is never told less than what actually happened.

**P2 — The model never generates commands.**
The language model selects a tool from a registry and fills in typed parameters. It never emits shell, PowerShell, registry paths, or code that reaches the OS. Every command that runs is one we wrote and tested.

**P3 — Mutating operations are reversible by construction.**
A tool that changes state must read and record the prior state *before* changing it. If it cannot, it is read-only or it does not ship.

**P4 — Read before write, always.**
No operation writes a value without first querying the current one. This is what makes P3 possible and what makes explanations accurate.

**P5 — Nothing mutates without explicit confirmation.**
The user sees the plain-English action *and* the exact command, then approves. This holds even though P2 means the model cannot invent commands, because the model can still choose the wrong tool.

**P6 — Local-first, modest hardware.**
No network required for any core function. No account. No telemetry. Must be usable on the low-end laptop our target user actually owns.

**P7 — Explanations are authored, not generated.**
The text the user reads about what happened comes from `ToolResult.explanation`, written by us. The model may wrap it in conversation. It may never replace it or paraphrase the outcome.

## 4. Layers

```
┌──────────────────────────────────────────────────────────┐
│  Interface                                               │
│  Phase 1: CLI (development + testing scaffold)           │
│  Phase 3: GUI (the surface the real user ever sees)      │
└───────────────────────────┬──────────────────────────────┘
                            │  intent (plain English)
┌───────────────────────────▼──────────────────────────────┐
│  Orchestrator                                            │
│  shortlist candidate tools → model picks tool + args      │
│  → validate → preview → confirm → execute → journal       │
│  OPTIONAL. The layers below work with no model at all.   │
└───────────────────────────┬──────────────────────────────┘
                            │  ToolCall(name, args)
┌───────────────────────────▼──────────────────────────────┐
│  Registry                                                │
│  namespaced tool catalogue + parameter schemas            │
└───────────────────────────┬──────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────┐
│  Tools            deterministic, tested, no AI            │
│  system.info  power.monitor_timeout  display.brightness   │
│  Each declares: safety level, schema, preview, execute,   │
│  undo, and its own explanation text.                      │
└───────────────────────────┬──────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────┐
│  OS Adapter                                              │
│  windows/  powercfg · PowerShell · ms-settings · registry │
│  Single place where the OS is actually touched.           │
└───────────────────────────┬──────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────┐
│  Undo Journal                                            │
│  append-only record of prior state for every mutation     │
└──────────────────────────────────────────────────────────┘
```

The important property: **cut the Orchestrator off and everything below still works.** That is how Atlas is built and tested in phase 1, and it is why a disappointing local model cannot sink the project.

## 5. The tool contract

This is the core of the codebase. Getting it right at tool #1 is free; retrofitting it at tool #20 will not happen.

```python
# engine/tool.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Safety(Enum):
    READ_ONLY = "read_only"   # cannot change machine state
    MUTATING = "mutating"     # changes state; requires confirm + undo


@dataclass
class ToolResult:
    """What every tool returns. `explanation` is mandatory (P1, P7)."""
    title: str
    data: dict[str, Any]
    explanation: str
    command_run: str | None = None      # exact command, shown to user
    reversible: bool = False
    undo_token: str | None = None       # journal entry id


@dataclass
class Preview:
    """Shown to the user before a mutation runs (P5)."""
    summary: str          # plain English: "Screen will turn off after 15 min"
    command: str          # exact command that will execute
    current_value: str    # what it is now (P4)
    new_value: str
    reversible: bool


@dataclass
class Parameter:
    name: str
    type: type
    description: str
    required: bool = True
    minimum: float | None = None
    maximum: float | None = None
    choices: list[Any] | None = None


class Tool(ABC):
    name: str                       # "power.monitor_timeout"
    category: str                   # "power"
    description: str                # used for model routing + shortlisting
    safety: Safety = Safety.READ_ONLY
    parameters: list[Parameter] = []

    # ---- required of every tool -------------------------------------
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        ...

    # ---- required of MUTATING tools only ---------------------------
    def preview(self, **kwargs) -> Preview:
        raise NotImplementedError

    def undo(self, undo_token: str) -> ToolResult:
        raise NotImplementedError

    # ---- validation: never trust the caller (P2 defence) -----------
    def validate(self, **kwargs) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for p in self.parameters:
            if p.name not in kwargs:
                if p.required:
                    raise ValueError(f"{self.name}: missing '{p.name}'")
                continue
            v = kwargs[p.name]
            if not isinstance(v, p.type):
                raise ValueError(
                    f"{self.name}: '{p.name}' must be {p.type.__name__}"
                )
            if p.choices is not None and v not in p.choices:
                raise ValueError(f"{self.name}: '{p.name}' must be one of {p.choices}")
            if p.minimum is not None and v < p.minimum:
                raise ValueError(f"{self.name}: '{p.name}' below minimum {p.minimum}")
            if p.maximum is not None and v > p.maximum:
                raise ValueError(f"{self.name}: '{p.name}' above maximum {p.maximum}")
            clean[p.name] = v
        return clean
```

`validate()` lives in the tool, never in the prompt. The tool rejects bad input regardless of whether a human, a test, or a model sent it. A model that hallucinates a monitor timeout of `-5` gets a `ValueError`, not a broken machine.

## 6. Execution pipeline for a mutating action

```
1. User types: "make my screen stay on longer"
2. Registry shortlists ~10 candidate tools by description match
3. Model picks    power.monitor_timeout, {minutes: 30}
4. tool.validate()          → reject bad args here, before anything runs
5. tool.preview()           → reads CURRENT value from OS   (P4)
6. Show user: summary + exact command + current → new
7. User confirms                                            (P5)
8. Journal.record(prior_state)                              (P3)
9. tool.execute()
10. Return ToolResult with authored explanation + undo_token (P1, P7)
11. `atlas undo` is now available for this action
```

Steps 4, 5, 7, 8 are the product. Steps 2 and 3 are the convenience.

If the model's confidence is low, **do not guess** — return the top three candidates and let the user pick. For our target user, "I think you mean one of these three" builds more trust than a confident wrong action.

## 7. Model layer

**Job:** intent → `(tool_name, arguments)`. Nothing else. This is standard tool calling / function calling.

**Why routing and not generation:** a 1–3B model running on our target user's laptop is not reliable enough to author correct `powercfg` or registry operations, and being wrong here damages someone's only computer. Choosing from a shortlist of ten described functions is a task small models handle acceptably.

**Runtime:** Ollama or `llama.cpp` bindings, so the model file is swappable without touching Atlas.

**Tiers:**

| Tier | Model size | Role |
|---|---|---|
| Floor | 1–3B local | Default. Routing only. Must work on 8 GB RAM, no GPU. |
| Better | 7–8B local | Optional for users with the hardware. Better disambiguation. |
| None | — | CLI / GUI menus. Full functionality, no natural language. |

**Scaling the registry:** flat routing across a large tool set degrades badly on small models — at ~200 tools a 3B model starts guessing. Mitigation, built in from the start:

1. Namespace tools by category (`power.*`, `display.*`, `network.*`).
2. Retrieve a shortlist of ~10 candidates by matching the user's phrasing against tool descriptions (keyword/embedding match, not the LLM).
3. Give the model only the shortlist.
4. Below a confidence threshold, present options instead of acting.

## 8. OS adapter — Windows surface preference

Touch the OS in exactly one layer, and prefer documented surfaces in this order:

1. **Purpose-built CLI utilities** — `powercfg`, `netsh`, `dism`. Documented, stable, scriptable, easy to read back.
2. **PowerShell cmdlets** — `Get-`/`Set-` pairs give read-before-write almost for free.
3. **`ms-settings:` URIs** — when the honest answer is "open the right page for you." Zero risk, still genuinely useful to our user, who mostly cannot *find* the setting.
4. **Registry** — last resort. Only with the prior value read and journaled first, and only for keys we have documented and tested.

Never in v1: BIOS/UEFI writes, kernel drivers, anything without a tested revert path.

## 9. Undo journal

Append-only JSON Lines at `%LOCALAPPDATA%\Atlas\journal.jsonl`.

```json
{"id": "a3f1c8", "ts": "2026-08-02T14:03:11", "tool": "power.monitor_timeout",
 "args": {"minutes": 30}, "prior": {"minutes": 10},
 "command": "powercfg /change monitor-timeout-ac 30", "undone": false}
```

- Written **before** `execute()`, not after. A crash mid-operation must still leave a revert path.
- `atlas undo` reverts the most recent entry; `atlas history` lists them.
- Never rewritten, only appended. Undoing appends a new entry.

This file is also the honest answer to "what has Atlas done to my computer?" — a question our target user deserves to be able to ask.

## 10. Directory layout

```
engine/
  tool.py           Tool, Safety, Parameter, Preview
  tool_result.py    ToolResult — explanation is mandatory
  registry.py       registration, namespacing, shortlist retrieval
  journal.py        append-only undo journal
  executor.py       the safe-execution pipeline
  renderer.py       ToolResult -> terminal output
windows/
  powercfg.py       power timeouts, locale-resistant parsing
  winsettings.py    per-user registry values + SystemParametersInfo
tools/
  system/system_info.py        read-only hardware report
  power/timeouts.py            screen and sleep timeouts
  accessibility/settings.py    pointer, text, click speed, caret
ui/
  viewmodel.py      all UI logic, no tkinter import
  app.py            the tkinter window (drawing only)
  theme.py widgets.py
main.py             CLI dispatcher, nothing else
run_ui.py           launches the window
tests/
```

`main.py` holds no presentation logic. The formatting loop currently in it moves to `core/renderer.py`, or it gets copy-pasted into every future tool.

## 11. Out of scope for v1

Named explicitly so scope creep has to argue with a document:

- **BIOS/UEFI configuration** — highest-value idea in the manifesto, highest risk of bricking a machine. Needs the safety framework to be mature and battle-tested first.
- **Guest mode / private-session handover** — genuinely valuable, but it is a separate product touching accounts, credential stores, and browser profiles.
- **Filesystem search replacement** — real pain, real scope. Phase 4.
- **Automatic file organization** — Phase 4, and must be suggest-then-confirm, never silent.
- **PATH / environment / version management** — Phase 4.
- **Cross-platform support** — the `os/` adapter boundary exists so this is possible later. Not now.

## 12. Open questions

- Which mutations need admin elevation, and how is that surfaced without training the user to click through UAC unthinkingly?
- Shortlist retrieval: keyword matching (zero dependencies, weaker) or local embeddings (better, heavier — conflicts with P6)?
- Where does "explain what this setting does" live — a static authored knowledge base per tool, or model-generated? P7 argues strongly for authored.
- Confidence threshold for routing: needs a labelled set of real phrasings to calibrate against. Worth collecting from day one.
- **Localization of CLI output.** Parsing `powercfg` text depends on English strings — `"Current AC Power Setting Index"` does not exist on a non-English Windows install. Prefer PowerShell/WMI where a typed value can be read back instead of scraped. This will have to be resolved before shipping to strangers (§7 of the roadmap's definition), since our target user is not assumed to be running en-US.
