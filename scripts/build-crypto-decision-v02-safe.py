#!/usr/bin/env python3
"""Hardening wrapper for Stage 11C v0.2 refinement.

Checks that the consumed v0.1 diagnostic backtest belongs to the exact current
v0.1 methodology before refinement, then ensures Counter-Thesis challenges the
underlying raw directional state even when a v0.2 guardrail suppresses the
published effective Market View to MIXED.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "scripts" / "build-crypto-decision-v02.py"
DECISION_PATH = ROOT / "data" / "crypto-decision-intelligence.json"
BACKTEST_PATH = ROOT / "data" / "crypto-backtest.json"

spec = importlib.util.spec_from_file_location("crypto_decision_v02", MODEL_PATH)
model = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(model)


def canonical_hash(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


current = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
backtest = json.loads(BACKTEST_PATH.read_text(encoding="utf-8"))
if current.get("version") != "0.1":
    raise SystemExit("v0.2 refinement lineage check expects the current production artifact to still be v0.1 before first activation.")
current_methodology_hash = canonical_hash(current.get("methodology") or {})
source_methodology_hash = (backtest.get("model_snapshot") or {}).get("methodology_sha256")
if not source_methodology_hash or source_methodology_hash != current_methodology_hash:
    raise SystemExit(
        f"Refinement lineage mismatch: v0.1 artifact={current_methodology_hash}, backtest source={source_methodology_hash}"
    )


def counter_thesis_hardened(symbol, asset, m, risk, evidence_readiness):
    result = model.base.counter_thesis(symbol, asset, m.get("raw_state") or m.get("state"), risk, evidence_readiness)
    factors = list(result.get("factors") or [])
    for guard in m.get("guardrails", []):
        factors.append({
            "severity": guard.get("severity", "MODERATE"),
            "text": guard.get("message", "Market-structure guardrail is active."),
        })
    high = sum(1 for x in factors if x.get("severity") == "HIGH")
    strength = "HIGH" if high else ("MODERATE" if len(factors) >= 2 else ("LOW" if factors else "LIMITED"))
    return {"status": "ACTIVE" if factors else "LIMITED", "strength": strength, "factors": factors}


model.counter_thesis_v02 = counter_thesis_hardened
raise SystemExit(model.main())
