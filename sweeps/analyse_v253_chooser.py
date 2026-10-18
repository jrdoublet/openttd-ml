"""Replay hors jeu du chooser V252, depuis des journaux existants.

Caracteristiques : table ENGINES du code analyse_v253_avions.py (table agy,
non certifiee par l'API). Tarifs : helper OpenTTD 15.3 deja utilise par C119.
Pas d'appel moteur. Les prix ne sont pas extrapoles ni indexes par une inflation
supposee. La disponibilite exacte et les filtres NoAI restent non observes.
"""
import argparse
import ast
import json
import math
from pathlib import Path
import re
import struct

from analyse_c119_air_income_shadow import cargo_income, PAX_PAYMENT, MAIL_PAYMENT

ROOT = Path(__file__).resolve().parents[1]


def f32(value):
    """Squirrel utilise des flottants 32 bits dans ce runtime."""
    return struct.unpack('f', struct.pack('f', value))[0]


def engines_from_code():
    source = ROOT / 'sweeps/analyse_v253_avions.py'
    for node in ast.parse(source.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == 'ENGINES' for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('table ENGINES absente')


def replay(plane, distance, demand, *, planes=1, direct=False,
           mail=True, amort=True, running=True):
    """OpexAirEconomics : fixedPlanes, aeroport deja paye, transit_cost=0.

    direct=True ne fait QU'oter /4 : sensibilite C100, pas un replay C121.
    Les operations flottantes suivent l'ordre du Squirrel ; divisions entieres
    pour le forfait courrier et l'amortissement. Aucun arrondi des jours avant
    le tarif (ceil seulement), aucun ceil de carried.
    """
    speed = f32(plane['speed_noai'] / (1.0 if direct else 4.0))
    flight = f32(distance / f32(f32(.036) * speed))
    one_way = max(1.0, f32(flight + 3.0))
    round_trip = f32(2.0 * one_way)
    trips = f32(f32(30.4) / one_way)
    capacity = f32(plane['pax'] * trips)
    headway = f32(round_trip / planes)
    pickup = next((p for limit, p in ((7.5, 130), (15, 95), (30, 50),
                                     (52.5, 25)) if headway < limit), 0)
    rating = f32(f32(100.0 * f32(32.5 + pickup)) / 255.0)
    offered = f32(f32(demand * rating) / 100.0)
    carried = int(min(offered, f32(planes * capacity)))
    days = math.ceil(one_way)
    pax_income = cargo_income(distance, days, PAX_PAYMENT)
    mail_income = cargo_income(distance, days, MAIL_PAYMENT) if mail else 0
    fare = f32((pax_income + mail_income * 15 // 100) * 104 / 100.0)
    revenue = int(f32(12 * carried * fare))
    running_annual = planes * plane['running'] if running else 0
    amort_annual = planes * plane['price'] // 20 if amort else 0
    profit = revenue - running_annual - amort_annual
    capital = planes * plane['price']
    # Squirrel division entiere tronquee vers zero, y compris profit negatif.
    roi = abs(profit * 1000) // capital * (1 if profit >= 0 else -1)
    return dict(profit=profit, revenue=revenue, running=running_annual,
                amort=amort_annual, roi=roi, days=days, one_way=one_way,
                headway=headway, rating=rating, offered=offered,
                capacity=f32(planes * capacity), carried=carried,
                pax_income=pax_income, mail_income=mail_income, fare=fare)


def fields(raw):
    return dict(re.findall(r'(\w+)=([^\s]+)', raw))


def analyse(path, limit=3):
    lines = path.read_text(encoding='utf-8').splitlines()
    builds, events = {}, []
    characteristics = engines_from_code()
    for lineno, raw in enumerate(lines, 1):
        if ' AIR_BUILD ' in raw:
            kv = fields(raw)
            builds[int(kv['line'])] = kv
        if ' V252_ENGINE ' not in raw and ' V252_REPLACE ' not in raw:
            continue
        kv = fields(raw)
        if kv.get('new_engine') != '217' or 'demand_now' not in kv:
            continue
        build = builds.get(int(kv['line']))
        if build is None:
            continue
        # Eviter trois observations successives de la meme ligne.
        if any(e['line'] == int(kv['line']) for e in events):
            continue
        date = re.search(r'OPEX (\d+-\d+-\d+)', raw).group(1)
        year = int(date.split('-')[0])
        distance = int(build['dist'])
        event = dict(line=int(kv['line']), date=date, log_line=lineno,
                     distance=distance, demand_old=int(kv['demand_old']),
                     demand_now=int(kv['demand_now']), scenarios={})
        for name, demand, opts in (
                ('mode2', event['demand_old'], {}),
                ('ancien_mode3', event['demand_now'], {}),
                ('sans_division_vitesse', event['demand_now'], {'direct': True}),
                ('sans_courrier', event['demand_now'], {'mail': False}),
                ('sans_amortissement', event['demand_now'], {'amort': False}),
                ('sans_running', event['demand_now'], {'running': False})):
            rows = [dict(engine=eid, **replay(p, distance, demand, **opts))
                    for eid, p in characteristics.items() if p['intro'] < year]
            rows.sort(key=lambda r: (r['profit'], r['roi']), reverse=True)
            event['scenarios'][name] = rows
        events.append(event)
        if len(events) == limit:
            break
    return dict(source=str(path), characteristics_source='sweeps/analyse_v253_avions.py:ENGINES',
                limitations=[
                    'Table agy du code, pas un dump des candidats NoAI au choix.',
                    'Introduction par annee seulement : candidats intro < annee ; bornes exactes inconnues.',
                    'Tarif standard OpenGFX sans inflation, helper C119 ; prix constants de la table.',
                    'Distance AIR_BUILD (conservee par la ligne) ; aucune geometrie inventee.',
                    'Sensibilites separees, pas des corrections C121 ni des profits realises.',
                    'Nombre vivant au choix non journalise : aucun N de flotte suppose.'],
                engines=characteristics, events=events)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--limit', type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(analyse(args.log, args.limit), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
