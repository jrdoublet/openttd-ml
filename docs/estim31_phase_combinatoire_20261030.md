# ESTIM-31 — phase combinatoire et neutralité de référence (30 octobre)

## Protocole et état du travail

**Mandat :** maximiser exclusivement le ratio des moyennes de `profit_year`
OpexAI / AAAHogEx-115 au 1er décembre 1974, sur 40 cartes 256² appariées,
1970–1974. La valeur, Wilcoxon, IC95 et l'ancien gain minimal ne sont **pas**
des critères éliminatoires. La santé du banc et la séparation OFF sont des
préconditions techniques indépendantes du classement économique.

**Point de départ gelé :** `experiments/estim31-c121-dispatch-20261029`
commit `89463ad0`, son 40×5 ESTIM31 qualifié **90,8789 %**
(Opex 2 627 711 £/an, AAA 2 891 442 £/an) et OFF historique **95,1563 %**
(Opex 2 856 233, AAA 3 001 621). Trois autres 40×5 terminés donnent
89,7763 %, 88,1498 % et 87,8014 % avec 401, 440 et 318 discordances
de snapshots OFF inter-campagnes. **Ne pas relancer ces campagnes.**

### Diagnostic OFF : séparer les quatre sources d'écarts

- **Source** : les bundles 40×5 des trois nouvelles variantes diffèrent de
  la source C121 de référence essentiellement par des paramètres globaux
  d'ESTIM (ou leurs commentaires). Ces paramètres ne doivent pas modifier la
  politique OFF. L'approche modulaire sépare plus strictement les octets
  historiques C121 d'un module FullScan `require()` uniquement si
  `estim_unifie & 1`, sans élagage par la borne C121 non démontrée ; en OFF,
  les scans historiques et `C121_GE` sont inchangés.
- **Configuration** : dans les manifestes 40×5 précédents, `reference`
  résout `OpexAI[probes=2]`, `estim_unifie=0`, EB14=0 et les mêmes paramètres
  effectifs, cartes, horizon et taille d'échantillon. Un réglage expérimental
  défini seulement pour la politique `variant` ne doit jamais s'appliquer au
  témoin. Le chemin OFF doit être testé à source byte-identique.
- **Instrumentation** : même `probes=2` sur les quatre lots ; jamais
  `probes=770`. Le diagnostic C63 et les journaux de choix de moteur obtenus
  avec `probes=258` sont **distincts** et peuvent déplacer la chronologie.
- **Exécution** : le même chemin OFF produit déjà cinq différences sur seed999
  entre les 5×5 et 40×5 du bundle historique, et les OFF de trois bundles
  récents divergent aussi **entre eux** (jusqu'à plusieurs centaines de
  champs), souvent en 1972–1974 et dans les deux sociétés. Cela démontre
  une reproductibilité inter-campagnes imparfaite ; le rôle exact des huit
  workers, des changements de source inactifs et du moteur est à isoler.

La stricte identité des paramètres et des sources **exécutées** est plus
fondamentale qu'une égalité bit-à-bit du résultat d'une simulation
stochastique multi-processus. Il reste toutefois nécessaire d'expliquer et
de documenter les discordances avant de promouvoir une variante récente.

## Nouveau criblage combinatoire préparé (AUCUN résultat économique encore)

Les huit bundles `results/estim31_joint_next20261030/` proviennent de
`module_a150_r100_w15`, où le C121 historique est restauré octet pour
octet et le FullScan expérimental chargé sous ESTIM seulement. Le générateur
est `sweeps/estim31_joint_next_prepare.py` ; tests de contrats
`sweeps/test_estim31_joint_next_prepare.py` ; lanceur séquentiel Docker
`sweeps/run_estim31_joint_next_20261030.ps1` ; lecteur des duels
`sweeps/estim31_joint_next_analyse.py`.

| Scénario (prefix `mix_`) | AIR | RAIL | Poids | Profil | EB14 | Statue | EB2 | Charge min AIR |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| `a100_w15_statue0_eb2` | 1,00 | 1,00 | 15 | incliné | 3 | 0 | 1 | 0 |
| `a100_w15_statue0_load25` | 1,00 | 1,00 | 15 | incliné | 3 | 0 | 0 | 25 |
| `a125_r125_w05_flat_statue0` | 1,25 | 1,25 | 5 | plat | 3 | 0 | 0 | 0 |
| `a125_w15_eb142_load25` | 1,25 | 1,00 | 15 | incliné | 2 | 2 | 0 | 25 |
| `a100_r125_w15_eb142_statue0` | 1,00 | 1,25 | 15 | incliné | 2 | 0 | 0 | 0 |
| `a125_w15_eb2_load25` | 1,25 | 1,00 | 15 | incliné | 3 | 2 | 1 | 25 |
| `a150_w15_statue0_eb2` | 1,50 | 1,00 | 15 | incliné | 3 | 0 | 1 | 0 |
| `a075_r125_w15_statue0` | 0,75 | 1,25 | 15 | incliné | 3 | 0 | 0 | 0 |

Le croisement statue0 × coefficient AIR veut tester si la trésorerie libérée
finance effectivement des ouvertures AIR/hubs et des moteurs 223/228
rentables ; EB2 × charge25 veut tester si la réallocation du capital vers
la gare et les avions a un effet favorable **ensemble**, malgré des effets
isolés possiblement négatifs ; EB14=2 évite le travail PO01C 1970 lorsque
son conflit avec l'amorçage AIR n'est pas compensé. Les profils de distance
plat/incliné et le poids d'a priori sont couplés au facteur RAIL, pas balayés
indépendamment. **Toutes ces propositions restent des hypothèses.**

Le programme ne touche pas `master` ni les valeurs par défaut, n'ajoute
aucune constante au produit, ne requalifie pas les variantes déjà achevées
et refuse explicitement de commencer si `docker ps` constate un Docker actif.
Un autre processus, `results/estim31_joint_newgrid20261030`, détenait le
seul Docker au contrôle initial ; il n'a pas été interrompu ou doublé.

**Mesures exigées avant décision :** ratio 5×5, profit Opex et AAA séparés,
nombre et moment de divergences OFF, provenance SHA, stock 223/228, cash,
prêts, aéroports, trains, ville desservie et opcodes observés. Les
investissements ne doivent pas être assimilés aux devis ni à
`AIAccounting`. Les capex réellement décaissés, ventes/remboursements et
rollback exigent un protocole distinct non perturbateur ou dûment comparé
à son témoin ; sans cela ne rapporter que le résidu non attribué
`profit_year + Δloan − Δcash`.

## État de validation

- Bundles préparés de façon write-once, C121, settings et globals historiques
  byte-identiques aux fichiers figés d'entrée ; fichier FullScan unique
  modifié sous ESTIM uniquement.
- 3 tests de séparation source + 4 contrats C121 existants : **7 OK**.
- Aucun Docker créé, aucun essai économique de cette nouvelle série déclaré
  terminé tant que son résumé `.json` de fin n'existe pas.
- Les tests généraux antérieurs sur `89463ad0` : **3 131 OK** (6 ignorés,
  2 échecs attendus) ; relancer après toute modification comportementale.

## Révision technique après audit (05:55–05:58, avant nos nouveaux duels)

Le générateur initial `estim31_joint_next_prepare.py` ne doit **pas** être utilisé
pour de nouvelles qualifications sans modification : il injecte les priors au
premier `OpexC121ChooseRoutePlaneFullScan`, donc trop tard pour les calculs
antérieurs, et peut réinitialiser un coefficient appris après Save/Load.
En outre, `C121_GE` peut court-circuiter la recherche exhaustive même avec
la borne d'élagage désactivée. Cela préserve bien le fonctionnement OFF
historique, mais ne garantit pas l'argmax sur chaque nouveau projet ESTIM.

**Solution expérimentale isolée** : `estim31_joint_safe_prepare_20261030.py`
construit onze bundles `results/estim31_joint_safe20261030/`. Il affecte
AIR/RAIL/poids et éventuellement le profil plat au **chargement du module**
`air_economics_c121_fullscan.nut`, via le `require()` opt-in, avant la copie
des priors vers les niveaux dans `settings.nut`. Sous ESTIM il neutralise
la branche shortcut de `C121_GE`, tout en gardant les deux scans historiques
et `C121_GE` **octet pour octet** identiques sur le chemin OFF.
Le scan expérimental conserve les contrôles physiques et l'ordre par borne
indicative, mais aucun arrêt par une borne économique non démontrée.
Trois des onze combinaisons reprennent des interactions prometteuses de la
grille concurrente avec ce correctif de validité :

| Scénario safe complémentaire | AIR | RAIL | Poids | Profil | Charge minimale |
|---|---:|---:|---:|---|---:|
| `mix_a200_r150_w05_flat_load25` | 2,00 | 1,50 | 5 | plat | 25 % |
| `mix_a200_r075_w15_slope` | 2,00 | 0,75 | 15 | incliné | 0 |
| `mix_a175_r125_w30_flat` | 1,75 | 1,25 | 30 | plat | 0 |

Autre interaction : deux copies `results/estim31_railnorm_safe20261030/`
réutilisent les bundles sûrs et, sous ESTIM bit16 uniquement, multiplient
`line.predRevenue` par `OpexEstimRailRevenueFactor(distance)/ESTIM_K_R.rail`
avant d'accumuler la recette prédite. Le flux `candidate.revenueAnnual` vers
`line.predRevenue` est brut du profil ESTIM RAIL : l'opération normalise donc
le niveau appris par rapport au profil déjà appliqué au score, sans ajouter
de constante. Précaution : des sauvegardes anciennes et déjà calibrées ne
doivent pas être mélangées aveuglément avec la nouvelle somme.

**Le test de reproductibilité OFF est maintenant exécutable sans Git dans le
bundle** : `sweeps/estim31_off_replay_20261030.ps1`, image figée et contrôle
préalable d'exclusivité Docker, 999 et 2026 × deux répétitions, `probes=2`,
un worker initialement. `estim31_off_replay_analyse_20261030.py` contrôle
les quatre parties, les 480 snapshots mensuels, la provenance et les
**1 680 comparaisons** (sept champs × deux compagnies × deux graines × 60 mois),
puis attribue toute divergence à une graine/compagnie/date/champ. Les nouveaux
contrats Python synthétiques de ce lecteur passent ; **aucun replay réel
n'est déclaré terminé à cette date**.

Les contrats ciblés hors simulation ont passé **13 tests**, incluant les
copies safe et railnorm ; le lancement des parties et le contrôle Save/Load
graine999 restent nécessaires. Les éventuels verdicts `gain_short` du runner
ne sont jamais utilisés comme filtre de classement dans cette campagne.

### Signaux de la grille concurrente (5×5 seulement)

Lecture directe des `.jsonl` et résumés existants, sans modifier le processus
concurrent : AIR 2,00 / RAIL 1,50 / poids5 / profil plat / garde25 atteint
**93,204 %** (Opex **2 588 633 £/an**, AAA **2 777 388 £/an**), cinq
graines, 0 divergence OFF historique ; AIR 2,00 / RAIL 0,75 / poids15
atteint **90,227 %** (Opex **2 648 813**, AAA **2 935 729 £/an**),
0 divergence OFF ; AIR1,75 / RAIL1,25 / poids30 / plat affiche
**88,095 %**, mais 10 discordances OFF et pas de qualification 40×5.
L'ancien ESTIM31 vaut **83,203 %** sur ses propres cinq graines de référence ;
la dispersion entre duels et la faiblesse du dénominateur AAA de certains
scénarios empêchent de conclure avant le 40×5.

**Limite essentielle** : ni ces JSONL ni les stocks moteurs 223/228 ne
permettent de déduire les achats bruts, le CAPEX réel par catégorie, les
reventes et les rollbacks. Les devis `AIAccounting` peuvent inclure du
`AITestMode` et ne seront jamais présentés comme décaissements certains.

### Contrôles réels ajoutés à 06:07–06:10

**Rejeu OFF à un worker TERMINÉ** : même bundle `a150_r100_w05` historique,
source SHA `88eb2adbb9a61b6a53fed36362906b80c49719613515206d79eeba4d3ee44ff4`,
image figée, graines 999/2026 répétées deux fois, `probes=2`, quatre parties
saines. Sur **1 680 comparaisons** des sept champs, **12 divergences** :
`AAAHogEx_999` 7, `OpexAI_999` 5 ; premier écart
`1974-10-01` dans les opcodes Opex (37 920 697 contre 37 920 856), puis
trésorerie et profits/valeur. Graine2026 identique. **La contention entre
8 workers n'est donc pas nécessaire pour observer une dérive** ; l'origine
RNG/exécution exacte reste indéterminée, ne pas l'imputer sans preuve.
Rapport calculé par `sweeps/estim31_off_replay_analyse_20261030.py` et contrôles
synthétiques dédiés. Le replay à 8 workers pourrait préciser la fréquence
mais ne répare pas cette reproductibilité interne à un worker.

**Save/Load seed999 de la combinaison sûre AIR2/RAIL1,5/w5/plat/load25
TERMINÉ**, image figée, `probes=2`, `script-debug 4` : phases A/B une année
chacune, **13 saves en A et 13 en B**, reprise authentique de la save
`1970-07-01`, marqueur `LOAD_RECONCILE saved=4 kept=4 dropped=0`, statut OK,
aucune erreur moteur signalée. Une entreprise humaine fantôme inactive
apparaît après rechargement (artefact connu du harnais) : cela confirme la
reprise et la persistance de l'IA, **pas l'égalité stricte avec la trajectoire
sans recharge**. Source et paramètres de la copie correspondent aux hashes
du `design.json`. Sous `probes=2`, `DECISION_LOG` ne journalise pas les achats
`AIR_BUILD` : les éventuels `C121_BUILD` et stocks VEHS permettent seulement
une preuve partielle des moteurs physiques, pas toutes les transactions.

**Incident de lancement corrigé sans partie démarrée :** C66 refuse une
politique expérimentale déclarant explicitement `v249_statue=2` et
`eb2_new_station_fallback=0` quand ils correspondent aux défauts du témoin
et ne sont donc pas de véritables interventions. Les lanceurs 5×5 et 40×5
omettent maintenant ces réglages lorsqu'ils valent les défauts, tout en
gardant EB14/ESTIM et les non-défauts explicitement. Le bundle de gel
incomplet créé par cette première tentative a été vérifié isolément puis
supprimé ; la source du scénario est restée intacte. Le premier banc 5×5
safe a commencé à 06:09, sous le Docker unique, **sans verdict encore**.

### Résultats nouveaux 5×5 et nouveaux leviers à 06:23

Les deux premières configurations **safe** (11 préparées) ont été
intégralement mesurées : cinq graines appariées, dix jeux sains, `probes=2`,
OFF zéro discordance historique sur les champs comparés :

| Source expérimentale | Ratio moyennes à 01/12/1974 | Opex £/an | AAA £/an | Comparateur 5×5 concurrent |
|---|---:|---:|---:|---:|
| safe AIR2,00/RAIL1,50/w5/plat/load25 | **84,6119 %** | 2 370 570 | 2 801 699 | 93,2039 % |
| safe AIR2,00/RAIL0,75/w15/incliné | **80,5254 %** | 2 510 662 | 3 117 852 | 90,2268 % |

Les sources safe placent les coefficients avant toute décision ESTIM et ne
font **aucun** raccourci `C121_GE` sous ESTIM ; les sources concurrentes
utilisent encore le shortcut sous ESTIM. Les effets propres du shortcut,
de l'ordonnancement de scan et de la dérive d'exécution ne sont pas
entièrement séparés ; la baisse de ratio n'est **pas** une preuve isolée
de causalité. Le volume d'opcodes observés est partiel (panneaux), pas
le coût CPU global : dans le scénario AIR2/RAIL1,5, 47,16 millions
d'opcodes partiels dans la version concurrente contre 33,80 millions
dans safe, avec moins d'aéroports (34,2 → 32,0) et d'avions (54,8 → 51,6)
dans safe, indiquant un changement substantiel de réseau réalisé.

**Prototype moteur et flotte initiale :** `estim31_motor_joint_prepare_20261030.py`
génère trois copies opt-in, sans nouveau coefficient numérique et avec
OFF byte-identique. Au lieu d'élire un moteur sur la seule économie N=1
puis de calculer N=1/N=2 pour l'unique gagnant, chaque moteur recevable
est évalué par `OpexC121WinnerEconomics` N=1/N=2 fusionné et le meilleur
score combiné moteur+flotte gagne, sans `C121_GE` ni arrêt `upperScore`.
Premier duel 5×5 AIR2/RAIL1,5/w5/plat/load25 : **87,2846 %**
(Opex **2 460 926 £/an** / AAA **2 819 426 £/an**), soit +2,67 points
sur safe de paramètres correspondants ; **22 divergences OFF** dans ce
nouveau replay : résultats exploratoires, pas qualifiés à 40×5.
Le calendrier de calcul N=1/N=2, la divergence OFF et l'impact des
deux différences de source imposent de nouvelles validations.

**Prototype V161 + V252 marginal** : trois copies séparées
`results/estim31_v161_safe20261030` reçoivent un changement opt-in
`ESTIM_UNIFIE & 1` qui supprime seulement sous ESTIM le veto V252 de
mutation de moteur avant calcul d'une marge V161 *pour le même moteur
encore vivant*, puis force ce même moteur lors de l'achat et le revalide.
Le chemin des remplacements suite à crash reste intact ; seul l'achat
de renfort revalidé utilise le `forcedEngine`. Aucun chiffre économique
n'est encore disponible ; les contrats structurels passent. Cela
vise précisément l'interaction entre choix initial des moteurs,
capital de renfort et modèle AIR appris.

**Audit du vivier RAIL 1970** : la garde C121 empêche les constructions
RAIL avant 1971 ; EB14=3 publie des offres RAIL après un premier chantier
AIR par tranches PO01C toutes les 64 ticks, avec 40k opcodes visés par
tranche. Les appels PO01C précèdent certaines tâches AIR et peuvent
modifier le calendrier des investissements. Un déplacement aveugle de
PO01C en fin de tour pourrait au contraire affamer tout le vivier RAIL
car C78 consomme déjà l'essentiel du budget ; recommander un diagnostic
de marge réelle avant de changer la politique. Une reprise de prix des
offres RAIL 1970 devenues vieilles en 1971 reste à qualifier.

**Mesure de caisse réelle non perturbatrice** : le décodeur
`estim31_real_accounts_from_saves_20261030.py` exploite la comptabilité
`PLYR.yearly_expenses` des `.sav` OpenTTD (3 exercices × 13 postes).
Indices 0 construction tous modes, 1 achats de véhicules moins ventes,
2–5 frais opérationnels par mode, 7–10 recettes par mode, 11 intérêts,
12 autres dont actions municipales. Signes : charges positives,
recettes et produits de cession négatifs. Le cumul courant se décale
au premier checkpoint de février (en janvier, encore ancien exercice).
Les différences entre cumuls de deux `.sav` fournissent les **postes nets
réellement inscrits** pour la période, sans appels ni opcodes IA nouveaux.
Cela ne permet **pas** les achats bruts, les coûts de construction AIR
contre RAIL, le coût isolé des statues ni le remplacement par avion.
Le décodeur a été testé sur une vraie save 1970-07-01 et sur deux tests
de contrat du rollover et des signes ; l'archive native `--retain-savegames`
sera utilisée au 40×5 (environ 4 800 sauvegardes, coût disque notable).
La copie des sauvegardes post-processus peut changer l'ordonnancement des
autres workers, donc n'est pas une preuve forte de non-perturbation du duel
à 8 workers ; provenance et OFF du même duel restent obligatoires.

**40×5 historique d'arbitrage en cours à 06:20**, sous le seul Docker,
copie isolée `results/estim31_oldge_best_40x5_20261030` de la meilleure
grille concurrente. Il réutilise ses paramètres exacts et l'image figée,
avec un nouveau nom de campagne et `--retain-savegames`. Sa source
`air_economics_c121.nut` contient des fonctions FullScan ajoutées à la
fin et son `C121_GE` ESTIM n'est pas démontré exact ; même si son ratio
est supérieur à 95 %, il reste **comparateur diagnostique** tant que
cette réserve technique n'est pas résolue. Aucune mesure 40×5 nouvelle
n'est anticipée avant publication d'un vrai résumé final complet.

### Diagnostic 40×5 terminé à 06:35 : meilleure ancienne grille

Le duel `results/estim31_oldge_best_40x5_20261030` est **terminé** sur
40 graines, 80/80 jeux sains, source gelée, 8 workers, `probes=2`,
1970–1974, 256², avec 4 800 sauvegardes archivées et le Docker libéré.
Le ratio de moyennes 01/12/1974 est **92,785063 %**, OpexAI
**2 614 480,750 £/an**, AAAHogEx-115 **2 817 781,950 £/an**, écart
apparié −203 301,200 £/an. Bootstrap descriptif du ratio
**[87,7087 % ; 98,1759 %]** ; 19/40 graines profitables face à AAA.
Le OFF **de ce duel** atteint 96,093121 %, contre la référence OFF plus
ancienne 95,156346 %, et présente **358 écarts / 2 800** comparaisons
de champs annuels, donc sa trajectoire n'est pas strictement reproductible.
Le ratio variante dépasse le meilleur ESTIM31 historiquement qualifié
90,87889 % de +1,90617 point, mais **ne dépasse pas l'OFF historique**.
La source conserve `C121_GE` sous ESTIM sans démonstration d'exhaustivité
par projet : ce résultat est **un diagnostic économique, pas une
qualification technique sans réserve**.

Stocks et couverture fin 1974, moyennes Opex : trésorerie 1 440 776 £,
53,25 avions, 26,325 trains, 33,025 aéroports et 32,425 villes avec
aéroport. `observed_opcodes_total` 48 205 376, **partiel**.
La lecture physique `CITY.statues` sur les saves finales (80/80) donne
21,375 villes ayant une statue Opex dans la variante contre 5,525 dans
son propre OFF ; AAAHogEx possède 15,625 puis 16,375 villes avec statue
respectivement. Ces nombres constatent des états physiques, pas les
coûts ou tentatives bruts d'actions municipales.

Les postes de dépenses réellement comptabilisés, les acquisitions 223/228
visibles entre sauvegardes, les échecs de construction et les rollbacks
restent à compléter ou à limiter explicitement si les archives ne les
contiennent pas. Ne pas attribuer le différentiel de profit aux statues
sans les autres contre-factuels : les moteurs, villes, hubs, AIR, RAIL et
ordonnancements changent également.

À ce stade, **19 tests ciblés passent**, ainsi que sept analyseurs de
syntaxe PowerShell. Les essais 40×5 safe, motorjoint, railnorm et V161,
les replays huit workers, les acquisitions brutes 223/228, les nouveaux
Save/Load de V161, le relevé précis des rollbacks et la batterie générale
restent à exécuter si l'exposition et la fenêtre Docker le permettent.

### Reprise des 5×5 supplémentaires (07:16–07:25)

Une file supplémentaire de **neuf** duels 5×5 s'est achevée à 07:15, sans
Docker en doublon, notamment la variante `v161` à AIR2,00/RAIL0,75/poids15 :
**95,32751 %** (Opex 2 907 214, AAA 3 049 712 £/an), cinq paires saines,
contre **80,52539 %** (Opex 2 510 662, AAA 3 117 852 £/an) pour son parent
`safe` et **90,93142 %** (Opex 2 751 481, AAA 3 025 886 £/an) pour
`motorcap` N=1/N=2 à flotte physiquement admissible. Le second V161
AIR2/RAIL1,5/poids5/plat/load25 atteint **90,9765 %** (Opex 2 755 066,
AAA 3 028 326), contre 84,6119 % pour son parent safe. Les 5×5 ne
sont **pas** des validations 40×5 ni des preuves causales isolées ; leur
variation d'AAAHogEx entre duels et la dérive OFF sont documentées dans
`docs/estim31_followup_screen_summary_20261030.json`. Sur les duels 5×5,
V161 AIR2/RAIL0,75 présente 240 écarts OFF/350 inter-campagnes et
`motorcap` 22 ; en revanche, les sources OFF restent protégées par l'opt-in.

À l'examen des trois fichiers V161, l'intervention n'affecte sous ESTIM
que l'achat de renfort *du même moteur vivant*, contrôle son moteur/son prix
juste avant débit, conserve le chemin de crash, et n'ajoute aucune constante
produit. `OpexC121InitialEngineUpperScore` ne retourne `null` que sur des
préconditions de marché/physique (prix, capacité, moteur/rotation ou recette
invalide), non parce que le score supérieur serait plus bas qu'un gagnant.
L'ancien `C121_GE` peut en revanche dispenser d'examiner les autres moteurs
et n'est **pas** techniquement qualifié sous ESTIM.

**Interaction nouvelle préparée, non jouée au moment de cette note :**
`sweeps/estim31_v161_motorcap_prepare_20261030.py` crée deux bundles
write-once `results/estim31_v161_motorcap20261030/`, croisant les quatre
fichiers opt-in disjoints de V161 et du N1/N2 corrigé. Teste la source
parente identique, le jeu des fichiers modifiés exactement égal à leur union,
les deux fonctions C121 historiques inchangées, les moteurs révalidés, et
l'absence de `break` par borne non prouvée. Deux tests dédiés et 13 ciblés
existants sont verts, syntaxe PowerShell du lanceur dédiée validée. Ne
promouvoir un croisement en 40×5 qu'après un vrai 5×5 sain du même bundle.

**Autre duel en cours au contrôle :** l'agent concurrent a lancé un 40×5
`grid31_a200_r075_w15_slope_40x5_20261030`, source antérieure avec GE,
dans l'unique Docker. Ne pas interrompre, ne pas en extrapoler le résultat,
ni le mélanger avec les nouveaux bundles `safe` ou `v161`.

**Dépenses constatées via 4 800 saves du vieux GE 40×5 :** au 01/12/1974,
les écritures 1974 YTD de sa variante Opex sont 73 682,7 £ de construction
globale, 367 928,1 £ d'achats de véhicules nets des ventes et
1 301 181,6 £ du poste divers dont actions municipales, contre
124 655,6 £, 775 972,3 £ et 267 437,5 £ dans son témoin OFF, respectivement.
Le poste « autres » croît de **1 033 744 £** par graine en moyenne et mérite
une autopsie, sans attribuer tout ce montant aux statues. Les compteurs
physiques mensuels de moteurs 223/228 sont des **minima d'entrées observées**,
non un journal exhaustif des achats ; aucune ventilation AIR/RAIL du poste
construction ni un chiffre de rollback certain n'en découle.

### Croisements V161 complémentaires et second 40×5 concurrent

Le 40×5 de l'autre agent `grid31_a200_r075_w15_slope_40x5_20261030`
s'est finalement terminé : 80 parties produites, **79 `complete` et une
`stagnation_suspect`** (Opex, graine 802204, horizon présent, activité
`declining_without_expansion`). Ratio descriptif des moyennes **94,460621 %**
(Opex **2 692 185,575 £/an**, AAA **2 850 061,275 £/an**), ratio du témoin
OFF de ce duel **96,003859 %**, 360 divergences OFF historiques sur 2 800.
Le statut malsain et le shortcut GE sans preuve excluent cette campagne du
classement technique final, malgré son ratio plus haut que 92,7851 %.

La source `results/estim31_v161_policy20261030/` contient quatre copies
**strictement identiques octet pour octet à la variante V161 AIR2/RAIL0,75
existante**, mais avec réglages appariés : `statue0`, `EB14=2`, `load25`,
et `statue0×EB14=2`. Elles sont opt-in, sans nouvelle constante ni défaut
public. Leur objectif est de séparer la compétition de capital AIR/RAIL,
la dépense municipale V249 et la disponibilité des renforts.

Deux autres copies `results/estim31_no_upper20261030/` examinent
l'élimination du seul **calcul** de la borne de tri C121 dans les deux scans
ESTIM : les candidats éligibles sont alors gardés en ordre catalogue,
chacun évalué, et le départage final par score/profit/ID est inchangé.
Le raccourci GE reste désactivé sous ESTIM et les deux scans historiques
OFF byte-identiques. Cette variante ne prétend pas encore gagner des opcodes
ni du profit : comparer d'abord les vrais 5×5, puis les profits 40×5
des variantes techniquement saines. Les tests ciblés des copies et de
leurs provenance/neutralité de source passent.

À partir de 07:33, une qualification **40×5 de V161 AIR2/RAIL0,75/poids15**
(source `estim31_v161_safe20261030/mix_a200_r075_w15_slope`, SHA
`15078ee31b595f31c9deb054de58cd88edeb72ed9e1eafc9b03463535a28f879`)
a commencé dans l'unique Docker, 8 workers, 256², `probes=2`, autosaves
conservées. **Ne pas publier de verdict avant présence du résumé final,
des 80 statuts et des snapshots annuels des deux compagnies.**

### Qualification V161 40×5 terminée à 07:51 : meilleur signal

`estim31v161_mix_a200_r075_w15_slope_40x5_20261030` est **réellement achevé** :
40 graines communes, 80/80 parties `game_ok=true` / `game_status=complete`,
400 checkpoints annuels `reference` et 400 `variant`, provenance source
`15078ee31b595f31c9deb054de58cd88edeb72ed9e1eafc9b03463535a28f879`,
Docker `sha256:f4b2b9b3...`, 256², années 1970–1974, 8 workers,
`probes=2` et saves mensuelles conservées. Contrôle direct et analyseur
indépendant concordants.

| Au 01/12/1974 | OFF propre au duel | V161 (ESTIM31, EB14=3, AIR=2,00, RAIL=0,75, poids=15, profil incliné, V249=2, EB2=0, load=0) |
|---|---:|---:|
| Profit Opex moyen 40 graines (£/an) | 2 840 621,600 | **2 946 867,750** |
| Profit AAA moyen 40 graines (£/an) | 2 909 840,000 | **2 839 022,725** |
| Ratio des deux moyennes | **97,621230 %** | **103,798667 %** |
| Différence de profits Opex−AAA (£/an) | −69 218,400 | **+107 845,025** |

V161 gagne 22/40 duels face à AAA ; intervalle bootstrap descriptif du
ratio **[97,76056 %, 110,28337 %]**, **aucun veto économique** sur cet
intervalle ni sur Wilcoxon/valeur. Le gain de ratio contre l'ancien
ESTIM31 qualifié (90,87889 %) est **+12,91978 points**, contre OFF
historique (95,15635 %) **+8,64232 points** ; sources et tirages de ces
références diffèrent et ne doivent pas constituer un contre-factuel exact.

Le tableau final imprimé par le runner affiche **le témoin OFF** de la
campagne (2,84062/2,90984 M£), non la variante : ne pas confondre ces
résultats avec les 2,94687/2,83902 M£ lus dans les lignes portant
`duel_policy_id=estim31v161_mix_a200_r075_w15_slope`. Le verdict
`fail_primary` au seuil ancien de 4 % n'est pas un critère de cette mission.

Fin 1974, Opex V161 compte en moyenne **77,975 avions, 24,250 trains,
33,325 aéroports et 32,725 villes avec aéroport**, trésorerie
**1 144 314,80 £** ; contre OFF du même duel **65,900 avions, 24,175 trains,
34,175 aéroports, 33,450 villes et 2 405 229,475 £**. Les moteurs 223
et 228 sont observés en **stocks physiques** finaux de 2 040/408 au
total sur 40 V161, contre 889/440 OFF, **pas des achats bruts**.
`observed_opcodes_total` = 48,38 M contre 51,10 M, indicateur partiel,
`observed_opcode_complete_cpu=false`. Il existe **1 663 discordances
OFF inter-campagnes / 2 800 champs** ; ce fait appelle la prudence sur
la reproductibilité exacte, mais n'est pas imputable automatiquement à un
bug de source OFF : un replay du même code à un worker avait déjà divergé.

La nouvelle source n'a ni `C121_GE` actif sous ESTIM ni élagage par score
supérieur non prouvé, et ses décisions de renforcement revalident le moteur
et les marges juste avant l'achat. La validation Save/Load **spécifique à
V161** et le relevé des écritures PLYR de cette campagne sont les derniers
contrôles fonctionnels nécessaires avant de figer le classement définitif.
La file des huit autres croisements 5×5 a débuté à 07:52 dans le Docker
libéré ; aucune conclusion anticipée sur leur rang 40×5.

**Exploration élargie des coefficients AIR/RAIL initiaux :** quatre copies
write-once `estim31_v161_coeff20261030` réemploient exactement le modèle
V161 et ne modifient que les trois anciennes affectations de niveau et poids
`ESTIM_K_R_PRIOR` à l'initialisation : AIR2,00/RAIL0,50/poids15,
AIR2,25/RAIL0,75/poids15, AIR2,25/RAIL0,50/poids5 et
AIR2,50/RAIL0,75/poids15. Les autres sources et le OFF sont byte-identiques ;
aucun résultat économique n'est disponible au moment de la préparation,
tests de séparation positifs. Ces tuples visent à savoir si V161 change
l'optimum de coefficient et à isoler une éventuelle synergie AIR/RAIL.

### Huit croisements V161 : tous les 5×5 terminés à 08:17

Les huit campagnes ont chacune 10/10 jeux complets et sains, cinq graines
appariées. Les ratios sont calculés avec les deux profits du même duel,
jamais avec un dénominateur AAA emprunté à une autre campagne.

| Variation | Ratio 5×5 | Opex (£/an) | AAA (£/an) |
|---|---:|---:|---:|
| V161 × N=1/N=2, plafond physique | **103,218655 %** | 2 979 404 | 2 886 498 |
| V249=0 et EB14=2 | 98,408337 % | 2 813 504 | 2 859 010 |
| N=1/N=2 et suppression du calcul de borne C121 | 98,030577 % | 2 985 054 | 3 045 024 |
| EB14=2 | 96,812794 % | 2 793 641 | 2 885 612 |
| Sans calcul de borne, N=1 historique | 95,706230 % | 2 800 010 | 2 925 630 |
| V249=0 | 95,392413 % | 2 832 245 | 2 969 046 |
| Garde AIR load25 | 92,749293 % | 2 747 514 | 2 962 302 |
| N=1/N=2, AIR2/RAIL1,50/poids5/plat/load25 | 91,988213 % | 2 804 700 | 3 048 978 |

Ces 5×5 sont exploratoires et leurs dénominateurs AAA varient avec
l'exécution ; ils ne sont pas une preuve d'effet causal ou un classement
40×5. Le croisement V161 × N=1/N=2 est le premier candidat à qualifier
sur les mêmes 40 graines. Quatre variantes AIR/RAIL initial ont commencé
une nouvelle file séquentielle après la clôture de celle-ci.

**Postes comptables réels PLYR, 1974 YTD arrêté au 01/12**, issus
des 80 dernières sauvegardes vérifiées par SHA, pour V161 gagnant
contre son propre OFF (moyennes £/graine) :

| Catégorie nette | V161 | OFF | Écart V161−OFF |
|---|---:|---:|---:|
| Construction tous modes | 71 169 | 130 171 | −59 002 |
| Achats de véhicules moins ventes tous modes | 953 541 | 784 737 | +168 804 |
| Autres dépenses, dont statues | 1 118 636 | 270 989 | +847 647 |
| Recettes AIR (signe retourné) | 2 552 420 | 2 294 484 | +257 937 |
| Recettes RAIL (signe retourné) | 604 873 | 728 537 | −123 664 |
| Exploitation AIR | 396 846 | 324 862 | +71 984 |

La lecture est non perturbatrice et ne transforme pas les achats nets en
acquisitions brutes de moteurs 223/228, ni le poste Autres en dépenses
prouvées de statues. Fichiers : `docs/estim31_v161_accounts_40x5_final_20261030.json`
et `sweeps/estim31_accounts_final_fast_20261030.py`.

**Pourquoi le rail est vide en 1970 :** le code de cette source, dans
`projects.nut:524-528`, retire explicitement les projets RAIL de la
sélection pendant le premier catalogue AIR. Le préchargement en
arrière-plan EB3 (`po01c_regen.nut:701-716,886-905`) n'autorise pas
leur financement. C'est une exclusion de capital voulue, et pas une
preuve que le vivier ne produit aucune opportunité.

### Grille de quatre nouveaux coefficients V161 : 5×5 clôturés (08:30)

| Priors AIR / RAIL / poids (pente RAIL) | Ratio des deux moyennes 5×5 | Opex £/an | AAA £/an | Santé |
|---|---:|---:|---:|---|
| 2,50 / 0,75 / 15 | **103,285240 %** | 2 862 537 | 2 771 487 | 10/10 sains |
| 2,25 / 0,75 / 15 | non classé | — | — | 9/10 complets, seed42 Opex `stagnation_suspect` |
| 2,25 / 0,50 / 5 | 88,950634 % | 2 725 694 | 3 064 277 | 10/10 sains |
| 2,00 / 0,50 / 15 | 86,421994 % | 2 822 557 | 3 266 017 | 10/10 sains |

Ces ratios 5×5 ne sont pas des confirmations 40×5 ; le dénominateur
AAAHogEx doit être conservé propre à chaque duel, les exécutions
historiquement divergent parfois malgré une source identique. Le
coefficient AIR2,50/RAIL0,75 demeure un second candidat à qualifier.
La campagne **V161×choix moteur C121 N1/N2** a commencé son vrai 40×5
à 08:30, 8 workers et 10 CPU/8 GiB dans le seul Docker, source
`183187e6b60f442edf3f0ea7eaa556cfccb4729aed185f1ddf12298e242711c9`.
À l'heure de cette note elle est encore en cours, aucun ratio 40×5
de ce croisement n'est disponible.

**Piste économique complémentaire préparée, pas encore exécutée :**
`estim31_v161_rail1970_20261030/v161_a200_r075_allow_rail1970`
supprime uniquement sous `ESTIM_UNIFIE & 1` le bloc
`projects.nut` qui interdit le financement de tout RAIL durant la
première fenêtre AIR. Les candidats RAIL doivent déjà être présents
et physiquement admissibles, aucun barème ou constante supplémentaire
n'est créé. Test de modification exacte d'un seul fichier et
neutralité source OFF passé. Mesurer exposition (trains dès 1970),
timing/opcodes et ratio 5×5 avant toute promotion économique ; si les
candidats restent absents, documenter une non-exposition sans inventer
un gain.

### Qualification V161 × C121 N=1/N=2 : nouveau record (08:48)

Le duel `estim31vcap_mix_a200_r075_w15_slope_40x5_20261030` est
**achevé** : 40 graines strictement communes, 80/80 jeux complets/sains,
400 checkpoints annuels dans chaque politique, manifeste et source SHA
`183187e6b60f442edf3f0ea7eaa556cfccb4729aed185f1ddf12298e242711c9`
contrôlés. Source opt-in V161 `same-engine` × choix moteur exact
N=1/N=2 avec plafond physique, AIR2,00/RAIL0,75/poids15/profil incliné,
EB14=3, V249=2, EB2=0, charge min AIR=0, `estim_unifie=31`,
`probes=2`, huit workers.

| Profit au 01/12/1974, moyenne de 40 graines | OpexAI | AAAHogEx-115 |
|---|---:|---:|
| V161 × N=1/N=2 (même duel) | **3 006 415,575 £/an** | **2 834 558,325 £/an** |
| V161 précédent, autre duel | 2 946 867,750 £/an | 2 839 022,725 £/an |

**Ratio exact des deux moyennes de la nouvelle campagne : 106,062929 %**,
écart apparié moyen +171 857,250 £/an, **27/40 victoires**, soit
+2,264262 points sur le précédent record V161 **103,798667 %**.
Le témoin OFF **de ce même duel** vaut **98,167743 %**
(Opex 2 861 644 £/an contre AAA 2 915 056 £/an) :
la variante le dépasse de **7,895186 points** sur le critère relatif.
Les comparaisons entre deux campagnes ne constituent pas un appariement
expérimental parfait, car les trajectoires OFF divergent déjà à source
identique ; seul le ratio de profits au sein de chaque duel fonde
le classement.

Au dernier checkpoint Opex, moyenne : **80,250 avions**, **24,475 trains**,
**33,575 aéroports**, **33,075 villes avec aéroport**, trésorerie
**1 106 026,70 £**, emprunts nuls. Stocks physiques cumulés sur
40 jeux : moteur 223 **1 645**, moteur 228 **64**, moteur 220 **858**
(ne pas les appeler des achats). `observed_opcodes_total` atteint
**53,965 M** par jeu en moyenne, observation **incomplète du CPU**.
L'OFF présente 1 695 discordances historiques sur 2 800 champs comparés,
à distinguer d'une modification comportementale OFF.

Le relevé indépendant des **60 stocks mensuels physiques** par graine
(40/40 couvertes, SHA exigés, sans instrumentation en moteur) mesure la somme
des hausses de stock visibles, **minimum de nouvelles apparitions entre deux
snapshots et non nombre réel de transactions**. V161×motorcap :
223 = **1 953**, 228 = **69**, 220 = **1 015** hausses positives sur
40 jeux ; V161 antérieur : 223 = **2 436**, 228 = **449**, 220 = **69**.
Les disparitions mensuelles et les achats/ventes intramensuels empêchent
de transformer ces mouvements en CAPEX brut. Résultats et validation :
`sweeps/estim31_engine_stock_deltas_20261030.py`,
`docs/estim31_v161_motorcap_stock_steps_40x5_20261030.json`,
`docs/estim31_v161_stock_steps_40x5_20261030.json`.

Les journaux `RAIL_ATTEMPT` retenus (couverture
`retained_signs_only`, **pas** journal exhaustif des investissements)
témoignent d'un rail construit surtout en 1971–1972 : motifs `OK`
motorcap, agrégés sur 40 graines, **0 en 1970, 420 en 1971,
448 en 1972, 70 en 1973, 21 en 1974**, contre **0/408/448/79/15**
dans V161 sans motorcap. Il subsiste un effondrement des succès après
1972 et aucune trace de construction RAIL en 1970, cohérente avec
l'interdit de financement déjà identifié. Les motifs `OK` sont
les signatures d'essais conservées, non le nombre total de dépenses
ou un bilan transactionnel exhaustif.

Le décodeur de classement vérifie désormais *exactement* les 40 graines
et les deux compagnies à chacune des cinq dates annuelles pour
chaque politique, les 80 statuts détaillés, le `probes=2` témoin,
`estim_unifie=31` variant, les identités de campagne et
les empreintes SHA des parties, snapshots et manifeste ; des tests
synthétiques couvrent doublon, source mélangée et politique non neutre.
Publication du code de contrôle : `f5c129d5`.

La deuxième qualification prioritaire, **V161 AIR2,50/RAIL0,75/poids15**,
a démarré à **08:48:58** dans le seul Docker (session `19413`,
`estim31vcoef_v161_a250_r075_w15_40x5_20261030`). Son écran 5×5
était sain à 103,285240 % ; aucun ratio 40×5 ne peut être anticipé.

### Qualification AIR2,50 et protocole des dix ans

La campagne V161 AIR2,50/RAIL0,75/poids15 est terminée : **80/80 parties
saines**, SHA source `10d21056814b32f8672db28c7d6016538904ae335e1fa7c22bef0dfbd00527ec`,
ratio des moyennes **105,171758 %** (Opex **2 939 119,125 £/an**,
AAA **2 794 589,700 £/an**) : deuxième rang, derrière le croisement
V161×motorcap à **106,062929 %**, devant V161 AIR2 initial à
**103,798667 %**. Comptabilité PLYR réellement inscrite à la save
du 1er décembre 1974 contrôlée 80/80 : dans le croisement motorcap,
Opex 1974 YTD construction tous modes **73 263,075 £**, achats véhicules
nets **974 756,875 £**, autres **1 160 717,875 £**, recettes AIR
**2 629 958,275 £**, RAIL **627 705,025 £**. Pour V161 AIR2,50,
respectivement **92 332,825 £**, **996 126,275 £**,
**1 083 520,375 £**, **2 560 617,2 £** et **621 223,175 £**.
Il est interdit de convertir ces postes nets et tous modes en achats
bruts de moteurs, dépenses par infrastructure ou facture des statues.

**Nouvelle instruction utilisateur** : au terme du classement sain des
40×5, figer **les trois meilleures variantes** et exécuter **trois duels
20 graines × 10 ans, 1970–1979**, sur les vingt graines canoniques
communes, huit workers, un seul Docker, `probes=2` et les bundles
source gelés. Classer exclusivement par
`100 × mean_20(profit_year Opex au 1979-12-01) /
mean_20(profit_year AAAHogEx au 1979-12-01)`,
avec chaque dénominateur issu du duel correspondant. Ne pas appliquer
de veto valeur/Wilcoxon/IC95/ancien `gain_short`; exiger 40/40 parties
saines, 20 graines appariées, dix snapshots annuels complets et
empreintes de source/manifeste valides. **La meilleure à dix ans deviendra
le nouveau défaut** après contrôles techniques et Save/Load. C'est une
autorisation explicite de promotion qui modifie la règle antérieure
« toutes variantes à défaut 0 » pour la seule configuration gagnante.
Ne pas altérer le `master` sale ni le travail concurrent : intégration
dans une branche dédiée, puis publication contrôlée.

Outils préparés :
`sweeps/estim31_top3_20x10_20261030.py` (figer le top 3 et
vérifier toutes les séries 20×10 avant de choisir) et
`sweeps/run_estim31_finalist_20x10_20261030.ps1`
(sélection figée par rang, exclusivité Docker, budgets identiques).
**Aucune qualification décennale n'est présumée terminée.**

L'essai exploratoire RAIL finançable en 1970 a fini 5×5 sain,
**97,296780 %** de ratio des deux profits, contre **99,056010 %**
pour son témoin propre ; **aucun train construit en 1970** sur
les cinq graines. Non exposé au résultat attendu, sans promotion 40×5.

**Clôture des deux écrans capcombo 5×5** : motorcap×AIR2,50 donne
**102,799555 %** (Opex 3 006 218,8 £, AAA 2 924 350 £) et
motorcap×V249=0/EB14=2 donne **103,590107 %**
(Opex 2 958 670 £, AAA 2 856 131,8 £), dix parties saines
chacun. Ces résultats n'ont que cinq graines et ne sont pas substituables
aux trois qualifications 40×5 déjà achevées ; aucune promotion sur
cette seule base.

**Trio figé pour 20×10** dans
`docs/estim31_top3_frozen_20261030.json`, ordre de ratios 40×5 :
1. `v161cap/mix_a200_r075_w15_slope` : **106,062929 %**,
   source `183187e6b60f...` ;
2. `v161coeff/v161_a250_r075_w15` : **105,171758 %**,
   source `10d21056814b...` ;
3. `v161/mix_a200_r075_w15_slope` : **103,798667 %**,
   source `15078ee31b595...`.

Premier banc décennal lancé le **30/10 à 09:47:01**, top1 V161×motorcap,
20 graines × 10 ans, huit workers, uniquement le Docker disponible.
Il ne faut pas déduire son résultat 1979 des cinq premières années.

### Premier 20×10 terminé et sain (10:13)

`estim31ten_estim31vcap_mix_a200_r075_w15_slope_20x10_20261030`
est **réellement terminé sur 40/40 jeux sains**, vingt graines appariées,
dix ans (1970–1979), source gelée
`183187e6b60f442edf3f0ea7eaa556cfccb4729aed185f1ddf12298e242711c9`,
`probes=2`, huit workers. Le lecteur exige les 400 checkpoints annuels
par politique et la cohérence SHA du manifeste, des jeux et des snapshots.

**Variante V161×motorcap au 01/12/1979** :
Opex **4 290 978,400 £/an**, AAAHogEx **6 582 408,650 £/an**,
ratio des moyennes **65,188575 %**, écart apparié
**−2 291 430,250 £/an**, zéro victoire sur vingt graines.
Témoin OFF du *même duel* : Opex **4 038 345,350 £/an**,
AAA **6 892 616,350 £/an**, ratio **58,589440 %**.
Cette comparaison interne est valide mais ne suffit **pas** à choisir
le nouveau défaut avant les deux autres 20×10.

Fin 1979, Opex conserve **16 072 476,05 £** de caisse moyenne,
**84,95 avions**, **27,95 trains**, **34,90 aéroports**,
**34,10 villes avec aéroport**, emprunt nul.
Le fort matelas de trésorerie suggère une capacité d'investissement
non mobilisée, pas un chiffre de dépenses prouvé : les comptes PLYR
de fin de campagne seront lus sur les dernières sauvegardes.
`observed_opcode_complete_cpu=false` : ne pas présenter les
compteurs comme CPU exhaustif.

La **deuxième** qualification 20×10, V161 AIR2,50/RAIL0,75,
a démarré automatiquement le **30/10 à 10:13:14**, sous l'unique Docker.
La troisième reste en file séquentielle, aucun défaut modifié.
