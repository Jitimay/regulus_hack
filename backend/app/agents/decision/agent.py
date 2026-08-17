"""
Decision Agent.

Evaluates simulation results through multi-criteria decision analysis
and produces the final structured recommendation.

The agent uses Gemini to provide qualitative reasoning about the recommendation,
but the quantitative evaluation (ranking, robustness, sensitivity) comes
from the simulation engine. Gemini never overrides computed numbers.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.prompts import DECISION_AGENT_SYSTEM_PROMPT
from app.domain.decisions import (
    AlternativeComparison,
    Recommendation,
    RunResult,
    ScenarioResult,
    SensitivityResult,
)
from app.domain.evidence import ResearchFindings
from app.infrastructure.gemini import GeminiClient

logger = logging.getLogger(__name__)


class DecisionAgent:
    def __init__(self, gemini: GeminiClient) -> None:
        self._gemini = gemini

    async def generate_recommendation(
        self,
        run_id: str,
        scenario_results: list[ScenarioResult],
        sensitivity: SensitivityResult,
        findings: list[ResearchFindings],
        research_loop_count: int,
    ) -> Recommendation:
        """
        Produce the final recommendation by combining:
        - Quantitative simulation results (computed, authoritative)
        - Gemini reasoning (qualitative, explanatory)

        The recommended scenario is always the one with rank=1 from the
        simulation engine. Gemini provides the reasoning, risks, and conditions.
        """
        if not scenario_results:
            raise ValueError("No scenario results to evaluate")

        # The simulation engine has already ranked scenarios — trust rank=1
        top_scenario = min(scenario_results, key=lambda r: r.rank)
        others = [r for r in scenario_results if r.rank != 1]

        # Build context for Gemini
        context = self._build_decision_context(
            top_scenario, others, sensitivity, findings, research_loop_count
        )

        try:
            gemini_output = await self._gemini.generate_structured(
                context, DECISION_AGENT_SYSTEM_PROMPT
            )
        except Exception as e:
            logger.error("Gemini decision generation failed: %s", e)
            gemini_output = self._fallback_reasoning(top_scenario, sensitivity)

        # Validate and extract Gemini reasoning — never override computed numbers
        reasoning = gemini_output.get("reasoning", self._default_reasoning(top_scenario))
        key_risks = gemini_output.get("key_risks", ["Model uncertainty", "Implementation risk"])
        key_assumptions = gemini_output.get(
            "key_assumptions",
            ["Evidence is representative of actual conditions", "Budget allocated as modeled"],
        )
        conditions_for_change = gemini_output.get(
            "conditions_for_change",
            ["If electricity reliability improves significantly", "If rainfall patterns change substantially"],
        )
        uncertainty_notes = gemini_output.get(
            "uncertainty_notes",
            f"Dominant uncertainty: {sensitivity.dominant_variable} (score: {sensitivity.dominant_uncertainty_score:.2f})",
        )

        # Build alternative comparisons
        alternatives = []
        for other in others[:3]:  # Top 3 alternatives
            reason = next(
                (
                    r
                    for r in gemini_output.get("alternative_rejections", [])
                    if r.get("scenario") == other.scenario_name
                ),
                None,
            )
            alternatives.append(AlternativeComparison(
                scenario_name=other.scenario_name,
                reason=reason.get("reason", "Lower composite score") if reason else "Lower composite score combining expected impact, robustness, and downside risk",
                key_weakness=reason.get("weakness", "Lower performance on one or more key criteria") if reason else self._infer_weakness(other, top_scenario),
                expected_impact=round(other.access_improvement.mean, 3),
            ))

        # Confidence: Gemini's estimate, but capped by evidence quality
        max_evidence_confidence = max(
            (f.items[0].confidence for f in findings if f.items),
            default=0.5,
        )
        gemini_confidence = float(gemini_output.get("confidence", 0.72))
        # If dominant uncertainty is high, cap confidence
        uncertainty_penalty = max(0.0, sensitivity.dominant_uncertainty_score - 0.3) * 0.5
        final_confidence = max(0.40, min(gemini_confidence, max_evidence_confidence) - uncertainty_penalty)

        # Evidence IDs
        evidence_ids = [item.id for f in findings for item in f.items[:3]]

        # Sensitive variable names
        sensitive_vars = [e.variable_name for e in sensitivity.entries[:3]]

        return Recommendation(
            run_id=run_id,
            recommended_scenario_id=top_scenario.scenario_id,
            recommended_scenario_name=top_scenario.scenario_name,
            intervention_type=top_scenario.intervention_type,
            expected_impact=round(top_scenario.access_improvement.mean, 3),
            expected_households_served=round(top_scenario.expected_households_served),
            robustness=round(top_scenario.robustness, 3),
            confidence=round(final_confidence, 2),
            cost_usd=top_scenario.cost_usd,
            summary=self._build_summary(top_scenario, final_confidence),
            reasoning=reasoning,
            key_risks=key_risks[:5],
            key_assumptions=key_assumptions[:5],
            sensitive_variables=sensitive_vars,
            evidence_items=evidence_ids[:10],
            alternative_comparisons=alternatives,
            conditions_for_change=conditions_for_change[:4],
            uncertainty_notes=uncertainty_notes,
            research_loops_completed=research_loop_count,
        )

    def _build_decision_context(
        self,
        top: ScenarioResult,
        others: list[ScenarioResult],
        sensitivity: SensitivityResult,
        findings: list[ResearchFindings],
        loops: int,
    ) -> str:
        scenario_summary = "\n".join([
            f"- {r.scenario_name}: access_improvement_mean={r.access_improvement.mean:.3f}, "
            f"robustness={r.robustness:.2f}, p10={r.access_improvement.p10:.3f}, rank={r.rank}"
            for r in sorted([top, *others], key=lambda x: x.rank)
        ])
        sensitivity_summary = "\n".join([
            f"- {e.variable_name}: score={e.sensitivity_score:.3f}, direction={e.direction}"
            for e in sensitivity.entries[:5]
        ])
        evidence_summary = f"{sum(len(f.items) for f in findings)} total evidence items across {loops} research loops"

        return f"""
Evaluate the following simulation results and produce a structured recommendation.

TOP SCENARIO (rank 1): {top.scenario_name}
- Expected access improvement: {top.access_improvement.mean:.3f} (median: {top.access_improvement.median:.3f})
- Robustness (P >= target): {top.robustness:.2f}
- Downside (P10): {top.access_improvement.p10:.3f}
- Expected households served: {top.expected_households_served:.0f}
- Cost: ${top.cost_usd:,.0f}

ALL SCENARIOS:
{scenario_summary}

SENSITIVITY ANALYSIS:
Dominant variable: {sensitivity.dominant_variable} (score: {sensitivity.dominant_uncertainty_score:.2f})
{sensitivity_summary}

EVIDENCE QUALITY:
{evidence_summary}
Research loops completed: {loops}

Produce a JSON recommendation with: reasoning, key_risks (list), key_assumptions (list),
conditions_for_change (list), uncertainty_notes, confidence (0-1),
alternative_rejections (list of {{scenario, reason, weakness}}).
"""

    def _build_summary(self, top: ScenarioResult, confidence: float) -> str:
        pct_improvement = top.access_improvement.mean * 100
        households = int(top.expected_households_served)
        return (
            f"Scenario analysis indicates {top.scenario_name} offers the best expected outcome: "
            f"approximately {pct_improvement:.1f}% improvement in water access, "
            f"reaching an estimated {households:,} households with {top.robustness:.0%} robustness. "
            f"Confidence: {confidence:.0%}. This is a model estimate — results are sensitive to "
            f"real-world conditions that differ from model assumptions."
        )

    def _default_reasoning(self, top: ScenarioResult) -> str:
        return (
            f"{top.scenario_name} achieves the highest composite score across expected impact, "
            f"robustness, and downside protection. The simulation engine ranked it first based on "
            f"Monte Carlo analysis of {top.robustness:.0%} probability of meeting the access target."
        )

    def _fallback_reasoning(self, top: ScenarioResult, sensitivity: SensitivityResult) -> dict:
        return {
            "reasoning": self._default_reasoning(top),
            "key_risks": [
                f"Model uncertainty in {sensitivity.dominant_variable}",
                "Implementation execution risk",
                "Community adoption and maintenance capacity",
            ],
            "key_assumptions": [
                "Budget fully deployed as modeled",
                "Evidence is representative of actual local conditions",
            ],
            "conditions_for_change": [
                f"If {sensitivity.dominant_variable} improves significantly beyond current estimates",
                "If budget constraints change or implementation costs differ",
            ],
            "confidence": 0.65,
        }

    def _infer_weakness(self, other: ScenarioResult, top: ScenarioResult) -> str:
        if other.robustness < top.robustness - 0.05:
            return "Lower robustness — higher probability of falling short of access target"
        if other.access_improvement.p10 < top.access_improvement.p10 - 0.02:
            return "Higher downside risk — worse worst-case scenario"
        if other.access_improvement.mean < top.access_improvement.mean - 0.03:
            return "Lower expected access improvement"
        return "Lower composite score across impact, robustness, and downside protection"
