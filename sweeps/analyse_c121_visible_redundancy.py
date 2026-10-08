"""Matched NoAI economics costs, with strict equivalence and temporal coverage."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from analyse_c121_pax_flux import numeric_fields


def decode(text):
    rows = []
    fields = ("case", "stable", "equal", "have", "cap", "fallback",
              "target_ops", "before_ops", "after_ops", "fused_ops")
    for line in text.splitlines():
        if "[0] [I] C121_VISIBLE_REDUNDANCY_CASE " not in line:
            continue
        payload = line.split("C121_VISIBLE_REDUNDANCY_CASE ", 1)[1]
        row = numeric_fields(payload)
        if any(not isinstance(row.get(k), int) or row[k] < 0 for k in fields):
            raise ValueError("missing or invalid measurement")
        reason = re.search(r"\breason=(\w+)\b", payload)
        if reason is None or row["stable"] not in (0, 1) or row["equal"] not in (0, 1):
            raise ValueError("invalid comparison")
        if row["stable"] and not row["equal"]:
            raise ValueError("matched outputs differ")
        if row["fallback"] > 2:
            raise ValueError("invalid fallback count")
        row["reason"] = reason[1]
        rows.append(row)
    if not rows or [r["case"] for r in rows] != list(range(1, len(rows)+1)):
        raise ValueError("missing or duplicate cases")
    return rows


def summarise(rows):
    stable = [r for r in rows if r["stable"]]
    if not stable:
        raise ValueError("no temporally matched cases")
    original = sum(r["target_ops"]+r["before_ops"]+r["after_ops"] for r in stable)
    fused = sum(r["fused_ops"] for r in stable)
    if original <= 0:
        raise ValueError("missing baseline cost")
    return {"cases": len(rows), "matched_cases": len(stable),
            "date_crossing_cases": len(rows)-len(stable),
            "matched_outputs_equal": all(r["equal"] for r in stable),
            "original_economics_ops": original, "fused_economics_ops": fused,
            "saved_ops": original-fused, "saved_pct": 100*(original-fused)/original,
            "target_ops": sum(r["target_ops"] for r in stable),
            "before_ops": sum(r["before_ops"] for r in stable),
            "after_ops": sum(r["after_ops"] for r in stable),
            "fallback_depths": sum(r["fallback"] for r in stable),
            "rebuild_reasons_all_cases": dict(Counter(r["reason"] for r in rows)),
            "cost_scope": "economics only, capture and fallback included; demand geometry excluded",
            "economic_verdict": "not_evaluated", "adoption": False}


def analyse(folder):
    report = json.loads((folder / "report.json").read_text(encoding="utf8"))
    if not report["pass"] or not all(report["checks"].values()):
        raise ValueError("unhealthy or incomplete diagnostic")
    raw = (folder / "engine.log").read_bytes()
    log_hash = hashlib.sha256(raw).hexdigest()
    if log_hash != report["log_sha256"]:
        raise ValueError("engine log changed")
    rows = decode(raw.decode("utf8"))
    result = summarise(rows)
    result.update(folder=str(folder), log_sha256=log_hash,
                  plan_sha256=hashlib.sha256((folder / "plan.json").read_bytes()).hexdigest(),
                  decoder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), rows=rows)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = analyse(args.folder)
    with args.out.open("x", encoding="utf8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
