# Town growth OFF — preuves du 2 octobre 2026

[Fiche et plan pré-enregistré](../../../docs/town_growth_off_20261002.md).
[Résumé compact](summary.json), [résumé détaillé archivé](results/town_growth_off_20261002_summary.json.gz),
[index des archives](index.json).

Le packager courant `sweeps/package_review_evidence.py` a été appelé avec
`--write` sur une racine temporaire ne contenant que les douze entrées TG
énumérées. Après déplacement, les chemins d'index ont été ajustés et les hashes
bruts/gzip et les tailles décompressées revérifiés. L'index historique global
reste inchangé ; ce paquet ne prétend pas couvrir ses citations manquantes.

Les trois campagnes retenues utilisent le même SHA `1f07b4e` et le même bundle
`c8d11b37ef893831711d713315793eee35de85a545dd031c90c37da3046b2552`.
Les JSON et manifestes bruts, les audits dérivés et le smoke sont archivés ici.
La tentative diagnostic `r1` échouée à la collecte conserve son manifeste ;
elle n'a aucun résultat ni verdict économique.

JSONL, journaux moteur et bundles demeurent dans les dossiers locaux `results/` ;
leurs hashes et les fingerprints détaillés des sources sont dans le résumé.
Pour C121, le JSONL contient 9598/9600 lignes : deux checkpoints intermédiaires
AAAHogEx de la graine 8675309 manquent (référence 1972-02-01, OFF 1972-12-01).
Les retours moteur ont 120 observations par compagnie, les rapports finaux
20/20 paires complètes et quatre trimestres valides. Aucune ligne manquante
n'a été reconstruite ; cette limite d'archive est distincte de la couverture
du primaire final. Aucun défaut n'a changé.
