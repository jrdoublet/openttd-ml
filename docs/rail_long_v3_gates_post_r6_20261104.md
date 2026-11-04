# RAIL-LONG v3 — qualification économique après le correctif R6 (4 novembre 2026)

## Protocole pré-enregistré, avant mesure

Mandat utilisateur explicite : quatre portes **A et B**, chacune en **rail seul** et en **multimodal**, après clôture du correctif transactionnel et Save/Load R6. Les campagnes historiques `rail_long_v3_gate_*_20261104_r1` (bundle `4087fdfa4b7f8d87020861cb01cd2a130374e343bc8b0f32354dfbd87abaf355`, sondes 6, garde de valeur 100 %) **ne qualifient pas** le code corrigé. Le bundle du smoke technique R6 était `be98d35222c11fb77ab859aa88ca7d28c44f305202ad964fe66ad8bdc3a64688`. La nouvelle empreinte doit être contrôlée dans chaque manifeste, et les quatre empreintes doivent être identiques entre elles ; sinon les résultats ne sont pas cumulés comme qualification d'un même état source.

- Dépôt : `/openttd-ml/.wt_sibling_20261102` ; branche `exp/rail-sibling-20261102`, HEAD `99f29d9c858f390de6193978a4f12d3fbdb48127`, arbre local **sale** contenant des ajouts v3 non suivis. Aucune modification de code IA pendant les bancs ; `rail_long` reste au défaut `0`. Les opt-in `invest_stall` et `double_grow` restent au défaut `0`.
- **Seule intervention testée** : `rail_long=0` contre `rail_long=3` dans le même arbre ; métrique primaire : `profit_year` OpexAI ON moins OpexAI OFF, appariée par graine, même monde, même AAAHogEx. Le ratio contre AAAHogEx n'est pas le résultat causal primaire.
- **Rail seul** : référence `OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1,rail_long=0]`, variante identique sauf `rail_long=3` ; AAAHogEx avec route, tram, bateau et avion désactivés (`disable_veh_roadveh=1`, `disable_veh_tram=1`, `disable_veh_ship=1`, `disable_veh_aircraft=1`).
- **Multimodal** : référence `OpexAI[rail_sibling=1,rail_open=1,rail_long=0]`, variante identique sauf `rail_long=3` ; AAAHogEx modes par défaut. Les deux modes partagent `rail_sibling=1` et `rail_open=1`, donc les conclusions sont **conditionnelles à ces réglages communs**, pas aux défauts absolus.
- **Moteur/protocole** : OpenTTD 15.3, départ 1970, carte 256×256 (`--map-size 8`), `--probes 2` identique pour les deux bras, sans télémétrie mensuelle coûteuse ; une répétition par graine, graines canoniques du lanceur (40 pour A ; 20 pour B), `--cpus 10 --memory 8g --max-workers 10`, image `openttd-lab:latest` figée, cache `openttd-lab-home`, montage parent Windows `C:\Users\jr\vscode\openttd-ml\openttd-ml`. Un seul conteneur de banc à la fois et contrôle `docker ps` avant lancement.
- **A (rail puis multimodal)** : protocole V102 canonique **40 graines × 3 ans**, règle `gain_short`, `--required-seeds 40 --required-years 3 --years 3 --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5`. Critères : 40 paires complètes et saines ; delta moyen ≥ 4 % de la moyenne OFF, p Wilcoxon <0,05, borne basse IC95 bootstrap >0 et garde moyenne de valeur −5 %.
- **B (rail puis multimodal)** : **20 graines × 10 ans**, `non_erosion`, `--min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5`. Critères : 20 paires saines, borne haute IC95 bootstrap ≥0 et ratio moyen de valeur ≥95 % ; un passage ne prouve pas un gain. L'utilisateur a **expressément demandé les deux B**, donc elles seront réalisées même si A échoue ; dans ce cas leur statut est diagnostic hors parcours d'adoption, sans modification de défaut.
- Bootstrap du harnais 20 000 réplications, graine 0 ; contrôles des quatre trimestres terminaux, couverture, `comparison_complete`, `adoption_sample_complete`, `metric_coverage_complete`, NoAI et exposition physique `rail_long=3` dans les journaux disponibles. L'exposition v3 est déjà attestée en moteur par le diagnostic R3 et les reprises R6, mais ne préjuge pas de son incidence statistique sous `probes=2`.
- Avant portes, tests ciblés 21 v3 et 11 v2 ainsi que projections OFF ; smoke causal de compilation une graine × un an hors échantillon d'adoption. Ne rejouer ni R3 ni les reprises Save/Load R6. Aucun commit, push, merge, stash, reset, clean, changement de défaut ou interruption de conteneur externe.

Identifiants réservés (nouveaux, résultats non écrasés) :

| Étape | Campagne |
| --- | --- |
| Smoke causal | `rail_long_v3_post_r6_smoke_pair_1x1_20261104_r1` |
| A rail seul | `rail_long_v3_post_r6_gate_a_rail_40x3_20261104_r1` |
| A multimodal | `rail_long_v3_post_r6_gate_a_multimodal_40x3_20261104_r1` |
| B rail seul | `rail_long_v3_post_r6_gate_b_rail_20x10_20261104_r1` |
| B multimodal | `rail_long_v3_post_r6_gate_b_multimodal_20x10_20261104_r2` (r1 bloquée avant gel Docker ; r2 exécutée) |

## Résultats et audit

### Résultats effectivement obtenus

Les **quatre campagnes économiques** ci-dessous sont **complètes, saines et correctement appariées** : 0 partie défaillante ; `comparison_complete=true`, `adoption_sample_complete=true`, `metric_coverage_complete=true`, et 4/4 trimestres valides au checkpoint terminal pour tous les bras OpexAI. Les intervalles de confiance bootstrap utilisent 20 000 tirages et la graine 0. La quatrième campagne, B multimodale, a été achevée après retour de Docker sous le nouvel identifiant r2, sans remplacer ni interpréter la tentative r1 incomplète.

| Porte | Paires | Δ profit_year moyen (ON−OFF) | Médiane | V / D / E | Wilcoxon p | IC95 bootstrap du Δ | Ratio valeur ON/OFF | Verdict brut |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| A rail seul, 40×3 | 40/40 | **−7 389,60 £/an** | −36 344 £/an | 18/22/0 | 0,675257 | [−65 549,55 ; +52 721,88] £/an | −2,4225 % | `fail_primary` |
| A multimodal, 40×3 | 40/40 | **−64 458,45 £/an** | −83 228,50 £/an | 16/24/0 | 0,108799 | [−128 444,63 ; −1 225,80] £/an | −0,7601 % | `fail_primary` |
| B rail seul, 20×10 | 20/20 | **+47 146,05 £/an** | +23 265,50 £/an | 11/9/0 | 0,329983 | [−77 912,85 ; +154 969,25] £/an | +1,5082 % | `pass` (`non_erosion`) |
| B multimodal, 20×10 | 20/20 | **+99 740,75 £/an** | +36 819 £/an | 11/9/0 | 0,245487 | [−60 770,65 ; +262 410,65] £/an | +1,7590 % | `pass` (`non_erosion`) |

Seuil de gain A : +42 280,03 £/an en rail seul et +99 625,29 £/an en multimodal, outre Wilcoxon p < 0,05 et IC95 bas > 0. La garde de valeur −5 % passe dans les **quatre campagnes**. Les deux A échouent : aucune adoption n'est justifiée. Les **deux B passent en non-érosion**, mais ne prouvent ni gain ni équivalence économique : leurs IC95 englobent zéro. Les deux B restent des **diagnostics hors parcours d'adoption**, puisque leurs portes A respectives ont échoué.

### Chronologie et indices de mécanisme

À partir des checkpoints appariés du 1er décembre de chaque année, différence moyenne de `profit_year` ON−OFF, en **k£/an** :

| Année | A rail, 40 graines | A multimodal, 40 graines | B rail, 20 graines | B multimodal, 20 graines |
| --- | ---: | ---: | ---: | ---: |
| 1970 | −3,9 | −2,4 | +1,5 | −0,9 |
| 1971 | +11,5 | −12,8 | +45,3 | +9,4 |
| 1972 | −7,4 | −64,5 | +34,8 | +5,3 |
| 1973 | — | — | −17,0 | −2,6 |
| 1974 | — | — | −6,0 | +40,2 |
| 1975 | — | — | +21,7 | +102,2 |
| 1976 | — | — | +31,6 | +94,6 |
| 1977 | — | — | +31,8 | +176,3 |
| 1978 | — | — | +38,2 | +61,3 |
| 1979 | — | — | +47,1 | +99,7 |

Les échantillons A (40 graines) et B (20 graines) diffèrent : ne pas comparer leurs niveaux comme un effet temporel à graines constantes. À fin 1972, le bras v3 compte en moyenne **1,00 véhicule ferroviaire de moins** en A rail et **2,33 de moins** en A multimodal ; dans ce dernier, il compte aussi **1,18 avion de plus** et **0,45 véhicule routier de plus**. En B rail, le différentiel des véhicules ferroviaires passe de −1,55 fin 1974 à −0,65 fin 1979. **En B multimodal, v3 dispose à fin 1979 de 3,80 véhicules ferroviaires de moins et de 3,00 avions de plus en moyenne**, avec un delta de profit annuel positif non significatif. Ces changements montrent une interaction plausible entre investissement et composition du parc, mais **ne prouvent ni la cause exacte, ni la rentabilité marginale des allongements**. Les variations par graine sont importantes (A multimodal : plus mauvais −569 273 £/an sur 802204, meilleur +346 662 £/an sur 100).

La télémétrie physique détaillée et `script-debug` n'ont pas été activés dans ces portes (`probes=2`, conformément au protocole économique). Les journaux moteur des 20×10 rail sont vides ; **aucun décompte physique d'`upgrade_done` par graine ne peut être inféré de ces résultats**. Les modernisations v3 certifiées dans le diagnostic R3 et les trois reprises Save/Load R6 restent la preuve d'exposition technique distincte.

### Provenance, empreintes et limites

- Smoke apparié 1×1 : `rail_long_v3_post_r6_smoke_pair_1x1_20261104_r1`, 2/2 parties saines ; bundle **`071e51b440cc105aab5adf3fcd56415d9e02fbd2d575aab487b224488227b12c`** ; résultat `diagnostic_only`, non extrapolable.
- A rail : même empreinte `071e51b4…`.
- A multimodal, B rail et B multimodal r2 : **`dd1fb8e341486444bf2afd07fa4c86368c02b84e12e65660bd7bca1f9893cc3d`**. Identité exacte confirmée entre ces trois nouvelles campagnes.
- La seule différence de source entre `071e51b4…` et `dd1fb8…` est un enrichissement des journaux de diagnostic dans `ai/OpexAI/invest_stall_fleet.nut` (capacités et identités des wagons), derrière `invest_stall=0` dans les deux bras. La comparaison **ON/OFF au sein de chaque porte** reste correctement figée. Il serait néanmoins faux de présenter les **quatre portes** comme une qualification à empreinte unique ; aucun code IA n'a été changé par ce chantier pendant un banc.
- Les trois anciennes campagnes au bundle `4087fdfa…` étaient sur la version antérieure à R6 et une garde de valeur 100 %. Elles ne sont pas combinées aux nouveaux résultats.

**Incident Docker r1, résolu sans modifier le moteur ni les résultats historiques :** la tentative `rail_long_v3_post_r6_gate_b_multimodal_20x10_20261104_r1` était restée bloquée avant tout manifeste/bundle/checkpoint dans son client `docker run` ; le même problème affectait alors un conteneur minimal. Après vérification d'absence de conteneur, seuls les deux clients Docker de notre propre tentative ont été arrêtés, pas Docker Desktop, WSL ni les autres agents. Le 4 novembre, le test de démarrage `docker run --rm --cpus=1 --memory=1g --memory-swap=1g openttd-lab:latest python3 --version` a réussi (Python 3.12.16). L'inventaire des 123 fichiers AI du bundle B rail a confirmé leur identité avec le code source avant gel. **La porte B multimodale r2 a ensuite réussi : 40/40 parties, aucun `failed_runs`, 20/20 paires, couvertures complètes et 40 relevés OpexAI terminaux à 4/4 trimestres, image Docker inchangée, même bundle `dd1fb8…` que A multimodal et B rail, `pass non_erosion` avec garde valeur −5 % tenue.** Preuves `results/rail_long_v3_post_r6_gate_b_multimodal_20x10_20261104_r2.{json,jsonl,manifest.json,console.log}` et bundle figé `_bundle`. L'ancien `r1` n'a pas été recyclé ni présenté comme une mesure.

**Verdict final des quatre portes demandées : A rail FAIL, A multimodal FAIL, B rail PASS non-érosion diagnostique, B multimodal PASS non-érosion diagnostique. Décision d'adoption : NO-GO** pour `rail_long=3` car les **deux A 40×3 ont échoué**. Le défaut reste `0`. Aucun commit, push, merge ou changement de défaut.
