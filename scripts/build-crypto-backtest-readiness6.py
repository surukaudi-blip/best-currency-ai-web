#!/usr/bin/env python3
"""Crypto 6-check trend qualification diagnostic.

Tests the dashboard qualification framework against the same consumed 365-day
historical window used by the v0.4.1 Actionability diagnostic.

Six checks:
1. Canonical Direction
2. MTF Alignment
3. Regime Guardrail
4. Decision Risk
5. Counter-Thesis
6. Actionability Gate (Primary Gate)

Historical reconstruction limits are explicit:
- Direction, MTF and Regime are reconstructed from completed market data.
- Decision Risk is a market-only proxy because historical regulatory/evidence
  state is not backfilled.
- Counter-Thesis is the market-reconstructable subset of production logic only;
  regulatory/evidence factors are not fabricated.
- Actionability is the existing v0.4.1 market-only proxy from the consumed
  diagnostic, not the full current production evidence/data ceiling stack.

This script is diagnostic evidence only. It does not tune thresholds, change the
model, create asset-specific rules, estimate profit probability, or freeze it.
"""

from __future__ import annotations

import importlib.util
import json
import math
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
V041_SCRIPT = ROOT / "scripts" / "build-crypto-backtest-v041.py"
UNIVERSE_PATH = ROOT / "data" / "crypto-universe.json"
LINEAGE_PATH = ROOT / "data" / "crypto-model-lineage.json"
PRIOR_BT_PATH = ROOT / "data" / "crypto-backtest-v041.json"
OUTPUT_PATH = ROOT / "data" / "crypto-backtest-readiness6.json"

spec = importlib.util.spec_from_file_location("crypto_bt_v041", V041_SCRIPT)
v041 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(v041)
bt = v041.bt

HISTORY_DAYS = 365
WARMUP_DAYS = 90
FORWARD_HORIZONS = (1, 3, 7)


def production_pct_return(latest, prior):
    if prior == 0:
        return None
    return round((latest / prior - 1.0) * 100.0, 4)


def production_signed_score(value, span):
    if value is None:
        return None
    return round(bt.clamp(50.0 + 50.0 * float(value) / float(span)), 2)


def production_weighted_available(parts):
    rows = [(score, weight) for score, weight in parts if score is not None]
    total = sum(weight for _, weight in rows)
    if total <= 0:
        return None
    return round(sum(float(score) * weight for score, weight in rows) / total, 2)


# Exact production rounding parity used in the prior v0.4.1 diagnostic.
bt.pct_return = production_pct_return
bt.signed_score = production_signed_score
bt.weighted_available = production_weighted_available


def status_three(pass_if: bool, caution_if: bool = False) -> str:
    if pass_if:
        return "PASS"
    if caution_if:
        return "CAUTION"
    return "FAIL"


def market_counter_thesis(canonical: Dict[str, Any], risk: Dict[str, Any], r1: Optional[float]) -> Dict[str, Any]:
    """Reconstruct only production Counter-Thesis factors available from price history."""
    factors: List[Dict[str, str]] = []
    state = canonical.get("state")
    r1v = float(r1 or 0.0)
    r7 = v041.fnum(canonical.get("return_7d"))
    r30 = v041.fnum(canonical.get("return_30d"))
    vol = v041.fnum(risk.get("volatility_30d"))
    dd = v041.fnum(risk.get("drawdown_90d"))

    if state == "SUPPORTIVE" and r1v <= -4.0:
        factors.append({"severity": "MODERATE", "factor": "OPPOSING_1D_SHOCK"})
    if state == "PRESSURED" and r1v >= 4.0:
        factors.append({"severity": "MODERATE", "factor": "OPPOSING_1D_REBOUND"})
    if r7 is not None and r30 is not None and r7 * r30 < 0:
        factors.append({"severity": "MODERATE", "factor": "7D_30D_DIRECTION_CONFLICT"})
    if vol is not None and vol >= 90.0:
        factors.append({"severity": "HIGH", "factor": "EXTREME_30D_VOLATILITY"})
    elif vol is not None and vol >= 60.0:
        factors.append({"severity": "MODERATE", "factor": "ELEVATED_30D_VOLATILITY"})
    if dd is not None and dd <= -35.0:
        factors.append({"severity": "HIGH", "factor": "DEEP_90D_DRAWDOWN"})
    elif dd is not None and dd <= -25.0:
        factors.append({"severity": "MODERATE", "factor": "MATERIAL_90D_DRAWDOWN"})
    if risk.get("risk_state") == "HIGH":
        factors.append({"severity": "HIGH", "factor": "HIGH_MARKET_ONLY_DECISION_RISK"})

    high = sum(1 for x in factors if x.get("severity") == "HIGH")
    strength = "HIGH" if high else ("MODERATE" if len(factors) >= 2 else ("LOW" if factors else "LIMITED"))
    return {
        "strength": strength,
        "factors": factors,
        "historical_scope": "MARKET_RECONSTRUCTABLE_SUBSET_ONLY",
    }


def check_states(canonical: Dict[str, Any], mtf_data: Dict[str, Any], risk: Dict[str, Any], act: Dict[str, Any], counter: Dict[str, Any]) -> Dict[str, str]:
    directional = canonical.get("state") in {"SUPPORTIVE", "PRESSURED"}
    mtf_score = float(mtf_data.get("score") or 0.0)
    regime_score = float((act.get("ceilings") or {}).get("regime_guardrail") or 0.0)
    risk_state = str(risk.get("risk_state") or "UNAVAILABLE")
    counter_strength = str(counter.get("strength") or "UNAVAILABLE")
    action_state = str(act.get("state") or "UNAVAILABLE")

    return {
        "direction": status_three(directional),
        "mtf": status_three(mtf_score >= 80.0, mtf_score >= 60.0),
        "regime": status_three(regime_score >= 80.0, regime_score >= 60.0),
        "risk": status_three(risk_state == "LOW", risk_state == "MODERATE"),
        # Current dashboard semantics: only LOW passes; MODERATE cautions; LIMITED fails closed.
        "counter_thesis": status_three(counter_strength == "LOW", counter_strength == "MODERATE"),
        "actionability": status_three(action_state == "ACTIONABLE", action_state == "SELECTIVE"),
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
        can = v041.canonical_v01(prices, i)
        mtf_data = v041.mtf(prices, i, can["state"])
        risk = v041.base_market_risk(prices, i, can)
        participation = v041.market_participation(volumes, i)
        act = v041.actionability(can, mtf_data, risk, participation, "v041")
        r1 = bt.pct_return(prices[i], prices[i - 1]) if i >= 1 else None
        counter = market_counter_thesis(can, risk, r1)
        checks = check_states(can, mtf_data, risk, act, counter)
        pass_count = sum(1 for v in checks.values() if v == "PASS")
        caution_count = sum(1 for v in checks.values() if v == "CAUTION")
        # Sensitivity only: treating LIMITED Counter-Thesis (no reconstructed challenge factors)
        # as PASS. This is reported separately and does not redefine the dashboard rule.
        alt_checks = dict(checks)
        if counter.get("strength") == "LIMITED":
            alt_checks["counter_thesis"] = "PASS"
        alt_pass_count = sum(1 for v in alt_checks.values() if v == "PASS")

        sign = 1 if can["state"] == "SUPPORTIVE" else (-1 if can["state"] == "PRESSURED" else 0)
        row: Dict[str, Any] = {
            "date": dates[i],
            "asset": asset["symbol"],
            "canonical_state": can["state"],
            "canonical_score": can["score"],
            "mtf_state": mtf_data["state"],
            "mtf_score": mtf_data["score"],
            "regime_ceiling": (act.get("ceilings") or {}).get("regime_guardrail"),
            "market_risk_state": risk.get("risk_state"),
            "market_risk_score": risk.get("risk_proxy"),
            "volatility_30d": risk.get("volatility_30d"),
            "drawdown_90d": risk.get("drawdown_90d"),
            "counter_thesis_market_strength": counter.get("strength"),
            "counter_thesis_market_factor_count": len(counter.get("factors") or []),
            "actionability_state": act.get("state"),
            "actionability_score": act.get("score"),
            "actionability_limiter": act.get("limiter"),
            "checks": checks,
            "checks_passed": pass_count,
            "checks_caution": caution_count,
            "alt_limited_counter_checks_passed": alt_pass_count,
            "primary_gate_passed": checks.get("actionability") == "PASS",
        }
        for h in FORWARD_HORIZONS:
            fwd = bt.pct_return(prices[i + h], prices[i])
            directional = fwd * sign if sign else None
            row[f"dir_{h}d"] = bt.safe_round(directional, 4)
            row[f"hit_{h}d"] = directional > 0 if directional is not None else None
        rows.append(row)
    return rows


def wilson(hits: int, n: int, z: float = 1.96) -> Optional[Dict[str, float]]:
    if n <= 0:
        return None
    p = hits / n
    den = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / den
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / den
    return {"low_percent": round(max(0.0, center - half) * 100.0, 2), "high_percent": round(min(1.0, center + half) * 100.0, 2)}


def metric(rows: List[Dict[str, Any]], predicate) -> Dict[str, Any]:
    directional = [r for r in rows if r.get("canonical_state") in {"SUPPORTIVE", "PRESSURED"}]
    selected = [r for r in directional if predicate(r)]
    out: Dict[str, Any] = {
        "observations": len(selected),
        "coverage_percent_of_all": round(len(selected) / len(rows) * 100.0, 2) if rows else None,
        "retention_percent_of_directional": round(len(selected) / len(directional) * 100.0, 2) if directional else None,
    }
    for h in FORWARD_HORIZONS:
        valid = [r for r in selected if r.get(f"hit_{h}d") is not None]
        hits = sum(1 for r in valid if r.get(f"hit_{h}d") is True)
        drets = [float(r[f"dir_{h}d"]) for r in valid if r.get(f"dir_{h}d") is not None]
        out[f"hit_rate_{h}d_percent"] = round(hits / len(valid) * 100.0, 2) if valid else None
        out[f"hit_rate_{h}d_wilson95"] = wilson(hits, len(valid))
        out[f"avg_directional_return_{h}d_percent"] = round(sum(drets) / len(drets), 4) if drets else None
    return out


def main() -> int:
    universe = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
    lineage = json.loads(LINEAGE_PATH.read_text(encoding="utf-8"))
    prior = json.loads(PRIOR_BT_PATH.read_text(encoding="utf-8")) if PRIOR_BT_PATH.exists() else {}

    assets = universe.get("assets") or universe.get("symbols") or []
    all_rows: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    for asset in assets:
        try:
            rows = build_asset_rows(asset)
            all_rows.extend(rows)
            print(f"{asset.get('symbol')}: {len(rows)} rows")
        except Exception as exc:
            errors.append({"asset": str(asset.get("symbol")), "error": str(exc)})
            print(f"ERROR {asset.get('symbol')}: {exc}")

    directional = [r for r in all_rows if r.get("canonical_state") in {"SUPPORTIVE", "PRESSURED"}]
    check_names = ["direction", "mtf", "regime", "risk", "counter_thesis", "actionability"]

    individual: Dict[str, Any] = {}
    for check in check_names:
        if check == "direction":
            individual[check] = {
                "pass": metric(all_rows, lambda r: True),
                "note": "Direction PASS defines the directional evaluation universe; MIXED has no directional sign to score as trend continuation.",
            }
        else:
            individual[check] = {
                "pass": metric(all_rows, lambda r, c=check: (r.get("checks") or {}).get(c) == "PASS"),
                "not_pass": metric(all_rows, lambda r, c=check: (r.get("checks") or {}).get(c) != "PASS"),
            }

    exact_counts = {str(k): metric(all_rows, lambda r, kk=k: int(r.get("checks_passed") or 0) == kk) for k in range(1, 7)}
    at_least = {str(k): metric(all_rows, lambda r, kk=k: int(r.get("checks_passed") or 0) >= kk) for k in range(1, 7)}

    primary_gate = {
        "passed": metric(all_rows, lambda r: bool(r.get("primary_gate_passed"))),
        "not_passed": metric(all_rows, lambda r: not bool(r.get("primary_gate_passed"))),
        "readiness_5plus_primary_pass": metric(all_rows, lambda r: int(r.get("checks_passed") or 0) >= 5 and bool(r.get("primary_gate_passed"))),
        "readiness_5plus_primary_not_pass": metric(all_rows, lambda r: int(r.get("checks_passed") or 0) >= 5 and not bool(r.get("primary_gate_passed"))),
        "other_five_pass_primary_fail": metric(all_rows, lambda r: all((r.get("checks") or {}).get(c) == "PASS" for c in check_names[:-1]) and (r.get("checks") or {}).get("actionability") != "PASS"),
        "strict_6_of_6": metric(all_rows, lambda r: int(r.get("checks_passed") or 0) == 6),
    }

    sensitivity = {
        "counter_thesis_LIMITED_treated_as_PASS_strict_6_of_6": metric(all_rows, lambda r: int(r.get("alt_limited_counter_checks_passed") or 0) == 6),
        "counter_thesis_LIMITED_count": sum(1 for r in directional if r.get("counter_thesis_market_strength") == "LIMITED"),
        "note": "Sensitivity only. Official dashboard currently passes Counter-Thesis only when strength=LOW; LIMITED fails closed. No rule is changed by this diagnostic.",
    }

    baseline = ((prior.get("summary") or {}).get("v01_all_directional") or {})
    primary_prior = ((prior.get("summary") or {}).get("v041_actionable_only") or {})
    strict = primary_gate["strict_6_of_6"]
    strict7 = strict.get("hit_rate_7d_percent")
    base7 = baseline.get("hit_rate_7d_percent")

    artifact = {
        "version": "1.0",
        "status": "CRYPTO_6CHECK_TREND_QUALIFICATION_DIAGNOSTIC_COMPLETE",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "MAJOR_LIQUID_CRYPTO_ASSETS_V1",
        "model_frozen": False,
        "test_design": {
            "historical_window_days": HISTORY_DAYS,
            "warmup_days": WARMUP_DAYS,
            "forward_horizons_days": list(FORWARD_HORIZONS),
            "historical_window_status": "CONSUMED_DIAGNOSTIC_NOT_FRESH_OOS",
            "production_rounding_parity": "ENFORCED",
            "threshold_search": False,
            "asset_specific_rules": False,
            "historical_protocol_regulatory_network_state_backfilled": False,
            "direction_mtf_regime_reconstruction": "MARKET_HISTORY_RECONSTRUCTABLE",
            "decision_risk_reconstruction": "MARKET_ONLY_PROXY",
            "counter_thesis_reconstruction": "MARKET_ONLY_SUBSET_OF_PRODUCTION_FACTORS",
            "actionability_reconstruction": "V041_MARKET_ONLY_PROXY",
            "readiness_scoring": "ONE_POINT_PER_PASS_SIX_CHECKS; CAUTION_AND_FAIL_ZERO_POINTS",
            "primary_gate": "ACTIONABILITY_GATE",
        },
        "check_rules": {
            "direction": "PASS if canonical v0.1 is SUPPORTIVE or PRESSURED",
            "mtf": "PASS >=80; CAUTION 60-79.99; FAIL <60",
            "regime": "PASS ceiling >=80; CAUTION 60-79.99; FAIL <60",
            "risk": "PASS LOW; CAUTION MODERATE; FAIL HIGH",
            "counter_thesis": "PASS LOW; CAUTION MODERATE; LIMITED/HIGH fail closed under current dashboard semantics",
            "actionability": "PRIMARY GATE: PASS ACTIONABLE >=80; CAUTION SELECTIVE; FAIL FILTERED",
        },
        "lineage": {
            "canonical_v01_methodology_sha256": ((lineage.get("canonical_direction") or {}).get("methodology_sha256")),
            "prior_v041_diagnostic_status": prior.get("status"),
        },
        "sample": {
            "all_rows": len(all_rows),
            "directional_rows": len(directional),
            "errors": errors,
            "check_pass_counts_directional": dict(sorted(Counter(int(r.get("checks_passed") or 0) for r in directional).items())),
        },
        "baseline_reference": {
            "v01_all_directional": baseline,
            "v041_actionable_only_prior_diagnostic": primary_prior,
        },
        "individual_check_effect": individual,
        "exact_checks_passed": exact_counts,
        "at_least_checks_passed": at_least,
        "primary_gate_analysis": primary_gate,
        "counter_thesis_semantics_sensitivity": sensitivity,
        "diagnostic_deltas": {
            "strict_6of6_7d_vs_v01_baseline_pp": round(float(strict7) - float(base7), 2) if strict7 is not None and base7 is not None else None,
            "strict_6of6_7d_vs_prior_v041_actionable_pp": round(float(strict7) - float(primary_prior.get("hit_rate_7d_percent")), 2) if strict7 is not None and primary_prior.get("hit_rate_7d_percent") is not None else None,
        },
        "governance": [
            "Diagnostic uses an already-consumed historical window and is not Fresh OOS.",
            "No historical protocol/regulatory/network evidence is fabricated or backfilled.",
            "Results must not be used for threshold search or asset-specific rules on this consumed window.",
            "Readiness and hit rates are not probabilities of profit.",
            "Trade execution remains OFF and the Crypto model remains unfrozen.",
        ],
    }
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT_PATH}")
    print(json.dumps({
        "directional_rows": len(directional),
        "strict_6of6": primary_gate["strict_6_of_6"],
        "primary_gate_passed": primary_gate["passed"],
        "limited_counter_sensitivity_6of6": sensitivity["counter_thesis_LIMITED_treated_as_PASS_strict_6_of_6"],
    }, indent=2))
    return 0 if all_rows and not errors else (0 if all_rows else 1)


if __name__ == "__main__":
    raise SystemExit(main())
