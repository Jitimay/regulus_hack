"""
Research/Data Agent.

Collects and structures evidence for the infrastructure decision problem.
Supports both a real Gemini-powered research path and a mock/demo path
that uses the synthetic Maji Valley dataset.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.prompts import RESEARCH_AGENT_SYSTEM_PROMPT
from app.domain.evidence import EvidenceItem, ResearchFindings
from app.domain.models import ConfidenceLevel, EvidenceStatus, utcnow
from app.infrastructure.gemini import GeminiClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Demo / synthetic data for Maji Valley
# ---------------------------------------------------------------------------

MAJI_VALLEY_EVIDENCE: list[dict[str, Any]] = [
    {
        "variable_name": "electricity_reliability",
        "claim": "Maji Valley electricity grid averages approximately 14 hours/day operational uptime",
        "value": 0.58,
        "unit": "fraction of day",
        "confidence": 0.55,
        "status": "assumption",
        "source": "Illustrative data based on peri-urban Bujumbura infrastructure patterns",
        "tags": ["energy", "infrastructure"],
    },
    {
        "variable_name": "rainfall",
        "claim": "Annual rainfall in Maji Valley estimated at 620–680mm with moderate inter-annual variability",
        "value": 650.0,
        "unit": "mm/year",
        "confidence": 0.62,
        "status": "assumption",
        "source": "Illustrative data based on peri-urban Bujumbura infrastructure patterns",
        "tags": ["climate", "water_source"],
    },
    {
        "variable_name": "household_demand",
        "claim": "Combined population across Kijani, Mtoni, and Amani: approximately 4,500 households",
        "value": 4500.0,
        "unit": "households",
        "confidence": 0.72,
        "status": "assumption",
        "source": "Illustrative data based on peri-urban Bujumbura infrastructure patterns",
        "tags": ["demographics"],
    },
    {
        "variable_name": "water_availability",
        "claim": "Current water availability estimated at 70–80% of peak community demand",
        "value": 0.75,
        "unit": "fraction of demand",
        "confidence": 0.55,
        "status": "inferred",
        "source": "Derived from rainfall and groundwater estimates — illustrative estimate based on Burundi infrastructure patterns",
        "tags": ["water_source"],
    },
    {
        "variable_name": "storage_level",
        "claim": "Existing storage capacity: approximately 1–1.5 days of community demand",
        "value": 1.2,
        "unit": "days of storage",
        "confidence": 0.65,
        "status": "assumption",
        "source": "Infrastructure survey estimates — illustrative estimate based on Burundi infrastructure patterns",
        "tags": ["infrastructure"],
    },
    {
        "variable_name": "pump_availability",
        "claim": "Current pump availability estimated at 55–65% of required uptime due to grid limitations",
        "value": 0.60,
        "unit": "fraction",
        "confidence": 0.50,
        "status": "inferred",
        "source": "Derived from electricity reliability — illustrative estimate based on Burundi infrastructure patterns",
        "tags": ["infrastructure"],
    },
]

# Additional evidence retrieved in follow-up research loops
MAJI_VALLEY_FOLLOWUP_EVIDENCE: list[dict[str, Any]] = [
    {
        "variable_name": "electricity_reliability",
        "claim": "Updated: Regional grid operator reports confirm average 14.5 hrs/day supply in peri-urban Bujumbura; solar irradiance levels are above regional average",
        "value": 0.60,
        "unit": "fraction of day",
        "confidence": 0.72,
        "status": "external_evidence",
        "source": "Regional grid operator reports + solar irradiance data (illustrative estimate based on Burundi infrastructure patterns)",
        "tags": ["energy", "solar", "infrastructure"],
        "notes": "Updated confidence from 0.55 to 0.72 based on additional corroborating data",
    },
    {
        "variable_name": "pump_availability",
        "claim": "Solar-powered pump systems in comparable peri-urban East Africa regions achieve 85–95% uptime vs 55–65% for grid-dependent pumps",
        "value": 0.90,
        "unit": "fraction (solar scenario)",
        "confidence": 0.75,
        "status": "external_evidence",
        "source": "Similar-region case studies — illustrative estimate based on Burundi infrastructure patterns",
        "tags": ["solar", "infrastructure"],
    },
    {
        "variable_name": "rainfall",
        "claim": "Updated: Long-term rainfall records for Bujumbura region show mean 820mm/year with coefficient of variation ~0.18",
        "value": 820.0,
        "unit": "mm/year",
        "confidence": 0.70,
        "status": "external_evidence",
        "source": "Regional meteorological station data (illustrative estimate based on Burundi infrastructure patterns)",
        "tags": ["climate", "water_source"],
    },
    {
        "variable_name": "storage_level",
        "claim": "Storage expansion to 3 days capacity reduces shortage frequency by ~60% in comparable scenarios",
        "value": 3.0,
        "unit": "days of storage (post-intervention)",
        "confidence": 0.68,
        "status": "inferred",
        "source": "Infrastructure engineering estimates — illustrative based on East Africa case studies",
        "tags": ["infrastructure", "storage"],
    },
    {
        "variable_name": "water_availability",
        "claim": "Combined solar pumping + storage intervention raises effective water availability to 85–92% of peak demand",
        "value": 0.88,
        "unit": "fraction of demand",
        "confidence": 0.65,
        "status": "inferred",
        "source": "Derived from pump uptime and storage capacity estimates — illustrative",
        "tags": ["water_source", "infrastructure"],
    },
]


class ResearchAgent:
    def __init__(
        self,
        gemini: GeminiClient,
        use_mock: bool = True,
    ) -> None:
        self._gemini = gemini
        self._use_mock = use_mock

    async def gather_evidence(
        self,
        run_id: str,
        decision_question: str,
        evidence_requirements: list[str],
        research_loop: int = 0,
        target_variable: str | None = None,
    ) -> ResearchFindings:
        """
        Main entry point: collect evidence for the given requirements.

        Args:
            run_id: The associated run.
            decision_question: The user's original question.
            evidence_requirements: List of evidence gaps to fill.
            research_loop: Which loop iteration (0 = first, 1+ = follow-up).
            target_variable: If set, focus this loop on this specific variable.
        """
        if self._use_mock:
            return self._mock_findings(run_id, research_loop, target_variable)

        return await self._gemini_findings(
            run_id, decision_question, evidence_requirements, research_loop, target_variable
        )

    def _mock_findings(
        self,
        run_id: str,
        research_loop: int,
        target_variable: str | None,
    ) -> ResearchFindings:
        """Return synthetic Maji Valley evidence."""
        if research_loop == 0:
            raw_items = MAJI_VALLEY_EVIDENCE
            query = "Initial evidence collection for Maji Valley water infrastructure"
            summary = (
                "Initial evidence collected from illustrative estimate based on Burundi infrastructure patternsset. "
                "Key uncertainty identified: electricity reliability (confidence 0.55). "
                "All data is illustrative — not real-world statistics."
            )
            missing = [
                "Confirmed grid outage frequency with independent verification",
                "Pump failure rate and maintenance history",
                "Seasonal demand variation across communities",
                "Solar irradiance levels for Maji Valley",
            ]
        else:
            # Filter follow-up evidence to items relevant to the target variable when possible
            target = target_variable or "electricity_reliability"
            targeted = [
                item for item in MAJI_VALLEY_FOLLOWUP_EVIDENCE
                if item.get("variable_name") == target
            ]
            raw_items = targeted if targeted else MAJI_VALLEY_FOLLOWUP_EVIDENCE
            query = f"Follow-up research targeting: {target} (loop {research_loop})"
            summary = (
                f"Follow-up evidence collected for '{target}'. "
                "Confidence updated with additional corroborating data. "
                "All data is illustrative — not real-world statistics."
            )
            missing = [
                "Long-term solar panel maintenance cost data",
                "Community technical capacity assessment",
            ]

        items = [
            EvidenceItem(
                run_id=run_id,
                claim=r["claim"],
                value=r.get("value"),
                unit=r.get("unit"),
                variable_name=r.get("variable_name"),
                source=r["source"],
                confidence=r["confidence"],
                confidence_level=ConfidenceLevel.from_float(r["confidence"]),
                status=EvidenceStatus(r["status"]),
                retrieved_at=utcnow(),
                research_loop=research_loop,
                tags=r.get("tags", []),
                notes=r.get("notes"),
            )
            for r in raw_items
        ]

        findings = ResearchFindings(
            run_id=run_id,
            research_loop=research_loop,
            query=query,
            items=items,
            missing_information=missing,
            summary=summary,
        )
        findings.compute_counts()
        return findings

    async def _gemini_findings(
        self,
        run_id: str,
        decision_question: str,
        evidence_requirements: list[str],
        research_loop: int,
        target_variable: str | None,
    ) -> ResearchFindings:
        """Use Gemini to generate structured research findings."""
        loop_context = (
            f"\n\nThis is research loop {research_loop + 1}. "
            f"Focus particularly on: {target_variable}"
            if target_variable
            else ""
        )

        prompt = f"""
Decision question: {decision_question}

Evidence requirements:
{chr(10).join(f'- {req}' for req in evidence_requirements)}
{loop_context}

Gather evidence for the above requirements. Return a JSON object with this schema:
{{
  "findings": [
    {{
      "claim": "string — specific, falsifiable claim",
      "variable_name": "string — one of: rainfall, electricity_reliability, household_demand, water_availability, storage_level, pump_availability, distribution_capacity, water_access",
      "value": number or null,
      "unit": "string",
      "confidence": 0.0-1.0,
      "status": "external_evidence|assumption|inferred",
      "source": "string — source name and caveat",
      "tags": ["string"]
    }}
  ],
  "missing_information": ["string"],
  "summary": "string"
}}
"""
        raw = await self._gemini.generate_structured(prompt, RESEARCH_AGENT_SYSTEM_PROMPT)

        findings_raw = raw.get("findings", [])
        missing = raw.get("missing_information", [])
        summary = raw.get("summary", "Research completed.")

        items = []
        for f in findings_raw:
            try:
                confidence = float(f.get("confidence", 0.5))
                item = EvidenceItem(
                    run_id=run_id,
                    claim=f["claim"],
                    value=f.get("value"),
                    unit=f.get("unit"),
                    variable_name=f.get("variable_name"),
                    source=f.get("source", "Gemini research"),
                    confidence=confidence,
                    confidence_level=ConfidenceLevel.from_float(confidence),
                    status=EvidenceStatus(f.get("status", "assumption")),
                    retrieved_at=utcnow(),
                    research_loop=research_loop,
                    tags=f.get("tags", []),
                )
                items.append(item)
            except (KeyError, ValueError) as e:
                logger.warning("Skipping malformed evidence item: %s — %s", f, e)

        findings = ResearchFindings(
            run_id=run_id,
            research_loop=research_loop,
            query=f"Evidence requirements: {evidence_requirements}",
            items=items,
            missing_information=missing,
            summary=summary,
        )
        findings.compute_counts()
        return findings
