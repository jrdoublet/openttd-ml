"""Full refresh-body costs, requiring equal prepared inputs and date."""
import argparse
import hashlib
import json
from pathlib import Path
from analyse_c121_pax_flux import numeric_fields


def decode(text):
    rows = []
    fields = ("case", "stable", "input_equal", "equal", "original_ops", "candidate_ops", "samples")
    for line in text.splitlines():
        if "[0] [I] C121_VISIBLE_FUSED_CASE " not in line:
            continue
        row = numeric_fields(line.split("C121_VISIBLE_FUSED_CASE ", 1)[1])
        if any(not isinstance(row.get(k), int) or row[k] < 0 for k in fields):
            raise ValueError("missing or invalid body measurement")
        if any(row[k] not in (0, 1) for k in ("stable", "input_equal", "equal")):
            raise ValueError("invalid match status")
        if row["stable"] and row["input_equal"] and not row["equal"]:
            raise ValueError("matched outputs differ")
        rows.append(row)
    if not rows or [r["case"] for r in rows] != list(range(1, len(rows)+1)):
        raise ValueError("missing or duplicate cases")
    return rows


def summarise(rows):
    matched = [r for r in rows if r["stable"] and r["input_equal"]]
    original = sum(r["original_ops"] for r in matched)
    candidate = sum(r["candidate_ops"] for r in matched)
    if not matched or original <= 0:
        raise ValueError("no comparable full-body costs")
    return {"cases": len(rows), "matched_cases": len(matched),
            "date_crossing_cases": sum(not r["stable"] for r in rows),
            "stable_date_changed_inputs": sum(r["stable"] and not r["input_equal"] for r in rows),
            "matched_outputs_equal": all(r["equal"] for r in matched),
            "original_body_ops": original, "candidate_body_ops": candidate,
            "saved_ops": original-candidate, "saved_pct": 100*(original-candidate)/original,
            "original_ops_per_quote": original/len(matched), "candidate_ops_per_quote": candidate/len(matched),
            "matched_observed_margin_cases": sum(r["samples"] > 0 for r in matched),
            "cost_scope": "full quote body including symmetric input capture and internal logs, excluding cache restoration and comparison",
            "limitation": "live API changes and date crossings excluded; instrumented trajectory, not economic qualification",
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
