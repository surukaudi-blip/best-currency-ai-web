#!/usr/bin/env python3
"""Stage 11C.5 final pre-freeze cross-check for Crypto v0.4.1.

This is a governance/QA audit only. It does not change model formulas, thresholds,
asset rules, directional states, or execution policy.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SCRIPTS = ROOT / "scripts"

UNIVERSE = DATA / "crypto-universe.json"
MARKET = DATA / "crypto-market-data.json"
EVIDENCE = DATA / "crypto-evidence.json"
DECISION = DATA / "crypto-decision-intelligence.json"
BACKTEST = DATA / "crypto-backtest-readiness6.json"
LINEAGE = DATA / "crypto-model-lineage.json"
UI = ROOT / "crypto-readiness.js"
V041 = SCRIPTS / "build-crypto-decision-v041.py"
BASE = SCRIPTS / "build-crypto-decision.py"
MARKET_SCRIPT = SCRIPTS / "build-crypto-market.py"
COUNTERFIX = SCRIPTS / "build-crypto-decision-v041-counterfix.py"
OUTPUT = DATA / "crypto-prefreeze-crosscheck.json"


def load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


checks: List[Dict[str, Any]] = []


def add(check_id: str, area: str, status: str, evidence: Any, *, blocking: bool = False, note: str = "") -> None:
    checks.append({
        "id": check_id,
        "area": area,
        "status": status,
        "blocking": bool(blocking),
        "evidence": evidence,
        "note": note,
    })


universe = load(UNIVERSE)
market = load(MARKET)
evidence = load(EVIDENCE)
decision = load(DECISION)
backtest = load(BACKTEST)
lineage = load(LINEAGE)
ui_text = text(UI)
v041_text = text(V041)
base_text = text(BASE)
market_text = text(MARKET_SCRIPT)
counterfix_text = text(COUNTERFIX)

expected = [x.get("symbol") for x in universe.get("assets", []) if x.get("symbol")]
expected_set = set(expected)
market_rows = market.get("assets") or []
decision_rows = decision.get("symbols") or []
protocol_rows = evidence.get("protocol_evidence") or []
market_symbols = [x.get("symbol") for x in market_rows if x.get("symbol")]
decision_symbols = [x.get("symbol") for x in decision_rows if x.get("symbol")]
protocol_symbols = [x.get("symbol") for x in protocol_rows if x.get("symbol")]

# 1. Universe and current data integrity.
universe_ok = len(expected) == 8 and len(expected_set) == 8 and set(market_symbols) == expected_set and set(decision_symbols) == expected_set
add("DATA_UNIVERSE", "data_integrity", "PASS" if universe_ok else "FAIL", {
    "expected_symbols": expected,
    "market_symbols": market_symbols,
    "decision_symbols": decision_symbols,
}, blocking=not universe_ok)

market_ready = (
    market.get("status") == "CRYPTO_MARKET_DATA_READY"
    and not (market.get("errors") or [])
    and all(x.get("status") == "READY" for x in market_rows)
)
add("MARKET_READY", "data_integrity", "PASS" if market_ready else "FAIL", {
    "status": market.get("status"),
    "errors": market.get("errors") or [],
    "ready_assets": sum(1 for x in market_rows if x.get("status") == "READY"),
}, blocking=not market_ready)

sessions = [((x.get("completed_daily_context") or {}).get("completed_session")) for x in market_rows]
history = [int(((x.get("completed_daily_context") or {}).get("history_observations") or 0)) for x in market_rows]
clock = market.get("market_clock") or {}
completed_ok = (
    len(set(sessions)) == 1
    and sessions and sessions[0] == clock.get("latest_completed_session")
    and bool(clock.get("partial_current_day_excluded_from_daily_context"))
    and all(v >= 90 for v in history)
)
add("COMPLETED_SESSION_ONLY", "no_lookahead", "PASS" if completed_ok else "FAIL", {
    "sessions": sorted(set(sessions)),
    "latest_completed_session": clock.get("latest_completed_session"),
    "partial_current_day_excluded": clock.get("partial_current_day_excluded_from_daily_context"),
    "min_history_observations": min(history) if history else None,
}, blocking=not completed_ok)

# 2. Source/provenance integrity.
provider = market.get("provider") or {}
source_ok = (
    provider.get("name") == "CoinGecko"
    and provider.get("mode") == "KEYED_SERVER_SIDE"
    and provider.get("raw_series_published") is False
    and "dt.date() >= today" in market_text
    and "continue" in market_text
)
add("MARKET_SOURCE_INTEGRITY", "source_integrity", "PASS" if source_ok else "FAIL", {
    "provider": provider.get("name"),
    "mode": provider.get("mode"),
    "raw_series_published": provider.get("raw_series_published"),
}, blocking=not source_ok)

reg_status = evidence.get("regulatory_source_status") or []
evidence_ok = (
    str(evidence.get("status") or "").startswith("CRYPTO_EVIDENCE_READY")
    and set(protocol_symbols) == expected_set
    and all(x.get("status") == "READY" for x in protocol_rows)
    and len(reg_status) >= 2
    and all(x.get("status") == "READY" for x in reg_status)
)
add("EVIDENCE_SOURCE_INTEGRITY", "source_integrity", "PASS" if evidence_ok else "FAIL", {
    "status": evidence.get("status"),
    "protocol_assets": protocol_symbols,
    "regulatory_sources_ready": sum(1 for x in reg_status if x.get("status") == "READY"),
    "regulatory_sources_total": len(reg_status),
}, blocking=not evidence_ok, note="Partial/deferred network telemetry is allowed when explicitly disclosed; missing data is not imputed.")

# 3. Canonical lineage and model identity.
lineage_hash = ((lineage.get("canonical_direction") or {}).get("methodology_sha256"))
decision_hash = ((decision.get("canonical_direction_model") or {}).get("methodology_sha256"))
lineage_ok = bool(lineage_hash) and lineage_hash == decision_hash == "2e58009070741bf6e2cb4c2b0c3b7dff154c5b8250651bc0963a15eef00b7be4"
add("CANONICAL_LINEAGE_HASH", "lineage", "PASS" if lineage_ok else "FAIL", {
    "lineage_hash": lineage_hash,
    "decision_hash": decision_hash,
}, blocking=not lineage_ok)

frozen_ok = decision.get("frozen") is False and bool((decision.get("guardrails") or {}).get("model_is_unfrozen"))
add("PREFREEZE_STATE", "lineage", "PASS" if frozen_ok else "FAIL", {
    "frozen": decision.get("frozen"),
    "model_status": decision.get("model_status"),
}, blocking=not frozen_ok)

# 4. D/W/M formula and canonical-direction boundaries.
mtf_policy = decision.get("multi_timeframe_policy") or {}
mtf_ok = (
    mtf_policy.get("weights") == {"daily": 0.45, "weekly": 0.35, "monthly": 0.20}
    and mtf_policy.get("return_spans_percent") == {"daily": 6.0, "weekly": 12.0, "monthly": 25.0}
    and mtf_policy.get("state_thresholds") == {"supportive_gte": 62, "pressured_lte": 38}
    and mtf_policy.get("role") == "CONFIRMATION_ONLY_NOT_DIRECTION_SOURCE"
)
add("MTF_FIXED_FORMULA", "mtf", "PASS" if mtf_ok else "FAIL", mtf_policy, blocking=not mtf_ok)

symbol_consistency = True
symbol_issues: List[str] = []
for row in decision_rows:
    sym = row.get("symbol")
    canonical = (row.get("market_structure") or {}).get("state")
    mtf = row.get("multi_timeframe_alignment") or {}
    act = row.get("actionability") or {}
    ai = row.get("ai_decision_reasoner") or {}
    if mtf.get("canonical_state") != canonical:
        symbol_consistency = False; symbol_issues.append(f"{sym}: MTF canonical mismatch")
    if ai.get("canonical_market_view") != canonical:
        symbol_consistency = False; symbol_issues.append(f"{sym}: reasoner canonical mismatch")
    if ai.get("actionability_state") != act.get("state") or ai.get("actionability_score") != act.get("score"):
        symbol_consistency = False; symbol_issues.append(f"{sym}: reasoner Actionability mismatch")
    if canonical not in {"SUPPORTIVE", "PRESSURED"} and float(act.get("score") or 0) > 45.0:
        symbol_consistency = False; symbol_issues.append(f"{sym}: MIXED canonical escaped 45 ceiling")
add("DIRECTION_MTF_ACTIONABILITY_CONSISTENCY", "mtf", "PASS" if symbol_consistency else "FAIL", {
    "issues": symbol_issues,
}, blocking=not symbol_consistency)

# 5. Boundary-condition tests on v0.4.1 pure regime functions.
spec = importlib.util.spec_from_file_location("crypto_v041_qa", V041)
v041 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(v041)
vol_cases = [
    (None, "UNKNOWN_VOL", 55.0),
    (44.9999, "LOW_VOL", 100.0),
    (45.0, "MODERATE_VOL", 70.0),
    (74.9999, "MODERATE_VOL", 70.0),
    (75.0, "HIGH_VOL", 55.0),
]
dd_cases = [
    (None, "UNKNOWN_DRAWDOWN", 60.0),
    (-14.9999, "NORMAL_DRAWDOWN", 100.0),
    (-15.0, "MATERIAL_DRAWDOWN", 100.0),
    (-29.9999, "MATERIAL_DRAWDOWN", 100.0),
    (-30.0, "STRESSED_DRAWDOWN", 60.0),
]
vol_results = [(v, v041.volatility_regime(v)) for v, _, _ in vol_cases]
dd_results = [(v, v041.drawdown_regime(v)) for v, _, _ in dd_cases]
boundary_ok = all(r.get("state") == st and float(r.get("ceiling")) == cap for (_, st, cap), (_, r) in zip(vol_cases, vol_results))
boundary_ok = boundary_ok and all(r.get("state") == st and float(r.get("ceiling")) == cap for (_, st, cap), (_, r) in zip(dd_cases, dd_results))
add("REGIME_BOUNDARIES", "boundary_conditions", "PASS" if boundary_ok else "FAIL", {
    "volatility": [{"input": v, **r} for v, r in vol_results],
    "drawdown": [{"input": v, **r} for v, r in dd_results],
}, blocking=not boundary_ok)

policy = decision.get("actionability_policy") or {}
action_policy_ok = (
    policy.get("thresholds") == {"actionable": 80, "selective": 60, "filtered": 0}
    and policy.get("explicit_regime_caps") == {"LOW_VOL": 100, "MODERATE_VOL": 70, "HIGH_VOL": 55, "UNKNOWN_VOL": 55, "STRESSED_DRAWDOWN": 60}
    and policy.get("role") == "PRIMARY_OPERATIONAL_READINESS_LAYER"
    and policy.get("does_not_reverse_canonical_direction") is True
    and policy.get("no_asset_specific_rules") is True
)
add("ACTIONABILITY_PRIMARY_GATE_POLICY", "actionability", "PASS" if action_policy_ok else "FAIL", policy, blocking=not action_policy_ok)

# 6. Decision Risk and Counter-Thesis semantics.
risk_source_ok = (
    '"LOW" if score < 35' in base_text
    and '"MODERATE" if score < 65' in base_text
    and '"HIGH"' in base_text
)
add("RISK_BOUNDARIES", "risk", "PASS" if risk_source_ok else "FAIL", {
    "low": "score < 35",
    "moderate": "35 <= score < 65",
    "high": "score >= 65",
}, blocking=not risk_source_ok)

ct_sem = decision.get("counter_thesis_semantics") or {}
ct_rows_ok = all(((x.get("counter_thesis") or {}).get("strength") in {"LOW", "MODERATE", "HIGH"}) for x in decision_rows)
ct_ok = (
    ct_sem.get("version") == "COUNTER_THESIS_0.2"
    and ct_sem.get("readiness_mapping") == "LOW=PASS; MODERATE=CAUTION; HIGH=FAIL"
    and "strength = \"LOW\"" in counterfix_text
    and "strength = \"MODERATE\"" in counterfix_text
    and "strength = \"HIGH\"" in counterfix_text
    and ct_rows_ok
)
add("COUNTER_THESIS_V02", "counter_thesis", "PASS" if ct_ok else "FAIL", {
    "semantics": ct_sem,
    "current_strengths": {x.get("symbol"): (x.get("counter_thesis") or {}).get("strength") for x in decision_rows},
}, blocking=not ct_ok)

# 7. Reasoner sanity and execution guardrails.
reasoner_ok = True
reasoner_issues: List[str] = []
for row in decision_rows:
    sym = row.get("symbol")
    canonical = (row.get("market_structure") or {}).get("state")
    act_state = (row.get("actionability") or {}).get("state")
    ai = row.get("ai_decision_reasoner") or {}
    expected_decision = "WATCH" if canonical not in {"SUPPORTIVE", "PRESSURED"} else (
        "EVALUATE_SETUP" if act_state == "ACTIONABLE" else "REVIEW_SELECTIVELY" if act_state == "SELECTIVE" else "DEPRIORITIZE"
    )
    if ai.get("decision") != expected_decision:
        reasoner_ok = False; reasoner_issues.append(f"{sym}: expected {expected_decision}, got {ai.get('decision')}")
    if ai.get("buy_sell") != "NOT_GENERATED" or ai.get("profit_probability") != "NOT_ESTIMATED" or ai.get("trade_execution") != "OFF":
        reasoner_ok = False; reasoner_issues.append(f"{sym}: execution/probability guardrail mismatch")
add("REASONER_SANITY", "reasoner", "PASS" if reasoner_ok else "FAIL", {"issues": reasoner_issues}, blocking=not reasoner_ok)

# 8. Backtest/no-leakage governance and fixed outcome definition.
test_design = backtest.get("test_design") or {}
backtest_ok = (
    test_design.get("historical_window_status") == "CONSUMED_DIAGNOSTIC_NOT_FRESH_OOS"
    and test_design.get("threshold_search") is False
    and test_design.get("asset_specific_rules") is False
    and test_design.get("historical_protocol_regulatory_network_state_backfilled") is False
    and test_design.get("forward_horizons_days") == [1, 3, 7]
)
add("BACKTEST_GOVERNANCE", "no_lookahead", "PASS" if backtest_ok else "FAIL", test_design, blocking=not backtest_ok)

# Current diagnostic after semantic correction should be coherent but not treated as fresh proof.
strict6 = ((backtest.get("primary_gate_analysis") or {}).get("strict_6_of_6") or {})
primary = ((backtest.get("primary_gate_analysis") or {}).get("passed") or {})
diag_ok = (
    backtest.get("status") == "CRYPTO_6CHECK_COUNTER_THESIS_SEMANTIC_REVISION_DIAGNOSTIC_COMPLETE"
    and strict6.get("observations") == 60
    and strict6.get("hit_rate_7d_percent") == 65.0
    and primary.get("hit_rate_7d_percent") == 60.24
)
add("CONSUMED_DIAGNOSTIC_PARITY", "backtest", "PASS" if diag_ok else "FAIL", {
    "strict_6_of_6": strict6,
    "primary_gate": primary,
}, blocking=not diag_ok, note="Diagnostic values are QA evidence only and are not profit probabilities.")

# 9. Asset-specific hidden bias.
asset_specific_ok = (
    (decision.get("actionability_policy") or {}).get("no_asset_specific_rules") is True
    and (lineage.get("guardrails") or {}).get("no_asset_specific_rules_from_consumed_backtest") is True
    and "if symbol ==" not in v041_text
    and "if symbol==" not in v041_text
)
add("NO_ASSET_SPECIFIC_TUNING", "bias_control", "PASS" if asset_specific_ok else "FAIL", {
    "actionability_policy": (decision.get("actionability_policy") or {}).get("no_asset_specific_rules"),
    "lineage_guardrail": (lineage.get("guardrails") or {}).get("no_asset_specific_rules_from_consumed_backtest"),
}, blocking=not asset_specific_ok)

# 10. Dependency/double-counting map. This is intentional guardrail overlap, not independent evidence.
dependency_map = {
    "volatility": ["Decision Risk", "Regime Guardrail", "Counter-Thesis at extreme/elevated levels"],
    "drawdown": ["Decision Risk", "Regime Guardrail", "Counter-Thesis at material/deep levels"],
    "regulatory_uncertainty": ["Decision Risk", "Regime Guardrail at high asset-specific uncertainty", "Counter-Thesis"],
    "mtf": ["MTF check", "Actionability asset_mtf_readiness"],
}
ui_discloses_checklist = (
    "Readiness mengukur kelengkapan persyaratan review" in ui_text
    and "readiness ≠ win probability" in ui_text
    and "Actionability adalah Primary Gate" in ui_text
)
add("DEPENDENCY_DOUBLE_COUNTING", "dependency_control", "PASS_WITH_CONDITION", {
    "dependency_map": dependency_map,
    "ui_discloses_checklist_not_probability": ui_discloses_checklist,
}, blocking=False, note="The six checks are a governance checklist, not six statistically independent votes. Do not convert 5/6 or 6/6 into confidence/profit probability or tune weights on the consumed window.")

# 11. UI and observability governance.
ui_ok = (
    ui_discloses_checklist
    and "PRIMARY GATE" in ui_text
    and "SELECTIVE/FILTERED" in ui_text
    and "trade execution OFF" in ui_text
)
add("UI_GOVERNANCE", "ui", "PASS" if ui_ok else "FAIL", {
    "primary_gate_disclosed": "PRIMARY GATE" in ui_text,
    "readiness_not_probability": "readiness ≠ win probability" in ui_text,
    "execution_off": "trade execution OFF" in ui_text,
}, blocking=not ui_ok)

observability_ok = (
    isinstance(market.get("errors"), list)
    and isinstance(decision.get("errors"), list)
    and bool(decision.get("generated_at"))
    and bool(market.get("generated_at"))
    and bool(evidence.get("generated_at"))
    and bool(lineage.get("source_commits"))
)
add("OBSERVABILITY_AUDIT_TRAIL", "observability", "PASS" if observability_ok else "FAIL", {
    "market_generated_at": market.get("generated_at"),
    "evidence_generated_at": evidence.get("generated_at"),
    "decision_generated_at": decision.get("generated_at"),
    "lineage_version": lineage.get("version"),
}, blocking=not observability_ok)

# 12. Freeze governance prerequisites.
fresh_oos_policy = lineage.get("historical_window_policy") or {}
freeze_governance_ok = (
    fresh_oos_policy.get("status") == "CONSUMED_DIAGNOSTIC_NOT_FRESH_OOS"
    and fresh_oos_policy.get("fresh_oos_after_freeze_remains_primary_validation") is True
    and (lineage.get("guardrails") or {}).get("no_directional_threshold_search") is True
    and (lineage.get("guardrails") or {}).get("actionability_remains_primary_gate") is True
    and (lineage.get("guardrails") or {}).get("trade_execution") == "OFF"
)
add("FREEZE_GOVERNANCE_PREREQS", "freeze_governance", "PASS" if freeze_governance_ok else "FAIL", {
    "historical_window_policy": fresh_oos_policy,
    "guardrails": lineage.get("guardrails") or {},
}, blocking=not freeze_governance_ok)

hard_failures = [c for c in checks if c["status"] == "FAIL" and c["blocking"]]
conditions = [c for c in checks if c["status"] == "PASS_WITH_CONDITION"]
if hard_failures:
    overall = "FAIL"
    freeze_recommendation = "BLOCK_FREEZE"
elif conditions:
    overall = "PASS_WITH_CONDITIONS"
    freeze_recommendation = "READY_FOR_FREEZE_WITH_GOVERNANCE_CONDITIONS"
else:
    overall = "PASS"
    freeze_recommendation = "READY_FOR_FREEZE"

artifact = {
    "version": "1.0",
    "stage": "CRYPTO_11C5_FINAL_PREFREEZE_CROSSCHECK",
    "generated_at": iso_now(),
    "overall_decision": overall,
    "freeze_recommendation": freeze_recommendation,
    "model_frozen": False,
    "scope": universe.get("scope"),
    "model": {
        "canonical_direction": "v0.1 exact core",
        "decision_layer": "v0.4.1 regime-aware Actionability",
        "counter_thesis": "COUNTER_THESIS_0.2",
        "primary_gate": "ACTIONABILITY >=80 ACTIONABLE",
    },
    "summary": {
        "checks_total": len(checks),
        "pass": sum(1 for c in checks if c["status"] == "PASS"),
        "pass_with_condition": len(conditions),
        "fail": sum(1 for c in checks if c["status"] == "FAIL"),
        "blocking_failures": len(hard_failures),
    },
    "checks": checks,
    "conditions_carried_to_freeze": [
        "Treat six-check readiness as a dependent governance checklist, not six independent statistical signals.",
        "Do not convert readiness %, 5/6, 6/6, or historical hit rates into profit probability.",
        "Do not tune thresholds, check weights, or asset-specific rules on the consumed historical window.",
        "Fresh OOS after freeze remains the primary validation evidence; historical evidence/protocol/regulatory state was not backfilled.",
        "Any future material methodology change requires a new model version and new C.4/C.5/freeze cycle.",
    ],
    "diagnostic_reference": {
        "strict_6_of_6_observations": strict6.get("observations"),
        "strict_6_of_6_hit_rate_7d_percent": strict6.get("hit_rate_7d_percent"),
        "primary_gate_observations": primary.get("observations"),
        "primary_gate_hit_rate_7d_percent": primary.get("hit_rate_7d_percent"),
        "historical_status": test_design.get("historical_window_status"),
    },
    "governance": {
        "no_formula_change_by_this_audit": True,
        "no_threshold_search": True,
        "no_asset_specific_rules": True,
        "no_buy_sell": True,
        "profit_probability": "NOT_ESTIMATED",
        "trade_execution": "OFF",
        "fresh_oos_required_after_freeze": True,
    },
}
OUTPUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"11C.5: {overall}; checks={len(checks)}; blocking_failures={len(hard_failures)}; conditions={len(conditions)}")
raise SystemExit(1 if hard_failures else 0)
