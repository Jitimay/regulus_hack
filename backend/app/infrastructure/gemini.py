"""
Gemini client wrapper.

Provides a clean abstraction over google-generativeai so the rest of
the codebase never imports it directly. Supports both the real API and
a mock mode for local development without credentials.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Wraps the Gemini generative AI SDK.

    Handles:
    - Model initialization with configurable model name
    - Structured JSON output extraction with validation
    - Retry with exponential backoff on transient failures
    - Mock mode for local development
    """

    def __init__(self, model_name: str, mock_mode: bool = False) -> None:
        self._model_name = model_name
        self._mock_mode = mock_mode
        self._model = None

        if not mock_mode:
            self._init_model()

    def _init_model(self) -> None:
        try:
            import google.generativeai as genai

            self._model = genai.GenerativeModel(
                model_name=self._model_name,
                generation_config={
                    "temperature": 0.2,  # Low temperature for structured reasoning
                    "top_p": 0.95,
                    "max_output_tokens": 8192,
                },
            )
            logger.info("gemini_client_initialized model=%s", self._model_name)
        except ImportError:
            logger.warning("google-generativeai not installed; switching to mock mode")
            self._mock_mode = True
        except Exception as e:
            logger.error("Failed to initialize Gemini: %s", e)
            self._mock_mode = True

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
    ) -> str:
        """Generate a text response from Gemini."""
        if self._mock_mode:
            return self._mock_response(prompt)

        import asyncio

        full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt

        def _call() -> str:
            response = self._model.generate_content(full_prompt)
            return response.text

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call)

    async def generate_structured(
        self,
        prompt: str,
        system_instruction: str | None = None,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a structured JSON response from Gemini.

        Extracts JSON from the response text robustly — handles code blocks,
        leading text, etc. Returns raw parsed dict; Pydantic validation is
        the caller's responsibility.
        """
        json_instruction = (
            "\n\nIMPORTANT: You must respond with ONLY valid JSON. "
            "Do not include any prose, markdown fences, or explanations. "
            "Output raw JSON only."
        )
        full_prompt = prompt + json_instruction
        raw = await self.generate(full_prompt, system_instruction)
        return _extract_json(raw)

    def _mock_response(self, prompt: str) -> str:
        """Return a plausible mock response for local dev."""
        prompt_lower = prompt.lower()

        if "problem" in prompt_lower or "analyze" in prompt_lower:
            return json.dumps({
                "objective": "Maximize reliable household water access while controlling downside risk",
                "constraints": ["Budget: $50,000", "Three communities", "Grid reliability uncertain"],
                "variables": ["electricity_reliability", "pump_availability", "storage_level", "water_availability"],
                "evidence_requirements": ["Grid outage frequency", "Pump maintenance costs", "Rainfall patterns"],
                "candidate_interventions": ["pump_expansion", "storage_expansion", "solar_pumping", "combined_strategy"],
            })

        if "evidence" in prompt_lower or "research" in prompt_lower:
            return json.dumps({
                "findings": [
                    {
                        "claim": "Electricity grid in Maji Valley averages 14 hours/day uptime",
                        "variable_name": "electricity_reliability",
                        "value": 0.58,
                        "unit": "fraction of day",
                        "confidence": 0.65,
                        "status": "assumption",
                        "source": "Regional infrastructure reports (synthetic demo data)",
                    },
                    {
                        "claim": "Total households across three communities: ~4,500",
                        "variable_name": "household_demand",
                        "value": 4500,
                        "unit": "households",
                        "confidence": 0.78,
                        "status": "assumption",
                        "source": "Community survey estimates (synthetic demo data)",
                    },
                    {
                        "claim": "Annual rainfall: approximately 600–700mm, moderate variability",
                        "variable_name": "rainfall",
                        "value": 650,
                        "unit": "mm/year",
                        "confidence": 0.60,
                        "status": "assumption",
                        "source": "Regional climate data (synthetic demo data)",
                    },
                ],
                "missing_information": [
                    "Actual grid outage frequency with high confidence",
                    "Current pump maintenance schedule and failure rates",
                    "Seasonal demand variation",
                ],
                "summary": "Initial evidence collected from synthetic demo dataset. Key uncertainty: electricity reliability.",
            })

        if "uncertainty" in prompt_lower or "sensitivity" in prompt_lower:
            return json.dumps({
                "needs_additional_research": True,
                "dominant_variable": "electricity_reliability",
                "research_question": "What is the actual grid reliability for Maji Valley communities?",
                "reason": "Electricity reliability has the highest sensitivity score (0.71) and low confidence (0.45). This variable directly drives pump availability and thus the comparative advantage of solar pumping.",
            })

        if "decision" in prompt_lower or "recommend" in prompt_lower:
            return json.dumps({
                "recommended_scenario": "solar_pumping",
                "reasoning": "Solar pumping eliminates the dominant source of uncertainty (electricity reliability) and delivers the highest expected access improvement with strong robustness. Combined strategy performs similarly but costs more relative to the marginal gain for this budget.",
                "confidence": 0.76,
                "key_risks": [
                    "Solar panel maintenance requires local technical capacity",
                    "High upfront capital cost concentrates risk in equipment procurement",
                    "Does not address storage shortfall during dry season",
                ],
                "key_assumptions": [
                    "Electricity grid reliability remains below 70% over next 5 years",
                    "Solar irradiance sufficient for consistent generation",
                    "Community maintenance capacity can be trained",
                ],
                "conditions_for_change": [
                    "If grid reliability improves above 85%, pump expansion becomes equally cost-effective",
                    "If rainfall drops below 500mm/year, storage expansion becomes critical",
                    "If community technical capacity is very low, distribution improvements may be preferable",
                ],
                "additional_research_findings": {
                    "electricity_reliability": {
                        "alpha": 7.5,
                        "beta": 2.0,
                        "confidence": 0.72,
                        "source": "Updated estimate from regional grid operator reports (synthetic demo)",
                    }
                },
            })

        return json.dumps({"result": "ok", "message": "Mock response"})


def _extract_json(text: str) -> dict[str, Any]:
    """
    Robustly extract JSON from a Gemini response.

    Handles:
    - Raw JSON
    - JSON wrapped in ```json ... ``` blocks
    - JSON preceded by explanatory prose
    """
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
    match = fence_pattern.search(text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Find the first { ... } block
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from Gemini response: {text[:200]}")
