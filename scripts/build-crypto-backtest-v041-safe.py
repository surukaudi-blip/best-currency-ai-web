#!/usr/bin/env python3
"""Run Crypto v0.4.1 diagnostic with exact production rounding parity.

Production Stage 11A rounds completed percent inputs to 4 decimals. Stage 11C v0.1
then rounds component scores and weighted Market Structure scores to 2 decimals.
This wrapper enforces that same sequence for the consumed-window diagnostic.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "scripts" / "build-crypto-backtest-v041.py"
OUTPUT = ROOT / "data" / "crypto-backtest-v041.json"

spec = importlib.util.spec_from_file_location("crypto_backtest_v041", BASE)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def production_pct_return(latest, prior):
    if prior == 0:
        return None
    return round((latest / prior - 1.0) * 100.0, 4)


def production_signed_score(value, span):
    if value is None:
        return None
    return round(module.bt.clamp(50.0 + 50.0 * float(value) / float(span)), 2)


def production_weighted_available(parts):
    rows = [(score, weight) for score, weight in parts if score is not None]
    total = sum(weight for _, weight in rows)
    if total <= 0:
        return None
    return round(sum(float(score) * weight for score, weight in rows) / total, 2)


module.bt.pct_return = production_pct_return
module.bt.signed_score = production_signed_score
module.bt.weighted_available = production_weighted_available

code = module.main()

if OUTPUT.exists():
    artifact = json.loads(OUTPUT.read_text(encoding="utf-8"))
    artifact.setdefault("test_design", {})["production_rounding_parity"] = {
        "percent_inputs_decimals": 4,
        "component_score_decimals": 2,
        "weighted_market_score_decimals": 2,
        "status": "ENFORCED"
    }
    OUTPUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

raise SystemExit(code)
