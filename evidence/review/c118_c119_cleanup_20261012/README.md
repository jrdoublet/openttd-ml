# C118/C119 — preuves techniques du retrait

Complément de fusion : cinq artefacts ajoutés pour `dd826d6` avec V157/V158/V160 à1. L'index contient40 archives vérifiées ;247 contrats et un smoke défauts42×1 sain. Voir `docs/c118_c119_merge_preparation_20261012.md`. Aucun effet économique du cumul qualifié.

Archive bornée des trois smokes, manifestes, logs, audits et copies avant retrait. Les JSONL et bundles complets restent locaux dans `results/`. Aucun gain économique ni d opcodes qualifié.

`index.json` associe chaque chemin original aux octets bruts et gzip, tailles et SHA-256. Toutes les archives ont été redécompressées et comparées aux sources. Le script `sweeps/package_review_evidence.py` fournit les primitives de compression/hash ; cet index local ne remplace pas l index historique global.

Les rapports `docs/c119_air_income_retrait_20261012.md` et `docs/c118_territorial_retrait_20261012.md` détaillent les protocoles et limites.
