#!/usr/bin/env python3
"""P6: reproduce descriptive first AIR line estimates versus saved line profits.

Reads existing company-0 C121_BUILD line=0 records and monthly bench JSONL;
never invokes OpenTTD. The realized number is the January 1 following an
accounting year, from line_telemetry.profit_this_year_gbp (NOT actual_profit,
target_profit, or the stale profit_last_year_gbp).

Usage:
  python -X utf8 sweeps/diag_p6_firstline_realized.py \
    --logs results/modal_air_defaults_master85c88_40x5_20261025_engine \
    --snapshots results/modal_air_defaults_master85c88_40x5_20261025.jsonl
"""

import argparse
from collections import defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
from statistics import mean


FILENAME = re.compile(r"^(?P<arm>.+)_seed(?P<seed>\d+)_r(?P<rep>\d+)\.log(?:\.gz)?$")
BUILD = re.compile(r"\[0\]\s+\[I\]\s+C121_BUILD\s+(?P<fields>[^\r\n]*)")
KV = re.compile(r"([A-Za-z_][A-Za-z_0-9]*)=(\S+)")
YEARS = (1970, 1971, 1972)


def number(token, context, positive=False):
    if token is None:
        return None
    try:
        value = float(token)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context}: invalid numeric value {token!r}") from exc
    if not math.isfinite(value) or (positive and value <= 0):
        raise ValueError(f"{context}: invalid numeric value {token!r}")
    return value


def _bytes_sha256(path):
    opening = gzip.open if str(path).endswith(".gz") else open
    digest = hashlib.sha256()
    with opening(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_build(path):
    opening = gzip.open if str(path).endswith(".gz") else open
    builds = []
    with opening(path, "rt", encoding="utf-8") as stream:
        for line_no, raw in enumerate(stream, 1):
            match = BUILD.search(raw)
            if not match:
                continue
            context = f"{path}:{line_no}"
            tokens = match["fields"].split()
            entries = [KV.fullmatch(token) for token in tokens]
            if any(entry is None for entry in entries):
                raise ValueError(f"{context}: malformed C121_BUILD field")
            keys = [entry[1] for entry in entries]
            if len(keys) != len(set(keys)):
                raise ValueError(f"{context}: duplicate C121_BUILD field")
            values = {entry[1]: entry[2] for entry in entries}
            if values.get("line") != "0":
                continue
            if values.get("arm") != "newpair" or values.get("new_airports") != "2":
                raise ValueError(f"{context}: unexpected first AIR line type")
            try:
                stations = tuple(sorted((
                    int(values["station_id_a"]), int(values["station_id_b"])
                )))
            except (KeyError, ValueError) as exc:
                raise ValueError(f"{context}: missing station identifiers") from exc
            if len(set(stations)) != 2 or stations[0] < 0:
                raise ValueError(f"{context}: invalid station pair")
            estimated = number(values.get("decision_profit"), context)
            capital = number(values.get("decision_capital"), context, positive=True)
            if estimated is None or capital is None:
                raise ValueError(f"{context}: missing decision quote")
            builds.append({
                "stations": stations,
                "decision_profit": estimated,
                "decision_capital_quote": capital,
                "decision_roi_quote": estimated / capital,
                "actual_profit_second_quote": number(values.get("actual_profit"), context),
                "target_profit_quote": number(values.get("target_profit"), context),
                "initial_plan_vehicles": number(values.get("decision_n"), context),
            })
    if len(builds) != 1:
        raise ValueError(f"{path}: expected one first-line C121_BUILD, got {len(builds)}")
    return builds[0]


def collect_builds(folder):
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"missing engine-log directory: {folder}")
    paths = sorted((*folder.glob("*.log"), *folder.glob("*.log.gz")))
    if not paths:
        raise ValueError(f"no engine logs: {folder}")
    games = {}
    for path in paths:
        matched = FILENAME.fullmatch(path.name)
        if matched is None:
            raise ValueError(f"unidentified engine log: {path}")
        if matched["arm"] != "air_defaults":
            raise ValueError(f"unexpected campaign arm: {path}")
        seed, repetition = int(matched["seed"]), int(matched["rep"])
        if repetition != 0:
            raise ValueError(f"unexpected repeat: {path}")
        identity = (seed, repetition)
        base = path.name[:-3] if path.name.endswith(".gz") else path.name
        digest = _bytes_sha256(path)
        if identity in games:
            if games[identity]["basename"] != base or games[identity]["sha256"] != digest:
                raise ValueError(f"ambiguous or contradictory first-line logs: {path}")
            games[identity]["files"].append(str(path))
            continue
        games[identity] = {
            **parse_build(path), "basename": base,
            "sha256": digest, "files": [str(path)],
        }
    return games


def _station_tuple(row):
    values = row.get("station_ids")
    if (not isinstance(values, list) or len(values) != 2
            or any(not isinstance(value, int) for value in values)):
        return None
    return tuple(sorted(values))


def _line_match(lines, stations, context):
    if not isinstance(lines, list):
        raise ValueError(f"{context}: missing line telemetry array")
    if any(not isinstance(line, dict) for line in lines):
        raise ValueError(f"{context}: malformed line telemetry")
    matches = [line for line in lines
               if line.get("mode") == "air" and _station_tuple(line) == stations]
    if len(matches) > 1:
        raise ValueError(f"{context}: ambiguous matching AIR lines")
    return matches[0] if matches else None


def _read_line(line, context):
    profit = number(line.get("profit_this_year_gbp"), context)
    ids = line.get("vehicle_ids")
    if ids is not None:
        if (not isinstance(ids, list)
                or any(not isinstance(value, int) for value in ids)
                or len(ids) != len(set(ids))):
            raise ValueError(f"{context}: invalid aircraft identifiers")
        ids = sorted(ids)
    return {
        "observed_profit_year": profit,
        "aircraft_ids": ids,
        "observed_aircraft_count": line.get("vehicles"),
    }


def read_snapshots(path, games):
    """Stream JSONL: retain first 1970 sighting and January next-year snapshots."""
    required_dates = {f"{year + 1}-01-01": year for year in YEARS}
    snapshots = defaultdict(dict)
    initial = {}
    provenance = None
    with Path(path).open("r", encoding="utf-8") as stream:
        for line_no, raw in enumerate(stream, 1):
            row = json.loads(raw)
            run = row.get("run")
            if not isinstance(run, list) or len(run) != 3 or run[0] != "OpexAI":
                continue
            key = tuple(run[1:])
            if key not in games:
                continue
            day = row.get("date")
            needed = day in required_dates
            first = isinstance(day, str) and day.startswith("1970-")
            if not needed and not first:
                continue
            context = f"{path}:{line_no}:{key}:{day}"
            stamp = (row.get("campaign_id"), row.get("source_bundle_sha256"),
                     row.get("duel_policy_id"))
            game_identity = f"{stamp[0]}:policy={stamp[2]}:s{key[0]}:r{key[1]}"
            if (not stamp[0] or not isinstance(stamp[1], str)
                    or not re.fullmatch(r"[0-9a-f]{64}", stamp[1])
                    or stamp[2] != "air_defaults" or row.get("policy_id") != stamp[2]
                    or row.get("game_id") != game_identity):
                raise ValueError(f"{context}: missing/invalid campaign provenance")
            if provenance is None:
                provenance = stamp
            elif provenance != stamp:
                raise ValueError(f"{context}: campaign provenance changed")
            telemetry = row.get("line_telemetry")
            if not isinstance(telemetry, dict) or telemetry.get("ok") is not True:
                observed = {"observed_profit_year": None, "aircraft_ids": None,
                            "observation_error": (
                                telemetry.get("error") if isinstance(telemetry, dict)
                                else "no_line_telemetry"
                            )}
            else:
                matched = _line_match(telemetry.get("lines"), games[key]["stations"], context)
                observed = (
                    {**_read_line(matched, context), "observation_error": None}
                    if matched is not None else
                    {"observed_profit_year": None, "aircraft_ids": None,
                     "observation_error": "no_matching_air_line"}
                )
            if needed:
                year = required_dates[day]
                if year in snapshots[key]:
                    raise ValueError(f"{context}: duplicate January checkpoint")
                snapshots[key][year] = {"snapshot_date": day, **observed}
            if (first and observed["aircraft_ids"]
                    and (key not in initial or day < initial[key]["snapshot_date"])):
                initial[key] = {"snapshot_date": day, "aircraft_ids": observed["aircraft_ids"]}
    return snapshots, initial, provenance


def _check_manifest(logs, snapshots, games, provenance, manifest=None):
    """Cross-check the campaign's declared artifacts and games when available.

    Frozen manifests contain Linux /work paths. Resolve them relative to the
    manifest's original parent rather than treating /work as a Windows path.
    A manifest does not authenticate the bytes of individual engine logs.
    """
    snapshots = Path(snapshots)
    selected = Path(manifest) if manifest is not None else snapshots.with_suffix(".manifest.json")
    if not selected.is_file():
        if manifest is not None:
            raise ValueError(f"manifest explicitly requested but missing: {selected}")
        return False, None
    try:
        source = json.loads(selected.read_text(encoding="utf-8"))
        if not isinstance(source, dict):
            raise ValueError("not an object")
        artifacts = source["artifacts"]
        declared_manifest = PurePosixPath(artifacts["manifest"])
        if (not declared_manifest.is_absolute()
                or declared_manifest.name != selected.name):
            raise ValueError("manifest path/name mismatch")
        root = declared_manifest.parent
        for label, supplied in (("engine_logs", logs), ("checkpoints", snapshots)):
            declared = PurePosixPath(artifacts[label])
            relative = declared.relative_to(root)
            if (not relative.parts or any(part == ".." for part in relative.parts)
                    or (selected.parent.resolve() / Path(*relative.parts)).resolve()
                    != Path(supplied).resolve()):
                raise ValueError(f"manifest {label} does not match supplied source")
        stamp = (source["campaign_id"], source["source_bundle"]["sha256"],
                 source["policy"]["id"])
        if (provenance is None or stamp != provenance
                or not isinstance(stamp[1], str)
                or re.fullmatch(r"[0-9a-f]{64}", stamp[1]) is None):
            raise ValueError("manifest campaign, bundle or policy mismatch")
        entries = source["games"]
        if not isinstance(entries, list):
            raise ValueError("manifest games must be a list")
        identities = set()
        for game in entries:
            seed, repetition = game["seed"], game["repeat"]
            if (type(seed) is not int or type(repetition) is not int
                    or seed < 0 or repetition < 0):
                raise ValueError("manifest invalid game seed or repetition")
            identity = (seed, repetition)
            expected_id = f"{stamp[0]}:policy={stamp[2]}:s{seed}:r{repetition}"
            slot = game["company_slots"]["0"]
            if (identity in identities or game["policy_id"] != stamp[2]
                    or game["game_id"] != expected_id
                    or slot["ai"] != "OpexAI" or slot["policy_id"] != stamp[2]):
                raise ValueError(f"manifest invalid or duplicate OpexAI game: {identity}")
            identities.add(identity)
        if identities != set(games):
            raise ValueError("manifest games disagree with engine-log identities")
    except (KeyError, TypeError, AttributeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid or conflicting manifest {selected}: {exc}") from exc
    return True, str(selected)


def _ranks(values):
    result = [0] * len(values)
    ordered = sorted(range(len(values)), key=lambda position: values[position])
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[index]]:
            end += 1
        rank = (index + 1 + end) / 2
        for position in ordered[index:end]:
            result[position] = rank
        index = end
    return result


def _pearson(x, y):
    if len(x) < 2:
        return None
    ax, ay = mean(x), mean(y)
    covariance = sum((a - ax) * (b - ay) for a, b in zip(x, y))
    denominator = math.sqrt(sum((a - ax) ** 2 for a in x) *
                            sum((b - ay) ** 2 for b in y))
    return covariance / denominator if denominator else None


def _statistics(rows, expected):
    present = [row for row in rows if row["observed_profit_year"] is not None]
    xs = [row["decision_profit"] for row in present]
    ys = [row["observed_profit_year"] for row in present]
    return {
        "expected_games": expected,
        "observed_games": len(present),
        "missing_games": expected - len(present),
        "mean_decision_profit": round(mean(xs), 3) if xs else None,
        "mean_observed_profit": round(mean(ys), 3) if ys else None,
        "ratio_sum_observed_to_decision_pct": (
            round(100 * sum(ys) / sum(xs), 3) if sum(xs) else None
        ),
        "bias_decision_minus_observed": (
            round(mean(a - b for a, b in zip(xs, ys)), 3) if xs else None
        ),
        "mean_absolute_error": (
            round(mean(abs(a - b) for a, b in zip(xs, ys)), 3) if xs else None
        ),
        "pearson": (round(_pearson(xs, ys), 4) if _pearson(xs, ys) is not None else None),
        "spearman": (
            round(_pearson(_ranks(xs), _ranks(ys)), 4)
            if _pearson(_ranks(xs), _ranks(ys)) is not None else None
        ),
    }


def _fleet_id_cohorts(rows):
    """Endpoint aircraft-ID agreement only, not proof of unchanged operations."""
    labels = ("same_ids", "different_ids", "unknown_ids")
    grouped = {label: [] for label in labels}
    for row in rows:
        changed = row["fleet_changed_since_first_observation"]
        label = "unknown_ids" if changed is None else (
            "different_ids" if changed else "same_ids")
        grouped[label].append(row)
    return {
        label: {"cohort_games": len(grouped[label]),
                **_statistics(grouped[label], len(grouped[label]))}
        for label in labels
    }


def analyze(logs, snapshots, expected_games=40, manifest=None):
    games = collect_builds(logs)
    if len(games) != expected_games:
        raise ValueError(f"expected {expected_games} independent games; found {len(games)}")
    measured, first, provenance = read_snapshots(snapshots, games)
    manifest_verified, manifest_path = _check_manifest(
        logs, snapshots, games, provenance, manifest)
    details, cohorts = [], defaultdict(list)
    for (seed, repetition), entry in sorted(games.items()):
        baseline = first.get((seed, repetition))
        for year in YEARS:
            obs = measured[(seed, repetition)].get(year, {
                "snapshot_date": None, "observed_profit_year": None,
                "aircraft_ids": None, "observation_error": "missing_january_checkpoint",
            })
            values = {
                "seed": seed, "repeat": repetition, "year": year,
                "stations": entry["stations"],
                "decision_profit": entry["decision_profit"],
                "decision_capital_quote": entry["decision_capital_quote"],
                "decision_roi_quote": entry["decision_roi_quote"],
                "actual_profit_second_quote": entry["actual_profit_second_quote"],
                "target_profit_quote": entry["target_profit_quote"],
                "initial_fleet_snapshot": baseline,
                **obs,
                "fleet_changed_since_first_observation": (
                    sorted(baseline["aircraft_ids"]) != sorted(obs["aircraft_ids"])
                    if baseline and obs["aircraft_ids"] is not None else None
                ),
            }
            details.append(values)
            cohorts[year].append(values)
    return {
        "scope": "first constructed AIR lines, observed vehicles, no causal intervention",
        "provenance": {
            "campaign_id": provenance[0] if provenance else None,
            "source_bundle_sha256": provenance[1] if provenance else None,
            "duel_policy_id": provenance[2] if provenance else None,
        },
        "provenance_manifest_verified": manifest_verified,
        "provenance_manifest_path": manifest_path,
        "games": len(games),
        "years": {str(year): _statistics(cohorts[year], len(games)) for year in YEARS},
        "fleet_id_cohorts_by_year": {
            str(year): _fleet_id_cohorts(cohorts[year]) for year in YEARS
        },
        "rows": details,
        "limitations": [
            "1970 first-line operation starts after January 1; year is partial.",
            "C121 actual_profit and target_profit are quotes, not observed results.",
            "decision_capital is a quote, not verified physical CAPEX.",
            "profit_this_year_gbp is grouped current-aircraft earnings, not infra-adjusted ROI.",
            "Fleet rotation can remove historical profits from later snapshots.",
            "Fleet cohorts compare aircraft IDs only at the earliest 1970 sighting "
            "and the January checkpoints; equal endpoints do not prove an "
            "unchanged fleet throughout the accounting year.",
            "Fleet ID cohorts are selected outcomes, not matched causal arms; "
            "different aircraft IDs do not isolate the cause of profit drift.",
            "Only constructed lines are observed; no rejected-project counterfactual.",
            "Manifest checks campaign, bundle, declared paths and game identities when "
            "available, but does not hash individual engine logs; an in-place replacement "
            "under the declared name cannot be detected from this manifest.",
            "Without a manifest the campaign origin of engine logs is unverified.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", required=True, type=Path)
    parser.add_argument("--snapshots", required=True, type=Path)
    parser.add_argument("--manifest", type=Path,
                        help="optional frozen campaign manifest; autodetected next to snapshots")
    parser.add_argument("--expected-games", type=int, default=40)
    args = parser.parse_args(argv)
    try:
        if args.expected_games < 1:
            raise ValueError("expected-games must be positive")
        output = analyze(args.logs, args.snapshots, args.expected_games,
                         manifest=args.manifest)
    except (OSError, ValueError, EOFError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
