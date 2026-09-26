# Tâches — réduire l'écart avec AAAHogEx

État courant actualisé le **2026-09-22**. Ce fichier est la **seule liste autoritaire du
travail restant**. Les travaux terminés, résultats et décisions sont dans les journaux ;
une ancienne mention « à faire » ne remet pas un chantier dans cette liste.

## État courant

Le défaut comprend C68, C69 bis/C70/C75 et, depuis le 2026-09-23, **C77 corrigé**
désormais actif en permanence ; ses trois anciens réglages ont été supprimés de `info.nut`/`settings.nut`.
C76,
les travailleurs C80, le mémo de croissance urbaine, C81 et C82 restent expérimentaux à défaut 0.
Depuis le 2026-09-24, `c83_preempt_open` et `air_batch_town_reserve` sont implémentés, défaut 0 ;
leurs 5×6 sont défavorables (préemption : profit neutre, valeur −8 % ; réserve : −180 k£/an, 0/5) et
aucun n'est retenu. Le script `sweeps/analyse_air_demand_vs_realized.py` compare le profit aérien prédit
au réalisé ; il ne change pas l'IA.
La version C76 retenue saute la régénération complète sans changement, avec filet annuel.
Les bancs C77 seul et C82 du 22 septembre sont terminés et non adoptés : ils ne sont plus
à lancer. Les feeders et Lakes sont retirés ; la cartographie C67 n'est pas implémentée.

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
| **V89 — débit de recherche rail opportuniste** | **exposition confirmée ; 5×6 causal non favorable** | Diagnostic solo 3×6 du 2026-09-25 sur le défaut courant, graines 42/100/999, 3/3 saines : **6 recherches terminées**, durée recherche médiane **189,5 j** (20–735 j), **4 lignes mises en service**, délai sélection→service médian **225 j** (102–822 j), fin recherche→service médian **61 j**. Dans les années avec recherche active, le débit reste de l'ordre de quelques centaines d'itérations/an (294–900 ; médiane 739) malgré V91=120. Duel causal 5×6 `v89_rail_throughput_vs_default_5x6_20260925` : **profit_year −62,0 k£/an**, médiane **−117,7 k£**, **2/3**, p=1,0, IC95 **[−177,5 ; +53,5] k£/an** ; valeur **+1,48 %**. Le goulot calendaire existe, mais V89 ne montre pas de gain économique au 5×6. **Ne pas lancer le 20×10 tel quel** ; retravailler l'allocation du slack/opcodes avant nouvelle qualification. [Fiche](28_v89_debit_recherche_rail.md), [synthèse](33_caisse_1970_1972_et_leviers_aaa.md). |
| **AIR MAIL-only** | analyse terminée, non implémenté | AAAHogEx tire ≈267 k£/an de 4,8 lignes / 10 avions MAIL-only au 5×6. OpexAI connaît `mailCargo` et ajoute le mail comme supplément aux lignes PASS, mais `OpexAirPlans`, `OpexAirEconomics` et `OpexBuildAirRoute` restent passagers et refittent explicitement vers `paxCargo`. Prototype minimal : **MAIL-only entre aéroports Opex déjà existants**, demande MAIL réelle des bassins, avion refitté MAIL, mêmes deux ordres ; aucun nouvel aéroport dans le premier essai. Smoke puis 5×6 par cargo. [Synthèse](33_caisse_1970_1972_et_leviers_aaa.md). |
| **V90 — A* rail rapide vendorisé** | **défaut 1 (décision utilisateur du 2026-09-24) : équivalence parfaite, gain −8 %** | Réduction par au moins 2 du coût en opcodes d'une itération d'A* rail, à tracé et exploration strictement identiques. Copies vendorisées GPLv2 dans `ai/OpexAI/pathfinder_v90/` (`OpexBinaryHeapV90`, `OpexAyStarV90`, `OpexRailPathFinderV90`). Optimisations : ensemble fermé en table Squirrel native au lieu d'AIList, précalcul des constantes (taille de carte, offsets, coordonnées de buts), mémoïsation par recherche des requêtes invariantes de tuiles (`GetSlope`, `IsBuildable`, `IsCoastTile`, `IsBridgeTile`, `IsTunnelTile`, `HasTransportType`) et types de ponts par longueur. Réglage `v90_fast_pathfinder` (défaut 0) et mode de test parallèle pas à pas `v90_pathfinder_check` (défaut 0, traces `V90_CHECK`). **Mesure (2026-09-24)** : zéro écart sur ≈ 3 300 pas comparés ; 2 821 → 2 583 opcodes/itération (−8 %), car un appel API ne coûte presque rien en opcodes : le coût est dans la logique Squirrel (tas, `Path`, `_Cost`). Un gain ≥ ×2 exige de réduire le nombre d'itérations (heuristique pondérée), donc de changer le tracé. [Fiche](29_v90_pathfinder_rail.md) §9. |
| **V91 — heuristique pondérée A* rail (weighted A*)** | **poids 120 par défaut (décision utilisateur du 2026-09-24)** : recherches ÷ 5, coût A* +3,6 %, 20×10 neutre (médiane +28 k£/an, 11/9, p = 0,82, valeur −0,8 %) ; poids 150 rejeté (−40,8 k£/an, 7/13) | Réduction forte du nombre d'itérations d'exploration du pathfinder rail (levier direct pour accélérer les recherches par ≥ ×2). Multiplication de l'estimation admissible `_Estimate` par $w = \text{weight\_pct} / 100$ ($w \in [1{,}0 ; 3{,}0]$) dans `OpexRailPathFinderV90`. Réglage `v91_astar_weight_pct` (entier 100-300, pas 10, défaut 100 = V90 strictement inchangé, aucun surcoût d'opcodes au défaut grâce à la sélection de fonction au constructeur). Mode de test `v90_pathfinder_check` adapté (désactivation des alertes pas à pas, publication de la trace de fin `V90_CHECK name=finish_weighted` avec itérations, longueurs via `OpexSegmentTiles`, coûts et ratios). Instrumentation `RAIL_SEARCH_END` étendue sous `C56_TASK_TRACE` (résultat `found`/`none`/`cap`, longueur et poids). Protocole : smoke check 1×1 poids 150, mesure itérations/recherche et longueur des tracés à 100/150/200 sur graines 100/999/1234 × 8 ans avec `probe_events`+`probe_scheduler`, puis duel apparié 20×10 `run_c66_reference.py` contre le défaut (métrique `profit_year`, effet utile +50 k£/an, garde −5 %). [Fiche](30_v91_astar_pondere.md). |
| **C67 — carte par blocs** | **C67.3 à C67.6 livrés ; aucun consommateur métier exposé** | C67.3 : S=5 retenu provisoirement. C67.4 : service résumable dans le reliquat de tick sous 'c67_terrain_map=0', quasi neutre. C67.5 : graphe/oracle eau exact-ou-inconnu livré. C67.6 : sonde eau appelée 32 fois (6 paires) en 256², jamais en 512² ; côté rail, 16 lignes / 20 parties et capital pré-A* déjà à ~5 % du coût réel, donc aucun consommateur eau/rail suffisamment exposé pour être branché. Les services restent **non branchés aux décisions économiques**. [Contrat](c67_cartographie_contrat.md), journaux du [23](journaux/journal_2026-09-23.md) et du [24](journaux/journal_2026-09-24.md). |
| **Facteur rail 1,70 (biasPct)** | Constat C67.6, à mesurer | Sur 16 lignes tentées, le coût réel vaut ~0,96× le capital financé avant A* : le facteur 1,70 surestime fortement le besoin. Mesurer d'abord les candidats rail refusés par ce facteur avant toute modification. [Contrat C67 §20](c67_cartographie_contrat.md). |
| **C67 — lecture de bloc par Valuate** | À mesurer (fixture, sans partie longue) | Comparer le lecteur tuile-par-tuile actuel à AITileList.AddRectangle + Valuate sur blocs 5×5 et 10×10 : opcodes, exactitude des résumés et borne non suspendable. Remplacer _readOne seulement si le gain est net ; ne jamais lancer un Valuate sur une carte entière. |
| **C78 — occasions présentes chez AAAHogEx, absentes chez OpexAI** | C78.3/C78.4 validés ; C83.1 qualifié | **C78.3/C78.4** restent validés. Le défaut C83.1 résiduel était sémantique : le watcher confondait une ligne AIR commerciale proche avec un aéroport occupant physiquement le slot, et la génération ciblée ne garantissait pas `ClosestTown(anchor)==ville cible`. Correction du 2026-09-24 : état Opex par aéroports physiques, constante C83 distincte, site ciblé contraint au TownID du slot et télémétrie `c83_slot_claimed/lost`. L'ablation 24 villes n'est pas retenue ; le défaut final reste **6 villes**. Son 20×10 donne **+165,3 k£/an**, 15/5, p=0,0414, valeur **+6,78 %** et fait tomber les monopoles AAA fin 1979 **215→178**. [Fiche](22_c78_lignes_vs_aaa.md) §10. |
| **C83 — empêcher les monopoles aériens d'AAAHogEx** | **C83.1 qualifié (6 villes) ; `c83_fixes`, `c83_preempt_open` et `air_batch_town_reserve` à défaut 0** | Le 20×10 du défaut 6 villes reste qualifié : **+165,3 k£/an**, 15/5, p=0,0414, valeur **+6,78 %**, monopoles AAA fin 1979 **215→178**. Les correctifs de revue restent sous **`c83_fixes` défaut 0**. **`c83_preempt_open`** (défaut 0) garde une seule grande ville encore vide (`GetAllowedNoise()==2`) et lui donne la priorité défensive devant hub→hub, sans sauter le test de profit. **`air_batch_town_reserve`** (défaut 0) ne finance qu'un projet aérien par ville de nouvel aéroport ; les autres restent dans le vivier. **5×6 du 24 :** `c83_preempt_open` −4 k£/an, 3/2, valeur **−8 %** (garde violée) → non retenu ; `air_batch_town_reserve` **−180 k£/an, 0/5**, IC95 entièrement négatif, valeur −6 % → rejeté (réserve appliquée après la sélection sous budget, capital libéré perdu). **C83.2 non retenu.** [Fiche](22_c78_lignes_vs_aaa.md) §11–§13. **`c83_fixes` (défaut 0) non adopté** : 20×10 du 2026-09-24 `fail_primary`, −28,8 k£/an, 10/10, p=1,0, IC95 [−158 ; +100] k, valeur +1,78 % ; créneaux Opex −2,1, villes Opex −1,95, véhicules −13 %, déficit croissant à partir de 1972. Correctif de portée (2026-09-25) : la contrainte `OpexAirSlotTownId` ne vaut plus que pour les sites de course C83 (`c83SlotTown`), plus pour la recherche AIR ordinaire. 5×6 (`c83_slotscope_vs_default_6y_5seeds_20260924b`) : −30 k£/an, 1/4, créneaux −1,4, villes −1,2 : la contrainte globale n'explique pas seule le recul. Suspect suivant : `OpexAirC83WatchTowns` (seuil pratique ~600 hab.) ; séparer `c83_fixes` en réglages distincts avant de mesurer. |
| **C80 — ordonnanceur** | Qualification économique de la pile | Socle, travailleurs rail/ville, tranches 4-5, pistes C76 1-5 (`c76_lean_invalidation`, horloge C39.6 complète) intégrés. **`c80_air_hub_index` passé à 1 par défaut (décision utilisateur du 2026-09-23)** : décisions exactes, −32 % d'opcodes hub→hub, réservés pour C67 ; 20×10 neutre (−16 k£/an 9/11, valeur +1,3 % ; [nuit du 23](journaux/23_nuit_2026-09-23.md) §9). **Validé par l'utilisateur le 2026-09-24.** Neutralité confirmée par le 40×10 `mean40` du 24 (+11 k£/an, 20/20, IC95 [−67 ; +90], valeur +1,9 % ; [nuit du 24](journaux/24_nuit_2026-09-24.md) §3). Non retenus : `c76_freight_rotation` (20×10 : −59 k£/an 9/11), `c76_lean_invalidation` (20×10 sur le nouveau défaut, avec C76 : 4/16, p = 0,0118, IC95 négatif, garde de valeur dépassée ; [nuit du 23](journaux/23_nuit_2026-09-23.md) §6), `c80_air_choice_memo`, `c80_marginal_floor` (20×10 : −107 k£/an 6/14), `c80_air_eval_fast` (aucun gain). **Adoptés et désormais actifs en permanence** : injection incrémentale de flotte + mise à jour AIR ciblée, auparavant exposées par `c80_fleet_inject`/`c80_air_targeted_update`. Leur 20×10 du 2026-09-23 est neutre (−19,9 k£/an, médiane +2,7 k£/an, 10/10, p=1,0, valeur +1,66 %, 20/20 paires) ; les deux réglages ont donc été supprimés de `info.nut`/`settings.nut`. **`c76_regen_targeted` passé à 1 par défaut (décision utilisateur du 2026-09-24)**, en application de la règle d'adoption des optimisations d'opcodes (AGENTS.md §4 : gain d'opcodes + 20×10 sans perte) : ≈ 54 % de régénérations complètes évitées, 20×10 sur le défaut C77 neutre (−8,3 k£/an, valeur −2,8 %, contre −64,5 k£/an et −7,4 % à l'ancien N3). **`town_growth_plan_memo` passe aussi à 1 par défaut le 2026-09-24** : −70 à −80 % du coût `town_growth`, puis 20×10 causal sur le défaut `dd4058d` neutre (−4,2 k£/an, 9/11, p=0,8238, IC95 [−119,8 ; +111,5] k£/an, valeur −1,43 %, 20/20 paires). **`c80_mode_regen` passe également à 1 par défaut** : régénérations réactives 127 → 0 M op en 1976–79, puis 20×10 causal **+52,2 k£/an**, médiane +34,2 k£, 11/9, p=0,8238, IC95 [−55,3 ; +159,7] k£/an, valeur **+3,29 %**, 20/20 paires. Le découpage d'`OpexAirPlans` reste un refactor sans changement de logique. Prochaine étape : 20×10 de la pile complète sur ce nouveau défaut. [Contrat et mesures](18_orchestrateur_double_registre.md), [nuit du 24](journaux/24_nuit_2026-09-24.md) §6-§7. |
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
étapes séparées et mesurables :

1. **Mesurer les tours réellement inutiles avant de changer l'ordre.** Sous `probe_scheduler`, ajouter
   par tâche : `selected`, `did_work`, `noop_reason`, jours/ticks/opcodes et âge depuis le dernier vrai
   travail. Séparer au minimum `report_same_year`, `repay_same_month`, `catalog_fresh`, maintenance
   sans travail et `projects_empty`. Publier aussi le nombre de tâches de fond traversées entre deux
   passages utiles de `projects`, surtout sur 1970-1972. Cette étape est observatoire.
2. **Admission `skip-not-due` avant le choix de la tâche.** Déplacer les gardes calendaires et états
   sûrs dans un prédicat d'éligibilité du scheduler, sans changer le corps métier :
   - `report` admissible seulement si `year != _lastReportYear` ;
   - `repay` admissible seulement si le mois courant diffère de `_lastRepayMonth` ;
   - `catalog` admissible seulement si mois/invalidation/couches/capital imposent réellement une
     resélection ou reconstruction ;
   - les slots C41 dormants restent désactivés comme aujourd'hui.
   Une tâche non due doit être **sautée dans le même scan**, pas élue puis consommée pour rien. Premier
   banc causal : cette seule modification, sans nouvelle règle de priorité économique.
   **Architecture opcodes à préparer en parallèle, sans l'activer en bloc** : après l'action utile du
   tick, les workers résumables pourront consommer le reliquat d'opcodes avant `Sleep(1)`, puis être
   réarbitrés tranche par tranche selon le travail déjà prêt et ce qui bloque réellement l'aval
   (`rail_search`, `town_growth`, puis C67). Ce n'est pas le retour de `loop_budget` : aucune deuxième
   décision économique complète n'est lancée sur le reliquat. Voir
   [34_arbitrage_economique_unifie.md](34_arbitrage_economique_unifie.md) §5.5.
3. **Rendre la maintenance conditionnelle quand une garde bon marché existe.** `expand`, `refleet`,
   `scrap` et `town_growth` ne doivent pas obtenir automatiquement le même droit de passage qu'un
   investissement neuf si aucun travail n'est plausible. Préférer des drapeaux/queues `needs*`
   alimentés par événements et états existants (`needsRefleet`, ligne à étendre, véhicule retiré,
   ville effectivement éligible) à un appel complet qui découvre ensuite qu'il n'y a rien à faire.
   Ne pas inventer un scan coûteux juste pour savoir s'il faut scanner.
4. **Sortir le watcher C83 du passage `projects`.** Aujourd'hui la transition est détectée seulement
   dans `_tryBuildProjects()` via `_c83WatchAirSlotTransitions()` : une ville surveillée passe de
   `AITown.GetAllowedNoise()==2` à `==1`, sans aéroport Opex, puis seulement alors
   `_c77EnqueueEntity(["air"], "town", townId, true, "c83_slot_race")` alimente la file réactive.
   Comme NoAI ne fournit pas d'événement « concurrent vient de poser un aéroport », conserver le
   sondage O(1) `GetAllowedNoise`, mais le faire comme **producteur réactif léger indépendant de
   `projects`**, avant le dépilage réactif de `_runOrchestratorTick` (ou à une cadence courte bornée).
   Le watcher ne construit rien : il détecte/coalesce/enqueue seulement. Tester explicitement les
   transitions `2→1`, `11→1` après disparition Opex, `1→0`, réarmement et Save/Load.
5. **Faire viser l'occasion par le réactif.** Une course C83 doit transporter l'identité de la ville
   et, après régénération ciblée, ne doit pas se réduire à un `_tryBuildProjects()` générique capable
   de construire un autre rang du portefeuille. Réutiliser la promotion défensive existante ou une
   exécution ciblée qui revalide au dernier moment : slot toujours à `1`, aucun aéroport Opex,
   candidat AIR rentable, finançable et encore constructible. `k_pass` reste la protection générale
   des constructions ordinaires ; la course à une ressource périssable est l'exception explicite.
6. **Séparer ensuite priorité investissement et maintenance, sans permuter aveuglément la file.** Une
   fois `skip-not-due` qualifié, tester un ordonnanceur par classes. La cible n'est plus « un worker
   obligatoire avant la file », mais :
   `réactif urgent → action/tâche réellement due → allocation du reliquat aux workers → Sleep(1)`.
   Le choix du worker dépend du pipeline : un A* qui bloque le meilleur projet passe devant ; si des
   résultats rail sont déjà prêts, `town_growth` ou plus tard C67 peuvent récupérer le reliquat.
   Avec `FLEET_PORTFOLIO`, `air_fleet` doit surtout **produire/injecter un candidat** ; c'est ensuite le
   portefeuille qui arbitre renfort d'une ligne existante contre nouvelle ligne. Ne pas recréer une
   règle « servir toute la flotte avant de construire ».
7. **Politique bootstrap séparée, uniquement après la phase structurelle.** Mesurer sur les premières
   années une règle où `town_growth` et éventuellement `repay` cèdent leur tour lorsqu'un projet
   rentable est immédiatement finançable. Ce changement touche l'allocation de capital : réglage à
   défaut 0, diagnostic 5×6 puis banc officiel seulement si l'exposition est réelle. `town_growth`
   reste autorisé comme emploi du capital résiduel ; le remboursement garde les protections de
   `_tryRepayLoan()` et ne doit jamais être supprimé globalement.
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

Ordre d'implémentation recommandé : **(1) instrumentation → (2) skip-not-due → (4) watcher C83
réactif → (5) construction C83 ciblée → (3) maintenance conditionnelle → (6) classes de priorité
→ (7) politique bootstrap**. Les étapes 2 et 4 sont les candidats les plus conservateurs : elles
réduisent respectivement les tours manifestement vides et la latence d'une ressource périssable sans
changer le classement économique normal du portefeuille.

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
