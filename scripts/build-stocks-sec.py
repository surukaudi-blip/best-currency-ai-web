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


def form_family(form: Optional[str]) -> Optional[str]:
    if not form:
        return None
    if form.startswith("10-Q"):
        return "QUARTERLY"
    if form.startswith("10-K"):
        return "ANNUAL"
    return form


def fact_candidates(
    companyfacts: Dict[str, Any],
    tags: Iterable[str],
    preferred_units: Iterable[str],
    forms: Tuple[str, ...] = ("10-K", "10-Q", "10-K/A", "10-Q/A"),
) -> List[Dict[str, Any]]:
    """Collect valid observations across all candidate tags, then sort by recency.

    Companies can migrate from older US-GAAP concepts to newer concepts. Selecting the
    first tag with any historical data can therefore surface a stale value. We instead
    consider all semantically acceptable tags and choose the freshest filed observation.
    """
    facts = ((companyfacts.get("facts") or {}).get("us-gaap") or {})
    preferred = list(preferred_units)
    candidates: List[Dict[str, Any]] = []

    for tag in tags:
        concept = facts.get(tag)
        if not concept:
            continue
        units = concept.get("units") or {}
        unit_order = preferred + [u for u in units.keys() if u not in preferred]
        chosen_unit = next((u for u in unit_order if units.get(u)), None)
        if not chosen_unit:
            continue
        for item in units.get(chosen_unit) or []:
            if (
                item.get("form") in forms
                and item.get("filed")
                and item.get("end")
                and isinstance(item.get("val"), (int, float))
            ):
                enriched = dict(item)
                enriched["_tag"] = tag
                enriched["_unit"] = chosen_unit
                candidates.append(enriched)

    candidates.sort(
        key=lambda x: (x.get("end") or "", x.get("filed") or ""),
        reverse=True,
    )
    return candidates


def comparable_previous(latest: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return a same-concept, same-fiscal-period prior-year observation when available."""
    latest_tag = latest.get("_tag")
    latest_unit = latest.get("_unit")
    latest_fp = latest.get("fp")
    latest_fy = latest.get("fy")
    latest_family = form_family(latest.get("form"))
    latest_end = latest.get("end")

    pool = [
        item
        for item in candidates
        if item.get("end") != latest_end
        and item.get("_tag") == latest_tag
        and item.get("_unit") == latest_unit
        and form_family(item.get("form")) == latest_family
    ]

    # Strongest comparison: same SEC fiscal period in immediately prior fiscal year.
    if latest_fp is not None and isinstance(latest_fy, int):
        exact = [
            item
            for item in pool
            if item.get("fp") == latest_fp and item.get("fy") == latest_fy - 1
        ]
        if exact:
            exact.sort(key=lambda x: (x.get("end") or "", x.get("filed") or ""), reverse=True)
            return exact[0]

    # Conservative fallback: same fiscal-period label, most recent older observation.
    if latest_fp is not None:
        same_fp = [item for item in pool if item.get("fp") == latest_fp]
        if same_fp:
            same_fp.sort(key=lambda x: (x.get("end") or "", x.get("filed") or ""), reverse=True)
            return same_fp[0]

    return None


def summarize_fact(
    companyfacts: Dict[str, Any],
    tags: Iterable[str],
    preferred_units: Iterable[str],
) -> Optional[Dict[str, Any]]:
    candidates = fact_candidates(companyfacts, tags, preferred_units)
    if not candidates:
        return None

    # Deduplicate equivalent observations while preserving the freshest filing.
    unique: List[Dict[str, Any]] = []
    seen = set()
    for item in candidates:
        key = (
            item.get("_tag"),
            item.get("_unit"),
            item.get("end"),
            item.get("fp"),
            item.get("fy"),
            item.get("val"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    latest = unique[0]
    previous = comparable_previous(latest, unique)
    growth_percent = None
    if previous and previous.get("val") not in (None, 0):
        growth_percent = round((latest["val"] - previous["val"]) / abs(previous["val"]) * 100, 2)

    return {
        "tag": latest.get("_tag"),
        "unit": latest.get("_unit"),
        "value": latest.get("val"),
        "period_end": latest.get("end"),
        "filed": latest.get("filed"),
        "form": latest.get("form"),
        "fiscal_year": latest.get("fy"),
        "fiscal_period": latest.get("fp"),
        "previous_value": previous.get("val") if previous else None,
        "previous_period_end": previous.get("end") if previous else None,
        "comparison_family": form_family(latest.get("form")),
        "comparison_basis": "SAME_FISCAL_PERIOD_PRIOR_YEAR" if previous else None,
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
    event_30d = sum(
        1
        for f in filings
        if f.get("form", "").startswith("8-K")
        and (days_since(f.get("filing_date")) or 9999) <= 30
    )

    metrics = {
        "revenue": summarize_fact(
            companyfacts,
            ["RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenues"],
            ["USD"],
        ),
        "net_income": summarize_fact(companyfacts, ["NetIncomeLoss", "ProfitLoss"], ["USD"]),
        "operating_income": summarize_fact(companyfacts, ["OperatingIncomeLoss"], ["USD"]),
        "operating_cash_flow": summarize_fact(
            companyfacts,
            ["NetCashProvidedByUsedInOperatingActivities"],
            ["USD"],
        ),
        "cash": summarize_fact(
            companyfacts,
            ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
            ["USD"],
        ),
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
        print(
            "SEC_USER_AGENT is required. Example: 'Best Currency AI Name contact@example.com'",
            file=sys.stderr,
        )
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
        "version": "1.1",
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
            "xbrl_latest_across_accepted_tags": True,
            "fundamental_comparison_same_fiscal_period_prior_year": True,
            "trade_execution": "OFF",
        },
        "companies": companies,
        "errors": errors,
    }
    OUTPUT_PATH.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)} with status {status}")
    return 0 if companies else 1


if __name__ == "__main__":
    raise SystemExit(main())
