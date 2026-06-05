"""
Stage 4 — Refinement Engine
Acts as the "linker" step of our compiler.
Takes the full CompleteSchema and resolves cross-layer inconsistencies.
This stage has access to all layers simultaneously.
"""
from __future__ import annotations
import json
from backend.llm_client import call_llm
from backend.validation.schemas import CompleteSchema


SYSTEM_INSTRUCTION = """You are AppForge Stage 4: Refinement Engine.
You receive a complete application schema and must resolve ALL cross-layer inconsistencies.
You are the final linker before validation. Your job:
1. Ensure every UI form field has a matching API param and DB column
2. Ensure every API role exists in auth_schema
3. Ensure foreign keys reference real tables and columns
4. Fill any obvious gaps (missing CRUD endpoints, missing columns)
5. Remove hallucinated/inconsistent references
Return the complete, corrected schema. Same structure as input."""


PROMPT_TEMPLATE = """Refine and repair this application schema for cross-layer consistency.

CURRENT SCHEMA (may have inconsistencies):
{schema_json}

KNOWN ISSUES TO CHECK:
- UI components should reference real API endpoints
- API endpoints should reference real DB tables  
- Auth roles in endpoints/pages must exist in auth_schema
- Foreign keys must reference real tables.columns
- Every entity in UI must have a matching DB table
- Business logic gates should reference valid roles

Your task:
1. Find ALL inconsistencies
2. Fix them by adding missing pieces or correcting wrong references
3. Do NOT remove anything valid
4. Return the complete corrected schema in EXACTLY the same JSON structure

Return the complete refined schema JSON (same structure as input, all fields required).
"""


def run_stage4(schema: CompleteSchema, mode: str = "balanced") -> tuple[CompleteSchema, dict]:
    """
    Run Stage 4: Refinement.
    Returns (CompleteSchema, stage_metrics_dict)
    """
    schema_json = json.dumps(schema.model_dump(), indent=2)
    prompt = PROMPT_TEMPLATE.format(schema_json=schema_json)

    raw, tokens_in, tokens_out, latency_ms = call_llm(
        prompt=prompt,
        stage="stage4_refinement",
        mode=mode,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    # Handle case where LLM wraps in an extra key
    if "schema" in raw and isinstance(raw["schema"], dict):
        raw = raw["schema"]
    if "app_name" not in raw and len(raw) == 1:
        raw = list(raw.values())[0]

    # Fix assumption format if needed
    assumptions = raw.get("assumptions", [])
    if assumptions and isinstance(assumptions[0], str):
        raw["assumptions"] = [
            {"field": "refinement", "value": a, "reason": "fixed during refinement"}
            for a in assumptions
        ]

    refined = CompleteSchema(**raw)
    metrics = {
        "latency_ms": latency_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "status": "success",
    }
    return refined, metrics
