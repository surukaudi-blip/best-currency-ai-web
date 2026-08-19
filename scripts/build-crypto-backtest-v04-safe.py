#!/usr/bin/env python3
"""Run v0.4 Actionability diagnostic with production rounding parity."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "scripts" / "build-crypto-backtest-v04.py"
OUTPUT = ROOT / "data" / "crypto-backtest-v04.json"

spec = importlib.util.spec_from_file_location("crypto_backtest_v04", BASE)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def production_pct_return(latest, prior):
    if prior == 0:
        return None
    return round((latest / prior - 1.0) * 100.0, 4)


def production_weighted_available(parts):
    rows = [(score, weight) for score, weight in parts if score is not None]
    total = sum(weight for _, weight in rows)
    if total <= 0:
        return None
    return round(sum(float(score) * weight for score, weight in rows) / total, 2)


module.bt.pct_return = production_pct_return
module.bt.weighted_available = production_weighted_available

code = module.main()
if OUTPUT.exists():
    artifact = json.loads(OUTPUT.read_text(encoding="utf-8"))
    artifact.setdefault("test_design", {})["production_rounding_parity"] = {
        "percent_inputs_decimals": 4,
        "component_score_decimals": 2,
        "weighted_score_decimals": 2,
        "status": "ENFORCED",
    }
    OUTPUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

raise SystemExit(code)
