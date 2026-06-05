"""
AppForge AI — FastAPI Server
Serves both the API and the static frontend.
"""
from __future__ import annotations
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import backend.db as db

app = FastAPI(
    title="AppForge AI",
    description="Natural Language → Application Schema Compiler",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


# ── Static files + index ──────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "system": "AppForge AI"}


# ── Main generation endpoint (SSE streaming) ──────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str
    mode: str = "balanced"   # fast | balanced | premium


@app.post("/api/generate/stream")
async def generate_stream(req: GenerateRequest):
    """
    Streams pipeline progress events as Server-Sent Events (SSE).
    Each event is: data: {json}\n\n
    """
    from backend.pipeline.orchestrator import run_pipeline

    async def event_generator():
        async for event in run_pipeline(req.prompt, mode=req.mode):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: {\"event\": \"done\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Synchronous generate (non-streaming) for eval + API clients ───────────────

@app.post("/api/generate")
async def generate(req: GenerateRequest):
    """Non-streaming endpoint. Returns complete result when done."""
    from backend.pipeline.orchestrator import run_pipeline
    final_event = {}
    async for event in run_pipeline(req.prompt, mode=req.mode):
        if event.get("event") == "complete":
            final_event = event.get("data", {})
    return final_event


# ── History + Metrics ─────────────────────────────────────────────────────────

@app.get("/api/runs")
async def get_runs(limit: int = 20):
    db.init_db()
    return db.get_recent_runs(limit=limit)


@app.get("/api/metrics")
async def get_metrics():
    db.init_db()
    return {
        "aggregate": db.get_aggregate_metrics(),
        "eval_summary": db.get_eval_summary(),
    }


# ── Evaluation endpoint ───────────────────────────────────────────────────────

@app.post("/api/eval/run")
async def run_eval(max_cases: int = 5, mode: str = "fast"):
    """Triggers the evaluation suite (runs in-process — use for demo only)."""
    from backend.evaluation.metrics import run_evaluation

    # Synchronous pipeline wrapper for evaluation
    import asyncio

    def sync_pipeline(prompt: str, mode: str = "fast") -> dict:
        async def _collect():
            final = {}
            async for ev in __import__(
                "backend.pipeline.orchestrator", fromlist=["run_pipeline"]
            ).run_pipeline(prompt, mode=mode):
                if ev.get("event") == "complete":
                    final = ev.get("data", {})
            return final
        return asyncio.run(_collect())

    summary = run_evaluation(sync_pipeline, mode=mode, max_cases=max_cases)
    return summary


# ── Cost estimation ───────────────────────────────────────────────────────────

@app.get("/api/cost-estimate")
async def cost_estimate(mode: str = "balanced", prompt_length: int = 200):
    """Returns estimated cost range for a given mode."""
    estimates = {
        "fast":     {"latency_s": "2-5",   "cost_usd": "0.0005-0.002",  "model": "gemini-2.5-flash"},
        "balanced": {"latency_s": "3-7",  "cost_usd": "0.0005-0.002",   "model": "gemini-2.5-flash"},
        "premium":  {"latency_s": "4-10", "cost_usd": "0.0005-0.002",    "model": "gemini-2.5-flash"},
    }
    return estimates.get(mode, estimates["balanced"])


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    db.init_db()
    print("[OK] AppForge AI started - DB initialized")


if __name__ == "__main__":
    import uvicorn
    from backend.config import HOST, PORT
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
