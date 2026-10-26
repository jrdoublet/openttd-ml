#!/usr/bin/env python3
"""V307 0.5 : tentatives rail de production (RAIL_ATTEMPT appariees a PROJECT_CHOSEN par src/dst).

Usage : python3 sweeps/diag_v307_rail_attempts.py results/<campagne>_engine [...]
Duree du choix a la fin de tentative par issue, taux d ABND par annee, jointures,
repetitions d ABND par extremite. Journaux decision_log + --script-debug requis.
"""
import gzip,re,sys,collections,statistics
from pathlib import Path
from datetime import date
L=re.compile(r"\[0\] \[I\] OPEX (\d+)-(\d+)-(\d+) (PROJECT_CHOSEN|RAIL_ATTEMPT) (.*)$")
rows=[]
for d in sys.argv[1:]:
  for p in sorted(Path(d).glob("*.log*")):
    chosen={}
    op=gzip.open if p.suffix==".gz" else open
    for raw in op(p,"rt",errors="replace"):
      m=L.search(raw)
      if not m: continue
      dt=date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
      f=dict(t.split("=",1) for t in m.group(5).split() if "=" in t)
      k=(f.get("src"),f.get("dst"))
      if m.group(4)=="PROJECT_CHOSEN":
        if f.get("mode")=="rail": chosen[k]=dt
      else:
        c=chosen.pop(k,None)
        rows.append(dict(f,camp=Path(d).name,file=p.name,date=dt,days=(dt-c).days if c else None))
print("tentatives",len(rows))
by=collections.Counter((r["reason"]) for r in rows); print(by.most_common())
def tab(sel,label):
  ds=[r["days"] for r in sel if r["days"] is not None]
  print(f"{label}: n={len(sel)} jours med={statistics.median(ds) if ds else '-'} q90={sorted(ds)[int(.9*len(ds))] if ds else '-'} total={sum(ds)}")
tab([r for r in rows if r["reason"]=="OK"],"OK")
tab([r for r in rows if r["reason"]=="ABND"],"ABND")
ab=[r for r in rows if r["reason"]=="ABND"]
print("ABND par jointure:",collections.Counter((r.get("join_end"),r.get("shared_dest")) for r in ab))
print("OK par jointure:",collections.Counter((r.get("join_end"),r.get("shared_dest")) for r in rows if r["reason"]=="OK"))
# repetitions par extremite
for end in ("src","dst"):
  c=collections.Counter((r["camp"],r["file"],r[end]) for r in ab)
  print(end,"ABND distincts",len(c),"repetes",sum(v-1 for v in c.values()))
# rate by year
yr=collections.defaultdict(lambda:[0,0])
for r in rows:
  if r["reason"] in("OK","ABND"):
    yr[r["date"].year][0]+=1; yr[r["date"].year][1]+= r["reason"]=="ABND"
print("annee: n, ABND", dict(sorted(yr.items())))
