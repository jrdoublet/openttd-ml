"""Unmasked preflight distribution for every v2 baseline rank plus a small future tail."""
import atexit
import json
import math
import os
import re
import shutil
import statistics
from openttdlab import bananas_ai_library, local_folder, run_experiments

CFG = """[difficulty]
number_towns = 3
industry_density = 4
[economy]
inflation = false
town_growth_rate = 2
[game_creation]
starting_year = 1970
map_x = 8
map_y = 8
"""
SEEDS = (42, 1, 7, 100, 2026)
RANKS = (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 90, 100, 110, 120, 150)
SCRATCH, NAME, OUTPUT = "/tmp/openttd-ml-preflight-distribution-v2", "TrainLineAIPreflightDistributionV2", "results/phase2_preflight_distribution_v2.json"
STATUS = re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
BARRIER = re.compile(r"^TRLN\|(\d+)\|B(\d+)\|([MO])$")

def scratch():
    if os.path.exists(SCRATCH): raise RuntimeError(f"scratch exists: {SCRATCH}")
    shutil.copytree("ai/TrainLineAI", SCRATCH)
    p = SCRATCH + "/main.nut"; s = open(p).read(); old = "  local BARRIER_BASE = 5000;"
    if s.count(old) != 1: raise RuntimeError("expected BARRIER_BASE=5000 once")
    open(p, "w").write(s.replace(old, "  local BARRIER_BASE = 0;"))
    p = SCRATCH + "/info.nut"; s = open(p).read(); old = 'function GetName()        { return "TrainLineAI"; }'
    open(p, "w").write(s.replace(old, f'function GetName()        {{ return "{NAME}"; }}'))

def keep(row):
    e=row["experiment"]; return ({"seed":e["seed"],"rank":dict(e["ais"][0][1])["pair_rank"],"date":str(row["date"]),"signs":[x["name"] for x in row["chunks"].get("SIGN",{}).values()]},)

if __name__ == "__main__":
    scratch(); atexit.register(shutil.rmtree, SCRATCH, ignore_errors=True)
    runs=[(s,r) for s in SEEDS for r in RANKS]
    ex=tuple({"seed":s,"days":3650,"openttd_config":CFG,"ais":(local_folder(SCRATCH,NAME,ai_params=(("num_trains",2),("wagons_per_train",2),("engine_rank",1),("pair_rank",r),("line_index",i),("stagger_slot",0))),)} for i,(s,r) in enumerate(runs))
    out=run_experiments(openttd_version="13.4",opengfx_version="7.1",max_workers=3,result_processor=keep,ai_libraries=(bananas_ai_library("5046524c","Pathfinder.Rail"),),experiments=ex)
    latest={}
    for x in out:
        k=(x["seed"],x["rank"])
        if k not in latest or x["date"]>latest[k]["date"]: latest[k]=x
    rows=[]
    for k,x in sorted(latest.items()):
        st=bt=None
        for z in x["signs"]:
            if m:=STATUS.match(z): st=m.groups()
            elif m:=BARRIER.match(z): bt=m.groups()
        q={"seed":x["seed"],"pair_rank":x["rank"],"raw_signs":x["signs"]}
        if st:q.update(stage=st[1],reason=st[2])
        if bt:q.update(first_mutation_tick=int(bt[1]),preflight_elapsed_ticks=int(bt[1])-1)
        rows.append(q)
    ticks=[x["first_mutation_tick"] for x in rows if "first_mutation_tick" in x]
    p90=sorted(ticks)[math.ceil(.9*len(ticks))-1]
    payload={"design":{"seeds":SEEDS,"ranks":RANKS,"barrier_base_in_scratch":0},"summary":{"attempted":len(rows),"reached_first_mutation":len(ticks),"min_first_mutation_tick":min(ticks),"median_first_mutation_tick":statistics.median(ticks),"p90_nearest_rank":p90,"max_first_mutation_tick":max(ticks)},"records":rows}
    json.dump(payload,open(OUTPUT,"w"),indent=2); print(json.dumps(payload["summary"],indent=2))
