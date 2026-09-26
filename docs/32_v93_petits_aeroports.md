# V93 — grands aéroports dans les villes sous 600 habitants

État au 2026-09-25 : **deux réglages, défaut 0**.
`v93_airport_no_pop_floor` est mesuré en duel 5×6 et laissé à 0.
`v93_air_demand_production` correspond sur `master` à **V93.1**, également
laissé à 0 après un 20×10 nettement défavorable. Une variante simplifiée
**V93.2** a été testée sur la branche `v93-demand-residual`, puis rejetée au
5×6 ; son comportement n'est pas fusionné dans `master`. Le plancher minimal
`V93_AIRPORT_MIN_POP = 100` et le plafond V93.1
`V93_AIR_LINE_PAX_CAP = 200` restent donc présents dans le code courant.

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

### V93.1 — ce que fait `v93_air_demand_production` sur `master`

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

### Duel V93.1, 20 graines × 10 ans

Campagne `v93_1_air_demand_vs_default_20x10_20260924`, 20 paires complètes.
La première version est nettement rejetée :

- `profit_year` : **−421,5 k£/an** en moyenne, médiane −409,4 k£, 3/17,
  `p=0,002577`, IC95 Student **[−586,4 ; −256,6] k£/an** ;
- valeur d'entreprise : **−1,790 M£**, soit **−18,24 %**, 4/16 ;
- véhicules : **−17,45** (**−11,16 %**) ;
- créneaux aéroport Opex : **−4,85**, 1/18/1, `p=0,000076` ;
- villes avec présence Opex : **−4,15**, 2/18, `p=0,000402` ;
- villes partagées 1–1 : **−2,4** ; monopoles AAAHogEx `(2,0)` : **+1,2**.

La divergence apparaît très tôt : l'écart moyen de créneaux Opex vaut déjà
−2,0 en 1971 et environ −5 à partir de 1972. Le déficit de `profit_year`
s'amplifie ensuite jusqu'à −421,5 k£/an en 1979. Le cumul
`pourcentage transporté + /(lignes+1) + bassin + plafond 100/200` sous-estime
donc trop fortement la demande et étrangle l'expansion AIR.

### V93.2 — expérience de demande résiduelle simplifiée, non fusionnée

La branche historique `v93-demand-residual` a conservé le même réglage à
défaut 0 mais a essayé une fonction plus simple :

1. production passagers réelle du mois passé ;
2. part du bassin réellement couverte par l'aéroport ;
3. correction de concurrence `×70/(transported+70)` uniquement lorsqu'aucune
   ligne Opex ne touche encore cette extrémité.

Cette variante supprimait la division générale par `(lignes Opex + 1)` et les
plafonds fixes 200/100 pax par mois. Quand une ligne Opex existait déjà, le
pourcentage transporté n'était plus appliqué car il mélange nos propres avions
et ceux des concurrents.

Smoke 1×1, graine 42, 1 an : exécution saine mais `Δprofit_year = −67,6 k£/an`
et valeur −30,44 % contre le défaut. Le 5×6
`v93_2_demand_residual_vs_default_5x6_20260924` confirme un signal défavorable :

- `profit_year` : **−203,9 k£/an**, médiane −155,3 k£, **0/5**,
  `p=0,0625`, IC95 Student **[−332,0 ; −75,7] k£/an** ;
- ratio des moyennes de `profit_year` : **−15,29 %** ;
- valeur d'entreprise : **−541,5 k£**, soit **−10,98 %** ;
- véhicules : **+3,0** en moyenne ;
- créneaux Opex : **−3,6** ; villes Opex présentes : **−3,0**.

V93.2 reste donc une expérience archivée : **pas de 20×10 et pas de fusion du
comportement dans `master`** sous cette forme.

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
l'ancien modèle ne sont pas une preuve sous une future fonction de demande.
La formule C82 et son défaut restent en place.

V93.1 et V93.2 sont désormais tous deux défavorables. Avant tout nouvel essai,
changer le modèle causalement plutôt que prolonger l'une de ces variantes.
Métrique, effet utile et garde de valeur doivent être fixés avant le prochain
banc. Ne pas combiner automatiquement une nouvelle fonction de demande avec le
retrait du plancher de 600 habitants : ce serait un essai distinct.

## Prédit contre réalisé

`sweeps/analyse_air_demand_vs_realized.py` ne change pas l'IA. Il lit les
sorties JSON ou JSONL déjà produites par les harnais :

- `C78_AIRPAIR` admis (`P` = profit prédit ; `paxOld` et `paxNew` quand V93.1
  est armé — `parse_c78_logs`) ;
- `C78_BUILD` ;
- `LINE_PROFIT` s'il est présent (`parse_c56_log_line`) ;
- les snapshots de `diag_c78_lines_vs_aaa.py` : `companies["0"].lines`
  (`towns`, `vehicles`, `profit_last_year`), et `C78_AIRPOOL` pour la
  population.

La jointure est la paire de villes non ordonnée. Les identifiants de sauvegarde
valent l'identifiant API plus un ; le harnais a déjà soustrait 1, et le script
utilise `towns`, pas `towns_raw`.

Deux modèles, parce que `P` n'appartient qu'au modèle qui a tourné :

- proxy de population : admission sans `paxNew` ;
- production : admission avec `paxNew`.

Pour chacun : médiane et moyenne du rapport profit réalisé / profit prédit, et,
si le chiffre existe, passagers réalisés / passagers mensuels prédits. Découpage
par bande de la plus petite ville (`<600`, `600-1500`, `>1500`) et par degré
d'aéroport (nombre de lignes aériennes OpexAI sur l'aéroport, tuile de gare si
elle est dans le snapshot, sinon ville). Le facteur de calibration du revenu est
la médiane réalisé/prédit sur le revenu ; il reste vide tant que les entrées
n'ont pas les deux revenus. Le facteur passagers est celui qui recentrerait un
revenu proportionnel aux passagers, à tarif constant. Le résumé français dit
quelles entrées manquent. Contrats : `sweeps/test_analyse_air_demand_vs_realized.py`.
Pas de partie lancée pour remplir ces tableaux.

## V95 — requalification ciblée post-1973 (2026-09-26)

La suite n'a pas réouvert V93. La sonde passive `v95_air_post73_probe=1`
cherche à blanc un site pour les villes `<600` et les extensions actuellement
rejetées par `origin_served`, puis conserve séparément : production mensuelle
réelle de la ville, couverture du site en tuiles productrices, estimation de la
production captée, coût du site et économie C68. Le comportement par défaut
reste inchangé et le plancher de 600 reste actif.

Le diagnostic solo graines 42/100/999 × 6 ans montre une forte exposition mais
pas un gisement rentable évident. Sur 154 candidats `small`, le profit courant
médian vaut **16,6 k£/an**, contre **10,8 k£/an** quand l'extrémité nouvelle est
réévaluée par le bassin mesuré ; aucun ne dépasse 50 k£/an mesuré. Les seconds
slots Opex sont eux aussi nombreux (141 événements), mais passent de **23,9** à
**8,7 k£/an** de profit médian. Le coût de site est modeste (≈18–19 k£ en
médiane) : le verrou est la qualité de demande, pas le prix du terrain.

En duel passif contre AAAHogEx, V95 trouve **60 seconds slots concurrents** sur
3×6. Dix-neuf routes entières dépassent 50 k£/an avec la demande mesurée, mais
ce chiffre inclut le hub Opex existant. La contribution estimée du **nouveau
site** n'est que ≈**3,9 k£/an** en médiane et **0/60** satisfait simultanément
`measured_profit >= profit` et `measured_profit > hub_only_profit`. Le signal
territorial existe, mais il n'est donc pas équivalent à une bonne nouvelle ligne
économique.

Conclusion : **aucun 5×6 causal V95 n'est lancé**. Un futur filtre doit mesurer
la valeur résiduelle/marginale du nouveau site ou une valeur territoriale
explicite ; un simple seuil PASS/MAIL + coût + profit de route entière serait
trop permissif. Voir `docs/35_v95_air_post1973.md`.
