#!/usr/bin/env python3
"""Diagnostic retest for Crypto Decision Intelligence v0.3 hybrid.

The same historical window used by v0.1/v0.2 is already consumed. This retest is
strictly diagnostic. It evaluates whether the fixed 50/50 hybrid improves the
known trade-off between v0.1 sensitivity and v0.2 over-filtering without searching
blend weights or thresholds.
"""

from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
BT02_HELPERS_PATH = ROOT / "scripts" / "build-crypto-backtest-v02.py"
MODEL_PATH = ROOT / "scripts" / "build-crypto-decision-v03.py"
UNIVERSE_PATH = ROOT / "data" / "crypto-universe.json"
DECISION_PATH = ROOT / "data" / "crypto-decision-intelligence.json"
BT01_PATH = ROOT / "data" / "crypto-backtest.json"
BT02_PATH = ROOT / "data" / "crypto-backtest-v02.json"
OUTPUT_PATH = ROOT / "data" / "crypto-backtest-v03.json"

spec_bt2 = importlib.util.spec_from_file_location("crypto_backtest_v02_helpers", BT02_HELPERS_PATH)
bt2 = importlib.util.module_from_spec(spec_bt2)
assert spec_bt2 and spec_bt2.loader
spec_bt2.loader.exec_module(bt2)

spec_model = importlib.util.spec_from_file_location("crypto_decision_v03_retest", MODEL_PATH)
model = importlib.util.module_from_spec(spec_model)
assert spec_model and spec_model.loader
spec_model.loader.exec_module(model)

bt = bt2.bt
HISTORY_DAYS = 365
WARMUP_DAYS = 90
FORWARD_HORIZONS = (1, 3, 7)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fnum(v: Any) -> Optional[float]:
    return bt.fnum(v)


def r4(v: Optional[float]) -> Optional[float]:
    return round(float(v), 4) if v is not None else None


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


def market_risk_proxy(context: Dict[str, Any], m: Dict[str, Any]) -> Optional[float]:
    vol = model.v01.volatility_risk(fnum(context.get("realized_volatility_30d_annualized_percent")))
    dd = model.v01.drawdown_risk(fnum(context.get("drawdown_from_90d_high_percent")))
    one_day = model.clamp(abs(fnum(context.get("return_1d_percent")) or 0.0) / 10.0 * 100.0)
    conflict, _ = model.v01.horizon_conflict_risk({"completed_daily_context": context})
    reversal = model.reversal_exhaustion_risk_v03(m)
    parts = [
        (vol, model.RISK_WEIGHTS_V03["volatility"]),
        (dd, model.RISK_WEIGHTS_V03["drawdown"]),
        (one_day, model.RISK_WEIGHTS_V03["one_day_shock"]),
        (conflict, model.RISK_WEIGHTS_V03["horizon_conflict"]),
        (reversal, model.RISK_WEIGHTS_V03["reversal_exhaustion"]),
    ]
    return model.v01.weighted_available(parts)


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
        synthetic = {"symbol": asset.get("symbol"), "completed_daily_context": context}
        m = model.market_structure_v03(synthetic)
        state = m.get("state")
        raw_state = m.get("raw_state")
        sign = 1 if state == "SUPPORTIVE" else (-1 if state == "PRESSURED" else 0)
        fwd = {h: r4(bt.pct_return(prices[i + h], prices[i])) for h in FORWARD_HORIZONS}
        directional = {h: (r4((fwd[h] or 0.0) * sign) if sign and fwd[h] is not None else None) for h in FORWARD_HORIZONS}
        hits = {h: (directional[h] > 0 if directional[h] is not None else None) for h in FORWARD_HORIZONS}
        hybrid = m.get("hybrid") or {}
        agreement = hybrid.get("agreement") or {}
        extremity = hybrid.get("extremity") or {}
        alignment = m.get("alignment") or {}
        score = fnum(m.get("score"))
        structure_extremity = round(abs((score if score is not None else 50.0) - 50.0) * 2.0, 2)
        rows.append({
            "date": dates[i],
            "asset": asset.get("symbol"),
            "score": score,
            "state": state,
            "raw_state": raw_state,
            "directional_eligible": bool(m.get("directional_eligible")),
            "clarity": structure_extremity,
            "structure_extremity": structure_extremity,
            "v01_score": hybrid.get("v01_absolute_score"),
            "v01_state": hybrid.get("v01_state"),
            "v02_score": hybrid.get("v02_volatility_normalized_score"),
            "v02_state": hybrid.get("v02_raw_state"),
            "agreement_state": agreement.get("state"),
            "agreement_score": agreement.get("score"),
            "extremity_state": extremity.get("state"),
            "aligned_count": alignment.get("aligned_count"),
            "guardrail_codes": [x.get("code") for x in m.get("guardrails", []) if x.get("code")],
            "return_7d": context.get("return_7d_percent"),
            "return_30d": context.get("return_30d_percent"),
            "close_vs_sma20": context.get("close_vs_sma20_percent"),
            "close_vs_sma50": context.get("close_vs_sma50_percent"),
            "volatility_30d": context.get("realized_volatility_30d_annualized_percent"),
            "drawdown_90d": context.get("drawdown_from_90d_high_percent"),
            "market_risk_proxy": market_risk_proxy(context, m),
            "vol_regime": bt.vol_regime(fnum(context.get("realized_volatility_30d_annualized_percent"))),
            "drawdown_regime": bt.drawdown_regime(fnum(context.get("drawdown_from_90d_high_percent"))),
            "fwd_1d": fwd[1], "fwd_3d": fwd[3], "fwd_7d": fwd[7],
            "dir_1d": directional[1], "dir_3d": directional[3], "dir_7d": directional[7],
            "hit_1d": hits[1], "hit_3d": hits[3], "hit_7d": hits[7],
        })
    return rows


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    x = bt.summarize(rows)
    # The base helper calls |score-50| "clarity". In v0.3 that value is diagnostic
    # structure extremity only and never boosts Decision Readiness.
    x["high_extremity_directional_n"] = x.pop("high_clarity_directional_n", 0)
    x["high_extremity_7d_miss_rate_percent"] = x.pop("high_clarity_7d_miss_rate_percent", None)
    return x


def grouped(rows: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get(key) or "UNKNOWN")].append(row)
    return {k: summarize(v) for k, v in sorted(buckets.items())}


def agreement_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = Counter(str(r.get("agreement_state") or "UNKNOWN") for r in rows)
    direct_conflicts = [r for r in rows if r.get("agreement_state") == "DIRECT_CONFLICT"]
    directional = [r for r in rows if r.get("state") in {"SUPPORTIVE", "PRESSURED"}]
    strong = [r for r in directional if r.get("agreement_state") == "STRONG_CONSENSUS"]
    partial = [r for r in directional if r.get("agreement_state") == "PARTIAL_CONSENSUS"]
    return {
        "counts": dict(counts),
        "direct_conflicts": len(direct_conflicts),
        "effective_directional": len(directional),
        "strong_consensus_directional": len(strong),
        "partial_consensus_directional": len(partial),
        "strong_consensus_7d_hit_rate_percent": summarize(strong).get("hit_rate_7d_percent") if strong else None,
        "partial_consensus_7d_hit_rate_percent": summarize(partial).get("hit_rate_7d_percent") if partial else None,
    }


def guardrail_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Counter[str] = Counter()
    for row in rows:
        for code in row.get("guardrail_codes") or []:
            counts[code] += 1
    extreme = [r for r in rows if r.get("extremity_state") == "EXTREME"]
    directional_extreme = [r for r in extreme if r.get("state") in {"SUPPORTIVE", "PRESSURED"}]
    return {
        "guardrail_counts": dict(counts),
        "extreme_structure_observations": len(extreme),
        "extreme_directional_observations": len(directional_extreme),
        "extreme_directional_7d_hit_rate_percent": summarize(directional_extreme).get("hit_rate_7d_percent") if directional_extreme else None,
        "extreme_directional_7d_miss_rate_percent": (
            round(100.0 - float(summarize(directional_extreme).get("hit_rate_7d_percent")), 2)
            if directional_extreme and summarize(directional_extreme).get("hit_rate_7d_percent") is not None else None
        ),
    }


def flags(summary: Dict[str, Any], development: Dict[str, Any], reused: Dict[str, Any], per_asset: List[Dict[str, Any]], regimes: Dict[str, Any], agree: Dict[str, Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    hit7 = fnum(reused.get("hit_rate_7d_percent"))
    dev7 = fnum(development.get("hit_rate_7d_percent"))
    ext_miss = fnum(reused.get("high_extremity_7d_miss_rate_percent"))
    coverage = fnum(summary.get("directional_coverage_percent"))
    if int(reused.get("directional_observations") or 0) >= 40 and hit7 is not None and hit7 < 50:
        out.append({"severity": "HIGH", "code": "REUSED_WINDOW_7D_BELOW_50", "message": "Hybrid reused diagnostic-window 7-day directional hit rate is below 50%."})
    if ext_miss is not None and ext_miss >= 50:
        out.append({"severity": "HIGH", "code": "HIGH_EXTREMITY_MISS_RATE_HIGH", "message": "High-extremity directional observations still miss at least 50% of 7-day outcomes."})
    if hit7 is not None and dev7 is not None and abs(hit7 - dev7) >= 10:
        out.append({"severity": "MODERATE", "code": "DEVELOPMENT_REUSED_GAP_10PP", "message": "Development and reused diagnostic-window 7-day hit rates differ by at least 10 percentage points."})
    if coverage is not None and coverage < 25:
        out.append({"severity": "MODERATE", "code": "DIRECTIONAL_COVERAGE_TOO_LOW", "message": "Hybrid directional coverage is below 25%, indicating excessive passivity."})
    if coverage is not None and coverage > 65:
        out.append({"severity": "MODERATE", "code": "DIRECTIONAL_COVERAGE_TOO_HIGH", "message": "Hybrid directional coverage is above 65%, indicating insufficient selectivity."})
    for row in per_asset:
        x = row.get("reused_diagnostic_window") or {}
        n = int(x.get("directional_observations") or 0)
        h = fnum(x.get("hit_rate_7d_percent"))
        if n >= 20 and h is not None and h < 45:
            out.append({"severity": "MODERATE", "code": f"WEAK_ASSET_{row.get('asset')}", "message": f"{row.get('asset')} remains below 45% 7-day directional hit rate in the reused diagnostic window."})
    for regime, metrics in (regimes.get("volatility") or {}).items():
        n = int(metrics.get("directional_observations") or 0)
        h = fnum(metrics.get("hit_rate_7d_percent"))
        if n >= 40 and h is not None and h < 47:
            out.append({"severity": "MODERATE", "code": f"WEAK_{regime}", "message": f"Hybrid 7-day directional performance is weak in {regime}."})
    if int(agree.get("direct_conflicts") or 0) > 0:
        out.append({"severity": "INFORMATIONAL", "code": "DIRECT_MODEL_CONFLICTS_OBSERVED", "message": "v0.1 and v0.2 produced opposite directional states on some historical observations; v0.3 correctly fails those cases closed to MIXED."})
    return out


def main() -> int:
    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    prior1 = json.loads(BT01_PATH.read_text(encoding="utf-8"))
    prior2 = json.loads(BT02_PATH.read_text(encoding="utf-8"))
    universe = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
    if decision.get("version") != "0.3" or decision.get("model_status") != "EXPERIMENTAL_HYBRID_PREVALIDATION":
        raise SystemExit("Run Stage 11C v0.3 hybrid decision workflow before v0.3 retest.")
    if decision.get("frozen") is True:
        raise SystemExit("v0.3 retest is pre-freeze diagnostic and fails closed after freeze.")
    if model.HYBRID_WEIGHTS != {"v01_absolute": 0.50, "v02_volatility_normalized": 0.50}:
        raise SystemExit("v0.3 retest refuses non-symmetric hybrid weights.")

    all_rows: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    for asset in universe.get("assets", []):
        try:
            rows = build_rows(asset)
            all_rows.extend(rows)
            print(f"{asset.get('symbol')}: {len(rows)} v0.3 hybrid retest observations")
        except Exception as exc:
            errors.append({"asset": str(asset.get("symbol") or asset.get("id")), "error": str(exc)[:500]})
    if errors:
        raise SystemExit("v0.3 retest fails closed: " + json.dumps(errors))

    all_rows.sort(key=lambda r: (r["date"], r["asset"]))
    dev_rows, reused_rows, split_date = bt.chronological_split(all_rows)
    summary = summarize(all_rows)
    development = summarize(dev_rows)
    reused = summarize(reused_rows)

    per_asset = []
    for symbol in [x.get("symbol") for x in universe.get("assets", [])]:
        rows = [r for r in all_rows if r.get("asset") == symbol]
        drows = [r for r in dev_rows if r.get("asset") == symbol]
        rrows = [r for r in reused_rows if r.get("asset") == symbol]
        per_asset.append({
            "asset": symbol,
            "overall": summarize(rows),
            "development": summarize(drows),
            "reused_diagnostic_window": summarize(rrows),
            "agreement": agreement_stats(rows),
            "extremity": guardrail_stats(rows),
        })

    regimes = {
        "volatility": grouped(all_rows, "vol_regime"),
        "drawdown": grouped(all_rows, "drawdown_regime"),
    }
    agreement = {
        "overall": agreement_stats(all_rows),
        "development": agreement_stats(dev_rows),
        "reused_diagnostic_window": agreement_stats(reused_rows),
    }
    extremity = {
        "overall": guardrail_stats(all_rows),
        "development": guardrail_stats(dev_rows),
        "reused_diagnostic_window": guardrail_stats(reused_rows),
    }

    failures = [r for r in all_rows if r.get("state") in {"SUPPORTIVE", "PRESSURED"} and r.get("hit_7d") is False]
    failures.sort(key=lambda r: (-(fnum(r.get("structure_extremity")) or 0.0), fnum(r.get("dir_7d")) or 0.0))
    failure_cases = [{
        "date": r.get("date"), "asset": r.get("asset"), "state": r.get("state"), "score": r.get("score"),
        "structure_extremity": r.get("structure_extremity"), "v01_score": r.get("v01_score"), "v01_state": r.get("v01_state"),
        "v02_score": r.get("v02_score"), "v02_state": r.get("v02_state"), "agreement_state": r.get("agreement_state"),
        "forward_7d_percent": r.get("fwd_7d"), "directional_7d_percent": r.get("dir_7d"),
        "volatility_30d": r.get("volatility_30d"), "drawdown_90d": r.get("drawdown_90d"),
        "market_risk_proxy": r.get("market_risk_proxy"), "vol_regime": r.get("vol_regime"),
        "drawdown_regime": r.get("drawdown_regime"), "guardrail_codes": r.get("guardrail_codes"),
    } for r in failures[:20]]

    diagnostic_flags = flags(summary, development, reused, per_asset, regimes, agreement["overall"])
    artifact = {
        "version": "3.0",
        "status": "CRYPTO_V03_HYBRID_RETEST_COMPLETE_REQUIRES_11C5_REVIEW",
        "scope": decision.get("scope"),
        "generated_at": now_iso(),
        "model_snapshot": {
            "version": decision.get("version"),
            "model_status": decision.get("model_status"),
            "frozen": False,
            "methodology_sha256": bt.canonical_hash(decision.get("methodology") or {}),
            "hybrid_refinement": decision.get("hybrid_refinement"),
        },
        "test_design": {
            "historical_window_days": HISTORY_DAYS,
            "warmup_days": WARMUP_DAYS,
            "forward_horizons_days": list(FORWARD_HORIZONS),
            "chronological_split": "70_PERCENT_DEVELOPMENT_30_PERCENT_REUSED_DIAGNOSTIC_WINDOW",
            "split_date": split_date,
            "last_30_percent_status": "CONSUMED_REUSED_DIAGNOSTIC_NOT_UNTOUCHED_HOLDOUT",
            "hybrid_weights": model.HYBRID_WEIGHTS,
            "hybrid_weight_search": "PROHIBITED",
            "threshold_search": "PROHIBITED",
            "production_market_structure_reused_directly": True,
            "historical_protocol_regulatory_network_state_not_backfilled": True,
        },
        "summary": summary,
        "development": development,
        "reused_diagnostic_window": reused,
        "per_asset": per_asset,
        "regimes": regimes,
        "agreement_diagnostics": agreement,
        "extremity_diagnostics": extremity,
        "comparison": {
            "v01_overall": prior1.get("summary"),
            "v01_consumed_holdout": prior1.get("diagnostic_holdout"),
            "v02_overall": prior2.get("summary"),
            "v02_reused_diagnostic_window": prior2.get("reused_diagnostic_window"),
            "all_comparisons_are_diagnostic_not_new_oos": True,
        },
        "failure_cases": failure_cases,
        "diagnostic_flags": diagnostic_flags,
        "guardrails": {
            "diagnostic_only": True,
            "no_lookahead": True,
            "no_hybrid_weight_search": True,
            "no_threshold_optimization": True,
            "same_historical_window_is_consumed": True,
            "fresh_oos_remains_primary_validation": True,
            "no_buy_sell": True,
            "no_profit_probability": True,
            "trade_execution": "OFF",
        },
        "next_gate": "11C5_PRE_FREEZE_CROSS_CHECK_REQUIRED_AFTER_V03_REVIEW",
    }
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"v0.3 hybrid retest: observations={summary.get('observations')}; directional={summary.get('directional_observations')}; reused7d={reused.get('hit_rate_7d_percent')}; flags={len(diagnostic_flags)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
