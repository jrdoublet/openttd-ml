# Correctifs — revue de code 2026-09-15

Synthèse des constats des 19 étapes de revue (`docs/revue_code_2026-09-15_plan.md`, fichiers
`docs/revue/2026-09-15_etape_01..19_*.md`), regroupés **par mécanisme** et non par étape. Rien
n'est corrigé par ce document : il priorise, il tranche la gravité de groupe, il propose un ordre
et un modèle/effort de **correction**, sur le modèle de `docs/revue_code_2026-09-06_correctifs.md`.

**Recomptage.** 132 constats sur 19 étapes : **29 P1, 52 P2, 51 P3**. Ils sont couverts par
**21 groupes de mécanisme** (les 29 P1 tiennent dans **14** d'entre eux). Aucun constat n'est perdu :
ceux qui ne rejoignent aucun groupe sont listés en fin de document avec le commit auquel les
greffer.

**Barème d'effort** : niveau du skill `/code-review` (low/medium/high/xhigh/max) appliqué à la
**correction**, pas à la relecture. Repère repris du 09-06 et confirmé par cette passe : la
correction d'un bug de logique localisé réussit bien à **Sonnet 5** ; un correctif qui touche une
**méthodologie de mesure**, une **garantie d'optimalité** ou l'**unité d'une grandeur économique**
mérite **Opus 5**. Mapping Codex : sol ≈ Opus, terra ≈ Sonnet.

> **Réconciliation 2026-09-17 — B6/06.11.** Le défaut de péremption du vivier incrémental est
> désormais mesuré sans réintroduire le refresh unsafe :
> `results/review_b6_0611_join_resolved_5x6.json`, 10/10 runs sains. 136/348 sélections
> incrémentales choisissent un top recyclé ; sur 127 tops fret sondés, 117 sont repricés exactement
> et 6/114 cas décidables changeraient d'élection. Le signal prouve un effet local de 06.11 mais pas
> un bénéfice aval d'un refresh général. Le patch concurrent qui perdait subventions/extensions
> reste retiré ; `portfolio_cache` est conservé et aucun 20×10 n'est lancé.

**Ce que la revue a changé par rapport au 09-06.** Le mode d'échec dominant n'est plus l'erreur de
calcul, c'est l'**artefact de mesure** — et la revue le retrouve à trois étages superposés : le
harnais publie des grandeurs qui ne sont pas celles qu'il nomme (Tier 0), le code in-game publie
des constantes sur des canaux de banc (Tier 2, M1), et plusieurs drapeaux sont **structurellement
incapables de différer de leur contrôle** (H2, M2). Tant que ces trois étages tiennent, tout banc
mesure autre chose que ce qu'il annonce, y compris les bancs qui serviront à valider les
correctifs de ce document. D'où l'ordre : le harnais d'abord, le comportement ensuite.

---

## Tier 0 — Avant tout nouveau banc : le harnais ne mesure pas ce qu'il annonce

Ce tier n'améliore aucune partie. Il rend interprétable tout ce qui suit. Les cinq groupes sont
indépendants les uns des autres et peuvent partir en parallèle.

### H1. La règle d'adoption du projet n'est appliquée par aucun script

**Constats** : 17.2 (P1), 18.4 (P1), 17.5 (P2).

- `sweeps/bench_1v1_5y_20seeds.py:708-725` — le verdict `pass`/`fail_*` du protocole C66.4 se
  décide sur `primary_stats["mean"] >= min_useful_primary_delta` et sur un ratio de moyennes,
  rien d'autre. Le bloc `decision_rule` publié (`:733-739`) l'assume : `"primary_rule":
  "mean(variant-reference) >= min_useful_primary_delta"`.
- `:445-447`, `:467-468` — le test des signes **est calculé**, correctement, ex æquo exclus
  (`sign_test_n_excluding_ties`, `exact_sign_test_p`, binomial exact bilatéral) — et **n'entre
  dans aucune décision**. Le rapport peut imprimer `verdict=pass` et `p_signes=1.0` sur la même
  ligne (`:1110-1113`).
- `sweeps/bench_v2.py:556-607` — le banc officiel apparié n'a pas de test des signes du tout :
  seulement `arm_a_beats_arm_b` (`:599`) et un `n` qui **inclut les ex æquo**. Ni défaites, ni
  ex æquo, ni p-valeur, ni différences brutes par graine ne sortent dans le JSON : le test n'est
  même pas reconstituable à la main a posteriori. Idem dans `bench.py`, `head_to_head.py`,
  `diag_c63_c58.py`.
- `bench_1v1_5y_20seeds.py:472-498` et `:707` — la garde de valeur écarte à raison les paires à
  dénominateur ≤ 0 et publie le compte d'exclusions, mais ce compte n'entre dans aucune décision :
  19 graines en faillite sur 20 laissent la garde trancher **sur une seule graine**, avec
  `comparison_complete=True`.

**Gravité de groupe : P1 — la plus haute du lot.** La méthode écrite (`ai/OpexAI/CLAUDE.md:97-100`,
« test des signes d'abord, ≥ 15/20, p < 0,05, moyennes ensuite ») n'existe dans aucun code qui
rend un verdict. C'est la porte par laquelle les 82 défauts actifs sont entrés et par laquelle
entreront tous les correctifs de ce document. 17.5 est élevé de P2 à P1 au sein du groupe : il
partage le mécanisme exact de 17.2 (une statistique juste, publiée, non branchée sur la décision).

- **Modèle : Opus 5, effort high** (Codex sol, high). Diff court, enjeu maximal : il faut trancher
  ce que « fail-closed » signifie sur les **statistiques** et pas seulement sur les parties, et
  décider ce qui l'emporte quand signes et moyennes divergent. C'est l'audit statistique
  d'adoption, le seul type de tâche où Sonnet avait laissé passer quelque chose au 09-06 (C29.3 →
  C31).
- **Opportuniste** : la fiche C66.4 (`docs/taches.md:289-291`) coche déjà « V/D/égalités et test
  des signes excluant les égalités » — la case est optimiste : le calcul existe, le verdict ne
  l'utilise pas. Corriger la fiche dans le même passage, sinon la prochaine lecture conclura que
  le point est clos.

### H2. Un bras de banc qui ne pouvait pas différer de son contrôle (constat initial G0, désormais clos)

**Constats** : 18.1 (P1), 18.2 (P1), 01.2 (P1), 05.1 (P1), 18.3 (P2), 01.3 (P2), 01.4 (P2),
01.5 (P2), 01.6 (P2), 06.6 (P2), 11.2 (P2), 14.5 (P2), 01.7 (P3).

Un seul mécanisme, deux causes qui se renforcent.

*Côté harnais — le banc ne sait pas ce qu'il a joué.*
- `sweeps/bench_v2.py:238-239` — l'arm nu `"OpexAI"` est construit avec un tuple de réglages
  **vide** : il hérite de tout ce que `info.nut` déclare le jour du run. `"arms": args.arms`
  (`:667`) n'enregistre que la chaîne : le JSON ne permet pas de savoir a posteriori quelle
  configuration de référence a tourné. C'est G0 littéralement, neuf jours plus tard.
- `bench_v2.py:90-228` — `parse_opex_variant` valide les bornes mais ne compare **jamais** la
  valeur fournie au défaut déclaré : rien n'empêche d'épingler la même valeur non standard dans
  les deux bras. C'est exactement le cas `feeder_mail_strict_orders` (01.3) : les deux bras
  pinnent `feeder_candidates=1` (défaut 0), `feeder_portfolio=0` (défaut 1) et
  `feeder_hub_check=0` (défaut 1). Le résultat, négatif compris, ne se transporte pas au défaut
  adopté.
- `bench_v2.py:111-222` — `staged_bootstrap` (défaut 1, `info.nut:2432`) est **inexprimable** par
  le harnais : `OpexAI[staged_bootstrap=…]` lève `ValueError`. Quatre autres réglages actifs
  (`vivier_ratio_filter`, `feeder_hub_wait_max`, `feeder_hub_min_days`, `air_joined_stop_limit`)
  sont pinnables mais jamais forcés, donc suivent le défaut courant sans avertissement (01.6).

*Côté code — le bras traité et le bras de contrôle produisent le même comportement.*
- `settings.nut:38-39` — `if (roadPaxCatchment > 0)` refuse la valeur 0, donc le bras de contrôle
  documenté `road_pax_catchment_pct = 0` conserve 86 (`globals_pre.nut:21`). Et même s'il
  passait, `candidates.nut:2242-2244` le plancherait à 1 %, jamais à 22 %. Le `t = 2,48 / 14/20`
  cité en `info.nut:2131-2132` est à re-qualifier (01.2).
- `info.nut:210` / `globals_pre.nut:410` — `event_vehicle_autoreplaced` est actif, jamais lu, et
  sa globale n'est lue par personne (01.4). Idem `rail_min_distance` (`info.nut:2421`, défaut 25,
  aucune lecture, 01.7). Un bras qui les déplace produit des ex æquo lus comme « le drapeau n'a
  pas joué ».
- `scheduler_tasks.nut:682` — `town_growth_skip_noop` ne peut rien mesurer : `_tryTownGrowth`
  n'a aucun `return true` (`task_town.nut:53-219`, confirmé deux fois, étapes 11 et 15), donc la
  condition se réduit au drapeau seul et la branche que le réglage est censé activer n'a jamais
  de comparaison à faire (11.2).
- `projects.nut:1398` / `:1462` — sous `portfolio_dynamic_batch = 1`, les projets de flotte sont
  jetés du vivier sans être régénérés quand `fleetPlan = null`. Inerte au défaut, le bug ne mord
  **que dans le bras expérimental** : il biaise silencieusement l'A/B qui doit trancher ce
  réglage, et retire du vivier exactement l'arbitrage que C34.2 mesure (06.6).
- `info.nut:1648-1670` — `abandon_cooldown_days` (365) et `abandon_gen_filter` (1) portent
  toujours les défauts d'avant G0, sans commentaire référençant la décision du 09-06. Ils coupent
  le vivier à cinq sites indépendants (`candidates.nut:2295`, `:2603`, `:2674`, `:2935`, `:3353`).
  **La décision de G0 n'a jamais été rendue** (05.1).
- `task_feeders.nut:332-334` vs `builder_road.nut:1278`, `:1570` — `feeder_mail_strict_orders=0`
  ne restaure le comportement legacy que pour le camion postal, jamais pour les bus feeder, dont
  le correctif est inconditionnel. Le « banc causal » annoncé par la description du réglage
  (`info.nut:1305`) ne compare pas des bras symétriques (14.5).
- `globals_post.nut:9`, `:24`, `:25` — trois plafonds documentés comme actifs ne sont lus nulle
  part ; `ROAD_MAX_NEW_LINES_PER_YEAR` est passé de 36 à *aucun* au collapse `portfolio_v2` sans
  que ce soit mesuré (01.5).

**Gravité de groupe : P1.** Pris un par un, la moitié de ces constats sont P2/P3 parce qu'ils sont
inertes au défaut. Ensemble ils disent une seule chose : **le protocole ne peut pas garantir qu'un
bras mesure ce qu'il annonce**, ni au moment du run, ni a posteriori.

- **Volet harnais et audit — Modèle : Opus 5, effort high** (Codex sol, high). Trois livrables :
  (1) résoudre et **journaliser dans le JSON** la liste complète des réglages effectivement joués
  dans chaque bras, contrôle inclus ; (2) refuser — ou au minimum signaler — un épinglage
  identique hors défaut dans les deux bras ; (3) rendre les 227 réglages exprimables, ou
  déclarer explicitement la liste blanche comme incomplète. Le volet **audit d'adoption** des
  82 défauts actifs part du triage déjà fait en 01.6 (18 avec 20 graines + p-value, **43 avec
  20 graines sans p-value lisible**, 4 sur petit banc, 9 sans trace de banc, 8 sans aucune
  mention dans `docs/`) : le traiter **par lots**, pas réglage par réglage.
- **Volet code — Modèle : Sonnet 5, effort low à medium** (Codex terra, low). Correctifs
  mécaniques et indépendants : la garde `> 0` de `settings.nut:38-39` ; le retrait ou le câblage
  de `event_vehicle_autoreplaced` et `rail_min_distance` ; la régénération inconditionnelle des
  projets de flotte (06.6) ; le `return true` manquant de `_tryTownGrowth` (11.2) ; les trois
  commentaires de `globals_post.nut` qui décrivent des bornes inexistantes (01.5).
- **Décision à rendre, pas à coder** : G0 sur `abandon_gen_filter`/`abandon_cooldown_days` (05.1)
  attend une confirmation humaine depuis le 09-06. Trancher **maintenant** : soit les remettre à
  0 en attendant un banc isolé, soit assumer explicitement le défaut dans `info.nut` avec la
  justification. Le statu quo silencieux est le pire des trois.

### H3. Le banc publie un compte de véhicules qui n'est pas une flotte

**Constats** : 17.1 (P1), 19.4 (P1), 17.4 (P2), 17.10 (P2).

- `bench_1v1_5y_20seeds.py:264` — `"n_vehicles": veh_dec["vehicle_pool_entries"]`, le compteur
  **brut** du pool (têtes + wagons + ombres + rotors + parties articulées), alors que le décodeur
  rend au même endroit `primary_vehicles_count`. Sur la fixture de contrôle : **26 pour
  21 véhicules réels (+23,8 %)**, et le selftest **fige** l'écart (`:1137-1138`). Surestimation
  **fonction de la composition de flotte** — 0 % pour une flotte routière pure, +100 % par avion,
  +200 % par hélicoptère, +N par convoi de N wagons — donc fonction du bras. Propagé tel quel par
  `bench_v2.py:483` dans tous les JSON de campagne.
- `bench_v2.py:361` — `"n_vehicles": len(chunks.get("VEHS", {}))`, le compte le plus faux du
  dépôt : pool entier, **tous propriétaires confondus**, véhicules d'effet et catastrophes
  compris. 33 pour 21 véhicules réels, dont 7 entrées de type 4 qui n'appartiennent à personne.
  C'est ce `n_vehicles`-là que lit le plancher du smoke test (`smoke_test.py:55-56`) : **le
  plancher « au moins 1 véhicule » est franchi par la fumée d'une usine**, même si l'IA n'a rien
  construit (17.10).
- `bench_1v1_5y_20seeds.py:266-267` — `primary_vehicles` et `primary_vehicles_by_mode`, la
  contrepartie correcte, sont enregistrés **et jamais lus** : absents de `SUCCESS_METRICS`
  (`bench_v2.py:68-74`), donc ni `arm_statistics`, ni `paired_comparisons`, ni
  `build_policy_comparison` ne les touchent (17.4).
- `diag_1v1_shared_monthly.py:108`, `:140`, `:755-758` — `qualified_modes` est recopié dans le
  retour de `vehicle_breakdown` puis **jamais lu**, alors que `physical_counters.py:46-51`
  déclare `QUALIFIED_MODES["water"] = False`. `mode_totals`, `n_units`, `rolling_capital`,
  `profit_total` et `profit_per_vehicle` intègrent donc silencieusement un mode que le projet
  documente lui-même comme non qualifié, jusque dans `render_final_comparison` (`:995-1024`).

**Ce que la synthèse ajoute aux étapes 17 et 19.** La fiche C66.1 (`docs/taches.md:105-108`) a
**délibérément** gardé `n_vehicles` brut « pour assurer la rétro-compatibilité sans dérive
silencieuse », et a livré le décodeur correct, qualifié par égalité ensembliste exacte contre
l'API NoAI (`:113-120`). Le défaut n'est donc **pas** le décodeur — il est juste et testé. Le
défaut est que **les consommateurs n'ont jamais été migrés** : tableaux, moyennes par bras,
plancher de smoke et agrégats mensuels lisent encore le brut, ou ignorent le gating. La case `[x]`
de C66.1 est à rouvrir sur ce seul volet.

**Gravité de groupe : P1.** Tout énoncé « profit par véhicule », « valeur par véhicule » ou
« rendement par véhicule » du projet — dont le « 93 % de rendement par véhicule » déjà retiré une
fois et le « 564 véhicules contre 102 » de `ai/OpexAI/CLAUDE.md:17-20` — passe par ce
dénominateur.

- **Modèle : Sonnet 5, effort medium** (Codex terra, medium). Travail mécanique une fois la
  décision prise, et la décision est courte : garder `n_vehicles` brut sous son nom honnête,
  migrer **tous** les consommateurs vers `primary_vehicles*`, ajouter le gating `qualified_modes`
  à `diag_1v1_shared_monthly.py`, et brancher le plancher du smoke sur le décodeur. Le selftest
  `:1137-1138` doit être réécrit en même temps, sinon il rebloque le correctif.
- **Opportuniste** : à faire **avant** le dépouillement du diagnostic P1 C63/C58, qui compte des
  véhicules par mode.

### H4. Le fail-closed s'arrête à la partie, jamais aux statistiques ni à la vie de l'IA

**Constats** : 17.3 (P1), 17.6 (P2), 17.7 (P2), 17.8 (P2), 17.9 (P2), 17.11 (P2), 17.12 (P2).

Même motif à six niveaux : **une absence est lue comme une valeur**.

- `bench_1v1_5y_20seeds.py:893-958` — sur le chemin C66.3 (le banc de référence, celui qui a
  produit le 0/20 cité par `CLAUDE.md:15-17`), rien ne compare `len(by_game)` à `len(exps)` ni
  `len(summary)` à `2 × len(exps)`. Une partie qui ne rend aucune ligne disparaît : moyennes sur
  19 graines, `failed_runs` vide, code de sortie 0, en-tête « 20 graines ». La garde existe — mais
  seulement sur le chemin à deux politiques (`:700-705`) (17.3).
- `game_health.py:486-492` + `:390-395` — `stagnation_suspect` exige `no_signal`, qui exige que
  `company_value` n'ait pas bougé sur 3 pas. Or `company_value` intègre trésorerie, emprunt et
  dépréciation : **une compagnie qui possède un seul véhicule ou un emprunt qui court ne peut
  jamais être `no_signal`**. Une partie C56 (« l'IA cesse toute activité après 1970 sans erreur
  NoAI ») ressort `complete`, `run_ok=True`, `game_ok=True`, et entre dans les moyennes comme une
  partie saine. Le nom `earning_without_expansion` est trompeur : `value_changes` (`:381-383`)
  compte aussi une valeur qui **s'effondre** (17.6).
- `game_health.py:453-493` — `classify_company` n'impose **aucun plancher d'activité** : pas de
  condition sur `primary_vehicles > 0`, `n_stations > 0` ni `company_value > 1`. Un AAAHogEx qui
  se charge, crée sa compagnie et ne joue pas produit un duel `game_ok=True` où OpexAI « gagne »
  contre un adversaire à l'arrêt. Le smoke test, lui, connaît ce plancher
  (`smoke_test.py:48-59`) (17.7).
- `game_health.py:313-335` — rien ne vérifie le **nombre** ni la continuité des checkpoints : une
  partie dont 48 sur 60 manquent mais qui atteint décembre passe `complete`. `bench_v2.py:485`
  calcule pourtant `n_savegames`, jamais comparé à rien. Effet second : `ACTIVITY_RECENT_STEPS =
  3`, compté en checkpoints et non en mois, devient silencieusement une fenêtre de plusieurs
  années (17.8).
- `game_health.py:524-534` — sans `engine_log_path`, la garde `missing_engine_log` est inopérante
  et la partie ressort `game_ok=True` sans aucune erreur, ni attribuée ni non attribuée.
  Exposition latente aujourd'hui (`main()` la renseigne toujours), active pour tout autre
  appelant (17.9).
- `smoke_test.py:87` — `summarise(rows)` sans `expected_last_year` : une partie arrêtée au bout de
  3 mois sort `run_ok=True`. La porte de PR laisse passer un gel précoce, c'est-à-dire C56 (17.11).
- `smoke_test.py:69` — `enable_engine_failure_capture` n'est ni importé ni appelé. C'est lui qui
  pose l'**unique `timeout` du dépôt** : sans lui, un OpenTTD bloqué fait pendre la CI
  indéfiniment, et un crash moteur remonte en trace Python sans qu'aucun
  `results/smoke_ci.json` ne soit écrit (17.12).

**Gravité de groupe : P1.** 17.6 et 17.7 combinés signifient que **le mode d'échec non élucidé
n°1 du projet (C56) est invisible pour le banc**, des deux côtés du duel. C'est plus grave que
n'importe lequel des P2 pris isolément : le banc est l'arbitre externe de toute décision du
projet, et il déclare sain le seul état qu'il devrait rendre impossible.

- **Modèle : Opus 5, effort high** (Codex sol, high) pour 17.6 + 17.7 : définir un plancher
  d'activité qui distingue « la valeur bouge » de « la valeur s'effondre », et qui vaille pour
  l'adversaire sans le handicaper, est une question de méthode — c'est le quatrième faux positif
  rouvert le 09-14, et le seul encore ouvert.
- **Modèle : Sonnet 5, effort medium** (Codex terra, medium) pour 17.3, 17.8, 17.9, 17.11, 17.12 :
  cinq gardes mécaniques, chacune de quelques lignes, chacune sur le patron d'une garde qui existe
  déjà ailleurs dans le même fichier. À faire dans un seul commit.
- **Opportuniste** : c'est l'objet exact de C66.2 (`docs/taches.md:162`, « séparer santé du
  moteur, santé des compagnies et activité de l'IA ») et de C66.5 (critères de clôture).

### Clôture H1 / H3 / H4 — 2026-09-16

Ces trois groupes sont **corrigés et revalidés sur le workspace courant**.

**H1 — règle d'adoption réellement appliquée.**

- C66.4 exige désormais **20 paires** pour rendre un verdict d'adoption. Le test des signes exact
  bilatéral est premier : **≥ 15/20 victoires et p < 0,05** ; le seuil sur la moyenne du delta ne
  vient qu'ensuite. Un banc plus court reste exploitable mais son verdict est
  `diagnostic_only`.
- La comparaison est fail-closed sur la couverture : `primary_metric_n` et le nombre de
  dénominateurs positifs de la garde de valeur doivent couvrir toutes les paires planifiées.
- `bench_v2.py` publie maintenant V/D/égalités, `sign_test_n_excluding_ties`,
  `sign_test_p` et les deltas appariés par graine.
- **Limite vérifiée le 2026-09-16** : `bench_v2.py` reste un banc descriptif. Il publie
  `protocol_15_of_20_pass` quand `n == 20`, mais ne combine pas ce test avec un seuil de
  moyenne pour rendre un verdict d'adoption complet. L'autorité d'adoption reste donc C66.4
  (`bench_1v1_5y_20seeds.py`) ; aucun second protocole générique n'est inventé ici.

**H3 — le nombre de véhicules est une flotte physique.**

- `n_vehicles` désigne maintenant les véhicules primaires pilotables et vaut
  `primary_vehicles`; `vehicle_pool_entries` et `total_vehicle_pool_entries` gardent les
  comptes bruts nécessaires au diagnostic.
- `primary_vehicles` rejoint `SUCCESS_METRICS`; le smoke teste ce compteur et le diagnostic
  mensuel applique le gating `qualified_modes`. L'eau reste explicitement non qualifiée.
- Sur le 5×6 final, le pool brut dépasse la flotte primaire de **34 à 550 entrées** suivant la
  composition : l'écart H3 n'était donc pas cosmétique.

**H4 — fail-closed jusqu'aux statistiques.**

- la grille mensuelle attendue est contrôlée sans trou ; les jeux planifiés qui ne produisent
  aucune ligne et les identités de campagne incohérentes deviennent des échecs explicites ;
- l'absence de journal moteur est un `engine_error` ; le timeout est limité à
  `_run_experiment` et ne touche plus les téléchargements OpenTTDLab ;
- une compagnie sans véhicule primaire, sans gare ou avec `company_value <= 1` devient
  `inactive_company` ; `stagnation_suspect` n'est plus une issue économique admissible ;
- une valeur qui baisse sans expansion récente est distinguée de
  `earning_without_expansion` et classée `declining_without_expansion`.
- Régression ajoutée le 2026-09-16 : flotte/gares constantes, valeur
  `1200 -> 900` avec un rebond ponctuel tardif. Le rebond ne masque plus la baisse nette :
  `declining_without_expansion`, `stagnation_suspect`, `run_ok=false`,
  `game_ok=false`.

**Validations rejouées.**

- `python sweeps/test_physical_counters.py` → **7/7 OK** ;
- `python sweeps/test_game_health.py` → **26/26 OK** ;
- `python sweeps/bench_1v1_5y_20seeds.py --selftest` → OK ;
- `python sweeps/diag_1v1_shared_monthly.py --selftest` → OK ;
- compilation Python des harnais concernés → OK ;
- `git diff --check` → OK.

Smoke réel après les derniers correctifs :
`results/review_h134_smoke_ci_2x3_v3.json`, **2 graines × 3 ans**, résultat **PASSED**,
2/2 runs, 36 checkpoints par run, horizon `1972-12-01`, chunks physiques valides.

Diagnostic C66.4 final :
`results/review_h134_5x6_air_presite_v2.json`, **5 graines × 6 ans**, soit 10 parties
référence/variante. Audit programmatique : **10/10 jeux**, **20/20 lignes**
`complete/run_ok/game_ok`, 0 `failed_run`, **1 440 checkpoints = 20 × 72 mois exacts**,
0 trou, 0 erreur non attribuée, 0 véhicule non classé, 0 gare non résolue. Le manifeste fige
CPU=3, mémoire/swap=2g/2g, l'image
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`
et une seule différence effective : `air_presite: 0 -> 1`.

La comparaison de politiques donne V/D/E **2/3/0**, `p=1,0`, delta moyen de
`profit_year` **+20 419,8** et garde de valeur **+3,578 %**, mais rend
**`diagnostic_only`**. C'est le contrôle attendu : une moyenne positive sur 5 paires ne peut
plus être prise pour une adoption. Ces nombres valident le harnais, pas `air_presite=1`.

**Limite de cette preuve historique** : le workspace était dirty pendant ce diagnostic précis. Le manifeste enregistre le SHA Git
`769fdf9baed4042b830fbf24393c17a65f530a56`, `dirty=1` et le bundle exact
`fe883b9eb5d43a6a87961ac7cfa03380670e35599f84253285af28021a7da502`. La preuve est donc
attachée aux sources réellement exécutées, sans prétendre correspondre à un HEAD propre. Ce
`dirty=1` ne décrit pas l'état global ultérieur : le lot courant est parti d'un HEAD
`b5dd06e3cd47b55bbf508bc0c0bbac2e45e6a582` vérifié propre avant l'autorité B1/08.2. Le smoke
final post-correctifs enregistre ensuite honnêtement `dirty=1`, puisque les correctifs de cette
passe sont présents mais non commités.

### H5. La métrique nord — profit par opcode — n'est ni mesurée, ni comptée, ni dépensée

**Constats** : 18.5 (P1), 06.1 (P1), 11.4 (P2), 06.3 (P2), 07.2 (P2), 19.5 (P2), 01.8 (P3),
09.8 (P3).

- **Aucun banc ne la mesure (G0bis, inchangé depuis le 09-06)** : `SUCCESS_METRICS`
  (`bench_v2.py:68-74`), `keep()` (`:340-368`), `keep_c63()` (`diag_c63_c58.py:921-937`),
  `bench.py:65-83` et `head_to_head.py:87-120` ne lisent **aucune** donnée d'opcodes (18.5).
  `diag_1v1_shared_monthly.py:294-316` non plus : le schéma de sortie n'a aucun champ
  opcodes/CPU, donc ce harnais ne peut pas mesurer le coût de la sonde qu'il arme lui-même (19.5,
  cf. B2/19.1).
- **Le seul tri qui devait s'en servir n'existe pas** : `projects.nut:2113` — `local byOpcodes =
  funded;` puis `best = byOpcodes`. Aucun tri. `opcodeScore` est calculé aux quatre fabriques
  (`:340`, `:399`, `:435`, `:465`) et n'ordonne rien ; les deux longs commentaires qui justifient
  la précision d'`expectedOps` argumentent sur un second tri inexistant (06.3).
- **Le sélecteur en brûle des dizaines de milliers pour des résultats jetés** :
  `projects.nut:623-631`, `:636-648`, `:757-763` — **quatre balayages complets du vivier** par
  passe, dont le premier est intégralement perdu au défaut (`portfolio_floor_pct = 0`) et le
  quatrième ne sert qu'à une statistique lue seulement quand `funded` est vide. `alternatives`
  n'est pas un top-K, c'est le vivier **entier** (`:2036`, `:2047`), pour un budget de l'ordre de
  10 000 opcodes par tick. **Deux des quatre balayages sont supprimables sans changer un seul
  résultat de sélection** (06.1).
- **La boucle par défaut en jette ~9 700 par tick** : `main.nut:511-546` — à `loop_budget = 0`
  (défaut), une seule tâche est exécutée puis `Sleep(1)`, et le commentaire `:521-525` documente
  lui-même le gaspillage. L'étape 16 note que c'est le patron d'auto-handicap que le projet
  s'interdit par ailleurs (`pathfinder_sleep_ticks`, décision « armes égales » gelée). C20 et
  C36.1 sont vérifiés **sans rapport** : le diagnostic du 09-06 est à revérifier avec
  `loop_budget = 1` explicite, pas supposé résolu (11.4).
- **Le proxy d'itérations reste sous-compté, pas le coût H5 observé** :
  `builder_rail.nut:746-803` — le franchissement de segment sonde jusqu'à 18 longueurs de pont plus
  un tunnel sous `AITestMode` sans incrémenter `state.iterations`/`sliceSpent` (07.2). La
  réconciliation du workspace courant montre toutefois qu'aucun classement vivant ni
  `OpexAvailableCapital` ne consomme aujourd'hui `result.iterations`/`line.iterations`. Le coût H5
  utilisé par le harnais est `OB|A.result.opcodes`, mesuré par `budget.begin/end` autour de la
  recherche et incluant ces sondes.
- **Deux `GetSetting` payés en chemin chaud pour une valeur déjà en globale** :
  `builder_road.nut:743` (par candidat routier) et `main.nut:471-472` (01.8, 09.8).

**Gravité de groupe : P1.** L'objectif n°1 déclaré du projet n'est visible nulle part : ni dans un
JSON, ni dans un tri, ni dans une économie de dépense. 06.1 est le **seul correctif de tout ce
document à comportement strictement identique** — il n'a besoin d'aucun banc pour être justifié.

- **Modèle : Sonnet 5, effort medium** (Codex terra, medium) pour l'instrumentation G0bis —
  brancher sur le harnais les compteurs déjà existants et déjà publiés (panneaux `IP|`/`IB|`,
  `stats.selectionOpcodes`, `budget.nut`), pas en concevoir de nouveaux — et pour 06.1
  (suppression de deux balayages, résultat inchangé). **07.2 n'est plus un patch neutre à faire** :
  incrémenter `state.iterations` modifierait aussi les budgets/timeSafe/slices du pathfinder.
- **Modèle : Opus 5, effort high** (Codex sol, high) pour 11.4 seul : basculer `loop_budget` au
  défaut change l'admission au budget de tick de **toute** la partie et touche la position
  « armes égales ». À bancher, pas à décider en revue.
- **Modèle : Haiku, effort low** pour 01.8 et 09.8, en passant par un commit qui touche déjà
  `builder_road.nut`/`main.nut`.
- **Opportuniste** : `loop_budget` figure déjà parmi les constantes non tranchées de C43/E3
  (`docs/taches.md:809-811`) — 11.4 lui donne son mécanisme chiffré. Faire G0bis **avant** de
  rebancer B6 (portefeuille), sinon on optimise encore sur un artefact qui ne voit pas le coût
  que A1 doit précisément faire apparaître (conclusion inchangée du 09-06).

---

## Tier 1 — Bugs actifs par défaut, dans l'ordre d'impact économique

### B1. Aérien : le cycle 771 se referme sur lui-même, sans mémoire ni repli

**Constats** : 08.1 (P1), 08.2 (P1), 08.3 (P1), 08.4 (P2), 08.5 (P2), 08.7 (P3).

C'est le fait mesuré le plus gros et le moins expliqué du dépôt — 1 396 des 1 590 `build_failed`
sont des 771, et la sonde du 09-15 donne 291/291 **sans aucun aéroport OpexAI dans la ville**.
L'étape 8 en donne le mécanisme complet et inédit, en trois pièces qui s'emboîtent :

1. **L'élection a cessé d'élire un site constructible.** `builder_air.nut:567-585` et `:471-485` —
   sous `air_cheap_site = 1` (défaut), le sondage `BuildAirport` en test échoue, le code ne traite
   explicitement que `ERR_LOCAL_AUTHORITY_REFUSES`, **jette `err`** et délègue à
   `OpexAirCanLevelFootprint` (`:407-419`), qui ne regarde jamais `err`. Un 771 sur terrain plat
   ressort donc en `ok = true`, le site est élu **et mis en cache** (`:604`). Le chemin legacy
   `air_cheap_site = 0` (`:586-598`) ne présente pas le défaut : il rejoue `BuildAirport` en test
   après `LevelTiles`. **C36.3 a converti, sans le dire, une précondition « l'aéroport passerait »
   en « le terrain est plat »**, en même temps qu'il économisait des opcodes.
2. **Aucune mémoire ne borne le cycle.** `builder_air.nut:40-45` — `OpexAirInvalidateCachedSite`
   est une mémoire **de site** pour une erreur **de ville** : la couronne de recherche est
   déterministe, le terrain n'a pas changé, le scan suivant réélit la même ancre. La clé de portée
   ville existe (`OpexAirTownLimitAbandonKey`, `:886-889`) et est **lue** (`:1037-1038`, `:1230`),
   mais son unique écrivain (`task_air.nut:9-16`) est derrière `air_town_limit_memory`, **défaut
   0**. Avec `air_abandon_site = 0` aussi, un 771 n'est mémorisé à aucun niveau.
3. **Il n'y a pas de repli — pas un repli qui échoue, un repli qui n'existe pas.** Les 11 appels
   `BuildAirport` passent tous `AIStation.STATION_NEW` : le troisième argument `StationID` de
   l'API n'est **jamais** emprunté, donc aucun *distant join*. Aucun `AITile.DemolishTile` dans le
   fichier ; `RemoveAirport` n'apparaît qu'au rollback de nos propres aéroports neufs. Et le seul
   « join » du fichier (`OpexAirBuildJoinedStops`, `:1411-1529`) joint des **arrêts de bus** à
   notre propre station, après coup : il ne peut structurellement pas contourner un plafond de
   stations.

Deux constats voisins nourrissent le même cycle et s'y traitent :
- `builder_air.nut:1628-1638` — sur `BFAIL`, le seul cas majoritaire en pratique, `keepOrphan`
  empêche explicitement le rollback et laisse l'aéroport A payé sur la carte, **occupant un
  emplacement de station dans la ville de A**. Le commentaire `:1401-1403` annonce l'inverse. Le
  mécanisme se nourrit donc aussi de nos propres orphelins (08.4).
- `builder_air.nut:1696-1706` — la boucle de démarrage passe `built` au rollback alors qu'il
  contient les appareils **déjà démarrés**, contre ce qu'affirme `:1396-1400`. Un échec tardif
  laisse un avion en vol, non vendu, avec des ordres vers deux stations supprimées. Borné
  aujourd'hui par `fleet_portfolio = 1` (un seul appareil), atteignable dès qu'un plan en
  dimensionne plus (08.5). C'est le résidu **véhicules** de G7, pas le résidu aéroports.
- `builder_air.nut:1587-1592`, `:1612-1617` — `result.error` est périmé sur `HUB`/`HUBB` (aucune
  commande exécutée, `GetLastError()` rend une erreur antérieure), ce qui pollue le comptage 771
  lu par `task_air.nut:436` (08.7).

**Gravité de groupe : P1, la plus haute du Tier 1.**

- **Modèle : Opus 5, effort high** (Codex sol, high), en **trois commits mesurés séparément** :
  1. *Rendre le verdict de la sonde décisif* (08.1). C'est le seul correctif qui supprime la
     **cause** plutôt qu'un symptôme, et il est petit : ne pas écraser `err` par un test de
     terrain. Attention au coût en opcodes que C36.3 était venu chercher — le mesurer, sinon on
     rejoue C36.3 à l'envers.
  2. *Mémoire de ville* (08.2). C'est déjà le **candidat causal P1 pré-enregistré** de
     `docs/taches.md:578-588` (`air_town_limit_memory = 1`, pilote instrumenté). Ne pas l'adopter
     sans banc officiel : ce serait exactement le piège H2, sur le drapeau le plus en vue du
     projet.
  3. *Repli* (08.3). **Conception avant code** : `docs/taches.md:603` note qu'aucun contournement
     de 771 n'est prouvé dans le code OpenTTD. Trancher entre *distant join*, nettoyage ciblé et
     « prendre les slots utiles plus tôt » (`:629`) avant d'écrire une ligne.
- **Modèle : Sonnet 5, effort medium** pour 08.4, 08.5, 08.7, dans un commit séparé — 08.5 est
  destructeur si mal corrigé (même prudence que G7 au 09-06 : vérifier chaque site explicitement,
  pas par pattern-matching).
- **Opportuniste** : `task_projects.nut:66-90` construit une clé
  `build_error_air_town_limit_<townTile>` sur le même fait que `OpexAirTownLimitAbandonKey` —
  **deux mémoires du même événement, sur des drapeaux différents**. À unifier dans le commit 2.

**Passe corrective 2026-09-16.** 08.1 est corrigé sans toucher au pathfinder : sous
`AIR_CHEAP_SITE`, le repli par nivellement n'est désormais autorisé que pour
`ERR_LOCAL_AUTHORITY_REFUSES` et `ERR_FLAT_LAND_REQUIRED`. Un 771, un
`ERR_AREA_NOT_CLEAR` ou toute autre erreur du premier `BuildAirport` reste un échec de sonde
et n'est plus mis en cache comme site valide.

Le smoke obligatoire 2×3 `review_b1_probe_fix_smoke_2x3.json` passe. Le diagnostic
`review_b1_probe_fix_5x6.json` est complet 5/5 ; comparé à la référence immédiatement
pré-correctif de `review_h5_loop_budget_5x6.json`, 3 graines sont identiques et 2 divergent.
Delta moyen : `company_value = -183 428 £`, `profit_year = -32 569 £/an`. Le coût opcode
observé augmente sur les deux graines affectées. **Aucun gain économique n'est revendiqué** :
08.1 est une correction de vérité du verdict de sonde.

08.2 reste au défaut 0. Le 5×6 historique `p1_town_limit_5x6_v1.json`, antérieur à 08.1, n'est
plus recyclé comme preuve sur la nouvelle base. L'autorité actuelle
`results/review_b1_082_town_memory_c66_4_20x10.json` est complète **20/20** : le candidat
`air_town_limit_memory=1` donne `profit_year` **−55 605,6 £/an** en moyenne, médiane
**−82 543,5**, **8 V / 12 D**, `p=0,503445`. La garde de valeur passe à **+3,297638 %**, mais le
primaire échoue : verdict **`fail_primary`**. `air_town_limit_memory=0` est donc conservé et aucun
nouveau 20×10 n'est requis.

08.3 reste conception sans code. Les diagnostics 771 existants montrent 291/291 erreurs seed 42
avec zéro aéroport OpexAI dans la ville : le plafond est déjà consommé par AAAHogEx. Distant join
et nettoyage OpexAI ne créent donc pas un troisième slot ; `early_slot` reste le mécanisme adopté
pour la course aux slots.

### B2. L'entonnoir C63/C58 : le chantier prioritaire mesure faux à tous les étages

**Constats** : 13.1 (P1), 02.1 (P1), 19.1 (P1), 19.2 (P1), 13.2 (P2), 13.4 (P2), 13.5 (P2),
19.3 (P2), 13.7 (P3).

C'est la chaîne qui porte la priorité P1 du projet (`docs/taches.md:441`). Cinq défauts distincts,
tous sur la même chaîne, du `.nut` qui émet au `.py` qui lit :

1. **Un échec de construction rail n'est jamais enregistré sur le chemin livré.**
   `task_rail.nut:287-292` garde le seul `passDiscards.append` d'échec rail sous
   `C63_INVEST_PROBE` **seul**, là où route, air et eau l'appendent sous
   `C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL`. Pire, ce site n'est atteint que
   par le chemin **bloquant** : avec `rail_search_resumable = 1` (défaut), l'échec passe par
   `_consumeRailSearch` et `task_projects.nut:519-521` n'enregistre **rien, sous aucun drapeau**.
   Conséquence : `OpexC63ClassifyOpportunity` rend **`invalid`** — un échec de chantier rail est
   compté comme « le meilleur projet était structurellement impossible » — puis un A* entier est
   rebrûlé sur la paire qui vient d'échouer, et la passe est reclassée `waiting_compute` (13.1).
2. **Le ledger attribue chaque intervalle au mauvais état.** `probes.nut:359-422` calcule `days`
   comme l'écart depuis la *précédente* observation, puis le crédite au `kind` de la passe **qui
   vient de se produire**. La fonction voisine `OpexC63EnsureYear` (`:339-357`) fait l'inverse, et
   c'est elle qui a raison. Les jours réellement passés `absent` sont comptés sous `launched`
   (02.1).
3. **Deux des cinq étages mélangent stock et flux**, à l'émission comme à la lecture.
   `task_projects.nut:29-40` — `considered` et `accepted` sont des **tailles de portefeuille à
   l'instant t**, `attempted` et `built` des **compteurs de passe** ; les cinq sont émis sur la
   même ligne à chaque dispatch. `diag_1v1_shared_monthly.py:360-366` puis `:822-825` les somme
   tous indifféremment par mois, et `render_monthly_report` (`:942-956`) les affiche sous un
   en-tête unique. Les deux premiers étages valent donc « taille du vivier × nombre de passes » et
   sont inexploitables en valeur absolue. Accessoirement `funded = attempted − cashRejects` est
   **inférieur** à `attempted` alors qu'il est imprimé avant (13.2, 19.2).
4. **La ventilation par mode a un parseur et aucun émetteur.** `MONTHLY_FUNNEL_DETAIL` n'existe
   dans aucun `.nut` ; `diag_1v1_shared_monthly.py:391-481` en a un parseur complet, et son
   selftest le valide sur du texte **fabriqué à la main** (`:1150-1177`), donc il passe sans
   jamais exercer un run réel. Résultat : `None` silencieux, indiscernable d'un mois sans
   activité — sur le chantier qui a précisément besoin de savoir **quel mode** se fait refuser
   (13.5, 19.3).
5. **Une sonde efface une autre, et la sonde est forcée d'un seul côté du duel.**
   `task_rail.nut:257-264` — les `passDiscards` sont appendés sous trois drapeaux mais **remis à
   `[]` sous `DECISION_LOG` seul** : allumer `decision_log` en même temps que `c63_invest_probe`
   efface les refus, `cashRejects` chute, `funded` est surévalué (13.4). Et
   `diag_1v1_shared_monthly.py:609-610` : il n'existe **aucun chemin de code** où `shared=True` et
   `funnel=False`, donc `monthly_funnel=1` est armé côté OpexAI et jamais côté AAAHogEx, sans
   qu'aucun réglage du script ne permette d'isoler l'effet de la sonde sur la trajectoire — qui
   est pourtant l'enjeu annoncé de ce fichier (19.1). Enfin `fleet_grow_failed` n'est appendé que
   sous `C63_INVEST_PROBE` alors que son voisin `insufficient_cash` l'est sous les trois : avec
   `monthly_funnel = 1` seul, `built` baisse sans qu'aucun `r_*` n'augmente (13.7).

**Gravité de groupe : P1. C'est le prérequis du chantier P1 lui-même** : le diagnostic commun
5×6 de `docs/taches.md:455` ne peut pas être lu tant que 13.1 et 13.2 tiennent.

- **Modèle : Opus 5, effort high** (Codex sol, high). 13.1 et 13.2 ne sont pas des correctifs
  mécaniques : ils demandent de décider **ce que l'entonnoir doit dire** et à quelle granularité
  (normaliser à l'émission ou à la lecture ; faire de `considered`/`accepted` des flux ou les
  sortir de l'entonnoir). 02.1 touche l'attribution temporelle d'un ledger.
- **Contrainte de correctif déjà établie** (étape 13, à ne pas redécouvrir) : corriger
  l'attribution de `days` dans `probes.nut` **n'exige aucune contrepartie** dans
  `task_projects.nut` ; en revanche un correctif qui décalerait `lastKind` d'une passe casserait
  `_c63RecordPassAndProbe` (`task_projects.nut:2-21`).
- **Opportuniste** : la consigne « Ne pas activer aveuglément `decision_log` partout »
  (`docs/taches.md:459`) reçoit ici son mécanisme exact (13.4) — l'ajouter à la fiche. Le parseur
  `MONTHLY_FUNNEL_DETAIL` est à **supprimer ou à alimenter**, décision conjointe avec C63/C58 :
  c'est un point nouveau, sans fiche, à numéroter.

**Clôture B2 — 2026-09-16.** Le code courant avait déjà corrigé une partie du groupe :
`--no-funnel` rend la sonde mensuelle réellement optionnelle ; `considered/accepted` sont des
stocks moyens par passe tandis que `funded/attempted/built` restent des flux ; le lecteur publie
`metric_kinds` ; `fleet_grow_failed` est visible sous `MONTHLY_FUNNEL` ; le chemin
`DECISION_LOG` ne remet plus `passDiscards` à zéro. L'absence d'émetteur
`MONTHLY_FUNNEL_DETAIL` reste une limite de couverture, mais elle n'est plus silencieuse :
`funnel_detailed_state=missing_emitter`.

Deux défauts restaient réellement actifs et sont corrigés :

1. **02.1** : les jours écoulés sont maintenant crédités à `previousKind`/
   `previousAbsentCause`; l'observation courante incrémente son `n` sans récupérer le temps
   antérieur. Le flush annuel transporte le dernier état sans double incrément.
2. **13.1, chemin cash compris** : le candidat rail est conservé avant
   `_consumeRailSearch`, puis les outcomes `failed` **ou** `cash` sont ajoutés à
   `passDiscards` sous `DECISION_LOG || C49_SCARCITY_LEDGER || C63_INVEST_PROBE ||
   MONTHLY_FUNNEL`. Le selftest contrôle désormais cette responsabilité appelant/appelé.

Le diagnostic final `results/review_b2_c63_real_5x6_v2.json` tourne avec 6 workers / 6 CPU,
2g RAM/swap et cache persistant. 5/5 jeux atteignent 1975 ; les années closes 1970–1974 sont
complètes, 1975 est explicitement ouverte/partielle. Le JSON est fail-closed sur les années closes
manquantes et les `table_traps` : `invariants.ok=true`, aucune erreur. Les 25 années-graines
closes donnent 1 495 jours `unaffordable`, 1 242 `invalid`, 985 `absent`,
526 `waiting_compute`, 4 819 `launched`, 0 `demand`. L'ancienne lecture « le capital est
exclu » est donc invalidée ; aucune politique n'est adoptée sur ce 5×6.

Validation post-dernier `.nut` : `diag_c63_c58.py --selftest` OK, compilation Python OK,
`git diff --check` OK et smoke obligatoire
`results/review_b2_final_smoke_2x3.json` → **PASSED** avec les résultats économiques inchangés
par rapport au smoke B1 au défaut (sondes désactivées).

### B3. Route : la cible de flotte est détruite avant d'atteindre le classement

**Constats** : 09.3 (P2), 09.4 (P2), 09.5 (P3), 09.6 (P3), 09.9 (P3), plus le renvoi 09.I
(`task_road.nut:40-47`).

- `economy.nut:630-633` — `vehiclesForVolume` (la vraie cible, dérivée de
  `offered / (capacity × tripsPerMonth)`) est calculée puis immédiatement plafonnée par
  `OpexRoadPhysicalVehicleCap(1, 1)` → **2**, avec des arguments **littéraux**, alors que le
  commentaire `:586-588` promet que la fonction est réappelée en aval « avec les VRAIS comptes de
  quais ». En aval, `builder_road.nut:1325-1328` ne relève `want` que sous `ROAD_MULTISTOP`
  (défaut `false`) et le bloc **exclut de toute façon les bus** (`:1189`). Pour toute ligne de
  bus, `physicalCap = 2` à jamais. `vehiclesForVolume` n'est stocké nulle part, ni journalisé, ni
  reporté sur `line` : **l'information « cette ligne voulait 7 bus » est détruite à la source**,
  et la ligne est ensuite *scorée* comme une ligne à 2 bus (09.3).
- `builder_road.nut:1311-1314` + `economy.nut:589-595` — le commentaire énonce correctement la
  règle du jeu (« un arrêt n'accueille que DEUX véhicules **à la fois** ») : c'est une contrainte
  de **simultanéité**. `2 × min(nStopsA, nStopsB)` la transforme en borne sur la **flotte
  entière**, ce qui n'est exact que si le temps de trajet est nul. Le fichier dispose pourtant du
  modèle temporel qui manque (`oneWayDays = transitDays + dwellDays`,
  `ROAD_PAX_STOP_DWELL_DAYS = 6`) : la fraction de cycle réellement passée à quai vaut
  `dwell / (transit + dwell)`, sous 50 % dès 20 tuiles. **L'erreur croît avec la distance, donc
  avec le revenu par trajet.** Second effet : un arrêt d'extension est un quai de plus et ajoute
  ~6 jours de dwell, mais `task_road.nut:40-47` n'incrémente ni `nStopsA` ni `nStopsB` — une
  extension dégrade la fréquence sans jamais ouvrir droit à un véhicule (09.4).
- Trois scories qui rendront tout correctif plus cher : la formule du plafond réimplémentée à la
  main au lieu d'être appelée (09.5), une docstring qui annonce un plafond que la fonction
  n'applique pas et dont l'invariant est entièrement à la charge de l'unique appelant (09.6), et
  un commentaire qui affirme `MAX_ROAD_VEHICLES = 2` quand la constante vaut 8 (09.9).

**Gravité de groupe : élevée à P1.** Chaque constat isolé est P2 ou P3 ; ensemble ils expliquent
l'écart de volume que le projet cherche depuis trois revues (564 véhicules contre 102), et ils
**détruisent l'information à la source** — aucune mesure aval, aucun refleet, aucun rapport annuel
ne peut rattraper ce que le classement a jeté.

- **Modèle : Opus 5, effort high** (Codex sol, high). Le plafond modélise une grandeur physique et
  C50b a déjà **réfuté sa suppression brute** (20/20 défavorable sur l'air, 27/40 sur la route) :
  le correctif n'est ni un relèvement de constante ni une suppression, c'est une **remise à
  l'échelle temporelle** de la contrainte de quai.
- **Premier commit recommandé, à comportement inchangé** : simplement **journaliser
  `vehiclesForVolume`** à côté de la cible tronquée, sur `line` et dans un panneau. C'est la
  mesure qui manque pour trancher, et elle ne change aucune décision.
- **Opportuniste** : P2 C61/C59, volet Route (`docs/taches.md:763-767`). La fiche dit « la cible
  est du trafic rentable supplémentaire, pas le passage de 2 à 8 véhicules » et reste conditionnée
  à P1 : 09.3/09.4 lui donnent enfin le mécanisme, sans lever la condition.

**Clôture B3 — 2026-09-16, expérimentation non adoptée.** Le workspace courant conserve trois
grandeurs distinctes de bout en bout : `vehiclesForVolume` = cible brute de demande,
`roadBerthCapacity` = capacité simultanée de quai (`2 * min(stops)`), `roadVehicleCap` = plafond
de flotte retenu. Le switch expérimental `road_time_scaled_cap` est un booléen **défaut 0**. Sous
0, le chemin historique est conservé ; sous 1, et seulement pour `kind == "pax"`, le plafond vaut
`floor(berthCapacity * oneWayDays / ROAD_PAX_STOP_DWELL_DAYS)`, borné inférieurement par
`berthCapacity` et supérieurement par `MAX_ROAD_VEHICLES`. Le fret retourne volontairement le
plafond historique : aucun modèle de temps de chargement fiable n'autorise à lui appliquer le dwell
passagers. `C50B_ROAD_CAP_RELAX` conserve sa priorité historique. L'instrumentation
`vehiclesForVolume` et les champs berth/fleet restent actifs dans ranking, `PROJECT_CHOSEN`, lignes,
feeders et `LINE_REVENUE`; la persistance des lignes est générique et conserve ces scalaires.

Validation statique finale : `python -m py_compile sweeps/diag_b3_road_fleet_targets.py
sweeps/test_b3_road_fleet_targets.py`, `python sweeps/diag_b3_road_fleet_targets.py --selftest`,
`python sweeps/test_b3_road_fleet_targets.py` (**12/12**) et `git diff --check` passent. Le smoke
obligatoire post-dernier `.nut` :

`docker run --rm --cpus=6 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v
"${PWD}:/work" -w /work openttd-lab python3 sweeps/smoke_test.py --out
results/review_b3_time_scaled_cap_smoke_2x3_v3.json`

→ **PASSED 2/2** : seed 100 valeur 2 172 396 £, profit annuel 1 212 715 £, score 419,
40 gares/39 véhicules ; seed 42 valeur 2 638 035 £, profit annuel 1 657 231 £, score 550,
53 gares/50 véhicules.

Le premier `review_b3_time_scaled_cap_paired_5x6.json` est **invalide comme preuve B3** : le
diagnostic avait réutilisé `build_arms()` avec son snapshot complet de réglages et aucune télémétrie
`PORTFOLIO_RANK` / `PROJECT_CHOSEN` / `LINE_REVENUE` B3 n'était collectée. Le harnais a été corrigé
sans modifier le gameplay pour utiliser deux `local_folder` ne fixant explicitement que
`decision_log` et `road_time_scaled_cap`. Le diagnostic probant est :

`docker run --rm --cpus=6 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v
"${PWD}:/work" -w /work openttd-lab python3 sweeps/diag_b3_road_fleet_targets.py --years 6
--seeds 42 100 999 1234 5678 --workers 6 --out
results/review_b3_time_scaled_cap_paired_5x6_v2.json`

→ **5 paires / 10 runs complets et sains**, horizon 1975-12-01, 72 checkpoints par run.
Invariants : référence pax `vehicle_cap == berth_cap` ; référence fret idem ; variante fret idem ;
aucun selected/actual au-dessus de `vehicle_cap` ; borne pax `<= MAX_ROAD_VEHICLES` ; champs B3
complets. Le seul invariant volontairement faux est `variant_pax_temporal_cap_exercised=false` :
au défaut courant `road_pax_build=0`, **aucun projet pax n'atteint ranking/chosen**. Les années-ligne
pax observées sont du `town_growth`, avec cible brute maximale 1 ; le nouveau plafond ne peut donc
jamais devenir causal. À l'inverse, le fret expose bien de nombreuses cibles brutes >2, mais reste
volontairement sous l'ancien cap faute de modèle de chargement fiable.

Économie variante `1 - 0` sur ce 5×6 : `company_value` moyenne **-52 094,8 £** (2 V / 3 D),
`profit_year` **-29 119,4 £/an** (2 V / 3 D), `primary_vehicles` +1,4 et flotte route +0,8.
Le mécanisme pax n'étant pas exercé et le signal économique n'étant pas positif, il n'existe aucune
base pour une autorité d'adoption : **pas de 20×10**, défaut maintenu à **0**, correctif expérimental
et instrumentation conservés derrière switch. B3 est clos comme expérimentation non adoptée.

### B4. Rabattement : un troisième chemin d'ordre, des extensions effacées, deux populations

**Constats** : 09.1 (P1), 09.2 (P2), 14.4 (P2), 09.7 (P3).

Le correctif feeders du 09-15 a visité deux des **quatre** sites d'ordre du dépôt. L'étape 9 a
vérifié ligne à ligne que les deux visités sont rigoureusement symétriques (construction
`builder_road.nut:1273-1299` vs refleet `:1567-1584`, tableau complet de comparaison) : la
régression survivante n'est pas entre eux.

- `builder_road.nut:1452`, `:1471` — `OpexBuildRoadExtension` pose `flags = C53_ORDER_NONSTOP ?
  OF_NON_STOP_INTERMEDIATE : OF_NONE` **sans aucun test `isFeeder`**, alors que les lignes
  1455-1457 juste au-dessus branchent bien sur `extensionType == "feeder_extension"`. La séquence
  devient `[A ville : OF_NO_UNLOAD] → [A' ville : OF_NONE] → [hub : OF_TRANSFER|OF_NO_LOAD]` : le
  bus décharge à `A'`, choisi précisément sur une tuile qui produit des passagers donc dans un
  tissu qui les accepte. **Les passagers sont livrés au trottoir d'en face.** Actif au défaut
  (`feeder_town_coverage = 1`), et l'extension **est** le mode de croissance nominal d'un feeder
  (`candidates.nut:2927-2928`). Le mode d'échec « feeder bâti, hub vide » revient, avec un an de
  retard sur la création de la ligne (09.1).
- `builder_road.nut:1582-1584` — le refleet sans survivant reconstruit exactement 2 ordres et
  exige `GetOrderCount == 2`, ignorant `line.extraStops`. Après une perte totale de flotte sur une
  ligne étendue, les arrêts d'extension restent bâtis, plus personne ne les dessert, et **la
  réparation automatique est bloquée** : `OpexRoadLineTownStopCount` compte toujours
  `extraStops`, donc la ligne est réputée au plafond de sa commune (09.2).
- `task_feeders.nut:202-230` et `:354-376` — les deux constructeurs de feeders omettent `kind` du
  dictionnaire de ligne, alors que `candidate.kind` est lu juste au-dessus (`:175`) et que
  `task_road.nut:349` l'inclut systématiquement. `OpexRoadExtensionCandidates` exige
  `line.kind == "pax"` : **deux populations de feeders au comportement de croissance différent**,
  sans raison apparente. C'est ce qui détermine le rayon d'action réel de 09.1 (14.4).
- `builder_road.nut:1561` vs `:1261-1266` — le refleet rebâtit le véhicule depuis le moteur
  **courant** du catalogue sans revérifier `RoadVehHasPowerOnRoad` : si le catalogue a basculé sur
  un type de route que le dépôt ne porte pas, le véhicule est acheté, démarré et compté sans
  jamais pouvoir rouler (09.7).

**Gravité de groupe : P1.** 09.1 est actif au défaut et ramène le mode d'échec que le correctif du
09-15 venait d'éliminer.

- **Modèle : Sonnet 5, effort high** (Codex terra, high). Bug de logique localisé, mais avec un
  historique **immédiat** de correctif partiel : la règle à appliquer est « **un seul producteur
  d'ordres de feeder** », pas quatre copies à garder synchrones. Vérifier les quatre sites
  explicitement — c'est la leçon G7 du 09-06, et c'est elle qui a manqué en `c74a123`.
- **Opportuniste** : 14.4 (`kind` manquant) est un préalable, pas une suite : sans lui, corriger
  09.1 ne répare que la moitié des feeders.

**Clôture B4 — 2026-09-16.** Le workspace courant corrige le P1 observé et le préalable 14.4 sans
modifier un défaut stratégique :

- `builder_road.nut` utilise un couple unique de helpers d'ordres feeder pour la construction, le
  refleet et `feeder_extension` ; les arrêts ville/intermédiaires sont `NO_UNLOAD`, le hub
  `TRANSFER|NO_LOAD` ;
- `task_feeders.nut` persiste `kind = candidate.kind` sur le feeder bus dédié, mais pas sur le
  feeder courrier, qui reste hors de l'éligibilité pax ;
- `sweeps/test_b4_feeder_orders.py` : 6/6 ; `diag_c53_orders.py --selftest` : OK ;
  `results/review_b4_smoke_2x3.json` : PASSED ;
- `results/review_b4_bus_extensions_5x6_ordl.json` : 5/5 jeux complets, 13
  `feeder_extension`, 3 `bus_pax_extension`, 12 listes ORDL feeder étendues distinctes,
  `errors=[]`, `invalid_extended_feeders=0` partout. Les ordres décodés confirment
  `LOAD_IF_POSSIBLE + NO_UNLOAD` en ville/intermédiaire et `NO_LOAD + TRANSFER` au hub.

Le 5×6 est volontairement **diagnostique**. Il ne justifie ni changement de défaut ni adoption de
politique ; aucun 20×10 n'est donc requis pour cette clôture. Les P2/P3 voisins 09.2/09.7 restent
des constats séparés et ne sont pas maquillés en « corrigés » par ce lot.

### B5. Rail : la machine à états se gèle, se perd au rechargement, et meurt si on l'active

**Constats** : 01.1 (P1), 07.1 (P1), 11.6 (P1), 11.7 (P2), 13.11 (P3), 13.12 (P3).

Un seul champ, `this._railSearch`, garde l'exclusivité de **toute** recherche rail : sa garde
d'entrée est en tête de `_tryBuildRailProject` (`task_rail.nut:149`) et de `_expandRailLines`
(`:308`). La revue trouve trois façons distinctes de ne jamais le rendre, plus un crash latent sur
le chemin que G5 veut rouvrir.

- `task_rail.nut:1070-1086` — `_consumeRailUpgrade` fait un simple `return;` sur
  `reason == "CASH"` **sans remettre `_railSearch` à `null`**, là où la recherche primaire possède
  `C41_RAIL_CASH_RELEASE` (`:881-885`, `:895-899`). Le champ reste en `{kind="upgrade",
  phase="build"}` indéfiniment, et **toute** nouvelle recherche rail est rejetée derrière lui.
  C'est le mécanisme de G6 réapparu ailleurs que là où G6 le décrivait (07.1).
- `main.nut:132-140` vs `persist.nut:2-219` — `_railExpansion`, `_railSearch` et `_dynamicBatch`
  n'apparaissent ni dans `Save()`, ni dans `Load()`, ni dans `_reconcileAfterLoad()`. Pour
  `_railExpansion` en particulier, le second train a pu être acheté et lancé avant la sauvegarde :
  la finalisation n'ayant jamais lieu, **le train physique devient orphelin de `_lines`** et la
  ligne redevient éligible à une expansion qu'elle vient de recevoir. Le contraste avec la
  réconciliation complète et prudente de `_lines`/`_pendingLines` montre que c'est un oubli, pas un
  choix (11.6). Même famille pour les files de réparation `_c41RailSignalLines`/
  `_c41RailJunctionLines` (11.7), avec cette différence qu'il s'agit d'une file de travail
  fonctionnelle, pas d'un compteur : sa perte a un effet de jeu.
- `task_rail.nut:541-549` — la phase `resume` de `_continueRailExpansion` est **la seule sans
  issue de secours** : elle réessaie `StartStopVehicle` indéfiniment, sans panneau ni libération,
  donc plus aucun second train ni doublement de voie de toute la partie, sans trace (13.12).
- `task_rail.nut:521`, `:565` — **`RAIL_EXPAND_APPROACH_TILES` n'est définie nulle part dans le
  dépôt** (ni `const`, ni `enum`, ni affectation, ni dans tout l'historique git). Inerte aux
  défauts livrés, mais **dès qu'un bras de banc pose `rail_expand = 1`** — exactement le bras
  qu'appelle G5 — la première expansion éligible tue le script sur
  `the index '…' does not exist`, c'est-à-dire la mort silencieuse décrite par `CLAUDE.md`. Ce
  n'est pas une régression C65 : les deux lectures ont été introduites par `5a41488` sans que la
  constante existe (01.1).
- `task_rail.nut:426` puis `:455-461` — le garde accepte explicitement une ligne sans clé
  `doubleTrack`, l'affectation exige qu'elle existe (`=` au lieu de `<-`). Inatteignable
  aujourd'hui, réactivé par une sauvegarde antérieure à l'ajout des clés — et `save_full_state`
  vaut 1 au défaut (13.11).

**Gravité de groupe : P1.**

- **Modèle : Haiku, effort low** pour 01.1 seul, **et il doit partir en premier** : avant tout
  banc `rail_expand = 1`, donc avant toute reprise de G5. Une ligne.
- **Modèle : Sonnet 5, effort high** (Codex terra, high) pour 07.1, 13.11, 13.12 : machine à états
  à corriger avec un historique de « passer d'un blocage silencieux à un autre ». Prévoir le cas
  `CASH` **et** le cas `resume` explicitement dans la suite de test.
- **Modèle : Opus 5, effort medium** (Codex sol, medium) pour 11.6/11.7, mais uniquement pour
  **trancher la conception** : rendre l'état reprenable (le persister et le réconcilier) ou le
  rendre idempotent (le recalculer au chargement). Les deux sont défendables ; les mélanger ne
  l'est pas. L'écriture ensuite est du Sonnet.

**Clôture B5 — 2026-09-16.** Réconciliation préalable : **07.1, 13.11 et 13.12 étaient déjà
corrigés dans le code courant** et n'ont pas été réimplémentés. Les écarts encore actifs étaient
01.1, 11.6 et 11.7.

- **01.1** : `RAIL_EXPAND_APPROACH_TILES = 8`, aligné sur la fenêtre locale maximale
  `OpexPlacePathApproachSignal(..., maxDistance=8)`.
- **11.6** : `_railExpansion` est projeté en scalaires sérialisables et possède une machine de
  commit `idle/build_started/wagon_built/wagon_moved/metadata_done`. Une reprise ne reconstruit
  jamais un wagon dans l'état ambigu `build_started`; un `pendingWagon` identifié est réutilisé ;
  un wagon déjà attaché est détecté physiquement ; les métadonnées sont idempotentes. Une rame
  `resume` déjà repartie n'est jamais togglée une seconde fois. `_railSearch` et
  `_dynamicBatch` ne sont pas sérialisés : seule leur présence est conservée, puis le reload
  les abandonne et force une reconstruction du portefeuille/catalogue.
- **11.7** : files C41 persistées, LineID invalides filtrés, tâches réarmées seulement si le réglage
  correspondant est actif et la file non vide.

Validation :

- `python sweeps/test_b5_rail_persistence.py` → **11/11** ;
- campagne **10/10**, santé **26/26**, compteurs physiques **7/7** ;
- selftests C63, mensuel et C66.4 → OK ; `py_compile` et `git diff --check` → OK ;
- smoke `results/review_b5_smoke_2x3.json` → **PASSED** ;
- `results/review_b5_save_load_seed42.json` : 36 saves avant, 24 après,
  `LOAD_RECONCILE` présent, aucun échec moteur/script, `rail_search_dropped=1` ;
- `results/review_b5_save_load_seed42_6y.json` : 72 saves avant, 13 après,
  reload au 1974-10-01, `LOAD_RECONCILE` présent, aucun échec moteur/script,
  `rail_search_dropped=1` ;
- `results/review_b5_rail_expand_5x6.json` : **5/5 complets**, `protocol_failures=[]`.

Limites : les round-trips n'ont pas intercepté une expansion wagon active
(`rail_expansion_* = 0`) ; `approach/depot/resume` sont donc couverts par les 11 tests de
contrat, pas par un checkpoint moteur forcé. Aucune sauvegarde historique `stateVersion=1`
n'était disponible localement pour un round-trip réel ; la compatibilité est field-guarded et
testée statiquement. L'état `build_started` reste volontairement fail-closed : si Save tombe
après la commande mais avant stockage du VehicleID, la reprise n'émet **jamais** un second
`BuildVehicle` ; un wagon libre non identifié peut donc rester au dépôt dans cette fenêtre
extrême. Ce résidu borné est préféré au doublon.

Le défaut `rail_expand` reste **0**. Le 5×6 est un diagnostic de sûreté, pas une adoption ;
aucun 20×10 n'était requis.

### B6. Portefeuille : classer un choix unique sur un ratio (successeur direct de G1)

**Constats** : 06.2 (P1), 04.3 (P2), 06.5 (P2), 06.11 (P3), 06.12 (P3).

G1 est **fermé sur ses quatre énoncés de 2026-09-06** (voir le tableau plus bas) : la borne du
branch-and-bound est caduque, l'élection modale et l'objectif sont corrigés et vérifiés ligne à
ligne, la fenêtre de capital fonctionne sous un autre nom. Le nœud a changé de forme, pas de
place.

- `projects.nut:644`, `:606`, `:2083` — la clé de tri est `fundScore = profitAnnual / capital`,
  un **ratio**, honnêtement commenté. Mais chaque projet est testé **seul** contre le budget
  entier (`:637`) et `PORTFOLIO_MAX_BATCH = 1` fait qu'**un seul projet est construit par passe**.
  Pour un choix unique et indivisible, l'argmax du ratio n'est pas l'argmax du profit : 45 k£ pour
  9 k£ de profit passe devant 280 k£ pour 50 k£. **C'est littéralement l'erreur que le commentaire
  `:591-596` dit avoir corrigée** en supprimant le sac à dos ; le remplacement a changé l'objectif
  (revenu → profit) et **conservé la forme ratio**, donc conservé le biais *cheap-first* pour la
  seule décision qui compte. Le garde-fou prévu, `portfolio_floor_pct`, est à **0** — et le même
  commentaire chiffre ce que 0 coûte : « −24,4 % de valeur et −30,7 % de profit annuel » (06.2).
- `candidates.nut:791-809` — en amont, le `ratio` qui classe au `TOP_K` intègre un `turnoverBonus`
  de 60 à 130 % que le champ `roi` transmis en aval **ne reflète pas**. La raison du classement et
  la valeur exposée divergent, et pas à cause d'un autre drapeau : l'écart existe au défaut (04.3).
- `projects.nut:1850` vs `:2083` — le budget de capital est lu **230 lignes avant** d'être utilisé,
  avec la découverte aérienne entre les deux, chiffrée à « ~21 jours de temps de jeu » par
  `scheduler_tasks.nut:570-575`, alors que `capital.nut:44-46` exige explicitement une relecture
  après chaque dépense. Le chemin incrémental, lui, relit bien : **l'asymétrie est entre les deux
  chemins** (06.5).
- `projects.nut:1390-1414` — l'économie des candidats recyclés n'est jamais recalculée (topologie
  seulement) alors que feeders, flotte et aérien sont régénérés frais : l'asymétrie « air frais /
  rail gelé » favorise structurellement le mode dont les chiffres sont récents (06.11). Et
  `OpexPrequoteRailCandidates` désigne les deux candidats qui échappent au ×1,7 par un
  préclassement au ratio **qui ne connaît pas la contrainte de capital** — dernier reste de
  « élire d'abord, financer ensuite » (06.12, inerte au défaut).

**Gravité de groupe : P1.** Verdict inchangé depuis trois audits : *le code ne classe pas sur ce
qu'il prétend classer*, et c'est le terrain sur lequel A1 doit être construit.

- **Modèle : Opus 5, effort max** (Codex sol, high). Le plus risqué du lot : toucher l'objectif de
  classement change quel projet est bâti à *chaque* cycle de toute la partie. **Plusieurs commits
  mesurés séparément** (d'abord 04.3 — aligner le classement et la valeur exposée ; puis 06.5 —
  relire le capital au bon endroit ; puis 06.2), jamais un seul gros diff, sinon aucun banc ne
  pourra attribuer l'effet.
- **Réserve à lever avant de coder** : `portfolio_floor_pct = 0` peut signifier « hypothèse
  banquée et rejetée » (`ai/OpexAI/CLAUDE.md`). Le retrouver dans l'audit H2 **avant**. L'asymétrie
  logique tient quel que soit le verdict ; l'ordre de correction en dépend.
- **Ne surtout pas faire avant H1 et H5** : rebancer un objectif de classement sur un banc qui ne
  sait ni épingler ses bras ni appliquer le test des signes, et qui ne voit pas le coût d'opcodes,
  c'est refaire C29.3 en plus gros.
- **Opportuniste** : **A1** (dénominateur de classement selon la ressource rare), comme au 09-06 —
  et l'avertissement de `docs/taches.md:792` (« ne pas relancer `portfolio_max_batch` /
  `portfolio_dynamic_batch`, ni un prix d'opcode ajouté au score, sur la seule foi d'anciens
  profils ») s'applique mot pour mot.

### B7. Eau : un budget qui ne borne pas ce qu'il prétend, un second juge qui brûle du capital

**Constats** : 10.1 (P1), 10.3 (P1), 10.2 (P2), 10.5 (P2), 10.4 (P3).

- `lib_water.nut:194-201` — le contrôle de `WATER_LAKES_OPS` n'est évalué qu'**entre deux tours**
  de la boucle externe de `FindPath` : jamais à l'intérieur d'un tour, jamais pendant
  `InitializePath`/`AddPoint` (`:161-174`, `:310-366`), qui déclenchent `_AllGroups` (`:368-389`,
  boucle `do…while`) sur un graphe dont la taille croît avec la partie. `builder_water.nut:577-580`
  le documente lui-même (« borne le NOMBRE d'itérations, pas le coût d'UNE itération »).
  **Le garde-fou ne peut donc pas empêcher le gel qu'il a été adopté pour supprimer** — et
  `water_lakes_ops_budget` a précisément été adopté « sur suppression d'un mode d'échec dur »
  malgré un gain de valeur non significatif (7/1/12, p = 0,070). C'est le meilleur candidat
  mécanique pour C56 que la revue ait produit (10.1).
- `builder_water.nut:735-748` — `OpexBuildWaterRoute` construit les **deux quais réels** (argent
  dépensé, `:699`, `:706`) puis revérifie la connectivité avec le **BFS borné** à 24 tuiles, c'est
  à-dire exactement la fenêtre que Lakes a été introduit pour contourner à l'étage du tri. Une
  paire admise par Lakes au-delà de 24 tuiles peut échouer ici et déclencher `OpexWaterRollback` :
  les deux quais sont démolis, sans remboursement. **Un `NOWATER` à ce stade n'est pas neutre,
  c'est du capital perdu sur une paire que le juge amont avait validée** (10.3).
- `builder_water.nut:599-606` — le repli Manhattan est un plancher de distance géométriquement
  correct, mais `navigableDistance` devient `oneWayDays`, qui pilote `tripsPerMonth` **et** sert
  d'argument « jours » à `GetCargoIncome`. Sous-estimer la distance **surestime à la fois la
  capacité et le revenu unitaire** : c'est un plancher de distance conservateur et un **plafond de
  ROI optimiste** — l'inverse de ce que « repli conservateur » suggère. Le compteur
  `profile.lakes_fallback_navigable` existe déjà pour en mesurer la fréquence, et rien ne
  l'exploite (10.2).
- `lib_water.nut:147-159` — le constructeur de Lakes peuple une `AIList` avec **une entrée par
  tuile de la carte entière**, instance unique persistante, jamais sauvegardée donc reconstruite à
  chaque chargement. Le commentaire ne chiffre que le cas 256². À 1024²/2048², c'est 16× puis
  64× plus d'entrées, jamais échantillonnées ni comparées au repère « > 50 Mo = mauvaise IA »
  (10.5 — voir aussi M4).
- `lib_water.nut:301-308` — le seul `Valuate` à fonction Squirrel du dépôt existe bien, mais il est
  **mort** (`GetPathLength` n'a aucun appelant) et, même réactivé aux tailles en jeu
  (`WATER_MAX_WATER_TILES = 8`, soit ~64 comparaisons), sans danger réel. Le point du plan est
  confirmé **et désamorcé** : ne pas le traiter comme un risque de crash (10.4).

**Gravité de groupe : P1**, entièrement à cause de 10.1 et 10.3 : le premier touche C56, le seul
mode d'échec dur non élucidé du projet ; le second dépense du capital réel.

- **Modèle : Opus 5, effort medium** (Codex sol, medium) pour 10.1 et 10.3 : il fallait décider **où**
  poser le contrôle d'opcodes sans casser la protection contre le gel (C57 disait explicitement
  « conserver la protection »), et **quel juge fait foi** à la construction. Ce sont deux choix de
  conception, pas deux `if`.
- **Modèle : Sonnet 5, effort low** pour 10.2 : rendre le repli conservateur **économiquement** et
  non seulement géométriquement (par exemple majorer `oneWayDays` quand le repli est emprunté), en
  s'appuyant sur le compteur qui existe déjà.
- **10.5 n'est pas un correctif, c'est une mesure** — voir M4.
- **Historique, supersédé le 2026-09-17** : C57 devait calibrer les 50 000 opcodes de Lakes ; ce
  travail est abandonné avec l'architecture Lakes. La suite est C67, analyse spatiale de carte par
  blocs et remplacement propre de la connectivité importée.

**Clôture technique B7 — 2026-09-17.** La condition historique « ne corriger que si un freeze
actuel est reproduit » est supersédée pour **10.1 et 10.3** : les deux défauts sont directement
présents dans le code courant et ont été corrigés. `FindPath` interroge maintenant le budget
opcodes jusque dans ses boucles internes et ne committe plus une grosse mutation de graphe avant
d'avoir passé les scans bornés ; le chemin Lakes exécute le BFS de connectivité des fronts réels
avant le premier `BuildDock`, donc un `NOWATER` n'engage plus les deux quais. Le chemin legacy
conserve son contrôle post-construction.

Validation : contrat B7 ciblé + suite commune **61/61**, selftests affectés, `py_compile` et
`git diff --check` OK. Le smoke final `results/review_final_residuals_smoke_2x3.json` est sain sur
les deux graines. Le scan ciblé `results/review_b7_water_c56_targeted_2x10.json` (2026/1337,
10 ans) reste **inconclusif** faute de traces C56 datées ; le parseur publie désormais
`frozen_count=null`, `measurable_count=0`, `inconclusive_count=2` au lieu de transformer cette
absence de mesure en « 0 gel ». 10.2 a ensuite été corrigé fail-closed : le fallback Manhattan
n'alimente plus `OpexWaterEconomics` quand la distance navigable exacte manque. 10.5 a ensuite été
clos par mesure externe RAM/opcodes jusqu'à 2048² ; aucun default n'est modifié et aucun 20×10
n'est requis.

**Décision d'architecture du 2026-09-17.** Après cette clôture, l'utilisateur abandonne
`MinchinWeb.Lakes` comme base future. Les correctifs 10.1/10.2/10.3 restent valides pour le chemin
courant jusqu'à sa migration, et 10.5 reste une mesure historique. En revanche C57 est fermé sans
suite : ne pas calibrer `WATER_LAKES_OPS`. Le nouveau chantier C67 doit construire une analyse de
carte commune à l'eau et au terrain par blocs 5×5/10×10 typés, mesurer les deux granularités puis
migrer les consommateurs avant de retirer les settings/code Lakes.

Cette cartographie doit aussi devenir un **canal de prévision commun aux projets** : coût financier
probable, ROI corrigé du terrain, coût en opcodes, temps/ticks de décision et de construction,
risque de faisabilité, choix du mode et corridor de pré-pathfinding. Le type `eau/plat/vallonné/
montagne/...` ne doit pas remplacer les mesures sous-jacentes : chaque bloc conserve un vecteur de
caractéristiques physiques, complété par une couche dynamique (villes, industries,
infrastructures). Les invalidations doivent être locales pour éviter un nouveau scan global.

Contrainte supplémentaire : la construction de cette cartographie est **lazy et opportuniste**.
Interdiction d'un scan global monolithique au démarrage. Un projet déclenche le calcul des blocs
qui lui manquent ; ceux-ci sont mémorisés. Le scheduler peut compléter d'autres blocs en arrière-plan
seulement par tranches strictement bornées lorsque des opcodes sont disponibles et qu'aucune tâche
plus utile n'est prête (par exemple manque de trésorerie pour construire). Cette tâche de fond doit
être préemptable/reprenable et une carte partielle doit rester un état valide pour tous les
consommateurs.

### B8. Cycle de vie de flotte et de rebut : une ligne en liquidation peut recevoir un avion neuf

**Constats** : 14.1 (P1), 15.2 (P2), 14.2 (P3).

- `task_air.nut:619-810` — `_resizeAirFleets` ne teste **jamais** `line.scrapping`, contrairement
  à son équivalent routier (`task_road.nut:405`). Les deux seuls garde-fous indirects sont
  `deadStreak >= 2` et `lastProfit < 0`. Or `task_report.nut:263-274` recalcule les deux **chaque
  année pour toute ligne aérienne, y compris `scrapping = true`** : pendant la fenêtre de vente
  étalée (`SCRAP_TIMEOUT_YEARS = 2`), les appareils pas encore rentrés volent et génèrent un
  profit mesuré ; si une année est positive, les deux refus tombent **en même temps**. La boucle de
  croissance peut alors acheter un avion **neuf** sur une ligne dont les autres appareils partent
  au hangar pour y être vendus — l'inverse exact de l'intention du correctif G10 documenté juste à
  côté (14.1).
- `task_report.nut:431-432` — `scrapStartYear` est posé une seule fois et **jamais réinitialisé**,
  ni par le sauvetage feeder (`:357-387`, qui remet pourtant `scrapping=false` et
  `scrapVehicles=[]`), ni par `_triggerScrapLine` (`:312-343`). Une ligne ferraillée, sauvée, puis
  redevenue déficitaire des années plus tard repart avec l'**ancien** `scrapStartYear` : `stuck`
  est vrai dès le premier passage, la ligne est retirée immédiatement et ses véhicules encore en
  service sont abandonnés **sans les deux ans de grâce** que le mécanisme garantit (15.2).
- 14.2 est un constat de localisation, pas un bug : `task_air.nut` ne décide jamais du rebut, il ne
  fait que **lire** `deadStreak`/`lastProfit` comme motifs de refus de croissance. La décision vit
  dans `task_report.nut`. À retenir pour le correctif : le garde manquant est du côté air, la
  source du symptôme du côté rapport.

**Gravité de groupe : P1.** 14.1 dépense du capital sur une ligne au moment exact où on la liquide.

- **Modèle : Sonnet 5, effort medium** (Codex terra, medium). Deux gardes à ajouter, chacune
  symétrique d'un code qui existe déjà. Le seul piège est celui de `tree_planting` au 09-06 : une
  garde ajoutée silencieusement peut éteindre un chemin entier — prévoir un banc de non-régression,
  pas seulement un smoke.
- **Réserve à noter** : 14.6 **infirme** l'autre moitié de G10 (sous-comptage de la flotte
  aérienne avant le premier rapport annuel). `vehCount`/`lastLiveVehicles` sont écrits
  immédiatement sur les deux chemins de construction, avec `result.vehicles.len()`. Ne pas
  rouvrir ; si le symptôme mesuré est réel, sa cause est en amont (H3 est le premier suspect : le
  compteur du **banc**, pas celui du jeu).

**Clôture B8 — 2026-09-16.** Les deux constats actifs ont été réconciliés avec le workspace
courant. 14.1 restait bien exposé au défaut : `_resizeAirFleets` traversait les lignes
`scrapping`, y compris avant la branche `needsRefleet`, et le projet flotte pouvait en plus rester
stale dans le cache jusqu'à `_tryBuildFleetProject`. Deux gardes sont donc posées : la production
de plan AIR refuse immédiatement une ligne en liquidation (`AIR_FLEET reason=scrapping`), et le
site transactionnel revalide `line.scrapping` juste avant `OpexAirAddPlane` (`FLEET_PROJECT
reason=scrapping`). Une ligne en liquidation ne peut plus acheter ni reconstruire un avion neuf.

15.2 subsistait comme défaut d'état, mais son scénario feeder est devenu surtout une dette de
compatibilité : les parties neuves courantes ne renvoient plus les feeders déficitaires dans le
même chemin de rebut. Le correctif reste nécessaire et local : `_triggerScrapLine` réécrit
`scrapStartYear` au début de **chaque nouveau cycle**, le sauvetage feeder supprime le timer, et le
fallback de `_scrapDeadLines` est conservé pour une ancienne sauvegarde déjà en liquidation sans
champ. Les logs `SCRAP_LINE` publient `start_year` puis `elapsed` à la sortie ; `FEEDER_RECOVER`
publie `scrap_timer_reset=1`.

Validation : `sweeps/test_b8_scrap_lifecycle.py` **7/7**, selftest de
`sweeps/diag_b8_scrap_lifecycle.py` OK, compilation Python OK et `git diff --check` OK. Le smoke
obligatoire a été rejoué sur la politique adoptée :

`docker run --rm --cpus=6 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v
"${PWD}:/work" -w /work openttd-lab python3 sweeps/smoke_test.py --arm
'OpexAI[air_early_slot=1]' --seeds 42 100 --years 3 --max-workers 2 --out
results/review_b8_scrap_lifecycle_smoke_2x3.json`

→ **PASSED 2/2**. Seed 100 : valeur 2 170 435 £, profit annuel 1 164 148 £, score 408,
34 gares/40 véhicules. Seed 42 : 3 261 459 £, 2 015 106 £/an, score 595,
54 gares/55 véhicules.

Diagnostic invariant 5×6 :

`docker run --rm --cpus=6 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v
"${PWD}:/work" -w /work openttd-lab python3 sweeps/diag_b8_scrap_lifecycle.py --years 6
--seeds 42 100 999 1234 5678 --workers 5 --out results/review_b8_scrap_lifecycle_5x6.json`

→ **5/5 runs complets et sains**, aucun événement de schéma invalide et aucune croissance AIR
observée pendant un intervalle de rebut. Limite essentielle : cette fenêtre 1970–1975 n'exerce
**aucun** `SCRAP_LINE`, aucun `FEEDER_RECOVER` et donc aucun projet flotte stale ; le 5×6 prouve
l'absence de régression/horizon, pas l'exposition économique du bug. Les invariants de sûreté qui
portent sur ces branches sont donc fournis par les 7 contrats ciblés, pas par une extrapolation des
zéros runtime. Aucun réglage ni nouveau défaut n'est adopté ; `early_slot` reste inchangé.

### B9. Aérien : l'économie du plan reste asymétrique et hétérogène en unités (G4 résiduel)

**Constats** : 08.6 (P2), 08.9 (P3), 08.10 (P3), 08.8 (P3).

G4 est **fermé sur son énoncé** — l'étape 8 a vérifié que la boucle de retour existe
(`OpexAirReconcileActualBuild:711-742`, appelée en `:1735`) et que le coût des arrêts est dans le
ROI **deux fois plutôt que zéro** (réservé avant élection, puis inclus dans `result.actualCost`),
sans double comptage. Ce qui reste est plus petit mais réel.

- `builder_air.nut:744-763` — `OpexAirReserveJoinedStops` charge le coût des arrêts sur le capital
  à l'élection, mais **rien n'est ajouté côté demande** (le commentaire l'assume : le bassin est
  inconnu avant que la station existe). Biais directionnel proportionnel au nombre d'aéroports
  **neufs** : 4 arrêts réservés pour un `newpair`, 2 pour un `hubsite`, 0 pour un `hubhub` —
  c'est-à-dire exactement dans le sens qui **défavorise l'ouverture de nouvelles paires**, alors
  que l'écart mesuré contre AAAHogEx est un écart de volume. Second point : la réserve utilise la
  constante 2 et ignore `AIR_JOINED_STOP_LIMIT` (08.6).
- `builder_air.nut:1454-1465` — le captage marginal d'un arrêt joint n'exclut que **sa tuile**
  (`dx + dy <= airportCoverage`) puis retient la production de **tout le disque** de rayon
  `coverage`, dont une partie reste dans la couverture de l'aéroport. La déduplication *entre
  arrêts* utilise pourtant le bon critère (`2 * coverage`, `:1505`) (08.9).
- `builder_air.nut:716-718` — `monthlyPax = baseMonthly + joinedMonthly` additionne 22 % d'une
  **population** et une somme de `GetCargoProduction` : le `monthlyPax` réconcilié **n'a pas
  d'unité homogène**, et il alimente le profit et le ROI post-chantier, c'est-à-dire la grandeur
  qui sert de vérité aux registres (08.10).
- `builder_air.nut:1045`, `:1233-1234`, `:1290-1291` — les 22 % sont écrits en dur trois fois
  alors que `TOWN_CATCHMENT_SHARE_PCT` est employé dix lignes plus haut dans le même fichier
  (08.8).

**Gravité de groupe : P2.**

- **Modèle : Opus 5, effort medium** (Codex sol, medium). Ce n'est pas un bug de logique : c'est
  l'unité et la symétrie d'un modèle de ROI. 08.10 en particulier demande de décider **quelle
  grandeur** `monthlyPax` doit porter, ce qui touche aussi le chemin `AIR_DEMAND_PLAN`.
- **À chiffrer avant d'agir, pas à supposer** : l'amplitude de 08.6 dépend de
  `catalog.costRoadBusStop` (`catalog.nut:684`). Le mesurer décide si le groupe vaut un commit.
- **Ne pas signaler comme bugs** : `airportDelayDays = 3.0` et `OpexAirCadenceCap` sont les
  approximations connues du chantier C61 (`docs/taches.md:759-762`), pas des nombres magiques.

**Clôture B9 — workspace du 2026-09-16.** Les quatre résidus sont maintenant soldés, sans
adoption de default AIR :

- **08.6** : la sonde a montré que `BT_BUS_STOP` n'est pas une réserve exacte du coût traversant
  joint (environ 450..2250 £/arrêt selon les builds exposés). Les arrêts joints sont donc
  optionnels avant chantier : coût/demande joints nuls au choix, puis `actualCost` réel après
  chantier ;
- **08.8** : les trois littéraux 22 % ont été remplacés par
  `TOWN_CATCHMENT_SHARE_PCT` ; la politique 22 % elle-même n'est pas changée ;
- **08.9** : le modèle post-build utilise l'union réelle de la station moins le catchment propre
  de l'aéroport. Pré-fix, le brut surestimait le marginal sur 50/63 endpoints ; post-fix,
  `model_error_pax=0` sur 59/59 endpoints neufs ;
- **08.10** : le default population-proxy n'additionne plus une production physique ; ce marginal
  n'est ajouté que dans le mode explicitement production-based.

Preuves : `review_b9_air_catchment_smoke_2x3_v4.json` **2/2** ;
`review_b9_air_catchment_reconciled_5x6.json` **10/10**, 148 builds / 296 endpoints, horizon
complet, zéro invariant cassé ; tests B9+freeze **17/17**, selftest et `py_compile` OK.

Le placement reste une différence descriptive : sur le sous-ensemble STNN comparable, AAAHogEx
est à 6,06 tuiles du rectangle-ville en moyenne et couvre le centre dans 37,85 % des snapshots,
contre 7,47 / 20,0 % pour Opex. Le TownID STNN est normalisé par un offset dominant +1 inféré des
mêmes aéroports Opex, non codé en dur. Les chunks ne donnent pas la production catchment exacte
d'AAAHogEx.

**Non-adoption explicite :** `air_demand_plan=1` possède déjà l'autorité
`bench_air_demand_plan_10y.json` (20×10) défavorable : **−51,5 % `profit_year`**, 5/20,
`p_signes=0,041`. Une variante B9 intermédiaire encore plus conservatrice a supprimé tout AIR
Opex dans son 5×6 et a été retirée. Aucun 20×10 nouveau n'est justifié. Les defaults restent
`air_demand_plan=0`, `air_catchment_probe=0` et `early_slot=1`.

---

## Tier 2 — Artefacts de mesure in-game, pièges dormants et dette structurelle

### M1. Les canaux de mesure in-game publient des constantes et des agrégats infaisables

**Constats** : 06.7 (P2), 13.3 (P2), 06.4 (P2), 15.3 (P2), 05.3 (P2), 13.6 (P2), 06.8 (P3),
13.8 (P3). Cf. aussi 06.3, traité en H5.

Un seul motif : **un panneau ou un compteur survit à la suppression du mécanisme qu'il mesurait**,
et continue de publier une valeur qui se lit comme une mesure.

- `projects.nut:821-822`, `:1353-1354`, `:1526-1527`, `:1933`, `:2087-2088` — cinq sites écrivent
  `knapsackNodes = 0` et `knapsackExact = true`, jamais retouchés : **il n'existe plus aucun sac à
  dos ni branch-and-bound dans le dépôt**. Le champ 5 du panneau `IG|` est donc la constante `0`
  sur toutes les parties, sous un commentaire de 7 lignes — **identique au caractère près dans
  `task_projects.nut:890-893` et `scheduler_tasks.nut:294-297`** — qui explique pourquoi ce champ
  permet de « distinguer *le solveur a prouvé l'optimum* de *il a épuisé son budget de nœuds* ».
  Un dépouillement qui le lit conclut « optimum prouvé à chaque passe » (06.7, 13.3). **C'est la
  scorie la plus dangereuse du lot, parce qu'elle est branchée sur un canal de banc.**
- `projects.nut:2091-2100` — `selectedCapital` somme le capital des **64** projets retenus, chacun
  testé **seul** contre le budget entier : la somme le dépasse d'un ordre de grandeur et décrit un
  portefeuille infaisable, pourtant publié dans `IB|`. `capitalRemaining` est écrit sur trois
  chemins, **lu nulle part**, vaut 0 en permanence, et alimente le champ `remaining=` du journal
  VIVIER (06.4).
- `projects.nut:714`, `:1347`, `:1933` — `poolInfundable` et `modeReplaced` ne sont incrémentés
  nulle part ; le premier est publié sous l'étiquette `infundable=`, un zéro constant présenté
  comme une mesure du vivier écarté faute de capital — information qui **existe pourtant** sous le
  nom `budgetRejected` (06.8).
- `ledgers.nut:335-338` — `local val = 0;` puis `company_value=` dans le rapport C50. Codé en dur
  depuis le commit qui a introduit la fonction, et **aucun appel à `AICompany.GetCompanyValue`
  n'existe nulle part dans `ai/OpexAI`** : la métrique que le projet désigne comme celle qui
  compte n'est jamais lue par l'IA, y compris dans la sonde censée en tracer la chronologie (15.3).
- `candidates.nut:2049-2053` — `stats.profitTooLow` est incrémenté à la fois pour un rejet réel et
  pour un candidat **conservé**, puis publié sous `OpexDecide("VIVIER_REJECT", …)` : qui lit ce
  compteur pour mesurer l'attrition du vivier surestime les rejets économiques. Chemin toujours
  actif via le fret (05.3).
- `task_rail.nut:374-376` — le panneau `EU|` est posé **inconditionnellement** à chaque dispatch
  de `_expandRailLines`, alors que `rail_expand = 0` fait sortir la boucle immédiatement : cinq
  zéros, un `AISign.BuildSign` par cycle de file pendant toute la partie. Le pool de panneaux est
  une **ressource finie partagée par toute la mesure**, et l'entonnoir d'expansion lu par
  `sweeps/opex_full_campaign.py:1162` est noyé sous des milliers de lignes nulles (13.6).
- `task_projects.nut:883-906` vs `scheduler_tasks.nut:287-307` — le duplicata a divergé : `IB|`
  porte ici un quatrième champ `|B<batchBuilt>` absent côté scheduler, et le budget de
  30 caractères annoncé suppose un `batchBuilt` à un chiffre (13.8).

**Gravité : élevée à P1 pour le sous-ensemble branché sur un canal de banc** — 06.7/13.3, 06.4,
15.3, 05.3. Le reste reste P2/P3. C'est le mode d'échec dominant du projet appliqué à lui-même :
la mesure ment, et elle ment dans le sens rassurant.

- **Modèle : Sonnet 5, effort medium** (Codex terra, medium). Suppression, renommage et
  réécriture de commentaires périmés, sans changement de comportement. Le seul jugement à porter
  est « supprimer le champ ou l'alimenter », **champ par champ** : `knapsackExact` doit disparaître
  (le mot « optimum » n'a plus d'objet), `company_value` doit être alimenté, `poolInfundable` doit
  être remplacé par `budgetRejected`. Les deux copies de 13.8 se corrigent ensemble.
- **Ordre : tôt.** C'est bon marché et c'est un prérequis de lecture pour le dépouillement de B2.

### M2. `"mode" in line` sans test de valeur : trois mécanismes rendus silencieusement inopérants

**Constats** : 04.1 (P1), 04.2 (P1), 02.2 (P2).

Toute ligne rail construite porte désormais `mode = "rail"` (`task_rail.nut:1014`,
`candidates.nut:813`). Trois filtres testent la **présence** du champ au lieu de sa **valeur** —
et le prédicat correct existe à six endroits des mêmes fichiers (`candidates.nut:993`, `:1012`,
`:1284`, `lines.nut:381`, `:406`, et tous les filtres route vérifiés par l'étape 4).

- `candidates.nut:1361` et `:1420` — `OpexPlaceJoinPax`/`OpexPlaceJoinFreight` : `stations`,
  `sources` et `sinks` restent **toujours vides**. **Le mécanisme H2 entier** — la jointure d'une
  extrémité libre sur une gare déjà bâtie, décrite en détail par les commentaires C29 « DE LA
  GUILLOTINE AU FILET » — **est un no-op complet**, pax et fret (04.1).
- `candidates.nut:1310-1322` — `OpexStationCargoLineCount` rend toujours 0, donc `OpexShareBasin`
  fait `amount / 1` : le partage de bassin est une **fonction identité déguisée** (04.2).
- `lines.nut:223`, `:254` — `OpexJoinCompatible` rend toujours `false` face à une vraie ligne rail,
  donc la branche de succès de `OpexFindStationJoin` est inatteignable et `refuse` reste bloqué à
  `"N"` (« aucune ligne rail avec un plan de quai ») même quand le conflit **est** une ligne rail
  avec quai. En aval, `OpexOriginJoinable` (`candidates.nut:1301-1307`) ne peut jamais récupérer
  une origine déjà desservie (02.2).

**Gravité de groupe : P2 comme bug, P1 comme piège de mesure.** Les quatre drapeaux concernés
(`join_place`, `basin_share`, `station_join`) sont à 0, donc aucun effet en production. Mais
chacun est **garanti à zéro effet quel que soit son mérite** : un banc les mesurerait comme
« testés et neutres ». C'est la même famille que H2, avec une autre cause.

- **Modèle : Sonnet 5, effort low** (Codex terra, low). Trois prédicats à aligner sur celui qui
  existe déjà. Le périmètre est borné et vérifié : l'étape 4 a **lu** les filtres route pour
  confirmer qu'ils n'ont pas le défaut, et l'étape 5 l'a reconfirmé.
- **Règle de séquencement** : corriger **avant** qu'un banc touche l'un de ces drapeaux, et
  **jamais dans le même commit** qu'un banc — sinon le banc mesure le correctif et le drapeau
  ensemble.

### M3. G12 : le matériel est élu avant tout calcul de ROI

**Constats** : 03.1 (P2), 03.2 (P2), 03.3 (P2). Statut inchangé depuis le 09-06, confirmé site par
site.

- `catalog.nut:363-377` — un seul wagon par cargo, sur la seule capacité, sans départage de prix,
  de coût d'exploitation ni de poids, et **sans départage d'égalité** (le premier trouvé gagne,
  ordre `AIEngineList` non garanti).
- `catalog.nut:713-728` — même schéma pour la route ; la justification écrite porte sur le type
  d'arrêt, pas sur pourquoi la capacité prime sur toute mesure économique.
- `catalog.nut:533-536`, `:578-579` — un seul avion par type d'aéroport, et pour les grands
  aéroports **n'importe quel gros avion gagne sur n'importe quel petit** avant même de regarder la
  capacité. L'arbitrage ROI existe *entre* types d'aéroport (jusqu'à 5 `airCombos`), jamais
  *entre* avions compatibles d'un même type.

Contre-exemple « bien fait » dans le même fichier, à répliquer plutôt qu'à inventer : le départage
locomotive à quatre critères (`catalog.nut:437-495`), qui ne réduit pas l'ensemble évalué.

- **Modèle : Sonnet 5, effort high** (Codex terra, medium-high) — inchangé depuis le 09-06. Peu
  visible en vanilla homogène, **porte d'entrée si le projet ajoute un jour des NewGRF**.
- **Opportuniste** : le §3 de G12 (filtre de feeders sur le mauvais objet catalogue) partage son
  terrain avec B1 — à faire dans la foulée de B1, pas dans un passage catalogue isolé.

**Clôture M3 — workspace du 2026-09-16.**

Le lot a été repris measurement-first avec une sonde `equipment_roi_probe=0` par défaut
(contrat désormais **230 settings**). Aucun choix catalogue n'est modifié sous 0. Sous 1 seulement,
les alternatives wagon/route/air sont conservées pour calculer un contrefactuel avec les fonctions
économiques réelles, avant admission puis après route/site ; route et air publient en plus la
capacité réellement observée après refit. `native_choices` et `refit_proxy_choices` restent des
canaux distincts.

La réconciliation du code courant corrige deux formulations historiques : la locomotive rail est
déjà couplée au convoi et départagée physiquement/économiquement ; le vieux filtre feeder sur le
mauvais objet est déjà remplacé par `OpexHubPaxCatchmentRadius(hub)`. Les résidus actifs sont donc
le wagon unique, le véhicule route unique et surtout l'appareil unique par type d'aéroport. La
préférence de type d'aéroport (`bestPlan.airport.allowBig`) reste une politique séparée et n'a pas
été changée par M3.

Validation : tests freeze+M3+B9 **23/23**, selftests bench + analyseur M3 OK, `py_compile` OK,
`git diff --check` OK. Smoke final
`results/review_m3_equipment_roi_smoke_2x3_v5.json` : **4/4 bras sains**.
Diagnostic `results/review_m3_equipment_roi_5x6.json` : **10/10**, horizon complet,
135 887 événements. Rail : 55 106 comparaisons et aucun multi-choix. Route : 736 comparaisons,
18 multi-choix mais zéro regret/flip. Air : 79 807 comparaisons multi-choix, 75 742 sélections
différentes du meilleur profit, 77 884 du meilleur ROI et **2 371 flips d'admission** sur 78 077
pré-admissions ; regret profit moyen +7 776,81 £/an, max +31 825 £/an.

En vanilla/OpenGFX, aucun `refit_proxy_choice` n'est exposé et les 158 capacités air + 80 route
observées après refit ont un delta nul : **pas de P1 de mesure démontré**. Le risque NewGRF reste
non mesuré et ne doit pas être extrapolé depuis ce banc.

Décision : **M3 est clos comme diagnostic, sans adoption**. Le signal air définit une piste P2
concrète — choix d'appareil économique par route — mais le meilleur appareil varie réellement par
route (le catalogue choisit toujours 228 ; les meilleurs profits se répartissent notamment sur
218/217/223). Ce n'est pas un correctif technique P1 ; aucun comportement/default n'est changé et
aucun 20×10 n'est lancé dans cette passe.

Le lot a aussi corrigé deux défauts P1 du harnais révélés par le smoke : sérialisation Windows du
`result_processor` lancé depuis `__main__`, et selftest de télémétrie ligne périmé après
l'ajout du champ `airport`. Le contrôle CLI 1×1 final passe ; les runners B9/M3 conservent les
logs moteur sans changer le schéma métier existant.

### M4. Conformité NoAI : configurations désormais exercées, aucun P1

**Constats** : 16.1 (P2), 16.2 (P2), 16.3 (P3), 16.4 (P3), plus 10.5 (P2).

Ce groupe n'est pas une liste de bugs, c'est une **absence de banc** : la checklist de
`docs/00_conseils.md` (« 90 % des crashs d'IA viennent des bancs Redirect Left ») n'a toujours pas
été exercée.

- `pf.forbid_90_deg` : **zéro occurrence** dans les 34 fichiers. Le rail passe par
  `import("pathfinder.rail", …)` (`main.nut:28`), dont le source n'est pas vendorisé : son
  traitement réel est **invérifiable depuis ce dépôt**. Le code OpexAI qui l'entoure est
  correctement borné (`builder_rail.nut:377-410`) et `OpexBuildDepot` absorbe un refus de virage
  (4 offsets testés), donc le risque n'est ni confirmé ni réfuté — **il est à tester** (16.1).
- `vehicle.max_trains`/`max_roadveh`/`max_aircraft`/`max_ships` : aucun chemin de décision ne les
  consulte. Les deux seuls lecteurs sont une sonde passive (`tension.nut:133-137`) et un journal
  a posteriori (`ledgers.nut:255-265`). Avec `max_trains = 0` au démarrage, l'IA génère des
  candidats rail, **paie de vrais chantiers de voie, gare et dépôt**, et n'échoue qu'à
  `BuildVehicle` — pas de crash (le rollback est vérifié robuste), mais un gaspillage systématique
  le temps que chaque paire du vivier soit découverte une à une comme irréalisable, et un
  cooldown de 365 jours derrière. **Un unique `AIGameSettings.GetValue` en tête de cycle l'éviterait
  pour tout le mode** (16.2).
- Empreinte RAM de la VM Squirrel : confirmée jamais mesurée, et **non mesurable depuis le
  script** (l'API NoAI n'expose aucun accesseur de tas). Seule une mesure externe le peut (16.4),
  et 10.5 donne la structure à surveiller en premier : une entrée par tuile de carte, ×16 à 1024²,
  ×64 à 2048², reconstruite à chaque chargement.
- 16.3 est **reclassé P3 et clos** : OpenTTD n'expose pas d'interrupteur `enable_rail/road/air/
  water`, le seul levier est le plafond de véhicules (16.2), et le cas voisin réellement présent
  dans l'API — un mode sans aucun engin constructible — est proprement géré
  (`catalog.nut:326-349`, `candidates.nut:59`).

- **Modèle : Sonnet 5, effort medium** (Codex terra, medium), mais **le livrable est un banc, pas
  un diff** : trois runs (90° interdits ; `max_trains = 0` au démarrage ; carte 1024²) plus une
  mesure RAM externe. Le seul correctif de code justifié aujourd'hui est le test unique de 16.2.
- **Opportuniste** : « réglages de partie avec mode désactivé, RAM Squirrel » figurent déjà parmi
  les sujets *disponibles* de `docs/taches.md:835-836`, sans fiche numérotée. **À promouvoir en
  tâche numérotée** : c'est la seule famille de crash que le projet n'a jamais exercée, et le coût
  d'entrée est de trois parties.

**Clôture M4 — mesure dynamique du 2026-09-16.**

Le lot n'est plus une simple absence de banc. `sweeps/run_m4_conformity.py` exerce deux scénarios
sur les mêmes cinq graines pendant six ans, avec santé/horizon fail-closed et C63 :

- `max_trains=0` : **10/10 runs sains**, zéro train et zéro station facility rail Opex finaux,
  30 projets rail choisis et 15 `NOTRAIN`. C63 enregistre `n_fail=16`,
  `actual_fail=176313`. Huit années-graines où `NOTRAIN` est l'unique raison d'échec cumulent
  **120 018 £** à elles seules : le gaspillage d'infrastructure avant découverte du plafond est
  causalement prouvé. Voie/dépôt ne sont pas comptés séparément par le parser physique ;
- `pf.forbid_90_deg=1` : **10/10 runs sains**, aucune erreur NoAI, 34 projets rail choisis et du
  rail construit dans les cinq graines (1/4/2/2/2 véhicules rail finaux). L'hypothèse
  crash/boucle n'est pas reproduite sur ce périmètre ; le banc ne prétend ni auditer les internals
  de la bibliothèque externe ni prouver la neutralité économique.

Le contrôle `results/review_m4_conformity_control_5x6.json` est également **10/10 sain**.
Descriptivement, le scénario `max_trains=0` finit à −3,70 % de `profit_year` moyen et −1,95 %
de `company_value` moyenne face à ce contrôle sur ces cinq graines. Ce résultat n'est pas une
autorité d'adoption et n'ouvre aucun 20×10.

16.2 reste **P2**, pas P1, mais il a ensuite été corrigé explicitement :
`OpexRailVehicleSlotAvailable()` rejette avant A*/devis et `OpexExecuteRailPlan` refait la garde
juste avant la première dépense. `results/review_m4_162_fail_before_spend_5x6.json` donne 10/10 runs
sains sous `max_trains=0`, zéro projet rail choisi, zéro `RAIL_BUILD_FAIL`, `actual_fail=0` et
`pure_notrain_actual_fail=0`. Aucun 20×10 n'est requis pour ce correctif de sûreté/admission.

16.3 demeure clos/non-bug. **16.4 / 10.5 est désormais clos comme mesure externe** : le micro-banc
`WaterMemoryProbe` reproduit l'allocation dominante du constructeur Lakes et la garde vivante pour
mesurer le RSS du processus. Sur 256²/512²/1024², `results/review_water_memory_10_5_16_4_v3.json`
donne respectivement 127,44 / 127,64 / 127,94 B par tuile et ~14,001 opcodes/tuile. Le 2048² long
`results/review_water_memory_2048_long_3x.json` termine 3/3 : delta RSS médian 524 788 KiB
(128,12 B/tuile), 58 726 159 opcodes nets (14,0014/tuile), 5 872 ticks, HWM processus max
698 444 KiB. L'échec à horizon court était une allocation non terminée, sans preuve d'OOM ni de
plafond `AIList`. Aucun changement de comportement/default n'est adopté. **M4 reste clos comme
diagnostic/conformité**, avec 16.2 clos techniquement et 16.4 clos par mesure.

Cette mesure n'ouvre plus C57 : la décision postérieure est de retirer Lakes lors de C67. Le coût
mesuré (~128 B/tuile) sert désormais de baseline à battre par la représentation compacte en blocs,
pas de justification pour optimiser l'`AIList` actuel.

### M5. G2 résiduel : l'invalidation événementielle reste optionnelle et à 0

**Constats** : 12.1 (P2), 12.2 (P3).

- `event_handlers.nut:770-808` — `_onEngineAvailable` rafraîchit les bornes du catalogue
  **sans aucune garde** (`OpexRefreshEpochBounds`, ligne 774), mais le bloc qui pose
  `_portfolioInvalidated` et remet `dueCycle = 0` est gardé par `C39_ENGINE_REFRESH`, **défaut 0**.
  Au défaut, chaque nouveau moteur modifie tout de suite les bornes utilisées par la génération
  sans forcer la reconstruction du portefeuille dérivé dans le même mois. Borné à un seul type
  d'événement et documenté comme expérimental non adopté : ce n'est pas une régression silencieuse.
- `event_handlers.nut:354-384` — `_onIndustryClose` rafraîchit le catalogue sans jamais invalider
  le portefeuille, **asymétriquement** à `_onIndustryOpen` et `_onTownFounded` qui, sous le même
  genre de garde, déclenchent systématiquement les deux. Inerte au défaut, mais le réglage est
  prévu pour être activé.

- **Modèle : Sonnet 5, effort low** (Codex terra, low), **en passant** par un commit qui touche
  déjà `event_handlers.nut`. Jamais en tâche dédiée : le volet lourd de G2 est fermé.

### M6. Périmètre dormant : ne rien justifier par ces chemins

**Constats** : 05.2 (P1 en tant que cadrage), 05.4 (P3), 05.5 (P3), 05.7 (P3), plus 06.9, 06.10,
06.12 (P3, inertes au défaut).

Vérifié à la main par l'étape 5 : `road_pax_build = 0`, `road_pax_extensions = 0`,
`feeder_candidates = 0`, `air_split_feeder_test = 0` et `c42_subsidies = 0`. **Sur les cinq
fonctions que l'enjeu de l'étape 5 annonçait, seule `OpexRoadFreightCandidates` génère réellement
des candidats au défaut.** Chaque réglage porte sa justification (préserver la demande
aéroportuaire, banc défavorable, stratégie legacy) — ce n'est pas un bug, mais ça reclasse tout ce
qui vit derrière.

**Gravité : abaissée à P3 en tant que défaut** (aucun code livré n'est en cause), **conservée comme
cadrage P1 de la priorisation** : aucun correctif de ce document ne doit être justifié par l'un de
ces chemins, et `docs/taches.md:763-764` le dit déjà pour la route (« une réforme visant les bus
interurbains ne résoudra pas le duel courant »).

- **Modèle : aucun correctif aujourd'hui.** Sonnet 5, low, si l'un des cinq est un jour rallumé —
  et dans ce cas 05.4 (borne `roadGenMax` ignorée par la seule famille qu'elle visait) est à
  corriger **avant** le banc, sinon la famille sous-génère silencieusement la bande qu'elle devait
  admettre.

### M7. Ordonnanceur : trois contrats implicites sans garde-fou

**Constats** : 11.1 (P2), 11.3 (P3), 11.5 (P3), 11.8 (P3).

- `main.nut:290-325` / `scheduler.nut:214-243` / les 15 `_dispatch*` — le contrat « nom de tâche »
  vit en trois endroits sans table nom→fonction. Les trois listes sont vérifiées **identiques
  aujourd'hui** (extraction + diff, 15/15/15). Le risque historique était qu'un renommage à un seul
  endroit tombe dans la branche par défaut et désactive la tâche silencieusement. **Workspace
  courant : corrigé** par un `AILog.Error("Unknown scheduler task name: " + task.name)` placé
  avant `task.enabled = false`. La sémantique du fallback et des tâches connues reste inchangée.
- `scheduler_tasks.nut:678-693` — seul site de récursion de l'ordonnanceur. Pas de risque de pile
  (profondeur bornée par la file), mais `_runNextTask()` réécrit `_c41LastTaskName`, si bien que
  `_runNextTaskWithSlackLedger` attribue les opcodes de l'appel **entier** à la tâche *suivante*,
  jamais à `town_growth` — c'est-à-dire qu'il fausse la télémétrie même qui doit servir à
  revérifier le sous-effectif de gares (11.3).
- Trois familles de deadline non unifiées et documentées précisément — `dueCycle`, cadences
  calendaires internes aux dispatchs, budgets d'opcodes — dont **aucune ne connaît les deux
  autres**, chacune ajoutée par une fiche différente (11.5). Et `_lastAirFleetMonth`
  (`main.nut:166`), déclaré, non persisté, sans lecteur dans le périmètre (11.8).

- **Modèle : Sonnet 5, effort medium** (Codex terra, medium) pour 11.1 seul : une table
  nom→fonction, ou au minimum une `AILog.Error` sur nom inconnu. Petit diff, supprime un mode de
  défaillance lent à diagnostiquer.
- **Ne pas unifier les trois familles de deadline dans le même commit** (11.5) : c'est une refonte
  de l'ordonnancement, pas un correctif, et rien ne montre aujourd'hui qu'elle rapporte. 11.3 et
  11.8 sont de l'hygiène à greffer.

**Clôture M7/11.1 — 2026-09-16.** Le patch est volontairement limité à une ligne de diagnostic
dans `scheduler.nut`. `sweeps/c65_pass3.py` lit maintenant la vraie `_taskQueue`, et
`sweeps/test_scheduler_task_contract.py` vérifie l'égalité exacte file/cascade/handlers ainsi que
l'ordre log → disable → return du fallback inconnu. Tests ciblés+freeze **13/13**, selftest C65
**14 événements / 15 tâches**, `py_compile` et `git diff --check` OK. Smoke post-`.nut`
`results/review_m7_scheduler_smoke_2x3.json` : **4/4 sain**, horizon complet, aucune erreur NoAI
ni occurrence du fallback sur les tâches normales. Pas de 5×6/20×10.

Réconciliation des voisins : 11.2 est déjà corrigé par les retours booléens de
`task_town.nut::_tryTownGrowth` ; 11.3 reste dormant/non exposé sous les defaults actuels ;
11.6/11.7 sont clos par B5 ; 11.8 est caduc. Aucun de ces voisins n'est promu par M7/11.1.

---

## Tier 3 — Hygiène, à faire uniquement en passant

Jamais en tâche dédiée : greffer sur le commit du groupe qui touche déjà le fichier.

| Constat | Objet | Greffer sur |
|---|---|---|
| 03.4 | `OpexTensionMacroRegime` + `OpexProjectScoreForRegime`, **160 lignes de code mort inatteignable même drapeau activé** (`tension.nut:311-470`) | M3 (même famille catalogue/scoring) ou le jour où `tension.nut` est rouvert |
| 02.3 | `_tryRepayLoan` n'a pas la garde `interval <= 0` de son symétrique `OpexTryReborrow` (`capital.nut:118-121`) | tout commit touchant `capital.nut` |
| 04.4 | seuil d'acceptation `8` en dur au lieu de `ROAD_ACCEPTANCE_FULL_UNIT` (`candidates.nut:549`) | M2 (même fichier) |
| 05.6 | `OpexBands` aveugle sous 25 et au-dessus de 200 tuiles, précisément sur la partie la plus récente du domaine rail | B5 ou B2 (diagnostic) |
| 05.8 | commentaire citant un réglage `tree_planting` qui **n'existe pas** (`candidates.nut:3184-3188`) | M2 |
| 08.11 | deux globales jamais lues, un champ de sonde mort, une variable masquée, une disjonction inatteignable | B1 |
| 09.5, 09.6, 09.9 | formule du plafond recopiée à la main, docstring qui annonce un plafond non appliqué, commentaire `MAX_ROAD_VEHICLES = 2` contre une constante à 8 | B3 |
| 13.9, 13.10 | paramètre `year` inutilisé et `budget_before` trompeur ; `OpexC41RepairJunction` rend `0` pour deux échecs différents | B2 |
| 15.4 | retour inatteignable après le chemin de succès (`task_water.nut:77`) | B7 |
| 01.9, 01.10 | justification physique d'un réglage chiffrée avec une valeur qui n'est plus le défaut ; deux replis de globale divergents de leur défaut déclaré | H2 |
| 06.9, 06.10 | `generationCapitalBudget` figé sous `portfolio_cache` ; `emptyCause` calculé sur des listes périmées dans le chemin incrémental | B6 |
| 11.3, 11.8 | attribution d'opcodes corrompue par la récursion ; champ déclaré sans lecteur | M7 |
| 12.3 | le compteur `33/33 untracked` mesure l'absence de correspondance **ligne**, pas l'absence de remap véhicule | M5 |
| 17.13 | `results/smoke_ci.json` embarque **trois stdout moteur complets** à chaque porte de PR (`smoke_test.py:107-115`) ; le banc 1v1 les retire, pas le smoke | H4 |
| 17.14 | `vehicle_owner`, `station_owner` et surtout `attach_campaign_identity` sont du **code mort**, et cette dernière porte deux contrôles (identité de campagne instable, identité absente) que `main()` ne refait pas | H4 |
| 17.15 | une compagnie disparue en faillite entre dans la moyenne de `company_value` avec 0 mais est écartée de celle de `profit_year` : deux métriques du même tableau sur des effectifs différents | H1 |
| 17.16 | le timeout moteur patche `subprocess.check_output` du module entier : un téléchargement lent d'OpenTTD/OpenGFX devient un `engine_failure` de partie | H4 |
| 17.17 | ~60 réécritures complètes du stdout par partie (1 200 par banc de 20 graines), chacune avec `mkdir(parents=True)` | H4 |
| 21.1 | constante de rotor d'aéronef fausse (`subtype in (3, 4)`, le vrai rotor vaut `6`), rendue inerte par la garde `unitnumber == 0` (`physical_counters.py:246-251`) | tout commit qui touche `physical_counters.py`, sinon seul |
| 21.3 | `test_game_health.py` ne teste jamais un `company_value` décroissant à `fleet_changes == 0` — le cas exact que 17.6 corrige | H4, dans le même commit que le correctif 17.6 |

**Modèle pour ce tier, s'il était un jour isolé : Haiku (Codex luna), effort low.** Ne mérite pas
un passage dédié.

---

## Tier « ne pas toucher maintenant »

- **Tension / prix d'ombre** (G14 du 09-06). `tension_scoring` et `shadow_pricing` sont vérifiés à
  0 sur les quatre valeurs (`info.nut:1234-1240`, `:1259-1265`) ; C35.3/4/5 ont été mesurés et
  rejetés. **Ne pas ouvrir de tâche**, sauf si A1 (dans B6) veut réutiliser une forme de prix
  d'ombre — auquel cas relire avec Opus 5, effort high, vu la subtilité de dualité LP. Seule
  exception immédiate : 03.4 (160 lignes mortes), à supprimer en passant.
- **`biasPct` 170 / 121** (`projects.nut:205-206`). Surcoûts **réellement mesurés**, avec leur
  origine, leur statut et leur sortie documentés ; le facteur ne s'applique qu'à la part travaux
  et un devis réel le court-circuite. **Ne pas toucher, ne pas relitiger.**
- **`airportDelayDays = 3.0`, `OpexAirCadenceCap`, `OpexRoadPhysicalVehicleCap`** — approximations
  connues du chantier C61, pas des nombres magiques. Le travail est en B3/B9, pas une suppression.
- **`pathfinder_sleep_ticks = 0`** — décision « armes égales » explicitement gelée le 2026-08-29
  après lecture du code d'AAAHogEx. **NE PAS ROUVRIR.**
- **Les 8 globales définies en double ou en triple** — recomptées, **toutes portent la même valeur
  à chaque définition**, et `OpexLoadSettings()` les réécrit ensuite. Piège de maintenance, pas
  défaut de comportement. Ne pas relitiger comme un bug (étape 1).
- **G3, G7, G9, G8** — fermés, voir le tableau ci-dessous. Ne pas les rouvrir sous leur forme de
  2026-09-06.

---

## Statut des groupes G0-G12 (revue du 2026-09-06)

| Groupe | Statut | Justification (étape qui tranche) |
|---|---|---|
| **G0** — décision d'adoption + reproductibilité du banc | **FERMÉ — candidat non adopté** | H2 a gelé/résolu les réglages effectifs ; C66.4 officiel 20×10 a comparé 20 paires et rendu `fail_primary`. Defaults conservés : `abandon_gen_filter=1`, `abandon_cooldown_days=365`. |
| **G0bis** — profit par opcode absent des bancs | **FERMÉ côté H5** | Les sorties officielles publient maintenant le coût d'opcodes **observé** (`IG|/OB|A/RB|/OA|/OM|W`) et les densités associées, explicitement partielles et jamais présentées comme CPU total. Aucun default `loop_budget` adopté. |
| **G1** — portefeuille : borne, élection modale, objectif, fenêtre de cache | **FERMÉ sur ses 4 énoncés ; successeur B6 diagnostiqué** | Les quatre énoncés historiques restent clos. B6 a ensuite mesuré le cheap-first, le snapshot de capital et le recyclage ; aucun changement de politique n'a été adopté. |
| **G2** — réélection après abandon + invalidation événementielle | **FERMÉ pour l'essentiel, résidu mineur** | §1 **corrigé et vérifié sain deux fois** (12.H1, puis étape 13) : `_hadAbandonsThisPass` est posé par `_markPairAbandoned` sur tous les chemins, sans garde `DECISION_LOG`, lu et remis à zéro sans fuite. §2 **fermé côté `projects.nut`** (`_portfolioInvalidated` court-circuite bien la garde mensuelle). Résidu : 12.1/12.2, deux handlers dont le couplage reste derrière un flag à 0. → **M5** |
| **G3** — économie rail : recalcul post-tracé | **FERMÉ, vérification résiduelle soldée** | Blocking et resumable convergent vers `OpexCompleteRailRouteAfterSearch`, qui somme le tracé réel puis rappelle `OpexLineEconomics(... candidate.kind ..., routeDistance)`. Le même chemin couvre pax **et fret** ; aucune branche fret ne saute le recalcul. |
| **G4** — économie aérienne : refléter le trafic capté | **FERMÉ, résidu B9 fermé** | B9 a corrigé 08.6/08.8/08.9/08.10 et validé smoke 2×3 + 5×6 10/10, marginal joint exact 59/59. Aucun default AIR n'a été adopté. |
| **G5** — `rail_refleet` inatteignable | **FERMÉ via B5** | La garde refleet est inconditionnelle et B5 a corrigé la globale 01.1 qui empêchait `rail_expand=1` de vivre, puis verrouillé état/persistance par 11/11 tests et round-trips. Ne pas rouvrir G5 sous sa forme historique. |
| **G6** — A* rail bloquée par un échec | **FERMÉ via B5** | Le primaire libère correctement les plans en échec/cash ; le gel upgrade 07.1 a été traité par B5 et la machine d'état rail est réconciliée au reload. Les contrats B5 + smoke associés constituent la preuve actuelle. |
| **G7** — rollback aérien destructeur | **FERMÉ** | Étape 8, vérifié aux six sites : `OpexAirRollback` **n'ignore pas A** (ligne 1405), et **B est protégé** à chacun des six appels, qui passent tous `reuseA ? null : airportA` et `reuseB ? null : airportB`. Pour un plan `hubhub`, `reuseA` et `reuseB` valent tous deux `true` : l'échec ne démolit **rien**. Aucun aéroport existant ne peut être démoli, donc aucune ligne tierce cassée. Deux constats voisins **neufs**, de nature différente : 08.4 (orphelin délibérément conservé sur `BFAIL`) et 08.5 (résidu **véhicules**, pas aéroports). → **B1** |
| **G8** — terrassement d'exploration aérienne non attribué | **FERMÉ (caduc)** | `OpexAirCanLevelFootprint` (`builder_air.nut:407-419`) ouvre un `AITestMode()` avant `LevelTiles` et ne nivelle donc rien réellement ; le commentaire `:580` porte la marque du correctif (« G7§2 : test-mode seulement ; le terrassement réel est fait par le constructeur »). L'exploration ne dépense plus. **Ironie à noter** : c'est ce même correctif qui a créé 08.1, en laissant le verdict de terrain écraser celui de la sonde. |
| **G9** — quarantaine fret→ville + filtre feeders | **FERMÉ** | Étape 2 : `OpexAbandonedPairKey` (`lines.nut:268-305`) est maintenant symétrique — repli `"t" + srcTown` **et** `"t" + dstTown` — donc plus aucune collision `freight\|cargo\|id\|-1` ; le préfixe `"t"` exclut toute collision avec un ID d'industrie numérique. Étape 5 : `candidates.nut:2674-2677` porte la même clé (commentaire « G9§1 ») et `OpexRoadFeederCandidates` respecte désormais `ABANDON_GEN_FILTER` (`:2932-2938`, « G9§2 »). Les deux volets sont clos aux deux bouts. |
| **G10** — cycle de vie flotte air/route | **FERMÉ via B8** | Le sous-comptage historique est infirmé et B8 garde maintenant les projets flotte hors des lignes en liquidation ; contrats rebut 7/7 + smoke validés. Le 5×6 n'a pas exposé de rebut réel, limite conservée. |
| **G11** — constructeur maritime + feeder postal | **FERMÉ sur 10.1/10.2/10.3 techniques ; Lakes à remplacer** | Budget Lakes interruptible dans les parcours internes + distance navigable inconnue rejetée avant économie + connectivité préflight avant dépense ; tests ciblés/intégration et smoke final sains. 10.5 est mesuré jusqu'à 2048². Décision ultérieure : abandonner Lakes et C57 ; remplacement traité séparément par C67. |
| **G12** — catalogue : le matériel élu avant ROI | **FERMÉ comme diagnostic M3, non adopté** | M3 5×6 10/10 : rail non exposé multi-choix, route sans regret, AIR fortement exposé mais P2 de politique route-spécifique. Aucun P1 vanilla, NewGRF non mesuré, aucun 20×10. |

**Compléments de 2026-09-06 hors G0-G12.** *Tier 3 hygiène* : les trois points listés restent
valides, et 03.4 (`OpexTensionMacroRegime`, 160 lignes) est **reconfirmé code mort inatteignable
même drapeau activé**. *G14 (tension / prix d'ombre)* : statut inchangé, voir « ne pas toucher ».

---

## Constats non repris dans un groupe

Aucun. Les 132 constats des 19 étapes sont soit dans l'un des 21 groupes, soit dans le tableau
d'hygiène du Tier 3 avec le groupe auquel les greffer. Trois constats ne donnent lieu à **aucun
correctif** et sont conservés comme résultats négatifs, à ne pas redécouvrir :

- **15.1 — C56 : le cycle annuel n'en contient pas la cause.** Recherche à la main dans
  `task_report.nut`, `task_town.nut`, `task_water.nut`, `ledgers.nut` : aucune boucle `while`,
  aucun `try`/`catch` dans tout `ai/OpexAI` (donc une exception y resterait visible comme erreur
  NoAI et ne peut pas expliquer un arrêt « sans erreur »), toutes les boucles bornées. **Dit
  explicitement plutôt que de forcer un diagnostic.** Le candidat le plus solide reste 10.1 (B7),
  et le banc ne le verrait pas de toute façon (17.6, H4).
- **14.3 — G5 est rectifié, pas à rouvrir sous sa forme d'origine** (voir le tableau).
- **10.4 — le `Valuate` à fonction Squirrel est confirmé présent, mort et inoffensif** : motif
  réel, aucun appelant, et même réactivé aux tailles en jeu (~64 comparaisons contre un budget de
  10 000 opcodes/tick) il ne peut pas produire le crash « excessive CPU usage in valuator
  function ». Confirmé aussi transversalement par 16.V4 : c'est le seul du dépôt.

---

## Deux questions que les étapes ont explicitement renvoyées à celle-ci

**1. Le smoke test : 3 graines × 2 ans (code) ou 2 graines × 3 ans (convention écrite) ?**
(17.18.) Les deux coûtent six années-graine. Le code échange une année de profondeur contre une
graine de largeur. **Recommandation : aligner le code sur la convention écrite (2 × 3).** La
deuxième année fait apparaître le cycle de rapport annuel ; la **troisième** est la première où un
ferraillage peut suivre un rapport annuel et où B8 (14.1, 15.2) devient observable. Et le point
est de toute façon subordonné à 17.11 : tant qu'`expected_last_year` n'est pas passé à
`summarise`, la durée annoncée n'est pas vérifiée, donc le choix ne change rien. **Corriger 17.11
d'abord, puis trancher**, en confirmant avec qui a mesuré le budget « ~2-5 min ».

**2. Les fichiers de harnais couverts par aucune étape du plan.** (Renvoi de l'étape 17.)
`sweeps/physical_counters.py` (546 l.) et `sweeps/campaign_freeze.py` (545 l.) sont déclarés
fichiers de harnais de campagne (`CAMPAIGN_HARNESS_FILES`) et portent tout ce dont H3, H4 et le
gel de campagne dépendent, sans qu'aucune étape ne les ait lus. Idem pour les deux seuls tests
unitaires du harnais, `test_game_health.py` (428 l.) et `test_physical_counters.py` (448 l.).
Le `QUALIFIED_MODES["water"] = False` de `physical_counters.py:50` est **tranché ici** :
c'est un gating à appliquer chez les consommateurs (H3), pas une question ouverte.

**Étape 21 tenue le 2026-09-16** (`docs/revue/2026-09-15_etape_21_harnais_campagne.md`) :
le discriminant tête/composant de `physical_counters.py` est confirmé exact bit à bit contre les
en-têtes amont d'OpenTTD (`GroundVehicleSubtypeFlags`, `AircraftSubType`, `VehState`,
`StationFacility`) — la clôture C66.1 tient à une relecture fraîche, pas seulement à la confiance
dans les tests. Trois constats mineurs en sortent (21.1, 21.2, 21.3, détaillés dans le fichier
d'étape). **Réconciliation courante** : 21.3 est fermé par les tests H4 de valeur décroissante ;
21.2 possède désormais `test_campaign_freeze.py` pour le cœur fail-closed (230 réglages,
résolution/rejet des settings, garde de politique, fingerprint et état Git). La copie complète
`prepare_frozen_campaign` / bibliothèques reste sans test unitaire isolé, mais elle a été exercée
par les campagnes C66 gelées. Le vieux renvoi 21.6 vers `bench_v2.py` ne rouvre pas H2 :
les décisions C66.4/G0 passent désormais par le harnais gelé qui résout et compare les réglages
effectifs ; `bench_v2.py` générique n'est pas utilisé comme autorité d'adoption.

---

## Ordre d'exécution recommandé

1. **H1 + H2 + H3 + H4** — le harnais. Sans eux, chaque correctif suivant se valide sur un banc
   qui ne sait pas ce qu'il a joué (H2), ne teste pas les signes (H1), compte des wagons comme des
   véhicules (H3) et déclare saine une IA à l'arrêt (H4). Les quatre sont indépendants et peuvent
   partir en parallèle. **La décision G0 (05.1) se rend ici, pas plus tard.**
2. **H5** — G0bis (instrumentation opcodes) et **06.1 immédiatement**, qui est le seul correctif du
   document à comportement strictement identique : deux balayages du vivier supprimés sans changer
   un résultat de sélection.
3. **M1 + M2** — bon marché, sans changement de comportement, et prérequis de lecture : M1 supprime
   des constantes publiées comme des mesures sur des canaux de banc, M2 supprime quatre drapeaux
   garantis à zéro effet. Faire **avant** tout dépouillement et **avant** tout banc qui touche ces
   drapeaux.
4. **B1 + B4** en parallèle (fichiers disjoints : air vs route). B1 est le plus gros fait mesuré du
   dépôt, en trois commits mesurés séparément ; B4 ramène un mode d'échec que le dépôt croyait
   corrigé.
5. **B2 + B7** en parallèle. B2 est le **prérequis du chantier P1** lui-même : le diagnostic
   commun C63/C58 n'est pas lisible tant que 13.1 et 13.2 tiennent. B7 remonte immédiatement en
   tête si un gel reproductible réapparaît.
6. **B3 + B5 + B8** en parallèle (fichiers disjoints). Commencer B3 par le commit à comportement
   inchangé (journaliser `vehiclesForVolume`) : c'est la mesure qui manque pour trancher. **01.1
   part avant tout le reste de B5**, et avant toute reprise de G5.
7. **B6** — le portefeuille, en plusieurs commits mesurés séparément, **après** H1 et H5 et
   **après** avoir retrouvé le statut de banc de `portfolio_floor_pct`. C'est le préalable direct
   à A1, comme au 09-06.
8. **B9 + M3 + M4** : désormais **faits**. B9 est corrigé/validé ; M3 et M4 sont clos comme
   diagnostics non adoptés.
9. **M5 + M7 + Tier 3** : M7/11.1 est maintenant fait ; M5/M6 et 11.3 restent
   dormants/non exposés. Le Tier 3 reste de l'hygiène, pas une source de P1 courant.
   **Tier « ne pas toucher »** hors sujet tant qu'A1 ne le rouvre pas explicitement.

**Greffes opportunistes vers `docs/taches.md`** (vérifiées par grep ciblé, sans lecture
intégrale) : rouvrir le volet « consommateurs » de **C66.1** (H3) ; corriger la case « test des
signes » de **C66.4** (H1) ; **C66.2/C66.5** reçoivent H4 ; **C57** est désormais supersédé par
**C67** (analyse de carte par blocs + remplacement de Lakes) ; **C43/E3** reçoit le mécanisme
chiffré de `loop_budget` (11.4) ; **C61/C59 volet Route** reçoit le mécanisme de B3, sans lever sa
condition à P1 ; la **fiche 771** (`docs/taches.md:578-630`) reçoit B1, dont le candidat causal
pré-enregistré est déjà le §2. Les deux anciens trous cités ici sont désormais soldés :
`MONTHLY_FUNNEL_DETAIL` a été traité avec B2 et la conformité NoAI a été exercée par M4.
L'étape 21 possède désormais `test_campaign_freeze.py` pour son cœur fail-closed ; seule la copie
complète campagne/bibliothèques reste sans test unitaire isolé.

**Clôture H5 — 2026-09-16.** G0bis est désormais instrumenté avec un périmètre
explicite : sélection `IG|`, tentative rail `OB|A`, plan/build route `RB|`,
planification air `OA|`, planification eau des succès `OM|W`. Le JSON marque
`complete_cpu_measurement=false` et nomme le ratio
`final_profit_year_per_observed_mopcode`, afin de ne pas transformer cette couverture
partielle en faux « profit/CPU ». `test_campaign_freeze.py` passe 10/10, le smoke
2×3 `review_h5_final_smoke_2x3.json` passe et les invariants de somme des composantes
sont vérifiés sur `review_h5_observed_ops_2x3.json` et le diagnostic mensuel partagé.

06.1 et 06.3 étaient déjà corrigés dans le workspace réconcilié. Les deux
`GetSetting("road_cheap_trace")` résiduels ont été supprimés au profit de la globale
chargée une fois. 11.4 a été rejoué en 5×6 : cinq égalités exactes entre
`loop_budget=0` et `1` sur économie, physique et coût observé ; le bras est donc
écarté sans 20×10 et le défaut reste 0. 07.2 reste une limite connue du compteur
d'itérations, mais n'est pas corrigé au prix d'un changement de pathfinder :
`OB|A.result.opcodes` est désormais la source de coût réel rail du harnais et englobe les sondes
de structure. La relecture finale confirme aussi qu'aucun consommateur métier courant ne relit
`result.iterations`/`line.iterations` pour le classement ou le capital.

## Réconciliation M1/B6 — workspace du 2026-09-16

**M1 est clos sans changement métier.** Deux constats étaient déjà corrigés avant cette passe :
knapsackExact était déjà forcé à false et VIVIER ne publiait déjà plus infundable=0. Les écarts
encore actifs ont été corrigés : C50 lit la valeur trimestrielle réelle de la compagnie ; les vrais
rejets routiers profitNonPositive sont séparés des profitBelowFloorKept conservés ; les métriques
de pool sont nommées selectionPoolCapital / nextProjectCapital avec aliases IB/JSON historiques ;
PORTFOLIO_RANK distingue désormais score legacy, rank_score, budget_score, finance_capital,
turnover_bonus et generation_ratio. selectedCapital reste volontairement inchangé parce que
GROWTH_YIELDS le consomme.

Preuves M1 : test_m1_measurement_truth.py 8/8, selftest C50 OK, test B3 affecté 12/12,
py_compile OK et smoke review_m1_measurement_truth_smoke_2x3.json 2/2.

**B6 est clos comme lot P1 de diagnostic, sans adoption de politique.** Le 5×6 apparié
review_b6_portfolio_causality_paired_5x6.json a 10/10 runs sains. PORTFOLIO_MAX_BATCH=1 et
portfolio_floor_pct=0 sont observés partout. 630/639 sélections ont un capital vivant différent
du snapshot ; âge moyen 4,44 jours, maximum 12 ; 50 passages changent l'abordabilité, 1 203
bascules cumulées. Sur 501 choix comparables, le premier au fundScore diffère du meilleur profit
abordable 146 fois ; le contre-factuel est supérieur 145 fois, delta moyen +1 742 £/an, médiane 0,
maximum +23 113. 592/2 214 rangs ont un turnoverBonus non neutre et 164/476 top-5 ont un ordre
ROI différent de rank_score. 139/345 choix incrémentaux utilisent un projet recyclé ; âge moyen
14,36 jours, maximum 43. 06.12 reste dormant avec rail_prequote=0.

06.2 reste une **politique de classement**, pas un correctif automatique. portfolio_floor_pct=50
possède déjà une autorité postérieure au 09/09 défavorable (bench_floor50_10y_20seeds.json :
−4,94 % de valeur, 4 V / 16 D) : non-adoption confirmée et aucun nouveau 20×10.

**06.5 est désormais clos comme candidat non adopté.** Le diagnostic passif actuel
`results/review_b6_065_live_budget_5x6.json` rejoue le sélecteur exact sur des clones avec le capital
vivant : 41/630 choix changent, 39 avec un profit local supérieur, delta médian +17 322 £/an et
moyen +25 123,68 £/an. Le levier existant `portfolio_fresh_budget=1` a donc été testé sur C66.4
5×6 apparié (`results/review_b6_065_fresh_budget_c66_4_5x6.json`) : 5/5 paires complètes,
`profit_year` −135 528,6 £/an moyen, 1 V / 4 D, `company_value` −27,307 % en ratio des moyennes.
Signal négatif : pas de promotion en 20×10 et défaut conservé à 0. **06.11 est depuis clos comme
diagnostic P3, sans correctif général adopté.** Le Docker 5×6
`results/review_b6_0611_join_resolved_5x6.json` mesure le contre-factuel frais équivalent : 136/348
tops incrémentaux sont recyclés ; 117/127 tops fret sondés sont repricés exactement et 6/114 cas
décidables changeraient d'élection. Le refresh comportemental concurrent reste rejeté : il supprimait
les subventions et extensions routières du vivier incrémental sans les régénérer ensuite.

Validation post-instrumentation 06.5 : tests ciblés + selftest du diagnostic, compilation Python,
`git diff --check`, puis C66.3 `results/review_b6_065_final_smoke_2x3.json` **2/2** complet sans
erreur NoAI. L'instrumentation reste derrière `decision_log=1` et le défaut de politique reste 0.

Validation B6 : tests M1+B6 13/13, selftest du diagnostic OK, compilation Python OK et smoke
review_b6_portfolio_causality_smoke_2x3.json 2/2. Les écarts économiques du bras decision_log=1
mesurent aussi la perturbation d'instrumentation et ne sont pas une autorité d'adoption.

## Clôture G0 — autorité C66.4 du 2026-09-16

Les mentions antérieures « G0 ouvert » ci-dessus décrivent l'état constaté au début de la revue ;
elles ne sont pas réécrites rétrospectivement. La décision manquante est désormais rendue.

Le nouveau diagnostic factoriel
`results/review_g0_abandon_factorial_4arm_5x6.json` a comparé `1/365`, `0/365`, `1/0`
et `0/0` sur 5 graines × 6 ans. Il confirme causalement que le filtre de génération, l'expiration
du cooldown et les retries après libération sont réellement actifs. Le signal économique du bras
`0/0` était assez positif pour déclencher, et seulement déclencher, une autorité 20×10.

L'autorité officielle `results/review_g0_c66_4_20x10.json` utilise 20 paires × 10 ans,
`profit_year` comme primaire, +50 000 £/an comme effet utile minimal et -5 % comme garde valeur.
Les 20/20 paires sont complètes. `0/0 - 1/365` donne **+11 264,85 £/an**, 11 V / 9 D,
`p_signes=0,823803`; `company_value` est à **+2,759 %** en ratio des moyennes. Les champs
officiels donnent `sign_pass=false`, `primary_mean_pass=false`,
`value_guard_pass=true`, `verdict=fail_primary`.

**Décision : G0 clos, candidat non adopté.** Les défauts restent
`abandon_gen_filter=1` et `abandon_cooldown_days=365`. Aucun défaut `.nut` n'a changé, donc
la campagne elle-même clôt ce lot sans nouveau smoke. Bundle
`845c5b283d86c05fb3360445596e1967edde1d2cbfcd82fb19f08e7864b1dcb2`, manifest
`78c4ac1fe74189a119f954902b8a24242c44158bd812bc5d9a5792d4d7bb1047`.

## Passe résiduelle et preuves versionnables — 2026-09-17

Les résidus techniques hors eau ont été soldés : `task_rail.nut` vide `passDiscards` après les
deux flushes de `PROJECT_DISCARD`, le panneau `EU|` couvre désormais `RAIL_EXPAND || RAIL_REFLEET`,
le bit IG historique est parsé comme `selection_not_exact` avec
`knapsack_truncated=null`, et `bench_1v1_3y_10seeds.py` publie `n_vehicles` via le décodeur physique
H3. Le contrat ciblé `test_review_residual_contracts.py` est inclus dans la suite **61/61** passée
avant le smoke final.

Le smoke final post-`.nut` `results/review_final_residuals_smoke_2x3.json` est complet et sain sur
42/100 ; son manifeste enregistre correctement le workspace courant `dirty=1`. Les preuves citées
ci-dessus restent valides.

## C68 — sélection économique de l'avion par route, adoptée le 2026-09-17

Le diagnostic M3/G12 montrait un appareil catalogue statique alors que le meilleur profit variait
par route. C68 introduit `air_route_plane_selection` comme intervention minimale : après le choix
historique de la paire, des sites, du type d'aéroport et de la demande, les appareils compatibles
sont réévalués avec `OpexAirEconomics`; meilleur `profitAnnual`, ROI en départage. Sous `0`, le couple
historique appareil/économie est conservé.

Preuves : smoke post-implémentation `review_c68_air_route_plane_smoke_2x3_v3.json` **4/4 sain** ;
5×6 `review_c68_air_route_plane_5x6.json` **10/10 sain**, 4/5 graines positives et
**+235 565 £/an** moyen. L'autorité `review_c68_air_route_plane_20x10_v2.json` est complète
**20/20** : `profit_year` **+128 201 £/an**, 15 V / 5 D, `p_signes=0,041389`, IC95 du delta moyen
[12 230,64 ; 244 171,36] ; `company_value` +34,206 % en ratio des moyennes. Les trois conditions
C66.4 (`sign_pass`, effet moyen >= +50 000, garde valeur >= -5 %) passent ; verdict **`pass`**.

**Décision : adoption.** `air_route_plane_selection=1` devient le défaut livré. Le mécanisme ne
prétend pas corriger les routes éliminées plus tôt par `maxOrderDistance` de l'appareil catalogue ni
recalculer `AIR_DEMAND_PLAN` avec l'appareil C68 : ces pré-filtres restent volontairement hors de
l'intervention causale testée.

Le smoke post-adoption `results/review_c68_adopted_default_smoke_2x3.json` passe **2/2**. Le manifeste
confirme que C68 vaut 1 dans `defaults` et `effective`, alors que `explicit` contient seulement
`air_early_slot=1`, `abandon_gen_filter=1` et `abandon_cooldown_days=365`.

Résidu d'analyse explicitement conservé : les pertes finales de `profit_year` sur les graines
`7`, `42`, `1337`, `12345`, `424242` doivent être expliquées avant toute nouvelle généralisation de
la politique. L'hypothèse à tester est une interaction avec les propriétés de carte et la trajectoire
d'investissement, plutôt qu'un simple mauvais choix d'appareil uniforme. Le brut annuel
baseline/C68/delta des trois métriques principales est exporté dans
`results/review_c68_air_route_plane_20x10_v2_annual_metrics.csv`. La graine `7` est prioritaire car
elle termine aussi avec une `company_value` inférieure ; les quatre autres conservent une valeur
finale supérieure malgré leur perte de profit annuelle.
par cette revue sont désormais empaquetées sous `evidence/review/` en gzip déterministe. L'index
conserve les tailles et SHA256 du JSON brut et du gzip ; `sweeps/test_review_evidence.py` vérifie
décompression, hash brut, couverture des références et recompression déterministe. `results/`
reste ignoré, mais les preuves décisives sont maintenant versionnables.
