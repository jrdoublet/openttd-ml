# V257 — Composition des rames, 18 octobre 2026

Implémentation expérimentale sur `v257comp`, worktree
`/home/deploy/projects/wt-v257comp`, base master `546cbec`, arbre initial propre.
Demande utilisateur : deux modes derrière un seul réglage à défaut 0, commits
locaux en français ; aucune partie, aucun Docker, aucun push. Ces interdictions
priment sur le lancement automatique des bancs d'AGENTS.md. Aucune qualification
économique ni compilation Squirrel n'est revendiquée.

## Cause des rames voyageurs à un wagon

Au défaut, `candidates.nut:961` fixe `TOWN_CATCHMENT_SHARE_PCT=22`.
`candidates.nut:1030` additionne les productions mensuelles des deux villes puis
applique cette part de captage. `economy.nut:238` applique ensuite
`STATION_RATING_PCT=50` (`economy.nut:24`) au volume transmis.
Le dimensionnement porte donc, hors réglage expérimental de part voyageurs,
sur **11 % de la production des deux villes**. La fréquence chargée voyageurs
compte les deux sens (`economy.nut:91`), à partir du temps de trajet et du séjour
mécanique. `economy.nut:245` calcule :

`wagons = ceil(offre_calibrée / (capacité_wagon × trajets_chargés_par_mois))`.

Le résultat est ramené à au moins un wagon. La correction du cycle
(`economy.nut:268`) utilise encore cette offre réduite. Lorsque celle-ci tient
dans un wagon, **un wagon est exactement le résultat attendu de ces heuristiques**.
Ce n'est ni une troncature entière accidentelle ni un plafond codé à un wagon.
L'ampleur du captage réel n'est pas démontrée par cette lecture statique.

Le quai voulu est dérivé de cette petite rame et d'une marge de deux wagons
(`catalog.nut:49`, marge physique vanilla documentée dans ce fichier). Le quai
trouvé borne le recalcul dans `builder_rail.nut:2900`, puis le chemin A* borne le
recalcul final dans `builder_rail.nut:2970`. `OpexApplyRailEconomics`
(`economy.nut:528`) reporte simultanément wagons, locomotive, capacités, capital
et profit. `OpexBuildTrains` (`builder_rail.nut:2612`) construit exactement les
nombres demandés ; chaque longueur réelle est mesurée avant attelage et le
débordement du quai déclenche le nettoyage transactionnel.

Après construction, le second train et le doublement copient `line.wagons`,
`line.loco`, `cargo2` et `wagons2` (`builder_rail.nut:4449`, `:4487`). Les trains
supplémentaires V190 sont clonés depuis une rame existante
(`task_rail.nut:541`). **Aucun de ces chemins ne redimensionne le convoi.**
L'allongement de wagons en service a été figé à zéro puis retiré
(`task_rail.nut:383`). Une petite composition initiale se perpétue donc.
Le seul journal `LINE_FLEET` à la construction ne prouve pas l'absence de tout
ajout ultérieur : le constat communiqué est conservé avec cette limite.

## Vérification indépendante du source AAAHogEx

Le dossier `ai/AAAHogEx-115/` existe dans ce worktree et a été lu directement.
Aucun code de l'adversaire n'est copié.

- `trainroute.nut:955` : longueur disponible = minimum des deux quais ;
  `:858` et `:904` la transmettent à l'estimateur d'une route existante.
- `estimator.nut:1660` augmente locomotives/wagons ; `:1670` compare la longueur
  du plan en seizièmes de tuile au quai disponible, avec `maxStationSpread`.
  Ce n'est pas un nombre universel de huit wagons ni une obligation de remplir
  tous les quais : plusieurs compositions admissibles sont évaluées.
- `estimator.nut:1036` trie les compositions par ROI lorsque `roiBase` est actif.
  Le coût courant inclut les wagons (`:2142`) ; la pente intervient dans
  l'évaluation physique (`:1693`, `:2198`).
- `route.nut:1152` détermine les cargos supplémentaires : pour le bidirectionnel,
  acceptation aux deux extrémités ; pour le fret, production/livraison à la source
  et acceptation à destination. `trainroute.nut:399` vérifie leur transportabilité.
- Le chemin courant `TrainPlan.IncreaseNumWagon` (`estimator.nut:1967`, surtout
  `:1985`) ajoute au cargo ayant le plus petit rapport **capacité/production**.
  `CalculateSubCargoNumWagons` (`:1125`) existe aussi, mais sa seule définition
  ne suffit pas à décrire le chemin courant d'augmentation. Le diagnostic qui
  cite cette ancienne fonction est donc précisé ici.
- `trainroute.nut:1171`, `:1221` construit les nombres retenus pour chaque cargo,
  avec refit au cargo demandé. Cette capacité NewGRF de l'adversaire n'est pas
  ajoutée implicitement au catalogue OpexAI.

## Modes livrés

`info.nut:615`, `globals_pre.nut:545`, `settings.nut:149` : `v257_consist`, entier
0..2, **0 aux quatre difficultés**. Chargement unique au démarrage. Le code métier
est dans `rail_consist_v257.nut`, chargé par `main.nut` après `economy.nut`.

**0 — témoin.** Dimensionnement historique et réglages existants conservés.
Les réparations du transport mixte dans le constructeur V190 et son budget de
clonage sont gardées par V257 ; elles n'activent pas V163 au défaut.

**1 — production.** Les productions mensuelles de la paire viennent des API
`AITown.GetLastMonthProduction` et `AIIndustry.GetLastMonthProduction`.
Le repli voyageurs population × 22 % est désactivé sous V257. Les voyageurs
utilisent la somme des deux villes ; le fret utilise la production de la source.
Le dimensionnement n'applique ni le captage fixe de 22 %, ni la note forfaitaire
de 50 %. Il cherche la plus petite composition capable d'emporter cette offre
avec son cycle physique ; à défaut de place, il conserve la dernière composition
admissible. Il n'impose pas artificiellement deux wagons aux petits gisements.
Le mode 1 est mono-cargo, même si un autre drapeau de second cargo est actif.

La borne provient du quai trouvé après recherche, de `station.station_spread`
avant recherche et de `vehicle.max_train_length`. La conversion nominale est
`OpexRailNominalMaxWagons` (`catalog.nut:18`), fondée sur les longueurs vanilla
mesurées de 8/16 de tuile. Le constructeur garde son contrôle des longueurs
réelles et rejette les compositions qui débordent : aucun plafond de 8 ou 13
wagons n'a été inventé. La marge de quai existante est conservée.

**2 — production et mélange.** Ajoute voyageurs + courrier et le second cargo
fret de la source accepté à destination, en réutilisant les extracteurs et le
constructeur V163. Le quai est partagé au prorata production/capacité, avec au
moins un wagon par cargo si deux wagons peuvent tenir. Chaque essai recalcule
la masse pleine pondérée, la plus faible vitesse limite et le séjour mécanique
le plus long des deux wagons. Le cache mono-cargo est évité pour ce calcul : sa
clé ne distingue pas les compositions mixtes.

Après sélection des emprises A*, `OpexV257ObservePair`
(`rail_consist_v257.nut:61`) vérifie le second cargo sur **ces** emprises :
courrier produit et accepté aux deux bouts ; fret produit côté source et
accepté côté destination. Une absence remet son volume à zéro avant le recalcul
économique final. Le seuil d'acceptation 8 vient de NoAI 15.3.
`GetCargoProduction` compte des producteurs : il n'est jamais substitué à une
production mensuelle.

**Économie et construction.** Les nombres renvoyés par le plan sont injectés
dans le modèle commun avant capacités, revenus, achat et amortissement
(`economy.nut:302`). L'entretien de chaque wagon est ajouté à celui de la
locomotive (`:421`, prix API déjà lus au catalogue). Le classement utilise une
rame sur voie simple, deux si V190 est actif : il ne crédite pas un second train
qui ne serait pas construit. Le revenu reste borné par la note de gare calculée,
pas automatiquement égal à toute la production. Un recalcul final impossible
arrête le projet au lieu de construire avec le modèle périmé.

Les seconds trains recopient les nombres enregistrés et les modèles de wagons
enregistrés dans `v257Wagon` / `v257Wagon2` ; le clonage conserve physiquement la
composition. Ces tables de valeurs API suivent la projection générique
`persist.nut:557` et les lignes conservées après chargement (`:853`). Aucun
curseur ni cache décisionnel persistant n'est ajouté. `save_full_state=0`
conserve sa limite historique : il ne sauvegarde pas les lignes complètes.
Les lignes antérieures à V257 ne sont pas transformées automatiquement.

**Différences avec V163 rejeté.** V163 dimensionnait à 50 %, allouait d'abord
le quai au cargo principal et ajoutait le second dans le reliquat, en utilisant
le poids du premier type pour l'ensemble. Il excluait le courrier voyageurs.
V257 change ces quatre points, ajoute l'entretien des wagons et aligne le
nombre de rames estimées sur la flotte initialement livrable. Il s'agit d'une
nouvelle intervention comportementale, **pas d'une requalification de V163**.
Sa porte A échouée et son 20×10 global négatif restent inchangés ; les mécanismes
partagés ne lui transfèrent aucun verdict.

## Limites et validation

La production des deux villes est une **borne d'offre observée**, pas le flux
origine–destination CargoDist, ni une mesure de la part effectivement captée
par ces quais. Le modèle conserve ses approximations de sens chargés, de note,
de relief et de cycle ; le choix catalogue de locomotive reste celui d'OpexAI.
La rame peut donc être trop grande économiquement. Ces modes sont des candidats
à exposer, pas une promesse de profit ni une implémentation du modèle AAA.
Les NewGRF plus longs restent protégés par rejet à la mesure, sans catalogue
universel de longueur/refit. Aucun réglage protégé n'est modifié ; les familles
C67, V177, V180, V182, V197–V200, V207 et `rail_geometry_*` gardent leurs valeurs
et politiques propres.

**Réglages : 76 → 77 AddSetting**, un ajout, aucune suppression. Cela dépasse
d'une unité le plafond de travail 76 ; avec l'ajout annoncé d'une autre branche,
le cumul serait 78. Le budget moteur de `GetSettings` est distinct
(`script_info.hpp`, `MAX_GET_SETTING_OPS=100000`) : sans moteur, sa consommation
réelle n'est pas validée. Le contrat Python historique conserve son plafond 76
hors ajout V257 explicitement nommé.

Validation exécutée :

- `python3 /home/deploy/.claude/jobs/e230de46/tmp/undecl.py ai/OpexAI` : seulement
  `AICONFIG_BOOLEAN`, `CONFIG_BOOLEAN`.
- `delim.py ai/OpexAI` : aucune anomalie.
- `orphans2.py ai/OpexAI` : les trois orphelins connus seulement,
  `OpexAirV95CompetitorSecondSlotOpen`, `OpexRoadTryJoinStop`,
  `OpexV131KeepStructures`.
- `PYTHONPATH=sweeps python3 -m unittest discover -s sweeps -p "test_*.py"` :
  **1 935 tests, OK, 3 ignorés**, dont 13 nouveaux contrats V257.
- `git diff --check` : vert.

Les nouveaux tests vérifient réglage, branche témoin, bornes physiques, mélange,
réévaluation sur les emprises, cohérence économique, conservation des wagons,
chemins de construction et exposition. Les contrats existants V163/V207/V212
et le compte V246 ont été adaptés aux nouveaux chemins. Ce sont des contrôles
statiques Python : **ni compilation/exécution Squirrel, ni roundtrip Save/Load,
ni exposition, ni mesure d'opcodes, ni preuve économique exécutées**.

## Commandes prêtes, non exécutées

Profil VPS, à lancer après vérification du contexte, de l'image, du cache et
de l'absence d'autre campagne. Les bras sont sur le même arbre figé ; seul le
mode V257 diffère. Rail seul chez **les deux IA** ; aucun paquet protégé ajouté.
Faire séparément les modes 1 et 2 (`MODE=1` puis `MODE=2`), avec identifiants
neufs à chaque lancement. `decision_log=1` est identique dans les deux bras et
`--script-debug` assure sa collecte. Ces diagnostics ne sont pas des portes A/B.

Smoke **1 graine × 1 an**, deux duels par mode :

```bash
MODE=1
python3 sweeps/run_c66_reference.py \
  --campaign "v257comp_m${MODE}_smoke_1x1_20261018" \
  --reference "OpexAI[mode_air=0,mode_road=0,mode_water=0,decision_log=1,v257_consist=0]" \
  --variant "OpexAI[mode_air=0,mode_road=0,mode_water=0,decision_log=1,v257_consist=${MODE}]" \
  --variant-policy-id "v257_consist_m${MODE}" \
  --aaahogex-setting disable_veh_aircraft=1 \
  --aaahogex-setting disable_veh_roadveh=1 \
  --aaahogex-setting disable_veh_tram=1 \
  --aaahogex-setting disable_veh_ship=1 \
  --decision-rule gain_short --primary-metric profit_year \
  --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5 \
  --required-seeds 40 --required-years 3 --repeats 1 \
  --years 1 --seeds 42 --script-debug --line-telemetry \
  --cpus 3 --memory 2g --max-workers 3
```

Exposition **3 graines × 4 ans**, six duels par mode, après smoke sain :

```bash
MODE=1
python3 sweeps/run_c66_reference.py \
  --campaign "v257comp_m${MODE}_expo_3x4_20261018" \
  --reference "OpexAI[mode_air=0,mode_road=0,mode_water=0,decision_log=1,v257_consist=0]" \
  --variant "OpexAI[mode_air=0,mode_road=0,mode_water=0,decision_log=1,v257_consist=${MODE}]" \
  --variant-policy-id "v257_consist_m${MODE}" \
  --aaahogex-setting disable_veh_aircraft=1 \
  --aaahogex-setting disable_veh_roadveh=1 \
  --aaahogex-setting disable_veh_tram=1 \
  --aaahogex-setting disable_veh_ship=1 \
  --decision-rule gain_short --primary-metric profit_year \
  --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5 \
  --required-seeds 40 --required-years 4 --repeats 1 \
  --years 4 --seeds 42 7 100 --script-debug --line-telemetry \
  --cpus 3 --memory 2g --max-workers 3
```

À contrôler : santé complète ; lignes voyageurs toujours à un wagon ou non ;
`V257_CONSIST` (production, wagons par cargo, quai, longueur réelle, locomotive,
vitesse, rames prévues/construites) ; `RAIL_BUILD` et `RAIL_EXPAND` ;
`LINE_REVENUE` (capacités, chargements, attente et notes du second cargo).
Une première année sans rail est un smoke sain mais sans exposition.
Les traces doivent démontrer le chargement des deux cargos, pas seulement
leur capacité. Prévoir ensuite un roundtrip Save/Load et, si l'intervention
est retenue, un protocole V102 neuf avant toute adoption.
