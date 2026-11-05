# Suite de nuit — OpexAI / OpenTTD 15.3 — 5 novembre 2026

## Cadre et décisions

- Worktree : `.wt_rail_loop_20261104` (branche `ccr-6d627d08-tlnphk`, HEAD au début `80df60e9241e03b328c98164b81fe8b45ee49b41`, dirty intentionnel).
- Docker : `openttd-lab:latest`, image `sha256:0480a863e164856797412ff4a0782621464a52087abbb9c056dd3587d46cac31` ; un seul conteneur actif à la fois, 10 CPU, 8 GiB, 10 workers.
- `rail_loop=1` reste le défaut, `rail_loop=2` conservé, `rail_loop=3` strictement opt-in ; `rail_fill=0` inchangé. Le défaut `v257_demand=1` est une **décision ultérieure explicite de l'utilisateur du 2026-11-05** (voir « Décision de défaut ») ; aucun push, merge, stash, reset ni clean.
- Évaluation économique `--probes 2 --value-guard-max-loss-pct 100`; la garde à 100 % est un choix expérimental explicite, **pas** la garde habituelle de valeur à −5 %.

## V257-DEMAND — inventaire sans replay

### Décision de défaut

Sur instruction explicite de l'utilisateur du **5 novembre 2026**, `v257_demand=1` devient le **défaut pour les quatre difficultés** (easy, medium, hard, custom). Le réglage reste réversible à `0` ; la projection OFF supprime intégralement la couche V257-DEMAND et doit rester byte-exacte. Cette décision est distincte de la qualification économique et ne promeut ni `rail_fill` ni `rail_loop=3`.

**Dérogation explicitement assumée :** la porte A multimodale 40×5 reste **HOLD**, avec 39/40 paires exploitables, Δ profit **−27 122,69 £/an**, malgré les PASS A+B rail et B multimodal. Ce résultat n'est ni escamoté ni requalifié en PASS ; la décision utilisateur de changer le défaut prévaut sur ce signal négatif/incomplet. Aucun replay des portes économiques.

**Contrôle après changement de défaut.** `python -X utf8 -m unittest discover -s sweeps -p 'test_*.py' -q` : **3 427 tests, 17 échecs, 10 ignorés, 2 échecs attendus** ; journal `results/v257_default_full_suite_20261105.log`. Les **5/5 contrats V257-DEMAND passent**. La suite générale **n'est pas verte** : seul `test_b6_portfolio_causality` et deux `test_rail_long_v3_multi` étaient annoncés préexistants et admis ; la campagne actuelle trouve **trois** cas `test_rail_long_v3_multi` (sur `builder_rail.nut`, `task_v284.nut`, `invest_stall_fleet.nut`), soit un cas supplémentaire non admis. Tous les autres échecs hors tolérance sont listés ici, sans les effacer ni modifier leur source :

- `test_rail_long_20261103`: `test_both_stations_tested_at_equal_length_and_failed_long_falls_back` ;
- `test_rail_long_behavior_20261103`: `test_full_consist_needs_economic_volume_and_physical_cap`, `test_multitrain_requires_directional_pbs_certification_and_shared_orders`, deux sous-tests de `test_new_squirrel_has_no_common_parser_traps`, `test_off_projection_exact_hash_and_idempotence` (`builder_rail.nut`), `test_off_projection_fail_closed_when_partially_removed` (`builder_rail.nut`), `test_route_failure_retries_historical_length_at_most_once`, `test_station_length_and_short_capacity_threshold`, `test_tries_both_long_platforms_before_historical_fallback` ;
- `test_rail_long_v3_20261103`: `test_v1_v2_off_projection_is_idempotent_without_rewriting_fixtures` (`builder_rail.nut`) ;
- `test_rail_loop_v3_20261105`: `test_v3_off_is_exact_for_all_pre_v3_sources` (`info.nut`) — empreinte gelée avant la décision de défaut V257 et donc à réconcilier séparément ;
- `test_station_plan_precheck`: `test_only_guard_added_to_historical_rail_source` ;
- `test_rail_long_v3_multi`: troisième échec de projection OFF supplémentaire à la tolérance de deux.

**Bilan de tolérance :** 17 échecs = 1 B6 toléré + 2 multi tolérés + **14 non admis**. Le commit de la décision utilisateur ne constitue **pas** une approbation de ces 14 échecs. Les nombreux changements RAIL-LOOP/INVEST-STALL déjà présents dans le worktree ne sont pas inclus dans ce commit sélectif.

| Porte | Campagne JSON | Parties / paires | Verdict | Résultat |
|---|---|---:|---|---|
| A rail 40×5 | `results/v257_demand_gateA_40x5_20261104.json` | 80 / 40 | PASS | Δ profit +93 850,80 £/an ; p≈0,000570 ; IC95 [+50 592,83 ; +138 835,43] ; 29/11 |
| B rail 20×10 | `results/v257_demand_gateB_20x10_20261104.json` | 40 / 20 | PASS | Δ +94 682,40 £/an ; p≈0,132727 ; IC95 [+2 139,55 ; +191 276,35] ; 12/8. PASS de protocole ≠ effet significatif à p<0,05. |
| B multimodal 20×10 | `results/nuit_20261105_v257_demand_gateB_multimodal_20x10.json` | 40 / 20 | PASS `non_erosion` | Δ +37 185,35 £/an ; p=0,621513 ; IC95 [−112 556,85 ; +184 799,25] ; 11/9 ; valeur compagnie −0,218 %. |
| A multimodal 40×5 | `results/nuit_20261105_v257_demand_gateA_multimodal_40x5_r2.json` | 80 / 39 exploitables | **HOLD `incomplete`** | Δ −27 122,6923 £/an ; V/D/E 12/24/3 ; p=0,2144694 ; IC95 [−67 139,8974 ; +13 092,7436] ; valeur compagnie −1,244579 %. |

### Incident A multimodal

La relance `_r2` a effectivement exécuté 80 parties. **Un échec de santé AAAHogEx** sur la graine `246300` dans le bras `reference` : `noai_error[AAAHogEx]: Your script made an error`. Seulement 39/40 paires complètes. Verdict officiel `incomplete`; même les 39 paires exploitables ne démontrent pas +4 % (variation négative). Ne pas convertir en PASS ni rejouer les trois campagnes déjà PASS.

Manifestes SHA256 tels qu'enregistrés dans leurs JSON : A rail `16ef0b033809b78244ca28a1f957a014bc673ebe580387e87512021f371833c9` ; B rail `10e68da9c1fe73565b18631dc995ccd1c9a85c20a00263f5e71a917176edc4d4` ; B multimodal `10b65905073b769f480b8660fd16b2aeaf3cf0800f179f161632d36bd66f9188` ; A multimodal `_r2` `3c885b4d7cd71872727396a8df9e5b4685466745285ca97dd18dc62b11067523`.

## Combinaison B 20×10 rail seul

Campagne `results/nuit_20261105_combo_loop1_v257_fillF6_gateB_rail_20x10.json`, comparaison appariée à 20 graines (`202945` … `789380`) × 10 ans :

- Référence : `OpexAI[rail_sibling=1,rail_open=1,rail_loop=1,rail_fill=0,v257_demand=0,mode_air=0,mode_road=0,mode_water=0,probes=2]` ; AAAHogEx road/tram/ship/aircraft désactivés.
- Variante : même base + `rail_fill=1,v257_demand=1` ; boucle historique 1 inchangée, RAIL-FILL correction F6.
- **40/40 parties saines ; 20/20 paires, verdict `pass` selon `non_erosion`.** Δ profit moyen **+179 470,25 £/an**, médiane +161 872 £, victoires/défaites/égalité **17/3/0**, p Wilcoxon **0,00026130676**, IC95 bootstrap **[+102 854,20 ; +252 762,80] £/an**. Valeur de compagnie, ratio des moyennes, **+4,954984 %**, moyenne des ratios +5,6723 %. Garde de valeur configurée à 100 %.
- Empreintes bundle `21b8a3c91c1d4e76bb7ad644ce078d24adbc9f042c69c02f5a7a1730f08182eb` ; manifeste `e3df620985b2633471b591ae81355d56b4f69050986b3e8338f1a771e830bdd7`.
- **PASS économique expérimental, aucune promotion** : RAIL-FILL F6 n'a pas prouvé F2 (5 wagons ; observation 4), et les interactions ne sont pas une qualification physique de sécurité.

## RAIL-LOOP v3 — admission technique

Mode `rail_loop=3` demandé avec sortie arrière libre et constructible **au placement initial** de chaque quai fret, lead décalé, aucun remplacement/démolition aveugle des voies ou routes existantes ; prévention des autres transactions, PBS directionnels, Save/Load pendant construction, clones, projections OFF. Qualifier sur 17, 512, 314 et 8191, six ans, contre `rail_loop=1` ; exiger *strictement plus de boucles sur les quatre graines*, zéro rame perdue, santé 8/8 et exposition physique Save/Load. **Les portes A rail 40×5 et B rail 20×10 v3 sont interdites tant que tous ces critères ne passent pas.**

Diagnostic préalable du mode 2 : rejet `back_lead` sur 37 cas (23 rails déjà présents, 14 autres obstacles), d'où la réservation dès la première implantation. Le mode 2 n'avait pas passé l'amélioration sur chacune des graines. La compilation Squirrel et les tests statiques ne remplacent pas la certification par simulation.

### État et preuves v3

Implémentation expérimentale dans `ai/OpexAI/builder_rail.nut`, `rail_loop.nut`, `globals_pre.nut`, `settings.nut`, `info.nut`, `task_v284.nut` :

- `rail_loop=3` activé uniquement sur demande, quatre valeurs de difficulté inchangées à **1**. Modes historiques 1 et 2 conservés.
- Sélection des plans de quais fret par réservation logique des cases arrière, plans alternatifs (déplacement du quai entier, non destruction de routes/voies), validation après A*, avant devis et avant toute dépense ; métadonnées des leads arrière dans `platformA/B` persistables.
- Signal PBS de garde prévalidé au moteur sous `AITestMode` avant la transaction voie 2 ; PBS directionnels sur voie 2 AVANT raccordements. Raccordement de sortie (`GOAL`) avant entrée (`SRC`) pour limiter la possibilité de rejoindre une impasse en cas d'interruption.
- Journal `railLoopV3Txn` des pièces *avant* leur commande, confirmation avec signature de rail/ouvrage et rollback limité aux pièces neuves certifiées, non accessibles depuis les quais. En cas d'incertitude, HOLD sans démolition aveugle. Save/Load des transactions physiques interrompues mène à HOLD conservateur ; les recherches A* sans dépense peuvent être réessayées.
- **Limite de sûreté non levée :** duplication et croissance de flotte v3 désactivées intentionnellement car la réconciliation du VehicleID après interruption entre `CloneVehicle` et l'inscription n'est pas certifiée. Il serait faux de revendiquer la capacité 4–8 rames. Un dépôt à proximité immédiate d'une gare peut aussi rendre le PBS garde impossible, donc réduire l'exposition.
- Contrats locaux de géométrie et sécurité transactionnelle en cours de qualification ; projection OFF byte-exacte encore en contrôle au moment de cette entrée. Un test statique ne certifie ni un Save/Load interrompu au niveau moteur ni zéro rame perdue sur 6 ans.

### Smoke 4×6 effectué — **HOLD / fail_primary**

Campagne `results/nuit_20261105_rail_loop_v3_smoke_4x6.json`, `rail_loop=1` en référence contre `rail_loop=3` (autres réglages rail identiques), années 1970–1975, graines **17, 512, 314, 8191**, AAAHogEx rail seul. `--probes 6 --script-debug --line-telemetry --retain-savegames`, 10 workers, 10 CPU, 8 GiB, garde de valeur 100 %.

**8/8 parties complètes et 4/4 paires, zéro `failed_runs` ; verdict officiel `fail_primary`.** Δ moyen du profit annuel v3 − référence **−66 711 £/an**, médiane −122 299 £/an, victoires/défaites/égalités **1/3/0**, p Wilcoxon **0,375**, IC95 bootstrap **[−203 627 ; +95 413] £/an**, ratio des moyennes de valeur de compagnie **0,972627** (−2,737299 %). Ces résultats concernent v3 face au mode1, non OpexAI face à AAAHogEx.

| Graine | Commits `RLOOP phase=commit` mode1 | Commits v3 | Croissances mode1/v3 | Rejets v3 `guard_required_pre` | Condition v3 > mode1 |
|---|---:|---:|---:|---:|---|
| 17 | 0 | 0 | 0 / 0 | 17 | **NON** (égalité) |
| 512 | 0 | 0 | 0 / 0 | 31 | **NON** (égalité) |
| 314 | 1 | 0 | 6 / 0 | 34 | **NON** (régression) |
| 8191 | 0 | 0 | 0 / 0 | 17 | **NON** (égalité) |

Ces comptes sont extraits des huit journaux `results/nuit_20261105_rail_loop_v3_smoke_4x6_engine/*.log`, et mesurent les **événements de commit observés**, pas une reconstruction indépendante des infrastructures. **99 refus `guard_required_pre` v3**, révélant le blocage causal du PBS de garde avec la géométrie/dépôt historique. Aucune boucle v3 n'a été activée, donc aucun clone v3 n'est attendu (clonage explicitement désactivé par sûreté).

Les huit logs n'ont montré **aucune occurrence** des motifs de crash contrôlés (`vehicle_crashed`, `crashed train`, `train crashed`, `Lost train`) ; cette absence **ne démontre pas** à elle seule « 0 rame perdue ». Les sauvegardes ont été conservées (**576 fichiers `.sav` et 8 `.json`** dans `results/nuit_20261105_rail_loop_v3_smoke_4x6_saves`), mais **aucune injection de Save/Load en milieu de transaction n'a été validée par l'essai**. Sécurité physique des rames et reprise Save/Load : **HOLD / preuve insuffisante**. Les transactions ne se sont pas exposées en v3 du fait du rejet de garde.

Empreinte bundle figée : `8194d204aeb53f2439a8d5fa0a71931a1f10b33cd62e377a35a11cd912cb8dff` ; manifeste : `a766142495a8017e77fe89d40d2c4688ad4c18dc5d208d9f70c130eb500050f9`.

**Décision : portes A rail 40×5 et B rail 20×10 v3 NON LANCÉES**, car les quatre critères par graine échouent et le Save/Load physique n'est pas certifié. Aucun PASS ou capacité de plusieurs rames revendiqué. Prochaine correction technique possible : rendre constructible une fenêtre PBS de garde dès l'implantation initiale gare/dépôt, sans relâcher la sécurité des signaux ; conserver le refus strict tant que non certifié.

## Audit final et prochaines actions

Audit statique : `python -X utf8 -m unittest sweeps.test_rail_loop_v3_20261105 sweeps.test_rail_loop_v2_20261104 sweeps.test_rail_loop_20261104 sweeps.test_rail_fill_20261104 sweeps.test_v257_demand_20261104 -q` : **56/56 PASS** (13 v3, 4 v2, 20 historiques, 14 RAIL-FILL, 5 V257). Les projections v3→v2→v1→OFF sont byte-exactes sur leurs sources témoins et rejettent les fragments corrompus ; tests statiques Squirrel (délimiteurs et arités) PASS. `git diff --check` sans erreur. Aucun banc économique A/B v3 n'a été lancé faute d'admission ; ne pas confondre avec les portes V257 rail déjà terminées.

Contrôle final après le smoke : `docker ps` **vide** ; `git diff --check` **sans erreur** ; suite de 56 tests **PASS**. Worktree volontairement dirty, fichiers anciens et nouveaux non suivis préservés, rapport `docs/nuit_20261105_suite.md` présent. Aucun conteneur d'un autre agent interrompu.

Prochaines actions : (1) revoir la topologie gare/dépôt initiale pour une fenêtre PBS certifiable avant pose ; (2) développer la réconciliation sûre de VehicleID au clonage et le scénario injecté Save/Load en transaction ; (3) refaire le seul smoke de validation v3 après corrections, avant toute porte A/B et seulement sur nouvelles graines pour ces portes. Aucun défaut modifié, aucune promotion ni commit/push/merge/stash/reset/clean.
