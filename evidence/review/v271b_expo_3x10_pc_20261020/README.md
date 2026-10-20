# V271b benchmark — archived evidence

Campaign: `v271b_expo_3x10_pc_20261020` (20 October 2026).

Files are archived with their original `results/...` source paths and SHA-256 digests in `index.json`.
- The final JSON and manifest are stored uncompressed.
- Monthly JSONL data and all six engine logs are gzip-compressed (deterministic gzip header; `mtime=0`).
- Source bundle and vendored AAAHogEx code are **not** published.

For verification, decompress each `.gz`, compute SHA-256 over the original bytes and compare to `raw_sha256` in the index. Use `archive_sha256` to verify the committed file directly.

See `docs/v271b_expo_3x10_pc_20261020.md` for the comparison and its diagnostic-only verdict. The V271 decision-event log was **not** enabled; absence of `V271` events in engine logs is not proof of zero exposure.