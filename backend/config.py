"""
AppForge AI — Central Configuration
Manages LLM provider selection, model mapping, and temperature settings per stage.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM Provider ──────────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ── Model Registry ────────────────────────────────────────────────────────────
MODELS = {
    "fast":     os.getenv("FAST_MODEL",     "gemini-1.5-flash"),
    "balanced": os.getenv("BALANCED_MODEL", "gemini-1.5-pro"),
    "premium":  os.getenv("PREMIUM_MODEL",  "gemini-1.5-pro"),
}

DEFAULT_MODE = os.getenv("DEFAULT_MODE", "balanced")

# ── Per-Stage Temperature Settings ────────────────────────────────────────────
# Stage 1 (intent) gets slight creativity; later stages are deterministic
STAGE_TEMPERATURES = {
    "stage1_intent":     0.3,
    "stage2_design":     0.1,
    "stage3_schema":     0.0,
    "stage4_refinement": 0.0,
    "repair":            0.0,
}

# ── Cost Estimates (per 1M tokens, USD) ───────────────────────────────────────
COST_PER_1M = {
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro":   {"input": 3.50,  "output": 10.50},
    "gpt-4o":           {"input": 5.00,  "output": 15.00},
}

# ── Retry / Repair Config ─────────────────────────────────────────────────────
MAX_REPAIR_ATTEMPTS = 3
MAX_STAGE_RETRIES   = 2

# ── Server ────────────────────────────────────────────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
