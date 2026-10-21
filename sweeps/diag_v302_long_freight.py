"""Read existing decision logs; no engine invocation, standard library only.

Counts are events, not independent candidates. Missing upstream distance bins
and uninstrumented search-slot durations remain unknown. Each row cites its log.
"""
import argparse
from collections import Counter, defaultdict
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import re


def fields(text):
    return dict(re.findall(r"(\w+)=(\S+)", text))


def day(text):
    match = re.search(r"(?:OPEX )?(\d{4})-(\d{1,2})-(\d{1,2})", text.split("[I]")[-1])
    return date(*map(int, match.groups())) if match else None


def read_log(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as stream:
        return stream.readlines()


def analyze(path, width=256):
    chosen = {}
    attempts, selections, discards, aaa, mechanisms = [], [], [], [], []
    aaa_first_trains = []
    totals = Counter()
    rejects = Counter()
    events = Counter()
    for number, line in enumerate(read_log(path), 1):
        citation = f'{path}:{number}'
        if '[0]' in line and 'OPEX ' in line:
            match = re.search(r'OPEX \S+ (\w+) ', line)
            if not match:
                continue
            event = match[1]
            events[event] += 1
            row = fields(line)
            row.update(citation=citation, date=day(line).isoformat())
            if event == 'V302_JOIN':
                mechanisms.append(row)
            if event == 'VIVIER_GEN' and row.get('mode') == 'rail':
                totals.update({k: int(row[k]) for k in ('produced', 'kept')})
            if event == 'VIVIER_REJECT':
                rejects[row['reason']] += int(row['n'])
            if event == 'PROJECT_CHOSEN' and row.get('mode') == 'rail':
                chosen[(row['src'], row['dst'])] = row
                if row.get('kind') == 'freight' and int(row['dist']) > 160:
                    selections.append(row)
            if event == 'PROJECT_DISCARD' and row.get('mode') == 'rail':
                a, b = int(row['src']), int(row['dst'])
                distance = abs(a % width-b % width)+abs(a // width-b // width)
                if distance > 160:
                    row['manhattan'] = distance
                    row['kind'] = None  # no cargo/kind in this event
                    discards.append(row)
            if event == 'RAIL_ATTEMPT' and row.get('kind') == 'freight' and int(row['manh']) > 160:
                selection = chosen.pop((row['src'], row['dst']), None)
                row['cargo'] = selection.get('cargo') if selection else None
                row['selection_citation'] = selection['citation'] if selection else None
                row['selection_to_result_days'] = (day(line)-date.fromisoformat(selection['date'])).days if selection else None
                row['search_slot_days'] = None  # decision_log alone does not emit C56 dates
                attempts.append(row)
        if '[1]' in line:
            service = re.search(r'TrainRoute pathDistance:(\d+) distance:(\d+) (.*)', line)
            if service and int(service[2]) > 160 and not re.search(r'\[(Passengers|Mail)\]Rail', service[3]):
                aaa_first_trains.append(dict(date=day(line).isoformat(), citation=citation,
                                            station_manhattan=int(service[2]), route=service[3].strip(),
                                            first_train_built=True, terminal_trains=None))
            match = re.search(r'# RouteBuilder (Succeeded|Failed) 0 (\d+) (\d+) Build RailRoute (.*)', line)
            if match and int(match[3]) > 160 and not match[4].endswith((' Passengers', ' Mail')):
                aaa.append(dict(status=match[1], days=int(match[2]), manhattan=int(match[3]),
                                route=match[4].strip(), date=day(line).isoformat(), citation=citation,
                                trains_in_service=None))
    return dict(file=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                long_generated=None, long_in_pool=None, long_portfolio_selected=None,
                rail_generation_events=dict(totals), rejection_events_all_distances=dict(rejects),
                event_counts=dict(events), selections=selections, attempts=attempts,
                long_rail_discards_kind_unknown=discards, aaa=aaa, aaa_first_trains=aaa_first_trains,
                mechanisms=mechanisms, unfinished_choices=[r for r in chosen.values()
                    if r.get('kind') == 'freight' and int(r['dist']) > 160])


def terminal_services(result, width=256):
    """Consume the existing harness decoder, never count raw VEHS records.

    Cargo IDs 0/2 are PASS/MAIL only for the frozen temperate vanilla campaign.
    Multi-cargo trains remain freight if they also carry any non-passenger cargo.
    """
    snapshots = (result.get('line_telemetry') or {}).get('snapshots', [])
    unique = {}
    for snapshot in snapshots:
        key = (snapshot['duel_policy_id'], snapshot['arm'], snapshot['seed'], snapshot['repeat'], snapshot['date'])
        if key in unique and unique[key] != snapshot:
            raise ValueError(f'Conflicting snapshot {key}')
        unique[key] = snapshot
    latest = {}
    for key, snapshot in unique.items():
        group = key[:-1]
        if group not in latest or snapshot['date'] > latest[group]['date']:
            latest[group] = snapshot
    out = []
    for snapshot in latest.values():
        lines, unknown = [], []
        for line in snapshot['lines']:
            if line['mode'] != 'rail':
                continue
            cargos = line.get('capacity_by_cargo')
            if cargos is None:
                unknown.append(line['line_key_local'])
                continue
            if not any(str(c) not in ('0', '2') and n > 0 for c, n in cargos.items()):
                continue
            tiles = line.get('ordered_station_tiles', [])
            if len(tiles) != 2 or any(t is None for t in tiles):
                unknown.append(line['line_key_local'])
                continue
            a, b = tiles
            distance = abs(a % width-b % width)+abs(a // width-b // width)
            if distance > 160:
                lines.append(dict(line, manhattan=distance))
        out.append(dict(policy=snapshot['duel_policy_id'], arm=snapshot['arm'], seed=snapshot['seed'],
                        repeat=snapshot['repeat'], date=snapshot['date'], ok=snapshot['ok'],
                        unresolved_vehicles=snapshot.get('unresolved_vehicles'), unknown_lines=unknown,
                        lines=lines, trains=sum(l['vehicles'] for l in lines)))
    return out


def summary(files):
    groups = defaultdict(list)
    for item in files:
        groups[Path(item['file']).name.split('_seed')[0]].append(item)
    out = {}
    for arm, items in groups.items():
        rows = [r for i in items for r in i['attempts']]
        reasons = {}
        for reason in sorted({r['reason'] for r in rows}):
            subset = [r for r in rows if r['reason'] == reason]
            reasons[reason] = dict(n=len(subset), ops=sum(int(r['ops']) for r in subset),
                                  selection_to_result_days=sum(r['selection_to_result_days'] or 0 for r in subset),
                                  days_missing=sum(r['selection_to_result_days'] is None for r in subset))
        out[arm] = dict(attempts=len(rows), reasons=reasons,
                        chosen=sum(len(i['selections']) for i in items),
                        unique_pairs=len({(Path(i['file']).name, r['src'], r['dst'], r['cargo']) for i in items for r in i['attempts']}),
                        aaa=dict(Counter(r['status'] for i in items for r in i['aaa'])))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine_dirs', nargs='+', type=Path)
    parser.add_argument('--width', type=int, default=256)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--result', type=Path, help='Optional harness JSON with terminal line telemetry (temperate vanilla)')
    args = parser.parse_args()
    result = {}
    for directory in args.engine_dirs:
        paths = sorted(directory.glob('*.log')) + sorted(directory.glob('*.log.gz'))
        if not paths:
            parser.error(f'No logs in {directory}')
        if len({p.name.removesuffix('.gz') for p in paths}) != len(paths):
            parser.error('Duplicate plain/gzip log: select one representation')
        files = [analyze(path, args.width) for path in paths]
        result[directory.name] = dict(files=files, summary=summary(files))
    if args.result:
        with (gzip.open if str(args.result).endswith('.gz') else open)(args.result, 'rt', encoding='utf-8') as stream:
            campaign = json.load(stream)
        result['campaign'] = dict(source=str(args.result),
                                  sha256=hashlib.sha256(args.result.read_bytes()).hexdigest(),
                                  failed_runs=campaign['failed_runs'],
                                  comparison=campaign['policy_comparison'],
                                  terminal_services=terminal_services(campaign, args.width))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    for name, data in result.items():
        if 'summary' in data:
            print(name, json.dumps(data['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
