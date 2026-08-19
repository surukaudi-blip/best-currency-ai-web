#!/usr/bin/env python3
"""Diagnostic retest for refined Crypto Decision Intelligence v0.2.

Important: the historical 70/30 window was already inspected in the v0.1 backtest.
This script deliberately labels the last 30% as a REUSED diagnostic window, not an
untouched holdout. Its purpose is to test whether the structural refinement reduces
known failure modes; it cannot create new out-of-sample evidence.
"""

from __future__ import annotations

import importlib.util
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
BASE_BT_PATH = ROOT / "scripts" / "build-crypto-backtest.py"
MODEL_PATH = ROOT / "scripts" / "build-crypto-decision-v02.py"
UNIVERSE_PATH = ROOT / "data" / "crypto-universe.json"
DECISION_PATH = ROOT / "data" / "crypto-decision-intelligence.json"
PRIOR_PATH = ROOT / "data" / "crypto-backtest.json"
OUTPUT_PATH = ROOT / "data" / "crypto-backtest-v02.json"

spec_bt = importlib.util.spec_from_file_location("crypto_backtest_v01_helpers", BASE_BT_PATH)
bt = importlib.util.module_from_spec(spec_bt)
assert spec_bt and spec_bt.loader
spec_bt.loader.exec_module(bt)

spec_model = importlib.util.spec_from_file_location("crypto_decision_v02", MODEL_PATH)
model = importlib.util.module_from_spec(spec_model)
assert spec_model and spec_model.loader
spec_model.loader.exec_module(model)

HISTORY_DAYS = 365
WARMUP_DAYS = 90
FORWARD_HORIZONS = (1, 3, 7)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def r4(v: Optional[float]) -> Optional[float]:
    return round(float(v), 4) if v is not None else None


def fnum(v: Any) -> Optional[float]:
    return bt.fnum(v)


def mean(values: Sequence[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def completed_context(prices: List[float], volumes: List[Optional[float]], dates: List[str], i: int) -> Dict[str, Any]:
    latest = prices[i]
    sma20 = mean(prices[i - 19 : i + 1]) if i >= 19 else None
    sma50 = mean(prices[i - 49 : i + 1]) if i >= 49 else None
    v7 = [float(v) for v in volumes[max(0, i - 6) : i + 1] if v is not None]
    v30 = [float(v) for v in volumes[max(0, i - 29) : i + 1] if v is not None]
    av7, av30 = mean(v7), mean(v30)
    volume_ratio = (av7 / av30) if av7 is not None and av30 not in (None, 0) else None
    return {
        "completed_session": dates[i],
        "history_observations": i + 1,
        "return_1d_percent": r4(bt.pct_return(latest, prices[i - 1])) if i >= 1 else None,
        "return_7d_percent": r4(bt.pct_return(latest, prices[i - 7])) if i >= 7 else None,
        "return_30d_percent": r4(bt.pct_return(latest, prices[i - 30])) if i >= 30 else None,
        "close_vs_sma20_percent": r4(bt.pct_return(latest, sma20)) if sma20 not in (None, 0) else None,
        "close_vs_sma50_percent": r4(bt.pct_return(latest, sma50)) if sma50 not in (None, 0) else None,
        "realized_volatility_30d_annualized_percent": r4(bt.volatility_30(prices, i)),
        "drawdown_from_90d_high_percent": r4(bt.drawdown_90(prices, i)),
        "volume_7d_vs_30d_ratio": r4(volume_ratio),
    }


def partial_market_risk_proxy(context: Dict[str, Any], m: Dict[str, Any]) -> Optional[float]:
    vol = model.base.volatility_risk(fnum(context.get("realized_volatility_30d_annualized_percent")))
    dd = model.base.drawdown_risk(fnum(context.get("drawdown_from_90d_high_percent")))
    one_day = model.clamp(abs(fnum(context.get("return_1d_percent")) or 0.0) / 10.0 * 100.0)
    conflict, _ = model.base.horizon_conflict_risk({"completed_daily_context": context})
    reversal = model.reversal_exhaustion_risk(m)
    pieces = [
        (vol, model.RISK_WEIGHTS_V02["volatility"]),
        (dd, model.RISK_WEIGHTS_V02["drawdown"]),
        (one_day, model.RISK_WEIGHTS_V02["one_day_shock"]),
        (conflict, model.RISK_WEIGHTS_V02["horizon_conflict"]),
        (reversal, model.RISK_WEIGHTS_V02["reversal_exhaustion"]),
    ]
    return model.base.weighted_available(pieces)


def build_rows(asset: Dict[str, Any]) -> List[Dict[str, Any]]:
    chart = bt.fetch_json(
        f"/coins/{bt.urllib.parse.quote(asset['id'])}/market_chart",
        {"vs_currency": "usd", "days": HISTORY_DAYS, "precision": "full"},
    )
    pmap = bt.daily_map(chart.get("prices") or [])
    vmap = bt.daily_map(chart.get("total_volumes") or [])
    dates = sorted(pmap)
    if len(dates) < 150:
        raise ValueError(f"{asset['id']}: insufficient completed daily history ({len(dates)})")
    prices = [pmap[d] for d in dates]
    volumes = [vmap.get(d) for d in dates]
    last_anchor = len(dates) - max(FORWARD_HORIZONS) - 1
    rows: List[Dict[str, Any]] = []

    for i in range(WARMUP_DAYS, last_anchor + 1):
        context = completed_context(prices, volumes, dates, i)
        synthetic_asset = {"symbol": asset.get("symbol"), "completed_daily_context": context}
        m = model.market_structure_v02(synthetic_asset)
        state = m.get("state")
        raw_state = m.get("raw_state")
        sign = 1 if state == "SUPPORTIVE" else (-1 if state == "PRESSURED" else 0)
        fwd = {h: r4(bt.pct_return(prices[i + h], prices[i])) for h in FORWARD_HORIZONS}
        directional = {h: (r4((fwd[h] or 0.0) * sign) if sign and fwd[h] is not None else None) for h in FORWARD_HORIZONS}
        hits = {h: (directional[h] > 0 if directional[h] is not None else None) for h in FORWARD_HORIZONS}
        guard_codes = [x.get("code") for x in m.get("guardrails", []) if x.get("code")]
        alignment = m.get("alignment") or {}
        score = fnum(m.get("score"))
        rows.append({
            "date": dates[i],
            "asset": asset.get("symbol"),
            "score": score,
            "state": state,
            "raw_state": raw_state,
            "directional_eligible": bool(m.get("directional_eligible")),
            "clarity": round(abs((score if score is not None else 50.0) - 50.0) * 2.0, 2),
            "positive_count": alignment.get("positive_count"),
            "negative_count": alignment.get("negative_count"),
            "aligned_count": alignment.get("aligned_count"),
            "guardrail_codes": guard_codes,
            "return_7d": context.get("return_7d_percent"),
            "return_30d": context.get("return_30d_percent"),
            "close_vs_sma20": context.get("close_vs_sma20_percent"),
            "close_vs_sma50": context.get("close_vs_sma50_percent"),
            "volatility_30d": context.get("realized_volatility_30d_annualized_percent"),
            "drawdown_90d": context.get("drawdown_from_90d_high_percent"),
            "market_risk_proxy": partial_market_risk_proxy(context, m),
            "vol_regime": bt.vol_regime(fnum(context.get("realized_volatility_30d_annualized_percent"))),
            "drawdown_regime": bt.drawdown_regime(fnum(context.get("drawdown_from_90d_high_percent"))),
            "fwd_1d": fwd[1], "fwd_3d": fwd[3], "fwd_7d": fwd[7],
            "dir_1d": directional[1], "dir_3d": directional[3], "dir_7d": directional[7],
            "hit_1d": hits[1], "hit_3d": hits[3], "hit_7d": hits[7],
        })
    return rows


def recompute_directional(rows: List[Dict[str, Any]], use_raw_state: bool) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for src in rows:
        r = dict(src)
        state = r.get("raw_state") if use_raw_state else r.get("state")
        r["state"] = state
        sign = 1 if state == "SUPPORTIVE" else (-1 if state == "PRESSURED" else 0)
        for h in FORWARD_HORIZONS:
            raw = fnum(r.get(f"fwd_{h}d"))
            d = raw * sign if raw is not None and sign else None
            r[f"dir_{h}d"] = r4(d)
            r[f"hit_{h}d"] = (d > 0) if d is not None else None
        out.append(r)
    return out


def grouped(rows: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get(key) or "UNKNOWN")].append(row)
    return {k: bt.summarize(v) for k, v in sorted(buckets.items())}


def guardrail_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Counter[str] = Counter()
    directional_suppressed = 0
    for r in rows:
        for code in r.get("guardrail_codes") or []:
            counts[code] += 1
        if r.get("raw_state") in {"SUPPORTIVE", "PRESSURED"} and r.get("state") == "MIXED":
            directional_suppressed += 1
    raw_summary = bt.summarize(recompute_directional(rows, True))
    effective_summary = bt.summarize(rows)
    return {
        "guardrail_counts": dict(counts),
        "raw_directional_observations": raw_summary.get("directional_observations"),
        "effective_directional_observations": effective_summary.get("directional_observations"),
        "directional_observations_suppressed": directional_suppressed,
        "raw_high_clarity_7d_miss_rate_percent": raw_summary.get("high_clarity_7d_miss_rate_percent"),
        "effective_high_clarity_7d_miss_rate_percent": effective_summary.get("high_clarity_7d_miss_rate_percent"),
        "raw_hit_rate_7d_percent": raw_summary.get("hit_rate_7d_percent"),
        "effective_hit_rate_7d_percent": effective_summary.get("hit_rate_7d_percent"),
    }


def diagnostic_flags(summary: Dict[str, Any], development: Dict[str, Any], reused: Dict[str, Any], per_asset: List[Dict[str, Any]], regimes: Dict[str, Any]) -> List[Dict[str, str]]:
    flags: List[Dict[str, str]] = []
    hit7 = fnum(reused.get("hit_rate_7d_percent"))
    n = int(reused.get("directional_observations") or 0)
    miss = fnum(reused.get("high_clarity_7d_miss_rate_percent"))
    dev_hit = fnum(development.get("hit_rate_7d_percent"))
    coverage = fnum(summary.get("directional_coverage_percent"))
    if n >= 40 and hit7 is not None and hit7 < 50:
        flags.append({"severity": "HIGH", "code": "REUSED_WINDOW_7D_BELOW_50", "message": "The reused diagnostic window remains below 50% 7-day directional hit rate."})
    if miss is not None and miss >= 45:
        flags.append({"severity": "HIGH", "code": "HIGH_CLARITY_MISS_RATE_REMAINS_HIGH", "message": "High-clarity 7-day miss rate remains at or above 45% after refinement."})
    if hit7 is not None and dev_hit is not None and abs(hit7 - dev_hit) >= 10:
        flags.append({"severity": "MODERATE", "code": "DEVELOPMENT_REUSED_GAP_10PP", "message": "Development and reused diagnostic-window 7-day hit rates differ by at least 10 percentage points."})
    if coverage is not None and coverage > 70:
        flags.append({"severity": "MODERATE", "code": "DIRECTIONAL_COVERAGE_HIGH", "message": "Effective directional coverage remains above 70%."})
    if coverage is not None and coverage < 10:
        flags.append({"severity": "MODERATE", "code": "DIRECTIONAL_COVERAGE_LOW", "message": "Effective directional coverage falls below 10%."})
    for row in per_asset:
        x = row.get("reused_diagnostic_window") or {}
        an = int(x.get("directional_observations") or 0)
        ah = fnum(x.get("hit_rate_7d_percent"))
        if an >= 20 and ah is not None and ah < 45:
            flags.append({"severity": "MODERATE", "code": f"WEAK_ASSET_{row.get('asset')}", "message": f"{row.get('asset')} remains below 45% 7-day directional hit rate in the reused diagnostic window."})
    for regime, metrics in (regimes.get("volatility") or {}).items():
        rn = int(metrics.get("directional_observations") or 0)
        rh = fnum(metrics.get("hit_rate_7d_percent"))
        if rn >= 40 and rh is not None and rh < 47:
            flags.append({"severity": "MODERATE", "code": f"WEAK_{regime}", "message": f"7-day directional performance remains weak in {regime}."})
    return flags


def main() -> int:
    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    prior = json.loads(PRIOR_PATH.read_text(encoding="utf-8"))
    universe = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
    if decision.get("version") != "0.2" or decision.get("model_status") != "EXPERIMENTAL_REFINED_PREVALIDATION":
        raise SystemExit("Run refined Stage 11C v0.2 decision workflow before the v0.2 retest.")
    if decision.get("frozen") is True:
        raise SystemExit("v0.2 retest is a pre-freeze diagnostic and fails closed after freeze.")

    all_rows: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    for asset in universe.get("assets", []):
        try:
            rows = build_rows(asset)
            all_rows.extend(rows)
            print(f"{asset.get('symbol')}: {len(rows)} v0.2 retest observations")
        except Exception as exc:
            errors.append({"asset": str(asset.get("symbol") or asset.get("id")), "error": str(exc)[:500]})
    if errors:
        raise SystemExit("v0.2 retest fails closed: " + json.dumps(errors))

    all_rows.sort(key=lambda r: (r["date"], r["asset"]))
    dev_rows, reused_rows, split_date = bt.chronological_split(all_rows)
    summary = bt.summarize(all_rows)
    development = bt.summarize(dev_rows)
    reused = bt.summarize(reused_rows)

    per_asset: List[Dict[str, Any]] = []
    for symbol in [a.get("symbol") for a in universe.get("assets", [])]:
        rows = [r for r in all_rows if r.get("asset") == symbol]
        drows = [r for r in dev_rows if r.get("asset") == symbol]
        rrows = [r for r in reused_rows if r.get("asset") == symbol]
        per_asset.append({
            "asset": symbol,
            "overall": bt.summarize(rows),
            "development": bt.summarize(drows),
            "reused_diagnostic_window": bt.summarize(rrows),
            "guardrails": guardrail_stats(rows),
        })

    regimes = {
        "volatility": grouped(all_rows, "vol_regime"),
        "drawdown": grouped(all_rows, "drawdown_regime"),
    }
    guardrails = {
        "overall": guardrail_stats(all_rows),
        "development": guardrail_stats(dev_rows),
        "reused_diagnostic_window": guardrail_stats(reused_rows),
    }

    failures = [r for r in all_rows if r.get("state") in {"SUPPORTIVE", "PRESSURED"} and r.get("hit_7d") is False]
    failures.sort(key=lambda r: (-(fnum(r.get("clarity")) or 0.0), fnum(r.get("dir_7d")) or 0.0))
    failure_cases = [{
        "date": r.get("date"), "asset": r.get("asset"), "state": r.get("state"), "raw_state": r.get("raw_state"),
        "score": r.get("score"), "clarity": r.get("clarity"), "forward_7d_percent": r.get("fwd_7d"),
        "directional_7d_percent": r.get("dir_7d"), "volatility_30d": r.get("volatility_30d"),
        "drawdown_90d": r.get("drawdown_90d"), "market_risk_proxy": r.get("market_risk_proxy"),
        "aligned_count": r.get("aligned_count"), "guardrail_codes": r.get("guardrail_codes"),
        "vol_regime": r.get("vol_regime"), "drawdown_regime": r.get("drawdown_regime"),
    } for r in failures[:20]]

    flags = diagnostic_flags(summary, development, reused, per_asset, regimes)
    artifact = {
        "version": "2.0",
        "status": "CRYPTO_V02_RETEST_COMPLETE_REQUIRES_11C5_REVIEW",
        "scope": decision.get("scope"),
        "generated_at": now_iso(),
        "model_snapshot": {
            "version": decision.get("version"),
            "model_status": decision.get("model_status"),
            "frozen": False,
            "methodology_sha256": bt.canonical_hash(decision.get("methodology") or {}),
            "refinement": decision.get("refinement"),
        },
        "test_design": {
            "historical_window_days": HISTORY_DAYS,
            "warmup_days": WARMUP_DAYS,
            "forward_horizons_days": list(FORWARD_HORIZONS),
            "chronological_split": "70_PERCENT_DEVELOPMENT_30_PERCENT_REUSED_DIAGNOSTIC_WINDOW",
            "split_date": split_date,
            "last_30_percent_status": "CONSUMED_REUSED_DIAGNOSTIC_NOT_UNTOUCHED_HOLDOUT",
            "raw_historical_series_published": False,
            "historical_protocol_regulatory_network_state_not_backfilled": True,
            "production_market_structure_reused_directly": True,
        },
        "summary": summary,
        "development": development,
        "reused_diagnostic_window": reused,
        "per_asset": per_asset,
        "regimes": regimes,
        "guardrail_diagnostics": guardrails,
        "comparison_to_v01": {
            "v01_generated_at": prior.get("generated_at"),
            "v01_overall": prior.get("summary"),
            "v01_consumed_holdout": prior.get("diagnostic_holdout"),
            "comparison_is_diagnostic_not_new_oos": True,
        },
        "failure_cases": failure_cases,
        "diagnostic_flags": flags,
        "guardrails": {
            "diagnostic_only": True,
            "no_lookahead": True,
            "no_best_threshold_selection": True,
            "same_historical_window_is_not_untouched_holdout": True,
            "fresh_oos_remains_primary_validation": True,
            "no_buy_sell": True,
            "no_profit_probability": True,
            "trade_execution": "OFF",
        },
        "next_gate": "11C5_PRE_FREEZE_CROSS_CHECK_REQUIRED_AFTER_REVIEW",
    }
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"v0.2 retest: observations={summary.get('observations')}; directional={summary.get('directional_observations')}; reused7d={reused.get('hit_rate_7d_percent')}; flags={len(flags)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
