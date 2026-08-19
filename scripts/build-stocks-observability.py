#!/usr/bin/env python3
"""Stage 10D: frozen Stocks observability and prospective validation.

This builder is intentionally prospective. It never backfills historical decisions,
never changes Stage 10C weights, and never generates BUY/SELL instructions.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = ROOT / "data" / "stocks-decision-intelligence.json"
MARKET_PATH = ROOT / "data" / "stocks-market-data.json"
FREEZE_PATH = ROOT / "data" / "stocks-model-freeze.json"
HISTORY_PATH = ROOT / "data" / "stocks-decision-history.json"
WATCH_PATH = ROOT / "data" / "stocks-decision-watch.json"
OOS_PATH = ROOT / "data" / "stocks-oos-tracker.json"


def load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fnum(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def snapshot_for(symbol: Dict[str, Any], close: Optional[float], freeze: Dict[str, Any], captured_at: str) -> Dict[str, Any]:
    market = symbol.get("market_structure") or {}
    fund = symbol.get("fundamental_evidence") or {}
    readiness = symbol.get("decision_readiness") or {}
    risk = symbol.get("decision_risk") or {}
    counter = symbol.get("counter_thesis") or {}
    reasoner = symbol.get("ai_decision_reasoner") or {}
    session = symbol.get("market_session")
    baseline = freeze.get("baseline_market_session")
    phase = "PROSPECTIVE" if session and baseline and session > baseline else "FREEZE_BASELINE"
    payload = {
        "ticker": symbol.get("ticker"),
        "name": symbol.get("name"),
        "exchange": symbol.get("exchange"),
        "market_session": session,
        "captured_at": captured_at,
        "phase": phase,
        "model_id": freeze.get("model_id"),
        "model_hash": freeze.get("methodology_sha256"),
        "close": close,
        "market_view": market.get("state"),
        "market_score": market.get("score"),
        "fundamental_view": fund.get("state"),
        "fundamental_score": fund.get("score"),
        "fundamental_coverage_percent": fund.get("comparable_coverage_percent"),
        "alignment": symbol.get("cross_layer_alignment"),
        "readiness_score": readiness.get("score"),
        "readiness_state": readiness.get("state"),
        "risk_score": risk.get("score"),
        "risk_state": risk.get("state"),
        "counter_thesis_strength": counter.get("strength"),
        "reasoner_status": reasoner.get("status"),
        "reasoner_decision": reasoner.get("decision"),
        "buy_sell": "NOT_GENERATED",
        "trade_execution": "OFF",
    }
    payload["snapshot_sha256"] = canonical_hash(payload)
    payload["id"] = f"STK-{session}-{symbol.get('ticker')}"
    return payload


def previous_snapshot(entries: List[Dict[str, Any]], ticker: str, session: str) -> Optional[Dict[str, Any]]:
    prior = [e for e in entries if e.get("ticker") == ticker and e.get("market_session") and e.get("market_session") < session]
    return sorted(prior, key=lambda x: x.get("market_session"))[-1] if prior else None


def add_alert(alerts: List[Dict[str, Any]], ticker: str, code: str, severity: str, message: str, current: Any = None, previous: Any = None) -> None:
    alerts.append({
        "ticker": ticker,
        "code": code,
        "severity": severity,
        "message": message,
        "current": current,
        "previous": previous,
    })


def build_alerts(current: Dict[str, Any], previous: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    ticker = current.get("ticker") or "—"
    risk_state = current.get("risk_state")
    readiness_state = current.get("readiness_state")
    alignment = current.get("alignment")
    counter = current.get("counter_thesis_strength")
    reasoner_decision = current.get("reasoner_decision")

    if risk_state == "HIGH":
        add_alert(alerts, ticker, "RISK_HIGH", "HIGH", "Decision Risk is HIGH; review priority is elevated.", current.get("risk_score"))
    if readiness_state == "LOW_READINESS":
        add_alert(alerts, ticker, "READINESS_LOW", "HIGH", "Decision Readiness is LOW; the current view should be deprioritized.", current.get("readiness_score"))
    if alignment == "DIVERGENT":
        add_alert(alerts, ticker, "EVIDENCE_DIVERGENT", "HIGH", "Market and SEC evidence are directionally divergent.", alignment)
    if counter == "HIGH":
        add_alert(alerts, ticker, "COUNTER_THESIS_HIGH", "HIGH", "Counter-Thesis strength is HIGH.", counter)
    if reasoner_decision == "DEPRIORITIZE" and not any(a["code"] == "READINESS_LOW" for a in alerts):
        add_alert(alerts, ticker, "REASONER_DEPRIORITIZE", "MODERATE", "AI Decision Reasoner currently deprioritizes this symbol.", reasoner_decision)

    if previous:
        pairs = [
            ("MARKET_VIEW_CHANGED", "MODERATE", "market_view", "Market View changed"),
            ("FUNDAMENTAL_VIEW_CHANGED", "MODERATE", "fundamental_view", "Fundamental Evidence state changed"),
            ("ALIGNMENT_CHANGED", "MODERATE", "alignment", "Cross-layer alignment changed"),
            ("READINESS_STATE_CHANGED", "MODERATE", "readiness_state", "Decision Readiness state changed"),
            ("RISK_STATE_CHANGED", "HIGH" if risk_state == "HIGH" else "MODERATE", "risk_state", "Decision Risk state changed"),
            ("REASONER_STATUS_CHANGED", "MODERATE", "reasoner_status", "AI Reasoner status changed"),
            ("REASONER_DECISION_CHANGED", "HIGH" if reasoner_decision == "DEPRIORITIZE" else "MODERATE", "reasoner_decision", "AI review priority changed"),
        ]
        for code, severity, key, label in pairs:
            if current.get(key) != previous.get(key):
                add_alert(alerts, ticker, code, severity, f"{label}: {previous.get(key)} → {current.get(key)}.", current.get(key), previous.get(key))

        for code, key, label in [
            ("READINESS_MOVE_15", "readiness_score", "Decision Readiness"),
            ("RISK_MOVE_15", "risk_score", "Decision Risk"),
            ("MARKET_SCORE_MOVE_15", "market_score", "Market Structure score"),
        ]:
            a, b = fnum(current.get(key)), fnum(previous.get(key))
            if a is not None and b is not None and abs(a - b) >= 15.0:
                severity = "HIGH" if code == "RISK_MOVE_15" and a > b else "MODERATE"
                add_alert(alerts, ticker, code, severity, f"{label} moved materially by {a-b:+.1f} points.", a, b)
    return alerts


def settle_oos(entries: List[Dict[str, Any]], current_by_ticker: Dict[str, Dict[str, Any]], market_by_ticker: Dict[str, Dict[str, Any]], settled_at: str) -> None:
    for entry in entries:
        if entry.get("outcome", {}).get("status") != "PENDING_NEXT_MARKET_OBSERVATION":
            continue
        ticker = entry.get("ticker")
        current = current_by_ticker.get(ticker)
        market = market_by_ticker.get(ticker)
        if not current or not market:
            continue
        current_session = current.get("market_session")
        capture_session = entry.get("capture_market_session")
        if not current_session or not capture_session or current_session <= capture_session:
            continue
        current_close = fnum((market.get("latest_bar") or {}).get("close"))
        capture_close = fnum(entry.get("capture_close"))
        if current_close is None or capture_close in (None, 0):
            continue
        realized = round((current_close / capture_close - 1.0) * 100.0, 4)
        view = entry.get("prediction", {}).get("market_view")
        if realized == 0:
            hit = False
            direction = "FLAT"
        else:
            direction = "UP" if realized > 0 else "DOWN"
            hit = (view == "SUPPORTIVE" and realized > 0) or (view == "PRESSURED" and realized < 0)
        entry["outcome"] = {
            "status": "SETTLED",
            "settled_at": settled_at,
            "settlement_market_session": current_session,
            "settlement_close": current_close,
            "realized_return_percent": realized,
            "realized_direction": direction,
            "hit": bool(hit),
            "settlement_basis": "NEXT_COMPLETE_MARKET_OBSERVATION_CAPTURED_BY_PIPELINE",
        }


def capture_oos(entries: List[Dict[str, Any]], snapshot: Dict[str, Any], freeze: Dict[str, Any]) -> None:
    session = snapshot.get("market_session")
    ticker = snapshot.get("ticker")
    baseline = freeze.get("baseline_market_session")
    if not session or not baseline or session <= baseline:
        return
    if snapshot.get("market_view") not in {"SUPPORTIVE", "PRESSURED"}:
        return
    if any(e.get("ticker") == ticker and e.get("capture_market_session") == session for e in entries):
        return
    prediction = {
        "market_view": snapshot.get("market_view"),
        "market_score": snapshot.get("market_score"),
        "fundamental_view": snapshot.get("fundamental_view"),
        "fundamental_score": snapshot.get("fundamental_score"),
        "alignment": snapshot.get("alignment"),
        "decision_readiness_score": snapshot.get("readiness_score"),
        "decision_readiness_state": snapshot.get("readiness_state"),
        "decision_risk_score": snapshot.get("risk_score"),
        "decision_risk_state": snapshot.get("risk_state"),
        "reasoner_status": snapshot.get("reasoner_status"),
        "reasoner_decision": snapshot.get("reasoner_decision"),
    }
    immutable = {
        "ticker": ticker,
        "capture_market_session": session,
        "capture_close": snapshot.get("close"),
        "model_id": freeze.get("model_id"),
        "model_hash": freeze.get("methodology_sha256"),
        "prediction": prediction,
    }
    entry = dict(immutable)
    entry["id"] = f"STK-OOS-{session}-{ticker}"
    entry["captured_at"] = snapshot.get("captured_at")
    entry["prediction_sha256"] = canonical_hash(immutable)
    entry["outcome"] = {"status": "PENDING_NEXT_MARKET_OBSERVATION"}
    entries.append(entry)


def main() -> int:
    decision = load(DECISION_PATH)
    market = load(MARKET_PATH)
    freeze = load(FREEZE_PATH)
    history = load(HISTORY_PATH)
    oos = load(OOS_PATH)
    generated_at = now_utc()

    if decision.get("status") not in {"STOCKS_DECISION_INTELLIGENCE_READY", "PARTIAL"}:
        raise SystemExit("Stocks decision intelligence is not ready.")
    if not decision.get("frozen") or decision.get("model_status") != "FROZEN_PROSPECTIVE":
        raise SystemExit("Stocks model is not frozen. Run the hardened decision builder first.")
    if decision.get("model_hash") != freeze.get("methodology_sha256"):
        raise SystemExit("Frozen methodology hash mismatch; prospective collection stopped.")

    market_by_ticker = {x.get("ticker"): x for x in market.get("symbols", []) if x.get("ticker")}
    decision_by_ticker = {x.get("ticker"): x for x in decision.get("symbols", []) if x.get("ticker")}
    old_history = list(history.get("entries", []))
    history_entries = list(old_history)
    current_snapshots: List[Dict[str, Any]] = []
    all_alerts: List[Dict[str, Any]] = []

    for ticker in sorted(decision_by_ticker):
        symbol = decision_by_ticker[ticker]
        market_symbol = market_by_ticker.get(ticker) or {}
        close = fnum((market_symbol.get("latest_bar") or {}).get("close"))
        snap = snapshot_for(symbol, close, freeze, generated_at)
        current_snapshots.append(snap)
        previous = previous_snapshot(old_history, ticker, snap.get("market_session"))
        all_alerts.extend(build_alerts(snap, previous))
        if not any(e.get("ticker") == ticker and e.get("market_session") == snap.get("market_session") for e in history_entries):
            history_entries.append(snap)

    history_entries.sort(key=lambda x: (x.get("market_session") or "", x.get("ticker") or ""))
    history["updated_at"] = generated_at
    history["model_id"] = freeze.get("model_id")
    history["model_hash"] = freeze.get("methodology_sha256")
    history["entries"] = history_entries
    history["summary"] = {
        "snapshots": len(history_entries),
        "sessions": len({e.get("market_session") for e in history_entries if e.get("market_session")}),
        "symbols": len({e.get("ticker") for e in history_entries if e.get("ticker")}),
        "prospective_snapshots": sum(1 for e in history_entries if e.get("phase") == "PROSPECTIVE"),
        "baseline_snapshots": sum(1 for e in history_entries if e.get("phase") == "FREEZE_BASELINE"),
    }
    save(HISTORY_PATH, history)

    severity_rank = {"HIGH": 0, "MODERATE": 1, "INFORMATIONAL": 2}
    all_alerts.sort(key=lambda a: (severity_rank.get(a.get("severity"), 9), a.get("ticker") or "", a.get("code") or ""))
    high = sum(1 for a in all_alerts if a.get("severity") == "HIGH")
    moderate = sum(1 for a in all_alerts if a.get("severity") == "MODERATE")
    gate = "REVIEW_NOW" if high else ("REVIEW" if moderate else "STABLE")
    watch = {
        "version": "1.0",
        "status": "STOCKS_DECISION_WATCH_ACTIVE",
        "scope": decision.get("scope"),
        "generated_at": generated_at,
        "market_session": max((s.get("market_session") or "" for s in current_snapshots), default=None),
        "model_id": freeze.get("model_id"),
        "model_hash": freeze.get("methodology_sha256"),
        "summary": {
            "gate": gate,
            "high": high,
            "moderate": moderate,
            "informational": 0,
            "total": len(all_alerts),
            "symbols_under_watch": len({a.get("ticker") for a in all_alerts}),
        },
        "alerts": all_alerts,
        "guardrails": {
            "material_change_only": True,
            "alerts_are_review_priority_not_profit_probability": True,
            "baseline_is_not_historical_backfill": True,
            "no_buy_sell": True,
            "trade_execution": "OFF",
        },
    }
    save(WATCH_PATH, watch)

    oos_entries = list(oos.get("entries", []))
    current_by_ticker = {s.get("ticker"): s for s in current_snapshots if s.get("ticker")}
    settle_oos(oos_entries, current_by_ticker, market_by_ticker, generated_at)
    for snap in current_snapshots:
        capture_oos(oos_entries, snap, freeze)
    oos_entries.sort(key=lambda x: (x.get("capture_market_session") or "", x.get("ticker") or ""))
    settled = [e for e in oos_entries if e.get("outcome", {}).get("status") == "SETTLED"]
    pending = [e for e in oos_entries if e.get("outcome", {}).get("status") == "PENDING_NEXT_MARKET_OBSERVATION"]
    hits = sum(1 for e in settled if e.get("outcome", {}).get("hit") is True)
    misses = sum(1 for e in settled if e.get("outcome", {}).get("hit") is False)
    oos["updated_at"] = generated_at
    oos["model_id"] = freeze.get("model_id")
    oos["model_hash"] = freeze.get("methodology_sha256")
    oos["summary"] = {
        "captured": len(oos_entries),
        "settled": len(settled),
        "pending": len(pending),
        "hits": hits,
        "misses": misses,
        "hit_rate_percent": round(hits / len(settled) * 100.0, 2) if settled else None,
        "preliminary_target": (freeze.get("sample_policy") or {}).get("preliminary_settled_target", 20),
        "primary_target": (freeze.get("sample_policy") or {}).get("primary_settled_target", 60),
    }
    oos["entries"] = oos_entries
    save(OOS_PATH, oos)

    print(f"10D ready: {len(history_entries)} history snapshots, {len(all_alerts)} alerts, {len(oos_entries)} OOS captures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
