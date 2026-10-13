# Retrait de C116 — 13 octobre 2026

Décision utilisateur après analyse : supprimer `c116_air_marginal_capital` et nettoyer ses dépendances exclusives. Ancien défaut 0 ; C121 définitivement adopté court-circuitait déjà la substitution finale. Les rejets historiques restent inchangés ; ce retrait ne constitue aucune qualification économique.

Base `e8285c4`, branche `codex/c118-c119-merge-20261012`, checkout isolé `results/c118_c119_merge_stage_20261012`. Checkout principal et travaux P0 préservés. Aucun commit ni push demandé.

## Périmètre

- Déclaration, chargement et globale retirés ; gardes C115 et C69 simplifiées selon l'ancien état OFF.
- Quatre helpers exclusifs retirés : `OpexC116RouteFinanceCapital`, `OpexC116UnlockedProjectOpportunity`, `OpexC116BestPendingAirProject`, `OpexC116ChooseBuildPlan`.
- Construction directe du plan classé ; annotations et log `C116_EQUIPMENT` supprimés. Span `build.air.choose_plan`, garde de caisse et transaction conservés.
- Sondes C104/C116, snapshots et helpers partagés conservés. Corps des helpers C116 restants dans le module moteur identiques avant/après.
- Huit anciens lanceurs C116 retirés ; sauvegardes préalables et SHA-256 dans `results/c116_before_20261013/sha256.json`. Tests exclusifs retirés, contrats de sondes et d'exécution conservés/adaptés.
- Aucun état C116 spécifique dans Save/Load ; `persist.nut`, modules économiques/catalogue C121 et `probes.nut` inchangés. Tous les autres réglages identiques à la base.

## Validation pré-enregistrée

283 contrats ciblés verts, zéro échec/erreur/skip (`results/cleanup_c116_contracts_20261013.json`).

Smoke technique `cleanup_c116_defaults_smoke_20261013_r1` : une graine 42, un an, une répétition, référence `OpexAI` contre AAAHogEx, défauts courants, aucune variante et aucune sonde ajoutée. Lanceur courant `run_c66_reference.py`, gel avant exécution, Docker local desktop-linux, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, 10 CPU, 8 Go RAM/swap, 10 workers, cache `openttd-lab-home`. Aucun conteneur actif au contrôle préalable. Objectif : compilation/exécution et santé ; pas de conclusion économique, ni porte A/B.

## Résultat

Smoke exécuté : `cleanup_c116_defaults_smoke_20261013_r3`, 1/1 duel complet, deux compagnies actives et horizon atteint, aucune erreur non attribuée. La première année reste un smoke, pas une preuve économique. Bundle `01fd7b944ec58e830074e55efd28c7626bd27e609b83e1b4b04f23c53bf2ebc9`, manifeste `82ea89f3638223f7c58ab8ddddb30c2c62f5b4afc5eb2c47a6b3b4b957028d49`. Sources locales modifiées figées avant exécution.

Les essais r1 et r2 se sont arrêtés avant toute partie : r1 rejet du format explicite `--reference OpexAI`, r2 options de comparaison sans variante. r3 utilise la référence implicite aux défauts, sans option comparative ; aucune relance fondée sur un résultat économique.

[12 preuves archivées](../evidence/review/c116_cleanup_20261013/README.md), empreintes brutes et gzip vérifiées. Pas de campagne A/B, pas de commit/push.
