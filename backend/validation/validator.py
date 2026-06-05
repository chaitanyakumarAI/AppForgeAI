"""
AppForge AI — Cross-Layer Consistency Validator
Runs after schema generation to detect all inconsistencies between DB, API, UI, and Auth layers.
"""
from __future__ import annotations
from .schemas import (
    CompleteSchema, ValidationReport, ValidationIssue
)


def validate_schema(schema: CompleteSchema) -> ValidationReport:
    """
    Main validator — runs all cross-layer checks and returns a ValidationReport.
    """
    issues: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    checks_run = 0

    db_tables  = {t.name.lower(): t for t in schema.db_schema}
    db_columns = {
        t.name.lower(): {c.name.lower() for c in t.columns}
        for t in schema.db_schema
    }
    api_paths   = {f"{e.method} {e.path}" for e in schema.api_schema}
    auth_roles  = {r.name.lower() for r in schema.auth_schema}
    ui_routes   = {p.route for p in schema.ui_schema}

    # ── Check 1: Auth roles referenced in API must exist ─────────────────────
    checks_run += 1
    for endpoint in schema.api_schema:
        for role in endpoint.roles:
            if role.lower() not in auth_roles:
                issues.append(ValidationIssue(
                    issue_type="missing_auth_role",
                    layer="cross_layer",
                    message=f"Endpoint '{endpoint.method} {endpoint.path}' references role '{role}' which is not defined in auth_schema.",
                    severity="error",
                    suggested_fix=f"Add role '{role}' to auth_schema."
                ))

    # ── Check 2: UI accessible_by roles must exist ────────────────────────────
    checks_run += 1
    for page in schema.ui_schema:
        for role in page.accessible_by:
            if role.lower() not in auth_roles:
                issues.append(ValidationIssue(
                    issue_type="missing_auth_role",
                    layer="cross_layer",
                    message=f"UI page '{page.route}' references undefined role '{role}'.",
                    severity="error",
                    suggested_fix=f"Add role '{role}' to auth_schema."
                ))

    # ── Check 3: API endpoints referencing a DB table must have that table ────
    checks_run += 1
    for endpoint in schema.api_schema:
        if endpoint.db_table:
            if endpoint.db_table.lower() not in db_tables:
                issues.append(ValidationIssue(
                    issue_type="orphaned_reference",
                    layer="cross_layer",
                    message=f"API endpoint '{endpoint.path}' references DB table '{endpoint.db_table}' which does not exist.",
                    severity="error",
                    suggested_fix=f"Add table '{endpoint.db_table}' to db_schema or fix endpoint reference."
                ))

    # ── Check 4: API response_fields must exist in the referenced DB table ────
    checks_run += 1
    for endpoint in schema.api_schema:
        if endpoint.db_table and endpoint.response_fields:
            table_cols = db_columns.get(endpoint.db_table.lower(), set())
            for field in endpoint.response_fields:
                if field.lower() not in table_cols and field not in ("id", "*", "all"):
                    warnings.append(ValidationIssue(
                        issue_type="inconsistent_field",
                        layer="cross_layer",
                        message=f"API '{endpoint.path}' response field '{field}' not found in table '{endpoint.db_table}'.",
                        severity="warning",
                        suggested_fix=f"Add '{field}' column to '{endpoint.db_table}' table or remove it from response_fields."
                    ))

    # ── Check 5: UI components referencing API endpoints ──────────────────────
    checks_run += 1
    for page in schema.ui_schema:
        for comp in page.components:
            if comp.api_endpoint:
                if comp.api_endpoint not in api_paths:
                    # Try partial match
                    path_only = comp.api_endpoint.split(" ")[-1]
                    matched = any(path_only in p for p in api_paths)
                    if not matched:
                        warnings.append(ValidationIssue(
                            issue_type="orphaned_reference",
                            layer="cross_layer",
                            message=f"UI component '{comp.id}' on page '{page.route}' references API '{comp.api_endpoint}' which is not in api_schema.",
                            severity="warning",
                            suggested_fix=f"Add endpoint '{comp.api_endpoint}' to api_schema."
                        ))

    # ── Check 6: UI components referencing entities must have a DB table ──────
    checks_run += 1
    for page in schema.ui_schema:
        for comp in page.components:
            if comp.entity:
                if comp.entity.lower() not in db_tables:
                    issues.append(ValidationIssue(
                        issue_type="orphaned_reference",
                        layer="cross_layer",
                        message=f"UI component '{comp.id}' references entity '{comp.entity}' with no matching DB table.",
                        severity="error",
                        suggested_fix=f"Add table '{comp.entity.lower()}' to db_schema."
                    ))

    # ── Check 7: Foreign keys must reference existing tables + columns ─────────
    checks_run += 1
    for table in schema.db_schema:
        for col in table.columns:
            if col.foreign_key:
                parts = col.foreign_key.split(".")
                if len(parts) == 2:
                    ref_table, ref_col = parts[0].lower(), parts[1].lower()
                    if ref_table not in db_tables:
                        issues.append(ValidationIssue(
                            issue_type="orphaned_reference",
                            layer="db",
                            message=f"Table '{table.name}'.'{col.name}' has foreign key to non-existent table '{ref_table}'.",
                            severity="error",
                            suggested_fix=f"Add table '{ref_table}' or fix the foreign key."
                        ))
                    elif ref_col not in db_columns.get(ref_table, set()):
                        issues.append(ValidationIssue(
                            issue_type="orphaned_reference",
                            layer="db",
                            message=f"Table '{table.name}'.'{col.name}' FK references non-existent column '{ref_table}.{ref_col}'.",
                            severity="error",
                            suggested_fix=f"Add column '{ref_col}' to table '{ref_table}'."
                        ))

    # ── Check 8: Business logic gates reference valid roles ───────────────────
    checks_run += 1
    for gate in schema.business_logic.gates:
        for role in gate.applies_to:
            if role.lower() not in auth_roles and role.lower() != "*":
                warnings.append(ValidationIssue(
                    issue_type="inconsistent_field",
                    layer="business_logic",
                    message=f"Business gate '{gate.name}' applies to undefined role '{role}'.",
                    severity="warning",
                    suggested_fix=f"Add role '{role}' to auth_schema."
                ))

    # ── Check 9: Each role must have at least one permission ──────────────────
    checks_run += 1
    for role in schema.auth_schema:
        if not role.permissions:
            warnings.append(ValidationIssue(
                issue_type="missing_key",
                layer="auth",
                message=f"Role '{role.name}' has no permissions defined.",
                severity="warning",
                suggested_fix=f"Add at least one permission to role '{role.name}'."
            ))

    # ── Check 10: Every DB table must have a primary key ─────────────────────
    checks_run += 1
    for table in schema.db_schema:
        has_pk = any(c.primary_key for c in table.columns)
        if not has_pk:
            issues.append(ValidationIssue(
                issue_type="missing_key",
                layer="db",
                message=f"DB table '{table.name}' has no primary key column.",
                severity="error",
                suggested_fix=f"Add a primary key column (e.g. 'id UUID PRIMARY KEY') to '{table.name}'."
            ))

    error_issues = [i for i in issues if i.severity == "error"]
    passed = len(error_issues) == 0

    return ValidationReport(
        passed=passed,
        issues=issues,
        warnings=warnings,
        checks_run=checks_run
    )
