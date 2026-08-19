#!/usr/bin/env python3
"""Hardening wrapper for Stage 11C v0.3 hybrid activation and refresh."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "scripts" / "build-crypto-decision-v03.py"
DECISION_PATH = ROOT / "data" / "crypto-decision-intelligence.json"
BT01_PATH = ROOT / "data" / "crypto-backtest.json"
BT02_PATH = ROOT / "data" / "crypto-backtest-v02.json"


def canonical_hash(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


spec = importlib.util.spec_from_file_location("crypto_decision_v03", MODEL_PATH)
model = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(model)

current = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
bt01 = json.loads(BT01_PATH.read_text(encoding="utf-8"))
bt02 = json.loads(BT02_PATH.read_text(encoding="utf-8"))
v01_hash = (bt01.get("model_snapshot") or {}).get("methodology_sha256")
v02_hash = (bt02.get("model_snapshot") or {}).get("methodology_sha256")
if not v01_hash or not v02_hash:
    raise SystemExit("v0.3 lineage requires methodology hashes from both prior diagnostic artifacts.")

if model.HYBRID_WEIGHTS != {"v01_absolute": 0.50, "v02_volatility_normalized": 0.50}:
    raise SystemExit("v0.3 fixed symmetric hybrid weights changed; activation fails closed.")
if abs(sum(model.HYBRID_WEIGHTS.values()) - 1.0) > 1e-12:
    raise SystemExit("v0.3 hybrid weights do not sum to 1.0.")

if current.get("version") == "0.2":
    current_v02_hash = canonical_hash(current.get("methodology") or {})
    if current_v02_hash != v02_hash:
        raise SystemExit(f"v0.3 lineage mismatch: current v0.2={current_v02_hash}, v0.2 retest={v02_hash}")
elif current.get("version") == "0.3":
    lineage = current.get("hybrid_refinement") or {}
    if lineage.get("source_v02_methodology_sha256") != v02_hash:
        raise SystemExit("Existing v0.3 artifact failed persistent v0.2 lineage validation.")
    if lineage.get("historical_windows_consumed") is not True:
        raise SystemExit("Existing v0.3 artifact does not preserve consumed-history governance.")
else:
    raise SystemExit(f"Unsupported decision artifact version for v0.3 activation/refresh: {current.get('version')}")

code = model.main()
artifact = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
lineage = artifact.setdefault("hybrid_refinement", {})
lineage["source_v01_methodology_sha256"] = v01_hash
lineage["source_v02_methodology_sha256"] = v02_hash
lineage["fixed_hybrid_weights_verified"] = True
lineage["historical_windows_consumed"] = True
artifact.setdefault("guardrails", {})["hybrid_weight_search_prohibited"] = True
artifact.setdefault("guardrails", {})["model_remains_unfrozen"] = True
DECISION_PATH.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
raise SystemExit(code)
