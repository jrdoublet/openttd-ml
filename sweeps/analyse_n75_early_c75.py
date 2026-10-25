"""Lecture hors jeu des traces N75_EARLY_C75 (une ou plusieurs parties).

Les traces sont des observations de passes. Les projets distincts sont
dedupliques par fichier, annee et cle, jamais par occurrence de recheck.
Le signe N5|pass_tick|rank|mode|phase|line permet de verifier E/T/B/X/P meme
avec `probes=2`; B seul correspond a un chantier reel dans cette passe.
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


EVENT = re.compile(r"N75_EARLY_C75\s+([^\r\n]+)")
PAIR = re.compile(r"(?:^|\s)([a-z_]+)=([^\s]+)")
SIGN = re.compile(r"N5\|(\d+)\|(\d+)\|([ATRW])\|([ETBXP])\|(-?\d+)")


def parse_lines(lines, source="<memory>"):
    """Retourne événements structurés et panneaux signés, sans sommer les rechecks."""
    events = []
    signs = set()
    for line in lines:
        for match in EVENT.finditer(line):
            fields = dict(PAIR.findall(match.group(1)))
            if {"phase", "pass_tick", "rank", "key", "mode", "year"} <= fields.keys():
                events.append({**fields, "source": source})
        for match in SIGN.finditer(line):
            signs.add((source, *match.groups()))
    return events, signs


def summarize(events, signs=()):
    per_year = defaultdict(lambda: Counter())
    distinct = defaultdict(set)
    for entry in events:
        year = entry["year"]
        phase = entry["phase"]
        event_id = (entry["source"], entry["pass_tick"], entry["rank"], entry["key"])
        distinct[(year, "unique_candidate_keys")].add((entry["source"], entry["key"]))
        distinct[(year, phase)].add(event_id)
        if phase == "eligible" and entry.get("reason") == "shadow_only":
            distinct[(year, "shadow_only")].add(event_id)
        if phase == "built":
            distinct[(year, "unique_built_keys")].add((entry["source"], entry["key"]))
    for (year, phase), rejected in tuple(distinct.items()):
        if phase != "rejected":
            continue
        attempts = distinct[(year, "attempt")]
        distinct[(year, "executor_rejected")].update(rejected & attempts)
        distinct[(year, "screen_rejected")].update(rejected - attempts)
    for (year, phase), ids in distinct.items():
        per_year[year][phase] = len(ids)
    for (source, tick, rank, mode, code, line_id) in signs:
        distinct[("sign", code)].add((source, tick, rank, mode, code, line_id))
    return {
        "per_year": {year: dict(counts) for year, counts in sorted(per_year.items())},
        "signed_events": {phase: len(distinct[("sign", phase)]) for phase in "ETBXP"},
        "measurement_limit": (
            "eligible is a screen, attempt is an executor call, built is a physical line "
            "constructed in the same pass; these cannot establish terminal profit uplift "
            "or whether the baseline would have built the line next pass"
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs="+", type=Path, help="fichiers texte engine des bras N75")
    parser.add_argument("--out", type=Path, help="rapport JSON facultatif")
    args = parser.parse_args(argv)
    events = []
    signs = set()
    for path in args.logs:
        with path.open(encoding="utf-8", errors="replace") as handle:
            part_events, part_signs = parse_lines(handle, str(path))
        events.extend(part_events)
        signs.update(part_signs)
    result = summarize(events, signs)
    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
