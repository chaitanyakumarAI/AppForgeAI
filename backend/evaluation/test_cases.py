"""
AppForge AI — Evaluation Test Cases
20 carefully crafted test prompts for the benchmark:
- 10 real product prompts (realistic, production-grade)
- 10 edge cases (vague, conflicting, incomplete, circular)
"""

REAL_PRODUCT_PROMPTS = [
    {
        "id": "real_01",
        "category": "CRM",
        "prompt": "Build a CRM with login, contacts management, deal pipeline, dashboard, role-based access (admin/sales/viewer), and premium plan with Stripe payments. Admins can see full analytics. Sales reps can only see their own deals.",
    },
    {
        "id": "real_02",
        "category": "LMS",
        "prompt": "Create a Learning Management System where instructors can create courses with video lessons, quizzes, and assignments. Students can enroll, track progress, and get certificates on completion. Admins manage users and revenue.",
    },
    {
        "id": "real_03",
        "category": "HR Tool",
        "prompt": "Build an HR management system with employee directory, leave management, payroll tracking, performance reviews, and org chart. HR managers can approve leaves and manage payroll. Employees can view their own profile.",
    },
    {
        "id": "real_04",
        "category": "E-commerce",
        "prompt": "Build a multi-vendor marketplace where sellers can list products, manage inventory, and track orders. Buyers can browse, add to cart, checkout with Stripe, and track deliveries. Admin has full oversight and takes a 10% commission.",
    },
    {
        "id": "real_05",
        "category": "Project Management",
        "prompt": "Create a project management tool like Jira with projects, sprints, tickets (with priority/status), kanban board, and time tracking. Team leads can assign tickets. Developers update status. PMs see all analytics.",
    },
    {
        "id": "real_06",
        "category": "Invoice Manager",
        "prompt": "Build an invoicing SaaS where freelancers can create clients, generate invoices, send them by email, track payment status (paid/unpaid/overdue), and see monthly revenue reports. Support recurring invoices.",
    },
    {
        "id": "real_07",
        "category": "Healthcare",
        "prompt": "Build a telemedicine platform where patients can book appointments with doctors, have video consultations, view prescriptions, and medical history. Doctors manage their schedule and write prescriptions. Admin manages billing.",
    },
    {
        "id": "real_08",
        "category": "Event Management",
        "prompt": "Create an event management platform where organizers can create events, sell tickets (paid and free), manage attendees, send bulk emails, and see analytics. Attendees can register, get QR tickets, and check in.",
    },
    {
        "id": "real_09",
        "category": "Inventory",
        "prompt": "Build a warehouse inventory management system with products, categories, suppliers, purchase orders, sales orders, stock alerts when quantity drops below threshold, and reporting. Multi-warehouse support.",
    },
    {
        "id": "real_10",
        "category": "SaaS Analytics",
        "prompt": "Create a SaaS analytics dashboard where companies can connect their data sources, build custom dashboards with charts and KPIs, set up automated reports, and share dashboards with team members with view/edit permissions.",
    },
]

EDGE_CASE_PROMPTS = [
    {
        "id": "edge_01",
        "category": "vague",
        "prompt": "build an app",
        "expected_behavior": "Should list many ambiguities, make reasonable assumptions, build a simple todo/productivity app",
    },
    {
        "id": "edge_02",
        "category": "conflicting",
        "prompt": "Build a social network that is completely private and public at the same time. All data should be both encrypted and publicly searchable.",
        "expected_behavior": "Should detect conflict, choose privacy-first approach, document the conflict in ambiguities",
    },
    {
        "id": "edge_03",
        "category": "incomplete",
        "prompt": "a dashboard",
        "expected_behavior": "Should build a generic analytics dashboard with common KPI components",
    },
    {
        "id": "edge_04",
        "category": "circular_roles",
        "prompt": "Build a system where admins are managed by super-admins who are managed by admins. Everyone can see everything except what they can't see.",
        "expected_behavior": "Should break circular dependency, create linear role hierarchy, flag the circular reference",
    },
    {
        "id": "edge_05",
        "category": "no_entities",
        "prompt": "I want users to be able to do things and admins to manage stuff and there should be some kind of reporting.",
        "expected_behavior": "Should infer a basic internal tool with user/admin roles and reporting module",
    },
    {
        "id": "edge_06",
        "category": "contradictory_scale",
        "prompt": "Build a simple app for 1 billion concurrent users. It should be super simple with just one page.",
        "expected_behavior": "Should note scale contradiction, build the simple 1-page app, flag that 1B scale needs infrastructure beyond schema",
    },
    {
        "id": "edge_07",
        "category": "technical_jargon_overload",
        "prompt": "Build a microservices-based event-driven CQRS architecture with eventual consistency, saga patterns, and distributed tracing using OpenTelemetry for a todo app.",
        "expected_behavior": "Should extract 'todo app' as the core, note architectural preferences in assumptions, build a clean todo schema",
    },
    {
        "id": "edge_08",
        "category": "impossible_requirements",
        "prompt": "Build an app that generates revenue automatically with zero users, no database, infinite storage, and real-time sync with no latency.",
        "expected_behavior": "Should flag impossible requirements, make reasonable assumptions, build closest feasible version",
    },
    {
        "id": "edge_09",
        "category": "emoji_only",
        "prompt": "🏋️📊💪📱🔔💰",
        "expected_behavior": "Should interpret as fitness/workout tracker with analytics, notifications, and payments",
    },
    {
        "id": "edge_10",
        "category": "feature_explosion",
        "prompt": "Build an app with login, signup, dashboard, CRM, LMS, e-commerce, payments, analytics, AI chatbot, video calls, calendar, email marketing, SMS notifications, social feed, file sharing, API marketplace, blockchain rewards, AR product previews, and voice commands.",
        "expected_behavior": "Should handle feature explosion gracefully, group into coherent modules, flag scope as 'complex', build core schema without hallucinating missing connections",
    },
]

ALL_TEST_CASES = REAL_PRODUCT_PROMPTS + EDGE_CASE_PROMPTS
