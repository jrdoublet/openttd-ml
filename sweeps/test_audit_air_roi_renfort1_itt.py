"""Fixtures de randomisation prospective AIR-ROI-RENFORT-1 ; aucun Docker."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import sys

# rebasé le 24/10 : skip si pytest est absent sur l'hôte (AGENTS.md §3)
try:
    import pytest
except ImportError:
    import unittest
    raise unittest.SkipTest("pytest n'est pas installé sur l'hôte (AGENTS.md §3)")

sys.path.insert(0, str(Path(__file__).parent))
from audit_air_roi_renfort1_itt import analyze, add_months, cluster_itt, read_assignments


def assignment(seed, eid, arm, *, baseline=2, kind="hubsite", saturation=0, p=50,
               station_a=200, station_b=400, start="1972-1-15", outcome=True):
    pre = (f"OPEX {start} AIRR1_ITT_ASSIGN id={eid} seed={seed} line=7 "
           f"arm={arm} seq=1 p={p} hash=77 tick_pre=555 vehicles_before={baseline} "
           f"want=1 target=4 kind={kind} saturation={saturation} "
           f"station_a={station_a} station_b={station_b} v161_model=55000 roi=100 "
           "quote=100000 until_date=737000\n")
    if not outcome:
        return pre
    added = 1 if arm == "reinforce" else 0
    reason = "OK" if added else "ASSIGNED_DEFER"
    return (pre + f"OPEX {start} AIRR1_ITT_OUTCOME id={eid} seed={seed} line=7 "
            f"arm={arm} tick_after=555 added={added} replaced=0 reason={reason} actual_cost=1234\n")


def create_log(folder, seed, entries, *, name="itt"):
    path = folder / f"{name}_seed{seed}_r0.log"
    path.write_text("".join(entries), encoding="utf-8")
    return path


def month_rows(seed, episode, profit, *, line=7, count=24):
    return [{"record_type": "airr1_itt_month", "seed": seed, "episode_id": episode,
             "line": line, "month_offset": m, "net_profit_gbp": profit,
             "complete": True} for m in range(1, count + 1)]


def create_months(folder, records):
    path = folder / "months.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
    return path


def test_exposure_reports_arms_and_protects_missing_economic_endpoints(tmp_path):
    path = create_log(tmp_path, 42, [assignment(42, "a", "reinforce", baseline=1),
                                     assignment(42, "b", "deferred", baseline=5,
                                                kind="newpair", saturation=1)])
    report = analyze([path], replays=50, include_episodes=True)
    assert report["exposure"]["assigned"] == {"treatment": 1, "deferred": 1}
    assert report["exposure"]["reported_deliveries_treatment"] == 1
    assert report["exposure"]["verified_deliveries_with_vehicle_id"] == 0
    assert report["exposure"]["fleet"] == {"1": 1, "2": 0, "3-4": 0, ">=5": 1, "unknown": 0}
    assert report["exposure"]["saturation"]["saturated"] == 1
    assert report["exposure"]["kind"]["hubsite"] == 1
    assert report["itt_line_net_profit_last_12m"]["mean"] is None
    assert report["itt_line_net_profit_last_12m"]["ci95_seed_cluster"] is None
    assert report["marginal_physical_roi"] is None
    assert report["displaced_investments_verified"] is None
    assert all(r["line_profit_last_12m"] is None for r in report["episodes"])


def test_randomized_net_itt_mean_with_seed_cluster_and_unbuilt_assignments(tmp_path):
    logs = []
    rows = []
    # Seed 42: treat=120/12, defer=20/12; seed 100: treat=40/12, defer=20/12.
    # Δ mean by seed = (100+20)/2=60, 95% seed-resampling CI=[20,100].
    for seed, t, d in [(42, 10, 20 / 12), (100, 40 / 12, 20 / 12)]:
        logs.append(create_log(tmp_path, seed, [assignment(seed, f"t{seed}", "reinforce", outcome=False),
                                               assignment(seed, f"d{seed}", "deferred")]))
        rows.extend(month_rows(seed, f"t{seed}", t))
        rows.extend(month_rows(seed, f"d{seed}", d))
    report = analyze(logs, month_paths=[create_months(tmp_path, rows)], replays=20000, include_episodes=True)
    estimate = report["itt_line_net_profit_last_12m"]
    assert estimate["mean"] == pytest.approx(60)
    assert estimate["ci95_seed_cluster"] == pytest.approx([20, 100])
    assert estimate["seeds_with_both_arms"] == 2
    assert estimate["assigned_treatment_observed"] == 2
    assert report["exposure"]["treatment_missing_outcome"] == 2
    assert report["monthly_net_observation"] == {"complete_24_months": 4}
    assert report["strata"]["fleet"]["2"]["mean"] == pytest.approx(60)
    assert report["marginal_physical_roi"] is None


def test_partial_months_and_wrong_line_remain_missing(tmp_path):
    path = create_log(tmp_path, 42, [assignment(42, "t", "reinforce"),
                                     assignment(42, "d", "deferred")])
    partial = month_rows(42, "t", 20, count=23)
    mistaken = month_rows(42, "d", 10, line=8)
    observed = create_months(tmp_path, partial + mistaken)
    res = analyze([path], month_paths=[observed], replays=100)
    assert res["monthly_net_observation"]["incomplete_or_duplicated_24_months"] == 2
    assert res["itt_line_net_profit_last_12m"]["mean"] is None


def test_deduplication_and_seed_not_independent_ep_counts(tmp_path):
    same_seed = create_log(tmp_path, 42, [assignment(42, "a", "reinforce"),
                                          assignment(42, "b", "deferred"),
                                          assignment(42, "c", "reinforce")])
    rows = month_rows(42, "a", 10) + month_rows(42, "b", 5) + month_rows(42, "c", 15)
    res = analyze([same_seed], month_paths=[create_months(tmp_path, rows)], replays=300)
    assert res["itt_line_net_profit_last_12m"]["mean"] == pytest.approx(90)
    assert res["itt_line_net_profit_last_12m"]["ci95_seed_cluster"] is None
    assert res["itt_line_net_profit_last_12m"]["seeds_with_both_arms"] == 1
    repeated = tmp_path / "duplicate_seed42_r0.log"
    repeated.write_text(assignment(42, "dup", "reinforce") +
                        assignment(42, "dup", "reinforce"), encoding="utf-8")
    observed_episodes, _, issues = read_assignments([repeated])
    assert issues["duplicate_assignment"] == 1
    assert "duplicate_assignment" in observed_episodes[0]["issue"]


def test_telemetry_vehicle_only_without_false_net_roi(tmp_path):
    log_path = create_log(tmp_path, 42, [assignment(42, "t", "reinforce")])
    first_day = date(1972, 2, 1)
    checkpoints = []
    for i in range(25):
        day = add_months(first_day, i)
        # YTD croît de 100 £/mois ; last_year couvre les 12 mois révolus.
        ytd = 100 * (day.month - 1)
        checkpoints.append({"run": ["OpexAI", 42, 0], "date": day.isoformat(),
                            "line_telemetry": {"ok": True, "lines": [
                                {"mode": "air", "ordered_station_tiles": [400, 200],
                                 "profit_this_year_gbp": ytd,
                                 "profit_last_year_gbp": 1200}]}})
    telemetry = tmp_path / "telemetry.jsonl"
    telemetry.write_text("".join(json.dumps(r) + "\n" for r in checkpoints), encoding="utf-8")
    report = analyze([log_path], telemetry_paths=[telemetry], replays=200, include_episodes=True)
    ep = report["episodes"][0]
    assert ep["line_telemetry_status"] == "vehicle_profit_24_full_calendar_months_proxy"
    assert ep["line_fleet_profit_12m_proxy"] == pytest.approx(1200)
    assert ep["line_profit_last_12m"] is None
    assert report["itt_line_net_profit_last_12m"]["mean"] is None
    assert report["marginal_physical_roi"] is None


def test_telemetry_unmatched_station_or_ambiguous_refuses_proxy(tmp_path):
    log_path = create_log(tmp_path, 42, [assignment(42, "x", "deferred")])
    wrong = [{"run": ["OpexAI", 42, 0], "date": "1972-2-1",
              "line_telemetry": {"ok": True, "lines": [{"mode": "air",
              "ordered_station_tiles": [201, 400], "profit_this_year_gbp": 100}]}}]
    telemetry = tmp_path / "bad.jsonl"
    telemetry.write_text("".join(json.dumps(r) + "\n" for r in wrong), encoding="utf-8")
    res = analyze([log_path], telemetry_paths=[telemetry], replays=10, include_episodes=True)
    assert res["episodes"][0]["line_telemetry_status"] == "incomplete_or_unmatched_vehicle_months"
    assert res["episodes"][0]["line_fleet_profit_12m_proxy"] is None


def test_randomized_cross_seed_means_descriptive_until_cluster_replication():
    rows = [{"seed": "42", "arm": "treatment", "line_profit_last_12m": 200, "issue": []},
            {"seed": "100", "arm": "deferred", "line_profit_last_12m": 100, "issue": []}]
    out = cluster_itt(rows, replays=200)
    assert out["seeds_with_both_arms"] == 0
    assert out["mean"] == 100
    assert out["treatment_seeds"] == 1
    assert out["deferred_seeds"] == 1
    assert out["ci95_seed_cluster"] is None


def test_vehicle_operating_months_from_real_log_schema_preserve_net_limit(tmp_path):
    logs = []
    for seed in (42, 100):
        logs.append(create_log(tmp_path, seed, [assignment(seed, f"t{seed}", "reinforce"),
                                                assignment(seed, f"d{seed}", "deferred")]))
        with logs[-1].open("a", encoding="utf-8") as handle:
            for arm, profit in (("t", 20), ("d", 10)):
                for month in range(1, 25):
                    handle.write(f"OPEX 1973-1-1 AIRR1_ITT_MONTH id={arm}{seed} seed={seed} "
                                 f"line=7 month_offset={month} complete=1 aircraft=2 "
                                 f"vehicle_net_profit_gbp={profit} running_cost_est_gbp=5 "
                                 f"revenue_est_gbp={profit + 5} maintenance_gbp=na "
                                 "scope=vehicle_operating_no_infrastructure\n")
    result = analyze(logs, replays=1000, include_episodes=True)
    operating = result["itt_line_vehicle_operating_profit_last_12m"]
    assert operating["mean"] == pytest.approx(120)
    assert operating["ci95_seed_cluster"] == pytest.approx([120, 120])
    assert operating["seeds_with_both_arms"] == 2
    assert result["itt_line_net_profit_last_12m"]["mean"] is None
    assert result["monthly_net_observation"]["complete_24_months_vehicle_operating"] == 4
    assert all(r["aircraft_24m"] == 2 for r in result["episodes"])


def test_reject_broken_vehicle_accounting_and_missing_month(tmp_path):
    path = create_log(tmp_path, 42, [assignment(42, "t", "reinforce")])
    with path.open("a", encoding="utf-8") as handle:
        for month in range(1, 25):
            handle.write("OPEX 1973-1-1 AIRR1_ITT_MONTH id=t seed=42 line=7 "
                         f"month_offset={month} complete={int(month != 12)} "
                         "vehicle_net_profit_gbp=10 running_cost_est_gbp=5 "
                         "revenue_est_gbp=15 scope=vehicle_operating_no_infrastructure\n")
    result = analyze([path], include_episodes=True, replays=100)
    assert result["episodes"][0]["line_vehicle_operating_profit_last_12m"] is None
    assert result["itt_line_vehicle_operating_profit_last_12m"]["mean"] is None


def test_prospective_windows_survive_old_failure_and_annualize_by_observed_days(tmp_path):
    logs = []
    for seed in (42, 100):
        path = create_log(tmp_path, seed, [assignment(seed, f"t{seed}", "reinforce"),
                                           assignment(seed, f"d{seed}", "deferred")])
        logs.append(path)
        with path.open("a", encoding="utf-8") as stream:
            for arm, profit in (("t", 20), ("d", 10)):
                for month in range(1, 25):
                    # Mois 3 rompu ; la fenêtre 13..24 est néanmoins indépendante.
                    ok = month != 3
                    stream.write(f"OPEX 1973-1-1 AIRR1_ITT_MONTH id={arm}{seed} seed={seed} "
                                 f"line=7 month_offset={month} complete={int(ok)} "
                                 f"interval_valid={int(ok)} fail_reason={'none' if ok else 'vehicle_sold_or_lost'} "
                                 f"date_due={1000 + month * 30} date_actual={1000 + month * 30 + 2} "
                                 f"days=30 vehicle_net_profit_gbp={profit} "
                                 f"running_cost_est_gbp=5 revenue_est_gbp={profit + 5} "
                                 "scope=vehicle_operating_no_infrastructure\n")
    result = analyze(logs, replays=500, include_episodes=True, followup_v2=True)
    assert result["itt_line_vehicle_operating_profit_first_12m"]["mean"] is None
    assert result["itt_line_vehicle_operating_profit_last_12m"]["mean"] == pytest.approx(121.75)
    assert result["itt_line_vehicle_operating_profit_last_12m"]["seeds_with_both_arms"] == 2
    assert result["monthly_net_observation"]["24m_valid"] == 4
    assert result["monthly_net_observation"]["12m_vehicle_sold_or_lost"] == 4


def test_prospective_windows_refuse_stale_or_irregular_measurement(tmp_path):
    path = create_log(tmp_path, 42, [assignment(42, "a", "reinforce")])
    with path.open("a", encoding="utf-8") as stream:
        for month in range(1, 25):
            lag = 15 if month == 14 else 0
            stream.write("OPEX 1974-1-1 AIRR1_ITT_MONTH id=a seed=42 line=7 "
                         f"month_offset={month} complete=1 days=30 "
                         f"date_due={1000 + month * 30} date_actual={1000 + month * 30 + lag} "
                         "vehicle_net_profit_gbp=20 running_cost_est_gbp=5 "
                         "revenue_est_gbp=25 scope=vehicle_operating_no_infrastructure\n")
    result = analyze([path], replays=100, include_episodes=True, followup_v2=True)
    ep = result["episodes"][0]
    assert ep["line_vehicle_operating_profit_first_12m"] is not None
    assert ep["line_vehicle_operating_profit_last_12m"] is None
    assert ep["followup_24m_status"] == "invalid_interval_clock"
