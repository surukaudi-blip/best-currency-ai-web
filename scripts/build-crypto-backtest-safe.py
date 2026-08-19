#!/usr/bin/env python3
"""Run Stage 11C.4 with exact Stage 11C market-score rounding parity.

Production Stage 11A stores percent-return inputs at 4 decimals. Stage 11C then
rounds component scores and weighted Market View scores at 2 decimals. This
wrapper patches the diagnostic engine to follow the same sequence before the
historical evaluation is executed.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "scripts" / "build-crypto-backtest.py"
OUTPUT = ROOT / "data" / "crypto-backtest.json"

spec = importlib.util.spec_from_file_location("crypto_backtest_base", BASE)
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
    return round(module.clamp(50.0 + 50.0 * float(value) / float(span)), 2)


def production_weighted_available(parts):
    rows = [(score, weight) for score, weight in parts if score is not None]
    total = sum(weight for _, weight in rows)
    if total <= 0:
        return None
    return round(sum(float(score) * weight for score, weight in rows) / total, 2)


module.pct_return = production_pct_return
module.signed_score = production_signed_score
module.weighted_available = production_weighted_available

code = module.main()

if OUTPUT.exists():
    artifact = json.loads(OUTPUT.read_text(encoding="utf-8"))
    artifact.setdefault("test_design", {})["production_rounding_parity"] = {
        "percent_inputs_decimals": 4,
        "component_score_decimals": 2,
        "weighted_market_score_decimals": 2,
        "status": "ENFORCED",
    }
    artifact.setdefault("limitations", {}).update({
        "current_universe_selection_bias_possible": True,
        "cross_asset_observations_not_independent": True,
        "overlapping_forward_windows_create_serial_dependence": True,
        "historical_holdout_is_not_fresh_oos": True,
        "historical_non_market_evidence_not_reconstructed": True,
    })
    OUTPUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

raise SystemExit(code)
