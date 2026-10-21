"""PO01C log measurements, no engine imports. Durations are game days."""
import re
from datetime import date


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
    return {'published': batches, 'published_count': len(batches),
            'slice_count': len(slices),
            'slice_ops': sum(int(r['ops']) for r in slices),
            'max_slice_ops': max((int(r['ops']) for r in slices), default=None),
            'max_slice_days': max((int(r['days']) for r in slices), default=None),
            'freezes_over_5_days': sum(int(r['days']) > 5 for r in slices + sync),
            'synchronous_reactive': sync,
            'script_errors': text.count('[0] [S] Your script made an error')}
