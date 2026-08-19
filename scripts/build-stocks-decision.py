#!/usr/bin/env python3
"""Build Stocks Stage 10C explainable decision-intelligence artifact.

Inputs:
  data/stocks-intelligence.json      (SEC official evidence, Stage 10A)
  data/stocks-market-data.json       (daily OHLCV context, Stage 10B)

This pre-validation model intentionally does NOT generate BUY/SELL calls or profit
probabilities. It produces auditable decision-support states that must be frozen
and prospectively validated in Stage 10D before any performance claim.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
SEC_PATH = ROOT / "data" / "stocks-intelligence.json"
MARKET_PATH = ROOT / "data" / "stocks-market-data.json"
OUTPUT_PATH = ROOT / "data" / "stocks-decision-intelligence.json"

FUNDAMENTAL_WEIGHTS = {
    "revenue": 0.20,
    "net_income": 0.20,
    "operating_income": 0.15,
    "operating_cash_flow": 0.20,
    "diluted_eps": 0.15,
    "cash": 0.05,
    "stockholders_equity": 0.05,
}

MARKET_WEIGHTS = {
    "return_20d": 0.35,
    "close_vs_sma20": 0.25,
    "close_vs_sma50": 0.30,
    "return_5d": 0.10,
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def signed_score(value: Optional[float], span: float) -> Optional[float]:
    if value is None:
        return None
    return round(clamp(50.0 + 50.0 * float(value) / span), 2)


def weighted_available(parts: List[Tuple[Optional[float], float]]) -> Optional[float]:
    available = [(score, weight) for score, weight in parts if score is not None]
    total_weight = sum(weight for _, weight in available)
    if total_weight <= 0:
        return None
    return round(sum(float(score) * weight for score, weight in available) / total_weight, 2)


def state_from_score(score: Optional[float]) -> str:
    if score is None:
        return "UNAVAILABLE"
    if score >= 62:
        return "SUPPORTIVE"
    if score <= 38:
        return "PRESSURED"
    return "MIXED"


def alignment_state(market_state: str, fundamental_state: str) -> Tuple[str, float]:
    if market_state in {"SUPPORTIVE", "PRESSURED"} and market_state == fundamental_state:
        return "ALIGNED", 100.0
    if market_state in {"SUPPORTIVE", "PRESSURED"} and fundamental_state in {"SUPPORTIVE", "PRESSURED"}:
        return "DIVERGENT", 25.0
    if "UNAVAILABLE" in {market_state, fundamental_state}:
        return "INCOMPLETE", 20.0
    return "MIXED_ALIGNMENT", 65.0


def freshness_score(days: Optional[int], bands: List[Tuple[int, float]]) -> float:
    if days is None:
        return 20.0
    for max_days, score in bands:
        if days <= max_days:
            return score
    return 20.0


def participation_score(volume_ratio: Optional[float]) -> float:
    if volume_ratio is None:
        return 40.0
    ratio = float(volume_ratio)
    if ratio >= 1.5:
        return 90.0
    if ratio >= 1.0:
        return 80.0
    if ratio >= 0.75:
        return 70.0
    if ratio >= 0.5:
        return 55.0
    return 35.0


def volatility_risk(vol: Optional[float]) -> float:
    if vol is None:
        return 50.0
    v = float(vol)
    if v <= 25:
        return 20.0
    if v <= 40:
        return 20.0 + (v - 25.0) / 15.0 * 25.0
    if v <= 60:
        return 45.0 + (v - 40.0) / 20.0 * 25.0
    return clamp(70.0 + (v - 60.0) / 30.0 * 25.0, 70.0, 95.0)


def event_risk(recent_8k_count: Optional[int]) -> float:
    count = int(recent_8k_count or 0)
    if count <= 0:
        return 20.0
    if count == 1:
        return 45.0
    if count == 2:
        return 65.0
    return 85.0


def divergence_risk(alignment: str) -> float:
    return {"ALIGNED": 25.0, "MIXED_ALIGNMENT": 45.0, "DIVERGENT": 80.0, "INCOMPLETE": 70.0}.get(alignment, 50.0)


def balance_sheet_risk(fundamentals: Dict[str, Any]) -> Tuple[float, Optional[float]]:
    liabilities = fundamentals.get("liabilities") or {}
    assets = fundamentals.get("assets") or {}
    lg = liabilities.get("change_percent_vs_comparable_reported_period")
    ag = assets.get("change_percent_vs_comparable_reported_period")
    if lg is None or ag is None:
        return 35.0, None
    spread = round(float(lg) - float(ag), 2)
    if spread <= 0:
        return 25.0, spread
    if spread <= 10:
        return 40.0, spread
    if spread <= 25:
        return 65.0, spread
    return 85.0, spread


def market_structure(market: Dict[str, Any]) -> Dict[str, Any]:
    ctx = market.get("derived_market_context") or {}
    parts = {
        "return_20d": signed_score(ctx.get("return_20d_percent"), 15.0),
        "close_vs_sma20": signed_score(ctx.get("close_vs_sma20_percent"), 8.0),
        "close_vs_sma50": signed_score(ctx.get("close_vs_sma50_percent"), 12.0),
        "return_5d": signed_score(ctx.get("return_5d_percent"), 8.0),
    }
    score = weighted_available([(parts[k], MARKET_WEIGHTS[k]) for k in MARKET_WEIGHTS])
    return {"score": score, "state": state_from_score(score), "components": parts}


def fundamental_evidence(sec: Dict[str, Any]) -> Dict[str, Any]:
    fundamentals = sec.get("fundamentals") or {}
    components: Dict[str, Any] = {}
    weighted: List[Tuple[Optional[float], float]] = []
    available_weight = 0.0
    for key, weight in FUNDAMENTAL_WEIGHTS.items():
        metric = fundamentals.get(key) or {}
        comparable = metric.get("comparison_basis") == "SAME_FISCAL_PERIOD_PRIOR_YEAR"
        change = metric.get("change_percent_vs_comparable_reported_period") if comparable else None
        score = signed_score(change, 25.0) if change is not None else None
        components[key] = {
            "change_percent": change,
            "score": score,
            "comparison_basis": metric.get("comparison_basis"),
        }
        weighted.append((score, weight))
        if score is not None:
            available_weight += weight
    score = weighted_available(weighted)
    coverage = round(available_weight / sum(FUNDAMENTAL_WEIGHTS.values()) * 100.0, 1)
    return {"score": score, "state": state_from_score(score), "comparable_coverage_percent": coverage, "components": components}


def readiness(sec: Dict[str, Any], market: Dict[str, Any], market_score: Optional[float], fundamental_score: Optional[float], alignment_score: float, comparable_coverage: float) -> Dict[str, Any]:
    sec_completeness = float(sec.get("evidence_completeness_percent") or 0.0)
    quality = market.get("data_quality") or {}
    bars = float(quality.get("bars_received") or 0.0)
    market_completeness = clamp(bars / 50.0 * 100.0)
    market_freshness = freshness_score((market.get("freshness") or {}).get("calendar_days_since_latest_session"), [(3, 100.0), (5, 80.0), (7, 55.0)])
    sec_freshness = freshness_score((sec.get("freshness") or {}).get("days_since_latest_material_filing"), [(45, 100.0), (90, 80.0), (180, 60.0), (365, 40.0)])
    clarity_values = [abs(float(x) - 50.0) * 2.0 for x in (market_score, fundamental_score) if x is not None]
    clarity = round(sum(clarity_values) / len(clarity_values), 2) if clarity_values else 20.0
    participation = participation_score((market.get("derived_market_context") or {}).get("latest_volume_vs_20d_average_ratio"))
    score = round(
        0.10 * sec_completeness
        + 0.10 * market_completeness
        + 0.05 * comparable_coverage
        + 0.10 * market_freshness
        + 0.10 * sec_freshness
        + 0.25 * alignment_score
        + 0.20 * clarity
        + 0.10 * participation,
        2,
    )
    if score >= 70:
        state = "READY_FOR_REVIEW"
    elif score >= 50:
        state = "CONDITIONAL_REVIEW"
    else:
        state = "LOW_READINESS"
    return {
        "score": score,
        "state": state,
        "components": {
            "sec_completeness": round(sec_completeness, 2),
            "market_completeness": round(market_completeness, 2),
            "comparable_fundamental_coverage": comparable_coverage,
            "market_freshness": market_freshness,
            "sec_freshness": sec_freshness,
            "cross_layer_alignment": alignment_score,
            "directional_clarity": clarity,
            "market_participation": participation,
        },
    }


def risk(sec: Dict[str, Any], market: Dict[str, Any], alignment: str) -> Dict[str, Any]:
    ctx = market.get("derived_market_context") or {}
    v_risk = volatility_risk(ctx.get("annualized_volatility_20d_percent"))
    shock = clamp(abs(float(ctx.get("return_1d_percent") or 0.0)) / 6.0 * 100.0)
    e_risk = event_risk((sec.get("freshness") or {}).get("recent_8k_count_30d"))
    d_risk = divergence_risk(alignment)
    b_risk, liability_asset_spread = balance_sheet_risk(sec.get("fundamentals") or {})
    raw_adjustment = 30.0
    score = round(0.35 * v_risk + 0.15 * shock + 0.15 * e_risk + 0.20 * d_risk + 0.10 * b_risk + 0.05 * raw_adjustment, 2)
    state = "LOW" if score < 35 else ("MODERATE" if score < 65 else "HIGH")
    return {
        "score": score,
        "state": state,
        "components": {
            "volatility": round(v_risk, 2),
            "one_day_shock": round(shock, 2),
            "recent_material_filing_activity": round(e_risk, 2),
            "evidence_divergence": round(d_risk, 2),
            "balance_sheet_stress": round(b_risk, 2),
            "liability_growth_minus_asset_growth_pct_points": liability_asset_spread,
            "raw_price_adjustment_caution": raw_adjustment,
        },
    }


def counter_thesis(sec: Dict[str, Any], market: Dict[str, Any], market_state: str, fundamental_state: str, risk_state: str) -> Dict[str, Any]:
    ctx = market.get("derived_market_context") or {}
    factors: List[Dict[str, str]] = []
    if market_state == "SUPPORTIVE" and fundamental_state == "PRESSURED":
        factors.append({"severity": "HIGH", "text": "Market structure is supportive while comparable SEC fundamentals are pressured."})
    if market_state == "PRESSURED" and fundamental_state == "SUPPORTIVE":
        factors.append({"severity": "HIGH", "text": "Market structure is pressured while comparable SEC fundamentals remain supportive."})
    r1 = float(ctx.get("return_1d_percent") or 0.0)
    if market_state == "SUPPORTIVE" and r1 <= -3.0:
        factors.append({"severity": "MODERATE", "text": "Latest session shows a sharp negative move against the supportive structure."})
    if market_state == "PRESSURED" and r1 >= 3.0:
        factors.append({"severity": "MODERATE", "text": "Latest session shows a sharp positive move against the pressured structure."})
    vol = ctx.get("annualized_volatility_20d_percent")
    if vol is not None and float(vol) >= 50.0:
        factors.append({"severity": "MODERATE", "text": "20-day realized volatility is elevated, increasing regime-instability risk."})
    recent_8k = int((sec.get("freshness") or {}).get("recent_8k_count_30d") or 0)
    if recent_8k >= 1:
        factors.append({"severity": "MODERATE", "text": "Recent 8-K activity can introduce material-event uncertainty that market-only signals may miss."})
    if risk_state == "HIGH":
        factors.append({"severity": "HIGH", "text": "Aggregate decision risk is high, constraining confidence in the directional view."})
    high = sum(1 for f in factors if f["severity"] == "HIGH")
    strength = "HIGH" if high >= 1 else ("MODERATE" if len(factors) >= 2 else ("LOW" if factors else "LIMITED"))
    return {"status": "ACTIVE" if factors else "LIMITED", "strength": strength, "factors": factors}


def reasoner(market_state: str, fundamental_state: str, alignment: str, readiness_state: str, readiness_score: float, risk_state: str, counter: Dict[str, Any]) -> Dict[str, Any]:
    if risk_state == "HIGH":
        status = "RISK_CONSTRAINED"
    elif alignment == "DIVERGENT":
        status = "EVIDENCE_DIVERGENT"
    elif market_state == fundamental_state == "SUPPORTIVE":
        status = "COHERENT_SUPPORTIVE"
    elif market_state == fundamental_state == "PRESSURED":
        status = "COHERENT_PRESSURED"
    else:
        status = "MIXED_CONTEXT"

    if readiness_score < 50 or risk_state == "HIGH":
        decision = "DEPRIORITIZE"
    elif status in {"COHERENT_SUPPORTIVE", "COHERENT_PRESSURED"} and readiness_score >= 70:
        decision = "REVIEW_SELECTIVELY"
    else:
        decision = "WATCH"

    return {
        "status": status,
        "decision": decision,
        "market_view": market_state,
        "fundamental_view": fundamental_state,
        "readiness_state": readiness_state,
        "counter_thesis_strength": counter.get("strength"),
        "buy_sell": "NOT_GENERATED",
        "profit_probability": "NOT_ESTIMATED",
        "trade_execution": "OFF",
    }


def build_symbol(sec: Dict[str, Any], market: Dict[str, Any]) -> Dict[str, Any]:
    m = market_structure(market)
    f = fundamental_evidence(sec)
    alignment, alignment_score = alignment_state(m["state"], f["state"])
    rd = readiness(sec, market, m["score"], f["score"], alignment_score, f["comparable_coverage_percent"])
    rk = risk(sec, market, alignment)
    ct = counter_thesis(sec, market, m["state"], f["state"], rk["state"])
    ai = reasoner(m["state"], f["state"], alignment, rd["state"], rd["score"], rk["state"], ct)
    return {
        "ticker": market.get("ticker") or sec.get("ticker"),
        "name": market.get("name") or sec.get("name"),
        "exchange": market.get("exchange") or sec.get("exchange"),
        "market_session": (market.get("freshness") or {}).get("latest_market_session"),
        "latest_sec_filing_date": (sec.get("freshness") or {}).get("latest_material_filing_date"),
        "market_structure": m,
        "fundamental_evidence": f,
        "cross_layer_alignment": alignment,
        "decision_readiness": rd,
        "decision_risk": rk,
        "counter_thesis": ct,
        "ai_decision_reasoner": ai,
        "provenance": {
            "market_data": "Alpha Vantage TIME_SERIES_DAILY / Stage 10B",
            "official_company_evidence": "SEC EDGAR submissions + XBRL / Stage 10A",
            "news": "DEFERRED_TO_UNIFIED_NEWS_INTELLIGENCE",
        },
    }


def main() -> int:
    sec_artifact = load_json(SEC_PATH)
    market_artifact = load_json(MARKET_PATH)
    errors: List[Dict[str, Any]] = []
    symbols: List[Dict[str, Any]] = []

    if sec_artifact.get("status") not in {"OFFICIAL_EVIDENCE_READY", "PARTIAL"}:
        errors.append({"scope": "SEC", "error": "Stage 10A official evidence is not ready."})
    if market_artifact.get("status") not in {"DAILY_MARKET_DATA_READY", "PARTIAL"}:
        errors.append({"scope": "MARKET", "error": "Stage 10B daily market data is not ready."})

    sec_by_ticker = {x.get("ticker"): x for x in sec_artifact.get("companies", []) if x.get("ticker")}
    market_by_ticker = {x.get("ticker"): x for x in market_artifact.get("symbols", []) if x.get("ticker")}
    for ticker in sorted(set(sec_by_ticker) | set(market_by_ticker)):
        sec = sec_by_ticker.get(ticker)
        market = market_by_ticker.get(ticker)
        if not sec or not market:
            errors.append({"ticker": ticker, "error": "Missing Stage 10A or 10B input; fail closed."})
            continue
        try:
            symbols.append(build_symbol(sec, market))
        except Exception as exc:
            errors.append({"ticker": ticker, "error": str(exc)})

    if symbols and not errors:
        status = "STOCKS_DECISION_INTELLIGENCE_READY"
    elif symbols:
        status = "PARTIAL"
    else:
        status = "UNAVAILABLE"

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    artifact = {
        "version": "0.1",
        "status": status,
        "scope": sec_artifact.get("scope") or market_artifact.get("scope"),
        "generated_at": generated_at,
        "model_status": "EXPERIMENTAL_PREVALIDATION",
        "frozen": False,
        "source_readiness": {
            "sec_official_evidence": sec_artifact.get("status"),
            "daily_market_data": market_artifact.get("status"),
            "news": "DEFERRED_TO_UNIFIED_NEWS_INTELLIGENCE",
            "decision_intelligence": status,
        },
        "guardrails": {
            "no_buy_sell": True,
            "no_profit_probability": True,
            "decision_support_only": True,
            "weights_not_tuned_on_outcomes": True,
            "freeze_required_before_prospective_validation": True,
            "trade_execution": "OFF",
        },
        "methodology": {
            "market_structure": {
                "weights": MARKET_WEIGHTS,
                "supportive_threshold": 62,
                "pressured_threshold": 38,
                "inputs": ["20D return", "close vs SMA20", "close vs SMA50", "5D return"],
            },
            "fundamental_evidence": {
                "weights": FUNDAMENTAL_WEIGHTS,
                "comparison_rule": "Only SAME_FISCAL_PERIOD_PRIOR_YEAR SEC XBRL comparisons are eligible.",
                "change_span_for_score": "-25% maps toward 0; +25% maps toward 100; clipped outside span.",
            },
            "decision_readiness": {
                "weights": {
                    "sec_completeness": 0.10,
                    "market_completeness": 0.10,
                    "comparable_fundamental_coverage": 0.05,
                    "market_freshness": 0.10,
                    "sec_freshness": 0.10,
                    "cross_layer_alignment": 0.25,
                    "directional_clarity": 0.20,
                    "market_participation": 0.10,
                },
                "states": {"ready_for_review": ">=70", "conditional_review": "50-69.99", "low_readiness": "<50"},
            },
            "decision_risk": {
                "weights": {
                    "volatility": 0.35,
                    "one_day_shock": 0.15,
                    "recent_material_filing_activity": 0.15,
                    "evidence_divergence": 0.20,
                    "balance_sheet_stress": 0.10,
                    "raw_price_adjustment_caution": 0.05,
                },
                "states": {"low": "<35", "moderate": "35-64.99", "high": ">=65"},
            },
            "validation_policy": "Stage 10C weights are pre-validation and must be frozen before Stage 10D prospective collection. No outcome tuning is performed here.",
        },
        "symbols": symbols,
        "errors": errors,
    }
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)} with status {status} for {len(symbols)} symbols")
    return 0 if symbols else 1


if __name__ == "__main__":
    raise SystemExit(main())
