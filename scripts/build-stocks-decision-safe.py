#!/usr/bin/env python3
"""Harden Stage 10C with a minimum comparable-fundamental coverage gate."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = ROOT / "scripts" / "build-stocks-decision.py"
OUTPUT_PATH = ROOT / "data" / "stocks-decision-intelligence.json"

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
if OUTPUT_PATH.exists():
    artifact = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    methodology = artifact.setdefault("methodology", {}).setdefault("fundamental_evidence", {})
    methodology["minimum_comparable_coverage_percent"] = 40
    methodology["coverage_guardrail"] = "Below 40% comparable coverage, Fundamental Evidence state is INSUFFICIENT and cross-layer alignment fails closed."
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

raise SystemExit(code)
