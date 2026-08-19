#!/usr/bin/env python3
"""Stage 11C.4 v0.4.1 diagnostic — regime-aware Actionability selection test.

The historical 365-day window is already consumed diagnostic evidence.
This test does NOT retune v0.1 direction, D/W/M spans/weights, or 62/38 thresholds.
It compares the prior v0.4 market-only Actionability proxy with v0.4.1's explicit
volatility/drawdown regime caps. Protocol/regulatory/network history is not backfilled.
"""

from __future__ import annotations

import importlib.util
import json
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = ROOT / "scripts" / "build-crypto-backtest.py"
UNIVERSE_PATH = ROOT / "data" / "crypto-universe.json"
DECISION_PATH = ROOT / "data" / "crypto-decision-intelligence.json"
LINEAGE_PATH = ROOT / "data" / "crypto-model-lineage.json"
OUTPUT_PATH = ROOT / "data" / "crypto-backtest-v041.json"

spec = importlib.util.spec_from_file_location("crypto_bt_base", BASE_SCRIPT)
bt = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(bt)

HISTORY_DAYS = 365
WARMUP_DAYS = 90
FORWARD_HORIZONS = (1, 3, 7)
V01_WEIGHTS = {
    "return_30d": 0.30,
    "close_vs_sma20": 0.25,
    "close_vs_sma50": 0.30,
    "return_7d": 0.15,
}


def fnum(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def canonical_v01(prices: List[float], i: int) -> Dict[str, Any]:
    latest = prices[i]
    r7 = bt.pct_return(latest, prices[i - 7]) if i >= 7 else None
    r30 = bt.pct_return(latest, prices[i - 30]) if i >= 30 else None
    sma20 = bt.mean(prices[i - 19 : i + 1]) if i >= 19 else None
    sma50 = bt.mean(prices[i - 49 : i + 1]) if i >= 49 else None
    vs20 = bt.pct_return(latest, sma20) if sma20 not in (None, 0) else None
    vs50 = bt.pct_return(latest, sma50) if sma50 not in (None, 0) else None
    comps = {
        "return_30d": bt.signed_score(r30, 25.0),
        "close_vs_sma20": bt.signed_score(vs20, 12.0),
        "close_vs_sma50": bt.signed_score(vs50, 20.0),
        "return_7d": bt.signed_score(r7, 12.0),
    }
    score = bt.weighted_available([(comps[k], V01_WEIGHTS[k]) for k in V01_WEIGHTS])
    st = bt.state_for(score, 62.0, 38.0)
    return {
        "score": bt.safe_round(score),
        "state": st,
        "return_7d": r7,
        "return_30d": r30,
        "close_vs_sma20": vs20,
        "close_vs_sma50": vs50,
    }


def relation_score(tf_state: str, canonical: str) -> Tuple[str, float]:
    if canonical not in {"SUPPORTIVE", "PRESSURED"}:
        return "CANONICAL_NOT_DIRECTIONAL", 45.0
    if tf_state == canonical:
        return "SUPPORTS_CANONICAL", 100.0
    if tf_state == "MIXED":
        return "NEUTRAL_TO_CANONICAL", 55.0
    if tf_state in {"SUPPORTIVE", "PRESSURED"}:
        return "OPPOSES_CANONICAL", 0.0
    return "UNAVAILABLE", 35.0


def mtf(prices: List[float], i: int, canonical: str) -> Dict[str, Any]:
    latest = prices[i]
    values = {
        "daily": (bt.pct_return(latest, prices[i - 1]) if i >= 1 else None, 6.0, 0.45),
        "weekly": (bt.pct_return(latest, prices[i - 7]) if i >= 7 else None, 12.0, 0.35),
        "monthly": (bt.pct_return(latest, prices[i - 30]) if i >= 30 else None, 25.0, 0.20),
    }
    frames = {}
    total = 0.0
    for name, (value, span, weight) in values.items():
        market_score = bt.signed_score(value, span)
        tf_state = bt.state_for(market_score, 62.0, 38.0)
        relation, rscore = relation_score(tf_state, canonical)
        frames[name] = {
            "return_percent": bt.safe_round(value, 4),
            "market_score": bt.safe_round(market_score),
            "state": tf_state,
            "relation": relation,
            "relation_score": rscore,
            "weight": weight,
        }
        total += rscore * weight
    alignment = round(total, 2)
    return {
        "score": alignment,
        "state": "STRONG" if alignment >= 80 else ("MODERATE" if alignment >= 60 else "LOW"),
        "frames": frames,
    }


def base_market_risk(prices: List[float], i: int, canonical: Dict[str, Any]) -> Dict[str, Any]:
    vol30 = bt.volatility_30(prices, i)
    dd90 = bt.drawdown_90(prices, i)
    r1 = bt.pct_return(prices[i], prices[i - 1]) if i >= 1 else None
    conflict_count, conflict_risk = bt.horizon_conflict(
        canonical.get("return_7d"),
        canonical.get("return_30d"),
        canonical.get("close_vs_sma20"),
        canonical.get("close_vs_sma50"),
    )
    one_day = bt.clamp(abs(r1 or 0.0) / 10.0 * 100.0)
    vol_risk = bt.volatility_risk(vol30)
    dd_risk = bt.drawdown_risk(dd90)
    risk = bt.weighted_available([
        (vol_risk, 0.30),
        (dd_risk, 0.20),
        (one_day, 0.15),
        (conflict_risk, 0.10),
    ])
    risk_state = "LOW" if (risk if risk is not None else 100) < 35 else ("MODERATE" if (risk if risk is not None else 100) < 65 else "HIGH")
    return {
        "risk_proxy": bt.safe_round(risk),
        "risk_state": risk_state,
        "volatility_30d": bt.safe_round(vol30, 4),
        "drawdown_90d": bt.safe_round(dd90, 4),
        "volatility_risk": vol_risk,
        "drawdown_risk": dd_risk,
        "conflict_count": conflict_count,
        "vol_regime": bt.vol_regime(vol30),
        "drawdown_regime": bt.drawdown_regime(dd90),
    }


def v04_regime_ceiling(risk: Dict[str, Any]) -> float:
    ceiling = {"LOW": 100.0, "MODERATE": 70.0, "HIGH": 45.0}.get(risk.get("risk_state"), 55.0)
    if float(risk.get("volatility_risk") or 0.0) >= 70:
        ceiling = min(ceiling, 55.0)
    if float(risk.get("drawdown_risk") or 0.0) >= 65:
        ceiling = min(ceiling, 60.0)
    return round(ceiling, 2)


def v041_regime_ceiling(risk: Dict[str, Any]) -> Tuple[float, str]:
    ceilings = {"v04_base": v04_regime_ceiling(risk)}
    vol = fnum(risk.get("volatility_30d"))
    dd = fnum(risk.get("drawdown_90d"))
    if vol is None:
        ceilings["UNKNOWN_VOL"] = 55.0
    elif vol < 45.0:
        ceilings["LOW_VOL"] = 100.0
    elif vol < 75.0:
        ceilings["MODERATE_VOL"] = 70.0
    else:
        ceilings["HIGH_VOL"] = 55.0
    if dd is None:
        ceilings["UNKNOWN_DRAWDOWN"] = 60.0
    elif dd <= -30.0:
        ceilings["STRESSED_DRAWDOWN"] = 60.0
    elif dd <= -15.0:
        ceilings["MATERIAL_DRAWDOWN"] = 100.0
    else:
        ceilings["NORMAL_DRAWDOWN"] = 100.0
    limiter = min(ceilings, key=ceilings.get)
    return round(min(ceilings.values()), 2), limiter


def market_participation(volumes: List[Optional[float]], i: int) -> float:
    return float(bt.participation_score(volumes, i) or 45.0)


def actionability_state(score: float) -> str:
    if score >= 80:
        return "ACTIONABLE"
    if score >= 60:
        return "SELECTIVE"
    return "FILTERED"


def actionability(canonical: Dict[str, Any], mtf_data: Dict[str, Any], risk: Dict[str, Any], participation: float, version: str) -> Dict[str, Any]:
    canonical_gate = 100.0 if canonical.get("state") in {"SUPPORTIVE", "PRESSURED"} else 45.0
    asset_readiness = round(0.80 * float(mtf_data.get("score") or 0.0) + 0.20 * participation, 2)
    if version == "v04":
        regime_score, regime_limiter = v04_regime_ceiling(risk), "V04_MARKET_RISK"
    else:
        regime_score, regime_limiter = v041_regime_ceiling(risk)
    ceilings = {
        "regime_guardrail": regime_score,
        "asset_mtf_readiness": asset_readiness,
        "canonical_gate": canonical_gate,
    }
    score = round(min(ceilings.values()), 2)
    limiter = min(ceilings, key=ceilings.get)
    return {
        "score": score,
        "state": actionability_state(score),
        "limiter": limiter,
        "regime_limiter": regime_limiter,
        "asset_mtf_readiness": asset_readiness,
        "market_participation": participation,
        "ceilings": ceilings,
    }


def build_asset_rows(asset: Dict[str, Any]) -> List[Dict[str, Any]]:
    chart = bt.fetch_json(
        f"/coins/{urllib.parse.quote(asset['id'])}/market_chart",
        {"vs_currency": "usd", "days": HISTORY_DAYS, "precision": "full"},
    )
    pmap = bt.daily_map(chart.get("prices") or [])
    vmap = bt.daily_map(chart.get("total_volumes") or [])
    dates = sorted(pmap)
    prices = [pmap[d] for d in dates]
    volumes = [vmap.get(d) for d in dates]
    if len(dates) < 150:
        raise ValueError(f"{asset['symbol']}: insufficient historical observations")
    rows: List[Dict[str, Any]] = []
    last_anchor = len(dates) - max(FORWARD_HORIZONS) - 1
    for i in range(WARMUP_DAYS, last_anchor + 1):
        can = canonical_v01(prices, i)
        mtf_data = mtf(prices, i, can["state"])
        risk = base_market_risk(prices, i, can)
        part = market_participation(volumes, i)
        act04 = actionability(can, mtf_data, risk, part, "v04")
        act041 = actionability(can, mtf_data, risk, part, "v041")
        sign = 1 if can["state"] == "SUPPORTIVE" else (-1 if can["state"] == "PRESSURED" else 0)
        row = {
            "date": dates[i],
            "asset": asset["symbol"],
            "canonical_score": can["score"],
            "canonical_state": can["state"],
            "mtf_score": mtf_data["score"],
            "mtf_state": mtf_data["state"],
            "v04_actionability_score": act04["score"],
            "v04_actionability_state": act04["state"],
            "v041_actionability_score": act041["score"],
            "v041_actionability_state": act041["state"],
            "v041_limiter": act041["limiter"],
            "v041_regime_limiter": act041["regime_limiter"],
            "market_risk_state": risk["risk_state"],
            "vol_regime": risk["vol_regime"],
            "drawdown_regime": risk["drawdown_regime"],
            "volatility_30d": risk["volatility_30d"],
            "drawdown_90d": risk["drawdown_90d"],
        }
        for h in FORWARD_HORIZONS:
            fwd = bt.pct_return(prices[i + h], prices[i])
            directional = fwd * sign if sign else None
            row[f"dir_{h}d"] = bt.safe_round(directional, 4)
            row[f"hit_{h}d"] = directional > 0 if directional is not None else None
        rows.append(row)
    return rows


def metric(rows: List[Dict[str, Any]], predicate) -> Dict[str, Any]:
    directional = [r for r in rows if r.get("canonical_state") in {"SUPPORTIVE", "PRESSURED"}]
    selected = [r for r in directional if predicate(r)]
    out = {
        "observations": len(selected),
        "coverage_percent_of_all": round(len(selected) / len(rows) * 100.0, 2) if rows else None,
        "retention_percent_of_v01_directional": round(len(selected) / len(directional) * 100.0, 2) if directional else None,
    }
    for h in FORWARD_HORIZONS:
        valid = [r for r in selected if r.get(f"hit_{h}d") is not None]
        hits = sum(1 for r in valid if r.get(f"hit_{h}d") is True)
        drets = [float(r[f"dir_{h}d"]) for r in valid if r.get(f"dir_{h}d") is not None]
        out[f"hit_rate_{h}d_percent"] = round(hits / len(valid) * 100.0, 2) if valid else None
        out[f"avg_directional_return_{h}d_percent"] = round(sum(drets) / len(drets), 4) if drets else None
    return out


def bucket_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "v01_all_directional": metric(rows, lambda r: True),
        "v04_selective_or_actionable": metric(rows, lambda r: r.get("v04_actionability_state") in {"SELECTIVE", "ACTIONABLE"}),
        "v04_actionable_only": metric(rows, lambda r: r.get("v04_actionability_state") == "ACTIONABLE"),
        "v041_selective_or_actionable": metric(rows, lambda r: r.get("v041_actionability_state") in {"SELECTIVE", "ACTIONABLE"}),
        "v041_actionable_only": metric(rows, lambda r: r.get("v041_actionability_state") == "ACTIONABLE"),
    }


def main() -> int:
    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    lineage = json.loads(LINEAGE_PATH.read_text(encoding="utf-8"))
    if decision.get("version") != "0.4.1" or decision.get("model_status") != "EXPERIMENTAL_V01_CORE_MTF_ACTIONABILITY_V041_PREVALIDATION":
        raise SystemExit("Run Crypto Decision v0.4.1 before the v0.4.1 diagnostic.")
    if decision.get("frozen") is True:
        raise SystemExit("v0.4.1 must remain unfrozen during diagnostic evaluation.")
    expected_hash = ((lineage.get("canonical_direction") or {}).get("methodology_sha256"))
    active_hash = ((decision.get("canonical_direction_model") or {}).get("methodology_sha256"))
    if not expected_hash or active_hash != expected_hash:
        raise SystemExit(f"Canonical v0.1 lineage mismatch: expected {expected_hash}, got {active_hash}")

    universe = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
    all_rows: List[Dict[str, Any]] = []
    for asset in universe.get("assets", []):
        rows = build_asset_rows(asset)
        all_rows.extend(rows)
        print(f"{asset['symbol']}: {len(rows)} v0.4.1 observations")
    all_rows.sort(key=lambda r: (r["date"], r["asset"]))

    overall = bucket_summary(all_rows)
    per_asset = []
    for symbol in [x.get("symbol") for x in universe.get("assets", [])]:
        rows = [r for r in all_rows if r.get("asset") == symbol]
        per_asset.append({"asset": symbol, **bucket_summary(rows)})

    regimes: Dict[str, Any] = {"volatility": {}, "drawdown": {}}
    for key, outkey in [("vol_regime", "volatility"), ("drawdown_regime", "drawdown")]:
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in all_rows:
            grouped[str(row.get(key) or "UNKNOWN")].append(row)
        regimes[outkey] = {name: bucket_summary(rows) for name, rows in sorted(grouped.items())}

    directional_rows = [r for r in all_rows if r.get("canonical_state") in {"SUPPORTIVE", "PRESSURED"}]
    state_distribution = Counter(r.get("v041_actionability_state") for r in all_rows)
    limiter_distribution = Counter(r.get("v041_limiter") for r in directional_rows)
    regime_limiter_distribution = Counter(r.get("v041_regime_limiter") for r in directional_rows)

    violations = {
        "moderate_vol_actionable": sum(1 for r in all_rows if r.get("vol_regime") == "MODERATE_VOL" and r.get("v041_actionability_state") == "ACTIONABLE"),
        "high_vol_actionable": sum(1 for r in all_rows if r.get("vol_regime") == "HIGH_VOL" and r.get("v041_actionability_state") == "ACTIONABLE"),
        "stressed_drawdown_actionable": sum(1 for r in all_rows if r.get("drawdown_regime") == "STRESSED_DRAWDOWN" and r.get("v041_actionability_state") == "ACTIONABLE"),
    }

    flags: List[Dict[str, str]] = []
    for key, count in violations.items():
        if count:
            flags.append({"severity": "HIGH", "code": f"REGIME_POLICY_VIOLATION_{key.upper()}", "message": f"Found {count} ACTIONABLE observations that violate the explicit v0.4.1 regime policy."})
    raw7 = fnum(overall["v01_all_directional"].get("hit_rate_7d_percent"))
    sel7 = fnum(overall["v041_selective_or_actionable"].get("hit_rate_7d_percent"))
    act7 = fnum(overall["v041_actionable_only"].get("hit_rate_7d_percent"))
    if raw7 is not None and sel7 is not None and sel7 < raw7:
        flags.append({"severity": "REVIEW", "code": "SELECTIVE_GATE_NOT_7D_ACCURACY_UPLIFT", "message": "SELECTIVE+ACTIONABLE does not improve 7-day hit rate over raw v0.1 on the consumed diagnostic window; keep SELECTIVE as review priority rather than an accuracy claim."})
    retention = fnum(overall["v041_actionable_only"].get("retention_percent_of_v01_directional"))
    if retention is not None and retention < 3:
        flags.append({"severity": "REVIEW", "code": "ACTIONABLE_RETENTION_VERY_LOW", "message": "ACTIONABLE retains under 3% of v0.1 directional observations on the consumed window."})

    artifact = {
        "version": "4.1",
        "status": "CRYPTO_V041_ACTIONABILITY_DIAGNOSTIC_COMPLETE_REQUIRES_11C5_REVIEW",
        "generated_at": bt.iso_now(),
        "scope": decision.get("scope"),
        "model_snapshot": {
            "decision_version": decision.get("version"),
            "model_status": decision.get("model_status"),
            "frozen": False,
            "canonical_v01_methodology_sha256": active_hash,
            "actionability_version": "CRYPTO_ACTIONABILITY_0.2",
        },
        "test_design": {
            "historical_window_days": HISTORY_DAYS,
            "warmup_days": WARMUP_DAYS,
            "forward_horizons_days": list(FORWARD_HORIZONS),
            "historical_window_status": "CONSUMED_DIAGNOSTIC_NOT_FRESH_OOS",
            "canonical_direction": "EXACT_V01_RECONSTRUCTION",
            "mtf_changed_from_v04": False,
            "directional_thresholds_changed_from_v04": False,
            "asset_specific_rules": False,
            "v041_change_scope": "REGIME_AWARE_ACTIONABILITY_CEILING_ONLY",
            "market_only_actionability_proxy": True,
            "historical_protocol_regulatory_network_state_not_backfilled": True,
            "no_threshold_search": True,
        },
        "regime_policy": {
            "LOW_VOL": "May reach ACTIONABLE subject to other ceilings.",
            "MODERATE_VOL": "Maximum SELECTIVE (ceiling 70).",
            "HIGH_VOL": "Maximum FILTERED (ceiling 55).",
            "UNKNOWN_VOL": "Maximum FILTERED (ceiling 55).",
            "STRESSED_DRAWDOWN": "Maximum SELECTIVE (ceiling 60).",
        },
        "summary": overall,
        "per_asset": per_asset,
        "regimes": regimes,
        "actionability_state_distribution": dict(state_distribution),
        "limiter_distribution": dict(limiter_distribution),
        "regime_limiter_distribution": dict(regime_limiter_distribution),
        "regime_policy_violations": violations,
        "diagnostic_flags": flags,
        "guardrails": {
            "canonical_direction_is_exact_v01": True,
            "mtf_does_not_reverse_direction": True,
            "historical_non_market_evidence_not_backfilled": True,
            "consumed_historical_window": True,
            "fresh_oos_remains_primary_validation": True,
            "no_asset_specific_rules": True,
            "no_buy_sell": True,
            "no_profit_probability": True,
            "trade_execution": "OFF",
        },
        "next_gate": "11C5_PRE_FREEZE_CROSS_CHECK_AFTER_V041_REVIEW",
    }
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("v0.4.1 diagnostic complete:", json.dumps(overall, ensure_ascii=False))
    print("regime policy violations:", json.dumps(violations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
