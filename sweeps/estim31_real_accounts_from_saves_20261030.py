"""Read OpenTTD's REAL posted category net accounts from retained autosaves.

This is a post-game, outside-AI decoder. Construction is all modes together;
NewVehicles is purchases minus proceeds of sales, all modes and replacements.
ExpensesType::Other includes town statues among other items. Never attribute
these accounting nets to a particular AIR/RAIL/statue/renew purchase.

Requires the optional frozen harness --retain-savegames archive. Filenames
are mapped through campaign manifest.games, not inferred from their labels.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

import openttdlab

NAMES=('construction_all_modes','new_vehicles_net_all_modes','train_running',
       'road_running','aircraft_running','ship_running','property',
       'train_revenue','road_vehicle_revenue','aircraft_revenue',
       'ship_revenue','loan_interest','other_including_town_actions')


def accounting_year(date_value):
    """Jan 1 save still displays closing preceding year in current slot."""
    return date_value.year-1 if date_value.month==1 else date_value.year


def read_sav(path):
    with path.open('rb') as f:
        game=openttdlab.parse_savegame(iter(lambda:f.read(65536),b''))
    chunks={key:value['records'] for key,value in game['chunks'].items()}
    day_index=int(chunks['DATE']['0']['date'])-366
    day=date(1,1,1)+timedelta(days=day_index)
    records=chunks['PLYR']
    result={}
    for key in ('0','1'):
        company=records.get(key) or records.get(int(key))
        if not isinstance(company,dict):
            continue
        values=company.get('yearly_expenses')
        if not isinstance(values,(list,tuple)) or len(values)!=39:
            raise ValueError(f'Expected 3x13 accounts in {path} slot {key}')
        result[key]=[int(v) for v in values[:13]]
    return day,result


def diff_accounts(checkpoints):
    """Compute period postings from company-specific cumulative fiscal totals.

    Cross-fiscal-year first value starts at zero, not previous December's YTD.
    Save dates are period END dates (typically first day of following month).
    """
    previous={}
    results=[]
    for row in sorted(checkpoints,key=lambda x:(x['game_index'],x['company'],x['date'])):
        key=(row['game_index'],row['company'],accounting_year(row['date']))
        prior=previous.get(key,[0]*len(NAMES))
        values=row['cumulative']
        if len(values)!=len(NAMES):
            raise ValueError('Unexpected account width')
        delta=[value-old for value,old in zip(values,prior)]
        previous[key]=values
        results.append(dict(game_index=row['game_index'],seed=row['seed'],
                            policy=row['policy'],company=row['company'],
                            checkpoint_date=row['date'].isoformat(),
                            accounting_year=accounting_year(row['date']),
                            postings_net_by_category=dict(zip(NAMES,delta)),
                            ytd_net_by_category=dict(zip(NAMES,values))))
    return results


def analyze(root,campaign):
    manifest_path=root/'results'/f'{campaign}.manifest.json'
    manifest=json.loads(manifest_path.read_text('utf-8'))
    archives=root/'results'/f'{campaign}_saves'
    games=manifest['games']
    if len(games)!=80:
        raise ValueError(f'Expected 40 seeds x 2 policy games, got {len(games)}')
    checkpoint=[]
    for i,game in enumerate(games):
        folder=archives/str(i)
        archive=json.loads((folder/'archive.json').read_text('utf-8'))
        items=archive['savegames']
        if len(items)<60:
            raise ValueError(f'Game {i} has only {len(items)} archived saves')
        for item in items:
            save=folder/item['path']
            digest=hashlib.sha256(save.read_bytes()).hexdigest()
            if digest!=item['sha256']:
                raise ValueError(f'Archive checksum mismatch: {save}')
            day,players=read_sav(save)
            for slot,company in (('0','OpexAI'),('1','AAAHogEx')):
                if slot not in players:
                    raise ValueError(f'Paired campaign {game["game_id"]} missing slot {slot}')
                checkpoint.append(dict(game_index=i,seed=game['seed'],
                       policy=game['policy_id'],company=company,date=day,
                       cumulative=players[slot]))
    records=diff_accounts(checkpoint)
    if len(records)!=len(checkpoint):
        raise ValueError('Accounting row count changed')
    # At the ranking cut-off, these are YTD posted real nets to 1974-12-01;
    # never describe them as full-year 1974 or gross purchases/expenses.
    final=[r for r in records if r['checkpoint_date']=='1974-12-01']
    groups=defaultdict(list)
    for row in final:
        groups[(row['policy'],row['company'])].append(row)
    summary={}
    for (policy,company),rows in sorted(groups.items()):
        if len(rows)!=40:
            raise ValueError(f'Expected 40 final accounts: {(policy,company)} has {len(rows)}')
        summary[f'{policy}:{company}']={k:mean(r['ytd_net_by_category'][k] for r in rows)
                                       for k in NAMES}
    return dict(campaign=campaign,source_manifest=str(manifest_path),
                source_archive=str(archives),category_names=NAMES,
                sign='positive=net costs, negative=net revenue/asset sale proceeds',
                attribution_limit=('Construction all modes combined; NewVehicles buys less sales all modes; '
                    'statues indistinguishable within Other; not a per-object cash ledger.'),
                cutoff='1974-12-01 (1974 YTD, excludes unfinished December)',
                games=len(games),checkpoints=len(checkpoint),
                summary_means_40=summary,period_records=records)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--campaign',required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    out=analyze(args.bundle.resolve(),args.campaign)
    args.out.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ACCOUNTING',args.campaign,'games',out['games'],'checkpoints',out['checkpoints'])
    print(json.dumps(out['summary_means_40'],indent=2))


if __name__=='__main__':
    main()
