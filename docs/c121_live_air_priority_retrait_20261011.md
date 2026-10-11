# Retrait de la priorité AIR du premier renfort live

Décision utilisateur du 11/10/2026 : supprimer `c121_air_first_live_air_priority`, nettoyer le code, committer et pousser. Le mécanisme `c121_air_first_live_growth=1` et sa fenêtre de quatre ans restent conservés.

## Résultat historique, sans requalification

Campagne `c121_suite5_20261004_112415_live_air_priority_A`, 40 graines × 3 ans, ON−OFF, chaque bras contre AAAHogEx sur carte partagée. Référence figée `a855906`, bundle `cd8d0dabad0de4f720a81340ff64390d4cbf0d2b31d36ffa676a909ef12f73bb`. C121 economics/catalogue à 1 dans les deux bras, autres réglages aux défauts adoptés de cette référence.

40/40 paires complètes, échantillon et couverture des métriques complets. Profit annuel terminal : moyenne +5 435,625 £/an (+0,315088 %), médiane +4 183 £/an, IC95 bootstrap [−29 287,225 ; +38 724,375], Wilcoxon bilatéral p=0,566499793, 21 victoires / 18 défaites / 1 égalité. Valeur : −0,201231 %, garde −5 % tenue. Règle `gain_short`, seuil +4 % (+69 004,448 £/an), bootstrap 20 000 rééchantillonnages, graine 0 : **`fail_primary`**. Gain requis non démontré ; ni perte significative ni neutralité démontrée. Aucune B.

[JSON original](../results/c121_suite5_20261004_112415/snapshot/results/c121_suite5_20261004_112415_live_air_priority_A.json). Ce résultat historique ne mesure pas le nettoyage courant ni les changements intégrés depuis le 04/10.

## Périmètre

Retrait de la déclaration, globale, chargement et branche de report du renfort dans `task_projects.nut`, avec son calcul de condition devenu inutile et ses contrats exclusifs. Le shadow conserve `OpexC121FirstLiveAirOpportunity`, les traces `C121_FIRST_LIVE_PRIORITY`, leur déduplication et le marqueur `c121FirstLive`. Son contrat vérifie maintenant l'absence de `continue`/`break` sur toute la branche. La croissance live, ses observations et les helpers financiers partagés sont conservés. Aucun champ Save/Load ni schéma modifié ; l'état shadow demeure transitoire.

Les scripts d'analyse de résultats historiques et les rapports antérieurs sont conservés. Aucun résultat économique ou gain d'opcodes n'est revendiqué pour ce retrait. Les travaux AC restent hors du commit.

## Validation

Contrats économie C121 : 55/55 ; investissement : 3/3 ; cohérence cache : 6/6 ; subventions : 8/8, soit 72 contrats verts sur le code synchronisé. `git diff --check` sans erreur.

Smoke `cleanup_live_priority_smoke_20261011_r2`, défauts chargés, graine42 ×1 an, un duel contre AAAHogEx : complet et sain (`game_ok=true`, deux compagnies `run_ok=true`, aucune raison d'échec). Exécuté après la fin de la campagne AC concurrente, sur `d3937b3` avec ce retrait local, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, 10 CPU/8 Go/swap8 Go/10 workers. Bundle `32c11c9e5850090e868dfaf29d50b799bab5f558dcf8bea35cec0b75b3b7c7b2`. [JSON](../results/cleanup_live_priority_smoke_20261011_r2.json), [manifeste](../results/cleanup_live_priority_smoke_20261011_r2.manifest.json). Validation technique uniquement, aucune comparaison économique avant/après. La tentative r1 a été refusée par le parseur (`--reference OpexAI`) avant toute partie ; r2 omet cet argument pour charger les défauts.
