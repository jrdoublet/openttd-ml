"""Audit diagnostic des activations RAIL_REPAIR_IDLE dans un replay 40x5.

Ne pas interpréter le replay `probes=258` comme une porte économique : les
journaux moteur ajoutent des opcodes et modifient certaines trajectoires.
"""

import collections
import hashlib
import json
import re
from pathlib import Path

from bench_v2 import SEEDS_40

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/rail_repair_idle_exposure_40x5_20261030.json"
TARGET = ROOT / "docs/rail_repair_idle_exposure_40x5_20261030_events.json"
MARKERS = (
    "RAIL_REPAIR_IDLE", "RAIL_SITE_REPAIR", "RAIL_ASTAR_REPAIR",
    "RAIL_POSE_REPAIR", "V131_REPAIR", "RAIL_BUILD",
)


def extract(line):
    return line.split(" OPEX ", 1)[-1]


def od(line):
    src = re.search(r"\bsrc=(\d+)", line)
    dst = re.search(r"\bdst=(\d+)", line)
    return (int(src.group(1)), int(dst.group(1))) if src and dst else None


def main():
    raw = SOURCE.read_bytes()
    payload = json.loads(raw)
    assert payload["years"] == 5 and payload["starting_year"] == 1970
    assert payload["seeds"] == list(SEEDS_40)
    assert len(payload["summary"]) == 40
    assert not payload["failed_runs"]

    counts = collections.Counter()
    per_seed = []
    for record in sorted(payload["summary"], key=lambda r: r["seed"]):
        assert record["run_ok"] and record["last_date"] == "1974-12-01"
        assert record["n_savegames"] == 60, (record["seed"], record["n_savegames"])
        lines = (record.get("openttd_output") or "").splitlines()
        events = {marker: [extract(line) for line in lines if " " + marker + " " in line]
                  for marker in MARKERS}
        phases = collections.Counter()
        for line in events["RAIL_REPAIR_IDLE"]:
            phase = re.search(r"\bphase=([a-z_]+)", line)
            if phase:
                phases[phase.group(1)] += 1
        assert phases["start"] == 1, record["seed"]
        counts["games"] += 1
        counts["idle_reset"] += phases["reset"]
        counts["idle_enabled"] += phases["enabled"]
        counts["idle_enabled_seeds"] += bool(phases["enabled"])

        sites = events["RAIL_SITE_REPAIR"]
        astar = events["RAIL_ASTAR_REPAIR"]
        pose = events["RAIL_POSE_REPAIR"]
        v131 = events["V131_REPAIR"]
        builds = events["RAIL_BUILD"]
        rescued_builds = [line for line in builds if "site_repair=1" in line]
        astar_start = [line for line in astar if "action=start" in line]
        astar_end = [line for line in astar if "action=end" in line]
        counts["site_attempts"] += len(sites)
        counts["site_with_alternative"] += sum(
            int(re.search(r"\boptions=(\d+)", line).group(1)) > 0 for line in sites
        )
        counts["site_successful_builds"] += len(rescued_builds)
        counts["astar_starts"] += len(astar_start)
        counts["astar_ends"] += len(astar_end)
        counts["astar_abnd"] += sum("result=ABND" in line for line in astar_end)
        counts["pose_events"] += len(pose)
        counts["v131_events"] += len(v131)
        counts["rail_builds"] += len(builds)
        for built in rescued_builds:
            assert od(built) in {od(site) for site in sites}, (
                "site_repair=1 must match SITE event", record["seed"], built
            )
        per_seed.append({
            "seed": record["seed"], "idle_enabled": phases["enabled"],
            "idle_resets": phases["reset"],
            "site_attempts": sites,
            "site_successful_builds": rescued_builds,
            "astar_events": astar,
            "pose_events": pose,
            "v131_events": v131,
        })

    assert counts["rail_builds"] == counts["idle_reset"]
    output = {
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "scope": "secondary instrumental replay, not economic 40x5",
        "settings": payload["arms"],
        "years": 5,
        "n_seeds": len(per_seed),
        "counts": dict(counts),
        "per_seed": per_seed,
    }
    TARGET.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print("SEEDS", len(per_seed), "RAW_SHA256", output["source_sha256"])
    for key, val in sorted(counts.items()):
        print(key, val)
    print("EVIDENCE", TARGET)


if __name__ == "__main__":
    main()
