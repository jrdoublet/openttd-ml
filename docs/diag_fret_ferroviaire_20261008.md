# Fret ferroviaire 1971–1975 — diagnostic du 8 octobre 2026

**Statut : mesure descriptive et audit statique ; aucun correctif comportemental qualifié.**
Ne pas transformer les chiffres historiques ci-dessous en estimation de gain au
défaut courant. Les trois jeux de résultats proviennent de campagnes distinctes.

## Décrochage sur le profil courant

Source : `results/c121_visible_flux_porteA_40x6_20261008.jsonl`, bras
`reference`, 40 graines, 6 ans, dernier snapshot au **1er décembre** de
chaque année. Ce JSONL mesure les trains tous cargos et les gares, **sans**
`line_telemetry`, ni `decision_log`, ni sauvegardes retenues.

| Année | Trains Opex | Trains AAA | Gares rail Opex | Gares rail AAA |
|---|---:|---:|---:|---:|
| 1971 | 4,60 | 5,22 | 9,30 | 10,53 |
| 1972 | 8,97 | 10,93 | 15,60 | 18,40 |
| 1973 | 11,40 | 19,12 | 19,75 | 26,82 |
| 1974 | 13,35 | 30,10 | 22,80 | 34,33 |
| 1975 | 15,07 | 39,55 | 25,57 | 40,58 |

Le décrochage accélère en 1973 ; il est **impossible de ventiler ce 40×6**
entre marchandises, courrier et voyageurs avec les enregistrements conservés.
Les panneaux `IB` comptent des constructions Opex tous modes, partagées dans
les deux snapshots du duel : ne pas les attribuer à AAA, les dupliquer ou les
interpréter comme des constructions de fret.

## Ventilation physique du fret : campagnes disposant des sauvegardes

Analyseur passif :
`sweeps/analyse_rail_freight_snapshots.py`. Il utilise
`line_telemetry.snapshots` produit hors moteur NoAI par le harnais existant,
avec `CargoID=0` PASS, `CargoID=2` MAIL pour les cartes tempérées en jeu.
Les rames mixtes et celles sans capacité identifiée sont isolées ; une rame
mixte n'est affectée à aucun total pur. Le relevé est le dernier snapshot de
décembre. Comparaison indépendante au `primary_vehicles_by_mode.rail` des
JSONL : **50/50 concordances** (campagne 5×5) et **36/36**
(campagne 3×6), aucune anomalie de compte.

### Campagne du 6 octobre, cinq graines, référence, 1971–1974

Source : `results/rail_pax_territory_diag_5x5_20261006.{json,jsonl}`.
Les graines sont 42, 59527, 292001, 701256, 841478.

| Année | Trains fret Opex/AAA | Trains PASS Opex/AAA | Trains MAIL Opex/AAA |
|---|---:|---:|---:|
| 1971 | 0,2 / 2,8 | 0,4 / 0,6 | 0 / 2,8 |
| 1972 | 1,6 / 5,4 | 0,8 / 1,2 | 0 / 4,8 |
| 1973 | 2,8 / 7,2 | 2,8 / 6,0 | 0 / 7,8 |
| 1974 | 4,0 / 16,4 | 3,0 / 5,8 | 0 / 8,0 |

En 1974, AAA possède aussi 1,4 rame mixte en moyenne. Écart fret AAA−Opex
par graine : 42 = 2, 59527 = 19, 292001 = 26, 701256 = 7, 841478 = 8
trains ; **5/5** graines en déficit de fret Opex.

### Campagne du 2 octobre, trois graines, référence C121, 1971–1975

Source : `results/c121_autopsy_c115_vs_c121_3x6_20261002_r1.{json,jsonl}`,
bras `c121_base`, graines 42, 100, 999.

| Année | Fret Opex/AAA | MAIL Opex/AAA | PASS Opex/AAA |
|---|---:|---:|---:|
| 1971 | 3,67 / 2,67 | 0 / 3,33 | 2,33 / 0,67 |
| 1972 | 3,67 / 3,67 | 0 / 6,33 | 3,00 / 1,00 |
| 1973 | 5,00 / 5,00 | 0 / 14,00 | 3,67 / 1,00 |
| 1974 | 5,33 / 8,67 | 0 / 14,67 | 4,33 / 3,00 |
| 1975 | 5,67 / 14,00 | 0 / 18,67 | 4,67 / 4,00 |

En 1975, l'écart total de 26,33 trains vient surtout du MAIL :
18,67 trains (~71 %), et 8,33 de fret hors courrier (~32 %) ;
le léger avantage PASS Opex compense le reliquat. **Mais** le profit des
véhicules `profit_this_year` (au 1er décembre, cumul partiel de l'année) est
alors fret **99,9 k£ Opex / 662,5 k£ AAA**, contre MAIL
**0 / 46,8 k£** et PASS **13,9 / 10,9 k£**. Le retard de profit
ferroviaire observé porte donc surtout sur les marchandises, contrairement
au retard en nombre de trains. Ce sont des profits de véhicules exploités,
pas une mesure du profit de projets rejetés.

Les deux petits échantillons proviennent d'arbres historiques et de politiques
distincts. Leurs ventilations **ne s'appliquent pas** aux 40 graines du 8/10.

### Complément moteur du 8 octobre, profil courant, cinq graines × six ans

Après rétablissement du Docker Desktop local, la campagne figée **sans variante**
`results/rail_freight_current_5x6_20261008_r1.{json,jsonl}` a terminé
**5/5 parties** sur les graines 42, 100, 999, 1234, 5678, avec
`--line-telemetry`, 10 CPU / 8 Go / 5 workers ; code Git `45df803`
(arbre dirty=1), image `openttd-lab` `f4b2b9b3b739…`.
L'analyse externe `results/rail_freight_current_5x6_20261008_r1.analysis.json`
confirme **60/60** concordances entre les classes de cargo et les trains
physiques. Chiffres moyens par partie au 1er décembre :

| Année | Fret Opex / AAA | PASS Opex / AAA | MAIL Opex / AAA |
|---|---:|---:|---:|
| 1971 | 2,2 / 3,0 | 3,6 / 0,0 | 0 / 2,2 |
| 1972 | 3,6 / 4,8 | 6,4 / 0,8 | 0 / 6,0 |
| 1973 | 5,2 / 10,2 | 8,0 / 4,0 | 0 / 6,2 |
| 1974 | 6,6 / 17,0 | 8,2 / 6,6 | 0 / 7,8 |
| 1975 | 7,0 / 24,0 | 8,8 / 7,8 | 0 / 8,2 |

En 1975, AAA a également 0,8 rame mixte en moyenne (hors des trois
colonnes pures). Le profit ferroviaire **fret pur** observé en décembre
(`profit_this_year`, année partielle) est de **91,2 k£ / 1 266,3 k£**
par graine Opex / AAA. Il ne s'agit ni de la même campagne que le 40×6,
ni d'un gain causalement imputable au classement ou à un filtre.

**Panneaux OR/OB dans la nouvelle campagne.** Au dernier snapshot du
1er décembre 1975, 85 panneaux OR, 85 OB, zéro troncature, zéro
malformation et zéro différence de multiplicité par clé ; une clé
`(année,ligne,position)` ambiguë sur seed5678. Par année, les panneaux
retrouvés donnent :

| Année | OR | OK | Autres | Opcodes OB |
|---|---:|---:|---:|---:|
| 1971 | 36 | 34 | 2 | 88 530 979 |
| 1972 | 18 | 13 | 5 | 85 789 004 |
| 1973 | 14 | 11 | 3 | 57 516 234 |
| 1974 | 10 | 5 | 5 | 81 357 042 |
| 1975 | 7 | 5 | 2 | 31 540 405 |

Ces panneaux ne portent pas `kind` : ils mélangent les tentatives rail fret
et PASS. La limite de panneaux de la carte peut rendre invisible une
tentative sans laisser de trou OR-vs-OB ; **il ne s'agit pas d'un recensement
exhaustif prouvé**. Malgré cette réserve, le volume observé de tentatives
diminue fortement après 1971, cohérent avec un goulot avant A*, à
distinguer expérimentalement de la raréfaction réelle de projets rentables.

## Trois mécanismes à examiner par ordre de preuve

1. **Élection et financement dans le portefeuille** — `projects_selection.nut`
   (`OpexProjectSelectAffordable`, `OpexProjectInsertDefensive`,
   `OpexProjectDefensiveAirPriority`) et `task_projects.nut` :
   rang C77 AIR devant score, ratio profit/capital, capital disponible,
   attente et arrêt de passe. Le diagnostic V99 du 03/10 (autre arbre,
   décrit dans `docs/taches.md`) rapporte `PROJECT_CHOSEN` rail
   21/10/5/8/4 par année 1971–75, malgré 117–139 apparitions annuelles
   dans le TOP5 en 1972–75 ; médiane de score AIR/rail 877/247 en 1972
   et 140/50 en 1975. C'est une piste forte, **pas une mesure sur 08/10,
   ni encore isolée par `kind=freight`**.
   **Rectificatif V99** : la calibration C70 a ensuite REFUTÉ la thèse
   « score brut AIR écrase le rail » : facteur appris AIR/rail
   0,269/0,620 en 1974, 0,241/0,706 en 1975, d'où une quasi-parité
   du score effectif médian (180/173 puis 227/216). Il faut mesurer
   la priorité lexicographique C77, les refus de cash/floor et les
   occasions d'exécution avant d'envisager une recalibration.
2. **Tracé et chantier après choix** — `task_rail.nut`,
   `builder_rail.nut` : diagnostic historique `raildrop_probe_5x6_20261003`
   décrit dans `docs/taches.md` : 49 tentatives tous types rail,
   32 OK, 10 TRKFAIL, 5 ABND, 1 STNFAIL, 1 SITEB. 1971 : 23/24 OK ;
   1972–75 : 9/25 OK. Ces nombres ne sont pas spécifiques au fret ni
   transposables automatiquement au code courant.
3. **Génération et restrictions d'origines** — `candidates.nut` exclut
   si `sa != null || sb != null`, tandis que
   `projects_generation.nut::OpexCandidateStillValid` exclut
   si les deux sont servies. Les autres filtres comprennent production,
   acceptation, site, distance, profit et ratio, TOP_K et rotation d'un
   seul cargo à la fois (`projects_generation.nut:13-78`).
   L'ancienne mesure origin-served shadow 4×4 : 204 paires one-served
   exclues, mais 203 quand le vivier frais avait déjà atteint TOP_K20.
   La perte économique demeure inconnue.

**C80/C121 industry→town.** Le bug `TileIndex` traité comme
`IndustryID` est corrigé : `AIIndustry.GetIndustryID(tile)`.
Un défaut sémantique demeure dans `rail_prep_c121.nut:253-255` et
`task_rail.nut:1823-1825,2115-2119` : la destination des frets
industry→town, pourtant admissible dans `candidates.nut:1791-1857`
et `builder_rail.nut:280-294`, est refusée faute d'IndustryID.
Le worker C80 est OFF ; la préparation C121 est ON mais ne couvre
essentiellement que 1970, puis les plans récupérés en 1971.
**Exposition réelle et rôle dans le retard 1972–75 non mesurés** :
ne pas en faire le correctif principal sans comptage de cas.

### Nouveaux diagnostics décisionnels, le 8 octobre

Les campagnes suivantes sont **diagnostiques**, sur le bundle figé au
Git `7b5964b` ; les sondes consomment des opcodes et peuvent modifier
la trajectoire. Leurs profits ne se comparent donc pas causalement à
ceux de `rail_freight_current_5x6_20261008_r1`.

- `rail_freight_funnel_dlog_2x6_20261008_r1` :
  `decision_log=1`, 2 graines 42/100 × 6 ans, 2/2 parties complètes.
  Les événements `PORTFOLIO_RANK` et `PROJECT_CHOSEN` conservent
  `kind=freight|pax`, contrairement à OR/OB. Seed42 : aucun fret parmi
  les cinq premières positions enregistrées en 1973–75, alors que
  les projets pax continuent. Seed100 : des projets fret existent encore
  en 1975, mais aucun `PROJECT_CHOSEN` fret cette année.
- `rail_freight_funnel_shadow_3x6_20261008_r1` :
  `decision_log=1,probe_portfolio=1,
  rail_origin_exposure_shadow=1,rail_origin_exposure_detail_shadow=1`,
  graines 42/100/999 × 6 ans, 3/3 parties complètes.
  `RAIL_PREPAIR` distingue paires fret industrie/ville, et les
  `VIVIER_REJECT` exposent les gardes. Exemple seed100 en 1974 :
  les deux générations fallback freight-only examinent 490 paires
  vers les villes, dont 210 sauts `zero_monthly` et
  270 rejets `origin_served` ; seulement 9 candidats finissent
  dans les tableaux `kept`. **Occurrences de génération**, pas
  projets distincts ni gains possibles. Seed999 garde au contraire
  du fret classé jusqu'en 1975 : verrou non universel.

Analyseur extérieur `sweeps/analyse_rail_freight_dlog.py` :
`results/rail_freight_funnel_dlog_2x6_20261008_r1.analysis.json`
et `results/rail_freight_funnel_shadow_3x6_20261008_r1.analysis.json`.
Les compteurs `ranked_top5_occurrences` sont des occurrences répétées
de classements, **pas un nombre de propositions uniques**.

### Instrument sélection fret, toujours OFF par défaut

La nouvelle option diagnostique `rail_freight_select_shadow=0`
est déclarée dans `info.nut`, `settings.nut` et `globals_pre.nut`.
`projects_selection.nut::OpexRailFreightSelectShadow` est appelé
uniquement sous la garde du flag, après finalisation du portefeuille.
Il distingue `total_f`, `cash_f`, `floor_f`, `eligible_f`,
`selected_f`, les destinations ville, le fret/pax dans l'ensemble
retenu, ainsi que `head_mode`/`head_tier` et les scores effectifs.
L'analyseur de journaux mesure les passes où le fret est finançable
mais aucun fret n'est retenu. Un appel représente **un re-classement**
et non une nouvelle opportunité indépendante.

Contrats Python et **smokes moteur réussis** sur le bundle figé
`1c993a929af70e592fb70db8e4029c4280cc9178e6b6d8188d47e19cb9b6ec1a`
(Git `7b5964b`, arbre dirty, image Docker `f4b2b9b3b739…`) :

- `rail_freight_select_shadow_off_smoke_1x1_20261008_r1` : seed42, un an,
  1/1 partie saine, défaut OFF, compilation/chargement vérifiés.
- `rail_freight_select_shadow_on_smoke_1x2_20261008_r1` : seed42, deux ans,
  1/1 partie saine, 723 relevés `RAIL_FREIGHT_SELECT_SHADOW` réels parsés,
  403 en 1970 et 320 en 1971.
- `rail_freight_select_shadow_diag_3x6_20261008_r1` : graines 42, 100, 999,
  six ans, **3/3 parties saines** avec la seule sonde de sélection ON,
  `decision_log` et `probe_portfolio` OFF. Analyse :
  `results/rail_freight_select_shadow_diag_3x6_20261008_r1.analysis.json`.

| Graine / année | Reclassements | Appels avec fret admissible | Appels avec fret retenu | Fret alternatif / cash / floor / admissible / retenu (occurrences) |
|---|---:|---:|---:|---|
| 42 / 1973 | 136 | 3 | 0 | 3 / 0 / 0 / 3 / 0 |
| 42 / 1974 | 180 | 0 | 0 | 0 / 0 / 0 / 0 / 0 |
| 42 / 1975 | 101 | 89 | 89 | 135 / 0 / 0 / 135 / 129 |
| 100 / 1973 | 194 | 26 | 20 | 47 / 5 / 0 / 42 / 20 |
| 100 / 1974 | 198 | 22 | 21 | 26 / 0 / 0 / 26 / 21 |
| 100 / 1975 | 202 | 55 | 47 | 180 / 0 / 0 / 180 / 150 |
| 999 / 1973 | 164 | 95 | 92 | 358 / 163 / 0 / 195 / 182 |
| 999 / 1974 | 284 | 64 | 31 | 406 / 112 / 0 / 294 / 63 |
| 999 / 1975 | 111 | 111 | 109 | 544 / 0 / 0 / 544 / 404 |

La raréfaction est très variable : seed42 n'a aucune alternative fret
dans ses 180 classements de 1974 ; seed999 en a encore et perd une partie
à la rétention TOP64. Le `floor` ne filtre **aucun** fret de cet échantillon,
et le cash n'en filtre plus aucun en 1975. Lorsque du fret est admissible,
la tête est parfois AIR ordinaire ou flotte, mais **jamais AIR défensif
C77 tier>0** sur ces trois parties. Cela exclut une preuve de blocage
C77 direct au moment du classement ici, sans prouver pourquoi le fret
éligible n'est pas ensuite élu/posé. Chaque valeur du tableau compte des
**reclassements répétés**, et non des projets ou des opportunités distincts.

Le diagnostic complémentaire `rail_freight_select_choice_diag_3x6_20261008_r1`
(`rail_freight_select_shadow=1,decision_log=1`) a été **interrompu** dès
constat de concurrence avec la campagne d'un autre agent
`v133_air_build_retry_40x5_20261008_r1`. Seul notre conteneur a été
arrêté ; cette tentative (exit 137) ne produit **aucune preuve exploitable**.
Il reste à relier rétention, `PROJECT_CHOSEN`, `RAIL_ATTEMPT` et pose
dans les **mêmes parties**, puis à mesurer le cargo et le type de destination
sur les étapes qui perdent des projets.

**Cas concret dans le diagnostic plus ancien, sous d'autres sondes ON** :
`rail_freight_funnel_shadow_3x6_20261008_r1`, seed999, année 1974 :
40 occurrences de fret dans le TOP5, **7 fois en tête**, mais aucun
`PROJECT_CHOSEN` ni `RAIL_ATTEMPT` fret. La paire `cargo=GOOD`,
`src=53889`, `dst=58684` apparaît en tête sept fois, avec trois
`PROJECT_DISCARD` `too_close_no_join` (2 mai, 24 août, 17 septembre)
et cinq `search_in_progress` à d'autres passages ; les 15 `too_close_no_join`
ferroviaires annuels regroupent tous cargos, sans attribution automatique
au fret. Le décalage sémantique est vérifié :
`OpexCandidateStillValid` (`projects_generation.nut`) laisse passer un
projet rail lorsqu'une seule extrémité est déjà desservie ; `_tooClose`
(`lines.nut`) le bloque avant pose si l'une des origines est trop proche,
hors `joinLineId`. **Une proposition périmée peut donc occuper les premiers
rangs et être rejetée avant A\*.** Il faut quantifier cette exposition
sur le défaut non instrumenté et déterminer si sa suppression accélère
effectivement des constructions rentables avant tout correctif.

## Diagnostic apparié et intervention ciblée du 8 octobre au soir

La campagne rail_freight_select_choice_diag_3x6_20261008_r2 a révélé un
défaut de la sonde : sous decision_log=1, le diagnostic B6 appelle aussi
OpexProjectSelectAffordable sur des copies avec une limite de 1. Ces
sélections simulées étaient confondues avec le TOP64 réel ; les totaux
combinés r2 ne sont donc pas exploitables pour estimer les pertes au TOP64.
Le drapeau interne realSelection=false sur le seul appel B6 supprime ce
doublon sans modifier le choix réel. Smoke corrigé
rail_freight_shadow_real_only_smoke_1x2_20261008_r1 : complet, exactement
688 relevés de sélection pour 688 événements B6_PORTFOLIO.

Nouvelle campagne rail_freight_select_choice_real_3x6_20261008_r3 :
3/3 parties complètes sur les graines 42/100/999, six ans ; code Git
7b5964b dirty, bundle
1bce502b5117c2208a85a1e0e452c18c6ebc0ed98105e9443942d1369a3debb4.
Résultats : results/rail_freight_select_choice_real_3x6_20261008_r3.analysis.json.
Les compteurs sont des occurrences répétées sur une partie instrumentée.

| Graine / an | Fret éligible / retenu | Choix fret | Tentatives fret |
|---|---:|---:|---|
| 42 / 1973 | 83 / 83 | 4 | 1 OK, 2 TRKFAIL |
| 42 / 1974 | 174 / 174 | 15 | 15 TRKFAIL |
| 42 / 1975 | 208 / 208 | 14 | 14 TRKFAIL |
| 100 / 1974 | 126 / 126 | 2 | 2 ABND |
| 100 / 1975 | 125 / 125 | 1 | 1 OK |
| 999 / 1974 | 107 / 74 | 2 | 2 OK |
| 999 / 1975 | 53 / 50 | 2 | 2 OK |

Sur seed42, les 29 TRKFAIL 1974–1975 concernent seulement deux couples
fret : 5258 vers 5200 (16 tentatives) et 5258 vers 5717 (13).
Coût actual retourné dans RAIL_ATTEMPT : 218 851 livres cumulées,
80 547 666 opcodes de tentative, zéro ligne construite. La trace
RAIL_TRACK_FAIL avant rollback signale toujours err=260
(ERR_AREA_NOT_CLEAR), index=1, tile=4744, stn=1, own=1, bld=0 :
le rail bute sur le lead occupé par notre propre gare après pose.
Le chemin historique ne mémorise pas TRKFAIL, d'où ces reprises. Cette
fréquence concerne la partie instrumentée et ne constitue pas une preuve
de gain économique sur le défaut normal.

**Intervention isolée pré-enregistrée avant benchmark** : nouveau réglage
rail_freight_trkfail_memory, défaut 0 aux quatre difficultés. À 1, ne
mémoriser que le TRKFAIL d'un projet freight dont l'échec vérifie
ERR_AREA_NOT_CLEAR sur notre gare au lead du chemin A* (position 1 ou
avant-dernière du tracé). Le premier pilote utilisait le prédicat exact
OpexRailTrackFailureIsPersistentGeometry, mais le match historique
peut substituer un autre quai au même station_exit : il restait inerte.
Le prédicat final OpexRailTrackFailureIsPersistentPathLead identifie
la tuile réellement traversée, sans élargir le garde géométrique V100.
Réutiliser le ledger d'abandon C33 et son délai de 365 jours, sans activer
rail_geometry_guard, l'identité exacte ni le préfiltre V100. Risques :
une autre géométrie de la même paire pourrait réussir, ou le capital
pourrait être déplacé vers des projets AIR moins rentables.

**Qualification pré-enregistrée** : tests de contrat et smoke 1 graine
sur une année, diagnostic d'exposition puis porte A gain_short à
40 graines canoniques × 5 ans (horizon fixé avant résultat pour englober
le décrochage 1974–1975), profit terminal Opex variante moins référence,
moyenne au moins +4 % du profit terminal moyen de référence, Wilcoxon
exact bilatéral p<0,05, borne basse IC95 bootstrap positive et garde de
valeur -5 %. Seulement si A passe, porte B non_erosion à 20 graines
canoniques × 10 ans, borne supérieure IC95 bootstrap au moins zéro,
garde de valeur -5 %. Même bundle, autres réglages au défaut, aucun
decision_log/probe, 10 CPU, 8 Go, 10 workers PC local. Défaut maintenu à
0 sans deux portes réussies ; aucun commit ni push.

### Validation de la mémoire fret et verdict économique

Deux smokes A/B 1×1 complets et sains ont confirmé le chargement
du réglage OFF/ON. Les contrats spécifiques (2/2) et ceux du garde
géométrique existant (12/12) sont verts. Le profil diagnostic
`rail_freight_trkfail_exact_exposure_1x6_20261008_r3` (seed42,
six ans, deux bras avec `decision_log=1` et
`rail_freight_select_shadow=1`) prouve l'activation :
**31 → 5 tentatives fret TRKFAIL**, abandon de paires dans le bras ON.
Profit annuel terminal variante-référence +216 275 £, valeur +6,54 %,
sur **une seule réalisation instrumentée** : aucun verdict économique.

Porte A **sans sondes**, campagne
`rail_freight_trkfail_memory_gateA_40x5_20261008_r1`, Git
`7b5964b` dirty, bundle
`98e9eae4e17b6479344a0e4c7477ada8dbc9d56e4341a2470153970e9a4c1268`,
manifeste SHA256
`26a19147ec5d0feffc6ddbca8b823cf84c98c2bf588fb64ae0eb0ddcbc86b06e`,
image `openttd-lab` SHA256 `f4b2b9b3b739…`.
40/40 paires, 80/80 parties complètes, aucun run en échec,
comparaison, échantillon d'adoption et couverture métrique complètes.
Année terminale 1974, bootstrap 20 000 rééchantillonnages, graine 0.

| Porte A, Opex variante − référence | Résultat |
|---|---:|
| Delta moyen profit_year | **−7 887,325 £/an** |
| Médiane | 0 £/an |
| Victoires / défaites / égalités | **5 / 11 / 24** |
| Wilcoxon exact bilatéral | p = 0,3754578 |
| IC95 bootstrap | **[−27 991,75 ; +12 656,40] £/an** |
| Seuil de gain relatif +4 % | **+65 633,91 £/an** |
| Valeur, ratio des moyennes | **+0,2032 %** ; garde tenue |
| Verdict du harnais | **fail_primary** |

Effets très hétérogènes : graine42 +207 506 £/an, graine313707
+151 811 £/an, mais graine442018 −166 740 £/an,
graine423960 −150 385 £/an et graine73 −135 753 £/an.
24 graines restent identiques à l'horizon. L'économie des reprises
**ne démontre pas de gain économique** sur le protocole complet.
**Porte B 20×10 non lancée, toggle conservé à 0, non adopté.**
Pas de changement de règle ou d'horizon après ce résultat.

## Correctif suivant : cohérence cache rail / proximité de chantier

Après rejet économique de la mémoire `TRKFAIL`, investigation des
classements rail dont le projet reste dans `candidateGroups` alors que
la passe d'exécution l'écarte `too_close_no_join`.
`OpexCandidateStillValid` (`projects_generation.nut`) ne rejette
historiquement que les **deux** origines déjà desservies ; à l'exécution
`_tooClose` (`lines.nut`) applique `ORIGIN_SEPARATION` à
**chacune** et `MIN_SEPARATION` aux gares, sauf la ligne `joinLineId`.
Le nouveau `OpexRailCachedProximity` reproduit ce second contrat dans
le seul chemin de cache (revalidation incrémentale et sélection
`OpexReselectProjects`) ; génération fraîche et `_tooClose`
restent inchangés. Projets spéciaux `isChain` ignorés par prudence
tant qu'ils ne sont pas qualifiés. Aucun nouvel état Save/Load.

Réglage `rail_cached_proximity_gate`, **défaut 0** aux quatre
difficultés : 0 historique sans scan supplémentaire ; 1 sonde qui
journalise `RAIL_CACHE_PROXIMITY phase=incremental|reselect`
sous `decision_log=1` sans rejeter ; 2 enlève le projet bloqué
avant le TOP64. Un log est une **occurrence** de revalidation / resélection,
pas un OD unique ni un chantier avorté. Hypothèse : retirer les choix
qui meurent avant A* peut faire remonter des projets viables ; cela
ne garantit ni construction ni profit supplémentaires. Le filtre ne
force aucune extension `origin_reuse`.

Validation prévue avant résultat : tests statiques de parité avec
`_tooClose`, smoke moteur OFF/ON, exposition 1×6/3×6,
puis porte A 40 graines canoniques × **5 ans** (horizon tardif
pré-enregistré, seuil +4 % de profit terminal Opex, p Wilcoxon exact
bilatéral < 0,05, IC95 bootstrap borne basse > 0, garde de valeur
−5 %). Seulement si A passe, B20×10 `non_erosion`.
Profil local 10 CPU, 8 Go et 10 workers, une campagne à la fois,
défaut 0 sans qualification complète. Aucun commit/push.

### Exposition, validation et verdict (cache / proximité)

- Contrats `sweeps/test_rail_cached_proximity_gate.py` : **3/3 verts**,
  vérification des quatre défauts à 0, de la parité des deux rayons et de
  l'exception `joinLineId`, des branches OFF/shadow/ON, et de l'absence
  d'intervention dans le générateur frais / dans `_tooClose`.
- Smoke C66.4 `rail_cached_proximity_smoke_1x1_20261008_r1`,
  seed42, 1 an, les deux bras complets/sains ; première exposition
  économique +48 417 £/an (un point, **diagnostic_only**, non généralisable).
- Shadow 3 graines × 6 ans `rail_cached_proximity_shadow_3x6_20261008_r1`,
  `rail_cached_proximity_gate=1,decision_log=1`, complet 3/3.
  Rejets qui **auraient** lieu (passages / couples distincts par
  `kind|src|dst`) : seed42 **757 / 34** (tout pax), seed100
  **1 078 / 18** (1 025 pax et 53 fret), seed999 **2 376 / 68**
  (1 668 pax et 708 fret). Total **4 211 passages** pour **120 clés
  distinctes (somme par graine)**, dont **3 450 pax** et **761 fret** ;
  **3 563** passages de resélection et **648** d'incrémental.
  Le volume représente des revisites fréquentes d'une même paire, et
  **pas** 4 211 chantiers échoués ni de projets indépendants.
- Porte A complète **sans sondes** :
  `rail_cached_proximity_gateA_40x5_20261008_r1`, référence
  `OpexAI[rail_cached_proximity_gate=0]`, variante `=2`,
  même bundle SHA256
  `9783ca4d868b802c0f4ab944b8c52bd714ad72b0f35a461d776ab3c4f8201a28`,
  manifeste SHA256
  `eced3bbab7d71707d974fafcaec24e1f4e0261442d820d46c0ee2f2d92e1f820`,
  Git `7b5964b` dirty, image Docker `f4b2b9b3b739…`.
  **40/40 paires, 80/80 parties complètes, 0 run en échec** ;
  couverture, échantillon et protocole d'adoption complets.
  Année terminale 1974 (5 ans).

| Porte A : variante − référence Opex | Résultat |
|---|---:|
| Δprofit_year moyen | **+42 709,10 £/an** |
| Médiane | +33 174 £/an |
| Victoires / défaites / égalités | **22 / 18 / 0** |
| Wilcoxon exact bilatéral | **p=0,320308** |
| IC95 bootstrap (20 000 tirages) | **[−32 304,48 ; +118 465,60] £/an** |
| Seuil utile de +4 % | **+65 667,71 £/an** |
| Ratio des valeurs moyennes | **+2,2654 %**, garde tenue |
| Δvéhicules Opex moyen | −1,725 |
| Verdict brut | **fail_primary** |

Ce résultat **ne prouve pas** que nettoyer le cache augmente le
profit d'OpexAI malgré une moyenne positive : intervalle traversant
zéro, p non significatif et seuil préenregistré non atteint.
La baisse moyenne des véhicules demande prudence quant à l'argument
« plus de lignes rail ». **Porte B20×10 non lancée, réglage maintenu
à 0**, aucun changement d'heuristique d'origine ni de _tooClose.
Ne pas requalifier post-hoc la variante sur 22/40 victoires.

### Comptage moteur exhaustif des issues de tentative, 1974–1975

La porte économique 40×5 précédente se termine en **1974** et ne
conservait ni logs `RAIL_ATTEMPT` exhaustifs ni `line_telemetry`.
Les panneaux `OR/OB` conservés en fin de partie ne permettent pas
la ventilation fret/passagers. Pour répondre à la question des échecs
sur 1974–1975, une **nouvelle partie diagnostique distincte** a été
réalisée : `rail_failure_audit_5x6_20261008_r1`, cinq graines
`42,100,999,1234,5678`, 6 ans et **10/10 parties saines**.
Deux politiques d'un même bundle
`0a9321bf0da40406cbebfc90e68d02e57d73181f678aea5597a7ad8b2f8798ee` :
`rail_cached_proximity_gate=0` contre `=2`, toutes deux avec
`rail_failure_audit=1` uniquement. Image Docker `f4b2b9b3b739…`,
Git `7b5964b` dirty ; manifeste
`952a207bc92645b643ec4e5972860c139c0cc28e561bfd39a25f561e059828df`.
Source : `results/rail_failure_audit_5x6_20261008_r1.json` et
`results/rail_failure_audit_5x6_20261008_r1.analysis.json`.

La nouvelle sonde `rail_failure_audit` (défaut **0** aux quatre
difficultés) écrit directement un `RAIL_AUDIT` par appel de
`_recordRailAttempt` et un par refus de proximité depuis les
quatre branches de `_tryBuildRailProject`, avec
`stage/ kind/ cargo/ src/ dst/ reason/ ok/ actual/ ops`. Elle
ne dépend pas des panneaux SIGN limités ni de `decision_log`.
Le décodeur `sweeps/analyse_rail_failure_audit.py` sépare les
**tentatives terminées** des **refus pré-A*** et fournit les clés
distinctes. Tests 3/3 et smoke 1×2 sains ; aucun événement invalide
dans les dix logs. Les recherches encore en attente et les candidats
jamais sélectionnés ne sont pas des tentatives achevées.

| Année | Genre | Référence : OK / tentatives | Variante : OK / tentatives | Autres issues réf. | Autres issues var. |
|---|---|---:|---:|---|---|
| 1974 | **Fret** | **0 / 1** | **2 / 6** | TRKFAIL 1 | TRKFAIL 2, ABND 2 |
| 1974 | Voyageurs | 5 / 12 | 3 / 5 | TRKFAIL 1, STNFAIL 1, ABND 3, NOPA 2 | ABND 2 |
| 1975 | **Fret** | **4 / 7** | **3 / 6** | TRKFAIL 1, SITEB 1, ABND 1 | TRKFAIL 2, STNFAIL 1 |
| 1975 | Voyageurs | 2 / 6 | 0 / 1 | ABND 3, NOPA 1 | STNFAIL 1 |
| **1974 total rail** | Tous | **5 / 13** | **5 / 11** | **8 échecs** | **6 échecs** |
| **1975 total rail** | Tous | **6 / 13** | **3 / 7** | **7 échecs** | **4 échecs** |

Sous le filtre, les échecs bruts baissent (1974 8→6 ; 1975
7→4) parce que **le nombre de tentatives baisse aussi** (13→11
puis 13→7). En 1974, le nombre de constructions réussies est
inchangé à 5, malgré un transfert de voyageurs (5→3) vers le fret
(0→2). En **1975, les réussites diminuent de moitié (6→3)**,
dont voyageurs 2→0 et fret 4→3. Les TRKFAIL des tentatives
achevées ne diminuent pas : 1974 **2→2** et 1975 **1→2**
tous genres réunis. Aucun gain de fiabilité de pose n'est démontré.

Le garde pré-A* supprime bien les rejets tardifs au chantier : en
1974, `too_close_no_join` passe de **206 passages fret et 113
passagers** à **0 et 0** ; en 1975, de **29 fret et 36 passagers**
à **0 et 0**. Ces passages répétés correspondent respectivement
en référence à **6+16** clés cargo/OD en 1974 et **4+2**
en 1975 (chaque graine séparée). Ils sont désormais filtrés en
amont du TOP64 ; leur disparition du précheck n'indique pas
qu'un nouveau chantier est devenu rentable.

La ventilation des cargos confirme que l'effet fret n'est pas une
simple variante de PASS : tentatives fret en 1974, référence
`LVST=1` ; variante `IORE=1,GRAI=1,OIL_=1,COAL=3`.
En 1975, référence `GOOD=1,GRAI=4,COAL=2` ; variante
`OIL_=3,GOOD=1,GRAI=1,COAL=1`. Aucun cargo courrier
n'est enregistré dans ces tentatives.

**Limite causale :** ces 5×6 sont de nouveaux parcours de jeu
avec une sonde active, pas une relecture exhaustive de la porte
40×5 sans sonde ni une preuve d'équivalence des trajectoires.
Ils expliquent le fonctionnement mécanique et son déplacement
des tentatives, sans requalifier le `fail_primary` de la porte A
40×5. `rail_cached_proximity_gate=0` et
`rail_failure_audit=0` restent les défauts. Aucune porte B.

## Instrumentation minimale, protocole et limites

- L'analyseur ci-dessus ne change rien au code NoAI.
  `python -X utf8 sweeps/analyse_rail_freight_snapshots.py
  results/<campaign>.json --policy reference --crosscheck-jsonl
  results/<campaign>.jsonl --out results/<unique>.analysis.json`.
  Tester son contrat avec `python -X utf8 -m unittest discover -s sweeps
  -p test_analyse_rail_freight_snapshots.py`.
- `sweeps/bench_1v1_5y_20seeds.py::rail_attempt_sign_metrics` extrait
  passivement les panneaux `OR`/`OB` **retenus** par la carte (raison,
  itérations, opcodes, année). Ils ne portent pas `kind=freight` ;
  signes tronqués, absents ou identifiants de tentative ambigus sont
  rapportés explicitement. Aucun total de panneaux ne constitue une
  preuve d'exhaustivité des tentatives.
- **Exécuté le 08/10, après rétablissement Docker** : smoke référence
  `rail_freight_sign_smoke_1x1_20261008_r2`, puis référence 5×6
  `rail_freight_current_5x6_20261008_r1`. Aucune campagne doublée,
  aucune intervention IA. Le diagnostic 5×6 emploie le profil local
  `--cpus 10 --memory 8g --max-workers 5` (limite admise : 10 workers).
- Pour expliquer le funnel fret, seule une **petite sonde annuelle OFF**
  par défaut par `cargo` et `destinationKind` pourra compter les
  passages `generated→TOP_K→fundable→selected→A*→built`, avec les
  rejets exacts (served, production, acceptation, ratio, score, caisse,
  prépa industry→town, géométrie). Vérifier que le OFF préserve les
  décisions et les opcodes, puis faire un smoke moteur. Les logs détaillés
  `decision_log=1` coûtent des opcodes et peuvent dévier la trajectoire.

**État au 08/10 après récupération du runtime :** Docker Desktop
29.8.2 a permis le smoke 1×1 et le diagnostic 5×6 **complets et sains**.
Le blocage restant est la ventilation par `kind` du funnel
`generation→sélection→construction` et la fréquence réelle des rejets
industry→town. Aucun réglage métier n'a été activé ni qualifié, aucune
porte A/B V102 n'a été déclenchée. Pas de commit/push de ce diagnostic.
