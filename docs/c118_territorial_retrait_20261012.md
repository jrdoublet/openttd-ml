# Retrait de c118_air_territorial_expansion

**Suite :** commit ciblé et préparation de fusion demandés le12/10 après validation. [Archive versionnée des preuves techniques](../evidence/review/c118_c119_cleanup_20261012/README.md). Les mentions « aucun commit/push » ci-dessous décrivent l'étape de retrait ; aucune qualification économique du cumul avec V157/V158/V160 n'en découle.

Décision utilisateur du 12/10/2026, après l'analyse du candidat : « Supprime et nettoie le code ». Retrait ciblé de la politique territoriale C118 autonome ; C121 définitivement adopté, C120 et la sonde de couverture restent préservés. Aucun commit ni push demandé. Le retrait C119 précédent et les travaux P0/AC locaux ne sont pas annulés.

## Historique et portée

Le booléen était à0 aux quatre difficultés. Il classait les projets par nouvelles villes productrices dans le catchment, puis délai de financement du prochain projet territorial, avec départage profit/ROI. Sous C121, le changement de moteur après classement était déjà interdit, mais activer C118 pouvait encore modifier classement et financement : le drapeau OFF n'était pas une preuve de code mort.

La [synthèse du 30/09](journaux/synthese_decisions_2026-09-30.md) rapporte le diagnostic historique `smoke_c118_territorial_1x3_20260927_r2`, graine42 ×3 ans contre C115, sonde de couverture commune : profit−50,3 %, valeur−56,9 %, retard dès le premier mois malgré le même moteur. Cette formulation est documentée comme rejetée. Un diagnostic sur une graine ne qualifie pas un effet moyen et ne mesure pas le retrait sur C121 courant ; aucune réouverture ni nouvelle porte économique.

## Code retiré et consommateurs préservés

- Déclaration, globale/chargement, snapshot de sélection et compteur exclusif de diagnostics moteur retirés.
- Préparation de la frontière territoriale, finance minimale alternative, exception au plancher, ordre lexicographique et inhibition de promotion défensive retirés. Les règles économiques, C77, C121 et les branches C120 gardent le comportement de l'ancien défaut C118 OFF.
- Chooser territorial et exports C118 du scan C115 retirés ; C116 conserve son chemin historique, bloqué sous C121. Annotations des plans/projets et actualisations/comparaisons V141 spécifiques à C118 retirées.
- Helpers devenus sans consommateur après ce retrait supprimés : `OpexCapitalQuoteAlternativeFinance` et `OpexV141WriteSlot`. Financement central, apprentissage de devis et publication V141 partagés conservés.
- `OpexC118EngineFitsPlan`, utilisé par C121, **strictement inchangé**. Helpers de couverture réelle et caches conservés ; leurs gardes ne dépendent plus du drapeau supprimé, mais toujours de la sonde C118 ou de C120. `OpexC118SetProjectField` reste consommé par C120.
- `c118_air_coverage_probe=0`, émission `C118_COVERAGE`/`C8V|` conservées. Traces de décisions propres à la politique retirées ; décodeur historique `c118_sign_metrics` et analyseurs C118 inchangés pour relire les anciens artefacts. Aucun champ ni schéma Save/Load modifié.
- Deux lanceurs C118 et le contrat d'intégration exclusif retirés après copie/hashes vérifiés. Contrats de couverture conservés dans `test_c118_air_territorial_expansion.py`. Deux lanceurs C120 débarrassés de l'option C118 supprimée ; aucun de ces bancs historiques lancé.

[Sources avant retrait et hashes](../results/cleanup_c118_sources_backup_20261012/manifest.json), [lanceurs/tests originaux](../results/cleanup_c118_launchers_tests_backup_20261012/manifest.json), [audit reproductible des composants partagés](../results/cleanup_c118_audit_20261012.json). L'audit compare les corps exacts des fonctions partagées, vérifie les seules simplifications de garde, l'absence des symboles de politique, les copies et `persist.nut` inchangé. Pour le builder de projets, seule l'annotation C118 a disparu ; helper d'amortissement flotte inchangé et empreinte de son contrat actualisée sur cette preuve.

## Validation technique

**188 tests ciblés verts** : 137 couverture C118/C120, C115/C116/C121, publication AIR/V141, flotte partielle, paiement physique et contrats C119/V92 ; 45 amortissement/devis/C122 ; six V141 supplémentaires. Deux premières assertions périmées (empreinte globale du builder et appel finance alternatif C118) ont été diagnostiquées puis adaptées au retrait effectif, sans masquer une modification de la sonde ni du financement partagé.

`git diff --check` sans erreur. Les tests Python ne compilent pas Squirrel.

**Deux smokes moteur42×1 complets et sains**, chacun un duel contre AAAHogEx : `cleanup_c118_defaults_smoke_20261012_r1`, défauts chargés, puis `cleanup_c118_coverage_smoke_20261012_r1` avec seul `c118_air_coverage_probe=1`. Deux compagnies actives par duel, `run_ok=true`, `horizon_complete=true`, aucune erreur de script ou non attribuée. Trois trimestres initiaux valides, couverture partielle attendue à un an. **Dix événements distincts de couverture** sous sondeON, confirmés par le JSONL et dix logs `C118_COVERAGE` ; zéro au défaut, zéro décision de politique C118 dans les deux jeux. Les checkpoints répétés ne sont pas des observations indépendantes.

Campagne indépendante `v158-b20x10-20261012` active lors du contrôle initial : attente de sa fin, sans interruption, puis contrôle Docker libre avant chaque smoke. PC `desktop-linux`, 10 CPU/8 Go/swap8 Go/10 workers, cache `openttd-lab-home`, `script-debug`, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`. Bundle commun `e106f0076fc2ce1dbccc51841de4c1a8e86a66cf06fdfa12085ef7e6bc536e41` ; manifestes défauts `2cd046f0928a2730d6dc5362a39eadfc73aa60123f4f618462f30d2157a6f7e5`, couverture `825dd1bc7ab87980e5628e4f2cd8c239296f8907d998aa291675502c5a417f21`. Audit des réglages : traitement C118 absent, sonde0/1 selon le jeu, C121 économie/catalogue/paiement physique à1. Pas de comparaison économique entre ces smokes ni qualification causale du nettoyage.

[Résultat défauts](../results/cleanup_c118_defaults_smoke_20261012_r1.json), [manifeste défauts](../results/cleanup_c118_defaults_smoke_20261012_r1.manifest.json), [résultat sonde](../results/cleanup_c118_coverage_smoke_20261012_r1.json), [manifeste sonde](../results/cleanup_c118_coverage_smoke_20261012_r1.manifest.json), [audit des deux smokes](../results/cleanup_c118_smokes_audit_20261012.json).

Source de départ `master` HEAD `0988bbad0cda87f2335169cbade53c6af6e1ecda`, arbre local dirty incluant C119 et les modifications de sondes préexistantes. Aucun A/B, gain économique/opcodes ou identité de trajectoire revendiqués. Aucun commit/push.
