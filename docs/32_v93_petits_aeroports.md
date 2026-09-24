# V93 — grands aéroports dans les villes sous 600 habitants

État au 2026-09-24 : **deux réglages, défaut 0**.
`v93_airport_no_pop_floor` est mesuré en duel 5×6 et laissé à 0.
`v93_air_demand_production` (V93.1) est implémenté, contrats hôte seulement.
Plancher minimal `V93_AIRPORT_MIN_POP = 100` et plafond de demande
`V93_AIR_LINE_PAX_CAP = 200` : constantes dans `globals_pre.nut`, pas des
réglages. Les deux réglages sont indépendants.

## Ce qu'AAAHogEx fait, et ce qu'OpexAI refusait

Duel 5 graines × 6 ans, départ 1970. AAAHogEx pose des aéroports **LARGE**
dans 35 villes de moins de 600 habitants. Les lignes qui touchent une telle
ville rapportent environ 50–66 k£/an. Son champ `airportTraits.population`
(`ai/AAAHogEx-115/air.nut`, vers la ligne 10) n'est pas un filtre. Il vérifie
que l'aéroport tient encore dans le budget de bruit de la ville
(`place.nut`, `_CanBuildAirport`, `GetAllowedNoise` /
`AIAirport.GetNoiseLevelIncrease`), puis classe le site par la production
attendue autour de l'ancre et par l'économie de la route (`main.nut`, vers
1440–1460, `GetExpectedProduction`).

OpexAI, au défaut, écarte ces villes avant toute économie :
`combo.kind == "large" && towns[i].pop < 600` dans `OpexAirPlansFindSites` et
dans le complément de sites hub. En 1970-1982 le combo petit n'existe pas :
`AT_SMALL` expire en 1959, `AT_COMMUTER` arrive en 1983
(`AIAirport.IsValidAirportType`). La première version du réglage, qui
n'ouvrait que ce combo, ne pouvait rien poser sur la fenêtre des bancs.

## Vivier de villes

`OpexAirSortedTowns` (`builder_air.nut:180`) trie toutes les villes du
catalogue par population décroissante. `_refreshTowns` (`catalog.nut:890`)
n'en retire aucune. `OpexAirTownPoolLimit` (`builder_air.nut:194`) borne ce
tri par la capacité spatiale C78.3 : `min(nombre de villes, cellules en X ×
cellules en Y, 4 × (cellules en X + cellules en Y))`, avec
`cellule = ceil(taille / AIR_TOWN_MIN_DISTANCE)` et
`AIR_TOWN_MIN_DISTANCE = 32` (`builder_air.nut:13`).

Sur une carte 256² du duel, cela fait 8 × 8 = 64, et le périmètre vaut aussi
64. Le plafond est donc **64 villes**. Le vivier observé est d'environ
**43 villes**, c'est-à-dire la carte entière. Les villes sous 600 habitants
sont déjà dedans. Le classement par population ne les jette que lorsque la
carte dépasse le plafond (une 1024², plafond 256, en a 700 et plus). Les
duels 256² ne sont pas dans ce cas. **Le vivier n'est pas modifié.**

Le rejet qui les sortait du scan est le test des 600 habitants, plus bas.

## Ce que fait le réglage

À 1 :

- le test `kind == "large" && pop < 600` ne rejette plus
  (`builder_air.nut:2486` et `2908`) ;
- une ville de moins de 100 habitants est refusée (`town_pop_v93`), grand ou
  petit aéroport, pour ne pas sonder les hameaux ;
- à partir de 100 habitants, la ville va à `OpexAirFindSite`, puis les
  filtres déjà en place décident : `profit_nonpositive`
  (`builder_air.nut:2824`) et le ROI du portefeuille ;
- `C78_AIRTOWN` écrit `outcome=site v93=1 pop=<habitants>` quand un site est
  trouvé dans une ville sous 600 grâce au réglage (`builder_air.nut:2504`).
  Le complément hub écrit la même ligne seulement si le scan principal n'avait
  pas déjà retenu cette ville (`builder_air.nut:2926`). Compter les `town=`
  distincts. Au défaut, la ligne reste `outcome=site` ;
- un plan grand laisse encore passer les combos `kind == "small"` qui
  suivent. Ce parcours est inchangé, et il reste vide avant 1983.

À 0, chaque nouveau test est un booléen faux. Le rejet à 600 habitants, le
`break` après un plan grand et la ligne `outcome=site` sont ceux d'aujourd'hui.
Le plancher de 100 n'est pas évalué. Pas d'appel d'API en plus.

Inchangés : ville déjà desservie, plafond de gares, clés d'abandon, filtre
hub `pop >= 2500` sur le combo petit, interdiction des gros avions sur
`AT_SMALL` et `AT_COMMUTER`. La course au second créneau C83 exige toujours
`AIR_EARLY_SLOT_MIN_POP` (1 000, `builder_air.nut:297`) : une ville sous 600
habitants peut recevoir un premier aéroport, elle n'entre pas dans cette
priorité.

## Recherche de site et bruit

`OpexAirFindSite` n'appelle pas `AIAirport.GetNoiseLevelIncrease`. La
constructibilité est le `BuildAirport` en mode test.

`AIAirport.GetNearestTown` (`builder_air.nut:688`) est la ville à laquelle le
moteur imputerait l'aéroport, pas un seuil de population. Le rayon est le
même pour toutes les villes : couronnes de 4 à `AIR_SITE_RADIUS` (25), et
rejet si le rectangle est à plus de 25 tuiles du centre (`builder_air.nut:683`).
Un hameau collé à une plus grande ville perd ses ancres au profit de la
voisine. Une ville isolée n'est pas pénalisée par ce test.

Avec `economy.station_noise_level = 0`, réglage du duel,
`AITown.GetAllowedNoise` vaut `max(0, 2 − nombre d'aéroports)`
(`projects.nut:668-671`). Ce nombre ne dépend pas de la population. Une ville
de 150 habitants sans aéroport accepte un `AT_LARGE` aussi bien qu'une grande
ville. `GetAllowedNoise` ne sert, dans OpexAI, qu'à la course au second
créneau (`builder_air.nut:298`).

Un refus `ERR_LOCAL_AUTHORITY_REFUSES` sur une emprise plate est accepté
comme site (`builder_air.nut:735-737`, et le même traitement sur le cache).
Ce code couvre aussi le plafond de bruit (`builder_air.nut:3659-3660`). Dans
le duel le bruit est coupé, donc le premier aéroport d'une petite ville n'est
pas refusé pour ça. Si le bruit était armé, le plafond suit la population :
une petite ville pourrait refuser un grand aéroport, et `FindSite` rendrait
quand même le site. Le chantier échouerait ensuite. Les bancs 1970-1979 ne
sont pas dans ce cas.

## Demande : ce qui rend une petite ville plus belle que le terrain

Le plan ne lit pas `AITown.GetLastMonthProduction`. Il pose

`monthlyPax = (popA + popB) × TOWN_CATCHMENT_SHARE_PCT / 100`

(`builder_air.nut:2772` ; hub vers site `3112` ; hub vers hub `3320-3321`).

`TOWN_CATCHMENT_SHARE_PCT = 22` (`candidates.nut:1039`) est la part mesurée de
la **production mensuelle** d'une ville qui atteint une gare
(`candidates.nut:1029-1036`). Le plan aérien applique ces 22 % à la
**population** affichée.

La production du moteur, elle, se tire par tuile de maison, toutes les
256 ticks : si le tirage `X` (0…255) est inférieur à la population de la
tuile, la tuile produit `floor(X / 8) + 1` passagers
(`docs/mecanique_jeu.md:375-376`). C'est convexe en la population de la tuile.
Une tuile de 8 habitants produit en espérance environ 0,27 passager par mois
(0,03 par habitant). Une tuile de 64 habitants en produit environ 9,8
(0,15 par habitant). Le modèle inscrit 0,22 passager capté par habitant :
environ six fois la production totale d'une petite tuile, et environ une fois
et demie celle d'une tuile déjà grande. Une ville de 1970 sous 600 habitants,
faite de petites maisons, est donc **surévaluée** plus fortement qu'une grande
ville passée dans la même formule, et surévaluée par rapport à sa production
réelle.

Le plancher `monthlyPax < 10` puis `monthlyPax = 10` (`builder_air.nut:2775`,
et `3116`, `3325`, `1056`) ne relève que les paires dont la somme des
populations est inférieure à 46. Deux villes au plancher de 100 donnent
déjà 44. Ce plancher ne gonfle pas les villes que V93 laisse entrer. Il
gonflerait des hameaux plus petits ; ils restent exclus.

La position du site n'entre pas dans ce calcul. La recherche commence à
4 tuiles du centre, donc l'emprise rate souvent les quelques maisons d'une
petite ville. AAAHogEx, de son côté, lit la production des tuiles autour de
l'ancre. OpexAI inscrit 22 % de toute la population quel que soit l'endroit
où l'aéroport se pose : au moment de la décision, la petite ville paraît
plus riche que le captage réel du site. Les arrêts joints, qui ramènent le
centre-ville après la pose, ne comptent ni en coût ni en demande avant le
chantier (`builder_air.nut:1108-1109`). Ils ne corrigent le chiffre qu'une
fois la ligne construite.

Le sens pour le réglage : une ville de 100 à 599 habitants franchit plus
facilement `profit_nonpositive` que sa production réelle ne le justifierait,
surtout en bout de ligne avec une grande ville. C'est le filtre économique
voulu ; il est optimiste, pas un second plancher de population.

## Validation du plancher

Le duel 5×6 de `v93_airport_no_pop_floor=1` est dans la section V93.1. Il ne
passe pas la garde de valeur. Le défaut reste 0. Les lignes `outcome=site
v93=1` disent combien de villes sous 600 habitants ont reçu un site.

## V93.1 — demande par production

### Duel du plancher, 5 graines × 6 ans

`v93_airport_no_pop_floor=1` contre le défaut, même AAAHogEx figée.

| | |
|---|---|
| `profit_year` | moyenne **+33 k£/an**, médiane **+103 k£/an**, 3 graines au-dessus et 2 en dessous |
| IC95 | **[−296 ; +362] k£/an** |
| Valeur d'entreprise | **−15 %**, garde de **−5 %** franchie |
| Aéroports OpexAI | **33** contre **24** par partie |
| Avions OpexAI | **73** contre **89** par partie |

OpexAI pose davantage d'aéroports et moins d'avions. Le profit moyen est
positif, l'intervalle contient zéro, et la valeur tombe. Le réglage n'est pas
adopté. La section précédente explique le sens : le plan inscrit 22 % de la
population, ce qui rend une petite ville plus riche que sa production et que
le bassin réel du site. V93.1 change ce chiffre, pas le plancher.

### Ce qu'AAAHogEx fait (idée seulement)

`TownCargo` dans `ai/AAAHogEx-115/place.nut`, relu sans en copier le code.

- Base : `AITown.GetLastMonthProduction` du cargo passagers. Si ce chiffre
  dépasse la population, repli `population / 8` (`place.nut` vers 2969).
- `AdjustUsing` (vers 1927) : tant qu'aucune route à nous ne part de la ville,
  `production * 70 / (GetLastMonthTransportedPercentage + 70)`. Sinon, division
  par le nombre de routes qui ont cette ville pour source, nouvelle comprise,
  et par le nombre de compagnies.
- Plafond par ligne (vers 2958-2966) : 200 passagers par mois, 100 si la ville
  a moins de 700 habitants. Si la ville ne peut plus croître, ×2/3 (vers 2922,
  `CanGrowth`, lié à leur réseau de bus).
- Contrôle du site : `AITile.GetCargoProduction` sur le rayon de captage
  (vers 2750).

### Ce que fait `v93_air_demand_production`

Réglage 0/1, défaut **0**, déclaré dans `info.nut`, chargé dans
`settings.nut`, globale `V93_AIR_DEMAND_PRODUCTION <- false`. Il ne lit pas
`v93_airport_no_pop_floor`. Les deux peuvent être armés ensemble.

À 1, `OpexAirTownMonthlyPax(town, siteAnchor, airport, lines)` fournit les
passagers mensuels d'**une** extrémité. La paire envoyée à `OpexAirEconomics`
reste la **somme des deux extrémités**, plus, à la réconciliation, le bassin
marginal des arrêts joints. Les quatre calculs passent par ce helper :
nouvelle paire, hub vers site, hub vers hub (les deux bouts, y compris le
partage utilisé par `AIR_HUBHUB_MARGINAL`), et `OpexAirReconcileActualBuild`.

Pour une extrémité :

1. Production du mois passé, cargo passagers du catalogue
   (`catalog.paxCargo`, repli `AICargo.CC_PASSENGERS`, aucun identifiant
   codé en dur). Si elle dépasse la population, `population / 8`.
2. Tant qu'aucune ligne aérienne OpexAI ne touche cette ville ou cet
   aéroport, `production * 70 / (pourcentage transporté + 70)`. Le
   pourcentage est alors celui des autres. Le poids 70 est la constante
   `V93_AIR_COMPETITOR_WEIGHT`.
3. Division par `(lignes OpexAI + 1)`, toujours, donc aussi quand le compte
   est nul (diviseur 1). Les lignes se reconnaissent au centre-ville
   (`originA` / `originB`) ou à la tuile d'aéroport (`stationA` /
   `stationB`). Les deux extrémités sont divisées. Le modèle de population
   ne divisait que le hub.
4. Part captée par l'ancre, si elle est connue. `AITile.GetCargoProduction`
   compte des **tuiles productrices**, pas des passagers (correction de relecture
   du 2026-09-24 : la première version s'en servait comme borne en passagers).
   On compare donc deux comptes de tuiles : celles du rayon de l'aéroport
   (`OpexAirAirportCatchmentProduction`, emprise et rayon de couverture) et
   celles de la ville (rayon 4 + √pop / 8, borné à 20, depuis son centre). La
   demande est multipliée par leur rapport quand il est inférieur à 1. Un
   aéroport déjà posé utilise son type réel ; sinon, le type que l'on
   s'apprête à construire.
5. Plafond `V93_AIR_LINE_PAX_CAP` = 200 passagers par mois, moitié (100) si
   la population est inférieure à `V93_AIR_LINE_PAX_SMALL_POP` = 700.

Le plancher `monthlyPax = 10` reste sur le chemin du défaut. Il n'est pas
réappliqué au chiffre du helper.

Le facteur ×2/3 de croissance et la division par le nombre de compagnies
restent la méthode AAAHogEx. Ils ne sont pas dans ce réglage : le test de
croissance d'AAAHogEx dépend de son réseau de bus, et le pourcentage
transporté ne sépare pas nos avions de ceux des autres une fois qu'une ligne
OpexAI existe.

À 0, les formules `(population × 22 %)` et le plancher de 10 s'exécutent
comme avant. Chaque site ajoute le test du booléen, qui est faux : le helper
n'est pas appelé, et le chantier aérien reçoit les mêmes arguments qu'avant.

Mémo : `GetLastMonthProduction`, le pourcentage transporté et la somme de
bassin sont rangés dans `AIR_ECONOMICS_MEMO` pour le mois courant
(`AIR_MEMO_MONTH`, même horloge que le mémo C80). Clés `v93t|` (ville) et
`v93c|` (ancre, type, cargo). Le nombre de lignes est mémoïsé à part, et
jeté dès que `lines.len()` change, parce qu'une ligne nouvelle change le
diviseur au cours du mois.

Sonde : quand la génération C78 écrit une ligne `C78_AIRPAIR` admise et que
le réglage est à 1, la ligne gagne `paxNew=` (chiffre utilisé) et `paxOld=`
(proxy de population, plancher de 10 compris). À 0, le texte admis est celui
d'aujourd'hui.

### Ce qu'il faut remesurer

`AIR_PAX_REVENUE_CALIBRATION_PCT` reste **104**. `OpexAirFarePerPax` l'applique
au revenu par passager (et à la part de courrier) avant le profit. Le même
facteur est recopié dans le revenu marginal hub vers hub quand
`AIR_HUBHUB_MARGINAL` est armé. Le réglage `air_pax_revenue_calibration_pct`
ne le remplace que s'il est strictement positif. Il a été calé sur le rapport
revenu réel / revenu prédit quand la demande prédite était le proxy de
population (médiane 1,0427). On ne le change pas. Il faudra le remesurer sur
le modèle de production avant tout recalage.

C82 (`c82_engine_calibration`, défaut 0) non plus. `OpexC82ChooseRoutePlane`
choisit le moteur avec `OpexC82EngineFactor`, et `OpexC82Profit` pondère le
score du projet. Les facteurs viennent du rapport annuel réel / prédit par
moteur (`task_report.nut`, rechargés par `OpexC82RecomputeFactors`). Le prédit
passe par `monthlyPax` dans `OpexAirEconomics`. Des facteurs appris sur
l'ancien modèle ne sont pas une preuve sous V93.1. La formule et le défaut
restent en place.

Avant d'armer l'un ou l'autre par défaut : smoke 1×1 avec
`v93_air_demand_production=1`, puis duel apparié 5×6 contre le défaut.
Métrique, effet utile et garde de valeur fixés avant le banc. Le plancher de
600 habitants a déjà son 5×6 ; le combiner avec V93.1 est un essai distinct.
Contrats hôte seulement pour l'instant. Pas de partie lancée avec ce
changement.
