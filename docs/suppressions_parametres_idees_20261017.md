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

## 7. V227 : C84, C85, V193, V194

| Réglage | Idée | Verdict |
|---|---|---|
| `c84_air_target_fleet` | Dimensionner une flotte cible par ligne AIR et scorer les renforts par le profit **marginal** have → have+n recalculé par le modèle (courbe non linéaire). | Réfuté (−69,6 k£/an). L'idée du score marginal vit dans C121 (`c121Marginal*`, `targetAirPlanes`). |
| `c85_air_equipment_frontier` | Frontière statique avion/équipement par aéroport (dominance prix, capacité, vitesse, portée) pour élaguer le choix. | Caduc depuis le moteur de la partie (V96). |
| `v193_chain_towns` | Génération V88 bornée : N villes les plus peuplées par paire source → usine, meilleure chaîne seule. | Rail seul 10×3 : −31,7 k£/an, valeur −7,8 %. Idée de réseau reprise en **V226** (araignée à la AAAHogEx). |
| `v194_short_to_served_dst` | Exempter du filtre de distance courte les lignes vers une destination déjà desservie par notre rail. | Nul (−17 k). Même reprise V226. |

20×10 contre master : −0,58 %, 9/11, p = 0,90, valeur +1,15 % : neutre.

## 8. V230 : apprentissage des devis, proximité rail en cache, fret rail court

| Réglage | Idée | Verdict |
|---|---|---|
| `capital_quote_learning` | Apprendre, par mode, famille et distance, le rapport devis/réel du capital (et du besoin révisé route) pour corriger la finance de décision. | Porte A 40×3 : −106,8 k£/an, 14/40, p = 0,015 (09/10). Les devis sont déjà exacts juste avant construction (A* rail en `AITestMode`, C121 en AIR) : l'apprentissage ajoutait du bruit. L'idée côté **profit** est reprise en V229 (C70 par mode × distance × cargo). |
| `rail_cached_proximity_gate` | Revalider les candidats rail du cache contre les deux rayons de `_tooClose` avant TOP_K, pour ne plus sélectionner des projets que le chantier refuserait. | Porte A 40×5 `fail_primary`. `_tooClose` reste le seul contrôle. |
| `v185_rail_short_freight_pct` | Facteur fixe sur le revenu prédit du fret rail < 100 tuiles (réalisé 0,50 pour 0,69 prédit). | Négatif (−44,7 k). Une correction apprise par cellule est préférable (V229). |

20×10 contre V227 : +0,22 %, 10/10, p = 0,87, valeur −0,61 % : neutre.

## 9. V231 : famille `rail_origin_reuse`, mémoire TRKFAIL fret, bus interurbains, P7, invalidation légère, lot AIR

Décision utilisateur du 17/10 : **tout supprimer plutôt que réparer**. Ces idées seront refaites plus tard avec un meilleur modèle et plus d'effort. Cette section garde donc le maximum de matière pour une réécriture **from scratch**. Commits : `df2f045` et `819b367` (moi), `c62bee0` (agy, `air_efficiency_*`), `39c0154` (grok, V92/V93.1). Smoke graine 42 : value 544 872, profit 573 573. Il diffère de master, sans doute par les opcodes du lot rail. Le lot AIR, lui, ne change rien au smoke. La fixture R1 passe en entier. 20×10 `v231_20x10_20261017` contre V230 : profit −82,8 k£/an (−2,28 %), 10/10, p = 0,29, IC95 [−220 k ; +51 k], valeur −1,72 % : **neutre**, fusionné le 17/10.

### 9.1 `rail_origin_reuse` et ses 11 sous-réglages (−3 900 lignes)

**Idée.** Le générateur rail exclut toute paire dont **une** extrémité est déjà servie par nous (`origin_served`, `candidates.nut`). On n'étend donc jamais le réseau à partir d'une gare existante. `rail_origin_reuse=1` relâchait cette exclusivité : une paire n'était rejetée que si **ses deux** extrémités étaient servies. Le chantier rejoignait alors la gare existante par un quai parallèle, au lieu d'en construire une à moins de `MIN_SEPARATION` (motif de rejet `too_close_no_join`, 600 à 750 par banc rail seul, premier motif de rejet).

**Mécanique retirée.** C'est utile pour une réécriture.
- **Contrat de compatibilité** `OpexRailOriginCompatibleService`. Le service existant doit avoir :
  - une seule gare logique (StationID unique) ;
  - un quai connu ;
  - le même genre (pax/fret) et le même cargo ;
  - en fret, le même rôle (A→A, B→B) : on ne transforme pas une destination en source.
  - `_multiline_match` testait toutes nos lignes de même StationID, pas seulement la première.
  - `_cross_cargo` autorisait un autre cargo sur la même gare fret, en ignorant le rôle.
- **Sous-familles** `_pax` et `_freight`, à 1, sous le parent.
- **`_fallback`.** Les extensions ne remplissaient le vivier que s'il restait sous TOP_K avec les seules origines libres. Le défaut diagnostique était l'égalité de priorité.
- **Évaluation différée** (`deferReuseAdmission`, `OpexRailOriginReuseFinalize`). Les extensions étaient évaluées après les candidats libres. `OpexRailSelectFreightReusePool` choisissait le pool fret. Les compteurs de pré-appariement étaient journalisés (`RAIL_PREPAIR`, `RAIL_ORIGIN_REUSE_FALLBACK`).
- **Priorité AIR.** `_air_priority_shadow` mesurait si une extension rail aurait déplacé le projet AIR finançable suivant. `_air_priority` l'appliquait (`OpexRailOriginReuseAirOpportunity` dans `_tryBuildProjects`).
- **`_search_cap_k`.** Plafond d'itérations A* propre aux extensions (`OpexRailCandidateHardCap`, 40 k).
- **`_search_supersede`.** Une extension pouvait remplacer une recherche A* en cours sur une paire moins bonne (`_maybeSupersedeRailSearchForOriginReuse`).
- **Ombres d'exposition** `rail_origin_exposure_shadow` et `_detail_shadow` : comptaient les paires que le relâchement aurait exposées, sans rien décider.
- **Ce qui reste.** Le comportement historique, c'est-à-dire l'exclusion dès qu'une extrémité est servie. Restent aussi la jointure de quai V88 (`OpexJoinPlatformPlans`, 4 tuiles latérales, plat strict) et la destination partagée **V178** (`strictOriginReuseJoin` ne dépend plus que de `V178_RAIL_SHARED_DEST` et de `candidate.shared_dest`).

**Mesures.**
- Rail seul 10×3 (`railseul_origin_reuse_10x3_20261014`) : +0,7 k£/an, 7/3, p = 0,56. 11 lignes jointes, 10 échecs `SITEAB` (quai parallèle introuvable).
- Avec V179 sur la base de l'époque (`reuse_railseul_10x3_20261014`) : −13,2 k£/an, 3/4/2.
- Contre la pile B (`reuse_railseul_10x3_20261015`) : −30,7 k£/an, médiane −40,6 k, 4/6, p = 0,32, IC95 [−84,9 ; +25,2] k. **147 lignes posées contre 144** : relâcher `origin_served` n'apporte pas de volume.
- Diagnostic agy du 14/10 sur 598 `too_close_no_join` du bras reuse : 51 % visent une **destination** déjà desservie, 42 % une source.

**Leçons pour la réécriture.**
1. Le goulot n'était pas l'offre de paires. Le vivier rail est vide en 1972-73 parce qu'il n'est régénéré qu'une fois par an (V217). Or la **pose** échoue : `SITEAB`, géométrie de quai joint trop stricte.
2. Côté destination, l'idée vit dans V178/V179, gardés. V178 fait +68 k£/an en rail seul, mais `fail_primary` en partie complète.
3. Le bon modèle est sans doute celui d'AAAHogEx : un hub et des rabattements en **transfert** (voir taches.md, 15/10). C'est la réutilisation d'origine à grande échelle, avec un tronc capable d'absorber le flux. Cela suppose double voie et multi-trains (V197-V201, horizon 10 ans), pas un simple relâchement du filtre. Voir V226 (réseau araignée).
4. Un réécrivain doit prévoir dès le départ un générateur de quai joint plus permissif (pentes, longueurs variables). V188, retiré au §6, testait les pentes.

### 9.2 `rail_freight_trkfail_memory`

**Idée.** Mémoriser les paires fret dont la pose échoue (`TRKFAIL`) pour ne pas les rechoisir. `task_rail.nut` ne bannit la paire que pour `ABND`/`SITE*`/`NOPA`/`STNFAIL`, pas pour `TRKFAIL`. `OpexRailTrackFailureIsPersistentPathLead` reconnaissait l'échec persistant au `lead` A*.

**Constat.** Graine 42 sous sondes : 29 échecs fret en 1974-75, sur **deux paires** seulement, 218 851 £ de tentatives sans ligne. Cause : `ERR_AREA_NOT_CLEAR` (err = 260, persistante, pas `ERR_VEHICLE_IN_THE_WAY`). Elle tombe à la tuile `lead` de la gare B, sur la **dernière** pièce posée. L'A* validait pourtant cette pièce en `AITestMode` : l'occupation apparaît entre la recherche et la pose. Hypothèses H1-H4 dans taches.md (ligne « C61 »).

Second défaut, géométrique, démontré par lecture : un pont ou un tunnel dont l'extrémité tombe sur le `lead` laisse la transition finale non posée.

**Mesure.**
- Prototype 1×6 : 31 → 5 `TRKFAIL` fret.
- Porte A 40×5 sans sondes : −7,9 k£/an, 5/11/24, p = 0,38. `fail_primary`.
- L'effet sur le moteur est réel, le gain économique nul. Les pertes sont concentrées sur peu de graines.

**Ce qui reste.** La garde géométrique `rail_geometry_guard` + `rail_geometry_pair_memory` (V100, intouchable) couvre le cas géométrique. `trackFailure` n'est plus rempli que sous `DECISION_LOG || RAIL_GEOMETRY_GUARD`.

**Réécriture.** Corriger la **cause** plutôt que mémoriser l'échec :
- revalider le tracé en `AITestMode` juste avant la pose (`OpexTestRailTrack` existe) ;
- ou poser la voie avant les gares ;
- ou refuser les franchissements collés à une sortie de gare (`startx`/`endx`).

### 9.3 Bus interurbains : `road_pax_build`, `road_pax_catchment_pct`, `road_stop_catchment_houses`

**Idée.** Lignes de bus passagers ville → ville (`OpexRoadPaxCandidates`) avec un bassin de captage par arrêt :
- `road_pax_catchment_pct=86` : part de la production de la ville captée par arrêt, mesurée le 30/08 (22 % historiques) ;
- `road_stop_catchment_houses=10` : plafond physique de maisons dans un rayon de 3 (`OpexTownBusCatchment`).

**Mesure.** Retest C121 du 03/10 (`resultats_retests_c121_nuit_20261004.md`) : `road_pax_build` 0→1 donne −60,4 k£/an (−4,22 %), IC95 [−100,9 ; −22,6], p = 0,014, valeur −2,66 %. Défaut 0 depuis, pour préserver la demande des aéroports : les bus siphonnent les mêmes villes.

**Décision du 07/10.** La route n'est qu'un rabattement vers les gares et aéroports (`route_pas_prioritaire`). AAAHogEx a 78 % de bus, mais en **transfert** vers ses gares (53 %).

**Ce qui reste.** Le fret routier, `road_pax_dwell_days` et les constantes de captage encore lues par l'économie.

**Réécriture.** Ne plus faire de bus autonomes. Les faire en **rabattement** (ordre de transfert vers une gare rail ou un aéroport à nous), et compter la demande prise à l'AIR.

### 9.4 `c76_lean_invalidation`

**Idée.** Sous `c76_regen_targeted=1`, éviter la reconstruction complète du vivier quand seuls le budget, une ligne ou une subvention changent : simple resélection ou invalidation de couche ciblée (`_c76PurgeInvalidCandidates`).

**Mesure.** Rejeté en duel 20×10 : −151 k£/an (`c76_c77_reliquat_audit_20261012.md`). Une partie du « coût » des reconstructions complètes est en fait **utile** : elles réexaminent le vivier avec la nouvelle caisse.

**Ce qui reste.** `_c76BumpLayer("lines", false)` sur les changements de lignes et de villes. `_portfolioInvalidated = true` sur une subvention périmée pendant un devis route. `budgetStale = stale`.

**Réécriture.** Distinguer ce qui change le **vivier** (nouvelles paires possibles) de ce qui ne change que la **sélection** (caisse). L'audit des reconstructions du 12/10 donne 72 % des opcodes à l'intention réactive `regen`.

### 9.5 `exp_scheduler_skip_not_due` (P7)

**Idée.** L'ordonnanceur sautait les tâches pas encore dues dans la même passe (`OpexExpSchedulerSkipReason`, `OpexExpSchedulerSelectTask`).

**Audit du 11/10.** Gain plafonné à un tick par saut. Environ 1 jour de jeu et 10 k opcodes sur 6 ans : indétectable. Le −17,2 k£/an du 5×6 du 30/09 était du bruit de duel.

**Ce qui reste.** Scan suffixe, puis file entière au cycle suivant. Ne pas rouvrir.

### 9.6 Lot AIR, agy : `air_efficiency_batch`, `_preflight`, `_dedupe`, `_reselect`

| Réglage | Idée | Mesure |
|---|---|---|
| `air_efficiency_batch` | Chapeau A/B combinant les trois suivants. | 5×6 : −97,9 k£/an, valeur −8,26 % (02/10). |
| `air_efficiency_preflight` | Pré-tester les deux extrémités d'un aéroport (`OpexAirPreflightEndpoint`) avant de payer le chantier. | 20×10 canonique : −89,3 k£/an, 4/14/2, p = 0,031, `fail_primary`. Le helper reste pour la sonde `air_bfail_precheck_shadow`. |
| `air_efficiency_dedupe` | Une seule entrée AIR par paire OD (`airPairBest`) dans la sélection. | Smoke : −43,9 k£/an, valeur −21 %. Plusieurs variantes d'une même paire laissent le choix au sac à dos. |
| `air_efficiency_reselect` | Resélection déclenchée par un seuil de caisse plutôt que la cadence du catalogue. | 5×6 : −94,8 k£/an, 1/4, valeur −8,07 %. « Interdit de réactivation » (taches.md, cadence des passes). |

Repli : `stale = gainOk && doubleOk`, `cadenceFresh = this._lastCatalogMonth == ym`.

### 9.7 Lot AIR, grok : `v92_air_service_choice`, `v93_air_demand_production`

- **V92.** Choisir un **service** AIR (moteur × nombre d'avions), plus une variante bon marché à un avion de la même route, avec rééquipement ultérieur (`v92PendingEngine`). Mesure : −570 k / −469 k£/an, 0/5, IC95 [−887 ; −254] k, valeur −42 %. Ce qui reste : mémo C80 → `OpexAirChooseRoutePlaneFull`, courrier forfaitaire 15 %, durée de vie 20 ans. Le moteur est quasi fixe par partie (V96, table moteurs C121) : choisir le service ne sert à rien.
- **V93.1.** Demande AIR tirée de la production pax du mois précédent (`AITown.GetLastMonthProduction`), moins la part concurrente, plafonnée par ligne, aux deux bouts. Mesure : 20×10 −421,5 k£/an, valeur −18,24 %. La demande reste le proxy population × `TOWN_CATCHMENT_SHARE_PCT` (plancher 10). **`v93_airport_no_pop_floor` (qualifié) est gardé.** Le paramètre positionnel `serviceScan` d'`OpexAirEconomics` reste, toujours faux.
- **Réécriture.** La demande mesurée sous-estime la demande induite par un nouvel aéroport, puisque la production suit le service. Si on la reprend, la mesurer **après** desserte, pour les renforts et non pour l'ouverture.

## 10. V232 : chaîne de biens V88 et lot AIR

Décision utilisateur du 17/10 : **supprimer V88 et repartir de zéro** (tâche V233, marquée « compliquée, ne pas confier à agy »). Commit `c862fd8` : 7 réglages, −1 900 lignes, dont 5 scripts Python V88.

### 10.1 `v88_goods_chain` et ses 6 sous-réglages

**Idée.** Construire une chaîne industrielle complète en deux étapes, notée comme **un seul projet** : (1) intrants (céréales, bétail, acier) → usine de transformation ; (2) biens → ville acceptatrice, au départ d'un quai joint à la gare de l'usine.
- **Verrou visé.** Une usine non alimentée a une production nulle, donc le générateur ordinaire ne propose jamais de ligne biens.
- **Estimation des biens.** Le volume aval était déduit du volume amont transporté (`OPEX_GOODS_CHAIN_OUTPUT_PER_INPUT = 1.0`).
- **Chiffrage du projet.** Capital, profit et ROI cumulés des deux étapes : `ratio = opcodeRatio + 15 × roi`.

**Mécanique retirée.**
- **Générateur.** `OpexGoodsChainCandidates` (`candidates.nut`) : pour chaque cargo à effet biens et chaque usine transformatrice non bloquée, chaque intrant accepté, chaque source libre productive et chaque ville acceptatrice libre dans la borne rail. Il appelait deux fois `OpexMakeCandidate`. Journal `CHAIN_GEN`.
- **Étape 1** (`task_rail.nut`, dans `_tryBuildRailProject`).
  - Refus `chain_in_progress` si une chaîne est déjà active.
  - `_tooClose` est testé sur l'étape 1.
  - Lancement de l'A* de l'étape 1 (`isChainStep1`, `chainParent`).
  - À la pose, `_setActiveGoodsChain({step = 2, factoryId, townId, inputLineId, factoryStationId, factoryPlatform, goodsCandidate, year})`.
- **Étape 2** (`_tryBuildGoodsChainStep2`).
  - Vérifie que l'usine et la ligne d'intrants existent toujours, puis pose `joinPlatform`, `joinStationId` et `joinLineId`.
  - Lance l'A* et construit.
  - Bannit la paire en cas d'échec, sauf `REPLAN_GEOM`.
  - Reprise en tête de passe dans `_tryBuildProjects`, et à la consommation de l'A* (`_consumeRailSearch`).
- **État persistant.** `_activeGoodsChain`, sauvegardé (`OpexSaveGoodsChain` / `OpexLoadGoodsChain`, sans flottants) et réconcilié au chargement (usine, ville, ligne, gare, locomotive). Les sauvegardes anciennes qui portent la clé `activeGoodsChain` sont simplement ignorées.
- **Sous-réglages.**
  - `v88_chain_force` : chaîne forcée en tête (palier +1000 dans l'insertion, exemption du plancher de profit).
  - `v88_step2_plan_immediate` : étape 2 construite dès que son tracé est prêt, même si le créneau A* est occupé.
  - `v88_all_inputs` : tous les intrants sans la rotation `freightCargo`.
  - `v88_chain_step1_finance` : `budgetCapital` = capital de l'étape 1 seule.
  - `v88_step2_rail_prio` : refus `chain_step2_prio` des autres projets rail, seuil de tranche V89 plafonné à 2 500 opcodes.
  - `v88_step2_cash_reserve` : capital de l'étape 2 réservé dans `OpexAvailableCapital`.
- **Clés.** Clé de projet `chain|…` (`projects_models.nut`), clé d'abandon par étape (`lines.nut`), destination `chain` dans la sonde de portefeuille, exclusion de la préparation A* C121, sonde V217 sur l'étape 1.
- **Ce qui reste.** La jointure de quai `OpexJoinPlatformPlans` et les champs `join*`, utilisés par **V178** (destination partagée). La branche « joindre A » de `OpexRailStationPlans` n'a plus d'appelant au défaut, mais elle est gardée parce qu'elle appartient au code V178. Le flag `isTransformer` du catalogue reste aussi, non utilisé.

**Mesures.**
- Solo 5×8, 25-26/09 ([27_v88_chaines_biens.md](27_v88_chaines_biens.md) §5.4-5.6) :
  - sans correctifs : 2 chaînes livrant sur 5 graines, décision → étape 2 en 2,37 ans ;
  - avec les 4 correctifs : 7 chaînes livrant, 5/5 graines, 1,85 an médian, premières livraisons 6,7 à 14,5 k£/an.
- Duels 5×6 du 26/09 (§5.7) :
  - 4 correctifs : −286,6 k£/an, 0/5, valeur −15,1 % ;
  - sans réserve ni priorité : −234,2 k ;
  - chaînes seules : −117,1 k.
  - Dans les trois cas, effondrement de l'AIR (graine 5678 : 109 → 31 avions).
- Rail seul 10×3 du 14/10 : −298,5 k£/an, 0/9, p = 0,004, valeur −60,8 %. 11 423 `CHAIN_GEN` sur la graine 42, 5 lignes par partie au lieu de 15.
- V193 (génération bornée, retiré en V227) : −31,7 k, nul ; seulement 8 lignes marchandises sur 10 parties.
- V218 (greffe sur une ligne existante, grok, non fusionné) : porte A −27,0 k£/an, 17/23.

**Défauts jamais corrigés** (lecture de code, 26/09 et 16/10).
1. Score gonflé sous `step1_finance` : profit des deux étapes ÷ capital de l'étape 1.
2. `_tryBuildGoodsChainStep2` rend `true` au simple lancement de l'A* : `builtCount` est faux et `k_pass` appliqué à tort.
3. Une passe `projects` qui lance un A* s'arrête et saute tous les projets suivants, AIR compris : AAA prend alors les places d'aéroport.

**Leçons pour la réécriture (V233).** Ne pas générer usine × ville × source. Valoriser l'aval comme une **option** dans le score des lignes vers transformateur. Greffer la ligne biens sur la production **mesurée**. Pas de verrou global, pas de réserve, pas d'arrêt de passe. Qualifier sur 6-10 ans en surveillant la flotte AIR.

### 10.2 Lot AIR, grok : devis de site V126 et réserve de ville (`a957f9c`)

| Réglage | Idée | Mesure | Ce qui reste |
|---|---|---|---|
| `air_site_cost_quote`, `air_site_cost_margin_pct`, `air_site_quote_keep_legacy_margin` | Ajouter au capital aéroport C121 le devis de terrassement et le coût des arrêts joints. Remplacer la marge de caisse historique (30 / 12 / 2 k£ selon 2 / 1 / 0 aéroports neufs) par 2 000 £ + `pct` × coût de site. `keep_legacy_margin` ne servait qu'à l'observateur de devis périmé. | V126 : porte A 40×3 `fail_primary`, −92,7 k£/an, 20/20 ; capital exact + marge 2 k£ ne paient pas (fiche V126). La caisse n'est pas le verrou. | Capital = prix catalogue × aéroports neufs ; marge historique. La sonde `probe_air_finance_margin` devise encore et journalise (cache 365 j, bouclier `AIAccounting`). `OpexAirStaleQuoteObserve` est retiré ; `air_site_stale_shadow` n'a plus d'observateur (à retirer en V239). |
| `air_batch_town_reserve` | Ne financer qu'un projet AIR par ville d'aéroport **neuf** dans un lot ; les plans écartés restent dans le vivier. | 5×6 du 24/09 : −179,9 k£/an. | `OpexAirBatchPlanStillLive` (rejet `batch_plan_dead`) et `OpexAirSlotTownId`. |

### 10.3 Lot AIR, agy : concurrence visible C121 et calibration par moteur C82 (`72528e9`)

| Réglage | Idée | Mesure | Ce qui reste |
|---|---|---|---|
| `c121_air_visible_competition` | Partager la demande d'extrémité avec les aéroports concurrents **observés** par tuile (`OpexC121VisibleAirportOwners`, cache catalogue 30 j au lieu de 365). Recalcul quotidien de la cible et de la marge des lignes vivantes (`OpexC121RefreshVisibleFleet`). Renforts plafonnés à `targetAirPlanes` et à la cible physique (garde `TARGET` dans `OpexAirAddPlane`). | Porte A 40×6 du 08/10 : −0,89 %. Il corrigeait le devis mais préservait les marges observées. V161 couvre le profit net de renfort. | Allocation par notes de gare (`OpexC121StationCompetitionBuckets`), cible initiale posée à la construction, croissance `first_live`. |
| `c121_air_visible_fused` | Une seule passe `0→cap` (`OpexC121VisibleFleetEconomics`, paramètre `marginalOut`) pour les points `have` et `have+1`. | Optimisation d'opcodes d'un parent rejeté. | — |
| `air_fleet_c121_preguard` | Sauter le recalcul visible tant que la ligne n'a pas d'année complète ou est en refroidissement de croissance. | Idem. | Gardes d'âge, de profit et de cadence de `_resizeAirFleets`. |
| `c82_engine_calibration` | Facteur réalisé/prédit **par moteur** (`(Σ ratios + 1) / (n + 1)`), publié au rapport annuel. Il remplaçait C70 dans `OpexCalibratedProfit` et choisissait l'avion par route sur le profit calibré (`OpexC82ChooseRoutePlane`). | Défaut 0 depuis C82 ; moteur quasi fixe par partie (V96) : rien à arbitrer. | Calibration par mode C70. **L'idée d'un apprentissage par cellule revient en V229** (mode × distance × cargo). |

### 10.4 Verdict V232

Les trois lots sont réunis sur `v232-rail` : 15 réglages, 226 → 211. Contrats sans nouvel échec, fixture R1 verte, smoke différent.
- **20×10 `v232_20x10_20261017` contre V231** : profit −41,0 k£/an (−1,16 %), 9/11, p = 0,62, IC95 [−201 k ; +133 k], valeur −0,83 % : **neutre**.
- **Cumul contre V230** : −123,8 k£/an (−3,42 %), 8/12, p = 0,23, IC95 [−275 k ; +24 k], valeur −2,54 %. Sous la garde de −5 %, mais **la dérive s'additionne lot après lot**.

## 11. V236 : 26 réglages numériques figés en constantes (17/10, moi)

Principe : aucun de ces réglages n'était un mécanisme à part entière ; ce sont des calibrations dont la valeur n'a pas bougé depuis leur qualification. La globale garde son nom et prend la valeur par défaut d'`info.nut` ; la lecture dans `settings.nut` et l'`AddSetting` disparaissent. **Smoke strictement identique à master** (graine 42, 1 an : valeur 421 646, profit 484 420, 19 véhicules, 20 gares) ⇒ fusion directe, sans 20×10. 211 → 185 réglages.

| Réglage | Constante | Valeur | Origine / remarque |
|---|---|---:|---|
| `pathfinder_sleep_ticks` | — (Sleep retiré) | 0 | Bridage pour parties avec humains ; à 0 depuis le principe « armes égales ». Le `Sleep` de `OpexAdvanceRailPathfinder` et de `OpexAdvanceSegmentedSearch` est supprimé, la garde `sleepTicks <= 0` du groupage V129 aussi. Pour une partie avec humains, il faudrait le réintroduire. |
| `rail_terrain_factor` | `RAIL_TERRAIN_FACTOR` (`economy.nut`) | 100 | Multiplicateur de coût de terrain du devis rail (voir `opexai_prix_rail_terrain`). |
| `rail_finance_bias_pct` | `RAIL_FINANCE_BIAS_PCT` | 100 | Biais du score rail C75bis ; 100 = neutre. |
| `v212_rail_pax_revenue_pct`, `v212_rail_pax_capital_pct` | `V212_RAIL_PAX_*_PCT` | 100 / 100 | Recalage pax rail V212, remis à 100 le 16/10 (perdant en partie complète). La branche `!= 100` d'`OpexLineEconomics` est maintenant morte : à retirer avec un futur lot (contrat `test_v212_pax_calibration` encore sur la garde). |
| `v214_rail_turn_cost`, `v214_rail_tight_turn_cost` | `V214_RAIL_*` | 300 / 1500 | Coût des virages AAA dans l'A*. ⚠️ globales passées de 0 à 300/1500 : c'était la valeur effective via `info.nut`. |
| `loan_repay_floor_k` | `LOAN_REPAY_FLOOR` (`globals_post.nut`) | 300 000 £ | Plancher de caisse avant remboursement. |
| `pathfinder_hard_cap_k` | `HARD_ITERATION_CAP` | 5 000 | ⚠️ globale passée de 10 000 à 5 000 (valeur effective). |
| `abandon_cooldown_days` | `ABANDON_COOLDOWN_DAYS` (`globals_post.nut`) | 365 | ⚠️ globale passée de 0 à 365. Mémoire d'abandon (G0). |
| `project_top_k` | `PROJECT_TOP_K` (`projects.nut`) | 64 | Fenêtre de sélection ; la variante dynamique part au lot V234 (tâche V241). |
| `air_early_slot_target_towns`, `_min_pop`, `_bonus_pct` | `AIR_EARLY_SLOT_*` | 6 / 1 000 / 50 | Paramètres du créneau aérien précoce (l'interrupteur `air_early_slot` part au lot V237). |
| `air_fleet_cadence_days` | `AIR_FLEET_CADENCE_DAYS` | 7 | Cadence de la tâche flotte AIR. |
| `v161_prior_own`, `v161_prior_neighbour` | `V161_PRIOR_*` | 13 000 / 2 600 | A priori du profit marginal par avion (V161). |
| `air_joined_stop_limit` | `AIR_JOINED_STOP_LIMIT` | 2 | Arrêts routiers joints à un aéroport. |
| `air_pax_revenue_calibration_pct` | `AIR_PAX_REVENUE_CALIBRATION_PCT` | 104 | Calibration du revenu pax AIR. |
| `air_hub_max_routes` | `AIR_HUB_MAX_ROUTES` | 3 | ⚠️ globale passée de 0 à 3. Plafond de routes par hub (C121, `36fa8c7`). |
| `unprofitable_streak_threshold` | `UNPROFITABLE_STREAK_THRESHOLD` | 3 | Années déficitaires avant vente. |
| `v91_astar_weight_pct` | `V91_ASTAR_WEIGHT_PCT` | 120 | A* pondéré V91. |
| `v172_rail_long_weight_pct`, `_dist` | `V172_RAIL_LONG_WEIGHT_*` | 200 / 100 | Pondération des longues lignes rail. |
| `v168_rail_max_dist` | `V168_RAIL_MAX_DIST` | 160 | Borne de distance rail (qualifiée le 13/10). |
| `c121_air_first_live_growth_phase_years` | `C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS` | 4 si `c121_air_first_live_growth`, 0 sinon | Durée de phase de la croissance « première vivante ». |

Lanceurs : `bench_v2.py` perd ses validations dédiées (un de ces noms passé en `OpexAI[...]` est désormais refusé comme « réglage OpexAI inconnu ») ; l'auto-test de `bench_1v1_5y_20seeds.py` vérifie l'absence d'`air_fleet_cadence_days`. Les scripts de diagnostic historiques (`diag_g0_abandon_factorial.py`, `run_g0_c66_4.py`, `run_m3_*`, `run_m4_conformity.py`, `diag_water_memory.py`, `diag_1v1_shared_monthly.py`) citent encore `abandon_cooldown_days` ou `air_early_slot_*` : ils ne sont plus rejouables tels quels. Contrats : 20 tests adaptés (`assertNotIn` + valeur de la globale) ; aucun nouvel échec.

## 12. V237 : 33 commutateurs AIR/catalogue adoptés figés (17/10, codex)

Principe : chaque réglage valait 1 aux quatre difficultés depuis son adoption ; le chemin ON devient le seul chemin et la branche OFF disparaît. Les modes entiers C117 (lean), V160, V161 et V158 sont figés à 1. Codex (commit d'origine `7a0183a`, rebasé sur V236 en `9e93a4b`), 133 fichiers dont 37 modules IA, 90 fichiers `sweeps/` et 6 fixtures `tests/mechanisms/`. 185 → 152 réglages (la base de codex était à 211 ; le rebase a réappliqué les retraits V236).

**Refus Save/Load** : `c121_air_project_realization_adaptive` reste, car `persist.nut::OpexC121StrategyStateEnabled` conditionne la sauvegarde de la stratégie avec lui. `persist.nut` est inchangé.

| Réglage(s) | Mécanisme conservé | Branche OFF retirée |
|---|---|---|
| `air_site_min_catchment`, `c96_air_site_catchment`, `v94_air_site_list` | Filtre production/acceptation voyageurs, recherche bornée du meilleur bassin (C96), scan `AITileList` (V94). | Chemin de site historique (déjà court-circuité par C96). |
| `c117_lean_sampling` | Échantillonnage lean hors sonde. | Mode 2 (double comptage) et `OpexC117NewC121View`, `OpexC117FlushLeanMonth`, `OpexC117CompareLeanSampling`. |
| `air_c121_physical_payment_days` | Durée physique aller + manœuvres pour le paiement. | Proxy distance + 30 j `OpexC119AirIncomeDays` et ses cinq replis. |
| `c121_air_game_engine`, `air0310_v96_shortcut_lean` | Moteur établi par type d'aéroport (V96), gardes de viabilité, scan de secours. | Rollback et score supérieur inutilisé du raccourci. |
| `c121_air_winner_fusion`, `c121_air_one_or_two_planes`, `air0310_one_two_fused` | Gagnant N=1/N=2 avec invariants communs, départ opposé du second avion. | Les deux évaluations complètes séparées, l'ancienne économie de profondeur libre, l'argument `fusion`, `OpexC121WinnerTariffEpoch`. |
| `c121_catalog_incremental`, `c121_catalog_air_first_year`, `c121_flat_bootstrap`, `c121_air_first_year_rail_prep` | Catalogue découpé, bootstrap plat (qualifié le 03/10), année AIR sous `MODE_AIR`, préparation rail sous `MODE_AIR && MODE_RAIL` (3 routes max, sans construire). | Catalogue monolithique, amorçage par étapes. |
| `c121_air_first_live_growth` | Admission anticipée 1→2 avions sur preuve vivante équilibrée. | — (la durée de phase est figée par V236). |
| `air_p0_direct_realization` | Ratios C121 matures directs. | Désactivation. |
| `air_route_plane_selection` | Choix d'avion compatible par route (repli si aucun catalogue compatible). | Avion unique historique. |
| `air_early_slot` | Priorité aux premiers créneaux des grandes villes. | — |
| `air_fleet_cooldown_prefilter`, `air_fleet_routes_index`, `v161_fleet_net_marginal` | Préfiltre de cadence, index partagé par passe, plafond net des voisines (V161). | Modes directs/comparateurs V160. |
| `c80_air_hub_index`, `c80_marginal_floor` | Index exact routes/paires, plancher marginal. | Scans sans index. |
| `air0310_incremental_publish`, `air0310_hub_snapshot`, `air0310_site_validity_cache`, `v141_catalog_incremental`, `v147_air_catalog_tasks`, `air_publish_lazy_select` | Publication incrémentale (qualifiée le 04/10), snapshots ordonnés, cache de validité, rafraîchissement en place, trois tâches AIR de file, sélection paresseuse. | Filtre local historique, reconversion systématique, sélection immédiate, dispatch monolithique. |
| `ac04_extra_site_dedup`, `ac05_skip_unused_hub_income`, `ac06_c76_snapshot_ack`, `ac04_hub_usage_gate` | Dédoublonnage physique, acquittement des seules révisions couvertes, validation des hubs au point d'usage. | Interface résiduelle d'AC05 (plus de consommateur). |

Lanceurs : les A/B devenus impossibles (moteur de partie, fusion, croissance « première vivante ») s'arrêtent explicitement ; le profil early-slot de `diag_1v1_shared_monthly.py` devient un commentaire. Contrats : `v237_contracts.py` et `test_v237_fixed_air.py` (six contrats transversaux) ajoutés.

**Verdict** : smoke valide, non identique (valeur 394 808, profit 453 973) ; fixture R1 complète OK. 20×10 `v237_20x10_20261017` contre V232 : profit +24,7 k£/an (+0,71 %), 11/9, p = 0,90, IC95 [−154 k ; +195 k], valeur +2,02 % : **neutre**. Cumul contre V230 : −99,1 k£/an (−2,73 %), 7/13, p = 0,29, IC95 [−252 k ; +49 k], valeur −0,58 %. Fusionné le 17/10.

## 13. V239 : 28 sondes, shadows et checkers (17/10, moi)

Principe : ces réglages ne changent aucune décision. Ils journalisent, rejouent en ombre ou vérifient un double calcul. Tous valaient 0 par défaut et n'étaient plus lus par aucun banc courant. Retirer leur code supprime 3 563 lignes `.nut` nettes (29 fichiers, après rebasage sur V237) et deux modules entiers : `air_flux_probe.nut` (C121 station flux) et `selection_diagnostics.nut` (`SELECTION_LIGHT`). Le groupe de sondes 256 (« vérifications en double calcul », V167) est désormais vide ; le bit reste réservé. 152 → 124 réglages.

Le smoke est valide mais **non identique** à master (graine 42, 1 an : valeur 542 509, profit 570 421, 22 véhicules, 22 gares). C'est attendu : le retrait des gardes `if (PROBE)` décale les opcodes. ⇒ 20×10 avant fusion.

**Verdict 20×10** (`v239_20x10_20261017`, `92d95ed`) : contre V237 profit +147,5 k£/an (+4,19 %), 8/12, p = 0,55, IC95 [−32,7 k ; +346,3 k] ; valeur +2,34 %, p = 0,55. Cumul contre V230 : profit +1,34 %, p = 0,65 ; valeur +1,75 %. ⇒ neutre, fusionné.

| Réglage | Ce qu'il mesurait | Ce qui a été retiré avec |
|---|---|---|
| `catalog_cost_probe` | Opcodes du rafraîchissement du catalogue et de la génération de projets (`PROJECTS_COST`, `AIR_LIGHT`, `CATALOG_COST_SLICE`, `SELECTION_LIGHT`). Avait montré le coût de 21 k opcodes du catalogue (fiche `catalogue_churn_et_cout`). | `OpexCatalogCostSliceLog`, `OpexAirLight*` (le paramètre `light` des signatures `OpexAirPlansStep*`/`HubDiscoveryPhase`), `selection_diagnostics.nut`, `OpexC121RailPrepLog` |
| `exp_opcode_exact_check` | Double calcul historique/exact des chemins `opcode_exact` (sites route, plan route, tri flotte AIR, couverture) avec journal des écarts. | Les cinq fonctions `*Gated` d'`opcode_exact.nut` réduites à leur retour rapide ; `EXP_OPCODE_EXACT_ON = EXP_OPCODE_EXACT` |
| `v90_pathfinder_check`, `v129_rail_astar_check` | Vérification pas à pas BaNaNaS ↔ V90, puis V90 ↔ V129 (sommet du tas, coût, priorité ; `V129_CHECK`). A garanti l'identité 20/20 de V129 (fiche `v129_astar_exact_adopte`). | Branches `else if (V90_PATHFINDER_CHECK)` / `V129_RAIL_ASTAR_CHECK` de `builder_rail.nut` ; les classes `OpexRailPathfinderCheckerV90`/`V129` restent dans `pathfinder_v90/` (bibliothèque, plus instanciées) |
| `v94_air_site_check` | Recherche de site d'aéroport historique et `AITileList` sur la même entrée, l'historique décidant (`V94_CHECK`). | Branche de comparaison d'`OpexAirFindSite` |
| `v141_catalog_incremental_check` | Sous `probe_events`, recalcul de `OpexProjectFromAir` sur l'AIR publié avec journal `V141_CHECK identical/diff`. | `OpexV141DecisionFieldDiff`, `OpexV141LogCheck` |
| `probe_c121_engine_table` | Table moteur hors ligne C121 (`analyse_c121_engine_table.py`) ; verdict : moteur quasi fixe par partie (fiche `table_moteurs_c121_verdict`). | `OpexEngTab*`, globales `C121_ENGTAB_*` |
| `probe_air_engine_depth` | Ombre : score du second à N=1 et N=2 avec le noyau fusionné (`AIR_ENGINE_DEPTH`). | `AirEngineDepth*`, `AIR_ENGINE_DEPTH_*` |
| `probe_air_finance_margin` | `AIR_FINANCE_TRY` aux contrôles de caisse AIR et premier revenu des lignes construites (V126). | `OpexAirFinanceMarginLogSelect`, `AIR_FINANCE_MARGIN_YEAR` ; les devis V126 restants sont ceux du chemin actif |
| `r19_fault_inject` | TEST : forcer le rollback de la Nᵉ nouvelle route AIR après mise en service (reprise R19). | Bloc R19 et `shield` d'`air_construction.nut`, `R19_FAULT_ROUTE_SEQ` |
| `rail_freight_select_shadow` | Caisse, plancher et sélection finale du fret rail. | Journal dédié |
| `v95_air_post73_probe` | Opportunités AIR post-1973 rejetées par plancher de population ou ville servie. A conduit à V93 (plancher supprimé, qualifié). | `OpexV95*` |
| `air_bfail_precheck_shadow` | Test de B avant de payer A pour les plans à deux aéroports neufs, comparé au réel. | Journal dédié |
| `air_site_stale_shadow` | Re-devis des sites AIR retenus avant caisse/construction. | Journal dédié |
| `c97_air_c69_engine_probe` | Argmax moteur × profondeur de flotte en P/max(capital, K_dec) ; ne pilote plus `C69_TRACK_BUILDS`. | Terme `|| C97_…` de `C69_TRACK_BUILDS` |
| `c98_air_realized_probe` | Profit/revenu prédit contre réalisé par avion, note et utilisation. | Journal dédié |
| `c116_air_project_probe` | Opportunité de déblocage de projet AIR/global/propre via le scan C115/C68. | `OpexC116*`, globales `C116_AIR_PROJECT_PROBE_*` |
| `c117_air_throughput_probe` | Débit AIR par fenêtres de 30 j (passagers livrés, sièges, cadence, attente). Le mode C117 lean reste. | Contexte de sonde des deux chemins de construction AIR |
| `c121_station_flux_probe` | Bilan des gares PASS (chargements, files, pertes, transferts). | Module `air_flux_probe.nut` |
| `c118_air_coverage_probe` | Couverture réelle des villes par les bassins AIR (`C118_COVERAGE`). | Journal dédié |
| `c121_air_economics_shadow`, `c121_air_engine_replay_shadow` | Ombre économique C121 (demande B9, volume, cycle, paiement C119) et rejeu moteur sur capacités observées. | `ReplayEngineChoice`, `keepLineDiagnostics`, champs `replay_*` du journal `C121_BUILD` |
| `c121_air_first_live_shadow`, `c121_kpass_shadow`, `c121_kdec_cold_shadow` | Cadence C121 : preuve vivante à 60/90 j, arrêts de passe K_pass avec regard en avant, rang K_dec contrefactuel. | `OpexC121FirstLiveAirOpportunity`, `OpexC121KPassShadow`, journal `C121_KDEC_COLD_FUNDED`, `FirstLiveLog` |
| `c121_air_pressure_probe` | Pression concurrentielle AIR sur les villes de créneau déjà inspectées. | Gardes repliées (`persist.nut` : l'état reste sauvegardé sous `C121_AIR_PROJECT_REALIZATION_ADAPTIVE` / C122, format inchangé) |
| `b9_air_catchment_probe`, `b9_air_demand_shadow` | Bassin et demande AIR avant construction (B9/G4). | Journaux dédiés |

Tests : 12 fichiers de contrats de sondes supprimés (`test_v95_air_post73_probe`, `test_c98_air_realized_probe`, `test_c97_air_c69_engine`, `test_air_rollback_net_probe`, `test_air_bfail_precheck_shadow`, `test_rail_freight_select_shadow`, `test_catalog_cost_probe`, `test_c121_station_flux_probe`, `test_c116_air_incremental_probe`, `test_air_finance_margin_probe`, `test_air0310_6_engine_depth`, `test_air_orphan_reuse_probe`) ; environ 95 méthodes de contrat qui ne lisaient que du code de sonde sont retirées, les autres sont adaptées (`assertNotIn`). Lanceurs : `,catalog_cost_probe=1` retiré des diagnostics de chronologie et de profil d'opcodes ; `r19_fault_inject` passe dans la liste des réglages retirés de `diag_three_lots_integration.py` / `diag_r1_r3_mechanisms.py`. Les autres lanceurs dédiés sont traités par V243.

Piège trouvé en route : après le retrait des déclarations, `settings.nut` lisait encore `EXP_OPCODE_EXACT_CHECK`, `C116_AIR_PROJECT_PROBE` et `C97_AIR_C69_ENGINE_PROBE`. En Squirrel, c'est une erreur d'exécution au chargement, invisible aux tests statiques. Un contrôle « identifiant MAJUSCULE utilisé mais plus déclaré », comparé à master, les a trouvés avant le smoke.

Rebasage sur V237 (fusionné entre-temps) : la résolution « intersection » automatique des conflits a produit des `local` en double, des accolades orphelines et des blocs `AddSetting` mal formés. Méthode retenue : prendre le côté master hunk par hunk, puis refaire les retraits V239 par script (blocs `if (SONDE)` morts, fonctions orphelines), reconstruire `info.nut` en retirant les blocs `AddSetting` entiers par expression régulière, et contrôler : identifiants MAJUSCULES non déclarés, fonctions orphelines, `local` retirés encore lus, accolades équilibrées et profondeur nulle à chaque `function`, suite de tests.
