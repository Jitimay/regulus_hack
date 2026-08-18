---
title: "How I built Regulus: an autonomous Gemini agent that loops until it's confident"
published: true
description: "A deep dive into building a multi-agent infrastructure decision system with Gemini, probabilistic graphical models, and autonomous research loops — built for the All Things Agentic Hackathon."
tags: gemini, agents, python, hackathon
cover_image: https://raw.githubusercontent.com/YOUR_USERNAME/regulus/main/docs/architecture.svg
---

> I created this post as part of my entry for the [All Things Agentic Hackathon](https://allthingsagentichackathon.devpost.com/) by Google. #AllThingsAgenticHackathon

---

## The problem I wanted to solve

Infrastructure allocation decisions — "how do we spend $50,000 to improve water access across three communities?" — are genuinely hard. They involve:

- **Uncertain evidence** (grid reliability estimates, rainfall projections)
- **Multiple competing interventions** (solar pumping vs. pump expansion vs. storage)
- **Compounding risks** (what if the grid gets worse? what if rainfall drops?)

A chatbot gives you a confident-sounding answer. What I wanted was a system that *investigates*, quantifies its own uncertainty, and tells you when it needs to look harder before committing to a recommendation.

That's Regulus.

---

## The core agentic behavior

The key insight is a loop that most AI systems skip:

```
research → model → simulate → sensitivity analysis
                                      ↓
                          is dominant uncertainty material?
                                 yes ↓        no ↓
                          re-research      finalize
                          (targeted)
```

After the initial simulation, Regulus runs a sensitivity analysis to find which variable has the most influence on the outcome. If that variable's uncertainty score is above a threshold (0.35), the Orchestrator autonomously triggers another research cycle — specifically targeting that variable — then rebuilds the model and re-simulates.

This loop runs up to 3 times. The system decides on its own whether to keep investigating.

---

## Architecture

Four agents, coordinated by an Orchestrator:

**Orchestrator** — the only stateful agent. Drives all transitions, decides whether to loop, manages failure handling.

**Research Agent** — collects structured evidence with explicit confidence and provenance for every claim. Supports both real Gemini calls and a synthetic demo dataset.

**Simulation Agent** — translates evidence into a Probabilistic Graphical Model (PGM), then delegates to the pure-Python math engine.

**Decision Agent** — combines the quantitative simulation ranking with Gemini's qualitative reasoning. Critically: Gemini *cannot override* the computed ranking — it only adds context.

```
Orchestrator.execute()
  → ResearchAgent.gather_evidence()       → ResearchFindings
  → SimulationAgent.build_model()         → PGMGraph
  → SimulationAgent.run_simulation()      → [ScenarioResult]
  → SimulationAgent.run_sensitivity()     → SensitivityResult
  → [loop if material uncertainty]
  → DecisionAgent.generate_recommendation() → Recommendation
```

---

## The math layer (the part I'm most proud of)

I made a deliberate architectural decision: **Gemini does not do the math**.

The `pgm/` package is pure Python (NumPy, SciPy, NetworkX):

- `water_model.py` — builds a DAG Bayesian network: `rainfall → water_availability → pump_availability → distribution_capacity → water_access`
- `simulation.py` — DAG-aware Monte Carlo. Samples root nodes from priors, propagates parent influence to children via weighted blending. 500–1000 samples per scenario.
- `sensitivity.py` — One-at-a-time (OAT) perturbation: perturb each node +10%, re-simulate, measure delta in `water_access` mean. Normalized to [0,1].

Scenario ranking uses a weighted composite:
```
score = 0.50 × mean_improvement + 0.30 × robustness + 0.20 × downside_protection
```

This means the recommendation is always the mathematically best scenario. Gemini explains *why*, but can't change *which*.

---

## Tech stack

| Layer | Stack |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind, Recharts, React Flow |
| Backend | Python 3.12, FastAPI, Pydantic |
| AI | Google Gemini 2.5 Flash via `google-genai` SDK |
| Math | NumPy, SciPy, NetworkX |
| Cloud | Cloud Run, Firestore, Pub/Sub |

The mandatory hackathon requirements are met:
- ✅ Gemini 2.5 Flash via Gemini API
- ✅ GenAI SDK (`google-genai`) as the Google Agent Framework
- ✅ Cloud Run + Firestore + Pub/Sub

---

## What I learned

**1. Explicit state machines beat implicit conversation history.**
The Orchestrator maintains a `OrchestratorState` Pydantic model, not a chat history. This makes the workflow recoverable — if a step fails, you know exactly where you were.

**2. Dual-mode infrastructure is worth the upfront cost.**
Every external dependency (Gemini, Firestore, Pub/Sub) has an in-memory mock. This made local development and testing completely frictionless — no GCP credentials needed to run the full pipeline.

**3. Don't let the LLM do the math.**
Gemini is excellent at qualitative reasoning and structured JSON extraction. It's not a Monte Carlo engine. Keeping the math in pure Python made the system deterministic, testable, and auditable.

**4. The agentic loop is the product.**
The most interesting behavior — the autonomous re-research loop — is only a few dozen lines of code in the Orchestrator. But it's what makes Regulus feel genuinely agentic rather than just a fancy prompt chain.

---

## Try it

- **Live demo**: [your-app.vercel.app](https://your-app.vercel.app)
- **Code**: [github.com/YOUR_USERNAME/regulus](https://github.com/YOUR_USERNAME/regulus)

Click "Run demo scenario" to see the full pipeline execute — including the autonomous uncertainty loop — in about 10–15 seconds.
