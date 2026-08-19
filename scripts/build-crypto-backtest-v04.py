#!/usr/bin/env python3
"""Stage 11C.4 v0.4 diagnostic: exact v0.1 direction + D/W/M Actionability.

This evaluates whether the *market-reconstructible* parts of v0.4 improve selection
quality while keeping v0.1 canonical direction unchanged. Historical protocol,
regulatory, and chain-evidence states are not fabricated or backfilled.

The full production Actionability score includes operational evidence/data ceilings;
this historical diagnostic therefore reports a MARKET-ONLY ACTIONABILITY PROXY using:
- exact v0.1 canonical directional core,
- Daily/Weekly/Monthly canonical alignment,
- market participation,
- reconstructible market-risk regime ceiling.

The 365-day window has already been inspected in v0.1/v0.2/v0.3 work and is consumed
diagnostic evidence, not Fresh OOS.
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
V01_BACKTEST_PATH = ROOT / "data" / "crypto-backtest.json"
OUTPUT_PATH = ROOT / "data" / "crypto-backtest-v04.json"

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


def tf_state(value: Optional[float], span: float) -> Tuple[Optional[float], str]:
    sc = bt.signed_score(value, span)
    return sc, bt.state_for(sc, 62.0, 38.0)


def relation_score(tf_st: str, canonical: str) -> Tuple[str, float]:
    if canonical not in {"SUPPORTIVE", "PRESSURED"}:
        return "CANONICAL_NOT_DIRECTIONAL", 45.0
    if tf_st == canonical:
        return "SUPPORTS_CANONICAL", 100.0
    if tf_st == "MIXED":
        return "NEUTRAL_TO_CANONICAL", 55.0
    if tf_st in {"SUPPORTIVE", "PRESSURED"}:
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
        sc, st = tf_state(value, span)
        rel, rel_score = relation_score(st, canonical)
        frames[name] = {
            "return_percent": bt.safe_round(value, 4),
            "score": bt.safe_round(sc),
            "state": st,
            "relation": rel,
            "relation_score": rel_score,
            "weight": weight,
        }
        total += rel_score * weight
    alignment = round(total, 2)
    return {
        "score": alignment,
        "state": "STRONG" if alignment >= 80 else ("MODERATE" if alignment >= 60 else "LOW"),
        "frames": frames,
    }


def market_regime_ceiling(prices: List[float], i: int, canonical_data: Dict[str, Any]) -> Dict[str, Any]:
    vol30 = bt.volatility_30(prices, i)
    dd90 = bt.drawdown_90(prices, i)
    r1 = bt.pct_return(prices[i], prices[i - 1]) if i >= 1 else None
    conflict_count, conflict_risk = bt.horizon_conflict(
        canonical_data.get("return_7d"),
        canonical_data.get("return_30d"),
        canonical_data.get("close_vs_sma20"),
        canonical_data.get("close_vs_sma50"),
    )
    one_day = bt.clamp(abs(r1 or 0.0) / 10.0 * 100.0)
    risk = bt.weighted_available([
        (bt.volatility_risk(vol30), 0.30),
        (bt.drawdown_risk(dd90), 0.20),
        (one_day, 0.15),
        (conflict_risk, 0.10),
    ])
    risk_state = "LOW" if (risk or 100) < 35 else ("MODERATE" if (risk or 100) < 65 else "HIGH")
    ceiling = {"LOW": 100.0, "MODERATE": 70.0, "HIGH": 45.0}[risk_state]
    if bt.volatility_risk(vol30) >= 70:
        ceiling = min(ceiling, 55.0)
    if bt.drawdown_risk(dd90) >= 65:
        ceiling = min(ceiling, 60.0)
    return {
        "score": round(ceiling, 2),
        "risk_proxy": bt.safe_round(risk),
        "risk_state": risk_state,
        "volatility_30d": bt.safe_round(vol30, 4),
        "drawdown_90d": bt.safe_round(dd90, 4),
        "conflict_count": conflict_count,
        "vol_regime": bt.vol_regime(vol30),
        "drawdown_regime": bt.drawdown_regime(dd90),
    }


def market_participation(volumes: List[Optional[float]], i: int) -> float:
    return float(bt.participation_score(volumes, i) or 45.0)


def market_actionability(canonical: Dict[str, Any], mtf_data: Dict[str, Any], regime: Dict[str, Any], participation: float) -> Dict[str, Any]:
    canonical_gate = 100.0 if canonical.get("state") in {"SUPPORTIVE", "PRESSURED"} else 45.0
    asset_readiness = round(0.80 * float(mtf_data.get("score") or 0.0) + 0.20 * participation, 2)
    ceilings = {
        "regime_guardrail": float(regime.get("score") or 0.0),
        "asset_mtf_readiness": asset_readiness,
        "canonical_gate": canonical_gate,
    }
    score = round(min(ceilings.values()), 2)
    limiter = min(ceilings, key=ceilings.get)
    if score >= 80:
        state = "ACTIONABLE"
    elif score >= 60:
        state = "SELECTIVE"
    else:
        state = "FILTERED"
    return {
        "score": score,
        "state": state,
        "limiter": limiter,
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
        reg = market_regime_ceiling(prices, i, can)
        part = market_participation(volumes, i)
        act = market_actionability(can, mtf_data, reg, part)
        sign = 1 if can["state"] == "SUPPORTIVE" else (-1 if can["state"] == "PRESSURED" else 0)
        row = {
            "date": dates[i],
            "asset": asset["symbol"],
            "canonical_score": can["score"],
            "canonical_state": can["state"],
            "mtf_score": mtf_data["score"],
            "mtf_state": mtf_data["state"],
            "daily_state": mtf_data["frames"]["daily"]["state"],
            "weekly_state": mtf_data["frames"]["weekly"]["state"],
            "monthly_state": mtf_data["frames"]["monthly"]["state"],
            "actionability_score": act["score"],
            "actionability_state": act["state"],
            "actionability_limiter": act["limiter"],
            "market_risk_proxy": reg["risk_proxy"],
            "market_risk_state": reg["risk_state"],
            "vol_regime": reg["vol_regime"],
            "drawdown_regime": reg["drawdown_regime"],
        }
        for h in FORWARD_HORIZONS:
            fwd = bt.pct_return(prices[i + h], prices[i])
            directional = fwd * sign if sign else None
            row[f"fwd_{h}d"] = bt.safe_round(fwd, 4)
            row[f"dir_{h}d"] = bt.safe_round(directional, 4)
            row[f"hit_{h}d"] = directional > 0 if directional is not None else None
        rows.append(row)
    return rows


def metric(rows: List[Dict[str, Any]], predicate) -> Dict[str, Any]:
    selected = [r for r in rows if predicate(r) and r.get("canonical_state") in {"SUPPORTIVE", "PRESSURED"}]
    out = {
        "observations": len(selected),
        "coverage_percent_of_all": round(len(selected) / len(rows) * 100.0, 2) if rows else None,
    }
    canonical_n = sum(1 for r in rows if r.get("canonical_state") in {"SUPPORTIVE", "PRESSURED"})
    out["retention_percent_of_v01_directional"] = round(len(selected) / canonical_n * 100.0, 2) if canonical_n else None
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
        "v04_selective_or_actionable": metric(rows, lambda r: r.get("actionability_state") in {"SELECTIVE", "ACTIONABLE"}),
        "v04_actionable_only": metric(rows, lambda r: r.get("actionability_state") == "ACTIONABLE"),
    }


def main() -> int:
    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    if decision.get("version") != "0.4" or decision.get("model_status") != "EXPERIMENTAL_V01_CORE_MTF_ACTIONABILITY_PREVALIDATION":
        raise SystemExit("Run Crypto Decision v0.4 before the v0.4 Actionability backtest.")
    if decision.get("frozen") is True:
        raise SystemExit("v0.4 must remain unfrozen during diagnostic backtest.")

    v01_bt = json.loads(V01_BACKTEST_PATH.read_text(encoding="utf-8"))
    expected_hash = ((v01_bt.get("model_snapshot") or {}).get("methodology_sha256"))
    active_hash = ((decision.get("canonical_direction_model") or {}).get("methodology_sha256"))
    if not expected_hash or active_hash != expected_hash:
        raise SystemExit(f"Canonical v0.1 lineage mismatch: expected {expected_hash}, got {active_hash}")

    universe = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
    all_rows: List[Dict[str, Any]] = []
    for asset in universe.get("assets", []):
        rows = build_asset_rows(asset)
        all_rows.extend(rows)
        print(f"{asset['symbol']}: {len(rows)} v0.4 observations")
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

    limiter_distribution = Counter(
        r.get("actionability_limiter") for r in all_rows if r.get("canonical_state") in {"SUPPORTIVE", "PRESSURED"}
    )
    state_distribution = Counter(r.get("actionability_state") for r in all_rows)

    flags: List[Dict[str, str]] = []
    base7 = fnum(overall["v01_all_directional"].get("hit_rate_7d_percent"))
    sel7 = fnum(overall["v04_selective_or_actionable"].get("hit_rate_7d_percent"))
    act7 = fnum(overall["v04_actionable_only"].get("hit_rate_7d_percent"))
    if sel7 is not None and base7 is not None and sel7 < base7:
        flags.append({"severity": "HIGH", "code": "SELECTIVE_GATE_DEGRADES_7D", "message": "SELECTIVE+ACTIONABLE market-only gate has lower 7D directional hit rate than raw v0.1 directional observations."})
    if act7 is not None and base7 is not None and act7 < base7:
        flags.append({"severity": "HIGH", "code": "ACTIONABLE_GATE_DEGRADES_7D", "message": "ACTIONABLE-only market gate has lower 7D directional hit rate than raw v0.1 directional observations."})
    retention = fnum(overall["v04_selective_or_actionable"].get("retention_percent_of_v01_directional"))
    if retention is not None and retention < 30:
        flags.append({"severity": "MODERATE", "code": "ACTIONABILITY_RETENTION_TOO_LOW", "message": "v0.4 retains less than 30% of v0.1 directional observations at SELECTIVE or better."})

    artifact = {
        "version": "4.0",
        "status": "CRYPTO_V04_ACTIONABILITY_DIAGNOSTIC_COMPLETE_REQUIRES_11C5_REVIEW",
        "scope": decision.get("scope"),
        "generated_at": bt.iso_now(),
        "model_snapshot": {
            "version": "0.4",
            "model_status": decision.get("model_status"),
            "frozen": False,
            "canonical_v01_methodology_sha256": active_hash,
            "actionability_version": "CRYPTO_ACTIONABILITY_0.1",
        },
        "test_design": {
            "historical_window_days": HISTORY_DAYS,
            "warmup_days": WARMUP_DAYS,
            "forward_horizons_days": list(FORWARD_HORIZONS),
            "historical_window_status": "CONSUMED_DIAGNOSTIC_NOT_FRESH_OOS",
            "canonical_direction": "EXACT_V01_RECONSTRUCTION",
            "mtf": {
                "daily": "1D completed return; absolute span 6%",
                "weekly": "7D completed return; absolute span 12%",
                "monthly": "30D completed return; absolute span 25%",
                "weights": {"daily": 0.45, "weekly": 0.35, "monthly": 0.20},
                "state_thresholds": {"supportive_gte": 62, "pressured_lte": 38},
            },
            "actionability_proxy": "MARKET_ONLY; reconstructible MTF + participation + market-risk regime. Historical protocol/regulatory/network evidence and operational freshness are not backfilled.",
            "actionability_thresholds": {"actionable": 80, "selective": 60},
            "no_threshold_search": True,
        },
        "summary": overall,
        "per_asset": per_asset,
        "regimes": regimes,
        "limiter_distribution": dict(limiter_distribution),
        "actionability_state_distribution": dict(state_distribution),
        "diagnostic_flags": flags,
        "guardrails": {
            "canonical_direction_is_exact_v01": True,
            "mtf_does_not_reverse_direction": True,
            "historical_non_market_evidence_not_backfilled": True,
            "market_only_actionability_proxy": True,
            "no_threshold_search": True,
            "consumed_historical_window": True,
            "fresh_oos_remains_primary_validation": True,
            "no_buy_sell": True,
            "no_profit_probability": True,
            "trade_execution": "OFF",
        },
        "next_gate": "11C5_PRE_FREEZE_CROSS_CHECK_AFTER_V04_REVIEW",
    }
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("v0.4 diagnostic complete:", json.dumps(overall, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
