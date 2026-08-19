#!/usr/bin/env python3
"""Prospective-only Fresh OOS tracker for frozen Crypto v0.4.1.

Rules:
- Never creates records for baseline or earlier sessions.
- Never imports rows from consumed historical backtests.
- Eligible prediction requires directional canonical v0.1 plus Actionability Primary Gate PASS.
- Primary endpoint is 7D directional continuation; 1D and 3D are secondary.
- Six-check readiness is stored as governance context, not probability/confidence.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = ROOT / "data" / "crypto-model-freeze.json"
DECISION_PATH = ROOT / "data" / "crypto-decision-intelligence.json"
MARKET_PATH = ROOT / "data" / "crypto-market-data.json"
TRACKER_PATH = ROOT / "data" / "crypto-fresh-oos.json"


def load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iso_date(v: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(v))
    except Exception:
        return None


def fnum(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def six_checks(symbol: Dict[str, Any]) -> Dict[str, bool]:
    market = symbol.get("market_structure") or {}
    mtf = symbol.get("multi_timeframe_alignment") or {}
    action = symbol.get("actionability") or {}
    risk = symbol.get("decision_risk") or {}
    counter = symbol.get("counter_thesis") or {}
    regime = ((action.get("dimensions") or {}).get("regime_guardrail") or {})

    direction = str(market.get("state") or "").upper() in {"SUPPORTIVE", "PRESSURED"}
    mtf_pass = (fnum(mtf.get("score")) or -1.0) >= 80.0
    regime_pass = (fnum(regime.get("score")) or -1.0) >= 80.0
    risk_pass = str(risk.get("state") or "").upper() == "LOW"
    counter_pass = str(counter.get("strength") or "").upper() == "LOW"
    action_score = fnum(action.get("score"))
    action_pass = str(action.get("state") or "").upper() == "ACTIONABLE" and action_score is not None and action_score >= 80.0
    return {
        "canonical_direction": direction,
        "mtf_alignment": mtf_pass,
        "regime_guardrail": regime_pass,
        "decision_risk": risk_pass,
        "counter_thesis": counter_pass,
        "actionability_gate": action_pass,
    }


def main() -> int:
    freeze = load(FREEZE_PATH)
    decision = load(DECISION_PATH)
    market = load(MARKET_PATH)
    tracker = load(TRACKER_PATH)

    if freeze.get("status") != "CRYPTO_MODEL_FROZEN":
        raise SystemExit("Crypto freeze artifact missing or invalid.")
    if tracker.get("model_id") != freeze.get("model_id"):
        raise SystemExit("Fresh OOS tracker model_id does not match freeze artifact.")
    if tracker.get("frozen_methodology_sha256") != freeze.get("frozen_methodology_sha256"):
        raise SystemExit("Fresh OOS tracker methodology hash mismatch.")

    baseline = iso_date(freeze.get("baseline_market_session"))
    current_session = iso_date(decision.get("market_session"))
    if baseline is None or current_session is None:
        raise SystemExit("Missing valid baseline/current completed session.")

    market_by_symbol = {x.get("symbol"): x for x in market.get("assets", []) if x.get("symbol")}
    records = list(tracker.get("records") or [])

    # Settle only on the exact prospective horizon session. We do not substitute
    # later closes for a missed horizon and we never fetch historical rows here.
    for rec in records:
        pred_date = iso_date(rec.get("prediction_session"))
        symbol = rec.get("symbol")
        row = market_by_symbol.get(symbol) or {}
        current_close = fnum((row.get("completed_daily_context") or {}).get("completed_close_usd"))
        baseline_close = fnum(rec.get("baseline_close_usd"))
        if pred_date is None or current_close is None or baseline_close is None:
            continue
        delta = (current_session - pred_date).days
        expected_up = rec.get("canonical_direction") == "SUPPORTIVE"
        for h in (1, 3, 7):
            key = f"outcome_{h}d"
            if rec.get(key) is None and delta == h:
                actual_up = current_close > baseline_close
                rec[key] = {
                    "settled_session": current_session.isoformat(),
                    "settled_close_usd": current_close,
                    "direction_hit": bool(actual_up == expected_up),
                    "directional_return_percent": round(((current_close / baseline_close) - 1.0) * 100.0 * (1.0 if expected_up else -1.0), 4),
                }

    existing = {(r.get("symbol"), r.get("prediction_session")) for r in records}
    if current_session > baseline:
        for symbol in decision.get("symbols", []):
            sym = symbol.get("symbol")
            direction = str((symbol.get("market_structure") or {}).get("state") or "").upper()
            action = symbol.get("actionability") or {}
            action_score = fnum(action.get("score"))
            primary_pass = direction in {"SUPPORTIVE", "PRESSURED"} and str(action.get("state") or "").upper() == "ACTIONABLE" and action_score is not None and action_score >= 80.0
            if not primary_pass or (sym, current_session.isoformat()) in existing:
                continue

            row = market_by_symbol.get(sym) or {}
            close = fnum((row.get("completed_daily_context") or {}).get("completed_close_usd"))
            if close is None:
                continue

            checks = six_checks(symbol)
            records.append({
                "model_id": freeze.get("model_id"),
                "prediction_session": current_session.isoformat(),
                "symbol": sym,
                "baseline_close_usd": close,
                "canonical_direction": direction,
                "canonical_score": (symbol.get("market_structure") or {}).get("score"),
                "mtf_score": (symbol.get("multi_timeframe_alignment") or {}).get("score"),
                "regime_score": (((action.get("dimensions") or {}).get("regime_guardrail") or {}).get("score")),
                "decision_risk_score": (symbol.get("decision_risk") or {}).get("score"),
                "decision_risk_state": (symbol.get("decision_risk") or {}).get("state"),
                "counter_thesis_strength": (symbol.get("counter_thesis") or {}).get("strength"),
                "actionability_score": action_score,
                "actionability_state": action.get("state"),
                "six_checks": checks,
                "checks_passed": sum(1 for v in checks.values() if v),
                "strict_6_of_6": all(checks.values()),
                "outcome_1d": None,
                "outcome_3d": None,
                "outcome_7d": None,
                "governance": "Prospective frozen-model observation; not a trade signal or profit probability."
            })

    settled_7d = [r for r in records if r.get("outcome_7d") is not None]
    hits_7d = sum(1 for r in settled_7d if (r.get("outcome_7d") or {}).get("direction_hit") is True)
    tracker["records"] = records
    tracker["summary"] = {
        "predictions_total": len(records),
        "primary_7d_settled": len(settled_7d),
        "primary_7d_hits": hits_7d,
        "primary_7d_hit_rate_percent": round(hits_7d / len(settled_7d) * 100.0, 2) if settled_7d else None,
        "strict_6_of_6_predictions": sum(1 for r in records if r.get("strict_6_of_6") is True),
        "status_note": "Prospective-only tracker. Historical diagnostic rows are never imported."
    }
    tracker["latest_completed_session_seen"] = current_session.isoformat()
    TRACKER_PATH.write_text(json.dumps(tracker, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Crypto Fresh OOS: session={current_session}; predictions={len(records)}; settled_7d={len(settled_7d)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
