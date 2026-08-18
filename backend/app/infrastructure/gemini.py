"""
Gemini client wrapper — uses the official Google GenAI SDK (google-genai).

This satisfies the hackathon mandatory requirement:
  "at least one Google Agent Framework: Google ADK, GenAI SDK, Antigravity SDK or GenKit"

The GenAI SDK (google-genai) is the official Python client for Gemini API.
See: https://googleapis.github.io/python-genai/

Supports both the real API and a mock mode for local development without credentials.
"""

from __future__ import annotations

import json
import logging
import os
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
    Wraps the Google GenAI SDK (google-genai).

    Handles:
    - Client initialization with configurable model name
    - Structured JSON output extraction with validation
    - Retry with exponential backoff on transient failures
    - Mock mode for local development without credentials
    """

    def __init__(self, model_name: str, mock_mode: bool = False) -> None:
        self._model_name = model_name
        self._mock_mode = mock_mode
        self._client = None

        if not mock_mode:
            self._init_client()

    def _init_client(self) -> None:
        try:
            from google import genai

            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if api_key:
                self._client = genai.Client(api_key=api_key)
            else:
                # Use Application Default Credentials (for Cloud Run)
                self._client = genai.Client(
                    vertexai=bool(os.environ.get("GOOGLE_CLOUD_PROJECT")),
                    project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
                    location=os.environ.get("GOOGLE_CLOUD_REGION", "us-central1"),
                )
            logger.info("gemini_client_initialized sdk=google-genai model=%s", self._model_name)
        except ImportError:
            logger.warning("google-genai not installed; switching to mock mode")
            self._mock_mode = True
        except Exception as e:
            logger.error("Failed to initialize GenAI client: %s — switching to mock mode", e)
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
        """Generate a text response from Gemini via the GenAI SDK."""
        if self._mock_mode:
            return self._mock_response(prompt)

        import asyncio
        from google.genai import types

        contents = prompt
        config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.95,
            max_output_tokens=8192,
            system_instruction=system_instruction,
        )

        def _call() -> str:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=contents,
                config=config,
            )
            return response.text

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _call)

    async def generate_structured(
        self,
        prompt: str,
        system_instruction: str | None = None,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a structured JSON response from Gemini.

        Uses the GenAI SDK's response_mime_type="application/json" for
        reliable structured output when not in mock mode.
        """
        if self._mock_mode:
            raw = self._mock_response(prompt)
            return _extract_json(raw)

        import asyncio
        from google.genai import types

        json_instruction = (
            "\n\nIMPORTANT: Respond with ONLY valid JSON. "
            "No prose, no markdown fences. Raw JSON only."
        )
        config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.95,
            max_output_tokens=8192,
            system_instruction=system_instruction,
            response_mime_type="application/json",
        )

        def _call() -> str:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=prompt + json_instruction,
                config=config,
            )
            return response.text

        loop = asyncio.get_running_loop()
        raw = await loop.run_in_executor(None, _call)
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
                "reason": "Electricity reliability has the highest sensitivity score and low confidence. This variable directly drives pump availability and the comparative advantage of solar pumping.",
            })

        if "decision" in prompt_lower or "recommend" in prompt_lower:
            return json.dumps({
                "recommended_scenario": "solar_pumping",
                "reasoning": "Solar pumping eliminates the dominant source of uncertainty (electricity reliability) and delivers the highest expected access improvement with strong robustness.",
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
    Handles raw JSON, markdown fences, and prose-prefixed responses.
    """
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE).search(text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start: brace_end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from Gemini response: {text[:200]}")
