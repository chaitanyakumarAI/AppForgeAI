"""
Stage 1 — Intent Extractor
Parses raw user input into a structured IntentSpec.
Handles vague, ambiguous, and conflicting prompts gracefully.
"""
from __future__ import annotations
from backend.llm_client import call_llm
from backend.validation.schemas import IntentSpec


SYSTEM_INSTRUCTION = """You are AppForge Stage 1: Intent Extractor.
Your job is to parse a user's natural language app description into a structured intent specification.
You MUST handle:
- Vague prompts: extract what you can, list ambiguities, make reasonable assumptions
- Conflicting requirements: note conflicts in ambiguities, pick the safer option
- Missing information: fill with industry-standard defaults

Always return valid JSON matching the IntentSpec schema exactly."""


PROMPT_TEMPLATE = """Parse this app description into a structured IntentSpec JSON:

USER PROMPT:
{user_prompt}

Return a JSON object with EXACTLY these fields:
{{
  "app_name": "string (short, descriptive name)",
  "app_type": "string (e.g. CRM, LMS, e-commerce, HR-tool, internal-tool, marketplace, SaaS)",
  "description": "string (one clear sentence about what this app does)",
  "entities": ["list of core data entities, e.g. User, Contact, Product, Order"],
  "roles": ["list of user roles, e.g. admin, user, manager, guest"],
  "features": ["list of features, e.g. login, dashboard, payments, analytics, RBAC, notifications"],
  "integrations": ["list of external integrations if any, e.g. Stripe, SendGrid, Google Calendar"],
  "constraints": ["hard constraints the app must satisfy"],
  "ambiguities": ["unclear or conflicting parts of the prompt — list each one"],
  "assumptions": [
    {{
      "field": "what was unclear",
      "value": "what you assumed",
      "reason": "why this assumption makes sense"
    }}
  ],
  "complexity": "simple | medium | complex"
}}

Rules:
- If the prompt is extremely vague (e.g. 'build an app'), extract what you can and list ambiguities
- Never hallucinate features not implied by the prompt
- Always include at least a 'User' entity
- Always include at least one role (default: 'admin', 'user')
"""


def run_stage1(user_prompt: str, mode: str = "balanced") -> tuple[IntentSpec, dict]:
    """
    Run Stage 1: Intent Extraction.
    Returns (IntentSpec, stage_metrics_dict)
    """
    prompt = PROMPT_TEMPLATE.format(user_prompt=user_prompt)
    raw, tokens_in, tokens_out, latency_ms = call_llm(
        prompt=prompt,
        stage="stage1_intent",
        mode=mode,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    # Ensure assumptions are properly structured
    assumptions = raw.get("assumptions", [])
    if assumptions and isinstance(assumptions[0], str):
        assumptions = [{"field": "general", "value": a, "reason": "assumed from context"} for a in assumptions]
        raw["assumptions"] = assumptions

    intent = IntentSpec(**raw)

    metrics = {
        "latency_ms": latency_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "status": "success",
    }
    return intent, metrics
