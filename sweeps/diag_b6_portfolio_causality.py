"""B6 passive paired 5x6 portfolio diagnostic; never an adoption authority."""
import argparse, json, re, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path
import openttdlab
from openttdlab import bananas_ai_library, local_folder, run_experiments

ROOT = Path("/work") if Path("/work").exists() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
import bench_v2
from bench_v2 import OPENGFX_VERSION, OPENTTD_VERSION, enable_savegame_cleanup, keep as bench_keep, make_cfg, summarise as bench_summarise
from game_health import assess_game, annotate_summary

STARTING_YEAR = 1970
DEFAULT_SEEDS = [42, 100, 999, 1234, 5678]
REFERENCE, PROBE = "OpexAI[b6_current]", "OpexAI[b6_probe]"
OPEX_RE = re.compile(r"OPEX (\d+)-(\d+)-(\d+) ([A-Z0-9_]+)\s*(.*)$")
_real_check_output = openttdlab.subprocess.check_output

def _debug(args, *rest, **kwargs):
    args = tuple(args)
    if any(str(x).startswith("-vnull") for x in args):
        args = args[:1] + ("-d", "script=4") + args[1:]
    return _real_check_output(args, *rest, **kwargs)
openttdlab.subprocess.check_output = _debug

def fields(rest):
    return dict(x.split("=", 1) for x in rest.split() if "=" in x)
def integer(f, k, d=None):
    try: return int(f[k])
    except (KeyError, TypeError, ValueError): return d
def number(f, k, d=None):
    try: return float(f[k])
    except (KeyError, TypeError, ValueError): return d

def parse_events(output):
    out = {"b6": [], "ranks": [], "fresh_eq": [], "fresh_top": [], "repriced_top": []}
    for raw in (output or "").splitlines():
        m = OPEX_RE.search(raw)
        if not m: continue
        y, mo, day, kind, rest = m.groups()
        if kind not in ("B6_PORTFOLIO", "PORTFOLIO_RANK", "B6_FRESH_EQ", "B6_FRESH_TOP", "B6_RECYCLE_TOP_PRICE"): continue
        f = fields(rest); base = {"date": f"{y}-{int(mo):02d}-{int(day):02d}", "year": int(y)}
        if kind == "B6_PORTFOLIO":
            row = {**base, "path": f.get("path")}
            for k in ("snapshot_budget","live_budget","budget_delta","snapshot_age_days","affordability_flips","alternatives","affordable_snapshot","pool_selected","max_batch","floor_pct","actual_profit","actual_cap","actual_roi","actual_turnover_bonus","actual_generation_ratio","cf_profit","cf_cap","cf_roi","cf_turnover_bonus","cf_generation_ratio","same_profit_choice","delta_profit","live_selected","live_profit","live_cap","same_live_choice","live_profit_delta","actual_live_affordable","actual_age_days","actual_recycled","pool_recycled"):
                row[k] = integer(f, k)
            row.update({"actual_mode": f.get("actual_mode"), "cf_mode": f.get("cf_mode"), "live_mode": f.get("live_mode"), "actual_rank_score": number(f,"actual_rank_score"), "cf_rank_score": number(f,"cf_rank_score")})
            out["b6"].append(row)
        elif kind == "PORTFOLIO_RANK":
            row = {**base, "mode": f.get("mode")}
            for k in ("rank","roi","turnover_bonus","generation_ratio","finance_capital","profit"): row[k] = integer(f,k)
            for k in ("rank_score","rank_score_raw","budget_score"): row[k] = number(f,k)
            out["ranks"].append(row)
        elif kind == "B6_FRESH_EQ":
            row = {**base, "scope": f.get("scope")}
            for k in ("stale","matched","missing","ambiguous","aged","age_sum","age_max",
                      "profit_changed","profit_delta_sum","profit_abs_sum","profit_abs_max",
                      "capital_delta_sum","capital_abs_sum","capital_abs_max",
                      "finance_delta_sum","finance_abs_sum","finance_abs_max",
                      "roi_delta_sum","roi_abs_sum","roi_abs_max","rebuild_days"):
                row[k] = integer(f, k)
            out["fresh_eq"].append(row)
        elif kind == "B6_FRESH_TOP":
            row = {**base, "status": f.get("status"), "scope": f.get("scope")}
            for k in ("age_days","stale_profit","fresh_profit","delta_profit",
                      "stale_capital","fresh_capital","delta_capital",
                      "stale_finance","fresh_finance","stale_roi","fresh_roi","rebuild_days",
                      "old_n","fresh_n"):
                row[k] = integer(f, k)
            out["fresh_top"].append(row)
        else:
            row = {**base, "status": f.get("status"), "mode": f.get("mode"),
                   "decision": f.get("decision"), "runner_mode": f.get("runner_mode")}
            for k in ("age_days","monthly","stale_profit","fresh_profit","delta_profit",
                      "fresh_revenue",
                      "stale_capital","fresh_capital","delta_capital",
                      "stale_finance","fresh_finance","stale_roi","fresh_roi","budget"):
                row[k] = integer(f, k)
            for k in ("fresh_score","runner_score"):
                row[k] = number(f, k)
            out["repriced_top"].append(row)
    return out

def analyse(events):
    rows, ranks = events["b6"], events["ranks"]
    paths = Counter(r["path"] for r in rows)
    comparable = [r for r in rows if (r["actual_profit"] or 0)>0 and (r["cf_profit"] or 0)>0]
    inc = [r for r in rows if r["path"]=="incremental"]
    rec = [r for r in inc if r["actual_recycled"]==1 and (r["actual_age_days"] or -1)>=0]
    batches=[]; cur=[]
    for r in ranks:
        if r["rank"]==0 and cur: batches.append(cur); cur=[]
        cur.append(r)
    if cur: batches.append(cur)
    order_errors=0; roi_inversions=0
    for b in batches:
        good=[r for r in b if r["rank_score"] is not None]
        if any(a["rank_score"] < z["rank_score"] for a,z in zip(good,good[1:])): order_errors += 1
        rois=[r["roi"] for r in good if r["roi"] is not None]
        if any(a < z for a,z in zip(rois,rois[1:])): roi_inversions += 1
    req=("rank_score","rank_score_raw","budget_score","finance_capital","roi","turnover_bonus","generation_ratio","profit")
    schema=[r for r in ranks if any(r.get(k) is None for k in req)]
    bd=[r["budget_delta"] for r in rows if r["budget_delta"] is not None]; ages=[r["snapshot_age_days"] for r in rows if r["snapshot_age_days"] is not None]; flips=[r["affordability_flips"] for r in rows if r["affordability_flips"] is not None]; dp=[r["delta_profit"] for r in comparable if r["delta_profit"] is not None]
    live_rows=[r for r in rows if r["same_live_choice"] is not None]
    live_changed=[r for r in live_rows if r["same_live_choice"]==0]
    live_dp=[r["live_profit_delta"] for r in live_changed if r["live_profit_delta"] is not None]
    fresh_eq = events.get("fresh_eq", [])
    fresh_top = events.get("fresh_top", [])
    repriced_top = events.get("repriced_top", [])
    fresh_all = [r for r in fresh_eq if r["scope"] == "all"]
    matched_top = [r for r in fresh_top if r["status"] == "matched"]
    by_scope = {}
    for scope in sorted({r["scope"] for r in fresh_eq if r.get("scope")}):
      rs = [r for r in fresh_eq if r["scope"] == scope]
      matched = sum((r["matched"] or 0) for r in rs)
      aged = sum((r["aged"] or 0) for r in rs)
      by_scope[scope] = {
        "events": len(rs),
        "stale": sum((r["stale"] or 0) for r in rs),
        "matched": matched,
        "missing": sum((r["missing"] or 0) for r in rs),
        "ambiguous": sum((r["ambiguous"] or 0) for r in rs),
        "profit_changed": sum((r["profit_changed"] or 0) for r in rs),
        "profit_delta_mean_matched": (sum((r["profit_delta_sum"] or 0) for r in rs) / matched) if matched else None,
        "profit_abs_mean_matched": (sum((r["profit_abs_sum"] or 0) for r in rs) / matched) if matched else None,
        "profit_abs_max": max((r["profit_abs_max"] or 0) for r in rs) if rs else None,
        "capital_abs_mean_matched": (sum((r["capital_abs_sum"] or 0) for r in rs) / matched) if matched else None,
        "finance_abs_mean_matched": (sum((r["finance_abs_sum"] or 0) for r in rs) / matched) if matched else None,
        "roi_abs_mean_matched": (sum((r["roi_abs_sum"] or 0) for r in rs) / matched) if matched else None,
        "age_mean_days": (sum((r["age_sum"] or 0) for r in rs) / aged) if aged else None,
        "age_max_days": max((r["age_max"] or 0) for r in rs) if rs else None,
      }
    top_profit_deltas = [r["delta_profit"] for r in matched_top if r["delta_profit"] is not None]
    top_ages = [r["age_days"] for r in matched_top if r["age_days"] is not None and r["age_days"] >= 0]
    repriced_ok = [r for r in repriced_top if r["status"] == "ok"]
    repriced_profit_deltas = [r["delta_profit"] for r in repriced_ok if r["delta_profit"] is not None]
    repriced_ages = [r["age_days"] for r in repriced_ok if r["age_days"] is not None and r["age_days"] >= 0]
    return {
      "counts":{"b6_events":len(rows),"rank_events":len(ranks),"rank_batches":len(batches),"paths":dict(paths)},
      "policy":{"max_batch_values":sorted({r["max_batch"] for r in rows if r["max_batch"] is not None}),"floor_pct_values":sorted({r["floor_pct"] for r in rows if r["floor_pct"] is not None})},
      "budget":{"nonzero_budget_delta_events":sum(x!=0 for x in bd),"budget_delta_min":min(bd) if bd else None,"budget_delta_max":max(bd) if bd else None,"snapshot_age_max_days":max(ages) if ages else None,"snapshot_age_mean_days":statistics.mean(ages) if ages else None,"affordability_flip_events":sum(x>0 for x in flips),"affordability_flips_total":sum(flips),"affordability_flips_max":max(flips) if flips else None},
      "live_budget_counterfactual":{"measured_events":len(live_rows),"choice_changed_events":len(live_changed),"choice_same_events":sum(r["same_live_choice"]==1 for r in live_rows),"actual_no_longer_affordable_events":sum(r["actual_live_affordable"]==0 and (r["actual_cap"] or 0)>0 for r in live_rows),"live_became_available_events":sum((r["actual_cap"] or 0)==0 and r["live_selected"]==1 for r in live_rows),"live_selection_empty_events":sum(r["live_selected"]==0 for r in live_rows),"profit_delta_positive_events":sum((x or 0)>0 for x in live_dp),"profit_delta_negative_events":sum((x or 0)<0 for x in live_dp),"profit_delta_mean":statistics.mean(live_dp) if live_dp else None,"profit_delta_median":statistics.median(live_dp) if live_dp else None,"profit_delta_min":min(live_dp) if live_dp else None,"profit_delta_max":max(live_dp) if live_dp else None,"live_modes":dict(Counter(r["live_mode"] for r in live_rows if r["live_selected"]==1))},
      "ranking":{"comparable_events":len(comparable),"same_as_best_profit":sum(r["same_profit_choice"]==1 for r in comparable),"different_from_best_profit":sum(r["same_profit_choice"]==0 for r in comparable),"counterfactual_profit_gain_positive":sum((r["delta_profit"] or 0)>0 for r in comparable),"delta_profit_mean":statistics.mean(dp) if dp else None,"delta_profit_median":statistics.median(dp) if dp else None,"delta_profit_max":max(dp) if dp else None,"actual_modes":dict(Counter(r["actual_mode"] for r in comparable)),"counterfactual_modes":dict(Counter(r["cf_mode"] for r in comparable)),"rank_score_order_errors":order_errors,"roi_inversion_batches":roi_inversions,"turnover_non_neutral_rank_events":sum(r["turnover_bonus"] not in (None,100) for r in ranks),"actual_turnover_bonus":dict(Counter(r["actual_turnover_bonus"] for r in comparable)),"cf_turnover_bonus":dict(Counter(r["cf_turnover_bonus"] for r in comparable))},
      "recycling":{"incremental_events":len(inc),"actual_recycled_events":len(rec),"pool_recycled_total":sum((r["pool_recycled"] or 0) for r in inc),"recycled_age_mean_days":statistics.mean([r["actual_age_days"] for r in rec]) if rec else None,"recycled_age_max_days":max([r["actual_age_days"] for r in rec]) if rec else None},
      "fresh_equivalence":{
        "events_all": len(fresh_all),
        "by_scope": by_scope,
        "top": {
          "events": len(fresh_top),
          "matched": len(matched_top),
          "missing": sum(r["status"] == "missing" for r in fresh_top),
          "ambiguous": sum(r["status"] == "ambiguous" for r in fresh_top),
          "profit_changed": sum((x or 0) != 0 for x in top_profit_deltas),
          "profit_delta_mean": statistics.mean(top_profit_deltas) if top_profit_deltas else None,
          "profit_delta_median": statistics.median(top_profit_deltas) if top_profit_deltas else None,
          "profit_delta_min": min(top_profit_deltas) if top_profit_deltas else None,
          "profit_delta_max": max(top_profit_deltas) if top_profit_deltas else None,
          "age_mean_days": statistics.mean(top_ages) if top_ages else None,
        },
      },
      "repriced_recycled_freight_top":{
        "events": len(repriced_top),
        "ok": len(repriced_ok),
        "status": dict(Counter(r["status"] for r in repriced_top)),
        "decision": dict(Counter(r["decision"] for r in repriced_top)),
        "modes": dict(Counter(r["mode"] for r in repriced_top)),
        "decision_change_events": sum((r["decision"] or "").startswith("change_") for r in repriced_top),
        "decision_keep_events": sum(r["decision"] == "keep" for r in repriced_top),
        "profit_changed": sum((x or 0) != 0 for x in repriced_profit_deltas),
        "profit_delta_positive": sum((x or 0) > 0 for x in repriced_profit_deltas),
        "profit_delta_negative": sum((x or 0) < 0 for x in repriced_profit_deltas),
        "profit_delta_mean": statistics.mean(repriced_profit_deltas) if repriced_profit_deltas else None,
        "profit_delta_median": statistics.median(repriced_profit_deltas) if repriced_profit_deltas else None,
        "profit_delta_min": min(repriced_profit_deltas) if repriced_profit_deltas else None,
        "profit_delta_max": max(repriced_profit_deltas) if repriced_profit_deltas else None,
        "age_mean_days": statistics.mean(repriced_ages) if repriced_ages else None,
        "age_max_days": max(repriced_ages) if repriced_ages else None,
      },
      "schema":{"rank_schema_errors":schema[:10]}
    }

def health_summary(rows, arm, years):
    series=sorted(rows,key=lambda r:r["date"]); final=series[-1].get("openttd_output") or ""
    assessment=assess_game(series,starting_year=STARTING_YEAR,years=years,expected_companies=(arm,),slot_map={0:{"company_id":0,"name":arm}},engine_log=final)
    annotated=annotate_summary(bench_summarise(series,expected_last_year=STARTING_YEAR+years-1,expected_savegames=years*12),series,assessment)
    if len(annotated)!=1: raise AssertionError(f"resume inattendu: {arm}")
    return annotated[0], assessment

def selftest():
    sample="\n".join([
      "OPEX 1971-1-2 B6_PORTFOLIO path=build snapshot_budget=100 live_budget=120 budget_delta=20 snapshot_age_days=3 affordability_flips=1 alternatives=4 affordable_snapshot=2 pool_selected=2 max_batch=1 floor_pct=0 actual_mode=road actual_profit=10 actual_cap=20 actual_rank_score=500 actual_roi=300 actual_turnover_bonus=100 actual_generation_ratio=44 cf_mode=rail cf_profit=30 cf_cap=90 cf_rank_score=333 cf_roi=310 cf_turnover_bonus=130 cf_generation_ratio=80 same_profit_choice=0 delta_profit=20 live_selected=1 live_mode=rail live_profit=30 live_cap=90 same_live_choice=0 live_profit_delta=20 actual_live_affordable=1 actual_age_days=0 actual_recycled=0 pool_recycled=0",
      "OPEX 1971-1-2 PORTFOLIO_RANK rank=0 mode=road roi=300 turnover_bonus=100 generation_ratio=44 score=1 rank_score=500 rank_score_raw=500 budget_score=1 finance_capital=20 profit=10",
      "OPEX 1971-1-2 PORTFOLIO_RANK rank=1 mode=rail roi=310 turnover_bonus=130 generation_ratio=80 score=2 rank_score=333 rank_score_raw=333 budget_score=2 finance_capital=90 profit=30",
      "OPEX 1971-2-2 B6_PORTFOLIO path=incremental snapshot_budget=90 live_budget=90 budget_delta=0 snapshot_age_days=0 affordability_flips=0 alternatives=2 affordable_snapshot=2 pool_selected=1 max_batch=1 floor_pct=0 actual_mode=rail actual_profit=20 actual_cap=40 actual_rank_score=500 actual_roi=320 actual_turnover_bonus=115 actual_generation_ratio=70 cf_mode=rail cf_profit=20 cf_cap=40 cf_rank_score=500 cf_roi=320 cf_turnover_bonus=115 cf_generation_ratio=70 same_profit_choice=1 delta_profit=0 live_selected=1 live_mode=rail live_profit=20 live_cap=40 same_live_choice=1 live_profit_delta=0 actual_live_affordable=1 actual_age_days=25 actual_recycled=1 pool_recycled=1",
      "OPEX 1971-3-2 B6_FRESH_EQ scope=all stale=4 matched=3 missing=1 ambiguous=0 aged=3 age_sum=45 age_max=20 profit_changed=2 profit_delta_sum=30 profit_abs_sum=50 profit_abs_max=30 capital_delta_sum=5 capital_abs_sum=15 capital_abs_max=10 finance_delta_sum=8 finance_abs_sum=18 finance_abs_max=12 roi_delta_sum=7 roi_abs_sum=9 roi_abs_max=5 rebuild_days=2",
      "OPEX 1971-3-2 B6_FRESH_EQ scope=rail stale=2 matched=2 missing=0 ambiguous=0 aged=2 age_sum=30 age_max=20 profit_changed=2 profit_delta_sum=40 profit_abs_sum=40 profit_abs_max=30 capital_delta_sum=5 capital_abs_sum=5 capital_abs_max=5 finance_delta_sum=8 finance_abs_sum=8 finance_abs_max=8 roi_delta_sum=7 roi_abs_sum=7 roi_abs_max=5 rebuild_days=2",
      "OPEX 1971-3-2 B6_FRESH_TOP status=matched scope=rail age_days=20 stale_profit=20 fresh_profit=50 delta_profit=30 stale_capital=40 fresh_capital=45 delta_capital=5 stale_finance=68 fresh_finance=76 stale_roi=320 fresh_roi=325 rebuild_days=2",
      "OPEX 1971-3-3 B6_RECYCLE_TOP_PRICE status=ok mode=rail decision=change_rank age_days=21 monthly=120 stale_profit=20 fresh_profit=32 fresh_revenue=50 delta_profit=12 stale_capital=40 fresh_capital=42 delta_capital=2 stale_finance=68 fresh_finance=71 stale_roi=320 fresh_roi=330 fresh_score=450.7 runner_score=500 runner_mode=air budget=100"
    ])
    a=analyse(parse_events(sample))
    assert a["policy"]=={"max_batch_values":[1],"floor_pct_values":[0]}
    assert a["budget"]["affordability_flips_total"]==1 and a["ranking"]["different_from_best_profit"]==1
    assert a["live_budget_counterfactual"]["choice_changed_events"]==1
    assert a["live_budget_counterfactual"]["profit_delta_mean"]==20
    assert a["ranking"]["roi_inversion_batches"]==1 and a["recycling"]["actual_recycled_events"]==1
    assert a["fresh_equivalence"]["by_scope"]["all"]["matched"]==3
    assert a["fresh_equivalence"]["by_scope"]["all"]["profit_abs_mean_matched"]==50/3
    assert a["fresh_equivalence"]["top"]["profit_delta_mean"]==30
    assert a["repriced_recycled_freight_top"]["events"]==1
    assert a["repriced_recycled_freight_top"]["profit_delta_mean"]==12
    assert a["repriced_recycled_freight_top"]["decision_change_events"]==1
    print("selftest OK")

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--years",type=int,default=6); p.add_argument("--seeds",nargs="+",type=int,default=DEFAULT_SEEDS); p.add_argument("--workers",type=int,default=6); p.add_argument("--out",type=Path,default=ROOT/"results"/"review_b6_portfolio_causality_paired_5x6.json"); p.add_argument("--selftest",action="store_true"); a=p.parse_args()
    if a.selftest: selftest(); return
    a.out.parent.mkdir(parents=True,exist_ok=True); bench_v2.CHECKPOINT_PATH=a.out.with_suffix(".jsonl")
    if bench_v2.CHECKPOINT_PATH.exists(): bench_v2.CHECKPOINT_PATH.unlink()
    arms={REFERENCE:local_folder(str(ROOT/"ai"/"OpexAI"),"OpexAI",(("air_early_slot",1),("decision_log",0))),PROBE:local_folder(str(ROOT/"ai"/"OpexAI"),"OpexAI",(("air_early_slot",1),("decision_log",1)))}
    ex=[{"seed":s,"days":365*a.years,"openttd_config":make_cfg(STARTING_YEAR),"ais":(arms[arm],),"bench_run":[arm,s,0]} for arm in (REFERENCE,PROBE) for s in a.seeds]
    enable_savegame_cleanup(); rows=list(run_experiments(openttd_version=OPENTTD_VERSION,opengfx_version=OPENGFX_VERSION,experiments=ex,max_workers=min(a.workers,6,len(ex)),result_processor=bench_keep,ai_libraries=(bananas_ai_library("51554648","Queue.FibonacciHeap"),bananas_ai_library("5046524c","Pathfinder.Rail"))))
    grouped=defaultdict(list)
    for r in rows: grouped[tuple(r["run"])].append(r)
    summaries={}; health={}; by_seed={}; all_events={"b6":[],"ranks":[],"fresh_eq":[],"fresh_top":[],"repriced_top":[]}; healthy=True
    for arm in (REFERENCE,PROBE):
      for s in a.seeds:
        key=(arm,s,0); series=grouped.get(key,[])
        if not series: health[key]={"run_ok":False}; healthy=False; continue
        sm,ass=health_summary(series,arm,a.years); summaries[key]=sm; health[key]={"run_ok":sm.get("run_ok"),"horizon_complete":sm.get("horizon_complete"),"game_ok":ass.get("game_ok"),"last_date":sm.get("last_date"),"failure_reason":sm.get("failure_reason")}; healthy=healthy and bool(sm.get("run_ok") and sm.get("horizon_complete") and ass.get("game_ok"))
        if arm==PROBE:
          ev=parse_events(max(series,key=lambda r:r["date"]).get("openttd_output") or ""); by_seed[str(s)]=analyse(ev); all_events["b6"]+=ev["b6"]; all_events["ranks"]+=ev["ranks"]; all_events["fresh_eq"]+=ev["fresh_eq"]; all_events["fresh_top"]+=ev["fresh_top"]; all_events["repriced_top"]+=ev["repriced_top"]
    agg=analyse(all_events); pairs=[]
    metrics=("company_value","profit_year","performance_history","n_stations","primary_vehicles")
    for s in a.seeds:
      ref=summaries.get((REFERENCE,s,0),{}); pro=summaries.get((PROBE,s,0),{}); pairs.append({"seed":s,"economics":{m:{"reference":ref.get(m),"probe":pro.get(m),"delta":None if ref.get(m) is None or pro.get(m) is None else pro.get(m)-ref.get(m)} for m in metrics}})
    econ={}
    for m in metrics:
      vals=[x["economics"][m]["delta"] for x in pairs if x["economics"][m]["delta"] is not None]; econ[m]={"mean":statistics.mean(vals) if vals else None,"median":statistics.median(vals) if vals else None,"min":min(vals) if vals else None,"max":max(vals) if vals else None,"probe_wins":sum(v>0 for v in vals),"reference_wins":sum(v<0 for v in vals),"ties":sum(v==0 for v in vals)}
    inv={"all_runs_healthy_complete_horizon":healthy,"probe_events_present":agg["counts"]["b6_events"]>0,"rank_events_present":agg["counts"]["rank_events"]>0,"fresh_equivalence_present":agg["fresh_equivalence"]["events_all"]>0,"max_batch_is_exactly_1":agg["policy"]["max_batch_values"]==[1],"portfolio_floor_pct_is_exactly_0":agg["policy"]["floor_pct_values"]==[0],"rank_event_schema_complete":not agg["schema"]["rank_schema_errors"],"rank_score_monotonic_in_emitted_top5":agg["ranking"]["rank_score_order_errors"]==0,"build_path_observed":agg["counts"]["paths"].get("build",0)>0,"incremental_path_observed":agg["counts"]["paths"].get("incremental",0)>0}
    payload={"purpose":"B6 paired passive diagnostic; no adoption authority.","years":a.years,"seeds":a.seeds,"workers":min(a.workers,6,len(ex)),"arms":{REFERENCE:{"air_early_slot":1,"decision_log":0},PROBE:{"air_early_slot":1,"decision_log":1}},"invariants":inv,"aggregate_probe":agg,"by_seed_probe":by_seed,"paired_economics":pairs,"paired_economic_deltas":econ,"health":{f"{arm}|{s}":v for (arm,s,_),v in health.items()},"limits":["5x6 is diagnostic only; no default/policy adoption authority.","Reference vs probe economics measure decision-log/probe perturbation, not a portfolio policy.","Best-profit counterfactual uses snapshot budget and does not simulate downstream network effects.","06.11 fresh-equivalence compares the cached vivier immediately before a normal full rebuild with that rebuild's generated vivier; only unique stable-key matches are treated as equivalent.","Missing or ambiguous fresh keys are counted, never refreshed or imputed.","turnover_bonus affects rail candidate generation ratio/TopK upstream; final fundScore is profit/financeCapital."]}
    a.out.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8"); print(json.dumps({"invariants":inv,"aggregate_probe":agg,"economics":econ},sort_keys=True))

if __name__=="__main__": main()
