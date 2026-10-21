# Démonstration hors ligne des frontières de temps (21 octobre 2026)

Périmètre : lecture des formules actuelles et des preuves déjà versionnées des
campagnes PC **40 SOLO + 40 DUEL, départ 1970, horizon dix ans, carte 256²**.
Aucune partie, aucun Docker, aucune modification de `ai/OpexAI`.
Reproduction : `python -X utf8 sweeps/demo_frontieres_temps_20261021.py`
(détail avec `--json`). Entrée :
`evidence/review/roi_calibration_predictors_20261021/bandes_distance_roi_20261021.json`.

## Frontières réellement appliquées

`ai/OpexAI/candidates.nut:349-434` rafraîchit `catalog.bounds` et les logs
`EPOCH_BOUNDS`, consommés par `OpexRoadDistanceAllowed` (`:457-469`),
`OpexAirPairInBand` (`:472-484`), `OpexRailPaxPairInBand` (`:486-495`),
ainsi que les découpages des autres producteurs. `catalog.bounds` existe déjà :
aucune nouvelle recherche de géométrie par candidat n'est nécessaire.

Sur **2 109 événements de 80 parties**, une seule configuration a été relevée :

| Seuil, en tuiles | Mesure 1970-1979 | Rôle |
|---|---:|---|
| `roadMin` et `roadMax` | 7 | `2 * rayon_bus + 1` ; route exclusive pratiquement vide |
| `railMin` | 7 | Plancher rail pax |
| `roadGenMax` | 200 | La route *est quand même explorée* au-delà de `roadMax` |
| `railAirOverlapMin`, `airMin` | 200 | Chevauchement AIR+RAIL réduit à la distance 200 |
| `railMax` | 200 | `V294_RAIL_DIST_DECOUPLE=200` prime ici sur le plafond A* inverse |
| `airMax` | 512 | Portée/transit, plafonné au Manhattan maximal de carte |

`roadMax` (`candidates.nut:265-312`) dérive d'un modèle d'amortissement avec
un tarif différentiel à 20 tuiles ; sa valeur 7 peut aussi provenir d'un
dénominateur non positif. **On ne peut pas en déduire que tous les couples au-delà
de 7 tuiles sont économiquement préférables en rail.**

`railAir` (`:315-328`) résout une égalité de temps avec la vitesse rail du
catalogue pour **deux wagons à 20 tuiles**, le moteur avion le plus rapide et
le type d'aéroport actuel supposé identique aux deux extrémités. Son résultat
est ensuite borné entre `roadMax` et `railMax` (`:391-410`). L'avion est
autorisé seul au-delà de 200 selon la distance Manhattan **des centres-ville** ;
son plafond `airMax` porte sur la **distance de vol**, une autre grandeur.
`AIR_BUILD.dist` ne peut donc remplacer la distance de sélection.

## Trois modèles AIR existants et deux conversions de vitesse

La frontière emploie `OpexAirManeuverDays` (`candidates.nut:221-238`), alors que
la production économique C121 calcule le vol via
`OpexC121PhysicalOneWayDaysFromSpeed` (`air_economics_c121.nut:39-61`).
`OpexAirTripModel` (`air_trip.nut:37-73`) subsiste dans les chemins legacy
d'équipement/cadence (`air_route_economics.nut:16-25`, `air_engine_choice.nut`).

| Grandeur pour un aller, deux aéroports 6×6, avion API assez rapide | Frontière historique | `OpexAirTripModel` historique | C100.1 / C121 physique |
|---|---:|---:|---:|
| Vitesse avion pour le vol | `V_API / plane_speed` | `V_API / 4` | `V_API` directe |
| Taxi en vitesse du helper | `min(V_API,150) / plane_speed` | aucun taxi détaillé | `min(V_API,50)` |
| Proxy longueur taxi cumulée | 24 tuiles | — | 16 tuiles (= 2/3 × 24) |
| Taxi (`4096 / (74·1,6·v)`) | 22,14 j | — | 11,07 j |
| Transition verticale | 4,05 j | — | 4,05 j |
| Temps fixe pour un aller | **26,19 j** | **3,00 j** | **15,13 j** |

Le modèle de frontière conserve la vitesse de taxi divisée par 4 après
application de sa limite à 150. La correction C100.1 a établi que la limite
moteur de taxi est 50, avec la compensation `plane_speed` déjà appliquée par
OpenTTD (`air_trip.nut:2-14`). L'ancien temps de **26 j par sens** est donc
une hypothèse historique plus pessimiste que le calcul physique existant.
Ce ne sont pas 26 jours de chargement. Voir
`docs/39_c100_c101_air_physical_engine_choice.md:59-90` pour les mesures et
les essais économiques, dont les modifications de choix AIR furent négatives.

**Autre écart essentiel :** la frontière transforme une tuile en jours via
`4096 / (74 * 1.6 * v) = 34,5946/v`, tandis que les modèles économiques AIR
et RAIL utilisent `1/(0,036*v) = 27,7778/v` (`air_trip.nut:51`,
`air_economics_c121.nut:45`, `economy.nut:251`). Pour une même vitesse,
le premier donne **24,54 % de jours supplémentaires**. Il ne faut pas
calculer un temps fixe dans l'une de ces unités puis l'associer sans contrôle
à l'autre conversion, ni employer `V_API/4` dans un bras et `V_API` dans
l'autre comme si les deux étaient la même cinématique.

### Scénarios numériques reproductibles

Ici, **vitesse effective rail 115** et **vitesse API avion 570** en unités de
vitesse utilisées par le code, `plane_speed=4`, deux grands aéroports. Les
vitesses sont un **exemple plausible, pas une observation des moteurs des
80 parties** : l'agrégat sauvegardé ne contient ni `vRail` ni `vAir`
individuels. Pour `d` tuiles :

`T_rail = d * jours_par_tuile(vRail)` et
`T_air = fixe + d * jours_par_tuile(vAir)`, d'où
`d_croisement = fixe / (tauRail - tauAir)` si `tauRail > tauAir`.

| Modèle appliqué au même exemple | Croisement théorique (tuiles) | Lecture |
|---|---:|---|
| Frontière actuelle : 26,19 j, vol à 570/4, conversion frontière | **451,21** | Rabattue à `railMax=200` ; aucune vraie bande overlap |
| Frontière avec 3 j, même vitesse/diviseur/conversion | **51,68** | Changer le seul délai modifie radicalement la frontière |
| Frontière avec C100.1 : 15,13 j, vol à 570, conversion frontière | **62,98** | Basculer ensemble vitesse physique et manœuvre |
| Économie legacy : 3 j, vol à 570/4, conversion économique | **64,36** | Même 3 j, autres jours par tuile |
| Économie C121 : 15,13 j, vol à 570, conversion économique | **78,44** | Même physique C100.1, autres jours par tuile |

Les deux seuils physiques (63 et 78) diffèrent à cause de **la conversion
des jours/tuile**. Pour le cas 115/570, le code actuel tronque le seuil
62,98 en **62** via `.tointeger()` s'il était substitué dans la frontière ;
le véritable premier entier où l'avion devient plus rapide est 63.
La frontière ne mesure qu'un critère cinématique grossier, pas l'égalité de
ROI ni la rentabilité d'une ligne.

Deux contre-exemples vérifiables confirment le rôle de la vitesse : avec
rail 128 et avion API 320, le chemin historique à `/4=80` n'a **aucun
croisement** (avion en croisière plus lent), alors que C100.1 donne 93,27
tuiles dans la conversion frontière ; rail 80 et avion API 320 donnent
46,63 tuiles en C100.1. Aucun facteur unique de distance ne corrige les
deux situations.

## Portée sur les seules lignes RAIL voyageurs (`PASS`)

**Rectification indispensable : la frontière RAIL/AIR est exclusivement une
frontière de génération des projets VOYAGEURS.** Le fret RAIL est exploré
avec `OpexFreightCandidates`, sans comparaison AIR équivalente ni refit
AIR activé. Il est erroné de compter tous les cargos RAIL pour chiffrer
la nouvelle zone de concurrence AIR : la première version de cette
démonstration avait annoncé 827 lignes, alors qu'elle incluait le fret.
Ce nombre est **annulé**, pas une estimation du changement de portefeuille.

Comptage exact de `cargo=PASS` sur les journaux de lignes matures :

| Distance RAIL, tuiles | SOLO PASS (n=44) | DUEL PASS (n=54) |
|---|---:|---:|
| Moins de 64 | 22 | 29 |
| 64 à 77 | 11 | 14 |
| 78 à 199 | **11** | **11** |
| 200 ou plus | 0 | 0 |

La frontière d'essai de 64 tuiles ferait entrer **25 PASS RAIL DUEL**
dans la bande où AIR serait également autorisé (14+11), et le scénario
physique à 78 tuiles **11 PASS RAIL DUEL**. Ce sont des **lignes déjà
construites**, pas le nombre de nouveaux candidats ni une estimation
du profit. Le changement de frontières pourrait rendre possibles de
nombreuses nouvelles paires AIR non calculées dans le banc ; l'effet
d'opcodes de cette prospection reste inconnu. Sur SOLO, les chiffres
correspondants sont 22 (frontière 64) et 11 (frontière 78).

Les 1 892 lignes AIR DUEL matures sont toutes `PASS` (hors
courrier secondaire) ; 24 étaient à la limite Manhattan 200,
1 868 au-delà. On reconstruit Manhattan depuis les centres de villes :
`AIR_BUILD.dist` mesure une autre distance, celle du vol.

Le script peut reproduire les comptes voyageurs depuis les journaux
bruts :

```powershell
python -X utf8 sweeps/demo_frontieres_temps_20261021.py --duel-logs results/calibration_pc_20261021/results/calib_duel_40x10_pc_20261021_engine
```

### Le forfait AIR de trois jours n'est pas un temps physique

`OpexAirTripModel` a dans son chemin legacy `airportDelayDays=3.0`,
mais cela ne valide **pas** une manœuvre de 3 jours en jeu ; c'est une
hypothèse historique de l'estimateur de revenu/capacité. Le **proxy
physique C100.1** calcule plutôt ~15,13 jours de roulage/mouvements
verticaux dans l'exemple AT_LARGE 6x6, tandis que l'ancien helper de
frontière compte ~26,19 jours : leur différence tient à la vitesse de
taxi et à la longueur estimée au sol. Les temps de chargement AIR
sont encore une troisième grandeur. Ces chiffres ne doivent pas être
additionnés aveuglément aux délais C121 déjà attribués aux hubs.

**Comparer les frontières en C100.1 n'autorise pas à changer le modèle
AIR actif** : ses expériences causales passées n'ont pas qualifié une
substitution à l'économie legacy. La première démonstration doit rester
une illustration des frontières de vitesse, pas une prévision de ROI.

## ROUTE vers RAIL et temps d'arrêt

`OpexComputeRoadToRailDistance` (`candidates.nut:265-312`) approxime un
capital initial différentiel divisé par un excédent de revenu par tuile
moins le coût des voies. `deltaM = GetCargoIncome(PASS,20,tRail) −
GetCargoIncome(PASS,20,tBus)` est un différentiel **pour le trajet complet** ;
le code le **divise par 20** avant le dénominateur. Le rapport ancien
`docs/03_decoupage_pax_candidates.md:429-445` affiche `4100/(2550−45)≈22`
alors que cette division vaut **1,64** : cet exemple historique est erroné
arithmétiquement, et son `deltaM=0,85` ne tient pas compte de la division
par les 20 tuiles de référence du code actif.

Sensibilité illustrative, capital différentiel **4 100 £**, 100 voyageurs/mois,
voie **45 £/tuile**, ROI cible **40 %**, rayon bus 3 (toutes ces hypothèses
sont affichées, **aucune n'est mesurée sur les 80 parties**) :

| Différentiel tarif RAIL–BUS **pour 20 tuiles** (£/passager) | Borne `roadMax` calculée |
|---:|---:|
| 0,25 | 7 (dénominateur négatif) |
| 0,50 | 136 |
| 1,00 | 39 |
| 2,00 | 16 |
| 4,00 | 7 |
| 8,00 | 7 (plancher géométrique) |

Le **7 observé** ne détermine pas la raison de ce plancher. La formule
route→rail considère une vitesse BUS à 80 % du maximum et une vitesse RAIL
effective calculée à 20 tuiles ; elle approxime l'écart de **tarif**,
pas le ROI complet des deux projets et ne peut remplacer l'arbitrage économique.

**Rail** : `OpexRailEffectiveSpeed` (`catalog.nut:127-219`) intègre déjà
l'accélération et le freinage, mais pas l'arrêt à quai. Le temps mécanique
de chargement/déchargement **est désormais déjà payé** par le modèle actif
`OpexRailStationDwellDays` (`economy.nut:80-99`, `:254-255`) :
`2 * 40 * ceil(capacité_par_wagon/5) / 74` jours par trajet chargé,
avec `v216f_dwell_pct=100` aux quatre niveaux (`info.nut:393-400`,
`settings.nut:109`). Exemple 40 unités/wagon : **8,65 j**. Pour le fret,
`loadDays = perTrain*30/monthlyUnits` (`economy.nut:363-379`)
agit **en plus seulement sur la note de station** via `effectiveHeadway` ;
il n'est pas ajouté aux rotations `tripsPerMonth`. Il représente une
attente de remplissage, distincte du temps mécanique.

**Air** : `OpexAirTripModel` et le cycle physique C121 n'ajoutent pas
explicitement de séjour de chargement. Un calcul documentaire du
chargement réel existe déjà dans
`sweeps/analyse_c121_air_economics_shadow.py:222-243` : source vanilla
OpenTTD 15.3, 20 ticks entre tranches, capacité PASS 20 et MAIL 5 par
tranche, PASS/MAIL en parallèle, déchargement puis chargement ;
`(1+20*max(ceil(PAX_A / (20 * départs)) + ceil(PAX_B / (20 * départs)),
ceil(MAIL_A/(5 * départs)) + ceil(MAIL_B/(5 * départs))))/74` jours
par visite (quantités mensuelles et départs mensuels). Exemple sans MAIL,
100 PASS/mois par extrémité et 5 départs/mois : **41/74 = 0,55 j par
visite** (deux visites par aller-retour) ; avec 2 départs/mois :
**121/74 = 1,64 j par visite**. Le replay source existant
(`:530-559`) referme le couplage chargement↔cadence, mais n'est pas le
code de production. C121 ajoute séparément les délais observés de hub
(`air_economics_c121.nut:225-253`), donc il faut contrôler leur périmètre
avant de rajouter encore de l'attente.

Le timetable antérieur (`docs/43_c121_air_economics_shadow_20260928.md:90-124`)
mesurait un résidu médian vol brut→parcours de **21,57 j**, avec congestion
et vieillissement des hubs. Ce résidu **ne mesure pas isolément**
15,13 j de manœuvres ni un temps de chargement, et ne justifie pas de
remplacer la cinématique physique sans validation indépendante.

## Formules minimales envisageables, à garder en observation

Au rafraîchissement annuel, réutiliser des grandeurs déjà connues et
calculer une seule fois `tauRail`, `tauAir`, `TfixeAIR` puis
`max(roadMax, min(railMax, TfixeAIR/(tauRail−tauAir)))`, avec traitement
explicite de `tauRail <= tauAir`. Pour la cohérence avec C121, ces trois
grandeurs devraient employer ensemble **vitesse avion directe, taxi 50,
proxy 2/3 et jours/tuile `1/(0,036*v)`**. La frontière ainsi obtenue
serait ~78 tuiles dans notre scénario, au lieu de 200. L'opération ne
coûterait en candidats que la lecture de `catalog.bounds` déjà effectuée.
La validité de la vitesse rail effective calculée à 20 tuiles pour d'autres
distances demeure une approximation à déclarer.

Il serait prématuré d'appliquer ces nombres comme filtres d'exclusion :
une égalité de **temps** ne garantit pas une égalité de **profit**, et
les nouveaux candidats AIR sur 62–199 n'ont pas de rendement observé
dans le banc. Les C100/C101 avaient déjà produit des pertes économiques
importantes en remplaçant la cinématique d'équipement AIR. Garder
la production AIR, ses profits, C121, la finance et le tri inchangés
tant qu'un contrefactuel complet n'a pas été testé.
