---
title: "I grew up with 10-hour power cuts. So I built an AI agent to solve infrastructure decisions."
published: true
description: "A Burundian developer builds Regulus — an autonomous Gemini agent that researches, models, simulates, and loops until it's confident enough to recommend how to allocate scarce infrastructure budgets."
tags: gemini, agents, python, hackathon
---

> I created this post as part of my entry for the [All Things Agentic Hackathon](https://allthingsagentichackathon.devpost.com/) by Google. #AllThingsAgenticHackathon

---

## Where this comes from

I'm from Burundi. I grew up in a neighborhood where the electricity grid ran maybe 10–14 hours a day on a good day. Water pumps failed when the grid went down. Storage tanks ran dry during dry season. Local authorities had to decide how to spend scarce budgets — $30,000 here, $50,000 there — on infrastructure that might or might not work depending on variables nobody had good data on.

Those decisions were made by gut feel, political pressure, or whoever had the loudest voice in the room. Not because the decision-makers were incompetent — but because the tools to do it rigorously simply didn't exist at that level.

I built Regulus to change that.

---

## The problem Regulus solves

Imagine you're a local authority in Bujumbura's peri-urban zone. You have $50,000. You need to improve water access for three communities — Kijani (6,000 people), Mtoni (4,000), Amani (3,000). Your options:

- **Pump expansion** — more electric pumps, but the grid only runs 58% of the time
- **Storage expansion** — tanks buffer supply, but don't fix the pump problem
- **Solar pumping** — eliminates grid dependency, but high upfront cost
- **Combined strategy** — balanced, but spreads the budget thin

Which do you choose? It depends on how reliable the grid actually is. On rainfall patterns. On whether pump failures are grid-caused or mechanical. On how much each community's demand varies seasonally.

A chatbot gives you a confident answer based on none of that. Regulus investigates.

---

## What Regulus actually does

Regulus is not a chatbot. It's an autonomous investigation pipeline:

```
1. Decompose the problem into variables and evidence requirements
2. Research evidence — classify confidence and provenance for every claim
3. Build a Probabilistic Graphical Model from the evidence
4. Run Monte Carlo simulation across all intervention scenarios
5. Run sensitivity analysis — which variable dominates the outcome?
6. If dominant uncertainty is material (score ≥ 0.35): loop back to step 2,
   targeting that specific variable
7. Finalize recommendation with explicit assumptions, risks, and conditions
```

Step 6 is the key. The system decides on its own whether it knows enough. If electricity reliability has a sensitivity score of 0.71 and confidence of only 0.55, the Orchestrator agent says: *"I need better data on this before I commit."* It triggers another research cycle, updates the model, re-simulates, and re-evaluates. Up to 3 times.

---

## The architecture

Four agents, coordinated by an Orchestrator:

**Orchestrator** — stateful workflow engine. Drives all transitions, decides whether to loop, handles failures gracefully.

**Research Agent** — collects structured evidence with confidence scores and provenance labels (`external_evidence`, `assumption`, `inferred`, `computed`).

**Simulation Agent** — translates evidence into a PGM, then delegates to the pure-Python math engine. Gemini is not involved in the calculations.

**Decision Agent** — combines the quantitative ranking with Gemini's qualitative reasoning. The recommended scenario is always the one ranked #1 by the simulation engine. Gemini explains why — it cannot override the math.

```
Orchestrator
  → ResearchAgent.gather_evidence()     → ResearchFindings
  → SimulationAgent.build_model()       → PGMGraph (8 nodes, DAG)
  → SimulationAgent.run_simulation()    → ScenarioResults (Monte Carlo)
  → SimulationAgent.run_sensitivity()   → SensitivityResult
  → [loop if score ≥ 0.35]
  → DecisionAgent.generate_recommendation() → Recommendation
```

---

## Why the math is not delegated to Gemini

This was a deliberate architectural decision. The `pgm/` package is pure Python (NumPy, SciPy, NetworkX):

- **DAG-aware Monte Carlo**: samples root nodes from priors, propagates parent influence to children via weighted blending
- **OAT sensitivity analysis**: perturbs each node +10%, re-simulates, measures delta in `water_access` mean
- **Composite scenario ranking**: `0.5 × mean_improvement + 0.3 × robustness + 0.2 × downside_protection`

This makes the system deterministic, testable, and auditable. You can inspect every number. You can change the evidence and watch the recommendation change. That's what "transparent AI" actually means.

---

## Tech stack

| Layer | Stack |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind, Recharts, React Flow |
| Backend | Python 3.12, FastAPI, Pydantic |
| AI | Google Gemini 2.5 Flash via `google-genai` SDK |
| Math | NumPy, SciPy, NetworkX |
| Cloud | Cloud Run, Firestore, Pub/Sub |

Mandatory hackathon requirements:
- ✅ Gemini 2.5 Flash via Gemini API
- ✅ GenAI SDK (`google-genai`) as the Google Agent Framework
- ✅ Cloud Run + Firestore + Pub/Sub

---

## What I learned

**The agentic loop is the product.** The re-research loop is only ~50 lines of code in the Orchestrator. But it's what makes Regulus feel genuinely autonomous rather than a fancy prompt chain.

**Explicit state machines beat conversation history.** The Orchestrator maintains a `OrchestratorState` Pydantic model. If a step fails, you know exactly where you were. The workflow is recoverable.

**Dual-mode infrastructure is worth the upfront cost.** Every external dependency has an in-memory mock. Local development works with zero GCP credentials. This saved hours of debugging.

**Personal experience is a design requirement.** I didn't have to imagine the problem. I grew up inside it. That made every architectural decision clearer — because I knew what a real decision-maker in Bujumbura actually needs.

---

## Try it

- **Live demo**: [your-app.vercel.app](https://your-app.vercel.app)
- **Code**: [github.com/YOUR_USERNAME/regulus](https://github.com/YOUR_USERNAME/regulus)

Click "Run demo scenario" — the full pipeline, including the autonomous uncertainty loop, runs in about 10–15 seconds.
