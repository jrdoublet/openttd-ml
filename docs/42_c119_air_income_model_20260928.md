# C119 — audit du modèle de revenu AIR face à AAAHogEx

Date : 2026-09-28.

## Verdict

L'audit initial « temps + mail » était incomplet : il manquait une différence AAAHogEx décisive, la **distance de paiement**.

AAAHogEx sépare trois grandeurs que le modèle Opex historique mélangeait davantage :

- distance de paiement : en prébuild, `totalDistance = distance`, où `distance` est la distance Manhattan entre les extrémités ;
- temps de paiement : `cruiseDays`, calculé sur `pathDistance + 30` pour l'AIR ;
- cycle/débit : `2 * (cruiseDays + loadingTime)`, puis attente de station et flotte.

Le rerun descriptif C119 enrichi montre :

- `paymentDistance / flightDistance` : **1,240×** médian ;
- réel / yield prédit : **2,035× legacy → 1,426×** avec distance Manhattan + temps AAA-like ;
- cette correction retire environ **59 %** de l'excès de biais au-dessus de 1 ;
- revenu réel / revenu prédit : **1,383× → 0,979×** en médiane ;
- ajouter ensuite le mail moteur ne ferme pas davantage le gap : le résidu yield remonte à **1,471×**.

Un C119 minimal est donc implémenté derrière `c119_air_income_model=0` par défaut. Il modifie **uniquement les entrées de paiement AIR prébuild** ; cycle, débit, flotte, `monthlyPax`, B9, territorial, ordres et full-load restent inchangés.

Le causal 5×6 contre C115 est favorable mais non concluant : `profit_year` **+91,0 k£/an** moyen, médiane **+130,5 k£**, **4/1**, `p=0,375`; valeur **+5,10 %** en ratio des moyennes. C119 reste donc **désactivé par défaut** et aucun 20×10 n'est lancé automatiquement.

## 1. Comparaison exacte OpexAI / AAAHogEx

| Grandeur AIR | OpexAI C115 / historique | AAAHogEx-115 | Conséquence |
|---|---|---|---|
| Distance géométrique / cycle | `OpexFlightDistance = max(dx,dy)+0,414*min(dx,dy)` | `AirRoute.GetPathDistance` : même approximation | Géométrie proche pour le trajet physique. |
| Distance passée à `GetCargoIncome` | historiquement distance AIR diagonale | en prébuild `totalDistance = distance`, distance Manhattan | Différence C119 majeure : +24 % médian sur le corpus. |
| Distance de temps de vol | distance AIR + délai de manoeuvre Opex | `realPathDistance = pathDistance + 30`, +50 si breakdown | AAA encode approche/atterrissage comme distance équivalente. |
| Vitesse AIR | C115 rejoue la vitesse NoAI directe dans le chemin C100 concerné | `AIEngine.GetMaxSpeed(engine)` | Pas de division /4 supplémentaire à appliquer sous NoAI 15.3. |
| Temps passé à `GetCargoIncome` | historiquement `ceil(oneWayDays)`, donc incluant le délai aéroport | `cruiseDays + additionalCruiseDays` | AAA sépare paiement et cycle. |
| Cycle / débit | `roundTripDays = 2*oneWayDays` | `days = 2*(cruiseDays+loadingTime)` | Sémantique distincte du paiement. |
| Chargement | pas de terme cargo explicite dans le trip model | AIR 74 unités/j, mail AIR ralenti | AAA modélise explicitement le chargement. |
| Capacité pax | capacité/refit du moteur | capacité moteur/refit | Même principe. |
| Capacité mail | legacy 15 % ; V92 peut exploiter `plane.mailCapacity` | `GetMailSubcargoCapacity(engine)` via capacité véhicule réelle | Différence testée séparément. |
| Bidirectionnel | volume offert/capacité, sans « plein retour » explicite | AIR : capacité pleine aussi au retour | Hypothèse AAA très optimiste sur le corpus C119. |
| Production | `monthlyPax` du projet/catchment | production attendue AAA, puis rating | Variables non directement interchangeables. |
| Station rating | fonction Opex du headway | `GetStationRate(speed)+170` | AAA applique `production*stationRate/255`. |
| Débit maximal | cadence/capacité Opex | `30*engineCapacity/stationDateSpan` | Plafond aéroport explicite chez AAA. |
| Nombre d'avions | capacité/cycle + variantes Opex | `deliverableProduction*12*days/(365*capacity)+1`, borné | AAA dimensionne après production et débit max. |
| Running cost | flotte × running cost + infra | running cost × flotte + infra/dépréciation selon chemin | Grandeurs proches mais agrégation différente. |
| Revenu annuel | `12*carried*incomePerUnit` | revenu par rotation × rotations/an × flotte | Formulation différente. |
| Profit annuel | revenu − running − amortissement/infra | revenu − running − infra, avec logique propre de dépréciation | Pas strictement identique. |

Sources locales : `ai/OpexAI/builder_air.nut`, `ai/AAAHogEx-115/air.nut`, `estimator.nut`, `route.nut`, `utils.nut`.

## 2. Décomposition descriptive

Le rerun C119 enrichi compte **441 lignes matures**, dont **436** avec yield réalisé exploitable.

| Shadow | réel / yield prédit médian | réel / revenu prédit médian | gain yield prédit vs legacy |
|---|---:|---:|---:|
| legacy | **2,035×** | **1,383×** | base |
| temps AAA-like seul | **1,785×** | **1,206×** | **×1,137** |
| mail moteur seul | **2,098×** | **1,407×** | **×0,951** |
| temps + mail moteur | **1,837×** | **1,228×** | **×1,118** |
| distance Manhattan seule | **1,653×** | **1,121×** | **×1,240** |
| **distance + temps AAA-like** | **1,426×** | **0,979×** | **×1,415** |
| distance + temps + mail moteur | **1,471×** | — | moins bon que sans mail moteur |

Le point décisif est donc la **distance de paiement**, pas le mail. Distance + temps explique environ **59 %** de l'excès `2,035-1` et centre presque exactement le revenu médian.

Diagnostic non décisionnel : en injectant le mix mail réellement transporté, distance + temps laisse environ **1,14×** de résidu yield. Cela montre qu'une partie du reliquat vient de l'utilisation asymétrique du mail, mais cette information future ne peut pas être utilisée en prébuild.

## 3. Temps : paiement ≠ cycle physique

Sur les lignes matures :

- `actual_leg_days / pred_oneway_days` legacy : **0,671×** ;
- `actual_leg_days / aaa_income_days` : **2,415×** ;
- donc le temps AAA-like vaut ~**0,414×** du trajet physique réellement observé.

Le temps AAA-like n'est pas un meilleur prédicteur du **cycle physique** ; ce n'est pas son rôle. Il sert ici uniquement de durée de paiement pour `AICargo.GetCargoIncome`.

Smoke API Docker seed 42 :

- **88 requêtes / 88 lookups** ;
- **0 erreur** ;
- **0 mismatch** entre mini-NoAI OpenTTD 15.3 et replay Python pour vitesse, PASS/MAIL et temps.

Artefact : `results/c119_income_api_smoke_seed42_20260928.json`.

## 4. Mail : capacité moteur ≠ charge réalisée

Sur le rerun mature :

- capacité mail/pax moteur médiane : **0,111** ;
- mail réellement transporté / pax : **0,357** ;
- load factor pax médian : **0,314** ;
- load factor mail médian : **0,925**.

Le ratio réalisé ~0,35 vient donc surtout du fait que le mail sature alors que la cabine passagers est peu remplie. Il ne faut ni coder `mailPct=34` ni déduire le mix futur de la charge réalisée.

Remplacer le forfait legacy 15 % par la seule capacité mail moteur réduit ici le yield prédit d'environ 5 % en médiane ; C119 ne retient donc pas cette partie.

## 5. Hypothèses AAA : bidirectionnel, production/rating, capacité aéroport

### Plein dans les deux sens

Le service est bidirectionnel en fréquence : `min(tripsA,tripsB)/max` médian **0,889**.

Mais les charges passagers médianes ne sont que :

- sens A : **0,300** ;
- sens B : **0,292**.

Seulement **1 ligne sur 431** (**0,23 %**) dépasse 90 % de charge pax dans les deux sens. L'hypothèse AAA « cabine pleine au retour » est donc clairement optimiste sur ce corpus.

### Production × stationRate / 255

AAAHogEx applique bien :

`ratedProduction = production * stationRate / 255`

puis :

`deliverableProduction = min(ratedProduction, maxRouteCapacity)`.

Appliquer cette formule au `base_monthly` Opex n'est pas valide : ce n'est pas la même variable que `GetExpectedProduction` AAA. Hors bonus riche, le rated/base vaut ~**0,812×**, mais reste ~**6,5×** le `predCarried` Opex médian ; le pax réel ne représente qu'environ **0,09×** de ce volume.

Conclusion : le modèle de production AAA ne peut pas être transplanté sans reconstruire la même notion de production.

### Capacité aéroport / stationDateSpan

AAAHogEx prébuild borne le débit à :

`30 * engineCapacity / stationDateSpan`.

Sur une route existante, `GetStationDateSpan` multiplie aussi le span par le nombre de routes utilisant chaque extrémité.

Le rerun C119 journalise les spans bruts ; `headway / stationDateSpan` vaut **10,09×** en médiane. Le plafond aéroport n'est donc pas le goulot typique des lignes observées. C119 ne modifie pas la flotte.

## 6. Implémentation C119

Le réglage `c119_air_income_model` existe et reste **0 par défaut**.

Quand il est actif, dans l'économie AIR prébuild uniquement :

1. `incomeDistance = AIMap.DistanceManhattan(siteA, siteB)` ;
2. `incomeDays = (flightDistance + 30) * 664 / (AIEngine.GetMaxSpeed * 24 * dayLengthFactor)` ;
3. `OpexAirFarePerPax` reçoit ces deux grandeurs.

Le trip model reste calculé sur la distance AIR existante. Le cycle, le headway, `capacityPerPlane`, la flotte cible, le volume `carried`, la logique C115 et le portefeuille ne sont pas recalculés à partir de la distance Manhattan.

Le mail reste inchangé.

Aucune constante issue des cinq graines, aucun EngineID, aucun `mail=34 %`, aucun facteur global ×2 ni logique OpenGFX spécifique n'entre dans le chemin décisionnel. Le replay Python contient des constantes OpenGFX uniquement pour vérifier les appels API historiques.

## 7. Validation causale

Tests statiques ciblés C117/C119 : **26/26 OK**.

Smoke causal seed42 ×2 ans :

- `profit_year` : **+118,97 k£/an** ;
- valeur : **+162,6 k£**, soit **+15,14 %** ;
- le smoke est uniquement indicatif, n=1.

Causal 5×6, graines 42, 100, 999, 1234, 5678 :

- **5/5 paires complètes** ;
- `profit_year` : moyenne **+91,0 k£/an**, médiane **+130,5 k£** ;
- W/L : **4/1** ;
- sign-test `p=0,375` ;
- IC95 normale : **[-183,2 ; +365,3] k£/an** ;
- ratio des moyennes `profit_year` : **+6,38 %** ;
- valeur : moyenne **+285,8 k£**, **4/1**, ratio des moyennes **+5,10 %** ;
- véhicules primaires : **-1,0** en moyenne ;
- station rating médian : **-3,2 points** en moyenne ;
- évolution moyenne de l'écart de `profit_year` face à AAAHogEx : **+102,2 k£/an**, mais seulement **2/3** graines et forte variance.

Verdict 5×6 : **`diagnostic_only`**. Le signal était prometteur mais ne qualifiait pas une adoption.

Sur instruction ultérieure, C119 a ensuite été qualifié en **20×10** contre le même témoin C115, sur les 20 graines canoniques :

- **20/20 paires complètes** ;
- `profit_year` : moyenne **+70,9 k£/an**, médiane **+76,2 k£/an** ;
- W/L : **11/9**, sign-test **`p=0,823803`** ;
- IC95 normale : **[-51,3 ; +193,2] k£/an** ; IC95 Student : **[-59,6 ; +201,5] k£/an** ;
- ratio des moyennes `profit_year` : **+3,42 %** ;
- valeur : moyenne **+504,5 k£**, médiane **+304,3 k£**, **11/9**, ratio des moyennes **+4,45 %** ; le garde-fou valeur passe ;
- `profit` : moyenne **+26,4 k£**, médiane **+30,6 k£**, **12/8**, `p=0,503445` ;
- évolution de l'écart `profit_year` face à AAAHogEx : moyenne **+432,3 k£/an**, médiane **+578,3 k£/an**, **12/8**, `p=0,503445` ;
- `performance_history` : moyenne **-19,65**, **5/15**, `p=0,041389` ;
- véhicules primaires : **+4,5** en moyenne ; slots aéroport Opex : **-0,4** en moyenne ; villes avec aéroport Opex : **-0,15** en moyenne.

Verdict harnais 20×10 : **`fail_primary`**. Le delta moyen primaire dépasse bien le seuil utile de +50 k£/an (`primary_mean_pass=true`) et la valeur passe (`value_guard_pass=true`), mais le critère directionnel échoue (`sign_pass=false`, seulement 11/20 gains). C119 reste donc **désactivé par défaut**. La correction de paiement reste mécaniquement mieux fondée et peut servir de composant au futur modèle AIR unifié, mais elle n'est pas adoptée seule comme amélioration causale de C115.

## 8. Artefacts

- `sweeps/analyse_c119_air_income_shadow.py`
- `sweeps/report_c119_distance_shadow.py`
- `sweeps/test_c119_air_income_shadow.py`
- `sweeps/test_c119_air_income_model.py`
- `sweeps/run_c119_income_api_smoke.py`
- `sweeps/run_c119_air_income_smoke.py`
- `sweeps/run_c119_air_income_5x6.py`
- `results/c119_air_income_shadow_5x6_20260928_summary.json`
- `results/c119_distance_decomposition_20260928.json`
- `results/c119_income_api_smoke_seed42_20260928.json`
- `results/c119_air_income_smoke_seed42_20260928.json`
- `results/c119_air_income_vs_c115_5x6_20260928.json`
- `results/c119_air_income_vs_c115_20x10_20260928.json`

Aucun commit/push.
