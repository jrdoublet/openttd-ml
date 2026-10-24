"""Tests d'identification temporelle et d'arithmétique pour AIR-ROI-RENFORT-1."""

from pathlib import Path
import sys

# rebasé le 24/10 : skip si pytest est absent sur l'hôte (AGENTS.md §3)
try:
    import pytest
except ImportError:
    import unittest
    raise unittest.SkipTest("pytest n'est pas installé sur l'hôte (AGENTS.md §3)")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_air_roi_renfort1 import (episode, match_line_proxies, read_shadow,
                                    reference_panel, roi_probe_episode, summarize_shadow)


def sample(event_id="100-2-reinforce-7", date="1972-2-1", source="prior", model=60000,
           raw=12000, calibrated=12000, outcome="built", same_tick="1", cash_ready="1",
           added="1", n=1, k_dec=100000):
    return "\n".join([
        f"OPEX {date} AIRF1_BUY id={event_id} channel=reinforce tick=100 "
        f"line=7 rank=3 cash=200000 reserve=25000 avail=175000 unit_price=40000 "
        f"spend={40000 * n} finance={40000 * n + 1000} "
        f"k_dec_snapshot={k_dec} k_dec_selection_tick=95 raw_profit={raw} "
        f"calibrated_profit={calibrated} raw_roi=300 fund_score=120 "
        f"v161_src={source} v161_model={model}",
        f"OPEX {date} AIRF1_CLOCK id={event_id} same_tick={same_tick}",
        f"OPEX {date} AIRF1_READY id={event_id} same_tick={same_tick} same_cash={cash_ready}",
        f"OPEX {date} AIRF1_LIST id={event_id} rail_remaining=2 rail_pass_reason=too_close_no_join",
        f"OPEX {date} AIRF1_POOL id={event_id} truncated=1",
        f"OPEX {date} AIRF1_OUTCOME id={event_id} outcome={outcome} added={added} "
        f"replaced=0 cash_after=160000",
    ]) + "\n"


def test_v161_c70_c69_different_denominators_and_physical_cost_unobserved(tmp_path):
    path = tmp_path / "seed42.log"
    path.write_text(sample(calibrated=9000), encoding="utf8")
    records, _ = read_shadow(path)
    row = episode(next(iter(records.values())), path)
    assert row["planned_units"] == 1
    assert row["model_total_profit"] == 60000
    assert row["cap_ratio"] == pytest.approx(.2)
    assert row["published_roi_pm"] == 300
    assert row["calibrated_roi_pm"] == pytest.approx(9000 * 1000 / 41000)
    assert row["fund_roi_recomputed_pm"] == 90  # K_dec 100k, plus grand que finance
    assert row["k_dec_tick_lag"] == 5
    assert row["cash_delta_post"] == 40000
    assert row["actual_cost_observed"] is None
    assert row["stable"]


def test_different_files_do_not_merge_same_id_and_built_versus_stable(tmp_path):
    (tmp_path / "one.log").write_text(sample(same_tick="0"), encoding="utf8")
    (tmp_path / "two.log").write_text(sample(cash_ready="0"), encoding="utf8")
    (tmp_path / "three.log").write_text(sample(outcome="failed", added="0"), encoding="utf8")
    result = summarize_shadow(sorted(tmp_path.glob("*.log")), include_episodes=True)
    assert result["counts"]["reinforce_built"] == 2
    assert result["counts"]["reinforce_built_unstable"] == 2
    assert result["counts"]["reinforce_stable_built"] == 0
    assert result["counts"]["attempts"] == 3
    assert len(result["episodes"]) == 3


def test_duplicate_id_disqualifies_stability(tmp_path):
    path = tmp_path / "dup.log"
    text = sample()
    text += "OPEX 1972-2-1 AIRF1_BUY id=100-2-reinforce-7 line=7\n"
    path.write_text(text, encoding="utf8")
    result = summarize_shadow([path])
    assert result["counts"]["duplicates"] == 1
    assert result["counts"]["reinforce_built"] == 1
    assert result["counts"]["reinforce_stable_built"] == 0


def test_multiple_units_model_total_and_growth_proxy_not_aircraft(tmp_path):
    path = tmp_path / "many.log"
    a = sample(n=2, raw=10000, model=20000, added="2")
    b = sample(event_id="200-3-reinforce-7", date="1973-2-1", n=1)
    path.write_text(a + b, encoding="utf8")
    out = summarize_shadow([path])
    assert out["by_planned_units"]["2"]["n"] == 1
    assert out["by_planned_units"]["2"]["cap_ratio_median"] == pytest.approx(.25)
    assert out["by_growth_history_proxy"]["1"]["n"] == 1
    assert out["decision_dimension_coverage"]["planes_before_exact"] == 0


def test_post_purchase_c121_is_line_proxy_and_second_buy_blocks_link(tmp_path):
    one = sample()
    path = tmp_path / "post.log"
    path.write_text(one + "C121_FLEET_MARGINAL line=7 year=1974 added=1 obs_profit=-5000\n",
                    encoding="utf8")
    res = summarize_shadow([path])
    assert res["post_purchase_line_proxy"]["matched"] == 1
    assert res["post_purchase_line_proxy"]["prediction_minus_line_delta_median"] == 17000
    assert res["post_purchase_line_proxy"]["economic_attribution"] is None
    path.write_text(one + sample(event_id="150-3-reinforce-7", date="1973-1-1")
                    + "C121_FLEET_MARGINAL line=7 year=1974 added=1 obs_profit=20000\n",
                    encoding="utf8")
    assert summarize_shadow([path])["post_purchase_line_proxy"]["matched"] == 0


def test_reference_panel_remains_separate_and_legacy_planes_observed(tmp_path):
    path = tmp_path / "ref.log"
    path.write_text("OPEX 1973-4-2 FLEET_PROJECT action=grow line=7 added=1 "
                    "price=40000 profit=6000 roi=150 v161_model=30000 v161_src=prior\n"
                    "OPEX 1973-5-2 AIR_FLEET action=grow line=8 planes_before=2 planes_after=3\n",
                    encoding="utf8")
    ref = reference_panel([path])
    assert ref["fleet_projects_built"] == 1
    assert ref["fleet_model_roi_median_pm"] == 750
    assert ref["legacy_planes_before_histogram"] == {2: 1}
    assert ref["scope"] == "independent_reference_no_shadow_join"


def test_airr1_fields_provenance_missing_and_exact_transaction(tmp_path):
    path = tmp_path / "r1.log"
    eid = "101-7-reinforce-9"
    path.write_text(
        f"OPEX 1972-2-1 AIRR1_PRE id={eid} tick_pre=101 date_pre=7000 "
        "baseVehicles=2 baseVehicles_src=plan_before vehCount=2 vehCount_src=line_before "
        "want=1 want_src=plan_before waitPaxA=na waitPaxA_src=missing "
        "planeCapacity=80 planeCapacity_src=line_cached_before\n"
        f"OPEX 1972-2-1 AIRR1_CONTEXT id={eid} tick_pre=101 "
        "c121Arm=hubsite c121Arm_src=line_historical lineAgeDays=650 "
        "lineAgeDays_src=derived_from_buildDate marginalSamples=0 "
        "marginalSamples_src=line_before coldStart=1 coldStart_src=derived_from_samples "
        "v161Neighbours=2 v161Neighbours_src=plan_before v161Amort=5500 "
        "v161Amort_src=line_cached_before kDec=80000 kDec_src=selection_snapshot "
        "kDecTick=99 kDecTick_src=selection_snapshot c77Tier=0 "
        "c77Tier_src=selection_cached lastHistoricalCycleDays=na "
        "lastHistoricalCycleDays_src=missing\n"
        f"OPEX 1972-2-1 AIRR1_OUTCOME id={eid} tick_pre=101 tick_after=101 "
        "actualCost=32500 actualCost_src=accounting_transaction "
        "added=1 added_src=constructor_return replaced=0 "
        "replaced_src=constructor_return reason=OK reason_src=constructor_return\n",
        encoding="utf8")
    records, observations = read_shadow(path)
    assert observations == []
    episode_row = roi_probe_episode(next(iter(records.values())), path)
    assert episode_row["complete"] and episode_row["same_tick"]
    assert episode_row["values"]["actualCost"] == 32500
    assert episode_row["values"]["v161Neighbours"] == 2
    assert episode_row["values"]["c77Tier"] == 0
    assert episode_row["values"]["waitPaxA"] is None
    assert episode_row["provenance"]["waitPaxA"] == "missing"
    assert episode_row["provenance"]["lineAgeDays"] == "derived_from_buildDate"
    assert episode_row["causal_incremental_profit"] is None
    result = summarize_shadow([path], include_episodes=True)
    assert result["air_roi_renfort1"]["episodes"] == 1
    assert result["air_roi_renfort1"]["complete"] == 1
    assert result["air_roi_renfort1"]["successful_additions"] == 1
    assert result["air_roi_renfort1"]["actual_cost_on_successful_addition"] == 1
    assert result["decision_dimension_coverage"]["planes_before_exact"] == 1
    assert result["decision_dimension_coverage"]["saturation"] == 0
    assert result["decision_dimension_coverage"]["line_arm"] == 1
    assert result["counts"].get("attempts", 0) == 0  # sonde 2a autonome de AIRF1


def test_airr1_incomplete_invalid_source_or_inconsistent_ticks_disqualified(tmp_path):
    path = tmp_path / "incomplete.log"
    eid = "200-1-reinforce-2"
    path.write_text(
        f"OPEX 1973-1-1 AIRR1_PRE id={eid} tick_pre=200 "
        "vehCount=5 vehCount_src=missing planeCapacity=oops "
        "planeCapacity_src=line_cached_before\n"
        f"OPEX 1973-1-1 AIRR1_OUTCOME id={eid} tick_pre=200 tick_after=201 "
        "actualCost=na actualCost_src=missing added=0 added_src=constructor_return\n",
        encoding="utf8")
    row = summarize_shadow([path], include_episodes=True)["air_roi_renfort1"]["details"][0]
    assert not row["complete"]
    assert row["same_tick"] is False
    assert row["values"]["vehCount"] is None
    assert row["values"]["planeCapacity"] is None
    assert row["provenance"]["planeCapacity"] == "invalid"
    assert row["values"]["actualCost"] is None
