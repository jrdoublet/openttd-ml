"""Verify archived V263 evidence without local results or an engine run."""

import gzip
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    index = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))
    payloads = {}
    for entry in index["artifacts"]:
        path = (ROOT / entry["archive"]).resolve()
        assert path.is_relative_to(ROOT), path
        assert entry["source"] not in payloads, entry["source"]
        packed = path.read_bytes()
        raw = gzip.decompress(packed)
        for kind, data in (("raw", raw), ("gzip", packed)):
            assert len(data) == entry[kind + "_bytes"], entry["source"]
            assert sha256(data) == entry[kind + "_sha256"], entry["source"]
        payloads[entry["source"]] = raw

    manifests = {}
    results = {}
    for campaign in index["campaigns"]:
        name = campaign["campaign_id"]
        prefix = "results/" + name
        data = json.loads(payloads[prefix + ".json"])
        manifest_raw = payloads[prefix + ".manifest.json"]
        manifest = json.loads(manifest_raw)
        manifests[name] = manifest
        results[name] = data
        assert data["campaign_id"] == manifest["campaign_id"] == name
        assert sha256(manifest_raw) == data["manifest_sha256"]
        assert data["source_bundle_sha256"] == manifest["source_bundle"]["sha256"]
        assert len(data["policies"]) == 1 and not data["failed_runs"]
        assert data["repeats"] == 1 and data["years"] == campaign["years"]
        assert len(data["seeds"]) == campaign["games"]
        games = data["games"]
        assert len(games) == campaign["games"]
        assert len({g["game_id"] for g in games}) == len(games)
        for game in games:
            assert game["game_ok"] and game["game_status"] == "complete"
            assert not game["unattributed_errors"]
            assert all(c["run_ok"] and c["horizon_complete"] for c in game["companies"].values())
            log = prefix + "_engine/" + Path(game["engine_log_path"]).name
            assert log in payloads, log
        expected = {(arm, seed, 0) for seed in data["seeds"] for arm in ("OpexAI", "AAAHogEx")}
        summaries = {(r["arm"], r["seed"], r["repeat"]): r for r in data["summary"]}
        assert set(summaries) == expected and len(data["summary"]) == len(expected)
        for row in summaries.values():
            assert row["run_ok"] and row["horizon_complete"]
            assert row["last_date"] >= data["expected_last_checkpoint"]
            if data["years"] == 10:
                assert row["last_date"] == data["expected_last_checkpoint"]
                assert row["n_savegames"] == 120
                assert row["include_in_economic_stats"]
                assert row["profit_year_coverage"] == "complete"
                assert row["profit_year_quarters_valid"] == 4
        checkpoints = set()
        terminal = {}
        for line in payloads[prefix + ".jsonl"].splitlines():
            row = json.loads(line)
            key = tuple(row["run"])
            assert key in expected and row["campaign_id"] == name
            assert row["source_bundle_sha256"] == data["source_bundle_sha256"]
            checkpoint = (*key, row["date"])
            assert checkpoint not in checkpoints, checkpoint
            checkpoints.add(checkpoint)
            if row["date"] == summaries[key]["last_date"]:
                terminal[key] = row
        assert len(checkpoints) == sum(r["n_savegames"] for r in summaries.values())
        assert set(terminal) == expected
        for key, row in terminal.items():
            for metric in ("profit_year", "company_value", "primary_vehicles", "n_stations"):
                assert row[metric] == summaries[key][metric], (key, metric)
        print(f"{name}: {len(games)} healthy games, {len(checkpoints)} unique checkpoints")

    ref_name = "v263_master_n2_20x10_pc_20261019"
    var_name = "v263_branch_n2_20x10_pc_20261019"
    ref, var = results[ref_name], results[var_name]
    rm, vm = manifests[ref_name], manifests[var_name]
    assert ref["seeds"] == var["seeds"]
    assert rm["sources"]["AAAHogEx"]["sha256"] == vm["sources"]["AAAHogEx"]["sha256"]
    assert rm["configuration"]["raw"] == vm["configuration"]["raw"]
    assert rm["versions"] == vm["versions"] and rm["libraries"] == vm["libraries"]
    rs, vs = [m["policies"][0]["settings"]["effective"] for m in (rm, vm)]
    assert set(rs) - set(vs) == {
        "v252_air_engine_refresh", "v257_rail_refresh", "v259_bridge_renew", "v264_convergent_freight"
    }
    assert not set(vs) - set(rs)
    changed = {k: [rs[k], vs[k]] for k in rs.keys() & vs.keys() if rs[k] != vs[k]}
    assert changed == {"v178_rail_shared_dest": [1, 0], "v179_rail_gen_dest_served": [1, 0]}
    means = [sum(r["profit_year"] for r in d["summary"] if r["arm"] == "OpexAI") / 20 for d in (ref, var)]
    assert abs((means[1] - means[0]) - 48883.05) < 0.001
    print(f"Verified {len(payloads)} archives. Descriptive delta: {means[1] - means[0]:.2f} GBP/year.")
    print("Qualification remains blocked: effective AI settings differ.")


if __name__ == "__main__":
    verify()
