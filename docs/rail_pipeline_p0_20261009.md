# P0 — Pipeline rail 1972–1975, autopsie observationnelle (09/10/2026)

## Protocole pré-enregistré avant nouvelle collecte

Mission : identifier la première perte mesurable de fret potentiellement rentable,
de la génération à la pose puis à l'exploitation. Aucune politique candidate,
aucune qualification économique ni nouveau défaut de production.

État initial constaté : `/openttd-ml`, branche `master`, HEAD `cb23a17`,
arbre local modifié par plusieurs chantiers préexistants. Ces modifications
doivent être préservées ; les bundles de chaque nouvelle campagne figent
le code réellement exécuté et servent d'unique référence de provenance.

Les jeux du 08/10 (choix fret 3×6, échecs 5×6, chronologie 20×5) et ceux du
09/10 (PREASTAR 5×6) ont des bundles distincts : leurs effectifs ne constituent
pas un funnel apparié. Les sondes existantes comprennent `decision_log`,
`probe_portfolio`, `rail_freight_select_shadow`, `rail_failure_audit`,
`rail_origin_exposure_shadow`, `rail_origin_exposure_detail_shadow` et
`probe_rail_preastar`, tous OFF aux quatre difficultés en production.

Pour réunir les événements sur **la même partie**, protocole diagnostique
prévu : un smoke apparié graine 42 × 1 an avec toutes les sondes OFF contre
toutes ON, puis, si sain et Docker libre, une collecte mono-bras ON, cinq
graines **42, 100, 999, 512, 515222** × **6 ans** (1970–1975),
`--script-debug --line-telemetry`, profil PC local 10 CPU/8 Gio/5 workers.
Les cinq graines sont fixées avant toute lecture de ce nouveau banc, afin
d'inclure le fret rare, des rejets de pose répétés, des A* plafonnés et des
contre-exemples OK déjà documentés. Aucune recherche de seuil ni sélection
postérieure d'horizon. Une seule campagne Docker active à la fois.

Sondes ON communes :
`rail_freight_select_shadow=1,rail_failure_audit=1,probe_rail_preastar=1,rail_origin_exposure_shadow=1,rail_origin_exposure_detail_shadow=1,decision_log=1,probe_portfolio=1`.
Il s'agit d'une **observation intrusive** : les surcoûts d'opcodes peuvent
dévier le calendrier et les choix. Le smoke n'établit que la santé, une
éventuelle parité très courte et la présence du schéma ; un delta ON/OFF
ultérieur ne serait pas un gain causal. Aucune preuve externe sur les mêmes
graines n'est automatiquement comparable au bundle nouvellement figé.

Définitions à respecter dans l'analyse : `(campagne,bras,graine,répétition)`
est l'espace d'identité ; `(kind,cargo,src,dst)` est une **clé de paire**,
pas une identité de projet persistante. Les `RID` n'identifient que les
recherches A* et leurs `BUILD` dans une même partie. Les revisites de
classement, les paires examinées, les préparations stock `ready` et les
projets refusés doivent rester distincts des lignes construites. Tout
rapprochement sans identifiant strict reste `unmatched/ambiguous`.
Le profit des véhicules `profit_this_year` est partiel à chaque checkpoint ;
le financement d'un chantier n'est pas un profit net après investissement.

La collecte doit être rapportée avec son bundle, son manifeste, l'identité
Git/dirty, sa santé, ses dénominateurs par étape et les censures. Le correctif
éventuel demandera une preuve de mécanisme et un contrefactuel incluant les
véritables lignes OK sacrifiées, puis seulement le protocole V102.

## Verdict après moteur — preuve nouvelle du 9 octobre

Le smoke `rail_p0_funnel_smoke_42x1_20261009_r1` a terminé **2/2** parties
saines. Le profit annuel Opex **ON−OFF est +5 525 £** sur cette unique graine
après un an : la collecte instrumentée perturbe déjà les décisions. Ce nombre
**n'est pas** un résultat économique de politique et interdit toute comparaison
causale des profits entre les deux bras.

La collecte observationnelle mono-bras
`results/rail_p0_funnel_obs_5x6_20261009_r1.{json,jsonl}` est **5/5 complète**,
0 échec, avec logs moteur des graines 42, 100, 999, 512 et 515222.
Bundle figé SHA256
`d85053ddcd41e57aa5a9f325ed5e783432643a45b227f1f0d8948a077da5cd7a`,
manifeste SHA256
`84f92fae9e76da64ca308fc501b367dde24fef09348a9675664e88001fa0a79a`,
Git `cb23a172` **dirty=1**, image `openttd-lab` SHA256
`f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Ce profil sondé finit 1975 avec profit Opex moyen 1,667 M£/an contre AAA
3,497 M£/an, uniquement descriptif et indépendant du 20×5 du 8 octobre.

### Chaîne effective et périmètre des dénominateurs

`OpexBuildCandidates` examine des paires, soumises à production/acceptation,
servi/proximité, distance et ratio. **`produced` ne désigne pas les projets
viables** : `candidates.nut:2090-2301` le construit depuis `pairsTotal`.
`candidates.nut:2221` garde en parallèle les TOP20 dans `rail.best`,
pour la préparation/stock ; `projects.nut:492-498` donne **tous**
`rail.candidates` au portefeuille normal. `projects_selection.nut:1144-1466`
applique budget/cash, floor, C70, C77 et TOP64 multi-mode. Après véritable
`PROJECT_CHOSEN`, `task_rail.nut` prépare les quais, lance la recherche
primaire, ou laisse patienter si `_railSearch` est déjà occupé. Une recherche
`RAIL_PREASTAR_START` peut prendre des centaines de jours ; `OK` conduit
ensuite au devis et à la pose, où `STNFAIL`, `TRKFAIL`, etc. restent possibles.
Le stock C121/`stock` et les `upgrade` de lignes existantes sont des voies
latérales, **pas des nouvelles lignes** : ne jamais additionner leurs OK.

La paire observée `(kind,cargo_label,src_tile,dst_tile)` déduplique les revisites
au sein d'une étape/année, mais **ne prouve pas une identité de projet stable**.
`RAIL_ATTEMPT` historique manque de `cargo`; le RID strict
`(arm,seed,repeat,tick_seq)` relie uniquement les événements
`RAIL_PREASTAR_START/END/BUILD`. Il ne relie pas cryptographiquement le
classement au chantier, ni `lineId` à la clé de stations physiques dans les
sauvegardes. Les rapprochements OD ci-dessous sont donc annotés *plausibles,
non uniques si un autre projet occupe la même paire*. `RAIL_BUILD` possède
`cargo,line,src,dst` mais pas `kind`. Le type destination industry→town est
dans `project.payload.dstTown` (ou `candidate.dstTown`), `isChain` à isoler ;
les logs annuels de choix n'exposent **pas** ces discriminants par projet.

Artefacts :

- `results/rail_p0_funnel_obs_5x6_20261009.analysis.json` : flux annuels par
  graine/année/cargo, OD distinctes, RID censurés et warnings.
- `results/rail_p0_funnel_obs_5x6_20261009.funnel.csv` : **table de funnel**
  par graine, année 1972–75, kind, cargo et catégorie de destination ; valeurs
  absentes volontairement laissées vides. Une ligne `cargo_mix_unresolved/town`
  compte des **paires examinées** et non des projets industry→town identifiés.
- `results/rail_p0_funnel_obs_5x6_20261009.rids.csv` : recherches par RID,
  mode primaire/upgrade/stock, dates, issue, itérations, statut d'appariement.
- `results/rail_p0_funnel_obs_5x6_20261009.summary.json` : agrégats par
  graine/année et autopsie des OD revisitées, avec confiance de jointure.

### Funnel effectivement observé, 1972–1975

Les chiffres agrégés suivants sont les **sommes de passages de reclassement**
dans cinq parties ; seules les colonnes `choix` et `tentatives` proviennent
d'événements distincts du scheduler/chantier. `retenu` désigne les occurrences
fret dans le TOP64, non un stock de projets uniques. Les mouvements historiques
de `rail.best` TOP20 constituent un flux **parallèle** non reporté ici.

| Année | Fret éligible / retenu (occurrences) | Passes avec fret éligible / sans aucun fret retenu | Choix fret | Tentatives fret achevées | RID primaires lancés | Upgrades lancés |
|---|---:|---:|---:|---:|---:|---:|
| 1972 | 977 / 774 | 63 / 6 | 3 | 0 | 3 | 6 |
| **1973** | **633 / 445** | **87 / 45** | **0** | **0** | **0** | **0** |
| 1974 | 1 679 / 1 449 | 150 / 3 | 3 | 4 (3 OK, 1 STNFAIL) | 3 (dont 1 pax) | 2 |
| 1975 | 2 444 / 2 215 | 176 / 2 | 3 | 1 (OK) | 3 | 2 |

*Les 1974/1975 RID commencent l'année indiquée, mais les tentatives achevées
peuvent correspondre à des recherches commencées en 1972.* Ainsi en 1974,
`seed42` COAL et `seed100` GOOD et `seed515222` COAL ont terminé leur
recherche antérieure ; compter `RID starts` et `RAIL_AUDIT attempt` séparément
est indispensable. Les dates exactes et valeurs sont dans les CSV.

À l'échelle des graines, **la pénurie de cash et la priorité AIR ne sont
pas le blocage unique** : seed512 n'a que 19 occurrences de fret éligible en
1973, zéro sélection de fret et zéro recherche A* en cours toute cette année.
Pour les quatre autres graines, une recherche primaire ou upgrade commencée
en 1972 occupe l'unique emplacement de recherche ferroviaire pendant 1973.
Ainsi l'absence de `PROJECT_CHOSEN` en 1973 est principalement cohérente
avec **le chantier A* antérieur**, et non avec un TOP20 destructeur ou avec
un score AIR supposé systématiquement supérieur au score C70 recalibré.
Les 45 passes sans fret retenu ne sont pas 45 pertes indépendantes ;
AIR et flotte peuvent aussi gagner la tête pendant les autres passes.

La génération des paires de destination est visible **sans identité OD** :
`RAIL_PREPAIR` totalise, sur les cinq graines, industrie→industrie
154/54/24/180 et industrie→ville 476/1753/501/2931 paires *examinées*
en 1972/73/74/75. Un `freight_cargo=-1` représente plusieurs cargos ;
les résultats peuvent être répétés ou invalide au niveau production.
Ne pas interpréter ces grands totaux comme autant de lignes potentiellement
rentables. Le tableau CSV conserve explicitement `cargo_mix_unresolved`.

### Temps, itérations, résultats et premières pertes dans les mêmes parties

Les 5×6 logs contiennent **38 RID**, dont 31 `OK`, 2 `ABND` plafonnés et 5
censurés ; modes : primaire 9 OK / 4 censures, upgrades 7 OK / 2 ABND /
1 censure, stock 15 OK historiques. Les `stock` 1970 sont surtout `READY` :
leur `OK` valide une recherche ou un plan, **pas** une nouvelle voie posée.
Des `OK` d'upgrade peuvent aboutir à `TRACKFAIL` après recherche : exemple
seed512, `rid=13791_5`, 1972-01-16→03-24, `OK` 5150 itérations puis
`RAIL_PREASTAR_BUILD failed:TRACKFAIL`; le nouvel upgrade suivant
`rid=15192_6` est `OK` et construit (823 itérations).

| Graine, type, RID | Début → fin | Durée calendaire | Issue réelle | Interprétation |
|---|---|---:|---|---|
| 100 GOOD primaire `15672_4` | 1972-04-27 → 1974-01-23 | **636 jours** | OK A*, construit début février 1974 | Ligne freight financée mais très différée |
| 42 COAL primaire `19274_7` | 1972-11-07 → 1974-11-20 | **743 jours** | OK 5472 itérations, puis `STNFAIL` | Deux années de slot immobilisé sans nouvelle ligne |
| 515222 COAL primaire `19805_6` | 1972-12-06 → 1974-05-29 | **539 jours** | OK 3035 itérations, construit | Réalisation tardive, malgré succès A* |
| 999 COAL upgrade `17152_4` | 1972-07-16 → 1975-03-05 | **962 jours** | `ABND` 10000/10000, `NOPATH` à pose | Empêche les primaires de démarrer sur cette carte |
| 100 COAL upgrade `27806_5` | 1974-02-12 → 1974-12-21 | **312 jours** | `ABND` 10000/10000 | Puis nouvelle upgrade censurée fin 1975 |
| 999 GOOD primaire `38896_7` | 1975-10-04 → 10-05 | **1 jour** | OK 125 itérations, construit | Contre-exemple : des primaires courts et viables restent possibles |

La durée est **la période en jours OpenTTD entre début et fin de recherche**,
pas un temps CPU constamment actif. Les budgets de 10 000 itérations ne sont
pas des limites en jours. Les cinq RIDs sans END sont censurés et ne
deviennent pas artificiellement ABND. Sur 1974, quatre tentatives de fret
`RAIL_AUDIT` dépensent **188 296 £ actualCost** et 27 718 846 opcodes
de **tentative** ; 1975 une tentative fret dépense 55 237 £. Le total 1975
tous genres (y compris pax) est 100 746 £ et 6 239 120 opcodes. Les
`actualCost` d'échec enregistrent les dépenses du builder, pas une preuve
de perte nette finale après rollback. Les millions d'opcodes d'A* avant
exécution sont distincts de `RAIL_AUDIT.opcodes` et ne s'additionnent pas
sans vérifier les périmètres de mesure.

### Trois autopsies économiques, avec contre-exemples

1. **Seed42 COAL 9815→13978.** Première élection le **07/11/1972** ;
   devis alors **39 153 £/an de profit prédit**, **46 168 £ de capital**.
   RID primaire 19274_7 de cette date à **20/11/1974**,
   résultat A* `OK`, 5 472 itérations ; chantier ultérieur
   `STNFAIL` le **28/11/1974**, coût builder enregistré 0 £,
   **aucune ligne construite**. C'est une perte **après élection,
   avant exploitation**, chiffrée en délai mais **sans profit réalisé
   contrefactuel**. L'autre diagnostic du 8/10 a isolé sur une trajectoire
   instrumentée différente le lead de gare ERR_AREA_NOT_CLEAR/TRKFAIL :
   ne pas fusionner ce motif avec `STNFAIL` de la seed42 actuelle.

2. **Seed100 GOOD 29583→46727.** Élection le **26/04/1972**, profit prédit
   **111 209 £/an**, capital **52 305 £**. RID 15672_4 lancé le lendemain,
   `OK` le **23/01/1974** (6 393 itérations). Pose réussie le **03/02/1974**,
   `RAIL_BUILD line=33` le 04/02 ; coût de chantier **64 187 £**.
   La télémétrie de cette *même* partie montre en décembre 1974 une seule
   ligne GOOD nouvelle identifiable par stations `rail|146,147`, véhicule454,
   profit YTD **−2 074,55 £**, encore **−2 315,82 £** en décembre 1975.
   La correspondance de cargo et de fenêtre suggère cette liaison mais
   **aucune colonne `lineId=33 ↔ station-pair` ne prouve l'identité exacte**.
   Il est donc illégitime de soustraire mécaniquement ces résultats de
   **111 209 £** ou de conclure à une perte de 64 187 £ : prévision annuelle,
   coût d'investissement et profit YTD partiel ont des sens différents.

3. **Seed515222 COAL 25670→45133.** Élection et début de RID 19805_6 le
   **06/12/1972**, profit prévu **46 986 £/an**, capital **44 567 £**.
   A* `OK` le 29/05/1974, pose `OK` le **14/06/1974**, coût chantier
   **51 087 £** ; YTD observé pour la *nouvelle paire COAL* `rail|172,173`
   (veh595) **+11 865,85 £ en décembre 1974** puis **+30 360,18 £ en
   décembre 1975**. Appariement OD→stations non strict : ce cas démontre
   néanmoins que des ajouts tardifs peuvent mûrir. Sur cette même graine,
   WOOD 26809→40081 élu le 15/06/1974, 173 jours de A*, construit
   13/12 pour 73 022 £, 34 287 £/an prévus ; une nouvelle paire WOOD
   apparaît en 1975 avec +31 151,18 £ YTD (identité OD non directement
   enregistrée dans le snapshot).

**Contre-exemples nécessaires.** Le GOOD nouveau seed999 posé en octobre 1975
termine un primaire en **125 itérations / 1 jour** ; profit observé de la
nouvelle paire GOOD en décembre 1975 **+3 093,64 £** (maturité censurée).
Une référence historique **distincte** `rail_failure_audit_5x6_20261008_r1`
montre seed100 OIL_ 44757→57293 : trois TRKFAIL les 02/12/1974,
03/01/1975 et 23/02/1975, puis **OK le 13/05/1975** ; interdire
définitivement une paire au premier échec aurait sacrifié ce vrai succès.
Inversement, des nouvelles lignes GOOD de la présente cohorte restent
déficitaires en YTD. Ni un préfiltre A*, ni plus de trains, ni une mémoire
TRKFAIL ne garantissent un gain net.

### Profits physiques validés, et séparation d'avec l'investissement

`line_telemetry` de **la même campagne 5×6** a 60/60 snapshots annuels
concordants avec le nombre de trains rail primaires des JSONL (deux véhicules
AAA non-rail sans ordre résolu, uniquement 1971). Totaux **cinq graines**
pour le fret pur, sans PASS/MAIL/mixte :

| Décembre | Trains fret Opex / AAA | Profit des véhicules fret YTD Opex / AAA |
|---|---:|---:|
| 1972 | 17 / 33 | 222 956 £ / 1 757 295 £ |
| 1973 | 17 / 68 | 224 389 £ / 2 779 998 £ |
| 1974 | 19 / 106 | 229 159 £ / 3 981 812 £ |
| 1975 | 22 / 128 | 282 412 £ / 5 962 550 £ |

Seules **quatre nouvelles paires fret** apparaissent entre les checkpoints
1973→1974 et 1974→1975 ; apparition de paire ne signifie nouvelle ligne
sans vérifier `vehicle_ids`. Exemple seed512 WOOD véhicule52 change de
`rail|25,26` à `rail|25` dès 1972 : ce n'est **pas** un nouvel
investissement. Les sommes YTD sont partielles au **1er décembre** :
elles ne sont ni `profit_year` à quatre trimestres clos ni un retour cash
sur construction. La chronique de **20 graines du 08/10** (bundle distinct)
montrait déjà déficit ferroviaire 1974 5,8 trains Opex/33,2 AAA, mais elle
présente **3 discordances de véhicules sur 200 checkpoints** dans le sous-
traitement cargo ; garder les campagnes distinctes.

### Hiérarchie causale et seul candidat de correctif

1. **Démontré, première perte principale sur 4/5 graines en 1973 :**
   `_railSearch` unique reste monopolisé par un primaire ou upgrade démarré
   en 1972. Quatre recherches significatives dépassent 500 jours, dont
   une upgrade plafonnée après 962 jours. La sélection continue de
   produire des alternatives fret, mais aucune nouvelle primaire n'est
   lancée en 1973. **Délai constaté et immobilisation de l'accès au worker
   prouvés ; valeur des projets non exécutés inconnue.** Seed512 constitue
   le contre-exemple nécessaire avec fret éligible rare, non retenu et
   absence de recherche active.
2. **Démontré, pertes secondaires à la pose :** un `OK` d'A* peut finir
   `STNFAIL`/`TRACKFAIL`; cas seed42 après 743 jours et seed512 sur
   upgrade. Sur la campagne indépendante 3×6 du 8/10, seed42 subit
   29 TRKFAIL sur deux OD, 218 851 £ `actualCost` et 80,55 M opcodes
   de tentatives : cette répétition est réelle **dans son bundle propre**,
   mais la mémoire corrective 40×5 a ensuite échoué économiquement.
3. **Plausible et hétérogène avant l'élection :** classement C70/C77,
   rotation cargo, production/acceptation et cash. En 1973 633 occurrences
   éligibles/445 retenues et 45 passes éligibles sans fret retenu ;
   ces nombres ne mesurent ni projets uniques perdus, ni rentabilité
   vérifiée. Aucun résultat n'établit une domination AIR universelle.
4. **Plausible pour la rentabilité finale (H3) :** des nouvelles lignes
   sont moins rentables que leurs prédictions et certaines mûrissent
   avec délai. Aucun profit de projet jamais construit n'est observable.
   Les exemples positifs et négatifs **réfutent** l'identification du
   nombre de trains à l'utilité économique.
5. **Défaut de code distinct, exposition économique inconnue :**
   `rail_prep_c121.nut:253-256` et `task_rail.nut:1860-1863,2162-2166`
   demandent un IndustryID à destination des freight→town, malgré
   `candidate.dstTown` correct. La préparation C121 est active au défaut
   courant (`c121_air_first_year_rail_prep=1`) ; le worker C80 de stock
   reste OFF. Cette erreur coupe une branche de préparation et mérite une
   vérification locale, mais n'explique pas directement 1973 sans compter
   **les vrais candidats fret→ville qui atteignent cette garde**.

**Une seule proposition P0 à tester, pas à adopter :** mécanisme de **reprise
coopérative de plusieurs recherches A* ferroviaires**, conservant l'état
propre à chaque recherche, les budgets individuels et leur ordre logique,
mais permettant à une primaire en attente de consommer des tranches lorsque
une upgrade monopolise `_railSearch`. Le déclencheur est causalement
documenté : upgrade COAL seed999 **962 jours** pendant que le chemin des
nouveaux rails reste fermé, puis GOOD `OK` en **125 itérations / 1 jour**
après libération du slot. Ce n'est ni un seuil de distance, ni une coupe
d'itérations, ni une mémoire d'échec, ni une augmentation de stock.
Ce candidat **reste non validé et non implémenté** : il faut d'abord prouver
qu'un second état A* indépendant est reprenable sans replanification,
établir le nombre d'`OK` sacrifiés, les chemins réellement posés et la
concurrence de cash/opcodes entre tracés, et comparer un replay figé
référence/candidat sans instrument intrusif. La porte A gain_short V102
40×3 (ou horizon alternatif annoncé **avant** le banc), puis la porte B
non_erosion 20×10 sont requises si ces conditions sont satisfaites.
Une simple augmentation de trains ou une réduction d'opcodes ne suffira pas.

### Reproduction HOST et moteur

```powershell
python -X utf8 -m unittest discover -s sweeps -p test_analyse_rail_pipeline_p0.py
python -X utf8 -m unittest discover -s sweeps -p test_analyse_rail_preastar.py
python -X utf8 sweeps/analyse_rail_pipeline_p0.py results/rail_p0_funnel_obs_5x6_20261009_r1_engine --out results/rail_p0_funnel_obs_5x6_20261009.analysis.json --funnel-csv results/rail_p0_funnel_obs_5x6_20261009.funnel.csv --rid-csv results/rail_p0_funnel_obs_5x6_20261009.rids.csv
python -X utf8 sweeps/rapport_rail_pipeline_p0.py results/rail_p0_funnel_obs_5x6_20261009.analysis.json --out results/rail_p0_funnel_obs_5x6_20261009.summary.json
python -X utf8 sweeps/analyse_rail_freight_snapshots.py results/rail_p0_funnel_obs_5x6_20261009_r1.json --policy rail_p0_observation --crosscheck-jsonl results/rail_p0_funnel_obs_5x6_20261009_r1.jsonl
```

Commande exacte de collecte (déjà terminée, **ne pas relancer** sans raison) :

```powershell
python -X utf8 sweeps/run_c66_reference.py --campaign rail_p0_funnel_obs_5x6_20261009_r1 --reference "OpexAI[rail_freight_select_shadow=1,rail_failure_audit=1,probe_rail_preastar=1,rail_origin_exposure_shadow=1,rail_origin_exposure_detail_shadow=1,decision_log=1,probe_portfolio=1]" --policy-id rail_p0_observation --years 6 --seeds 42 100 999 512 515222 --repeats 1 --cpus 10 --memory 8g --max-workers 5 --script-debug --line-telemetry
```

L'étude ne touche aucun défaut, ne livre aucun correctif comportemental et
ne qualifie aucune politique économique. Les données additionnelles
indispensables pour un contrefactuel sont le lien strict
`project_id/RID/lineId/stationIDs`, le type de destination de chaque candidat
et la maturité de revenu sur une fenêtre commune.

### Prolongement P0 : score exactement au refus, recherche occupante et limite du contrefactuel

La seconde campagne `rail_p0_blocked_score_5x6_20261009_r1`, cinq duels
complets et sains, est entièrement documentée dans
[l'autopsie du créneau A*](rail_p0_blocked_opportunity_20261009.md).
Elle utilise le bundle distinct `293d8e65…` et les sondes minimales
`rail_failure_audit=1,probe_rail_preastar=1` : **aucun des comptes ci-après
ne doit être fusionné** avec le premier funnel `d85053dd…`.

Sur 7 627 refus A* logués, **623 fret** avec cargo et score du projet
au moment du refus sont appariés strictement, **105** sont des visites de
la paire déjà en recherche. **518** visites concernent donc des paires fret
concurrentes, soit **83 paires-années**, **64 OD+cargo+graine uniques**
sur 1972–1975. Pour 1973 seul : **175 visites, 21 paires fret distinctes**,
toutes avec un score initial strictement positif ; il n'existe toujours
aucun profit réel des possibilités non construites. Les rangs et scores
ne garantissent ni chantier réalisable ni financement live à la pose.

Un événement probant : seed515222 le **1973-08-15**, 14 alternatives
fret finançables selon le portefeuille et 14 retenues, dont quatre paires
COAL concurrentes de rangs 1–4 et de profit prévu 35,9–40,8 k£/an
refusées `search_in_progress` pendant le vrai A* `RID 23756_6` ;
celui-ci finit `OK` le 28 octobre et le chantier est `OK` le 3 novembre.
Un achat réel de flotte intervient pendant ce blocage ; un bypass AIR
est autorisé le 16 août, sans preuve de construction issue du bypass.
Aucun contrefactuel n'établit qu'un second A* aurait abouti ni quel
capital/profit net il aurait produit. Trois OD fret initialement refusées
ont plus tard fait l'objet d'un RID construit sur cette cohorte ; aucune
mémoire de refus permanent ne serait sûre.

Verdict : **goulot de lancement A* causalement identifié, bénéfice
économique d'un ordonnanceur N=2 non démontré**. Techniquement faisable
à la condition de conserver un budget d'opcodes global, les vrais `OK`
et les sémantiques de chantier et Save/Load. La refonte N=2 n'est pas
implémentée ni qualifiée : il manque un essai de comportement conservant
les réussites historiques et mesurant constructions/profits après capital.
Le premier correctif prioritaire reste donc à l'état d'expérience isolée
à spécifier, avant toute porte V102 ou adoption.
