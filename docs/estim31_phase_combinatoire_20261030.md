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

Le 40×5 de l'autre agent \x60grid31_a200_r075_w15_slope_40x5_20261030\x60
s'est finalement terminé : 80 parties produites, **79 \x60complete\x60 et une
\x60stagnation_suspect\x60** (Opex, graine 802204, horizon présent, activité
\x60declining_without_expansion\x60). Ratio descriptif des moyennes **94,460621 %**
(Opex **2 692 185,575 £/an**, AAA **2 850 061,275 £/an**), ratio du témoin
OFF de ce duel **96,003859 %**, 360 divergences OFF historiques sur 2 800.
Le statut malsain et le shortcut GE sans preuve excluent cette campagne du
classement technique final, malgré son ratio plus haut que 92,7851 %.

La source \x60results/estim31_v161_policy20261030/\x60 contient quatre copies
**strictement identiques octet pour octet à la variante V161 AIR2/RAIL0,75
existante**, mais avec réglages appariés : \x60statue0\x60, \x60EB14=2\x60, \x60load25\x60,
et \x60statue0×EB14=2\x60. Elles sont opt-in, sans nouvelle constante ni défaut
public. Leur objectif est de séparer la compétition de capital AIR/RAIL,
la dépense municipale V249 et la disponibilité des renforts.

Deux autres copies \x60results/estim31_no_upper20261030/\x60 examinent
l'élimination du seul **calcul** de la borne de tri C121 dans les deux scans
ESTIM : les candidats éligibles sont alors gardés en ordre catalogue,
chacun évalué, et le départage final par score/profit/ID est inchangé.
Le raccourci GE reste désactivé sous ESTIM et les deux scans historiques
OFF byte-identiques. Cette variante ne prétend pas encore gagner des opcodes
ni du profit : comparer d'abord les vrais 5×5, puis les profits 40×5
des variantes techniquement saines. Les tests ciblés des copies et de
leurs provenance/neutralité de source passent.

À partir de 07:33, une qualification **40×5 de V161 AIR2/RAIL0,75/poids15**
(source \x60estim31_v161_safe20261030/mix_a200_r075_w15_slope\x60, SHA
\x6015078ee31b595f31c9deb054de58cd88edeb72ed9e1eafc9b03463535a28f879\x60)
a commencé dans l'unique Docker, 8 workers, 256², \x60probes=2\x60, autosaves
conservées. **Ne pas publier de verdict avant présence du résumé final,
des 80 statuts et des snapshots annuels des deux compagnies.**

### Qualification V161 40×5 terminée à 07:51 : meilleur signal

\x60estim31v161_mix_a200_r075_w15_slope_40x5_20261030\x60 est **réellement achevé** :
40 graines communes, 80/80 parties \x60game_ok=true\x60 / \x60game_status=complete\x60,
400 checkpoints annuels \x60reference\x60 et 400 \x60variant\x60, provenance source
\x6015078ee31b595f31c9deb054de58cd88edeb72ed9e1eafc9b03463535a28f879\x60,
Docker \x60sha256:f4b2b9b3...\x60, 256², années 1970–1974, 8 workers,
\x60probes=2\x60 et saves mensuelles conservées. Contrôle direct et analyseur
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
\x60duel_policy_id=estim31v161_mix_a200_r075_w15_slope\x60. Le verdict
\x60fail_primary\x60 au seuil ancien de 4 % n'est pas un critère de cette mission.

Fin 1974, Opex V161 compte en moyenne **77,975 avions, 24,250 trains,
33,325 aéroports et 32,725 villes avec aéroport**, trésorerie
**1 144 314,80 £** ; contre OFF du même duel **65,900 avions, 24,175 trains,
34,175 aéroports, 33,450 villes et 2 405 229,475 £**. Les moteurs 223
et 228 sont observés en **stocks physiques** finaux de 2 040/408 au
total sur 40 V161, contre 889/440 OFF, **pas des achats bruts**.
\x60observed_opcodes_total\x60 = 48,38 M contre 51,10 M, indicateur partiel,
\x60observed_opcode_complete_cpu=false\x60. Il existe **1 663 discordances
OFF inter-campagnes / 2 800 champs** ; ce fait appelle la prudence sur
la reproductibilité exacte, mais n'est pas imputable automatiquement à un
bug de source OFF : un replay du même code à un worker avait déjà divergé.

La nouvelle source n'a ni \x60C121_GE\x60 actif sous ESTIM ni élagage par score
supérieur non prouvé, et ses décisions de renforcement revalident le moteur
et les marges juste avant l'achat. La validation Save/Load **spécifique à
V161** et le relevé des écritures PLYR de cette campagne sont les derniers
contrôles fonctionnels nécessaires avant de figer le classement définitif.
La file des huit autres croisements 5×5 a débuté à 07:52 dans le Docker
libéré ; aucune conclusion anticipée sur leur rang 40×5.

**Exploration élargie des coefficients AIR/RAIL initiaux :** quatre copies
write-once \x60estim31_v161_coeff20261030\x60 réemploient exactement le modèle
V161 et ne modifient que les trois anciennes affectations de niveau et poids
\x60ESTIM_K_R_PRIOR\x60 à l'initialisation : AIR2,00/RAIL0,50/poids15,
AIR2,25/RAIL0,75/poids15, AIR2,25/RAIL0,50/poids5 et
AIR2,50/RAIL0,75/poids15. Les autres sources et le OFF sont byte-identiques ;
aucun résultat économique n'est disponible au moment de la préparation,
tests de séparation positifs. Ces tuples visent à savoir si V161 change
l'optimum de coefficient et à isoler une éventuelle synergie AIR/RAIL.
