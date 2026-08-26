"""Generate the raw and tidy, seed-split-ready Phase-2 hurdle dataset; no model is trained."""
import csv
import json
import math
import os
import re
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
DAYS, INFRA_LIFE_YEARS = 3650, 30
SEEDS = tuple(range(1001, 1051))
# Rangs bornes a 180 et non 200 : sur les 50 graines de la campagne v1, seul le rang 200
# a produit un PAIROOR (graine 1020, moins de 200 paires eligibles sur cette carte). Un PAIROOR
# est un echec de configuration, pas de terrain : il pollue la classe negative du classifieur.
RANKS = (0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180)
RAW, TABLE = "docs/phase2_hurdle_campaign_v1.json", "data/phase2_hurdle_v1.csv"
STATUS=re.compile(r"^TRLN\|(\d+)\|(\w+)\|(\w+)\|(\d+)/(\d+)$")
DETAIL=re.compile(r"^TRLN\|(\d+)\|T(\d+)-(\d+)\|D(\d+)\|C(-?\d+)$")
VEH=re.compile(r"^TRLN\|(\d+)\|V(-?\d+)$")
BARRIER=re.compile(r"^TRLN\|(\d+)\|B(\d+)\|([MO])$")
PAIR=re.compile(r"^TRLN\|(\d+)\|P(\d+)-(\d+)\|D(\d+)$")
FIELDS=("attempt_id","seed","line_index","stagger_slot","pair_rank","engine_rank","num_trains","wagons_per_train","town_a","town_b","town_a_population","town_b_population","distance_straight","built","stage","failure_reason","barrier_flag","first_mutation_tick","construction_cost","vehicle_cost","infra_cost","n_lead_vehicles","sum_profit_last_year","avg_max_age_years","vehicle_amortization_annual","infra_amortization_annual","amortization_annual","profit_ligne")

def params(seed_i, rank_i, attempt):
    return (("num_trains",1+(2*rank_i+seed_i)%3),("wagons_per_train",1+(5*rank_i+2*seed_i)%6),
            ("engine_rank",(3*rank_i+seed_i)%7),("pair_rank",RANKS[rank_i]),("line_index",attempt),("stagger_slot",0))

def veh(chunks):
    total=[]; ages=[]
    for v in chunks.get("VEHS",{}).values():
        if v.get("type")!=0: continue
        c=v["train"][0]["common"][0]
        if c["owner"]==0 and c["unitnumber"]!=0: total.append(c["profit_last_year"]); ages.append(c["max_age"])
    return None if not ages else {"n_lead_vehicles":len(ages),"sum_profit_last_year":sum(total),"avg_max_age_years":round(sum(ages)/len(ages)/365,2)}

def keep(row):
    e=row["experiment"]
    return ({"attempt_id":e["attempt_id"],"seed":e["seed"],"date":str(row["date"]),"ai_params":dict(e["ais"][0][1]),"signs":[s["name"] for s in row["chunks"].get("SIGN",{}).values()],"veh":veh(row["chunks"])},)

def parse(x):
    st=dt=bt=pt=None; vc=None
    for s in x["signs"]:
        if m:=STATUS.match(s): st=m.groups()
        elif m:=DETAIL.match(s): dt=m.groups()
        elif m:=VEH.match(s): vc=int(m.group(2))
        elif m:=BARRIER.match(s): bt=m.groups()
        elif m:=PAIR.match(s): pt=m.groups()
    p=x["ai_params"]
    r={"attempt_id":x["attempt_id"],"seed":x["seed"],"line_index":p["line_index"],"stagger_slot":p["stagger_slot"],"pair_rank":p["pair_rank"],"engine_rank":p["engine_rank"],"num_trains":p["num_trains"],"wagons_per_train":p["wagons_per_train"],"town_a":None,"town_b":None,"town_a_population":None,"town_b_population":None,"distance_straight":None,"built":False,"stage":None,"failure_reason":None,"barrier_flag":None,"first_mutation_tick":None,"construction_cost":None,"vehicle_cost":None,"infra_cost":None,"n_lead_vehicles":None,"sum_profit_last_year":None,"avg_max_age_years":None,"vehicle_amortization_annual":None,"infra_amortization_annual":None,"amortization_annual":None,"profit_ligne":None}
    if st: r.update(stage=st[1],failure_reason=st[2],built=st[1]=="success")
    if pt: r.update(town_a_population=int(pt[1]),town_b_population=int(pt[2]),distance_straight=int(pt[3]))
    if dt: r.update(town_a=int(dt[1]),town_b=int(dt[2]),distance_straight=int(dt[3]),construction_cost=int(dt[4]),vehicle_cost=vc)
    if bt: r.update(first_mutation_tick=int(bt[1]),barrier_flag=bt[2])
    if r["construction_cost"] is not None and vc is not None: r["infra_cost"]=r["construction_cost"]-vc
    if x["veh"] and vc is not None:
        r.update(x["veh"]); va=vc/r["avg_max_age_years"]; ia=r["infra_cost"]/INFRA_LIFE_YEARS; r.update(vehicle_amortization_annual=round(va),infra_amortization_annual=round(ia),amortization_annual=round(va+ia),profit_ligne=round(r["sum_profit_last_year"]-va-ia))
    return r

def corr(xs, ys):
    good=[(x,y) for x,y in zip(xs,ys) if x is not None]
    if len(good)<2:return None
    a,b=zip(*good); ma,mb=statistics.mean(a),statistics.mean(b); d=math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b)); return None if not d else round(sum((x-ma)*(y-mb) for x,y in good)/d,6)

if __name__=="__main__":
    runs=[(si,ri) for si in range(len(SEEDS)) for ri in range(len(RANKS))]
    ex=tuple({"attempt_id":i,"seed":SEEDS[si],"days":DAYS,"openttd_config":CFG,"ais":(local_folder("ai/TrainLineAI","TrainLineAI",ai_params=params(si,ri,i)),)} for i,(si,ri) in enumerate(runs))
    if any(len(e["ais"])!=1 for e in ex): raise RuntimeError("one company per game invariant violated")
    out=run_experiments(openttd_version="13.4",opengfx_version="7.1",max_workers=3,result_processor=keep,ai_libraries=(bananas_ai_library("5046524c","Pathfinder.Rail"),),experiments=ex)
    latest={}
    for x in out:
        if x["attempt_id"] not in latest or x["date"]>latest[x["attempt_id"]]["date"]:latest[x["attempt_id"]]=x
    if len(latest)!=len(ex):raise RuntimeError(f"incomplete: {len(latest)}/{len(ex)}")
    rows=[parse(latest[i]) for i in range(len(ex))]
    os.makedirs("data",exist_ok=True)
    with open(TABLE,"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    reasons={}; flags={"M":0,"O":0,"missing":0}
    for r in rows: reasons[r["failure_reason"]]=reasons.get(r["failure_reason"],0)+1; flags[r["barrier_flag"] or "missing"]+=1
    features=("pair_rank","engine_rank","num_trains","wagons_per_train","town_a_population","town_b_population","distance_straight")
    sanity={"row_count":len(rows),"seed_count":len(set(r["seed"] for r in rows)),"built":sum(r["built"] for r in rows),"not_built":sum(not r["built"] for r in rows),"failure_reasons":{k:v for k,v in reasons.items() if k!="OK"},"barrier":flags,"missing_by_column":{k:sum(r[k] is None for r in rows) for k in FIELDS},"unique_feature_values":{k:len(set(r[k] for r in rows if r[k] is not None)) for k in features},"feature_built_correlations":{k:corr([r[k] for r in rows],[int(r["built"]) for r in rows]) for k in features}}
    raw={"design":{"seeds":SEEDS,"ranks":RANKS,"line_count":len(rows),"parameter_design":"deterministic balanced cycles: engine 0..7, trains 1..3, wagons 1..6; one AI/company and stagger_slot=0 per game","barrier_base_tick":11000},"sanity":sanity,"records":rows}
    json.dump(raw,open(RAW,"w"),indent=2);print(json.dumps(sanity,indent=2));print(TABLE)
