"""Purely offline postprocessing for the two 2026-10-25 C66.3 modal benchmarks.

No engine invocation, and no policy/AI edits. The output intentionally keeps
line counts and straight-line station separations distinct from true projects,
track length, construction expense, or load factors.
"""
import collections
import json
import math
import pathlib
import statistics as st

# Analysis code is versioned in sweeps/, while raw benchmark output remains
# local and ignored under results/. Resolve independently of the caller's cwd.
ROOT = pathlib.Path(__file__).resolve().parent.parent / 'results'
ARMS = ('OpexAI', 'AAAHogEx')
YEARS = range(1970, 1975)


def agg(a):
    v = [float(x) for x in a if isinstance(x, (int, float)) and math.isfinite(x)]
    return {'n': len(v), 'mean': st.mean(v) if v else None,
            'median': st.median(v) if v else None,
            'min': min(v) if v else None, 'max': max(v) if v else None}


def distance(line):
    tiles = line.get('ordered_station_tiles') or []
    if len(tiles) < 2 or any(not isinstance(t, int) for t in tiles[:2]):
        return None
    # map-size=8: packed TileIndex = y * 256 + x
    a, b = tiles[:2]
    return math.hypot(a % 256 - b % 256, a // 256 - b // 256)


def cargo_class(capacity_by_cargo):
    """Separate mixed PASS/MAIL + freight instead of crediting all profit to freight.

    A cargo ID without positive carrying capacity is not an observed service.
    The classification describes a whole line, not a cargo-specific profit.
    """
    cargos = {str(k) for k, v in (capacity_by_cargo or {}).items()
              if isinstance(v, (int, float)) and math.isfinite(v) and v > 0}
    pax_mail = bool(cargos & {'0', '2'})
    freight = bool(cargos - {'0', '2'})
    if pax_mail and freight:
        return 'mixed_passenger_freight'
    if freight:
        return 'freight'
    return 'passenger_mail' if pax_mail else 'unknown'


def summarize(mode):
    prefix = f'modal_{mode}_defaults_master85c88_40x5_20261025'
    j = json.loads((ROOT / (prefix + '.json')).read_text(encoding='utf-8'))
    by_arm = {arm: {} for arm in ARMS}
    rows = {}
    last_seen = {}
    first_line_dates = {}
    notes = collections.Counter()
    final_attempts = collections.defaultdict(dict)
    for row in j['summary']:
        by_arm[row['arm']][int(row['seed'])] = row

    # One JSONL record per company/month/seed. Derive without retaining all
    # saved line snapshots in RAM; do not double count monthly observations.
    with (ROOT / (prefix + '.jsonl')).open(encoding='utf-8') as f:
        for raw in f:
            r = json.loads(raw)
            arm, seed, rep = r['run']
            if arm not in ARMS:
                continue
            date = r['date']
            year = int(date[:4])
            key = (arm, int(seed), year)
            if date[5:7] == '12':
                rows[key] = r
                if arm == 'OpexAI':
                    final_attempts[int(seed)] = r.get('rail_attempt_sign_by_year') or {}
            t = r.get('line_telemetry')
            if isinstance(t, dict) and t.get('ok'):
                lines = t.get('lines') or []
                if lines:
                    k0 = (arm, int(seed))
                    first_line_dates.setdefault(k0, date)
                for line in lines:
                    # Stable within a seed and arm only. AAA uses group IDs,
                    # Opex a station-set key. Not a common route identifier.
                    lk = (arm, int(seed), line['line_key_local'])
                    last_seen.setdefault(lk, date)
            elif isinstance(t, dict) and not t.get('ok'):
                notes['invalid_line_snapshot'] += 1

    def line_metrics(arm, year):
        counts, per_line, profits, distances, waiting = [], [], [], [], []
        vehicle_profits = []
        modes = collections.Counter(); cargos = collections.Counter()
        capacity = collections.Counter(); neg = 0
        segments = collections.defaultdict(list)
        cargo_classes = collections.defaultdict(list)
        cargo_distance = collections.defaultdict(list)
        unresolved = []; booked = []; coverage = []
        for seed in by_arm[arm]:
            r = rows.get((arm, seed, year))
            if not r:
                continue
            t = r.get('line_telemetry') or {}
            if not t.get('ok'):
                continue
            lines = t.get('lines') or []
            counts.append(len(lines))
            unresolved.append(len(t.get('unresolved_vehicles') or []))
            booked.append(sum(float(l.get('vehicle_value') or 0) for l in lines))
            num_vehicles = r.get('n_vehicles')
            if isinstance(num_vehicles, (int, float)) and num_vehicles:
                coverage.append(sum(l.get('vehicles') or 0 for l in lines)/num_vehicles)
            for line in lines:
                modes[line.get('mode')] += 1
                pl = line.get('profit_this_year_gbp')
                if isinstance(pl, (float, int)):
                    profits.append(pl)
                    if pl < 0:
                        neg += 1
                for v in line.get('vehicle_financials') or []:
                    vp = v.get('profit_this_year_gbp')
                    if isinstance(vp, (int, float)):
                        vehicle_profits.append(vp)
                dist = distance(line)
                if dist is not None:
                    distances.append(dist)
                band = ('<40' if dist is not None and dist < 40 else
                        '40-79' if dist is not None and dist < 80 else
                        '80-159' if dist is not None and dist < 160 else
                        '>=160' if dist is not None else 'unknown')
                if isinstance(pl, (int, float)):
                    segments[band].append(pl)
                line_cargo_class = cargo_class(line.get('capacity_by_cargo'))
                if isinstance(pl, (int, float)):
                    cargo_classes[line_cargo_class].append(pl)
                    cargo_distance[f'{line_cargo_class}/{band}'].append(pl)
                for cargo, value in (line.get('capacity_by_cargo') or {}).items():
                    cargos[str(cargo)] += 1
                    capacity[str(cargo)] += value
                for station in line.get('endpoint_cargo_stats') or []:
                    for rec in (station.get('cargo') or {}).values():
                        mw = rec.get('max_waiting_cargo')
                        if isinstance(mw, (int, float)):
                            waiting.append(mw)
            if lines:
                per_line.append(sum(float(l.get('profit_this_year_gbp') or 0) for l in lines)/len(lines))
        return {'line_count_per_game': agg(counts), 'line_profit_current_year_gbp': agg(profits),
                'active_vehicle_profit_current_year_gbp': agg(vehicle_profits),
                'line_profit_mean_per_game_line_gbp': agg(per_line),
                'negative_line_snapshots': neg, 'line_snapshots': sum(counts),
                'straight_station_distance_tiles': agg(distances),
                'capacity_by_cargo_units_sum': dict(capacity),
                'lines_containing_cargo': dict(cargos), 'lines_by_mode': dict(modes),
                'endpoint_max_waiting_cargo': agg(waiting),
                'line_profit_by_straight_distance': {k: agg(v) for k,v in segments.items()},
                'line_profit_by_cargo_class': {k: agg(v) for k,v in cargo_classes.items()},
                'line_profit_by_cargo_distance': {k: agg(v) for k,v in cargo_distance.items()},
                'unresolved_vehicles_per_game': agg(unresolved),
                'book_value_of_active_line_vehicles_per_game_gbp': agg(booked),
                'share_primary_vehicles_attributed_to_lines': agg(coverage)}

    summary = {'campaign': prefix, 'mode': mode, 'commit': '85c88c8a52d11a77e577a12c05456a5192355cff',
               'bundle_sha256': j['source_bundle_sha256'], 'game_count': len(j['games']),
               'failed_runs': j['failed_runs'], 'status_counts': dict(collections.Counter(
                   g['game_status'] for g in j['games'])),
               'summary_count': len(j['summary']), 'rows_december': len(rows),
               'invalid_line_snapshots': notes['invalid_line_snapshot'],
               'first_line_dates': {arm: {str(seed): first_line_dates.get((arm, seed))
                                           for seed in by_arm[arm]} for arm in ARMS},
               'by_arm': {}, 'annual': {}, 'losses': {}, 'final_rail_attempt_signs': {}}
    for arm in ARMS:
        values = list(by_arm[arm].values())
        summary['by_arm'][arm] = {metric: agg(row.get(metric) for row in values)
                                  for metric in ('profit_year', 'n_vehicles', 'n_stations',
                                                 'money', 'current_loan', 'company_value',
                                                 'median_station_rating')}
        summary['annual'][arm] = {}
        for year in YEARS:
            annual_rows = [rows[(arm, seed, year)] for seed in by_arm[arm]
                           if (arm, seed, year) in rows]
            metrics = {metric: agg(r.get(metric) for r in annual_rows)
                       for metric in ('profit_year', 'n_vehicles', 'n_stations',
                                      'money', 'current_loan', 'company_value',
                                      'income_last_year', 'expenses_last_year',
                                      'air_passenger_capacity', 'air_vehicle_book_value')}
            quarterly = [r.get('delivered_cargo_last_quarter') for r in annual_rows]
            quarterly = [x for x in quarterly if isinstance(x, list)]
            metrics['delivered_last_quarter_cargo0_passenger'] = agg(
                (x[0] if len(x) > 0 else None) for x in quarterly)
            metrics['delivered_last_quarter_cargo2_mail'] = agg(
                (x[2] if len(x) > 2 else None) for x in quarterly)
            metrics['delivered_last_quarter_non_pax_mail'] = agg(
                sum(v for i,v in enumerate(x) if i not in (0,2) and isinstance(v,(int,float)))
                for x in quarterly)
            metrics['lines'] = line_metrics(arm, year)
            summary['annual'][arm][str(year)] = metrics
    for year in YEARS:
        rr = rows
        ratios = []; diffs = []
        for seed in sorted(set(by_arm['OpexAI']) & set(by_arm['AAAHogEx'])):
            a = rr.get(('OpexAI', seed, year)); b = rr.get(('AAAHogEx', seed, year))
            if a and b and isinstance(a.get('profit_year'), (int, float)) and isinstance(b.get('profit_year'), (int, float)):
                diffs.append(a['profit_year']-b['profit_year'])
                if b['profit_year'] > 0:
                    ratios.append(100*a['profit_year']/b['profit_year'])
        o=summary['annual']['OpexAI'][str(year)]['profit_year']['mean']
        a=summary['annual']['AAAHogEx'][str(year)]['profit_year']['mean']
        summary['losses'][str(year)] = {
            'ratio_of_means_pct': 100*o/a if o is not None and a else None,
            'paired_ratio_percent': agg(ratios), 'opex_minus_aaa_profit_year': agg(diffs),
            'opex_wins': sum(d>0 for d in diffs), 'opex_losses': sum(d<0 for d in diffs)}
    reasons = collections.Counter(); budgets = collections.Counter()
    # Each final December monthly row gives an *accumulated by-year* sign
    # breakdown, not one event per monthly snapshot.
    for sign_by_year in final_attempts.values():
        for year, entry in sign_by_year.items():
            if not isinstance(entry, dict): continue
            budgets[str(year)] += entry.get('iterations', 0) or 0
            for reason,n in (entry.get('reasons') or {}).items():
                reasons[f'{year}/{reason}'] += n
    summary['final_rail_attempt_signs'] = {'by_year_reason': dict(reasons), 'iterations_by_year': dict(budgets)}
    return summary


def publish_reports():
    """Write new diagnostics only, without replacing historical observations.

    Check both destinations before calculating either report, then calculate
    both reports before creating a file. Exclusive creation also covers a
    competing writer arriving after the existence check.
    """
    modes = ('rail', 'air')
    destinations = {
        mode: ROOT / f'modal_{mode}_defaults_master85c88_40x5_20261025_analysis.json'
        for mode in modes
    }
    existing = [path for path in destinations.values() if path.exists()]
    if existing:
        raise FileExistsError(f"rapports existants : {', '.join(map(str, existing))}")
    reports = {mode: summarize(mode) for mode in modes}
    for mode, result in reports.items():
        path = destinations[mode]
        with path.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(mode, result['status_counts'], 'profit 1974', result['losses']['1974'])


if __name__ == '__main__':
    publish_reports()
