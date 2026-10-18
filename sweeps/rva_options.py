"""One dossier per OD; full alternative quotes, no fixed V207 package.

Option economics are computed with the existing dry cycle/company contracts.
No route commands. Actual footprint must be requoted after partial failure.
"""
from rva_dry_cycle import dry_cycle, known
from rva_company_gain import company_gain


def dossier_key(src, dst, cargo):
    return (min(src, dst), max(src, dst), cargo)


def evaluate_options(key, options, *, context, budget, actual_tiles=None):
    evaluated, seen = [], set()
    for option in options:
        identity = option['option_id']
        if identity in seen:
            raise ValueError('Duplicate option')
        seen.add(identity)
        if dossier_key(*option['od']) != key:
            raise ValueError('Options must share an OD dossier')
        if not option.get('feasible'):
            evaluated.append({'option_id': identity, 'status': 'infeasible'})
            continue
        if actual_tiles is not None and set(option['tiles']) != set(actual_tiles):
            evaluated.append({'option_id': identity, 'status': 'requote_actual_footprint'})
            continue
        if option.get('incremental_tiles') == [] and option.get('extension'):
            evaluated.append({'option_id': identity, 'status': 'redundant_extension'})
            continue
        cycle = dry_cycle(**option['cycle'])
        revenues = []
        for cargo in cycle['cargos']:
            income = option['annual_income_per_monthly_unit'].get(cargo['cargo'])
            carried = cargo['carried_month']
            revenues.append(carried * income if known(carried) and known(income) and income >= 0 else None)
        line = dict(option['line'], context=context, demand_basis='physical_line_demand',
                    revenue_basis='final_company_receipts', corrections=option['corrections'],
                    revenue_annual=sum(revenues) if revenues and all(known(v) for v in revenues) else None)
        net = company_gain(line, option['effects'], affected_inventory_complete=option['effects_complete'])
        capital = net['capital_required']
        evaluated.append({'option_id': identity, 'status': 'estimated', 'cycle': cycle, **net,
                          'affordable': known(capital) and capital <= budget})
    eligible = [r for r in evaluated if r.get('affordable') and known(r.get('gain_company_annual'))]
    # Stable input order breaks ties; no score coefficient or extra OD purchase.
    selected = max(eligible, key=lambda r: r['gain_company_annual']) if eligible else None
    return {'dossier': key, 'options': evaluated,
            'selected_option': selected['option_id'] if selected else None,
            'status': 'estimated' if selected else 'reference_fallback'}
