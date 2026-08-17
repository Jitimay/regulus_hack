# Regulus — Agent Reference

Regulus uses four autonomous agents coordinated by the Orchestrator. Each agent has a focused role, its own system prompt, and explicit input/output contracts.

---

## 1. Orchestrator Agent

**File:** `backend/app/agents/orchestrator/agent.py`

### Role

Controls the entire workflow. The Orchestrator is the only agent that maintains explicit state (`OrchestratorState`) and drives all transitions.

### Responsibilities

- Decompose the user's decision problem into structured `ProblemDefinition`
- Delegate evidence collection to the Research Agent
- Request model construction from the Simulation Agent
- Inspect simulation and sensitivity results
- **Decide autonomously** whether dominant uncertainty is material enough to require another research loop
- Trigger re-research, model rebuild, and re-simulation when justified
- Coordinate the final Decision Agent call
- Manage all run state transitions and event emission

### Autonomous loop logic

```python
while sensitivity.is_material and loops_done < MAX_RESEARCH_LOOPS:
    # Trigger additional research targeting dominant_variable
    # Rebuild model with merged evidence
    # Rerun simulation + sensitivity
    # Re-evaluate materiality
```

Materiality threshold: `sensitivity_score >= 0.35`

Maximum loops: `3` (configurable via `MAX_RESEARCH_LOOPS` env var)

### Failure handling

- Wraps the entire workflow in a try/except
- On any unhandled exception: transitions run to `FAILED`, writes error message
- Uses graceful transition logic that skips invalid state transitions rather than crashing

---

## 2. Research/Data Agent

**File:** `backend/app/agents/research/agent.py`

### Role

Collects structured evidence about infrastructure variables. Classifies confidence and provenance for every claim.

### Inputs

- `decision_question` — original user question
- `evidence_requirements` — list of evidence gaps from the Orchestrator
- `research_loop` — which iteration (0 = initial, 1+ = follow-up)
- `target_variable` — optional focus for follow-up loops

### Outputs

`ResearchFindings` containing:
- List of `EvidenceItem` objects with claim, value, unit, confidence, source, status
- `missing_information` — gaps not filled
- Counts by confidence level

### Evidence classification

| Status | Meaning |
|---|---|
| `external_evidence` | Retrieved from a data source with verifiable provenance |
| `assumption` | Reasonable assumption without external verification |
| `inferred` | Derived from other evidence through explicit reasoning |
| `computed` | Output of a calculation, not a direct observation |

### Demo / mock mode

When `USE_MOCK_RESEARCH=true`, the agent uses the `MAJI_VALLEY_EVIDENCE` and `MAJI_VALLEY_FOLLOWUP_EVIDENCE` synthetic datasets. These are clearly labeled as demo data in every evidence item's `source` field.

### Real Gemini path

When mock mode is off, the agent calls Gemini with a structured prompt and parses the JSON response via `GeminiClient.generate_structured()`. Malformed items are logged and skipped — they do not crash the run.

---

## 3. Simulation/Modeling Agent

**File:** `backend/app/agents/simulation/agent.py`

### Role

Translates evidence into a PGM, configures scenarios, and coordinates numerical simulation. **Does not perform computations itself** — delegates entirely to the PGM engine.

### Inputs

- `ResearchFindings` (from Research Agent)
- `run_id` and list of requested `InterventionType` values

### Outputs

- `PGMGraph` — validated probabilistic graphical model
- `ScenarioSet` — intervention scenarios with modifiers
- `list[ScenarioResult]` — ranked Monte Carlo results
- `SensitivityResult` — per-variable sensitivity scores

### Evidence → PGM mapping

The agent maps evidence items to node distribution parameters using a structured translation:

- `electricity_reliability` evidence → Beta distribution alpha/beta via method of moments
- `rainfall` evidence → Normal distribution mean/std
- `pump_availability` evidence → Beta distribution alpha/beta
- `water_availability` evidence → Normal mean

Evidence confidence directly adjusts the concentration parameter (higher confidence → tighter distribution).

### What Gemini does NOT do here

The Simulation Agent uses Gemini only for interpreting evidence in edge cases. The actual probability calculations, Monte Carlo sampling, and sensitivity scores are computed entirely in Python (`pgm/` package). This is a deliberate architectural constraint.

---

## 4. Decision Agent

**File:** `backend/app/agents/decision/agent.py`

### Role

Produces the final structured recommendation by combining quantitative simulation results with Gemini's qualitative reasoning.

### Critical constraint

The recommended scenario is **always** the one ranked #1 by the simulation engine. Gemini provides reasoning, risks, assumptions, and conditions — but cannot override the computed ranking.

### Multi-criteria evaluation

The simulation engine ranks scenarios using:

| Criterion | Weight |
|---|---|
| Expected access improvement (mean) | 50% |
| Robustness — P(outcome ≥ target) | 30% |
| Downside protection (P10) | 20% |

The Decision Agent then adds qualitative context on top of this quantitative ranking.

### Outputs

`Recommendation` containing:
- `recommended_scenario_name`
- `expected_impact` — mean access improvement (0–1)
- `expected_households_served`
- `robustness` — fraction of Monte Carlo runs above target
- `confidence` — honest estimate penalized for unresolved uncertainty
- `reasoning` — evidence-based explanation from Gemini
- `key_risks` — at least 2 concrete risks
- `key_assumptions` — at least 2 explicit assumptions
- `conditions_for_change` — at least 2 conditions under which a different intervention becomes preferable
- `alternative_comparisons` — why each non-recommended scenario was not chosen
- `uncertainty_notes`
- `research_loops_completed`

### Confidence calculation

```python
final_confidence = max(0.40,
    min(gemini_confidence, max_evidence_confidence)
    - uncertainty_penalty  # scales with dominant sensitivity score
)
```

This ensures confidence is always penalized by unresolved model uncertainty.

---

## Agent prompts

**File:** `backend/app/agents/prompts.py`

Each agent has a dedicated system prompt covering:
- Role definition
- Responsibilities
- Tool usage policy
- Uncertainty policy
- Safety policy (no certainty claims)
- Failure behavior
- Required output format

Prompts are modular strings — they are injected per agent call, not concatenated into one giant prompt.

---

## Inter-agent communication

Agents do not call each other directly. All coordination goes through the Orchestrator:

```
Orchestrator.execute()
  → calls ResearchAgent.gather_evidence() → returns ResearchFindings
  → calls SimulationAgent.build_model(findings) → returns PGMGraph
  → calls SimulationAgent.run_simulation(graph, scenarios) → returns results
  → calls SimulationAgent.run_sensitivity(graph) → returns SensitivityResult
  → [loop if material uncertainty]
  → calls DecisionAgent.generate_recommendation(results, sensitivity, findings)
```

All intermediate results are stored in Firestore before the next step, making the workflow recoverable.
