# FLEET-ARB — 5 novembre 2026

Branche de livraison : `codex/fleet-arbiter-20261105`. Base : `873b67ec`
(`origin/master` après fetch), avec la fusion ferroviaire et `rail_loop=1`,
`v257_demand=1` aux quatre difficultés. Aucun défaut existant modifié.
`fleet_arb` vaut **0** aux quatre difficultés ; le chargement unique est dans
`settings.nut`. L'arbre de travail utilisateur et `master` restent préservés.

Cette livraison est une **implémentation expérimentale**, pas une qualification
économique. Les contrats Python ne compilent pas Squirrel. Les parties et le
roundtrip moteur ci-dessous restent à exécuter sur le PC ; aucun résultat de
smoke, de gain économique ou de « zéro rame perdue » n'est revendiqué ici.

## Conception

`OpexFleetPropose(action)` reçoit `{line, mode, kind, cost,
marginalProfitYear, source}` ; les cinq types sont `add_vehicle`, `add_wagons`,
`sell`, `replace`, `refit`. `OpexFleetRequest` est uniquement l'adaptateur de
construction de cette table. Les réglages de capacité existants, notamment
`OpexRoadPhysicalVehicleCap` et `OpexAirCadenceCap`, restent des contraintes
physiques : ils ne constituent pas un second allocateur de crédits.

L'arbitre utilise des **autorisations réclamées par l'écrivain**. Le premier appel
met une proposition en file et retourne `false`. Au changement de mois, la
sélection donne des autorisations ; un prochain passage du même écrivain refait
son devis et consomme son autorisation. Lui seul exécute ensuite sa transaction
historique, avec ses ordres, métadonnées, validations et rollback. Aucun callback
Squirrel ne capture des variables locales ; aucun constructeur de véhicules
n'est réimplémenté dans l'arbitre. Une autorisation non consommée expire au mois
suivant. L'exposition devra donc mesurer séparément retenu, commencé et exécuté.

Le classement compare `profitA * coûtB` et `profitB * coûtA` en flottants pour
éviter le débordement entier. Une économie positive à coût nul passe avant les
achats ; à rendement égal, ordre FIFO. Les produits des ventes ne financent pas
par anticipation les achats. Le budget de sélection est la caisse disponible
(`OpexAvailableCapital`, sans emprunt implicite), moins **50 000 £**, moins les
réservations des transactions engagées. Les remplacements réservent le prix
**brut** de la nouvelle rame, pas le coût net après vente de l'ancienne.

Bornes : **64 propositions**, **8 autorisations par mois**, refus au-delà de
88 verrous actifs/récents (marge pour les identités de nouvelles lignes), et
contrôle coopératif de **12 000 opcodes** entre unités de travail. Un reliquat
de file est conservé quand ce contrôle est atteint. Le tri de 64 éléments,
la maintenance des verrous et une unité indivisible ont un dépassement borné :
12 000 n'est pas un plafond exact mesuré du coût total de la fonction. La
construction reste soumise aux budgets et phases de ses transactions natives.

Une ligne identifiée par `lineId` partage un seul verrou entre modes/écrivains.
Avant sa création, l'identité est la paire origine/destination/cargo, ou la paire
de villes du plan. `OpexFleetBorn` transmet la protection à l'identité publiée.
Le verrou dure **90 jours après la fin** et interdit aussi un nouveau passage
du même écrivain. Les journaux natifs en cours et les retraites en attente
empêchent une autre admission. Cela interdit notamment vendre après acheter et
raccourcir après allonger pendant la fenêtre ; ce n'est pas une interdiction
permanente de réviser une ligne devenue réellement déficitaire.

Les devis devenus plus chers, moins profitables ou dont la composition physique
a changé ne consomment pas l'autorisation précédente. La caisse est relue lors
de la consommation ; V257 et V284 la relisent encore avant la reconstruction.
Les chemins synchrones rendent leur résultat via `OpexFleetResult`. Pour les
transactions sans résultat synchrone, la fin du journal natif et une empreinte
physique bornée permettent le rapprochement mensuel, identifié par le motif
`native_transaction_finished`. Cette observation n'est pas une preuve autonome
de succès économique ou d'absence de perte ; elle doit être rapprochée du journal
du constructeur et des identités physiques au banc.

`OpexDecide("FLEET_ARB", ...)` distingue `proposed`, `retained`, `refused`
avec motif, `started`, `executed`, `failed`. Exemples de motifs : `budget`,
`action_limit`, `recent_action`, `transaction_busy`, `quote_changed`,
`grant_expired`, `cost_unknown`, `margin_unknown`, `nonpositive_margin`.
Activation du journal : `probes=258`, identique dans les deux bras du diagnostic.

## Persistance et OFF

Les deux sorties de `Save` ajoutent, uniquement ON, la version et des verrous
scalaires (source, type, échéance, mois, réservation brute, lineId). Aucun objet
API, callback, float, plan vivant ou référence de ligne n'est sérialisé par
l'arbitre. `Load` valide et borne le schéma. Files, autorisations et références
actives sont purgées ; les journaux transactionnels existants sont conservés par
leurs propres mécanismes. Une réservation restaurée reste bloquée tant que son
journal existe ; elle est libérée prudemment après réconciliation, avec une
nouvelle fenêtre de protection. Une ancienne sauvegarde sans état d'arbitrage
ne rejoue aucune proposition. Les rollbacks et récupérations ne redemandent
jamais une autorisation qui pourrait empêcher de remettre la rame en service.

`sweeps/fleet_arb_off.py` constitue la couche externe des projections historiques.
Ses substitutions littérales et SHA256 restaurent **les 33 sources existantes
modifiées**, octet pour octet, aux blobs Git de `873b67ec`. Les deux nouveaux
modules disparaissent de la projection OFF. Une insertion partiellement
modifiée ou une modification historique inexpliquée échoue. Les anciennes
fixtures et leurs SHA ne sont pas recalculés. Les lecteurs des contrats anciens
appliquent explicitement cette projection avant leurs propres transformations,
y compris les choix de témoins de fusion faits à l'import.

Inventaire actuel : **158 AddSetting**, contre 157 sur la base ; le plafond V251
est relevé de 75 à 76, tandis que son témoin historique projeté reste à 68.
Cette égalité de sources projetées est une preuve statique OFF ; elle ne prouve
pas l'égalité des trajectoires moteur à l'opcode près après ajout de branches.

## Carte des écrivains et conflits

Les quatre conflits initiaux sont le diagnostic fourni pour cette intervention :
V257 raccourcissant RAIL-LONG, protection particulière RAIL-FILL contre V257,
V284 contrariant le doublement fret, et INVEST-STALL 0/37 aboutissements.
Ils ne sont pas remesurés dans cette livraison et ne valent pas validation du
nouvel arbitre. Leur mécanisme commun est l'absence d'exclusion entre décisions
de flotte ; les protections existantes restent présentes.

| Famille | Entrée d'admission | Transaction conservée / conflit couvert |
|---|---|---|
| V257 | `_v257Review` | Remplacement complet et taille de rame ; réserve brute et exclusion des allongements récents |
| V284 / RAIL-FILL | `OpexV284Select` | `OpexV284Tick`, construction puis adoption ; partage du verrou avec V257 et doublement |
| INVEST-STALL | `OpexInvestStallFleetSelect` | Quais via RAIL-LONG v2, rame via V284 ; réservation jusqu'à disparition du journal |
| RAIL-LONG v2 flotte / v3 | Sélecteurs de flotte et d'upgrade | V284 / construction native multi-locomotives ; récupération intacte |
| RAIL-LOOP | `OpexRailLoopClone` | Clone d'une boucle certifiée ; infrastructure de conversion hors action de flotte |
| RAIL-PAIR, V233L, DOUBLE-GROW | Sélecteurs avant publication du pending / clone | Transactions et carnets natifs ; aucun nouveau constructeur |
| Rail initial, second train, upgrade | Builders après devis | `OpexBuildTrains` et variantes existantes |
| Route | `OpexBuildRoadRoute`, `OpexRoadRefleet` | Un véhicule par complément arbitré ; plafonds physiques conservés |
| Air | `OpexBuildAirRoute`, `OpexAirAddPlane`, crash et V252 | Cadence conservée ; marge du prochain avion, remplacement avant retraite |
| Eau | `OpexBuildWaterRoute`, crash | Transaction navire existante et rollback |
| Courrier / feeders / transfert routier | Entrées spécifiques | Proposition refusée si devis marginal complet indisponible ; pas de contournement physique |
| Ferraillage | `_triggerScrapLine` | Dépôt et ventes continuent sans réarbitrage ; fin/timeout libère la réservation |
| Retraites / rollback / Load | Journal parent | Ne sont pas de nouveaux choix de flotte ; leur nettoyage doit pouvoir aboutir |

L'inventaire exhaustif contient **100 sites**, y compris `BuildVehicleWithRefit`
et `MoveWagon` (attachement effectif dans ce dépôt), dans
`sweeps/fixtures/fleet_arb_writers_20261105.json`. Aucun appel autonome à
`AttachWagon`/`RefitVehicle` n'a été trouvé. Les appels sous `AITestMode` sont
distingués des mutations ; le test refuse tout nouveau site non recensé.
Les références fichier:ligne figurent dans l'annexe ci-dessous.

## Risques et limites à exposer

- Le rendement est une estimation. Les compléments rail utilisent un delta de
  capacité/demande avec coûts marginaux, l'air réutilise V161, V284/INVEST leurs
  estimateurs. Les consistes hétérogènes ou trop grandes sont refusées lorsque
  l'adaptateur ne peut pas les chiffrer ; aucun profit moyen de ligne n'est
  présenté comme profit marginal d'un véhicule supplémentaire.
- Certains chemins optionnels n'ont pas de devis marginal joint fiable :
  conversion DOUBLE-GROW v1/v2, allongement de quai RAIL-LONG v2 sans provenance
  INVEST-STALL, courrier enfant, transfert entre deux lignes et airport feeder.
  Ils passent par l'API mais sont **refusés explicitement** (coût/marge inconnu).
  Leur compatibilité fonctionnelle ON n'est donc pas revendiquée. Les reprises
  air/eau dont la ligne n'a pas de profit prévisionnel sont aussi refusées.
- La réserve brute est conservatrice et peut immobiliser trop de caisse pendant
  une transaction longue. Les contraintes de caisse natives restent des gardes
  de faisabilité, même lorsqu'elles sont plus strictes que les 50 000 £ communs.
- La revalidation peut invalider une autorisation chaque mois. Un écrivain dont
  la cadence est annuelle peut ne pas la consommer ; mesurer `grant_expired`
  avant d'interpréter une absence d'effet comme une neutralité économique.
- Le coût de sélection est borné structurellement et contrôlé en opcodes, mais
  pas mesuré ici. Les scans de devis restent dans les écrivains existants.
- Save/Load est couvert statiquement ; la reprise moteur pendant achat, adoption,
  rollback et retraite doit encore être exercée. Une purge d'intention ne doit
  jamais être comptée comme une construction exécutée.

## Plan pré-enregistré pour le PC

OpenTTD 15.3/API15, image et adversaire figés par `run_c66_reference.py`.
Depuis la branche publiée, vérifier Docker local, image `openttd-lab:latest`,
cache, montage, AAAHogEx-115 local et absence de campagne identique en cours.
Profil PC : **10 CPU, 8 Go RAM/swap, 10 workers**. Ne pas lancer ces commandes
contre un daemon VPS (profil 3/2g/3 requis sur celui-ci).

Préparer dans PowerShell (remplacer `python` par l'exécutable Python local si
nécessaire ; `rtk proxy` reste applicable sur ce poste) :

```powershell
$common = @('--image','openttd-lab:latest','--cpus','10','--memory','8g','--max-workers','10',
  '--primary-metric','profit_year','--min-useful-primary-delta-pct','4',
  '--value-guard-max-loss-pct','5','--repeats','1')
$railAAA = @('--aaahogex-setting','disable_veh_roadveh=1',
  '--aaahogex-setting','disable_veh_tram=1','--aaahogex-setting','disable_veh_ship=1',
  '--aaahogex-setting','disable_veh_aircraft=1')
$ref = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]'
$on = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,fleet_arb=1]'
```

1. **Smoke compilation 1×1**, deux duels appariés, aucune conclusion économique :

```powershell
python -X utf8 sweeps/run_c66_reference.py @common @railAAA --campaign fleet_arb_compile_20261105_r1 --reference $ref --variant $on --variant-policy-id fleet_arb --decision-rule gain_short --required-seeds 40 --required-years 5 --years 1 --seeds 42 --probes 258 --script-debug
```

2. **Smoke d'exposition 4×6**, graines fixées **17 512 314 8191**, huit duels :

```powershell
python -X utf8 sweeps/run_c66_reference.py @common @railAAA --campaign fleet_arb_exposure_4x6_20261105_r1 --reference $ref --variant $on --variant-policy-id fleet_arb --decision-rule gain_short --required-seeds 40 --required-years 5 --years 6 --seeds 17 512 314 8191 --probes 258 --script-debug --line-telemetry --retain-savegames results/fleet_arb_exposure_4x6_20261105_r1_saves
```

Le diagnostic 4×6 n'est pas une porte d'adoption. Exiger santé 8/8, horizon
complet, zéro erreur NoAI et, sur l'ensemble des quatre bras ON, au moins une
exécution confirmée de croissance et une décision concurrente refusée. Publier
par année/mode/source les nombres proposé, retenu, started, exécuté, échoué,
expiré et les refus de verrou. Un refus de verrou est un **conflit potentiel
évité**, pas une preuve que l'action refusée aurait effectivement détruit du
profit. Ne pas compter les répétitions de refus d'un même couple ligne/source
pendant une fenêtre comme autant de conflits distincts.

Critère matériel impératif : **0 rame perdue** par transaction arbitrée.
Rapprocher les identités ancien/nouveau, les logs natifs, l'adoption, les ordres,
le redémarrage et les sauvegardes ; conserver les crashes externes séparément.
Utiliser `physical_counters.py`, jamais `len(VEHS)`. Toute perte, transaction
orpheline ou exposition nulle arrête la progression ; pas de relance favorable.

Tester aussi un save/load avant sélection, après autorisation, en attente de
dépôt, après construction avant adoption, pendant rollback et après commit.
Réutiliser `sweeps/save_load_roundtrip.py` et ses contrôles moteur ; son scénario
doit exposer ces phases et activer effectivement `fleet_arb=1` (un roundtrip
générique sans transaction arbitrée n'est pas une validation de ce mécanisme).
Comparer verrous/réservations et identité des véhicules avant/après ; zéro
double achat, zéro double vente et aucune intention fantôme rejouée.

3. Après smoke sain et exposition établie, **A 40×5** (horizon demandé, différent
du 40×3 courant), séparément rail seul et multimodal. Pas de sonde de décision,
`probes=2` identique ; graines canoniques du harnais, aucune sélection a posteriori :

```powershell
python -X utf8 sweeps/run_c66_reference.py @common @railAAA --campaign fleet_arb_A_rail_40x5_20261105_r1 --reference $ref --variant $on --variant-policy-id fleet_arb --decision-rule gain_short --required-seeds 40 --required-years 5 --years 5 --probes 2
python -X utf8 sweeps/run_c66_reference.py @common --campaign fleet_arb_A_multi_40x5_20261105_r1 --reference 'OpexAI' --variant 'OpexAI[fleet_arb=1]' --variant-policy-id fleet_arb --decision-rule gain_short --required-seeds 40 --required-years 5 --years 5 --probes 2
```

Pour chaque strate : 40/40 paires, couverture et santé complètes, Wilcoxon exact
bilatéral p<0,05, IC95 bootstrap de la moyenne strictement positif en borne basse,
gain moyen ≥4 % du profit terminal de référence, garde de valeur −5 %.

4. Après A complet et `pass` de la strate correspondante, **B 20×10** sur PC,
sur autorisation explicite de ce banc long ; commandes préparées, non lancées :

```powershell
python -X utf8 sweeps/run_c66_reference.py @common @railAAA --campaign fleet_arb_B_rail_20x10_20261105_r1 --reference $ref --variant $on --variant-policy-id fleet_arb --decision-rule non_erosion --years 10 --probes 2
python -X utf8 sweeps/run_c66_reference.py @common --campaign fleet_arb_B_multi_20x10_20261105_r1 --reference 'OpexAI' --variant 'OpexAI[fleet_arb=1]' --variant-policy-id fleet_arb --decision-rule non_erosion --years 10 --probes 2
```

20/20 paires, couverture annuelle complète, borne haute IC95 bootstrap ≥0,
garde de valeur −5 %. Conserver les verdicts bruts, manifests/bundles, journaux
et deltas par graine. Budget prévu hors roundtrip : 2 parties de compilation,
8 d'exposition, 160 pour les deux A, puis 80 pour les deux B seulement si admises.
Le défaut reste 0 même après livraison ; aucune adoption n'est implicite.

## Validation hôte

La base a exécuté la suite complète avant modification : **3 867 tests,
89 échecs, 29 erreurs, 13 skips, 2 échecs attendus**. AAAHogEx-115 est absent
de cet arbre (les erreurs `test_v166` correspondantes sont attendues) ; les
autres échecs préexistants restent distincts, notamment contrats ESTIM et
artefacts expérimentaux absents. Le bilan final et la comparaison cas par cas
sont dans `evidence/review/fleet_arbiter_20261105/tests.json`.

Commande logique commune avant/après :
`python3 -X utf8 -m unittest discover -s sweeps -p 'test_*.py'`.
Sur cet hôte Windows, le même module est lancé avec le Python embarqué Codex,
`python3` n'étant pas sur PATH. Les contrats FLEET-ARB lisent les sources ON
réelles ; les contrats historiques retirent uniquement la couche FLEET-ARB.

Résultat final : **3 883 tests, 89 échecs, 29 erreurs**, mêmes 118 cas que
la base ; **aucune nouvelle défaillance**. Les 16 contrats FLEET-ARB passent.
Les 13 skips et 2 échecs attendus sont inchangés. La suite globale reste rouge
pour ses causes préexistantes ; elle n'est pas présentée comme entièrement verte.

## Annexe — sites physiques relus

Chemins relatifs à `ai/OpexAI/` ; lignes de cette livraison.

| Fichier:ligne(s) | Fonction | Admission / rôle |
|---|---|---|
| `air_construction.nut:371, 415, 419` | `OpexBuildAirRoute` | BUILD_AIR |
| `air_fleet.nut:146, 150, 153, 160, 163, 171, 180` | `OpexAirAddPlane` | AIR_FLEET |
| `air_fleet.nut:234, 239, 247, 250` | `OpexAirRefleetCrashedPlane` | AIR_CRASH |
| `air_recovery.nut:41, 50` | `OpexAirContinueRollback` | Cleanup of the parent transaction; never re-arbitrate cleanup |
| `airport_feeder.nut:374, 411, 414` | `OpexAirportFeederBuild` | AIRPORT_FEEDER |
| `airport_feeder_siting.nut:101, 105` | `OpexAirportFeederRecover` | Cleanup of the parent transaction; never re-arbitrate cleanup |
| `airport_rail_feeder_dispatch.nut:36` | `OpexAirportRailFeederRecover` | Cleanup of the parent transaction; never re-arbitrate cleanup |
| `builder_rail.nut:4556` | `OpexRollback` | Cleanup of the parent transaction; never re-arbitrate cleanup |
| `builder_rail.nut:4616` | `OpexV301Trim` | Cleanup of the parent transaction; never re-arbitrate cleanup |
| `builder_rail.nut:4666, 4676, 4706, 4724` | `OpexBuildTrains` | OpexExecuteRailPlan / OpexV190ExecuteRailPlan / OpexV198ExecuteRailPlan / OpexExecuteUpgradeAfterSearch / OpexBuildSecondTrain / V257 / V284 / RAIL_LONG_V3 / DOUBLE_CONVERSION (unknown quote refused) |
| `builder_rail.nut:6047` | `OpexV190RollbackDoubleTrack` | Cleanup of the parent transaction; never re-arbitrate cleanup |
| `builder_road.nut:4279, 4282` | `OpexRoadRollback` | Cleanup of the parent transaction; never re-arbitrate cleanup |
| `builder_road.nut:5372, 5535` | `OpexBuildRoadRoute` | BUILD_ROAD |
| `builder_road.nut:6493, 6504, 6544, 6548, 6556, 6557` | `OpexRoadRefleet` | ROAD_REFLEET |
| `builder_water.nut:493` | `OpexWaterRollback` | Cleanup of the parent transaction; never re-arbitrate cleanup |
| `builder_water.nut:629` | `OpexBuildWaterRoute` | BUILD_WATER |
| `builder_water.nut:686, 690, 693` | `OpexWaterRefleetCrashedShip` | WATER_CRASH |
| `bus_districts.nut:602, 625` | `OpexRoad1yBuildMailChild` | ROAD_MAIL_CHILD |
| `bus_districts.nut:917, 920, 937` | `OpexRoad1yWeakStep` | ROAD_WEAK_TRANSFER |
| `double_grow_fleet.nut:248, 269` | `OpexDoubleGrowFleet` | DOUBLE_GROW |
| `persist.nut:225, 240` | `OpexAI::_abortPersistedRailExpansion` | Cleanup of the parent transaction; never re-arbitrate cleanup |
| `persist.nut:297` | `OpexAI::_reconcileRailExpansionAfterLoad` | Cleanup of the parent transaction; never re-arbitrate cleanup |
| `rail_long_v3_multi.nut:188, 203, 217, 236, 249` | `OpexRailLongV3MultiBuild` | OpexBuildTrains: admitted parent construction or replacement |
| `rail_long_v3_upgrade.nut:128` | `OpexRailLongV3UpgradeRestoreOrders` | RAIL_LONG_V3: native recovery and depot dispatch |
| `rail_long_v3_upgrade.nut:435` | `OpexRailLongV3UpgradeAdopt` | RAIL_LONG_V3: native journal, sell only after verified adoption |
| `rail_loop.nut:497, 500` | `OpexRailLoopClone` | RAIL_LOOP |
| `rail_templates.nut:802, 807` | `OpexV198ExecuteRailPlan` | BUILD_RAIL |
| `task_rail.nut:588, 595, 603, 607` | `OpexRailLongGrowFleet` | RAIL_LONG_GROW |
| `task_rail.nut:818, 822` | `OpexAI::_expandRailLines` | RAIL_REFLEET |
| `task_rail.nut:909, 934, 981, 996, 1007, 1008` | `OpexAI::_continueRailExpansion` | Legacy persisted expansion only: no new assignment to _railExpansion in live sources |
| `task_rail_pair.nut:243` | `OpexAI::_v271TandemSource` | AITestMode quote; no physical mutation before admission |
| `task_rail_pair.nut:460, 635` | `OpexAI::_v271Continue` | RAIL_PAIR: admitted native transaction or rollback |
| `task_report.nut:677` | `OpexAI::_triggerScrapLine` | SCRAP_LINE |
| `task_report.nut:712` | `OpexAI::_scrapDeadLines` | SCRAP_LINE: admitted scrap journal |
| `task_report.nut:795, 860` | `OpexAI::_scrapRetiredVehicles` | V252 / V257 / V284: retirement after replacement or rollback ticket |
| `task_v252.nut:189, 197, 204, 228, 230` | `OpexAI::_dispatchV252AirEngineRefresh` | V252 |
| `task_v257.nut:170` | `OpexV257SaleValue` | AITestMode quote; no physical mutation before admission |
| `task_v257.nut:177` | `OpexV257Discard` | Cleanup of the parent transaction; never re-arbitrate cleanup |
| `task_v257.nut:461` | `OpexAI::_v257Review` | V257 |
| `task_v257.nut:488, 494, 643` | `OpexAI::_v257ReplaceStep` | V257: admitted replacement journal; live spend recheck |
| `task_v257.nut:698, 721` | `OpexV257Reconcile` | Cleanup of the parent transaction; never re-arbitrate cleanup |
| `task_v284.nut:558, 570` | `OpexV284Tick` | V284 / INVEST_STALL / RAIL_LONG_V2_FLEET: native journal; live spend recheck |
| `v233_long_good.nut:3207` | `OpexV233LGrowthStep` | V233L: admitted pending clone |
