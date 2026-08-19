#!/usr/bin/env python3
"""Harden Stage 10C and enforce the Stage 10D frozen-model manifest."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = ROOT / "scripts" / "build-stocks-decision.py"
OUTPUT_PATH = ROOT / "data" / "stocks-decision-intelligence.json"
FREEZE_PATH = ROOT / "data" / "stocks-model-freeze.json"

spec = importlib.util.spec_from_file_location("stocks_decision_base", BASE_SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

_original_fundamental = module.fundamental_evidence
_original_alignment = module.alignment_state


def hardened_fundamental(sec):
    result = _original_fundamental(sec)
    if float(result.get("comparable_coverage_percent") or 0.0) < 40.0:
        result["state"] = "INSUFFICIENT"
    return result


def hardened_alignment(market_state, fundamental_state):
    if fundamental_state == "INSUFFICIENT":
        return "INCOMPLETE", 20.0
    return _original_alignment(market_state, fundamental_state)


module.fundamental_evidence = hardened_fundamental
module.alignment_state = hardened_alignment

code = module.main()
freeze_error = 0
if OUTPUT_PATH.exists():
    artifact = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    methodology = artifact.setdefault("methodology", {}).setdefault("fundamental_evidence", {})
    methodology["minimum_comparable_coverage_percent"] = 40
    methodology["coverage_guardrail"] = "Below 40% comparable coverage, Fundamental Evidence state is INSUFFICIENT and cross-layer alignment fails closed."

    if FREEZE_PATH.exists():
        freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
        canonical = json.dumps(artifact.get("methodology", {}), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        current_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        expected_hash = freeze.get("methodology_sha256")
        match = bool(expected_hash) and current_hash == expected_hash
        artifact["freeze_validation"] = {
            "status": "MATCH" if match else "HASH_MISMATCH",
            "model_id": freeze.get("model_id"),
            "expected_methodology_sha256": expected_hash,
            "current_methodology_sha256": current_hash,
            "baseline_market_session": freeze.get("baseline_market_session"),
        }
        if match:
            artifact["model_status"] = "FROZEN_PROSPECTIVE"
            artifact["frozen"] = True
            artifact["model_id"] = freeze.get("model_id")
            artifact["model_hash"] = current_hash
        else:
            artifact["model_status"] = "FREEZE_HASH_MISMATCH"
            artifact["frozen"] = False
            freeze_error = 3

    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

raise SystemExit(freeze_error or code)
