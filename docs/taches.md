# Liste des tâches

Backlog **actif** : uniquement ce qui est **en suspens ou à faire**.

⚠️ **Avant toute recommandation stratégique, grepper AUSSI
[`docs/taches_archive_2026-09-09.md`](taches_archive_2026-09-09.md)** — instantané verbatim de ce
fichier avant son nettoyage du 2026-09-09, qui garde tout l'historique : mesures, bancs, verdicts
adoptés **et rejetés**, pièges de méthode. Ce fichier-ci ne détaille plus les pistes écartées ; les
reproposer sans avoir lu l'archive est l'erreur classique du projet. Le détail d'une journée vit
dans `docs/journal_*.md`.

---

## 🔴 Où en est vraiment OpexAI — À LIRE AVANT TOUT LE RESTE

**OpexAI perd contre AAAHogEx, très largement.** Référence
(`results/bench_1v1_3y_1aeefe1_20seeds.json`, 20 graines × 3 ans, lecture appariée, 0 échec) :

| métrique | écart apparié vs AAAHogEx | graines gagnées |
|---|---:|---:|
| `company_value` | **−87,8 %** (602 750 £ contre 4 947 586 £) | **0/20** |
| `profit_year` | **−91,5 %** | **0/20** |
| `performance_history` | −71,0 % | 0/20 |
| `median_station_rating` | −12,0 % | 0/20 |

Décomposition : `8,5 % de profit = 12,4 % de volume × 68,6 % de rendement unitaire`. **~85 % de
l'écart vient du VOLUME** (8× moins de véhicules et de gares), ~15 % du rendement. La note de gare
presque au niveau ne veut PAS dire que l'IA est presque au niveau.

**Le goulot n'est pas la trésorerie** : avec ≥300 k£ en caisse, OpexAI ne construit rien dans
**61,2 %** des transitions mensuelles contre 2,8 % chez AAAHogEx ; 19,2 mois actifs sur 36 contre
32,4. Le goulot est le **débit du contrôleur** — sélection, planification, exécution.

⚠️ **Conséquence pour arbitrer** : toute décision qui réduit le volume pousse contre la métrique
n°1 identifiée, même si elle tient la valeur à court horizon.

---

## Comment lire les chiffres sans se tromper

- **Banc officiel = 20 graines × 10 ans apparié** (`AGENTS.md`). En dessous c'est un diagnostic :
  ne jamais changer un défaut sur un 5×3.
- **Une graine seule ne tranche rien** ([[banc_monograine_insuffisant]]). Plancher de détection
  ~15 % **pour les moyennes** ; en dessous, lire le test des signes — une moyenne peut être tirée
  par 2-3 graines divergentes alors que le compte de victoires est proche du hasard.
- **Un défaut « adopté » dans un document n'est PAS une garantie que le code l'applique.** Lire
  `info.nut` **et** `main.nut` avant de bâtir dessus (leçon `tree_planting`, régression invisible
  une journée entière).
- **Un cache exact peut changer la trajectoire** : moins d'opcodes ⇒ cadence de décision différente
  ⇒ chiffres différents à calcul identique (C41.30, C41.38, memo `origin_sitable`). Ne pas
  confondre avec un changement de comportement.
- `HEAD + PBS (e027037)` n'est pas une baseline valide (détail en archive).

---

## Fiches ouvertes

- 🔴 **C39 — Déclencher un rafraîchissement seulement quand il change la décision.** La tâche
  `catalog` appelle `catalog.refresh()` puis `OpexBuildProjects()` à chaque changement de mois (ou
  plus tôt sur événement / croissance du capital), et les 4 couches — catalogue, candidats,
  portefeuille, sac à dos — sont couplées sans critère de fraîcheur propre. `portfolio_cache`
  (C36.1) a montré que l'incrémental remplace un rebuild complet sans perte, mais au seul niveau
  portefeuille. Le gain visé est la **décision de déclenchement**, pas le coût d'un rafraîchissement
  individuel ([[catalogue_churn_et_cout]]).
  **Fait** : C39.0–C39.4 (sondes, trace, `EngineAvailable` non adopté, avions rejetés dominés) ;
  vérification API 15.3 des noms d'événements. **Reste** : le critère de staleness par couche.

- 🔴 **C41 — Scheduler opportuniste.** Ossature en place (registre de révisions, ledgers passifs,
  sous-catalogues ciblés) ; longue série de sous-tâches de profilage/cache close — **détail en
  archive, ne pas re-mesurer**.
  **Adoptés au banc officiel 20×10** : `c41_rail_pax_cruise_cache` (C41.30, −29,6 % d'opcodes
  rail), `c41_rail_freight_cruise_cache` (C41.38), `c41_rail_freight_acceleration_cache` (C41.40),
  `c41_rail_freight_town_service_cache`.
  **Reste** : le cœur de la fiche — l'admission opportuniste elle-même (C41.13/C41.14 ont préparé
  le contrat « couche + coût prudent + admission », mais la mesure a **refusé** l'admission : 0
  reliquat exploitable). Reportés : ⏸️ `OpexRoadPaxCandidates` (coût dominant, profil fait),
  ⏸️ C41.45 (dimensionnement de rame fret hors vitesse).
  **Mesure avant orchestrateur (2026-09-09) :** la sonde passive
  `c41_monthly_busy_ledger` attribue les opcodes de chaque mois à la tâche/continuation effective.
  Duel partagé 5 graines × 3 ans (`results/diag_1v1_shared_month_busy_3y_5seeds.json`), critère
  strict « ≥300 k£ en caisse et aucune construction » : seulement 2 mois qualifiés (tous deux
  seed 7), mais **8,48 M / 12,00 M opcodes = 70,6 %** sont `rail_search`; `catalog` = 15,0 % et
  `town_growth` = 14,0 %. Conclusion : la cible mesurée est la continuation de recherche rail,
  **pas** la génération monolithique générale. Ne pas écrire d'orchestrateur global avant d'avoir
  rendu cette continuation préemptible/mesurable séparément ; l'échantillon de mois reste petit.
  **Town growth — banc de slot corrigé, résultat nul (2026-09-10).** Le premier fichier
  `bench_town_growth_skip_noop_10y_20seeds.json` est **invalide** : le skip était inconditionnel,
  mais `town_growth_skip_noop=0` n'était ni déclaré dans `info.nut`, ni lu dans `Start()` ; les
  deux bras ne pouvaient donc pas isoler la variante. Banc refait avec réglage déclaré et lu,
  20 graines × 10 ans, 40/40 saines : historique `0` moins skip `1` = valeur **−233 k£**
  (skip +1,47 %, 12/20), score +7,3 (historique 12/20), profit annuel +30,5 k£ (skip 11/20),
  note −1,38 (skip 11/20). Chaque moyenne est très inférieure à son erreur standard et aucun
  signe ne dépasse 12/20 : **ni rejet ni adoption**. Défaut 0 conservé ;
  `results/bench_town_growth_skip_noop_correct_10y_20seeds.json`. Le skip ne retire pas le coût
  des traces `TRACEX`/`DEPOTX` déjà consommé dans `_tryTownGrowth` : ce coût reste un sujet séparé.

  📝 **C41.46–C41.49 — contrat écrit avant code (2026-09-09) :
  [`docs/04_arbitrage_rail_search.md`](04_arbitrage_rail_search.md).** Suite directe de la mesure
  ci-dessus, sur la chronologie `results/diag_1v1_shared_timeline_2y_seed42.json`. Quatre tranches,
  toutes à défaut `0`. 🔑 **Trouvaille qui réordonne le travail** : l'unique ligne rail de la partie
  a mis **9 mois** à naître — 4 mois d'A\*, puis **5 mois** en `phase == "build"` bloquée sur
  `"cash"`. Pendant ces 5 mois `_railSearch` reste non nul, donc `_expandRailLines` sort par sa
  garde (`main.nut:4417`) et **aucune autre recherche rail ne peut démarrer** : le canal rail est
  gelé. C'est la même forme que le blocage par plan en échec déjà corrigé (garde `planFailed`,
  G3§1), motif trésorerie non couvert (**C41.47**, codé et ADOPTÉ au banc 20×10 — voir plus bas). **Ce
  correctif ne demande aucun dénominateur commun et précède l'arbitrage.**
  ⚠️ `rail_search_resumable` est **déjà à 1, adopté** (`info.nut:1167`) et les rejets −23,1 % /
  −13,3 % ont été soignés par C20 (`rail_micro_deadline=1`) : il n'y a rien à rouvrir.

  ✅ **C41.46 — fait et mesuré (2026-09-09), et ça renverse le §1.1 de départ.**
  `c41_rail_slice_ledger=0` (défaut) encadre isolément le seul appel `_continueRailSearch()` et
  sépare, par différence avec la mesure totale de la passe, les opcodes **nets** de la tranche A\*
  de ceux de la tâche de file exécutée dans la même passe — le ledger C41.11 les agrégeait sous
  `rail_search`. Diagnostic 5 graines × 6 ans, `results/diag_c41_46_rail_slice_ledger_6y_5seeds.json`,
  0 échec : **part nette 45,0 % en 1971 → 13,1 % en 1975, cumul 23,3 %** (`done_rate` 1,5 % —
  quasi aucune tranche n'achève sa recherche dans l'année où elle est comptée). Les 79,7 %/70,6 %
  mesurés précédemment surestimaient donc massivement le coût réel de l'A\* rail : le gros du
  « coût rail_search » est en fait la tâche de file qui tourne à côté (`catalog`/`projects` les
  plus probables, non prouvé — ce ledger est un accumulateur unique, pas ventilé par tâche
  coïncidente). **Conséquence : le gisement d'opcodes visé par C41.49 est ~3× plus faible
  qu'estimé et continue de baisser ; la question à instruire avant lui n'est plus « faut-il couper
  l'A\* » mais « quelle tâche de file gonfle le coût, et pourquoi » — un sujet C39, pas C41.**
  🐛 Piège trouvé au premier smoke test : le premier essai journalisait via `OpexC41SchedulerLog`,
  gatée sur `C41_SLACK_LEDGER/OPPORTUNITY/ADMISSION` — `c41_rail_slice_ledger=1` seul n'aurait rien
  émis. Corrigé par un gate dédié (`OpexC41RailSliceLog`), comme les sondes rail-lost.

  ✅ **C41.47 — ADOPTÉ au banc officiel 20×10 (2026-09-09) : le diagnostic 5×6 était NUL mais
  sous-puissant, pas un vrai résultat.** `c41_rail_cash_release=1` (défaut, était `0`) :
  `_consumeRailSearch()` libère `_railSearch` dès le premier blocage trésorerie (N=0, symétrique
  de `planFailed` G3§1), `candidate.railPlan` conservé. Deux points laissés ouverts par le
  contrat tranchés à l'implémentation : N=0, et **aucune revalidation à ajouter** —
  `OpexBuildLine` réutilise déjà `candidate.railPlan` sans replanification (`builder_rail.nut:1918`),
  donc le risque « carte périmée » est préexistant à ce correctif, pas introduit par lui. Effet
  vérifié dans le code (pas seulement mesuré) : tant que `_railSearch` est non nul,
  `_tryBuildRailProject` rejette TOUT autre candidat rail (`reason=search_in_progress`,
  `main.nut:2574`) et `_expandRailLines` sort (`main.nut:4445`) — le gel touche tout le canal, pas
  seulement la ligne élue.
  **Diagnostic 5×6** (`results/diag_c41_47_rail_cash_release_6y_5seeds.json`) était NUL : total de
  lignes construites identique (14/14), délai mixte, 2 graines/5 sans jamais diverger — échantillon
  utile de 3, sous le plancher de détection ([[banc_monograine_insuffisant]]).
  **Banc officiel 20×10** (`results/bench_c41_47_rail_cash_release_10y_20seeds.json`, 0 échec) :
  test des signes **net et cohérent sur les 5 métriques** — `profit`/`profit_year` **19/20
  (p<0,0001)**, `company_value`/`performance_history` 16/20 (p=0,012, même seuil que l'adoption du
  mode route), `median_station_rating` 15/20 (p=0,041). Les t sur la différence moyenne restent
  faibles (|t|<1,5, direction cohérente mais amplitude bruitée par graine) — lire le test des
  signes, pas la moyenne, exactement le cas que documente [[banc_monograine_insuffisant]]. Le
  diagnostic 5×6 avait simplement un échantillon utile trop petit (3 graines) pour voir un effet
  net à 20. **Défaut passé à `1`** (`info.nut`, `main.nut`).

  ✅ **C41.48 — sonde livrée et mesurée (2026-09-09), à l'opposé de C41.14 : il y a bien matière
  à arbitrer.** `c41_rail_domination_probe=0` (défaut) journalise à chaque frontière de tranche
  segmentée (`slice.done==false`) : itérations dépensées/restantes, segments franchis, préfixe,
  distance restante, profit/capital du candidat rail, et **le meilleur projet réellement
  finançable** (`OpexAvailableCapital()`, même formule que le chemin de construction réel) prêt à
  bâtir au même instant. Diagnostic 5×6, `results/diag_c41_48_rail_domination_probe_6y_5seeds.json`,
  0 échec : **1 511 frontières sur 30 graines-années, 1 205 (79,8 %) avec une alternative
  finançable, dont 973 (80,7 % de ces 1 205) une AUTRE ligne — pas juste le candidat rail lui-même
  qui se voit "finançable" avant d'être construit.** `rail_profit` moyen 26–45 k£/an,
  `best_cost` moyen 50–56 k£, `rail_capital` 48–53 k£ : ordres de grandeur comparables, pas des
  miettes. **Contrairement à C41.14 (0 admission sur 56 fenêtres), le matériau pour un test de
  domination existe en abondance.**
  ⚠️ **Mais croisé avec C41.46, ce n'est pas un feu vert pour C41.49 tel qu'écrit dans le contrat**
  : le gisement d'opcodes que cette règle visait à économiser est modeste et décroissant (23,3 %
  cumulé). La fréquence élevée ici dit « il y a souvent un choix réel », pas « économiser des
  opcodes ici rapporte beaucoup ». Si C41.49 se justifie, c'est plutôt pour rediriger du **capital**
  vers un projet prêt plus tôt (effet volume, la métrique n°1), ce qui change le dénominateur de la
  règle proposée (délai de construction, pas itérations/opcodes) — **reformulation non faite,
  à trancher avant tout code.**
  **Reste** : C41.49 non codé, sa justification d'origine affaiblie, à reformuler avant d'écrire
  quoi que ce soit.

- 🔴 **C42 — Transformer les offres de subvention non attribuées en candidats.** `C17`/`A7.3`
  (`event_subsidy_probe`) est fait : écoute par événement, aucun sondage en boucle. Mais c'est une
  **sonde en lecture seule, défaut 0** — elle mesure, elle ne génère ni ne priorise aucun candidat.
  Spécification déjà écrite dans `docs/cible.md` §6 (canal opportuniste : « subventions non
  attribuées, si temps restant > chantier estimé ») et §5 (« grandeur limitante = temps avant
  fermeture »). Repli documenté : 180 jours (AdmiralAI), mais à **dériver du chantier estimé**.
  ⚠️ AAAHogEx a **0 occurrence** d'`AISubsidy` : terrain non occupé par l'adversaire. À spécifier
  (comment une offre devient un candidat scoré sans voler son classement au vivier) avant tout code.

- 🔶 **C43 / E3 — Audit des constantes en dur.** 46 `const` contre 35 réglages exposés, sans revue
  systématique. Trois issues : **exposer** (décisionnelle), **vérifier** (prétend traduire une règle
  du jeu), **étalonner** (posée à vue). ⚠️ Ne pas toutes exposer — 46 configurations mortes de plus.
  **Méthode validée** : instrumenter **avant** d'étalonner (compter combien de fois chaque
  plafond/plancher mord) — c'est ainsi que `PROJECT_TOP_K` a été confondu.
  **Fait** (chiffres en archive) : `PROJECT_TOP_K` (mord ~71 % des appels, 2 variantes benchées,
  aucune retenue), `MIN_SEPARATION` (no-op mesuré), `PROJECT_POOL_K` (code inatteignable au défaut),
  `TARGET_HEADWAY_DAYS` (pure télémétrie), `ROAD_MIN_PROFIT_ANNUAL`/`ROAD_MIN_DISTANCE`.
  **Reste** : clore famille 2 (`DEAD_STREAK_THRESHOLD`, `SCRAP_TIMEOUT_YEARS` — pas de compteur
  prêt, instrumentation ciblée à écrire) ; famille 1 (14 plafonds) pas commencée.
  🔴 **Hors périmètre à reprendre** : `CASH_RESERVE_MAX` domine le comportement de réserve, jamais
  étalonnée. 🔶 `loop_budget` (drainage de tick) non tranché. 🔶 `pax_near` non audité.

- 🔴 **C44 — La ressource rationnée n'est ni le capital ni les opcodes : c'est le TOUR DE CYCLE.**
  Vérifié dans le code : l'élection se fait sur `fundScore = profitAnnual × 1000 / financeCapital`
  (densité de capital pure) ; les opcodes sont calculés partout mais **absents du score qui élit**
  (`opcodeScore` ne remplit qu'un second vivier) ; le **temps calendaire de chantier n'a aucun
  champ** ; le tour de cycle — ce qu'un projet élu consomme à `maxBatch=1` — n'est facturé nulle
  part. Conséquence mesurée (C37) : un bus de 5 tuiles à ROI 6 490 prend le rang 0 sur la densité et
  occupe tout le passage, puis le mois suivant ; le coût réel est le profit aérien forclos.
  ⛔ **Cinq formulations déjà écartées — ne pas reproposer** : C35 (prix d'ombre `λ_ops × a_ops` en
  £ → 0 rail sur 4 graines /4), les deux « corrections » de C35.4 (7/7 défaites chacune), A1
  (dénominateur variable, décliné pour doctrine), C37 (verrou calendaire, artefact réparé), et
  l'**empreinte `K/C + Ops/Φ`** (`docs/02_empreinte.md` : à α=1 c'est le classement actuel, la
  seule information neuve est le terme opcodes, donc le `a_ops` incommensurable de C35).
  **Contraintes d'une solution** : garder le classement par densité (c'est lui qui élit rail et
  flotte) ; ne pas additionner de terme en opcodes bruts.
  🔗 `maxBatch = 1` n'est même pas une constante — c'est un `local` — et c'est lui qui rend le tour
  de cycle rare. Toute reprise doit dire si elle price cette rareté ou la supprime.

- 🔴 **C45 — Implémenter `Save()`/`Load()`.** `OpexAI::Save`/`Load` n'existent nulle part (vérifié
  par grep) : chaque clichage émet `[script:3] [W] Save function is not implemented`. Sans eux, une
  partie **rechargée** perd tout l'état interne (`_taskQueue`, `_staleness`, `_abandonedPairs`,
  `_nextLineId`, ledgers C41, `_lines`) et l'IA repart de zéro dans un monde qui a déjà ses gares —
  double-comptage et désynchronisation silencieuse.
  **À cadrer avant de coder** : quels champs sont *reconstructibles sans perte* depuis les chunks
  (`_lines` dérivable de `VEHS`/`STNN` par `owner`, `_catalog` rafraîchi au premier cycle) contre
  l'**état de décision pur** qui serait perdu (dueCycle, révisions `_staleness`, `_abandonedPairs`,
  `_nextLineId`, compteurs C41) — perdre les seconds dégrade sans crasher, donc sans se voir.

- 🔴 **C46 — OpexAI ne construit rien sur une carte 1024².** Diagnostic du 2026-09-09 (graine 42,
  1 an, `-d script=4`, AAAHogEx tournant normalement sur la même carte).
  **Cause** : `catalog.refresh()` révèle **731 villes / 871 industries** (`number_towns` est une
  densité : ~15× plus qu'à 256²), puis `OpexPaxCandidates` ne revient jamais — double balayage de
  paires O(n²) non borné, ~266 815 paires contre ~1 225 à 256².
  **Partiellement corrigé** : `1c12fd5` a introduit l'indexation spatiale (grille de maille
  `bounds.railMax`) et `catalog.bounds` à la place des bandes en dur → terme quadratique éliminé
  pour le pax.
  **Reste** : (a) **vérifier `OpexFreightCandidates` et `OpexBuildRoadCandidates`** — sur 871
  industries une forme O(n²) donnerait ~379 000 paires, pire que le pax ; (b) **re-tester une 1024²
  de bout en bout** : le travail utile reste linéaire mais lourd (~20 000 paires à portée × économie
  complète), un pré-score bon marché avant `OpexLineEconomics` (comme le fait l'eau) pourrait être
  nécessaire — heuristique, donc banc obligatoire.

---

## 🔴 Mode eau — chantier NON FINI (audit de clôture 2026-09-09)

Le module est reconstruit sur `MinchinWeb.Lakes` + `Marine` (`ai/OpexAI/lib_water.nut`,
`Queue.FibonacciHeap-3` vendorisé, réglage `water_lakes_connectivity`), et les trois apports
annoncés sont présents. **Mais le chantier ne peut pas être clos**, pour deux raisons distinctes.

**1. Le banc officiel va contre le défaut.**
`results/bench_water_lakes_connectivity_10y_20seeds.json` (20 graines × 10 ans, 40/40 saines) : la
moyenne favorise le bras historique **OFF** — valeur 13,21 M£ contre 11,24 M£ (+17,5 %), score
848,1 vs 759,5, profit annuel 2,21 M£ vs 1,94 M£ (+13,7 %). Mais OFF ne gagne que 7/20, 6/20, 5/20,
6/20 graines : quelques graines divergentes tirent la moyenne, et le test des signes ne confirme que
le profit trimestriel (p = 0,041). **Le gain fonctionnel de Lakes n'est pas une justification
empirique pour garder le défaut à 1** — décision à réexaminer.

**2. Quatre défauts fonctionnels + un risque, à corriger ou trancher :**
- **La génération de sites est le goulot en amont, et Lakes n'y change rien.**
  `results/diag_c41_3b_water_site_profile_6y_5seeds.json` : 591 918 opcodes, **0 plan**, dont
  557 253 (94,1 %) dans la recherche de sites — 557 109 dans le seul scan/filtrage contre 144 dans
  les tests de quai. **Aucune paire n'atteint le BFS ni l'économie.** `OpexWaterFindSite` ne visite
  que `r <= coverage` autour de la tuile centrale : si aucune côte admissible n'est trouvée là, le
  moteur de connectivité est hors-sujet. Redessiner ou mesurer cette recherche **d'abord**.
- **Le repli de distance après succès de Lakes n'est pas conservateur** (contrairement à ce que son
  commentaire affirme). Manhattan est un **plancher** de la longueur navigable : l'utiliser comme
  distance navigable sous-estime `oneWayDays`, donc **surestime** capacité, revenu et ROI. Une paire
  sans distance navigable mesurée ne doit pas être classée avec ce minorant.
- **La construction réintroduit le faux négatif du BFS borné.** Après pose des quais,
  `OpexWaterFindConnection(realA, realB)` redevient juge de connectivité et rollbacke en `NOWATER` :
  une paire admise par Lakes parce que son détour dépasse la bounding-box peut donc échouer à la
  construction pour la raison même que Lakes devait supprimer. Revalider sur les fronts réels sans
  remettre le BFS borné en position de juge.
- **La correction de division mensuelle est incomplète.** `30.0 / oneWayDays.tofloat()` supprime la
  division entière, mais le clamp `if (tripsPerMonth < 1.0) tripsPerMonth = 1.0` crédite encore tout
  trajet > 30 jours d'un voyage mensuel complet. Garder la valeur fractionnaire (et vérifier la
  convention aller simple / aller-retour).
- **Grandes cartes non qualifiées** : le constructeur de Lakes ajoute une entrée `AIList` par tuile
  (65 536 en 256², 1 048 576 en 1024², 4 194 304 en 2048²). L'instance est persistante et paresseuse,
  mais aucun diagnostic mémoire/opcodes sur 1024² n'existe. Risque à mesurer, pas bug démontré.

**Critère de clôture** : corriger ou trancher les quatre incohérences, obtenir au diagnostic 5×6 des
paires qui atteignent réellement connectivité **et** économie (avec au moins une construction sur une
graine contrôlée), qualifier le coût sur 1024², puis refaire le banc officiel avant de confirmer le
défaut.

ℹ️ `WATER_LAKES_ITERATIONS` calibré par mesure (500 ; pire cas observé 153, budget jamais épuisé) —
ce point-là est clos.

---

## Réutilisation des bibliothèques vendorisées (`ai/library/`)

Licences vérifiées fichier par fichier, graphe de dépendances vérifié ; conventions et pièges dans
`AGENTS.md`, section « Bibliothèques tierces vendorisées ».

**Reste, par ordre de valeur** :
1. **Air — `airportDelayDays`** : `OpexAirTripModel` utilise une constante fixe à 3,0 jours quel que
   soit le type d'aéroport, contre la table par type de `SuperLib.Engine.GetAircraftTravelTime`
   (5 à 10 j, additionnés aux deux bouts). L'air pèse ~64 % du capital.
   ⚠️ SuperLib documente lui-même ces valeurs comme **devinées** : mesurer le délai réel par type
   **avant** tout remplacement, sinon on échange une constante devinée contre une autre.
2. **Catchment de gare** : `SuperLib.Station::GetAcceptanceCoverageTiles`/`GetSupplyCoverageTiles`
   donnent les tuiles réelles contre les approximations `road_pax_catchment_pct` /
   `road_stop_catchment_houses`. Pas chiffré.
3. **Aéroports** : `SuperLib.Airport` (placement, bruit, acceptation avant construction) — poste le
   plus cher et le plus défaillant (7× `ERR_FLAT_LAND_REQUIRED` + 1× `ERR_AREA_NOT_CLEAR` sur 20
   tentatives), mais le plus gros morceau (1117 lignes).
4. **`Pathfinder.Road.nut`** — seul fichier LGPLv2.1 du lot, en dernier.

✅ **Air — rectangle de nivellement corrigé (2026-09-09, adoption utilisateur).** Le diagnostic
`results/diag_air_afail_6y_5seeds.json` (5 graines × 6 ans) comptait 2 054
`ERR_FLAT_LAND_REQUIRED` sur 2 254 tentatives air (92,2 % d'échecs). La trace 1v1 seed 42 a montré
qu'AAAHogEx construisait ensuite dans 13 des 22 villes rejetées par Opex. La cause était la borne
`+(width-1,height-1)` de `OpexAirFootprintEnd` : `AITile.LevelTiles` attend `+(width,height)`,
comme `SuperLib.Tile.CostToFlattern` et AAAHogEx. Après correction,
`results/diag_air_afail_rect_end_6y_5seeds.json` donne 38 erreurs de terrain non plat, 204 succès
sur 263 tentatives et 22,4 % d'échecs. **Adopté sans banc officiel 20×10 sur validation explicite
de l'utilisateur**, le défaut étant géométrique et le diagnostic univoque.

✅ **Air — invalidation d'une ancre de cache refusée (2026-09-09, décision utilisateur).** Après
un échec réel, `OpexAirInvalidateCachedSite` efface seulement la clé `(ville, type)` qui pointe
encore vers cette ancre ; une recherche ultérieure ne peut donc pas la traiter comme valide.
Diagnostic `results/diag_air_afail_cache_invalidate_6y_5seeds.json` : 204 succès dans les deux
bras, 263 → 262 tentatives et 59 → 58 échecs. **Pas un gain de volume mesuré**, mais adopté pour
conserver l'invariant « un refus réel invalide une prédiction » sur validation explicite de
l'utilisateur.

❌ **Pas des candidats, ne pas rouvrir** : temps de trajet **rail** (`OpexRailEffectiveSpeed` fait
déjà croisière dichotomique + accélération + intégration, cache adopté au banc — SuperLib serait une
régression) ; **note municipale** (`OpexBoostTownRating` compare déjà le bon enum depuis le
2026-09-02, [[aitown_getrating_est_un_enum]]) ; **route** (`OpexRoadLineEconomics` est déjà dératée,
SuperLib est plus cru) ; `Marine.BuildDepot`, `ShipPathfinder`, `WBC` (dépendent de `graph.aystar`
v6, absent du disque).

🆕 **Idée non chiffrée : filtre proactif de note municipale.** `AITown.GetRating` n'est appelé qu'une
fois dans tout le code (`OpexBoostTownRating`), et uniquement **en réaction** à un
`ERR_LOCAL_AUTHORITY_REFUSES` déjà survenu. Rien n'écarte en amont une ville sous le seuil de refus
avant de dépenser des opcodes en recherche de site, alors que la lecture est quasi gratuite.
`SuperLib.Town::TownRatingAllowStationBuilding` donne le test. **Avant de coder** : (1) chiffrer
combien de candidats touchent une ville sous ce seuil — si c'est rare, c'est un no-op coûteux à
maintenir, comme `MIN_SEPARATION` ; (2) s'assurer qu'un rejet précoce n'écarte pas une ville qui
méritait le recours réactif existant.

---

## Robustesse et publication (non prioritaire pour le banc)

- **Réglages de partie non testés** : aucune recherche de `forbid_90_degree_turns` ni de garde pour
  un type de véhicule désactivé (`max_trains=0`…). Sans conséquence pour le banc (config figée),
  vrai trou si l'IA est publiée pour des parties humaines.
- **Aucun interrupteur `enable_rail`/`enable_road`/`enable_air`/`enable_water`** : le portefeuille
  suppose toujours les quatre modes disponibles.
- **Empreinte RAM de la VM Squirrel jamais mesurée.**
- 🔶 **Workflow GitHub avec OpenTTDLab** : smoke test à chaque PR, banc à la demande (demandé le
  2026-08-29, non fait).

---

## Autres points en suspens

- ⏸️ **`PORTFOLIO_REFRESH_MIN_GAIN` — en attente de C41** (décidé le 2026-09-08). C41 construit
  précisément l'ordonnancement que ce seuil gouverne ; le remesurer avant porterait sur un chemin
  bientôt remplacé.
- 🔴 **Suites du raccordement de gare** (`station_join=0`). Le vivier rouvert ne paie pas, même après
  traction : véhicules +23,6 % (t = 3,50) mais valeur sous le plancher. Le second mur (vivier de
  candidats à partir de 1982) rend `station_join` structurellement inerte — c'est ce mur qu'il faut
  traiter, pas le réglage.
- 🔴 **Agrandir une gare existante** — deux motifs, dont le second est le plus lourd (archive).
- 🔴 **Gérer les jonctions de rails** — condition technique de l'agrandissement : sans jonction, deux
  lignes ne peuvent pas partager une gare.
- 🔶 **Modèle de coût A\*** (`candidates.nut`) : préalable distance fait, **recalibrage conjoint non
  fait**.
- ✅ **`origin_sitable=1` confirmé au banc officiel apparié 20×10 (2026-09-09).**
  `results/bench_origin_sitable_10y_20seeds.json`, 40/40 parties saines : OFF (`0`) contre ON
  (`1`). ON est légèrement devant en valeur (11,24 M£ contre 11,17 M£, +0,7 %), score (+0,6 %),
  profit trimestriel (+3,2 %) et annuel (+2,2 %), mais aucun écart n'est convaincant : 9/20
  victoires OFF pour valeur/profits, 10/20 pour le score (test des signes bilatéral p ≥ 0,824).
  Surtout, le coût de volume du diagnostic court ne se reproduit pas : ON a 168,0 véhicules
  contre 165,4 et 74,3 gares contre 76,1. Le filtre reste donc à `1` par défaut : résultat nul à
  légèrement favorable, sans régression de volume démontrée.
- ⚠️ **`complex_cargo = 1` reste le défaut sur un résultat NUL** au retest officiel 20×10
  (2026-09-08) : le gain de 5 ans ne réplique pas à 10. Conservé faute de raison de couper un vrai
  mécanisme de jeu sur un null result, pas parce qu'il est validé.

---

## 📓 Historique

- **[`docs/taches_archive_2026-09-09.md`](taches_archive_2026-09-09.md)** — instantané verbatim de
  ce fichier avant nettoyage : tout l'historique des mesures, bancs et verdicts. **À grepper avant
  toute recommandation stratégique.**
- `docs/journal_*.md` — un fichier par jour, le détail le plus fin. Les références `§0 <ordinal>`
  se retrouvent par `grep -rn "0 <ordinal>" docs/journal_*.md`.
