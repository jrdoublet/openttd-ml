**Everything you need is in this prompt (also versioned as `docs/prompt_pc_v216_factoriel_20261016.md`): the arms, options and campaign names below ARE the pre-registered commands. There is nothing to look up in the repository.**

Run the two diagnostic campaigns F1 then F2 on this PC, **one at a time, without stopping in between**. They were pre-registered on the VPS on 16/10/2026 (V216, step 4.1). They are **diagnostics**: the launcher's verdict (`fail_primary`, `pass`…) is meaningless here and must not be interpreted. Do not change any default, do not commit, push, merge or edit any versioned file (`docs/taches.md` included).

## Code
- **Do not touch the main checkout** (no pull, no checkout, no merge). Run `git fetch origin`, then `git worktree add --detach ../wt-pc-v216-facto 3ad94b5`. Inside it, check that `git rev-parse --short HEAD` prints `3ad94b5`; if `3ad94b5` can't be found after the fetch, stop and tell me. Run everything below from that worktree.
- Copy `ai/AAAHogEx-115` from the main checkout into the worktree (not tracked by git).
- Run the static contracts once: `python -m unittest discover -s sweeps -p "test_*.py"`. **Expected: all green, 2 235 tests, 3 skipped** (checked on the VPS on this commit). Any red test: stop and tell me.
- Save the analysis script at the end of this prompt as `../v216_facto_analyse.py` (next to the worktree, **not inside it**).
- Before removing the worktree, copy its `results/<campaign>*` (JSON, JSONL, logs, `_engine` directories) into the main `results/` (`git worktree remove` deletes ignored files).

## Common rules
- Launcher: `python -X utf8 sweeps/run_c66_reference.py --campaign <id> --policy-id ref --reference "OpexAI[<REF>]" --variant "OpexAI[<VAR>]" --variant-policy-id <short> <options>`. Omit `--seeds` (canonical seeds).
- PC profile on every command: `--cpus 10 --memory 8g --max-workers 10`. If a campaign dies with `httpx.ReadTimeout` before the first game, add `--network host` (BaNaNaS is IPv6-only).
- Options of both campaigns (40 seeds × 3 years): `--primary-metric profit_year --value-guard-max-loss-pct 5 --repeats 1 --decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 40 --required-years 3 --years 3 --script-debug --line-telemetry`.
- **Smoke before each campaign**: same arms and AAA options, `--campaign <id>_smoke --seeds 42 --years 3 --required-seeds 1 --required-years 3`. Healthy = both duels complete, no "Your script made an error" in the engine logs, neither company `inactive_company`. If the smoke is unhealthy, write it in the report and skip that campaign.
- If AAAHogEx crashes on one seed (known: seed 73, `route.nut:2056`, in games where AAA has all modes), do not rerun it; note it in the report and continue.

## Arm settings
- `FULL = decision_log=1,probes=6` (OpexAI with all modes)
- `RAIL = mode_air=0,mode_road=0,mode_water=0,decision_log=1,probes=6` (OpexAI rail only)
- `AAARAIL` = AAA restricted to rail: `--aaahogex-setting disable_veh_roadveh=1 --aaahogex-setting disable_veh_tram=1 --aaahogex-setting disable_veh_ship=1 --aaahogex-setting disable_veh_aircraft=1`

## F1 — AAA rail only (cells D and B)
- Campaign `v216_facto_aaarail_40x3_pc_<yyyymmdd>`, `--variant-policy-id complet`, plus the `AAARAIL` options.
- REF = `RAIL` (cell D: us rail only vs AAA rail only); VAR = `FULL` (cell B: us full game vs AAA rail only).
- Analysis: `python ../v216_facto_analyse.py results v216_facto_aaarail_40x3_pc_<yyyymmdd> ref complet > results/v216_facto_aaarail_40x3_pc_<yyyymmdd>.v216.md`

## F2 — AAA full game (cells A and C)
- Campaign `v216_facto_aaacomplet_40x3_pc_<yyyymmdd>`, `--variant-policy-id railseul`, **no** AAA option.
- REF = `FULL` (cell A: us full game vs AAA full game); VAR = `RAIL` (cell C: us rail only vs AAA full game).
- Analysis: `python ../v216_facto_analyse.py results v216_facto_aaacomplet_40x3_pc_<yyyymmdd> ref railseul > results/v216_facto_aaacomplet_40x3_pc_<yyyymmdd>.v216.md`

## Report per campaign (`results/<campaign>.summary.md`)
- The launcher's summary lines as printed (mean and median delta, W/L/T, p, CI, healthy pairs), without interpreting the verdict.
- Mean OpexAI and AAAHogEx `profit_year` per arm.
- The full output of the analysis script (the `.v216.md` file).
- Seeds excluded or crashed, if any.

## Global summary at the end (`results/v216_facto_pc_<yyyymmdd>.summary.md`), shown to me
One table with the four cells A, B, C, D (rows) and these columns: OpexAI mean profit_year, AAAHogEx mean profit_year, rail PASS realised/predicted revenue (n, median, sum ratio), rail PASS realised/predicted profit (median, sum ratio), rail freight realised/predicted revenue (n, sum ratio), AIR realised/predicted revenue (n, sum ratio, cells A and B only), RAIL_BUILD PASS and freight per year, AIR_BUILD per year. Then paste the co-location tables of cells A and B. Change nothing yourself.

## Analysis script (save as `../v216_facto_analyse.py`)
```python
"""V216 factorial diagnostic: realised/predicted per mode and cargo, builds, co-location.

Usage: python v216_facto_analyse.py <results_dir> <campaign> <policy_id> [<policy_id> ...]

Reads <results_dir>/<campaign>_engine/<policy>_seed*_r0.log (engine logs, --script-debug)
and <results_dir>/<campaign>.jsonl (line telemetry). Read-only.

Realised/predicted: lines built in 1971 with >= 180 days of operation by 1972-01-01,
LINE_REVENUE year=1972 (= 1971 since construction), annualised; rail scaled to the initial
train count, AIR kept at whole-line level. Revenue = real_prof + real_run * days / 365 (real_run is an annual rate).
"""
import collections
import datetime
import glob
import json
import os
import re
import statistics
import sys

KV = re.compile(r'(\w+)=(\S+)')
MIN_DAYS = 180


def cargo_group(cargo):
    return cargo if cargo in ('PASS', 'MAIL') else 'freight'


def parse_log(path):
    builds, revs = {}, {}
    rail_builds = collections.Counter()
    air_builds = {1970: 0, 1971: 0, 1972: 0}
    with open(path, errors='replace') as fh:
        for line in fh:
            if ' OPEX ' not in line:
                continue
            rest = line.split(' OPEX ', 1)[1].split()
            if len(rest) < 2:
                continue
            date, kind = rest[0], rest[1]
            if kind not in ('RAIL_BUILD', 'AIR_BUILD', 'LINE_REVENUE'):
                continue
            fields = dict(KV.findall(' '.join(rest[2:])))
            year = int(date.split('-')[0])
            if kind == 'RAIL_BUILD':
                builds[fields['line']] = (date, fields)
                rail_builds[(year, cargo_group(fields.get('cargo', '?')))] += 1
            elif kind == 'AIR_BUILD':
                if 'line' in fields:
                    builds.setdefault(fields['line'], (date, fields))
                air_builds[year] = air_builds.get(year, 0) + 1
            elif fields.get('year') == '1972':
                revs[fields['line']] = fields
    rows = []
    for lid, r in revs.items():
        if lid not in builds:
            continue
        bdate, b = builds[lid]
        y, m, d = map(int, bdate.split('-'))
        if y != 1971:
            continue
        days = (datetime.date(1972, 1, 1) - datetime.date(y, m, d)).days
        if days < MIN_DAYS:
            continue
        vehs = int(r.get('vehs', 1)) or 1
        # Rail: scale to the initial train count. AIR: whole line (the C121 prediction is
        # made for a fleet depth that differs from the single plane bought at build).
        t0 = int(b['trains']) if 'trains' in b else vehs
        scale = min(1.0, t0 / vehs)
        real_prof = float(r['real_prof'])
        real_rev = real_prof + float(r['real_run']) * days / 365.0
        pred_prof, pred_rev = float(r['pred_prof']), float(r['pred_rev'])
        if pred_prof <= 0 or pred_rev <= 0:
            continue
        k = 365.0 / days * scale
        rows.append((r['mode'], cargo_group(r['cargo']), pred_rev, real_rev * k, pred_prof, real_prof * k))
    return rows, rail_builds, air_builds


def coloc(jsonl, policy):
    """Rail PASS lines existing in Dec 1971: 1972 profit per train vs # of their towns with our airport."""
    snap = collections.defaultdict(dict)
    if not os.path.exists(jsonl):
        return {}
    with open(jsonl) as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get('policy_id') != policy:
                continue
            run = d.get('run')
            if not run or run[0] != 'OpexAI':
                continue
            lt = d.get('line_telemetry') or {}
            date = d.get('date') or ''
            if lt.get('lines') and (date.startswith('1971-12') or date.startswith('1972-12')):
                snap[tuple(run)][date[:7]] = lt['lines']
    res = collections.defaultdict(list)
    for months in snap.values():
        if '1971-12' not in months or '1972-12' not in months:
            continue
        old = {l['line_key_local'] for l in months['1971-12']}
        air_towns = set()
        for l in months['1972-12']:
            if l['mode'] == 'air':
                air_towns.update(l.get('town_ids') or [])
        for l in months['1972-12']:
            if l['mode'] != 'rail' or l.get('cargo_types') != ['0'] or l['line_key_local'] not in old:
                continue
            n_air = len(set(l.get('town_ids') or []) & air_towns)
            res[n_air].append(l.get('profit_this_year_gbp', 0) * 12 / 11 / max(1, l.get('vehicles', 1)))
    return res


def main():
    results_dir, campaign, policies = sys.argv[1], sys.argv[2], sys.argv[3:]
    engine = os.path.join(results_dir, campaign + '_engine')
    jsonl = os.path.join(results_dir, campaign + '.jsonl')
    print(f"## {campaign}\n")
    for pol in policies:
        logs = sorted(glob.glob(os.path.join(engine, f"{pol}_seed*_r0.log")))
        groups = collections.defaultdict(list)
        rail_b, air_b = collections.Counter(), collections.Counter()
        for path in logs:
            rows, rb, ab = parse_log(path)
            for mode, cg, *vals in rows:
                groups[(mode, cg)].append(vals)
            rail_b.update(rb)
            air_b.update(ab)
        print(f"### policy `{pol}`: {len(logs)} games\n")
        print("| mode | cargo | n | revenue median | revenue sum ratio | profit median | profit sum ratio | mean pred profit | mean real profit |")
        print("|---|---|---|---|---|---|---|---|---|")
        for (mode, cg), g in sorted(groups.items()):
            rr = [x[1] / x[0] for x in g]
            pr = [x[3] / x[2] for x in g]
            print(f"| {mode} | {cg} | {len(g)} | {statistics.median(rr):.2f} | "
                  f"{sum(x[1] for x in g) / sum(x[0] for x in g):.2f} | {statistics.median(pr):.2f} | "
                  f"{sum(x[3] for x in g) / sum(x[2] for x in g):.2f} | "
                  f"{sum(x[2] for x in g) / len(g):.0f} | {sum(x[3] for x in g) / len(g):.0f} |")
        print()
        print("| builds | 1970 | 1971 | 1972 |")
        print("|---|---|---|---|")
        print(f"| AIR_BUILD | {air_b[1970]} | {air_b[1971]} | {air_b[1972]} |")
        for cg in ('PASS', 'MAIL', 'freight'):
            print(f"| RAIL_BUILD {cg} | {rail_b[(1970, cg)]} | {rail_b[(1971, cg)]} | {rail_b[(1972, cg)]} |")
        print()
        res = coloc(jsonl, pol)
        if res:
            print("| rail PASS lines (Dec 1971) by # of their towns with our airport | lines | 1972 profit/train median | mean |")
            print("|---|---|---|---|")
            for k in sorted(res):
                v = res[k]
                print(f"| {k} | {len(v)} | {statistics.median(v):.0f} | {sum(v) / len(v):.0f} |")
            print()


if __name__ == '__main__':
    main()
```
