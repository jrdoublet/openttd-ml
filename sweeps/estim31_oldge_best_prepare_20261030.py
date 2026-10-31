"""Freeze a private read-only source copy of the concurrent best 5×5.

Used only as a historical GE-shortcut comparator; its certification under
the stricter all-engine ESTIM requirement is explicitly unresolved.
"""
import hashlib
import json
import shutil
from pathlib import Path

from sweeps.estim31_joint_next_prepare import REPO

BASE=REPO/'results/estim31_joint_newgrid20261030/a200_r150_w05_flat_load25'
DEST=REPO/'results/estim31_oldge_best_40x5_20261030'

def prepare():
    if DEST.exists():
        raise FileExistsError(f'No overwrite: {DEST}')
    for tree in ('ai','ai_libraries','sweeps'):
        shutil.copytree(BASE/tree,DEST/tree)
    for filename in ('Dockerfile','requirements.txt','requirements-ml.txt','design.json'):
        shutil.copy2(BASE/filename,DEST/filename)
    # Unlike the safe module, concurrent newgrid embedded the experimental
    # FullScan functions at the end of air_economics_c121.nut itself.
    files=('air_economics_c121.nut','globals_pre.nut','settings.nut','info.nut')
    for fn in files:
        a,b=BASE/'ai/OpexAI'/fn,DEST/'ai/OpexAI'/fn
        if a.read_bytes()!=b.read_bytes():
            raise ValueError(f'Source changed in copy: {fn}')
    manifesto = json.loads((BASE/'results/grid31_a200_r150_w05_flat_load25_5x5_20261030.manifest.json').read_text('utf-8'))
    report=dict(source_campaign=manifesto['campaign_id'],
                original_source=str(BASE),
                original_manifest=str(BASE/'results/grid31_a200_r150_w05_flat_load25_5x5_20261030.manifest.json'),
                image_id=manifesto['runtime']['docker_image_id'],
                options=manifesto['execution']['options'],
                source_sha256={fn:hashlib.sha256((DEST/'ai/OpexAI'/fn).read_bytes()).hexdigest() for fn in files},
                certification_note=('C121_GE ESTIM shortcut not proven exact; '+
                    'FullScan functions embedded in historical source module; '
                    '40x5 serves as diagnostic benchmark only'))
    (DEST/'copy_provenance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('PREPARED_OLD_GE', DEST)

if __name__=='__main__':
    prepare()
