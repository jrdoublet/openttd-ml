"""Entonnoir rail par annee en partie complete (lecture seule, journaux decision_log).

Usage : python sweeps/analyze_rail7273.py <engine_dir> <policy_id> [--years 1971-1974]

Pour chaque annee, sommes sur les parties (et moyenne par partie entre parentheses) :
- vivier : candidats rail produits / gardes (VIVIER_GEN mode=rail) ;
- classement : lignes rail dans PORTFOLIO_RANK, meilleur rang rail median par classement ;
- choix : PROJECT_CHOSEN par mode, capital engage par mode ;
- rail : tentatives (RAIL_ATTEMPT ok / echecs par raison), poses (RAIL_BUILD), echecs de pose
  (RAIL_BUILD_FAIL par raison) ;
- abandons de projets (PROJECT_DISCARD) par mode et raison ;
- caisse : budget vivant median des choix (B6_PORTFOLIO live_budget).
"""
import argparse
import collections
import glob
import os
import re
import statistics

KV = re.compile(r'([\w.]+)=(\S+)')
KINDS = {'VIVIER_GEN', 'PORTFOLIO_RANK', 'PROJECT_CHOSEN', 'RAIL_ATTEMPT', 'RAIL_BUILD',
         'RAIL_BUILD_FAIL', 'PROJECT_DISCARD', 'B6_PORTFOLIO', 'AIR_BUILD', 'VIVIER'}


def events(path):
    """Yield (year, month, kind, fields) for the decision events this analysis reads."""
    with open(path, errors='replace') as fh:
        for line in fh:
            if ' OPEX ' not in line:
                continue
            parts = line.split(' OPEX ', 1)[1].rstrip('\n').split(' ', 2)
            if len(parts) < 2 or parts[1] not in KINDS:
                continue
            try:
                y, m, _ = (int(x) for x in parts[0].split('-'))
            except ValueError:
                continue
            f = dict(KV.findall(parts[2] if len(parts) > 2 else ''))
            f['_day'] = parts[0].split('-')[2]
            yield y, m, parts[1], f


def day_index(y, m, d=1):
    return y * 372 + (m - 1) * 31 + d


def game_funnel(path):
    """Per year counters for one game."""
    chosen_at = {}
    years = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    lists = collections.defaultdict(lambda: collections.defaultdict(list))
    current = None
    for y, m, kind, f in events(path):
        c = years[y]
        if kind == 'VIVIER_GEN' and f.get('mode') == 'rail':
            c['vivier']['produced'] += int(f.get('produced', 0))
            c['vivier']['kept'] += int(f.get('kept', 0))
            c['vivier']['gens'] += 1
        elif kind == 'PORTFOLIO_RANK':
            # Un classement = suite de rangs partant de 0 ; on garde le meilleur rang rail
            # (10**6 = aucun rail dans ce classement).
            if f.get('rank') == '0':
                if current is not None:
                    lists[current[0]]['best_rail_rank'].append(current[1])
                current = [y, 10 ** 6]
                c['rank']['lists'] += 1
            c['rank']['rows'] += 1
            if f.get('mode') == 'rail':
                c['rank']['rail_rows'] += 1
                if current is not None:
                    current[1] = min(current[1], int(f.get('rank', 0)))
        elif kind == 'PROJECT_CHOSEN':
            mode = f.get('mode', '?')
            c['chosen'][mode] += 1
            if mode == 'rail':
                chosen_at.setdefault((f.get('src'), f.get('dst')), day_index(y, m, int(f['_day'])))
            c['capital'][mode] += int(f.get('cost', 0) or 0)
        elif kind == 'RAIL_ATTEMPT':
            c['attempt']['ok' if f.get('ok') == '1' else 'ko:' + f.get('reason', '?')] += 1
            c['attempt_kind'][f.get('kind', '?')] += 1
            t0 = chosen_at.pop((f.get('src'), f.get('dst')), None)
            if t0 is not None:
                lists[y]['choice_to_attempt_days'].append(day_index(y, m, int(f['_day'])) - t0)
            if f.get('search_ops', '').isdigit():
                lists[y]['search_mops'].append(int(f['search_ops']) / 1e6)
            if f.get('iters', '').isdigit():
                lists[y]['iters'].append(int(f['iters']))
        elif kind == 'RAIL_BUILD':
            c['build'][f.get('cargo', '?')] += 1
        elif kind == 'RAIL_BUILD_FAIL':
            c['build_fail'][f.get('reason', '?')] += 1
        elif kind == 'PROJECT_DISCARD':
            c['discard'][f.get('mode', '?') + ':' + f.get('reason', '?')] += 1
        elif kind == 'B6_PORTFOLIO':
            try:
                lists[y]['live_budget'].append(int(f.get('live_budget', 0)))
            except ValueError:
                pass
        elif kind == 'AIR_BUILD':
            c['air']['builds'] += 1
    if current is not None:
        lists[current[0]]['best_rail_rank'].append(current[1])
    return years, lists


def med(xs, nd=0):
    if not xs:
        return '—'
    return round(statistics.median(xs), nd) if nd else int(statistics.median(xs))


def fmt_counter(counter, n_games, top=6):
    items = counter.most_common(top)
    return ', '.join(f'{k} {v} ({v / n_games:.1f})' for k, v in items) or '—'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('engine')
    ap.add_argument('policy')
    ap.add_argument('--years', default='1971-1974')
    args = ap.parse_args()
    y0, y1 = (int(x) for x in args.years.split('-'))
    logs = sorted(glob.glob(os.path.join(args.engine, f'{args.policy}_seed*_r0.log')))
    total = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    lists = collections.defaultdict(lambda: collections.defaultdict(list))
    n = 0
    for path in logs:
        years, ls = game_funnel(path)
        if not years:
            continue
        n += 1
        for y, groups in years.items():
            for g, counter in groups.items():
                total[y][g].update(counter)
        for y, d in ls.items():
            for k, v in d.items():
                lists[y][k].extend(v)
    out = [f'# Entonnoir rail par année — `{args.policy}`, {n} parties', '',
           'Sommes sur les parties ; entre parenthèses, moyenne par partie.', '']
    for y in range(y0, y1 + 1):
        t, l = total[y], lists[y]
        ranks = [r for r in l['best_rail_rank'] if r < 10 ** 6]
        absent = sum(1 for r in l['best_rail_rank'] if r >= 10 ** 6)
        out += [f'## {y}', '',
                f"- vivier rail : {t['vivier']['gens']} générations, produits {t['vivier']['produced']}, "
                f"gardés {t['vivier']['kept']} ({t['vivier']['kept'] / max(n, 1):.1f})",
                f"- classements : {t['rank']['lists']}, lignes {t['rank']['rows']} dont rail "
                f"{t['rank']['rail_rows']} ; meilleur rang rail médian "
                f"{statistics.median(ranks) if ranks else '—'} ; classements sans rail {absent}",
                f"- choisis : {fmt_counter(t['chosen'], n)}",
                f"- capital engagé (k£) : " + ', '.join(
                    f'{k} {v // 1000} ({v / 1000 / n:.0f})' for k, v in t['capital'].most_common()),
                f"- tentatives rail : {fmt_counter(t['attempt'], n, 8)} ; par nature {fmt_counter(t['attempt_kind'], n)}",
                f"- poses rail : {fmt_counter(t['build'], n, 8)}",
                f"- échecs de pose : {fmt_counter(t['build_fail'], n)}",
                f"- abandons : {fmt_counter(t['discard'], n, 8)}",
                f"- budget vivant médian des choix : "
                f"{statistics.median(l['live_budget']) // 1000 if l['live_budget'] else '—'} k£ "
                f"({len(l['live_budget'])} choix)",
                f"- choix → tentative : médiane {med(l['choice_to_attempt_days'])} j "
                f"({len(l['choice_to_attempt_days'])} appariés) ; itérations médianes {med(l['iters'])} ; "
                f"opcodes de recherche médians {med(l['search_mops'], 2)} M", '']
    print('\n'.join(out))


if __name__ == '__main__':
    main()
