from backend.validation.schemas import (
    IntentSpec, Assumption, ArchitectureSpec, EntityDef, FieldDef,
    PermissionMatrix, ApiEndpointSummary, UIPage, CompleteSchema,
    DBTable, DBColumn, APIEndpoint, APIParam, UIComponent, UIPageSchema,
    AuthRole, BusinessGate, BusinessLogic, ValidationReport, ExecutionReport,
    ExecutionCheck, PipelineMetrics, StageMetrics, AppForgeResponse
)

def get_mock_crm_response(run_id: str, prompt: str, mode: str) -> AppForgeResponse:
    # 1. Intent Spec
    intent = IntentSpec(
        app_name="AppForge CRM",
        app_type="CRM",
        description="Premium CRM platform with contacts management, deal pipeline, role-based access control, analytics, and Stripe billing integrations.",
        entities=["users", "contacts", "deals"],
        roles=["admin", "sales", "viewer"],
        features=["login", "contacts-management", "deal-pipeline", "analytics-dashboard", "stripe-billing"],
        integrations=["Stripe"],
        constraints=["Role-based data scoping", "Stripe payment gate for premium features"],
        ambiguities=["Are deal pipeline stages static or customizable?"],
        assumptions=[
            Assumption(
                field="deal_pipeline_stages",
                value="static",
                reason="Standard CRM features use standard stages (lead, qualified, proposal, won, lost)."
            )
        ],
        complexity="complex"
    )

    # 2. Architecture Spec
    arch = ArchitectureSpec(
        data_model=[
            EntityDef(
                name="users",
                fields=[
                    FieldDef(name="id", type="integer", primary_key=True),
                    FieldDef(name="email", type="string", unique=True),
                    FieldDef(name="password_hash", type="string"),
                    FieldDef(name="role", type="string")
                ]
            ),
            EntityDef(
                name="contacts",
                fields=[
                    FieldDef(name="id", type="integer", primary_key=True),
                    FieldDef(name="name", type="string"),
                    FieldDef(name="email", type="string"),
                    FieldDef(name="phone", type="string"),
                    FieldDef(name="owner_id", type="integer", foreign_key="users.id")
                ]
            ),
            EntityDef(
                name="deals",
                fields=[
                    FieldDef(name="id", type="integer", primary_key=True),
                    FieldDef(name="contact_id", type="integer", foreign_key="contacts.id"),
                    FieldDef(name="value", type="float"),
                    FieldDef(name="stage", type="string"),
                    FieldDef(name="owner_id", type="integer", foreign_key="users.id")
                ]
            )
        ],
        permission_matrix=[
            PermissionMatrix(role="admin", permissions=["*"]),
            PermissionMatrix(role="sales", permissions=["contacts:read", "contacts:write", "deals:read", "deals:write"]),
            PermissionMatrix(role="viewer", permissions=["contacts:read", "deals:read"])
        ],
        api_surface=[
            ApiEndpointSummary(path="/api/auth/login", method="POST", auth_required=False, description="User authentication"),
            ApiEndpointSummary(path="/api/contacts", method="GET", roles=["admin", "sales", "viewer"], description="List contacts"),
            ApiEndpointSummary(path="/api/contacts", method="POST", roles=["admin", "sales"], description="Create contact"),
            ApiEndpointSummary(path="/api/deals", method="GET", roles=["admin", "sales", "viewer"], description="List deals"),
            ApiEndpointSummary(path="/api/deals", method="POST", roles=["admin", "sales"], description="Create deal"),
            ApiEndpointSummary(path="/api/analytics", method="GET", roles=["admin"], description="View sales analytics"),
            ApiEndpointSummary(path="/api/billing/stripe", method="POST", roles=["admin", "sales"], description="Initialize Stripe billing")
        ],
        ui_flows=[
            UIPage(name="Login", route="/login", accessible_by=["*"], description="Authentication page"),
            UIPage(name="Dashboard", route="/dashboard", accessible_by=["admin", "sales", "viewer"], description="Main summary workspace"),
            UIPage(name="Contacts", route="/contacts", accessible_by=["admin", "sales", "viewer"], description="Manage contacts list"),
            UIPage(name="Deals", route="/deals", accessible_by=["admin", "sales", "viewer"], description="Sales pipelines"),
            UIPage(name="Analytics", route="/analytics", accessible_by=["admin"], description="Admin revenue charts"),
            UIPage(name="Billing", route="/billing", accessible_by=["admin", "sales"], description="Stripe billing portal")
        ],
        auth_strategy="JWT",
        has_payments=True,
        has_analytics=True
    )

    # 3. Complete Schema
    schema = CompleteSchema(
        app_name="AppForge CRM",
        version="1.0",
        db_schema=[
            DBTable(
                name="users",
                columns=[
                    DBColumn(name="id", type="INTEGER", primary_key=True),
                    DBColumn(name="email", type="VARCHAR", unique=True),
                    DBColumn(name="password_hash", type="VARCHAR"),
                    DBColumn(name="role", type="VARCHAR", default="sales")
                ],
                description="System users and credentials"
            ),
            DBTable(
                name="contacts",
                columns=[
                    DBColumn(name="id", type="INTEGER", primary_key=True),
                    DBColumn(name="name", type="VARCHAR"),
                    DBColumn(name="email", type="VARCHAR"),
                    DBColumn(name="phone", type="VARCHAR", nullable=True),
                    DBColumn(name="owner_id", type="INTEGER", foreign_key="users.id")
                ],
                description="Client leads and contact details"
            ),
            DBTable(
                name="deals",
                columns=[
                    DBColumn(name="id", type="INTEGER", primary_key=True),
                    DBColumn(name="contact_id", type="INTEGER", foreign_key="contacts.id"),
                    DBColumn(name="value", type="FLOAT", default=0.0),
                    DBColumn(name="stage", type="VARCHAR", default="lead"),
                    DBColumn(name="owner_id", type="INTEGER", foreign_key="users.id")
                ],
                description="Sales opportunities and current pipeline status"
            )
        ],
        api_schema=[
            APIEndpoint(
                path="/api/auth/login",
                method="POST",
                summary="Authenticate user and issue token",
                auth_required=False,
                request_params=[
                    APIParam(name="email", type="string", required=True),
                    APIParam(name="password", type="string", required=True)
                ],
                response_fields=["token", "user"],
                db_table="users"
            ),
            APIEndpoint(
                path="/api/contacts",
                method="GET",
                summary="Retrieve lists of contacts",
                auth_required=True,
                roles=["admin", "sales", "viewer"],
                response_fields=["id", "name", "email", "phone", "owner_id"],
                db_table="contacts"
            ),
            APIEndpoint(
                path="/api/contacts",
                method="POST",
                summary="Create a new contact",
                auth_required=True,
                roles=["admin", "sales"],
                request_params=[
                    APIParam(name="name", type="string", required=True),
                    APIParam(name="email", type="string", required=True),
                    APIParam(name="phone", type="string", required=False)
                ],
                response_fields=["id", "name"],
                db_table="contacts"
            ),
            APIEndpoint(
                path="/api/deals",
                method="GET",
                summary="Retrieve deals list",
                auth_required=True,
                roles=["admin", "sales", "viewer"],
                response_fields=["id", "contact_id", "value", "stage", "owner_id"],
                db_table="deals"
            ),
            APIEndpoint(
                path="/api/deals",
                method="POST",
                summary="Create a new deal opportunity",
                auth_required=True,
                roles=["admin", "sales"],
                request_params=[
                    APIParam(name="contact_id", type="integer", required=True),
                    APIParam(name="value", type="float", required=True),
                    APIParam(name="stage", type="string", required=False)
                ],
                response_fields=["id", "value", "stage"],
                db_table="deals"
            ),
            APIEndpoint(
                path="/api/analytics",
                method="GET",
                summary="Calculate and compile sales metrics",
                auth_required=True,
                roles=["admin"],
                response_fields=["*"],
                db_table="deals"
            ),
            APIEndpoint(
                path="/api/billing/stripe",
                method="POST",
                summary="Initialize checkout session via Stripe",
                auth_required=True,
                roles=["admin", "sales"],
                request_params=[
                    APIParam(name="plan_id", type="string", required=True)
                ],
                response_fields=["checkout_url"],
                db_table="users"
            )
        ],
        ui_schema=[
            UIPageSchema(
                name="Login",
                route="/login",
                title="Authenticate to Portal",
                accessible_by=["*"],
                components=[
                    UIComponent(id="login-form", type="Form", api_endpoint="POST /api/auth/login", fields=["email", "password"])
                ]
            ),
            UIPageSchema(
                name="Dashboard",
                route="/dashboard",
                title="AppForge CRM Dashboard",
                accessible_by=["admin", "sales", "viewer"],
                components=[
                    UIComponent(id="summary-kpis", type="Card", entity="deals", fields=["value", "stage"]),
                    UIComponent(id="recent-deals-chart", type="Chart", entity="deals", api_endpoint="GET /api/deals")
                ]
            ),
            UIPageSchema(
                name="Contacts",
                route="/contacts",
                title="Contact Management Workspace",
                accessible_by=["admin", "sales", "viewer"],
                components=[
                    UIComponent(id="contacts-list-table", type="DataTable", entity="contacts", api_endpoint="GET /api/contacts"),
                    UIComponent(id="new-contact-creator", type="Form", entity="contacts", api_endpoint="POST /api/contacts", fields=["name", "email", "phone"])
                ]
            ),
            UIPageSchema(
                name="Deals",
                route="/deals",
                title="Sales Pipelines",
                accessible_by=["admin", "sales", "viewer"],
                components=[
                    UIComponent(id="deals-board-kanban", type="DataTable", entity="deals", api_endpoint="GET /api/deals"),
                    UIComponent(id="new-deal-creator", type="Form", entity="deals", api_endpoint="POST /api/deals", fields=["contact_id", "value", "stage"])
                ]
            ),
            UIPageSchema(
                name="Analytics",
                route="/analytics",
                title="Executive Revenue Analytics",
                accessible_by=["admin"],
                components=[
                    UIComponent(id="pipeline-won-chart", type="Chart", entity="deals", api_endpoint="GET /api/analytics")
                ]
            ),
            UIPageSchema(
                name="Billing",
                route="/billing",
                title="Stripe Subscription Portal",
                accessible_by=["admin", "sales"],
                components=[
                    UIComponent(id="stripe-checkout-launcher", type="Card", api_endpoint="POST /api/billing/stripe")
                ]
            )
        ],
        auth_schema=[
            AuthRole(name="admin", permissions=["*"]),
            AuthRole(name="sales", permissions=["contacts:read", "contacts:write", "deals:read", "deals:write"]),
            AuthRole(name="viewer", permissions=["contacts:read", "deals:read"])
        ],
        business_logic=BusinessLogic(
            gates=[
                BusinessGate(name="restrict_viewer_writes", description="Prevent viewer roles from submitting form changes", condition="role != 'viewer'", applies_to=["viewer"]),
                BusinessGate(name="sales_only_own_deals", description="Filter deal access to records owned by current sales rep", condition="role == 'admin' or owner_id == current_user.id", applies_to=["sales"])
            ],
            triggers=[
                {"event": "deal_won", "action": "send_slack_notification"},
                {"event": "new_user", "action": "create_stripe_customer"}
            ]
        ),
        assumptions=[
            Assumption(field="pipeline_stages", value="lead, opportunity, won, lost", reason="Configured standard stages for simplicity.")
        ]
    )

    # 4. Validation Report (Perfect, Passed)
    val = ValidationReport(
        passed=True,
        issues=[],
        warnings=[],
        checks_run=10
    )

    # 5. Execution Report (Fully executable)
    exec_report = ExecutionReport(
        executable=True,
        checks=[
            ExecutionCheck(component="db_schema", status="pass", detail="All 3 tables compiled correctly. Primary keys and foreign key constraints successfully resolved."),
            ExecutionCheck(component="api_schema", status="pass", detail="All 7 endpoints route cleanly. Data-scoped access controls and authorization parameters verified."),
            ExecutionCheck(component="ui_schema", status="pass", detail="All 6 views and linked form/chart components map to active entities and backend API routes."),
            ExecutionCheck(component="auth_schema", status="pass", detail="Role definitions ('admin', 'sales', 'viewer') verified. RBAC scoping checks pass static analysis."),
            ExecutionCheck(component="business_logic", status="pass", detail="Business rules and transaction gates compiled into AST with no circular loops detected.")
        ],
        components_verified=5,
        unresolved_references=[]
    )

    # 6. Pipeline Metrics
    metrics = PipelineMetrics(
        total_latency_ms=4820,
        estimated_cost_usd=0.0,
        model_used="AppForge Mock compiler Engine",
        mode=mode,
        repair_attempts=0,
        stages={
            "stage1_intent": StageMetrics(latency_ms=950, status="success"),
            "stage2_design": StageMetrics(latency_ms=1200, status="success"),
            "stage3_schema": StageMetrics(latency_ms=1600, status="success"),
            "stage4_refinement": StageMetrics(latency_ms=800, status="success"),
            "validation": StageMetrics(latency_ms=120, status="success"),
            "runtime_simulation": StageMetrics(latency_ms=150, status="success")
        }
    )

    # 7. Final Response
    return AppForgeResponse(
        run_id=run_id,
        status="success",
        intent=intent,
        architecture=arch,
        app_schema=schema,
        validation_report=val,
        execution_report=exec_report,
        metrics=metrics
    )
