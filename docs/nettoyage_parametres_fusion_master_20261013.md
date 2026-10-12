# Fusion du nettoyage C118/C119/C120 avec master — 13 octobre 2026

Demande utilisateur : « Fusionne la branche avec master ». Intégration dans le
checkout isolé `results/c118_c119_merge_stage_20261012` pour préserver le checkout
principal dirty et ses diagnostics P0. Branche publiée avant fusion :
`codex/c118-c119-merge-20261012`, HEAD `68759f5`. Distant intégré :
`origin/master` au `c309272`, 14 commits supplémentaires depuis la préparation.
Les nouveaux défauts V159 (`c117_lean_sampling=1`) et V161
(`v161_fleet_net_marginal=1`) sont conservés avec V157/V158/V160 à 1.
Leurs décisions et verdicts historiques restent ceux de master.

## Résolution et contrats

Un seul conflit : empreinte globale du builder dans
`sweeps/test_parallel_fleet_amort_shadow.py`. Helper de sonde identique aux deux
parents ; builder fusionné exactement égal à celui de master privé de la seule
annotation C118 retirée. Empreinte recalculée après cette vérification.
Deux espaces finaux hérités du document V159 retirés.

287 contrats ciblés verts, zéro erreur/échec/skip, dont V159 et V161 ; autres
spécifications de réglages identiques à master, C118/C119/C120 absents des chemins
actifs. Pas de modification supplémentaire de politique, ni requalification
économique du cumul. [Audit et contrats](../results/cleanup_master_merge_contracts_20261013.json).

## Smoke pré-enregistré

`cleanup_master_merge_defaults_smoke_20261013_r1`, graine42, un an, un duel
Opex/AAAHogEx, défauts effectivement livrés, aucune variante économique.
Harnais `run_c66_reference.py`, code fusionné committé avant exécution, contexte
Docker `desktop-linux`, image
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
10 CPU/8 Go RAM/swap 8 Go/10 workers, volume `openttd-lab-home`.
Montage racine avec répertoire d'exécution dans le checkout isolé ; Docker libre
vérifié. Compilation/exécution, santé et horizon attendu à un an ; trois
trimestres valides possibles la première année. Pas de preuve économique.

Après smoke sain et audit des manifestes : publication normale vers master et
actualisation de la branche, sans force-push, sans toucher aux fichiers locaux P0.
Si master avance avant le push, intégrer et revalider les changements pertinents.

## Résultat de validation

Commit de fusion `e359523` (parents `68759f5` et `c309272`). Smoke exécuté sur
ce commit propre (`dirty=false`) : 1/1 duel sain, Opex/AAA actifs, horizons complets,
aucune erreur non attribuée, trois trimestres valides pour cette année initiale.
Bundle `6f0133904565d2928e0cd73cbddc0cc2c582a340103888c9792ebb8e4a0d8eab`,
manifest `8fcf714f73681cd75f4704cb9ae538c04cf0880f8b76126c317e4418865502e4`.
Manifest audité : C118/C119/C120 absents, V157/V158/V159/V160/V161 et C121 à 1.

[Sept preuves archivées](../evidence/review/cleanup_master_merge_20261013/README.md) :
JSON, manifest, log moteur, contrats, audit de santé/défauts, résolution de
l'empreinte et script d'audit reproductible ancré à `c309272`. Octets bruts/gzip
vérifiés par SHA-256. Validation technique seulement ; les portes économiques
des fonctionnalités intégrées ne sont pas rejouées ni requalifiées.

État documentaire arrêté après validation, avant push normal vers `master` et
la branche de nettoyage. Le checkout principal reste à son état local antérieur,
avec les diagnostics P0 non committés ; aucune synchronisation destructive,
aucun stash/reset, aucune suppression de branche. Pour la suite, utiliser ce
checkout isolé ou réconcilier explicitement le travail local avant synchronisation.

Dernier fetch avant publication : master a avancé au `72526c6`, uniquement pour
mettre à jour le diagnostic V149 dans `docs/taches.md`. Mise à jour intégrée sans
conflit ; `ai/OpexAI` et `sweeps` identiques au commit `e359523` exécuté par le
smoke. Aucun nouveau contrôle moteur nécessaire pour cette seule documentation.
