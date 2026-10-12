# C118/C119 — commit ciblé et fusion préparée

Demande utilisateur du12/10 : « Commite et prépare la fusion sur origin, j'ai en parallèle active157158 et160 par défaut ». La publication distante n'est pas demandée à cette étape.

## Commits et périmètre

- **`c79bf0f`**, sur le `master` principal : retrait des politiques autonomes C118/C119, contrats adaptés, rapports/passation et35 artefacts techniques archivés. Seules les deux entrées de ce chantier dans `docs/taches.md` et le journal sont committées. `probes.nut`, son test de flux station, les diagnostics/scripts/preuves P0 et leurs sections documentaires restent locaux.
- **`dd826d6630455cf9105fd7714a9d5eee51816614`**, fusion locale de `origin/master` au **`02d243f`** avec `c79bf0f`, dans la branche **`codex/c118-c119-merge-20261012`**, checkout isolé `results/c118_c119_merge_stage_20261012`.
- Deux conflits : `projects_selection.nut` et `docs/taches.md`. La sélection conserve l'insertion par dichotomie V157, ses clés mises en cache, le parcours historique forcé des shadows et la resélection paresseuse V158 ; les branches C118 et la condition `!c118Active` nouvellement ajoutées en amont sont retirées. Le backlog conserve les décisions des deux côtés. V160 et les autres livraisons distantes restent incluses.
- Contrats C121/C122 adaptés aux parcours V157 (argument `forceHistoric=true` pour le shadow K_dec ; vérification de C122 dans le parcours historique). Le contrat V154 perd seulement sa référence au flag C118 supprimé. Retours à la ligne Markdown préservés avec la syntaxe CommonMark sans espaces finaux ; deux lignes vides terminales de tests importés retirées.

## Défauts conservés

Vérification déclarations quatre difficultés, chargement, tests et manifeste du smoke :

| Réglage | Défaut fusionné |
|---|---:|
| `select_bisect_insert` — V157/V154 | 1 |
| `incr_revalidate_index` — V157/V156 | 1 |
| `air_publish_lazy_select` — V158 | 1 |
| `air_fleet_routes_index` — V160 | 1 |
| `c121_air_economics` / `c121_catalog_incremental` | 1 / 1 |
| `air_c121_physical_payment_days` | 1 |
| `c118_air_territorial_expansion` / `c119_air_income_model` | retirés |

Aucun autre défaut réinterprété ni nouvelle qualification économique du cumul. Les décisions d'adoption distantes et leurs verdicts restent celles des rapports originaux.

## Validation de la fusion

**247 tests ciblés verts**,25 modules couvrant les retraits, financement/publication/flotte et V153/V154/V155/V156/V158/V160. Les deux premières assertions périmées, diagnostiquées après intégration V157, ont été adaptées sans modification du traitement adopté. Aucun chemin non fusionné restant, `git diff --check` sans erreur.

Smoke **`c118_c119_merge_defaults_smoke_20261012_r1`**, défauts chargés,42×1, un duel OpexAI/AAAHogEx : **1/1 jeu complet et sain**, deux compagnies actives, `run_ok=true`, `horizon_complete=true`, aucune erreur de script ou non attribuée. Source Git **`dd826d6`, dirty=0** ; les sondes P0 locales sont exclues de ce checkout. Trois trimestres initiaux valides : couverture partielle attendue, validation technique uniquement.

Bundle `27226d9f91b2bfe419bc0ad2e4d172b9ed384b23452f3541e0f6c6d0f8a028b7`, manifeste `fd63252ae0669d899f3c1e255b3bfa2e0c734d3053098ac49778a365da78ffdd`. Docker `desktop-linux` libre avant lancement, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,10 CPU/8 Go/swap8 Go/10 workers, cache `openttd-lab-home`, montage du parent principal et exécution dans le checkout isolé. AAAHogEx local copié uniquement dans le dossier ignoré, sans code adverse versionné.

[Archive versionnée](../evidence/review/c118_c119_cleanup_20261012/README.md) portée à **40 artefacts** :35 du retrait et cinq de l'intégration (résultat, manifeste, log, contrats, audit). Octets bruts et gzip vérifiés par tailles/SHA-256 ; JSONL et bundles complets restent locaux. [Audit de fusion](../results/c118_c119_merge_audit_20261012.json), [JSON du smoke](../results/c118_c119_merge_defaults_smoke_20261012_r1.json), [contrats](../results/c118_c119_merge_contracts_20261012.json).

## État de livraison

Fusion prête dans la branche isolée, **aucun push**. `origin/master` recontrôlé après smoke reste à `02d243f`. Le checkout principal reste sur son commit ciblé `c79bf0f`, avec tous les travaux P0 préexistants ; il n'est pas basculé sur la fusion préparée. La publication pourra utiliser la branche préparée après instruction explicite, en recontrôlant le distant s'il a avancé. Aucun reset, stash, force-push, suppression de branche ou interruption de campagne.
