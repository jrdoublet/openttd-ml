# Passation — paramètres OpexAI examinés au12/10

Complément courant à la [passation du11/10](passation_nettoyage_parametres_20261011.md). `docs/taches.md` reste la seule liste autoritaire du travail restant. Les mentions « aucun commit/push » dans les rapports décrivent leur étape de validation antérieure ; la publication ciblée a été demandée explicitement le12/10.

## Décisions réconciliées

| Paramètre examiné | Décision et état | Mesure / validation conservée |
|---|---|---|
| `rail_upgrade_failure_memory` | Adoption explicite à1 conservée | 40×10 `fail_primary`, équivalence non démontrée ; [rapport](rail_upgrade_failure_memory_40x10_20261010.md) |
| `air_c121_physical_payment_days` | Adoption explicite à1 conservée | 100×3 `fail_primary`, non-infériorité non démontrée ; [rapport](air_payment_100x3_20261010.md) |
| `v126_air_served_town_reuse` | Retiré, `5b05be9` | 18 contrats, smoke ; distinct du devis V126 |
| `c121_air_target_limit` | Retiré, `5b05be9` | 102 contrats, smoke et fixture visible |
| `c121_fleet_stock_growth` | Retiré, `5b05be9` | 91 contrats et smoke |
| `c121_territory_first` | Retiré, `3bccc8b` | 40×3 et40×5 `fail_primary` ; [rapport](c121_territory_first_40x5_20261011.md) |
| `c121_aaa_line` | Retiré, `3bccc8b` | 10×3 diagnostic défavorable ; [rapport](c121_aaa_line_10x3_20261011.md) |
| `c121_air_observation_growth` | Retiré, `436e1b5` | 100×3 `fail_primary_and_value_guard` ; [rapport](c121_observation_growth_100x3_20261011.md) |
| `c121_air_first_observation_growth` | Retiré avec ses4 sous-réglages, `edac183` | 100×3 `fail_primary` ; sous-réglages non testés après échec du parent ; [rapport](c121_first_observation_100x3_20261011.md) |
| `c121_air_first_live_air_priority` | Retiré, `daf9486` | Historique40×3 `fail_primary`,72 contrats et smoke ; [bilan](c121_live_air_priority_retrait_20261011.md) |
| `c121_kpass_air_continue` | Retiré, `5e6fe47` | Shadow conservé,72 contrats et smoke ; [bilan](c121_kpass_air_continue_retrait_20261012.md) |
| `c121_kdec_cold_exempt` | Retiré, `5e6fe47` | Historique A40×3 perdant,100 contrats, smoke et53 assertions VM ; [bilan](c121_kdec_cold_exempt_retrait_20261012.md) |
| `c121_air_engine_realization` | Retiré, `5e6fe47` | Learner partagé conservé,83 contrats et smoke ; [bilan](c121_air_engine_realization_retrait_20261012.md) |
| `c121_air_project_realization` | Retiré, `5e6fe47` | Repli50/50 supprimé ; adaptatif/direct conservés. Commit commun137 contrats, smoke et fixture de parité ; [bilan](c121_air_project_realization_retrait_20261012.md) |
| `c121_air_defensive_floor` | Examiné, **protégé et conservé à0**, non retiré | R7 : plancher global0, chemins exécutés/cadence à préserver ; pas de nouveau banc |
| `c121_air_initial_project_economics` | Retiré sur demande après40×5, inclus dans le présent commit | +0,148 %, `fail_primary`, exposition directe absente sous choix1/2 ;94 contrats et smoke ; [mesure](c121_initial_project_40x5_20261012.md), [retrait](c121_initial_project_retrait_20261012.md) |
| `c122_air_regime_priority` | Retiré sur demande après40×3, inclus dans le présent commit | −0,996 %, `fail_primary`,13 graines avec promotion ;106 contrats et smoke ; [mesure](c122_regime_priority_40x3_20261012.md), [retrait](c122_regime_priority_retrait_20261012.md) |
| `c122_air_threat_retry` | **Conservé à0**, aucune suppression demandée | 40×5 instrumenté :−0,490 %, `fail_primary`,6 retries/5 graines ; [mesure](c122_threat_retry_40x5_20261012.md) |

Les paramètres de sondes et shadows sont exclus du nettoyage par décision utilisateur. Les variantes live actives, la fenêtre4 ans, l'adaptatif/direct et les consommateurs partagés restent préservés. Aucun réglage numérique dépendant d'un parent rejeté n'est requalifié par le retrait du parent. Gain non démontré, perte significative et décision de simplification restent distincts.

## Point encore ouvert : réparation liée à `c122_air_threat_retry`

Trois constructions après relance à J+19/J+45/J+582 ; trois cas perdus, dont56 rejets après une intention. Une ville prise sous ON est perdue sous OFF ; les deux autres prises existent aussi sous OFF. Pas trois sauvetages causaux établis. [Audit des six cas](c122_retry_reparation_audit_20261012.md).

La tâche demandée est inscrite dans `docs/taches.md` : identifier l'ancre/motif précis, l'exécution C77 et le site choisi, puis comparer si nécessaire une recherche plus complète ou élargie sur l'endpoint défaillant. Rayon25, distance≤25 et arrêt C96 après4 sites/1 couronne supplémentaire : augmenter seulement le rayon peut être sans effet. L'API native ne cherche pas automatiquement un site ; `AITileList` et les tests natifs sont déjà employés. Le helper SuperLib `FindInTownAirportPlacement` est une comparaison possible, pas un remplacement identique. Aucun réarmement implicite de V133/C83 local.

## Sources, validation et publication

Les trois nouvelles comparaisons ont été pré-enregistrées et figées depuis `f6139d8` avec les overlays explicités dans leurs rapports. Le40×3 C122 et le40×5 retry incluent le retrait initial-project déjà validé ; le40×5 retry inclut aussi le retrait priority. Les modifications de sonde P0 parallèles sont exclues de ces copies comparatives. Le retry compare une sonde de menace commune=1 : résultat dans ce contexte instrumenté, pas qualification du témoin sondeOFF. Aucune porte B, adoption ou nouvelle mesure économique du cumul des retraits.

[Archive versionnée des preuves](../evidence/review/parameter_cleanup_20261012/README.md) :50 artefacts (JSON/manifestes/plans/synthèses/CSV, dix logs des retries et smoke de publication), octets bruts et gzip vérifiés par SHA-256. Les bundles complets et JSONL restent locaux ; aucune preuve économique du nettoyage combiné ajoutée.

Commits antérieurs `edac183`, `daf9486` et `5e6fe47` vérifiés présents dans `origin/master` lors du fetch du12/10 ; le statut « edac183 non poussé » du11/10 est donc historique. Départ de cette publication : master local `f6139d8`, distant `2b8f01a` (10 commits supplémentaires, dont V147 adopté). Intégration isolée et contrôle technique de l'arbre à publier, sans absorber les diagnostics P0 locaux. La synchronisation de V147 ne requalifie pas économiquement les nettoyages.

Le commit ciblé contient les deux nouveaux retraits, leurs contrats/diagnostics nécessaires, les six rapports C121/C122, cette passation et seulement les sections correspondantes des tâches/journal. `probes.nut`, son test de flux station, les scripts/rapports/preuves P0 et les sections P0 des fichiers partagés restent hors périmètre. Pas de staging global, pas de force-push.

Commit de nettoyage `d508c46`, fusion isolée `1100a96` avec les10 commits distants. Seul conflit : `docs/taches.md`, résolu en conservant toutes les décisions distantes et les entrées de ce chantier. **135 tests ciblés verts**,50 preuves vérifiées. Smoke propre de l'arbre fusionné `parameter_publish_smoke_20261012_r1`,42×1,1/1 duel sain, deux compagnies actives/horizon complet, aucune erreur non attribuée ; retraits absents des défauts et retry0 confirmés. Bundle `d00176f780b6b8231df76d895f57e802d2e5a1790a2b0cc7475aff939126ef22`, manifeste `53c841bcc86918aa56cdfde7deb9d22eee796cb2aface92d0af38cd3e1c88570`. Cette intégration technique n'est pas une qualification économique du cumul avec V147.

## Prompt de reprise

```text
Nous poursuivons le nettoyage des paramètres OpexAI dans
C:\Users\jr\vscode\openttd-ml\openttd-ml.
Lis AGENTS.md, RTK.md, l'État courant de docs/taches.md et les passations
du11/10 puis du12/10. Vérifie HEAD, git status/diff et les campagnes Docker.

Les paramètres déjà examinés et leurs décisions sont listés dans la passation
du12/10. Ne reteste pas un retrait, ne réarme pas les politiques abandonnées.
Les sondes/shadows sont exclus du nettoyage ; préserve les travaux parallèles P0/AC.
Les adoptions explicites rail_upgrade_failure_memory=1 et
air_c121_physical_payment_days=1 restent conservées.

c121_air_initial_project_economics et c122_air_regime_priority sont retirés.
c122_air_threat_retry reste à0 : 40×5 instrumenté fail_primary,6 retries/5 graines.
La réparation de site associée est une tâche distincte de diagnostic : ancre,
motif exact, étapes C77, puis éventuelle recherche plus complète/élargie ciblée.
Ne pas implémenter ou lancer ce chantier à la seule demande « suivant ».

Si je demande « suivant », présente seulement le prochain candidat hors sondes :
rôle, défaut, historique, dépendances, Save/Load et complexité du retrait.
Analyse seule, aucun banc ni modification implicite. Commit/push sur demande.
Les campagnes nécessaires utilisent des sources figées et10 CPU/8 Go/10 workers
sur ce PC, après vérification de Docker et des campagnes concurrentes.
```
