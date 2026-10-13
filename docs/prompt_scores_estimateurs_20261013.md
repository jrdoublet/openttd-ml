# Prompt — trouver de meilleures modalités de calcul des scores (OpexAI)

*Rédigé le 13/10/2026 par Claude à la demande de l'utilisateur, à partir des seules informations déjà
mesurées. Les trous sont signalés « INFO NON DISPONIBLE » : ils n'ont pas été recherchés.*

---

## Ta mission

Tu travailles sur OpexAI, une IA OpenTTD (Squirrel, `ai/OpexAI/`) qui affronte AAAHogEx. Trouve de
**meilleures modalités de calcul des scores** : estimateurs de profit et de coût par mode et par
opération, puis règle de classement et de financement. Le juge final est le banc contre AAAHogEx
(`profit_year` à 3 ans, porte A 40×3 `gain_short`), pas la justesse d'un estimateur.

Livrables attendus :

1. Un diagnostic : pour chaque estimateur ci-dessous, ce qui est faux, pourquoi (mécanisme de jeu ou
   de code), et l'effet probable sur le **classement** (pas seulement sur la valeur absolue).
2. Trois à cinq propositions classées par gain attendu. Pour chacune :
   - l'hypothèse falsifiable ;
   - le changement de code, nommé par fonction ;
   - un réglage à défaut 0 ;
   - la mesure qui la confirmerait sur des journaux existants ;
   - le plan de banc pré-enregistrable (AGENTS.md §4.1 : contrats → smoke 1×1 → porte A 40×3 →
     porte B 20×10 `non_erosion`).
3. La liste de ce qu'il faudrait mesurer avant de décider, quand une information manque.

Interdits :

- Ne lance aucun banc Docker. Ne change aucun défaut. Ne commite pas sur `master`.
- Ne modifie pas le catalogue AIR (`air_catalog_c121.nut`, `air_economics_c121.nut` et voisins) :
  une refonte est en cours chez l'utilisateur. Tu peux le lire et proposer des changements, sans
  les appliquer.
- Ne repropose pas les pistes déjà réfutées (section 6).

## 1. La chaîne de décision actuelle

### 1.1 Score de financement, commun à tous les modes

```
fundScore = profitCalibré × 1000 / max(K_dec, capitalDeFinancement)
```

Code : `projects_selection.nut` (~l. 1240), `OpexProjectScore`.

**K_dec**, défini par C69 dans `OpexC69ComputeKDec` (`probes.nut`) :

- K_dec = F × τ.
- F est le flux de trésorerie d'exploitation par jour.
- τ = D / N, où D = min(365, jours depuis le début) et N = nombre de chantiers dans la fenêtre.
- Exemple : environ 60 k£ en janvier 1971 sur la graine 1.
- Sous K_dec, un rail à 40 k£ et un avion à 39 k£ sont comparés au profit absolu.

**Profit calibré**, calculé par `OpexC70Profit` (`projects_models.nut`) :

- Il vaut profit prédit × k_mode.
- k_mode = (Σ réalisé/prédit + 1) / (n + 1), sur les lignes d'âge ≥ 2 (`task_report.nut`,
  `OpexC70C82AccumulateLine`).
- Le réalisé est ramené au convoi initial et l'amortissement prédit en est retiré.
- C82, un facteur par moteur d'avion, est à défaut 0.

Exemptions de calibration :

- un profit observé (R2) ;
- un AIR qui porte déjà une réalisation C121 ≠ 1 ;
- un renfort C121, sauf sous V161.

**Calibration sur données de la partie : muette en 1970-71.** Vérifié le 13/10 dans les journaux :

- `C121_REALIZATION` vaut factor=1 pour tous les bras en 1970 et en 1971, faute de ligne mûre.
- En 1972, 1 à 2 lignes newpair par partie (facteur 0,62 à 0,82), aucun hub.
- Le premier facteur C70 tombe en janvier 1972.

Or **la caisse ne lie qu'en 1970-72** : elle est oisive dès 1973, avec une médiane de 0,5 M£ en 1973
et 5 M£ en 1977. Le classement se fait donc sur des modèles bruts exactement quand il compte.

**Capital de financement**, calculé par `OpexProjectFinanceCapital` (`projects_finance.nut`) =
`budgetCapital`, c'est-à-dire capital + marge du mode :

| Mode | Marge | Autre |
|---|---|---|
| AIR | 30 k£ pour 2 aéroports neufs, 12 k£ pour 1, 2 k£ pour 0 (`OpexAirRequiredMargin`) | |
| Rail | 0 | × `RAIL_FINANCE_BIAS_PCT` = 100 ; devis réel quand `capitalIsActual` |
| Route | 1 000 £ | × 121 % |
| Renfort | 1 000 £ | |
| Eau | `WATER_CAPITAL_MARGIN` | |

**Sélection.**

- Le portefeuille finance par fundScore décroissant sous `capitalBudget` = caisse − réserve.
- La réserve (`OpexCashReserve`) vaut un quart des coûts de fonctionnement annuels, bornée à
  [5 k ; 25 k], donc 25 k£ en 1971.
- L'emprunt restant n'est pas compté, mais l'emprunt est pris au maximum (300 k£) dès le 1/1/1970 :
  sans effet.
- Un projet qui ne rentre pas est sauté. Le suivant qui rentre est financé, même s'il est 5 fois
  moins bien classé (règle « ce qui rentre maintenant »).

### 1.2 Mesure du 13/10 : qui prend la caisse en 1971

Sources : `B6_PORTFOLIO` et sonde V165 ; campagnes `v149_diag5_5x3_20261013` et
`v165_probe_5x3_20261013` ; 5 graines (42, 1, 314, 12345, 8675309) ; 3 ans ; duel.

Scores médians au moment du choix en 1971 :

| Choisi | Score | Budget figé | Projets finançables |
|---|---|---|---|
| AIR | 1 346 à 1 606 | 74 à 77 k£ | 17 sur 45 |
| Rail | 283 à 325 | 52 à 55 k£ | 1 à 3 sur 83 à 121 |
| Renfort | 196 à 199 | 52 à 54 k£ | 1 sur 59 à 70 |

L'AIR est pris chaque fois qu'il rentre. Le rail et les renforts ne passent que quand un seul projet
rentre.

Chantiers non AIR de 1971 selon l'état du meilleur AIR du vivier au dernier choix (5 graines) :

| Bras | Hors AIR total | AIR bloqué par sa seule marge | AIR bloqué par marge + réserve | AIR hors de portée | Autres |
|---|---|---|---|---|---|
| master | 2,13 M£ | 14 chantiers, 0,55 M£ | 27 chantiers, 0,97 M£ | 11 chantiers | 5 |
| V149 (rail débloqué) | 2,48 M£ | 14 chantiers, 0,60 M£ | 27 chantiers, 1,14 M£ | 20 chantiers | 4 |

- Les renforts sont le premier poste. Au master en 1971, il y a 38 achats de renforts pour
  1,47 M£, contre 5,5 M£ d'AIR neuf.
- La marge en jeu vaut 30 k£ dans la grande majorité des cas (paire de deux aéroports neufs).
- Un avion coûtait 38 964 £ en 1970 (moteur 223). Une paire newpair avec 2 avions coûte
  ~125 k£ avant marge.

## 2. Estimateurs par mode et par opération, avec écarts constatés

Rappel : les résultats d'avant le 09/09 ne font plus foi. Les écarts ci-dessous datent tous du 12
ou du 13/10, sauf mention.

### 2.1 Rail — nouvelle ligne (fret et voyageurs)

Le modèle est `OpexLineEconomics` (`economy.nut`).

- **Transporté par mois** = min(production × `STATION_RATING_PCT`, trains × capacité × allers par mois).
  - `STATION_RATING_PCT` vaut 50 % fixe.
  - Cadence visée : `TARGET_HEADWAY_DAYS` = 7.
  - Au plus 2 trains (`MAX_RAIL_TRAINS`).
  - Le second train est évalué par `OpexRailSecondTrainMarginal`.
- **Revenu** = 12 × transporté × `AICargo.GetCargoIncome(cargo, distance, jours de trajet)`.
- **Exploitation** = trains × coût de la locomotive.
- **Amortissement** = prix des trains / durée de vie de la loco. L'infrastructure est amortie à 0 %
  (`INFRA_AMORT_PCT`).
- **Infrastructure** = distance × prix de la voie par tuile × `RAIL_TERRAIN_FACTOR`/100 (=100)
  + 2 × longueur de quai × prix de gare + dépôt.
  - Le dépôt n'est compté que sous `rail_depot_cost`, à défaut 0.
  - Avant l'A*, la distance est la distance Manhattan.
  - Ni le terrain, ni les ponts, ni le détour, ni les démolitions ne sont pricés.
- **Capital** = trains + infrastructure ; ROI = profit × 1000 / capital ; la variante retenue est
  celle au meilleur ROI.
- Après l'A*, le devis AITestMode remplace le capital (`OpexApplyRailActualCapital`), puis le coût
  réellement payé.
- Coût en opcodes : 1 070 itérations d'A* en moyenne par ligne posée en 1971. 45 lignes ont coûté
  80,7 M d'opcodes de recherche plus ~20 M de pose (diag V149 n°3).

Écarts mesurés, sur les lignes de 1971 (diags V149 n°3 à 5, 156 tentatives `RAIL_ATTEMPT`) :

- **Capital réel / modèle d'avant A*** :
  - médiane 1,08 au master et 1,11 sous V149 ; p90 1,25 ; max 1,50 ;
  - 1,06 sous 40 tuiles et 1,18 au-delà de 80.
  - Sur le seul terme « voie », l'écart est plus fort : la part infrastructure n'est pas isolée dans
    le journal.
- **Profit fret réalisé / prédit : 0,87** sur 89 lignes. Le réalisé est annualisé au prorata des
  jours d'exploitation, montée en charge comprise : c'est une borne basse.
  - ROI réalisé ~400 ‰ contre ~460 ‰ prédit.
- **Rail voyageurs : 0,17 à 0,26** du prédit (7 lignes), ROI réalisé ~60 ‰.
  - Sur 10 ans (master du 12/10, 20 parties), le rail voyageurs réalise ~2 k£/an par ligne contre
    21 à 26 k£ pour le fret.
- Cause avancée par le rapport du 12/10 : l'hypothèse d'un convoi unique rigide (1 train), alors
  qu'une mine de 180 à 250 t/mois remplit chaque passage.
- Fret par cargo (COAL, WOOD, IORE, GRAI…) : INFO NON DISPONIBLE.
- Justesse du second train (`OpexRailSecondTrainMarginal`) : INFO NON DISPONIBLE.
- Densification rail (V107) : INFO NON DISPONIBLE.
- Le fret n'est généré que pour UN cargo par régénération complète (`freightCargo`), soit environ
  1 par an.
- Comparaison avec AAAHogEx, en 1974 : rail fret AAA 745 k£ contre 89 k£ chez nous.

### 2.2 AIR — nouvelle ligne C121 (bras newpair, hubsite, hubhub)

Le modèle est `OpexC121AirEconomics` (`air_economics_c121.nut`).

**Trajet** (`OpexAirTripModel` / C121) :

- Le vol dure distance / (0,036 × vitesse) jours.
- On ajoute les manœuvres : roulage plafonné à 50 sur les deux tiers du demi-périmètre des deux
  aéroports, plus 300 ticks de montée et descente.

**Pour chaque taille de flotte N, de 1 au plafond de scan :**

- La cadence est N / aller-retour, bornée par la piste la plus saturée (jours de service de piste
  par type d'aéroport).
- La note de gare est simulée (`OpexC121RatingTarget` : vitesse + 33 + statue, attente, capacité par
  visite).
- La demande allouée à la gare tient compte de la concurrence, puis de la part de la ligne quand la
  gare est partagée.
- Transporté = min(offert, capacité × départs par mois), dans chaque sens, pour les passagers et le
  courrier.
  - Le courrier n'est compté que si la capacité courrier du moteur a été observée.
- Revenu = 12 × (transporté × `GetCargoIncome(distance Manhattan entre aéroports, jours physiques)`)
  × facteur de réalisation, moins la perte imposée aux lignes existantes du hub (cannibalisation).
  - Le facteur de réalisation ne vaut que pour les hubs : 0,75 + 0,25 × appris, ou ratio observé
    direct sous P0 (défaut 1).
- Exploitation = N × coût de l'avion + entretien des aéroports neufs.
- Amortissement = N × prix / durée de vie.
- Capital = aéroports neufs + N × prix. L'immobilisation est à 0.

**Choix de la flotte et du moteur.** La flotte retenue maximise profit/capital, sans K_dec. Le moteur
est choisi par argmax ; V96 (« moteur de la partie ») court-circuite le scan.

**Financement** = capital + marge (30, 12 ou 2 k£, voir 1.1).

Écarts mesurés :

- **Rapport du 12/10** (`docs/estime_realise_par_ligne_20261012.md`, 263 lignes mûres, première
  année pleine) : réalisé / estimé brut médian **0,463** et réalisé / estimé calibré C70 **0,712**.

  | Bras | Lignes | Réalisé / brut | Réalisé / calibré |
  |---|---|---|---|
  | newpair | 44 | 0,446 | 0,686 |
  | hubsite | 102 | 0,512 | 0,788 |
  | hubhub | 117 | 0,423 | 0,651 |

  Causes avancées :
  - délais de manœuvre et d'attente au hub (20 à 70 jours mesurés sur les aéroports chargés, soit
    40 à 60 % de rotations en moins) ;
  - remplissage dissymétrique passagers/courrier, avec des sièges occupés à 15-20 %.
- **Mesure du 13/10, lignes construites en 1971** (199 lignes à flotte inchangée, annualisées au
  prorata) :
  - réalisé / prédit brut **0,34 à 0,39** ;
  - ROI réalisé médian 514 à 619 ‰ contre 1 577 à 1 763 ‰ prédit.
  - Exemple, graine 1 : une ligne de 1970 prédite à 441 k£ réalise 239 k£ en 1972 (0,54).
- **Capital AIR** (mesure historique des marges, 03/10) :
  - réel / prévu médian 1,00, p90 1,15, max 1,74 ;
  - dépassement de marge dans 2,9 % des cas.
  - Le devis exact (V126) est précis (médiane −180 £).
- Comparaison avec AAAHogEx :
  - En 1974 : 48 k£ par avion chez AAA contre 15 k£ chez nous.
  - 89,5 % de nos véhicules sont des avions (7 par aéroport contre 1,4 chez AAA).
  - 99 % de notre capacité est passagers + courrier, contre 30 % de fret chez AAA.
- Justesse de la cannibalisation C121, mesurée isolément : INFO NON DISPONIBLE.
- Écart de capital ventilé par bras (hub contre paire neuve) : INFO NON DISPONIBLE.

### 2.3 AIR — renfort de flotte (refleet, +1 avion sur une ligne existante)

- **Modèle C121 marginal** : profit de la ligne à N+1 avions moins à N, avec la même machinerie
  qu'en 2.2.
- **Sous V161** (défaut 1 depuis le 13/10) : le profit est plafonné à
  13 000 − 2 600 × lignes voisines − amortissement, et l'exemption C70 est levée pour un renfort
  resté au modèle.
- Le capital vaut le prix de l'avion + 1 000 £.

Écarts :

- Exemple du 26/09/1970 : le modèle C121 prédisait 107 852 £/an pour un avion de plus, la règle V161
  11 052 £.
- Prévisions `FLEET_PROJECT` (avant V161) : 73 k£ (1972), 39 k£ (1973), 23 k£ (1974).
- Mesuré par régression (1971-79, 40 parties) : +9,6 k£/an sur la ligne et −1,8 k£/an par voisine,
  soit environ +3 k£/an net sur un hub plein. En 1971-72, la mesure n'est pas informative (±30 k).
- Rapport du 12/10 : réalisé ≈ 0,48 × brut.
- Porte A de V161 : +2,7 % (sous le seuil de 4 %), adopté par décision utilisateur.
- 🔴 **Décision utilisateur : les renforts ne doivent pas repasser devant les chantiers rail.**
  - Aujourd'hui ils sont dessous au score (196-199 contre 283-325 en 1971).
  - Ils restent pourtant le premier poste hors AIR en 1971 (règle « ce qui rentre », voir 1.2).

### 2.4 Route — bus et camions

- `economy.nut` ~l. 674-734 : infrastructure = distance × prix de la route par tuile + 2 × arrêt +
  dépôt.
  - La distance retenue est le maximum de la route trouvée et de la distance Manhattan.
- Financement × 121 % et marge de 1 000 £.
- Plafond physique connu comme grossier : 2 × min(arrêts) véhicules (C61).
- Revenu et exploitation détaillés : non relus, INFO NON DISPONIBLE ici.
- Écart réalisé / prédit : INFO NON DISPONIBLE (petits échantillons).
- Décision utilisateur du 07/10 : la route n'est qu'un rabattement vers gares et aéroports, pas de
  chantier route autonome.
- Chez AAA, 65 % des gares sont routières.

### 2.5 Eau, transformés, multi-cargo

- Eau : `OpexProjectFromWater` existe, marge `WATER_CAPITAL_MARGIN`. Écarts : INFO NON DISPONIBLE.
  C'est la phase 4 de la doctrine (bateaux quand on est riche).
- Cargo transformé (chaînes, V88) et trains multi-cargo (V163, à faire) : estimateurs absents ou non
  mesurés, INFO NON DISPONIBLE.
- Subventions : INFO NON DISPONIBLE.

### 2.6 Coût en opcodes

- Chaque projet porte `expectedOpcodes` et `opcodeScore`. Pour le rail : itérations bornées à
  `HARD_ITERATION_CAP` × 2 700 + transactions.
- Justesse de ces prédictions par mode : INFO NON DISPONIBLE, sauf les totaux rail cités en 2.1.

## 3. Pièges de mesure à respecter

- `PORTFOLIO_RANK` journalise le profit **brut**, pas le calibré.
- `LINE_REVENUE` compare le convoi initial prédit à la ligne entière réalisée : inutilisable pour
  comparer les modes.
- `RAIL_ATTEMPT` porte pre, model, quote, actual et ok/reason. Son champ `quote` contient en fait le
  coût réel final.
- Le réalisé de la première année est partiel. Annualiser, ou attendre l'âge 2 comme C70.
- **Bruit du duel : σ ≈ 290 k£ par graine.** Un 5×3 ne tranche rien : le même code V149 a donné
  +114 k£/an puis −113 k£/an à deux tirages.
- Les journaux de décision exigent `decision_log=1` dans les deux bras.

## 4. Ce qu'on sait de l'adversaire

- AAAHogEx change de dénominateur selon la ressource rare : profit par livre, par temps de chantier
  ou par véhicule. Nous divisons toujours par le capital.
- Tableau de bord à 3 ans :
  - valeur à 95 % d'AAA ;
  - profit à 67 % ;
  - note de gare −26 %, mais c'est un effet de composition, pas un levier.
- À 10 ans, l'écart est de ×4,65 ; 65 % viennent du rendement par véhicule.
- À 3 ans, il ne nous manque que du volume.

## 5. Pistes que la mesure ci-dessus suggère, sans les présumer

- Une calibration a priori pour 1970-71, pour tous les modes à la fois, qui cède la place aux
  facteurs de la partie dès qu'ils existent. Contrainte : ne pas faire repasser les renforts devant
  le rail.
- Une règle de financement qui tienne compte du temps d'attente du meilleur projet, au lieu de
  « ce qui rentre maintenant ». Sans réserver une caisse territoriale : variante rejetée, voir
  section 6.
- Des marges de financement cohérentes entre modes, fondées sur le risque mesuré du capital (AIR p90
  1,15 ; rail p90 1,25 ; avion = prix exact). Aujourd'hui, l'AIR paie 30 k£ fixes et le rail 0.
  Attention : l'apprentissage des ratios devis/réel (`capital_quote_learning`) a été rejeté le 09/10
  (section 6).
- Un dénominateur adapté à la ressource rare : capital en 1970-72, puis opcodes et véhicules.

## 6. Déjà réfuté ou rejeté : ne pas reproposer tel quel

- **« Territoire d'abord »** (`c121_territory_first`) : réserver la caisse du prochain aéroport et
  refuser les autres chantiers.
  - 40×3 : +0,91 % ; 40×5 : −1,45 %.
  - Rejeté et supprimé par l'utilisateur le 11/10.
- **`RAIL_TERRAIN_FACTOR`=170** (majorer le prix de la voie) : porte A échouée le 07/10.
- **V126**, capital AIR exact + marge 2 k£ : neutre (+23 k£/an, 07/10), sur un master sans rail
  concurrent.
- **Bonus fret dans le score** : annulé par l'utilisateur le 13/10.
- **Score rail `simple_roi` / `simple_opcode`** : rejetés définitivement le 11/10.
- **Revenus AIR appris** (`air_p0_learned_revenue`, ratio observé/prédit par époque de flotte) :
  40×5 −20,5 k£/an, rejet économique le 09/10. À distinguer de la réalisation directe des hubs
  (`air_p0_direct_realization`), adoptée le 10/10.
- **Apprentissage devis/réel du capital, tous modes** (`capital_quote_learning`) : porte A −106,8 k£/an,
  IC95 [−179 k ; −37 k], p=0,015, rejeté le 09/10 (`docs/capital_quote_p0_20261009.md`). Toute
  proposition de marges « au risque mesuré » doit dire en quoi elle diffère de celle-ci.
- **Temps physique de paiement C121** (`air_c121_physical_payment_days`) : +23,8 k£/an, `fail_primary`
  (09/10).
- **Invalidation exacte des productions en cache C121** (`c121_exact_prod_invalidation`) : +22,9 k£/an,
  `fail_primary` (09/10).
- **Seuils de filtrage rail 500 PAX / 200 fret, bonus de rotation, budget A*** : trois portes A
  `fail_primary` (09/10).
- **Hausse du nombre de candidats aériens** (V93 avant correction) : −15 % de valeur. Le plancher de
  600 habitants a ensuite été supprimé et qualifié autrement.
- **Fil rail « clos »** (03/10) : retoucher le score rail, les opcodes ou la réallocation du créneau
  A* n'a rien donné.
- **Réalisation projet et moteur C121 historiques** : retirées le 12/10 sur décision utilisateur.

## 7. Références

- Code : `economy.nut`, `air_economics_c121.nut`, `air_trip.nut`, `projects_builders.nut`,
  `projects_finance.nut`, `projects_models.nut`, `projects_selection.nut`, `capital.nut`,
  `task_report.nut`, `probes.nut`.
- Documents :
  - `docs/taches.md` (fiches V149, V161, V164, ligne « Estimé à l'élection / réalisé par ligne ») ;
  - `docs/estime_realise_par_ligne_20261012.md` ;
  - `docs/c121_territory_first_40x3_20261011.md`.
- Journaux (worktree `wt-v149-rail-unblock/results/`) :
  - `v149_diag{3,4,5}_5x3_20261013_engine` ;
  - `v165_probe_5x3_20261013_engine` (B6 avec meilleur AIR, caisse, réserve) ;
  - `v149_A40x3_20261013` (porte A V149, sans journaux de décision).
