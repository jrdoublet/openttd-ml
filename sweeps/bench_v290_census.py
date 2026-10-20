"""V290: Industry and water connectivity census benchmark launcher and analyzer.

Measures:
  (1) Number of Oil Rigs (plates-formes petrolieres) at start and when they appear
  (2) Source -> accepting coastal industry pairs connected by the same navigable water component
      for non-perishable bulk cargo (COAL, IORE, GRAI, WOOD, OIL_, STEL, GOOD)
      at Manhattan distance 40..400.

Contract: V290 in docs/taches.md.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

NAME = "IndustryCensusProbe"

# Regexes for log extraction
V290_START_RE = re.compile(r"V290_START\s+map_w=(?P<map_w>\d+)\s+map_h=(?P<map_h>\d+)")
V290_WATER_INIT_RE = re.compile(r"V290_WATER_INIT\s+comps=(?P<comps>\d+)")
V290_IND_RE = re.compile(
    r"V290_IND\s+id=(?P<id>\d+)\s+type=(?P<type>\S+)\s+tile=(?P<tile>\d+)\s+x=(?P<x>\d+)\s+y=(?P<y>\d+)\s+"
    r"on_water=(?P<on_water>\d+)\s+coastal=(?P<coastal>\d+)\s+water_comp=(?P<water_comp>-?\d+)\s+"
    r"dock=(?P<dock>\d+)\s+prod=(?P<prod>\S+)\s+accept=(?P<accept>\S+)"
)
V290_IND_CLOSE_RE = re.compile(r"V290_IND_CLOSE\s+id=(?P<id>\d+)")
V290_MONTH_RE = re.compile(
    r"V290_MONTH\s+date=(?P<date>\d{4}-\d{2}-\d{2})\s+industries=(?P<industries>\d+)\s+"
    r"oil_rigs=(?P<oil_rigs>\d+)\s+coastal=(?P<coastal>\d+)"
)
V290_PAIR_RE = re.compile(
    r"V290_PAIR\s+src=(?P<src>\d+)\s+dst=(?P<dst>\d+)\s+cargo=(?P<cargo>\S+)\s+"
    r"dist=(?P<dist>\d+)\s+same_comp=(?P<same_comp>\d+)"
)
V290_SUMMARY_CARGO_RE = re.compile(
    r"V290_SUMMARY\s+cargo=(?P<cargo>\S+)\s+pairs=(?P<pairs>\d+)\s+same_comp=(?P<same_comp>\d+)"
)
V290_SUMMARY_TOTAL_RE = re.compile(
    r"V290_SUMMARY_TOTAL\s+total_pairs=(?P<total_pairs>\d+)\s+total_same_comp=(?P<total_same_comp>\d+)"
)

TARGET_CARGOS = ["COAL", "IORE", "GRAI", "WOOD", "OIL_", "STEL", "GOOD"]

CANONICAL_SEEDS = (
    42, 100, 999, 1234, 5678,
    2026, 7, 77, 8888, 314159,
    11, 22, 33, 44, 55,
    66, 777, 888, 1000, 2000,
)
CANONICAL_SEEDS_EXTRA_20 = (
    423960, 613553, 515222, 781335, 375172,
    999533, 442018, 746035, 455216, 230185,
    706990, 983759, 802204, 232037, 723002,
    313707, 701256, 292001, 841478, 59527,
)
CANONICAL_SEEDS_40 = CANONICAL_SEEDS + CANONICAL_SEEDS_EXTRA_20


def stage_fixture(destination: Path, root: Path = ROOT) -> dict[str, str]:
    """Copy IndustryCensusProbe fixture files to destination and write manifest."""
    destination.mkdir(parents=True, exist_ok=False)
    sources = {
        "main.nut": root / "sweeps/fixtures/IndustryCensusProbe/main.nut",
        "info.nut": root / "sweeps/fixtures/IndustryCensusProbe/info.nut",
    }
    manifest = {}
    for name, path in sources.items():
        if not path.is_file():
            raise FileNotFoundError(f"Fixture source not found: {path}")
        shutil.copyfile(path, destination / name)
        manifest[name] = hashlib.sha256((destination / name).read_bytes()).hexdigest()
    (destination / "sources.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def parse_v290_logs(log_text: str) -> dict:
    """Parse raw log output and extract structured V290 records."""
    industries: dict[int, dict] = {}
    closed_industries: list[int] = []
    months: list[dict] = []
    pairs: list[dict] = []
    summary_by_cargo: dict[str, dict] = {}
    summary_total: dict[str, int] = {}
    water_comps = 0
    map_size = {"w": 0, "h": 0}

    for line in (log_text or "").splitlines():
        m_start = V290_START_RE.search(line)
        if m_start:
            map_size["w"] = int(m_start.group("map_w"))
            map_size["h"] = int(m_start.group("map_h"))
            continue

        m_w = V290_WATER_INIT_RE.search(line)
        if m_w:
            water_comps = int(m_w.group("comps"))
            continue

        m_ind = V290_IND_RE.search(line)
        if m_ind:
            ind_id = int(m_ind.group("id"))
            industries[ind_id] = {
                "id": ind_id,
                "type": m_ind.group("type"),
                "tile": int(m_ind.group("tile")),
                "x": int(m_ind.group("x")),
                "y": int(m_ind.group("y")),
                "on_water": int(m_ind.group("on_water")),
                "coastal": int(m_ind.group("coastal")),
                "water_comp": int(m_ind.group("water_comp")),
                "dock": int(m_ind.group("dock")),
                "prod": m_ind.group("prod"),
                "accept": m_ind.group("accept"),
            }
            continue

        m_close = V290_IND_CLOSE_RE.search(line)
        if m_close:
            closed_industries.append(int(m_close.group("id")))
            continue

        m_m = V290_MONTH_RE.search(line)
        if m_m:
            months.append({
                "date": m_m.group("date"),
                "industries": int(m_m.group("industries")),
                "oil_rigs": int(m_m.group("oil_rigs")),
                "coastal": int(m_m.group("coastal")),
            })
            continue

        m_pair = V290_PAIR_RE.search(line)
        if m_pair:
            pairs.append({
                "src": int(m_pair.group("src")),
                "dst": int(m_pair.group("dst")),
                "cargo": m_pair.group("cargo"),
                "dist": int(m_pair.group("dist")),
                "same_comp": int(m_pair.group("same_comp")),
            })
            continue

        m_sum = V290_SUMMARY_CARGO_RE.search(line)
        if m_sum:
            summary_by_cargo[m_sum.group("cargo")] = {
                "pairs": int(m_sum.group("pairs")),
                "same_comp": int(m_sum.group("same_comp")),
            }
            continue

        m_tot = V290_SUMMARY_TOTAL_RE.search(line)
        if m_tot:
            summary_total = {
                "total_pairs": int(m_tot.group("total_pairs")),
                "total_same_comp": int(m_tot.group("total_same_comp")),
            }
            continue

    return {
        "map_size": map_size,
        "water_comps": water_comps,
        "industries": industries,
        "closed_industries": closed_industries,
        "months": months,
        "pairs": pairs,
        "summary_by_cargo": summary_by_cargo,
        "summary_total": summary_total,
    }


def analyze_census(log_text: str, years: int = 3) -> dict:
    """Analyze parsed logs and produce per-seed metrics."""
    data = parse_v290_logs(log_text)
    months = data["months"]
    industries = data["industries"]
    pairs = data["pairs"]

    # 1. Oil rigs count at start and per year
    oil_rigs_start = months[0]["oil_rigs"] if months else 0
    oil_rigs_by_year: dict[str, int] = {}
    for m in months:
        date = m["date"]
        year = date.split("-")[0]
        # Keep the count at January 1st of each year, or latest if not exactly Jan 1st
        if date.endswith("-01-01") or year not in oil_rigs_by_year:
            oil_rigs_by_year[year] = m["oil_rigs"]

    # 2. Coastal industries by type (from start census)
    coastal_by_type: dict[str, int] = defaultdict(int)
    for ind in industries.values():
        if ind["coastal"] == 1 or ind["on_water"] == 1:
            coastal_by_type[ind["type"]] += 1
    coastal_count = sum(coastal_by_type.values())

    # 3. Pairs same_comp=1 by cargo and distance distribution
    pairs_by_cargo: dict[str, dict] = {}
    all_same_comp_dists: list[int] = []

    for cargo in TARGET_CARGOS:
        cargo_pairs = [p for p in pairs if p["cargo"] == cargo]
        same_comp_pairs = [p for p in cargo_pairs if p["same_comp"] == 1]
        dists = [p["dist"] for p in same_comp_pairs]
        all_same_comp_dists.extend(dists)

        pairs_by_cargo[cargo] = {
            "total": len(cargo_pairs),
            "same_comp": len(same_comp_pairs),
            "median_dist": float(statistics.median(dists)) if dists else None,
            "min_dist": min(dists) if dists else None,
            "max_dist": max(dists) if dists else None,
        }

    total_pairs = len(pairs)
    total_same_comp = len(all_same_comp_dists)
    median_distance_same_comp = float(statistics.median(all_same_comp_dists)) if all_same_comp_dists else None

    return {
        "map_size": data["map_size"],
        "water_comps": data["water_comps"],
        "total_industries_start": months[0]["industries"] if months else len(industries),
        "coastal_industries_count": coastal_count,
        "coastal_industries_by_type": dict(sorted(coastal_by_type.items())),
        "oil_rigs_start": oil_rigs_start,
        "oil_rigs_by_year": oil_rigs_by_year,
        "closed_industries_count": len(data["closed_industries"]),
        "pairs_by_cargo": pairs_by_cargo,
        "total_pairs": total_pairs,
        "total_same_comp": total_same_comp,
        "median_distance_same_comp": median_distance_same_comp,
        "months_count": len(months),
    }


def write_csv_summary(path: Path, results_by_seed: dict[int, dict], years: int = 3) -> None:
    """Write per-seed synthesis CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "seed",
        "years",
        "oil_rigs_start",
    ]
    # Year columns e.g. oil_rigs_1970, oil_rigs_1971, ...
    sample_res = next(iter(results_by_seed.values())) if results_by_seed else {}
    year_keys = sorted(sample_res.get("oil_rigs_by_year", {}).keys())
    if not year_keys:
        year_keys = [str(1970 + i) for i in range(years)]
    for y in year_keys:
        fieldnames.append(f"oil_rigs_{y}")

    fieldnames.extend([
        "total_industries",
        "coastal_industries",
        "coastal_by_type",
        "same_comp_pairs_total",
    ])
    for cargo in TARGET_CARGOS:
        fieldnames.append(f"same_comp_pairs_{cargo.lower()}")
    fieldnames.append("median_dist_same_comp")

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for seed, res in sorted(results_by_seed.items()):
            row = {
                "seed": seed,
                "years": years,
                "oil_rigs_start": res.get("oil_rigs_start", 0),
                "total_industries": res.get("total_industries_start", 0),
                "coastal_industries": res.get("coastal_industries_count", 0),
                "coastal_by_type": ";".join(f"{k}:{v}" for k, v in res.get("coastal_industries_by_type", {}).items()),
                "same_comp_pairs_total": res.get("total_same_comp", 0),
                "median_dist_same_comp": res.get("median_distance_same_comp") or 0.0,
            }
            by_year = res.get("oil_rigs_by_year", {})
            for y in year_keys:
                row[f"oil_rigs_{y}"] = by_year.get(y, row["oil_rigs_start"])

            by_cargo = res.get("pairs_by_cargo", {})
            for cargo in TARGET_CARGOS:
                row[f"same_comp_pairs_{cargo.lower()}"] = by_cargo.get(cargo, {}).get("same_comp", 0)

            writer.writerow(row)


def keep_probe_record(row: dict) -> tuple[dict]:
    """Result processor for OpenTTDLab workers."""
    return ({
        "run": row.get("experiment", {}).get("bench_run", [NAME, 42, 0]),
        "date": str(row.get("date", "")),
        "output": row.get("output") or "",
        "engine_failure": row.get("engine_failure"),
        "error": bool(row.get("error")),
    },)


def build_docker_cmd(
    campaign: str,
    seeds: list[int],
    years: int,
    cpus: int,
    memory: str,
    max_workers: int,
    out_dir: str = "results",
) -> str:
    """Format the canonical Docker launch command line for display or execution."""
    seed_str = " ".join(str(s) for s in seeds)
    return (
        f"docker run --rm --cpus={cpus} --memory={memory} --memory-swap={memory} "
        f"-v openttd-lab-home:/home/lab -v \"$PWD\":/work -w /work openttd-lab "
        f"python3 sweeps/bench_v290_census.py --campaign {campaign} --years {years} "
        f"--seeds {seed_str} --max-workers {max_workers} --out {out_dir}/{campaign}.json"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=str, default="v290_census", help="Campaign identifier")
    parser.add_argument("--seeds", type=int, nargs="+", default=None, help="List of seeds (default: 40 seeds)")
    parser.add_argument("--years", type=int, default=3, help="Simulation horizon in years (default: 3)")
    parser.add_argument("--out", type=Path, default=None, help="Output JSON path")
    parser.add_argument("--dry-run", action="store_true", help="Print execution commands without running")
    parser.add_argument("--parse-log", type=Path, default=None, help="Parse an existing log file and exit")

    # Docker profiles
    parser.add_argument("--profile", choices=["local", "vps"], default=None, help="Host profile (default: auto)")
    parser.add_argument("--cpus", type=int, default=None, help="CPUs allocated to container")
    parser.add_argument("--memory", type=str, default=None, help="Memory allocated to container")
    parser.add_argument("--max-workers", type=int, default=None, help="Worker count")

    args = parser.parse_args()

    if args.parse_log:
        text = args.parse_log.read_text(encoding="utf-8")
        analysis = analyze_census(text, years=args.years)
        print(json.dumps(analysis, indent=2))
        return

    # Resolve seeds
    seeds = args.seeds if args.seeds is not None else list(CANONICAL_SEEDS_40)

    # Resolve Docker profile limits
    # PC Local default: 10 cpus, 8g memory, 10 workers
    # VPS default: 3 cpus, 2g memory, 3 workers
    if args.profile == "vps":
        cpus = args.cpus or 3
        memory = args.memory or "2g"
        max_workers = args.max_workers or 3
    else:
        # Default to local PC profile (or auto)
        cpus = args.cpus or 10
        memory = args.memory or "8g"
        max_workers = args.max_workers or 10

    out_path = args.out or (ROOT / "results" / f"{args.campaign}.json")

    if args.dry_run:
        cmd = build_docker_cmd(args.campaign, seeds, args.years, cpus, memory, max_workers)
        print("=== DRY-RUN PLAN ===")
        print(f"Probe: {NAME}")
        print(f"Campaign: {args.campaign}")
        print(f"Seeds ({len(seeds)}): {seeds[:5]}... (total {len(seeds)})")
        print(f"Years: {args.years}")
        print(f"Docker limits: cpus={cpus}, memory={memory}, max-workers={max_workers}")
        print(f"Output JSON: {out_path}")
        print(f"Output CSV: {out_path.with_suffix('.csv')}")
        print("\nCommand to execute:")
        print(cmd)
        return

    # Verify execution environment
    if not Path("/work").is_dir():
        print("Error: must run inside canonical openttd-lab Docker with repo mounted at /work", file=sys.stderr)
        print("To see the command to run, use --dry-run", file=sys.stderr)
        sys.exit(1)

    if out_path.exists() or out_path.with_suffix(".csv").exists():
        print(f"Error: Output file already exists: {out_path}", file=sys.stderr)
        sys.exit(1)

    import bench_v2
    import openttdlab
    from game_health import enable_engine_failure_capture
    from openttdlab import local_folder, run_experiments

    # OpenTTDLab ne capture AILog qu'avec `-d script=4` (cf. diag_c39_events.py).
    real_check_output = openttdlab.subprocess.check_output

    def check_output_with_script_debug(cmd, *rest, **kwargs):
        cmd = tuple(cmd)
        if any(str(arg).startswith("-vnull") for arg in cmd):
            cmd = cmd[:1] + ("-d", "script=4") + cmd[1:]
        return real_check_output(cmd, *rest, **kwargs)

    openttdlab.subprocess.check_output = check_output_with_script_debug

    bundle = out_path.with_name(out_path.stem + "_fixture")
    manifest = stage_fixture(bundle)
    arm = local_folder(str(bundle.resolve()), NAME)
    config = bench_v2.make_cfg(1970, 8)
    bench_v2.enable_savegame_cleanup()
    enable_engine_failure_capture()

    days = args.years * 365
    experiments = [
        {
            "seed": s,
            "days": days,
            "openttd_config": config,
            "ais": (arm,),
            "bench_run": [NAME, s, 0],
        }
        for s in seeds
    ]

    print(f"Starting {len(seeds)} games of {NAME} for {args.years} years (workers={max_workers})...")
    rows = list(run_experiments(
        openttd_version=bench_v2.OPENTTD_VERSION,
        opengfx_version=bench_v2.OPENGFX_VERSION,
        max_workers=max_workers,
        result_processor=keep_probe_record,
        ai_libraries=(),
        experiments=experiments,
    ))

    # Save raw jsonl
    jsonl_path = out_path.with_suffix(".jsonl")
    jsonl_path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )

    # Group output by seed and analyze
    results_by_seed: dict[int, dict] = {}
    # Chaque ligne mensuelle recopie le journal complet : garder le plus long par graine.
    logs_by_seed: dict[int, str] = defaultdict(str)
    for r in rows:
        seed = r.get("run", [NAME, 42, 0])[1]
        out = r.get("output") or ""
        if len(out) > len(logs_by_seed[seed]):
            logs_by_seed[seed] = out

    for seed in seeds:
        seed_log = logs_by_seed[seed]
        results_by_seed[seed] = analyze_census(seed_log, years=args.years)

    # Write summary CSV
    csv_path = out_path.with_suffix(".csv")
    write_csv_summary(csv_path, results_by_seed, years=args.years)

    # Write summary JSON
    result_data = {
        "campaign": args.campaign,
        "openttd_version": bench_v2.OPENTTD_VERSION,
        "opengfx_version": bench_v2.OPENGFX_VERSION,
        "years": args.years,
        "seeds": seeds,
        "sources": manifest,
        "config": config,
        "by_seed": {str(s): results_by_seed[s] for s in seeds},
    }
    bench_v2.write_json_atomically(out_path, result_data)

    print(f"Census complete: JSON saved to {out_path}, CSV saved to {csv_path}")


if __name__ == "__main__":
    main()
