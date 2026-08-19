#!/usr/bin/env python3
"""Crypto 6-check diagnostic v1.1 with corrected Counter-Thesis semantics.

The underlying historical window remains the already-consumed 365-day diagnostic.
No threshold search, asset-specific tuning, or evidence-history fabrication is added.
Only Counter-Thesis semantics are corrected for parity with production QA:
LOW = no material active challenge, MODERATE = one or more moderate challenges,
HIGH = at least one high-severity challenge.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "scripts" / "build-crypto-backtest-readiness6.py"
OUTPUT = ROOT / "data" / "crypto-backtest-readiness6.json"

spec = importlib.util.spec_from_file_location("crypto_readiness6", BASE)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

_previous = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {}
_original_market_counter_thesis = module.market_counter_thesis


def corrected_market_counter_thesis(canonical, risk, r1):
    result = _original_market_counter_thesis(canonical, risk, r1)
    factors = list(result.get("factors") or [])
    has_high = any(str(x.get("severity") or "").upper() == "HIGH" for x in factors)
    if has_high:
        strength = "HIGH"
    elif factors:
        strength = "MODERATE"
    else:
        strength = "LOW"
    result["strength"] = strength
    result["semantics_version"] = "COUNTER_THESIS_0.2"
    return result


module.market_counter_thesis = corrected_market_counter_thesis
code = module.main()

if OUTPUT.exists():
    artifact = json.loads(OUTPUT.read_text(encoding="utf-8"))
    artifact["version"] = "1.1"
    artifact["status"] = "CRYPTO_6CHECK_COUNTER_THESIS_SEMANTIC_REVISION_DIAGNOSTIC_COMPLETE"
    artifact.setdefault("test_design", {})["counter_thesis_semantics"] = {
        "version": "COUNTER_THESIS_0.2",
        "change_type": "SEMANTIC_QA_CORRECTION_NOT_THRESHOLD_TUNING",
        "LOW": "No material active market-reconstructable counter-thesis factor.",
        "MODERATE": "One or more moderate challenge factors and no high factor.",
        "HIGH": "At least one high-severity challenge factor."
    }
    artifact.setdefault("check_rules", {})["counter_thesis"] = (
        "PASS LOW (no material active challenge); CAUTION MODERATE; FAIL HIGH."
    )

    old_strict = ((_previous.get("primary_gate_analysis") or {}).get("strict_6_of_6") or {})
    old_sensitivity = ((_previous.get("counter_thesis_semantics_sensitivity") or {}).get(
        "counter_thesis_LIMITED_treated_as_PASS_strict_6_of_6"
    ) or {})
    new_strict = ((artifact.get("primary_gate_analysis") or {}).get("strict_6_of_6") or {})

    artifact["counter_thesis_semantic_revision_evaluation"] = {
        "previous_official_semantics": {
            "strict_6_of_6_observations": old_strict.get("observations"),
            "strict_6_of_6_hit_rate_7d_percent": old_strict.get("hit_rate_7d_percent"),
            "strict_6_of_6_avg_directional_return_7d_percent": old_strict.get("avg_directional_return_7d_percent")
        },
        "previous_sensitivity_reference": {
            "observations": old_sensitivity.get("observations"),
            "hit_rate_7d_percent": old_sensitivity.get("hit_rate_7d_percent"),
            "avg_directional_return_7d_percent": old_sensitivity.get("avg_directional_return_7d_percent")
        },
        "revised_semantics_official_diagnostic": {
            "strict_6_of_6_observations": new_strict.get("observations"),
            "strict_6_of_6_hit_rate_7d_percent": new_strict.get("hit_rate_7d_percent"),
            "strict_6_of_6_avg_directional_return_7d_percent": new_strict.get("avg_directional_return_7d_percent")
        },
        "interpretation": (
            "Semantic parity check only. The consumed historical window cannot be used as fresh proof "
            "or for additional threshold tuning; Fresh OOS is still required after freeze."
        )
    }
    artifact.pop("counter_thesis_semantics_sensitivity", None)
    artifact.setdefault("governance", []).append(
        "Counter-Thesis v0.2 is a semantic correction: no material active challenge maps to LOW/PASS; no threshold was searched."
    )
    OUTPUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

raise SystemExit(code)
