# Regulus — Demo Guide

## The demonstration scenario

**Maji Valley Water Infrastructure Allocation**

> _Fictional region. Synthetic/illustrative data only._

A decision-maker needs to allocate a $50,000 budget to improve reliable water access across three communities in Maji Valley. The communities (Kijani, Mtoni, Amani) currently have partial, intermittent water access due to aging infrastructure and an unreliable electricity grid.

---

## Starting the demo

### Option A — One-click from the UI

1. Open `http://localhost:3000`
2. Click **Run demo scenario**
3. The form is pre-filled — click **Start analysis**
4. Watch the run dashboard

### Option B — API

```bash
curl -s -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d @demo_water_scenario_request.json
```

Or use the Swagger UI at `http://localhost:8000/docs`.

---

## What to watch for

### Step 1 — Problem analysis

The Orchestrator decomposes the question:
- Objective: maximize reliable household water access
- Constraints: $50,000 budget, 3 communities
- Evidence requirements: grid reliability, rainfall, population, storage

### Step 2 — Initial research

The Research Agent returns 6 evidence items from the synthetic Maji Valley dataset:
- 2–3 medium-confidence items
- 3–4 assumption-level items
- Key gap: electricity reliability has confidence 0.55

### Step 3 — Model construction

An 8-node Bayesian network appears on the model page. Note that `electricity_reliability` has a low confidence score and a strong edge to `pump_availability`.

### Step 4 — Scenario simulation

Four scenarios are evaluated with 500 Monte Carlo samples each:
- **Pump Expansion** — moderate improvement, vulnerable to grid outages
- **Storage Expansion** — reduces shortage frequency, doesn't address pump downtime
- **Solar Pumping** — eliminates grid dependency, expected to rank highly
- **Combined Strategy** — highest expected access but similar cost to others

### Step 5 — Sensitivity analysis (the key moment)

Sensitivity analysis reveals `electricity_reliability` dominates with a score ≥ 0.35. The Orchestrator logs:

```
Material uncertainty detected in 'electricity_reliability' (score 0.71 >= 0.35).
Initiating additional research (loop 2).
```

### Step 6 — Autonomous re-research

The Research Agent conducts a focused search on electricity reliability. New evidence:
- Updated grid reliability estimate with confidence 0.72 (was 0.55)
- Solar pump performance data from comparable regions

### Step 7 — Model update + re-simulation

The PGM updates with higher-confidence parameters for `electricity_reliability`. Solar pumping's advantage over pump expansion becomes clearer because the updated model confirms grid limitations.

### Step 8 — Final recommendation

The Decision Agent produces a recommendation for **Solar Pumping** or **Combined Strategy** (result depends on exact Monte Carlo seeds):

```
Recommendation: Solar-Powered Pumping
Expected access improvement: ~18–25%
Robustness: ~65–75%
Confidence: ~72%

Key reasoning: Solar pumping eliminates the dominant source of uncertainty
(electricity reliability). The updated evidence confirms grid limitations
are a structural constraint, not a temporary issue.

Key risks:
- Solar panel maintenance requires local technical capacity
- High upfront capital concentrates equipment risk

Conditions for change:
- If grid reliability improves above 85%, pump expansion becomes equally effective
- If rainfall drops below 500mm/year, storage expansion becomes critical
```

---

## Expected timing

| Phase | Expected duration (local, mock mode) |
|---|---|
| Problem analysis | < 1s |
| Initial research | < 1s |
| Model construction | < 1s |
| Simulation (500 samples) | 1–3s |
| Sensitivity analysis | 1–2s |
| Re-research | < 1s |
| Re-simulation | 1–3s |
| Decision | < 1s |
| **Total** | **~10–15 seconds** |

With real Gemini API calls, add ~3–8 seconds per agent call (network latency).

---

## Key observable behaviors

These behaviors demonstrate genuine agentic autonomy:

1. **Uncertainty detection** — The system identifies that it doesn't know enough about electricity reliability before committing to a recommendation.

2. **Research loop trigger** — The Orchestrator makes an autonomous decision to gather more evidence. No human told it to do this.

3. **Model update** — The PGM graph changes when new evidence is incorporated. The node table shows updated confidence values.

4. **Recommendation shift** — With higher confidence in electricity reliability constraints, the margin between solar and pump expansion widens.

5. **Evidence provenance** — Every evidence item carries a source, confidence level, and status label. Nothing is invented without labeling it as an assumption.

---

## Confirming the demo is real

To verify the system is actually executing (not faking):

1. Open the backend logs — you'll see structured log entries for each simulation step
2. Check the events list — timestamps are real execution timestamps, not pre-scripted
3. Inspect the model endpoint: `GET /api/v1/runs/{runId}/model` — the graph is computed from evidence, not a hardcoded file
4. Sensitivity scores vary slightly between runs with different seeds — they are computed, not fixed
5. The recommended scenario depends on the simulation results — change the evidence parameters and the recommendation changes

---

## Demo data notice

All data in the Maji Valley scenario is **synthetic and illustrative**. It does not represent:
- Any real location named Maji Valley
- Actual infrastructure statistics for any country or region
- Real survey or government data

The demo is designed to exercise the reasoning pipeline, not to inform actual policy.
