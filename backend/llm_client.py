"""
AppForge AI — LLM Client Abstraction
Wraps Google Gemini (primary) with a clean async interface.
Returns parsed JSON and token counts.
"""
from __future__ import annotations
import json
import time
import re
import google.generativeai as genai
from backend.config import (
    LLM_PROVIDER, GEMINI_API_KEY, MODELS, DEFAULT_MODE,
    STAGE_TEMPERATURES, COST_PER_1M
)


def _configure_gemini():
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set. Please add it to your .env file.")
    genai.configure(api_key=GEMINI_API_KEY)


def _extract_json(text: str) -> dict:
    """Robustly extracts JSON from LLM response, handling markdown code blocks."""
    text = text.strip()
    # Remove markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Find first { or [ and parse from there
        start = min(
            (text.find(c) for c in ["{", "["] if c in text),
            default=-1
        )
        if start != -1:
            try:
                return json.loads(text[start:])
            except Exception:
                pass
        raise ValueError(f"Could not extract valid JSON from LLM response. Preview: {text[:300]}")


def call_llm(
    prompt: str,
    stage: str,
    mode: str = DEFAULT_MODE,
    system_instruction: str | None = None,
) -> tuple[dict, int, int, float]:
    """
    Call the configured LLM and return:
      (parsed_json, tokens_in, tokens_out, latency_ms)
    """
    _configure_gemini()
    model_name = MODELS.get(mode, MODELS["balanced"])
    temperature = STAGE_TEMPERATURES.get(stage, 0.0)

    t0 = time.time()
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=genai.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json",
        ),
        system_instruction=system_instruction or (
            "You are AppForge AI — a compiler for software generation. "
            "Always return valid JSON matching the requested schema exactly. "
            "Never include explanations outside the JSON structure."
        ),
    )
    response = model.generate_content(prompt)
    latency_ms = int((time.time() - t0) * 1000)

    raw_text = response.text or ""
    parsed = _extract_json(raw_text)

    # Token counts
    try:
        tokens_in  = response.usage_metadata.prompt_token_count or 0
        tokens_out = response.usage_metadata.candidates_token_count or 0
    except Exception:
        tokens_in, tokens_out = 0, 0

    return parsed, tokens_in, tokens_out, latency_ms


def estimate_cost(model_name: str, tokens_in: int, tokens_out: int) -> float:
    """Returns estimated cost in USD."""
    rates = COST_PER_1M.get(model_name, {"input": 1.0, "output": 3.0})
    return (tokens_in * rates["input"] + tokens_out * rates["output"]) / 1_000_000
