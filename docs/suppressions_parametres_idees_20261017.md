# Paramètres supprimés et idées sous-jacentes (17/10/2026)

Mémoire des réglages retirés pendant la simplification (lot 1 du
[document de préparation](simplification_parametres_lot2_20261017.md), famille C99–C115).
Aucun ne changeait le défaut. Ils sont partis parce qu'ils étaient **OFF et sans effet**, pas
parce que toutes les idées étaient fausses. Pour retrouver le code : `git show <commit>~1:<fichier>`.

`c67_terrain_map` a été retiré (`7f77d63`), puis **réintégré** (`cb717da`) à la demande de
l'utilisateur. La carte par blocs `OpexTerrainMap` reste une brique de cartographie qui attend
un consommateur métier, par exemple la phase 4 bateaux ou V150.

## 1. Famille AIR C99–C114 : temps de vol physique et choix du moteur

Référence détaillée : [39_c100_c101_air_physical_engine_choice.md](39_c100_c101_air_physical_engine_choice.md).
Contexte : tout ce chemin n'était atteint qu'avec `c121_air_economics=0`. C121 est adopté
définitivement, donc ces branches n'étaient plus jamais exécutées.

| Réglage | Commit | Idée | Ce qu'on a appris |
|---|---|---|---|
| `c99_air_speed_api_fix` | `8601b86` | `AIEngine.GetMaxSpeed()` inclut déjà `plane_speed` ; l'ancien `/4` d'Opex était faux. | Correction physique juste. Le chemin conservé (`directSpeed`) en garde la logique. |
| `c100_air_trip_physical` | `e2c063d` | Temps de trajet = vitesse NoAI directe + roulage, piste et manœuvre verticale physiques. | Le **premier** C100, faux mais pessimiste (~26 j de manœuvre par sens), donnait ≈ +233 k£/an. La version corrigée C100.1 (~15 j) donnait −184 k£/an en 5×6. |
| `c101_air_physical_engine_choice` | `51cac45` | Classer les moteurs sous C100.1, mais rendre l'économie historique au portefeuille. | Smoke à −752 k£/an : on bascule vers des avions 2,6× plus chers en capital. Une version ROI relatif sur-corrige vers les petits appareils (−492 k). |
| `c103_air_c100_rank_replay` | `51cac45` | Rejouer **seulement** le classement moteur du premier C100. | Le mix 216/217 recherché est atteint, mais −390 k£/an. **Le gain venait du couplage classement + admission**, pas du seul argmax moteur. |
| `c105_air_replay_choice_physical_economics` | `51cac45` | Économie C100.1 partout, classement rejoué. | Variante intermédiaire, sans signal retenu. |
| `c106_air_marginal_physical_engine_choice` | `f671aac` | Choisir le moteur par **rendement marginal relatif** du capital en plus (sous C100.1), sans seuil de caisse. | Idée à garder en tête. C104 montre que passer de 217 à 218 coûte 2,9× le capital pour un rendement marginal ≈ 29 % du ROI de base. |
| `c108_air_onestep_physical_economics` | `f671aac` | C106 en une seule marche, économie C100.1 partout. | Pas adopté. |
| `c109_…`, `c112_air_speed_elasticity_*` | `8601b86` | Choix du moteur par **élasticité profit/vitesse** (seuils 0,5 et 0,75), sans constante de caisse ni EngineID. | Pas adopté. L'idée « la vitesse ne paie que si le temps fixe est faible » reste valable. |
| `c111_…`, `c113_air_c100_*_decision_shadow` | `4de6906` | Isolation causale : moteur rejoué C100, mais score et admission gardés sur un shadow C68. | Outils de diagnostic. Ils ont confirmé que l'effet passait par l'admission des routes. |
| `c114_air_c100_full_replay` | `8601b86` | Rejouer le vieux timing partout (moteur, admission, capital, flotte). | 20×10 à +195 k£/an mais `fail_primary` (12/8). **Gagnant sur les petits réseaux, perdant sur les réseaux mûrs.** |
| `c104_air_c100_compare_probe` | `ae41ea2` | Sonde passive : mêmes routes évaluées sous les trois modèles. | Change les opcodes ; 20×10 neutre (−0,08 %, 9/11, p = 0,87, valeur −0,75 %). |
| `c110_air_engine_calibration_choice_only` | `3d7c8ad` | Apprendre par moteur le rapport réalisé/prédit (C82) et ne s'en servir **que** pour choisir l'avion, sans toucher au score portefeuille. | Pas adopté. Smoke identique. L'idée « corriger le modèle par le réalisé, moteur par moteur » reste dans C82. |

**Idée centrale à retenir** : le vieux temps de manœuvre trop pessimiste agissait comme un
**régulariseur de capital**. Il freinait les gros avions pendant l'expansion, quand le capital
est rare, et devenait nuisible une fois le réseau mûr. C115 (« replay seulement si
`K_dec < capital_C68` ») a formalisé cette idée avec le goulot de capital C69, avant que C121
ne la remplace. Un futur choix de moteur devrait raisonner en **rendement marginal du capital
selon la rareté du capital**, pas en physique pure.

Encore en place : `OpexC104BestAirEngine` (partagé), `forcePhysicalTiming` /
`forceC100RankReplay` dans `air_trip.nut` et `air_route_economics.nut`.

## 2. Lot grok (`7f77d63`) : constantes mortes

| Constante | Idée | Verdict |
|---|---|---|
| `C55_FREIGHT_ORIGIN_RELAX` | C55 étape 2 : relâcher le verrou « une origine déjà servie » pour le fret routier. | Le filtre d'origine n'est pas le goulot : 86 % des rejets récupérés ne paient rien (banc 20×10 nul). Voir [plan_c55_road_pax.md](plan_c55_road_pax.md). |
| `PAX_NEAR` | Admettre les lignes pax ≤ 100 tuiles au profit prédit légèrement négatif, une tentative par an. | 20 graines : +10,5 % de gares (t = 4,27) mais valeur +0,6 % (t = 0,10). **Plus de volume, pas plus de valeur.** |
| `C53_ORDER_NOLOAD` | `OF_NO_LOAD` + déchargement au terminus des lignes de fret à sens unique, pour éviter d'attendre un rechargement au puits. | Effet physique mesuré (NoLoad 12,6 % route, 40 % rail), sans gain économique retenu. |

Refusés par grok et conservés : `C41_RAIL_LOST_*` (Save/Load) et `WATER_OPCODE_COMPAT_FALSE`
(calage d'opcodes).

## 3. Lot agy (`6e34a72`, sur master le 17/10)

20×10 contre master : +119,5 k£/an (+3,41 %), 13/7, Wilcoxon p = 0,033, IC95 [−18,9 k ; +244,8 k], valeur +1,78 %.

| Réglage | Idée | Pourquoi retiré |
|---|---|---|
| `c115_air_c100_capital_replay` | Voir §1 : rejouer C100 seulement quand le capital de décision `K_dec` est inférieur au capital du gagnant C68. Gain de +155 k£/an en 20×10, à 1 par décision utilisateur jusqu'à C121. | Les trois bras AIR et la revalidation passent par C121 au défaut. [Plan C115](air_c115_cleanup_plan_20261010.md). |
| `air_hubhub_marginal` | Hub→hub : déduire le revenu moyen déjà capté par le hub (revenu **marginal**, pas brut). | Court-circuité sous C121 + `ac05_skip_unused_hub_income`. L'idée de revenu marginal d'un hub partagé reste pertinente (congestion : modèle 0,99× à 1 avion, 0,53× à 3). |
| `c121_air_defensive_floor` | Plancher de profit défensif pour l'AIR dans la sélection du portefeuille. | OFF, et `PORTFOLIO_FLOOR_PCT=0`. |
| `OPEX_AIR_{CAP,PLAN,SITE,TOWN}_PAD` | Remplissages d'opcodes et mémorisation des sites et villes échoués, pour garder la trajectoire comparable entre bras. | Figés à `false`, sans réglage. |

## 4. Réglage `c121_air_economics` (`6420610`, repli `1460fed`)

C121 est le seul modèle économique AIR. Le réglage est retiré, puis la constante est repliée : chemin « ROI legacy » d'`OpexAirPlanBetter`, choix `OpexAirChooseRoutePlane` dans les trois bras, gardes `SHADOW && !C121`, sonde ABCD (`diag_c121_abcd.py`). Smoke non identique ; 20×10 contre master (référence `v222_air_20x10_20261017`) : −74 k£/an (−2,05 %), 7/13, Wilcoxon p = 0,28, IC95 [−207 k ; +63 k], valeur −1,61 % : neutre.

Suite (`e1d71b0`) : constante `C121_AIR_ECONOMICS` retirée, ainsi que la sonde `fleet_amort_shadow_probe` (`OpexFleetAmortShadow`, `OpexAmortProbe*`, adaptateur et tests Python). Idée : recalculer le profit d'un renfort de flotte AIR **net de l'amortissement des seuls avions ajoutés** (prix × n / durée de vie), pour voir si le classement du portefeuille changeait. Hors périmètre C84/C121, elle ne s'armait plus depuis l'adoption de C121. 20×10 contre le repli : +74 k£/an (+2,09 %), 9/11, p = 0,73, IC95 [−49 k ; +213 k], valeur +1,22 % : neutre. Si l'idée revient, l'implanter dans l'économie C121 (`OpexC121EngineEconomics`), pas en reconstruisant l'ancien chemin.

## 5. Lot 2B rail (V225 grok) : `v181_rail_max_trains`, `v192_rail_time_denom_pct`

| Réglage | Idée | Verdict |
|---|---|---|
| `v181_rail_max_trains` | Convertir une double voie en boucle à sens unique puis cloner jusqu'à N trains si l'attente source dépasse une rame. | Défaut 0, **inerte** (0 clonage, résultat identique au bit près). Plafond historique de 2 trains figé. `OpexConvertDoubleTrackToLoop` et `v181Loop` restent pour V190/V198. |
| `v192_rail_time_denom_pct` | Dénominateur rail du fundScore = capital × (1 + pct/100 × (distance/100)²), proxy du temps de chantier AAAHogEx. | Défaut 0, **nul confirmé** (10×3 bruit). Au défaut le dénominateur restait le capital : wrapper retiré. |

## 6. Lot 2B rail (V225 agy) : `v187_rail_refleet_during_search`, `v188_rail_join_slopes`

| Réglage | Idée | Verdict |
|---|---|---|
| `v187_rail_refleet_during_search` | Laisser doublement et renfort rail tourner pendant une recherche A* reprenable (doublement bloquant si `_railSearch` est occupé). | Rail seul 10×3 avec V188 : −126,7 k£/an, 3/7. |
| `v188_rail_join_slopes` | Accepter les pentes pour le quai joint parallèle (le `BuildRailStation` en mode test tranche, avec fondations). | Mesuré seulement avec V187. L'idée « plus de sites de quai joint » reste ouverte si le doublement redevient un levier. |

Lots V225 réunis (`8b87526`), 20×10 contre master : +0,40 %, 9/11, p = 0,90, valeur +0,55 % : neutre.
