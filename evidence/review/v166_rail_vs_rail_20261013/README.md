# V166 — rail contre rail, diagnostic du 13 octobre 2026

30 artefacts gzip et hashes dans `index.json`. Reproduction et limites :
[rapport](../../../docs/v166_rail_vs_rail_20x3_20261013.md).

Source `d00ba50`, bundle `4ac6f43d37298e53a7220abab2992f738eced09595960deed45a7bc876abb749`.
Smoke42×1 puis20×3 sains, un bras instrumenté Opex rail seul face à AAA rail seul.
Pas de comparaison de politiques, pas de qualification V102 ni de décision d'adoption.
19 paires terminales seulement pour la comparaison des services ; économie complète20/20.

Les archives réutilisent `gzip_deterministic`/`sha256` de
`sweeps/package_review_evidence.py`, avec vérification de chaque décompression.
Ne pas écraser une preuve existante avec une autre campagne.
