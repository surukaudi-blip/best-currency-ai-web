#!/usr/bin/env python3
"""Build Stage 11C Crypto Decision Intelligence.

Inputs:
  data/crypto-market-data.json  (Stage 11A)
  data/crypto-evidence.json     (Stage 11B)

This model is EXPERIMENTAL_PREVALIDATION and intentionally unfrozen.
It generates explainable decision-support states, not BUY/SELL calls or profit probabilities.
Historical backtest (11C.4) and Pre-Freeze Cross-Check (11C.5) are mandatory before freeze.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
MARKET_PATH = ROOT / "data" / "crypto-market-data.json"
EVIDENCE_PATH = ROOT / "data" / "crypto-evidence.json"
OUTPUT_PATH = ROOT / "data" / "crypto-decision-intelligence.json"

MARKET_WEIGHTS = {
    "return_30d": 0.30,
    "close_vs_sma20": 0.25,
    "close_vs_sma50": 0.30,
    "return_7d": 0.15,
}

READINESS_WEIGHTS = {
    "market_data_quality": 0.20,
    "market_freshness": 0.15,
    "evidence_readiness": 0.25,
    "directional_clarity": 0.25,
    "market_participation": 0.15,
}

RISK_WEIGHTS = {
    "volatility": 0.30,
    "drawdown": 0.20,
    "one_day_shock": 0.15,
    "regulatory_uncertainty": 0.15,
    "evidence_gap": 0.10,
    "horizon_conflict": 0.10,
}


def load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def fnum(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def signed_score(v: Optional[float], span: float) -> Optional[float]:
    if v is None:
        return None
    return round(clamp(50.0 + 50.0 * float(v) / span), 2)


def weighted_available(parts: List[Tuple[Optional[float], float]]) -> Optional[float]:
    rows = [(score, weight) for score, weight in parts if score is not None]
    total = sum(weight for _, weight in rows)
    if total <= 0:
        return None
    return round(sum(float(score) * weight for score, weight in rows) / total, 2)


def state_from_score(score: Optional[float]) -> str:
    if score is None:
        return "UNAVAILABLE"
    if score >= 62:
        return "SUPPORTIVE"
    if score <= 38:
        return "PRESSURED"
    return "MIXED"


def market_structure(asset: Dict[str, Any]) -> Dict[str, Any]:
    c = asset.get("completed_daily_context") or {}
    components = {
        "return_30d": signed_score(fnum(c.get("return_30d_percent")), 25.0),
        "close_vs_sma20": signed_score(fnum(c.get("close_vs_sma20_percent")), 12.0),
        "close_vs_sma50": signed_score(fnum(c.get("close_vs_sma50_percent")), 20.0),
        "return_7d": signed_score(fnum(c.get("return_7d_percent")), 12.0),
    }
    score = weighted_available([(components[k], MARKET_WEIGHTS[k]) for k in MARKET_WEIGHTS])
    return {
        "score": score,
        "state": state_from_score(score),
        "components": components,
        "completed_session": c.get("completed_session"),
        "basis": "COMPLETED_UTC_DAILY_CONTEXT_ONLY",
    }


def protocol_freshness_score(hours: Optional[float]) -> float:
    if hours is None:
        return 35.0
    if hours <= 72:
        return 100.0
    if hours <= 168:
        return 85.0
    if hours <= 720:
        return 65.0
    return 45.0


def network_readiness_score(row: Optional[Dict[str, Any]]) -> Tuple[float, str]:
    if not row:
        return 45.0, "UNAVAILABLE"
    status = row.get("status")
    if status == "READY":
        return 100.0, "READY"
    if status == "NOT_APPLICABLE_NATIVE_CHAIN":
        return 75.0, status
    if status == "DEFERRED":
        return 60.0, status
    if status == "ERROR":
        return 20.0, status
    return 40.0, str(status or "UNKNOWN")


def evidence_readiness(symbol: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
    protocol = next((x for x in evidence.get("protocol_evidence", []) if x.get("symbol") == symbol), None)
    network = next((x for x in evidence.get("network_evidence", []) if x.get("symbol") == symbol), None)
    reg_status = evidence.get("regulatory_source_status") or []
    regulators_ready = sum(1 for x in reg_status if x.get("status") == "READY")
    regulators_total = len(reg_status)

    p_score = protocol_freshness_score(fnum((protocol or {}).get("freshness_hours"))) if protocol and protocol.get("status") == "READY" else 20.0
    n_score, n_status = network_readiness_score(network)
    r_score = round(regulators_ready / regulators_total * 100.0, 2) if regulators_total else 20.0
    score = round(0.45 * p_score + 0.20 * n_score + 0.35 * r_score, 2)
    state = "READY" if score >= 75 else ("PARTIAL" if score >= 50 else "LOW_COVERAGE")
    return {
        "score": score,
        "state": state,
        "components": {
            "protocol_freshness": round(p_score, 2),
            "network_telemetry_readiness": round(n_score, 2),
            "regulatory_source_readiness": round(r_score, 2),
        },
        "protocol_status": (protocol or {}).get("status", "UNAVAILABLE"),
        "network_status": n_status,
        "regulatory_sources_ready": regulators_ready,
        "regulatory_sources_total": regulators_total,
        "directional_interpretation": "NOT_ASSIGNED",
    }


def market_freshness_score(asset: Dict[str, Any], market: Dict[str, Any]) -> float:
    session = (asset.get("completed_daily_context") or {}).get("completed_session")
    generated = market.get("generated_at")
    if not session or not generated:
        return 30.0
    try:
        d = datetime.fromisoformat(session).date()
        g = datetime.fromisoformat(str(generated).replace("Z", "+00:00")).date()
        age = (g - d).days
    except Exception:
        return 40.0
    if age <= 1:
        return 100.0
    if age <= 2:
        return 85.0
    if age <= 3:
        return 65.0
    return 35.0


def participation_score(asset: Dict[str, Any]) -> float:
    c = asset.get("completed_daily_context") or {}
    ratio = fnum(c.get("volume_7d_vs_30d_ratio"))
    if ratio is None:
        return 45.0
    if ratio >= 1.25:
        return 90.0
    if ratio >= 0.90:
        return 80.0
    if ratio >= 0.70:
        return 65.0
    if ratio >= 0.50:
        return 50.0
    return 35.0


def clarity_score(market_score: Optional[float]) -> float:
    if market_score is None:
        return 20.0
    return round(clamp(abs(float(market_score) - 50.0) * 2.0), 2)


def decision_readiness(asset: Dict[str, Any], market: Dict[str, Any], m: Dict[str, Any], e: Dict[str, Any]) -> Dict[str, Any]:
    c = asset.get("completed_daily_context") or {}
    history = fnum(c.get("history_observations")) or 0.0
    quality = clamp(history / 90.0 * 100.0)
    fresh = market_freshness_score(asset, market)
    clarity = clarity_score(m.get("score"))
    participation = participation_score(asset)
    components = {
        "market_data_quality": round(quality, 2),
        "market_freshness": round(fresh, 2),
        "evidence_readiness": round(float(e.get("score") or 0.0), 2),
        "directional_clarity": round(clarity, 2),
        "market_participation": round(participation, 2),
    }
    score = round(sum(components[k] * READINESS_WEIGHTS[k] for k in READINESS_WEIGHTS), 2)
    state = "READY_FOR_REVIEW" if score >= 70 else ("CONDITIONAL_REVIEW" if score >= 50 else "LOW_READINESS")
    return {"score": score, "state": state, "components": components}


def volatility_risk(v: Optional[float]) -> float:
    if v is None:
        return 55.0
    if v <= 35:
        return 20.0
    if v <= 60:
        return 20.0 + (v - 35.0) / 25.0 * 25.0
    if v <= 90:
        return 45.0 + (v - 60.0) / 30.0 * 25.0
    return clamp(70.0 + (v - 90.0) / 60.0 * 25.0, 70.0, 95.0)


def drawdown_risk(v: Optional[float]) -> float:
    if v is None:
        return 50.0
    dd = abs(min(float(v), 0.0))
    if dd <= 10:
        return 20.0
    if dd <= 20:
        return 20.0 + (dd - 10.0) * 2.0
    if dd <= 35:
        return 40.0 + (dd - 20.0) / 15.0 * 25.0
    return clamp(65.0 + (dd - 35.0) / 35.0 * 25.0, 65.0, 90.0)


def horizon_conflict_risk(asset: Dict[str, Any]) -> Tuple[float, int]:
    c = asset.get("completed_daily_context") or {}
    vals = [
        fnum(c.get("return_7d_percent")),
        fnum(c.get("return_30d_percent")),
        fnum(c.get("close_vs_sma20_percent")),
        fnum(c.get("close_vs_sma50_percent")),
    ]
    signs = [1 if v > 0 else (-1 if v < 0 else 0) for v in vals if v is not None]
    pos = sum(1 for x in signs if x > 0)
    neg = sum(1 for x in signs if x < 0)
    conflict = min(pos, neg)
    return ({0: 20.0, 1: 50.0, 2: 75.0}.get(conflict, 75.0), conflict)


def regulatory_uncertainty(symbol: str, evidence: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    score = 20.0
    for event in evidence.get("regulatory_evidence", []):
        age = fnum(event.get("freshness_hours"))
        scope = event.get("scope")
        assets = event.get("asset_scope") or []
        relevant = symbol in assets or scope == "CRYPTO_GENERAL"
        if not relevant:
            continue
        rows.append(event)
        if symbol in assets and age is not None and age <= 168:
            score = max(score, 85.0)
        elif scope == "CRYPTO_GENERAL" and age is not None and age <= 72:
            score = max(score, 60.0)
        elif age is not None and age <= 336:
            score = max(score, 45.0)
    return score, rows[:5]


def evidence_gap_risk(e: Dict[str, Any]) -> float:
    if e.get("state") == "READY":
        return 20.0
    if e.get("state") == "PARTIAL":
        return 50.0
    return 80.0


def decision_risk(symbol: str, asset: Dict[str, Any], evidence: Dict[str, Any], e: Dict[str, Any]) -> Dict[str, Any]:
    c = asset.get("completed_daily_context") or {}
    vol = volatility_risk(fnum(c.get("realized_volatility_30d_annualized_percent")))
    dd = drawdown_risk(fnum(c.get("drawdown_from_90d_high_percent")))
    one_day = clamp(abs(fnum(c.get("return_1d_percent")) or 0.0) / 10.0 * 100.0)
    reg, relevant_events = regulatory_uncertainty(symbol, evidence)
    gap = evidence_gap_risk(e)
    conflict, conflict_count = horizon_conflict_risk(asset)
    components = {
        "volatility": round(vol, 2),
        "drawdown": round(dd, 2),
        "one_day_shock": round(one_day, 2),
        "regulatory_uncertainty": round(reg, 2),
        "evidence_gap": round(gap, 2),
        "horizon_conflict": round(conflict, 2),
    }
    score = round(sum(components[k] * RISK_WEIGHTS[k] for k in RISK_WEIGHTS), 2)
    state = "LOW" if score < 35 else ("MODERATE" if score < 65 else "HIGH")
    return {
        "score": score,
        "state": state,
        "components": components,
        "horizon_conflict_count": conflict_count,
        "relevant_regulatory_events": [
            {"source": x.get("source"), "published_at": x.get("published_at"), "scope": x.get("scope"), "title": x.get("title")}
            for x in relevant_events
        ],
    }


def counter_thesis(symbol: str, asset: Dict[str, Any], market_state: str, risk: Dict[str, Any], e: Dict[str, Any]) -> Dict[str, Any]:
    c = asset.get("completed_daily_context") or {}
    factors: List[Dict[str, str]] = []
    r1 = fnum(c.get("return_1d_percent")) or 0.0
    r7 = fnum(c.get("return_7d_percent"))
    r30 = fnum(c.get("return_30d_percent"))
    vol = fnum(c.get("realized_volatility_30d_annualized_percent"))
    dd = fnum(c.get("drawdown_from_90d_high_percent"))

    if market_state == "SUPPORTIVE" and r1 <= -4.0:
        factors.append({"severity": "MODERATE", "text": "Latest completed day moved sharply against the supportive structure."})
    if market_state == "PRESSURED" and r1 >= 4.0:
        factors.append({"severity": "MODERATE", "text": "Latest completed day rebounded sharply against the pressured structure."})
    if r7 is not None and r30 is not None and r7 * r30 < 0:
        factors.append({"severity": "MODERATE", "text": "7-day and 30-day returns point in opposite directions."})
    if vol is not None and vol >= 90:
        factors.append({"severity": "HIGH", "text": "30-day realized volatility is extreme and can destabilize the current structure."})
    elif vol is not None and vol >= 60:
        factors.append({"severity": "MODERATE", "text": "30-day realized volatility is elevated."})
    if dd is not None and dd <= -35:
        factors.append({"severity": "HIGH", "text": "The asset remains in a deep drawdown from its 90-day high."})
    elif dd is not None and dd <= -25:
        factors.append({"severity": "MODERATE", "text": "The asset remains materially below its 90-day high."})
    if float((risk.get("components") or {}).get("regulatory_uncertainty") or 0.0) >= 60:
        factors.append({"severity": "MODERATE", "text": "A recent primary regulatory event raises uncertainty; Stage 11C does not assign it a bullish or bearish direction."})
    if e.get("state") != "READY":
        factors.append({"severity": "MODERATE", "text": f"Evidence coverage is {e.get('state')}; missing or deferred telemetry is not imputed."})
    if risk.get("state") == "HIGH":
        factors.append({"severity": "HIGH", "text": "Aggregate Decision Risk is HIGH, constraining confidence in the current Market View."})

    high = sum(1 for x in factors if x.get("severity") == "HIGH")
    strength = "HIGH" if high else ("MODERATE" if len(factors) >= 2 else ("LOW" if factors else "LIMITED"))
    return {"status": "ACTIVE" if factors else "LIMITED", "strength": strength, "factors": factors}


def reasoner(market_state: str, readiness: Dict[str, Any], risk: Dict[str, Any], counter: Dict[str, Any]) -> Dict[str, Any]:
    rd_score = float(readiness.get("score") or 0.0)
    risk_state = risk.get("state")
    if risk_state == "HIGH":
        status = "RISK_CONSTRAINED"
    elif readiness.get("state") == "LOW_READINESS":
        status = "EVIDENCE_INCOMPLETE"
    elif market_state == "SUPPORTIVE":
        status = "STRUCTURE_SUPPORTIVE"
    elif market_state == "PRESSURED":
        status = "STRUCTURE_PRESSURED"
    else:
        status = "MIXED_MARKET_STRUCTURE"

    if risk_state == "HIGH" or rd_score < 50:
        decision = "DEPRIORITIZE"
    elif market_state in {"SUPPORTIVE", "PRESSURED"} and rd_score >= 70 and counter.get("strength") != "HIGH":
        decision = "REVIEW_SELECTIVELY"
    else:
        decision = "WATCH"

    return {
        "status": status,
        "decision": decision,
        "market_view": market_state,
        "readiness_state": readiness.get("state"),
        "risk_state": risk_state,
        "counter_thesis_strength": counter.get("strength"),
        "buy_sell": "NOT_GENERATED",
        "profit_probability": "NOT_ESTIMATED",
        "trade_execution": "OFF",
    }


def global_context(market: Dict[str, Any]) -> Dict[str, Any]:
    g = market.get("global_market") or {}
    change = fnum(g.get("market_cap_change_24h_percent"))
    if change is None:
        regime = "UNAVAILABLE"
    elif change >= 2.0:
        regime = "RISK_ON_SNAPSHOT"
    elif change <= -2.0:
        regime = "RISK_OFF_SNAPSHOT"
    else:
        regime = "NEUTRAL_SNAPSHOT"
    return {
        "state": regime,
        "market_cap_change_24h_percent": change,
        "btc_dominance_percent": fnum(g.get("btc_dominance_percent")),
        "eth_dominance_percent": fnum(g.get("eth_dominance_percent")),
        "basis": "CURRENT_GLOBAL_SNAPSHOT_CONTEXT_ONLY_NOT_USED_TO_SET_COMPLETED_DAILY_MARKET_VIEW",
    }


def build_symbol(asset: Dict[str, Any], market: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
    symbol = asset.get("symbol")
    m = market_structure(asset)
    e = evidence_readiness(symbol, evidence)
    rd = decision_readiness(asset, market, m, e)
    rk = decision_risk(symbol, asset, evidence, e)
    ct = counter_thesis(symbol, asset, m.get("state"), rk, e)
    ai = reasoner(m.get("state"), rd, rk, ct)
    return {
        "symbol": symbol,
        "name": asset.get("name"),
        "market_session": (asset.get("completed_daily_context") or {}).get("completed_session"),
        "market_structure": m,
        "evidence_readiness": e,
        "decision_readiness": rd,
        "decision_risk": rk,
        "counter_thesis": ct,
        "ai_decision_reasoner": ai,
        "provenance": {
            "market_data": "Stage 11A CoinGecko keyed server-side completed UTC context",
            "evidence": "Stage 11B curated protocol/core repositories + SEC/CFTC + approved chain-specific telemetry",
        },
    }


def main() -> int:
    market = load(MARKET_PATH)
    evidence = load(EVIDENCE_PATH)
    if market.get("status") != "CRYPTO_MARKET_DATA_READY":
        raise SystemExit("Stage 11A market data is not ready.")
    if not str(evidence.get("status", "")).startswith("CRYPTO_EVIDENCE_READY"):
        raise SystemExit("Stage 11B evidence is not ready.")

    symbols: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    for asset in market.get("assets", []):
        if asset.get("status") != "READY":
            errors.append({"symbol": asset.get("symbol"), "error": "11A asset is not READY"})
            continue
        try:
            symbols.append(build_symbol(asset, market, evidence))
        except Exception as exc:
            errors.append({"symbol": asset.get("symbol"), "error": str(exc)[:500]})

    status = "CRYPTO_DECISION_INTELLIGENCE_READY" if symbols and not errors else ("PARTIAL" if symbols else "FAILED")
    artifact = {
        "version": "0.1",
        "status": status,
        "scope": market.get("scope"),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "model_status": "EXPERIMENTAL_PREVALIDATION",
        "frozen": False,
        "market_session": (market.get("market_clock") or {}).get("latest_completed_session"),
        "global_context": global_context(market),
        "methodology": {
            "market_structure": {
                "weights": MARKET_WEIGHTS,
                "score_spans_percent": {"return_30d": 25, "close_vs_sma20": 12, "close_vs_sma50": 20, "return_7d": 12},
                "state_thresholds": {"supportive_gte": 62, "pressured_lte": 38, "otherwise": "MIXED"},
                "direction_source": "COMPLETED_MARKET_DATA_ONLY",
            },
            "evidence_readiness": {
                "weights": {"protocol_freshness": 0.45, "network_telemetry_readiness": 0.20, "regulatory_source_readiness": 0.35},
                "network_policy": "READY=100, NOT_APPLICABLE=75, DEFERRED=60, ERROR=20; network metrics themselves are not cross-chain scored",
            },
            "decision_readiness": {"weights": READINESS_WEIGHTS, "thresholds": {"ready_for_review_gte": 70, "conditional_gte": 50}},
            "decision_risk": {"weights": RISK_WEIGHTS, "thresholds": {"low_lt": 35, "high_gte": 65}},
            "regulatory_policy": "Primary regulatory events can raise uncertainty/risk but are not assigned bullish/bearish direction in 11C.",
        },
        "symbols": symbols,
        "errors": errors,
        "guardrails": {
            "market_direction_comes_only_from_completed_market_data": True,
            "current_global_snapshot_is_context_not_direction_vote": True,
            "protocol_activity_not_directional": True,
            "regulatory_events_not_directional": True,
            "network_telemetry_not_cross_chain_scored": True,
            "missing_network_telemetry_not_imputed": True,
            "no_buy_sell": True,
            "no_profit_probability": True,
            "backtest_required_before_freeze": True,
            "pre_freeze_cross_check_required": True,
            "model_is_unfrozen": True,
            "trade_execution": "OFF",
        },
    }
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"11C: {status}; symbols={len(symbols)}; errors={len(errors)}; frozen=false")
    return 0 if status == "CRYPTO_DECISION_INTELLIGENCE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
