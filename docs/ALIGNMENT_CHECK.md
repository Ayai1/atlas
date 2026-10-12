# Does Atlas align with the Capstone guidelines?

Assessed against *Capstone Project-I (Guidelines), Woxsen University, School of Technology*.

**Verdict: strong alignment.** The project sits squarely inside the permitted topic areas, maps cleanly onto all four Course Outcomes, and is unusually far ahead on the one thing most Week-4 teams cannot show — a working, tested prototype. Three gaps are worth closing, and one competitive fact needs handling directly.

---

## 1. Topic eligibility

The guidelines list permitted areas including **Software Development and Applications**, **Artificial Intelligence and Machine Learning**, and **Cybersecurity**. Atlas is primarily the first, with a genuine AI/ML component in Phase 2 and a real safety/privacy dimension. It is not a borderline fit.

Review criteria for topic approval, and how Atlas reads against each:

| Criterion | Assessment |
|---|---|
| Feasibility within the semester | **Strong.** Phase 0 is already complete in Week 4. |
| Technical challenge appropriate for 7th semester | **Adequate.** Systems programming, OS interaction, architecture design, local model integration. |
| Innovation potential | **Good, with a caveat** — see §5. |
| Resource availability | **Strong.** No hardware, no cloud spend, no licences. |
| Industry or societal relevance | **Strong.** Directly targets an underserved user group. |
| Alignment with programme outcomes | **Strong.** See below. |

## 2. Course Outcomes

| CO | Requirement | Status |
|---|---|---|
| **CO1** | Identify real problems, SMART objectives | **Met.** Five SMART objectives with numeric targets and week deadlines (deck slide 8). Rooted in a first-hand problem statement. |
| **CO2** | Design and implement innovative solutions addressing gaps | **Met.** Architecture ties each design decision to a gap from the technology review. |
| **CO3** | Functional prototype with novelty and impact | **Exceeded for this stage.** 3,385 lines, 90 passing tests, working end to end at Week 4. |
| **CO4** | Document and communicate to academic standards | **Met.** Architecture and roadmap documents exist; deck follows the presentation rules. |

## 3. Rubric read (the five criteria that are actually scored)

| Criterion | Weight | Position | Reasoning |
|---|---|---|---|
| Problem Identification | 20% | **Strong** | The problem is specific, first-hand, and has a clearly defined user. The manifesto is a real asset — panels can tell the difference between lived frustration and a topic invented to fill a requirement. |
| Methodology | 25% | **Strong** | Phased, test-first, with an explicit rationale for the ordering. The "AI comes last" argument is a methodology strength, not a weakness, provided you frame it that way. |
| Innovation and Industry Relevance | 25% | **Good, needs careful framing** | This is the criterion most at risk. See §5. |
| Presentation Clarity | 15% | **Strong** | 19 slides, one idea per slide, visuals throughout, slide numbers, speaker notes. |
| Report Quality | 15% | **Not yet assessable** | The report does not exist yet. This is a Week-8 and Week-12 concern, not Week 4. |

## 4. Review-1 focus areas (Week 4, 20%)

The guidelines name five focus areas for the Initial Proposal Review specifically:

- [x] **Topic feasibility and relevance** — slides 3, 4
- [x] **Problem statement clarity** — slide 4
- [x] **Objectives and scope definition** — slide 8, plus explicit out-of-scope statement on slide 3
- [x] **Preliminary technology review** — slides 5, 6, 7
- [x] **Project plan and timeline** — slide 14

All five are covered. The prototype on slide 13 is beyond what Review 1 asks for.

---

## 5. The one thing you must handle: Microsoft got there first

While researching the technology review, I found that **Windows 11 (version 24H2, KB5062660) already ships an on-device AI agent inside the Settings app** that finds and changes settings from a natural-language description. Microsoft has also been rolling out Copilot Actions and an Agent Workspace for UI-level automation.

This matters. If a panel member knows this — or searches during your talk — an unqualified claim that "no such thing exists" damages your credibility on the 25% innovation criterion.

**Do not hide this. Lead with it.** It is on slide 5 as "closest prior art" and on slide 15 as a named risk, with the differentiation stated.

The defensible position is that natural-language settings search **is no longer the novel part**. What remains genuinely unaddressed:

1. **Guaranteed reversibility.** Microsoft's agent does not read and journal prior state before changing it. There is no universal one-step undo.
2. **A complete audit trail.** No reviewed system lets the user ask "what has this software changed on my computer?" and get a full answer.
3. **Offline, no account, open.** Runs on the machine the user already owns, with no sign-in and no telemetry.
4. **Refusing to let the model reach the OS.** Reported reliability problems with agentic OS features — misidentified UI elements, actions that do not work — are precisely what the routing-not-generating design prevents.

Reframe the contribution in one sentence: **not "AI that changes your settings" but "a safety and reversibility architecture for automated system changes, with AI as an optional interface to it."** That is defensible, current, and still yours.

## 6. Gaps to close

**Before the presentation (tonight):**

1. **Fill the placeholders.** Both names, both roll numbers, and your faculty mentor's name and designation on slide 1.
2. **Rehearse to time.** 19 slides in 15 minutes is roughly 45 seconds each. The literature review and comparison slides are where teams overrun — do not read the tables.
3. **Split the talk.** Guidelines require *all* team members to present and both of you to be ready for Q&A. Suggested split: one takes slides 1–8 (problem and objectives), the other 9–16 (methodology through future scope).

**Before Mid-Term (Week 8):**

4. **Expand the technology review to the full 12 columns.** The guidelines specify exact columns — performance, scalability, cost/licensing, compatibility, ease of use, security, current market, limitations. The deck's four-column version is a summary; the report needs the full table for 5–8 technologies.
5. **Get to 15–20 references.** The deck has 16 in IEEE format, which meets the minimum. Add domain-specific ones as the review deepens.
6. **Start the report early.** 3,000–4,000 words with a <15% similarity index. Note that the guidelines contradict themselves — §3.16 says <15%, §7.4 says <10%. **Ask your mentor which applies**; assume 10% to be safe.

## 7. Small compliance notes

- Guidelines suggest 24pt headings and 18pt body. The deck uses 30pt titles and 15–17pt body, with 10–12pt inside comparison tables. Table text cannot be 18pt and still fit; this is normal and defensible, but be aware it is a deviation.
- Slide numbers are present on every slide, as required.
- Deliverables due 48 hours before evaluation — check whether that applies to this review.
- Team must stay the same across 7th and 8th semesters. Confirm your teammate is committed to Capstone-II.

## 8. Honest summary

The project is well-aligned and you are ahead of schedule. Your two real risks are **scope** — an "OS companion" can mean almost anything, which is why the written out-of-scope list matters — and **novelty**, now that a major vendor occupies part of your problem space.

Both are manageable, and both are handled better by naming them yourself than by being asked. A panel rewards a team that has clearly thought about why its project might *not* be novel far more than one that claims uniqueness it cannot defend.

---

**Sources for the competitive findings**

- [Configure the agent in Windows Settings — Microsoft Learn](https://learn.microsoft.com/en-us/windows/configuration/settings/agent)
- [Windows 11 adds an AI agent to help you manage settings — Windows Central](https://www.windowscentral.com/microsoft/windows-11/whats-ai-agent-in-the-settings-app-on-windows-11-automation-explained)
- [Windows 11 Agent Workspace and Copilot Actions Preview Explained — Windows Forum](https://windowsforum.com/threads/windows-11-agent-workspace-and-copilot-actions-preview-explained.397580/)
- [Windows Copilot Pullback: Privacy, Reliability and Admin Controls — Windows Forum](https://windowsforum.com/threads/windows-copilot-pullback-privacy-reliability-and-admin-controls-on-windows-11.405308/)
- [Safety — Introduction, Open Interpreter documentation](https://docs.openinterpreter.com/safety/introduction)
