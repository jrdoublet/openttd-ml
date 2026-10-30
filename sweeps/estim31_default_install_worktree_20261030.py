"""Install a verified winner release into a clean, ISOLATED Git worktree.

Never touch the dirty shared master or an existing modified target. Copies
the complete tested OpexAI source set so dependent EB14/PO01C/feeder modules
do not silently disappear. Does not commit, push or alter branches.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(target, *args):
    return subprocess.run(['git', '-C', str(target), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def install(release, target):
    release = release.resolve()
    target = target.resolve()
    if target == release or target in release.parents or release in target.parents:
        raise ValueError('Do not install inside or over the source release')
    manifest = json.loads((release / 'release_manifest.json').read_text('utf-8'))
    if not manifest.get('deployable_source_ready') or manifest.get('production_ai_updated'):
        raise ValueError('Source release not sealed for an isolated promotion')
    if Path(git(target, 'rev-parse', '--show-toplevel')).resolve() != target:
        raise ValueError('Target must be a Git worktree root')
    if git(target, 'branch', '--show-current') in ('master', 'main'):
        raise ValueError('Never overwrite shared master/main checkout')
    # Avoid overwriting even a single concurrent edit, including untracked files.
    if git(target, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('Install target must be fully clean')
    source = release / 'ai/OpexAI'
    destination = target / 'ai/OpexAI'
    src = {p.relative_to(source).as_posix(): sha(p)
           for p in source.rglob('*') if p.is_file()}
    dst = {p.relative_to(destination).as_posix(): sha(p)
           for p in destination.rglob('*') if p.is_file()}
    if not set(dst).issubset(src):
        raise ValueError('Target has AI files absent from the frozen winner')
    if len(src) != manifest['opexai_file_count']:
        raise ValueError('Release OpexAI source file count mismatch')
    if sha(source / 'info.nut') != manifest['release_info_sha256']:
        raise ValueError('Release default settings were modified')
    # The sealed source is a self-contained AI with its own dependency files.
    for name in sorted(src):
        original = source / name
        copied = destination / name
        copied.parent.mkdir(parents=True, exist_ok=True)
        if not copied.exists() or sha(copied) != sha(original):
            shutil.copy2(original, copied)
    after = {p.relative_to(destination).as_posix(): sha(p)
             for p in destination.rglob('*') if p.is_file()}
    if after != src:
        raise ValueError('Installed AI does not byte-match default release')
    changed = sorted(name for name in src if dst.get(name) != src[name])
    return {'branch': git(target, 'branch', '--show-current'),
            'release_winner': manifest['winner'],
            'files_changed': changed,
            'files_changed_count': len(changed),
            'ai_source_sha_verified': True,
            'deployed_to_shared_master': False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--release', type=Path, required=True)
    ap.add_argument('--target-worktree', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    status = install(args.release, args.target_worktree)
    args.output.write_text(json.dumps(status, indent=2) + '\n', 'utf-8')
    print('ISOLATED_DEFAULT_INSTALLED', status['branch'],
          'updated_files=', status['files_changed_count'],
          'shared_master_unchanged=True')


if __name__ == '__main__':
    main()
