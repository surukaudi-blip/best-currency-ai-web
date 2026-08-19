#!/usr/bin/env python3
"""Build Stage 11B Crypto Evidence.

Evidence classes are intentionally separated:
- protocol/core implementation evidence from curated primary repositories,
- primary regulatory events from SEC/CFTC RSS,
- heterogeneous network telemetry only where an explicit source is approved.

No BUY/SELL, sentiment score, universal on-chain score, or profit probability is generated.
"""

from __future__ import annotations

import email.utils
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data" / "crypto-evidence-sources.json"
OUTPUT_PATH = ROOT / "data" / "crypto-evidence.json"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "").strip()
BASE_UA = SEC_USER_AGENT or "Best Currency AI evidence-research contact-not-configured"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return now_utc().isoformat().replace("+00:00", "Z")


def request_bytes(url: str, headers: Optional[Dict[str, str]] = None, data: Optional[bytes] = None, timeout: int = 30) -> bytes:
    merged = {"Accept": "*/*", "User-Agent": BASE_UA, **(headers or {})}
    req = urllib.request.Request(url, headers=merged, data=data, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read()


def request_json(url: str, headers: Optional[Dict[str, str]] = None, data: Optional[Dict[str, Any]] = None) -> Any:
    raw = request_bytes(
        url,
        headers={"Accept": "application/json", "Content-Type": "application/json", **(headers or {})},
        data=json.dumps(data).encode("utf-8") if data is not None else None,
    )
    return json.loads(raw.decode("utf-8"))


def safe_iso_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return value


def age_hours(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return round((now_utc() - dt.astimezone(timezone.utc)).total_seconds() / 3600.0, 2)
    except Exception:
        return None


def event_hash(parts: List[Any]) -> str:
    raw = "|".join(str(x or "") for x in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def github_headers() -> Dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def fetch_protocol(source: Dict[str, Any]) -> Dict[str, Any]:
    repo = source["repository"]
    base = f"https://api.github.com/repos/{repo}"
    releases = request_json(f"{base}/releases?per_page=3", headers=github_headers())
    commits = request_json(f"{base}/commits?per_page=1", headers=github_headers())
    latest_release = None
    if isinstance(releases, list) and releases:
        r = releases[0]
        latest_release = {
            "tag": r.get("tag_name"),
            "name": r.get("name"),
            "published_at": safe_iso_date(r.get("published_at")),
            "prerelease": bool(r.get("prerelease")),
            "url": r.get("html_url"),
        }
    latest_commit = None
    if isinstance(commits, list) and commits:
        c = commits[0]
        commit = c.get("commit") or {}
        author = commit.get("author") or {}
        latest_commit = {
            "sha": c.get("sha"),
            "subject": str((commit.get("message") or "").splitlines()[0])[:240],
            "committed_at": safe_iso_date(author.get("date")),
            "url": c.get("html_url"),
        }
    freshest = None
    candidates = [
        latest_release.get("published_at") if latest_release else None,
        latest_commit.get("committed_at") if latest_commit else None,
    ]
    for candidate in candidates:
        if candidate and (freshest is None or candidate > freshest):
            freshest = candidate
    return {
        "symbol": source.get("symbol"),
        "tier": source.get("tier"),
        "classification": source.get("classification"),
        "repository": repo,
        "status": "READY",
        "latest_release": latest_release,
        "latest_commit": latest_commit,
        "freshest_evidence_at": freshest,
        "freshness_hours": age_hours(freshest),
        "provenance": f"GitHub REST API /repos/{repo}/releases and /commits",
        "interpretation": "Core implementation activity is primary technical evidence, not a universal governance decision or directional market signal.",
    }


def parse_rss(source: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    raw = request_bytes(source["url"], headers={"Accept": "application/rss+xml, application/xml, text/xml"})
    root = ET.fromstring(raw)
    items = root.findall(".//item")
    parsed: List[Dict[str, Any]] = []
    for item in items[:100]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or item.findtext("date") or "").strip()
        published_at = None
        if pub:
            try:
                dt = email.utils.parsedate_to_datetime(pub)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                published_at = dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            except Exception:
                published_at = pub
        if title:
            parsed.append({"title": title[:400], "url": link, "published_at": published_at})
    meta = {
        "source": source.get("short"),
        "name": source.get("name"),
        "tier": source.get("tier"),
        "classification": source.get("classification"),
        "status": "READY",
        "items_scanned": len(parsed),
        "url": source.get("url"),
    }
    return meta, parsed


def match_regulatory_events(sources: List[Dict[str, Any]], protocol_sources: List[Dict[str, Any]], general_keywords: List[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    source_statuses: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    seen = set()
    asset_keywords = {s["symbol"]: [k.lower() for k in s.get("keywords", [])] for s in protocol_sources}
    general = [k.lower() for k in general_keywords]
    for source in sources:
        meta, items = parse_rss(source)
        source_statuses.append(meta)
        for item in items:
            text = (item.get("title") or "").lower()
            matched_assets = sorted({sym for sym, kws in asset_keywords.items() if any(k in text for k in kws)})
            crypto_general = any(k in text for k in general)
            if not matched_assets and not crypto_general:
                continue
            key = item.get("url") or item.get("title")
            if key in seen:
                continue
            seen.add(key)
            events.append({
                "event_id": event_hash([source.get("short"), item.get("title"), item.get("url"), item.get("published_at")]),
                "source": source.get("short"),
                "source_name": source.get("name"),
                "tier": source.get("tier"),
                "classification": "PRIMARY_REGULATORY_EVENT",
                "published_at": item.get("published_at"),
                "freshness_hours": age_hours(item.get("published_at")),
                "title": item.get("title"),
                "url": item.get("url"),
                "asset_scope": matched_assets,
                "scope": "ASSET_SPECIFIC" if matched_assets else "CRYPTO_GENERAL",
                "materiality": "UNSCORED_EVIDENCE",
                "directional_interpretation": "NOT_ASSIGNED_IN_11B",
            })
    events.sort(key=lambda x: x.get("published_at") or "", reverse=True)
    return source_statuses, events[:50]


def json_rpc(url: str, method: str, params: Optional[List[Any]] = None) -> Any:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    return request_json(url, data=payload)


def network_btc(source: Dict[str, Any]) -> Dict[str, Any]:
    base = source["endpoint"].rstrip("/")
    height = int(request_bytes(f"{base}/blocks/tip/height", headers={"Accept": "text/plain"}).decode("utf-8").strip())
    fees = request_json(f"{base}/fee-estimates")
    return {"tip_height": height, "fee_estimates_sat_vb": fees}


def network_sol(source: Dict[str, Any]) -> Dict[str, Any]:
    health = json_rpc(source["endpoint"], "getHealth").get("result")
    slot = json_rpc(source["endpoint"], "getSlot", [{"commitment": "finalized"}]).get("result")
    return {"health": health, "finalized_slot": slot}


def network_xrp(source: Dict[str, Any]) -> Dict[str, Any]:
    result = json_rpc(source["endpoint"], "server_info", [{}]).get("result") or {}
    info = result.get("info") or {}
    validated = info.get("validated_ledger") or {}
    return {
        "server_state": info.get("server_state"),
        "validated_ledger_seq": validated.get("seq"),
        "validated_ledger_age_seconds": validated.get("age"),
    }


def network_bnb(source: Dict[str, Any]) -> Dict[str, Any]:
    block_hex = json_rpc(source["endpoint"], "eth_blockNumber").get("result")
    chain_hex = json_rpc(source["endpoint"], "eth_chainId").get("result")
    return {
        "block_number": int(block_hex, 16) if isinstance(block_hex, str) else None,
        "chain_id": int(chain_hex, 16) if isinstance(chain_hex, str) else None,
    }


def collect_network(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    handlers = {"BTC": network_btc, "SOL": network_sol, "XRP": network_xrp, "BNB": network_bnb}
    for source in sources:
        base = {
            "symbol": source.get("symbol"),
            "name": source.get("name"),
            "tier": source.get("tier"),
            "classification": source.get("classification"),
            "source_status": source.get("status"),
            "endpoint": source.get("endpoint"),
            "note": source.get("note"),
            "captured_at": iso_now(),
            "cross_chain_comparable": False,
            "directional_interpretation": "NOT_ASSIGNED_IN_11B",
        }
        if source.get("status") != "ENABLED":
            base["status"] = source.get("status")
            base["metrics"] = None
            out.append(base)
            continue
        try:
            handler = handlers.get(source.get("symbol"))
            if not handler:
                raise RuntimeError("No approved telemetry handler configured")
            base["metrics"] = handler(source)
            base["status"] = "READY"
        except Exception as exc:
            base["status"] = "ERROR"
            base["error"] = str(exc)[:400]
            base["metrics"] = None
        out.append(base)
    return out


def main() -> int:
    cfg = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    errors: List[Dict[str, str]] = []
    protocol: List[Dict[str, Any]] = []
    for source in cfg.get("protocol_sources", []):
        try:
            protocol.append(fetch_protocol(source))
        except Exception as exc:
            errors.append({"layer": "protocol", "symbol": source.get("symbol"), "source": source.get("repository"), "error": str(exc)[:500]})
            protocol.append({
                "symbol": source.get("symbol"), "tier": source.get("tier"), "classification": source.get("classification"),
                "repository": source.get("repository"), "status": "ERROR", "error": str(exc)[:400]
            })

    regulatory_sources: List[Dict[str, Any]] = []
    regulatory_events: List[Dict[str, Any]] = []
    try:
        regulatory_sources, regulatory_events = match_regulatory_events(
            cfg.get("regulatory_sources", []), cfg.get("protocol_sources", []), cfg.get("regulatory_crypto_keywords", [])
        )
    except Exception as exc:
        errors.append({"layer": "regulatory", "source": "SEC/CFTC RSS", "error": str(exc)[:500]})

    network = collect_network(cfg.get("network_sources", []))
    for row in network:
        if row.get("status") == "ERROR":
            errors.append({"layer": "network", "symbol": row.get("symbol"), "source": row.get("name"), "error": row.get("error")})

    protocol_ready = sum(1 for x in protocol if x.get("status") == "READY")
    regulator_ready = sum(1 for x in regulatory_sources if x.get("status") == "READY")
    network_ready = sum(1 for x in network if x.get("status") == "READY")
    network_deferred = sum(1 for x in network if x.get("status") in {"DEFERRED", "NOT_APPLICABLE_NATIVE_CHAIN"})
    enabled_network_total = sum(1 for x in cfg.get("network_sources", []) if x.get("status") == "ENABLED")

    core_ready = protocol_ready == len(cfg.get("protocol_sources", [])) and regulator_ready == len(cfg.get("regulatory_sources", []))
    enabled_network_ready = network_ready == enabled_network_total
    if core_ready and enabled_network_ready:
        status = "CRYPTO_EVIDENCE_READY_PARTIAL_NETWORK"
    elif protocol_ready or regulator_ready or network_ready:
        status = "PARTIAL"
    else:
        status = "FAILED"

    artifact = {
        "version": "0.1",
        "status": status,
        "scope": cfg.get("scope"),
        "generated_at": iso_now(),
        "protocol_evidence": protocol,
        "regulatory_source_status": regulatory_sources,
        "regulatory_evidence": regulatory_events,
        "network_evidence": network,
        "coverage": {
            "protocol_assets_ready": protocol_ready,
            "protocol_assets_total": len(cfg.get("protocol_sources", [])),
            "regulatory_sources_ready": regulator_ready,
            "regulatory_sources_total": len(cfg.get("regulatory_sources", [])),
            "regulatory_events_matched": len(regulatory_events),
            "network_assets_ready": network_ready,
            "network_assets_total": len(cfg.get("network_sources", [])),
            "network_enabled_sources_total": enabled_network_total,
            "network_deferred_or_not_applicable": network_deferred,
        },
        "errors": errors,
        "guardrails": {
            "evidence_layer_only": True,
            "protocol_activity_is_not_automatically_market_direction": True,
            "regulatory_event_direction_is_not_assigned_in_11B": True,
            "network_telemetry_is_heterogeneous": True,
            "no_cross_chain_imputation": True,
            "no_universal_onchain_score": True,
            "no_buy_sell": True,
            "no_profit_probability": True,
            "unified_news_intelligence_not_yet_enabled": True,
            "trade_execution": "OFF",
        },
    }
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"11B: {status}; protocol={protocol_ready}/{len(cfg.get('protocol_sources', []))}; "
        f"regulators={regulator_ready}/{len(cfg.get('regulatory_sources', []))}; "
        f"network_ready={network_ready}/{enabled_network_total} enabled; events={len(regulatory_events)}; errors={len(errors)}"
    )
    return 0 if status == "CRYPTO_EVIDENCE_READY_PARTIAL_NETWORK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
