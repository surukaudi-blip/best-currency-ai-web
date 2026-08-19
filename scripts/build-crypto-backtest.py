#!/usr/bin/env python3
"""Stage 11C.4 — Historical Backtest for Crypto Decision Intelligence.

Purpose
-------
Diagnostic historical evaluation of the *directional Market View* used by Stage 11C.
The current 11C direction is intentionally based only on completed UTC market data,
so this backtest does not invent historical protocol, regulatory, or network states.
Those evidence layers remain subject to operational QA in 11C.5 and prospective OOS
validation after a future freeze.

Guardrails
----------
- Keyed CoinGecko server-side access only.
- 365-day window for plan-neutral reproducibility.
- No look-ahead: every signal uses data available at or before its anchor day.
- Forward returns are used only after the signal state is computed.
- No parameter optimization or automatic threshold selection.
- Chronological 70/30 development / diagnostic-holdout split.
- Holdout is diagnostic historical evidence, NOT Fresh OOS.
- Raw historical price series are never written to the public artifact.
- No BUY/SELL, no profit probability, trade execution OFF.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_PATH = ROOT / "data" / "crypto-universe.json"
DECISION_PATH = ROOT / "data" / "crypto-decision-intelligence.json"
OUTPUT_PATH = ROOT / "data" / "crypto-backtest.json"

DEMO_KEY = os.getenv("COINGECKO_DEMO_API_KEY", "").strip()
PRO_KEY = os.getenv("COINGECKO_PRO_API_KEY", "").strip()

if PRO_KEY:
    API_MODE = "PRO"
    BASE_URL = "https://pro-api.coingecko.com/api/v3"
    AUTH_HEADER = {"x-cg-pro-api-key": PRO_KEY}
elif DEMO_KEY:
    API_MODE = "DEMO"
    BASE_URL = "https://api.coingecko.com/api/v3"
    AUTH_HEADER = {"x-cg-demo-api-key": DEMO_KEY}
else:
    raise SystemExit("Missing COINGECKO_DEMO_API_KEY or COINGECKO_PRO_API_KEY. Backtest fails closed.")

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Best-Currency-AI/Stage11C4-Backtest",
    **AUTH_HEADER,
}
MIN_REQUEST_INTERVAL_SECONDS = 2.2 if API_MODE == "DEMO" else 0.15
_LAST_REQUEST_AT = 0.0
HISTORY_DAYS = 365
WARMUP_DAYS = 90
FORWARD_HORIZONS = (1, 3, 7)
SENSITIVITY_THRESHOLDS = (
    (60.0, 40.0),
    (62.0, 38.0),
    (65.0, 35.0),
    (68.0, 32.0),
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def throttle() -> None:
    global _LAST_REQUEST_AT
    wait = (_LAST_REQUEST_AT + MIN_REQUEST_INTERVAL_SECONDS) - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _LAST_REQUEST_AT = time.monotonic()


def fetch_json(path: str, params: Optional[Dict[str, Any]] = None, retries: int = 4) -> Any:
    qs = urllib.parse.urlencode(params or {}, doseq=True)
    url = f"{BASE_URL}{path}" + (f"?{qs}" if qs else "")
    last_error: Optional[Exception] = None
    for attempt in range(retries):
        throttle()
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=40) as res:
                return json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 429 or 500 <= exc.code < 600:
                time.sleep(min(16, 2 ** attempt))
                continue
            body = exc.read().decode("utf-8", errors="replace")[:400]
            raise RuntimeError(f"CoinGecko HTTP {exc.code}: {body}") from exc
        except Exception as exc:
            last_error = exc
            time.sleep(min(16, 2 ** attempt))
    raise RuntimeError(f"CoinGecko request failed after retries: {last_error}")


def fnum(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def pct_return(latest: float, prior: float) -> Optional[float]:
    if prior == 0:
        return None
    return (latest / prior - 1.0) * 100.0


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def mean(values: Sequence[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def median(values: Sequence[float]) -> Optional[float]:
    return statistics.median(values) if values else None


def safe_round(value: Optional[float], digits: int = 2) -> Optional[float]:
    return round(float(value), digits) if value is not None else None


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def daily_map(points: List[List[Any]]) -> Dict[str, float]:
    today = utc_now().date()
    out: Dict[str, float] = {}
    for row in points or []:
        if not isinstance(row, list) or len(row) < 2:
            continue
        try:
            dt = datetime.fromtimestamp(float(row[0]) / 1000.0, tz=timezone.utc)
            val = float(row[1])
        except (TypeError, ValueError, OSError):
            continue
        if dt.date() >= today:
            continue
        out[dt.date().isoformat()] = val
    return out


def signed_score(value: Optional[float], span: float) -> Optional[float]:
    if value is None:
        return None
    return clamp(50.0 + 50.0 * float(value) / float(span))


def weighted_available(parts: Iterable[Tuple[Optional[float], float]]) -> Optional[float]:
    rows = [(score, weight) for score, weight in parts if score is not None]
    total = sum(weight for _, weight in rows)
    if total <= 0:
        return None
    return sum(float(score) * weight for score, weight in rows) / total


def state_for(score: Optional[float], supportive_gte: float, pressured_lte: float) -> str:
    if score is None:
        return "UNAVAILABLE"
    if score >= supportive_gte:
        return "SUPPORTIVE"
    if score <= pressured_lte:
        return "PRESSURED"
    return "MIXED"


def volatility_30(prices: Sequence[float], i: int) -> Optional[float]:
    if i < 30:
        return None
    window = prices[i - 30 : i + 1]
    log_returns: List[float] = []
    for a, b in zip(window[:-1], window[1:]):
        if a > 0 and b > 0:
            log_returns.append(math.log(b / a))
    if len(log_returns) < 20:
        return None
    return statistics.pstdev(log_returns) * math.sqrt(365) * 100.0


def drawdown_90(prices: Sequence[float], i: int) -> Optional[float]:
    start = max(0, i - 89)
    window = prices[start : i + 1]
    if not window:
        return None
    peak = max(window)
    return pct_return(prices[i], peak)


def horizon_conflict(return_7d: Optional[float], return_30d: Optional[float], vs20: Optional[float], vs50: Optional[float]) -> Tuple[int, float]:
    vals = [return_7d, return_30d, vs20, vs50]
    signs = [1 if v > 0 else (-1 if v < 0 else 0) for v in vals if v is not None]
    pos = sum(1 for x in signs if x > 0)
    neg = sum(1 for x in signs if x < 0)
    conflict = min(pos, neg)
    return conflict, {0: 20.0, 1: 50.0, 2: 75.0}.get(conflict, 75.0)


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


def participation_score(volumes: Sequence[Optional[float]], i: int) -> Optional[float]:
    if i < 29:
        return None
    v7 = [float(v) for v in volumes[max(0, i - 6) : i + 1] if v is not None]
    v30 = [float(v) for v in volumes[max(0, i - 29) : i + 1] if v is not None]
    if len(v7) < 5 or len(v30) < 20:
        return None
    a7, a30 = mean(v7), mean(v30)
    if a7 is None or a30 in (None, 0):
        return None
    ratio = a7 / a30
    if ratio >= 1.25:
        return 90.0
    if ratio >= 0.90:
        return 80.0
    if ratio >= 0.70:
        return 65.0
    if ratio >= 0.50:
        return 50.0
    return 35.0


def vol_regime(v: Optional[float]) -> str:
    if v is None:
        return "UNKNOWN"
    if v < 45:
        return "LOW_VOL"
    if v < 75:
        return "MODERATE_VOL"
    return "HIGH_VOL"


def drawdown_regime(dd: Optional[float]) -> str:
    if dd is None:
        return "UNKNOWN"
    if dd <= -30:
        return "STRESSED_DRAWDOWN"
    if dd <= -15:
        return "MATERIAL_DRAWDOWN"
    return "NORMAL_DRAWDOWN"


def build_rows_for_asset(asset: Dict[str, Any], methodology: Dict[str, Any]) -> List[Dict[str, Any]]:
    asset_id = asset["id"]
    chart = fetch_json(
        f"/coins/{urllib.parse.quote(asset_id)}/market_chart",
        {"vs_currency": "usd", "days": HISTORY_DAYS, "precision": "full"},
    )
    pmap = daily_map(chart.get("prices") or [])
    vmap = daily_map(chart.get("total_volumes") or [])
    dates = sorted(pmap)
    if len(dates) < 150:
        raise ValueError(f"{asset_id}: insufficient completed daily history ({len(dates)})")
    prices = [pmap[d] for d in dates]
    volumes = [vmap.get(d) for d in dates]

    market_cfg = methodology.get("market_structure") or {}
    weights = market_cfg.get("weights") or {
        "return_30d": 0.30,
        "close_vs_sma20": 0.25,
        "close_vs_sma50": 0.30,
        "return_7d": 0.15,
    }
    spans = market_cfg.get("score_spans_percent") or {
        "return_30d": 25,
        "close_vs_sma20": 12,
        "close_vs_sma50": 20,
        "return_7d": 12,
    }
    thresholds = market_cfg.get("state_thresholds") or {}
    supportive_gte = float(thresholds.get("supportive_gte", 62))
    pressured_lte = float(thresholds.get("pressured_lte", 38))

    rows: List[Dict[str, Any]] = []
    last_anchor = len(dates) - max(FORWARD_HORIZONS) - 1
    for i in range(WARMUP_DAYS, last_anchor + 1):
        latest = prices[i]
        r7 = pct_return(latest, prices[i - 7]) if i >= 7 else None
        r30 = pct_return(latest, prices[i - 30]) if i >= 30 else None
        sma20 = mean(prices[i - 19 : i + 1]) if i >= 19 else None
        sma50 = mean(prices[i - 49 : i + 1]) if i >= 49 else None
        vs20 = pct_return(latest, sma20) if sma20 not in (None, 0) else None
        vs50 = pct_return(latest, sma50) if sma50 not in (None, 0) else None
        comps = {
            "return_30d": signed_score(r30, float(spans["return_30d"])),
            "close_vs_sma20": signed_score(vs20, float(spans["close_vs_sma20"])),
            "close_vs_sma50": signed_score(vs50, float(spans["close_vs_sma50"])),
            "return_7d": signed_score(r7, float(spans["return_7d"])),
        }
        score = weighted_available((comps[k], float(weights[k])) for k in weights)
        state = state_for(score, supportive_gte, pressured_lte)
        vol30 = volatility_30(prices, i)
        dd90 = drawdown_90(prices, i)
        r1 = pct_return(latest, prices[i - 1]) if i >= 1 else None
        conflict_count, conflict_risk = horizon_conflict(r7, r30, vs20, vs50)
        one_day_risk = clamp(abs(r1 or 0.0) / 10.0 * 100.0)
        market_risk_proxy = weighted_available(
            [
                (volatility_risk(vol30), 0.30),
                (drawdown_risk(dd90), 0.20),
                (one_day_risk, 0.15),
                (conflict_risk, 0.10),
            ]
        )
        fwd = {
            h: pct_return(prices[i + h], latest)
            for h in FORWARD_HORIZONS
        }
        direction_sign = 1 if state == "SUPPORTIVE" else (-1 if state == "PRESSURED" else 0)
        directional = {
            h: (fwd[h] * direction_sign if direction_sign else None)
            for h in FORWARD_HORIZONS
        }
        hits = {
            h: (directional[h] > 0 if directional[h] is not None else None)
            for h in FORWARD_HORIZONS
        }
        rows.append(
            {
                "date": dates[i],
                "asset": asset.get("symbol"),
                "asset_id": asset_id,
                "score": safe_round(score),
                "state": state,
                "clarity": safe_round(abs((score or 50.0) - 50.0) * 2.0),
                "return_7d": safe_round(r7, 4),
                "return_30d": safe_round(r30, 4),
                "close_vs_sma20": safe_round(vs20, 4),
                "close_vs_sma50": safe_round(vs50, 4),
                "volatility_30d": safe_round(vol30, 4),
                "drawdown_90d": safe_round(dd90, 4),
                "horizon_conflict_count": conflict_count,
                "market_risk_proxy": safe_round(market_risk_proxy),
                "market_participation_proxy": safe_round(participation_score(volumes, i)),
                "vol_regime": vol_regime(vol30),
                "drawdown_regime": drawdown_regime(dd90),
                "fwd_1d": safe_round(fwd[1], 4),
                "fwd_3d": safe_round(fwd[3], 4),
                "fwd_7d": safe_round(fwd[7], 4),
                "dir_1d": safe_round(directional[1], 4),
                "dir_3d": safe_round(directional[3], 4),
                "dir_7d": safe_round(directional[7], 4),
                "hit_1d": hits[1],
                "hit_3d": hits[3],
                "hit_7d": hits[7],
            }
        )
    return rows


def avg(values: List[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def summarize(rows: List[Dict[str, Any]], supportive_gte: Optional[float] = None, pressured_lte: Optional[float] = None) -> Dict[str, Any]:
    if supportive_gte is not None and pressured_lte is not None:
        working = []
        for row in rows:
            r = dict(row)
            r["state"] = state_for(fnum(r.get("score")), supportive_gte, pressured_lte)
            sign = 1 if r["state"] == "SUPPORTIVE" else (-1 if r["state"] == "PRESSURED" else 0)
            for h in FORWARD_HORIZONS:
                raw = fnum(r.get(f"fwd_{h}d"))
                d = raw * sign if raw is not None and sign else None
                r[f"dir_{h}d"] = d
                r[f"hit_{h}d"] = (d > 0) if d is not None else None
            working.append(r)
        rows = working

    states = Counter(r.get("state") for r in rows)
    directional = [r for r in rows if r.get("state") in {"SUPPORTIVE", "PRESSURED"}]
    result: Dict[str, Any] = {
        "observations": len(rows),
        "state_counts": {
            "SUPPORTIVE": states.get("SUPPORTIVE", 0),
            "MIXED": states.get("MIXED", 0),
            "PRESSURED": states.get("PRESSURED", 0),
        },
        "directional_observations": len(directional),
        "directional_coverage_percent": safe_round((len(directional) / len(rows) * 100.0) if rows else None),
    }
    for h in FORWARD_HORIZONS:
        hits = [bool(r[f"hit_{h}d"]) for r in directional if r.get(f"hit_{h}d") is not None]
        dreturns = [float(r[f"dir_{h}d"]) for r in directional if r.get(f"dir_{h}d") is not None]
        result[f"hit_rate_{h}d_percent"] = safe_round(sum(hits) / len(hits) * 100.0 if hits else None)
        result[f"avg_directional_return_{h}d_percent"] = safe_round(avg(dreturns), 4)
        result[f"median_directional_return_{h}d_percent"] = safe_round(median(dreturns), 4)
    for state in ("SUPPORTIVE", "PRESSURED", "MIXED"):
        state_rows = [r for r in rows if r.get("state") == state]
        result[f"{state.lower()}_avg_forward_7d_percent"] = safe_round(
            avg([float(r["fwd_7d"]) for r in state_rows if r.get("fwd_7d") is not None]), 4
        )
    high_clarity = [r for r in directional if (fnum(r.get("clarity")) or 0.0) >= 50.0 and r.get("hit_7d") is not None]
    high_misses = [r for r in high_clarity if r.get("hit_7d") is False]
    result["high_clarity_directional_n"] = len(high_clarity)
    result["high_clarity_7d_miss_rate_percent"] = safe_round(
        len(high_misses) / len(high_clarity) * 100.0 if high_clarity else None
    )
    return result


def summarize_grouped(rows: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key) or "UNKNOWN")].append(row)
    return {name: summarize(group) for name, group in sorted(groups.items())}


def chronological_split(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
    dates = sorted({r["date"] for r in rows})
    if len(dates) < 20:
        return rows, [], None
    cut_index = max(1, min(len(dates) - 1, int(len(dates) * 0.70)))
    cut_date = dates[cut_index]
    dev = [r for r in rows if r["date"] < cut_date]
    hold = [r for r in rows if r["date"] >= cut_date]
    return dev, hold, cut_date


def diagnostic_flags(
    overall: Dict[str, Any],
    dev: Dict[str, Any],
    hold: Dict[str, Any],
    sensitivity: List[Dict[str, Any]],
    regime_summary: Dict[str, Any],
) -> List[Dict[str, str]]:
    flags: List[Dict[str, str]] = []
    hold_n = int(hold.get("directional_observations") or 0)
    hold_hit = fnum(hold.get("hit_rate_7d_percent"))
    dev_hit = fnum(dev.get("hit_rate_7d_percent"))
    coverage = fnum(overall.get("directional_coverage_percent"))
    miss = fnum(overall.get("high_clarity_7d_miss_rate_percent"))

    if hold_n >= 40 and hold_hit is not None and hold_hit < 50:
        flags.append({"severity": "HIGH", "code": "HOLDOUT_7D_BELOW_50", "message": "Diagnostic holdout 7-day directional hit rate is below 50%."})
    if hold_hit is not None and dev_hit is not None and abs(hold_hit - dev_hit) >= 10:
        flags.append({"severity": "MODERATE", "code": "DEV_HOLDOUT_GAP_10PP", "message": "Development and diagnostic-holdout 7-day hit rates differ by at least 10 percentage points."})
    if coverage is not None and coverage < 10:
        flags.append({"severity": "MODERATE", "code": "DIRECTIONAL_COVERAGE_LOW", "message": "Directional states cover less than 10% of historical observations."})
    if coverage is not None and coverage > 70:
        flags.append({"severity": "MODERATE", "code": "DIRECTIONAL_COVERAGE_HIGH", "message": "Directional states cover more than 70% of historical observations; thresholds may be too permissive."})
    if miss is not None and miss >= 45:
        flags.append({"severity": "HIGH", "code": "HIGH_CLARITY_MISS_RATE_HIGH", "message": "High-clarity directional observations miss the 7-day direction at least 45% of the time."})

    sens_hits = [fnum(x.get("diagnostic_holdout", {}).get("hit_rate_7d_percent")) for x in sensitivity]
    sens_hits = [x for x in sens_hits if x is not None]
    if len(sens_hits) >= 2 and max(sens_hits) - min(sens_hits) >= 10:
        flags.append({"severity": "MODERATE", "code": "THRESHOLD_SENSITIVITY_HIGH", "message": "Holdout 7-day hit rate varies by at least 10 percentage points across nearby threshold settings."})

    for regime, metrics in (regime_summary.get("volatility") or {}).items():
        n = int(metrics.get("directional_observations") or 0)
        hit = fnum(metrics.get("hit_rate_7d_percent"))
        if n >= 40 and hit is not None and hit < 47:
            flags.append({"severity": "MODERATE", "code": f"WEAK_{regime}", "message": f"7-day directional hit rate is weak in {regime} with a meaningful sample."})
    return flags


def main() -> int:
    universe = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    if decision.get("status") != "CRYPTO_DECISION_INTELLIGENCE_READY":
        raise SystemExit("Stage 11C decision intelligence is not READY; backtest fails closed.")
    if decision.get("frozen") is True:
        raise SystemExit("Stage 11C is already frozen; 11C.4 is intended to run before freeze.")

    methodology = decision.get("methodology") or {}
    methodology_hash = canonical_hash(methodology)
    assets_cfg = universe.get("assets") or []
    all_rows: List[Dict[str, Any]] = []
    asset_errors: List[Dict[str, str]] = []

    for asset in assets_cfg:
        try:
            rows = build_rows_for_asset(asset, methodology)
            all_rows.extend(rows)
            print(f"{asset.get('symbol')}: {len(rows)} backtest observations")
        except Exception as exc:
            asset_errors.append({"asset": str(asset.get("symbol") or asset.get("id")), "error": str(exc)[:500]})

    if asset_errors:
        raise SystemExit("Backtest fails closed because one or more assets failed: " + json.dumps(asset_errors))
    if not all_rows:
        raise SystemExit("No backtest observations were generated.")

    all_rows.sort(key=lambda r: (r["date"], r["asset"]))
    dev_rows, hold_rows, split_date = chronological_split(all_rows)
    overall = summarize(all_rows)
    dev = summarize(dev_rows)
    hold = summarize(hold_rows)

    per_asset = []
    for symbol in [a.get("symbol") for a in assets_cfg]:
        rows = [r for r in all_rows if r.get("asset") == symbol]
        drows = [r for r in dev_rows if r.get("asset") == symbol]
        hrows = [r for r in hold_rows if r.get("asset") == symbol]
        per_asset.append(
            {
                "asset": symbol,
                "overall": summarize(rows),
                "development": summarize(drows),
                "diagnostic_holdout": summarize(hrows),
            }
        )

    sensitivity = []
    for sup, prs in SENSITIVITY_THRESHOLDS:
        sensitivity.append(
            {
                "supportive_gte": sup,
                "pressured_lte": prs,
                "is_current_baseline": sup == 62.0 and prs == 38.0,
                "overall": summarize(all_rows, sup, prs),
                "development": summarize(dev_rows, sup, prs),
                "diagnostic_holdout": summarize(hold_rows, sup, prs),
            }
        )

    regimes = {
        "volatility": summarize_grouped(all_rows, "vol_regime"),
        "drawdown": summarize_grouped(all_rows, "drawdown_regime"),
    }

    directional_failures = [
        r for r in all_rows
        if r.get("state") in {"SUPPORTIVE", "PRESSURED"} and r.get("hit_7d") is False
    ]
    directional_failures.sort(
        key=lambda r: (
            -(fnum(r.get("clarity")) or 0.0),
            fnum(r.get("dir_7d")) or 0.0,
        )
    )
    failure_cases = [
        {
            "date": r.get("date"),
            "asset": r.get("asset"),
            "state": r.get("state"),
            "score": r.get("score"),
            "clarity": r.get("clarity"),
            "forward_7d_percent": r.get("fwd_7d"),
            "directional_7d_percent": r.get("dir_7d"),
            "volatility_30d": r.get("volatility_30d"),
            "drawdown_90d": r.get("drawdown_90d"),
            "market_risk_proxy": r.get("market_risk_proxy"),
            "vol_regime": r.get("vol_regime"),
            "drawdown_regime": r.get("drawdown_regime"),
        }
        for r in directional_failures[:20]
    ]

    flags = diagnostic_flags(overall, dev, hold, sensitivity, regimes)
    artifact = {
        "version": "1.0",
        "status": "CRYPTO_BACKTEST_COMPLETE_REQUIRES_11C5_REVIEW",
        "scope": decision.get("scope"),
        "generated_at": iso_now(),
        "provider": {
            "name": "CoinGecko",
            "api_mode": API_MODE,
            "endpoint": "/coins/{id}/market_chart",
            "requested_history_days": HISTORY_DAYS,
            "raw_series_published": False,
        },
        "model_snapshot": {
            "model_status": decision.get("model_status"),
            "frozen": False,
            "methodology_sha256": methodology_hash,
            "current_market_session_at_test_time": decision.get("market_session"),
            "market_structure_methodology": methodology.get("market_structure"),
        },
        "test_design": {
            "historical_window_days": HISTORY_DAYS,
            "warmup_days": WARMUP_DAYS,
            "forward_horizons_days": list(FORWARD_HORIZONS),
            "chronological_split": "70_PERCENT_DEVELOPMENT_30_PERCENT_DIAGNOSTIC_HOLDOUT",
            "split_date": split_date,
            "holdout_classification": "HISTORICAL_DIAGNOSTIC_NOT_FRESH_OOS",
            "directional_states_scored": ["SUPPORTIVE", "PRESSURED"],
            "mixed_state_scored_directionally": False,
            "historical_evidence_policy": "Protocol/regulatory/network states are not reconstructed backward because they are non-directional 11B evidence and reliable point-in-time snapshots were not collected historically.",
            "market_risk_proxy_policy": "Only historically reconstructible market-derived risk components are shown; this proxy is not the full 11C Decision Risk score.",
        },
        "summary": overall,
        "development": dev,
        "diagnostic_holdout": hold,
        "per_asset": per_asset,
        "regimes": regimes,
        "threshold_sensitivity": sensitivity,
        "failure_cases": failure_cases,
        "diagnostic_flags": flags,
        "guardrails": {
            "diagnostic_only": True,
            "no_lookahead": True,
            "no_test_set_tuning": True,
            "no_outcome_optimization": True,
            "market_view_direction_only": True,
            "historical_protocol_regulatory_network_state_not_backfilled": True,
            "holdout_is_not_fresh_oos": True,
            "fresh_oos_remains_primary_validation": True,
            "no_buy_sell": True,
            "no_profit_probability": True,
            "trade_execution": "OFF",
        },
        "next_gate": "11C5_PRE_FREEZE_CROSS_CHECK_REQUIRED",
    }
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        "11C.4 complete: "
        f"observations={overall['observations']}, "
        f"directional={overall['directional_observations']}, "
        f"holdout_7d_hit={hold.get('hit_rate_7d_percent')}, "
        f"flags={len(flags)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
