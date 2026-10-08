"""Post-traitement passif des logs V100bis ``rail_geometry_live_replan``.

Le banc moteur reste la source de verite.  Ce script ne rejoue aucune decision :
il extrait uniquement les devis rail en echec, les refreshs V100bis et le devenir
ulterieur des memes paires ``src/dst`` dans les logs ``script=4``.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re


ARM_RE = re.compile(r"railgeom_live_replan_(off|on)_seed(\d+)_r\d+\.log$")
DATE_RE = re.compile(r"OPEX\s+(\d{4})-(\d+)-(\d+)\s+")
QUOTE_RE = re.compile(
    r"RAIL_QUOTE_FAIL\s+src=(\d+)\s+dst=(\d+).*?reason=([^\s]+)\s+err=(-?\d+)"
)
REPLAN_RE = re.compile(
    r"RAIL_GEOM_REPLAN\s+src=(\d+)\s+dst=(\d+)\s+refreshed=(\d+)\s+"
    r"reason=([^\s]+)\s+first_err=(-?\d+)"
)
REPLAN_QUOTE_RE = re.compile(
    r"RAIL_GEOM_REPLAN_QUOTE\s+src=(\d+)\s+dst=(\d+)\s+ok=(\d+)\s+reason=([^\s]+)"
)
ATTEMPT_RE = re.compile(
    r"RAIL_ATTEMPT\s+src=(\d+)\s+dst=(\d+).*?ok=(\d+)\s+reason=([^\s]+)"
)
BUILD_RE = re.compile(r"RAIL_BUILD\s+line=\d+\s+src=(\d+)\s+dst=(\d+)")


def _date_key(line: str) -> tuple[int, int, int] | None:
    match = DATE_RE.search(line)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def _date_text(key: tuple[int, int, int] | None) -> str | None:
    if key is None:
        return None
    return f"{key[0]:04d}-{key[1]:02d}-{key[2]:02d}"


def analyse(engine_dir: Path) -> dict:
    arms = {
        "off": {
            "files": 0,
            "quote_failures": Counter(),
            "quote_errors": Counter(),
            "attempt_reasons": Counter(),
            "replans": [],
            "replan_quotes": [],
        },
        "on": {
            "files": 0,
            "quote_failures": Counter(),
            "quote_errors": Counter(),
            "attempt_reasons": Counter(),
            "replans": [],
            "replan_quotes": [],
        },
    }
    timelines: dict[tuple[str, int, int, int], list[dict]] = defaultdict(list)

    for path in sorted(engine_dir.glob("*.log")):
        arm_match = ARM_RE.match(path.name)
        if arm_match is None:
            continue
        arm, seed_text = arm_match.groups()
        seed = int(seed_text)
        arms[arm]["files"] += 1
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            date_key = _date_key(line)
            quote = QUOTE_RE.search(line)
            if quote is not None:
                src, dst, reason, error = quote.groups()
                arms[arm]["quote_failures"][reason] += 1
                arms[arm]["quote_errors"][f"{reason}:{error}"] += 1
                timelines[(arm, seed, int(src), int(dst))].append(
                    {"kind": "quote_fail", "date_key": date_key, "date": _date_text(date_key),
                     "line": line_no, "reason": reason, "error": int(error)}
                )

            replan = REPLAN_RE.search(line)
            if replan is not None:
                src, dst, refreshed, reason, error = replan.groups()
                event = {
                    "seed": seed,
                    "src": int(src),
                    "dst": int(dst),
                    "date_key": date_key,
                    "date": _date_text(date_key),
                    "line": line_no,
                    "refreshed": int(refreshed),
                    "reason": reason,
                    "first_error": int(error),
                }
                arms[arm]["replans"].append(event)
                timelines[(arm, seed, int(src), int(dst))].append({"kind": "replan", **event})

            replan_quote = REPLAN_QUOTE_RE.search(line)
            if replan_quote is not None:
                src, dst, ok, reason = replan_quote.groups()
                event = {
                    "seed": seed,
                    "src": int(src),
                    "dst": int(dst),
                    "date_key": date_key,
                    "date": _date_text(date_key),
                    "line": line_no,
                    "ok": int(ok),
                    "reason": reason,
                }
                arms[arm]["replan_quotes"].append(event)
                timelines[(arm, seed, int(src), int(dst))].append({"kind": "replan_quote", **event})

            attempt = ATTEMPT_RE.search(line)
            if attempt is not None:
                src, dst, ok, reason = attempt.groups()
                arms[arm]["attempt_reasons"][reason] += 1
                timelines[(arm, seed, int(src), int(dst))].append(
                    {"kind": "attempt", "date_key": date_key, "date": _date_text(date_key),
                     "line": line_no, "ok": int(ok), "reason": reason}
                )

            build = BUILD_RE.search(line)
            if build is not None:
                src, dst = build.groups()
                timelines[(arm, seed, int(src), int(dst))].append(
                    {"kind": "build", "date_key": date_key, "date": _date_text(date_key), "line": line_no}
                )

    replan_cases = []
    for event in arms["on"]["replans"]:
        key = ("on", event["seed"], event["src"], event["dst"])
        later = [
            item for item in timelines[key]
            if (item.get("date_key"), item.get("line", -1))
            > (event.get("date_key"), event.get("line", -1))
        ]
        later_success = next(
            (item for item in later if item["kind"] == "build"
             or (item["kind"] == "attempt" and item.get("ok") == 1)),
            None,
        )
        later_attempt = next((item for item in later if item["kind"] == "attempt"), None)
        off_events = timelines.get(("off", event["seed"], event["src"], event["dst"]), [])
        off_stnfail = next(
            (item for item in off_events if item["kind"] == "quote_fail" and item.get("reason") == "STNFAIL"),
            None,
        )
        replan_cases.append(
            {
                "seed": event["seed"],
                "src": event["src"],
                "dst": event["dst"],
                "replan_date": event["date"],
                "refreshed": event["refreshed"],
                "refresh_reason": event["reason"],
                "first_error": event["first_error"],
                "later_attempt": None if later_attempt is None else {
                    k: v for k, v in later_attempt.items() if k not in {"date_key", "line"}
                },
                "later_success": None if later_success is None else {
                    k: v for k, v in later_success.items() if k not in {"date_key", "line"}
                },
                "off_same_pair_stnfail": None if off_stnfail is None else {
                    k: v for k, v in off_stnfail.items() if k not in {"date_key", "line"}
                },
            }
        )

    def serialise_arm(data: dict) -> dict:
        return {
            "files": data["files"],
            "quote_failures": dict(sorted(data["quote_failures"].items())),
            "quote_errors": dict(sorted(data["quote_errors"].items())),
            "attempt_reasons": dict(sorted(data["attempt_reasons"].items())),
            "replan_count": len(data["replans"]),
            "replan_quote_count": len(data["replan_quotes"]),
            "replan_refresh_reasons": dict(sorted(Counter(x["reason"] for x in data["replans"]).items())),
        }

    return {
        "schema_version": 1,
        "source": str(engine_dir),
        "arms": {arm: serialise_arm(data) for arm, data in arms.items()},
        "on_replan_cases": replan_cases,
        "on_replan_pairs_with_later_success": sum(case["later_success"] is not None for case in replan_cases),
        "on_replan_pairs_with_off_same_pair_stnfail": sum(
            case["off_same_pair_stnfail"] is not None for case in replan_cases
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("engine_dir", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    payload = analyse(args.engine_dir)
    rendered = json.dumps(payload, indent=2, sort_keys=False)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
