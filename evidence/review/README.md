# Review evidence

The benchmark working directory `results/` remains ignored because it contains
large transient engine output. The existing package is a **historical snapshot**,
not exhaustive coverage of current documentation. Its old `missing: []` applies
only to citations recognized when it was produced, not to recent C115/C119/C121/C122
results. Archive integrity and current citation coverage are separate checks.

`index.json` records, for each artifact, the original `results/...` path, the
raw byte count and SHA-256, and the committed gzip byte count and SHA-256.
Therefore an archived file can be checked byte-for-byte after decompression.

Audit citations without changing the package (the default):

```text
python sweeps/package_review_evidence.py
```

The audit scans root Markdown guides, all `docs/**/*.md` (including journals and
archives), and AI `AGENTS.md`/`CLAUDE.md` files, without campaign-prefix filtering.
It recognizes explicit `results/...json` paths, including JSON manifests, but not
bare campaign names, globs, JSONL logs or bundle directories. Historical references
are included for traceability, **not requalified as current performance evidence**.

`MISSING` means neither a local input nor a verified archive is available;
`PENDING` means a local input is not yet archived; `ERRORS` includes hash conflicts.
The exit code is 2 until coverage and integrity are complete, otherwise 0.
No missing result is reconstructed and no benchmark is launched.

Only when every cited input is available, explicitly request packaging:

```text
python sweeps/package_review_evidence.py --write
```

Existing indexed archives are hash-checked and retained even without local results.
A changed local result is a conflict, never a replacement for its archived proof.
Missing inputs or conflicts abort before writes; new paths preserve subdirectories
under `evidence/review/results/` to avoid basename collisions. The index records the
documents scanned. Writes are not a filesystem transaction: do not edit inputs or
run multiple packagers concurrently. The historical index was **not regenerated**
by the September 30 documentation correction; recent VPS artifacts remain needed.

Verify one artifact with Python:

```text
python -c "import gzip,hashlib; p='evidence/review/review_g0_c66_4_20x10.json.gz'; b=gzip.open(p,'rb').read(); print(hashlib.sha256(b).hexdigest())"
```

Compare the printed hash with the corresponding `raw_sha256` in `index.json`.
