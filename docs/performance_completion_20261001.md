# Performance face à AAAHogEx et compléments de validation — 01/10/2026

## Plan avant exécution

Demande : « teste les performances contre aaahog et finis les points inachevés ».
Périmètre de clôture : reliquats de l'intégration AIR/shadow/R1-R3, pas toute
la liste historique de `taches.md` ni une nouvelle politique économique.

1. Mesure descriptive du défaut courant contre **AAAHogEx-115**, mêmes cartes :
   graines **42, 100, 999, 1234, 5678**, **1970–1975**, fin **1976-02-01**,
   trois workers au maximum, un conteneur 3 CPU / 2 Go / sans swap.
   Sondes supplémentaires OFF ; C115=1 inchangé. Lanceur/collecteur existant
   `diag_cadence_duel`, bras `reference` seul. Aucune édition des sources pendant
   ce banc. Nouvelle mesure demandée explicitement, pas relance sélective.
2. Mesures annoncées avant lecture : ratio annuel Opex/AAA (moyenne des ratios
   et ratio des moyennes séparés), profits propres absolus et écart par graine,
   valeur et véhicules principaux par propriétaire ; santé et couverture complètes.
   Écart moyen/médian, IC95 exploratoire et victoires en 1975. Aucun verdict
   d'adoption ni attribution causale aux quatorze correctifs locaux cumulés.
3. Après le banc : compléter les fixtures Squirrel pures d'amortissement et
   examiner/raccorder les états dirigés R1/R3. Une simulation Python ou un
   garde forcé ne validera pas un achat, un refus API ou un checkpoint moteur.
   Les préconditions absentes resteront explicitement non validées.

Git/gh et `.git` absents : pas de SHA ni publication. Image existante :
`sha256:69d7e57aad5d3036f16655e8af23f36aa9fbb7c82c61ea325192c56b50e48e47`.
Cache `openttd-lab-home`, runtime 15.3 / NoAI 15 / OpenGFX 7.1 / Lab 0.0.75.
Empreintes avant/après et artefacts uniques, sans revendication de gel Git.

Sortie pré-enregistrée :
`results/duel_default_completion_20261001_r1.json`.

## Protocole dirigé R1/VM (avant exécution)

`sweeps/run_mechanism_fixtures.py` copie l'IA et n'édite que cette copie.
Matrice VM : 48 combinaisons C70/C82 × facteurs 0,5/1/1,5 × observé/prédit ×
quantités 1/4 × durées 20/13, plus frontières OFF/net nul/négatif/V92/exclusions.
Les entrées arithmétiques sont synthétiques, les fonctions exécutées sont celles
de production dans NoAI 15, pas une traduction Python.

Pour R1, intercepter une demande **réellement produite de quatre avions**, sans
modifier sa quantité ou les gardes. Préparer la trésorerie réelle avec un GS
(`ChangeBankBalance`, retour publié), puis appeler le sélecteur commun avec ce
candidat seul ; ceci teste le mécanisme, pas sa concurrence économique avec tout
le catalogue. Comparer P+999 puis P+1000 net réserve. Conserver la décision ajustée
et les IDs dans une enveloppe de fixture uniquement dans la copie. Suspendre le
coordinateur avant achat jusqu'à sauvegarde, recharger puis acheter réellement,
suspendre à nouveau, recharger et resoumettre le même snapshot. Enfin, mutation
réelle de flotte par le helper puis refus du snapshot caduc.

Trois phases séquentielles bornées **2/1/1 ans**, graine42, un worker. Les services
existants continuent pendant l'attente ; trésorerie, prix, IDs et ordres sont
revalidés au reload. Choisir la première sauvegarde explicitement marquée dans
l'état `selected` puis `purchased`, jamais une simple date intermédiaire.
Chaque sauvegarde réelle est hachée. Les fixtures altèrent le monde de test :
leurs profits ne sont **jamais** des performances comparables au défaut.
R3 nécessite un protocole distinct ; ces nouvelles fixtures ne le valident pas.

## Mesure du défaut contre AAAHogEx

Cinq parties sur cinq saines, horizon 1976-02-01, sources inchangées, sortie
conteneur 0 sans OOM. Aucun bras instrumenté dans cette mesure.

| Année | Profit moyen Opex | Profit moyen AAA | Moyenne des ratios Opex/AAA | Victoires Opex |
|---|---:|---:|---:|---:|
| 1970 | 415 169 £ | 635 032 £ | 66,98 % | 0/5 |
| 1971 | 973 520 £ | 1 635 416 £ | 60,76 % | 1/5 |
| 1972 | 1 346 508 £ | 2 267 318 £ | 59,60 % | 0/5 |
| 1973 | 1 350 601 £ | 2 881 805 £ | 46,89 % | 0/5 |
| 1974 | 1 483 879 £ | 3 410 306 £ | 43,13 % | 0/5 |
| 1975 | 1 524 370 £ | 4 747 851 £ | 31,82 % | 0/5 |

| Graine | Profit Opex 1975 | Profit AAA 1975 | Opex/AAA | Valeur Opex | Valeur AAA |
|---|---:|---:|---:|---:|---:|
| 42 | 1 576 878 £ | 4 618 254 £ | 34,14 % | 6 447 278 £ | 8 577 332 £ |
| 100 | 616 074 £ | 3 915 948 £ | 15,73 % | 2 645 327 £ | 8 131 772 £ |
| 999 | 1 969 954 £ | 4 208 862 £ | 46,80 % | 8 927 410 £ | 9 123 540 £ |
| 1234 | 1 397 926 £ | 4 760 227 £ | 29,37 % | 5 108 879 £ | 8 201 656 £ |
| 5678 | 2 061 017 £ | 6 235 965 £ | 33,05 % | 7 487 618 £ | 13 991 421 £ |

Le ratio des moyennes de profit en 1975 vaut **32,11 %**, distinct des 31,82 %
de moyenne des ratios. Écart moyen **−3 223 481 £/an** ; aucune victoire finale
en profit ou valeur. Opex plafonne après 1972 pendant qu'AAA continue à croître.
Le seul ratio ne permet pas de choisir entre génération, sélection et exploitation.
Source calculée : `results/duel_default_completion_20261001_analysis.json`.

Écart médian −3 299 874 £/an ; IC95 exploratoire de Student (4 degrés de
liberté) de l'écart moyen : [−4 086 626 ; −2 360 337] £/an. Cinq cartes de
diagnostic seulement : ce n'est ni un effet causal d'un correctif ni une
qualification d'adoption.

| Graine | Véhicules principaux Opex / AAA | Avions Opex / AAA | Aéroports Opex / AAA |
|---|---:|---:|---:|
| 42 | 136 / 213 | 118 / 34 | 29 / 31 |
| 100 | 92 / 252 | 83 / 46 | 21 / 38 |
| 999 | 171 / 240 | 152 / 49 | 27 / 40 |
| 1234 | 128 / 264 | 107 / 42 | 25 / 42 |
| 5678 | 112 / 346 | 99 / 61 | 25 / 50 |

Compteurs officiels au checkpoint final, filtrés par propriétaire. Plus d'avions
mais moins d'aéroports et moins de profit chez Opex ne démontre pas, à lui seul,
la cause marginale du déficit.

## Incidents techniques des nouvelles fixtures (preuves conservées)

- r1 : les **48 cas VM + neuf contrôles de frontière passent**. La fixture
   monde appelait `AIVehicle.GetOwner`, absent de NoAI15 ; remplacé dans la
   fixture uniquement par `AIVehicleList().HasItem`.
- r2 : attente GS expirée. Les panneaux sont filtrés par compagnie même en GS ;
   lecture/accusé sous `GSCompanyMode(0)`, modification de caisse en deity.
   Contrat vérifié dans le source OpenTTD15.3 `script_sign.cpp`/`script_signlist.cpp`.
- r3 : demande réelle want=4, frontière P+999 rejetée puis P+1000 sélectionnée,
   sauvegardes en état `selected` présentes. Le lecteur cherchait un jour trop tôt :
   dans `Save()`, NoAI expose encore la veille de la date DATE du checkpoint
   mensuel. Correction du lecteur avec vérification de la séquence complète
   des sauvegardes ; aucune substitution du checkpoint par une fraction temporelle.

Ces erreurs de préparation/lecture ne sont pas des échecs économiques ni des
régressions de l'IA de production. Aucun de ces artefacts n'est écrasé.

- r4 : checkpoint sélection **1970-06-01** effectivement chargé et ligne/IDs
   réconciliés. Une dépense d'exploitation de 30 £ entre l'accusé GS et le réveil
   AI empêchait la caisse exacte. Préparation amendée avant r5 : au plus vingt
   nouvelles commandes GS réelles pour obtenir l'égalité au moment du contrôle,
   puis abandon si inexposée. Les prix/gardes/API ne sont jamais substitués.

- r5 : garde réel `price=34863 need=41302 cash=41302` atteint après trois
   préparations GS au reload. Achat exécuté ; vérification ultérieure interrompue
   par `array.find`, indisponible dans cette VM. Remplacement par une boucle
   de comparaison d'IDs dans la fixture uniquement ; campagne r5 conservée.

## Protocole R3 dirigé (avant exécution)

Trois essais séparés, graine42, deux ans maximum chacun, un worker, aucune
concurrence avec les autres conteneurs. Copier trois vrais plans du portefeuille,
préparer la caisse par GS et les repasser au sélecteur commun ; vérifier leur
ordre normal et leur liveness initiale. Aucun tri artificiel, changement de
K_pass, quotas, bypass, booléen de caducité ou retour constructeur.

- Caducité : A–B, A–C puis D–E indépendant ; A–B doit réellement construire,
   A–C devenir caduc et D–E consommer l'unique bypass puis réussir.
- Cash : trois plans disjoints ; après premier succès, une vraie commande GS
   réduit le disponible sous le financement suivant. Exiger `finance >= K_pass`
   et l'arrêt cash réel avant commande du deuxième projet.
- Refus : trois plans disjoints ; après prétests et nivellement du deuxième
   projet, occuper réellement son ancre avec `AICompany.BuildCompanyHQ` dans la
   copie de test. Le vrai `BuildAirport` doit échouer ; conserver son code erreur,
   vérifier rollback/absence d'avion orphelin puis arrêt du troisième par K_pass.
   Le QG est un obstacle de fixture déclaré, pas un chantier fantôme ni une
   dépense économique comparable. R19 synthétique reste OFF.

Les services/ordres et la présence physique des véhicules attachés sont contrôlés
par API ; le lecteur R1/R3 existant vérifie les transitions. Une précondition
manquante ne devient jamais une réussite. Le portefeuille de trois candidats
est un état de test, pas une mesure de concurrence sur le catalogue complet.

## Résultats dirigés et régression

**R1/VM r6 terminé**, sortie 0 sans OOM ; sources, copie et fixtures inchangées.
Artefacts : `results/mechanism_completion/engine_20261001_r6/`.
48 cas VM +9 frontières passent ; cinq scénarios R1 passent avec les fonctions
de production, les prix/caisse réels et les ordres vérifiés par API :

- demande réelle quatre, budget 35 862 £ = prix 34 863 £ +999 : pas d'admission ;
- budget prix +1 000 : ajustement 4→1, puis garde d'achat réel
   `price=34863 need=41302 cash=41302`, un avion ajouté, aucun remplacé ;
- même snapshot après achat/reload : rejet `fleet_stale`, pas de double achat ;
- mutation réelle de flotte par helper puis rejet du snapshot indépendant caduc ;
- checkpoints sélection **1970-06-01** et achat **1970-07-01**, même requête
   `f64`, ligne5 et IDs réconciliés (inventaire1 puis2).

SHA256 des deux sauvegardes :
`e19f10de11dbed010894085b60c11829b67243a25e7d579862a6be0092990fb4` et
`117cac9998ab1f39768b4efeff6eb61f22d526550e7152b6aedf43d6353c5b21`.

Le contrôle annuel standard signale des mois manquants avant les deux reloads,
car il attend janvier. Le lecteur de fixture ajoute désormais un contrôle
mensuel strict à partir du vrai checkpoint ; le rapport annuel brut est conservé.
Il ne faut pas qualifier ces phases de campagnes économiques saines.

R3 caducité r1 a été interrompu par le terminal (sortie130) ; artefacts conservés.
R3 caducité r2 a exécuté A–B puis D–E, sauté naturellement A–C, avec initialement
trois plans vivants et deux avions attachés sans orphelin. Le lecteur a toutefois
traité à tort `schema_version` comme une erreur : sortie1, rapport brut conservé.
Correction limitée au lecteur : seuls `attributed`, `unattributed`, `engine_marker`
définissent les erreurs, et les champs absents restent invalidants.

La relecture hors moteur de R1 r6 et R3 caducité r2 confirme leurs intervalles
mensuels réels et les hashes de **76 sauvegardes +4 logs** ; aucune erreur script.
Reçu séparé `results/mechanism_completion/receipt_review_20261001_r1.json` :
caducité **validée après correction du lecteur**, sans réécrire la sortie1
originale ni rejouer pour obtenir une issue différente.

R3 cash r1 : complet, sortie0 sans OOM, trois liveness initiales ; après un
succès, arrêt réel `finance=101364 available=91364 threshold=0`, bypass inchangé.
R3 refus r1 : vrai obstacle QG, vrai refus `AFAIL error=260 ERR_AREA_NOT_CLEAR`,
bypass consommé puis arrêt du suivant à K_pass. La trace structurée perd toutefois
le détail : le gate des discards n'inclut pas `decision_log`. Avant r2, ajout de
`R1_R3_TEST_ONLY` à ce gate **dans la copie seulement**, conservation du vrai
`result.reason/error`. Ajout du contrôle du nombre d'aéroports avant/après refus
et de l'absence d'aéroport à l'ancre ; aucun retour API ou quota substitué.

Régression complète avant ce dernier correctif de lecteur : **1126 tests,
1124 réussites, 1 erreur historique Git absent, 1 skip**. Contrats du lecteur
et de santé après correction : **40/40 réussis**, dont13 nouveaux contrats de
fixtures. Aucun test Python ne remplace les exécutions Squirrel ci-dessus.

**R3 refus r2 terminé**, sortie0 sans OOM, toutes les vérifications passent.
`AFAIL error=260`, lignes1→1, bypass1→1 puis arrêt `k_pass` du rang2 ;
aéroports2→2, aucune récupération en attente, un avion attaché, aucun orphelin.
Artefacts finaux R3 : `r3_dead_20261001_r2` (reçu corrigé séparé),
`r3_cash_20261001_r1`, `r3_failure_20261001_r2`, sous
`results/mechanism_completion/`. Les trois expositions sont au premier passage,
**K_pass=0 naturellement**, pas une couverture de tous les régimes ultérieurs.
Le refus testé est à A avant construction d'aéroport, pas une qualification de
tous les chemins de récupération partielle R19.

Contrats finaux après collecte du refus : **136/136 réussis** (fixtures, santé,
R1/R3, intégration et shadow). La suite complète précitée précède les deux
derniers ajustements de collecte ; elle n'est pas présentée comme une nouvelle
régression complète du dernier arbre.

### Clôture et reliquats

Les **huit scénarios dirigés nommés** et la **matrice VM 48+9** sont exercés.
Code nouveau uniquement dans le lanceur/tests/fixtures ; hooks dans des copies
d'IA, aucune source de production ni défaut modifié. Aucun 20×10, commit ou
publication. Incidents, logs, sauvegardes et verdicts bruts conservés.

Restent distincts et ouverts : élection→exécution→profit réalisé par ligne sur
année complète ; réduction du coût copie/tri shadow ; rechargement d'un scan AIR
effectivement suspendu. Ces chantiers ne sont pas validés par les tests ci-dessus,
et aucun gain marginal des renforts ni neutralité des sondes n'est attribué.

Contrôle final après reprise : **123 fichiers sources AI** concordent avec les
manifestes des quatre campagnes retenues ; **126 sauvegardes et six logs**
concordent avec leurs empreintes et les intervalles mensuels réels sont complets.
Le reçu indépendant concorde avec les rapports bruts. Onze fichiers de livraison
contrôlés : syntaxe Python, liens locaux et espaces de fin de ligne OK ; aucun
diagnostic éditeur nouveau. Aucun conteneur actif, aucun OOM. La sortie1 de
R3 caducité reste conservée avec son correctif de lecture documenté.