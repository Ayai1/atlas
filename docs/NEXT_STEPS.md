# Atlas — Next Steps

**Context:** academic panel in 1 day. Target is "good level of progress," with shipping-worthy as the end-of-project goal.

---

## The strategy for today

You cannot build a settings *library* in one day. You can build one complete **vertical slice** — a single setting that travels the entire safety pipeline end to end. That is a far stronger panel demo than ten half-finished tools, because it proves the architecture rather than describing it.

The demo you are aiming for is three commands long:

```
atlas info                          → reads the machine, explains what it found
atlas set power.monitor_timeout 30  → shows the exact command, asks, changes it
atlas undo                          → puts it back
```

Then you open Windows Settings and show the value actually changed. That is the whole thesis, live, in ninety seconds.

Cut scope in this order if you fall behind: brightness tool → history command → renderer polish. **Never cut `undo`.** Undo is the argument.

---

## Hour-boxed plan (~9 hours)

### 0:00–0:30 — Repo hygiene
- [ ] Delete `main,py.txt` (stray duplicate of `main.py`)
- [ ] Rewrite `CHANGELOG.md` — it is currently a verbatim copy of `README.md`
- [ ] `requirements.txt`: pin `psutil`
- [ ] Fill `pyproject.toml` — name, version, entry point `atlas = "main:main"`
- [ ] Commit. A clean `git log` is visible evidence to a panel.

### 0:30–2:00 — Core contract
- [ ] Create `atlas/core/tool.py` — paste the `Safety`, `Parameter`, `ToolResult`, `Preview`, `Tool` code from `ARCHITECTURE.md` §5
- [ ] Create `atlas/core/registry.py` — a dict of `name → Tool` instance, `get()`, `all()`, `by_category()`
- [ ] Commit

### 2:00–2:45 — Renderer
- [ ] Move the formatting loop out of `main.py` into `atlas/core/renderer.py` as `render(result: ToolResult) -> str`
- [ ] Add rendering for `command_run` and the undo hint
- [ ] `main.py` should now be roughly five lines plus argument parsing

### 2:45–3:45 — Port SystemInfoTool
- [ ] Subclass the new `Tool`, `safety = Safety.READ_ONLY`
- [ ] Make sure `explanation` says something genuinely useful to a non-technical person — this is the line a panel will judge, so write it properly. Not "CPU: 8 cores" but "You have 8 processing cores, which is comfortable for everyday work and light editing."
- [ ] `atlas info` works

### 3:45–4:30 — Journal
- [ ] `atlas/core/journal.py` — append-only JSONL at `%LOCALAPPDATA%\Atlas\journal.jsonl`
- [ ] `record(tool, args, prior, command) -> id`, `last_undoable()`, `mark_undone(id)`
- [ ] Written **before** execute, never after

### 4:30–7:00 — The mutating tool
This is the centrepiece. `power.monitor_timeout` — how many minutes before the screen turns off.

Chosen because it reads back cleanly, reverts perfectly, is impossible to break a machine with, and is **visibly verifiable in the Windows Settings UI during the demo.**

- [ ] `atlas/os/windows/powercfg.py`:

```python
import re
import subprocess


def read_monitor_timeout_ac() -> int:
    """Minutes before the monitor turns off on AC power."""
    out = subprocess.run(
        ["powercfg", "/query", "SCHEME_CURRENT", "SUB_VIDEO", "VIDEOIDLE"],
        capture_output=True, text=True, check=True,
    ).stdout
    # powercfg reports the value in hex SECONDS
    m = re.search(r"Current AC Power Setting Index:\s*(0x[0-9a-fA-F]+)", out)
    if not m:
        raise RuntimeError("Could not read monitor timeout from powercfg")
    return int(m.group(1), 16) // 60


def write_monitor_timeout_ac(minutes: int) -> str:
    cmd = ["powercfg", "/change", "monitor-timeout-ac", str(minutes)]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return " ".join(cmd)
```

Two caveats on that parser, both verified:

- `powercfg` reports the value in **hex seconds**, but `/change` takes **minutes**. The `// 60` conversion is required, and it truncates — a timeout set to 90 seconds reads back as 1 minute. Fine for now; note it.
- Those output strings are **localized**. On a non-English Windows install `"Current AC Power Setting Index"` will not match and the tool will raise. Acceptable today, but it means parsing English CLI output is not a long-term strategy — the PowerShell/WMI route returns typed values instead. Log it as known.

- [ ] `atlas/tools/power/monitor_timeout.py` — `safety = Safety.MUTATING`, one `Parameter("minutes", int, minimum=1, maximum=180)`, with `preview()`, `execute()`, `undo()`
- [ ] CLI wiring: `atlas set`, confirmation prompt, `atlas undo`
- [ ] **Test the full round trip at least three times.** Change it, check Windows Settings, undo, check again.

### 7:00–7:45 — Docs and README
- [ ] Read `ARCHITECTURE.md` and `ROADMAP.md` properly — you have to defend every line of them
- [ ] Expand `README.md`: what Atlas is, who it is for, the four principles, how to run the demo

### 7:45–9:00 — Rehearse
- [ ] Run the demo start to finish, out loud, twice
- [ ] **Take screenshots of every step as a fallback.** Live demos fail on unfamiliar projectors and locked-down lab machines. Have the screenshots in a folder.
- [ ] Check whether the lab machine needs admin rights for `powercfg` and whether you will have them
- [ ] Time yourself

---

## What to say to the panel

Lead with the problem, not the technology. Your manifesto is the strongest asset you have — it is real, specific, first-hand pain, and panels can tell the difference between that and a project invented to fill a requirement.

**Opening, roughly:** "Windows has hundreds of settings that control how my computer behaves, and I am afraid of most of them. Not confused — afraid. I don't know if what I'm about to change does what I think, and I don't know how to put it back. Atlas is the layer that makes those changes safe to make."

Then the demo. Then the architecture — specifically the one decision that shows engineering judgment:

**"The language model in Atlas cannot touch my operating system."** It only chooses which of my tested functions to call and fills in the arguments. Every command that runs is one I wrote. A small model running locally on a cheap laptop is not reliable enough to author system commands, and being wrong damages the only computer someone owns — so I designed it so being wrong is survivable.

That sentence is what separates this from a project that pipes user text into an LLM and runs whatever comes out. Say it explicitly.

## Questions the panel will probably ask

**"Why not just use ChatGPT / an API?"**
Privacy is the easy answer, but the better one is the demographic: this user has one mid-spec laptop, is price-sensitive, and may have unreliable internet. Local-first means free, offline, and no account. Also, a cloud model generating shell commands for your machine is precisely the design I ruled out.

**"What if the AI does something wrong?"**
It can pick the wrong tool — that is why confirmation is mandatory and shows the exact command. It cannot invent a command, because it never generates commands. And every mutation is journaled before it runs, so there is always a revert path. Then demo `atlas undo`.

**"How is this different from Windows Settings?"**
Windows Settings assumes you know the name of the thing you want. Our user does not — that is the actual gap. Atlas takes "my screen keeps going dark while I'm reading" and finds the setting, explains it, and can undo it.

**"Isn't this scope enormous?"**
Yes — that is why the roadmap ships one category at a time, and why BIOS and guest mode are explicitly deferred with the reason written down. Point at §11 of the architecture doc. Showing you have *rejected* work is a stronger signal than showing ambition.

**"What have you actually built?"**
The safety framework and one complete vertical slice through it. Be straight about this. "One setting, fully correct, through an architecture that supports thirty" is a defensible answer. Inflating it is not, and panels probe.

**"Why should I believe you can finish it?"**
Because the hard part is not the AI — it is the library of tested, reversible operations, and that part needs no research, only work. And because the AI layer is optional: cut it out and Atlas still functions.

## The one weakness to get ahead of

A panel member will notice that the CLI is not usable by the person you described in your manifesto. Say it before they do: **the CLI is scaffolding for building and testing; the GUI in Phase 3 is the surface the real user ever sees.** Volunteering your own project's limitation is the single most credible thing you can do in a defense.

---

## After the panel — the first week

1. Write the test suite before adding more tools. Six tools with tested `undo()` beat twenty without.
2. Build out the power and display categories to about ten tools. Breadth in one area proves the pattern scales.
3. Start collecting phrasings — every way you would naturally ask for each setting. This becomes the Phase 2 routing test set, and you cannot generate it honestly after the fact.
4. Only then touch the model layer.
