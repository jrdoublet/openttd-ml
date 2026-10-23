# DIST-BORNES-1 — sonde de rendement du capital

23/10/2026, branche `dist-bornes-1-diag`. Ajout diagnostique uniquement :
`OpexLogEpochBoundsCost` dans `ai/OpexAI/candidates.nut:353`, appelé à côté de
`EPOCH_BOUNDS` dans le bloc `DECISION_LOG` de `OpexRefreshEpochBounds`.
Le helper a aussi une garde d'entrée. Aucun réglage, aucune écriture des bornes,
aucun changement des filtres, aucun résultat économique mesuré.

## Estimateurs réutilisés et hypothèses

- Villes fictives de **2 000 et 1 000 habitants**, non recherchées sur la carte.
  Demande mensuelle commune = `(2000 + 1000) * TOWN_CATCHMENT_SHARE_PCT / 100`,
  minimum 10 : formule population du générateur AIR
  (`ai/OpexAI/air_planning.nut:690`). C'est un scénario synthétique, pas la
  production mesurée employée par les candidats ferroviaires réels.
- Rail : `OpexLineEconomics` (`ai/OpexAI/economy.nut:166`, kind `pax`), avec
  locomotive et wagons du catalogue, dimensionnement de rame/quai et choix de
  1 à `MAX_RAIL_TRAINS` trains inchangés. Il réutilise vitesse effective et
  accélération (`catalog.nut:136`), arrêt en gare, note, capacité, tarif
  `AICargo.GetCargoIncome` (`economy.nut:383`), fonctionnement et amortissement
  (`economy.nut:395-397`). Aucun second cargo ferroviaire synthétique.
- Capital rail : reprise de la décomposition `economy.nut:332-334` :
  `d * (costTrackPerTile * RAIL_TERRAIN_FACTOR / 100)` + deux quais de la
  longueur choisie + **un dépôt systématiquement** + `rail.vehicleCost`
  (locomotives et wagons du dimensionnement). Le facteur existant est un
  surcoût terrain ; aucun détour géométrique additionnel n'est inventé.
  Distance de trajet = distance payée = d. Pas de recherche A*.
- AIR : `OpexAirEconomics` (`air_route_economics.nut:4`), aéroport et avion du
  catalogue (`catalog.airport`, `catalog.plane`), deux aéroports neufs, **un
  avion fixé**, sans plafond de trésorerie. Capital = deux prix d'aéroport +
  prix de l'avion. Maintenance selon `economy.infrastructure_maintenance`.
  Temps : `OpexAirTripModel` (`air_trip.nut:37`), chemin historique API/4 et
  délai fixe 3 jours. Tarif : `OpexAirFarePerPax`
  (`air_economics_c121.nut:3`), qui conserve le forfait courrier 15 % et la
  calibration AIR existante. Charges et amortissement conservés
  (`air_route_economics.nut:70-74`).
- Ce calcul AIR **n'est pas le modèle C121 de sélection avec sites, demande
  réelle, chargement et congestion des hubs**. Aucun site fictif ni état de
  hub n'est fabriqué ; le journal porte `model=rail_pax_air_legacy` pour
  empêcher cette confusion. Il compare les estimateurs sans sites existants,
  pas les offres effectivement constructibles du portefeuille.
- ROI signé en **‰/an** = `1000.0 * profitAnnual / capitalPhysique` : pas de
  troncature à zéro, pas d'immobilisation de transit. Les profits restent ceux
  des estimateurs, y compris leurs amortissements et calibrations actifs.
  Notamment, si `RAIL_DEPOT_COST=0`, l'amortissement rail omet le dépôt alors
  que le dénominateur de cette sonde l'inclut ; le recalage V275 éventuel du
  profit reste actif, mais sa réduction du capital n'est pas reprise.

## Journal et limites

Une boucle de **20 points** : d = 20, 40, …, 400 tuiles. Chaque ligne
`EPOCH_BOUNDS_COST` donne d, `roi_rail`, `roi_air`, capitaux, revenus et profits
annuels, nombre de trains/wagons et locomotive. La ligne finale donne scénario,
type d'aéroport, avion, facteur terrain, nombre de points valides et
`crossover=` : premier d où ROI AIR ≥ ROI rail, **−1 sinon**.
L'égalité de deux pertes compte conformément au critère demandé ; ce n'est
pas une déclaration de rentabilité. Un estimateur absent donne `NA`, pas zéro.
Un croisement avec moins de 20 points valides est incomplet ; absence du
catalogue AIR donne `status=unavailable points=0 crossover=-1`.

Le balayage reste théorique au-delà de la carte ou de la portée des appareils ;
aucun filtre de distance ni borne courante ne limite cette grille.
Un cache de croisière **local à la sonde** évite les recalculs partagés ; aucun
scan de villes/moteurs ni nouvel appel `Valuate`. Les estimateurs gardent leurs
boucles internes bornées. Coût réel d'opcodes non mesuré ; avec journal actif,
la consommation ajoutée peut décaler le rythme de jeu.

## Contrats et validation

`sweeps/test_dist_bornes_cost.py` : trois contrats (garde et appel unique,
grille/estimateurs/capital/croisement signé, absence d'écriture des bornes).
Le troisième reconstitue exactement le fichier préexistant en retirant le
helper et son appel, puis contrôle son SHA-256 :
`3744db72515531e36ca24d3cd600e73a539c265dae4246289499056e7b0d0fb5`.

Empreinte `candidates.nut` de `test_po01c_regen_split.py` **explicitement
rebasée** vers `1b7798460c4b6ee5754a873a317f3b08e3ed3dbbf05980e02267df8b4ba81fcc`.
Pas de nouveau `Valuate`, donc inventaires inchangés.

Résultats exécutés :

- `python3 -m unittest discover -s sweeps -p 'test_dist_bornes_cost.py'` :
  **3 tests OK**.
- `python3 -m unittest discover -s sweeps -p 'test_po01c_regen_split.py'` :
  **27 tests OK**.
- `python3 -m unittest discover -s sweeps -p 'test_*.py'` : **2 465 tests**,
  **1 échec, 14 erreurs, 7 ignorés, 2 échecs attendus**, 26,661 s.
  Deux erreurs d'import faute de `pytest` : `test_analyze_air_load_shadow`,
  `test_audit_air_roi_renfort1_itt`. Les douze autres erreurs et l'échec
  concernent `test_v166_aaahogex_settings` : le fichier non versionné
  `ai/AAAHogEx-115/info.nut` manque dans ce worktree. Le test de transmission
  au lanceur attend un code 0 et reçoit 2 à sa validation préalable ; ses
  appels Docker sont simulés. Aucun échec dans les contrats de la sonde ou
  les inventaires. Journal intégral local : `/tmp/dist_bornes_cost_unittest.log`.
- `git diff --check` : OK.

Compilation/exécution Squirrel non validées : Docker et parties interdits
par la demande. Aucun smoke, banc, push ni changement de configuration Git.
