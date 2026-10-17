# Scores et estimateurs — découpage SE-01 à SE-08

<a id="reprise-par-microtaches"></a>
## Reprise par microtâches — décision utilisateur du 14/10

L'utilisateur reprend le travail en limitant chaque échange à un petit lot.
Cette demande rouvre la recherche, sans annuler les verdicts antérieurs.
Le travail restant est suivi dans [docs/taches.md](taches.md), § État courant.

**EST-01 terminé — vérifier le contrat de comparaison des profits rail.**
Lecture locale ciblée sur `master@36ef545`, sans banc ni changement de code :

- `economy.nut:319-324` : profit annuel prédit = recettes − fonctionnement − amortissement.
- `task_report.nut:277-285` : profit réalisé = somme de `GetProfitLastYear`
  des véhicules encore valides ; le coût ajouté vient de `GetRunningCost`
  au moment du rapport. La fenêtre et les véhicules couverts doivent être contrôlés.
- `task_report.nut:460-511` : `LINE_REVENUE` expose ces champs bruts ;
  `real_rev = profit + runCost` reste une reconstruction, pas la recette
  comptable observée pendant tout l'exercice.
- `task_report.nut:79-95` : C70 soustrait déjà `predAmort` et ramène le
  profit au nombre initial de véhicules. Ne pas corriger l'amortissement
  une seconde fois dans le score. Cette normalisation ne prouve pas à elle
  seule une composition stable pendant l'exercice.

**Conclusion bornée :** les ratios bruts du journal ne suffisent pas à
diagnostiquer une erreur de modèle. Ce n'est ni un nouveau bug démontré,
ni une explication des échecs économiques passés. La prochaine étape est
un seul cas fret avec exercice et flotte vérifiables ; arrêt sur champ manquant,
sans étendre la collecte. Aucune calibration ni amélioration revendiquée.

### EST-02 — terminé sur données insuffisantes, sans comparaison économique

Un seul corpus consulté : campagne `scores_c77_rail_alt_dev5x5_20261014`,
témoin `rail_alt_shadow`, graine **42**, répétition **0**.
Sources sous `results/scores_c77_rank2_policy_stage_20261014/results/` :
`scores_c77_rail_alt_dev5x5_20261014.manifest.json`, fichier `.jsonl` homonyme,
et `scores_c77_rail_alt_dev5x5_20261014_engine/rail_alt_shadow_seed42_r0.log`.
Empreinte du bundle dans le manifeste et les relevés :
`bca8f94fc7299868d82c82d6e66b6121908cba89475747da46079f9bafa6b9f7`.
Ce témoin expérimental instrumenté ne représente pas les défauts actuels de master.

**Constat vérifié :** télémétrie par ligne mensuelle active, mais
`decision_log=0` dans le manifeste ; aucun `RAIL_BUILD` ni `LINE_REVENUE`
dans le journal exact du témoin. Son premier relevé comportant du rail,
le **1971-02-01**, contient simultanément `rail|35,36` (véhicule 72)
et `rail|39,40` (véhicule 84). Les fiches donnent stations, véhicules,
capacités et profits courant/précédent, mais ni date exacte de construction,
ni prévision initiale, ni amortissement prédit, ni `lineId` Opex.
Leur ordre dans le tableau n'est pas une preuve d'ordre de construction.

**Arrêt prévu appliqué :** impossible d'identifier strictement la première
ligne fret chronologique et de calculer son écart comparable avec ces seules
fiches. Aucune autre graine ou campagne recherchée, aucun résultat choisi
sur son profit, aucun ratio calculé. Il manque d'abord la liaison
**stations/véhicule → état initial de ligne Opex** portant `lineId`, date,
prévision et amortissement ; la continuité de flotte sur l'exercice reste
ensuite à vérifier. L'absence dans cette exportation ne prouve pas
l'absence dans une éventuelle sauvegarde brute.

## Plan initial et provenance

<a id="est03-mesure"></a>
### EST-03 — pré-enregistrement du banc de mesure (14/10, avant lancement)

L'utilisateur demande de lancer directement les bancs nécessaires. Un premier
lot de collecte remplace l'inventaire de sauvegardes prévu :

- Campagne neuve `est03_rail_line_measure_42x4_20261014_r1`, graine 42,
  une répétition, **quatre ans**, un duel OpexAI/AAAHogEx, tous modes.
  Cet horizon vise le premier exercice civil complet d'une ligne rail bâtie
  après le démarrage AIR, et son rapport annuel suivant.
- Source : checkout principal `master@36ef545`, changements locaux documentaires
  seulement ; code réellement exécuté figé par le harnais. Docker local
  `desktop-linux`, aucune campagne active avant lancement, image exacte
  `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`,
  cache `openttd-lab-home`, dépôt Windows monté par le lanceur sous `/work`.
  Budget : un duel, plafond 10 CPU / 8 Go / swap total 8 Go, **un worker**,
  timeout moteur 1 800 secondes.
- Bras unique `OpexAI[probe_portfolio=1,probes=6]` : panneaux et journal de
  décision ; `probe_portfolio` expose aussi le C69 `phase=line_calib`
  contenant `pred_amort`, `trains0`, `vehs` et l'année réalisée. Aucun défaut
  modifié. Les sondes peuvent déplacer la trajectoire : pas de comparaison
  économique avec l'ancienne partie non instrumentée.
- Conserver logs, JSON/JSONL, manifeste, bundle et sauvegardes mensuelles.
  Succès de collecte : partie saine au terme prévu, premier `RAIL_BUILD`
  fret identifiable, rapport d'âge >=2 et prévision/amortissement disponibles.
  Vérifier ensuite la continuité de flotte avant tout ratio comparable.
  Si exposition absente ou erreur technique : constater la limite, sans
  sélectionner une autre graine pour obtenir un chiffre favorable.
- Diagnostic C66.3, **aucune porte A/B et aucun seuil d'adoption** ; l'option
  `signs20` est sans rôle décisionnel en l'absence de variante.

Commande prévue, depuis la racine :

```powershell
rtk proxy py -3 -X utf8 sweeps/run_c66_reference.py --campaign est03_rail_line_measure_42x4_20261014_r1 --container-name est03-rail-line-measure-r1 --policy-id est03_measure --reference "OpexAI[probe_portfolio=1]" --probes 6 --years 4 --seeds 42 --repeats 1 --max-workers 1 --cpus 10 --memory 8g --engine-timeout 1800 --decision-rule signs20 --primary-metric profit_year --line-telemetry --line-telemetry-monthly --retain-savegames results/est03_rail_line_measure_42x4_20261014_r1_saves
```

### Provenance du plan antérieur

<a id="est03-resultat"></a>
### EST-03 terminé — champs manquants collectés ; EST-04 — entrée C70 vérifiée

Le banc `est03_rail_line_measure_42x4_20261014_r1` est **complet et sain** :
un duel, 48 checkpoints jusqu'au 1973-12-01, 48 sauvegardes conservées,
aucune partie échouée ni erreur non attribuée. Bundle
`4c3952843092f5e76b18f83714b01083a2326995a46fe784c8fc730b9d44b174`.
Il a utilisé le plafond local **10 CPU / 8 Go** et un worker pour l'unique
partie. Pour un lot de plusieurs parties, jusqu'à **10 workers** sont autorisés.

La première construction rail est bien du fret charbon, **ligne 15**, bâtie
le **28 janvier 1971**, 52 tuiles, un train et deux wagons, dépense 43 092 £.
Le premier relevé rail ne contient que cette ligne (`rail|38,39`, train 84).
Prévision annuelle : recettes 30 192 £ − fonctionnement 2 531 £ −
amortissement 1 414 £ = **26 247 £**. L'exercice 1971 est partiel et n'est
pas utilisé comme année complète.

Le **31 mars 1972**, la ligne est doublée ; le relevé d'avril ajoute le
train 274 et la capacité passe de 60 à 120. Pour l'exercice complet **1972**,
le rapport du 24 janvier 1973 donne 32 693 £ de profit véhicule total,
`trains0=1`, `vehs=2`, `pred_amort=1414`. Au checkpoint février 1973,
les profits individuels de l'exercice précédent sont 20 537,304688 £ pour
le train 84 et 12 156,984375 £ pour le train 274. Le journal moteur somme
les valeurs entières renvoyées par l'API, d'où 32 693 £.

| Vue sur 1972 | Montant | Rapport au profit prédit initial |
|---|---:|---:|
| Profit du train initial moins amortissement prédit | 19 123,30 £ | 72,86 % |
| Entrée annuelle de calibration C70 : `32693 / 2 - 1414` | 14 932,50 £ | 56,89 % |

**EST-04 vérifie uniquement ce calcul et les empreintes des sources.** Le
second rapport n'est pas le facteur de mode publié : celui-ci agrège les
lignes et leurs exercices. Le premier rapport n'est pas non plus le
rendement d'une ligne restée à un train : doublage et second train ont pu
modifier le trafic. Cette mesure confirme le mélange de durées de présence
dans la normalisation, sans démontrer un correctif économique gagnant.
Elle ne rouvre pas les variantes P4 de cohortes/jours-véhicules déjà rejetées.

Preuves locales :
[reçu de collecte et relevés mensuels](../results/est03_rail_line_measure_42x4_20261014_r1_line15_receipt.json),
[contrôle du calcul C70](../results/est04_line15_c70_input_20261014.json),
[résultat et santé du banc](../results/est03_rail_line_measure_42x4_20261014_r1.json).
Les reçus portent les hashes des sources ; aucun code ni défaut modifié.

### Provenance conservée

<a id="est05-resultat"></a>
### EST-05 terminé le 15/10 — premier cas fret à flotte observée stable

Même campagne EST-03, même témoin et graine 42 ; aucune nouvelle partie.
Sélection chronologique indépendante du profit : ligne 15 écartée pour
doublement en 1972, puis **ligne 16**, charbon, construite le **13 février
1971**, 36 tuiles, un train, deux wagons, coût physique 40 196 £.
Les événements `STATION_FIRST_VEHICLE` relient explicitement `line=16`
au véhicule **102** et aux gares **40/41** (`rail|40,41`).

**Contrôle de composition :** 14 relevés mensuels du 1972-01-01 au
1973-02-01, mêmes gares, même véhicule 102, capacité 60 ; aucun événement
`RAIL_EXPAND` associé à cette ligne dans le journal. Le rapport C69 du
25 janvier 1973 confirme `age=2`, `trains0=1`, `vehs=1` pour l'exercice
**1972**, première année civile complète. Cette couverture ne prouve
pas l'absence absolue de mutations entre deux relevés.

| Mesure sur le même périmètre initial | £/an |
|---|---:|
| Profit prédit après amortissement | 21 855 |
| Profit véhicule réalisé, entier API | 17 802 |
| Amortissement prédit à retrancher | 1 414 |
| Réalisé après cet amortissement | **16 388** |
| Écart au prédit | **−5 467 (−25,01 %)** |

Le save de février 1973 donne 17 802,304688 £ avant amortissement, cohérent
avec l'entier journalisé. Recettes prévues : 25 800 £ ; reconstruction
`profit + coût annuel courant` : 20 333 £. Les coûts annuels courant et
prédit valent tous deux 2 531 £, mais cette reconstruction ne constitue
pas une mesure exacte des recettes encaissées sur l'exercice.

**Conclusion bornée :** un écart prévision/réalisé persiste à flotte
observée stable. Les changements de production, trafic, concurrence et
réseau restent possibles ; aucun défaut de formule ni coefficient 0,75
n'est établi. Ce cas ne rouvre pas V185, les seuils de distance ou P4.
Prochain petit diagnostic : vérifier le volume prévu/réalisé de cette
même ligne avant de discuter le paiement unitaire ou la calibration.

[Reçu, événements sourcés, 14 relevés et empreintes](../results/est05_stable_line16_20261015.json).
Hashes des sources EST-03 vérifiés, identités/capacité/période et cohérence
API/save contrôlées par assertions. Aucun code IA ni défaut modifié.

### Provenance du report initial

<a id="est06-resultat"></a>
### EST-06 terminé le 15/10 — volume prédit retrouvé, livraison non qualifiée

Lecture seule de deux sauvegardes EST-03, dates décodées **1972-01-01**
et **1973-02-01**, empreintes vérifiées contre `archive.json`. Réutilisation
du parseur `openttdlab.parse_savegame` employé par le harnais courant ;
aucun moteur lancé.

- Le panneau `OQ|16|86|1|2|60`, dont le format est vérifié dans le
  `task_rail.nut` du bundle, donne **86 tonnes de charbon par mois**,
  soit **1 032 t/an** prévues pour un train de deux wagons, capacité 60.
- `PT|16|86|120|14|63|3` donne fret offert **86 t/mois**, capacité
  calculée **120 t/mois**, intervalle prévu 14 jours et note prévue 63 %.
  Le modèle initial est donc limité par l'offre, pas par la capacité calculée.
- Les enregistrements véhicule/gare inspectés ne donnent pas directement
  un cumul annuel livré par cette ligne. `PLYR.old_economy.delivered_cargo`
  agrège la compagnie ; cargaison en attente, chargement et capacité
  ne mesurent pas des livraisons annuelles.
- Le graphe `LGRP` contient néanmoins une arête gare **40→41**, cargo 1,
  avec `usage=356` au 1973-02-01 et `last_compression=720456`. Ce champ
  est une **piste de mesure non qualifiée**, pas 356 tonnes annuelles
  livrées. Le helper `station_supply.py` mesure la capture via `supply`,
  autre grandeur ; il ne valide pas la sémantique livraison de `usage`.

**Arrêt du lot :** tonnage réellement livré en 1972 laissé inconnu,
aucun ratio volume réel/prévu fabriqué. Prochaine microtâche : vérifier
la mise à jour et la compression de `LGRP.edges.usage` dans OpenTTD 15.3,
avant de décider si les sauvegardes suffisent ou si une sonde est nécessaire.
Le champ requis reste une quantité livrée datée et attribuée à la ligne,
sans confondre départ, chargement, circulation et livraison finale.

[Reçu, champs inspectés et hashes des sauvegardes](../results/est06_line16_volume_observability_20261015.json).
Aucun réglage, modèle ou code IA modifié.

<a id="est07-resultat"></a>
### EST-07 terminé le 15/10 — compteur d'arrivée, cumul annuel non récupérable par simple différence

Intervention bornée, sans partie ni code IA modifié : lecture des sources
officielles **OpenTTD 15.3** et nouvelle extraction des deux saves EST-06.
Empreintes contrôlées contre `archive.json` et le reçu précédent ; même
graphe 26, cargo 1, gares 40/41 appartenant à OpexAI, mêmes positions.

**Sémantique établie :**

- `Vehicle::BeginLoading` appelle `IncreaseStats` à l'arrivée, avant
  `PrepareUnload`. Le compteur ne constate donc pas l'acceptation finale
  ni le paiement du fret. [Appel moteur](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/vehicle.cpp#L2287).
- Pour chaque élément du convoi ayant `refit_cap > 0`, l'incrément est
  `min(refit_cap, cargo.StoredCount())`. L'arête agrège tous les convois
  du même cargo entre ces gares ; elle n'identifie pas la ligne OpexAI.
  Les appels prédictifs de `LinkRefresher::RefreshStats` inspectés passent
  un usage nul. [Incrément](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/station_cmd.cpp#L4314),
  [rafraîchissement](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/linkgraph/refresh.cpp#L181).
- `LinkGraph::Compress` divise l'usage par deux avec arrondi entier.
  `last_compression` devient le milieu entre sa valeur précédente et
  la date économique courante : **ce n'est pas la date de l'événement**.
  Une fusion redimensionne aussi les compteurs importés selon l'âge
  des graphes. [Compression et fusion](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/linkgraph/linkgraph.cpp#L66).

| Save décodé | Usage 40→41 | `last_compression` |
|---|---:|---:|
| 1972-01-01 | 510 | 720068 |
| 1973-02-01 | 356 | 720456 |

**Conclusion :** ni 356 ni la différence −154 ne mesurent les tonnes
livrées en 1972. Les compressions empêchent la soustraction directe ;
le second point inclut aussi janvier 1973. Sans détail intermédiaire,
les incréments avant/après chaque division ne sont pas identifiables.
Le tonnage annuel livré reste `null` dans le reçu, sans ratio au prédit.

**Règle exploitable :** sur une arête persistante, mêmes gares et cargo,
sans compression, fusion/redimensionnement, recréation ni débordement,
la différence mesure exactement l'usage enregistré aux arrivées.
L'attribution à la ligne et l'équivalence à des livraisons demandent
encore les contrôles des véhicules, du déchargement et des bornes annuelles.
Prochaine microtâche EST-08 (2/5) : extraire les points mensuels existants
du 1972-01-01 au 1973-01-01, séparer les intervalles exacts des intervalles
compressés et établir un total d'arrivées ou ses bornes conditionnelles.
Ne pas appeler ce total « livré » sans preuve ; aucune sonde nouvelle à ce stade.

[Reçu, observations et empreintes des sources](../results/est07_usage_semantics_20261015/receipt.json).
Validation : deux saves redécodés, identité/propriété et hashes vérifiés
par assertions, références source et diff documentaire contrôlés.

<a id="est08-resultat"></a>
### EST-08 terminé le 15/10 — volume arrivé borné à partir des saves mensuels

Même campagne EST-03, ligne 16, graine 42 ; **aucune nouvelle partie**.
Treize saves du **1972-01-01 au 1973-01-01**, SHA-256 contrôlés contre
l'archive. Le parseur et les décodeurs physiques du harnais vérifient
les deux gares OpexAI, leurs dates de construction et positions, le graphe
26/cargo 1, le train 102 et ses éléments `[102, 103, 86]`, capacité 60.
Ces identités restent stables aux treize observations.

**Méthode :** pour les neuf intervalles sans compression, différence
`V − U` de l'usage. Pour chacun des trois autres, une seule compression
est compatible avec les dates : au moins 128 jours séparent deux
compressions sous la règle moteur de 256 jours, contre 31 jours au plus
entre ces saves. Le compteur final satisfait `V = floor((U + x) / 2) + y`,
où `x` et `y` sont les incréments avant/après compression. Le total
`x + y` est donc compris entre **`V − floor(U/2)` et `2V + 1 − U`**.
Les dates candidates de compression, déduites de `last_compression`,
sont compatibles avec les trois fenêtres. Arrondis et bornes vérifiés
par énumération indépendante de 1 040 couples de petits entiers.

| Intervalle entre premiers du mois | Usage début → fin | Compression | Arrivées enregistrées, t |
|---|---:|---|---:|
| Janvier → février 1972 | 510 → 570 | non | 60 |
| Février → mars | 570 → 690 | non | 120 |
| Mars → avril | 690 → 405 | oui | 60–121 |
| Avril → mai | 405 → 525 | non | 120 |
| Mai → juin | 525 → 585 | non | 60 |
| Juin → juillet | 585 → 645 | non | 60 |
| Juillet → août | 645 → 412 | oui | 90–180 |
| Août → septembre | 412 → 472 | non | 60 |
| Septembre → octobre | 472 → 472 | non | 0 |
| Octobre → novembre | 472 → 532 | non | 60 |
| Novembre → décembre | 532 → 296 | oui | 30–61 |
| Décembre → janvier 1973 | 296 → 356 | non | 60 |
| **Total conditionnel** | | | **780–962** |

Contre **1 032 t/an prévues**, l'usage aux arrivées représente **75,58–93,22 %**,
soit un déficit de **6,78–24,42 %**, si les hypothèses de continuité tiennent.
Les neuf intervalles directs totalisent 600 t ; les trois compressés,
180–362 t. Ce sont des **bornes algébriques**, pas un intervalle de confiance.
Ne pas imposer des multiples de 60 : la capacité du train ne prouve pas
qu'il était plein à chaque arrivée.

**Limites :** absence supposée de recréation d'arête, fusion/redimensionnement,
changement de date ou débordement entre relevés ; les observations ne
prouvent pas cette continuité à chaque tick. L'arête agrège ses véhicules.
Le compteur est plafonné par `refit_cap` et précède le déchargement : le
tonnage finalement livré reste inconnu. Les saves affichent tous une fraction
calendaire 0 et une fraction économique 73 au jour précédent ; ces champs
sont conservés, sans présumer une égalité exacte avec la clôture comptable.
Le déficit de volume est désormais chiffré sous ces réserves ; il ne prouve
ni la cause des −25,01 % de profit, ni une correction d'estimateur à adopter.

**Prochaine microtâche EST-09 (2/5) :** exploiter ces mêmes saves pour mesurer
ou borner le fret capté à la gare source 40 (`supply`, helper existant)
et relever le stock en attente. Comparer offre prévue/capture/arrivées
pour distinguer manque de fret disponible et difficulté à l'acheminer,
sans assimiler capture, stock et débit ni ajouter une sonde.

[Reçu complet, hashes, dates et intervalles](../results/est08_line16_monthly_usage_20261015/receipt.json),
[script de reproduction hors moteur](../results/est08_line16_monthly_usage_20261015/analyze.py).
Contrôles ci-dessus et `git diff --check` réussis ; aucun code IA ni défaut modifié.

<a id="est09-resultat"></a>
### EST-09 terminé le 15/10 — capture inférieure au prévu, stock source en baisse

Lecture des mêmes **13 saves**, gare source 40, charbon de la ligne 16.
Hashes, dates, identité/propriété de la gare, graphe et cargo vérifiés.
Réutilisation de `station_supply.extract_station_supply` et `supply_intervals` :
neuf différences de capture exactes sous continuité, trois intervalles
compressés laissés inconnus par le helper puis **bornés séparément** avec
la formule EST-08 et ses hypothèses. Le helper de production est inchangé.

**Capture annuelle conditionnelle : 562–659 t**, soit **54,46–63,86 %** des
**1 032 t prévues** ; déficit de **36,14–45,54 %**. Les neuf intervalles
directs totalisent 467 t et les trois compressés 95–192 t. Le fret capté
mesure l'allocation à cette gare, pas la production totale de la mine.

Le stock est décodé dans `STNN.goods[cargo].cargo` puis `CAPA`, en sommant
`count` des paquets référencés. La référence sérialisée vaut **index + 1** ;
`CAPY` contient les paiements, pas les paquets. Les paquets présents sont
tous rattachés à la gare source 40. Le fret réservé au chargement est
compté séparément du disponible, conformément aux sources OpenTTD 15.3 :
[références](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/saveload/saveload.cpp#L1239),
[paquets](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/saveload/cargopacket_sl.cpp#L131),
[stock disponible/réservé](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/cargopacket.h#L573).

| Date du save | Capté depuis le save précédent, t | Disponible en gare, t | Réservé, t |
|---|---:|---:|---:|
| 1972-01-01 | — | 207 | 0 |
| 1972-02-01 | 98 | 245 | 0 |
| 1972-03-01 | 56 | 241 | 0 |
| 1972-04-01 | 39–78 | 164 | 0 |
| 1972-05-01 | 40 | 144 | 0 |
| 1972-06-01 | 45 | 69 | 20 |
| 1972-07-01 | 44 | 53 | 0 |
| 1972-08-01 | 28–57 | 33 | 0 |
| 1972-09-01 | 42 | 15 | 0 |
| 1972-10-01 | 45 | 0 | 0 |
| 1972-11-01 | 47 | 5 | 0 |
| 1972-12-01 | 28–57 | 0 | 20 |
| 1973-01-01 | 50 | 22 | 0 |

**Lecture bornée :** le stock disponible baisse de 207 à 22 t, après un
pic observé de 245 t ; il est entièrement vide au relevé d'octobre.
En décembre, zéro disponible ne signifie pas zéro stock : **20 t sont
réservées**. Les 780–962 t enregistrées aux arrivées peuvent aussi provenir
du stock constitué avant 1972. Ce n'est pas un bilan fermé : chargement
embarqué aux bornes et pertes ne sont pas reconstitués ; la baisse du stock
ne peut pas être attribuée intégralement au transport.

La capture inférieure à l'offre prévue est établie sous les réserves EST-08.
Cela oriente le diagnostic vers l'offre effectivement captée, **sans exclure
un effet du service sur la note de gare et donc sur la capture**. Ces points
mensuels ne prouvent pas l'absence de goulot d'acheminement. Production,
concurrence et note restent à distinguer ; aucune cause unique des −25,01 %
de profit, aucun nouveau coefficient ni réglage adopté.

**Prochaine microtâche EST-10 (2/5) :** identifier la mine source puis relever
sa production mensuelle de charbon et la note de la gare 40 sur les mêmes
saves. Comparer leur évolution à la capture, sans assimiler la production
de la mine à l'offre reçue par OpexAI ni déduire une causalité de la corrélation.

[Reçu et contrôles](../results/est09_line16_source_supply_20261015/receipt.json),
[script reproductible hors moteur](../results/est09_line16_source_supply_20261015/analyze.py).
Validation : 13 hashes/dates/identités, références et origines des paquets,
bornes des trois compressions par énumération, tests ciblés du helper et
`git diff --check`. Aucun nouveau banc, code IA ou défaut modifié.

<a id="est10-resultat"></a>
### EST-10 terminé le 15/10 — production, note et allocation totale de la mine

La source est **l'industrie 13**, tuile **19055**, identique au `src` du
`RAIL_BUILD` de la ligne 16. Tous les paquets source inspectés dans EST-09
portent `source_type=Industry`, `source_id=13`, cargo charbon ; identité,
position et date de construction de la mine restent stables.

**Mois clos :** les saves au premier jour calendaire précèdent encore le
changement de mois économique. `history[0]` n'est donc pas utilisé comme
mois clos. Lecture de `history[LAST_MONTH=1]` avec bit de validité, date
économique et contrôle de rotation sur le save précédent ; le save déjà
archivé du **1973-02-01** clôt décembre 1972. Au total, **14 saves vérifiés**,
aucune nouvelle partie. [Historique](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/misc/history_type.hpp#L45),
[rotation économique](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/industry_cmd.cpp#L2566).

Le champ industriel `transported` compte ici le fret **alloué aux gares**,
toutes compagnies confondues, par `MoveGoodsToStation` ; il ne mesure ni
le chargement d'OpexAI ni une livraison finale.
[Mise à jour moteur](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/industry_cmd.cpp#L539).

| Mois 1972 | Production mine, t | Alloué à toutes les gares, t | Capté gare 40, t (EST-09) | Note gare 40 au save suivant, % API |
|---|---:|---:|---:|---:|
| Janvier | 135 | 98 | 98 | 73 |
| Février | 117 | 84 | 56 | 71 |
| Mars | 117 | 92 | 39–78 | 70 |
| Avril | 104 | 89 | 40 | 70 |
| Mai | 117 | 100 | 45 | 68 |
| Juin | 117 | 96 | 44 | 70 |
| Juillet | 117 | 84 | 28–57 | 68 |
| Août | 117 | 84 | 42 | 72 |
| Septembre | 117 | 95 | 45 | 77 |
| Octobre | 117 | 96 | 47 | 80 |
| Novembre | 104 | 85 | 28–57 | 78 |
| Décembre | 117 | 94 | 50 | 78 |
| **Total** | **1 396** | **1 097** | **562–659** | — |

La production passe de 135 t en janvier à 117 t la plupart des mois,
104 t en avril/novembre ; taux interne 15→13. La note aux treize relevés
encadrant l'année est **68–80 %**, contre **63 % prévus** ; ce sont des
instantanés, pas des moyennes mensuelles. La conversion suit exactement
`GetCargoRating`/`ToPercent8`, `rating * 101 >> 8`.
[API](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_station.cpp#L149),
[conversion](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/core/math_func.hpp#L285).

**Conclusion bornée :** la production observée baisse modérément et les
notes relevées dépassent le prévu. Ces constats orientent vers la répartition
du fret entre gares, sans exclure des variations entre relevés.
L'allocation totale aux gares dépasse les 1 032 t prévues pour la ligne,
mais la gare 40 n'en reçoit qu'une partie. La différence **438–535 t**
est un **solde conditionnel à attribuer**, pas une quantité déjà prouvée
chez AAAHogEx. Les hypothèses EST-08/09 restent applicables ; pas de
causalité du profit, de tonnage finalement livré ni de correction adoptée.

**Limitation du helper découverte :** `bench_v2.station_ratings` est appelé
sur la gare 40 et renvoie une liste vide. Il filtre le bit 0 (`Acceptance`)
alors que cette source a le bit 1 (`Rating`) et `status=2`. La lecture
ciblée utilise ici la propriété de la gare vérifiée par `decode_stations`,
le bit `Rating` et la formule API sourcée ; aucun zéro de remplacement.
Le helper reste inchangé, correction ciblée à suivre séparément.

**Prochaine microtâche EST-11 (2/5) :** rechercher dans les saves les autres
gares recevant du charbon de la mine 13, leur propriétaire et leur première
apparition observée. Vérifier la répartition avant d'accuser la concurrence
ou de modifier l'estimation d'offre ; ne pas attribuer tout le solde à une
gare sur la seule présence de paquets.

[Reçu, sources et mois clos](../results/est10_line16_mine_rating_20261015/receipt.json),
[script hors moteur](../results/est10_line16_mine_rating_20261015/analyze.py).
Validation : hashes des 14 saves et des sources, identité mine/gare,
validité et rotation des douze mois, totaux et notes API vérifiés par
assertions ; diff documentaire contrôlé. Aucun code IA ou défaut modifié.

<a id="est11-resultat"></a>
### EST-11 terminé le 15/10 — seconde gare bénéficiaire identifiée chez AAAHogEx

Les **14 saves EST-10** sont relus et vérifiés contre l'archive. Tous les
paquets `CAPA` issus de `source_type=Industry`, `source_id=13` sont examinés,
y compris ceux hors gare, pour éviter de manquer un bénéficiaire dont le
quai est vide. La mine ne produit que le cargo 1, charbon, dans ces saves.
Le champ `CAPA.source` est la **première gare réceptrice**, distincte de
l'industrie d'origine et de l'emplacement actuel du paquet. Sémantique
déjà vérifiée dans les sources OpenTTD 15.3 d'EST-09.

**Deux premières gares réceptrices observées :**

| Gare | Propriétaire vérifié (`AIPL`) | Tuile | Construction enregistrée | Première présence dans la fenêtre | Premier paquet mine 13 observé dans la fenêtre |
|---|---|---:|---|---|---|
| 40 | OpexAI, compagnie 0 | 19309 | 1971-02-10 | 1972-01-01 | 1972-01-01 |
| **89** | **AAAHogEx, compagnie 1** | **18545** | **1972-01-21** | **1972-02-01** | **1972-03-01** |

Les deux sont des gares ferroviaires ; propriétaire, position et date de
construction restent stables. Les décodeurs physiques valident leurs
identités et les noms d'IA sont lus dans chaque save, sans présumer la
correspondance des compagnies. Aucun troisième bénéficiaire n'apparaît
dans les paquets conservés de ces quatorze relevés.

Au **1972-02-01**, la gare 89 existe mais son charbon a `status=0`, aucun
paquet et aucun nœud `LGRP` ; aucun paquet de la mine 13 ne la désigne
ailleurs dans le save. Au **1972-03-01**, six paquets totalisent **28 t**
ayant cette gare comme première réceptrice. C'est un **stock présent au
relevé**, pas un cumul annuel capté. Des paquets la désignent ensuite
dans les douze relevés de mars 1972 à février 1973 inclus.

**Conclusion :** une concurrence réelle pour le charbon de cette mine
est confirmée, chez AAAHogEx. La gare concurrente est construite après la
ligne Opex du **13 février 1971** et sa prévision initiale. Ce cas ne prouve
donc pas que l'estimateur ignorait dès l'origine un concurrent déjà présent.
Il expose un changement de concurrence pendant la période comparée.

**Limites :** date de construction, première présence et premier paquet
observé sont trois dates distinctes. Les snapshots ne donnent pas le
premier instant exact de capture et peuvent manquer des bénéficiaires
transitoires dont les paquets ont déjà disparu. Le solde **438–535 t**
d'EST-10 reste **non attribué quantitativement** : ne pas le verser en
bloc à la gare 89, ni additionner les stocks successifs. Pas de mesure
de livraison finale ni de verdict causal sur le profit.

**Prochaine microtâche EST-12 (2/5) :** mesurer ou borner la capture de la
gare 89 avec les compteurs mensuels `LGRP` existants, en contrôlant création,
identité et compressions. Comparer ensuite au solde EST-10, en conservant
l'inconnu lorsqu'une borne manque ; aucun nouveau banc ni changement IA.

[Reçu, identités, paquets et chronologie](../results/est11_mine13_recipient_stations_20261015/receipt.json),
[script de reproduction hors moteur](../results/est11_mine13_recipient_stations_20261015/analyze.py).
Validation : hashes des 14 saves, sources de décodage, mine/cargo, gares,
propriétaires, noms d'IA et stabilité vérifiés ; diff documentaire contrôlé.

<a id="est12-resultat"></a>
### EST-12 terminé le 15/10 — capture de la gare concurrente et bilan de répartition

Même campagne figée **`est03_rail_line_measure_42x4_20261014_r1`**, mêmes
14 sauvegardes, branche `master` / HEAD `36ef545`, modifications documentaires
locales conservées. Aucune nouvelle partie. Le diagnostic réutilise
`extract_station_supply` et `bounded_intervals` des harnais courants.

La gare **89 appartient à AAAHogEx**, compagnie 1, tuile 18545, construction
le 21 janvier 1972. À partir de mars, son charbon est suivi dans le graphe
**1**, membres **89/90**, sans changement observé d'identité ou de membres.
Tous les paquets conservés dont la première gare est 89 désignent la mine
13 comme origine. Cela contrôle l'attribution observée ; le compteur de
gare agrège néanmoins toutes les sources de charbon et ne prouve pas
l'absence de sources transitoires entre deux saves.

| Mois 1972 | Alloué par la mine, t | Capté gare 40 Opex, t | Capté gare 89 AAAHogEx, t |
|---|---:|---:|---:|
| Janvier | 98 | 98 | inconnu ; modèle de démarrage : 0 |
| Février | 84 | 56 | inconnu ; modèle de démarrage : 28 |
| Mars | 92 | 39–78 | 49 |
| Avril | 89 | 40 | 49 |
| Mai | 100 | 45 | 55 |
| Juin | 96 | 44 | 52 |
| Juillet | 84 | 28–57 | 44 |
| Août | 84 | 42 | 42 |
| Septembre | 95 | 45 | 50 |
| Octobre | 96 | 47 | 30–60 |
| Novembre | 85 | 28–57 | 40 |
| Décembre | 94 | 50 | 44 |

**Mesure à deux bornes présentes : mars–décembre, 455–485 t pour la gare 89.**
Neuf différences sont exactes sous continuité ; octobre comprend une
compression, compteur **369→214**, borne **30–60 t**. Le helper contrôle
les dates, l'identité et la compatibilité avec une seule division entière
par deux. Ces bornes ne sont pas un intervalle de confiance ; elles
conservent les hypothèses EST-08/09 d'absence de remise à zéro, transfert
de graphe ou activité transitoire invisible.

**Démarrage traité séparément :** en janvier, la gare n'existe pas au
premier relevé ; en février elle existe mais `status=0`, sans nœud ni
paquet. En mars, le nœud a `supply=28` et une référence de compression au
**9 février 1972**. Le moteur initialise le nœud à zéro et le graphe à la
date courante ; la réception de fret alimente `supply`.
[Initialisation](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/linkgraph/linkgraph.cpp#L29),
[création du graphe](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/linkgraph/linkgraph.h#L197),
[réception](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/station_cmd.cpp#L4401).
Sous l'hypothèse supplémentaire d'une première activation sans compteur
perdu, échec d'allocation de graphe, service transitoire ni fusion cachée,
cela donne **0 t en janvier et 28 t en février**. Les soldes industriels
des deux mois concordent, sans prouver à eux seuls cette continuité.
Le reçu conserve **`annual_capture_station89=null`** pour le résultat
strict et range ce modèle dans un champ distinct.

Avec ce modèle de démarrage et l'attribution à la seule mine 13,
**483–513 t sur l'année**, soit **44,0–46,8 % des 1 097 t allouées aux gares**
ou **34,6–36,7 % des 1 396 t produites**. Ne pas confondre ces dénominateurs.
Les **six mois exacts des deux côtés** (avril, mai, juin, août, septembre,
décembre) vérifient `capture40 + capture89 = allocation_mine13` sans résidu.
Tous les autres mois restent compatibles avec ce bilan dans leurs bornes,
y compris le démarrage sous les hypothèses explicites ci-dessus.

**Conclusion :** la capture adverse est compatible avec le solde annuel
**438–535 t** d'EST-10. La concurrence contribue à la répartition observée ;
ce n'est pas une mesure du tonnage qu'Opex aurait capté en solo, ni une
attribution causale de l'écart de profit. L'idée utilisateur de distinguer
calibration solo et concurrence reste une hypothèse de méthode : aucun
coefficient de perte, changement de score ou défaut adopté.

**Prochaine microtâche EST-13 (2/5) :** mesurer l'offre captée par la gare
40 avant l'entrée effective observée du concurrent, dans les saves de mars
1971 à février 1972. Contrôler identité/flotte, concurrence locale observée,
production contemporaine et prévision de 86 t/mois sur la même durée,
sans annualiser une période incomplète. Cette période locale ne remplace
pas un contrefactuel solo ; pas de nouvelle campagne à ce lot.

[Reçu et détail des hypothèses](../results/est12_station89_capture_20261015/receipt.json),
[script hors moteur](../results/est12_station89_capture_20261015/analyze.py).
Validation : hashes des 14 saves, archive, reçus et sources ; assertions
d'identité, dates, origine et bilan mensuel ; **13 tests ciblés** des helpers
`station_supply`/`station_supply_bounds` réussis ; diff documentaire contrôlé.
Aucun code IA, harnais ou réglage modifié.

<a id="est13-resultat"></a>
### EST-13 terminé le 15/10 — l'offre captée avant concurrence dépasse la prévision

Après la nouvelle demande « Reprends », lecture des saves du **1er mars 1971
au 1er février 1972**, soit **onze mois** (mars 1971–janvier 1972).
Le save du 1er mars 1972 sert seulement à fermer l'historique économique
de janvier : **13 saves vérifiés**, aucune nouvelle partie. Campagne et
bundle EST-03 inchangés (`4c395284…b174`, code source historique `36ef545`).
Le checkout a avancé en parallèle sur `master` à **`d524b651`** pendant
la reprise ; les helpers employés ont les mêmes hashes qu'en EST-12.
Ces résultats ne qualifient pas les défauts plus récents du checkout.
La mise à jour du backlog est limitée au suivi EST ; les autres travaux
présents dans `docs/taches.md` sont conservés.

**Comparabilité observée :** train 102, chaîne `[102,103,86]`, capacité
charbon **60 t**, gares 40/41, graphe 26 et membres inchangés aux relevés.
Les panneaux conservent l'offre prévue **86 t/mois**, la capacité calculée
**120 t/mois** et la note prévue **63 %**, dès le premier save de la fenêtre.
Tous les paquets conservés issus de la mine 13 ont la gare 40 comme première
réceptrice sur les douze bornes ; tous ceux dont la première gare est 40
proviennent de cette mine. La gare adverse 89 apparaît à la dernière borne,
sans activité charbon (`status=0`, aucun graphe). Le save supplémentaire
de mars, où elle reçoit du fret, est exclu de la fenêtre de capture.
Cela établit une période **sans concurrence locale observée**, pas une
partie solo ni l'absence prouvée de tout bénéficiaire transitoire.

| Mesure sur les onze mois | Résultat |
|---|---:|
| Offre prévue, 86 × 11 | **946 t** |
| Capture gare 40, bornes sous continuité | **1 158–1 247 t** |
| Écart à la prévision | **+22,4 à +31,8 %** |
| Production mine 13, mois clos valides | **1 579 t** |
| Allocation de la mine à toutes les gares | **1 158 t** |
| Notes gare 40 aux douze bornes, API | **72–74 %** |
| Stock disponible gare 40, début → fin | **0 → 245 t** |

Dix intervalles sont exacts sous continuité. **Novembre 1971** contient
une compression : **88–177 t**. Les dix différences exactes égalent
l'allocation industrielle du mois ; les **88 t** allouées en novembre
sont dans la borne. Sans ajouter une hypothèse de bilan fermé et d'origine
exclusive entre relevés, le reçu conserve la borne haute **1 247 t**.
Les réservations sont nulles aux douze bornes ; le stock final n'est pas
assimilé à une perte ou à une preuve suffisante de saturation permanente.

**Conclusion bornée :** sur cette période, l'offre captée n'est pas
surestimée par les 86 t/mois initiaux. Une baisse uniforme de cette offre
« pour calibrer le modèle de base » irait dans le mauvais sens sur ce cas.
La note observée dépasse la prévision et le fret s'accumule en gare : il
reste à mesurer ce qui arrive à destination. Cela ne valide ni temps de
trajet, ni revenu, ni profit, et ne transforme pas les effets de concurrence
EST-12 en coefficient causal. Aucun ratio de profit annuel n'est calculé
sur ces onze mois ; aucune extrapolation à douze mois.

**Prochaine microtâche EST-14 (2/5) :** borner le volume arrivé enregistré
sur l'arête 40→41 pendant les mêmes onze mois, avec la sémantique d'EST-08.
Comparer ce flux à la capture et à la prévision, tout en conservant les
inconnues de stock embarqué, de pertes et de livraison finale. Aucun
nouveau banc ni changement d'estimateur à ce lot.

[Reçu et détail mensuel](../results/est13_station40_before_competition_20261015/receipt.json),
[script hors moteur](../results/est13_station40_before_competition_20261015/analyze.py).
Validation : hashes des 13 saves, archive, sources et helpers inchangés ;
identités, flotte, panneaux prévisionnels, origines, dates, rotation des
mois clos et concordance des dix mois exacts contrôlés par assertions.
Les **13 tests des helpers réussis en EST-12** s'appliquent aux mêmes fichiers ;
diff et liens documentaires contrôlés. Aucun code IA ou harnais modifié.

<a id="est14-resultat"></a>
### EST-14 terminé le 15/10 — arrivées avant concurrence compatibles avec la prévision

Même ligne 16, train 102, gares **40→41**, cargo charbon, du **1er mars 1971
au 1er février 1972** : onze mois, **12 saves existants**, aucune nouvelle
partie. La méthode de différence et de compression est celle d'EST-08,
avec les décodeurs physiques du harnais. Archive, reçus, sources moteur et
saves sont vérifiés par SHA256. `master` reste à `d524b651` pour l'analyse ;
le code réellement joué est le bundle historique EST-03 `4c395284…b174`.

Le graphe 26, ses membres 40/41, les identités/propriétaires des gares et
la chaîne `[102,103,86]` de **60 t** restent identiques aux bornes. L'arête
40→41 existe dès mars, avec `usage=0`, puis atteint **570** en février.
La différence brute 570 n'est pas un total, car une compression intervient
en novembre 1971 : **660→450**, soit **120–241 t** sous le modèle d'une
division entière par deux. Les dix autres intervalles totalisent **780 t**.

| Mesure sur les mêmes onze mois | Résultat |
|---|---:|
| Volume prévu, 86 × 11 | **946 t** |
| Arrivées enregistrées, bornes sous continuité | **900–1 021 t** |
| Écart à la prévision | **−4,9 à +7,9 %** |
| Capture à la gare source, EST-13 | **1 158–1 247 t** |
| Capture moins arrivées, bornes conservatrices | **137–347 t** |
| Hausse du stock disponible en gare source | **245 t** |

**Conclusion :** la prévision de 946 t appartient à la fourchette observée.
Ce cas avant concurrence locale observée ne démontre donc pas un biais
du volume transporté prévu, malgré une capture supérieure à la prévision.
La hausse du stock est compatible avec l'écart capture–arrivées, mais
ne ferme pas le bilan : après sa soustraction, la fourchette résiduelle
est **−108 à +102 t**. Ce résidu n'est ni une mesure de pertes ni une
quantité à corriger ; stocks embarqués aux bornes, pertes et déchargement
restent à distinguer. Les deux compteurs partagent une compression :
leurs bornes peuvent être corrélées, leur soustraction est conservatrice.

**Limites conservées :** `usage` compte la cargaison à l'arrivée avant
déchargement, plafonnée par `refit_cap` par élément de rame ; il ne prouve
pas une livraison finale payée. L'arête agrège les véhicules qui la servent.
L'absence de recréation/fusion, remise à zéro, débordement ou contributeur
transitoire invisible reste supposée entre snapshots. Aucun profit annuel
n'est calculé sur ces onze mois, aucune équivalence économique ni correction
globale d'estimateur n'est démontrée. La capacité théorique de **120 t/mois**
ne devient pas une mesure de débit disponible du seul fait de ce diagnostic.

**Prochaine microtâche EST-15 (2/5) :** rechercher une mesure qualifiable de
durée de rotation du train 102 dans les saves/journaux existants, puis la
comparer au service prévu par le modèle. Séparer trajet, attente/chargement
et distances ; arrêter sur donnée manquante. Aucun nouveau banc ni changement
de formule à ce lot.

[Reçu et onze intervalles](../results/est14_line16_precompetition_arrivals_20261015/receipt.json),
[script hors moteur](../results/est14_line16_precompetition_arrivals_20261015/analyze.py).
Validation : 12 hashes/dates/identités/rame, continuité observée du graphe,
compatibilité des dates avec une seule compression ; **1 040 cas entiers**
de bornage contrôlés par énumération indépendante, plus le cas réellement
observé en novembre ; diff documentaire et liens vérifiés. Aucun code IA,
harnais ou réglage modifié.

<a id="est15-resultat"></a>
### EST-15 terminé le 15/10 — séjours en gare absents du cycle explicite de capacité

Même fenêtre **mars 1971–janvier 1972**, douze saves et mêmes identités.
Analyse sur `master` **`d524b651`**, bundle réellement joué EST-03
`4c395284…b174` / code historique `36ef545`. Le modèle est lu dans ce
bundle et vérifié contre son manifeste, sans modifier le code actuel.
Les protections C41 sur la vitesse effective, la croisière et l'accélération
ont été relues ; aucun remplacement par une formule de vitesse maximale.

**La bonne donnée est dans `ORDL`, pas dans `round_trip_time`.** La référence
du véhicule 102 vaut 26 et désigne la liste d'ordres 25 (`REF_ORDERLIST`, index
augmenté de 1). Deux ordres desservent 40 et 41 ; les drapeaux de temps imposé, bits
3 et 7, sont absents. `UpdateVehicleTimetable` enregistre alors les dernières
durées achevées de trajet et de séjour, arrondies vers le haut à **37 ticks**.
Les dates et compteurs des saves vérifient **74 ticks par jour économique**.
[Actualisation automatique](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/timetable_cmd.cpp#L469),
[drapeaux](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/order_base.h#L189),
[horloge](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/timer/timer_game_tick.h#L75).

Mars 1971 contient encore quatre valeurs nulles : relevé **incomplet**, pas
un trajet instantané. Les **onze relevés complets d'avril à février** donnent
les mêmes composantes :

| Composante mémorisée | Ticks | Jours, après arrondi moteur |
|---|---:|---:|
| Trajet vers 40 (retour) | 555 | **7,5** |
| Séjour en gare 40 | 259 | **3,5** |
| Trajet vers 41 (aller) | 592 | **8,0** |
| Séjour en gare 41 | 259 | **3,5** |
| Somme des composantes | 1 665 | **22,5** |

Ce sont les dernières composantes stockées, **pas onze rotations distinctes**
ni une moyenne temporelle. Leur somme peut réunir des segments de rotations
différentes. En retirant uniquement l'incertitude d'arrondi, les sommes des
durées sous-jacentes sont **14,53–15,5 j de trajet**, **6,03–7 j en gare**,
soit **20,55–22,5 j** au total. Ce ne sont pas des intervalles de confiance
ni les bornes d'un cycle réellement apparié. Le séjour comprend chargement,
déchargement et attente ; leur décomposition reste à établir.

**Comparaison au modèle figé :** un train de 60 t, panneau capacité 120 t/mois
et headway 14 j, ces deux derniers tronqués à l'entier. La formule fret
`60 × 30 / roundTripDays` et `roundTripDays = 2 × oneWayDays` placent le cycle
modélisé dans **(14,876 ; 15) jours**. Aucun temps de séjour explicite n'y est
ajouté. Le `loadDays` du modèle agit sur l'absence de ramassage, donc la note
et l'offre captée, **pas sur cette capacité**. Le trajet pur reste compatible
avec les composantes mémorisées ; les séjours constituent une omission
explicite et une piste mesurable. À titre de conversion seulement, la somme
des composantes donne **80–87,6 t par mois de 30 jours**, pas un débit validé.

**Autres compteurs écartés :** `round_trip_time` et le départ de régulation
restent nuls dans les douze saves ; ce champ est alimenté par les ordres de
régulation au dépôt, pas par chaque rotation ordinaire. `last_loading_tick`
ne conserve que le dernier départ et `current_order_time` la phase courante.
Le graphe `travel_time_sum/capacity` peut mêler estimations initiales et
capacité artificielle pendant chargement : il ne fournit pas une mesure
indépendante de rotation. Les deux événements `STATION_FIRST_VEHICLE` ne
décrivent que les premières visites. Le reçu conserve donc
**`exact_paired_rotation_days=null`**.
[Régulation au dépôt](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/vehicle.cpp#L1641),
[statistiques estimées du graphe](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/linkgraph/refresh.cpp#L208).

**Limite causale :** ni une constante universelle de 7 j, ni un changement
de vitesse ou de score ne sont qualifiés par cette ligne. La distance 36
du panneau est celle du candidat ; les tuiles de gares ne donnent pas à
elles seules la longueur du rail construit. Cette longueur n'est pas
mesurée ici. Le profit et les arrivées EST-14 ne prouvent pas que cette
omission explique à elle seule l'écart économique.

**Prochaine microtâche EST-16 (2/5) :** expliquer les séjours par les règles
de chargement/déchargement, la capacité et la vitesse de chargement des
wagons et la longueur de quai ; séparer l'attente de production. Chercher
une correction calculable avant construction, sans implémentation ni banc
dans ce lot, et sans transformer les 7 j observés en constante arbitraire.

[Reçu et douze relevés](../results/est15_line16_rotation_observability_20261015/receipt.json),
[script hors moteur](../results/est15_line16_rotation_observability_20261015/analyze.py).
Validation : hashes de l'archive, des saves, du manifeste, du modèle figé,
des sources OpenTTD 15.3 et du journal ; décodeurs physiques, référence des
ordres, drapeaux, phases, arrondis et conversion des deux horloges contrôlés.
Diff et liens vérifiés ; aucun code IA, harnais ou réglage modifié.

<a id="est16-resultat"></a>
### EST-16 clos le 15/10 — composante mécanique du séjour, limites explicites

Lot borné de complexité **2/5**, terminé à la demande « Finis », sans lancement
de la suite. Même campagne EST-03 et même bundle historique qu'EST-15 ; analyse
sur `master` `d524b651`. Aucun changement de formule ou de défaut courant.

**Entrées vérifiées dans les douze saves :** train 102, locomotive 23 sans
capacité, wagons 103 et 86 de modèle 29, chacun de **30 t de charbon** ;
`order.gradual_loading=1`, pénalité de quai activée et **aucun NewGRF**.
Gares 40 et 41 : rectangles **1×3 et 3×1**, propriétaire OpexAI. Le nombre
de véhicules et la composition proviennent du décodeur physique existant.

**Mécanisme OpenTTD 15.3 :** le wagon standard charge/décharge **5 unités par
tranche**. Tous les wagons sont parcourus au même passage, puis le train
attend **40 ticks** avant le passage suivant. Deux wagons de 30 t demandent
donc **six passages parallèles**, pas douze. Une rame dépassant le quai
subit une pénalité ; elle n'est pas attendue ici pour trois véhicules
standards sur trois tuiles. L'attente d'une production insuffisante sous
ordre de pleine charge est un mécanisme distinct.
[Wagons standards](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/table/engines.h#L44),
[chargement](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/economy.cpp#L1660),
[temporisation](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/economy.cpp#L1847),
[pénalité de quai](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/economy.cpp#L1597).

**Composante calculable, limitée à ce cas :** avec le cargo disponible et
les wagons remplis/vidés, `40 × max_i(ceil(capacite_i / 5)) / 74` donne
**3,243 j par gare**, soit **6,486 j pour les deux gares**. Ce n'est pas une
simulation exacte du départ : initialisation, ordonnancement et sortie de
gare ne sont pas chiffrés. Les 240 ticks mécaniques par gare sont compatibles
avec les **223–259 ticks** sous-jacents au séjour mémorisé de 259 ticks
(arrondi moteur à 37). L'arrondi ne justifie pas une constante universelle
de 7 jours, ni l'affirmation que l'attente de production est exactement nulle.

**Illustration hors IA :** ajouter cette seule composante à un trajet
aller-retour arrondi à 15 j ferait passer `60 × 30 / cycle` de **120 à
83,77 t par mois de 30 jours**. C'est un calcul de sensibilité, pas une
nouvelle prédiction qualifiée, une mesure du débit ou une preuve de gain.
Il indique une correction structurelle possible, dépendante des wagons,
plutôt qu'un coefficient de concurrence déduit de cette seule ligne.

**Inconnues conservées :** les saves mensuelles ne décomposent pas l'attente
de production et ne donnent pas une rotation complète appariée. L'accès
NoAI aux entrées nécessaires et la généralisation aux NewGRF ne sont pas
audités dans ce lot. Avant une éventuelle implémentation, vérifier ces
entrées et l'articulation avec `loadDays`, qui agit déjà sur note/capture,
pour éviter un double comptage. Aucun effet sur le classement ou le profit
n'est mesuré. C41 et les pistes P2/P4 fermées restent inchangés.

**Validation exécutée :** analyse hors moteur des **12 saves**, hashes des
entrées et sources, composition, capacités, réglages, absence de NewGRF,
dimensions des gares et compatibilité des arrondis ; diff documentaire et
liens locaux contrôlés. Aucun test de comportement ni nouvelle partie.
[Script reproductible](../results/est16_line16_station_dwell_model_20261015/analyze.py),
[reçu](../results/est16_line16_station_dwell_model_20261015/receipt.json),
[sources et hashes](../results/est16_line16_station_dwell_model_20261015/sources.json).
Reçu SHA-256 : `f3179ec72786e043393079088ee80992ff025c0f099e6bb33e4f215e95bd0a9c`.
À la clôture d'EST-16, les artefacts restent locaux dans `results/` ; aucun
commit ni publication n'avait été effectué. La demande suivante autorise le
commit et la publication de la documentation sur `master` ; les liens vers
`results/` désignent toujours des preuves locales, absentes du dépôt publié.

<a id="est17-resultat"></a>
### EST-17 terminé le 15/10 — correction calculable sous profil standard explicite

**Complexité 2/5, faisabilité statique uniquement.** Lecture du code local
`master@92c86206` et des sources officielles OpenTTD **15.3**. Au début du lot,
`origin/master@9a6b0bce` contient deux commits documentaires supplémentaires,
dont le rapprochement V216/EST ; aucun écart de code IA avec le HEAD étudié.
Aucun pull, changement IA, banc, commit ou push dans ce lot.

**Entrées accessibles avant construction :**

| Donnée | Accès et limite |
|---|---|
| Capacité du wagon | `AIEngine.GetCapacity(engine)` ; déjà stockée dans `catalog.wagonByCargo`. Capacité du cargo principal/par défaut, pas une promesse de capacité après refit. |
| Chargement progressif | `AIGameSettings.IsValid("order.gradual_loading")`, puis `GetValue` ; réglage booléen lisible par cette API. Inconnu ne doit pas devenir OFF. |
| Pénalité de quai | Même accès à `order.station_length_loading_penalty`. |
| Quai prévu | `OpexRailWantedPlatformLength`, puis `fixedPlatformLength` après choix du site. `catalog.platformLength` est la borne de partie, pas le quai construit. |
| Vitesse de chargement | Pas de méthode dans `AIEngine` ; les **5 unités** viennent du modèle standard vérifié en EST-16, pas d'une lecture API. |
| Longueur exacte du matériel | Pas de méthode dans `AIEngine`. `AIVehicle.GetLength` exige un véhicule construit ; le builder fait déjà cette vérification. |

[API Engine](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_engine.hpp),
[capacité effective renvoyée](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_engine.cpp#L83),
[lecture des réglages](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_gamesettings.cpp#L20),
[déclarations des réglages](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/table/settings/game_settings.ini#L86),
[longueur du véhicule](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_vehicle.hpp#L553).

**Périmètre retenu pour le prochain calcul à blanc :** fret homogène, un cargo,
wagons standards non articulés sans refit, profil figé sans NewGRF, chargement
progressif actif, rame tenant dans les deux quais. La longueur nominale déjà
utilisée par OpexAI est `8 × (1 + wagons)` en seizièmes de tuile ; la vérification
réelle du builder reste nécessaire. Hors de ce périmètre, le calcul sera
**non couvert**, sans valeur de remplacement inventée. L'identification générale
du matériel NewGRF et les callbacks de chargement restent hors de ce lot.

**Formule proposée, pour une rame donnée et une charge complète :**

```text
S_gare = (40 / 74) × max_i(ceil(capacite_wagon_i / 5))
T_service = T_trajet_aller_retour + S_source + S_destination
capacite_30j = 30 × nombre_trains × capacite_rame / T_service
transporte_30j = min(offre_captee_30j, capacite_30j)
```

Le maximum traduit le travail parallèle des wagons ; ce n'est pas la capacité
totale divisée par 5. Le trajet conserve C41. La formule estime la composante
mécanique, sans ajouter une constante d'entrée/sortie non mesurée. Pour la rame
60 t d'EST-16 et le trajet illustratif de 15 j : **21,486 j**, **83,77 t/30 j**.
Ce résultat reste une illustration, pas le cycle réel d'une rotation appariée.
Pour plusieurs trains, la capacité est un plafond hors conflits de circulation
et files en gare ; le cas à un train est celui retenu pour la première application.

**Production et `loadDays` : ne pas additionner deux fois l'attente.** Le cargo
s'accumule aussi pendant l'absence du train. Avec un train, une offre captée
constante `r` unités/jour, sans file ni variation de note, l'approximation
stationnaire donne `T_cycle = max(T_service, capacite_rame / r)`, et non leur
somme. Le minimum offre/capacité ci-dessus exprime la même limite de débit.
À 60 t offertes par 30 j, l'exemple donne 60 t transportées, avec 8,514 j
d'attente supplémentaire idéale ; à 86 t, la capacité mécanique devient la
limite. Ce ne sont pas des mesures d'attente réelle : stock initial, production
par à-coups, concurrence et files peuvent changer les séjours.

Dans le code courant, `loadDays = perTrain × 30 / monthlyUnits` utilise la
production d'entrée, puis réduit `effectiveHeadway` pour la note de gare.
Ce n'est ni une vitesse de manutention ni une mesure du stock disponible.
**Ne pas remplacer globalement `roundTripDays` :** cela affecterait aussi
headway, note, offre, nombre de trains et coût de transit. Pour EST-18,
conserver la note/offre courantes comme témoin explicite et calculer une
capacité corrigée séparée. Cette séparation permet de mesurer la propagation
du seul terme mécanique ; elle ne qualifie pas un modèle complet de note.
Le couplage note/séjour demandé par V216f reste à étudier avant adoption.

**Livrable et validation :** sept sources officielles archivées avec SHA-256,
inventaire des méthodes publiques, contrôle des types de réglages, hashes
du catalogue/modèle/builder et contrôle algébrique de trois régimes d'offre.
[Audit hors moteur](../results/est17_exante_station_service_20261015/audit.py),
[reçu](../results/est17_exante_station_service_20261015/receipt.json),
[sources](../results/est17_exante_station_service_20261015/sources.json).
Reçu SHA-256 : `ffafe883903c1ee81ce6b0263264bc23fc5d9916b8ab9380ef510d7f6826c46b`.
L'appel NoAI n'a pas été exécuté en partie ; aucun gain économique mesuré.
Ces artefacts restent locaux dans `results/`.

<a id="est18-resultat"></a>
### EST-18 terminé — propagation à blanc sur la ligne 16 (3/5)

Même campagne historique EST-03 et même rame de deux wagons de 30 t ;
ce calcul ne qualifie pas les défauts actuels. Les panneaux de mars 1971,
le journal de construction et les sources figées donnent : 86 t/mois
transportées prévues, revenu annuel 25 800, exploitation 2 531,
amortissement 1 414, soit **21 855 de profit annuel prévu**.

Avec les 6,4865 jours mécaniques d'EST-17, la capacité corrigée est dans
l'intervalle ouvert **83,7736–84,2597 t/mois**. Les panneaux tronqués
ne permettent pas de choisir entre 83 et 84 tonnes après conversion entière.
En gardant note, offre, tarif, coûts et rame constants :

| Transporté | Revenu annuel | Profit annuel | Variation profit et score à dénominateur constant |
|---|---:|---:|---:|
| 83 t/mois | 24 900 | 20 955 | −900, soit −4,12 % |
| 84 t/mois | 25 200 | 21 255 | −600, soit −2,75 % |

La perte de capacité d'environ 30 % ne se transmet donc pas intégralement
au profit : le modèle initial était limité par l'offre. Cela n'explique pas
à lui seul l'écart historique de profit réalisé, qui inclut d'autres effets.

Le dernier ajustement de rame utilise une offre de dimensionnement de
**136 × 50 % = 68 t/mois**, distincte des 86–87 t/mois offertes au modèle
final. À trajet figé, un wagon ne couvre pas 68 t, deux les couvrent encore :
**ce passage conserve deux wagons**. Passer à trois pour couvrir 86 t changerait
aussi la règle de dimensionnement. La sélection initiale locomotive/rame C41,
le meilleur nombre de trains et le vivier ne sont pas rejoués : classement
et achat contrefactuels restent inconnus. Capital modèle 37 936 et devis réel
40 196 restent distincts ; aucun changement de finançabilité dans ce calcul.

Validation hors moteur : hashes des sources/manifeste, panneaux et identité
du train, événements de construction, bornes et calculs entiers contrôlés.
[Script](../results/est18_line16_capacity_shadow_20261015/analyze.py),
[reçu](../results/est18_line16_capacity_shadow_20261015/receipt.json), SHA-256
`b7cf3ce3cb457644fc1958b1a4cfbfda4667393070877d0a5e1f532ae736d606`.
Artefacts locaux, aucun changement de comportement.

La demande ultérieure de terminer l'étude et récupérer V216 remplace la
proposition d'une nouvelle sonde EST-19 : on audite la sonde déjà livrée et
ses preuves, sans dupliquer les campagnes. [Bilan EST/V216 du 16/10](est_v216_bilan_20261016.md).

### Report documentaire initial

**Report documentaire sur master le 14 octobre 2026, à la demande de l'utilisateur.**
Le découpage ci-dessous provient de `docs/taches.md` sur
`codex/scores-p0-diagnostics-20261013`, sauvegardé dans le stash
`6bbc2af` avant le retour à master. Il conserve les complexités,
dépendances, livrables et conditions d'arrêt du plan initial.

**Statut courant : référence de planification, pas huit tâches nouvellement ouvertes.**
Le [bilan final et la suspension P2/P4](p2_p4_bilan_final_et_suspension_20261014.md)
sont postérieurs au plan et priment sur ses formulations « à faire » :
des travaux de reprise C77, de mesure et des variantes H1/H2/H3 ont depuis
été exécutés sans gain qualifié. Le [backlog courant](taches.md) reste
la seule liste autoritaire ; il mentionne une recherche rouverte sur le VPS
sans lever les rejets du cycle suspendu. Le présent report ne lance rien.
À toute reprise autorisée, rapprocher chaque étape des preuves déjà acquises,
puis ne conserver que son reliquat réellement ouvert.

Le 40×5 de SE-07 appartient au protocole cinq ans de ce plan historique.
Il ne remplace pas le parcours courant 40×3 puis 20×10 d'[AGENTS.md](../AGENTS.md) ;
un autre horizon doit être décidé et pré-enregistré pour le nouveau candidat.
Les rapports du 13/10 conservés à côté expliquent les résultats initiaux ;
leurs anciennes prochaines étapes ne prévalent pas sur le bilan du 14/10.

<a id="scores-estimateurs-suite-20261014"></a>
### Scores et estimateurs — suite de l'étude, découpage du 14/10

**Statut au moment du découpage initial : huit tâches prévues, aucune lancée par ce plan.**
Point de départ : [étude](scores_estimateurs_diagnostic_20261013.md),
[résultats](scores_estimateurs_resultats_20261013.md),
[qualification indépendante](scores_p2_p4_qualification_independante_20261013.md),
[mécanismes restants](scores_p2_p4_mecanismes_restants_20261013.md) et
[expérimentation complémentaire](scores_p2_p4_experimentation_complementaire_20261013.md).
Ces deux derniers rapports distinguent les lacunes anciennes des sondes et
sauvegardes désormais disponibles. Les résultats locaux sont des prérequis à
vérifier dans leur bundle, pas une validation automatique du code courant.

**Complexité** : 2/5 faible (consolidation), 3/5 moyenne (adaptation bornée),
4/5 élevée (plusieurs modules et validation moteur), 5/5 très élevée
(faisabilité ou attribution causale incertaine). Ce classement mesure la
difficulté technique et scientifique ; il ne chiffre ni durée ni coût Docker.

| ID / tâche | Complexité et difficulté principale | Dépendances | Livrable et condition de passage |
|---|---|---|---|
| **SE-01 — Prouver un rejeu depuis l'état exact avant C77** | **5/5 — très élevée.** Save/Load, état des workers, calendrier et coût VM peuvent modifier le vivier avant le choix. | Rapports et stages existants. **Première intervention bornée.** | Note de faisabilité puis preuve minimale : même monde, bundle, rivale, caisse, vivier admissible, tier C77/V88 et `K_dec` ; deux reprises A/A depuis cet état, première divergence localisée. Réutiliser l'A/A existant comme contrôle, sans le présenter comme un fork pré-C77 déjà acquis. Si l'état décisionnel ne peut être conservé ou la divergence expliquée, consigner le blocage et arrêter la suite causale. |
| **SE-02 — Compléter la traçabilité et l'historique des véhicules** | **4/5 — élevée.** Sorties entre relevés, persistance et retours A* différés. | SE-01 ; inventaire des sondes existantes avant toute extension. | Réutiliser `score_p4_exits_probe` et `score_c77_chain_probe` des stages : épisode → choix → tentative/veto → constructeur immédiat ou rail repris → `lineId`, ventes, remplacements et crashes. Ajouter seulement les champs manquants. Conserver inconnu le profit perdu entre deux observations si aucune API ne permet de le récupérer. Contrats ciblés, smoke, Save/Load si état modifié et mesure du coût ; instrumentation identique dans les deux bras. |
| **SE-03 — Construire le bilan net du réseau** | **4/5 — élevée.** Éviter doubles comptes, biais des survivants et confusion profit/capital. | SE-02. | Extracteur et fixtures réutilisant les décodeurs courants : ligne créée, services voisins du hub, flotte entrée/sortie, frais et transactions datés, profit total Opex. Réconcilier les agrégats avec les trimestres clos ; distinguer comptabilité de compagnie, amortissement du modèle et métriques par ligne. Publier couverture et inconnus ; aucun profit manquant imputé à zéro, aucune externalité déduite d'une simple corrélation. |
| **SE-04 — Mesurer le choix témoin contre son alternative** | **5/5 — très élevée.** Attribuer un effet réseau à une décision malgré les constructions différées et les décisions ultérieures. | SE-01 à SE-03 validées. | Petit diagnostic contrefactuel pré-enregistré : mêmes candidats simultanément finançables et de même tier, choix témoin/alternative depuis le même état, contrôles A/A et chaîne constructeur complète. Comparer profit net Opex, voisins, trésorerie et valeur sur une fenêtre fixée avant résultats. Définir budget et règle d'arrêt ; pas de sélection des seuls flips gagnants. Sans effet identifiable, arrêter avant tout nouvel estimateur. |
| **SE-05 — Définir un estimateur nouveau et falsifiable** | **4/5 — élevée.** Séparer apprentissage, validation indépendante et information disponible à la décision. | SE-04 concluante. | Une spécification liant un signal observable avant C77 au rendement marginal mesuré ; tester sa capacité à modifier un vrai choix admissible sur des observations tenues à l'écart de sa construction. Pour le froid P2, traiter censure et cohortes par opération ; ne pas importer les ratios des seuls survivants. Démontrer la différence avec les variantes rejetées et l'absence de double correction C70/C121/R2/V161. Sans cette preuve, aucune variante comportementale. |
| **SE-06 — Implémenter une seule variante isolée** | **4/5 — élevée.** Classement, catalogues, coût VM et persistance sont couplés. | SE-05 validée. | Prototype OFF aux quatre difficultés dans un arbre isolé sur la base courante vérifiée, avec chemin témoin comparable. Préserver financement/réserves, priorités C77/V88, protection rail face aux renforts, C121/R2/V161 et V166. Contrats ciblés, exposition du mécanisme, smoke causal et Save/Load si nécessaire. Aucun portage global des stages ni modification implicite du catalogue AIR. |
| **SE-07 — Qualifier le candidat sur des graines indépendantes** | **4/5 — élevée ; coût de calcul élevé.** Exposition, comparabilité et généralisation économique. | SE-06 saine ; protocole et budget figés avant mesure. | Conserver l'objectif terminal cinq ans de ce chantier : pré-enregistrer explicitement A **40×5 `gain_short`**, dérogation d'horizon au 40×3 standard, seuil relatif 4 %, Wilcoxon p<0,05, IC95 bootstrap bas >0 et garde valeur −5 %. Graines distinctes de celles ayant servi à construire/sélectionner le candidat. Seulement après A complète, saine et `pass`, B **20×10 `non_erosion`** selon AGENTS.md. Aucun nouveau 40×5 pour les politiques rejetées. Sondes communes si indispensables ; qualification instrumentée à distinguer du défaut livré sans sondes. Toute porte échouée arrête la séquence. |
| **SE-08 — Conclure et préparer une éventuelle adoption** | **2/5 — faible**, une fois les preuves obtenues. | SE-07, ou arrêt documenté à une porte antérieure. | Bilan gain/rejet/non-validé, provenance, limites et preuves versionnables ; mise à jour de cette liste. Une qualification favorable ne change pas seule le défaut : adoption explicite du seul mécanisme testé, puis contrôles du défaut livré selon AGENTS.md. Aucun commit, push ou merge implicite. |

**Ordre : SE-01 → SE-02 → SE-03 → SE-04 → SE-05 → SE-06 → SE-07 → SE-08.**
Les quatre premières tâches constituent le lot de preuve ; les quatre suivantes
sont conditionnelles. SE-08 peut clore le travail dès qu'une porte échoue.
Le test A/A déjà réussi sur une graine ne garantit pas toutes les reprises ;
les sondes ont déjà perturbé les trajectoires OFF/ON et doivent être communes
aux comparaisons causales. Les 120 sauvegardes mensuelles existantes ne sont
pas des états sauvegardés au tick immédiatement avant C77.

**Périmètre fermé :** P1/V165, P3, stable-cohort, véhicule-année non gardé,
garde uplift AIR, `fresh_equal`, `partial` et crash-only ne sont pas à relancer
sur la base de cette planification. P2 reste une question d'identification,
pas un coefficient froid à implémenter. Les bancs AIR/RAIL V166 et V167 restent
des chantiers distincts ; leurs tâches ne sont pas absorbées par ce plan.
