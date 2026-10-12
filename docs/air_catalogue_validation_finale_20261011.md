# Catalogue AIR — validation finale des correctifs isolés (11/10/2026)

**Addendum du 12/10/2026 :** l'utilisateur **valide aussi AC06 v2**,
en acceptant expressément son résidu +32 opcodes par paire en 1970–1971.
AC06 v2 est maintenant intégré localement avec AC04-B et AC05, flag à 1
par défaut, rollback 0. Les refus AC06 v2 mentionnés ci-dessous
reproduisent **l'état historique du 11/10**, antérieur à la nouvelle
autorisation. AC06 v1/v3 et AC04-A restent rejetés. Voir
[l'adoption du 12/10](ac06_v2_adoption_20261012.md).

## Contrat et périmètre, avant les mesures complémentaires

Décision utilisateur postérieure à V102 : **aucun gain économique ni opcode
n'est requis** ; rejeter seulement une dégradation démontrée dans l'un des
deux domaines. Un intervalle franchissant zéro ne constitue **pas** une
preuve de neutralité ni de perte. Les gains V102 A40×3 ne s'appliquent pas.
Les huit audits AC-01 à AC-08 sont clos ; **ne pas les recommencer**.
V141 et AIR0310 restent aux défauts adoptés, V142/V143 restent rejetés.

Staging indépendant : `results/ac_fixes_worktree_20261011` (base
`436e1b5`), quatre flags à 0 hors bras testé :
`ac04_hub_route_fix`, `ac04_extra_site_dedup`,
`ac05_skip_unused_hub_income`, `ac06_c76_snapshot_ack`.
Les modifications ne vont pas dans `master` avant une décision isolée,
puis test d'interaction. Aucun commit/push.

## Données existantes, conservées sans répétition

- **AC04-A** : A40×3 `ac04a_v102a_40x3_20261011_r2`, delta
  `profit_year` **+6 354 £/an**, IC95 environ [−33 552 ; +46 341].
  H5 partiel : **+3,885 M d'opcodes** (+21,55 %), IC95
  [+1,579 ; +6,346] M, mais seuls **1/40** appariements ont le même
  nombre global d'échantillons ; contribution principale
  `rail_attempt` +2,669 M et `selection` +0,767 M. Il faut mesurer le
  travail global de boucle, pas attribuer ce total à la découverte AIR.
  Décomposition appariée : **24/40** graines ont un nombre d'essais
  `rail_attempt` identique et leur delta moyen de ce poste n'est que
  **−2 724 opcodes** ; les **16/40** autres ont **+6,676 M opcodes** de
  delta de poste en moyenne. L'essentiel du signal provient donc d'un
  changement du nombre d'essais, **pas** d'un coût structurel par tentative
  démontré. Cela reste une hausse partielle réelle, pas encore l'usage global.
- **AC04-B** : A40×3 `ac04b_v102a_40x3_20261011`, B20×10
  `ac04b_nonerosion_20x10_20261011` ; B `profit_year`
  **+66 123 £/an**, IC95 [−5 857 ; +136 783], valeur +2,11 %.
  H5 B +0,984 M, IC95 [−6,130 ; +8,322] M, **1/20**
  dénominateur total d'échantillons apparié. Opcode global inconnu.
- **AC06** : A40×3 `ac06_v102a_40x3_20261011`, B20×10
  `ac06_nonerosion_20x10_20261011` ; B `profit_year`
  **−78 982 £/an**, IC95 [−192 524 ; +25 994], valeur −1,40 % :
  tendance défavorable, **pas** perte démontrée. H5 insuffisant.
  Décomposition annuelle sans nouveau banc :
  `sweeps/analyse_ac06_annual.py` lit les checkpoints préexistants de
  `ac06_nonerosion_20x10_20261011.jsonl` et enregistre
  `results/ac06_nonerosion_20x10_20261011_annual.json`.
  Moyenne ON−OFF : −11 138 £/an au checkpoint 1972, −51 060 £/an
  en 1975, −32 750 £/an en 1978 (pour 20/20 paires par an),
  puis −78 982 £/an en métrique terminale 1979. Les checkpoints
  annuels comparent strictement les dates de février suivant l'année
  évaluée ; la fin de partie 1979 vient du résumé officiel et n'est pas
  présentée comme un checkpoint fictif de février 1980.
- **AC05** : smoke `ac05_smoke42_1y_20261011` déjà acquis ;
  B20×10 `ac05_nonerosion_20x10_20261011` **terminé**
  (40/40 parties saines, même bundle figé et 20 graines canoniques).
  Profit ON−OFF **+29 990 £/an**, IC95 [−149 152 ; +192 701],
  13V/7D, valeur +1,48 %. Porte économique `non_erosion=pass`
  au sens absence de dégradation démontrée, **pas** équivalence prouvée.
  H5 partiel +6,81 M op (+5,46 %) IC95 franchissant zéro et
  **0/20 nombres d'échantillons identiques**, donc aucun verdict global
  fondé sur H5.

Les chiffres H5 couvrent une **fraction** du CPU IA (signes IG/OB/RB/OA),
pas toutes ses tâches ; nombres de construction et d'échantillons varient
avec les trajectoires.

### AC04-A, première mesure de boucle VM appariée

La campagne gelée `ac04a_opcode_loop_10x3_20261011` utilise
les dix graines ci-dessous, OFF/ON distincts, sondes identiques,
20/20 parties saines. `LOOP_OPS` **ne clôture que 1970 et 1971**
pour cet horizon de 3 ans ; 1972 a ses événements `AIR_LIGHT`, mais
pas d'agrégat annuel de boucle à cause du flush sur changement
d'année. Sur **1970+1971, les dix paires** :
travail total de la boucle ON−OFF **+305 616 opcodes** en moyenne,
ratio **+0,244 %**, IC95 bootstrap apparié **[+68 672 ; +621 115]**,
6 hausses/3 baisses/1 égalité. L'augmentation globale est **étayée sur
cette fenêtre instrumentée**, pas une extrapolation à 1972 ou
à une partie de 10 ans. La ventilation moyenne sur 2 ans :
`catalog_continuation` +408 090,
`orchestrator` −110 386 ; dans AIR,
`hub_site` −156 888 et `hub_hub` −103 891
malgré la hausse globale. Cette décomposition explique pourquoi
H5 rail et la seule phase AIR ne suffisaient pas au verdict.

### Diagnostic VM global 10×4 achevé : trois années clôturées

Quatre duels `*_opcode_loop_10x4_20261011`, mêmes dix graines et
bundle SHA256 `99e262af68bdd980643f905b0b4a9307407be43427dd2c930f73be7253078e4c`,
20/20 jeux sains **par cas**, tous les autres flags AC désactivés.
`LOOP_OPS` complet sur 1970–1972 ; 1973 reste censuré par le flush annuel.
Sommes exécutées ON−OFF sur ces trois années, moyenne par paire :

| Correctif | Delta de la boucle | Ratio sur référence | IC95 bootstrap apparié | Signes (+/−/=) |
|---|---:|---:|---|---|
| AC04-A | +305 230 ops | +0,159 % | [−763 776 ; +1 262 934] | 6/4/0 |
| AC04-B | −146 722 ops | −0,076 % | [−409 370 ; +54 178] | 1/3/6 |
| AC05 | −610 645 ops | −0,317 % | [−1 393 949 ; +111 134] | 4/6/0 |
| AC06 | −487 260 ops | −0,253 % | [−2 437 267 ; +823 153] | 9/1/0 |

Attention : AC04-A montrait +305 616 ops, IC95 > 0 sur **1970–1971**
en 10×3, mais le 10×4 étendu à 1972 ne confirme pas une hausse
globalement démontrée ; **conserver les deux observations**. Les phases se
réorganisent fortement : en 10×4 AC04-A, moyenne `orchestrator` +4,55 M,
`catalog_continuation` −3,76 M ; dans AIR `hub_hub` −3,93 M,
`hub_site` −1,37 M. Cela ne prouve ni surcoût intrinsèque du helper ni
absence de hausse induite. AC04-B ne diverge qu'en 1972 et ses six paires
sans changement ne justifient pas de l'appeler équivalent partout.

**Contradiction économique AC05 à résoudre :** le terminal 10×4 affiche
−64 392 £/an, IC95 [−128 260 ; −5 755], malgré le B20×10
antérieur +29 990 £/an avec intervalle traversant zéro. Il s'agit de
durées et échantillons distincts, pas d'un résultat à sélectionner selon
son signe. Une extension pré-définie avec les trente graines restantes
de `SEEDS_40`, sans répéter les dix premières, est en qualification
séquentielle AC04-A/AC05/AC06 à horizon 4 ans, source/bundle identiques.
`sweeps/analyse_ac_extension40.py` doit agréger les **quarante** paires,
en distinguant profits terminaux 1973 des opcodes clôturés 1970–1972.

**Extension AC04-A terminée (40 paires distinctes, même source) : REJET OPCODE.**
Le holdout de 30 graines ajoute +134 166 £/an de profit (IC95
[+59 349 ; +212 252]), mais ses opcodes globaux moyens sur 1970–1972
augmentent de +561 231 (IC95 traversant zéro). En cumul 10+30 : profit
terminal 1973 **+113 600 £/an**, IC95 **[+55 294 ; +175 042]** ; valeur
**+3,26 %**. Les opcodes globaux 1970–1972 : **+497 231** (+0,258 %),
IC95 [−340 494 ; +1 464 993]. Cependant la fenêtre **1970–1971** sur
les **40 mêmes paires** confirme le signal initial : **+213 974 opcodes**
(**+0,170 %**), IC95 **[+72 713 ; +370 559]**, 25 hausses,
14 baisses et 1 égalité. C'est une **dégradation globale démontrée dans
la fenêtre de début de partie** malgré un gain économique à quatre ans.
La règle utilisateur rejette une régression même sans seuil minimal :
**AC04-A REJETÉ**, pas de portage du correctif dans master, conserver
l'anomalie, l'essai et les preuves. Le nombre de tentatives rail et les
compositions des postes ne permettent pas de prétendre à un coût du seul
helper d'orphan, mais n'effacent pas l'augmentation globale observée.

**Extension AC05 terminée : ACCEPTER en isolé sous le contrat de
non-dégradation, intégration conditionnée à l'interaction.** Les trente
nouvelles graines seules donnent +12 835 £/an de profit (IC95
[−63 895 ; +90 152]) et −996 043 opcodes VM (IC95 franchit zéro).
En cumul 40×4 de graines distinctes, terminal 1973 : profit **−6 472
£/an**, IC95 **[−66 494 ; +54 951]**, valeur −0,578 % sans preuve de
perte ; 1970–1972 : **−899 693 opcodes** (−0,467 %), IC95
**[−1 860 639 ; +39 784]**. La fenêtre 1970–1971 ne montre pas non
plus de hausse démontrée. Le B20×10 préexistant reste +29 990 £/an,
IC95 franchissant zéro. Le 10×4 négatif n'est donc pas confirmé par
le holdout ; aucune équivalence statistique stricte n'est prétendue.

**Extension AC06 terminée : REJET opcode pour surcharge répétable.**
Le 30×4 additionnel seul affiche un profit −19 851 £/an, IC95
[−54 788 ; +5 616], sans perte économique démontrée ; sur les 40
graines distinctes, le profit 1973 est **−11 283 £/an**, IC95
**[−39 173 ; +9 427]**, valeur −0,234 %. L'opcode moyen global
1970–1972 vaut **−95 314**, IC95 [−647 421 ; +348 671] : le signe
de la moyenne **ne démontre pas** à lui seul une hausse. Cependant
**34/40** paires ont plus d'opcodes (p exact bilatéral des signes
**8,36×10⁻⁶**), médiane +451. Sur la fenêtre 1970–1971,
**38/40** hausses (p **1,49×10⁻⁹**), médiane **+451 opcodes** et
**25/40** paires exactement +451. Des écarts de trajectoires extrêmes
font traverser zéro à l'IC de la moyenne, mais ne masquent pas la
**surcharge positive systématique de la majorité des parties**, même
en dehors d'une correction C76 effectivement exposée. La règle
utilisateur ne fixe **aucune tolérance de surcoût** : **AC06 REJETÉ**
pour opcode. Le cas logique late-ack reste connu ; les Save/Load OFF/ON
restent sains, mais ne prouvent pas la présence d'un événement tardif en VM.
Ne pas activer AC06 par défaut ni intégrer son code de production.

**Sélection pour le test d'interaction : AC04-B et AC05 uniquement.**
AC04-A et AC06 restent dans le worktree d'essai avec leurs résultats,
sans activation en production ; le cumul B+05 doit être validé séparément
avant le portage minimal sur master.

## Campagnes opcodes additionnelles, pré-enregistrement

Diagnostic **gelé et apparié**, hors porte économique : privilégier
`sweeps/run_c66_reference.py` (`--script-debug`, bundles et manifestes
empreintés). Le collecteur
`sweeps/diag_ac_catalogue_opcode.py` est seulement un repli diagnostique
non gelé. Tester un correctif ON à la fois, autres
flags OFF, paire OFF/ON sur les **10 premières graines canoniques** :
`42 100 7 999 2026 1 17 73 314 512`, horizon **3 ans**,
10 workers/10 CPU au plus, pas de chevauchement Docker.
Sondes symétriques `probe_loop_ops=1,catalog_cost_probe=1`,
`--script-debug` (`-d script=4`). Utiliser techniquement
`gain_short` avec `--required-seeds 10 --required-years 3` et
seuil 0 seulement pour rendre le collecteur compatible : **ignorer
son verdict de gain**, seul le contrat de non-régression utilisateur
prévaut. Extraire les postes disjoints annuels `LOOP_OPS`
(exclure `sleep_left` de l'exécution ; publier sa différence en
contrôle), le coût de chaque phase `AIR_LIGHT`, les appels par phase,
et le mix `orchestrator/catalog_continuation/rail_throughput`.
Analyseur `sweeps/analyse_ac_loop_opcode.py`.

Cette instrumentation est davantage globale que H5 mais compte les ticks
traversés par l'IA et n'est pas un compteur matériel CPU. Les 10 graines
constituent un **diagnostic**, pas une preuve automatique d'équivalence
universelle ; si borne IC95 encore indécidable, conserver la réserve et
ne pas appeler la variante « neutre prouvée ». Un IC95 bootstrap apparié
entièrement positif du travail global, sans explication de couverture,
est un signal d'une régression nécessitant un verdict motivé ; aucune
hausse minimale arbitraire n'est exigée.

## Save/Load et décision

Pour AC06 seul : exécuter `sweeps/save_load_roundtrip.py` sous Docker
sur le code du staging avec le flag ON, puis une référence OFF au même
seed/horizon, en exigeant `LOAD_RECONCILE` après le chargement, aucune
erreur Squirrel, des compagnies viables, et un contrôle des révisions
et du scheduler lors du prochain refresh. La sauvegarde abandonnant la
tranche C78 active, vérifier la **régénération forcée après Load** et
absence d'acquittement tardif ; si impossible à prouver en runtime,
documenter le cas comme résiduel et ne pas feindre une preuve.
**Graine diagnostique retenue : 512**, première divergence économique
annuelle déjà observée dès 1970 dans la B20×10 (sélection causale,
non utilisable pour conclure à la moyenne). Horizon identique
`--years-a 2 --years-b 1` pour OFF et ON ; une nouvelle partie par bras,
suivie d'un rechargement de sa propre sauvegarde intermédiaire.

**Exécution moteur terminée :** `ac06_saveload_off_seed512_2p1_20261011.json`
et `ac06_saveload_on_seed512_2p1_20261011.json`, séquentiellement,
3 CPU/2 Go et même code/seed/horizon. Chacun : 25 sauvegardes phase A,
reprise `000000011.sav` datée 1971-01-01,
13 sauvegardes phase B, statut `OK`, marqueur
`LOAD_RECONCILE` positif, aucun marqueur d'échec moteur, constructions
et véhicules après reprise. Une compagnie humaine fantôme sans activité
apparaît dans les deux cas, artefact connu du banc.
**Limite d'exposition :** la sortie AILog ne publie aucun compteur
spécifique `C76` d'après le rechargement, si ce n'est le selftest
désactivé pour une partie chargée. Ces deux tests **ne prouvent pas**
qu'un événement C76 effectivement tardif a été observé entre
refresh et apply ; les garde-fous sur révisions restent établis par
quatre tests supplémentaires `sweeps/test_ac06_save_load_semantics.py`
et les contrats de code, pas par ce replay de Save/Load.

Chaque étape est autonome, sans enchaîner les quatre flags dans un
unique A/B. Après les verdicts séparés, combiner **seulement** les candidats
retenus et qualifier le cumul. Ne porter dans `master` que le code
justifié et ses tests après contrôle de coexistence avec les travaux
concurrents et `git diff --check`. Ni commit ni push.

## Épreuves d'interaction et optimisation après les verdicts v1

Sur décision utilisateur ultérieure, les **rejets opcode AC04-A/AC06 v1**
doivent être réexaminés à la recherche de redondances et de substituts
réellement moins coûteux (index, `AIList`, filtres natifs, allocations Squirrel).
L'autopsie détaillée est enregistrée dans
[`ac_opcode_optimisation_20261011.md`](ac_opcode_optimisation_20261011.md).
Deux variantes AC04-A v2 (réutilisation de `seenStations`/`hubIndex.routes`)
et AC06 v2 (snapshot des 7 compteurs, sans sérialisation Save/Load profonde)
ont été préparées **uniquement dans le worktree isolé**
`results/ac_opcode_opt_worktree_20261011` ; 19 contrats Python ont passé.
**Pas de qualification VM ou économique v2 à ce stade**, aucune activation
dans master ; préserver intégralement les résultats v1.

**Interaction économique AC04-B+AC05 :** campagne appariée
`ac_combo_ac04b_ac05_20261011_econ_20x10`, 20 graines × 10 ans,
40/40 parties saines. Profit ON−OFF **+59 835 £/an**, IC95 bootstrap
**[−75 536 ; +192 620]**, valeur +66 964 £, IC95
[−459 197 ; +636 675] : absence de dégradation économique démontrée,
mais pas preuve d'équivalence. H5 partiel +9,53 M observés, 0/20
dénominateurs appariés ; **ne pas en faire un verdict global**.
Le contrôle global `ac_combo_ac04b_ac05_20261011_opcode_10x4` doit être
vérifié avant tout portage dans master ; aucun résultat anticipé ici.

**Résultat du cumul VM obtenu :** dix graines × quatre ans, 20/20
parties complètes, source `99e262af68bdd980643f905b0b4a9307407be43427dd2c930f73be7253078e4c`,
sondes OFF/ON symétriques, 1970–1972 clôturées. Travail exécuté
**−230 118 opcodes** en moyenne (−0,1195 %), IC95 bootstrap
**[−897 523 ; +276 929]**, 5 hausses / 5 baisses. Sensibilité :
sur 1970 seulement, −11 688,5 (IC95 [−31 672 ; −517], 0 hausse),
sur 1970–1971 −51 812 (IC95 [−143 124 ; +30 605], 2 hausses).
**Aucune régression opcode du cumul démontrée** sur ces fenêtres ; cela
n'établit pas une équivalence universelle. Le cumul AC04-B+AC05 satisfait
les critères utilisateur séparés économie / opcode et peut être porté
minimalement dans master avec rollback par flags et contrôle Docker de
l'intégration effective. Les alternatives AC04-A/AC06 v2 sont des
expériences indépendantes et n'entrent pas dans ce cumul.

**Validation du portage master terminée :** `master` au HEAD
`daf9486` lors du portage, quatre fichiers de production modifiés
sans écraser les travaux concurrents, deux flags AC04-B/AC05 à 1
par défaut et réversibles à 0 ; AC04-A et AC06 absents du code actif.
**124 contrats ciblés verts**, `git diff --check` vert. Smoke moteur gelé
`ac_master_integrated_smoke_20261011_r2`, graine 42, 1 an,
**2/2 parties saines**, ON vs OFF mêmes métriques : profit annuel
436 329 £, valeur de compagnie 387 799 £, score 180,
16 véhicules / 19 gares ; bundle
`5658e871ed1cffa2450e85cbbe9270e79fcd837f1684a2cf5408577b9632d10c`,
Docker 3 CPU / 2 Go / 2 workers. Il s'agit d'un smoke de
chargement/parité précoce, **pas** d'une répétition de la B20×10
ni d'une preuve de neutralité à dix ans. L'essai de smoke précédent
`ac_master_default_smoke_20261011` a échoué **avant simulation**
car le harnais exige `OpexAI[cle=valeur]` dans la référence ; aucun
résultat moteur de cette tentative n'est interprété.

**Optimisations v2/v3 après mandat complémentaire :** l'index station
et la déduplication au premier parcours AC04-A v2 ne suppriment pas
la régression 1970–1971 : **+307 376 opcodes**, IC95
[+92 855 ; +609 554] sur 10 paires. AC06 v2 supprime la copie profonde
des tables C76 mais conserve **+32 opcodes** sur chacune des dix paires
en 1970–1971. AC06 v3 mutualise les filtrages de couches mais aboutit
à **+191 250 opcodes** en moyenne 1970–1972, IC95 **[+32 ; +573 685]**.
Trois tentatives v2/v3, 103 tests verts ; **toutes non adoptées** à cause
du critère sans tolérance. Les sources et bundles restent dans
`results/ac_opcode_opt_worktree_20261011` ;
[rapport causal](ac_opcode_optimisation_20261011.md).

**Bilan :** AC04-B/AC05 acceptés et intégrés localement ; AC04-A/AC06
rejetés sous leurs formes testées, problèmes documentés ; V141 maintenue,
V142/V143 non réintroduits, aucune modification de score, MAIL15,
flotte, portefeuille ou scheduling. Les phases AIR reprenables ont leurs
fonctions et curseurs indépendants, testés ; elles restent coordonnées
par le même ordonnanceur C78 plutôt que transformées en huit tâches
de file ayant une cadence différente, qui exigerait une autre preuve.
**Aucun commit ni push.**
