#!/usr/bin/env python3
"""Build Stage 11A Crypto Market Data from CoinGecko.

Guardrails:
- Server-side keyed access only (Demo or Pro).
- Publishes derived metrics, not the raw historical response.
- Completed daily-session metrics use UTC days strictly before today.
- No BUY/SELL, news, protocol evidence, or profit probability.
"""

from __future__ import annotations

import json
import math
import os
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_PATH = ROOT / "data" / "crypto-universe.json"
OUTPUT_PATH = ROOT / "data" / "crypto-market-data.json"

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
    raise SystemExit("Missing COINGECKO_DEMO_API_KEY or COINGECKO_PRO_API_KEY. Stage 11A fails closed.")

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Best-Currency-AI/Stage11A",
    **AUTH_HEADER,
}
MIN_REQUEST_INTERVAL_SECONDS = 2.2 if API_MODE == "DEMO" else 0.15
_LAST_REQUEST_AT = 0.0


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return now_utc().isoformat().replace("+00:00", "Z")


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
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 429 or 500 <= exc.code < 600:
                time.sleep(min(12, 2 ** attempt))
                continue
            body = exc.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"CoinGecko HTTP {exc.code}: {body}") from exc
        except Exception as exc:
            last_error = exc
            time.sleep(min(12, 2 ** attempt))
    raise RuntimeError(f"CoinGecko request failed after retries: {last_error}")


def as_float(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def pct_return(latest: float, prior: float) -> Optional[float]:
    if prior == 0:
        return None
    return round((latest / prior - 1.0) * 100.0, 4)


def mean(values: List[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def daily_map(points: List[List[Any]]) -> Dict[str, float]:
    today = now_utc().date()
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


def derive_history(chart: Dict[str, Any]) -> Dict[str, Any]:
    prices_by_date = daily_map(chart.get("prices") or [])
    caps_by_date = daily_map(chart.get("market_caps") or [])
    vols_by_date = daily_map(chart.get("total_volumes") or [])
    dates = sorted(prices_by_date)
    if len(dates) < 55:
        raise ValueError(f"Insufficient completed daily history: {len(dates)} observations")

    prices = [prices_by_date[d] for d in dates]
    latest = prices[-1]

    def ret(days: int) -> Optional[float]:
        if len(prices) <= days:
            return None
        return pct_return(latest, prices[-(days + 1)])

    sma20 = mean(prices[-20:])
    sma50 = mean(prices[-50:])

    log_returns: List[float] = []
    for a, b in zip(prices[-31:-1], prices[-30:]):
        if a > 0 and b > 0:
            log_returns.append(math.log(b / a))
    vol30 = statistics.pstdev(log_returns) * math.sqrt(365) * 100 if len(log_returns) >= 20 else None

    max90 = max(prices[-90:]) if prices[-90:] else latest
    drawdown90 = pct_return(latest, max90)

    aligned_vols = [vols_by_date.get(d) for d in dates if vols_by_date.get(d) is not None]
    vol7 = mean([float(v) for v in aligned_vols[-7:]]) if len(aligned_vols) >= 7 else None
    vol30avg = mean([float(v) for v in aligned_vols[-30:]]) if len(aligned_vols) >= 30 else None
    volume_ratio = round(vol7 / vol30avg, 4) if vol7 is not None and vol30avg not in (None, 0) else None

    latest_cap = caps_by_date.get(dates[-1])
    latest_vol = vols_by_date.get(dates[-1])
    turnover = round(latest_vol / latest_cap, 6) if latest_cap not in (None, 0) and latest_vol is not None else None

    return {
        "completed_session": dates[-1],
        "completed_close_usd": round(latest, 8),
        "completed_market_cap_usd": round(latest_cap, 2) if latest_cap is not None else None,
        "completed_volume_usd": round(latest_vol, 2) if latest_vol is not None else None,
        "history_observations": len(dates),
        "return_1d_percent": ret(1),
        "return_7d_percent": ret(7),
        "return_30d_percent": ret(30),
        "sma20_usd": round(sma20, 8) if sma20 is not None else None,
        "sma50_usd": round(sma50, 8) if sma50 is not None else None,
        "close_vs_sma20_percent": pct_return(latest, sma20) if sma20 else None,
        "close_vs_sma50_percent": pct_return(latest, sma50) if sma50 else None,
        "realized_volatility_30d_annualized_percent": round(vol30, 4) if vol30 is not None else None,
        "drawdown_from_90d_high_percent": drawdown90,
        "volume_7d_vs_30d_ratio": volume_ratio,
        "daily_volume_to_market_cap_ratio": turnover,
    }


def main() -> int:
    universe = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
    assets_cfg = universe.get("assets") or []
    ids = [a["id"] for a in assets_cfg]
    cfg_by_id = {a["id"]: a for a in assets_cfg}
    generated_at = iso_now()
    errors: List[Dict[str, str]] = []

    markets = fetch_json(
        "/coins/markets",
        {
            "vs_currency": "usd",
            "ids": ",".join(ids),
            "order": "market_cap_desc",
            "per_page": 50,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h,7d,30d",
            "precision": "full",
        },
    )
    market_by_id = {x.get("id"): x for x in markets if isinstance(x, dict) and x.get("id")}

    global_raw = fetch_json("/global")
    gd = (global_raw or {}).get("data") or {}
    global_market = {
        "active_cryptocurrencies": gd.get("active_cryptocurrencies"),
        "markets": gd.get("markets"),
        "total_market_cap_usd": as_float((gd.get("total_market_cap") or {}).get("usd")),
        "total_volume_usd": as_float((gd.get("total_volume") or {}).get("usd")),
        "btc_dominance_percent": as_float((gd.get("market_cap_percentage") or {}).get("btc")),
        "eth_dominance_percent": as_float((gd.get("market_cap_percentage") or {}).get("eth")),
        "market_cap_change_24h_percent": as_float(gd.get("market_cap_change_percentage_24h_usd")),
        "source": "CoinGecko /global",
    }

    output_assets: List[Dict[str, Any]] = []
    sessions: List[str] = []

    for asset_id in ids:
        cfg = cfg_by_id[asset_id]
        market = market_by_id.get(asset_id)
        if not market:
            errors.append({"asset": asset_id, "error": "Missing /coins/markets row"})
            continue
        try:
            chart = fetch_json(
                f"/coins/{urllib.parse.quote(asset_id)}/market_chart",
                {"vs_currency": "usd", "days": 120, "precision": "full"},
            )
            derived = derive_history(chart)
            sessions.append(derived["completed_session"])
            output_assets.append(
                {
                    "id": asset_id,
                    "symbol": cfg.get("symbol"),
                    "name": cfg.get("name"),
                    "status": "READY",
                    "spot_snapshot": {
                        "price_usd": as_float(market.get("current_price")),
                        "market_cap_usd": as_float(market.get("market_cap")),
                        "market_cap_rank": market.get("market_cap_rank"),
                        "total_volume_24h_usd": as_float(market.get("total_volume")),
                        "high_24h_usd": as_float(market.get("high_24h")),
                        "low_24h_usd": as_float(market.get("low_24h")),
                        "change_24h_percent": as_float(market.get("price_change_percentage_24h")),
                        "change_7d_percent": as_float(market.get("price_change_percentage_7d_in_currency")),
                        "change_30d_percent": as_float(market.get("price_change_percentage_30d_in_currency")),
                        "circulating_supply": as_float(market.get("circulating_supply")),
                        "total_supply": as_float(market.get("total_supply")),
                        "max_supply": as_float(market.get("max_supply")),
                        "ath_usd": as_float(market.get("ath")),
                        "ath_change_percent": as_float(market.get("ath_change_percentage")),
                        "last_updated": market.get("last_updated"),
                    },
                    "completed_daily_context": derived,
                    "provenance": {
                        "aggregated_market_snapshot": "CoinGecko /coins/markets",
                        "historical_context": "CoinGecko /coins/{id}/market_chart; 120-day request; only completed UTC days retained",
                        "raw_historical_series_published": False,
                    },
                }
            )
        except Exception as exc:
            errors.append({"asset": asset_id, "error": str(exc)[:500]})

    status = "CRYPTO_MARKET_DATA_READY" if len(output_assets) == len(ids) and not errors else ("PARTIAL" if output_assets else "FAILED")
    latest_session = max(sessions) if sessions else None
    artifact = {
        "version": "0.1",
        "status": status,
        "scope": universe.get("scope"),
        "generated_at": generated_at,
        "provider": {
            "name": "CoinGecko",
            "mode": "KEYED_SERVER_SIDE",
            "api_mode": API_MODE,
            "base_url": BASE_URL,
            "raw_series_published": False,
            "demo_rate_limit_guard": "<= approximately 28 requests/minute" if API_MODE == "DEMO" else None,
        },
        "market_clock": {
            "market": "24_7",
            "completed_daily_session_basis": "UTC_DAY",
            "latest_completed_session": latest_session,
            "partial_current_day_excluded_from_daily_context": True,
        },
        "global_market": global_market,
        "assets": output_assets,
        "errors": errors,
        "guardrails": {
            "market_data_only": True,
            "aggregator_is_not_official_protocol_or_regulatory_authority": True,
            "news_not_included": True,
            "official_protocol_and_regulatory_evidence_deferred_to_11B": True,
            "historical_backtest_not_run_in_11A": True,
            "no_buy_sell": True,
            "no_profit_probability": True,
            "trade_execution": "OFF",
        },
    }
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Stage 11A: {status}; {len(output_assets)}/{len(ids)} assets; session={latest_session}; errors={len(errors)}")
    return 0 if output_assets else 2


if __name__ == "__main__":
    raise SystemExit(main())
