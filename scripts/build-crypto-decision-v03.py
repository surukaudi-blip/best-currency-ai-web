#!/usr/bin/env python3
"""Stage 11C v0.3 — hybrid Crypto Decision Intelligence.

Hybrid principle
----------------
- v0.1 contributes sensitivity to absolute momentum / SMA displacement.
- v0.2 contributes volatility-normalized structure and risk governance.
- The hybrid Market View is the symmetric 50/50 average of the two independently
  computed scores. This blend is fixed a priori and is not selected by historical
  optimization.
- Directional eligibility is based on model agreement. v0.3 intentionally removes
  the hard v0.2 3-of-4 gate and does not turn extreme scores into automatic Market
  View suppression. Extremity is handled as risk/readiness context instead.

The model remains EXPERIMENTAL, PRE-VALIDATION and UNFROZEN. It never emits BUY/SELL
or profit probability. A separate diagnostic retest and 11C.5 review are mandatory
before any freeze decision.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
V01_PATH = ROOT / "scripts" / "build-crypto-decision.py"
V02_PATH = ROOT / "scripts" / "build-crypto-decision-v02.py"
BT01_PATH = ROOT / "data" / "crypto-backtest.json"
BT02_PATH = ROOT / "data" / "crypto-backtest-v02.json"
OUTPUT_PATH = ROOT / "data" / "crypto-decision-intelligence.json"

spec1 = importlib.util.spec_from_file_location("crypto_decision_v01_hybrid", V01_PATH)
v01 = importlib.util.module_from_spec(spec1)
assert spec1 and spec1.loader
spec1.loader.exec_module(v01)

spec2 = importlib.util.spec_from_file_location("crypto_decision_v02_hybrid", V02_PATH)
v02 = importlib.util.module_from_spec(spec2)
assert spec2 and spec2.loader
spec2.loader.exec_module(v02)

HYBRID_WEIGHTS = {"v01_absolute": 0.50, "v02_volatility_normalized": 0.50}
SUPPORTIVE_GTE = 62.0
PRESSURED_LTE = 38.0

READINESS_WEIGHTS_V03 = {
    "market_data_quality": 0.18,
    "market_freshness": 0.15,
    "evidence_readiness": 0.22,
    "model_agreement": 0.20,
    "market_participation": 0.10,
    "horizon_alignment": 0.15,
}
RISK_WEIGHTS_V03 = dict(v02.RISK_WEIGHTS_V02)


def fnum(value: Any) -> Optional[float]:
    return v01.fnum(value)


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return v01.clamp(value, lo, hi)


def state_from_score(score: Optional[float]) -> str:
    if score is None:
        return "UNAVAILABLE"
    if score >= SUPPORTIVE_GTE:
        return "SUPPORTIVE"
    if score <= PRESSURED_LTE:
        return "PRESSURED"
    return "MIXED"


def model_agreement(v01_state: str, v02_state: str, hybrid_state: str) -> Dict[str, Any]:
    directional = {"SUPPORTIVE", "PRESSURED"}
    if v01_state in directional and v02_state in directional and v01_state != v02_state:
        return {"state": "DIRECT_CONFLICT", "score": 20.0, "supports_directional": False}
    if hybrid_state in directional:
        same = int(v01_state == hybrid_state) + int(v02_state == hybrid_state)
        if same == 2:
            return {"state": "STRONG_CONSENSUS", "score": 100.0, "supports_directional": True}
        if same == 1 and (v01_state == "MIXED" or v02_state == "MIXED"):
            return {"state": "PARTIAL_CONSENSUS", "score": 80.0, "supports_directional": True}
        return {"state": "UNCONFIRMED_DIRECTION", "score": 45.0, "supports_directional": False}
    if v01_state == v02_state == "MIXED":
        return {"state": "MIXED_CONSENSUS", "score": 75.0, "supports_directional": False}
    if v01_state == "MIXED" or v02_state == "MIXED":
        return {"state": "SOFT_DISAGREEMENT", "score": 60.0, "supports_directional": False}
    return {"state": "NEUTRAL", "score": 50.0, "supports_directional": False}


def extremity_context(score: Optional[float]) -> Dict[str, Any]:
    if score is None:
        return {"state": "UNKNOWN", "risk_score": 35.0}
    distance = abs(float(score) - 50.0)
    if score <= 20.0 or score >= 80.0:
        return {"state": "EXTREME", "risk_score": 70.0}
    if distance >= 20.0:
        return {"state": "ELEVATED", "risk_score": 45.0}
    return {"state": "NORMAL", "risk_score": 20.0}


def market_structure_v03(asset: Dict[str, Any]) -> Dict[str, Any]:
    m1 = v01.market_structure(asset)
    m2 = v02.market_structure_v02(asset)
    s1, s2 = fnum(m1.get("score")), fnum(m2.get("score"))
    if s1 is None and s2 is None:
        hybrid_score = None
    elif s1 is None:
        hybrid_score = round(float(s2), 2)
    elif s2 is None:
        hybrid_score = round(float(s1), 2)
    else:
        hybrid_score = round(s1 * HYBRID_WEIGHTS["v01_absolute"] + s2 * HYBRID_WEIGHTS["v02_volatility_normalized"], 2)

    hybrid_state = state_from_score(hybrid_score)
    v01_state = str(m1.get("state") or "UNAVAILABLE")
    v02_raw_state = str(m2.get("raw_state") or m2.get("state") or "UNAVAILABLE")
    agreement = model_agreement(v01_state, v02_raw_state, hybrid_state)
    direct_conflict = agreement["state"] == "DIRECT_CONFLICT"
    directional_eligible = hybrid_state in {"SUPPORTIVE", "PRESSURED"} and agreement["supports_directional"] and not direct_conflict
    effective_state = "MIXED" if direct_conflict else hybrid_state
    extreme = extremity_context(hybrid_score)

    guardrails: List[Dict[str, str]] = []
    if direct_conflict:
        guardrails.append({
            "code": "MODEL_DIRECTION_CONFLICT",
            "severity": "HIGH",
            "message": "v0.1 absolute structure and v0.2 volatility-normalized structure point in opposite directions; effective Market View is suppressed to MIXED.",
        })
    elif hybrid_state in {"SUPPORTIVE", "PRESSURED"} and not directional_eligible:
        guardrails.append({
            "code": "HYBRID_DIRECTION_NOT_CONFIRMED",
            "severity": "MODERATE",
            "message": "Hybrid score is directional but the two source models do not provide sufficient consensus for selective review.",
        })
    if extreme["state"] == "EXTREME":
        guardrails.append({
            "code": "STRUCTURE_EXTREMITY_RISK",
            "severity": "MODERATE",
            "message": "Hybrid score is extremely extended. The Market View remains descriptive, while Decision Risk and readiness carry the reversal/exhaustion concern.",
        })

    return {
        "score": hybrid_score,
        "state": effective_state,
        "raw_state": hybrid_state,
        "directional_eligible": directional_eligible,
        "hybrid": {
            "blend": HYBRID_WEIGHTS,
            "v01_absolute_score": s1,
            "v01_state": v01_state,
            "v02_volatility_normalized_score": s2,
            "v02_raw_state": v02_raw_state,
            "agreement": agreement,
            "extremity": extreme,
        },
        "components": {
            "v01_absolute": m1.get("components"),
            "v02_volatility_normalized": m2.get("components"),
        },
        "normalized_z": m2.get("normalized_z"),
        "volatility_scale_annualized_percent": m2.get("volatility_scale_annualized_percent"),
        "alignment": m2.get("alignment"),
        "guardrails": guardrails,
        "completed_session": m1.get("completed_session") or m2.get("completed_session"),
        "basis": "SYMMETRIC_50_50_V01_ABSOLUTE_PLUS_V02_VOLATILITY_NORMALIZED",
    }


def reversal_exhaustion_risk_v03(m: Dict[str, Any]) -> float:
    agreement = ((m.get("hybrid") or {}).get("agreement") or {}).get("state")
    extremity = ((m.get("hybrid") or {}).get("extremity") or {}).get("state")
    if agreement == "DIRECT_CONFLICT":
        return 90.0
    if extremity == "EXTREME":
        return 70.0
    if extremity == "ELEVATED":
        return 45.0
    return 20.0


def decision_risk_v03(symbol: str, asset: Dict[str, Any], evidence: Dict[str, Any], e: Dict[str, Any], m: Dict[str, Any]) -> Dict[str, Any]:
    c = asset.get("completed_daily_context") or {}
    vol = v01.volatility_risk(fnum(c.get("realized_volatility_30d_annualized_percent")))
    dd = v01.drawdown_risk(fnum(c.get("drawdown_from_90d_high_percent")))
    one_day = clamp(abs(fnum(c.get("return_1d_percent")) or 0.0) / 10.0 * 100.0)
    reg, relevant_events = v01.regulatory_uncertainty(symbol, evidence)
    gap = v01.evidence_gap_risk(e)
    conflict, conflict_count = v01.horizon_conflict_risk(asset)
    reversal = reversal_exhaustion_risk_v03(m)
    components = {
        "volatility": round(vol, 2),
        "drawdown": round(dd, 2),
        "one_day_shock": round(one_day, 2),
        "regulatory_uncertainty": round(reg, 2),
        "evidence_gap": round(gap, 2),
        "horizon_conflict": round(conflict, 2),
        "reversal_exhaustion": round(reversal, 2),
    }
    score = round(sum(components[k] * RISK_WEIGHTS_V03[k] for k in RISK_WEIGHTS_V03), 2)
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


def decision_readiness_v03(asset: Dict[str, Any], market: Dict[str, Any], m: Dict[str, Any], e: Dict[str, Any], risk: Dict[str, Any]) -> Dict[str, Any]:
    c = asset.get("completed_daily_context") or {}
    history = fnum(c.get("history_observations")) or 0.0
    quality = clamp(history / 90.0 * 100.0)
    fresh = v01.market_freshness_score(asset, market)
    participation = v01.participation_score(asset)
    agreement_score = float((((m.get("hybrid") or {}).get("agreement") or {}).get("score")) or 50.0)
    alignment_score = float((m.get("alignment") or {}).get("score") or 50.0)
    components = {
        "market_data_quality": round(quality, 2),
        "market_freshness": round(fresh, 2),
        "evidence_readiness": round(float(e.get("score") or 0.0), 2),
        "model_agreement": round(agreement_score, 2),
        "market_participation": round(participation, 2),
        "horizon_alignment": round(alignment_score, 2),
    }
    base_score = round(sum(components[k] * READINESS_WEIGHTS_V03[k] for k in READINESS_WEIGHTS_V03), 2)
    risk_multiplier = {"LOW": 1.0, "MODERATE": 0.84, "HIGH": 0.62}.get(str(risk.get("state")), 0.75)
    agreement_state = (((m.get("hybrid") or {}).get("agreement") or {}).get("state"))
    agreement_multiplier = 0.70 if agreement_state == "DIRECT_CONFLICT" else (0.90 if agreement_state == "UNCONFIRMED_DIRECTION" else 1.0)
    final_score = round(base_score * risk_multiplier * agreement_multiplier, 2)
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
            "agreement_multiplier": agreement_multiplier,
            "readiness_is_not_profit_probability": True,
        },
    }


def counter_thesis_v03(symbol: str, asset: Dict[str, Any], m: Dict[str, Any], risk: Dict[str, Any], e: Dict[str, Any]) -> Dict[str, Any]:
    result = v01.counter_thesis(symbol, asset, m.get("raw_state") or m.get("state"), risk, e)
    factors = list(result.get("factors") or [])
    for guard in m.get("guardrails", []):
        factors.append({"severity": guard.get("severity", "MODERATE"), "text": guard.get("message", "Hybrid market-structure guardrail is active.")})
    high = sum(1 for x in factors if x.get("severity") == "HIGH")
    strength = "HIGH" if high else ("MODERATE" if len(factors) >= 2 else ("LOW" if factors else "LIMITED"))
    return {"status": "ACTIVE" if factors else "LIMITED", "strength": strength, "factors": factors}


def reasoner_v03(m: Dict[str, Any], readiness: Dict[str, Any], risk: Dict[str, Any], counter: Dict[str, Any]) -> Dict[str, Any]:
    agreement_state = (((m.get("hybrid") or {}).get("agreement") or {}).get("state"))
    state = m.get("state")
    risk_state = risk.get("state")
    if agreement_state == "DIRECT_CONFLICT":
        status = "MODEL_CONFLICT"
    elif risk_state == "HIGH":
        status = "RISK_CONSTRAINED"
    elif readiness.get("state") == "LOW_READINESS":
        status = "EVIDENCE_INCOMPLETE"
    elif state == "SUPPORTIVE":
        status = "HYBRID_STRUCTURE_SUPPORTIVE"
    elif state == "PRESSURED":
        status = "HYBRID_STRUCTURE_PRESSURED"
    else:
        status = "HYBRID_MIXED_STRUCTURE"

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
        "raw_market_view": m.get("raw_state"),
        "directional_eligible": m.get("directional_eligible"),
        "readiness_state": readiness.get("state"),
        "directional_gate": readiness.get("directional_gate"),
        "risk_state": risk_state,
        "counter_thesis_strength": counter.get("strength"),
        "buy_sell": "NOT_GENERATED",
        "profit_probability": "NOT_ESTIMATED",
        "trade_execution": "OFF",
    }


def build_symbol_v03(asset: Dict[str, Any], market: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
    symbol = asset.get("symbol")
    m = market_structure_v03(asset)
    e = v01.evidence_readiness(symbol, evidence)
    rk = decision_risk_v03(symbol, asset, evidence, e, m)
    rd = decision_readiness_v03(asset, market, m, e, rk)
    ct = counter_thesis_v03(symbol, asset, m, rk, e)
    ai = reasoner_v03(m, rd, rk, ct)
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
            "hybrid": "Stage 11C v0.3 symmetric v0.1 absolute + v0.2 volatility-normalized decision model",
        },
    }


def main() -> int:
    bt01 = json.loads(BT01_PATH.read_text(encoding="utf-8"))
    bt02 = json.loads(BT02_PATH.read_text(encoding="utf-8"))
    if not str(bt01.get("status", "")).startswith("CRYPTO_BACKTEST_COMPLETE"):
        raise SystemExit("v0.3 hybrid requires completed v0.1 diagnostic backtest lineage.")
    if not str(bt02.get("status", "")).startswith("CRYPTO_V02_RETEST_COMPLETE"):
        raise SystemExit("v0.3 hybrid requires completed v0.2 diagnostic retest lineage.")

    v01.build_symbol = build_symbol_v03
    code = v01.main()
    artifact = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    artifact["version"] = "0.3"
    artifact["model_status"] = "EXPERIMENTAL_HYBRID_PREVALIDATION"
    artifact["frozen"] = False
    artifact["hybrid_refinement"] = {
        "decision": "HYBRID_AFTER_V01_V02_DIAGNOSTIC_COMPARISON",
        "source_v01_backtest_generated_at": bt01.get("generated_at"),
        "source_v02_retest_generated_at": bt02.get("generated_at"),
        "historical_windows_consumed": True,
        "optimization_policy": "SYMMETRIC_STRUCTURAL_BLEND_NO_BEST_WEIGHT_SEARCH",
        "changes": [
            "50/50 symmetric blend of v0.1 absolute and v0.2 volatility-normalized market scores.",
            "Model agreement replaces directional clarity as a Decision Readiness component.",
            "Hard 3-of-4 horizon suppression is removed; alignment remains explanatory/readiness context.",
            "Extreme structure is carried as reversal/exhaustion risk instead of automatic Market View suppression.",
            "Direct v0.1/v0.2 directional conflict fails closed to MIXED.",
        ],
    }
    artifact["methodology"] = {
        "market_structure": {
            "hybrid_weights": HYBRID_WEIGHTS,
            "v01_component": "Absolute percentage spans from v0.1.",
            "v02_component": "30-day realized-volatility-normalized score from v0.2.",
            "state_thresholds": {"supportive_gte": SUPPORTIVE_GTE, "pressured_lte": PRESSURED_LTE, "otherwise": "MIXED"},
            "directional_policy": "Directional eligibility requires hybrid direction plus non-conflicting v0.1/v0.2 model agreement; no automatic 3-of-4 suppression.",
            "direct_conflict_policy": "Opposite directional states between v0.1 and v0.2 suppress effective Market View to MIXED.",
            "extremity_policy": "Extreme hybrid score raises reversal/exhaustion risk but does not automatically suppress descriptive Market View.",
        },
        "decision_readiness": {
            "weights": READINESS_WEIGHTS_V03,
            "risk_multipliers": {"LOW": 1.0, "MODERATE": 0.84, "HIGH": 0.62},
            "agreement_multipliers": {"direct_conflict": 0.70, "unconfirmed_direction": 0.90, "otherwise": 1.0},
            "thresholds": {"ready_for_review_gte": 70, "conditional_gte": 50},
        },
        "decision_risk": {
            "weights": RISK_WEIGHTS_V03,
            "thresholds": {"low_lt": 35, "high_gte": 65},
            "reversal_exhaustion_policy": "Extreme hybrid score or direct model conflict raises risk; it is not a directional vote.",
        },
        "evidence_readiness": {
            "weights": {"protocol_freshness": 0.45, "network_telemetry_readiness": 0.20, "regulatory_source_readiness": 0.35},
            "directional_policy": "Evidence readiness does not vote bullish/bearish.",
        },
        "regulatory_policy": "Primary regulatory events can raise uncertainty/risk but are not assigned bullish/bearish direction.",
    }
    artifact.setdefault("guardrails", {}).update({
        "v01_and_v02_history_are_consumed_diagnostics": True,
        "v03_requires_separate_diagnostic_retest": True,
        "no_freeze_before_v03_retest_and_11c5": True,
    })
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
