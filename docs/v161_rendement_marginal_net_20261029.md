# V161 — rendement marginal net du prochain avion (29/10/2026)

**Statut : implémentation et duels AIR seul sains, impact causal V161 non qualifié.**
Les duels du 29/10 contre AAAHogEx donnent un repère descriptif, mais aucun bras
pré-V161 sur un bundle comparable n'a été mesuré : ce ne sont pas des portes A/B.
Aucun changement de réglage par défaut ne découle de cette campagne.

## Décision et calcul

Les deux plafonds annuels historiques de V161 et les chemins qui les utilisaient
ont été retirés. Le portefeuille ne reprend plus `lastProfit / flotte` ni
`(predRevenue - predRunning) / flotte` comme prévision du prochain avion.

Une entrée de flotte représente **exactement un** renfort `n → n+1` :

    ΔR = recettes après − recettes avant, perte de trafic des voisines incluse
    ΔE = exploitation après − exploitation avant
    ΔA = amortissement après − amortissement avant
    ΔP = k_R × ΔR_brut − ΔE − ΔA  (ESTIM lorsqu'il est actif)
    ΔC = prix actuel du moteur réellement retenu

Dans le régime historique C121, la recette marginale déjà valorisée par C121
est utilisée, sans application supplémentaire de `k_R` ou de C70. En mode ESTIM
bit 4, les deltas physiques bruts publiés par C121 incluent désormais
`rawCannibalLossAnnual` (pertes de trafic des autres lignes du hub) avant
correction par `ESTIM_K_R.air`. Le classement et le ROI du projet utilisent le
profit net annuel et le capital de cet achat ; les contraintes de liquidité du
portefeuille sont conservées, avec le budget ESTIM bit 2 sans tampon historique.

La marge C121 calculée après la construction initiale porte le nombre d'appareils
`c121MarginalBaseVehicles` ainsi que `c121MarginalRunning` et
`c121MarginalAmort`, sauvegardés avec la ligne quand `save_full_state=1`
(valeur par défaut). Le mode de sauvegarde court, optionnel, ne sérialise pas les
lignes et donc pas ces deltas. Le profit est reconstruit à
partir de ces composantes, afin de tolérer les arrondis indépendants de Save/Load.
Elle n'est exploitée que
si ce nombre correspond à la flotte actuelle et qu'aucune observation ultérieure
n'a remplacé le palier initial. Le dernier palier observé négatif continue de
constituer un veto. Pour une ligne sans partage de gare, le modèle physique
`OpexAirEconomics` peut mesurer un nouveau `n → n+1` avec la demande,
le moteur et le prix connus. Il retire le coût de fonctionnement et
l'amortissement de **l'appareil supplémentaire**.

En l'absence de données suffisantes, si la flotte et le moteur ne correspondent
plus, ou si la ligne a des voisines sans marge réseau actuelle, la proposition
est refusée avec `marginal_unavailable_or_negative`, sans forfait de secours.
Un changement de modèle de moteur V252 exige également un devis propre :
la différence entre flottes homogènes n'est pas extrapolée à un mélange
d'avions. Le projet est revalidé avant le paiement ; un instantané périmé est
rejeté avec `fleet_marginal_stale`. Le chemin d'achat direct recalcule sa
marge entre deux achats successifs.

## Vérifications et limites

Les tests ciblés V161, R2, C121, ESTIM lots et V252 ont été adaptés au nouveau
contrat ; les simulations moteur 1 graine × 1 an et 1 graine × 3 ans
(seed 42) ont terminé avec le statut `OK`, respectivement dans
`results/v161_net_1x1_20261029_smoke.json` et
`results/v161_net_seed42_3y_20261029.json`. Au terme de la simulation
3 ans, le profit annuel société vaut 3 665 327 £, mais cette observation
isolée ne constitue pas une comparaison de rentabilité.

Le smoke **après** les derniers correctifs V161, graine 42 × 1 an, a également
terminé `status=OK` (`results/v161_net_final_seed42_1y_20261029.json`).
La suite complète finale après réconciliation et ajout d'une garde des
projections a exécuté **3 232 tests, aucun échec, 5 ignorés, 2 échecs attendus**
(`results/v161_suite_final2_20261029.log`). La première passe avait déjà
réussi avec 3 231 tests (`results/v161_suite_final_20261029.log`).

Le gel ESTIM OFF a été réconcilié par **huit couples d'ancres ON/OFF exacts et
revus**, répartis sur `air_catalog_c121.nut`, `projects_builders.nut`,
`projects_models.nut` et `projects_selection.nut` :
`sweeps/estim_unifie_v161_compat.py` complète sans rafraîchissement global
`sweeps/estim_unifie_off_lots.py`. Les projections sont idempotentes et
refusent les contextes altérés. Les empreintes antérieures AIR-site et V233L
ont été **conservées** : en ne réintroduisant que le bloc V161 supprimé sur une
copie en mémoire, on les retrouve exactement ; les deux nouvelles empreintes
post-V161 sont épinglées séparément dans leurs contrats. Le test ciblé
`test_estim_unifie.py` (11), `test_estim_unifie_bit16.py` (6),
`test_estim1_decision_probe.py` (4), `test_diag_air_site_probe.py` (15) et
`test_v233_long_good.py` (71) passe.

Un audit des deux formes du résultat économique C121 a détecté une erreur
latente sous ESTIM bit 4 : `rawCannibalLossAnnual` était calculé mais absent
des deux objets retournés. Le champ est maintenant publié dans chacun ; les
différences brutes `n→n+1` comprennent bien la perte annuelle de revenu
estimée sur les lignes voisines. Un contrat exige les deux occurrences.

### Save/Load et exposition réellement observée

Le roundtrip **défaut** `results/v161_saveload_debug4_seed42_20261029.json`
a conservé 36 sauvegardes en phase A et 12 après reprise ; le journal
`--script-debug 4` contient un `LOAD_RECONCILE` positif, **34/34 lignes
réconciliées**, aucune rejetée. Une compagnie humaine fantôme créée par le
rechargement est signalée séparément et ne fait pas partie des statistiques
OpexAI ; ce phénomène interdit de traiter ce roundtrip comme une comparaison
économique appariée.

Le roundtrip diagnostique **`estim_unifie=31,probes=258`**
(`results/v161_estim31_probe258_saveload_seed42_20261029.json`) s'est
également terminé sainement : sauvegarde mi-1971, 44 gares et 129 véhicules,
reprise un an, 78 gares et 216 véhicules, `LOAD_RECONCILE` positif.
Ses journaux Squirrel donnent **10 achats de renfort `FLEET_PROJECT`
sur la première trajectoire 3 ans** et **2 sur la branche reprise** ; toutes ces
transactions portent `want=1`, `added=1` et `v161_src=c121` avec prix,
profit et ROI de l'avion. Ces branches se recoupent temporellement : **ne pas
additionner 10+2 comme 12 événements indépendants**. Aucun échec de script
ni `fleet_marginal_stale` n'y a été relevé. Aucune exposition démontrée ici
pour `source=physical`, ni pour une transition de moteur V252.

Le modèle simplifié de la ligne isolée n'intègre pas la réaction dynamique des
concurrents, et la marge C121 de construction n'est pas recalculée en continu
sur un hub. Dans ce dernier cas un renfort reste indisponible tant qu'un nouveau
devis fiable n'existe pas : cela peut réduire fortement les achats d'avions
et le profit. Si V252 voudrait acheter un modèle d'avion différent de celui
présent sur la ligne, le devis homogène refuse explicitement plutôt que
d'inventer le rendement d'une flotte mixte. La réduction des achats et son
impact économique sont donc des risques, **pas des pertes déjà mesurées**.
Les refus `marginal_unavailable_or_negative` ne sont pas quantifiés par le
roundtrip `probes=258` : la sonde C69 correspondante n'était pas activée.

## Qualification nécessaire

Mesurer séparément l'exposition `c121`/`physical`, les rejets sans marge et
les achats effectifs, avec les mêmes sondes dans les deux bras. Figer une
référence **avant** ce changement, puis une variante de code, car une même
version sans réglage de bascule ne fournit pas de témoin A/B.
Après smoke comparatif sain, mener porte A 40 graines × 3 ans, puis porte B
20 graines × 10 ans seulement en cas de passage A et accord requis.
Vérifier `profit_year`, valeur de société, croissance AIR, répartition des
investissements et consommation d'opcodes ; ne pas interpréter le smoke
comme une preuve de gain.

## Duels AIR seul du 29/10 (référence descriptive, non A/B V161)

Bundle gelé unique SHA256 `b21f99c848e795395230359c9b4be6290124c053b8a1330e934a0a588f5ebd45`
(arbre de travail dirty au lancement, HEAD `12e4d39f`). Configuration réelle
vérifiée dans les manifestes : `estim_unifie=0`, `eb2_new_station_fallback=0`,
`air_load_min_pct=0`, `air_fleet_yield_rightsize=0`, `air_site_ranked=1`,
`air_site_funnel=1`, `c121_air_project_realization_adaptive=1` ;
`mode_air=1`, `mode_rail=mode_road=mode_water=0` ; `probes=2`.
AAAHogEx-115 : avions uniquement, trains/route/tram/navires désactivés.
Cartes 256² à partir de 1970, une répétition, seeds identiques, jeux appariés
sur la même carte, 0 partie invalide.

* **40×3** (40/40) : `profit_year` 1972 Opex **1 976 565 £**,
  AAAHogEx **2 008 117 £** (ratio de moyennes **98,43 %**) ;
  valeur moyenne Opex **3 775 100 £**, AAA **3 576 648 £** (+5,55 %),
  victoires profit 21/40.
* **20×10** (20/20) : `profit_year` 1979 Opex **2 357 764 £**,
  AAAHogEx **2 494 258 £** (ratio **94,53 %**) ; valeur moyenne Opex
  **15 866 246 £**, AAA **10 870 964 £** (+45,95 %), victoires profit
  9/20 et valeur 18/20. La trajectoire du ratio de profits passe par
  120,13 % en 1974, 111,32 % en 1977 et 94,53 % en 1979.

Archives sources (non écrasées) :
`results/v161_net_marginal_aironly_vs_aaa_40x3_20261029.json` et
`results/v161_net_marginal_aironly_vs_aaa_20x10_20261029.json` ;
preuves publiables compressées et manifestes sous
`evidence/v161_aironly_20261029/`. Synthèse et questions ouvertes dans
`docs/v161_aironly_duels_20261029.md`.

Ces résultats **ne démontrent pas que V161 améliore l'ancien code** : le
code de référence avant retrait des constantes 13 000 / 2 600 £ n'a pas
joué la même campagne. Ne pas présenter la supériorité de valeur sur AAA
comme un gain causal ou une qualification V102.
