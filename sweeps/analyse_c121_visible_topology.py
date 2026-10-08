"""Validate shadow topology against fresh NoAI geometry and decode costs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from analyse_c121_pax_flux import numeric_fields


def decode(text, *, scoped=False):
    cases, invalidations, depths = [], [], []
    for line in text.splitlines():
        if "[0] [I] C121_VISIBLE_TOPOLOGY_CASE " in line:
            row = numeric_fields(line.split("C121_VISIBLE_TOPOLOGY_CASE ", 1)[1])
            fields = ("case", "station", "old_hit", "new_hit", "tiles", "original_ops", "shadow_ops")
            if any(not isinstance(row.get(k), int) or row[k] < 0 for k in fields):
                raise ValueError("invalid topology cost")
            if row["old_hit"] not in (0, 1) or row["new_hit"] not in (0, 1):
                raise ValueError("invalid hit status")
            cases.append(row)
        elif "[0] [I] C121_VISIBLE_TOPOLOGY_INVALIDATE " in line:
            payload = line.split("C121_VISIBLE_TOPOLOGY_INVALIDATE ", 1)[1]
            row = numeric_fields(payload)
            reason = re.search(r"\breason=(\w+)\b", payload)
            if reason is None or not isinstance(row.get("entries"), int) or row["entries"] < 0:
                raise ValueError("invalid invalidation")
            row["reason"] = reason[1]
            allowed = ("age", "input", "station_lines") if scoped else ("age", "input")
            if row.get("kept") != int(row["reason"] in allowed):
                raise ValueError("physical invalidation suppressed")
            invalidations.append(row)
        elif "[0] [I] C121_VISIBLE_TOPOLOGY_DEPTH " in line:
            row = numeric_fields(line.split("C121_VISIBLE_TOPOLOGY_DEPTH ", 1)[1])
            if row.get("extra") not in (0, 1) or row.get("equal") != 1:
                raise ValueError("invalid directed depth")
            if row.get("fallback") != row["extra"]+1 or row.get("have") != row.get("cap", -1)+row["extra"]:
                raise ValueError("fallback not exposed")
            depths.append(row)
    if not cases or [r["case"] for r in cases] != list(range(1, len(cases)+1)):
        raise ValueError("missing or duplicate topology calls")
    if sorted(r["extra"] for r in depths) != [0, 1]:
        raise ValueError("directed fallback matrix incomplete")
    if not invalidations:
        raise ValueError("no invalidation exposure")
    return cases, invalidations, depths


def summarise(cases, invalidations, depths):
    original = sum(r["original_ops"] for r in cases)
    shadow = sum(r["shadow_ops"] for r in cases)
    if original <= 0:
        raise ValueError("missing baseline cost")
    recovered = [r for r in cases if not r["old_hit"] and r["new_hit"]]
    return {"calls": len(cases), "original_ops": original, "shadow_ops": shadow,
            "saved_ops": original-shadow, "saved_pct": 100*(original-shadow)/original,
            "original_hits": sum(r["old_hit"] for r in cases),
            "shadow_hits": sum(r["new_hit"] for r in cases),
            "avoided_materialisations": len(recovered),
            "avoided_materialisations_saved_ops": sum(r["original_ops"]-r["shadow_ops"] for r in recovered),
            "invalidation_counts": dict(Counter(r["reason"] for r in invalidations)),
            "kept_invalidations_with_nonempty_shadow": sum(r["kept"] and r["entries"] > 0 for r in invalidations),
            "directed_depths": depths,
            "cost_scope": "station topology lookup/materialisation only; fresh oracle and logging excluded",
            "economic_verdict": "not_evaluated", "adoption": False}


def analyse(folder, *, scoped=False):
    report = json.loads((folder / "report.json").read_text(encoding="utf8"))
    if not report["pass"] or not all(report["checks"].values()):
        raise ValueError("unhealthy or incomplete diagnostic")
    raw = (folder / "engine.log").read_bytes()
    log_hash = hashlib.sha256(raw).hexdigest()
    if log_hash != report["log_sha256"]:
        raise ValueError("engine log changed")
    cases, invalidations, depths = decode(raw.decode("utf8"), scoped=scoped)
    result = summarise(cases, invalidations, depths)
    result.update(folder=str(folder), scoped=scoped, log_sha256=log_hash,
                  plan_sha256=hashlib.sha256((folder / "plan.json").read_bytes()).hexdigest(),
                  decoder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  cases=cases, invalidations=invalidations)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--scoped", action="store_true")
    args = parser.parse_args()
    result = analyse(args.folder, scoped=args.scoped)
    with args.out.open("x", encoding="utf8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("cases", "invalidations")}, indent=2))
