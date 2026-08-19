#!/usr/bin/env python3
"""Stage 11C.5 semantic correction for Crypto v0.4.1 Counter-Thesis.

This wrapper does not alter Canonical v0.1, D/W/M, MTF, Regime, Decision Risk,
Actionability thresholds, or asset-specific rules. It corrects only the meaning
of Counter-Thesis strength so the state reflects the strongest active challenge:

- LOW: no material active counter-thesis factor was detected.
- MODERATE: one or more MODERATE challenge factors are active and no HIGH factor exists.
- HIGH: at least one HIGH challenge factor is active.

This is a semantic QA correction, not historical threshold optimization.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "scripts" / "build-crypto-decision-v041.py"
OUTPUT = ROOT / "data" / "crypto-decision-intelligence.json"

spec = importlib.util.spec_from_file_location("crypto_decision_v041", BASE)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

_original_counter_thesis = module.base.counter_thesis


def corrected_counter_thesis(symbol: str, asset: Dict[str, Any], market_state: str, risk: Dict[str, Any], evidence_readiness: Dict[str, Any]) -> Dict[str, Any]:
    result = _original_counter_thesis(symbol, asset, market_state, risk, evidence_readiness)
    factors = list(result.get("factors") or [])
    has_high = any(str(x.get("severity") or "").upper() == "HIGH" for x in factors)

    if has_high:
        strength = "HIGH"
        status = "ACTIVE"
    elif factors:
        strength = "MODERATE"
        status = "ACTIVE"
    else:
        strength = "LOW"
        status = "CLEAR"

    result["strength"] = strength
    result["status"] = status
    result["semantics_version"] = "COUNTER_THESIS_0.2"
    result["semantic_definition"] = (
        "Counter-Thesis measures active challenge strength: LOW means no material active "
        "challenge factor; MODERATE means one or more moderate factors; HIGH means at least "
        "one high-severity factor."
    )
    return result


module.base.counter_thesis = corrected_counter_thesis
code = module.main()

if OUTPUT.exists():
    artifact = json.loads(OUTPUT.read_text(encoding="utf-8"))
    artifact["counter_thesis_semantics"] = {
        "version": "COUNTER_THESIS_0.2",
        "change_type": "SEMANTIC_QA_CORRECTION_NOT_THRESHOLD_TUNING",
        "states": {
            "LOW": "No material active counter-thesis factor detected; dashboard PASS.",
            "MODERATE": "One or more moderate challenge factors are active; dashboard CAUTION.",
            "HIGH": "At least one high-severity challenge factor is active; dashboard FAIL."
        },
        "readiness_mapping": "LOW=PASS; MODERATE=CAUTION; HIGH=FAIL",
        "actionability_primary_gate_changed": False,
        "direction_mtf_regime_risk_changed": False,
        "trade_execution": "OFF"
    }
    OUTPUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

raise SystemExit(code)
