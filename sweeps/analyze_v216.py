"""V216 etape 3 : analyses des journaux de la sonde `v216_probe` (lecture seule).

Usage : python sweeps/analyze_v216.py <engine_dir> [<policy_id> ...]

Lit <engine_dir>/<policy>_seed*_r0.log (journaux moteur, --script-debug) et ecrit en Markdown :
- A : pourquoi le premier rail voyageurs passe (choisi contre meilleurs AIR finançable et non
  finançable de la meme selection) ;
- E : combien de fois K_dec l'emporte sur le capital de financement, par mode ;
- couts de la sonde (opcodes) et volumes de lignes.
Les analyses B, C, D, G, H s'ajoutent quand les diagnostics 20x3 sondes existent.
"""
import collections
import glob
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
    """Return (date, kind, fields) for an `OPEX <date> V216_*` line, else None."""
    if ' OPEX ' not in line or ' V216_' not in line:
        return None
    rest = line.split(' OPEX ', 1)[1].rstrip('\n').split(' ', 2)
    if len(rest) < 2 or not rest[1].startswith('V216_'):
        return None
    fields = {k: num(v) for k, v in KV.findall(rest[2] if len(rest) > 2 else '')}
    return rest[0], rest[1], fields


def parse_log(path):
    """Group a game's probe rows: selections (by seq), builds, flows, rejects."""
    game = {'select': {}, 'decomp': collections.defaultdict(list), 'built': [],
            'flow_done': [], 'reject': [], 'counts': collections.Counter()}
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
    return game


def is_rail_pax(row):
    return row.get('p.mode') == 'rail' and row.get('p.kind') == 'pax'


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


def main(argv):
    engine, policies = argv[0], argv[1:] or ['ref', 'probe']
    out = ['# V216 — analyses de la sonde', '']
    for pol in policies:
        logs = sorted(glob.glob(os.path.join(engine, f'{pol}_seed*_r0.log')))
        games = [(os.path.basename(p), parse_log(p)) for p in logs]
        games = [(n, g) for n, g in games if g['counts']]
        if not games:
            continue
        out += [f'## Politique `{pol}` : {len(games)} parties sondées', '']
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
        out += ['### E. K_dec plus grand que le financement', '', '| mode | K_dec gagne | lignes | part |',
                '|---|---|---|---|']
        for mode, (w, t) in sorted(kdec_wins([g for _, g in games]).items()):
            out.append(f'| {mode} | {w} | {t} | {w / t:.0%} |')
        out.append('')
        gs = ghost_summary([g for _, g in games])
        out += ['### V216a. Fantôme : couverture et facteurs (médianes par extrémité, %)', '',
                '| mode | extrémités | couvert par nous | couvert par adversaire seul | part ligne | gain compagnie | opcodes médians |',
                '|---|---|---|---|---|---|---|']
        for mode, d in sorted(gs.items()):
            med = lambda k: statistics.median(d[k]) if d[k] else float('nan')
            out.append(f"| {mode} | {len(d['own'])} | {med('own'):.0f} | {med('adv'):.0f} "
                       f"| {med('line'):.0f} | {med('gain'):.0f} | {med('ops'):.0f} |")
        out.append('')
        sel_ops = [s['probe_ops'] for _, g in games for s in g['select'].values() if 'probe_ops' in s]
        flow_ops = [f['probe_ops'] for _, g in games for f in g['flow_done'] if 'probe_ops' in f]
        out += ['### Coût de la sonde', '',
                f'- sélections journalisées : {len(sel_ops)}, opcodes total {sum(sel_ops)}, '
                f'médiane {statistics.median(sel_ops) if sel_ops else 0:.0f}, max {max(sel_ops, default=0)}',
                f'- relevés mensuels : {len(flow_ops)}, opcodes total {sum(flow_ops)}', '']
    print('\n'.join(out))


if __name__ == '__main__':
    main(sys.argv[1:])
