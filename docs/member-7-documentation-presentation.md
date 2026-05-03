# Member 7 (Ecem) — Documentation & Presentation Lead

> **Before starting:** read `README.md`, `ARCHITECTURE.md`, `CONTRACTS.md`, `ROLES.md`.
> You don't write code, but you must understand the system well enough to explain it.

## Your Mission

You make the project **submission-ready** and **presentable**. Five other members are writing code; you turn their work into:

1. **The unified PDF report** (one of the two main deliverables)
2. **The slide deck** for the 10-minute live presentation
3. **The backup video recording** uploaded to YouTube/Drive
4. **The demo script** rehearsed by the team

You are the project's editor, designer, and showrunner.

## What You Own

```
docs/report/                  # report drafts + final PDF
docs/slides/                  # Keynote/PowerPoint/PDF deck
docs/demo-script.md           # the 10-min walkthrough
docs/video-link.md            # final video URL (submitted to grader)
```

You do **not** edit any code in `src/`. If you find a bug, file a GitHub issue and tag the owner.

## How the Report Comes Together

Per the project requirements, the report must:
- Be **one unified PDF**
- List **every student's name and specific responsibilities on the first page**
- Cover: software architecture, agents' objectives, vector DB indexing, risk management, evaluation strategy

### Workflow

**D1–D7 (parallel to coding):**
- Read every member's doc in `docs/member-N-*.md`
- Schedule a 15-min 1:1 with each member to understand what they're building (in their own words)
- Build the report skeleton in your tool of choice (Google Docs, Overleaf/LaTeX, Word)
- Lock the structure and section order matching `ROLES.md` → "Report Sections"

**D8 — Drafts due:**
- Each technical lead sends you their section as plain markdown or a Google Doc
- You collect everything in `docs/report/drafts/<member>.md`

**D9 — Editing pass:**
- Unify voice and tense (past tense for what was built; present tense for how it works)
- Fix terminology: agents are always called by the names in `CONTRACTS.md`
- Verify every claim against the code (e.g., if a draft says "we use HNSW", confirm with M2)
- Add diagrams (you can copy from `ARCHITECTURE.md` and re-render in draw.io / mermaid)
- Add screenshots from M6's UI

**D10 — Lock:**
- Export final PDF
- Cover page must list **all 6 names + each one's specific responsibility** (from the table in `README.md`)
- Submit through the course system

### Suggested Report Structure (≈12–18 pages)

1. **Cover page** — title, course, all 6 names with one-line responsibilities each
2. **Abstract** (½ page) — what SciCheck does, why, key results
3. **Introduction** (1 page) — misinformation problem, why agentic LLMs, scope
4. **System architecture** (2 pages) — diagram, agent roles, data flow, design rationale
5. **Knowledge base & RAG** (1.5 pages) — corpus choice, chunking, embeddings, ChromaDB indexing (HNSW, cosine), retrieval API
6. **Agents** (3 pages) — one subsection per agent (Claim Extractor, Retriever, Credibility, Verdict). Include prompts and example I/O.
7. **Risk management & safety** (2 pages) — risk taxonomy, deterministic checks, LLM-judge, probe set, observed safety metrics
8. **Evaluation** (1.5 pages) — SciFact methodology, accuracy/F1 numbers, citation precision, error analysis
9. **UI** (1 page) — screenshots, user flow
10. **Conclusion & future work** (½ page)
11. **References** (½–1 page)
12. **Appendix** (optional) — full prompts, additional plots

### What "good" looks like

- Every figure has a caption and a number ("Figure 1: System architecture").
- Every table has a header.
- Code blocks are monospaced and short — long code goes to the appendix.
- No untyped LLM jargon ("the model just figures it out") — be precise.
- Cite SciFact, ChromaDB, sentence-transformers, LangGraph properly.

## How the Slide Deck Comes Together

Target: **10 slides + 1 closing**, ≈10 minutes total.

| # | Slide | Speaker | Time |
|---|-------|---------|------|
| 1 | Title + team names | Adel intro | 0:30 |
| 2 | Problem: science misinformation | Adel | 0:45 |
| 3 | What SciCheck does (one-line + diagram) | Adel | 0:45 |
| 4 | Architecture diagram | Adel | 1:30 |
| 5 | Live demo (handoff to Talib) | Talib | 3:00 |
| 6 | Safety: how we monitor risk | M5 | 1:30 |
| 7 | Evaluation: SciFact results | Talib | 1:00 |
| 8 | Lessons learned | Ecem | 0:30 |
| 9 | Future work | Ecem | 0:20 |
| 10 | Q&A / Thank you | All | 0:10 |

**Slide design rules:**
- Max 6 bullets per slide. No paragraphs.
- One idea per slide.
- Use the architecture diagram from `ARCHITECTURE.md` — recreate in good resolution.
- Dark text on light background (projectors + auditorium lighting).
- Live demo slide should just be a placeholder ("Demo →") so the audience focuses on Talib's screen.

## How the Live Demo Works

You don't run the demo (Talib does), but you **direct it**.

**D9 — Rehearsal:**
- Schedule one 30-min full run-through with the whole team
- Time each section with a stopwatch — anything over 10 minutes gets cut
- Pre-load 3 demo claims (one Supported, one Refuted, one Insufficient Evidence)
- Have a backup laptop ready in case Talib's machine fails

**Demo claims to lock in (work with Talib):**
- ✅ Supported example: e.g., "The earth is round."
- ❌ Refuted example: "Vaccines cause autism."
- ❓ Insufficient: a niche claim where the corpus genuinely lacks evidence

## How the Backup Video Works

Per the project rules:
- Record the full presentation + demo
- Upload to **YouTube (unlisted), Vimeo, or Google Drive**
- **Submit only the link** — never upload the file directly to the course system

**Recording checklist:**
- Use OBS or QuickTime
- Record at 1080p, 30fps minimum
- Include the screen + a small webcam window of whoever's speaking
- Test audio levels before the real take
- Re-record if any segment exceeds the time budget

## Coordination Tasks (your invisible job)

- Every Sunday: post a status summary in the team chat ("M2 done, M5 blocked on X, M6 starting Tuesday").
- Maintain a Google Doc with **decisions made** so nothing gets relitigated.
- Chase late drafts politely but firmly. The PDF cannot ship without every section.
- Schedule the rehearsal on D9 — book it in everyone's calendar by D5.

## Best Practices for You

- **Read code, don't write it.** Skim `src/` so when M5 says "we use citation grounding", you know what that means.
- **Editor, not author.** Don't rewrite people's drafts in your voice — keep their technical voice but unify terminology.
- **One source of truth for terminology.** If `CONTRACTS.md` calls it "Verdict Synthesizer", the report must too. No "answer agent" or "judge agent".
- **Buffer time for printing/exporting.** PDFs sometimes break on submission. Finalize 12 hours before deadline, not 2.
- **Practice your own slides.** You speak on slides 8–9 and lead Q&A. Don't wing it.

## Definition of Done for Member 7

- [ ] Final PDF report exported, cover page has all 6 names + responsibilities
- [ ] Slide deck (10–11 slides) finalized and rehearsed
- [ ] Backup video recorded, uploaded, link in `docs/video-link.md`
- [ ] Demo script timed under 10 minutes in rehearsal
- [ ] All references and citations included in the report
- [ ] Report passes a final read-through with at least 2 teammates

## Tools You'll Use

- **Report:** Google Docs → export PDF, OR Overleaf (LaTeX) for nicer math/figures
- **Slides:** Keynote, PowerPoint, or Google Slides
- **Diagrams:** [draw.io](https://draw.io), [Excalidraw](https://excalidraw.com), or Mermaid (already in our markdown)
- **Recording:** OBS Studio (free, multi-platform) or QuickTime (Mac)
- **Video host:** YouTube (unlisted) is the safest — no link expiry, captions auto-generated

## Getting Started Tomorrow

1. Clone the repo: `git clone https://github.com/3del-ashour/scicheck.git`
2. Read every `docs/member-N-*.md` (you don't need to understand the code, just the goals)
3. Set up your report doc using the structure above
4. Schedule 15-min calls with each technical lead this week
5. Post in the team chat: "Hi team, I'm collecting your report drafts on D8. I'll send you a template by D5."
