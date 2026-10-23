"""PO01C log measurements, no engine imports. Durations are game days."""
import re
import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from statistics import median


def events(text, tag):
    result = []
    for line in text.splitlines():
        m = re.search(r'\[0\] \[I\] OPEX (\d+)-(\d+)-(\d+) ' + tag + r' (.*)', line)
        if m:
            row = dict(re.findall(r'(\w+)=([^ ]*)', m[4]))
            row['date'] = date(*map(int, m.group(1, 2, 3))).isoformat()
            result.append(row)
    return result


def pending_save_dates(text):
    return {r['date'] for r in events(text, 'PO01C_BATCH') if r.get('phase') == 'save_pending'}


def summarize(text):
    batches = [r for r in events(text, 'PO01C_BATCH') if r.get('phase') == 'publish']
    slices = events(text, 'PO01C_SLICE')
    sync = [r for r in events(text, 'PO01C_SYNC') if r.get('reason') == 'reactive']
    return {'units': summarize_units(text),
            'published': batches, 'published_count': len(batches),
            'slice_count': len(slices),
            'slice_ops': sum(int(r['ops']) for r in slices),
            'max_slice_ops': max((int(r['ops']) for r in slices), default=None),
            'max_slice_days': max((int(r['days']) for r in slices), default=None),
            'freezes_over_5_days': sum(int(r['days']) > 5 for r in slices + sync),
            'synchronous_reactive': sync,
            'script_errors': text.count('[0] [S] Your script made an error')}


def summarize_units(text):
    """Only logged maxima above the slice budget, NOT all resumes/population."""
    groups = {}
    for row in events(text, 'PO01C_UNIT'):
        key = (row['mode'], row['gen'], row['site'])
        groups.setdefault(key, []).append(int(row['ops']))
    return [dict(mode=key[0], gen=key[1], site=key[2], count=len(values),
                 ops_max=max(values), ops_median=median(values))
            for key, values in sorted(groups.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine_dir', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    records = {}
    for path in sorted(args.engine_dir.glob('*.log')):
        raw = path.read_bytes()
        text = raw.decode('utf-8')
        record = summarize(text)
        record['sha256'] = hashlib.sha256(raw).hexdigest()
        record['bytes'] = len(raw)
        rejects = [int(r['n']) for r in events(text, 'VIVIER_REJECT')
                   if r.get('reason') == 'origin_served']
        record['origin_served_events'] = len(rejects)
        record['origin_served_rejections'] = sum(rejects)
        records[path.name] = record
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
