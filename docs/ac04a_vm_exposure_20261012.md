# AC04-A — autopsie causale, VM à état fixé et exposition

12 octobre 2026. Périmètre : analyse et fixtures dédiées, sans modification des
modules de production ni nouvelle qualification d'adoption. Les variantes AC04-A
v1 et v2 restent rejetées. La v3 `ac04_hub_usage_gate` est traitée séparément par
le pilote du chantier.

## P0 — ventilation des preuves conservées

L'anomalie reste présente dans la découverte historique : le premier passage
saute un aéroport avec `routeCount >= maxRoutes` avant de marquer son
`stationId` dans `seenStations` (`air_planning.nut:1300–1354`) ; le passage
`AIStationList(STATION_AIRPORT)` peut le reprendre comme orphelin avec
`routes=0` (`:1359–1377`). `OpexAir0310RefreshHubRoutes` ne rafraîchit pas les
orphelins (`:1065–1074`). Le garde physique en fin de batch reste distinct de
cette découverte et n'établit pas à lui seul l'absence d'éviction de projets.

Les mesures existantes, sans aucune nouvelle partie :

| Population et fenêtre | Profit OpexAI ON−OFF | LOOP_OPS globaux ON−OFF | Lecture |
|---|---:|---:|---|
| A40×3, terminal 1972 | +6 354 £/an ; IC95 [−33 552 ; +46 341] | H5 **partiel** +3,885 M, +21,55 % | Aucune preuve de gain économique à cette porte ; H5 ne mesure pas le total VM |
| 40×4, années VM closes 1970–1971 | terminal 1973 +113 600 £/an, IC95 [+55 294 ; +175 042] | **+213 974 op**, +0,170 %, IC95 [+72 713 ; +370 559] | Hausse globale étayée au début de partie |
| Les mêmes 40×4, années VM closes 1970–1972 | même terminal économique | +497 231 op, +0,258 %, IC95 [−340 494 ; +1 464 993] | Hausse globale non établie sur cette fenêtre plus longue |
| AC04-A v2, 10×4, années VM closes 1970–1971 | non rapprochable de façon causale au profit du précédent bundle | +307 376 op, IC95 [+92 855 ; +609 554] | L'optimisation du recomptage n'a pas éliminé le signal initial |

L'H5 du premier A40×3 alloue **+2,669 M** opcodes à `rail_attempt`
et **+0,767 M** à `selection` ; 24/40 graines sans variation du nombre de
`rail_attempt` ont un écart moyen de **−2 724** opcodes sur ce poste, contre
**+6,676 M** pour les 16/40 à nombre de tentatives différent. C'est un
indice puissant de trajectoires différentes. Cela ne prouve pas le prix d'un
appel intrinsèque du correctif AIR : les entrées d'un même appel peuvent
également changer.

`sweeps/test_ac04_causal_existing.py` relit les deux résumés de VM gelés
`ac04a_opcode_loop_10x4_20261011_phase_summary.json` (10 graines) et
`ac04a_extension30_opcode_loop_10x4_20261011_phase_summary.json`
(30 autres graines) sous `results/ac_fixes_worktree_20261011/results/`.
Il vérifie 40 graines distinctes, source figée, années alignées, postes
disjoints et recomposition exacte du total :

| Poste LOOP_OPS, moyenne par paire | 1970–1971 | 1970–1972 |
|---|---:|---:|
| `orchestrator` | **+512 127** | **+3 367 840** |
| `catalog_continuation` | **−303 995** | **−2 599 814** |
| `events` | +8 187 | −728 344 |
| `c117_sample` | −149 | +446 893 |
| `rail_throughput` | −1 499 | +7 349 |
| **Ensemble des postes exécutés** | **+213 974** | **+497 231** |

En 1970–1971, `orchestrator` change de nombre d'invocations sur **34/40**
graines : le delta moyen sur ces 34 est **+620 159** opcodes. Sur les **6/40**
sans changement de ce nombre, le delta moyen est **−100 052**. Pour
`catalog_continuation`, le nombre d'invocations change sur **35/40** ; le
delta moyen est **−346 539**, contre **−6 186** pour les cinq graines à
compte identique. En 1970–1972, `orchestrator` change de compte sur 39/40.
Ces données sont cohérentes avec un travail et des reprises réorganisés ;
elles ne constituent **pas** un microbenchmark du helper, et égalité de
compte ne signifie jamais égalité d'état, de projets ou de coût par appel.

Ne pas comparer les totaux bruts entre bundles AC04-A v1 et v2 : leurs bras
OFF ne sont pas identiques. Les contrastes recevables sont les paires OFF/ON
internes à un bundle figé. L'année terminale VM n'est pas close dans le
`LOOP_OPS` : dans les parties de quatre ans, 1973 est censurée ; 1973 est
uniquement l'année du terminal économique.

## P1 — fixture Squirrel à état fixé

`sweeps/test_ac04_causal_vm.py` produit dans un **répertoire nouveau** une
copie de `ai/OpexAI`, insère `ac04_causal_vm.nut` dans cette copie et la fait
charger au démarrage de l'IA. La fixture utilise la fonction de comptage
historique `OpexAir0310CountStationRoutes`, l'horloge VM `OpexOpsClock` et
des doublures temporaires des API station/ligne. Elle restaure les doublures
avant l'activité normale. Aucune écriture ne touche le code de production.

La matrice projetée compare quatre séquences : comportement historique,
AC04-A v1 (recompte à la passe orpheline), AC04-A v2 (marquage précoce et
index) et accès direct ciblé. Elle parcourt les cinq cas **zéro ligne, hub
libre, saturé, vrai orphelin, lignes mortes**, sous C80 OFF/ON et avec/sans
rafraîchissement de snapshot simulé. L'ordre de mesure alterne ABCD puis
DCBA, chaque bras exécutant 16 répétitions, avec une enveloppe vide à
soustraire et un digest des identités/routages. La sortie
`AC04_CAUSAL_VM` permet de calculer un coût **par invocation sur la même
entrée et dans la vraie VM NoAI**. Le script exige les 160 lignes de mesure,
leur unicité et les sorties des variantes convergentes sur ces données.

La fixture rejoue **le noyau de découverte** sur données synthétiques et
une projection de refresh ; elle ne mesure pas l'intégralité de
`OpexAirPlansDiscoverHubs`, de la revalidation, du classement ou des
interactions avec le monde réel. Ses résultats ne remplacent ni le contrôle
des entrées réelles ni les portes d'économie/opcodes globales.

Commandes reproductibles, depuis la racine :

```powershell
python -X utf8 -m unittest -q sweeps.test_ac04_causal_existing sweeps.test_ac04_causal_vm
python -X utf8 sweeps/test_ac04_causal_existing.py
python -X utf8 -m sweeps.test_ac04_causal_vm --prepare-out results/ac04_causal_vm_stage_20261012
```

Après coordination d'un créneau Docker dédié seulement :

```powershell
python -X utf8 -m sweeps.test_ac04_causal_vm --run-out results/ac04_causal_vm_20261012
```

L'exécution du harnais dans l'image NoAI doit vérifier compilation,
`AC04_CAUSAL_VM_COMPLETE pass=1`, 160 enregistrements complets, absence
d'assertion, sorties identiques pour les projections correctives, stabilité
par ordre et coût supplémentaire net en opcodes. Si ces contrôles échouent,
la mesure ne peut pas fonder une décision causale.

## P2 — exposition passive à pré-enregistrer avant son instrumentation

La sonde à réaliser **dans une copie d'essai dédiée et sous drapeau
OFF par défaut** doit suivre l'identité du candidat pendant les scans. Une
ligne d'exposition se définit par `(seed, date, scan-id, combo, airportType,
planeType, stationId, OD, arm, siteAnchor, restored, pairOrdinal)` ;
`stationId` mesure les hubs uniques, `(hub-station, site-anchor)` les
paires hub→site et `(hub-stationA, hub-stationB)` les paires hub→hub. Ne
pas agréger ces trois dénominateurs comme s'ils étaient interchangeables.

L'état au point de comparaison expose séparément
`historicalRoutes` (toutes les lignes AIR enregistrées),
`liveDiscoveryRoutes` (lignes non rejetées pour `deadStreak>=2`) et
`batchCapacityRoutes` (compteur utilisé juste avant chantier). Un simple
`stationId in hubIndex.routes` indique une station reliée dans
**l'historique**, pas nécessairement une station découverte comme vivante.
Sous C80=0, le repli dénombre explicitement les lignes, sur les mêmes
résolutions de StationID que la garde historique. Conserver C83, V93,
AIR_HUB_FIX, les différents types d'aéroport, les curseurs et
topologies Save/Load dans l'échantillon.

Les champs par combo distinguent : nombre de stations faussement
orphelines **uniques** ; nombre de paires effectivement parcourues,
éliminées avant devis, économiquement évaluées, admises puis retenues dans
le TopN/Top64 ; nombre réellement sélectionné et nombre finalement mort
`batch_plan_dead`. Pour le lien causal, conserver la première paire
`false_orphan` qui franchit la sélection, son rang et le meilleur candidat
AIR/RAIL valide qui aurait pris sa place dans un **contre-factuel hors
ligne** bâti depuis les traces de vivier complètes.

Le journal doit rester borné (agrégats par scan + au plus un petit
échantillon déterministe de paires par cas) ; les identités supplémentaires
ne doivent pas modifier le classement ni les curseurs. Faire d'abord une
campagne **A/A** avec instrumentations OFF et ON ou symétriques, en observant
le coût du journal, puis appliquer strictement le même instrument aux
deux bras d'un futur A/B. Ne jamais déclarer une paire « non exposée » à
partir du seul compte des hubs faux : l'exposition importante est le devis
payé et surtout l'éviction de projet viable dans le portefeuille commun.

## Correction minimale à étudier et décision restante

La piste la plus étroite reste une garde au **point d'usage** des hubs dans
hub→site et hub→hub, couvrant **première génération et reprises**. Pour
chaque StationID, calculer la capacité exacte une fois par combo, réutiliser
`ctx.hubIndex.routes` sous C80=1 et compter les lignes sous C80=0, puis
exclure la paire avant devis lorsque saturée. Garder inchangés l'ordre des
hubs, leurs ancres et les indices `hubSiteI/J`, `hubHubI/J`. Vérifier les
stations à seules lignes mortes et les variations de topologie à travers
la signature du snapshot. La nouvelle piste expérimentale
`ac04_hub_usage_gate` du pilote correspond à cette famille ; aucune
adoption n'est décidée dans ce rapport.

Même si la fixture VM révèle un coût intrinsèque négligeable, la hausse
globale déjà mesurée garde son statut de fait expérimental. L'utilisateur
autorise désormais une **légère** hausse d'opcodes compensée par une
amélioration économique **effectivement prouvée**, sans tolérance chiffrée
inventée. Il faut donc qualifier la variante v3 isolée avec exposition
mesurée, profits, valeur d'entreprise et `LOOP_OPS` globaux appariés,
notamment **1970–1971** et **1970–1972** comme fenêtres distinctes.

**État à la rédaction :** P0 reproduit localement ; tests Python du harnais
réussis ; exécution Squirrel VM en attente d'un créneau Docker coordonné ;
aucune preuve de coût intrinsèque, d'exposition du TopN ni d'adoption
nouvelle pour AC04-A.
