"""
Stage 2 — System Designer
Converts IntentSpec into a full ArchitectureSpec:
entities with fields, auth roles, API surface, and UI flows.
"""
from __future__ import annotations
import json
from backend.llm_client import call_llm
from backend.validation.schemas import IntentSpec, ArchitectureSpec


SYSTEM_INSTRUCTION = """You are AppForge Stage 2: System Designer.
You receive a structured intent specification and produce a complete application architecture.
Think like a senior software architect:
- Define every entity with proper fields and relationships
- Design a realistic permission matrix
- List all API endpoints needed
- Map out all UI pages and flows
Always return valid JSON. Be comprehensive but not redundant."""


PROMPT_TEMPLATE = """Design the complete application architecture for this intent:

INTENT SPEC:
{intent_json}

Return a JSON object with EXACTLY these fields:
{{
  "data_model": [
    {{
      "name": "EntityName",
      "fields": [
        {{
          "name": "field_name",
          "type": "string|integer|float|boolean|datetime|uuid|text|json|enum",
          "required": true,
          "unique": false,
          "primary_key": false,
          "foreign_key": "other_table.id or null",
          "enum_values": [],
          "default": null
        }}
      ],
      "relations": [
        {{"type": "has_many|belongs_to|has_one|many_to_many", "target": "EntityName"}}
      ],
      "indexes": ["field_name_or_composite"]
    }}
  ],
  "permission_matrix": [
    {{
      "role": "role_name",
      "permissions": ["entity:action", "entity:*", "*"]
    }}
  ],
  "api_surface": [
    {{
      "path": "/api/resource",
      "method": "GET|POST|PUT|PATCH|DELETE",
      "description": "what this endpoint does",
      "auth_required": true,
      "roles": ["role1", "role2"]
    }}
  ],
  "ui_flows": [
    {{
      "name": "PageName",
      "route": "/route",
      "accessible_by": ["role1", "role2"],
      "description": "what user can do on this page"
    }}
  ],
  "auth_strategy": "JWT",
  "has_payments": false,
  "has_analytics": false
}}

Rules:
- Every entity MUST have an 'id' field (uuid, primary_key: true)
- Every entity MUST have 'created_at' and 'updated_at' datetime fields
- Users entity MUST have email (unique), password_hash, and role fields
- Foreign keys use format "table_name.id"
- Include CRUD endpoints for every entity
- Include /api/auth/login, /api/auth/logout, /api/auth/me always
- Include a dashboard page always
- admin role should have all permissions (*)
- Set has_payments=true if payments are mentioned
- Set has_analytics=true if analytics/reporting is mentioned
"""


def run_stage2(intent: IntentSpec, mode: str = "balanced") -> tuple[ArchitectureSpec, dict]:
    """
    Run Stage 2: System Design.
    Returns (ArchitectureSpec, stage_metrics_dict)
    """
    intent_json = json.dumps(intent.model_dump(), indent=2)
    prompt = PROMPT_TEMPLATE.format(intent_json=intent_json)

    raw, tokens_in, tokens_out, latency_ms = call_llm(
        prompt=prompt,
        stage="stage2_design",
        mode=mode,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    arch = ArchitectureSpec(**raw)
    metrics = {
        "latency_ms": latency_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "status": "success",
    }
    return arch, metrics
