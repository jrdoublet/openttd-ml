# Retrait de la réalisation projet historique C121

Décision utilisateur du 12/10 : supprimer `c121_air_project_realization` parce que les corrections plus récentes le remplacent, nettoyer, committer puis vérifier la possibilité de pousser. Cette étape n'autorise pas une publication effective.

## Périmètre et compatibilité

Déclaration, globale et chargement du réglage retirés, ainsi que son repli `0.5 + 0.5 * learned`. La correction adaptative `c121_air_project_realization_adaptive=1` et son repli `0.75 + 0.25 * learned` sont conservés. Le facteur direct observé `air_p0_direct_realization=1` et son rollback0 restent disponibles. La porte supérieure du helper dépend désormais de l'adaptatif seul : avec adaptive0, le facteur reste1, comme auparavant avec project_realization0. L'ancien mode project1/adaptive0 est abandonné par décision utilisateur.

Learner partagé, pseudo-observation, seuil de maturité, marges flotte, C70/C82, classification C122 et Save/Load préservés. Les consommateurs runtime restants justifient leur conservation. Cette intervention ne supprime pas en bloc les lissages décrits dans le plan historique `air_p0_legacy_cleanup_plan_20261010.md` : seule la branche50/50 du réglage abandonné est retirée.

Contrats de réalisation adaptés, override historique du module de bras live retiré. Les preuves économiques restent intactes. L'ancien exploratoire40×3, avec adaptatif0, donnait +2 094 £/an (+0,146 %), IC95 bootstrap [−32 253 ; +35 784], p=0,78592, valeur+0,376 %, `fail_primary` ; ni gain ni perte significative établis. [JSON original](../results/c121_nuit_20261003_203842/snapshot/results/c121_nuit10_20261003_210612_air_project_realization_exploration.json).

## Validation du commit isolé

Les quatre retraits déjà demandés sont regroupés : K_pass continue, K_dec cold exempt, réalisation moteur et réalisation projet historique. Les changements AC04-A v3/CD01–CD06 sont explicitement exclus du commit et conservés dans le checkout. Les validations précédentes sur l'arbre partagé restent historiques ; la validation ci-dessous utilise une copie du code de l'index préparé pour le commit.

Copie `results/cleanup_parameter_commit_tree_20261012_r1`, base `a09a7b2`, préparation `prepared_index.json` (empreintes du code et liste des fichiers). **137 contrats ciblés verts** : économie52, réalisation directe4, C12211, game-engine7, replay2, cache6, shadow/décodeur23, calibration R2 6, portefeuille B6 7, flotte R1 8, C75 11. Après clarification de deux assertions textuelles vers le flag adaptatif exact, les52 contrats économie passent à nouveau ; le code NoAI testé reste identique.

Smoke isolé `cleanup_commit_smoke_20261012_r1`, défauts/graine42×1 an, un duel contre AAAHogEx : complet/sain. Bundle `7ec5a450052771dcdab0a213e147c4b2ebd62be8b113fa05c952a2605f686c1a`, manifeste `114eb4c9e066a22f307e98bf7b6fc7c27fa5a6e1e63817afb9cc5e4cae6f7c5b`. [JSON](../results/cleanup_parameter_commit_tree_20261012_r1/results/cleanup_commit_smoke_20261012_r1.json), [manifeste](../results/cleanup_parameter_commit_tree_20261012_r1/results/cleanup_commit_smoke_20261012_r1.manifest.json). Le SHA enregistré par le lanceur est celui du dépôt parent ; la copie de l'index et le bundle identifient les sources réellement exécutées.

Fixture copiée réutilisant le pilote K_dec : **53 assertions K_dec et 322 assertions de parité projet réussies**, intégrité mensuelle saine, sources et copie inchangées. Le helper avant retrait provient de `a09a7b2:ai/OpexAI/projects_models.nut`, seul l'ancien réglage est remplacé par false dans la copie témoin. La matrice couvre adaptive0/1, economics0/1, direct inactif/actif, newpair/hubsite/hubhub/inconnu, cinq valeurs apprises dont froid/bornes, deux ratios directs et plans null/incomplet. [Rapport](../results/cleanup_parameter_commit_tree_20261012_r1/results/c121_kdec_cold_contracts/projectcleanup_20261012_r1/report.json), [plan et hashes](../results/cleanup_parameter_commit_tree_20261012_r1/results/c121_kdec_cold_contracts/projectcleanup_20261012_r1/plan.json). Parité numérique sur les réglages conservés ; aucune identité de trajectoire/opcodes ni rentabilité économique du nettoyage revendiquée.

Docker local `desktop-linux`, aucune campagne concurrente au lancement, cache `openttd-lab-home`, montage du dépôt à `/work`, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, 10 CPU/8 Go/swap8 Go. Smoke10 workers, fixture1 worker.

## Commit et contrôle de publication

Commit ciblé demandé pour les quatre retraits, leurs contrats et leur documentation ; travaux AC/CD laissés locaux. Fetch distant effectué : `origin/master=4197791`, 14 commits supplémentaires par rapport à la base locale, principalement documentation et migration de tests. La vérification finale de push est un `git push --dry-run origin master` ; aucune publication réelle demandée ni exécutée.

Contrôle effectué après commit : **rejet `non-fast-forward`**, 1 commit local propre /14 commits distants supplémentaires. Accès au distant fonctionnel, mais une intégration des changements distants est nécessaire avant publication. Aucune fusion, force-push ou publication réelle effectuée pour contourner ce contrôle. Les travaux AC/CD restent locaux et hors du commit.
