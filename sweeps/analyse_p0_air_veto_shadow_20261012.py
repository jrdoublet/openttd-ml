"""Summarize AIR live-veto diagnostic logs, without claiming lost buildable projects.

This shadow is intentionally only a *sample* of retrospective recomputations:
at most 12 requests per projects pass and ranks <= 11 in builder. Source logs
must come from the same frozen bundle as the C66 diagnosis. A replay can itself
shift game timing or return first=none, and the rejected route might not be
funded or geographically constructible.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re


PAT = re.compile(r"OPEX (\d{4})-(\d{1,2})-(\d{1,2}) P0_AIR_VETO (.*)$")
EXPECTED = {"mode", "stage", "tick", "rank", "built_before", "best", "arm",
            "src", "dst", "reuseA", "reuseB", "first", "reasons"}


def parse(lines):
    records = []
    for line in lines:
        hit = PAT.search(line)
        if not hit:
            continue
        year, month, day, values = hit.groups()
        fields = {}
        for item in values.split():
            if "=" not in item:
                raise ValueError(f"unparseable AIR veto token: {item}")
            key, value = item.split("=", 1)
            if key in fields:
                raise ValueError(f"duplicate AIR veto field: {key}")
            fields[key] = value
        if EXPECTED - set(fields):
            raise ValueError(f"missing AIR veto fields: {EXPECTED - set(fields)}")
        if fields["mode"] != "air" or fields["stage"] not in ("projects", "builder"):
            raise ValueError("unexpected AIR veto mode/stage")
        records.append({"year": int(year), "month": int(month), "day": int(day),
                        "fields": fields})
    return records


def summarize(records):
    out = {}
    for year in sorted({x["year"] for x in records}):
        hits = [x for x in records if x["year"] == year]
        first = Counter(x["fields"]["first"] for x in hits)
        overlapping = Counter(reason for x in hits
                              for reason in x["fields"]["reasons"].split(",")
                              if reason and reason != "none")
        od_all = {(x["fields"]["src"], x["fields"]["dst"], x["fields"]["arm"])
                  for x in hits}
        od_date = {(x["month"], x["day"], x["fields"]["src"],
                    x["fields"]["dst"], x["fields"]["arm"]) for x in hits}
        pass_signature = {(x["month"], x["day"], x["fields"]["tick"],
                           x["fields"]["stage"]) for x in hits}
        out[str(year)] = {
            "logged_veto_replays": len(hits),
            "unique_od_arm_in_sample": len(od_all),
            "unique_od_arm_day_in_sample": len(od_date),
            "observed_tick_stage_passes": len(pass_signature),
            "stage": dict(sorted(Counter(x["fields"]["stage"] for x in hits).items())),
            "arms": dict(sorted(Counter(x["fields"]["arm"] for x in hits).items())),
            "first_reason": dict(sorted(first.items())),
            "all_reason_occurrences": dict(sorted(overlapping.items())),
            "ambiguous_replay_none": first.get("none", 0),
            "example_first_8": [{"date": f"{year}-{x['month']:02d}-{x['day']:02d}",
                                 "tick": x["fields"]["tick"],
                                 "rank": x["fields"]["rank"],
                                 "arm": x["fields"]["arm"],
                                 "src": x["fields"]["src"],
                                 "dst": x["fields"]["dst"],
                                 "first": x["fields"]["first"]}
                                for x in hits[:8]],
        }
    return out


def analyze(engine, seeds=(42, 100, 999), policy="p0_air_live_veto_reason_shadow"):
    result = {}
    for seed in seeds:
        path = engine / f"{policy}_seed{seed}_r0.log"
        if not path.exists():
            raise FileNotFoundError(path)
        events = parse(path.read_text(encoding="utf-8", errors="replace").splitlines())
        result[str(seed)] = {"events": len(events), "years": summarize(events)}
    return {"engine_logs": str(engine), "policy": policy, "by_seed": result,
            "limitations": [
                "Logs emitted only from intentionally bounded retrospectively diagnosed veto samples.",
                "No extrapolation of observed reason frequencies to all candidate OD or years.",
                "The shadow may alter simulation timing; do not event-pair this run to different probe flags.",
                "Reason labels reflect a second live recheck AFTER the initial boolean veto.",
                "A veto may be normal after earlier successful construction in the same batch.",
                "No project counterfactual geometry, profit, live finance, or construction is proven.",
            ]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("engine", type=Path)
    p.add_argument("--seeds", nargs="+", type=int, default=[42, 100, 999])
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    if args.out.exists():
        p.error("refusing to overwrite existing result")
    result = analyze(args.engine, tuple(args.seeds))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["by_seed"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
