#!/usr/bin/env python3
"""Stage 11C v0.4 — v0.1 canonical core + D/W/M MTF + Actionability.

Design principles
-----------------
1. Canonical direction comes from the original v0.1 Market Structure engine unchanged.
2. Daily / Weekly / Monthly are confirmation layers only; they never reverse canonical direction.
3. Actionability follows the Forex-style interpretable ceiling pattern:
   evidence quality, regime guardrail, asset/MTF readiness, data readiness, canonical gate.
4. Actionability is continuation/readiness context, not win-rate or profit probability.
5. No BUY/SELL instruction and trade execution remains OFF.
6. Model remains unfrozen until diagnostic backtest and 11C.5 Pre-Freeze Cross-Check pass.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = ROOT / "scripts" / "build-crypto-decision.py"
MARKET_PATH = ROOT / "data" / "crypto-market-data.json"
OUTPUT_PATH = ROOT / "data" / "crypto-decision-intelligence.json"
V01_BACKTEST_PATH = ROOT / "data" / "crypto-backtest.json"

spec = importlib.util.spec_from_file_location("crypto_decision_v01", BASE_SCRIPT)
base = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(base)


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def fnum(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def state(score: Optional[float]) -> str:
    if score is None:
        return "UNAVAILABLE"
    if score >= 62.0:
        return "SUPPORTIVE"
    if score <= 38.0:
        return "PRESSURED"
    return "MIXED"


def timeframe_score(value: Optional[float], span: float) -> Optional[float]:
    return base.signed_score(value, span)


def relation(tf_state: str, canonical_state: str) -> Dict[str, Any]:
    if canonical_state not in {"SUPPORTIVE", "PRESSURED"}:
        return {"relation": "CANONICAL_NOT_DIRECTIONAL", "score": 45.0}
    if tf_state == canonical_state:
        return {"relation": "SUPPORTS_CANONICAL", "score": 100.0}
    if tf_state == "MIXED":
        return {"relation": "NEUTRAL_TO_CANONICAL", "score": 55.0}
    if tf_state in {"SUPPORTIVE", "PRESSURED"}:
        return {"relation": "OPPOSES_CANONICAL", "score": 0.0}
    return {"relation": "UNAVAILABLE", "score": 35.0}


def build_mtf(asset: Dict[str, Any], canonical_state: str) -> Dict[str, Any]:
    c = asset.get("completed_daily_context") or {}
    specs = {
        "daily": (fnum(c.get("return_1d_percent")), 6.0, 0.45),
        "weekly": (fnum(c.get("return_7d_percent")), 12.0, 0.35),
        "monthly": (fnum(c.get("return_30d_percent")), 25.0, 0.20),
    }
    frames: Dict[str, Any] = {}
    weighted = 0.0
    total = 0.0
    supports = 0
    opposes = 0
    mixed = 0
    for name, (value, span, weight) in specs.items():
        sc = timeframe_score(value, span)
        st = state(sc)
        rel = relation(st, canonical_state)
        frames[name] = {
            "timeframe": name,
            "return_percent": value,
            "score": sc,
            "state": st,
            "span_percent": span,
            "weight": weight,
            **rel,
        }
        weighted += float(rel["score"]) * weight
        total += weight
        if rel["relation"] == "SUPPORTS_CANONICAL":
            supports += 1
        elif rel["relation"] == "OPPOSES_CANONICAL":
            opposes += 1
        elif rel["relation"] == "NEUTRAL_TO_CANONICAL":
            mixed += 1
    alignment = round(weighted / total, 2) if total else 0.0
    align_state = "STRONG" if alignment >= 80 else ("MODERATE" if alignment >= 60 else "LOW")
    constraints = []
    if canonical_state not in {"SUPPORTIVE", "PRESSURED"}:
        constraints.append("CANONICAL_V01_MIXED")
    if frames["weekly"]["relation"] == "OPPOSES_CANONICAL":
        constraints.append("WEEKLY_OPPOSES_CANONICAL")
    if frames["monthly"]["relation"] == "OPPOSES_CANONICAL":
        constraints.append("MONTHLY_OPPOSES_CANONICAL")
    if alignment < 60:
        constraints.append("MTF_ALIGNMENT_LOW")
    return {
        "score": alignment,
        "state": align_state,
        "primary_timeframe": "daily",
        "methodology": "Forex-inspired confirmation layer: Daily/Weekly/Monthly completed UTC returns are mapped with fixed absolute v0.1-style spans; 45% Daily + 35% Weekly + 20% Monthly canonical-relation score. MTF never reverses the v0.1 canonical Market View.",
        "canonical_state": canonical_state,
        "supporting_timeframes": supports,
        "opposing_timeframes": opposes,
        "neutral_timeframes": mixed,
        "constraints": constraints,
        "timeframes": frames,
    }


def regime_ceiling(symbol: Dict[str, Any]) -> Dict[str, Any]:
    risk = symbol.get("decision_risk") or {}
    components = risk.get("components") or {}
    risk_state = risk.get("state")
    ceiling = {"LOW": 100.0, "MODERATE": 70.0, "HIGH": 45.0}.get(risk_state, 55.0)
    reasons = [f"Decision Risk is {risk_state or 'UNKNOWN'}." ]
    if fnum(components.get("volatility")) is not None and float(components.get("volatility")) >= 70:
        ceiling = min(ceiling, 55.0)
        reasons.append("Volatility risk is elevated, so continuation readiness is capped.")
    if fnum(components.get("drawdown")) is not None and float(components.get("drawdown")) >= 65:
        ceiling = min(ceiling, 60.0)
        reasons.append("Deep drawdown raises reversal/exhaustion risk.")
    if fnum(components.get("regulatory_uncertainty")) is not None and float(components.get("regulatory_uncertainty")) >= 80:
        ceiling = min(ceiling, 70.0)
        reasons.append("Asset-specific regulatory uncertainty caps readiness.")
    return {"score": round(ceiling, 2), "reasons": reasons}


def data_readiness(symbol: Dict[str, Any]) -> Dict[str, Any]:
    old = symbol.get("decision_readiness") or {}
    comps = old.get("components") or {}
    quality = fnum(comps.get("market_data_quality")) or 0.0
    freshness = fnum(comps.get("market_freshness")) or 0.0
    score = round(min(quality, freshness), 2)
    return {
        "score": score,
        "market_data_quality": quality,
        "market_freshness": freshness,
        "reason": "Minimum of market-data quality and completed-session freshness.",
    }


def asset_readiness(symbol: Dict[str, Any], mtf: Dict[str, Any]) -> Dict[str, Any]:
    old = symbol.get("decision_readiness") or {}
    participation = fnum((old.get("components") or {}).get("market_participation")) or 45.0
    score = round(0.80 * float(mtf.get("score") or 0.0) + 0.20 * participation, 2)
    return {
        "score": score,
        "mtf_alignment": mtf.get("score"),
        "market_participation": participation,
        "methodology": "80% MTF canonical alignment + 20% market participation; this is a readiness ceiling, not a directional score.",
    }


def actionability(symbol: Dict[str, Any], mtf: Dict[str, Any]) -> Dict[str, Any]:
    canonical = (symbol.get("market_structure") or {}).get("state")
    evidence = round(float((symbol.get("evidence_readiness") or {}).get("score") or 0.0), 2)
    regime = regime_ceiling(symbol)
    asset = asset_readiness(symbol, mtf)
    data = data_readiness(symbol)
    canonical_gate = 100.0 if canonical in {"SUPPORTIVE", "PRESSURED"} else 45.0
    dimensions = {
        "evidence_quality": {"score": evidence, "reason": "Stage 11B official/protocol/network evidence readiness; evidence does not vote direction."},
        "regime_guardrail": regime,
        "asset_mtf_readiness": asset,
        "data_readiness": data,
        "canonical_gate": {"score": canonical_gate, "reason": "v0.1 canonical Market View must be directional before Actionability can become actionable."},
    }
    ceilings = {k: float(v.get("score") or 0.0) for k, v in dimensions.items()}
    score = round(min(ceilings.values()), 2)
    limiter = min(ceilings, key=ceilings.get)
    if score >= 80:
        st, decision = "ACTIONABLE", "EVALUATE_SETUP"
    elif score >= 60:
        st, decision = "SELECTIVE", "REVIEW_SELECTIVELY"
    else:
        st, decision = "FILTERED", "DEPRIORITIZE"
    constraints = list(mtf.get("constraints") or [])
    if regime["score"] < 80:
        constraints.append("REGIME_GUARDRAIL")
    if evidence < 60:
        constraints.append("EVIDENCE_BELOW_SELECTIVE_THRESHOLD")
    if data["score"] < 60:
        constraints.append("DATA_READINESS_LOW")
    if asset["score"] < 60:
        constraints.append("MTF_ASSET_READINESS_LOW")
    return {
        "version": "CRYPTO_ACTIONABILITY_0.1",
        "role": "primary_operational_readiness_layer",
        "scope": "continuation_readiness",
        "score": score,
        "state": st,
        "decision": decision,
        "limiter": limiter,
        "thresholds": {"actionable": 80, "selective": 60, "filtered": 0},
        "methodology": "Forex-style interpretable ceiling model: Actionability is the minimum of evidence quality, regime guardrail, asset/MTF readiness, data readiness, and the v0.1 canonical-direction gate. It never reverses canonical direction and is not a probability of profit.",
        "dimensions": dimensions,
        "constraints": sorted(set(constraints)),
        "signal": {
            "asset": symbol.get("symbol"),
            "canonical_market_view": canonical,
            "canonical_score": (symbol.get("market_structure") or {}).get("score"),
        },
        "buy_sell": "NOT_GENERATED",
        "profit_probability": "NOT_ESTIMATED",
        "trade_execution": "OFF",
    }


def main() -> int:
    # Rebuild exact original v0.1 artifact first.
    code = base.main()
    artifact = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    market = json.loads(MARKET_PATH.read_text(encoding="utf-8"))
    v01_bt = json.loads(V01_BACKTEST_PATH.read_text(encoding="utf-8"))

    current_v01_hash = canonical_hash(artifact.get("methodology") or {})
    expected_v01_hash = ((v01_bt.get("model_snapshot") or {}).get("methodology_sha256"))
    if not expected_v01_hash or current_v01_hash != expected_v01_hash:
        raise SystemExit(f"v0.1 lineage mismatch: expected {expected_v01_hash}, got {current_v01_hash}")

    market_by_symbol = {x.get("symbol"): x for x in market.get("assets", []) if x.get("symbol")}
    actionability_counts = {"ACTIONABLE": 0, "SELECTIVE": 0, "FILTERED": 0}

    for symbol in artifact.get("symbols", []):
        asset = market_by_symbol.get(symbol.get("symbol")) or {}
        canonical = (symbol.get("market_structure") or {}).get("state")
        mtf = build_mtf(asset, canonical)
        act = actionability(symbol, mtf)
        symbol["multi_timeframe_alignment"] = mtf
        symbol["actionability"] = act
        actionability_counts[act["state"]] = actionability_counts.get(act["state"], 0) + 1

        # Preserve original v0.1 readiness for audit; Actionability becomes the operational layer.
        symbol["v01_decision_readiness"] = symbol.get("decision_readiness")
        symbol["decision_readiness"] = {
            "score": act["score"],
            "state": act["state"],
            "decision": act["decision"],
            "role": "ACTIONABILITY_ALIAS_FOR_OPERATIONAL_READINESS",
            "readiness_is_not_profit_probability": True,
        }
        ai = symbol.setdefault("ai_decision_reasoner", {})
        ai["canonical_market_view"] = canonical
        ai["canonical_direction_source"] = "V0_1_ABSOLUTE_CORE"
        ai["mtf_alignment_state"] = mtf["state"]
        ai["mtf_alignment_score"] = mtf["score"]
        ai["actionability_state"] = act["state"]
        ai["actionability_score"] = act["score"]
        if canonical not in {"SUPPORTIVE", "PRESSURED"}:
            ai["status"] = "V01_MIXED_STRUCTURE"
            ai["decision"] = "WATCH"
        elif act["state"] == "ACTIONABLE":
            ai["status"] = "ACTIONABILITY_CONFIRMED"
            ai["decision"] = "EVALUATE_SETUP"
        elif act["state"] == "SELECTIVE":
            ai["status"] = "ACTIONABILITY_SELECTIVE"
            ai["decision"] = "REVIEW_SELECTIVELY"
        else:
            ai["status"] = "ACTIONABILITY_FILTERED"
            ai["decision"] = "DEPRIORITIZE"
        ai["buy_sell"] = "NOT_GENERATED"
        ai["profit_probability"] = "NOT_ESTIMATED"
        ai["trade_execution"] = "OFF"

    artifact["version"] = "0.4"
    artifact["model_status"] = "EXPERIMENTAL_V01_CORE_MTF_ACTIONABILITY_PREVALIDATION"
    artifact["frozen"] = False
    artifact["canonical_direction_model"] = {
        "version": "0.1",
        "role": "CANONICAL_DIRECTIONAL_CORE",
        "methodology_sha256": current_v01_hash,
        "historical_diagnostic_status": "BEST_DIRECTIONAL_CORE_AMONG_V01_V02_V03_ON_CONSUMED_WINDOW",
        "policy": "Canonical Market View is rebuilt from exact v0.1 logic; MTF and Actionability may filter priority but may not reverse direction.",
    }
    artifact["multi_timeframe_policy"] = {
        "timeframes": ["daily", "weekly", "monthly"],
        "weights": {"daily": 0.45, "weekly": 0.35, "monthly": 0.20},
        "return_spans_percent": {"daily": 6.0, "weekly": 12.0, "monthly": 25.0},
        "state_thresholds": {"supportive_gte": 62, "pressured_lte": 38},
        "role": "CONFIRMATION_ONLY_NOT_DIRECTION_SOURCE",
    }
    artifact["actionability_policy"] = {
        "version": "CRYPTO_ACTIONABILITY_0.1",
        "thresholds": {"actionable": 80, "selective": 60, "filtered": 0},
        "ceiling_dimensions": ["evidence_quality", "regime_guardrail", "asset_mtf_readiness", "data_readiness", "canonical_gate"],
        "role": "PRIMARY_OPERATIONAL_READINESS_LAYER",
        "not_profit_probability": True,
        "does_not_reverse_canonical_direction": True,
    }
    artifact["summary"] = artifact.get("summary") or {}
    artifact["summary"]["actionability_counts"] = actionability_counts
    artifact["summary"]["symbols_total"] = len(artifact.get("symbols", []))
    artifact["refinement_history"] = {
        "v01": "Best directional coverage/hit-rate balance on consumed 365-day diagnostic window.",
        "v02": "Volatility-normalized refinement was too conservative and did not improve overall directional hit rate.",
        "v03": "50/50 hybrid restored coverage but did not improve v0.1 accuracy and worsened extremity miss rate.",
        "v04": "Returns canonical direction to exact v0.1 and moves MTF/risk/evidence into a Forex-style Actionability quality overlay.",
        "historical_windows_consumed": True,
    }
    artifact["guardrails"] = {
        "model_is_unfrozen": True,
        "v01_canonical_direction_preserved": True,
        "mtf_confirmation_only": True,
        "actionability_does_not_reverse_direction": True,
        "actionability_is_not_profit_probability": True,
        "no_buy_sell": True,
        "trade_execution": "OFF",
        "backtest_required_before_11c5": True,
    }

    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Crypto v0.4 ready: v0.1 hash={current_v01_hash}, actionability={actionability_counts}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
