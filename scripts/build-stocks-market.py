#!/usr/bin/env python3
"""Build Stocks 10B daily market-data artifact from Alpha Vantage.

Stage 10B is intentionally market-data only. It does NOT create BUY/SELL calls,
Decision Readiness, risk scores, or final reasoning. Those belong to Stage 10C.

Required environment:
  ALPHA_VANTAGE_API_KEY=<your key>

The adapter uses TIME_SERIES_DAILY with outputsize=compact and publishes only the
latest OHLCV bar plus derived short-horizon statistics. It does not republish the
full provider time series.
"""

from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "data" / "stocks-config.json"
OUTPUT_PATH = ROOT / "data" / "stocks-market-data.json"
API_BASE = "https://www.alphavantage.co/query"
REQUEST_INTERVAL_SECONDS = 3.0


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def request_daily(symbol: str, api_key: str) -> Dict[str, Any]:
    query = urllib.parse.urlencode(
        {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "compact",
            "datatype": "json",
            "apikey": api_key,
        }
    )
    req = urllib.request.Request(
        f"{API_BASE}?{query}",
        headers={"User-Agent": "Best Currency AI market-data adapter"},
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Alpha Vantage HTTP {exc.code} for {symbol}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Alpha Vantage network error for {symbol}: {exc.reason}") from exc

    for key in ("Error Message", "Note", "Information"):
        if payload.get(key):
            raise RuntimeError(f"Alpha Vantage {key}: {payload[key]}")
    if "Time Series (Daily)" not in payload:
        raise RuntimeError(f"Alpha Vantage daily series missing for {symbol}")
    return payload


def fnum(value: Any) -> float:
    return float(str(value).replace(",", ""))


def parse_bars(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    series = payload.get("Time Series (Daily)") or {}
    bars: List[Dict[str, Any]] = []
    for session, row in series.items():
        try:
            bars.append(
                {
                    "session": session,
                    "open": fnum(row.get("1. open")),
                    "high": fnum(row.get("2. high")),
                    "low": fnum(row.get("3. low")),
                    "close": fnum(row.get("4. close")),
                    "volume": int(float(row.get("5. volume"))),
                }
            )
        except (TypeError, ValueError):
            continue
    bars.sort(key=lambda x: x["session"], reverse=True)
    if not bars:
        raise RuntimeError("No parseable daily OHLCV bars returned")
    return bars


def pct_change(latest: float, previous: Optional[float]) -> Optional[float]:
    if previous in (None, 0):
        return None
    return round((latest / previous - 1.0) * 100.0, 2)


def mean(values: List[float]) -> Optional[float]:
    return round(sum(values) / len(values), 4) if values else None


def annualized_volatility_20d(bars: List[Dict[str, Any]]) -> Optional[float]:
    if len(bars) < 21:
        return None
    returns = []
    for i in range(20):
        newer = bars[i]["close"]
        older = bars[i + 1]["close"]
        if newer > 0 and older > 0:
            returns.append(math.log(newer / older))
    if len(returns) < 2:
        return None
    return round(statistics.stdev(returns) * math.sqrt(252) * 100.0, 2)


def build_symbol(entry: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    ticker = entry["ticker"]
    payload = request_daily(ticker, api_key)
    bars = parse_bars(payload)
    latest = bars[0]
    closes = [b["close"] for b in bars]
    volumes = [b["volume"] for b in bars]

    sma20 = mean(closes[:20]) if len(closes) >= 20 else None
    sma50 = mean(closes[:50]) if len(closes) >= 50 else None
    avg_volume20 = mean([float(v) for v in volumes[:20]]) if len(volumes) >= 20 else None
    high20 = max((b["high"] for b in bars[:20]), default=None)
    low20 = min((b["low"] for b in bars[:20]), default=None)
    range20 = pct_change(high20, low20) if high20 is not None and low20 is not None else None

    latest_close = latest["close"]
    session_date = date.fromisoformat(latest["session"])
    freshness_days = (date.today() - session_date).days
    meta = payload.get("Meta Data") or {}

    return {
        "ticker": ticker,
        "name": entry.get("name"),
        "exchange": entry.get("exchange"),
        "source": {
            "provider": "Alpha Vantage",
            "function": "TIME_SERIES_DAILY",
            "mode": "HISTORICAL_DAILY_RAW_OHLCV",
            "provider_last_refreshed": meta.get("3. Last Refreshed"),
            "provider_time_zone": meta.get("5. Time Zone"),
            "full_raw_series_published": False,
        },
        "freshness": {
            "latest_market_session": latest["session"],
            "calendar_days_since_latest_session": freshness_days,
        },
        "latest_bar": latest,
        "derived_market_context": {
            "return_1d_percent": pct_change(latest_close, closes[1] if len(closes) > 1 else None),
            "return_5d_percent": pct_change(latest_close, closes[5] if len(closes) > 5 else None),
            "return_20d_percent": pct_change(latest_close, closes[20] if len(closes) > 20 else None),
            "sma_20": sma20,
            "sma_50": sma50,
            "close_vs_sma20_percent": pct_change(latest_close, sma20),
            "close_vs_sma50_percent": pct_change(latest_close, sma50),
            "annualized_volatility_20d_percent": annualized_volatility_20d(bars),
            "average_volume_20d": round(avg_volume20) if avg_volume20 is not None else None,
            "latest_volume_vs_20d_average_ratio": round(latest["volume"] / avg_volume20, 2) if avg_volume20 not in (None, 0) else None,
            "high_low_range_20d_percent": range20,
        },
        "data_quality": {
            "bars_received": len(bars),
            "minimum_for_50d_context_met": len(bars) >= 50,
            "price_adjustment": "RAW_AS_TRADED_UNADJUSTED",
            "corporate_action_caution": "Split/dividend adjustment is not included in 10B v1; long-horizon inference remains constrained.",
        },
        "decision_state": {
            "market_data_status": "DAILY_OHLCV_READY",
            "market_view": "DEFERRED_TO_STAGE_10C",
            "buy_sell": "NOT_GENERATED",
            "trade_execution": "OFF",
        },
    }


def main() -> int:
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
    if not api_key:
        print("ALPHA_VANTAGE_API_KEY is required", file=sys.stderr)
        return 2

    config = load_json(CONFIG_PATH)
    symbols: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for index, entry in enumerate(config.get("watchlist", [])):
        ticker = entry.get("ticker")
        try:
            print(f"Alpha Vantage daily: {ticker}")
            symbols.append(build_symbol(entry, api_key))
        except Exception as exc:
            errors.append({"ticker": ticker, "error": str(exc)})
        if index < len(config.get("watchlist", [])) - 1:
            time.sleep(REQUEST_INTERVAL_SECONDS)

    if symbols and not errors:
        status = "DAILY_MARKET_DATA_READY"
    elif symbols:
        status = "PARTIAL"
    else:
        status = "UNAVAILABLE"

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    artifact = {
        "version": "1.0",
        "status": status,
        "scope": config.get("scope"),
        "generated_at": generated_at,
        "provider": {
            "name": "Alpha Vantage",
            "function": "TIME_SERIES_DAILY",
            "mode": "HISTORICAL_DAILY_RAW_OHLCV",
            "outputsize": "compact",
            "entitlement": "historical_default",
            "requests_this_run": len(config.get("watchlist", [])),
        },
        "source_readiness": {
            "daily_ohlcv": status,
            "realtime": "DISABLED",
            "delayed_15m": "DISABLED",
            "adjusted_prices": "NOT_INCLUDED_IN_10B_V1",
            "decision_intelligence": "DEFERRED_TO_STAGE_10C",
        },
        "guardrails": {
            "raw_series_not_published": True,
            "derived_metrics_only_plus_latest_bar": True,
            "as_traded_unadjusted_prices": True,
            "corporate_action_adjustment_required_before_long_horizon_inference": True,
            "realtime_claims_prohibited": True,
            "no_buy_sell_from_market_data_alone": True,
            "provider_terms_apply": True,
            "trade_execution": "OFF",
        },
        "symbols": symbols,
        "errors": errors,
    }
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)} with status {status}")
    return 0 if symbols else 1


if __name__ == "__main__":
    raise SystemExit(main())
