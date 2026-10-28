# ROAD100 — ce que fait réellement AAAHogEx-115 en ROUTE seule (28/10/2026)

**Statut : analyse du concurrent, pas une qualification d'OpexAI.** Les cinq parités
`profit_year` restent **0/5**. Aucun code AAA n'a été copié, aucun réglage par défaut
modifié, aucun Docker ni nouveau duel lancé pour cette étude.

## Corpus et méthode

- `results/road100_baseline_40x5_20261027.{jsonl,json,manifest.json}` et
  `results/road100_baseline_40x5_20261027_engine/*.log` : 40 graines,
  `OpexAI` et `AAAHogEx` avec les autres modes désactivés ; snapshots du
  **1er décembre**, années 1970 et 1974 principalement.
- `results/road100_v30a_pax_units_roadonly_5x5_20261028_engine/reference_seed42_r0.log` :
  traces d'une première ligne AAA, avec campagne figée différente de la baseline ;
  à ne **pas** mélanger avec la baseline pour une inférence causale ON–OFF.
- `line_telemetry.lines` : une ligne est un **groupe de véhicules** observé ;
  `cargo_types=['0']` représente PASS. Distance ci-dessous = Manhattan entre
  deux tuiles de station, sur cartes 256² ; **pas** longueur exacte de voirie,
  ni distance entre centres de villes. Totaux sur **40 mondes**, non nombres
  de lignes par monde. On n'additionne pas les profits de véhicules pour les
  assimiler au `profit_year` de société.
- Les populations **exactes** des villes ne sont pas dans les clichés
  `line_telemetry`. Leurs productions mensuelles figurent dans certains
  journaux AAA. Ne pas inventer de populations à partir des productions.

**Population : ce que l'on sait réellement.** AAA examine les villes
productrices de PASS/MAIL au-delà de 200 habitants (`place.nut:1037-1044`).
Son rayon de recherche des quartiers dépend de la population : <700
habitants = rayon 3 ; 700..1199 = 4 ; 1200..1799 = 5 ;
1800..2699 = 6 ; 2700..3699 = 7 ; 3700..4999 = 8 ;
jusqu'à 12 pour 10200..12399 (`place.nut:2726-2744`). Ce sont des
**seuils de code**, et non la distribution démographique des lignes
construites. Dans les logs Opex des lignes PAX âge 1 (55 observations),
les populations de la plus petite ville sont p10/médiane/p90
**388/511/807**, celles de la plus grande **539/942/2203** ; cette
dernière distribution est celle d'Opex, **pas** d'AAA.

## Réseau réalisé : lignes, kilomètres de cases et flotte

| Fin d'année / société | Toutes lignes ROUTE | Véhicules ROUTE | Lignes PASS | Bus PASS | Profit annuel société, somme 40 mondes |
|---|---:|---:|---:|---:|---:|
| 1970 AAA | 167 | 2 111 | 164 | 2 082 | 5 379 911 £ |
| 1970 Opex | 114 | 228 | 23 | 46 | 323 809 £ |
| 1974 AAA | 2 007 | 19 864 | 754 | 4 836 | 86 456 264 £ |
| 1974 Opex | 287 | 574 | 61 | 122 | 1 190 119 £ |

Les ratios du **profit de société** Opex/AAA sont 6,02 % en 1970 et
1,38 % en 1974 dans ces clichés (les horizons intermédiaires et la mesure
terminale canonique restent dans le rapport baseline). En 1970, AAA a
principalement des autobus, alors qu'Opex a déjà 73 lignes de charbon
et seulement 23 lignes PASS.
`profit_year` décembre 1970 ne couvre que trois trimestres valides,
contre quatre pour les années 1971–1974 : respecter cette convention
pour les comparaisons de performance du banc.

**Trajectoire du critère primaire, moyenne de 40 sociétés par horizon**
(`profit_year` réellement enregistré en jeu, non revenu des lignes) :

| Horizon | AAAHogEx | OpexAI | Ratio Opex / AAA |
|---|---:|---:|---:|
| H1 (1970) | 134 498 £/an | 8 095 £/an | 6,02 % |
| H2 (1971) | 555 822 £/an | 26 907 £/an | 4,84 % |
| H3 (1972) | 1 108 485 £/an | 28 913 £/an | 2,61 % |
| H4 (1973) | 1 704 870 £/an | 29 110 £/an | 1,71 % |
| H5 (1974) | 2 161 407 £/an | 29 753 £/an | 1,38 % |

Pour H5 le **déficit primaire moyen est donc ~2 131 654 £/an**
dans la baseline ; le chiffre ON de V30a vient d'une autre campagne et
ne doit pas remplacer cette référence sans appariement. Les quantités
PASS livrées **par compagnie**, agrégées sur une année, illustrent
l'offre physique : AAA/Opex en 1970 **7 684/227**, 1971
**18 831/575**, 1972 **26 008/662**, 1973 **29 413/640** PASS
en moyenne par monde (1974 ne couvre que trois trimestres dans ce
dépouillement : **22 477/524**). Ces valeurs ne ventilent pas
la livraison par ligne.

**Distribution des flottes par groupe ROUTE** (p10 / médiane / p90 / max,
sur tous les groupes des 40 mondes) : AAA PASS 1970 = 2/12/25/44,
AAA PASS 1974 = 2/6/11/28, AAA charbon (cargo1) 1974 = 6/17/35/69,
AAA bois (cargo7) = 6/18/28/80, AAA minerai (cargo8) =
4/11/23/40. Tous les groupes PASS, charbon, bois et minerai Opex
observés en 1974 ont **exactement deux véhicules**. Il faut donc
résoudre simultanément le marché, la captation et la capacité de service,
pas seulement augmenter le nombre de projets. V31 n'a acheté aucun
bus supplémentaire dans son smoke, faute de vrais quais bilatéraux.

**Saturation de la limite moteur** : AAA configure `maxRoadVehicle=500`
dans les logs. En 1973, 7/40 compagnies sont déjà exactement à 500
véhicules ; en décembre 1974, **26/40 sont à 500**, **35/40 à au moins
490**, moyenne **496,6**. Opex est à **14,35** véhicules en moyenne,
maximum 24. Le problème d'Opex est d'abord le manque d'offre physique ;
chez AAA, l'accélération des ouvertures ralentit une fois cette limite
presque saturée.

**Évolution du portefeuille AAA observé aux clichés** (lignes persistantes,
pas dates exactes d'achat) :

| Cargo | 1970 | 1971 | 1972 | 1973 | 1974 |
|---|---:|---:|---:|---:|---:|
| PASS | 164 | 359 | 620 | 729 | 754 |
| MAIL | 3 | 205 | 391 | 534 | 560 |
| COAL | 0 | 26 | 130 | 217 | 228 |
| IORE | 0 | 0 | 8 | 98 | 114 |
| WOOD | 0 | 0 | 5 | 90 | 103 |

La première cohorte PASS (164 groupes visibles fin 1970) est encore
présente fin 1974, mais sa flotte médiane descend **de 12 à 9 bus** ;
la cohorte charbon vue pour la première fois en 1971 monte d'environ
**2,5 à 20 camions** de médiane. AAA redistribue donc de la capacité
des lignes pionnières PASS vers le fret en cours de maturation.

| Distance PASS | AAA 1970 | Opex 1970 | AAA 1974 | Opex 1974 |
|---|---:|---:|---:|---:|
| ≤20 cases | 0 | 3 | 0 | 6 |
| 21–42 | 1 | 15 | 11 | 42 |
| 43–80 | 42 | 5 | 117 | 13 |
| 81–160 | 118 | 0 | 602 | 0 |
| >160 | 3 | 0 | 24 | 0 |

**Découverte fondamentale :** AAA exploite des lignes PASS de 81–160
cases dès la première année (118/164), alors qu'Opex ne franchit jamais
80 cases dans les lignes voyageurs de cette baseline. La sélection des
marchés est pratiquement disjointe : 0 marché PASS commun en 1970 et
seulement 1 commun sur les 754 marchés PASS AAA en 1974, appariés par
graine et `market_key`. Ce constat **ne** prouve **pas** qu'une ligne
longue Opex serait rentable ou constructible sans captation et devis réel.

Les distances médianes des véritables groupes de transport en 1974 sont
**AAA vs Opex** : PASS 109/33 cases, COAL 92/36, MAIL 91/39,
WOOD 97/34, IORE 102/36, GOOD 86/43. L'écart de distance concerne
donc l'ensemble du portefeuille, pas seulement les bus.

### Diversification observée en 1974

Dans les 40 mondes AAA, les groupes ROUTE sont : 754 lignes PASS/
4 836 bus ; 228 groupes cargo id1/4 463 camions ; 560 groupes id2/
3 805 véhicules ; 103 groupes id7/1 880 véhicules ; 114 groupes id8/
1 480 véhicules ; 75 groupes id5/1 222 véhicules, et d'autres cargaisons.
Les identifiants reflètent le schéma cargo OpenTTD de la partie ; pour une
interprétation métier, résoudre les *labels* de chaque sauvegarde plutôt
que supposer la permanence des IDs dans tous les NewGRF. Aucun groupe
multicargo n'a été observé dans ces clichés.

En moyenne par monde, AAA possède à fin 1970 **52,8 véhicules** et
**15,3 k£ de caisse**, contre **5,7 véhicules** et **258 k£ de caisse**
chez Opex ; les emprunts restants sont respectivement **230,8 k£** et
**300 k£**. En 1974 : AAA ~496,6 véhicules, 2 247,5 k£ de caisse et
emprunt remboursé ; Opex ~14,4 véhicules, 277,6 k£ de caisse et
294,8 k£ d'emprunt. AAA convertit son capital initial et sa capacité
d'emprunt en services physiques plus tôt, puis réinvestit.

## Premier corridor AAA graine 42 : preuve de procédure

`reference_seed42_r0.log` : le **2 janvier 1970** AAA lit Danville
355 PASS/mois et Little Sintburg 327 PASS/mois de **production-ville**,
pas la capture d'un arrêt. Le **19 janvier** il classe leur connexion
bidirectionnelle à distance-centres 158 : estimation 340 PASS,
27 bus de capacité 35, capital affiché 210 574 £, `routeIncome`
202 498 £/an **prédit**, classement `roi:744` (par mille).
Le constructeur démarre le 19 janvier, crée des arrêts et extensions
`BuildSpreadPieceStations` aux deux extrémités le 23 janvier, puis
enregistre `RouteBuilder Succeeded` le **7 mars 1970**.

Sur les 40 logs AAA, les projets PAX **planifiés** à leur tentative
en 1970 (n=209, construction réussie ne garantissant pas encore tous
les véhicules achetés) ont une flotte estimée de **7 / 10 / 23 / 41**
aux p10 / médiane / p90 / maximum, une production opérationnelle
estimée de **140 / 212 / 383 PASS/mois** aux p10 / médiane / p90,
et une distance entre centres médiane de **113 cases**. Corrélations
de rang de Spearman : nombre de bus projetés avec production **0,577**,
avec distance **0,423**. Le nombre de bus dépend des **deux**, via
temps de rotation, et non d'un multiplicateur constant de population.
Ces productions sont les estimations de constructeur AAA, **pas**
les livraisons ni les productions marginales de stations Opex.

Dans la partie de référence V30a à fin 1970, le marché principal
correspondant compte **27 bus** et le groupe présente environ
**112 862 £ de profit de véhicules depuis janvier**, tandis que le
`profit_year` de la **société AAA** complète est **99 167 £**.
Les deux chiffres ne mesurent pas la même chose. On ne doit jamais
réinjecter ce profit AAA après construction dans les prévisions Opex.

**Les trois lignes PASS effectivement construites par AAA en 1970,
graine 42, bras référence V30a**, avec identifiants de station appariés
aux coordonnées des logs (volume PASS = production mensuelle des villes,
et `profit_this_year` = profit des groupes de véhicules, **pas société**) :

| Ligne AAA, villes | Production PASS/mois des villes | Distance centres → gares | Succès du chantier | Bus en décembre | Profit véhicules YTD en décembre |
|---|---:|---:|---|---:|---:|
| Danville – Little Sintburg | 355 / 327 | 158 → 134 | 7 mars | 27 | 112 862 £ |
| Little Frundingbury – Gredingstone | 332 / 175 | 71 → 56 | 24 mars | 6 | 24 038 £ |
| Gredingstone Bay – Sonfield | 234 / 190 | 154 → 140 | 10 août | 24 | 10 286 £ |

Les différences `distance centres → gares` rappellent que le site réel
est optimisé après classement ; un devis basé sur les centres n'est
pas une longueur de voirie. La ligne d'août peut avoir une grosse flotte
et un profit YTD modeste à fin 1970, car elle ne tourne pas toute l'année.

## Logique du code AAA, reformulée sans la recopier

1. **Origines et destinations :** `ai/AAAHogEx-115/main.nut:1250-1333,
   1333-1801` recense sources par cargo, industrie et ville, écarte
   les sources déjà saturées/non utilisables et explore les distances
   Manhattan. `place.nut:1026-1079` : villes PASS/MAIL de population
   >200 ; acceptation GOODS conditionnée notamment par la population.
   Il existe un minimum de production estimée **27** avant calcul du
   projet (`main.nut:1737-1771`), 25 candidats au plus par source,
   1 000 candidats globaux (`main.nut:874-881`).
2. **Marché et revenu :** pour une route bidirectionnelle ROAD, l'estimateur
   prend le minimum des productions estimées aux deux bouts
   (`main.nut:1744-1761`) ; il tient compte de la distance, du moteur,
   du temps, du coût et du fret. La prévision initiale de la ville
   utilise `AITown.GetLastMonthProduction`, puis des corrections
   d'utilisation, population/densité et `station_spread`
   (`place.nut:2922-2981`). Ces hypothèses ne sont **pas** une mesure
   exacte de la quantité transportée par les vrais quais.
3. **Flotte estimée :** `estimator.nut:264-315` : production retenue
   × note de station /255, livraison plafonnée par capacité de route,
   nombre cible de bus/camions fonction du temps aller-retour et de
   la capacité unitaire, recettes `AICargo.GetCargoIncome` et retour
   seulement lorsque les deux sens produisent. Score économique
   basé selon phase sur ROI, profit/temps de chantier ou profit/véhicule
   (`main.nut:781-836`, `estimator.nut:54-94`).
4. **Captation physique :** `station.nut:841-1045,2172-2223`
   recherche la position et l'orientation d'arrêts, puis étend le
   même StationID dans la zone autorisée avec des quais joints.
   Le comptage `AITile.GetCargoProduction` est en **producteurs**, et
   sert au choix des tuiles ; il ne fournit pas des PASS/mois.
   Les rabattements TownBus ne sont pas automatiquement ajoutés
   au premier corridor ROAD en mode `distant_join`
   (`road.nut:1157-1161`, `route.nut:4054-4069`).
5. **Route réellement bâtie :** `road.nut:842-1026` recherche un chemin
   avec A*, réutilise les routes, gère obstacles/ouvrages, construit
   les arêtes et réessaie en cas de refus (jusqu'à quatre tentatives).
   AAA n'est donc **pas** limité à une droite ou quelques doglegs
   géométriques ; son coût d'opcodes peut être élevé et n'est pas
   directement comparable au budget PO01C d'Opex.
6. **Mise en service et croissance :** `route.nut:2859-2873`
   construit d'abord un véhicule puis son clone. Ensuite, après
   service seulement, `route.nut:2720-2724,2837-2921` inspecte la
   **plus faible** attente des deux terminus bidirectionnels, ajuste
   la cible et achète jusqu'à quatre véhicules de plus par passe
   selon les limites de capacité et de finances. Ces attentes sont
   **ex post** : elles sont légitimes pour une flotte déjà créée,
   pas pour sélectionner un projet encore inexistant.
7. **Financement :** `main.nut:4215-4250,4295-4296` traite la capacité
   d'emprunt non utilisée comme fonds potentiellement mobilisables et
   attend/emprunte pour certaines commandes. La faible caisse AAA
   initiale n'est donc pas une faillite mais une allocation agressive.

## Ce que ROAD100 peut apprendre — pas un clone AAA

Le différentiel **H1** vient largement de l'accès à des marchés PASS
interurbains réellement servis à grande capacité ; le différentiel
**H5** cumule cette avance et la multiplication de lignes fret/courrier.
Opex ne doit **ni** déduire la production physique des seuls producteurs
de tuiles, **ni** prédire la capture depuis les véhicules ou le waiting
AAA. Le contre-audit PAX 40 graines (`docs/road100_calibration_pax_40graines_20261028.md`)
interdit aussi le multiplicateur V24 naïf.

Avant une nouvelle variante, préqualifier **quelques corridors** par
`town_population`, `town_pass_per_month`, deux unions de zones BUS réellement
constructibles (avec exclusion de stations Opex), capture marginale
estimée et **validée dans des lignes Opex existantes**, chemins PO01C
résumables qui peuvent réellement franchir d80..160, devis complet,
trésorerie, plafond de flotte et rentabilité nette conservatrice.
Documenter les obstacles géométriques récurrents de V30a (175 TRACEX
pour 32 admissions ; 118 répétitions de paires), plutôt que rescanner
les mêmes échecs. N'envisager le Gate A qu'après **construction et
livraisons effectives**, un gain primaire vérifié sur un pilote
strictement ROAD-only et sans dégradation des horizons précédents.

**Non résolu :** distributions exactes de population des villes sur les
40 cartes et attribution de la production de chaque maison aux stations
avant chantier. Les logs actuels ne donnent pas ces mesures pour toutes
les lignes ; une télémétrie supplémentaire est nécessaire avant de
prétendre en déduire une borne financière sûre.

## Diagnostic précis du plafond de distance Opex : pas une constante à changer

La baseline `road100_baseline_seed42_r0.log` publie
`EPOCH_BOUNDS roadMin=7 roadMax=7 roadGen=200` dès 1970.
`ai/OpexAI/candidates.nut:438-485,590-655` montre que la fenêtre
**effective** de génération ROAD est `roadGenMax=200` dans cette partie,
non `roadMax=7` et non un plafond rigide de 50 cases. **Il serait faux
de prétendre qu'augmenter `roadMax` vers 160 résoudrait le problème.**

À l'inverse, `OpexRoad100SiteFirstGenerator` (`candidates.nut:2128-2238`)
limite *explicitement* ses nouvelles paires PASS à **12..42 centres**,
au plus **six préplans par génération** et **2,5 M opcodes** : son
commentaire rapporte que des tentatives à 86..197 cases échouaient en
`TRACEX`. Le calcul `OpexRoadLineEconomics`
(`economy.nut:737-825`) part de **deux véhicules par paire de
quais simples**, même lorsque le volume théorique demanderait plus.
L'extension V31 à plusieurs quais reste conditionnée à une vraie pose
physique aux deux extrémités ; son smoke n'a acheté aucun bus.

Les trois verrous sont donc **la sélection/exposition de corridors
longs, la géométrie constructible et la capacité de quai/flotte**.
Les résultats négatifs ROAD100_LONG et les 175 refus TRACEX pour
32 admissions V30a, dont 118 répétitions de paires, empêchent de
présenter une hausse de distance ou de flotte comme un remède validé.
La prochaine preuve utile serait un **corridor d80..160 PASS ou fret**
identifié indépendamment par demande ex ante, desservi par deux vrais
arrêts et un chemin/route existants physiquement constructibles,
avec devis, cash, opcodes et charge/rentabilité conservatrice.
