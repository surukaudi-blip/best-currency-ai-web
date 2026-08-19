#!/usr/bin/env python3
"""Build the Stocks v1 official-evidence artifact from SEC EDGAR.

This script intentionally does NOT fetch stock prices and does NOT create BUY/SELL
recommendations. It converts SEC submissions + companyfacts into a compact,
auditable evidence artifact for the static GitHub Pages UI.

Required environment:
  SEC_USER_AGENT="Best Currency AI Name contact@example.com"

SEC fair-access policy currently limits automated access to 10 requests/sec.
This adapter stays below that limit and only requests the configured watchlist.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "data" / "stocks-config.json"
OUTPUT_PATH = ROOT / "data" / "stocks-intelligence.json"
SEC_BASE = "https://data.sec.gov"
REQUEST_INTERVAL_SECONDS = 0.16  # ~6.25 requests/sec, below SEC's 10/sec guideline.


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_json(url: str, user_agent: str) -> Dict[str, Any]:
    # Do not request compressed transfer encoding here: urllib does not transparently
    # decode gzip in all environments. Identity transfer keeps this build deterministic.
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"SEC request failed {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"SEC network error for {url}: {exc.reason}") from exc


def columnar_rows(obj: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    if not obj:
        return []
    keys = list(obj.keys())
    length = max((len(obj.get(k, [])) for k in keys), default=0)
    rows: List[Dict[str, Any]] = []
    for i in range(length):
        rows.append({k: obj.get(k, [])[i] if i < len(obj.get(k, [])) else None for k in keys})
    return rows


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def days_since(value: Optional[str]) -> Optional[int]:
    parsed = parse_date(value)
    return (date.today() - parsed).days if parsed else None


def recent_filings(submissions: Dict[str, Any], limit: int = 12) -> List[Dict[str, Any]]:
    recent = ((submissions.get("filings") or {}).get("recent") or {})
    rows = columnar_rows(recent)
    material_forms = {"10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A"}
    selected = [r for r in rows if r.get("form") in material_forms][:limit]
    out = []
    cik_unpadded = str(int(submissions.get("cik") or 0))
    for row in selected:
        accn = str(row.get("accessionNumber") or "")
        accn_path = accn.replace("-", "")
        primary = row.get("primaryDocument")
        filing_url = (
            f"https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{accn_path}/{primary}"
            if cik_unpadded and accn_path and primary
            else None
        )
        out.append(
            {
                "form": row.get("form"),
                "filing_date": row.get("filingDate"),
                "report_date": row.get("reportDate"),
                "accession_number": accn or None,
                "primary_document": primary,
                "description": row.get("primaryDocDescription"),
                "filing_url": filing_url,
            }
        )
    return out


def fact_candidates(
    companyfacts: Dict[str, Any],
    tags: Iterable[str],
    preferred_units: Iterable[str],
    forms: Tuple[str, ...] = ("10-K", "10-Q", "10-K/A", "10-Q/A"),
) -> Tuple[Optional[str], Optional[str], List[Dict[str, Any]]]:
    facts = ((companyfacts.get("facts") or {}).get("us-gaap") or {})
    for tag in tags:
        concept = facts.get(tag)
        if not concept:
            continue
        units = concept.get("units") or {}
        unit_order = list(preferred_units) + [u for u in units.keys() if u not in preferred_units]
        for unit in unit_order:
            values = units.get(unit) or []
            filtered = [
                x for x in values
                if x.get("form") in forms and x.get("filed") and x.get("end") and isinstance(x.get("val"), (int, float))
            ]
            if filtered:
                filtered.sort(key=lambda x: (x.get("end") or "", x.get("filed") or ""), reverse=True)
                return tag, unit, filtered
    return None, None, []


def form_family(form: Optional[str]) -> Optional[str]:
    if not form:
        return None
    if form.startswith("10-Q"):
        return "QUARTERLY"
    if form.startswith("10-K"):
        return "ANNUAL"
    return form


def summarize_fact(
    companyfacts: Dict[str, Any],
    tags: Iterable[str],
    preferred_units: Iterable[str],
) -> Optional[Dict[str, Any]]:
    tag, unit, values = fact_candidates(companyfacts, tags, preferred_units)
    if not values or tag is None or unit is None:
        return None

    unique: List[Dict[str, Any]] = []
    seen_ends = set()
    for item in values:
        end = item.get("end")
        if end in seen_ends:
            continue
        seen_ends.add(end)
        unique.append(item)

    latest = unique[0]
    latest_family = form_family(latest.get("form"))
    previous = next(
        (
            item
            for item in unique[1:]
            if form_family(item.get("form")) == latest_family
        ),
        None,
    )

    growth_percent = None
    if previous and previous.get("val") not in (None, 0):
        growth_percent = round((latest["val"] - previous["val"]) / abs(previous["val"]) * 100, 2)

    return {
        "tag": tag,
        "unit": unit,
        "value": latest.get("val"),
        "period_end": latest.get("end"),
        "filed": latest.get("filed"),
        "form": latest.get("form"),
        "fiscal_year": latest.get("fy"),
        "fiscal_period": latest.get("fp"),
        "previous_value": previous.get("val") if previous else None,
        "previous_period_end": previous.get("end") if previous else None,
        "comparison_family": latest_family,
        "change_percent_vs_previous_reported_period": growth_percent,
        "change_percent_vs_comparable_reported_period": growth_percent,
    }


def build_company(entry: Dict[str, Any], user_agent: str) -> Dict[str, Any]:
    cik = entry["cik"]
    submissions_url = f"{SEC_BASE}/submissions/CIK{cik}.json"
    facts_url = f"{SEC_BASE}/api/xbrl/companyfacts/CIK{cik}.json"

    submissions = get_json(submissions_url, user_agent)
    time.sleep(REQUEST_INTERVAL_SECONDS)
    companyfacts = get_json(facts_url, user_agent)
    time.sleep(REQUEST_INTERVAL_SECONDS)

    filings = recent_filings(submissions)
    latest_filing = filings[0] if filings else None
    filing_date = latest_filing.get("filing_date") if latest_filing else None
    event_30d = sum(1 for f in filings if f.get("form", "").startswith("8-K") and (days_since(f.get("filing_date")) or 9999) <= 30)

    metrics = {
        "revenue": summarize_fact(companyfacts, ["RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenues"], ["USD"]),
        "net_income": summarize_fact(companyfacts, ["NetIncomeLoss", "ProfitLoss"], ["USD"]),
        "operating_income": summarize_fact(companyfacts, ["OperatingIncomeLoss"], ["USD"]),
        "operating_cash_flow": summarize_fact(companyfacts, ["NetCashProvidedByUsedInOperatingActivities"], ["USD"]),
        "cash": summarize_fact(companyfacts, ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"], ["USD"]),
        "assets": summarize_fact(companyfacts, ["Assets"], ["USD"]),
        "liabilities": summarize_fact(companyfacts, ["Liabilities"], ["USD"]),
        "stockholders_equity": summarize_fact(companyfacts, ["StockholdersEquity"], ["USD"]),
        "diluted_eps": summarize_fact(companyfacts, ["EarningsPerShareDiluted"], ["USD/shares"]),
    }

    available_metrics = sum(1 for value in metrics.values() if value is not None)
    completeness = round(available_metrics / len(metrics) * 100, 1)

    return {
        "ticker": entry["ticker"],
        "cik": cik,
        "name": submissions.get("name") or entry.get("name"),
        "exchange": entry.get("exchange"),
        "sic": submissions.get("sic"),
        "sic_description": submissions.get("sicDescription"),
        "fiscal_year_end": submissions.get("fiscalYearEnd"),
        "entity_type": submissions.get("entityType"),
        "source": {
            "tier": "A",
            "provider": "SEC EDGAR",
            "submissions_url": submissions_url,
            "companyfacts_url": facts_url,
        },
        "freshness": {
            "latest_material_filing_date": filing_date,
            "days_since_latest_material_filing": days_since(filing_date),
            "recent_8k_count_30d": event_30d,
        },
        "recent_filings": filings,
        "fundamentals": metrics,
        "evidence_completeness_percent": completeness,
        "market_data": {
            "status": "UNAVAILABLE",
            "reason": "Licensed price/volume adapter not configured yet.",
        },
        "decision_state": {
            "status": "OFFICIAL_EVIDENCE_READY",
            "market_view": "UNAVAILABLE",
            "decision_readiness": "NOT_ELIGIBLE_WITHOUT_MARKET_DATA",
            "trade_execution": "OFF",
        },
    }


def main() -> int:
    user_agent = os.getenv("SEC_USER_AGENT", "").strip()
    if not user_agent:
        print("SEC_USER_AGENT is required. Example: 'Best Currency AI Name contact@example.com'", file=sys.stderr)
        return 2

    config = load_json(CONFIG_PATH)
    companies: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for entry in config.get("watchlist", []):
        try:
            print(f"SEC: {entry['ticker']} ({entry['cik']})")
            companies.append(build_company(entry, user_agent))
        except Exception as exc:
            errors.append({"ticker": entry.get("ticker"), "cik": entry.get("cik"), "error": str(exc)})

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    status = "OFFICIAL_EVIDENCE_READY" if companies and not errors else ("PARTIAL" if companies else "UNAVAILABLE")
    artifact = {
        "version": "1.0",
        "status": status,
        "scope": config.get("scope"),
        "generated_at": generated_at,
        "source_readiness": {
            "sec_official_evidence": status,
            "market_price": "UNAVAILABLE",
            "news": "DEFERRED_TO_UNIFIED_NEWS_INTELLIGENCE",
            "decision_intelligence": "NOT_ELIGIBLE_WITHOUT_MARKET_DATA",
        },
        "guardrails": {
            "market_view_requires_price_data": True,
            "no_buy_sell_without_market_layer": True,
            "no_single_filing_is_trade_instruction": True,
            "missing_data_fail_closed": True,
            "trade_execution": "OFF",
        },
        "companies": companies,
        "errors": errors,
    }
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)} with status {status}")
    return 0 if companies else 1


if __name__ == "__main__":
    raise SystemExit(main())
