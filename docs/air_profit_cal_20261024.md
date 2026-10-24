# AIR-ROI-LIGNE-1 — calibration commune des investissements AIR

Demande du 24/10 : essayer **0,8**, sans favoriser renforts ou hubs au détriment
des aéroports neufs. Implémentation opt-in `air_profit_cal_pct=80` ; **défaut 100**
aux quatre difficultés, entier 10..200, pas d'interface 5. Les valeurs entières
intermédiaires éventuellement fournies par le harnais sont aussi calculables.
Motivation fournie par l'utilisateur : 10 graines × 5 ans, 347 liaisons matures,
réel/prédit 0,42 à 140–200 tuiles et 0,38 au-delà, capital réel/devis ≈ 1,03.
Ces chiffres ne sont pas remesurés ici et ne qualifient pas 80 économiquement.

Branche initiale `air-profit-cal`, HEAD `c03fce93afc16cf86d2e36bb43d9f6dba8b4667d`,
arbre propre. `origin/master` local était `eec5db814734b99c03ed005bfc476c7ff20006c7` :
les deux arbres diffèrent déjà avant cette intervention ; aucun reset/rebase effectué.

## Frontière choisie et couverture

**Le coefficient s'applique à la publication du projet d'investissement**, pas
aux tables brutes des estimateurs. `OpexAirCalibrateInvestment`,
`ai/OpexAI/projects_models.nut:190`, multiplie `project.profitAnnual` et `project.roi`
par `pct / 100.0`. Il est appelé exactement deux fois dans le code, sur des
tables fraîchement créées. Aucun appel dans un consommateur ou un estimateur.
Les chemins rail/route/eau ne l'appellent pas et sont également exclus par sa garde.

Les comparaisons internes AIR (moteurs, profondeurs, nombre d'avions, bornes
supérieures de pruning) restent dans la même unité brute : un facteur positif
commun ne change ni leur ordre ni le signe. Il est donc inutile de multiplier
chaque itération de C121. **Toute sortie de ces chemins qui entre en concurrence
avec un investissement rail/route passe par les constructeurs ci-dessous.**
Ce choix évite aussi les changements de départage dus à un nouvel arrondi entier
dans les estimateurs. Le ROI publié conserve son arrondi historique, puis reçoit
le même facteur que le profit. Hors défaut, le résultat est flottant : un petit
profit positif n'est pas tronqué à zéro et la multiplication évite `profit*200`
en entier 32 bits.

Tous les chemins ci-dessous sont relatifs à `ai/OpexAI/` ; les lignes désignent
la version livrée avec ce document.

| Chemin | Fonction et fichier:ligne | Où intervient le facteur | Absence de double application |
|---|---|---|---|
| Deux nouveaux aéroports (`newpair`) | `OpexProjectFromAir`, `projects_builders.nut:263` | Appel commun ligne 300, sur `decisionEconomics` ou son repli `economics` | Nouvelle table `project`, aucune modification du plan source ; aucun test d'arm |
| Hub → site neuf (`hubsite`), hub → hub (`hubhub`) | Même constructeur ; génération dans `air_planning.nut` et `OpexC121CatalogChoice`, `air_catalog_c121.nut:109` | Exactement le même appel ligne 300 | Les réutilisations d'aéroports ne changent que le capital/marge existants, jamais le coefficient |
| Modèle legacy | `OpexAirEconomics`, `air_route_economics.nut:4` | À sa sortie vers `OpexProjectFromAir` | Estimateur brut inchangé ; pas de facteur dans `air_route_economics.nut` |
| C121 scan complet, ouverture, cible | `OpexC121AirEconomics:537`, `OpexC121OpeningEconomics:966`, `OpexC121EngineEconomics:1008`, dans `air_economics_c121.nut` | Publication de la décision par `OpexProjectFromAir` | Revenu, coûts, `decisionProfitAnnual`, scores internes et bornes restent bruts ensemble |
| C121 rapide/fusionné, profondeur 1/2, raccourci moteur | `OpexC121OneOrTwoDepth:1160`, `OpexC121OneOrTwoFused:1427`, `OpexC121WinnerEconomics:1462`, `OpexC121ChooseRoutePlane:1799`, même fichier | Même publication AIR | Pas de multiplication dans le chemin rapide ni lors de son repli vers le scan complet |
| Renfort C121 sous cible, marge cold-start ou observée | `OpexProjectFromFleet`, `projects_builders.nut:143` | Appel ligne 252, après choix de provenance et V161 | `c121MarginalProfit` de la ligne reste brut ; sa différence next−actual n'a jamais reçu ce facteur |
| Renfort depuis profit moyen réalisé ou repli `predRevenue-predRunning` | Même constructeur | Même appel ligne 252 | L'observation utilisée pour prévoir un nouvel achat est copiée, jamais modifiée dans la ligne |
| Plafond V161, source `model` **et** `prior` | `OpexV161PerPlaneProfit`, `air_fleet.nut:247`, appelé dans `projects_builders.nut:216` | Après `min(model, prior)`, à la publication | `f × min(M,P)`, et non `min(f × M,P)` ; aucun privilège au prior marqué `profitIsObserved` |
| Mode à blanc, rebuild, génération réactive PO01C | `_resizeAirFleets`, `task_air.nut` ; appels aux deux constructeurs dans `projects.nut`, `projects_generation.nut`, `projects_update.nut`, `po01c_regen.nut` | Les mêmes deux constructeurs | Les entrées de flotte sont brutes ; chaque nouveau projet est calibré une fois |
| Fit partiel au budget | `OpexProjectFitFleetToBudget`, `projects_selection.nut:547` | Hérite du profit déjà calibré et le réduit à la quantité achetée | Clone du projet, aucun rappel du calibrateur |
| Réutilisation de publication V141 / reselection V279 | `OpexV141RefreshPublishedAir`, `projects_update.nut:318` ; sélection dans `projects_selection.nut` | Réutilise les champs du projet | Aucun recalibrage sur un projet déjà publié |
| C70, financement, C69, classement | `OpexC70Profit`, `projects_models.nut:160` ; `OpexProjectFundProfit`, `projects_selection.nut:583` | C70 reçoit le profit déjà multiplié | `f × P × k` ou `f × P` selon l'exemption historique ; jamais `f²`. Les revenus ne sont pas des profits et restent inchangés |

`OpexAirFleetYield` (`task_air.nut:431`) ne classe que des lignes AIR entre elles,
avec leur profit par appareil : ordre inchangé sous un coefficient commun.
Le choix d'avion de remplacement dans `air_fleet.nut:56` ne compare aussi que
des avions entre eux. V252 (`task_v252.nut:121`) n'a **aucune prévision de profit
marginal** : âge, profit historique et réserve de capital ; aucun rendement
fictif n'est ajouté. Les remplacements de crash restent des réparations existantes.

## Gardes et absence de pénalité topologique supplémentaire

| Garde | Emplacement | Effet de 80 |
|---|---|---|
| Admission profit strictement positif | `air_planning.nut:695,1257,1424` ; `projects_builders.nut:269,271` ; renforts `projects_builders.nut:185,198` | Aucun changement de signe ; modèles bruts en amont, facteur strictement positif à la publication |
| Plancher de profit du portefeuille | `projects_selection.nut:686` et comparaison ligne 726 (diagnostic ligne 837) | **Désarmé : `floorProfit = 0`, sans autre affectation**. Le long commentaire historique ne décrit pas un seuil actif. Aucun rejet supplémentaire lié à un plancher absolu |
| Marge de caisse 30 000 / 12 000 / 2 000 selon 2/1/0 aéroports neufs | `OpexAirRequiredMargin`, `projects_builders.nut:258` ; `extraMargin`, `air_route_economics.nut:55` | Capital et marge inchangés ; ce ne sont pas des seuils de profit |
| Tampon renfort 1 000 | `projects_builders.nut:235`, `projects_selection.nut:554` | Inchangé, indépendant du profit |
| Refus V161 prior ≤ 0 | `air_fleet.nut:254` | Inchangé, avant facteur ; même signe si on multipliait le prior |
| Payback/tension | `OpexTensionVector`, `tension.nut:281` | Lit le projet calibré : tau augmente de 1/0,8 pour AIR **et** flotte. Sonde, pas garde de rejet d'aéroport |

La baisse de priorité AIR face au rail/route est volontaire. Elle s'applique à
chaque topologie et aux renforts ; elle ne garantit pas le même nombre de
constructions dans une partie. C77, réserves et K_dec restent leurs politiques
existantes : uniformité du facteur ne signifie pas suppression de ces différences.
Aucun garde de payback positif spécifique aux nouvelles liaisons n'a été trouvé.

## Logs, persistance et neutralité

Avec `probes=256`, `DECISION_LOG` ajoute `cal=<pourcentage>` à `PROJECT_CHOSEN`
AIR (`task_air.nut:296`), `FLEET_PROJECT` (`task_projects.nut:222,325`) et aux deux
`PORTFOLIO_RANK` (`projects_rank_log.nut:27,81`) pour AIR/flotte.
Le `profit=` du choix AIR est maintenant celui du projet d'investissement, cohérent
avec son ROI ; le modèle brut reste accessible dans le plan et le log `AIR_BUILD`.
`cal=80` signifie coefficient 0,8, pas coefficient C70.

`task_report.nut`, `line.predicted`, `lastProfit`, `c70Pred`, les marges réalisées
C121 et les journaux de profit **réalisé** sont préservés. Le learner C70 ne doit
pas diviser le réel par une prédiction déjà abaissée, ce qui annulerait le réglage.
La réconciliation post-construction conserve aussi le modèle brut.

Le réglage est chargé une fois par `OpexLoadSettings`. Aucun nouvel état
comportemental sauvegardé : les projets sont transitoires, invalidés au chargement
(`persist.nut:806,980`) puis reconstruits ; les historiques de ligne restent bruts.
Défaut 100 : retour avant toute arithmétique ou mutation ; valeurs et types
économiques inchangés. Cela ne prouve pas une identité de trajectoire moteur,
car même une garde supplémentaire coûte des opcodes.

## Validation

Contrats `sweeps/test_air_profit_cal.py` : 9 tests, déclaration/chargement,
identité à 100, limites/80, couverture des deux publications, tous les replis
renfort, placement après V161, fit/reselection sans second facteur, garde
désarmée, logs et empreintes des modèles/comptabilité non modifiés.
Ces tests sont des contrats source, **pas une compilation Squirrel**.

Rebasage explicite des seuls hashes `info.nut` et `settings.nut` dans
`test_po01c_regen_split.py` pour le nouveau réglage. Les autres hashes existants
restent conservés, y compris celui de `catalog.nut` déjà en échec. Inventaires
d'options mis à 59 dans V251 et les cinq contrats liés (retrait paramètres,
V246, V259, V276, V284). Aucun nouveau `Valuate`, aucune fixture V262 à modifier.

Commande exécutée avant/après :
`python3 -m unittest discover -s sweeps -p 'test_*.py'`, avec `TMPDIR` dans ce
worktree. État initial : 2 391 tests, 2 échecs, 4 erreurs d'import,
7 skips, 2 échecs attendus. État livré : **2 400 tests**, mêmes 2 échecs et
4 erreurs préexistants, 7 skips, 2 échecs attendus ; aucun nouvel échec.
Logs locaux conservés dans `results/air_profit_cal_contracts_20261024/`
(`baseline.log`, `origin.log`, `final.log`, non versionnés).

Échecs initiaux conservés : `test_generators_track_current_producers` (générateur
PO01C désynchronisé), `test_po01d_synchronous_path_bytes_unchanged` pour
`catalog.nut`. Imports indisponibles : `test_airr1_offline_postprocess_20261023`
(`openttdlab`), `test_analyze_air_load_shadow`, `test_audit_air_roi_renfort1`,
`test_audit_air_roi_renfort1_itt` (`pytest`). Pas d'installation implicite.

Contrôle distinct d'`origin/master` par `git archive` dans ce worktree, avec la
copie locale d'AAAHogEx pour les tests : 2 403 tests, 15 échecs, 5 erreurs.
Parmi eux, **un échec est un artefact de la copie sans son propre dépôt Git** :
`test_v279_reselect_memo.test_diff_projects_selection_limited` demande un diff
Git relatif au dossier archivé. Les 14 autres échecs portent sur PO01C
(générateur ; hashes builder_water, air_sites, candidates, catalog, main, probes,
settings, info ; dépendance economy), deux contrats de capture rail, R9 et
station-plan-precheck. La cinquième erreur est le contrat
`test_invalidation_follows_real_construction_only` qui cherche
`WATER_OPCODE_COMPAT_FALSE` absent. Les quatre imports manquants sont communs.
Ne pas attribuer ces écarts à AIR-ROI-LIGNE-1.

`git diff --check` vérifié. Aucun Docker, aucune partie, aucun smoke ni porte
économique, conformément à l'interdiction utilisateur. **80 reste non qualifié** ;
le défaut reste 100. Commit local uniquement, sans publication.
