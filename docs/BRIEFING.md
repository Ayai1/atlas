# Project briefing — read this before the review

Everything here is in plain language. If you can say all of this out loud comfortably, you are ready.

---

## 1. The project in one paragraph

We are building a local-first AI companion for your computer. You describe a problem in your own words — "my screen keeps going dark while I'm reading" — and it finds the Windows setting that controls it, tells you in plain English what it will change, shows you the exact command it will run, asks your permission, and records the old value so you can undo it afterwards. It runs entirely on your own machine, with no internet and no account.

**The one-sentence version:** it makes changing your own computer's settings safe for people who are not confident doing it.

**What we are selling is not automation. It is confidence.** People don't want a computer that acts without them. They want to stop being afraid of their own machine.

## 2. The problem, in four sentences

1. Windows has hundreds of settings, and to find one you must already know its name.
2. Nothing tells you what a setting actually does, or what the trade-off is.
3. Almost nothing records the old value, so you can't reliably put it back.
4. New AI assistants in operating systems will act on your machine, but don't keep a record of what they changed.

**Who this affects:** people who use their computer heavily, can tell something is wrong, but don't trust themselves to change it and have nobody to ask.

## 3. How it works — the pipeline, step by step

This is slide 8. Learn these seven steps; they are the core of the project.

| Step | Name | What happens | Why it matters |
|---|---|---|---|
| 1 | **Ask** | The user types a problem in their own words. | They don't need to know the setting's name. |
| 2 | **Shortlist** | We match their words against our tool descriptions and pick about ten candidates. **No AI in this step** — it's keyword matching. | Small models get confused choosing from hundreds of options. Narrowing first makes them far more reliable. |
| 3 | **Pick tool** | The local model chooses one tool from that shortlist and fills in the values. | This is the *only* thing the AI does. |
| 4 | **Check** | We validate the values against limits we defined (e.g. minutes must be 0–300, and an integer). | If the model returns nonsense like −5, it's rejected here, before Windows is touched. |
| 5 | **Confirm** | We read the current value, show the user the exact command, and wait for approval. | Nothing is applied without a human saying yes. |
| 6 | **Save old value** | We write the previous value to a journal file **before** changing anything. | If the program crashes mid-change, the way back still exists. |
| 7 | **Do it, explain, undo** | Our tested code runs the change, shows an explanation we wrote, and offers a one-step undo. | The user always knows what happened and can reverse it. |

**The three places it refuses rather than guesses** — this is the part to emphasise:

- **Step 4** — a value outside the safe range is rejected before Windows is touched.
- **Step 5** — nothing is applied until the user approves the exact command.
- **Step 6** — if the setting changed since the preview was shown, the change is abandoned rather than applied to a state the user never saw.

## 4. The architecture — six layers

Top to bottom. You should be able to name them in order.

1. **Interface** — the window the user sees (and a command line we use for development).
2. **Orchestrator** *(optional)* — the local model that picks a tool. **Remove this layer and everything below still works.**
3. **Registry** — the catalogue of available tools and their allowed values.
4. **Tool library** — ordinary tested Python. Each tool declares its safety level, its limits, how to preview itself, how to run, how to undo, and its own explanation text.
5. **OS adapter** — the single place where Windows is actually touched (`powercfg`, PowerShell, WMI).
6. **Audit journal** — an append-only file of old values, written before every change.

**The key line:** the model is a convenience layer, not a dependency.

## 5. The most important idea — routing, not generating

If you remember one thing, remember this.

**The language model never writes commands.** It only *chooses* one of the functions we already wrote and tested, and fills in the numbers. Every command that reaches Windows is one we authored and tested ourselves.

**Why this matters:** a small model running on a cheap laptop is not reliable enough to write correct system commands, and being wrong damages the only computer somebody owns. So we designed it so that being wrong is survivable — a wrong guess produces a wrong *menu choice*, not a broken machine.

The technical name for this is **tool calling** (or function calling).

## 6. Literature review — the five papers

All five are from 2026. For each: what it did, and the single sentence to say if asked.

**1. OSGuard: A Benchmark for Safety in Computer-Use Agents** — Mohammadmirzaei and Flanigan, 2026 (UC Santa Cruz)
Tested AI agents on 45 real desktop tasks where the request was perfectly ordinary but the environment held a hidden hazard. The agents finished the job but did something unsafe **38% of the time**. Adding the best safety checker only brought that down to **33%**.
*Limitation:* it measures how often agents go wrong. It offers no way to repair the damage.
*Say this:* "Their own numbers show blocking barely helps — 38% down to 33%. Prevention alone is not working."

**2. SafePred: A Predictive Guardrail for Computer-Using Agents** — Chen et al., 2026
Uses a model of the world to predict which actions will cause trouble later, and blocks them before they run.
*Limitation:* the prediction is a guess made by another model. If it guesses wrong, the action happens and cannot be taken back.
*Say this:* "It is a smarter guard, but it is still guessing, and there is no second chance if it guesses wrong."

**3. When Actions Go Off-Task** — Ning et al., 2026 (ICML)
Spots actions that drift away from what the user actually asked for, and rewrites them before they run.
*Limitation:* one model checking another model. It is only necessary because the agent writes its own actions.
*Say this:* "They need this because their agent invents actions. Ours picks from a fixed list, so there is nothing to police."

**4. When Benign Inputs Lead to Severe Harms** — Jones et al., 2026 (ICML)
Shows agents cause real harm even from completely ordinary, harmless requests. Gives 117 verified examples.
*Limitation:* proves the danger is not just bad users, but offers nothing to undo the harm.
*Say this:* "This is why confirmation matters even when the user is doing something totally normal."

**5. ActPlane: OS-Level Policy Enforcement** — Zheng et al., 2026
Puts the safety rules inside the operating system itself so nothing slips past, at under 10% speed cost.
*Limitation:* it can block an action but cannot reverse one it allowed, and the rules need an expert to write.
*Say this:* "The strongest enforcement in the field, and it still has no undo."

**The joint conclusion (memorise this):** every one of these tries to stop a mistake before it happens. Not one of them can undo a mistake after it happens. That is the gap we fill.


## 7. Existing tools, and how we differ

| Tool | Its limitation | How we differ |
|---|---|---|
| Windows Settings app | You must know the setting's name; no explanation, no undo | Finds it from a description of the symptom, explains it, reverts it |
| Windows 11 Settings AI Agent | Closed source; no universal undo or change history | Every change stores its old value first, so one-step undo always exists |
| Copilot Actions | Reported to misread UI elements; no auditable record | Never drives the GUI; calls tested functions and journals every change |
| Open Interpreter | Asks you to approve generated code you can't judge | The model can't write commands; you approve a tested operation in plain English |
| Tweak scripts / optimisers | Opaque bulk edits, little explanation or reversal | One change at a time, each explained, each individually revertible |

**Be honest about Microsoft.** Windows 11 already ships an on-device AI agent in the Settings app. Say so *before* they ask. Natural-language settings search is not our novelty. Our novelty is the four things below.

## 8. Our four novelty claims

1. The model can never write a command.
2. Every change records its old value first.
3. A complete, auditable change history.
4. Fully offline — no account, modest hardware.

No reviewed tool provides all four together.

## 9. Basic questions you must answer smoothly

**"What is your project?"**
A local-first AI companion that helps people safely change settings on their own computer, in plain language, with every change explained and reversible.

**"Why is it needed?"**
Because people can't find the setting they want, don't know what it does, and can't undo it — so they either avoid changing anything or follow instructions from the internet they don't understand.

**"Where is the AI?"**
The AI turns your sentence into a choice of which of our tested functions to run. That's Phase 2, week 11. We built the safety layer first on purpose — it's fully testable without a model, so a weak model can't sink the project. It degrades to a working menu-driven tool.

**"What if the AI gets it wrong?"**
Three answers. It can pick the wrong tool — that's why confirmation showing the exact command is mandatory. It can't invent a command, because it never writes commands. And every change is journaled before it runs, so there's always a way back.

**"How is this different from Windows Settings?"**
Windows Settings assumes you know the name of what you want. Our user doesn't — that's the actual gap. We take "my screen keeps going dark while I'm reading" and find the setting, explain it, and can undo it.

**"Microsoft already does this."**
Partly, yes, and we say so on slide 5. What they don't do is guarantee reversibility, keep an audit trail you can inspect, or run fully offline without an account.

**"What have you actually built?"**
The safety framework and one complete path through it: 3,385 lines of Python, 90 automated tests all passing, and a working change-and-revert on a real Windows setting.

**"Isn't the scope enormous?"**
Yes, which is why firmware and multi-user handover are written down as out of scope for Capstone-I with a stated reason. We ship one category of settings at a time.

**"Why should we believe you'll finish?"**
Because the hard part isn't the AI — it's the library of tested, reversible operations, and that needs work, not research. And the AI layer is optional: remove it and the tool still functions.

**"What technologies are you using?"**
Python 3.10+, psutil, pytest, Tkinter for the window, `powercfg` / PowerShell / WMI to reach Windows, and Ollama to run a local model later. Git, test-first development.

## 10. Words you should be able to define on the spot

- **Local-first** — runs on your machine, offline, no account; your data and control stay with you.
- **Reversible / undo** — we read and store the old value *before* changing it, so we can always put it back.
- **Audit journal** — an append-only file recording every change and its previous value. Answers "what has this software done to my computer?"
- **Tool calling / function calling** — the model chooses which pre-written function to run and fills in its arguments, instead of writing code.
- **Validation** — checking values against limits we defined, inside the tool, so it applies to every caller including the model.
- **Shortlist / retrieval** — narrowing hundreds of tools to about ten by keyword match, before the model chooses.
- **Read before write** — always query the current value first. This is what makes undo possible.

## 11. Numbers to have ready

- **3,385** lines of Python
- **90** automated tests, all passing
- **3** operations built (1 read-only, 2 reversible changes)
- **5** papers reviewed
- **5** existing tools compared
- **5** SMART objectives
- Target: **30** operations by week 9, **85%** correct tool selection by week 11, on **8 GB** RAM with no GPU
- We are in **week 4** of **12**

## 12. Splitting the talk

Ayaan: slides 1–5 (title, index, problem, literature review, existing tools).
Noorullah: slides 6–10 (objectives, methodology, architecture, progress, challenges).

Both of you must be ready to answer anything — the panel can direct a question to either of you.

## 13. Three things not to do

1. **Don't read the tables aloud.** Say what the table shows and point at the two rows that matter.
2. **Don't overclaim the AI.** It is not working yet. It's week 11.
3. **Don't say nothing like this exists.** It does, partly. Naming it first is what makes the rest of your claims credible.
