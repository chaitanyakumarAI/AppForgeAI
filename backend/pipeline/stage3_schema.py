"""
Stage 3 — Schema Generator
Converts ArchitectureSpec into the complete 5-layer schema:
DB, API, UI, Auth, and Business Logic.
This is the most token-intensive stage — uses structured output carefully.
"""
from __future__ import annotations
import json
from backend.llm_client import call_llm
from backend.validation.schemas import ArchitectureSpec, IntentSpec, CompleteSchema


SYSTEM_INSTRUCTION = """You are AppForge Stage 3: Schema Generator.
You produce the complete, production-ready schema for all layers of the application.
This output will be directly used to generate a working application.
Every field must be precise, consistent, and cross-referenced.
Always return valid JSON. No approximations."""


PROMPT_TEMPLATE = """Generate the complete 5-layer application schema from this architecture:

INTENT:
{intent_json}

ARCHITECTURE:
{arch_json}

Return a JSON object with EXACTLY this structure:
{{
  "app_name": "string",
  "version": "1.0",
  "db_schema": [
    {{
      "name": "table_name",
      "description": "what this table stores",
      "columns": [
        {{
          "name": "column_name",
          "type": "UUID|VARCHAR|TEXT|INTEGER|FLOAT|BOOLEAN|TIMESTAMP|JSONB|ENUM",
          "primary_key": false,
          "nullable": false,
          "unique": false,
          "default": null,
          "foreign_key": "ref_table.ref_col or null",
          "enum_values": []
        }}
      ],
      "indexes": ["column_name or composite_key"]
    }}
  ],
  "api_schema": [
    {{
      "path": "/api/resource",
      "method": "GET|POST|PUT|PATCH|DELETE",
      "summary": "what this endpoint does",
      "auth_required": true,
      "roles": ["role_names"],
      "request_params": [
        {{
          "name": "param_name",
          "type": "string|integer|boolean|object|array",
          "required": true,
          "location": "body|query|path|header",
          "description": "description"
        }}
      ],
      "response_fields": ["field1", "field2"],
      "db_table": "primary_table_name_or_null"
    }}
  ],
  "ui_schema": [
    {{
      "name": "PageName",
      "route": "/route",
      "title": "Page Display Title",
      "accessible_by": ["role1"],
      "layout": "default|sidebar|fullscreen|split",
      "components": [
        {{
          "id": "unique_component_id",
          "type": "DataTable|Form|Card|Chart|Sidebar|NavBar|Modal|StatsCard|KanbanBoard|FileUpload",
          "entity": "entity_name_or_null",
          "api_endpoint": "METHOD /api/path or null",
          "fields": ["field1", "field2"],
          "props": {{}}
        }}
      ]
    }}
  ],
  "auth_schema": [
    {{
      "name": "role_name",
      "permissions": ["entity:action", "*"],
      "inherits": "parent_role_or_null"
    }}
  ],
  "business_logic": {{
    "gates": [
      {{
        "name": "gate_name",
        "description": "what this gate controls",
        "condition": "user.plan == 'premium' or user.role == 'admin'",
        "applies_to": ["page_route or feature_name"]
      }}
    ],
    "computed_fields": [
      {{
        "entity": "entity_name",
        "field": "computed_field_name",
        "formula": "description of how it's computed"
      }}
    ],
    "triggers": [
      {{
        "event": "entity.action e.g. payment.created",
        "action": "what happens e.g. send_email, update_status"
      }}
    ]
  }},
  "assumptions": [
    {{
      "field": "what was decided",
      "value": "the decision",
      "reason": "why"
    }}
  ]
}}

CRITICAL RULES:
1. Every DB table MUST have 'id' (UUID, primary_key=true) as first column
2. Every DB table MUST have 'created_at' and 'updated_at' (TIMESTAMP, nullable=false)
3. All foreign keys must reference tables that exist in db_schema
4. All API endpoint roles must exist in auth_schema
5. All UI component entity fields must reference tables in db_schema
6. API response_fields must match actual column names in the db_table
7. Include ALL endpoints from the architecture's api_surface (plus add standard CRUD)
8. Include a NavBar component on every page
9. Component IDs must be unique across ALL pages
10. If payments: include /api/payments/create and /api/payments/webhook endpoints
11. If analytics: include a Chart component on the dashboard
"""


def run_stage3(intent: IntentSpec, arch: ArchitectureSpec, mode: str = "balanced") -> tuple[CompleteSchema, dict]:
    """
    Run Stage 3: Schema Generation.
    Returns (CompleteSchema, stage_metrics_dict)
    """
    intent_json = json.dumps(intent.model_dump(), indent=2)
    arch_json   = json.dumps(arch.model_dump(), indent=2)
    prompt = PROMPT_TEMPLATE.format(intent_json=intent_json, arch_json=arch_json)

    raw, tokens_in, tokens_out, latency_ms = call_llm(
        prompt=prompt,
        stage="stage3_schema",
        mode=mode,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    # Ensure assumptions are structured correctly
    assumptions = raw.get("assumptions", [])
    if assumptions and isinstance(assumptions[0], str):
        raw["assumptions"] = [
            {"field": "general", "value": a, "reason": "derived from architecture"}
            for a in assumptions
        ]

    schema = CompleteSchema(**raw)
    metrics = {
        "latency_ms": latency_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "status": "success",
    }
    return schema, metrics
