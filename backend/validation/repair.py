"""
AppForge AI — Targeted Repair Engine
Instead of a blind full retry, identifies which layer has issues and re-generates ONLY that layer.
"""
from __future__ import annotations
import json
from .schemas import CompleteSchema, ValidationReport, ValidationIssue


# ── Layer isolation: which layers need repair ──────────────────────────────────

def identify_repair_targets(report: ValidationReport) -> list[str]:
    """Returns list of layers to repair, in order of priority."""
    broken_layers: set[str] = set()
    for issue in report.issues:
        if issue.severity == "error":
            if issue.layer in ("db", "api", "ui", "auth", "business_logic"):
                broken_layers.add(issue.layer)
            elif issue.layer == "cross_layer":
                # cross-layer errors: repair whichever layer has the missing piece
                msg = issue.message.lower()
                if "db table" in msg or "foreign key" in msg or "column" in msg:
                    broken_layers.add("db")
                if "api endpoint" in msg or "api '" in msg:
                    broken_layers.add("api")
                if "ui " in msg:
                    broken_layers.add("ui")
                if "role" in msg or "auth" in msg:
                    broken_layers.add("auth")
    # Priority: db first (others depend on it), then api, auth, ui
    priority = ["db", "api", "auth", "business_logic", "ui"]
    return [l for l in priority if l in broken_layers]


def build_repair_prompt(schema: CompleteSchema, issues: list[ValidationIssue],
                         target_layer: str) -> str:
    """
    Builds a focused repair prompt for a specific layer.
    Only sends the relevant part of the schema + the issues to fix.
    """
    relevant_issues = [i for i in issues if i.layer == target_layer or i.layer == "cross_layer"]
    issue_text = "\n".join(
        f"- [{i.issue_type}] {i.message} → Fix: {i.suggested_fix}"
        for i in relevant_issues
    )

    if target_layer == "db":
        layer_json = json.dumps([t.model_dump() for t in schema.db_schema], indent=2)
        return_key = "db_schema"
    elif target_layer == "api":
        layer_json = json.dumps([e.model_dump() for e in schema.api_schema], indent=2)
        return_key = "api_schema"
    elif target_layer == "ui":
        layer_json = json.dumps([p.model_dump() for p in schema.ui_schema], indent=2)
        return_key = "ui_schema"
    elif target_layer == "auth":
        layer_json = json.dumps([r.model_dump() for r in schema.auth_schema], indent=2)
        return_key = "auth_schema"
    elif target_layer == "business_logic":
        layer_json = json.dumps(schema.business_logic.model_dump(), indent=2)
        return_key = "business_logic"
    else:
        layer_json = "{}"
        return_key = target_layer

    # Cross-reference context for the repair
    context_parts = []
    if target_layer != "db":
        context_parts.append(f"DB tables: {[t.name for t in schema.db_schema]}")
        context_parts.append(f"DB columns per table: { {t.name: [c.name for c in t.columns] for t in schema.db_schema} }")
    if target_layer != "auth":
        context_parts.append(f"Auth roles: {[r.name for r in schema.auth_schema]}")
    if target_layer != "api":
        context_parts.append(f"API endpoints: {[f'{e.method} {e.path}' for e in schema.api_schema]}")

    context_str = "\n".join(context_parts)

    return f"""You are a schema repair agent. Fix ONLY the {target_layer} layer of this app schema.

ISSUES TO FIX:
{issue_text}

CURRENT {target_layer.upper()} LAYER:
{layer_json}

CONTEXT FROM OTHER LAYERS (do not modify these, only use for reference):
{context_str}

INSTRUCTIONS:
1. Fix ALL issues listed above
2. Do NOT change anything that is not broken
3. Maintain all existing valid data
4. Return ONLY a valid JSON object with key "{return_key}" containing the fixed layer
5. No explanations, no markdown, just JSON

Return format:
{{ "{return_key}": <fixed_{target_layer}_layer_here> }}"""


def apply_repair(schema: CompleteSchema, repaired_layer: dict, target_layer: str) -> CompleteSchema:
    """Applies the repaired layer data back onto the schema."""
    schema_dict = schema.model_dump()

    layer_key_map = {
        "db":             "db_schema",
        "api":            "api_schema",
        "ui":             "ui_schema",
        "auth":           "auth_schema",
        "business_logic": "business_logic",
    }
    schema_key = layer_key_map.get(target_layer, target_layer)
    if schema_key in repaired_layer:
        schema_dict[schema_key] = repaired_layer[schema_key]

    return CompleteSchema(**schema_dict)
