# Review evidence

The benchmark working directory `results/` remains ignored because it contains
large transient engine output.  The JSON artifacts actually cited by the code
review are preserved here as deterministic gzip copies.

`index.json` records, for each artifact, the original `results/...` path, the
raw byte count and SHA-256, and the committed gzip byte count and SHA-256.
Therefore an archived file can be checked byte-for-byte after decompression.

Regenerate the package from a workspace containing the cited `results/*.json`:

```text
python sweeps/package_review_evidence.py
```

Verify one artifact with Python:

```text
python -c "import gzip,hashlib; p='evidence/review/review_g0_c66_4_20x10.json.gz'; b=gzip.open(p,'rb').read(); print(hashlib.sha256(b).hexdigest())"
```

Compare the printed hash with the corresponding `raw_sha256` in `index.json`.
