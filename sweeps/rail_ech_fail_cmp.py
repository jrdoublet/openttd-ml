import gzip,re,sys,glob,collections
B=[(0,60),(60,100),(100,160),(160,250),(250,9999)]
def b(d):
    for lo,hi in B:
        if lo<=d<hi: return f"{lo}-{hi if hi<9999 else '+'}"
for camp in sys.argv[1:]:
  tot={'opex':collections.defaultdict(lambda:[0,0]),'aaa':collections.defaultdict(lambda:[0,0])}
  reasons=collections.Counter()
  for f in sorted(glob.glob(camp+'/reference_seed*_r0.log.gz')):
    seen=set()
    for line in gzip.open(f,'rt',errors='replace'):
        if '[script:4] [0]' in line and 'RAIL_ATTEMPT' in line:
            m=re.search(r'RAIL_ATTEMPT (src=\S+ dst=\S+).*?manh=(\d+).*?ok=(\d) reason=(\S+)',line)
            if not m: continue
            k=(f,line.split('] [I] ')[-1][:10],m[1])
            if k in seen: continue
            seen.add(k)
            t=tot['opex'][b(int(m[2]))]; t[0]+=1; t[1]+=int(m[3])
            if m[3]=='0': reasons[m[4]]+=1
        elif '[script:4] [1]' in line and '# RouteBuilder ' in line and 'RailRoute' in line:
            m=re.search(r'# RouteBuilder (Failed|Succeeded) \S+ \S+ (\d+) ',line)
            if not m: continue
            t=tot['aaa'][b(int(m[2]))]; t[0]+=1; t[1]+= m[1]=='Succeeded'
  print('==',camp.split('/')[-1])
  for who in ('opex','aaa'):
    s=tot[who]; n=sum(v[0] for v in s.values()); ok=sum(v[1] for v in s.values())
    print(f"{who}: {ok}/{n} reussies ({100*ok/max(n,1):.0f} %) |", ' '.join(f"{k}:{v[1]}/{v[0]}" for k,v in sorted(s.items(),key=lambda x:int(x[0].split('-')[0]))))
  print('  echecs opex par raison:', dict(reasons.most_common(8)))
