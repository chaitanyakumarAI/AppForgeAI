# AppForge AI — NL to App Compiler

> **Convert natural language → validated, executable application schemas via a 4-stage AI pipeline.**

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 3. Run
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Open browser
# http://localhost:8000
```

## Architecture

```
Natural Language
    ↓
Stage 1: Intent Extractor   (IntentSpec JSON)
    ↓
Stage 2: System Designer    (ArchitectureSpec JSON)
    ↓
Stage 3: Schema Generator   (DB + API + UI + Auth + Business Logic)
    ↓
Stage 4: Refinement Engine  (cross-layer consistency linker)
    ↓
Validator (10 checks) ←→ Repair Engine (targeted layer re-gen)
    ↓
Runtime Simulator           (execution proof)
    ↓
Final Output (validated JSON schema)
```

## Pipeline Stages

| Stage | Input | Output | Temp |
|-------|-------|--------|------|
| Intent Extractor | Raw prompt | IntentSpec | 0.3 |
| System Designer | IntentSpec | ArchitectureSpec | 0.1 |
| Schema Generator | ArchitectureSpec | CompleteSchema | 0.0 |
| Refinement Engine | CompleteSchema | CompleteSchema (fixed) | 0.0 |

## Validation Checks (10 total)

1. API roles must exist in auth_schema
2. UI page roles must exist in auth_schema
3. API db_table references must exist in db_schema
4. API response_fields must match DB columns
5. UI components → API endpoints consistency
6. UI components → DB entity consistency
7. Foreign key resolution (table + column)
8. Business logic gate role references
9. Every auth role has ≥1 permission
10. Every DB table has a primary key

## Repair Engine

On validation failure → **targeted layer repair** (not full retry):
1. Identifies which layer(s) have errors
2. Builds focused repair prompt with just that layer + issues
3. Re-generates only the broken layer
4. Repeats up to 3 times

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/generate/stream` | SSE streaming generation |
| POST | `/api/generate` | Synchronous generation |
| GET | `/api/runs` | Run history |
| GET | `/api/metrics` | Aggregate metrics |
| POST | `/api/eval/run` | Run evaluation suite |
| GET | `/api/cost-estimate` | Cost estimate by mode |

## Cost vs Quality

| Mode | Model | Latency | Cost/Run |
|------|-------|---------|----------|
| Fast | gemini-1.5-flash | 2-5s | ~$0.001 |
| Balanced | gemini-1.5-pro | 5-12s | ~$0.01 |
| Premium | gemini-1.5-pro | 10-25s | ~$0.05 |

## Evaluation Framework

20 test cases: 10 real product prompts + 10 edge cases (vague, conflicting, impossible, emoji-only, etc.)

```bash
# Run evaluation (via API)
curl -X POST "http://localhost:8000/api/eval/run?max_cases=10&mode=fast"
```

Metrics tracked: success_rate, avg_latency_ms, avg_retries, failure_types, completeness_score
