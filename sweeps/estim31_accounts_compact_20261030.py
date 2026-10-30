"""Compact independently read posted OpenTTD expenses from archived saves.

Reports ACTUAL net account postings, not project estimates, quotations,
AIAccounting probes, cash residuals or gross purchases. Post-process only;
does not alter AI opcodes or executable simulation source. The full archive
remains in results; never mistake net vehicle purchases-minus-sales as capex
by engine or mode.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from sweeps.estim31_real_accounts_from_saves_20261030 import analyze, NAMES


def compact(data):
    rows = data['period_records']
    by_year = defaultdict(list)
    observed = defaultdict(int)
    for row in rows:
        if row['company'] == 'OpexAI':
            for eng in ('223', '228'):
                observed[(row['policy'], row['accounting_year'], eng)] += row.get(
                    'physical_new_vehicle_ids_at_checkpoint', {}
                ).get('air:engine=' + eng, 0)
        if (row['checkpoint_date'] == f"{row['accounting_year']}-12-01"):
            by_year[(row['policy'], row['company'], row['accounting_year'])].append(row)
    years = {}
    for (policy, company, year), lines in sorted(by_year.items()):
        if len(lines) != 40:
            raise ValueError(f'Expected exactly forty snapshots: {policy} {company} {year}')
        years[f'{year}:{policy}:{company}'] = {
            name: mean(a['ytd_net_by_category'][name] for a in lines) for name in NAMES
        }
    return dict(campaign=data['campaign'],
                source_manifest=data['source_manifest'],
                source_archive=data['source_archive'],
                games=data['games'],
                checkpoints=data['checkpoints'],
                cutoff=data['cutoff'],
                posted_net_expenses_1974_by_policy_company=data['summary_means_40'],
                yearly_dec1_ytd_net_account_means_40=years,
                physically_observed_minimum_air_entry_ids={
                    f'{year}:{policy}:engine={eng}': count
                    for (policy, year, eng), count in sorted(observed.items())
                },
                limitations=(
                    'OpenTTD PLYR net postings, not AIAccounting/quotes/residual cash. '
                    'Construction all modes, vehicles purchases minus sales across modes. '
                    'Other includes statues plus other items. Monthly physical new IDs are '
                    'minimum surviving entrants, not exhaustive gross acquisitions. '
                    'Cutoff 1974-12-01 excludes unfinished December.'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--campaign', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = compact(analyze(args.bundle.resolve(), args.campaign))
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n',
                           encoding='utf-8')
    print('ACCOUNTS_COMPACT', result['campaign'], result['games'],
          result['checkpoints'], 'yearly groups', len(result['yearly_dec1_ytd_net_account_means_40']))


if __name__ == '__main__':
    main()
