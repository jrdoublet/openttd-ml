"""Verify archived parameter-cleanup evidence, without Docker or results/."""
from pathlib import Path
import json, gzip, hashlib

root=Path(__file__).resolve().parent
data=json.loads((root/'index.json').read_text(encoding='utf-8'))
for item in data['artifacts']:
    compressed=(root/item['archive']).read_bytes()
    assert len(compressed)==item['gzip_bytes'],item['archive']
    assert hashlib.sha256(compressed).hexdigest()==item['gzip_sha256'],item['archive']
    raw=gzip.decompress(compressed)
    assert len(raw)==item['raw_bytes'],item['source']
    assert hashlib.sha256(raw).hexdigest()==item['raw_sha256'],item['source']
print(f"Verified {len(data['artifacts'])} artifacts (gzip and raw SHA-256)")
