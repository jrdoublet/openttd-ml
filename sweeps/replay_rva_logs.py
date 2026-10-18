"""Replay all recoverable V216 snapshots; archive incompleteness explicitly."""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

from analyze_v216 import parse_log
from rva_replay import logged_snapshot, select


def replay_directory(directory):
    directory = Path(directory)
    campaign = directory.name.removesuffix('_engine')
    manifest_path = directory.parent/(campaign+'.manifest.json')
    manifest = json.loads(manifest_path.read_text())
    bundle = directory.parent/(campaign+'_bundle.tar.gz')
    with tarfile.open(bundle) as archive:
        name=next(n for n in archive.getnames() if n.endswith('/ai/OpexAI/settings.nut'))
        settings=archive.extractfile(name).read().decode('utf-8')
    if 'PORTFOLIO_FLOOR_PCT = 0;' not in settings:
        raise ValueError('Cannot infer historical floor: inspect frozen settings')
    counts=collections.Counter();sources=[];examples=[]
    for path in sorted(directory.glob('*.log*')):
        policy=path.name.split('_seed')[0]
        settings_row=next(p['settings']['effective'] for p in manifest['policies'] if p['id']==policy)
        limit=settings_row['project_top_k']
        game=parse_log(path)
        sources.append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        for seq,selection in game['select'].items():
            counts['snapshots']+=1
            rows=game['decomp'].get(seq,[])
            snapshot=logged_snapshot(selection,rows,0,limit)
            result=select(snapshot)
            if result['status']=='not_covered':
                counts['incomplete_snapshot']+=1
                counts[result['reason']]+=1
                continue
            counts['complete_post_fit_snapshot']+=1
            logged_top = selection.get('top_key')
            if logged_top == 'none':
                logged_top = None
            match=result['selected']==logged_top
            counts['baseline_top_reproduced' if match else 'baseline_top_mismatch']+=1
            # A real, later successful build is a separate observed fact. Only
            # link a unique following built row before the NEXT selection.
            next_seq=min((s for s in game['select'] if s>seq),default=float('inf'))
            built=[r for r in game['built'] if seq<r['seq']<next_seq]
            matching=[r for r in built if r.get('key')==result['selected']]
            if len(matching)==1:
                counts['selected_key_linked_to_later_build']+=1
            # Store all covered snapshots: reviewer can inspect mismatch rather
            # than accepting only favourable examples.
            examples.append({'source':path.name,'seq':seq,'logged_top':logged_top,
                             'snapshot':snapshot,'replay':result,
                             'observed_build_key':matching[0]['key'] if len(matching)==1 else None})
    return {'campaign':campaign,'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            'bundle_archive_sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),
            'counts':dict(counts),'sources':sources,'covered_snapshots':examples,
            'executed_variant_purchase_changes':None,
            'limitation':'old_logs_lack_full_generation_admission_and_live_command_counterfactual'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directories',nargs='+',type=Path)
    p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    a.out.write_text(json.dumps({'schema':1,'campaigns':[replay_directory(d) for d in a.directories]},indent=2)+'\n')
