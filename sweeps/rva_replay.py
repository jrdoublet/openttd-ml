"""Explicit admission/finance/selection replay. No rank -> executed-buy shortcut.

Sources: projects_selection.nut:690-852,903-977; projects_models.nut:186.
Input is the post-fitting snapshot; refitting a fleet needs its original model.
"""
from rva_dry_cycle import known


def select(snapshot, overrides=None):
    if not snapshot.get('inventory_complete') or not snapshot.get('fit_complete'):
        return {'status': 'not_covered', 'reason': 'incomplete_inputs', 'selected': None}
    overrides = overrides or {}
    rows, rejected = [], {}
    for p in snapshot['projects']:
        q = dict(p)
        if p['key'] in overrides:
            q.update(overrides[p['key']])
        if any(not known(q.get(k)) for k in ('finance','decision_finance','profit','fund_profit','revenue','tier','bonus_pct')):
            return {'status':'not_covered','reason':'missing_economics','selected':None}
        if q.get('mode') == 'fleet' and q.get('fleet_exempt') is None:
            return {'status':'not_covered','reason':'missing_fleet_realization_contract','selected':None}
        if q['finance'] > snapshot['budget']:
            rejected[q['key']] = 'cash'
        else:
            rows.append(q)
    best = max((p['profit'] for p in rows), default=0)
    floor = max(0,best) * snapshot['floor_pct'] / 100
    admitted = [p for p in rows if p['profit'] >= floor]
    # Existing fallback retries without floor if nothing survived.
    if not admitted and floor > 0:
        admitted = rows
    for p in rows:
        if p not in admitted:
            rejected[p['key']] = 'floor'
    for p in admitted:
        denom = p['decision_finance'] if p.get('fleet_exempt') else max(snapshot['k_dec'],p['decision_finance'])
        score = p['fund_profit'] * 1000 / denom if p['fund_profit'] > 0 and denom > 0 else 0
        p['score'] = score * ((100+p['bonus_pct'])/100 if p['mode']=='air' and p['bonus_pct']>0 else 1)
    ordered = sorted(admitted, key=lambda p:(-p['tier'],-p['score'],-p['revenue']))
    ranked = ordered[:snapshot['limit']]
    return {'status':'replayed_post_fit','floor':floor,'rejected':rejected,
            'ranked':[p['key'] for p in ranked], 'selected':ranked[0]['key'] if ranked else None,
            'simulated_purchase':None, 'executed_purchase':None,
            'purchase_status':'requires_live_prechecks_path_quote_and_command_result'}


def logged_snapshot(selection, rows, floor_pct, limit):
    unique = {r['key']:r for r in rows}
    projects = []
    for key,r in unique.items():
        projects.append(dict(key=key,mode=r.get('p.mode'),finance=r.get('finance'),
            decision_finance=r.get('p.decisionFinanceCapital',r.get('finance')),
            profit=r.get('p.profitAnnual'),fund_profit=r.get('fund_profit'),
            revenue=r.get('p.revenueAnnual'),tier=r.get('tier'),
            bonus_pct=r.get('p.earlySlotBonusPct',0),
            fleet_exempt=None if r.get('p.mode')=='fleet' else False))
    return dict(inventory_complete=len(unique)==selection['alternatives'],
                fit_complete=True,projects=projects,budget=selection['budget'],
                k_dec=selection['k_dec'],floor_pct=floor_pct,limit=limit)
