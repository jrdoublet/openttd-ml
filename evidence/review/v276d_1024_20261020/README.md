# Pièces de preuve — V276d / 1024² / 2026-10-20

Rapport de validation : `docs/v276d_validation_1024_20261020.md`.

Contenu : 6 couples `campagne.json` + `campagne.manifest.json` (modes 0, 1 et 2 ; graine 42 isolée, puis 7/100/999) et les 12 journaux du moteur OpenTTD, compressés individuellement au format `.log.gz`.

Conventions des journaux : `<campagne>__reference_seed<N>_r0.log.gz`. Compression seulement, sans filtre ; les originaux non compressés restent dans les `results/..._engine` locaux, hors Git. Le `.jsonl` de checkpoints n'est pas publié car les synthèses et les archives de log sont conservées.

Lire un journal : `python -m gzip -d` ou `gzip -cd fichier.log.gz`. Vérifier le paramètre `configuration.map_size=10` dans chaque manifeste et les messages `OPEX 1970-...` en excluant `V262_SAVE` pour détecter le gel de la boucle IA.

Tous les duels ont été lancés sur `dc44958f4ff547ca090d32297b7c68907272596f`. Aucun essai à 256² n'a été archivé ici.
