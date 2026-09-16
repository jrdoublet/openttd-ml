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
    out = {"b6": [], "ranks": []}
    for raw in (output or "").splitlines():
        m = OPEX_RE.search(raw)
        if not m: continue
        y, mo, day, kind, rest = m.groups()
        if kind not in ("B6_PORTFOLIO", "PORTFOLIO_RANK"): continue
        f = fields(rest); base = {"date": f"{y}-{int(mo):02d}-{int(day):02d}", "year": int(y)}
        if kind == "B6_PORTFOLIO":
            row = {**base, "path": f.get("path")}
            for k in ("snapshot_budget","live_budget","budget_delta","snapshot_age_days","affordability_flips","alternatives","affordable_snapshot","pool_selected","max_batch","floor_pct","actual_profit","actual_cap","actual_roi","actual_turnover_bonus","actual_generation_ratio","cf_profit","cf_cap","cf_roi","cf_turnover_bonus","cf_generation_ratio","same_profit_choice","delta_profit","actual_age_days","actual_recycled","pool_recycled"):
                row[k] = integer(f, k)
            row.update({"actual_mode": f.get("actual_mode"), "cf_mode": f.get("cf_mode"), "actual_rank_score": number(f,"actual_rank_score"), "cf_rank_score": number(f,"cf_rank_score")})
            out["b6"].append(row)
        else:
            row = {**base, "mode": f.get("mode")}
            for k in ("rank","roi","turnover_bonus","generation_ratio","finance_capital","profit"): row[k] = integer(f,k)
            for k in ("rank_score","rank_score_raw","budget_score"): row[k] = number(f,k)
            out["ranks"].append(row)
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
    return {
      "counts":{"b6_events":len(rows),"rank_events":len(ranks),"rank_batches":len(batches),"paths":dict(paths)},
      "policy":{"max_batch_values":sorted({r["max_batch"] for r in rows if r["max_batch"] is not None}),"floor_pct_values":sorted({r["floor_pct"] for r in rows if r["floor_pct"] is not None})},
      "budget":{"nonzero_budget_delta_events":sum(x!=0 for x in bd),"budget_delta_min":min(bd) if bd else None,"budget_delta_max":max(bd) if bd else None,"snapshot_age_max_days":max(ages) if ages else None,"snapshot_age_mean_days":statistics.mean(ages) if ages else None,"affordability_flip_events":sum(x>0 for x in flips),"affordability_flips_total":sum(flips),"affordability_flips_max":max(flips) if flips else None},
      "ranking":{"comparable_events":len(comparable),"same_as_best_profit":sum(r["same_profit_choice"]==1 for r in comparable),"different_from_best_profit":sum(r["same_profit_choice"]==0 for r in comparable),"counterfactual_profit_gain_positive":sum((r["delta_profit"] or 0)>0 for r in comparable),"delta_profit_mean":statistics.mean(dp) if dp else None,"delta_profit_median":statistics.median(dp) if dp else None,"delta_profit_max":max(dp) if dp else None,"actual_modes":dict(Counter(r["actual_mode"] for r in comparable)),"counterfactual_modes":dict(Counter(r["cf_mode"] for r in comparable)),"rank_score_order_errors":order_errors,"roi_inversion_batches":roi_inversions,"turnover_non_neutral_rank_events":sum(r["turnover_bonus"] not in (None,100) for r in ranks),"actual_turnover_bonus":dict(Counter(r["actual_turnover_bonus"] for r in comparable)),"cf_turnover_bonus":dict(Counter(r["cf_turnover_bonus"] for r in comparable))},
      "recycling":{"incremental_events":len(inc),"actual_recycled_events":len(rec),"pool_recycled_total":sum((r["pool_recycled"] or 0) for r in inc),"recycled_age_mean_days":statistics.mean([r["actual_age_days"] for r in rec]) if rec else None,"recycled_age_max_days":max([r["actual_age_days"] for r in rec]) if rec else None},
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
      "OPEX 1971-1-2 B6_PORTFOLIO path=build snapshot_budget=100 live_budget=120 budget_delta=20 snapshot_age_days=3 affordability_flips=1 alternatives=4 affordable_snapshot=2 pool_selected=2 max_batch=1 floor_pct=0 actual_mode=road actual_profit=10 actual_cap=20 actual_rank_score=500 actual_roi=300 actual_turnover_bonus=100 actual_generation_ratio=44 cf_mode=rail cf_profit=30 cf_cap=90 cf_rank_score=333 cf_roi=310 cf_turnover_bonus=130 cf_generation_ratio=80 same_profit_choice=0 delta_profit=20 actual_age_days=0 actual_recycled=0 pool_recycled=0",
      "OPEX 1971-1-2 PORTFOLIO_RANK rank=0 mode=road roi=300 turnover_bonus=100 generation_ratio=44 score=1 rank_score=500 rank_score_raw=500 budget_score=1 finance_capital=20 profit=10",
      "OPEX 1971-1-2 PORTFOLIO_RANK rank=1 mode=rail roi=310 turnover_bonus=130 generation_ratio=80 score=2 rank_score=333 rank_score_raw=333 budget_score=2 finance_capital=90 profit=30",
      "OPEX 1971-2-2 B6_PORTFOLIO path=incremental snapshot_budget=90 live_budget=90 budget_delta=0 snapshot_age_days=0 affordability_flips=0 alternatives=2 affordable_snapshot=2 pool_selected=1 max_batch=1 floor_pct=0 actual_mode=rail actual_profit=20 actual_cap=40 actual_rank_score=500 actual_roi=320 actual_turnover_bonus=115 actual_generation_ratio=70 cf_mode=rail cf_profit=20 cf_cap=40 cf_rank_score=500 cf_roi=320 cf_turnover_bonus=115 cf_generation_ratio=70 same_profit_choice=1 delta_profit=0 actual_age_days=25 actual_recycled=1 pool_recycled=1"
    ])
    a=analyse(parse_events(sample))
    assert a["policy"]=={"max_batch_values":[1],"floor_pct_values":[0]}
    assert a["budget"]["affordability_flips_total"]==1 and a["ranking"]["different_from_best_profit"]==1
    assert a["ranking"]["roi_inversion_batches"]==1 and a["recycling"]["actual_recycled_events"]==1
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
    summaries={}; health={}; by_seed={}; all_events={"b6":[],"ranks":[]}; healthy=True
    for arm in (REFERENCE,PROBE):
      for s in a.seeds:
        key=(arm,s,0); series=grouped.get(key,[])
        if not series: health[key]={"run_ok":False}; healthy=False; continue
        sm,ass=health_summary(series,arm,a.years); summaries[key]=sm; health[key]={"run_ok":sm.get("run_ok"),"horizon_complete":sm.get("horizon_complete"),"game_ok":ass.get("game_ok"),"last_date":sm.get("last_date"),"failure_reason":sm.get("failure_reason")}; healthy=healthy and bool(sm.get("run_ok") and sm.get("horizon_complete") and ass.get("game_ok"))
        if arm==PROBE:
          ev=parse_events(max(series,key=lambda r:r["date"]).get("openttd_output") or ""); by_seed[str(s)]=analyse(ev); all_events["b6"]+=ev["b6"]; all_events["ranks"]+=ev["ranks"]
    agg=analyse(all_events); pairs=[]
    metrics=("company_value","profit_year","performance_history","n_stations","primary_vehicles")
    for s in a.seeds:
      ref=summaries.get((REFERENCE,s,0),{}); pro=summaries.get((PROBE,s,0),{}); pairs.append({"seed":s,"economics":{m:{"reference":ref.get(m),"probe":pro.get(m),"delta":None if ref.get(m) is None or pro.get(m) is None else pro.get(m)-ref.get(m)} for m in metrics}})
    econ={}
    for m in metrics:
      vals=[x["economics"][m]["delta"] for x in pairs if x["economics"][m]["delta"] is not None]; econ[m]={"mean":statistics.mean(vals) if vals else None,"median":statistics.median(vals) if vals else None,"min":min(vals) if vals else None,"max":max(vals) if vals else None,"probe_wins":sum(v>0 for v in vals),"reference_wins":sum(v<0 for v in vals),"ties":sum(v==0 for v in vals)}
    inv={"all_runs_healthy_complete_horizon":healthy,"probe_events_present":agg["counts"]["b6_events"]>0,"rank_events_present":agg["counts"]["rank_events"]>0,"max_batch_is_exactly_1":agg["policy"]["max_batch_values"]==[1],"portfolio_floor_pct_is_exactly_0":agg["policy"]["floor_pct_values"]==[0],"rank_event_schema_complete":not agg["schema"]["rank_schema_errors"],"rank_score_monotonic_in_emitted_top5":agg["ranking"]["rank_score_order_errors"]==0,"build_path_observed":agg["counts"]["paths"].get("build",0)>0,"incremental_path_observed":agg["counts"]["paths"].get("incremental",0)>0}
    payload={"purpose":"B6 paired passive diagnostic; no adoption authority.","years":a.years,"seeds":a.seeds,"workers":min(a.workers,6,len(ex)),"arms":{REFERENCE:{"air_early_slot":1,"decision_log":0},PROBE:{"air_early_slot":1,"decision_log":1}},"invariants":inv,"aggregate_probe":agg,"by_seed_probe":by_seed,"paired_economics":pairs,"paired_economic_deltas":econ,"health":{f"{arm}|{s}":v for (arm,s,_),v in health.items()},"limits":["5x6 is diagnostic only; no default/policy adoption authority.","Reference vs probe economics measure decision-log/probe perturbation, not a portfolio policy.","Best-profit counterfactual uses snapshot budget and does not simulate downstream network effects.","turnover_bonus affects rail candidate generation ratio/TopK upstream; final fundScore is profit/financeCapital."]}
    a.out.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8"); print(json.dumps({"invariants":inv,"aggregate_probe":agg,"economics":econ},sort_keys=True))

if __name__=="__main__": main()
