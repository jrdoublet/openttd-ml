# P0 RAIL — audit des traces de fréquence et suspension

[Rapport et limites](../../../docs/rail_ready_guard_exposure_20261011.md).
Audit hors ligne de 80 logs, 4 800 checkpoints OpexAI et 80 résumés du
40×5 A2 historique. Il ne lance aucune partie ni ne modifie la politique.

L'index local conserve hashes/tailles des sorties et scripts archivés.
`input_hashes.json.gz` identifie les journaux originaux, résultat, checkpoints
et manifeste ; les gros logs restent locaux. Les extraits numérotés du
bundle gelé préservent les conditions de comptage, publication et persistance.
Le grand index de revue et les preuves antérieures ne sont pas remplacés.

Les colonnes absentes et `null` restent inconnues : aucune estimation du
total opcode, nombre de visites ou suspensions causées par la garde.
Les tableaux de C75 ne couvrent que les passes productives et ne prouvent
ni neutralité de cadence ni causalité économique.

Vérification en lecture seule :

```text
python -B -X utf8 evidence/review/rail_ready_guard_exposure_20261011/verify.py
```

Ce paquet fait partie du commit documentaire demandé, sans push.
Trois doublons d'exploration locaux ont été retirés après vérification de leur
identité avec les archives. Leur contenu reste récupérable ici ; le vérificateur
contrôle aussi les empreintes brutes quand l'original local n'est plus présent.

Le nettoyage parallèle a retiré `sweeps/analyse_rail_ready_admission.py`.
Sa copie exacte est conservée ici dans `reader_dependency.py` (6 552 octets,
SHA256 `795cbf3553c753e927c9cffc1c61835b1c1da9e2a151df9383eb81c7d5c77c37`).
Elle fournit les expressions `FIELD` et `GAME` importées par l'analyse archivée.
Pour reproduire celle-ci dans une copie de travail, placer cette dépendance à
son chemin historique ; aucun rétablissement dans le dépôt courant n'est requis.
