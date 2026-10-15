# V216 — preuves du factoriel PC, 15 octobre 2026

F1 et F2, chacun précédé d'un smoke trois ans : 160/160 parties principales saines, 80/80 paires complètes et quatre parties de smoke saines. Diagnostics de contexte, sans qualification d'une politique ni interprétation des verdicts bruts comme adoption.

Les 25 archives gzip déterministes conservent les JSON finaux, manifestes, sorties du lanceur, rapports, script d'analyse fourni et scripts de restitution. `index.json` associe à chaque fichier son chemin d'origine, ses tailles et ses SHA-256 bruts et compressés. Taille compressée totale : environ 3,9 Mo.

Vérification indépendante des fichiers locaux de travail :

```text
python -X utf8 evidence/review/v216_factoriel_pc_20261015/verify.py
```

Le vérificateur contrôle les octets archivés, les empreintes des manifestes, le bundle commun, la santé, l'horizon et les quatre trimestres terminaux, les 40 graines communes et les ratios recalculés depuis les cohortes normalisées.

`v216_facto_pc_20261015.cohorts.json.gz` conserve, par journal moteur et bras, les lignes retenues par le script fourni, leurs valeurs prévues et réalisées annualisées, les constructions et les profits individuels des groupes de co-localisation. Chaque journal source est identifié par son nom et son SHA-256. Ces données permettent de recalculer les agrégats ; elles ne remplacent pas les journaux pour réexaminer l'extraction initiale.

Les journaux moteur complets, JSONL, sauvegardes, caches et bundles de sources restent locaux dans `results/`. Le présent paquet ne permet donc pas de relancer intégralement la simulation ou de réextraire tous les événements. Le script fourni est archivé sans modification ; son interprétation, ses limites et le passage du worktree au checkout principal sont documentés dans les rapports.

Ce paquet possède un index autonome, comme les autres publications ciblées du dépôt. L'index historique global `evidence/review/index.json` reste inchangé : son audit courant comporte des références manquantes ou non archivées sans rapport avec V216 ; il ne sert pas à valider ce paquet.

[Résultats des quatre cellules](../../../docs/v216_factoriel_pc_20261015.md) ; [bilan et passation](../../../docs/v216_factoriel_pc_20261015_suite.md).
