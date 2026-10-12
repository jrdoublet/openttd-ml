#!/usr/bin/env python3
"""Opcodes EXCLUSIFS par annee et par nom de span (OPEX SPAN, compagnie 0), moyenne par journal.

Usage : analyse_span_exclusive_by_year.py <journal.log> [...]
exclusif = max(0, op - somme des op des enfants directs). V151c, 12/10."""
import re,sys,collections
R=re.compile(r'OPEX (\d+)-\d+-\d+ SPAN id=(\d+) par=(\d+) dep=(\d+) n=(\S+) ds=(\d+)-\S+ t0=\d+ tk=\d+ op=(-?\d+)')
tot=collections.defaultdict(lambda: collections.defaultdict(int))
for f in sys.argv[1:]:
    spans={};child=collections.defaultdict(int)
    for l in open(f,errors='ignore'):
        if ' [0] ' not in l: continue
        m=R.search(l)
        if not m: continue
        y,i,p,d,n,ys,op=m.groups(); op=int(op)
        spans[i]=(int(ys),n,op); child[p]+=op
    for i,(y,n,op) in spans.items():
        tot[y][n]+=max(0,op-child.get(i,0))
for y in sorted(tot):
    s=sum(tot[y].values())
    top=sorted(tot[y].items(),key=lambda kv:-kv[1])[:14]
    print(y, f"tot_excl={s/1e6/ (len(sys.argv)-1):.1f}M/graine")
    for n,v in top: print(f"   {n:45s} {v/1e6/(len(sys.argv)-1):6.2f}M  {100*v/s:5.1f}%")
