#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def main():
    for path in sorted(RESULTS.glob("rail_origin_reuse*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        pc = data.get("policy_comparison")
        if not isinstance(pc, dict):
            continue
        py = (pc.get("aggregates") or {}).get("profit_year") or {}
        delta = (py.get("policy_delta") or {}).get("mean")
        gap = (py.get("duel_gap_evolution") or {}).get("mean")
        ci = (py.get("policy_delta") or {}).get("mean_bootstrap_95pct_ci")
        reference = pc.get("reference_policy_id")
        variant = pc.get("variant_policy_id")
        print(
            f"{path.name}\tyears={data.get('years')}\tpairs={pc.get('complete_pairs')}"
            f"\tref={reference}\tvariant={variant}\tprofit_delta={delta}\tgap_evolution={gap}"
            f"\tci={ci}\tverdict={pc.get('verdict')}"
        )


if __name__ == "__main__":
    main()
