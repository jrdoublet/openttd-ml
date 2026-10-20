# Preuves V277 + V279 — banc PC du 20/10/2026

Archive ciblée du smoke et du duel apparié 20×10, exécutés depuis `fb6b9ebe`.
Quatre fichiers sources de `results/` sont compressés sans altérer leurs octets :
les JSON finaux et leurs manifestes. `index.json` en conserve les chemins d'origine,
les tailles et les SHA-256 des données brutes et de chaque archive gzip.

Recréer le paquet avec les fichiers sources locaux :

```text
python -X utf8 evidence/review/v277v279_20261020/build.py
```

Vérifier les archives et les principaux critères du verdict :

```text
python -X utf8 evidence/review/v277v279_20261020/verify.py
```

Les JSONL, les journaux moteur complets et le bundle source restent locaux.
L'index global historique `evidence/review/index.json` n'est pas modifié :
cette archive est autonome. [Rapport de mesure](../../../docs/v277v279_porteB_20x10_pc_20261020.md).
