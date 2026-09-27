# Tâches — réduire l'écart avec AAAHogEx

État courant actualisé le **2026-09-25**. Ce fichier est la **seule liste autoritaire du
travail restant**. Les travaux terminés, résultats et décisions sont dans les journaux ;
une ancienne mention « à faire » ne remet pas un chantier dans cette liste.

## État courant

Le défaut comprend C68, C69 bis/C70/C75 et, depuis le 2026-09-23, **C77 corrigé**
désormais actif en permanence ; ses trois anciens réglages ont été supprimés de `info.nut`/`settings.nut`.
Depuis le 2026-09-24, `c76_regen_targeted`, `town_growth_plan_memo` et `c80_mode_regen`
sont **qualifiés et actifs par défaut** ; `c80_air_hub_index` l'est également depuis le 2026-09-23.
Les travailleurs C80 (`c80_worker_rail`, `c80_worker_town`), C81 et C82 restent expérimentaux à défaut 0.
Depuis le 2026-09-26, les workers A\* à stock de tracés (`c80_rail_stock_gate`, `c80_rail_stock_worker`) et `homogeneous_preselect` sont implémentés, défaut 0, non adoptés (voir leurs lignes). Test connu en échec sur `master` : `test_c75bis_v89_railfactor` attend encore `v89_rail_search_throughput` à 0.
Depuis le 2026-09-24, `c83_preempt_open` et `air_batch_town_reserve` sont implémentés, défaut 0 ;
leurs 5×6 sont défavorables (préemption : profit neutre, valeur −8 % ; réserve : −180 k£/an, 0/5) et
aucun n'est retenu. Le script `sweeps/analyse_air_demand_vs_realized.py` compare le profit aérien prédit
au réalisé ; il ne change pas l'IA.
La version C76 retenue saute la régénération complète sans changement, avec filet annuel.
Les bancs C77 seul et C82 du 22 septembre sont terminés et non adoptés : ils ne sont plus
à lancer. Les feeders et Lakes sont retirés. C67.3 à C67.6 sont livrés, mais aucun consommateur
métier n'est encore exposé : ne pas présenter C67 comme « non implémenté ».

Le **2026-09-25**, le **correctif sonde** restaure la pureté stricte du chemin `probe_scheduler=0`
dans `task_rail.nut` et `task_projects.nut` (identité binaire exacte vérifiée contre `b34e5de` sur
graines 100 et 999 × 6 ans avec recherches rail, ainsi que smoke 42 1 an). Trois leviers sont
implémentés/préparés derrière des réglages expérimentaux dont le défaut reproduit strictement le
comportement actuel : le C75 bis retenu est désormais `c75_kpass_bypass` **défaut 1** ;
`v89_rail_search_throughput` est désormais **défaut 1** par décision utilisateur du 2026-09-26, car V88 en dépend ;
`rail_finance_bias_pct` est désormais adopté à **100** par décision utilisateur du 2026-09-26. Les sondes V95 restent observatoires.

Les preuves, limitations et décisions correspondantes sont dans les journaux des
[20 septembre](journaux/journal_2026-09-20.md), [21 septembre](journaux/journal_2026-09-21.md) et
[22 septembre](journaux/journal_2026-09-22.md). La [source historique intégrale transférée](journaux/journal_2026-09-22_transfert_historique.md)
conserve les comptes rendus auparavant empilés ici. Consulter aussi le
[journal du 13](journaux/journal_2026-09-13.md) et l'[archive du 9](archives/taches_archive_2026-09-09.md)
avant toute réouverture. Les résultats antérieurs au 9 septembre ne font pas preuve actuelle.

## Travail restant

**Numérotation (décision utilisateur du 2026-09-24).** Les chantiers ouverts depuis la session
du VPS sont préfixés **V** (V86, V88, V89…), ceux des autres sessions gardent **C** : deux
sessions parallèles ne peuvent plus prendre le même numéro. Le numéro suit la séquence commune ;
avant d'en prendre un, vérifier qu'aucun C ni V ne le porte déjà.

| Chantier | Statut | Prochaine étape / condition |
|---|---|---|
| **V88 — chaînes industrielles de biens (goods)** | **diagnostic solo 5×8 terminé ; seuil duel non atteint** | Chaîne complète intrant (ex. céréales, bétail, acier) vers usine de transformation (`isTransformer`), puis biens vers ville acceptatrice (`AICargo.TE_GOODS`). Diagnostic 5×8 du 2026-09-25 (`v88_goods_chain_solo_5x8_20260925`) : **5/5 parties saines, 4 chaînes choisies, 2 terminées et 2 avec livraison**, sur les graines **42 et 7** ; seuil d'accès au duel fixé à ≥3/5, donc **ne pas lancer le 5×6 causal tel quel**. Délais médians corrigés : recherche étape 1 **153 j**, étape 2 **300,5 j**, décision→étape 2 **863,5 j (2,37 ans)**, étape 2→livraison **295 j**. Huit attentes `step=2 reason=rail_search` restent visibles. L'analyseur `analyse_v88_chains.py` a été corrigé : il perdait une chaîne terminée lorsqu'une nouvelle `CHAIN_CHOSEN` arrivait avant sa première `CHAIN_DELIVERY`. Prochaine étape : retravailler l'exposition/sélection ou le verrou rail avant nouvelle qualification. [Fiche](27_v88_chaines_biens.md). |
| **C87 — bus de croissance urbaine au ROI ; lignes AAAHogEx** | **20×10 terminé ; économiquement neutre, défaut 1 conservé** | Garde-fou : profit prédit > 0 sur les arrêts réels, fermeture après 2 ans pleins en perte, ville mémorisée dans `_abandonedPairs`. Le 5×6 avait montré l'effet mécanique : bus −40 %, lignes en perte 5,6→3,4 par graine, `profit_year` −16 k£/an, valeur −0,76 %. Le **20×10 causal du 2026-09-25** (`c87_town_growth_roi_gate_vs_current_default_20x10_20260925`) confirme la neutralité économique : **−8,5 k£/an** en moyenne, médiane **+5,3 k£**, **10/10**, p=1,0, IC95 **[−132,1 ; +115,1] k£/an**, valeur **+0,86 %**, 20/20 paires complètes. Le verdict brut `fail_primary` vient du seuil +50 k£/an, non de la garde de valeur. Le réglage reste à **1 par défaut** selon la décision utilisateur du 2026-09-24 visant à éviter les bus déficitaires qui dégradent la note. Télémétrie : rail fret ≈ 570 k£/an chez AAAHogEx contre 15 k£ chez OpexAI ; avions courrier seul ≈ 13 % de son profit. [Fiche](26_c87_bus_et_lignes_aaa.md). |
| **C75 bis — caisse inutilisée 1970–1972** | **adopté par décision utilisateur ; défaut 1** | `c75_kpass_bypass` franchit `K_pass` **au plus une fois par passe**, uniquement pour une nouvelle ligne `air/rail/road/water` déjà finançable ; `fleet` est exclu et les contrôles cash/marge/revalidation/A* restent actifs. Mesures : 5×6 **+148,5 k£/an** (5/0) ; 20×10 r2 **+48,0 k£/an**, 14/6, p=0,115318, valeur +5,85 % ; 20×10 r3 **+24,9 k£/an**, 10/10, p=1,0, valeur −0,77 % ; 40×10 r4 **+52,5 k£/an**, 22/18, p=0,635828, valeur +2,63 %. Agrégat des **80 paires** : **+44,4 k£/an**, médiane **+70,5 k£**, **46/34**, p=**0,218518**, IC95 ≈ **[−25,9 ; +114,8] k£/an**, valeur **+2,48 %**. Le signal agrégé reste non significatif et sous le seuil C66.4 de +50 k£/an, mais l'utilisateur a explicitement décidé le **2026-09-25** de promouvoir le réglage : **`c75_kpass_bypass=1` par défaut**. [Fiche](33_caisse_1970_1972_et_leviers_aaa.md). |
| **V89 — débit de recherche rail opportuniste** | **adopté à défaut 1 comme dépendance de V88** | Diagnostic solo 3×6 du 2026-09-25 : **6 recherches terminées**, durée médiane **189,5 j**, 4 lignes mises en service. Le 5×6 causal était non favorable : **−62,0 k£/an**, 2/3, p=1,0, valeur +1,48 %. Le **20×10 du 2026-09-26** (`v89_rail_search_throughput_vs_0_20x10_20260926`) confirme l'absence de gain direct : **−7,0 k£/an**, médiane +23,1 k£, 11/9, p=0,8238, valeur −0,96 %. La note de performance baisse de **−12,25 points**, 4/16, p=0,0118. En revanche l'écart de profit face à AAAHogEx s'améliore de **+606 k£/an** en moyenne, principalement parce qu'AAAHogEx est lui-même freiné dans les duels V89. Malgré ce profil, l'utilisateur impose **défaut 1** car V88 nécessite ce débit rail. [Fiche](28_v89_debit_recherche_rail.md), [synthèse](33_caisse_1970_1972_et_leviers_aaa.md). |
| **V95 — AIR post-1973 : `<600` / seconds slots** | **diagnostic passif terminé ; pas de 5×6 causal** | Sonde `v95_air_post73_probe` défaut 0, aucun effet décisionnel. Solo 42/100/999 ×6 : **366 événements, 290 candidats shadow** ; petites villes : profit médian courant **16,6 k£/an**, mesuré **10,8 k£/an**, 0 cas mesuré ≥50 k£ ; seconds slots Opex : **23,9→8,7 k£/an**, 0 cas strict non-dégradé + incrémental. Duel passif 3×6 : **60 seconds slots concurrents**, mais contribution marginale du nouveau site ≈**3,9 k£/an** en médiane et **0/60** au critère strict. Ne pas réactiver V93 ni benchmarker les gates causaux V95 tant qu'une sonde n'isole pas la demande résiduelle / valeur territoriale du nouveau site. [Fiche](35_v95_air_post1973.md). |
| **AIR MAIL-only** | analyse terminée, non implémenté | AAAHogEx tire ≈267 k£/an de 4,8 lignes / 10 avions MAIL-only au 5×6. OpexAI connaît `mailCargo` et ajoute le mail comme supplément aux lignes PASS, mais `OpexAirPlans`, `OpexAirEconomics` et `OpexBuildAirRoute` restent passagers et refittent explicitement vers `paxCargo`. Prototype minimal : **MAIL-only entre aéroports Opex déjà existants**, demande MAIL réelle des bassins, avion refitté MAIL, mêmes deux ordres ; aucun nouvel aéroport dans le premier essai. Smoke puis 5×6 par cargo. [Synthèse](33_caisse_1970_1972_et_leviers_aaa.md). |
| **V90 — A* rail rapide vendorisé** | **défaut 1 (décision utilisateur du 2026-09-24) : équivalence parfaite, gain −8 %** | Réduction par au moins 2 du coût en opcodes d'une itération d'A* rail, à tracé et exploration strictement identiques. Copies vendorisées GPLv2 dans `ai/OpexAI/pathfinder_v90/` (`OpexBinaryHeapV90`, `OpexAyStarV90`, `OpexRailPathFinderV90`). Optimisations : ensemble fermé en table Squirrel native au lieu d'AIList, précalcul des constantes (taille de carte, offsets, coordonnées de buts), mémoïsation par recherche des requêtes invariantes de tuiles (`GetSlope`, `IsBuildable`, `IsCoastTile`, `IsBridgeTile`, `IsTunnelTile`, `HasTransportType`) et types de ponts par longueur. Réglage `v90_fast_pathfinder` (défaut 0) et mode de test parallèle pas à pas `v90_pathfinder_check` (défaut 0, traces `V90_CHECK`). **Mesure (2026-09-24)** : zéro écart sur ≈ 3 300 pas comparés ; 2 821 → 2 583 opcodes/itération (−8 %), car un appel API ne coûte presque rien en opcodes : le coût est dans la logique Squirrel (tas, `Path`, `_Cost`). Un gain ≥ ×2 exige de réduire le nombre d'itérations (heuristique pondérée), donc de changer le tracé. [Fiche](29_v90_pathfinder_rail.md) §9. |
| **V91 — heuristique pondérée A* rail (weighted A*)** | **poids 120 par défaut (décision utilisateur du 2026-09-24)** : recherches ÷ 5, coût A* +3,6 %, 20×10 neutre (médiane +28 k£/an, 11/9, p = 0,82, valeur −0,8 %) ; poids 150 rejeté (−40,8 k£/an, 7/13) | Réduction forte du nombre d'itérations d'exploration du pathfinder rail (levier direct pour accélérer les recherches par ≥ ×2). Multiplication de l'estimation admissible `_Estimate` par $w = \text{weight\_pct} / 100$ ($w \in [1{,}0 ; 3{,}0]$) dans `OpexRailPathFinderV90`. Réglage `v91_astar_weight_pct` (entier 100-300, pas 10, défaut 100 = V90 strictement inchangé, aucun surcoût d'opcodes au défaut grâce à la sélection de fonction au constructeur). Mode de test `v90_pathfinder_check` adapté (désactivation des alertes pas à pas, publication de la trace de fin `V90_CHECK name=finish_weighted` avec itérations, longueurs via `OpexSegmentTiles`, coûts et ratios). Instrumentation `RAIL_SEARCH_END` étendue sous `C56_TASK_TRACE` (résultat `found`/`none`/`cap`, longueur et poids). Protocole : smoke check 1×1 poids 150, mesure itérations/recherche et longueur des tracés à 100/150/200 sur graines 100/999/1234 × 8 ans avec `probe_events`+`probe_scheduler`, puis duel apparié 20×10 `run_c66_reference.py` contre le défaut (métrique `profit_year`, effet utile +50 k£/an, garde −5 %). [Fiche](30_v91_astar_pondere.md). |
| **C67 — carte par blocs** | **C67.3 à C67.6 livrés ; aucun consommateur métier exposé** | C67.3 : S=5 retenu provisoirement. C67.4 : service résumable dans le reliquat de tick sous 'c67_terrain_map=0', quasi neutre. C67.5 : graphe/oracle eau exact-ou-inconnu livré. C67.6 : sonde eau appelée 32 fois (6 paires) en 256², jamais en 512² ; côté rail, 16 lignes / 20 parties et capital pré-A* déjà à ~5 % du coût réel, donc aucun consommateur eau/rail suffisamment exposé pour être branché. Les services restent **non branchés aux décisions économiques**. [Contrat](c67_cartographie_contrat.md), journaux du [23](journaux/journal_2026-09-23.md) et du [24](journaux/journal_2026-09-24.md). |
| **Facteur rail (biasPct)** | **adopté à `rail_finance_bias_pct=100` par décision utilisateur du 2026-09-26** | `candidate.capital` inclut déjà `RAIL_TERRAIN_FACTOR=170` sur la voie ; l'ancien défaut ajoutait encore `biasPct=170` dans `OpexProjectFinanceCapital`. C67.6 mesurait un coût réel ≈0,96× `candidate.capital`. Le 5×6 du 2026-09-25 était fortement positif : **+199,5 k£/an**, 5/0, valeur +12,6 %. Le **20×10 causal du 2026-09-26** (`rail_finance_bias100_vs_170_20x10_20260926`) donne **+47,3 k£/an** en moyenne, médiane **+115,3 k£**, **12/8**, p=0,503445, IC95 **[−130,7 ; +225,2] k£/an**, valeur **−1,87 %**, 20/20 paires ; verdict automatique `fail_primary` car non significatif et juste sous +50 k£/an. L'utilisateur choisit néanmoins l'adoption : **défaut 100**. [Contrat C67 §20](c67_cartographie_contrat.md). |
| **C67 — lecture de bloc par Valuate** | À mesurer (fixture, sans partie longue) | Comparer le lecteur tuile-par-tuile actuel à AITileList.AddRectangle + Valuate sur blocs 5×5 et 10×10 : opcodes, exactitude des résumés et borne non suspendable. Remplacer _readOne seulement si le gain est net ; ne jamais lancer un Valuate sur une carte entière. |
| **C78 — occasions présentes chez AAAHogEx, absentes chez OpexAI** | C78.3/C78.4 validés ; C83.1 qualifié | **C78.3/C78.4** restent validés. Le défaut C83.1 résiduel était sémantique : le watcher confondait une ligne AIR commerciale proche avec un aéroport occupant physiquement le slot, et la génération ciblée ne garantissait pas `ClosestTown(anchor)==ville cible`. Correction du 2026-09-24 : état Opex par aéroports physiques, constante C83 distincte, site ciblé contraint au TownID du slot et télémétrie `c83_slot_claimed/lost`. L'ablation 24 villes n'est pas retenue ; le défaut final reste **6 villes**. Son 20×10 donne **+165,3 k£/an**, 15/5, p=0,0414, valeur **+6,78 %** et fait tomber les monopoles AAA fin 1979 **215→178**. [Fiche](22_c78_lignes_vs_aaa.md) §10. |
| **C83 — empêcher les monopoles aériens d'AAAHogEx** | **C83.1 qualifié (6 villes) ; `c83_fixes`, `c83_preempt_open` et `air_batch_town_reserve` à défaut 0** | Le 20×10 du défaut 6 villes reste qualifié : **+165,3 k£/an**, 15/5, p=0,0414, valeur **+6,78 %**, monopoles AAA fin 1979 **215→178**. Les correctifs de revue restent sous **`c83_fixes` défaut 0**. **`c83_preempt_open`** (défaut 0) garde une seule grande ville encore vide (`GetAllowedNoise()==2`) et lui donne la priorité défensive devant hub→hub, sans sauter le test de profit. **`air_batch_town_reserve`** (défaut 0) ne finance qu'un projet aérien par ville de nouvel aéroport ; les autres restent dans le vivier. **5×6 du 24 :** `c83_preempt_open` −4 k£/an, 3/2, valeur **−8 %** (garde violée) → non retenu ; `air_batch_town_reserve` **−180 k£/an, 0/5**, IC95 entièrement négatif, valeur −6 % → rejeté (réserve appliquée après la sélection sous budget, capital libéré perdu). **C83.2 non retenu.** [Fiche](22_c78_lignes_vs_aaa.md) §11–§13. **`c83_fixes` (défaut 0) non adopté** : 20×10 du 2026-09-24 `fail_primary`, −28,8 k£/an, 10/10, p=1,0, IC95 [−158 ; +100] k, valeur +1,78 % ; créneaux Opex −2,1, villes Opex −1,95, véhicules −13 %, déficit croissant à partir de 1972. Correctif de portée (2026-09-25) : la contrainte `OpexAirSlotTownId` ne vaut plus que pour les sites de course C83 (`c83SlotTown`), plus pour la recherche AIR ordinaire. 5×6 (`c83_slotscope_vs_default_6y_5seeds_20260924b`) : −30 k£/an, 1/4, créneaux −1,4, villes −1,2 : la contrainte globale n'explique pas seule le recul. **Prochaine étape : ne plus mesurer `c83_fixes` en bloc. Le scinder en sous-réglages causaux et tester séparément les corrections de revue. Priorité au watcher `OpexAirC83WatchTowns` : le défaut C83.1 qualifié surveille les 6 plus grandes villes avec `AIR_EARLY_SLOT_MIN_POP=1000`, alors que `c83_fixes=1` passe à 6 villes contestables dès `OpexAirLargeAirportMinPop()=600` ; mesurer isolément ce changement 1000→600 / top-6→contestables avant de conserver ou rejeter les autres correctifs (réarmement/coalescence, identité physique du slot, élimination des paires mortes, scan ciblé).** |
| **C80 — ordonnanceur** | **Pile complète mesurée ; C80-6 non atteint** | Socle, travailleurs rail/ville, tranches 4-5, pistes C76 1-5 (`c76_lean_invalidation`, horloge C39.6 complète) intégrés. **`c80_air_hub_index` passé à 1 par défaut (décision utilisateur du 2026-09-23)** : décisions exactes, −32 % d'opcodes hub→hub, réservés pour C67 ; 20×10 neutre (−16 k£/an 9/11, valeur +1,3 % ; [nuit du 23](journaux/23_nuit_2026-09-23.md) §9). **Validé par l'utilisateur le 2026-09-24.** Neutralité confirmée par le 40×10 `mean40` du 24 (+11 k£/an, 20/20, IC95 [−67 ; +90], valeur +1,9 % ; [nuit du 24](journaux/24_nuit_2026-09-24.md) §3). Non retenus : `c76_freight_rotation` (20×10 : −59 k£/an 9/11), `c76_lean_invalidation` (20×10 sur le nouveau défaut, avec C76 : 4/16, p = 0,0118, IC95 négatif, garde de valeur dépassée ; [nuit du 23](journaux/23_nuit_2026-09-23.md) §6), `c80_air_choice_memo`, `c80_marginal_floor` (20×10 : −107 k£/an 6/14), `c80_air_eval_fast` (aucun gain). **Adoptés et désormais actifs en permanence** : injection incrémentale de flotte + mise à jour AIR ciblée, auparavant exposées par `c80_fleet_inject`/`c80_air_targeted_update`. Leur 20×10 du 2026-09-23 est neutre (−19,9 k£/an, médiane +2,7 k£/an, 10/10, p=1,0, valeur +1,66 %, 20/20 paires) ; les deux réglages ont donc été supprimés de `info.nut`/`settings.nut`. **`c76_regen_targeted` passé à 1 par défaut (décision utilisateur du 2026-09-24)** : ≈54 % de régénérations complètes évitées, 20×10 neutre (−8,3 k£/an, valeur −2,8 %). **`town_growth_plan_memo` défaut 1** : 20×10 neutre (−4,2 k£/an, 9/11, p=0,8238, valeur −1,43 %). **`c80_mode_regen` défaut 1** : +52,2 k£/an, 11/9, p=0,8238, valeur +3,29 %. **Pile complète workers mesurée le 2026-09-25** sur ce défaut : référence `c80_worker_rail=0,c80_worker_town=0`, variante `1,1`, campagne `c80_full_stack_workers_vs_current_default_20x10_20260925`, **20/20 paires**, `profit_year` **+32,6 k£/an**, médiane **+104,8 k£**, **12/8**, p=0,503445, IC95 **[−162,5 ; +227,7] k£/an**, valeur **+1,76 %**. **C80-6 n'est pas atteint** (15/20, p<0,05 et +50 k£/an requis) : workers rail/ville restent à défaut 0. [Contrat et mesures](18_orchestrateur_double_registre.md), [nuit du 24](journaux/24_nuit_2026-09-24.md) §6-§7. |
| **C80 — workers A\* rail : stock de tracés prêts** (2026-09-26) | **Implémenté derrière `c80_rail_stock_gate` et `c80_rail_stock_worker` (défaut 0) ; duel 5×6 négatif ; en pause** | Cible utilisateur : toute la recherche A\* dans des workers, seuls les projets rail à tracé prêt éligibles ; conception et décisions (N = 1, tracé valable 180 j, recherche plafonnée à 180 j, étape 1 d'une chaîne d'abord, retrait de V89 après le banc du worker) dans la [note 36](36_astar_workers_conception.md). Livré : porte d'éligibilité (plus aucun arrêt de passe dû à un A\*), worker de stock, fusion par mode avant la sélection (§3.2 bis), seuil `fundScore` avant l'A\* (dernier projet financé à la dernière sélection non vide), réparation par nouvel A\*, re-vérification corrigée (`OpexTestRailTrack` : `OpexBuildTrack` testait `AreTilesConnected` sur la carte réelle après un `BuildRail` en `AITestMode`, d'où un `track_blocked` systématique). Identité au défaut au bit près (42×1, 100 et 999 ×6). Mesures : porte seule, aucun rail, duel 5×6 **−290,7 k£/an, 1/4** ; worker complet (avec `homogeneous_preselect`) solo 3×6 profit −0,7 %, valeur +4,3 %, trains 6,3 → 1,7 ; **duel 5×6 −202,5 k£/an, 0/5, IC95 [−365 ; −40] k£, valeur −10,8 %** (`astar_e2e_vs_default_5x6_20260926`). Cause ouverte : à `fundScore` égal la sélection préfère l'aérien alors qu'en duel le rail du défaut vaut ~300 k£/an. Diagnostic V89 (`results/v89gap_solo_3x6_20260926.json`) : passes `projects` espacées de 1 à 4 mois avec ou sans V89 ; une recherche a occupé le slot rail 1 382 j (graine 999). Branche `astar-workers-e1`. |
| **Préclassement homogène** (`homogeneous_preselect`, 2026-09-26) | **Défaut 0 (décision utilisateur : option prudente, à combiner au worker)** | Les top-K rail (`ratio` = profit par opcode + ROI bonifié par paliers ×1,30/1,15/1,00/0,60, poids ×15) et route (profit par opcode, `ROAD_TOP_K` = 48) ne classaient pas comme la sélection (`fundScore`). Sous le réglage, tri par le `fundScore` du projet papier (mêmes fonctions que la sélection). Air et eau gardent leurs préférences propres (audit : [note 37](37_preselection_homogene.md)). Solo 3×6 : valeur +7,3 %, profit −4,0 %. **20×10 (`homog_preselect_vs_default_20x10_20260926`, commit `10e7f59`) : −39,2 k£/an, médiane −23,7 k£, 9/11, p = 0,82, IC95 [−192 ; +114] k£, valeur −1,2 % : neutre, `fail_primary`.** Branche `homog-preselect`, reprise dans `astar-workers-e1`. |
| **Profit réalisé par ligne et par mode** (2026-09-26) | **Réalisé mesuré ; estimé à l'élection non mesuré** | Duel 5×6 au défaut avec `--line-telemetry` (`lineprofit_default_5x6_20260926`, profit VEHS ÷ 256). OpexAI en régime : rail 17 lignes, 28,0 k£/an par ligne (médiane 20,5 k£) ; air 294 lignes, 23,0 k£ (médiane 18,6 k£) ; route 61 lignes, 1,6 k£ (médiane 0,4 k£, 23 % déficitaires). **AAAHogEx air : 95 lignes, médiane 83,7 k£/an par ligne (≈ 4,5× OpexAI), 2,43 avions par ligne** ; rail 623 k£/an au total ; route déficitaire. Estimé à l'élection : sortie de script non capturée en duel ; mesure proposée `OpexAI[probe_cost=1]` (panneaux de devis `DC|`/`AC|`), non lancée (chantier avions en parallèle). [Note 38](38_profit_estime_vs_realise.md) (⚠️ son explication par un facteur rail 170 % est fausse : le défaut est 100). |
| **`town_growth_plan_memo`** | **Qualifié, défaut 1** | Gain d'opcodes déjà mesuré : coût `town_growth` −70 à −80 %. 20×10 causal `0→1` sur le défaut `dd4058d`, seule différence effective : **−4,2 k£/an**, médiane −10,6 k£, **9/11**, p=0,8238, IC95 [−119,8 ; +111,5] k£/an ; valeur **−1,43 %** ; 20/20 paires, 0 échec. Neutre selon la règle AGENTS.md §4, donc adopté. [Bilan](16_bilan_volume.md) §11 ; [nuit du 24](journaux/24_nuit_2026-09-24.md) §6. |
| **`c80_mode_regen`** | **Qualifié, défaut 1** | Gain d'opcodes déjà mesuré : régénérations réactives complètes **127 M → 0 opcodes** sur 1976–79. 20×10 causal `0→1` après adoption du mémo : **+52,2 k£/an**, médiane +34,2 k£, **11/9**, p=0,8238, IC95 [−55,3 ; +159,7] k£/an ; valeur **+3,29 %** ; 20/20 paires, 0 échec. Neutre/non régressif selon AGENTS.md §4, donc adopté. [Nuit du 24](journaux/24_nuit_2026-09-24.md) §7. |
| **C76/C77 — régénération et événements** | **C77 corrigé adopté et intégré au chemin normal** | Le comportement du triplet historique `c77_opportunistic_candidates=1`, `c77_targeted_build=1`, `c77_fixes=1` est désormais permanent ; ces trois réglages ont été supprimés de `info.nut`/`settings.nut` et les branches `0` mortes ont été retirées. La référence 0/0/0 ne subsiste que comme configuration historique des bancs. Qualification appariée en trois lots 20×10, arrêtée après le lot 3 : lot 1 +160,6 k£/an, 12/8, p=0,503445, valeur +6,75 % ; lot 2 +103,2 k£/an, 11/9, p=0,823803, valeur +1,73 % ; lot 3 +135,1 k£/an, 11/9, p=0,823803, valeur +2,47 %. Cumul exploratoire 60 graines : 34/26, p exact bilatéral=0,366294, en baisse par rapport à 0,429591 après 40 graines. La réconciliation locale reste conservée : `_rebuildProjects` retransmet toujours `_activeSubsidies` sans C76 (contrat `test_c45_subsidy_persistence.py`) ; le bornage des régénérations non-AIR reste un reliquat ciblé. [Nuit du 23](journaux/23_nuit_2026-09-23.md), [revue C76-C77](#revue-c76-c77). |
| **F-RAIL-ECON-01 — coût du dépôt rail** | Neutre, laissé à 0 | `rail_depot_cost` (défaut 0) ajoute le coût d'un dépôt au capital rail. 20×10 : +16 k£/an, 9/11, valeur −0,8 % (`fail_primary`, [nuit du 24](journaux/24_nuit_2026-09-24.md) §2). |
| **C81 — chargement complet AIR** | Priorité basse | Éventuel duel après examen des résultats solo défavorables ; protocole dans la [fiche nuit](journaux/20_nuit_2026-09-22.md). Le simple achèvement du banc C82 n'impose pas ce lancement. |
| **Revue du code** | Réconciliation courante terminée | [Revue réconciliée du 22](revue_code_2026-09-22_reconciliation_courante.md) : correctifs du 22 revalidés, findings transactionnels/ordonnanceur encore ouverts, C78/C83 et harnais relus, dette de tests confirmée. Traiter les findings par lots ciblés avant de les considérer validés. |
| **V86 — cannibalisation hub→hub (AIR)** | **Clos : cannibalisation réelle, corrections perdantes** | Étape 1 (solo 5×10) : voisines −6,4 M£ pour +9,6 M£ de nouvelles lignes. Étape 2, duels 20×10 : `air_hubhub_marginal` −153 k£/an 4/16, garde de valeur franchie ; `air_hub_max_routes=6` −50 k£/an 8/12 ; −50 à −57 véhicules dans les deux cas ([nuit du 24](journaux/24_nuit_2026-09-24.md) §1, §4). Réglages laissés à 0. Ne pas freiner hub→hub sans meilleur placement du capital. |
| **C61 AIR** | En pause | Mesurer rotations, attente, demande et occupation avant modification des délais/capacités d'aéroport. |
| **C61 Route / croissance urbaine** | Travail séparé en cours | Réconcilier le reliquat sur les stations actives avec la session concernée avant intervention. |
| **C61 Rail** | Conditionnel | Examiner les `NOSPOT`/`TRACKFAIL` sur lignes rentables demandant réellement un second train avant un chantier de géométrie. |
| **C59 — ordres contextuels** | Non démarré | Corréler remplissage au départ, attente et profit ; une photographie du chargement ne suffit pas. |
| **C68 — cinq graines défavorables** | Suivi sans urgence | Analyse causale de 7, 42, 1337, 12345 et 424242 dans le banc d'adoption, graine 7 d'abord ; distinguer géométrie, investissement et pré-filtres catalogue. Historique dans l'annexe, section « clôture C68 » ; ne pas relancer l'adoption. |
| **Protocole de banc 40×10** | Décision à prendre avant le prochain banc | Bruit mesuré : écart-type de l'écart apparié ~300 k£/an pour des effets cherchés de 100-150 k£ (d ≈ 0,5) ; la règle 15/20 détecte un tel effet ~38 % du temps, 40 graines avec règle sur la moyenne des écarts ~89 %. Garder 10 ans (les effets évoluent entre 4 et 10 ans). **Capacité implémentée** (défaut inchangé `signs20`) : `--decision-rule mean40` dans `bench_1v1_5y_20seeds.py` et `run_c66_reference.py` (40 paires, borne basse de l'IC95 de Student > 0 et moyenne ≥ effet utile, garde de valeur inchangée) ; 20 graines proposées `SEEDS_EXTRA_20` dans `bench_v2.py` (LCG déterministe, graine 20260923, sans chevauchement). **À décider** : valider ces graines et la règle avant le premier banc 40×10. [Nuit du 23](journaux/23_nuit_2026-09-23.md) §5. |
| **C80 — filtrage des bras hub par ville cible** | Priorité basse (gain d'opcodes seulement) | `targetTownId` d'`OpexAirPlans` ne filtre que les nouvelles paires : une replanification « ciblée » coûte autant qu'une complète (~2,5 M opcodes en fin de partie). Filtrer aussi `OpexAirPlansHubToSite` et `OpexAirPlansHubToHub`, puis rendre réellement partielle la mise à jour AIR ciblée désormais active après chantier aérien. |
| **C80 — travailleur « rapport annuel »** | Non démarré | `report` pèse ~12 % du temps de file en fin de partie, d'un bloc une fois par an (`_reportLines`, calibrations C70/C82, retraits) : le découper en tranches de quelques lignes. |
| **C80 — régénération complète en travailleur** | Non démarré | `catalog` pèse ~25 % : génération rail/route d'un bloc ; l'aérien n'est découpé (C78.4) qu'au-delà de 64 villes, donc jamais sur les cartes 256² du banc. Contrat C80 §4.1 (`WorkerRegenCandidates`), jamais livré pour la régénération complète. |
| **Harnais — aide `--memory` du lanceur** | Fait | `sweeps/run_c66_reference.py` : le texte d'aide indique un pic observé sous 800 Mo même à 10 workers en duel 10 ans ; sur le VPS, 3 workers avec 2 Go suffisent. |
| **C88 — joueur humain actif et joueur IA actif** | Non démarré ; reconnaissance seule, demandé le 2026-09-24 | Deux booléens, recalculés quand une compagnie apparaît, fait faillite ou fusionne : au moins une compagnie humaine vivante, et au moins une compagnie IA vivante. Actif = compagnie encore dans le pool (`AICompany.ResolveCompanyID` différent de `COMPANY_INVALID`). Un spectateur n'est pas une compagnie. OpexAI compte comme IA. L'API NoAI 15 (`AICompany`, en-tête `script_company.hpp` du master relu le 2026-09-24) n'expose pas `Company::is_ai`, alors que le chunk `PLYR` des sauvegardes le porte. Première étape : le confirmer sur le binaire OpenTTD 15.3. Si l'API ne le donne pas, le constater et s'arrêter ; ne pas classer une compagnie par son nom, son argent ou son activité. Piège déjà mesuré : un rechargement headless crée une compagnie fantôme `is_ai=0` (~100 000 £, jamais mouvementée ; [journal du 13](journaux/journal_2026-09-13.md)). Cache reconstructible, rien à sauver. Aucun changement de décision ni de défaut. |
| **Améliorer et rendre rentables C85 puis C84** | demandé le 2026-09-24 ; les deux réglages restent à défaut 0 | Ordre imposé : **C85 d'abord**, C84 ensuite. **C85** (`c85_air_equipment_frontier`) : frontière conservatrice d'équipement, non adoptée. 5×6 : −24,5 k£/an, 2/3, garde de valeur tenue (−2,69 %) ; gain d'opcodes réel mais modeste (environ 4–8 % du planning AIR). Une short-list de rôles ou une borne de profit par route changerait le contrat de sûreté et doit être mesurée à part. [Fiche](25_c85_air_equipment_frontier.md). **C84** (`c84_air_target_fleet`) : profondeur de flotte mémorisée, chantier initial toujours à un avion. 5×6 propre : −69,6 k£/an ; le franchissement forcé du premier signal de mauvaise santé n'est pas un levier retenu. [Fiche](24_c84_air_target_fleet.md). Ne pas enchaîner C84 tant que C85 n'a pas un 5×6 au-dessus de +50 k£/an. Ne pas lancer de 20×10 ni changer un défaut avant cette qualification, garde de valeur −5 %. |
| **V92 — choix d'un service aérien** | **non retenu** (5×6 du 24 : V92 −570 k£/an, V92.1 −865 k, V92.2 −627 k / −86 k) | `v92_air_service_choice`. Pour chaque route : meilleur profit sur (moteur × nombre d'appareils), plus une variante à un appareil dont le prix ne dépasse pas le gros jet le moins cher. Une seule des deux variantes est construite. 5×6 défavorables pour toutes les variantes ; la meilleure (V92.2 critère 1, choix du défaut + départage) reste à −86 k£/an, 2/3. [Fiche](31_v92_choix_service_air.md) « Mesures du 2026-09-24 ». |
| **V93 — grands aéroports sous 600 habitants** | plancher non adopté ; V93.1 rejeté 20×10 ; V93.2 rejeté 5×6, non fusionné | `v93_airport_no_pop_floor` : 5×6, `profit_year` +33 k£/an mais valeur −15 %, non adopté. V93.1 `v93_air_demand_production` : **−421,5 k£/an**, 3/17, `p=.002577`, valeur **−18,24 %**, créneaux Opex −4,85. V93.2 sur `v93-demand-residual` retire `/ (lignes+1)` et les caps 100/200 : 5×6 **−203,9 k£/an**, 0/5, IC95 entièrement négatif, valeur **−10,98 %**, créneaux −3,6. **Le comportement V93.2 n'est pas fusionné dans `master`** ; le code courant reste V93.1 à défaut 0. Ne pas lancer de nouveau banc sans changer causalement le modèle. [Fiche](32_v93_petits_aeroports.md). |
| **V94 — pré-filtre AITileList des sites aériens** | **défaut 1 (décision utilisateur du 2026-09-25) : 20×10 neutre, décisions identiques** | `OpexAirFindSite` : anneaux paresseux `r = 4..25` (`AddRectangle` / `RemoveRectangle`), filtres natifs (eau, côte, `GetClosestTown` si slot, `GetNearestTown`), ordre `GetTileX` + `Sort` ascendant (à X égal, l'index de tuile donne Y). Sortie au premier site, sans tri Squirrel. Le coin C4, `OpexAirDistanceToRect` et `OpexAirFootprintCheapOk` restent en Squirrel. Réglages `v94_air_site_list` et `v94_air_site_check` (défaut 0). Le check exécute l'ancien scan comme décision et journalise `V94_CHECK`. Gain à lire sur `AIR_PLAN_PERF` `ops_sites` (coût de `Valuate` non connu hors partie). Protocole : smoke 1×1, solo check=1 sans DIFF, puis `ops_sites` v94=0 contre 1, puis 20×10 neutre (AGENTS.md §4, seuil +50 k£ non requis). [Fiche](30_v94_air_site_list.md). 20×10 du 2026-09-25 (`v94_air_site_list_vs_default_10y_20seeds_20260924`) : graine 1024 référence `stagnation_suspect`, verdict `incomplete` ; sur 19 paires −60,7 k£/an (médiane −80,4 k), 9/10, p=1,0, IC95 [−237 ; +115] k, valeur −4,07 %. Reporté sur `c83-fixes` + correctif de portée C83 : 114 `V94_CHECK OK`, 0 `DIFF`. Faux positif de santé sur 1024 (flotte/gares stables 4 mois, valeur 8 M£, caisse en hausse). Relance sur `c83-fixes` + correctif (`v94_on_c83_vs_default_10y_20seeds_20260925`) : **20/20 sains**, `profit_year` +1,3 k£/an (médiane +61,3 k), 13/7, p=0,263, IC95 [−122 ; +124] k, valeur −3,13 % ; véhicules −4,5. Verdict harnais `fail_primary` (seuil +50 k non applicable). |

<a id="c76-c77"></a>
### C76/C77 — limites du reliquat

L'implémentation et son intégration sont journalisées le 22. Les anciens contrats de
régénération par mode ne décrivent pas nécessairement la version C76 retenue. Pour le
reliquat des candidats injectés, vérifier la conservation du vivier et les contrats de
Save/Load sur cette version avant de proposer un correctif. La prise opportuniste de slots
adverses est désormais exposée passivement par C78. Sur le 5×6 sain du 22 septembre
trouve un passage `projects` avant le second aéroport AAA dans 43/43 cas, 10/43 avec un candidat
AIR finançable et 8/43 avec ce candidat déjà dans le portefeuille financé, mais 0/43 aéroport Opex
posé avant le second AAA. La tranche 2 explique les huit cas financés : quatre `k_pass`, trois
`cash` après des constructions antérieures de la passe, un `build_failed` (`AFAIL`, erreur 263).
La corrélation tentative/outcome est close ; aucune règle de décision n'est retenue sur cette seule
mesure. Un rerun effectué pendant l'intégration concurrente de C78.4 était invalide (missing_emitter,
zéro gare/véhicule Opex). Le correctif reprenable l'a remplacé par un smoke sain puis un 1024²
10×1 complet ; voir la fiche C78. L'ancien run reste seulement un témoin du défaut intermédiaire.
Depuis cette mesure passive, la demande utilisateur a retenu une règle distincte de **course
défensive au second créneau** sous C77 : quand `station_noise_level=0`, OpenTTD 15.3 expose via
`AITown.GetAllowedNoise()` le nombre de slots aéroportuaires restants (`2`, `1`, `0`). Une ville
sans aéroport Opex avec la valeur `1` a donc exactement un premier slot déjà occupé par un tiers.
Le projet AIR rentable/finançable qui touche cette ville reçoit une priorité lexicographique avant
`k_pass` et les autres dépenses ; un A* rail déjà terminé lui cède au plus une passe. Le premier
prototype par scan de tuiles a été rejeté après un smoke à 0 véhicule / 0 gare ; la version O(1)
est saine en smoke. La qualification économique 5×6 reste due.
Le renfort déclenché par attente durable reste une possibilité distincte.

### Plan ordonnanceur début de partie — admission, priorité et réactivité C83 (2026-09-25)

La cible plus générale — séparation producteurs d'information / registre commun d'opportunités /
urgence / score économique / exécution, avec intégration future des slots, de la concurrence et du
coût de calcul — est documentée dans [34_arbitrage_economique_unifie.md](34_arbitrage_economique_unifie.md).
Le chantier immédiat reste volontairement plus étroit : assainir les tâches existantes et le débit
de décision avant de raffiner la fonction objectif.

Constat de départ : la file de fond reste un round-robin presque plat. En régime courant, `projects`
attend les passages de `expand`, `refleet`, `town_growth`, `repay`, puis le cycle suivant
`catalog`, `report`, `scrap`, `air`/`air_fleet` avant de revenir. Plusieurs de ces tâches prennent
leur tour avant de constater dans leur dispatcher qu'elles ne sont pas réellement dues : `report`
sort si l'année n'a pas changé, `repay` si le mois n'a pas changé, `catalog` si le portefeuille est
encore frais. Ce coût est particulièrement mal placé au démarrage, où la valeur vient surtout de la
construction rapide de nouvelles lignes. En revanche, **ne pas réintroduire `fleet_before_new`** :
la priorité générale « flotte avant nouvelles lignes » a déjà perdu **−20,4 % de `profit_year` à
3 ans** et reste mauvaise à 10 ans. De même, ne pas rouvrir `portfolio_max_batch > 1` comme substitut
à un meilleur ordonnanceur.

Objectif : conserver les décisions économiques actuelles autant que possible, mais cesser de brûler
des tours sur des tâches non dues et faire de la file réactive un vrai chemin d'urgence. Procéder par
étapes séparées et mesurables selon la nouvelle priorité convenue :
- **P1** : instrumentation scheduler (fait)
- **P2** : cycle de vie du portefeuille post-build (fait, voir ci-dessous)
- **P3** : C75 bis / allocation de capital (retenu d'après P2 : 100 % `all_unaffordable`)
- **P4** : watcher C83 réellement réactif
- **P5** : reliquat opcodes → workers
- **P6** : arbitre simple des workers
- **P7** : maintenance conditionnelle / skip-not-due seulement comme nettoyage secondaire

1. **Mesurer les tours réellement inutiles avant de changer l'ordre (V95 item 1 / P1 — instrumenté, résultats v3 corrigés).**
   Instrumentation passive sous `probe_scheduler=1` greffée sur l'enveloppe `_runNextTaskWithSlackLedger()` (aucun code ni opcode ajouté aux chemins exécutés à `probe_scheduler=0`).
   Émission d'un enregistrement compact `SCHED_IDLE` par sélection individuelle, permettant des distributions réelles (sans agrégation mensuelle tronquée), le coût unitaire de chaque couple (tâche, raison) et la vérification stricte de l'invariant `did_work == true ⇔ skip_class == "work"`.
   Tests de contrat Python étendus (`sweeps/test_sched_idle.py`, 16 tests validés avec succès), analyseur réécrit (`sweeps/analyse_sched_idle.py`) et diagnostic 4 ans (`sweeps/diag_sched_idle.py` / `results/diag_v95c_idle_4y_s42_100_999.json`).
   - **Définitions de `did_work == true` par dispatcher** :
     - `catalog` : resélection, régénération, ou tranche AIR C78 appliquée (`ran == true`).
     - `report` : publication annuelle de début d'année (`_lastReportYear != year`).
     - `repay` : remboursement partiel ou total du prêt (`curLoan < preLoan`).
     - `scrap` : véhicule vendu ou ligne fermée/retirée (`curVehs < preVehs || curLines < preLines`).
     - `expand` : 2e train ou wagon ajouté, expansion ou recherche A* démarrée (`curVehs > preVehs || railExp || railSearch`).
     - `refleet` : nouveau véhicule acheté et ajouté à une ligne existante (`curVehs > preVehs`).
     - `town_growth` : travailleur urbain démarré, véhicule/gare/ligne urbaine construite.
     - `air_fleet` : injection de projets de flotte dans le vivier ou achat de nouvel avion.
     - `projects` : `projects_useful` (construction lancée/achevée, A* démarré/consommé, réactif C83 consommé, abandon traité). Seul `projects_useful` réinitialise les compteurs de cadence.
     - `air` : construction aérienne hors portefeuille (auto-désactivée sous AIR_PORTFOLIO).
     - Invariant vérifié : pour chaque tâche, `did_work + noop == selected`, et pour chaque événement, `classe == "work" ⇔ did_work == 1`.
   - **Perturbation mesurée (horizon 4 ans 1970–1973, graines 100, 42, 999, probe0 vs probe1)** :
     - graine 100 : valeur 2 759 363 £ → 4 191 113 £ (+51,9 %) ; profit_year 1 225 260 £ → 1 611 261 £ (+31,5 %) ; veh 81 → 110 (+29) ; st 35 → 46 (+11).
     - graine 42 : valeur 6 506 622 £ → 6 034 738 £ (−7,3 %) ; profit_year 2 798 372 £ → 2 595 595 £ (−7,2 %) ; veh 117 → 97 (−20) ; st 60 → 57 (−3).
     - graine 999 : valeur 5 420 465 £ → 5 464 179 £ (+0,8 %) ; profit_year 2 440 715 £ → 2 428 276 £ (−0,5 %) ; veh 85 → 82 (−3) ; st 63 → 57 (−6).
     - Moyenne deltas : valeur +15,1 %, profit_year +7,9 %. La mesure est prise sous la perturbation induite par le décalage des points de suspension NoAI sous sonde.
     - À `probe_scheduler=0`, conformité bit-à-bit stricte avec la référence solo (smoke 1 an graine 42 : valeur 393164, profit 302818, veh 24, st 22).
   - **Résultats par tâche (années complètes 1970–1972, couverture 12/12 sur les 3 graines, total = 3 860 sélections)** :
     | tâche | sel | work | noop | noop% | pred | after | ops tot | ops moy | ops med | jours tot | jours moy | age d med | age d p90 | age tk med |
     |---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
     | air | 3 | 0 | 3 | 100,0 % | 3 | 0 | 1 098 | 366 | 366 | 0 | 0,00 | — | — | — |
     | air_fleet | 429 | 0 | 429 | 100,0 % | 0 | 429 | 52 003 230 | 121 220 | 23 259 | 285 | 0,66 | — | — | — |
     | catalog | 430 | 102 | 328 | 76,3 % | 328 | 0 | 161 813 095 | 376 310 | 1 742 | 877 | 2,04 | 31,0 | 50,2 | 575 |
     | expand | 428 | 1 | 427 | 99,8 % | 0 | 427 | 4 318 152 | 10 089 | 10 004 | 38 | 0,09 | — | — | — |
     | projects | 428 | 102 | 326 | 76,2 % | 0 | 326 | 251 993 142 | 588 769 | 5 605 | 1 356 | 3,17 | 29,0 | 52,6 | 530 |
     | refleet | 428 | 12 | 416 | 97,2 % | 0 | 416 | 1 359 827 | 3 177 | 2 194 | 8 | 0,02 | 119,0 | 492,4 | 2 198 |
     | repay | 427 | 13 | 414 | 97,0 % | 338 | 76 | 1 237 321 | 2 898 | 391 | 15 | 0,04 | 43,5 | 178,8 | 801 |
     | report | 430 | 9 | 421 | 97,9 % | 421 | 0 | 10 003 297 | 23 263 | 459 | 58 | 0,13 | 380,5 | 388,0 | 7 047 |
     | scrap | 430 | 0 | 430 | 100,0 % | 0 | 430 | 304 310 | 708 | 659 | 7 | 0,02 | — | — | — |
     | town_growth | 427 | 17 | 410 | 96,0 % | 0 | 410 | 31 258 932 | 73 206 | 2 654 | 170 | 0,40 | 155,0 | 381,8 | 2 869 |
     | **Total** | **3 860** | **256** | **3 604** | **93,4 %** | **1 090** | **2 514** | **514 292 404** | **133 236** | **1 127** | **2 814** | **0,73** | — | — | — |
   - **Coût unitaire par couple (tâche, raison) (années complètes 1970–1972)** :
     | tâche | raison | classe | n | % tâche | ops tot | ops moy | ops med | ops p90 | jours moy | ticks moy | ticks med |
     |---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
     | scrap | scrap_no_work | after | 430 | 100,0 % | 304 310 | 708 | 659 | 875 | 0,02 | 0,3 | 0 |
     | air_fleet | air_fleet_no_work | after | 429 | 100,0 % | 52 003 230 | 121 220 | 23 259 | 322 211 | 0,66 | 11,8 | 2 |
     | expand | expand_no_work | after | 427 | 99,8 % | 4 172 001 | 9 770 | 10 004 | 10 117 | 0,09 | 1,3 | 1 |
     | report | report_same_year | pred | 421 | 97,9 % | 194 079 | 461 | 459 | 459 | 0,01 | 0,3 | 0 |
     | refleet | refleet_no_work | after | 416 | 97,2 % | 993 026 | 2 387 | 2 193 | 3 228 | 0,02 | 0,3 | 0 |
     | town_growth | town_growth_no_work | after | 410 | 96,0 % | 21 858 892 | 53 314 | 2 529 | 169 491 | 0,28 | 5,2 | 0 |
     | repay | repay_same_month | pred | 338 | 79,2 % | 132 263 | 391 | 391 | 391 | 0,00 | 0,0 | 0 |
     | catalog | catalog_fresh | pred | 328 | 76,3 % | 544 048 | 1 659 | 1 598 | 2 066 | 0,00 | 0,0 | 0 |
     | projects | projects_empty | after | 312 | 72,9 % | 1 488 997 | 4 772 | 4 474 | 6 515 | 0,00 | 0,0 | 0 |
     | catalog | catalog_refresh | work | 102 | 23,7 % | 161 269 047 | 1 581 069 | 1 149 919 | 3 655 919 | 8,60 | 159,4 | 115 |
     | projects | projects_useful | work | 102 | 23,8 % | 238 798 905 | 2 341 166 | 2 359 918 | 3 424 939 | 12,69 | 235,1 | 238 |
     | repay | repay_no_work | after | 76 | 17,8 % | 716 694 | 9 430 | 9 928 | 9 928 | 0,16 | 2,4 | 1 |
     | town_growth | town_growth_work | work | 17 | 4,0 % | 9 400 040 | 552 944 | 380 074 | 979 288 | 3,18 | 59,1 | 40 |
     | projects | projects_examined_no_effect | after | 14 | 3,3 % | 11 705 240 | 836 089 | 438 676 | 1 846 921 | 4,43 | 83,3 | 44 |
     | repay | repay_work | work | 13 | 3,0 % | 388 364 | 29 874 | 29 923 | 29 923 | 0,15 | 3,0 | 3 |
     | refleet | refleet_work | work | 12 | 2,8 % | 366 801 | 30 567 | 30 520 | 31 107 | 0,08 | 3,0 | 3 |
     | report | report_work | work | 9 | 2,1 % | 9 809 218 | 1 089 913 | 1 100 019 | 1 847 597 | 5,78 | 109,0 | 110 |
     | air | air_disabled | pred | 3 | 100,0 % | 1 098 | 366 | 366 | 366 | 0,00 | 0,0 | 0 |
     | expand | expand_work | work | 1 | 0,2 % | 146 151 | 146 151 | 146 151 | 146 151 | 1,00 | 14,0 | 14 |
   - **Couverture et répartition par graine × année** :
     - Graine 42 : 1970 12/12 (464 sel, 33 work, 431 noop, 92,9 %, 130 pred, 301 after) ; 1971 12/12 (104 sel, 29 work, 75 noop, 72,1 %, 12 pred, 63 after) ; 1972 12/12 (58 sel, 18 work, 40 noop, 69,0 %, 6 pred, 34 after) ; 1973 10/12 (50 sel, 12 work, 38 noop, 76,0 %, 6 pred, 32 after, partiel). Total 1970–1972 = 626 sel.
     - Graine 100 : 1970 12/12 (1 887 sel, 34 work, 1 853 noop, 98,2 %, 601 pred, 1 252 after) ; 1971 12/12 (526 sel, 34 work, 492 noop, 93,5 %, 149 pred, 343 after) ; 1972 12/12 (97 sel, 33 work, 64 noop, 66,0 %, 10 pred, 54 after) ; 1973 12/12 (69 sel, 18 work, 51 noop, 73,9 %, 8 pred, 43 after). Total 1970–1972 = 2 510 sel.
     - Graine 999 : 1970 12/12 (536 sel, 26 work, 510 noop, 95,1 %, 158 pred, 352 after) ; 1971 12/12 (125 sel, 29 work, 96 noop, 76,8 %, 17 pred, 79 after) ; 1972 12/12 (63 sel, 20 work, 43 noop, 68,3 %, 7 pred, 36 after) ; 1973 10/12 (33 sel, 14 work, 19 noop, 57,6 %, 2 pred, 17 after, partiel). Total 1970–1972 = 724 sel.
     - **Vérification de cohérence exacte des totaux** : 626 (s42) + 2 510 (s100) + 724 (s999) = **3 860 sélections**. La somme par graine coïncide à l'unité près avec la somme par année (2 887 en 1970 + 755 en 1971 + 218 en 1972 = 3 860), la somme par tâche (3 860) et la somme par raison (3 860). L'analyseur intègre une assertion de cohérence stricte qui échoue bruyamment en cas de divergence.
   - **Cadence `projects` utile (distributions réelles, n = 99 intervalles)** :
     - Tâches d'arrière-plan traversées entre deux passages utiles : moyenne = 37,6 tâches, médiane = 8 tâches, p90 = 80,0 tâches.
     - ~~Délai calendaire entre deux passages utiles : médiane 29,0 j~~ — **chiffre faux** : la réconciliation P2 bis (`results/diag_p2bis_reconciliation_4y_s42_100_999.*`) mesure ≈ 4 j médian entre passages utiles en phase de construction ; les passages vides sont concentrés dans 32 épisodes d'attente de capital (459 passages, ~0,1 j par tour de file).
     - Délai en ticks moteur : moyenne = 589,4 ticks, médiane = 530 ticks, p90 = 970,8 ticks.
   - **Candidats `skip-not-due` justifiés (cls=pred), classés par enjeu réel** :
     - `report_same_year` (421 tours, 461 ops moy, 459 ops med, 0,01 j moy, 0,3 tk moy, 194 079 ops tot, 6 jours totaux) : garde d'éligibilité annuelle évidente, consomme inutilement 11 mois sur 12.
     - `repay_same_month` (338 tours, 391 ops moy, 391 ops med, 0,00 j moy, 0,0 tk moy, 132 263 ops tot, 1 jour total) : garde calendaire mensuelle simple, supprime ~340 tours à vide.
     - `catalog_fresh` (328 tours, 1 659 ops moy, 1 598 ops med, 0,00 j moy, 0,0 tk moy, 544 048 ops tot, 0 jour total) : enjeu exclusivement en opcodes (~1 600 ops par tour gaspillé, soit un demi-million d'opcodes au total sans aucun tick moteur consommé).
     - `air_disabled` (3 tours, 366 ops moy, 366 ops med, 0,00 j moy, 0,0 tk moy, 1 098 ops tot) : inerte sous `AIR_PORTFOLIO`.
   - **Constat sur `projects_empty` et goulot de `projects`** :
     - Sur les 428 sélections de `projects`, 312 tours (72,9 %) sont des no-ops `projects_empty` (vivier vide). Ils constituent **95,7 % des 326 no-ops de la tâche** (les 14 restants étant `projects_examined_no_effect` où des projets existent mais ne sont pas finançables/faisables).
     - La comparaison avec `catalog` montre une symétrie parfaite : `catalog_refresh` a produit du travail exactement **102 fois**, et `projects_useful` a consommé ce travail exactement **102 fois**.
     - Dès qu'un projet est construit, l'hypothèse initiale postulait que « le vivier est vidé et projects tourne à vide » : cette hypothèse a été rigoureusement testée et réfutée par le diagnostic P2 ci-dessous.
     - **Conclusion P1** : le goulot de `projects` n'est pas sa fréquence de passage dans l'ordonnanceur (qui passe déjà largement assez souvent, tous les 8 tours de file en médiane), mais le cycle de réapprovisionnement et de financement du vivier.

2. **Cycle de vie du portefeuille post-build (V95 item 2 / P2 — instrumenté et mesuré).**
   Instrumentation légère sous `probe_scheduler=1` (`P2_BUILD` et `P2_RESOLVE`) greffée sur `_schedIdlePostDispatch()` dans `ai/OpexAI/ledgers.nut` (aucun surcoût ni opcode à `probe_scheduler=0`, conformité bit-à-bit vérifiée : smoke 1 an graine 42 = 393164 / 24 / 22 / 302818).
   Tests déterministes Python (`sweeps/test_p2_lifecycle.py`, 6 tests couvrant toutes les causes et raisons, 25/25 avec P1), décodeur/analyseur (`sweeps/analyse_p2_lifecycle.py`), diagnostic 4 ans (1970–1972 complets, graines 42, 100, 999 : `results/diag_p2_lifecycle_4y_s42_100_999.json` et `.md`).
   - **Réfutation de l'hypothèse de vidage systématique** :
     - Sur 102 constructions observées, le portefeuille **reste immédiatement non vide dans 70 cas (68,6 %)** (`cause=none`, `funded > 0` après `OpexIncrementalUpdateProjects`).
     - Dans seulement **32 cas (31,4 %)**, la construction vide le portefeuille (`funded == 0`).
   - **Répartition des causes de vide (`emptyCause`, n = 32)** :
     - `all_unaffordable` : **32 / 32 (100,0 % des cas de vide, 31,4 % du total)**. Des projets alternatifs sont toujours présents dans le vivier (médiane 383 alternatives scannées, 236 retenues), mais tous dépassent le capital restant.
     - `cache_exhausted` : **0 / 32 (0,0 %)**. Le vivier incrémental n'est jamais épuisé.
     - `empty_pool` / `stage_empty` / `abandon_filtered` / `selection_empty` : **0 / 32 (0,0 %)**.
   - **Délai de réapparition d'un portefeuille non vide (n = 32)** :
     - Min = 2 j, Médiane = **15,0 jours** (290,5 ticks moteur), Moyenne = 15,3 j, p90 = 28 j, Max = 47 j.
   - **Déclencheurs du retour à non-vide (`ret_reason`, n = 32)** :
     - `immediate` : 70 / 102 (68,6 %).
     - `air_fleet` : **16 / 32 (50,0 %)**. L'injection incrémentale de flotte aérienne introduit des appareils bon marché (~15–20 k£) immédiatement finançables sans attendre le mois suivant.
     - `month` : **8 / 32 (25,0 %)**. Nouveau mois calendaire forçant le rafraîchissement global.
     - `capital` : **4 / 32 (12,5 %)**. Hausse de trésorerie (>2× ou +50 k£).
     - Autres tâches (`expand`, `scrap`, `catalog_other`) : **4 / 32 (12,5 %)**.
   - **Analyse financière post-build (`all_unaffordable`, n = 32)** :
     - Capital restant médian après build : 23 567 £.
     - Capital requis médian pour le projet suivant (`next_k`) : 32 812 £.
     - Déficit médian : **seulement 5 475 £**.
   - **Conclusion causale et décision P3** :
     - Le vide n'est ni un manque réel d'opportunités, ni un vivier épuisé, ni un défaut de diversité du pool. Le blocage est **100 % financier** (`all_unaffordable`).
     - Selon la grille d'arbitrage convenue (`cache_exhausted` → refresh ciblé, `all_unaffordable` → C75 bis / allocation de capital, `stage_empty` → diversité), le résultat impose **C75 bis / allocation de capital** comme priorité P3 (déblocage caisse / contournement `k_pass` pour nouvelles lignes finançables).
3. **Priorité P3 : C75 bis / allocation de capital (levier issu de P2, désormais adopté sous `c75_kpass_bypass`, défaut 1).**
   Le diagnostic P2 ayant démontré que 100 % des vidages de vivier post-build sont de type `all_unaffordable`
   (déficit médian minime de 5 475 £), le contournement de `k_pass` est implémenté : au plus une fois par passe
   et uniquement pour une nouvelle ligne (`air`, `rail`, `road`, `water`) dont le capital est réellement disponible
   (`projCap <= availCap`), jamais pour `fleet`. Aucun état persistant nouveau (compteur local à la passe).
   Aucune réservation d'argent pour un A* rail simplement présent dans le vivier (une recherche rail en vol garde ses règles).
   Smokes 1y et solo 3y validés (divergence nette : +5 avions en 3 ans). Commandes 5×6 et 20×10 prêtes. Voir fiche C75 bis.
4. **Watcher C83 réellement réactif (P4).** Aujourd'hui la transition est détectée seulement
   dans `_tryBuildProjects()` via `_c83WatchAirSlotTransitions()` : une ville surveillée passe de
   `AITown.GetAllowedNoise()==2` à `==1`, sans aéroport Opex, puis seulement alors
   `_c77EnqueueEntity(["air"], "town", townId, true, "c83_slot_race")` alimente la file réactive.
   Comme NoAI ne fournit pas d'événement « concurrent vient de poser un aéroport », conserver le
   sondage O(1) `GetAllowedNoise`, mais le faire comme **producteur réactif léger indépendant de
   `projects`**, avant le dépilage réactif de `_runOrchestratorTick` (ou à une cadence courte bornée).
   Le watcher ne construit rien : il détecte/coalesce/enqueue seulement. Tester explicitement les
   transitions `2→1`, `11→1` après disparition Opex, `1→0`, réarmement et Save/Load.
   Faire viser l'occasion par le réactif : transporter l'identité de la ville et construire de manière
   ciblée si le créneau est encore libre.
5. **Mesure de pré-planification A* rail pendant l'attente de capital (P5 bis — corrigé, mesuré sous défaut et V89).**
   Instrumentation sous `probe_scheduler=1` (`P5_WAIT_START`, `P5_WAIT_END`, `P5_RAIL_PASS`, `P5_RAIL_SEARCH_START`, `P5_RAIL_SEARCH_END`, `P5_BUILD_LINE`) greffée dans `ledgers.nut` (le correctif sonde du 2026-09-25 a retiré toute garde V95 et restructuration de `task_rail.nut` et `task_projects.nut`, restaurant une pureté stricte du chemin `probe_scheduler=0` : identité bit-à-bit exacte vérifiée contre `b34e5de` sur graines 100 et 999 × 6 ans avec recherches rail, et smoke 42 1 an).
   Tests déterministes Python (`sweeps/test_p5_preplan.py`, 31 tests unitaires), analyseur (`sweeps/analyse_p5_preplan.py`), diagnostic étendu 6 ans (graines 42, 100, 999, horizon 1970–1975) sous deux bras : défaut (`v89_rail_search_throughput=0`) et V89 (`v89_rail_search_throughput=1`). Sorties : `results/diag_p5b_defaut_probe1_6y.json` et `results/diag_p5b_v89_probe1_6y.json`.
   - **Correction de l'artefact P5 et issues réelles de l'A*** :
     - Le constat P5 initial « 0/5 succès, 5/5 NOPA » était un pur artefact de mesure (`ledgers.nut` testait `plan.path`, or un tracé réussi remplit `plan.tiles` et `plan.ok`, jamais `path`). La détection au terme effectif de recherche via `plan.ok` / `plan.reason` montre **100 % de succès réels** :
       - Bras défaut : **16 / 16 recherches réussies (100,0 % OK)**, 0 NOPA, 0 plafond itérations, 0 SHORT/NOMATCH.
       - Bras V89 : **13 / 13 recherches réussies (100,0 % OK)**, 0 NOPA, 0 plafond itérations, 0 SHORT/NOMATCH.
   - **Coût A*, débit et durée calendaire (défaut vs V89)** :
     - Bras défaut : itérations médiane = **860,5** (p90 = 2 237) ; opcodes médiane = **2 525 197** (p90 = 6 174 037) ; durée calendaire médiane = **118,5 jours** (2 189 ticks, p90 = 288 j) ; débit A* = **1 556 opcodes/tick** (moyenne = 2 157).
     - Bras V89 : itérations médiane = **529** (p90 = 2 232) ; opcodes médiane = **1 451 465** (p90 = 6 151 267) ; durée calendaire médiane = **32,0 jours** (585 ticks, p90 = 242 j) ; débit A* = **1 210 opcodes/tick** (moyenne = 1 794). V89 divise par près de 4 la durée calendaire d'une recherche rail (−73 % en jours et en ticks).
   - **Exposition en attente de capital (`all_unaffordable`)** :
     - Épisodes d'attente observés : **41** sous défaut, **36** sous V89. Présence d'alternatives rail dans le vivier : **100,0 % des épisodes** (41/41 et 36/36).
     - Durée médiane d'un épisode : **15,0 jours** (277 ticks).
     - Opcodes inutilisés par tick d'attente : médiane = **1 391 ops/tk** (défaut) / **1 414 ops/tk** (V89), p90 = 3 100 à 3 700 ops/tk, cumul = 23,5 M opcodes gaspillés.
     - *Explication des écarts d'opcodes libres (450 à 4 500+ ops/tk)* : l'ordonnanceur dispose de 10 000 ops/tick alloués par le moteur. Lors des ticks actifs (reconstruction de catalogue, tri de projets, maintenance), une part du quota est consommée. Lors des ticks d'attente passive pure, 9 500+ opcodes sont relâchés.
   - **Impact quantifié du facteur 1,70 (double application vérifiée dans le code)** :
     - Le code applique `RAIL_TERRAIN_FACTOR = 170` (+70 % sur la voie, `economy.nut`), puis `RAIL_FINANCE_CAPITAL_BIAS_PCT = 170` (+70 % sur tout le projet, `projects.nut`), imposant un multiplicateur combiné de ~1,77 alors que le coût réel (C67.6) vaut 0,96×.
     - Contrefactuel calculé hors jeu (capital à 0,96/1,70 du modélisé, sans changer le code de décision) :
       - Capital requis médian : 82 552 £ → **46 617 £** (−43,5 %).
       - Déficit médian vs caisse : 54 029 £ → **18 317 £** (−35 712 £).
       - Rang médian vivier : 139 → **49** (+90 places !).
       - Épisodes finançables : 1/41 → **5/41** (+4).
       - Dans le Top 1 (meilleur ROI) : 0 → **2** ; Top 3 : 0 → **9 (22,0 %)** ; Top 5 : 0 → **10 (24,4 %)**.
     - Le facteur 1,70 masque lourdement le rail en refoulant ses projets du Top 3/5 vers les rangs 130–140.
   - **Avance mesurable et devenir des candidats** :
     - La recherche étant reprenable, le gain n'est pas binaire mais progressif :
     - Bras défaut : avance médiane disponible = **15,0 jours** (12,7 % de l'A*). Avance théorique totale = **628 jours**, dont **133 jours** sur des candidats effectivement construits plus tard dans la partie (`built_later` = 14 épisodes, 34,1 %). 26 épisodes dépassés par un autre mode (`superseded_by_other_mode`), 1 jamais construit (`never_built`).
     - Bras V89 : avance médiane disponible = **15,0 jours**, mais couvrant **46,9 % de l'A*** (durée réduite à 32 j).
   - **Perturbation sous sonde (`probe_scheduler=1` vs `probe_scheduler=0`)** :
     - Bras défaut : s100 (valeur +0,0 %, profit −14,0 %), s42 (valeur −4,3 %, profit +4,7 %), s999 (valeur +0,7 %, profit +2,1 %).
     - Bras V89 : s100 (valeur +10,0 %, profit +2,0 %), s42 (valeur +7,6 %, profit +6,0 %), s999 (valeur +2,1 %, profit +2,2 %).
   - **Synthèse et décision P5** :
     - La pré-planification A* n'est **pas réfutée techniquement** : le taux de succès est de 100 %, les opcodes d'attente sont amplement suffisants et 133 jours de chantier sont récupérables sur des lignes réelles.
     - Cependant, deux contraintes structurelles modifient l'arbitrage :
       1. Sans correction préalable du facteur 1,70, les candidats rail restent relégués au rang 139 et sont supplantés par d'autres modes dès que la caisse remonte (63 % des épisodes).
       2. L'activation de V89 règle déjà l'essentiel de la latence de recherche (118 j → 32 j) sans complexité d'anticipation.
     - **Recommandation et livrables** : C75 bis est adopté sous `c75_kpass_bypass=1`. Le facteur rail est adopté à `rail_finance_bias_pct=100`. V89 est désormais **défaut 1** par décision utilisateur afin de servir de dépendance à V88, malgré son 20×10 direct neutre sur le profit et négatif sur la note de performance. La pré-planification en reliquat (P5/P6) reste un levier complémentaire.
6. **Arbitre simple des workers (P6).** Sélection tranche par tranche selon le travail déjà prêt et ce qui bloque
   réellement l'aval (`rail_search`, `town_growth`, puis C67). Avec `FLEET_PORTFOLIO`, `air_fleet` doit surtout
   produire/injecter un candidat ; c'est le portefeuille qui arbitre renfort contre nouvelle ligne.
7. **Maintenance conditionnelle et admission `skip-not-due` comme nettoyage secondaire (P7).**
   Déplacer les gardes calendaires et états sûrs (`report_same_year`, `repay_same_month`, `catalog_fresh`,
   drapeaux `needs*` pour `refleet`/`expand`/`scrap`) dans un prédicat d'éligibilité du scheduler pour délester
   les no-ops prédictibles. Une tâche non due est sautée dans le même scan, pas élue puis consommée pour rien.
8. **Ne pas transformer `projects` en boucle chaude générale.** Après `k_pass`, ne pas faire
   systématiquement `projects → projects` ni augmenter le batch : les essais historiques de débit
   supplémentaire du portefeuille ont été négatifs. Les seules reprises accélérées admises sont une
   intention réactive identifiée (C83/crash/urgence réelle) ou la continuation ciblée d'un travail
   déjà commencé.
9. **Validation.** Pour chaque étape : tests scheduler déterministes (ordre, skip, anti-famine), smoke
   1×1, puis 5×6 sur les graines usuelles avec métriques de cadence (`projects` utiles/jour, délai
   `financeable→attempt`, délai `slot 2→1→enqueue→attempt`), économie (`profit_year`, valeur), nombre
   de lignes/aéroports/véhicules et part de tours no-op. Ne combiner les étapes qu'après avoir isolé
   leur effet ; toute variante qui améliore seulement les opcodes mais dégrade l'économie reste non
   adoptée.

Ordre d'implémentation (nouvelle séquence P1–P7 convenue le 2026-09-25) : **P1 instrumentation scheduler (fait) → P2 cycle de vie portefeuille (fait) → P3 C75 bis / allocation de capital (priorité décidée d'après P2) → P4 watcher C83 réactif → P5 reliquat opcodes workers → P6 arbitre workers → P7 maintenance conditionnelle / skip-not-due comme nettoyage secondaire**.

<a id="revue-c76-c77"></a>
### Revue du code C76-C77 — pistes (2026-09-22)

Revue en lecture seule du commit `06b5227` (branche `c80-suite`) par trois agents agy (C76, C77,
transverse orchestrateur et persistance), recoupée par Claude dans le code. **Mise à jour du
2026-09-23 : points 1 à 5 et les trois selftests codés** (branche `c76-pistes-a`, par agy, relus
et corrigés par Claude) : points 1-3 sous le réglage `c76_lean_invalidation` (défaut 0, effectif
sous `c76_regen_targeted`), point 4 sans réglage (sans effet de décision), point 5 sous
`probe_scheduler` (clés `reactive|<kind>` et `worker|<kind>`). Smokes sains (2 × 3 ans, défaut et
pile + `c76_lean_invalidation` : 0 régénération « budget », 57 évitées). **Première lecture de
l'horloge complète : sous C77, `reactive|c77_build` pèse 136 jours de jeu sur 2 ans** (point 6).
Aucun banc : effet non mesuré. Mesures citées : solo 3 graines × 10 ans, `docs/18_orchestrateur_double_registre.md` §14.

**C76 — coût des régénérations** (vérifié dans le code) :

1. **Raison « budget » → resélection.** Un doublement du capital relance une régénération complète
   (`scheduler_tasks.nut`, `_dispatchCatalog`, variable `stale`), alors que la génération des
   candidats ne dépend pas du capital (seule `OpexProjectSelectAffordable` le lit ;
   `builder_air.nut:1172` n'est qu'un champ de sonde). `OpexReselectProjects` suffit. Trivial ;
   8 régénérations complètes sur 3 parties.
2. **Couche `lines` relevée sans nécessité.** Elle invalide tous les modes. Or une ligne de bus de
   `town_growth` (`task_town.nut:214`) ne touche que les bus de sa ville ; un retrait de ligne
   déficitaire (`task_report.nut:534`) ne rend aucun candidat invalide ; un abandon de paire hors
   passe (`lines.nut:267`) est déjà filtré en mémoire (`OpexCandidateIsAbandoned`). Traitement
   local à la place. Principale source des régénérations « layers » (34 sur 3 parties).
3. **Subvention perdue → régénération complète redondante** (`task_road.nut:30` pose
   `_portfolioInvalidated` juste après la purge locale `_purgeSubsidyFromProjects`).
4. **Matrice de dépendances fausse pour l'eau** (`_c76GetModeDeps`) : l'eau dépend des villes, pas
   des industries (elle ne planifie que des passagers). `c80_mode_regen` l'exclut déjà ; reste la
   matrice et `_c76RunSelfTest`.

**Mesure (à traiter avant toute nouvelle optimisation de C80).** 5. L'horloge C39.6 n'impute ni
les intentions réactives ni les tranches de travailleurs (elles s'exécutent dans
`_runOrchestratorTick`, hors de `_runNextTaskWithSlackLedger`) : sous la pile C80, ~280 jours
imputés par an contre ~363 au défaut. Toute durée de tour mesurée sous C80 est biaisée.

**C77 — valeur** :

6. **La construction déclenchée ne vise pas l'occasion.** `c77_build` appelle `_tryBuildProjects`,
   qui bâtit le premier rang du vivier entier, pas le candidat de l'entité touchée ; et les
   occasions produites valent peu (ville fondée ~100 habitants, industrie neuve à faible
   production). Explication la plus plausible du 10/10 au 20×10 (hypothèse). Piste : ne construire
   que si le candidat de l'événement entre en tête du classement.
7. **Le déclencheur « AAAHogEx pose un aéroport → prendre le second créneau » n'existe pas**
   (aucun handler ne regarde les stations concurrentes). Seul déclencheur à valeur démontrée
   (`docs/22_c78_lignes_vs_aaa.md` §7) : relève de **C83**. Pas d'événement NoAI : scan périodique
   `AIStationList(AIStation.STATION_AIRPORT)` filtré par propriétaire. *Note d'intégration :* la
   course défensive C78 (ci-dessus) couvre depuis ce cas sans scan, via `AITown.GetAllowedNoise()==1`.

**Corrections mineures** (vérifiées) : au rechargement, une intention `c77_build` est perdue si le
vivier est vide (`orchestrator.nut:427`) ; sous C77 sans C76, l'invalidation historique est coupée
(`event_handlers.nut:563`, 600, 639) sans relais pour une fermeture d'industrie ; clé de coalescence
`c77|build|<raison>` qui fusionne deux événements de même nature (impact faible) ; une intention
`c77_entity` attend la fin de tout travailleur, y compris un A\* rail long (latence) ; double
tranche d'A\* dans un même tick par la récursion de `town_growth_skip_noop` (réglage à 0).

**Écarté** : « une régénération réactive corrompt l'A\* en cours » (faux : le chemin historique
régénère déjà pendant une recherche, qui porte son propre candidat) ; quota anti-famine de la file
réactive (hypothèse non mesurée, décision ouverte §3.1.3 de la fiche C80).

**Pistes C76 après le rejet de `lean` (2026-09-23, deux analyses agy recoupées par Claude dans le
code).** Mécanisme commun, vérifié dans le code, effet non mesuré : **chaque régénération complète
ne génère le fret que pour UN cargo** et fait tourner `_lastFreightCargo`
(`task_projects.nut:1062-1100`). `OpexReselectProjects` (`projects.nut:1151`) et la mise à jour
post-construction (`OpexIncrementalUpdateProjects`, qui acquitte la couche `lines`) ne font pas
tourner ce cargo. Au défaut (régénération mensuelle), le fret parcourt tous ses cargos en quelques
mois ; sous C76, il reste figé entre deux régénérations complètes, et la demande des candidats
(population, production, tarifs) aussi. `lean` retire encore des déclencheurs, dont
**chaque abandon de paire** (`lines.nut:266`, fréquent en AIR), ce qui cadre avec −143 k£/an
(hypothèse). Pistes, dans l'ordre :

1. ~~Mesurer l'exposition~~ **fait** ([nuit du 23](journaux/23_nuit_2026-09-23.md) §7) : le défaut ne
   régénère qu'à chaque tour de file (~86 j) ; C76 seul garde la même cadence grâce aux
   régénérations réactives ; `lean` retire ~40 % des changements de cargo fret.
2. **Rotation fret mensuelle légère** : implémentée (`c76_freight_rotation`, défaut 0,
   `3618073`). **Non retenu** : 20×10 contre le défaut −59 k£/an, 9/11, p = 0,82, valeur −1,5 %
   (`fail_primary`), malgré un 5×6 favorable ([nuit du 23](journaux/23_nuit_2026-09-23.md) §8). La
   rotation du fret n'est pas un levier démontré ; ne pas la reproposer sans nouvelle mesure.
3. **Réévaluation légère du vivier** (demande et profit des candidats existants, sans recherche
   spatiale), mensuelle ou trimestrielle.

Écarté à la vérification : « `fleetPlan` perdu quand la régénération est évitée » (la tâche
`air_fleet` l'injecte à chaque cycle, `scheduler_tasks.nut:690-697`) ; « subvention offerte ignorée
jusqu'au filet » (C77 permanent l'injecte, `event_handlers.nut:335`).

**Selftests à ajouter** (proposés par l'audit) : aller-retour Save/Load de la file réactive et d'un
travailleur `regen_candidates` réel ; intention mutatrice pendant un travailleur actif ; cycle de
vie d'une subvention C77 (`_c77InjectSubsidy`, purge).

<a id="c61"></a>
<a id="c59"></a>
### Exploitation des lignes — contraintes de mesure

AIR : `airportDelayDays = 3.0` est une hypothèse à mesurer ; une table estimée par type
ne suffit pas à la remplacer. Route : séparer fret, passagers interurbains et croissance
urbaine ; ne pas rouvrir les feeders retirés. Rail : conserver le modèle d'accélération
`OpexRailEffectiveSpeed` (C41). C59 : longue distance ne signifie pas automatiquement
que le chargement complet est supérieur ; intégrer demande, attente et congestion.

<a id="c64"></a>
<a id="c63"></a>
<a id="c58"></a>
<a id="c39"></a>
<a id="c41"></a>
<a id="c44"></a>
## Suites conditionnelles, sans lancement automatique

| Sujet | Condition de reprise |
|---|---|
| C63/C58 — investissement et recettes | Partir d'une erreur de coût/recette ou d'une occasion actuelle identifiée, en tenant compte du ledger C63 corrigé. Ne pas reprendre la conclusion historique « capital exclu » ni réintroduire les prédevis retirés. |
| C39/C41/C44 — calcul et fraîcheur | Occasion finançable retardée par un coût mesuré ; articuler avec C76/C77/C80, sans rouvrir les optimisations rejetées sur la seule foi d'un ancien profil. |
| C64 — politique adaptative | Mécanisme établi, règle pré-enregistrée et graines nouvelles ; pas de nouvelle recherche de seuil sur les graines ayant servi à le découvrir. |
| C43/E3 — constantes | Réserve, `pax_near` ou seuil de rebut impliqué dans une erreur mesurée ; aucun balayage général. |
| C42 bis — subventions | Exposition et rendement du producteur C77 courant ; ne pas restaurer les anciens drapeaux C42 supprimés. |
| C55 — bassins de demande | Sur-service ou partage de flux concurrents effectivement observé ; ne pas rouvrir le filtre d'origine. |
| Compatibilité NewGRF / M3 | Le diagnostic vanilla ne qualifie pas les choix de refit ni leurs capacités ; qualification dédiée si ce runtime entre dans le périmètre. |
| M2, M5/G2, M6, M7/11.3, B6/06.12 | Risques historiquement dormants : vérifier que leur chemin existe encore et devient exposé avant tout lot. |
| Placement/catchment, bruit aéroport, extension de gare, `station_join`, RAM Squirrel | Besoin démontré dans le code courant ; pas de reprise automatique depuis une ancienne liste de revue. |

## C67 — carte par blocs et connectivité

Le chemin actuel est le BFS borné de `builder_water.nut::OpexWaterFindConnection`.
`lib_water.nut` et les réglages Lakes ont été supprimés le 21 septembre, **avant C67**.
Voir le [journal du 21](journaux/journal_2026-09-21.md) pour la décision et le commit ; l'analyse
du code est dans le [journal du 22](journaux/journal_2026-09-22.md). Ne pas programmer un second retrait.
La consigne d'accord explicite avant un nouveau diagnostic de découverte maritime est conservée.

### Étapes et critères de passage

Les étapes sont séquentielles ; l’analyse initiale est consignée au journal du 22 septembre, sans qualification runtime.
Le [contrat initial C67.1](c67_cartographie_contrat.md) fixe les API proposées et le protocole ;
sa livraison est consignée au journal du 22.

| Étape | Livrable et périmètre | Validation avant passage |
|---|---|---|
| **C67.3 — qualification 5×5 / 10×10** | **Livré.** Matrice v2 complète ; S=5 retenu provisoirement après mesures mémoire/opcodes/précision jusqu'à 2048². | Revenir sur la granularité seulement si un consommateur réel démontre un autre compromis. |
| **C67.4 — cycle de vie et ordonnanceur** | **Livré.** c67_terrain_map défaut 0 ; calcul résumable, invalidation locale, reprise/annulation et remplissage opportuniste avant Sleep(1). | Le crochet est quasi neutre, pas strictement neutre : l'intégrer ensuite au futur arbitre commun de workers plutôt que multiplier les hooks spécialisés. |
| **C67.5 — graphe et oracle de connectivité** | **Livré.** water_graph.nut fournit un oracle exact-ou-inconnu borné ; aucun connecté/déconnecté faux admis sur les fixtures. | Ne le brancher qu'après exposition métier démontrée. |
| **C67.6 — sondes d'exposition** | **Livré ; aucun consommateur eau/rail retenu.** Eau : 6 paires en 256², aucune en 512². Rail : capital pré-A* déjà très proche du réel et un seul abandon A*. | Ne rien brancher par défaut. Conserver C67 comme infrastructure prête pour le futur pool de workers et chercher un usage AIR/cartographie seulement sur besoin démontré. |
| **C67.7 — adoption puis extensions conditionnelles** | Fixer avant le banc métrique primaire, effet minimal utile et garde-fou de valeur. Qualifier le consommateur retenu ; ouvrir séparément coûts/ROI, choix du mode, implantation et régions naturelles seulement si leur besoin est démontré. | Banc officiel apparié 20 graines × 10 ans complet et sain, verdict effectif du harnais et preuves figées. Adoption du défaut seulement après succès ; un gain de mémoire/opcodes seul ne prouve pas un gain économique. |

**État après C67.6.** Les briques de cartographie, cycle de vie et connectivité sont disponibles,
mais aucun consommateur eau/rail n'a démontré assez d'exposition pour justifier un branchement.
La suite n'est donc pas un « C67.7 automatique » : mesurer d'abord le lecteur de blocs par
AITileList + Valuate, puis intégrer C67 au futur arbitre de workers consommant le reliquat
d'opcodes. Un usage AIR/cartographie ne sera ouvert que lorsqu'un besoin métier concret sera
mesuré.

### Contraintes de conception

**Contrat de conception retenu.** Construire une représentation de carte propre à
OpexAI, commune à l’analyse du terrain et à la future connectivité hiérarchique. La carte
est découpée en blocs carrés réguliers ; deux granularités candidates sont à mesurer, **5×5** et
**10×10 tuiles**. La taille n'est pas fixée par intuition : le premier livrable de C67 doit comparer
coût mémoire/opcodes, précision et utilité pour les décisions.

Chaque bloc porte un résumé compact calculé depuis ses tuiles, au minimum : part eau/terre,
altitudes min/max/moyenne, amplitude de relief, proportion de terrain plat et indicateur de
pente/irrégularité. À partir de ces mesures, le bloc reçoit un type principal tel que **eau**,
**côte/mixte**, **plat**, **vallonné** ou **montagne**. Les seuils exacts et l'éventuel typage
secondaire sont à calibrer sur cartes réelles ; ils ne doivent pas devenir des constantes métier
avant mesure.

Les blocs forment ensuite un graphe spatial léger de voisinage. Ce niveau grossier doit pouvoir
servir à plusieurs consommateurs sans dupliquer des scans de carte : présélection de corridors,
coût/complexité de terrain, détection de grandes zones d'eau et connectivité grossière. Les tests
fins restent au niveau tuile lorsque la construction l'exige ; C67 n'a pas vocation à remplacer un
pathfinder exact par une classification grossière.

**Principe d'exécution : cartographie lazy et opportuniste.** C67 ne doit jamais lancer une grosse
tâche monolithique de cartographie complète au démarrage. Un bloc est calculé lorsqu'un projet a
besoin de l'étudier ; son résultat est ensuite mis en cache et réutilisé. En dehors de ces demandes,
la couverture de la carte peut progresser en tâche de fond par petits lots uniquement quand le
contrôleur dispose d'un budget d'opcodes réellement libre — par exemple lorsqu'aucun projet utile
n'est constructible faute de trésorerie — sans retarder les tâches métier prioritaires. Le scheduler
doit donc pouvoir interrompre/reprendre ce remplissage, lui imposer un budget strict par tranche et
abandonner immédiatement la cartographie de fond dès qu'un travail plus prioritaire apparaît.

La carte peut ainsi rester **partielle** pendant longtemps : les zones pertinentes pour les projets
réels seront naturellement cartographiées en premier. Aucune décision ne doit supposer que 100 % de
la carte est déjà connue ; une donnée de bloc absente signifie « à calculer si nécessaire », pas
« terrain neutre ». Le remplissage opportuniste est un bonus de temps mort, jamais une condition de
démarrage de l'IA ni un motif pour immobiliser des opcodes qui pourraient servir à une décision ou
une construction immédiatement utile.

Usages visés au-delà de la connectivité maritime :

- **prévision économique par projet** : utiliser le corridor de blocs pour estimer plus tôt le coût
  réel probable de construction, le délai avant mise en service et donc un ROI plus réaliste que les
  facteurs fixes actuels ;
- **prévision du coût de décision** : estimer avant le pathfinding exact le nombre d'opcodes et le
  temps/ticks nécessaires pour étudier puis construire un projet, afin d'ordonner les candidats par
  valeur attendue mais aussi par coût de calcul ;
- **pré-pathfinding hiérarchique** : chercher d'abord un corridor grossier dans le graphe de blocs,
  puis limiter l'A* exact aux zones plausibles au lieu d'explorer la carte sans information globale ;
- **risque de faisabilité** : dériver un indicateur de difficulté/échec probable à partir du relief,
  de l'eau, des pentes, de la constructibilité et de la fragmentation du corridor ;
- **choix du mode de transport** : comparer rail/route/eau/air à partir de la structure physique du
  corridor avant de lancer des devis lourds pour chaque famille ;
- **implantation et extensibilité** : repérer les zones adaptées aux gares, dépôts, quais et axes
  d'approche, ainsi que la place disponible pour double voie, allongement ou branches futures ;
- **détection de régions naturelles** : agréger les blocs en plaines, massifs, bassins, îles,
  péninsules ou corridors côtiers pour améliorer la génération même des candidats.

Le **type principal** d'un bloc est seulement une vue simplifiée. La représentation doit conserver
un vecteur de caractéristiques réutilisable, par exemple `water_ratio`, `buildable_ratio`,
`height_min/max/mean`, amplitude de relief, densité de pente, bords côtiers et densité
d'infrastructure. Le typage `eau/plat/montagne/...` est dérivé de ces mesures et ne doit pas faire
perdre l'information brute nécessaire aux modèles de coût, ROI ou temps.

La carte est conceptuellement séparée en deux couches : une **couche physique** relativement stable
(eau, altitude, pente, constructibilité) et une **couche dynamique** (villes, industries,
infrastructures Opex/adverses, gares, voies, routes). Les modifications locales de carte doivent
invalider seulement les blocs concernés. La cible architecturale devient donc :
`candidat -> corridor de blocs -> prévision £ / ROI / opcodes / durée / risque -> portefeuille ->
pathfinding exact seulement pour les candidats retenus`.

Contraintes de conception :

- **aucune structure persistante à une entrée par tuile de la carte entière**, contrairement à
  Lakes ; à 2048², une grille 5×5 représente au plus ~168 100 blocs et une grille 10×10 ~42 025,
  contre 4 194 304 tuiles ;
- construction interruptible/mesurable en opcodes et mémoire, compatible avec les grandes cartes ;
- représentation indépendante de MinchinWeb, réutilisable par eau **et** analyse générale du
  terrain ;
- stratégie explicite de rafraîchissement/invalidation des blocs affectés par les modifications de
  carte, plutôt qu'une reconstruction globale aveugle ;
- migration en deux temps : valider la représentation et ses oracles, puis seulement brancher les
  consommateurs sur le code courant.

Premier protocole attendu : construire les deux grilles sur 256²/512²/1024²/2048², mesurer
RAM/opcodes/temps, comparer 5×5 et 10×10, puis vérifier le typage sur un échantillon de blocs et la
connectivité eau contre un oracle BFS borné/exact. **Aucun default de jeu ou de politique n'est à
changer avant cette qualification.**

## Validation et clôture d'une tâche

Appliquer [AGENTS.md](../AGENTS.md) : documentation seule → diff et liens ; Squirrel →
tests pertinents et smoke 1×1 ; comportement → diagnostic apparié 5×6 ; adoption →
20×10 complet et sain, avec métrique, effet minimal et garde-fou fixés avant les résultats.
Ajouter la validation Save/Load quand nécessaire. Figer les entrées, conserver les limites
et ne pas confondre absence de significativité et équivalence.

**Graines du banc.** Il n'y a plus de graine morte connue : 2026, 1337 et 1024 gelaient dans la
phase eau (C56) jusqu'au correctif `water_lakes_ops_budget` du 2026-09-11. Vérifié sur les 20×10
duel du 2026-09-23 (bras défaut) : 2026 = 65 gares / 136 véhicules, 1337 = 57 / 164, 1024 = 91 /
191, pour une médiane d'environ 68 gares. Les 20 graines de `bench_v2.py` comptent donc toutes ;
ne pas en retirer. Un gel reste détecté par le harnais (`last_year` < `expected_last_year` →
`incomplete_run`), jamais moyenné en silence.

Docker : `--cpus=3 --memory=2g --memory-swap=2g`, volume `openttd-lab-home:/home/lab`,
dépôt réellement monté dans `/work`, trois workers maximum et une seule campagne VPS à la fois.

À la clôture, transférer le compte rendu dans `journal_YYYY-MM-DD.md` avec les preuves,
la décision et les réserves ; retirer l'action terminée de cette liste. Pour un chantier
partiellement livré, ne conserver ici que son reliquat et un lien vers le journal.
