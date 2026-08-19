#!/usr/bin/env python3
"""Stage 11C v0.2 — structural refinement after the first diagnostic backtest.

This is not a holdout optimizer. The changes address structural failure modes found
in 11C.4 v0.1: cross-asset scale mismatch, horizon disagreement, and false confidence
when an extreme pressured score occurs inside a deep drawdown.

The v0.1 core remains in the repository for auditability. This module imports it,
reuses the evidence/source logic, and replaces only the decision mechanics listed
in the v0.2 methodology artifact.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "scripts" / "build-crypto-decision.py"
BACKTEST_PATH = ROOT / "data" / "crypto-backtest.json"
OUTPUT_PATH = ROOT / "data" / "crypto-decision-intelligence.json"

spec = importlib.util.spec_from_file_location("crypto_decision_v01", BASE_PATH)
base = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(base)

# Keep the v0.1 directional weights. The refinement changes scale and gating,
# rather than searching the consumed diagnostic holdout for a new weight vector.
MARKET_WEIGHTS_V02 = dict(base.MARKET_WEIGHTS)
READINESS_WEIGHTS_V02 = {
    "market_data_quality": 0.18,
    "market_freshness": 0.15,
    "evidence_readiness": 0.22,
    "directional_clarity": 0.15,
    "market_participation": 0.10,
    "horizon_alignment": 0.20,
}
RISK_WEIGHTS_V02 = {
    "volatility": 0.22,
    "drawdown": 0.14,
    "one_day_shock": 0.10,
    "regulatory_uncertainty": 0.14,
    "evidence_gap": 0.10,
    "horizon_conflict": 0.12,
    "reversal_exhaustion": 0.18,
}
ALIGNMENT_REQUIRED = 3
SUPPORTIVE_GTE = 62.0
PRESSURED_LTE = 38.0


def fnum(v: Any) -> Optional[float]:
    return base.fnum(v)


def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return base.clamp(v, lo, hi)


def volatility_normalized_component(value_percent: Optional[float], annualized_vol_percent: Optional[float], horizon_days: int) -> Tuple[Optional[float], Optional[float]]:
    """Map a horizon return/displacement to a bounded score using its volatility scale.

    A z-like magnitude of +/-2 maps to 0/100. This is a fixed statistical scale,
    not a threshold selected from the consumed backtest.
    """
    if value_percent is None or annualized_vol_percent is None or annualized_vol_percent <= 0:
        return None, None
    daily_vol = annualized_vol_percent / math.sqrt(365.0)
    expected_horizon_vol = daily_vol * math.sqrt(float(horizon_days))
    if expected_horizon_vol <= 0:
        return None, None
    z = float(value_percent) / expected_horizon_vol
    score = clamp(50.0 + 25.0 * z)
    return round(score, 2), round(z, 4)


def raw_state_from_score(score: Optional[float], supportive_gte: float = SUPPORTIVE_GTE, pressured_lte: float = PRESSURED_LTE) -> str:
    if score is None:
        return "UNAVAILABLE"
    if score >= supportive_gte:
        return "SUPPORTIVE"
    if score <= pressured_lte:
        return "PRESSURED"
    return "MIXED"


def horizon_alignment(c: Dict[str, Any]) -> Dict[str, Any]:
    fields = {
        "return_30d": fnum(c.get("return_30d_percent")),
        "close_vs_sma20": fnum(c.get("close_vs_sma20_percent")),
        "close_vs_sma50": fnum(c.get("close_vs_sma50_percent")),
        "return_7d": fnum(c.get("return_7d_percent")),
    }
    signs = {k: (1 if v > 0 else (-1 if v < 0 else 0)) for k, v in fields.items() if v is not None}
    positive = sum(1 for v in signs.values() if v > 0)
    negative = sum(1 for v in signs.values() if v < 0)
    valid = len(signs)
    aligned = max(positive, negative)
    dominant = "POSITIVE" if positive > negative else ("NEGATIVE" if negative > positive else "BALANCED")
    alignment_score = 100.0 if aligned >= 4 else (80.0 if aligned == 3 else (50.0 if aligned == 2 else 30.0))
    return {
        "positive_count": positive,
        "negative_count": negative,
        "valid_count": valid,
        "aligned_count": aligned,
        "required_for_directional_state": ALIGNMENT_REQUIRED,
        "dominant_direction": dominant,
        "score": alignment_score,
        "components": signs,
    }


def extension_guardrails(raw_state: str, raw_score: Optional[float], drawdown_90d: Optional[float]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    if raw_score is None or drawdown_90d is None:
        return rows
    # Downside exhaustion: an extreme trend score inside a deep drawdown is not
    # treated as high-confidence continuation. This directly addresses the observed
    # structural reversal risk without selecting a new profit-maximizing threshold.
    if raw_state == "PRESSURED" and raw_score <= 20.0 and drawdown_90d <= -30.0:
        rows.append({
            "code": "DOWNSIDE_EXHAUSTION_RISK",
            "severity": "HIGH",
            "message": "Extreme downside structure occurs inside a deep 90-day drawdown; continuation confidence is suppressed because reversal/exhaustion risk is elevated.",
        })
    # Symmetric upside extension guardrail near the 90-day high.
    if raw_state == "SUPPORTIVE" and raw_score >= 80.0 and drawdown_90d >= -5.0:
        rows.append({
            "code": "UPSIDE_EXTENSION_RISK",
            "severity": "MODERATE",
            "message": "Extreme upside structure occurs close to the 90-day high; directional confidence is suppressed until continuation is confirmed.",
        })
    return rows


def market_structure_v02(asset: Dict[str, Any]) -> Dict[str, Any]:
    c = asset.get("completed_daily_context") or {}
    vol = fnum(c.get("realized_volatility_30d_annualized_percent"))
    inputs = {
        "return_30d": (fnum(c.get("return_30d_percent")), 30),
        "close_vs_sma20": (fnum(c.get("close_vs_sma20_percent")), 20),
        "close_vs_sma50": (fnum(c.get("close_vs_sma50_percent")), 50),
        "return_7d": (fnum(c.get("return_7d_percent")), 7),
    }
    components: Dict[str, Optional[float]] = {}
    normalized_z: Dict[str, Optional[float]] = {}
    for key, (value, horizon) in inputs.items():
        component, z = volatility_normalized_component(value, vol, horizon)
        components[key] = component
        normalized_z[key] = z

    raw_score = base.weighted_available([(components[k], MARKET_WEIGHTS_V02[k]) for k in MARKET_WEIGHTS_V02])
    raw_state = raw_state_from_score(raw_score)
    alignment = horizon_alignment(c)
    dd = fnum(c.get("drawdown_from_90d_high_percent"))
    guardrails = extension_guardrails(raw_state, raw_score, dd)

    alignment_confirmed = (
        (raw_state == "SUPPORTIVE" and alignment["positive_count"] >= ALIGNMENT_REQUIRED)
        or (raw_state == "PRESSURED" and alignment["negative_count"] >= ALIGNMENT_REQUIRED)
    )
    if raw_state in {"SUPPORTIVE", "PRESSURED"} and not alignment_confirmed:
        guardrails.append({
            "code": "HORIZON_ALIGNMENT_NOT_CONFIRMED",
            "severity": "MODERATE",
            "message": f"Directional score is not confirmed by at least {ALIGNMENT_REQUIRED} of 4 market horizons.",
        })

    extension_block = any(x["code"] in {"DOWNSIDE_EXHAUSTION_RISK", "UPSIDE_EXTENSION_RISK"} for x in guardrails)
    directional_eligible = raw_state in {"SUPPORTIVE", "PRESSURED"} and alignment_confirmed and not extension_block
    effective_state = raw_state if directional_eligible or raw_state == "MIXED" else "MIXED"

    return {
        "score": raw_score,
        "state": effective_state,
        "raw_state": raw_state,
        "directional_eligible": directional_eligible,
        "components": components,
        "normalized_z": normalized_z,
        "volatility_scale_annualized_percent": vol,
        "alignment": alignment,
        "guardrails": guardrails,
        "completed_session": c.get("completed_session"),
        "basis": "COMPLETED_UTC_DAILY_CONTEXT_VOLATILITY_NORMALIZED",
    }


def reversal_exhaustion_risk(m: Dict[str, Any]) -> float:
    codes = {x.get("code") for x in m.get("guardrails", [])}
    if "DOWNSIDE_EXHAUSTION_RISK" in codes:
        return 95.0
    if "UPSIDE_EXTENSION_RISK" in codes:
        return 80.0
    raw = fnum(m.get("score"))
    if raw is not None and (raw <= 20.0 or raw >= 80.0):
        return 55.0
    return 20.0


def decision_risk_v02(symbol: str, asset: Dict[str, Any], evidence: Dict[str, Any], e: Dict[str, Any], m: Dict[str, Any]) -> Dict[str, Any]:
    c = asset.get("completed_daily_context") or {}
    vol = base.volatility_risk(fnum(c.get("realized_volatility_30d_annualized_percent")))
    dd = base.drawdown_risk(fnum(c.get("drawdown_from_90d_high_percent")))
    one_day = clamp(abs(fnum(c.get("return_1d_percent")) or 0.0) / 10.0 * 100.0)
    reg, relevant_events = base.regulatory_uncertainty(symbol, evidence)
    gap = base.evidence_gap_risk(e)
    conflict, conflict_count = base.horizon_conflict_risk(asset)
    reversal = reversal_exhaustion_risk(m)
    components = {
        "volatility": round(vol, 2),
        "drawdown": round(dd, 2),
        "one_day_shock": round(one_day, 2),
        "regulatory_uncertainty": round(reg, 2),
        "evidence_gap": round(gap, 2),
        "horizon_conflict": round(conflict, 2),
        "reversal_exhaustion": round(reversal, 2),
    }
    score = round(sum(components[k] * RISK_WEIGHTS_V02[k] for k in RISK_WEIGHTS_V02), 2)
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


def decision_readiness_v02(asset: Dict[str, Any], market: Dict[str, Any], m: Dict[str, Any], e: Dict[str, Any], risk: Dict[str, Any]) -> Dict[str, Any]:
    c = asset.get("completed_daily_context") or {}
    history = fnum(c.get("history_observations")) or 0.0
    quality = clamp(history / 90.0 * 100.0)
    fresh = base.market_freshness_score(asset, market)
    raw_clarity = base.clarity_score(m.get("score"))
    participation = base.participation_score(asset)
    alignment_score = float((m.get("alignment") or {}).get("score") or 30.0)

    components = {
        "market_data_quality": round(quality, 2),
        "market_freshness": round(fresh, 2),
        "evidence_readiness": round(float(e.get("score") or 0.0), 2),
        "directional_clarity": round(raw_clarity, 2),
        "market_participation": round(participation, 2),
        "horizon_alignment": round(alignment_score, 2),
    }
    base_score = round(sum(components[k] * READINESS_WEIGHTS_V02[k] for k in READINESS_WEIGHTS_V02), 2)

    risk_multiplier = {"LOW": 1.0, "MODERATE": 0.82, "HIGH": 0.60}.get(str(risk.get("state")), 0.75)
    codes = {x.get("code") for x in m.get("guardrails", [])}
    if codes & {"DOWNSIDE_EXHAUSTION_RISK", "UPSIDE_EXTENSION_RISK"}:
        guardrail_multiplier = 0.65
    elif "HORIZON_ALIGNMENT_NOT_CONFIRMED" in codes:
        guardrail_multiplier = 0.80
    else:
        guardrail_multiplier = 1.0
    final_score = round(base_score * risk_multiplier * guardrail_multiplier, 2)
    state = "READY_FOR_REVIEW" if final_score >= 70 else ("CONDITIONAL_REVIEW" if final_score >= 50 else "LOW_READINESS")
    directional_gate = "ELIGIBLE_FOR_SELECTIVE_REVIEW" if (
        m.get("directional_eligible") is True and final_score >= 70 and risk.get("state") != "HIGH"
    ) else "WATCH_ONLY"
    return {
        "score": final_score,
        "base_score_before_risk_guardrails": base_score,
        "state": state,
        "directional_gate": directional_gate,
        "components": components,
        "adjustments": {
            "risk_multiplier": risk_multiplier,
            "guardrail_multiplier": guardrail_multiplier,
            "readiness_is_not_profit_probability": True,
        },
    }


def counter_thesis_v02(symbol: str, asset: Dict[str, Any], m: Dict[str, Any], risk: Dict[str, Any], e: Dict[str, Any]) -> Dict[str, Any]:
    result = base.counter_thesis(symbol, asset, m.get("state"), risk, e)
    factors = list(result.get("factors") or [])
    for guard in m.get("guardrails", []):
        factors.append({"severity": guard.get("severity", "MODERATE"), "text": guard.get("message", "Market-structure guardrail is active.")})
    high = sum(1 for x in factors if x.get("severity") == "HIGH")
    strength = "HIGH" if high else ("MODERATE" if len(factors) >= 2 else ("LOW" if factors else "LIMITED"))
    return {"status": "ACTIVE" if factors else "LIMITED", "strength": strength, "factors": factors}


def reasoner_v02(m: Dict[str, Any], readiness: Dict[str, Any], risk: Dict[str, Any], counter: Dict[str, Any]) -> Dict[str, Any]:
    state = m.get("state")
    raw_state = m.get("raw_state")
    codes = {x.get("code") for x in m.get("guardrails", [])}
    risk_state = risk.get("state")

    if codes & {"DOWNSIDE_EXHAUSTION_RISK", "UPSIDE_EXTENSION_RISK"}:
        status = "REVERSAL_RISK_CONSTRAINED"
    elif "HORIZON_ALIGNMENT_NOT_CONFIRMED" in codes:
        status = "ALIGNMENT_NOT_CONFIRMED"
    elif risk_state == "HIGH":
        status = "RISK_CONSTRAINED"
    elif readiness.get("state") == "LOW_READINESS":
        status = "EVIDENCE_INCOMPLETE"
    elif state == "SUPPORTIVE":
        status = "STRUCTURE_SUPPORTIVE"
    elif state == "PRESSURED":
        status = "STRUCTURE_PRESSURED"
    else:
        status = "MIXED_MARKET_STRUCTURE"

    if risk_state == "HIGH" or readiness.get("state") == "LOW_READINESS":
        decision = "DEPRIORITIZE"
    elif readiness.get("directional_gate") == "ELIGIBLE_FOR_SELECTIVE_REVIEW" and counter.get("strength") != "HIGH":
        decision = "REVIEW_SELECTIVELY"
    else:
        decision = "WATCH"

    return {
        "status": status,
        "decision": decision,
        "market_view": state,
        "raw_market_view": raw_state,
        "directional_eligible": m.get("directional_eligible"),
        "readiness_state": readiness.get("state"),
        "directional_gate": readiness.get("directional_gate"),
        "risk_state": risk_state,
        "counter_thesis_strength": counter.get("strength"),
        "buy_sell": "NOT_GENERATED",
        "profit_probability": "NOT_ESTIMATED",
        "trade_execution": "OFF",
    }


def build_symbol_v02(asset: Dict[str, Any], market: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
    symbol = asset.get("symbol")
    m = market_structure_v02(asset)
    e = base.evidence_readiness(symbol, evidence)
    rk = decision_risk_v02(symbol, asset, evidence, e, m)
    rd = decision_readiness_v02(asset, market, m, e, rk)
    ct = counter_thesis_v02(symbol, asset, m, rk, e)
    ai = reasoner_v02(m, rd, rk, ct)
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
            "refinement": "Stage 11C v0.2 structural refinement after 11C.4 v0.1 diagnostic findings",
        },
    }


def main() -> int:
    backtest = json.loads(BACKTEST_PATH.read_text(encoding="utf-8"))
    if not str(backtest.get("status", "")).startswith("CRYPTO_BACKTEST_COMPLETE"):
        raise SystemExit("11C v0.2 refinement requires the completed 11C.4 v0.1 diagnostic artifact.")

    # Patch only the symbol builder; base.main keeps source validation and fail-closed behavior.
    base.build_symbol = build_symbol_v02
    code = base.main()

    artifact = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    artifact["version"] = "0.2"
    artifact["model_status"] = "EXPERIMENTAL_REFINED_PREVALIDATION"
    artifact["frozen"] = False
    artifact["refinement"] = {
        "decision": "REFINE_AFTER_11C4_V01",
        "source_backtest_generated_at": backtest.get("generated_at"),
        "source_backtest_model_methodology_sha256": (backtest.get("model_snapshot") or {}).get("methodology_sha256"),
        "consumed_historical_holdout": True,
        "optimization_policy": "STRUCTURAL_REFINEMENT_ONLY_NO_BEST_THRESHOLD_SELECTION",
        "changes": [
            "Volatility-normalized directional components replace fixed percent spans.",
            "At least 3 of 4 market horizons must align before a directional state is eligible.",
            "Extreme downside inside deep drawdown triggers a reversal/exhaustion guardrail.",
            "A symmetric upside-extension guardrail suppresses extreme trend confidence near the 90-day high.",
            "Decision Readiness is explicitly reduced by risk and active guardrails.",
            "Decision Risk includes reversal/exhaustion risk.",
        ],
    }
    artifact["methodology"] = {
        "market_structure": {
            "weights": MARKET_WEIGHTS_V02,
            "normalization": "Each percent input is divided by its expected horizon volatility derived from 30-day annualized realized volatility; z-like +/-2 maps to score 0/100.",
            "normalization_horizons_days": {"return_30d": 30, "close_vs_sma20": 20, "close_vs_sma50": 50, "return_7d": 7},
            "state_thresholds": {"supportive_gte": SUPPORTIVE_GTE, "pressured_lte": PRESSURED_LTE, "otherwise": "MIXED"},
            "horizon_alignment_required": f"{ALIGNMENT_REQUIRED}_OF_4",
            "direction_source": "COMPLETED_MARKET_DATA_ONLY",
            "directional_gate": "Raw SUPPORTIVE/PRESSURED becomes effective directional state only when alignment is confirmed and no extension/exhaustion guardrail blocks it.",
        },
        "exhaustion_guardrails": {
            "downside": "Raw PRESSURED score <=20 while 90-day drawdown <=-30% suppresses directional eligibility.",
            "upside": "Raw SUPPORTIVE score >=80 while within 5% of 90-day high suppresses directional eligibility.",
            "purpose": "Reduce false confidence at extreme extension; not selected by maximizing the consumed holdout.",
        },
        "evidence_readiness": {
            "weights": {"protocol_freshness": 0.45, "network_telemetry_readiness": 0.20, "regulatory_source_readiness": 0.35},
            "directional_policy": "Evidence readiness does not vote bullish/bearish.",
        },
        "decision_readiness": {
            "weights": READINESS_WEIGHTS_V02,
            "risk_multipliers": {"LOW": 1.0, "MODERATE": 0.82, "HIGH": 0.60},
            "guardrail_multipliers": {"extension_or_exhaustion": 0.65, "alignment_not_confirmed": 0.80, "none": 1.0},
            "thresholds": {"ready_for_review_gte": 70, "conditional_gte": 50},
        },
        "decision_risk": {
            "weights": RISK_WEIGHTS_V02,
            "thresholds": {"low_lt": 35, "high_gte": 65},
            "reversal_exhaustion_component": True,
        },
        "regulatory_policy": "Primary regulatory events can raise uncertainty/risk but are not assigned bullish/bearish direction.",
    }
    artifact.setdefault("guardrails", {}).update({
        "v01_diagnostic_holdout_is_consumed": True,
        "v02_requires_new_diagnostic_retest": True,
        "no_freeze_before_v02_retest_and_11c5": True,
        "model_is_unfrozen": True,
    })
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"11C v0.2 refinement: {artifact.get('status')}; symbols={len(artifact.get('symbols', []))}; frozen=false")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
