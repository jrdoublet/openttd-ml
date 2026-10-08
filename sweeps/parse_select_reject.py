#!/usr/bin/env python3
"""
parse_select_reject.py

Parse les journaux d'OpexAI pour extraire la sonde SELECT_REJECT
et croise les candidats rejetes avec les paires aeriennes d'AAAHogEx.

Usage:
    python3 sweeps/parse_select_reject.py [--log <path_or_glob>] [--results <path.json>]
    python3 sweeps/parse_select_reject.py --selftest
"""

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

SELECT_REJECT_RE = re.compile(
    r'(?:OPEX\s+)?(?P<date>\d+-\d+-\d+)?\s*SELECT_REJECT\s+'
    r'pair=(?P<src>\d+)\|(?P<dst>\d+)\s+'
    r'type=(?P<type>\w+)\s+'
    r'reason=(?P<reason>\w+)\s+'
    r'rank=(?P<rank>\d+)\s+'
    r'score=(?P<score>\S+)\s+'
    r'top=(?P<top>\S+)'
)

AIR_TOWN_SERVED_RE = re.compile(r'AIR_TOWN_SERVED.*town_id=(\d+)\s+town_tile=(\d+)')
C96_SITE_RE = re.compile(r'C96_SITE.*town=(\d+).*tile=(\d+)')
AIR_BUILD_RE = re.compile(r'AIR_BUILD.*src=(\d+).*dst=(\d+).*src_town=(\d+).*dst_town=(\d+)')


def extract_town_map_from_logs(log_paths):
    """Construit un dictionnaire tile -> town_id a partir des traces du journal."""
    tile2town = {}
    for path in log_paths:
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                m = AIR_TOWN_SERVED_RE.search(line)
                if m:
                    tid, tile = int(m.group(1)), int(m.group(2))
                    tile2town[tile] = tid
                    continue
                m = C96_SITE_RE.search(line)
                if m:
                    tid, tile = int(m.group(1)), int(m.group(2))
                    tile2town[tile] = tid
                    continue
                m = AIR_BUILD_RE.search(line)
                if m:
                    s_tile, d_tile, s_tid, d_tid = (
                        int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
                    )
                    tile2town[s_tile] = s_tid
                    tile2town[d_tile] = d_tid
    return tile2town


def parse_select_reject_lines(lines, tile2town=None):
    """Extrait les enregistrements SELECT_REJECT d'une sequence de lignes."""
    records = []
    if tile2town is None:
        tile2town = {}

    for line in lines:
        m = SELECT_REJECT_RE.search(line)
        if not m:
            continue
        d = m.groupdict()
        src_val = int(d['src'])
        dst_val = int(d['dst'])

        # Si src_val et dst_val sont des tuiles, convertir en town_id
        src_town = tile2town.get(src_val, src_val)
        dst_town = tile2town.get(dst_val, dst_val)
        pair = tuple(sorted((src_town, dst_town)))

        records.append({
            'date': d.get('date'),
            'src_raw': src_val,
            'dst_raw': dst_val,
            'town_pair': pair,
            'type': d['type'],
            'reason': d['reason'],
            'rank': int(d['rank']),
            'score': float(d['score']),
            'top': float(d['top']),
            'line': line.strip(),
        })
    return records


def parse_select_reject_logs(log_paths, tile2town=None):
    """Lit une liste de fichiers logs et extrait tous les rejets."""
    if tile2town is None:
        tile2town = extract_town_map_from_logs(log_paths)

    records_by_seed = defaultdict(list)
    for path in log_paths:
        m_seed = re.search(r'seed(\d+)', path)
        seed = int(m_seed.group(1)) if m_seed else 0
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            recs = parse_select_reject_lines(f, tile2town)
            records_by_seed[seed].extend(recs)
    return records_by_seed, tile2town


def load_aaa_air_pairs_from_json(results_json_path):
    """
    Extrait les paires aeriennes construites par AAAHogEx depuis un fichier de resultats JSON.
    Retourne {seed: {pair: info_ligne}}.
    """
    if not results_json_path or not os.path.exists(results_json_path):
        return {}

    with open(results_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    snapshots = data.get('line_telemetry', {}).get('snapshots', [])
    aaa_pairs = defaultdict(dict)

    for snap in snapshots:
        if snap.get('arm') != 'AAAHogEx':
            continue
        seed = snap.get('seed', 0)
        lines = snap.get('lines', [])
        for line in lines:
            if line.get('mode') != 'air':
                continue
            town_ids = line.get('ordered_town_ids', [])
            if len(town_ids) >= 2:
                # Sauvegarde OpenTTD : TownID + 1 dans la capture
                tA = town_ids[0] - 1
                tB = town_ids[1] - 1
                pair = tuple(sorted((tA, tB)))
                # Conserver ou mettre a jour avec le profit le plus recent
                prev = aaa_pairs[seed].get(pair)
                profit = line.get('profit_last_year_gbp', 0.0)
                if prev is None or profit > prev.get('profit', 0):
                    aaa_pairs[seed][pair] = {
                        'townA': tA,
                        'townB': tB,
                        'profit': profit,
                        'vehicles': line.get('vehicles', 0),
                        'cargo_types': line.get('cargo_types', []),
                        'date': snap.get('date'),
                    }
    return aaa_pairs


def cross_rejects_with_aaa(records_by_seed, aaa_pairs_by_seed):
    """
    Croise les rejets de selection avec les paires AAAHogEx.
    Retourne la liste des correspondances et des statistiques globales.
    """
    matched = []
    reason_counter = Counter()
    type_counter = Counter()
    aaa_total = sum(len(pairs) for pairs in aaa_pairs_by_seed.values())
    matched_aaa_pairs = set()

    for seed, recs in records_by_seed.items():
        aaa_seed_pairs = aaa_pairs_by_seed.get(seed, {})
        for r in recs:
            reason_counter[r['reason']] += 1
            type_counter[r['type']] += 1
            pair = r['town_pair']
            if pair in aaa_seed_pairs:
                matched_aaa_pairs.add((seed, pair))
                matched.append({
                    'seed': seed,
                    'pair': pair,
                    'type': r['type'],
                    'reason': r['reason'],
                    'rank': r['rank'],
                    'score': r['score'],
                    'top': r['top'],
                    'date': r['date'],
                    'aaa_info': aaa_seed_pairs[pair],
                })

    return {
        'total_rejects': sum(len(v) for v in records_by_seed.values()),
        'reasons': dict(reason_counter),
        'types': dict(type_counter),
        'aaa_total_pairs': aaa_total,
        'aaa_matched_count': len(matched_aaa_pairs),
        'matches': matched,
    }


def format_report(analysis):
    """Produit un rapport texte synthese."""
    lines = []
    lines.append("=== Rapport d'analyse SELECT_REJECT ===")
    lines.append(f"Total rejets enregistres : {analysis['total_rejects']}")
    lines.append(f"Par motif : {analysis['reasons']}")
    lines.append(f"Par type : {analysis['types']}")
    lines.append(f"Paires AAA total : {analysis['aaa_total_pairs']}")
    lines.append(f"Paires AAA rejetees au portefeuille : {analysis['aaa_matched_count']}")
    if analysis['matches']:
        lines.append("\nDetail des paires AAA rejetees :")
        lines.append(f"{'Seed':<6} {'Paire':<12} {'Type':<10} {'Motif':<8} {'Rang':<6} {'Score':<10} {'Top':<10} {'Profit AAA':<12}")
        lines.append("-" * 80)
        for m in sorted(analysis['matches'], key=lambda x: (x['seed'], x['rank'])):
            p_str = f"{m['pair'][0]}|{m['pair'][1]}"
            profit_str = f"{int(m['aaa_info']['profit']):,} £"
            lines.append(f"{m['seed']:<6} {p_str:<12} {m['type']:<10} {m['reason']:<8} {m['rank']:<6} {m['score']:<10.1f} {m['top']:<10.1f} {profit_str:<12}")
    return "\n".join(lines)


def run_selftest():
    """Auto-test unitaire du parseur."""
    sample_logs = [
        "OPEX 1970-1-15 AIR_TOWN_SERVED scan=0 town_id=2 town_tile=24869 lines_state=empty",
        "OPEX 1970-1-15 AIR_TOWN_SERVED scan=0 town_id=30 town_tile=48086 lines_state=empty",
        "OPEX 1970-1-15 AIR_TOWN_SERVED scan=0 town_id=11 town_tile=10926 lines_state=empty",
        "OPEX 1970-2-1 SELECT_REJECT pair=24869|48086 type=newpair reason=cash rank=0 score=4500.5 top=3200.0",
        "OPEX 1970-2-1 SELECT_REJECT pair=24869|10926 type=hubsite reason=floor rank=12 score=800.0 top=3200.0",
        "OPEX 1970-3-1 SELECT_REJECT pair=24869|48086 type=newpair reason=dedupe rank=1 score=3100.0 top=3200.0",
        "OPEX 1970-3-1 SELECT_REJECT pair=10926|48086 type=hubhub reason=topk rank=64 score=1200.0 top=3200.0",
    ]
    t2t = {24869: 2, 48086: 30, 10926: 11}
    records = parse_select_reject_lines(sample_logs, t2t)
    assert len(records) == 4, f"Attendu 4 enregistrements, recu {len(records)}"
    assert records[0]['town_pair'] == (2, 30)
    assert records[0]['reason'] == 'cash'
    assert records[0]['rank'] == 0
    assert records[1]['reason'] == 'floor'
    assert records[2]['reason'] == 'dedupe'
    assert records[3]['reason'] == 'topk'

    aaa_pairs = {
        0: {
            (2, 30): {'townA': 2, 'townB': 30, 'profit': 150000.0, 'vehicles': 2, 'cargo_types': ['0']},
        }
    }
    recs_by_seed = {0: records}
    analysis = cross_rejects_with_aaa(recs_by_seed, aaa_pairs)
    assert analysis['total_rejects'] == 4
    assert analysis['reasons']['cash'] == 1
    assert analysis['reasons']['floor'] == 1
    assert analysis['reasons']['dedupe'] == 1
    assert analysis['reasons']['topk'] == 1
    assert analysis['aaa_matched_count'] == 1
    assert len(analysis['matches']) == 2  # (2, 30) apparait deux fois (cash puis dedupe)
    report = format_report(analysis)
    assert "cash" in report
    assert "2|30" in report
    print("Selftest parse_select_reject OK.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Parseur SELECT_REJECT et croisement AAA.")
    parser.add_argument('--log', default=None, help="Chemin ou motif glob vers les logs moteur.")
    parser.add_argument('--results', default=None, help="Chemin vers le fichier results.json de la campagne.")
    parser.add_argument('--selftest', action='store_true', help="Execute les tests internes.")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        return

    log_pattern = args.log or 'results/*_engine/*.log'
    log_files = sorted(glob.glob(log_pattern))
    if not log_files:
        print(f"Aucun log trouve pour le motif : {log_pattern}")
        return

    tile2town = extract_town_map_from_logs(log_files)
    records_by_seed, _ = parse_select_reject_logs(log_files, tile2town)

    results_file = args.results
    if not results_file:
        candidates = sorted(glob.glob('results/*.json'))
        if candidates:
            results_file = candidates[-1]

    aaa_pairs = load_aaa_air_pairs_from_json(results_file) if results_file else {}
    analysis = cross_rejects_with_aaa(records_by_seed, aaa_pairs)
    print(format_report(analysis))


if __name__ == '__main__':
    main()
