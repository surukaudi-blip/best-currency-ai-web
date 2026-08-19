#!/usr/bin/env python3
"""Stage 11C v0.4.1 — exact v0.1 core + D/W/M MTF + regime-aware Actionability.

This is a narrow refinement of v0.4.
- Canonical SUPPORTIVE/MIXED/PRESSURED remains exact v0.1 logic.
- Daily/Weekly/Monthly confirmation remains fixed and cannot reverse direction.
- Actionability adds explicit market-regime ceilings using raw completed-session
  30-day realized volatility and 90-day drawdown.
- No asset-specific rule, threshold search, BUY/SELL, or profit probability.
- Model remains unfrozen pending v0.4.1 diagnostic review and 11C.5.
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
LINEAGE_PATH = ROOT / "data" / "crypto-model-lineage.json"

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
        return {"relation": "CANONICAL_NOT_DIRECTIONAL", "relation_score": 45.0}
    if tf_state == canonical_state:
        return {"relation": "SUPPORTS_CANONICAL", "relation_score": 100.0}
    if tf_state == "MIXED":
        return {"relation": "NEUTRAL_TO_CANONICAL", "relation_score": 55.0}
    if tf_state in {"SUPPORTIVE", "PRESSURED"}:
        return {"relation": "OPPOSES_CANONICAL", "relation_score": 0.0}
    return {"relation": "UNAVAILABLE", "relation_score": 35.0}


def build_mtf(asset: Dict[str, Any], canonical_state: str) -> Dict[str, Any]:
    c = asset.get("completed_daily_context") or {}
    specs = {
        "daily": (fnum(c.get("return_1d_percent")), 6.0, 0.45),
        "weekly": (fnum(c.get("return_7d_percent")), 12.0, 0.35),
        "monthly": (fnum(c.get("return_30d_percent")), 25.0, 0.20),
    }
    frames: Dict[str, Any] = {}
    weighted = 0.0
    supports = opposes = neutral = 0
    for name, (value, span, weight) in specs.items():
        market_score = timeframe_score(value, span)
        tf_state = state(market_score)
        rel = relation(tf_state, canonical_state)
        frames[name] = {
            "timeframe": name,
            "return_percent": value,
            "score": market_score,
            "market_score": market_score,
            "state": tf_state,
            "span_percent": span,
            "weight": weight,
            "relation": rel["relation"],
            "relation_score": rel["relation_score"],
        }
        weighted += float(rel["relation_score"]) * weight
        if rel["relation"] == "SUPPORTS_CANONICAL":
            supports += 1
        elif rel["relation"] == "OPPOSES_CANONICAL":
            opposes += 1
        elif rel["relation"] == "NEUTRAL_TO_CANONICAL":
            neutral += 1
    alignment = round(weighted, 2)
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
        "methodology": "Confirmation only: 45% Daily + 35% Weekly + 20% Monthly canonical-relation score using completed UTC returns and fixed v0.1-style spans. MTF never reverses canonical v0.1 direction.",
        "canonical_state": canonical_state,
        "supporting_timeframes": supports,
        "opposing_timeframes": opposes,
        "neutral_timeframes": neutral,
        "constraints": constraints,
        "timeframes": frames,
    }


def volatility_regime(vol: Optional[float]) -> Dict[str, Any]:
    if vol is None:
        return {"state": "UNKNOWN_VOL", "ceiling": 55.0, "reason": "Missing 30-day realized volatility fails closed below SELECTIVE."}
    if vol < 45.0:
        return {"state": "LOW_VOL", "ceiling": 100.0, "reason": "Low-volatility regime does not impose an additional Actionability cap."}
    if vol < 75.0:
        return {"state": "MODERATE_VOL", "ceiling": 70.0, "reason": "Moderate volatility caps Actionability at SELECTIVE."}
    return {"state": "HIGH_VOL", "ceiling": 55.0, "reason": "High volatility caps Actionability below SELECTIVE."}


def drawdown_regime(drawdown: Optional[float]) -> Dict[str, Any]:
    if drawdown is None:
        return {"state": "UNKNOWN_DRAWDOWN", "ceiling": 60.0, "reason": "Missing 90-day drawdown caps Actionability at SELECTIVE."}
    if drawdown <= -30.0:
        return {"state": "STRESSED_DRAWDOWN", "ceiling": 60.0, "reason": "Stressed drawdown caps Actionability at SELECTIVE due to reversal/exhaustion risk."}
    if drawdown <= -15.0:
        return {"state": "MATERIAL_DRAWDOWN", "ceiling": 100.0, "reason": "Material drawdown is disclosed but does not independently block ACTIONABLE."}
    return {"state": "NORMAL_DRAWDOWN", "ceiling": 100.0, "reason": "Normal drawdown regime does not impose an additional Actionability cap."}


def regime_ceiling(symbol: Dict[str, Any], asset: Dict[str, Any]) -> Dict[str, Any]:
    risk = symbol.get("decision_risk") or {}
    components = risk.get("components") or {}
    risk_state = risk.get("state")
    risk_ceiling = {"LOW": 100.0, "MODERATE": 70.0, "HIGH": 45.0}.get(risk_state, 55.0)

    c = asset.get("completed_daily_context") or {}
    raw_vol = fnum(c.get("realized_volatility_30d_annualized_percent"))
    raw_dd = fnum(c.get("drawdown_from_90d_high_percent"))
    vol_reg = volatility_regime(raw_vol)
    dd_reg = drawdown_regime(raw_dd)

    ceilings = {
        "decision_risk_state": risk_ceiling,
        "volatility_regime": float(vol_reg["ceiling"]),
        "drawdown_regime": float(dd_reg["ceiling"]),
    }
    reasons = [f"Decision Risk is {risk_state or 'UNKNOWN'}.", vol_reg["reason"], dd_reg["reason"]]

    vol_component = fnum(components.get("volatility"))
    if vol_component is not None and vol_component >= 70:
        ceilings["legacy_volatility_risk"] = 55.0
        reasons.append("Legacy volatility-risk component is elevated.")
    dd_component = fnum(components.get("drawdown"))
    if dd_component is not None and dd_component >= 65:
        ceilings["legacy_drawdown_risk"] = 60.0
        reasons.append("Legacy drawdown-risk component is elevated.")
    reg_uncertainty = fnum(components.get("regulatory_uncertainty"))
    if reg_uncertainty is not None and reg_uncertainty >= 80:
        ceilings["regulatory_uncertainty"] = 70.0
        reasons.append("Asset-specific regulatory uncertainty caps readiness at SELECTIVE.")

    score = round(min(ceilings.values()), 2)
    limiter = min(ceilings, key=ceilings.get)
    return {
        "score": score,
        "limiter": limiter,
        "decision_risk_state": risk_state,
        "volatility_30d_annualized_percent": raw_vol,
        "volatility_regime": vol_reg["state"],
        "drawdown_from_90d_high_percent": raw_dd,
        "drawdown_regime": dd_reg["state"],
        "ceilings": ceilings,
        "reasons": reasons,
    }


def data_readiness(symbol: Dict[str, Any]) -> Dict[str, Any]:
    old = symbol.get("decision_readiness") or {}
    comps = old.get("components") or {}
    quality = fnum(comps.get("market_data_quality")) or 0.0
    freshness = fnum(comps.get("market_freshness")) or 0.0
    return {
        "score": round(min(quality, freshness), 2),
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
        "methodology": "80% MTF canonical alignment + 20% market participation; readiness only, not direction.",
    }


def actionability(symbol: Dict[str, Any], mtf: Dict[str, Any], asset: Dict[str, Any]) -> Dict[str, Any]:
    canonical = (symbol.get("market_structure") or {}).get("state")
    evidence = round(float((symbol.get("evidence_readiness") or {}).get("score") or 0.0), 2)
    regime = regime_ceiling(symbol, asset)
    asset_ready = asset_readiness(symbol, mtf)
    data = data_readiness(symbol)
    canonical_gate = 100.0 if canonical in {"SUPPORTIVE", "PRESSURED"} else 45.0
    dimensions = {
        "evidence_quality": {"score": evidence, "reason": "11B evidence readiness; evidence does not vote direction."},
        "regime_guardrail": regime,
        "asset_mtf_readiness": asset_ready,
        "data_readiness": data,
        "canonical_gate": {"score": canonical_gate, "reason": "Canonical v0.1 must be directional before Actionability can exceed FILTERED."},
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
    if regime["volatility_regime"] == "MODERATE_VOL":
        constraints.append("MODERATE_VOL_MAX_SELECTIVE")
    if regime["volatility_regime"] in {"HIGH_VOL", "UNKNOWN_VOL"}:
        constraints.append("HIGH_OR_UNKNOWN_VOL_FILTER")
    if regime["drawdown_regime"] == "STRESSED_DRAWDOWN":
        constraints.append("STRESSED_DRAWDOWN_MAX_SELECTIVE")
    if evidence < 60:
        constraints.append("EVIDENCE_BELOW_SELECTIVE_THRESHOLD")
    if data["score"] < 60:
        constraints.append("DATA_READINESS_LOW")
    if asset_ready["score"] < 60:
        constraints.append("MTF_ASSET_READINESS_LOW")

    return {
        "version": "CRYPTO_ACTIONABILITY_0.2",
        "role": "primary_operational_readiness_layer",
        "scope": "continuation_readiness",
        "score": score,
        "state": st,
        "decision": decision,
        "limiter": limiter,
        "thresholds": {"actionable": 80, "selective": 60, "filtered": 0},
        "methodology": "Forex-style minimum-ceiling Actionability with explicit volatility/drawdown regime caps. It filters priority but never reverses canonical v0.1 direction and is not a probability of profit.",
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
    lineage = json.loads(LINEAGE_PATH.read_text(encoding="utf-8"))
    expected_hash = ((lineage.get("canonical_direction") or {}).get("methodology_sha256"))
    if not expected_hash:
        raise SystemExit("Missing canonical v0.1 lineage hash; v0.4.1 fails closed.")

    # Rebuild exact v0.1 artifact first from current 11A + 11B inputs.
    code = base.main()
    artifact = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    market = json.loads(MARKET_PATH.read_text(encoding="utf-8"))
    current_hash = canonical_hash(artifact.get("methodology") or {})
    if current_hash != expected_hash:
        raise SystemExit(f"v0.1 lineage mismatch: expected {expected_hash}, got {current_hash}")

    market_by_symbol = {x.get("symbol"): x for x in market.get("assets", []) if x.get("symbol")}
    counts = {"ACTIONABLE": 0, "SELECTIVE": 0, "FILTERED": 0}
    regime_counts: Dict[str, int] = {}

    for symbol in artifact.get("symbols", []):
        asset = market_by_symbol.get(symbol.get("symbol")) or {}
        canonical = (symbol.get("market_structure") or {}).get("state")
        mtf = build_mtf(asset, canonical)
        act = actionability(symbol, mtf, asset)
        symbol["multi_timeframe_alignment"] = mtf
        symbol["actionability"] = act
        counts[act["state"]] = counts.get(act["state"], 0) + 1
        vr = ((act.get("dimensions") or {}).get("regime_guardrail") or {}).get("volatility_regime") or "UNKNOWN_VOL"
        regime_counts[vr] = regime_counts.get(vr, 0) + 1

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
        ai["actionability_limiter"] = act["limiter"]
        if canonical not in {"SUPPORTIVE", "PRESSURED"}:
            ai["status"], ai["decision"] = "V01_MIXED_STRUCTURE", "WATCH"
        elif act["state"] == "ACTIONABLE":
            ai["status"], ai["decision"] = "ACTIONABILITY_CONFIRMED", "EVALUATE_SETUP"
        elif act["state"] == "SELECTIVE":
            ai["status"], ai["decision"] = "ACTIONABILITY_SELECTIVE", "REVIEW_SELECTIVELY"
        else:
            ai["status"], ai["decision"] = "ACTIONABILITY_FILTERED", "DEPRIORITIZE"
        ai["buy_sell"] = "NOT_GENERATED"
        ai["profit_probability"] = "NOT_ESTIMATED"
        ai["trade_execution"] = "OFF"

    artifact["version"] = "0.4.1"
    artifact["model_status"] = "EXPERIMENTAL_V01_CORE_MTF_ACTIONABILITY_V041_PREVALIDATION"
    artifact["frozen"] = False
    artifact["canonical_direction_model"] = {
        "version": "0.1",
        "role": "CANONICAL_DIRECTIONAL_CORE",
        "methodology_sha256": current_hash,
        "policy": "Exact v0.1 Market Structure only; Actionability and MTF cannot reverse direction.",
    }
    artifact["multi_timeframe_policy"] = {
        "timeframes": ["daily", "weekly", "monthly"],
        "weights": {"daily": 0.45, "weekly": 0.35, "monthly": 0.20},
        "return_spans_percent": {"daily": 6.0, "weekly": 12.0, "monthly": 25.0},
        "state_thresholds": {"supportive_gte": 62, "pressured_lte": 38},
        "role": "CONFIRMATION_ONLY_NOT_DIRECTION_SOURCE",
    }
    artifact["actionability_policy"] = {
        "version": "CRYPTO_ACTIONABILITY_0.2",
        "thresholds": {"actionable": 80, "selective": 60, "filtered": 0},
        "ceiling_dimensions": ["evidence_quality", "regime_guardrail", "asset_mtf_readiness", "data_readiness", "canonical_gate"],
        "explicit_regime_caps": {
            "LOW_VOL": 100,
            "MODERATE_VOL": 70,
            "HIGH_VOL": 55,
            "UNKNOWN_VOL": 55,
            "STRESSED_DRAWDOWN": 60
        },
        "role": "PRIMARY_OPERATIONAL_READINESS_LAYER",
        "not_profit_probability": True,
        "does_not_reverse_canonical_direction": True,
        "no_asset_specific_rules": True,
    }
    artifact["summary"] = artifact.get("summary") or {}
    artifact["summary"]["actionability_counts"] = counts
    artifact["summary"]["volatility_regime_counts"] = regime_counts
    artifact["summary"]["symbols_total"] = len(artifact.get("symbols", []))
    artifact["refinement_history"] = {
        "lineage_file": "data/crypto-model-lineage.json",
        "v041_change_scope": "ACTIONABILITY_REGIME_GUARDRAIL_ONLY",
        "canonical_v01_changed": False,
        "mtf_formula_changed": False,
        "directional_thresholds_changed": False,
        "asset_specific_rules_added": False,
        "historical_windows_consumed": True,
    }
    artifact["guardrails"] = {
        "model_is_unfrozen": True,
        "v01_canonical_direction_preserved": True,
        "mtf_confirmation_only": True,
        "actionability_does_not_reverse_direction": True,
        "actionability_is_not_profit_probability": True,
        "no_asset_specific_rules": True,
        "no_buy_sell": True,
        "trade_execution": "OFF",
        "v041_diagnostic_required_before_11c5": True,
    }
    artifact["errors"] = artifact.get("errors") or []

    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Crypto v0.4.1 ready: v0.1 hash={current_hash}, actionability={counts}, regimes={regime_counts}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
