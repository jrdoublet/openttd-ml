"""V251 host-only reader of industry-type capability logs (no simulation).

Reads V251_INDUSTRY_TYPE startup records from engine .log / .log.gz files.
An AIIndustryType.CanBuildIndustry result concerns a TYPE, not the availability
of a physical tile. It is neither a successful build nor evidence of ROI.
Missing events/fields are reported as unknown, never inferred as zero.

Usage:
  python -B sweeps/diag_v251_industry_inventory.py \
      --campaign smoke=results/v285m6_instrument_smoke_1x3_pc_20261020_engine \
      --campaign exposure=results/v285m6_exposure_5x3_pc_20261020_engine

Prints JSON to stdout only; never writes or alters logs.
"""

import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import statistics


FILE_RE = re.compile(
    r"^(?P<arm>.+)_seed(?P<seed>[0-9]+)_r(?P<repeat>[0-9]+)\.log(?:\.gz)?$"
)
EVENT_RE = re.compile(
    r"\[0\]\s+\[[^\]]+\]\s+OPEX\s+\d+-\d+-\d+\s+V251_INDUSTRY_TYPE\s+(.*)$"
)
KV_RE = re.compile(r"([a-z_][a-z_0-9]*)=([^\s]+)")
SETTING_FIELDS = {"scope", "raw_industry_construction", "valid"}
TYPE_FIELDS = {
    "scope", "type", "name", "can_build", "can_prospect", "cost",
    "raw", "proc", "produced", "accepted", "raw_industry_construction",
}
COMPLETE_TYPE_FIELDS = (
    "name", "can_build", "can_prospect", "cost_reported", "raw", "proc",
    "produced", "accepted", "raw_industry_construction",
)


def content_sha256(path):
    """Hash uncompressed log bytes: copies must match even outside V251 records."""
    digest = hashlib.sha256()
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def optional_int(fields, name, context):
    token = fields.get(name)
    if token is None:
        return None
    if not re.fullmatch(r"-?[0-9]+", token):
        raise ValueError(f"{context}: invalid {name}={token!r}")
    return int(token)


def optional_flag(fields, name, context):
    value = optional_int(fields, name, context)
    if value is None:
        return None
    if value not in (0, 1):
        raise ValueError(f"{context}: expected 0/1 for {name}, got {value}")
    return bool(value)


def optional_cargos(fields, name):
    token = fields.get(name)
    return None if token is None else ([] if token == "-" else token.split(","))


def read_inventory(path):
    """Parse one log; return the exact observed startup inventory, not estimates."""
    path = Path(path)
    result = {"setting": None, "types": {}}
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as stream:
        for number, line in enumerate(stream, 1):
            if "V251_INDUSTRY_TYPE" not in line:
                continue
            context = f"{path}:{number}"
            match = EVENT_RE.search(line)
            if match is None:
                # Another company's output is not OpexAI's inventory.
                if re.search(r"\[0\].*V251_INDUSTRY_TYPE", line):
                    raise ValueError(f"{context}: malformed company-0 V251 event")
                continue
            tokens = match.group(1).split()
            pairs = []
            for token in tokens:
                kv = KV_RE.fullmatch(token)
                if kv is None:
                    raise ValueError(f"{context}: malformed V251 field {token!r}")
                pairs.append(kv.groups())
            if len(pairs) != len({name for name, _ in pairs}):
                raise ValueError(f"{context}: duplicate event field")
            fields = dict(pairs)
            if fields.get("scope") == "setting":
                unexpected = set(fields) - SETTING_FIELDS
                if unexpected:
                    raise ValueError(f"{context}: unexpected setting fields {sorted(unexpected)}")
                valid = optional_flag(fields, "valid", context)
                raw = optional_int(fields, "raw_industry_construction", context)
                setting = {
                    "valid": valid,
                    "raw_industry_construction": raw if valid is not False else None,
                }
                previous = result["setting"]
                if previous is not None and previous != setting:
                    raise ValueError(f"{context}: conflicting V251 setting records")
                result["setting"] = setting
            elif fields.get("scope") == "type":
                unexpected = set(fields) - TYPE_FIELDS
                if unexpected:
                    raise ValueError(f"{context}: unexpected type fields {sorted(unexpected)}")
                industry_id = optional_int(fields, "type", context)
                if industry_id is None or industry_id < 0:
                    raise ValueError(f"{context}: missing or invalid industry type id")
                reported_cost = optional_int(fields, "cost", context)
                type_record = {
                    "type_id": industry_id,
                    "name": fields.get("name"),
                    "can_build": optional_flag(fields, "can_build", context),
                    "can_prospect": optional_flag(fields, "can_prospect", context),
                    "cost_reported": reported_cost,
                    # Zero is observed, but is not a positive construction quote.
                    "cost_valid": None if reported_cost is None else reported_cost > 0,
                    "cost": reported_cost if reported_cost is not None and reported_cost > 0 else None,
                    "raw": optional_flag(fields, "raw", context),
                    "proc": optional_flag(fields, "proc", context),
                    "produced": optional_cargos(fields, "produced"),
                    "accepted": optional_cargos(fields, "accepted"),
                    "raw_industry_construction": optional_int(
                        fields, "raw_industry_construction", context
                    ),
                }
                key = str(industry_id)
                previous = result["types"].get(key)
                if previous is not None and previous != type_record:
                    raise ValueError(f"{context}: conflicting records for type {key}")
                result["types"][key] = type_record
            else:
                raise ValueError(f"{context}: unexpected scope={fields.get('scope')!r}")

    setting = result["setting"]
    if (setting is not None and setting["valid"] is True
            and setting["raw_industry_construction"] is not None):
        for record in result["types"].values():
            raw = record["raw_industry_construction"]
            if raw is not None and raw != setting["raw_industry_construction"]:
                raise ValueError(f"{path}: type/setting raw_industry_construction conflict")
    return result


def cost_stats(costs):
    if not costs:
        return {"n": 0, "min": None, "median": None, "max": None}
    return {
        "n": len(costs), "min": min(costs),
        "median": statistics.median(costs), "max": max(costs),
    }


def describe_run(identity, inventory, paths):
    arm, seed, repetition = identity
    setting, types = inventory["setting"], inventory["types"]
    observed = bool(setting is not None or types)
    missing = {
        str(key): [field for field in COMPLETE_TYPE_FIELDS if record[field] is None]
        for key, record in types.items()
    }
    incomplete_setting = (
        setting is None or setting["valid"] is None
        or (setting["valid"] is True and setting["raw_industry_construction"] is None)
    )
    partial = incomplete_setting or not types or any(missing.values())
    counts = None
    if observed:
        records = list(types.values())
        affordable = [
            record["cost"] for record in records
            if record["can_build"] is True and record["cost_valid"] is True
        ]
        counts = {
            "n_types_observed": len(records),
            "n_types_can_build": sum(r["can_build"] is True for r in records),
            "n_types_can_build_unknown": sum(r["can_build"] is None for r in records),
            "n_types_can_prospect": sum(r["can_prospect"] is True for r in records),
            "n_types_can_prospect_unknown": sum(r["can_prospect"] is None for r in records),
            "n_types_valid_cost": sum(r["cost_valid"] is True for r in records),
            "n_types_valid_cost_unknown": sum(r["cost_valid"] is None for r in records),
            "n_types_build_allowed_with_valid_cost": len(affordable),
            "build_allowed_type_costs": cost_stats(affordable),
        }
    return {
        "arm": arm, "seed": seed, "repetition": repetition,
        "source_files": [str(p) for p in paths],
        "status": ("unobserved" if not observed else "partial" if partial else "observed"),
        "setting": setting,
        "missing_type_fields": missing if observed else None,
        "counts": counts,
        "types": {key: types[key] for key in sorted(types, key=int)} if observed else None,
        "physical_site_buildable": None,
        "inventory_exhaustive": None,
        "profitability": None,
    }


def analyse_campaign(folder):
    """Group files by arm/seed/repetition; duplicate formats must agree exactly."""
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"not a campaign directory: {folder}")
    paths = sorted((*folder.glob("*.log"), *folder.glob("*.log.gz")))
    if not paths:
        raise ValueError(f"no engine logs in {folder}")
    runs = {}
    for path in paths:
        match = FILE_RE.fullmatch(path.name)
        if match is None:
            raise ValueError(f"{path}: cannot establish arm/seed/repetition")
        identity = (match["arm"], int(match["seed"]), int(match["repeat"]))
        inventory = read_inventory(path)
        digest = content_sha256(path)
        basename = path.name[:-3] if path.suffix == ".gz" else path.name
        if identity in runs:
            old_inventory, old_paths, old_digest, old_basename = runs[identity]
            if old_basename != basename:
                raise ValueError(f"ambiguous V251 game identity for {identity}: "
                                 f"{old_paths[0]} versus {path}")
            if old_inventory != inventory or old_digest != digest:
                raise ValueError(
                    f"conflicting V251 inventories or log copies for {identity}: "
                    f"{old_paths[0]} versus {path}"
                )
            old_paths.append(path)
        else:
            runs[identity] = (inventory, [path], digest, basename)

    records = [
        describe_run(key, runs[key][0], runs[key][1]) for key in sorted(runs)
    ]
    observed = [record for record in records if record["status"] != "unobserved"]
    return {
        "runs": records,
        "n_runs": len(records),
        "n_runs_observed": len(observed),
        "n_runs_unobserved": len(records) - len(observed),
        "n_runs_partial": sum(run["status"] == "partial" for run in observed),
        # These totals count run/type observations, NOT physical industries.
        "type_observations_can_build": (
            sum(run["counts"]["n_types_can_build"] for run in observed)
            if observed else None
        ),
        "type_observations_can_build_unknown": (
            sum(run["counts"]["n_types_can_build_unknown"] for run in observed)
            if observed else None
        ),
        "type_observations_can_prospect": (
            sum(run["counts"]["n_types_can_prospect"] for run in observed)
            if observed else None
        ),
        "type_observations_can_prospect_unknown": (
            sum(run["counts"]["n_types_can_prospect_unknown"] for run in observed)
            if observed else None
        ),
        "distinct_seeds": sorted({run["seed"] for run in records}),
        "physical_sites_verified": None,
        "economic_return_verified": None,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--campaign", action="append", required=True, metavar="NAME=DIR",
        help="read-only directory containing engine .log/.log.gz files",
    )
    args = parser.parse_args(argv)
    campaigns = {}
    try:
        for entry in args.campaign:
            name, sep, directory = entry.partition("=")
            if not sep or not name or not directory or name in campaigns:
                raise ValueError(f"expected unique NAME=DIR: {entry!r}")
            campaigns[name] = analyse_campaign(directory)
    except (ValueError, OSError, EOFError) as exc:
        parser.exit(2, f"V251 inventory failed closed: {exc}\n")
    print(json.dumps({"campaigns": campaigns}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
