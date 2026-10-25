"""V216 etape 3 : analyses des journaux de la sonde `v216_probe` (lecture seule).

Usage : python sweeps/analyze_v216.py <engine_dir>[:<policy>[,<policy>]] ...
   ou : python sweeps/analyze_v216.py <engine_dir> [<policy_id> ...] (compatibilite)

Lit <engine_dir>/<policy>_seed*_r0.log (journaux moteur, --script-debug) et ecrit en Markdown :
- A : pourquoi le premier rail voyageurs passe (choisi contre meilleurs AIR finançable et non
  finançable de la meme selection) ;
- B : attribution des erreurs (lignes rail 1971 >= 180 j, decomposee offre vs capacite vs sejour) ;
- D : test d'invariance entre cellules (critere principal gele [0.7, 1.4] et max/min <= 1.5) ;
- E : combien de fois K_dec l'emporte sur le capital de financement, par mode ;
- V216a : synthese des facteurs et couvertures du fantome ;
- Sensibilite du rang : choc de revenu rail PASS a couts fixes, hors rejeu des achats ;
- G : arrivee de la concurrence sur les industries fret rail ;
- Coûts de la sonde (opcodes) et volumes de lignes.
"""
import collections
import datetime
import glob
import math
import os
import re
import statistics
import sys

KV = re.compile(r'([\w.]+)=(\S+)')


def num(v):
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def parse_line(line):
    """Return (date, kind, fields) for an `OPEX <date> <KIND>` line, else None."""
    if ' OPEX ' not in line:
        return None
    rest = line.split(' OPEX ', 1)[1].rstrip('\n').split(' ', 2)
    if len(rest) < 2:
        return None
    date, kind = rest[0], rest[1]
    if not (kind.startswith('V216_') or kind in ('RAIL_BUILD', 'AIR_BUILD', 'LINE_REVENUE')):
        return None
    fields = {k: num(v) for k, v in KV.findall(rest[2] if len(rest) > 2 else '')}
    return date, kind, fields


def join_rail_lines(game):
    """Map each RAIL_BUILD line id to its preceding built_* DECOMP row (match src/dst).

    Returns a dict: line_id -> {'line': line_id, 'build': rb, 'decomp': decomp_row,
                                'date': date, 'cargo': cargo}
    """
    joined = {}
    built_decomps = list(game.get('built', []))
    used_decomps = set()

    for rb in game.get('rail_build', []):
        lid = rb.get('line')
        src = rb.get('src')
        dst = rb.get('dst')
        matched = None
        for i, d in enumerate(built_decomps):
            if i in used_decomps:
                continue
            d_src = d.get('p.src')
            d_dst = d.get('p.dst')
            if (d_src == src and d_dst == dst) or (d_src == dst and d_dst == src):
                matched = d
                used_decomps.add(i)
                break
        joined[lid] = {
            'line': lid,
            'build': rb,
            'decomp': matched,
            'date': rb.get('date'),
            'cargo': rb.get('cargo'),
        }
    return joined


def parse_log(path):
    """Group a game's probe rows: selections (by seq), builds, flows, rejects."""
    game = {
        'select': {},
        'decomp': collections.defaultdict(list),
        'built': [],
        'flow_done': [],
        'reject': [],
        'counts': collections.Counter(),
        'rail_build': [],
        'air_build': [],
        'line_revenue': [],
        'ind_flow': [],
        'town_flow': [],
        'station_flow': [],
    }
    with open(path, errors='replace') as fh:
        for line in fh:
            parsed = parse_line(line)
            if parsed is None:
                continue
            date, kind, f = parsed
            f['date'] = date
            game['counts'][kind] += 1
            if kind == 'V216_SELECT':
                game['select'][f['seq']] = f
            elif kind == 'V216_DECOMP':
                if str(f.get('role', '')).startswith('built_'):
                    game['built'].append(f)
                else:
                    game['decomp'][f['seq']].append(f)
            elif kind == 'V216_FLOW_DONE':
                game['flow_done'].append(f)
            elif kind == 'V216_GEN_REJECT_TOP':
                game['reject'].append(f)
            elif kind == 'V216_IND_FLOW':
                game['ind_flow'].append(f)
            elif kind == 'V216_TOWN_FLOW':
                game['town_flow'].append(f)
            elif kind == 'V216_STATION_FLOW':
                game['station_flow'].append(f)
            elif kind == 'RAIL_BUILD':
                game['rail_build'].append(f)
            elif kind == 'AIR_BUILD':
                game['air_build'].append(f)
            elif kind == 'LINE_REVENUE':
                game['line_revenue'].append(f)
    game['rail_joins'] = join_rail_lines(game)
    return game


def is_rail_pax(row):
    return row.get('p.mode') == 'rail' and row.get('p.kind') == 'pax'


def cargo_group(cargo):
    if cargo in ('PASS', 'PASSENGERS'):
        return 'PASS'
    if cargo in ('MAIL',):
        return 'MAIL'
    return 'freight'


def first_rail_pax_choice(game):
    """First rail pax build and the last logged selection before it.

    Returns (selection, built_row, rail_row_in_selection, top_row, best_air_ranked,
    best_air_unaffordable); rows may be None when absent from that selection.
    """
    built = [r for r in game['built'] if r.get('role') == 'built_pax']
    if not built:
        return None
    first = min(built, key=lambda r: r['seq'])
    prior = [s for s in game['select'] if s < first['seq']]
    if not prior:
        return game['select'].get(None, {}), first, None, None, None, None
    seq = max(prior)
    rows = game['decomp'].get(seq, [])
    rail = next((r for r in rows if r.get('key') == first.get('key')), None)
    top = next((r for r in rows if r.get('role') == 'ranked' and r.get('rank') == 0), None)
    air_ranked = min((r for r in rows if r.get('p.mode') == 'air' and r.get('role') == 'ranked'),
                     key=lambda r: r['rank'], default=None)
    air_unaff = next((r for r in rows if r.get('p.mode') == 'air' and r.get('role') == 'unaffordable'
                      and r.get('rank') == 0), None)
    return game['select'][seq], first, rail, top, air_ranked, air_unaff


def describe(row):
    if row is None:
        return '| — | — | — | — | — | — | — | — |'
    return (f"| {row.get('p.mode')}/{row.get('p.kind')} | {row.get('rank', '')} | {row.get('tier', 0)} "
            f"| {row.get('select_score', 0):.0f} | {row.get('fund_profit', 0)} "
            f"| {row.get('finance', 0)} | {row.get('p.revenueAnnual', 0)} "
            f"| {row.get('c.carried', row.get('e.carriedPax', '—'))} |")


def error_attribution_b(games):
    """B. Error attribution for rail lines built in 1971 with >= 180 days by 1972-01-01.

    Returns dict grouped by cargo group ('PASS', 'MAIL', 'freight'), each containing:
    - n: count of qualifying lines
    - rev_median: median of (annual_real_rev / pred_rev)
    - rev_sum_ratio: sum(annual_real_rev) / sum(pred_rev)
    - prof_median: median of (annual_real_prof / pred_prof)
    - prof_sum_ratio: sum(annual_real_prof) / sum(pred_prof)
    - mean_offered: mean c.offered
    - mean_capacity: mean c.monthlyCapacity
    - mean_corr_capacity: mean corrected_capacity (with dwell)
    - uncorr_binds: {'offered': count, 'capacity': count}
    - corr_binds: {'offered': count, 'capacity': count}
    - lines: list of line dicts
    """
    groups = collections.defaultdict(list)

    for game in games:
        rail_joins = game.get('rail_joins') or join_rail_lines(game)
        line_revs_1972 = {r.get('line'): r for r in game.get('line_revenue', [])
                          if str(r.get('year')) == '1972'}

        for lid, j in rail_joins.items():
            b = j['build']
            bdate = b.get('date', '')
            try:
                y, m, d = [int(p) for p in bdate.split('-')]
            except (ValueError, AttributeError):
                continue
            if y != 1971:
                continue
            days = (datetime.date(1972, 1, 1) - datetime.date(y, m, d)).days
            if days < 180:
                continue
            if lid not in line_revs_1972:
                continue

            r = line_revs_1972[lid]
            vehs = int(r.get('vehs', 1)) or 1
            t0 = int(b.get('trains', vehs))
            scale = min(1.0, float(t0) / float(vehs))

            real_prof = float(r.get('real_prof', 0.0))
            real_run = float(r.get('real_run', 0.0))
            real_rev = real_prof + real_run * days / 365.0
            pred_prof = float(r.get('pred_prof', 0.0))
            pred_rev = float(r.get('pred_rev', 0.0))
            if pred_rev <= 0 or pred_prof <= 0:
                continue

            k = (365.0 / days) * scale
            annual_real_rev = real_rev * k
            annual_real_prof = real_prof * k

            decomp = j.get('decomp') or {}
            offered = decomp.get('c.offered')
            capacity = decomp.get('c.monthlyCapacity')
            one_way = decomp.get('c.oneWayDays')
            dwell = decomp.get('dwell_station_days', 0.0)

            corr_capacity = None
            if capacity is not None and one_way is not None:
                rt = 2.0 * float(one_way)
                denom = rt + 2.0 * float(dwell)
                corr_capacity = float(capacity) * rt / denom if denom > 0 else float(capacity)

            uncorr_b = None
            if offered is not None and capacity is not None:
                uncorr_b = 'offered' if float(offered) <= float(capacity) else 'capacity'

            corr_b = None
            if offered is not None and corr_capacity is not None:
                corr_b = 'offered' if float(offered) <= float(corr_capacity) else 'capacity'

            cg = cargo_group(b.get('cargo', '?'))
            groups[cg].append({
                'line': lid,
                'cargo': b.get('cargo'),
                'date': bdate,
                'days': days,
                'pred_rev': pred_rev,
                'real_rev': annual_real_rev,
                'pred_prof': pred_prof,
                'real_prof': annual_real_prof,
                'offered': float(offered) if offered is not None else None,
                'capacity': float(capacity) if capacity is not None else None,
                'corr_capacity': corr_capacity,
                'dwell': float(dwell) if dwell is not None else 0.0,
                'uncorr_binds': uncorr_b,
                'corr_binds': corr_b,
                'decomp': decomp,
            })

    res = {}
    for cg, lines in sorted(groups.items()):
        rev_ratios = [l['real_rev'] / l['pred_rev'] for l in lines]
        prof_ratios = [l['real_prof'] / l['pred_prof'] for l in lines]
        offered_vals = [l['offered'] for l in lines if l['offered'] is not None]
        cap_vals = [l['capacity'] for l in lines if l['capacity'] is not None]
        corr_cap_vals = [l['corr_capacity'] for l in lines if l['corr_capacity'] is not None]

        u_binds = collections.Counter(l['uncorr_binds'] for l in lines if l['uncorr_binds'])
        c_binds = collections.Counter(l['corr_binds'] for l in lines if l['corr_binds'])

        res[cg] = {
            'n': len(lines),
            'rev_median': statistics.median(rev_ratios) if rev_ratios else 0.0,
            'rev_sum_ratio': sum(l['real_rev'] for l in lines) / sum(l['pred_rev'] for l in lines)
                             if sum(l['pred_rev'] for l in lines) > 0 else 0.0,
            'prof_median': statistics.median(prof_ratios) if prof_ratios else 0.0,
            'prof_sum_ratio': sum(l['real_prof'] for l in lines) / sum(l['pred_prof'] for l in lines)
                              if sum(l['pred_prof'] for l in lines) > 0 else 0.0,
            'mean_offered': sum(offered_vals) / len(offered_vals) if offered_vals else None,
            'mean_capacity': sum(cap_vals) / len(cap_vals) if cap_vals else None,
            'mean_corr_capacity': sum(corr_cap_vals) / len(corr_cap_vals) if corr_cap_vals else None,
            'uncorr_binds': dict(u_binds),
            'corr_binds': dict(c_binds),
            'lines': lines,
        }
    return res


def invariance_test_d(cells):
    """D. Invariance test: ratio of sums realised/predicted rail PASS revenue.

    For each cell:
    - Current estimator: sum(realised) / sum(predicted)
    - Ghost (gain): sum(realised) / sum(predicted * mean(g.a_gain_pct, g.b_gain_pct)/100)
    - Ghost (line): sum(realised) / sum(predicted * mean(g.a_line_pct, g.b_line_pct)/100)

    Numeric criterion only: four supplied cells, each ratio in [0.7, 1.4],
    max/min <= 1.5. Caller must verify the A/B/C/D experimental mapping.
    This does not validate line revenue as a measure of net company gain.
    """
    cell_results = {}
    missing_ghost = 0

    for label, games in cells.items():
        lines_pass = []
        for game in games:
            rail_joins = game.get('rail_joins') or join_rail_lines(game)
            line_revs_1972 = {r.get('line'): r for r in game.get('line_revenue', [])
                              if str(r.get('year')) == '1972'}
            for lid, j in rail_joins.items():
                b = j['build']
                if cargo_group(b.get('cargo', '')) != 'PASS':
                    continue
                bdate = b.get('date', '')
                try:
                    y, m, d = [int(p) for p in bdate.split('-')]
                except (ValueError, AttributeError):
                    continue
                if y != 1971:
                    continue
                days = (datetime.date(1972, 1, 1) - datetime.date(y, m, d)).days
                if days < 180:
                    continue
                if lid not in line_revs_1972:
                    continue

                r = line_revs_1972[lid]
                vehs = int(r.get('vehs', 1)) or 1
                t0 = int(b.get('trains', vehs))
                scale = min(1.0, float(t0) / float(vehs))

                real_prof = float(r.get('real_prof', 0.0))
                real_run = float(r.get('real_run', 0.0))
                real_rev = real_prof + real_run * days / 365.0
                pred_rev = float(r.get('pred_rev', 0.0))
                if pred_rev <= 0:
                    continue
                k = (365.0 / days) * scale
                annual_real_rev = real_rev * k

                decomp = j.get('decomp') or {}
                if any(not finite_number(decomp.get(key)) or not 0 <= decomp[key] <= 100
                       for key in ('g.a_gain_pct', 'g.b_gain_pct')):
                    missing_ghost += 1
                # Ghost gain pct
                g_ends = [decomp[k] for k in ('g.a_gain_pct', 'g.b_gain_pct')
                          if k in decomp and isinstance(decomp[k], (int, float))]
                gain_factor = (sum(g_ends) / len(g_ends) / 100.0) if g_ends else 1.0
                ghost_pred_rev_gain = pred_rev * gain_factor

                # Ghost line pct
                l_ends = [decomp[k] for k in ('g.a_line_pct', 'g.b_line_pct')
                          if k in decomp and isinstance(decomp[k], (int, float))]
                line_factor = (sum(l_ends) / len(l_ends) / 100.0) if l_ends else 1.0
                ghost_pred_rev_line = pred_rev * line_factor

                lines_pass.append({
                    'real_rev': annual_real_rev,
                    'pred_rev': pred_rev,
                    'ghost_pred_rev_gain': ghost_pred_rev_gain,
                    'ghost_pred_rev_line': ghost_pred_rev_line,
                })

        n = len(lines_pass)
        sum_real = sum(l['real_rev'] for l in lines_pass)
        sum_pred_curr = sum(l['pred_rev'] for l in lines_pass)
        sum_pred_gain = sum(l['ghost_pred_rev_gain'] for l in lines_pass)
        sum_pred_line = sum(l['ghost_pred_rev_line'] for l in lines_pass)

        cell_results[label] = {
            'n': n,
            'sum_real': sum_real,
            'sum_pred_curr': sum_pred_curr,
            'ratio_curr': (sum_real / sum_pred_curr) if sum_pred_curr > 0 else None,
            'sum_pred_gain': sum_pred_gain,
            'ratio_ghost_gain': (sum_real / sum_pred_gain) if sum_pred_gain > 0 else None,
            'sum_pred_line': sum_pred_line,
            'ratio_ghost_line': (sum_real / sum_pred_line) if sum_pred_line > 0 else None,
        }

    valid_ratios = [c['ratio_ghost_gain'] for c in cell_results.values()
                    if c['n'] > 0 and finite_number(c['ratio_ghost_gain'])]
    coverage_complete = len(cells) == 4 and len(valid_ratios) == 4 and missing_ghost == 0
    if not valid_ratios:
        verdict = 'INCOMPLETE (aucun rail PASS 1971)'
        min_r, max_r, spread = None, None, None
    else:
        min_r = min(valid_ratios)
        max_r = max(valid_ratios)
        spread = (max_r / min_r) if min_r > 0 else float('inf')
        range_ok = all(0.7 <= r <= 1.4 for r in valid_ratios)
        spread_ok = (spread <= 1.5)
        verdict = 'PASS' if (range_ok and spread_ok) else 'FAIL'

    numeric_verdict = verdict
    if not coverage_complete:
        verdict = 'INCOMPLETE (quatre cellules exploitables et fantomes complets requis)'

    return {
        'cells': cell_results,
        'min_ratio': min_r,
        'max_ratio': max_r,
        'spread': spread,
        'verdict': verdict,
        'numeric_verdict': numeric_verdict,
        'coverage_complete': coverage_complete,
        'missing_ghost_rows': missing_ghost,
    }


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def rail_pax_fixed_cost_shadow(row):
    """Conditional revenue shock, NOT a replay of V216a demand/sizing.

    Hold implicit costs, calibration and score denominator fixed. Require both
    endpoints; unknown fields are never replaced by zero or a neutral factor.
    Multi-cargo rows need a separate model and are deliberately unsupported.
    """
    keys = ('p.revenueAnnual', 'p.profitAnnual', 'fund_profit', 'select_score',
            'g.a_gain_pct', 'g.b_gain_pct')
    if any(not finite_number(row.get(k)) for k in keys):
        return None
    revenue, profit, funded, score, ga, gb = (row[k] for k in keys)
    if (not is_rail_pax(row) or revenue < profit or profit <= 0 or funded <= 0
            or score <= 0 or not (0 <= ga <= 100 and 0 <= gb <= 100)
            or row.get('c.revenue2', 0) != 0 or row.get('c.carried2', 0) != 0):
        return None
    factor = (ga + gb) / 200.0
    costs = revenue - profit
    new_profit = revenue * factor - costs
    new_funded = new_profit * funded / profit
    return {'revenue': revenue * factor, 'costs': costs, 'raw_profit': new_profit,
            'fund_profit': new_funded, 'score': max(0.0, score * new_funded / funded)}


def fixed_cost_rank_sensitivity(games):
    """Sensitivity within a fully logged *ranked* list, no new admission.

    Exclude unranked affordable candidates: their opcode/admission gates were
    not recorded. Unknown or truncated selections are reported, never counted
    as unchanged. Even a complete logged ranked list is not the whole vivier.
    """
    prepared = []
    unknown = []
    original_scores = {}
    total = 0
    for idx, game in enumerate(games):
        name = game.get('name', f'game_{idx}')
        copy = {'name': name, 'select': {}, 'decomp': {}}
        for seq, sel in game.get('select', {}).items():
            total += 1
            rows = [r for r in game.get('decomp', {}).get(seq, []) if r.get('role') == 'ranked']
            count = sel.get('ranked')
            reason = None
            if (not isinstance(count, int) or isinstance(count, bool) or count <= 0
                    or len(rows) != count
                    or any(not isinstance(r.get('rank'), int) for r in rows)
                    or {r.get('rank') for r in rows} != set(range(count))):
                reason = 'missing_or_truncated_ranked_list'
            elif (any(not r.get('key') for r in rows)
                  or len({r['key'] for r in rows}) != len(rows)):
                reason = 'ambiguous_candidate_keys'
            converted = []
            if reason is None:
                for row in sorted(rows, key=lambda r: r['rank']):
                    if (row.get('affordable') != 1
                            or any(not finite_number(row.get(k)) for k in ('fund_profit', 'select_score', 'tier'))
                            or row['fund_profit'] <= 0 or row['select_score'] <= 0):
                        reason = 'missing_or_invalid_ranked_fields'
                        break
                    new_row = dict(row)
                    if is_rail_pax(row):
                        shadow = rail_pax_fixed_cost_shadow(row)
                        if shadow is None:
                            reason = 'missing_or_unsupported_economics'
                            break
                        new_row.update(fund_profit=shadow['fund_profit'], select_score=shadow['score'])
                        # Legacy aggregator now receives the already-adjusted economics.
                        new_row.update({'g.a_gain_pct': 100, 'g.b_gain_pct': 100})
                    converted.append(new_row)
            if reason is None:
                # A neutral shock must reproduce the observed ordering before
                # attributing any change to economics. V88/tie policies may not
                # be fully logged; do not invent their counterfactual result.
                baseline = sorted(rows, key=lambda r: r['rank'])
                ordered = sorted(baseline, key=lambda r: (r['tier'], r['select_score']), reverse=True)
                if [r['key'] for r in baseline] != [r['key'] for r in ordered]:
                    reason = 'baseline_order_not_reproduced'
                viable = sorted((r for r in converted if r['fund_profit'] > 0),
                                key=lambda r: (r['tier'], r['select_score']), reverse=True)
                if (len(viable) > 1 and viable[0]['tier'] == viable[1]['tier']
                        and viable[0]['select_score'] == viable[1]['select_score']):
                    reason = 'ambiguous_top_tie'
            if reason:
                unknown.append({'game': name, 'seq': seq, 'reason': reason})
                continue
            original_scores[(name, seq)] = next(r['select_score'] for r in rows if r['rank'] == 0)
            copy['select'][seq] = sel
            copy['decomp'][seq] = converted
        prepared.append(copy)
    result = replay_selections_6(prepared)
    for change in result['detailed_changes']:
        change['orig_score'] = original_scores[(change['game'], change['seq'])]
    result.update(observed_selections=total, unknown_selections=unknown,
                  model='fixed_cost_rank_sensitivity_v1', purchase_replay_complete=False)
    return result


def replay_selections_6(games):
    """Historical v1 calculation, retained to reproduce archived reports.

    Not an economic replay: it scales profit instead of revenue less costs.

    For each selection (seq):
    - rail PASS fund_profit *= mean(g.a_gain_pct, g.b_gain_pct)/100
    - drop if rescaled fund_profit <= 0 (admission)
    - re-score: rescaled fund_profit * 1000 / denominator
      where denominator = fund_profit * 1000 / select_score
    - re-sort ranked + affordable by (tier desc, score desc)
    - report rank-0 changes, replacements, counts per game in 1971-72.
    """
    total_selections = 0
    changed_selections = 0
    changed_1971_1972 = 0
    game_changes = collections.defaultdict(lambda: {'total': 0, '1971_1972': 0, 'selections': 0})
    replacements = collections.Counter()
    detailed_changes = []

    for game_idx, game in enumerate(games):
        gname = game.get('name', f"game_{game_idx}")
        for seq, sel in sorted(game.get('select', {}).items()):
            total_selections += 1
            game_changes[gname]['selections'] += 1
            rows = game.get('decomp', {}).get(seq, [])

            orig_rank0 = next((r for r in rows if r.get('role') == 'ranked' and r.get('rank') == 0), None)

            # Candidates: ranked and affordable rows
            candidates = []
            for r in rows:
                role = str(r.get('role', ''))
                is_aff = (r.get('affordable') == 1) or (role in ('ranked', 'affordable'))
                if not is_aff or role.startswith('built_') or role == 'unaffordable':
                    continue

                fund_prof = float(r.get('fund_profit', 0))
                select_sc = float(r.get('select_score', 0))
                tier = int(r.get('tier', 0))

                if is_rail_pax(r):
                    g_ends = [r[k] for k in ('g.a_gain_pct', 'g.b_gain_pct')
                              if k in r and isinstance(r[k], (int, float))]
                    if g_ends:
                        gain_factor = (sum(g_ends) / len(g_ends)) / 100.0
                        rescaled_prof = fund_prof * gain_factor
                        if rescaled_prof <= 0:
                            continue  # dropped by admission
                        if select_sc > 0 and fund_prof > 0:
                            denom = (fund_prof * 1000.0) / select_sc
                            new_sc = (rescaled_prof * 1000.0) / denom
                        else:
                            new_sc = select_sc * gain_factor
                    else:
                        rescaled_prof = fund_prof
                        new_sc = select_sc
                else:
                    rescaled_prof = fund_prof
                    new_sc = select_sc

                mk = f"{r.get('p.mode', '?')}/{r.get('p.kind', '?')}"
                candidates.append({
                    'key': r.get('key'),
                    'mode_kind': mk,
                    'tier': tier,
                    'score': new_sc,
                    'rescaled_profit': rescaled_prof,
                    'orig': r,
                })

            candidates.sort(key=lambda c: (c['tier'], c['score']), reverse=True)
            new_rank0 = candidates[0] if candidates else None

            orig_key = orig_rank0.get('key') if orig_rank0 else None
            new_key = new_rank0['key'] if new_rank0 else None

            if orig_key != new_key:
                changed_selections += 1
                sdate = sel.get('date', '')
                try:
                    s_year = int(sdate.split('-')[0])
                except (ValueError, AttributeError):
                    s_year = 0
                is_71_72 = (s_year in (1971, 1972))
                if is_71_72:
                    changed_1971_1972 += 1
                    game_changes[gname]['1971_1972'] += 1

                game_changes[gname]['total'] += 1
                orig_mk = f"{orig_rank0.get('p.mode')}/{orig_rank0.get('p.kind')}" if orig_rank0 else 'none'
                new_mk = new_rank0['mode_kind'] if new_rank0 else 'none'
                replacements[(orig_mk, new_mk)] += 1
                detailed_changes.append({
                    'game': gname,
                    'seq': seq,
                    'date': sdate,
                    'orig_mk': orig_mk,
                    'orig_key': orig_key,
                    'orig_score': orig_rank0.get('select_score', 0) if orig_rank0 else 0,
                    'new_mk': new_mk,
                    'new_key': new_key,
                    'new_score': new_rank0['score'] if new_rank0 else 0,
                    'is_71_72': is_71_72,
                })

    return {
        'total_selections': total_selections,
        'changed_selections': changed_selections,
        'changed_1971_1972': changed_1971_1972,
        'game_changes': dict(game_changes),
        'replacements': dict(replacements),
        'detailed_changes': detailed_changes,
    }


def competitor_arrival_g(games):
    """G. Competitor arrival: share of our rail freight industries where stations_around rises within 12 mo.

    Proxy: industries in V216_IND_FLOW appearing after our RAIL_BUILD month with matching cargo.
    """
    records = []

    for game_idx, game in enumerate(games):
        gname = game.get('name', f"game_{game_idx}")
        rail_joins = game.get('rail_joins') or join_rail_lines(game)

        freight_builds = []
        for lid, j in rail_joins.items():
            b = j['build']
            cg = cargo_group(b.get('cargo', ''))
            if cg == 'freight':
                try:
                    y, m, d = [int(p) for p in b.get('date', '').split('-')]
                    dt_b = datetime.date(y, m, d)
                    freight_builds.append((dt_b, b.get('cargo'), lid))
                except (ValueError, AttributeError):
                    continue

        if not freight_builds:
            continue

        ind_flows = collections.defaultdict(list)
        for row in game.get('ind_flow', []):
            try:
                y, m, d = [int(p) for p in row.get('date', '').split('-')]
                dt_r = datetime.date(y, m, d)
                ind_flows[row.get('industry')].append((dt_r, row))
            except (ValueError, AttributeError):
                continue

        for ind, flows in ind_flows.items():
            flows.sort(key=lambda x: x[0])
            first_dt, first_row = flows[0]
            ind_cargo = first_row.get('cargo')
            base_stations = first_row.get('stations_around', 1)

            matched_build = None
            for dt_b, b_cargo, lid in freight_builds:
                if b_cargo == ind_cargo and 0 <= (first_dt - dt_b).days <= 62:
                    matched_build = (dt_b, lid)
                    break
            if not matched_build:
                continue

            dt_b, lid = matched_build
            competitor_arrived = False
            arrival_dt = None
            for dt_r, row in flows:
                days_since_build = (dt_r - dt_b).days
                if 0 <= days_since_build <= 365:
                    if row.get('stations_around', 0) > base_stations:
                        competitor_arrived = True
                        arrival_dt = dt_r
                        break

            records.append({
                'game': gname,
                'industry': ind,
                'cargo': ind_cargo,
                'line': lid,
                'build_date': dt_b.strftime('%Y-%m-%d'),
                'first_seen': first_dt.strftime('%Y-%m-%d'),
                'base_stations': base_stations,
                'arrived': competitor_arrived,
                'arrival_date': arrival_dt.strftime('%Y-%m-%d') if arrival_dt else '—',
                'months_to_arrival': (round((arrival_dt - dt_b).days / 30.4, 1)) if arrival_dt else None,
            })

    total_ind = len(records)
    arrived_count = sum(1 for r in records if r['arrived'])
    share = (arrived_count / total_ind) if total_ind > 0 else 0.0

    return {
        'total_industries': total_ind,
        'arrived_count': arrived_count,
        'share': share,
        'records': records,
    }


def kdec_wins(games):
    """E : per mode, share of logged candidates whose score denominator is K_dec."""
    wins, total = collections.Counter(), collections.Counter()
    for game in games:
        for seq, rows in game['decomp'].items():
            kdec = game['select'].get(seq, {}).get('k_dec', 0)
            for r in rows:
                mode = r.get('p.mode', '?')
                total[mode] += 1
                if kdec > r.get('finance', 0):
                    wins[mode] += 1
    return {m: (wins[m], total[m]) for m in total}


def ghost_summary(games):
    """V216a : medians per mode of own/adverse coverage share and line/gain factors (%)."""
    acc = collections.defaultdict(lambda: collections.defaultdict(list))
    for game in games:
        rows = [r for rs in game['decomp'].values() for r in rs] + game['built']
        for r in rows:
            mode = f"{r.get('p.mode')}/{r.get('p.kind')}"
            for end in ('a', 'b'):
                prod = r.get(f'g.{end}_prod')
                if not isinstance(prod, int) or prod <= 0:
                    continue
                acc[mode]['own'].append(100.0 * r[f'g.{end}_own'] / prod)
                acc[mode]['adv'].append(100.0 * r[f'g.{end}_adv'] / prod)
                acc[mode]['line'].append(r.get(f'g.{end}_line_pct', 100))
                acc[mode]['gain'].append(r.get(f'g.{end}_gain_pct', 100))
            if isinstance(r.get('g.ops'), int):
                acc[mode]['ops'].append(r['g.ops'])
    return acc


def parse_cli_args(argv):
    """Parse CLI arguments into a list of (engine_dir, [policy, ...]) tuples.

    Supports:
    - <engine_dir> [policy ...] (backward compatibility)
    - <engine_dir>[:<policy>[,<policy>]] ...
    """
    if not argv:
        return []
    if len(argv) > 1 and not any(':' in a for a in argv) and not os.path.isdir(argv[1]):
        return [(argv[0], argv[1:])]

    specs = []
    for arg in argv:
        if ':' in arg:
            edir, pol_str = arg.split(':', 1)
            pols = [p.strip() for p in pol_str.split(',') if p.strip()]
            specs.append((edir, pols or ['ref', 'probe']))
        else:
            specs.append((arg, ['ref', 'probe']))
    return specs


def main(argv):
    specs = parse_cli_args(argv)
    if not specs:
        print("Usage: python sweeps/analyze_v216.py <engine_dir>[:<policy>[,<policy>]] ...")
        return

    out = ['# V216 — analyses de la sonde', '']
    all_cells = {}

    for engine, policies in specs:
        for pol in policies:
            logs = sorted(glob.glob(os.path.join(engine, f'{pol}_seed*_r0.log')))
            games = []
            for p in logs:
                g = parse_log(p)
                if g['counts']:
                    g['name'] = os.path.basename(p)
                    games.append((os.path.basename(p), g))
            if not games:
                continue

            cell_label = f"{os.path.basename(os.path.normpath(engine))}:{pol}" if len(specs) > 1 else pol
            all_cells[cell_label] = [g for _, g in games]
            game_objs = [g for _, g in games]

            out += [f'## Politique `{cell_label}` : {len(games)} parties sondées', '']

            # A. Premier rail voyageurs
            out += ['### A. Premier rail voyageurs construit et dernière sélection avant lui', '',
                    '| partie | date | rôle | mode | rang | palier | score | profit calibré | financement | revenu | transporté |',
                    '|---|---|---|---|---|---|---|---|---|---|---|']
            for name, g in games:
                res = first_rail_pax_choice(g)
                if res is None:
                    out.append(f'| {name} | aucun | | | | | | | | | |')
                    continue
                sel, built, rail, top, air, unaff = res
                out.append(f"| {name} | {built.get('date', '')} | construit " + describe(built))
                for role, row in (('ce rail dans la sélection', rail), ('rang 0', top),
                                  ('meilleur AIR classé', air), ('meilleur AIR non finançable', unaff)):
                    out.append(f"| {name} | {sel.get('date', '')} | {role} " + describe(row))
            out.append('')

            # B. Error attribution
            b_res = error_attribution_b(game_objs)
            out += ['### B. Attribution des erreurs : lignes rail 1971 (>= 180 j)', '']
            if not b_res:
                out.append('Aucune ligne rail 1971 éligible (>= 180 jours).\n')
            else:
                out += ['| groupe | n | revenu médian | ratio sommes revenu | profit médian | ratio sommes profit | offre moy. | capacité moy. | cap. séjour | liaison modèle | liaison séjour |',
                        '|---|---|---|---|---|---|---|---|---|---|---|']
                for cg, d in sorted(b_res.items()):
                    mo = f"{d['mean_offered']:.1f}" if d['mean_offered'] is not None else '—'
                    mc = f"{d['mean_capacity']:.1f}" if d['mean_capacity'] is not None else '—'
                    mcc = f"{d['mean_corr_capacity']:.1f}" if d['mean_corr_capacity'] is not None else '—'
                    ub = f"{d['uncorr_binds'].get('offered', 0)} off / {d['uncorr_binds'].get('capacity', 0)} cap"
                    cb = f"{d['corr_binds'].get('offered', 0)} off / {d['corr_binds'].get('capacity', 0)} cap"
                    out.append(f"| {cg} | {d['n']} | {d['rev_median']:.2f} | {d['rev_sum_ratio']:.2f} | "
                               f"{d['prof_median']:.2f} | {d['prof_sum_ratio']:.2f} | {mo} | {mc} | {mcc} | {ub} | {cb} |")
                out.append('')

            # E. K_dec wins
            out += ['### E. K_dec plus grand que le financement', '', '| mode | K_dec gagne | lignes | part |',
                    '|---|---|---|---|']
            for mode, (w, t) in sorted(kdec_wins(game_objs).items()):
                out.append(f'| {mode} | {w} | {t} | {w / t:.0%} |')
            out.append('')

            # V216a Ghost summary
            gs = ghost_summary(game_objs)
            out += ['### V216a. Fantôme : couverture et facteurs (médianes par extrémité, %)', '',
                    '| mode | extrémités | couvert par nous | couvert par adversaire seul | part ligne | gain compagnie | opcodes médians |',
                    '|---|---|---|---|---|---|---|']
            for mode, d in sorted(gs.items()):
                med = lambda k: statistics.median(d[k]) if d[k] else float('nan')
                out.append(f"| {mode} | {len(d['own'])} | {med('own'):.0f} | {med('adv'):.0f} "
                           f"| {med('line'):.0f} | {med('gain'):.0f} | {med('ops'):.0f} |")
            out.append('')

            # Replay §6
            rep = fixed_cost_rank_sensitivity(game_objs)
            out += ['### Sensibilité du rang à coûts fixes (v1, hors rejeu des achats)', '',
                    'Choc sur le revenu, coûts/calibration/dénominateur constants ; seuls les projets déjà classés sont considérés.',
                    'Dimensionnement, seuils opcodes, nouveaux entrants et achats ne sont pas rejoués.',
                    f"- sélections observées : {rep['observed_selections']}",
                    f"- sélections calculables : {rep['total_selections']}",
                    f"- sélections indéterminées : {len(rep['unknown_selections'])}",
                    f"- sélections avec changement du rang 0 : {rep['changed_selections']} (dont {rep['changed_1971_1972']} en 1971-72)", '']
            for reason, count in sorted(collections.Counter(r['reason'] for r in rep['unknown_selections']).items()):
                out.append(f'- indéterminées ({reason}) : {count}')
            if rep['replacements']:
                out += ['| choix initial | remplaçant | occurrences |', '|---|---|---|']
                for (orig_mk, new_mk), count in sorted(rep['replacements'].items(), key=lambda x: -x[1]):
                    out.append(f"| {orig_mk} | {new_mk} | {count} |")
                out.append('')

            # G. Competitor arrival
            g_res = competitor_arrival_g(game_objs)
            out += ['### G. Arrivée de la concurrence (industries fret rail)', '',
                    f"- industries sources fret observées : {g_res['total_industries']}",
                    f"- arrivée d'un concurrent sous 12 mois : {g_res['arrived_count']} ({g_res['share']:.1%})",
                    "*(src tile non requis : proxy basé sur les lignes V216_IND_FLOW dont stations_around augmente après le mois de RAIL_BUILD)*", '']
            if g_res['records']:
                out += ['| partie | industrie | cargo | ligne | date construction | première obs. | gares initiales | arrivée 12 mois | date arrivée | mois écoulés |',
                        '|---|---|---|---|---|---|---|---|---|---|']
                for r in g_res['records']:
                    m_arr = f"{r['months_to_arrival']:.1f}" if r['months_to_arrival'] is not None else '—'
                    out.append(f"| {r['game']} | {r['industry']} | {r['cargo']} | {r['line']} | {r['build_date']} "
                               f"| {r['first_seen']} | {r['base_stations']} | {'OUI' if r['arrived'] else 'NON'} "
                               f"| {r['arrival_date']} | {m_arr} |")
                out.append('')

            # Coût de la sonde
            sel_ops = [s['probe_ops'] for g in game_objs for s in g['select'].values() if 'probe_ops' in s]
            flow_ops = [f['probe_ops'] for g in game_objs for f in g['flow_done'] if 'probe_ops' in f]
            out += ['### Coût de la sonde', '',
                    f'- sélections journalisées : {len(sel_ops)}, opcodes total {sum(sel_ops)}, '
                    f'médiane {statistics.median(sel_ops) if sel_ops else 0:.0f}, max {max(sel_ops, default=0)}',
                    f'- relevés mensuels : {len(flow_ops)}, opcodes total {sum(flow_ops)}', '']

    # D. Invariance test across all cells
    if all_cells:
        d_res = invariance_test_d(all_cells)
        out += ['## D. Test numérique d\'invariance (hors qualification économique)', '',
                'Vérifier la correspondance des quatre cellules à A/B/C/D ; revenu de ligne et gain net compagnie ne sont pas interchangeables.',
                '| cellule / politique | lignes PASS 1971 | somme réalisé | somme prévu actuel | ratio actuel | somme prévu fantôme (gain) | ratio fantôme (gain) | somme prévu fantôme (ligne) | ratio fantôme (ligne) |',
                '|---|---|---|---|---|---|---|---|---|']
        for cell, c in sorted(d_res['cells'].items()):
            rc = f"{c['ratio_curr']:.2f}" if c['ratio_curr'] is not None else '—'
            rg = f"{c['ratio_ghost_gain']:.2f}" if c['ratio_ghost_gain'] is not None else '—'
            rl = f"{c['ratio_ghost_line']:.2f}" if c['ratio_ghost_line'] is not None else '—'
            out.append(f"| {cell} | {c['n']} | {c['sum_real']:.0f} | {c['sum_pred_curr']:.0f} | {rc} "
                       f"| {c['sum_pred_gain']:.0f} | {rg} | {c['sum_pred_line']:.0f} | {rl} |")
        out.append('')
        crit_msg = (f"- ratios fantôme gain : min = {d_res['min_ratio']:.2f}, max = {d_res['max_ratio']:.2f}, "
                    f"max/min = {d_res['spread']:.2f} (seuil <= 1.5, borne [0.7, 1.4])"
                    if d_res['min_ratio'] is not None else "- aucune ligne rail PASS 1971 éligible")
        out += [crit_msg, f"**Verdict test d'invariance : {d_res['verdict']}**", '']

    print('\n'.join(out))


if __name__ == '__main__':
    main(sys.argv[1:])
