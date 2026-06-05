"""
AppForge AI — Pydantic Schemas (Strict Contract)
These define the exact data contract between pipeline stages.
"""
from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# ── Stage 1 Output: IntentSpec ─────────────────────────────────────────────────

class Assumption(BaseModel):
    field: str
    value: str
    reason: str

class IntentSpec(BaseModel):
    model_config = ConfigDict(strict=False)

    app_name: str = Field(..., description="Short app name")
    app_type: str = Field(..., description="e.g. CRM, LMS, e-commerce, internal-tool")
    description: str = Field(..., description="One-sentence description of what the app does")
    entities: list[str] = Field(..., description="Core data entities e.g. ['User','Contact','Deal']")
    roles: list[str] = Field(..., description="User roles e.g. ['admin','sales','viewer']")
    features: list[str] = Field(..., description="Feature list e.g. ['login','dashboard','payments']")
    integrations: list[str] = Field(default_factory=list, description="External integrations if any")
    constraints: list[str] = Field(default_factory=list, description="Hard constraints e.g. 'must be multi-tenant'")
    ambiguities: list[str] = Field(default_factory=list, description="Unclear parts of the prompt")
    assumptions: list[Assumption] = Field(default_factory=list, description="Assumptions made for ambiguities")
    complexity: Literal["simple", "medium", "complex"] = Field(default="medium")


# ── Stage 2 Output: ArchitectureSpec ──────────────────────────────────────────

class FieldDef(BaseModel):
    name: str
    type: Literal["string", "integer", "float", "boolean", "datetime", "uuid", "text", "json", "enum"]
    required: bool = True
    unique: bool = False
    primary_key: bool = False
    foreign_key: Optional[str] = None      # e.g. "users.id"
    enum_values: list[str] = Field(default_factory=list)
    default: Optional[Any] = None

class EntityDef(BaseModel):
    name: str
    fields: list[FieldDef]
    relations: list[dict[str, str]] = Field(default_factory=list)  # [{type, target}]
    indexes: list[str] = Field(default_factory=list)

class PermissionMatrix(BaseModel):
    role: str
    permissions: list[str]   # e.g. ["contacts:read", "contacts:write", "*"]

class ApiEndpointSummary(BaseModel):
    path: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    description: str
    auth_required: bool = True
    roles: list[str] = Field(default_factory=list)

class UIPage(BaseModel):
    name: str
    route: str
    accessible_by: list[str] = Field(default_factory=list)
    description: str

class ArchitectureSpec(BaseModel):
    model_config = ConfigDict(strict=False)

    data_model: list[EntityDef]
    permission_matrix: list[PermissionMatrix]
    api_surface: list[ApiEndpointSummary]
    ui_flows: list[UIPage]
    auth_strategy: Literal["JWT", "session", "oauth2"] = "JWT"
    has_payments: bool = False
    has_analytics: bool = False


# ── Stage 3 Output: CompleteSchema ────────────────────────────────────────────

class DBColumn(BaseModel):
    name: str
    type: str
    primary_key: bool = False
    nullable: bool = False
    unique: bool = False
    default: Optional[Any] = None
    foreign_key: Optional[str] = None
    enum_values: list[str] = Field(default_factory=list)

class DBTable(BaseModel):
    name: str
    columns: list[DBColumn]
    indexes: list[str] = Field(default_factory=list)
    description: str = ""

class APIParam(BaseModel):
    name: str
    type: str
    required: bool = True
    location: Literal["body", "query", "path", "header"] = "body"
    description: str = ""

class APIEndpoint(BaseModel):
    path: str
    method: str
    summary: str
    auth_required: bool = True
    roles: list[str] = Field(default_factory=list)
    request_params: list[APIParam] = Field(default_factory=list)
    response_fields: list[str] = Field(default_factory=list)
    db_table: Optional[str] = None    # primary DB table this endpoint touches

class UIComponent(BaseModel):
    id: str
    type: str    # "DataTable" | "Form" | "Card" | "Chart" | "Sidebar" | "NavBar"
    entity: Optional[str] = None
    api_endpoint: Optional[str] = None
    fields: list[str] = Field(default_factory=list)
    props: dict[str, Any] = Field(default_factory=dict)

class UIPageSchema(BaseModel):
    name: str
    route: str
    title: str
    accessible_by: list[str] = Field(default_factory=list)
    layout: str = "default"
    components: list[UIComponent]

class AuthRole(BaseModel):
    name: str
    permissions: list[str]
    inherits: Optional[str] = None

class BusinessGate(BaseModel):
    name: str
    description: str
    condition: str    # e.g. "user.plan == 'premium'"
    applies_to: list[str]

class BusinessLogic(BaseModel):
    gates: list[BusinessGate] = Field(default_factory=list)
    computed_fields: list[dict[str, str]] = Field(default_factory=list)
    triggers: list[dict[str, str]] = Field(default_factory=list)

class CompleteSchema(BaseModel):
    model_config = ConfigDict(strict=False)

    app_name: str
    version: str = "1.0"
    db_schema: list[DBTable]
    api_schema: list[APIEndpoint]
    ui_schema: list[UIPageSchema]
    auth_schema: list[AuthRole]
    business_logic: BusinessLogic
    assumptions: list[Assumption] = Field(default_factory=list)


# ── Validation Result ─────────────────────────────────────────────────────────

class ValidationIssue(BaseModel):
    issue_type: Literal[
        "missing_key", "type_mismatch", "orphaned_reference",
        "inconsistent_field", "missing_auth_role", "unreachable_route",
        "hallucinated_field"
    ]
    layer: Literal["db", "api", "ui", "auth", "business_logic", "cross_layer"]
    message: str
    severity: Literal["error", "warning"] = "error"
    suggested_fix: str = ""

class ValidationReport(BaseModel):
    passed: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    checks_run: int = 0

class ExecutionCheck(BaseModel):
    component: str
    status: Literal["pass", "fail", "warn"]
    detail: str

class ExecutionReport(BaseModel):
    executable: bool
    checks: list[ExecutionCheck]
    components_verified: int
    unresolved_references: list[str] = Field(default_factory=list)


# ── Final API Response ─────────────────────────────────────────────────────────

class StageMetrics(BaseModel):
    latency_ms: int
    tokens_in: int = 0
    tokens_out: int = 0
    status: str

class PipelineMetrics(BaseModel):
    model_config = ConfigDict(strict=False, protected_namespaces=())
    total_latency_ms: int
    estimated_cost_usd: float
    model_used: str
    mode: str
    repair_attempts: int = 0
    stages: dict[str, StageMetrics]

class AppForgeResponse(BaseModel):
    model_config = ConfigDict(strict=False, protected_namespaces=())
    run_id: str
    status: Literal["success", "failed", "repaired"]
    intent: Optional[IntentSpec] = None
    architecture: Optional[ArchitectureSpec] = None
    app_schema: Optional[CompleteSchema] = None
    validation_report: Optional[ValidationReport] = None
    execution_report: Optional[ExecutionReport] = None
    metrics: Optional[PipelineMetrics] = None
    error: Optional[str] = None
