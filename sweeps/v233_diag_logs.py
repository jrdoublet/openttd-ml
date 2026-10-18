"""Offline V233 exposure audit. Reads logs only; never imports an engine harness.

AIR counterfactual: last *visible* priced AIR portfolio observation, without
lookahead (B6 actual_profit/actual_cap or PORTFOLIO_RANK profit/finance_capital).
This proxy cannot reconstruct the full live AIR opportunity set. AIR_BUILD
profit/cost gives two separate, uncalibrated sensitivity checks.
"""
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re


def events(path):
    rows = []
    with Path(path).open(encoding="utf-8", errors="strict") as stream:
        for number, line in enumerate(stream, 1):
            match = re.search(r'\[0\].*?OPEX (\d+-\d+-\d+) (\S+) (.*)', line)
            if match is None:
                continue
            stamp = date(*map(int, match[1].split('-')))
            row = dict(re.findall(r'(\w+)=([^ ]+)', match[3]))
            row.update(_line=number, _date=stamp.isoformat(),
                       _day=stamp.toordinal(), _event=match[2])
            rows.append(row)
    return rows


def ratio(row, numerator, denominator):
    if numerator not in row or denominator not in row:
        return None
    capital = float(row[denominator])
    return float(row[numerator]) / capital if capital > 0 else None


def audit(rows):
    counts = Counter()
    last_model = best_model = last_build = best_build = preceding_yield = None
    candidates = []
    for row in rows:
        event = row['_event']
        if event == 'B6_PORTFOLIO' and row.get('actual_mode') == 'air':
            value = ratio(row, 'actual_profit', 'actual_cap')
            if value is not None:
                last_model = (value, row)
        if event == 'PORTFOLIO_RANK' and row.get('mode') == 'air':
            value = ratio(row, 'profit', 'finance_capital')
            if value is not None:
                last_model = (value, row)
        if last_model is not None and (best_model is None or last_model[0] > best_model[0]):
            best_model = last_model
        if event == 'AIR_BUILD':
            value = ratio(row, 'profit', 'cost')
            if value is not None:
                last_build = (value, row)
                if best_build is None or value > best_build[0]:
                    best_build = last_build
        if event == 'V233_YIELD':
            preceding_yield = row
        if event != 'V233_CHAIN' or row.get('state') != 'candidate':
            continue
        if preceding_yield is None or preceding_yield['factory'] != row['factory']:
            raise ValueError('Candidate without matching AIR admission')
        counts['candidates'] += 1
        counts['allowed'] += row['allowed'] == 'true'
        record = dict(candidate=row, admission=preceding_yield)
        unknown = preceding_yield['air_yield'] == 'unknown'
        counts['unknown'] += unknown
        if unknown:
            for name, alternative in [('last_model', last_model), ('best_model', best_model),
                                      ('last_build', last_build), ('best_build', best_build)]:
                counts[name + '_covered'] += alternative is not None
                passed = None if alternative is None else float(row['yield']) >= alternative[0]
                counts[name + '_passes'] += passed is True
                record[name] = None if alternative is None else dict(
                    rate=alternative[0], passed=passed, evidence=alternative[1])
        if row['allowed'] == 'true':
            # Hints only: a single input's capital is not a unique route ID.
            window = [e for e in rows if e['_line'] > row['_line']
                      and e['_day'] < row['_day'] + 90]
            record['input_yield_checks'] = [e for e in window
                if e['_event'] == 'V233_YIELD' and e['factory'] == row['factory']
                and e['cargo'] != preceding_yield['cargo']]
            record['capital_rank_hints'] = [e for e in window
                if row['inputs'] == '1' and e['_event'] == 'PORTFOLIO_RANK'
                and e.get('mode') == 'rail' and e.get('cargo') in ('GRAI', 'LVST', 'STEL')
                and abs(float(e['finance_capital']) - float(row['input_capital'])) < 1]
            budgets = [int(e['live_budget']) for e in window if e['_event'] == 'B6_PORTFOLIO']
            record['available_capital_range_90d'] = [min(budgets), max(budgets)] if budgets else None
        if unknown or row['allowed'] == 'true':
            candidates.append(record)
    return dict(counts=dict(counts), candidates=candidates)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log_dir', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('Output already exists; choose a new path')
    output = {}
    for path in sorted(args.log_dir.glob('*mode5_seed*_r0.log')):
        seed = re.search(r'seed(\d+)_r0', path.name)[1]
        output[seed] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            **audit(events(path)))
    if not output:
        parser.error('No mode 5 logs found')
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(output, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
