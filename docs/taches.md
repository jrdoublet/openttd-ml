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
(`results/bench_1v1_3y_1aeefe1_20seeds.json` ⛔ **ARCHIVÉ, chiffre à re-mesurer, voir AGENTS.md §2 bis**, 20 graines × 3 ans, lecture appariée, 0 échec) :

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

  📝 **C39.5 — cadence de `projects` pendant `_railSearch` actif : contrat écrit avant code
  (2026-09-10), [`docs/05_cadence_projects_rail_search.md`](05_cadence_projects_rail_search.md).**
  Relais de C41.49 fermée le même jour. ⚠️ **Le cadrage ci-dessous est conservé tel qu'il a été écrit AVANT la mesure — l'étape 1 en a renversé une partie, voir plus bas.**
  🔑 **Ce que le cadrage ajoute aux données de C41.49, par pure relecture** : les 89,3 % de
  « (c) jamais tentée » ne sont pas un taux d'échec mais un **dénominateur de round-robin**.
  (a+b) = 148/1 379 = **10,7 %** est le taux de dispatch observé de `projects`, et la file compte
  **10 tâches actives** en régime établi — pas 11 : `air` s'auto-désactive à sa première passe sous
  `air_portfolio=1` (`main.nut:6814`). 1/10 = 10,0 % : le taux mesuré EST le round-robin. Et quand
  `projects` obtient son tour, il bâtit **96,6 %** du temps (143/148). **Le fallthrough n'est pas
  cassé, il est cadencé** — reste à savoir si un tour de file dure des jours ou des semaines, ce
  qu'aucun ledger ne permet de dériver (les deux estimations disponibles diffèrent d'un facteur 2,
  §1.1 de la fiche : les commandes d'API consomment des jours de jeu sans consommer d'opcodes).
  ⚠️ **L'hypothèse nulle est armée par un réfuté** : `portfolio_max_batch=4` (banc 20×3 apparié,
  2026-09-02) a donné **−3,8 % de valeur, −7,9 % de gares**, avec la cause identifiée aux panneaux
  — un passage réussi régénère lui-même le portefeuille, donc bâtir plus par passe **fusionne deux
  cycles** au lieu d'en ajouter un, et *le vrai goulot est la concurrence pour la caisse*. Cette
  fiche rejoue le même geste sur l'axe *fréquence* : elle doit prouver un délai matériel **en jours
  de jeu** avant tout levier, sinon c'est le même réfuté sous un autre nom.
  **Étape 1 (telle que cadrée)** : sonde `c39_projects_cadence_probe` (défaut 0, gate DÉDIÉ
  `OpexC39ProjectsCadenceLog` — piège C41.46), trois points d'instrumentation, D1 délai de dispatch
  / D2 délai de captation / D3 abstentions **lues au site d'appel** (`main.nut:6847`, l'angle mort
  de la sonde C41.49). Critère de fermeture écrit d'avance : médiane(D2) ≤ 5 j **et** p90(D2) < 30 j
  sur ≥ 4 graines/5 → fiche close (30 j = la cadence de régénération mensuelle du vivier).
  🔑 **Trouvaille de lecture de code, utile hors fiche** : `_consumeRailSearch` ne tourne QUE dans
  la tâche `projects` (`main.nut:3320-3323`) — la phase `"build"` d'une recherche rail est cadencée
  par la même horloge que le fallthrough (atténué par C41.47 défaut 1, N=0).

  ✅ **C39.5 étape 1 MESURÉE le 2026-09-10 — et elle renverse le cadrage.** Sonde livrée
  (`c39_projects_cadence_probe=0` par défaut, `info.nut:675`), diagnostic 5 graines × 6 ans,
  `results/diag_c39_5_projects_cadence_probe_6y_5seeds.json`, **0 échec**, couverture 98,7 % du
  temps de jeu. 🐛 Deux défauts trouvés à la relecture/au lancement, tous deux invisibles à
  l'analyse statique : `railCandidate.mode` sur `_railSearch.candidate` (qui est le **payload**,
  sans slot `mode` — plantage garanti dès la sonde armée, et clé de vivier incompatible), et
  `c39_projects_cadence_probe` absent de la liste blanche de `sweeps/bench_v2.py`.
  **Résultats** — D1, intervalle entre deux tours de `projects` : **4 j** hors recherche rail,
  **36 j** pendant (médianes 34–44 j sur CHACUNE des 5 graines). D2, délai de captation : **4 j**
  hors, **192,5 j** pendant. D3 : `_portfolioInvalidated` **inerte (0,14 %)**, mais **vivier vide
  dans 55,3 % des tours**.
  🔑 **`cycles_since_last` vaut 1 dans 99,4 % des cas et n'excède JAMAIS 1** : `projects` n'est pas
  affamé, il obtient son tour à chaque cycle. **C'est le cycle qui dure 5× plus longtemps** — et
  **65,5 % du temps de jeu (7 073 j sur 10 803) se passe avec `_railSearch != null`**, donc les
  10 tâches de la file paient ce ralentissement pendant les deux tiers de la partie.
  ⚠️ **Conséquence : le critère de fermeture est raté (D2 = 64 j contre ≤ 5 j exigés) MAIS les
  leviers L1/L2 sont écartés aussi** — donner des tours supplémentaires à `projects` prendrait le
  tour de 9 tâches également pénalisées. Et 55,3 % de vivier vide est un sujet d'**offre**, pas
  d'ordonnancement. ⛔ Ne pas citer « D2 = 192 j » comme un coût de cadence : la sonde agrège
  cadence + file d'attente par rang (`PORTFOLIO_MAX_BATCH = 1`) + concurrence pour la caisse.
  ❌ **CORRIGÉ le 2026-09-10 par C39.6 — le « facteur 15 » ci-dessous est FAUX, faute d'unité de ma
  part** (74 ticks/jour supposés contre **18,48 mesurés**). Sonde `c39_pass_clock_ledger` (défaut 0),
  `results/diag_c39_6_pass_clock_6y_5seeds.json`, 5×6, 0 échec. 🔑 **Les jours SONT les opcodes** :
  part de la tranche A\* = 22,4 % des jours / 22,3 % des ticks / **22,9 % des opcodes**, et
  186 k opcodes par jour de jeu (= 10 k/tick × 18,5 ticks/jour). Aucun coût caché en jours d'API ;
  [[philosophie_opcodes_ressource]] tient.
  ⚠️ **Et le ×4,4 « passe avec tranche vs sans » est un ARTEFACT DE MATURITÉ** : par année, le
  rapport tombe de **4,84 (1971) à 0,91 (1975)** — en fin de partie une passe avec recherche rail
  ne coûte plus rien de plus. Même forme que l'effondrement 45 %→13 % de C41.46.
  🔑 **Le vrai effet : le coût d'une passe est multiplié par ~15 en cinq ans** (0,39 → 5,92 j/passe
  hors tranche). C'est ça qui étire l'horloge de décision, c'est cohérent avec les 2,09 M opcodes
  par reconstruction de catalogue (C41.22), et **c'est indépendant du canal rail**. Sujet à
  instruire ; couverture de la sonde 81,9 % (ledger annuel, dernière année partielle perdue).
  ❌ **Tension RÉSOLUE le 2026-09-10, et pas en ma faveur** (`results/diag_c39_6b_pass_clock_6y_5seeds.json`,
  ventilation année × tâche) : **la part des passes sous recherche rail passe de 13,9 % (1971) à
  89,5 % (1975)**. Comparer `rail_search=1` à `rail_search=0` sur toute la partie revient donc à
  **comparer la fin de partie au début**. Les « 35,5 j contre 2 j » de C39.5 mesurent la maturité,
  pas la recherche rail. ⛔ **Deuxième conclusion à moi corrigée dans la journée** (après le facteur
  15) : ne pas conditionner sur un état dont la fréquence dérive avec le temps sans contrôler l'âge
  de partie.

  🔑 **LE RÉSULTAT DE LA JOURNÉE — le débit de décision s'effondre d'un facteur 9,2.**
  Une passe = une décision. Par année : **168,0 passes/100 jours en 1971 → 18,3 en 1975**
  (2 854 → 342 passes, gros effectifs, pas un artefact). Un tour complet des 10 tâches passe de
  ~6 jours à **~55 jours**. C'est le mécanisme du **plafond de volume**, la métrique n°1.
  **Où part le coût** (opcodes/passe hors tranche A\*) : `projects` 147 k → **2 696 k (×18,4)**,
  `catalog` 164 k → **2 782 k (×17,0)**, `town_growth` 253 k → 1 964 k (×7,8). `catalog` recoupe
  les 2,09 M par reconstruction de C41.22 — mais **le suspect désigné n'était pas le bon :
  `projects` coûte autant et croît plus vite**, alors que la fiche C39 vise le rafraîchissement du
  catalogue.
  ⚠️ Effectifs de 1975 minuscules (3 à 5 passes par tâche) : les ratios par tâche sont indicatifs,
  le facteur 9 du débit ne l'est pas. ⚠️ `report` ×251 est un **artefact de la sonde** (elle
  journalise le ledger qu'elle accumule). ⚠️ Décalage d'étiquette : `year=1971` décrit l'année de
  jeu 1970 (publication au premier passage de l'année suivante), la 6ᵉ année n'est jamais publiée.

  ~~Version d'origine, réfutée~~ (`docs/05_...` §4.3) : une passe coûte ~3,6 jours de jeu
  pendant une recherche rail, alors que la tranche A\* ne pèse que ~146 k opcodes ≈ 0,2 jour
  (C41.46). **Facteur 15 inexpliqué entre le coût en opcodes et le temps de jeu perdu.** Ça
  reformule C41.46 : en opcodes la recherche rail pèse 23,3 %, en **jours** elle coûte ~5× le temps
  de cycle pendant 65 % de la partie — et c'est le jour, pas le tick, qui décide du volume.
  ⛔ **Aucun banc lancé, aucun levier codé, rien de commité.**

  🔒 **C39.5 FERMÉE le 2026-09-10 sur le levier de cadence — étape 1 bis décisive.** Sonde enrichie
  (`topSince`/`topTurns` : date et nombre de tours où un projet est **le meilleur finançable**,
  définition identique à C41.48), diagnostic relancé,
  `results/diag_c39_5b_projects_cadence_probe_6y_5seeds.json`, 0 échec, 754 dispatches.
  🔑 **`turns_since_top` = 1 en médiane, 1 au p90, 2 au maximum — dans les DEUX régimes** : dès
  qu'un projet devient le meilleur candidat finançable, il est bâti au **premier tour de `projects`
  qui suit**, recherche rail en vol ou non. Le délai brut (173 j sous recherche rail) est du **temps
  d'attente de rang**, pas de la cadence : un chantier par passe (`PORTFOLIO_MAX_BATCH = 1`).
  **Accélérer la cadence ne peut produire aucun chantier de plus** — même mécanisme que l'échec de
  `portfolio_max_batch=4`, retrouvé par l'autre bout. ⛔ Ne pas rouvrir un levier d'ordonnancement
  sur `projects`.
  🆕 **Trois questions survivent, aucune de cadence** : (1) le **facteur 15** entre le coût en
  opcodes d'une tranche A\* (~0,2 j) et les ~3,6 j de jeu qu'elle coûte à chaque passe, pendant
  65 % de la partie ; (2) **le meilleur finançable n'est PAS ce qui se construit 2 fois sur 3**
  (`never_top_share` 54,4 % au total, **67,8 % sous recherche rail**) — le candidat de tête du sac
  à dos est régulièrement injouable et c'est un rang inférieur qui passe, sujet de **qualité de
  vivier** ; (3) **vivier vide dans 58,6 % des tours**, et la correction de sonde tranche
  l'ambiguïté — `best_len_missing` = **0,0 %**, c'est une vraie vacuité, pas un objet absent
  (`_portfolioInvalidated` inerte à 0,27 %).

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
  ✅ **C41.49 reformulé le 2026-09-10** (`docs/04_arbitrage_rail_search.md` §C41.49) : la règle
  d'arrêt optimal en opcodes est abandonnée, pas juste affaiblie. Lecture du scheduler
  (`main.nut`) : sous le défaut (`portfolio_dynamic_batch=0`), le canal non-rail **n'est pas
  gelé** — quand un candidat rail est rejeté `search_in_progress`, `_tryBuildProjects` continue
  aux rangs suivants dans la même passe et peut déjà bâtir un air/route/eau finançable. Et ce que
  fait `projects` PENDANT une recherche rail n'a jamais été mesuré : le ledger C41.11 étiquette
  `rail_search` toute passe où `_railSearch != null`, quelle que soit la tâche réellement
  dispatchée — donc « `projects` 3/37 en 2 ans » (§0 de la fiche) veut dire 3 fois **hors**
  fenêtre de recherche rail, pas 3 fois au total.

  ✅ **Étape 0 codée et mesurée en 5×6 (2026-09-10) — (c) domine nettement, 5/5 graines,
  C41.49 fermé en tant que règle sur l'A\*.** Sonde `c41_projects_fallthrough_probe` (codée,
  jamais benchée), corrélée à `c41_rail_domination_probe` frontière par frontière
  (`results/diag_c41_49_projects_fallthrough_probe_6y_5seeds.json`, 0 échec). Sur 1 379
  frontières « avec alternative finançable » cumulées sur 5 graines (contre 973/1 511 en 6y5s
  côté C41.48 solo — l'écart vient du coût propre de la sonde combinée, qui déplace la
  trajectoire comme toujours) :
  - **(c) jamais tentée sur cette passe précise : 89,3 % (1 231/1 379), 88–90 % sur CHACUNE des
    5 graines** — `projects` n'est simplement pas dispatchée dans la même passe que la frontière
    (round-robin ~1/11 tâches actives) ;
  - **(a) déjà saisie et bâtie : 10,4 % (143/1 379)**, 9,4–11,6 % par graine — le fallthrough
    existe bel et bien, il capture juste rarement le bon instant ;
  - **(b) tentée et refusée pour une autre raison : 0,4 % (5/1 379)**, exactement 1 occurrence
    par graine — la trésorerie/`too_close` n'est quasiment jamais le facteur limitant ici.
  **Conclusion** : (c) domine à 88–90 % sur les 5 graines, largement au-dessus du seuil de
  passage du contrat (4/5). Une règle de domination sur l'A\* rail réglerait un non-problème :
  le canal ne "refuse" quasiment jamais l'alternative (b≈0), il ne l'essaie simplement pas
  assez souvent. **La fiche C41.49 est fermée en tant qu'arbitrage sur la recherche rail.** Le
  vrai levier est la cadence de dispatch de `projects` pendant une recherche rail active — un
  sujet de fraîcheur/ordonnancement, donc **C39**, pas C41. Aucun banc lancé (le contrat
  l'interdisait avant cette étape ; il n'y a maintenant rien à bancher, seulement une nouvelle
  fiche C39 à écrire).
  ⚠️ **Angle mort connu de la sonde** : le champ `invalidated` loggé à l'entrée de
  `_tryBuildProjects` est mort — le site d'appel (`main.nut:6791-6796`, tâche `"projects"`)
  filtre déjà `_portfolioInvalidated` avant même d'entrer dans la fonction, donc la sonde ne
  peut jamais l'y observer à `1`. Ça n'invalide pas le comptage attempted/built ni la
  classification (a)/(b)/(c) ci-dessus, mais une future fiche C39 sur la cadence de `projects`
  devra lire `_portfolioInvalidated` **au site d'appel**, pas dans `_tryBuildProjects`.
  ✅ **Relais écrit le 2026-09-10** : fiche **C39.5**,
  [`docs/05_cadence_projects_rail_search.md`](05_cadence_projects_rail_search.md) (métrique :
  délai de construction en jours de jeu, jamais un prix d'ombre en opcodes — ⛔ C35). Elle
  reclasse les 89,3 % de (c) en dénominateur de round-robin et arme une hypothèse nulle sur le
  réfuté `portfolio_max_batch` : voir la fiche C39 ci-dessus. **Plus rien à faire ici.**

- ⚠️ **C54 — CHIFFRE PRINCIPAL RETIRÉ le 2026-09-10. Les « 77 % » étaient un artefact de comptage.**
  ⛔ **La version ci-dessous (barrée) a été commitée dans `8c2cecc` puis réfutée le jour même par une
  sonde EN JEU** (`c54_vehicle_orders_probe`, `results/diag_c54_vehicle_orders_10y_5seeds.json`,
  5 graines × 10 ans, 0 échec). **Ne pas citer les taux de la version barrée.**

  🔑 **Le chunk `VEHS` ne compte pas des véhicules.** Comparaison API contre chunks, dernière année :

  | mode | API (véhicules réels) | chunks `VEHS` | écart |
  |---|---:|---:|---:|
  | rail | **20** | 70 | −50 (**wagons**) |
  | avion | **236** | 538 | **−302** (**ombres et rotors**) |
  | route | **222** | 277 | −55 |

  Wagons, ombres d'avion et rotors d'hélicoptère sont des entités du pool à **profit nul par
  construction**. J'avais compté **306** « avions à profit ≤ 0 » sur 538 : il y a **302 ombres**.
  Les deux nombres coïncident presque exactement — le taux mesurait le remplissage du pool, pas la
  rentabilité.

  ✅ **Les vrais taux, sur véhicules API et `profit_last_year` par année** (191 véhicules classés,
  au moins une année pleine) :

  | mode | jamais positif | devenu négatif | irrégulier | toujours positif | total |
  |---|---:|---:|---:|---:|---:|
  | avion | 0 | 2 | 29 | **63** | 94 |
  | rail | 1 | 1 | 1 | 5 | 8 |
  | route | **9** | 14 | 34 | 32 | 89 |

  **10 « jamais positifs » sur 191, soit 5,2 %** — dont 9 routiers. Et **100 « toujours positifs »**,
  là où la mesure par chunks n'en trouvait que 2. ⚠️ Effectifs faibles en rail (8 classés).

  ✅ **Ce qui reste vrai et vaut la peine** : quelques véhicules routiers sont durablement
  déficitaires — `vid=42` fait −136, −400, −475, −283… **neuf années consécutives**. Peu nombreux,
  mais jamais corrigés, ce qui rejoint **C52** (`ET_VEHICLE_UNPROFITABLE` n'est écouté nulle part).

  ❌ **Hypothèse « ordres mal donnés » RÉFUTÉE, nettement.** `distinct_dest = 2` pour **tous** les
  véhicules, **tous modes, toutes années, zéro exception** (`under_2_distinct_dest = 0` partout).
  Les ordres sont bien formés. Lu par `AIOrder.IsGotoStationOrder` + `GetOrderDestination`, sans
  supposition de format.

  ❌ **« 98 % de véhicules routiers orphelins » RETIRÉ — artefact de sonde.** Ma sonde cherchait
  chaque véhicule dans `line.vehicles`. **Les lignes routières ne portent pas ce champ, par
  conception documentée** (`OpexLineVehicleIds`, `main.nut`) : elles identifient leurs camions **par
  les ORDRES**, précisément pour ne pas ferrailler les véhicules des lignes voisines partageant un
  arrêt. Le 98 % mesurait « la route n'utilise pas le champ interrogé ».

  🔑 **RÈGLE DE MÉTHODE, à appliquer désormais** : pour toute grandeur **chaînée ou à variantes**
  (ordres, identité d'un véhicule dans le temps, appartenance à une ligne), **utiliser l'API du jeu,
  pas la lecture de chunk**. Six campagnes de lecture de sauvegarde ont buté **quatre fois** sur des
  structures mal supposées (`waiting` inexistant ; mode détecté par présence de clé sur un
  enregistrement à variantes ; `truck_stops` pris pour une liste ; `orders` sans correspondance dans
  `ORDR`). Les grandeurs **scalaires par gare** (notes, backlog, dimensions) se lisent en revanche
  très bien dans les chunks. ⚠️ Contrepartie assumée : une sonde en jeu consomme des opcodes et
  déplace donc la trajectoire.

  ~~Version d'origine, RÉFUTÉE :~~ 🔑 **Une flotte massivement improductive, jamais mesurée.**
  📝 Mesuré le 2026-09-10, `results/diag_station_fleet_10y_5seeds.json` (2 bras × 5 graines × 10 ans,
  0 échec, lecture des chunks `STNN`/`VEHS`/`ORDR`, aucune sonde de jeu).

  | mode | flotte v2=1 | profit ≤ 0 | part | flotte v2=0 | profit ≤ 0 | part |
  |---|---:|---:|---:|---:|---:|---:|
  | **rail** | 87 | 67 | **77,0 %** | 39 | 30 | **76,9 %** |
  | **avion** | 598 | 306 | **51,2 %** | 572 | 288 | **50,3 %** |
  | route | 305 | 76 | 24,9 % | 229 | 56 | 24,5 % |

  🔑 **Plus des 3/4 des trains et la moitié des avions ne rapportent rien ou perdent de l'argent**,
  et **les taux sont identiques dans les deux bras** : ce n'est pas un défaut de `portfolio_v2`,
  c'est un **état permanent de l'IA**. 374 véhicules sur 991 à profit ≤ 0 sur le chemin par défaut.
  🔗 **Lien direct avec C52** : `ET_VEHICLE_UNPROFITABLE` n'est **écouté nulle part**. L'IA n'a aucun
  moyen de s'apercevoir qu'un véhicule ne gagne rien, donc elle ne le remplace ni ne le supprime.
  **C52 passe du nettoyage à la piste principale.**
  ⚠️ **Réserves** : `profit_this_year` est un profit **en cours d'année** — un véhicule récent ou en
  trajet peut apparaître à 0 sans être déficitaire ; croiser avec `profit_last_year` et l'âge avant
  de conclure. Et « ≤ 0 » agrège nuls et négatifs, qui n'ont pas le même sens.

- ⚪ **C51 bis — la dissociation volume/valeur, expliquée (2026-09-10).**
  Le banc 20×10 montrait +30,4 % de gares pour un profit inchangé, soit **−23,0 % de profit par
  gare** (18/20, p=0,0004). Chaîne complète, par mesures directes :
  1. **La composition du réseau change**, elle ne fait pas que grossir. Effectifs recalculés depuis
     les distributions brutes (détection par **valeur**, `> 0`) :

     | mode | v2=1 | v2=0 | écart |
     |---|---:|---:|---:|
     | bus | 364 | 344 | +20 |
     | **camion** | **68** | **2** | **+66** |
     | **rail** | **42** | **14** | **+28** |
     | avion | 133 | 129 | +4 |

     `portfolio_v2=1` **ouvre deux canaux** que le legacy n'utilisait quasiment pas.
  2. Ces canaux sont les plus déficitaires (C54) : la flotte rail passe de 39 à 87 véhicules, dont
     **77 % à profit ≤ 0**.
  ⇒ **+66 gares camion et +28 gares rail → +48 trains dont 37 improductifs → profit total inchangé
  malgré +30 % de gares.**

  ⛔ **Cinq hypothèses testées et ÉLIMINÉES avant celle-là — ne pas les reproposer** : gares mortes
  (12 contre 4), gares non desservies (**aucune** gare non notée n'est à zéro visiteur), engorgement
  (46 contre 45, effectifs identiques), gares de destination (**réfutée** : les non notées chargent
  et ne déchargent jamais), chargement trop lent (les notes sont **meilleures** dans v2=1).
  ⛔ **« Cannibalisation » a été affirmée puis RETIRÉE** : c'était une déduction par élimination,
  sans mesure de flux.

  🔑 **114 des 133 aéroports sont joints à un arrêt de bus** (86 %), identiquement dans les deux
  bras. **Toute analyse par mode DOIT séparer les gares monomodales des multimodales** — sinon le
  revenu aérien de 114 gares est compté comme routier.

  🐛 **Trois contresens de structure de chunk commis dans la journée, tous du même type** — prescrire
  avant de vérifier : (a) champ `waiting` **inexistant** (le stock vit dans `max_waiting_cargo` et
  des paquets `CAPA`/`CAPY` non joints) ; (b) détection de mode par **présence de clé** alors que
  `STNN` est un enregistrement **à variantes** — 3 modes sur 4 comptaient le total ; (c)
  `truck_stops`/`bus_stops` pris pour des **listes** alors que ce sont des **scalaires** de
  sentinelle **0**, d'où 64 % du réseau invisible.
  ✅ **Ce qui a permis de les attraper** : exiger la publication des **distributions brutes** des
  discriminants, et une **garde anti-dégénérescence** (« un mode égale le total », « > 10 % sans
  mode », « seuil de quartile nul »). Les trois défauts ont été signalés par ces gardes, pas par un
  test qui échoue. **À reproduire dans toute sonde de chunk.**

- 🔴 **C55 — L'assouplissement du 2026-08-29 n'a jamais été appliqué à la ROUTE.**
  📝 Ouverte le 2026-09-10 par lecture de code, **sans campagne**.

  ### Le fait

  `OpexOriginServed` (`ai/OpexAI/candidates.nut:868`) écarte une paire dont une extrémité est à
  moins de `ORIGIN_SEPARATION = 3` d'une origine déjà servie. Son commentaire dit que l'exclusion a
  été **« RAMENÉE À SON NOYAU le 2026-08-29 : elle ne vaut plus que pour les paires dont les DEUX
  extrémités sont servies »**.

  🔑 **Cet assouplissement n'a été appliqué qu'au RAIL.** Deux règles cohabitent dans
  `OpexIncrementalCandidateStillValid` (`ai/OpexAI/projects.nut`) :

  | mode | règle en vigueur | lignes |
  |---|---|---|
  | **route** (hors feeders) | `OriginServed(src)` **OU** `OriginServed(dst)` → rejet, `includeRoad = true` | `1042-1043` |
  | rail | `OriginServed(src)` **ET** `OriginServed(dst)` → rejet, `includeRoad = false` | `1051` |

  Une **seule** extrémité servie suffit donc à écarter une paire routière — et `includeRoad = true`
  fait qu'une ligne routière verrouille **ses propres** origines.

  ### Pourquoi c'est probablement le mur observé en partie

  - La note d'archive ([[opexai_plafonnement]], campagne 20 ans graine 42) mesure **213 à 242 paires
    écartées par an** à partir de 1982, avec **0 à 3 candidats classés/an** : *« la règle un seul
    raccordement par origine a consommé la carte »*.
  - **La route est notre mode dominant** : 364 gares de bus sur 495 (mesuré le 2026-09-10).
  - **Le vivier est vide dans 58,6 % des tours de `projects`** (C39.5b) et 61,8 % des passes n'ont
    rien à classer (C49) — le symptôme, re-mesuré aujourd'hui sans avoir été relié à cette cause.
  - 🔑 **C'est une deuxième boucle négative**, après celle du coût de régénération (C48) : plus l'IA
    construit de lignes routières, plus elle se ferme définitivement de terrain.
  - 🔗 [[opexai_plafonnement]] établit aussi que **`station_join` est structurellement inerte** (0
    tentative en 20 ans) **à cause de cette règle** : elle supprime le candidat à la génération avant
    que la jointure puisse être proposée. Corriger C55 pourrait le rendre atteignable.

  ### ⛔ Ce que la fiche ne propose PAS

  **Ne pas supprimer la règle.** Son commentaire justifie explicitement `includeRoad = true` :
  *« sans quoi il rebâtirait chaque année la même paire »*. Le levier envisagé est de faire passer le
  **OU** en **ET** pour la route, comme c'est déjà le cas pour le rail — pas de retirer la garde.

  ⚠️ **Le piège à instruire avant tout code** : l'anti-doublon de secours, `OpexRoadPairServed`
  (`projects.nut:1044`), n'est appliqué **que si `p.kind == "pax"`**. Pour le **fret routier**, il
  n'y a donc **aucune** protection de rechange — assouplir sans traiter ce cas rouvrirait la
  reconstruction annuelle de la même paire, un défaut connu et corrigé. Et le fret routier est
  précisément le canal que `portfolio_v2=1` ouvre en grand (68 gares camion contre 2).

  ### Étapes

  1. ✅ **FAIT le 2026-09-11** — voir le verdict ci-dessous.
  2. ✅ **FAIT le 2026-09-11** (`04d4004` + `8444c7a`) — et la crainte de la fiche est réfutée :
     voir « ÉTAPE 2 » ci-dessous. Le vrai risque n'était pas le doublon, c'était le **sur-service**.
  3. ✅ **FAIT** — `c55_freight_origin_relax`, défaut 0, indissociable de l'étape 2 (le filet
     n'existe que sous le levier).
  4. ✅ **FAIT le 2026-09-11 — VERDICT NUL, NON ADOPTÉ.** Défaut maintenu à 0. Voir « ÉTAPE 4 ».

  ### ✅ ÉTAPE 1 MESURÉE le 2026-09-11 — et elle réfute la moitié de la fiche

  Sonde `c55_origin_relax_probe` (défaut 0, gate dédié `OpexC55OriginRelaxLog`), 7 points
  d'instrumentation posés là où le filtre d'origine frappe réellement des candidats routiers :
  le garde incrémental (`projects.nut:1045`) et les **quatre** voies d'exclusion du fret routier
  (`candidates.nut:1912`, `:1934`, `:1961`, `:1971`). Diagnostic 5 graines × 6 ans,
  `results/diag_c55_origin_relax_6y_5seeds.json`, **0 échec**.

  | année | vus | rejets | % rejet | `both_served` | `one_served` | dont **pax** | `duplicate` |
  |---|---:|---:|---:|---:|---:|---:|---:|
  | 1971 | 14 754 | 2 984 | 20,2 % | 232 | 2 752 | **0** | 0 |
  | 1972 | 14 351 | 5 973 | 41,6 % | 689 | 5 284 | **0** | 0 |
  | 1973 | 12 824 | 5 754 | 44,9 % | 802 | 4 952 | **0** | 0 |
  | 1974 | 9 635 | 4 641 | 48,2 % | 735 | 3 906 | **0** | 0 |
  | 1975 | 9 097 | 4 735 | **52,1 %** | 879 | 3 856 | **0** | 0 |
  | **cumul** | **60 661** | **24 087** | | **3 337** | **20 750** | **0** | **0** |

  🔑 **1. Le levier existe : 86,1 % des rejets n'ont qu'UNE extrémité servie**, donc seraient
  récupérés par le passage OU → ET. Et le **taux de rejet monte de 20,2 % à 52,1 % en cinq ans** —
  c'est bien la signature d'une carte qui se ferme, mesurée sur le code d'aujourd'hui et non sur
  l'archive du 2026-08-29.

  🔴 **2. Mais il est ENTIÈREMENT dans le FRET routier : `one_served_pax = 0`**, sur les 5 graines,
  toutes les années, sans exception. **La thèse de la fiche — « la route pax est notre mode
  dominant, donc c'est elle que la règle ferme » — est réfutée.**
  **Pourquoi**, vérifié dans le code après coup : la génération pax routière n'appelle
  **jamais** `OpexOriginServed`. Elle se garde avec `OpexRoadPairServed` (les **deux** extrémités,
  `candidates.nut:1829`) et un plafond de lignes par ville (`4 + pop/300`). Le verrou pax est donc
  **ailleurs**, et le OU → ET ne le touche pas.
  ⇒ Conséquence directe : **l'étape 2 (fret routier sans anti-doublon de rechange) n'est plus une
  précaution, c'est le sujet lui-même.** `OpexRoadPairServed` n'est appliqué qu'à `p.kind == "pax"`
  (`projects.nut:1053`), donc relâcher côté fret sans filet est exactement le geste que la fiche
  redoutait.

  🟡 **3. `duplicate_exact = 0`** sur les 20 750 : aucune paire récupérable ne tombe sur les deux
  extrémités d'une ligne routière existante. ⚠️ **Ne pas surinterpréter** : la clé disponible au site
  d'appel est `OpexRoadPairServed` — une proximité géométrique aux origines des lignes routières, pas
  une identité `(cargo, tuileA, tuileB)`. Un zéro signifie « ces paires fret ne recouvrent pas les
  lignes routières existantes », pas « aucune reconstruction annuelle possible ».

  ### ⚠️ Ce que cette mesure ne dit pas, et les deux biais à connaître

  - Elle ne dit **pas** si les candidats récupérés seraient rentables, constructibles, élus, ni s'ils
    amélioreraient la valeur. Elle ne simule aucune décision ET : c'était le contrat.
  - Les compteurs sont des **expositions au filtre**, pas des paires uniques : une même paire revue à
    chaque régénération est comptée à chaque fois. Les **proportions** sont l'information ; les
    valeurs absolues ne sont pas un nombre de lignes perdues.
  - 🔑 **La sonde déplace la trajectoire quand elle est à 1** : au site incrémental elle évalue les
    deux prédicats alors que le code livré court-circuite au premier, et au site « source servie »
    elle énumère les paires que le code saute. **Ne jamais comparer les métriques de partie entre un
    bras sondé et un bras normal.** À 0 elle est inerte (smoke 3×2 identique au véhicule près).
  - Reste ouvert, si on veut comprendre le **vrai** verrou pax : ventiler `both_served` par site
    d'appel, et instrumenter `OpexRoadPairServed` + le plafond `4 + pop/300` côté génération.

  ⚠️ **La mesure d'archive date du 2026-08-29, sur UNE graine, avant `portfolio_v2=1` par défaut
  (07/09).** Les 213-242 paires/an sont à re-mesurer : c'est exactement la leçon de C47, où un
  chiffre de deux jours s'était effondré d'un facteur 36. Le symptôme actuel (vivier vide 58,6 %)
  est en revanche mesuré sur le code d'aujourd'hui.

  ### ✅ ÉTAPE 2 FAITE le 2026-09-11 — la crainte de la fiche était la mauvaise

  Instruction par lecture de code (investigation déléguée, recoupée à la main sur
  `main.nut:3210-3218` et `candidates.nut:1802-1829`) **avant d'écrire une ligne**.

  🔴 **1. « Rebâtir la même paire fret chaque année » est IMPOSSIBLE, avec ou sans relaxation.**
  Deux gardes le couvrent déjà, et aucun n'est `OpexRoadPairServed` :
  - le **ET lui-même** : une paire identique a ses deux extrémités servies **par sa propre ligne**,
    donc le ET la rejette ;
  - le **doublon exact tous modes** de `OpexIncrementalCandidateStillValid`
    (`projects.nut:1010-1018`) : `line.cargo == p.cargo` **et** `originA/originB == src/dst`. Les
    lignes routières enregistrent bien `originA = candidate.src` (`main.nut:3328`), et les tuiles
    de candidat viennent d'identités stables (`AITown.GetLocation` / `AIIndustry.GetLocation`
    relues à chaque rafraîchissement, `catalog.nut:753-791`).
  ⇒ **L'avertissement de la fiche (« aucune protection de rechange pour le fret ») était faux.**

  🔑 **2. Le vrai risque, que la fiche ne nommait pas : le SUR-SERVICE.** Sous ET, une industrie
  source déjà servie reste éligible vers **N** destinations — et
  `AIIndustry.GetLastMonthProduction` n'est **jamais** décompté de ce qui est déjà capté
  (`candidates.nut:1928-2015`). N lignes partiraient donc de la même industrie en comptant chacune
  **toute** sa production. Symétriquement côté destination : le plafond `4 + pop/300` est
  **pax-only** (`candidates.nut:1802-1829`, et `OpexTownRoadLineCount` exclut explicitement les
  cargos non-passagers). Le seul frein actuel est la guillotine `servedIndustry[si]`.
  ⚠️ Côté RAIL, où le ET est déjà en vigueur, rien ne protège non plus : `OpexShareBasin` partage
  par `StationID`, ignore l'industrie productrice, et `basin_share` est à **0** par défaut.

  **Le filet retenu, et pourquoi il est le bon** : remplacer la **proximité géométrique**
  (`< ORIGIN_SEPARATION = 3`, toutes lignes tous cargos) par l'**identité exacte, même cargo** —
  `busy(cargo, tuile)` = « une ligne route **ou rail** de ce cargo a déjà cette tuile exacte pour
  origine ». Une source porte alors au plus une ligne par cargo, une destination aussi : le
  sur-service est fermé **sans** introduire de comptabilité de production restante (délibérément
  hors périmètre — jamais deux changements à la fois).

  🔑 **La propriété qui rend le banc interprétable** : `busy(cargo, tuile)` implique une origine
  route/rail à distance 0, donc `OpexOriginServed(tuile, true)`. **Le bras ON ne rejette donc que
  des candidats que OFF rejetait déjà : il ne peut qu'en AJOUTER, jamais en retirer.** Un écart au
  banc ne peut pas venir d'un candidat perdu.

  Livré sous `c55_freight_origin_relax` (défaut 0), aux **trois** sites où la règle OU frappait le
  fret : génération (`candidates.nut:1871`), revalidation incrémentale (`projects.nut:1042`),
  revalidation vive à la construction (`main.nut:3210`). Coût opcodes **nul à défaut** (l'index
  n'est construit que si le réglage est à 1) ; `8444c7a` ajoute la sortie anticipée d'une source
  déjà occupée, qui évitait d'énumérer puits + villes pour rien dans la boucle la plus chaude.
  Smoke 3×2 sur le bras ON : 3/3, aucun crash.

  ### 🔴 ÉTAPE 4 — BANC OFFICIEL : VERDICT NUL, NON ADOPTÉ (2026-09-11)

  `sweeps/bench_c55_freight_origin_relax_10y_20seeds.py`, 20 graines × 10 ans apparié, **0 échec**,
  `results/bench_c55_freight_origin_relax_10y_20seeds.json`. Test des signes AVANT les moyennes :

  | métrique | écart ON | OFF gagne | p (signes) |
  |---|---:|---:|---:|
  | valeur de compagnie | −1,3 % | 11/20 | 0,82 |
  | profit annuel | −2,3 % | 13/20 | 0,26 |
  | profit trimestre | −5,5 % | 12/20 | 0,50 |
  | score officiel | −0,2 % | 8/20 | 0,50 |
  | note de gare | +0,2 % | 10/20 | 1,00 |

  ⚠️ **Correction du 2026-09-11 (même jour)** : ces p-values comptaient les ex æquo comme des
  défaites. Recalculées avec les ex æquo exclus (1 à 3 graines selon la métrique) : valeur de
  compagnie **p = 0,65** (ON 8 / OFF 11), profit annuel **p = 0,17** (ON 6 / OFF 13), score officiel
  **p = 1,00** (ON 9 / OFF 8). **Le verdict nul est inchangé**, mais les chiffres publiés plus haut
  étaient faux. Voir la leçon de lecture dans C56.

  **Aucune métrique ne s'écarte du hasard.** L'écart-type de la différence appariée est de
  **2,16 M£ pour une base de 15,1 M£** (14 %) : le levier ne déplace pas la valeur, il rebrasse la
  trajectoire. Le delta de gares va de **−42 à +51** selon la graine (médiane **−1**, 9 graines en
  hausse contre 10 en baisse) — signature d'une perturbation chaotique, pas d'une amélioration.

  🔑 **Le résultat qui compte, et qui réfute la thèse restante de la fiche** : l'étape 1 avait
  mesuré que **86,1 % des rejets étaient récupérables**. Ils le sont bien — 19 graines sur 20
  changent de trajectoire, donc le levier est vivant — et ils ne rapportent **rien** : +0,8 gare
  en moyenne sur 88. **Le filtre d'origine n'était donc pas la contrainte mordante.** Le
  plafonnement de [[opexai_plafonnement]] et le vivier vide de C49 ont une autre cause : ce n'est
  pas la génération de candidats qui manque, c'est leur élection ou leur financement.
  ⚠️ Même leçon que le pathfinder segmenté (A5) : *des candidats en plus qui ne paient pas*.

  ### Ce que C55 laisse ouvert

  - 🔴 **Le sur-service n'est TOUJOURS pas traité en configuration par défaut** : à
    `c55_freight_origin_relax=0`, c'est la guillotine géométrique qui le masque, et le RAIL
    (où le ET est déjà en vigueur, `basin_share=0`) n'a **aucune** protection. Une comptabilité de
    production restante par `(cargo, industrie)` reste une tâche à part entière, **non mesurée**.
  - Le verrou **pax** reste non identifié (l'étape 1 a montré que ce n'est pas `OpexOriginServed`) :
    instrumenter `OpexRoadPairServed` et le plafond `4 + pop/300` côté génération.

- 🟡 **C57 — Calibrer `WATER_LAKES_OPS`, posé à 50 000 sans aucune mesure.**
  📝 Ouverte le 2026-09-11 en adoptant C56. **Le correctif est adopté, sa valeur ne l'est pas.**

  ### Le fait

  `WATER_LAKES_OPS = 50 000` (`ai/OpexAI/lib_water.nut`) est un **premier jet**, écrit comme tel
  dans le code. Il borne `_MinchinWeb_Lakes_::FindPath` en opcodes et empêche le gel — mais rien ne
  dit qu'il est au bon niveau.

  ⚠️ **Ce que les 12 ex æquo du banc C56 disent, et ce qu'ils ne disent PAS.** Ils disent que le
  budget **ne mord presque jamais** : sur 12 graines, la trajectoire est identique au pound près.
  Ils ne disent **pas** que 50 000 est bien choisi. Les deux erreurs possibles sont opposées et
  aucune n'est mesurée :
  - **trop haut** → on paie jusqu'à 50 000 opcodes par paire non conclue avant d'abandonner, dans
    une boucle qui voit toutes les paires de sites ;
  - **trop bas** → on écarte des liaisons maritimes **réellement connectées**, et l'IA s'interdit
    des lignes rentables sans jamais le savoir (`connected != true` → `continue`, silencieux).

  ### Étapes

  1. ⬜ **Mesurer d'abord la distribution**, avant de toucher à la valeur : sous sonde, journaliser
     pour chaque appel à `OpexWaterLakesConnected` les opcodes consommés **et** l'issue (connecté /
     pas de chemin / budget épuisé). Sans cet histogramme, tout nouveau chiffre serait un deuxième
     jet aveugle.
     🔑 La question qui tranche : **la distribution est-elle bimodale ?** Si les recherches qui
     aboutissent coûtent toutes très peu et que seules les pathologiques explosent, il existe un
     seuil franc et le réglage est facile. Sinon, il y a un arbitrage réel à faire.
  2. ⬜ Balayage de la valeur (p. ex. 5 000 / 20 000 / 50 000 / 200 000) sur les graines qui
     exercent vraiment l'eau, en comptant les paires **perdues** par budget, pas seulement la valeur.
  3. ⬜ Banc officiel 20×10 apparié sur la valeur retenue si elle diffère de 50 000.

  ⚠️ **Ne pas confondre avec C56** : C56 a établi qu'un budget *en opcodes* est nécessaire — ce point
  est acquis et mesuré. C57 ne porte que sur le **niveau**.
  🔗 Lié à [[philosophie_opcodes_ressource]] : c'est exactement un arbitrage opcode contre
  information.

- 🔴 **C56 — LA GRAINE 2026 EST MORTE : l'IA s'arrête après 1970, et ça fausse tous nos bancs.**
  📝 Ouverte le 2026-09-11, **découverte par accident** en mesurant l'exposition des événements C52.

  ### Le fait, mesuré deux fois indépendamment

  | source | ce qu'on voit sur la graine 2026 |
  |---|---|
  | `diag_c52_event_exposure_10y_5seeds.json` | **une seule année journalisée (1970)** sur dix, et **zéro** événement de tout type : 0 accident, 0 véhicule non rentable, 0 première desserte, 0 offre de subvention |
  | `bench_c55_freight_origin_relax_10y_20seeds.json` | **13 gares et 22 véhicules**, contre une **médiane de 94,5 gares** sur les 20 graines — 7 fois moins que la deuxième plus basse (42 gares) |

  ⚠️ **Le run est déclaré `run_ok = True`, sans `failure_reason`.** Ce n'est donc pas une erreur NoAI
  détectée : l'IA cesse simplement de produire son rapport annuel après 1970. Elle construit 13
  gares puis ne fait plus rien pendant neuf ans.

  ### Pourquoi c'est prioritaire, au-delà de la graine elle-même

  - 🔑 **Tous nos bancs 20 graines incluent cette graine morte**, qui tire chaque moyenne vers le bas
    et gonfle la variance appariée. Le banc C55 du même jour affiche un écart-type apparié de
    2,16 M£ pour une base de 15,1 M£ : une graine à 2,3 M£ au lieu de ~15 M£ y contribue seule.
  - 🔑 **C'est la seule graine des 20 dont les deux bras C55 étaient STRICTEMENT identiques.**
    Évidemment : rien ne se passe après 1970, donc aucune divergence n'est possible. Une graine morte
    est un **poids mort** dans un test des signes — elle ne peut jamais départager deux bras.
  - Si la cause est un blocage générique (boucle, budget d'opcodes épuisé, exception avalée), elle
    peut frapper d'autres graines **partiellement**, sans être aussi visible.

  ### ✅ ÉTAPE 1 FAITE le 2026-09-11 — et elle trouve un vrai bug, mais pas la cause complète

  Capture `sweeps/diag_c56_seed2026_trace.py` : graine 2026 **et témoin vivant 999**, 10 ans,
  `-d script=4` + `decision_log=1`, journaux bruts dans `results/c56_seed2026_trace/`.

  🔴 **1. La graine n'est PAS morte de façon déterministe.** Sous ce bras elle finit à **55 gares et
  82 véhicules** (contre 13 et 22 au banc C55, et 1 seule année journalisée au diagnostic C52).
  **L'année d'arrêt change avec le bras : 1970, 1972 selon la mesure.** Ce n'est donc pas « une
  carte impossible », c'est un arrêt dont le déclenchement dépend du déroulé.
  ⚠️ Conséquence de méthode : **activer une sonde change l'issue de cette graine.** Ne jamais
  comparer ses métriques entre deux bras.

  🔑 **2. LE BUG TROUVÉ : la mémoire d'abandon est indexée par PAIRE, alors qu'un échec
  d'aéroport est une propriété du SITE.** Le journal montre **7 échecs de construction aérienne, et
  les 7 impliquent la même tuile 3308**, à chaque fois avec un partenaire différent :

  | date | paire | erreur |
  |---|---|---|
  | 1971-1-30 | 46019 → 3308, 43738 → 3308 | 263 |
  | 1971-7-10 | 35852 → 3308, 57684 → 3308 | 263 |
  | 1971-10-13 | 51422 → 3308, 5507 → 3308 | 263 |
  | 1972-2-3 | 3308 → 39019 | 258 |

  Chaque paire est neuve, donc `_markPairAbandoned` ne bloque **jamais** rien : la clé d'abandon
  air est `"air|tuileA|tuileB"` (`projects.nut:997`). Le site 3308 est re-planifié et re-tenté
  indéfiniment — il apparaît **325 fois** dans le journal. Coût mesuré : **92 scans de plans aériens
  en 2 ans** contre **176 en 10 ans** pour le témoin, soit **2,6× le rythme annuel**, à ~275 000
  opcodes la passe.
  ⇒ C'est une **boucle négative** de plus, de la même famille que celles de C48 et C55 : l'IA paie
  sans cesse pour un échec qu'elle ne mémorise pas au bon niveau.
  ⚠️ Les codes 263 et 258 ne sont **pas** décodés : le source d'OpenTTD n'est pas sur cette machine
  et le journal n'écrit que le numéro. Les faire journaliser en clair est un préalable.

  🔴 **3. CE QUI N'EST PAS EXPLIQUÉ, et il ne faut pas faire semblant** : pourquoi l'IA cesse
  **toute** sortie à 1972-2-23, en plein milieu d'une planification aérienne
  (`AIR_PLAN_PERF ... plans=193`), alors que la partie continue huit ans de plus. **Aucun message
  d'erreur, aucune exception, aucune ligne hors du canal `[script:4]`.** La boucle d'opcodes est le
  suspect naturel — mais ce n'est pas établi. Le bug n°2 explique le gaspillage, **pas l'arrêt**.

  ### Étapes restantes

  1. ✅ **FAIT le 2026-09-11 — RÉPONDU : le script ne meurt pas, il ne SORT JAMAIS de `catalog`.**

  **a. Il n'y a aucun message perdu à chercher.** `openttdlab` fusionne déjà `stderr` dans `stdout`
  (`openttdlab.py:409`) et ne filtre rien. S'il existait un message de mort, nous l'aurions.

  🔑 **b. Les deux instruments existants sont aveugles à ce cas précis, par construction :**
  - `OpexDecide` journalise la tâche **paresseusement** (`main.nut:310-320`) : la ligne
    `TASK name=` n'est écrite qu'à l'entrée de journal **suivante**. Une tâche qui ne revient
    jamais n'est donc **jamais** journalisée.
  - `C39_PASS_CLOCK_LEDGER` et les ledgers C41 publient **annuellement** (`main.nut:6905`) : jamais
    rien si l'IA se fige en cours d'année.
  *Un instrument dont le silence coïncide avec le cas intéressant ne mesure rien* — même leçon que
  la sonde C52 le matin même.

  **c. La sonde écrite pour ça** : `c56_task_trace` (défaut 0, `0452bcc`), qui écrit `TASK_ENTER` /
  `TASK_EXIT` **immédiatement**. Capture `results/c56_seed2026_trace/seed_2026_tasktrace.log` :

  | trace | cycle | date |
  |---|---:|---|
  | `TASK_EXIT name=catalog` | 72 | 1972-7-2 |
  | `TASK_ENTER name=catalog` | 73 | 1972-7-28 |
  | `TASK_EXIT name=catalog` | 73 | 1972-8-6 |
  | **`TASK_ENTER name=catalog`** | **74** | **1972-9-3** |
  | — **aucun `TASK_EXIT`, jamais** — | | |

  ⇒ **L'IA se fige À L'INTÉRIEUR de la tâche `catalog`**, qui enchaîne sur `_rebuildProjects` puis
  la planification aérienne (`main.nut:7396-7416`, `:8021-8023`). Après ce dernier `TASK_ENTER`, le
  journal ne contient plus que de l'activité aérienne (`AIR_FLEET` ×19, `AIR_TOWN_SERVED` ×8) puis
  le silence. Le dernier scan coûte **529 873 opcodes**, presque le double des ~275 000 habituels.
  C'est exactement l'hypothèse n°1 de l'instruction de code, et elle était donnée comme « non
  tranchable par lecture » : c'est la mesure qui a tranché.

  ✅ **Le défaut se reproduit malgré la sonde** (arrêt en 1972 de nouveau) : l'instrument ne masque
  pas le bug, on peut continuer à creuser.
  ⚠️ `LOOP_TICK` (toutes les 200 itérations) s'est révélé **trop espacé pour servir** : 3 lignes sur
  toute la partie. C'est `TASK_ENTER`/`TASK_EXIT` qui porte tout le diagnostic.

  ### ✅ ÉTAPE 1 ter FAITE le 2026-09-11 — 🔴 LE GEL EST DANS LA PHASE **EAU**

  Jalons `STAGE_ENTER`/`STAGE_EXIT` posés sur les **cinq** phases de `OpexBuildProjects`
  (`65cda9c`), délibérément toutes instrumentées et pas seulement les suspectes. Capture
  `results/c56_seed2026_trace/seed_2026_stage.log` :

  | jalon | date |
  |---|---|
  | `TASK_ENTER name=catalog` | 1972-9-3 |
  | `STAGE_ENTER` / `STAGE_EXIT` **rail** | 1972-9-5 → 9-8 |
  | `STAGE_ENTER` / `STAGE_EXIT` **route** | 1972-9-8 → 9-8 |
  | `STAGE_ENTER` / `STAGE_EXIT` **air** | 1972-9-8 → 9-11 |
  | **`STAGE_ENTER` eau** | **1972-9-11** |
  | — *dernière ligne du journal entier* — | |

  🔑 **Rail, route et aérien entrent et sortent proprement. L'eau entre et ne sort jamais**, et son
  `STAGE_ENTER` est **la dernière ligne du journal**, toutes catégories confondues. Le gel est donc
  dans `OpexWaterPlans` (`projects.nut:1805`), c'est-à-dire dans `builder_water.nut`.

  ⚠️ **Ceci INVALIDE l'hypothèse aérienne** que le premier journal suggérait : l'aérien était le
  dernier *visible* parce qu'il est la dernière phase **bavarde** avant l'eau, qui est muette. Un
  raisonnement « la dernière trace nomme le coupable » aurait désigné l'aérien à tort. C'est
  précisément pourquoi les cinq phases ont été instrumentées, y compris celles qu'on croyait hors de
  cause.

  🔗 **Le dépôt sait déjà que ce code est défectueux** : `docs/01_opex_builder_water_review.md`
  recense **deux bugs confirmés** dans le BFS nautique et sa marge de bounding-box, et la décision
  du 2026-09-09 était de le remplacer par `MinchinWeb.Lakes`/`Pathfinder.Ship` (voir `AGENTS.md`
  §3). **Cette fiche fournit la première preuve en partie que ce code ne fait pas que mal calculer :
  il peut ne jamais rendre la main.**

  ### ✅ CORRECTIF ÉCRIT ET VÉRIFIÉ le 2026-09-11 — `water_lakes_ops_budget` (défaut 0)

  **Le geste** (`c5c9257`) : borner `_MinchinWeb_Lakes_::FindPath` en **opcodes** en plus de son
  plafond d'itérations, via `OpexOpsMeasureEnd` — qui relit une marque immuable (donc sûr en lecture
  répétée) et **compte explicitement les ticks traversés**, au lieu de soustraire deux restes de
  `GetOpsTillSuspend` (qui décroît puis se réinitialise à chaque tick : une soustraction naïve
  deviendrait négative au passage de tick). Sortie anticipée **identique** à l'épuisement du plafond
  d'itérations : `return false` sans toucher `_running`, que `OpexWaterLakesConnected` traduit déjà
  en `null`, et l'appelant saute la paire. **Aucun contrat de retour n'a été modifié.**
  ⚠️ `WATER_LAKES_OPS = 50 000` est un **premier jet non calibré**, écrit comme tel dans le code.

  **Vérification, témoin joué dans les mêmes conditions** (indispensable : le gel dépend du déroulé,
  et 1024 ne gèle pas toujours) :

  | graine | OFF | ON |
  |---|---|---|
  | 2026 | gelée 1977, **26 gares** | 1979, **109 gares** |
  | 1337 | gelée 1976, **35 gares** | 1979, **91 gares** |
  | 1024 (contrôle sain) | 1979, 126 gares | 1979, **126 gares** |

  ⇒ **Le gel disparaît sur les deux graines qui le reproduisaient, et la graine saine ne bouge pas
  d'une gare.** Les parties amputées retrouvent un développement normal.
  ### ✅ BANC OFFICIEL 20×10 — **ADOPTABLE**, mais pas pour la raison qu'affiche la moyenne

  `results/bench_c56_water_lakes_ops_10y_20seeds.json`, 20 graines × 10 ans apparié, **0 échec**.
  Le premier banc de ce dépôt dont les 20 graines jouent réellement dix ans.

  🔴 **LIRE CE TABLEAU, PAS LA MOYENNE.** Le banc affiche `+13,2 %` de valeur de compagnie. **Ce
  chiffre ne veut PAS dire « l'IA joue 13 % mieux »** : il est presque entièrement produit par trois
  parties qui, avant, ne jouaient pas.

  | population | n | ex æquo | médiane (valeur) |
  |---|---:|---:|---:|
  | graines qui gelaient (2026, 1337, 1024) | 3 | 1 | **+235,1 %** |
  | graines déjà saines | 17 | 11 | **+0,0 %** |

  Test des signes, **ex æquo exclus** (c'est leur définition) :

  | métrique | ON gagne | OFF gagne | ex æquo | p |
  |---|---:|---:|---:|---:|
  | score officiel | **8** | **0** | 12 | **0,008** |
  | valeur de compagnie | 7 | 1 | 12 | 0,070 |
  | profit annuel | 6 | 2 | 12 | 0,289 |
  | note de gare | 5 | 3 | 12 | 0,727 |

  **Verdict : adopter**, sur trois motifs et aucun d'eux n'est « le gain moyen » :
  1. il **supprime un mode d'échec dur**, établi causalement (témoin joué dans les mêmes conditions,
     contrôle sain immobile) ;
  2. **aucune régression** : sur 20 graines, une seule est en retrait, et 12 sont strictement
     identiques — le correctif est inerte là où Lakes ne dépasse pas le budget ;
  3. la direction est **constante sur les quatre métriques**, et significative sur le score officiel.

  ⚠️ `WATER_LAKES_OPS = 50 000` reste **non calibré**. Les 12 ex æquo disent qu'il ne mord presque
  jamais ; ils ne disent pas qu'il est au bon niveau.

  🔑 **ERREUR DE LECTURE À NE PLUS REFAIRE, commise ici même** : la sortie du banc affiche
  `wins = 1 / 20`, qui se lit **« le bras A gagne strictement 1 fois sur 20 »** — et **PAS** « le
  bras B en gagne 19 ». Les **ex æquo ne sont comptés nulle part**. Ici 12 graines sur 20 sont
  identiques au pound près ; lire 19 victoires là où il y en a 7 transformait un correctif honnête
  en triomphe imaginaire. **Toujours recompter victoires / défaites / ex æquo avant de conclure d'un
  `wins = k / n`.**

  1 quater. ⬜ ~~**Localiser le point exact dans `OpexWaterPlans`.**~~ Candidats à instrumenter :
     `OpexWaterFindSiteSlice` (`builder_water.nut:220`, boucle `while` à trois conditions d'arrêt)
     et le BFS `WATER_BFS_MAX_NODES`/`WATER_BFS_MARGIN` (`:29-30`, `:340-351`).
     ⚠️ **Toujours ne pas corriger le site 3308 ni l'eau avant d'avoir répondu** : ce serait perdre
     la reproduction.
  ### 🔴 ÉTAPE 1 quinquies FAITE le 2026-09-11 — **3 GRAINES SUR 20 GÈLENT, TOUTES DANS L'EAU**

  `sweeps/diag_c56_freeze_scan.py`, 20 graines × 10 ans, `c56_task_trace=1`, sans `decision_log`.
  `results/diag_c56_freeze_scan_10y_20seeds.json`.

  | graine | dernière année | phase du gel | gares |
  |---|---:|---|---:|
  | 2026 | **1970** | `c56_stage_water` | 25 |
  | 1337 | **1971** | `c56_stage_water` | 35 |
  | 1024 | **1972** | `c56_stage_water` | 50 |
  | *les 17 autres* | 1979 | — | médiane **106** |

  🔑 **Les 20 graines entrent dans la phase eau ; 17 en ressortent, 3 non.** Ce n'est donc pas « le
  code de l'eau ne tourne jamais » : il tourne partout et se fige sur **15 % des cartes**.
  🔑 **Les graines gelées perdent les deux tiers de leur développement** : 35 gares en médiane
  contre 106. Elles ne sont pas « difficiles », elles sont **amputées**.
  ⇒ **Toutes nos campagnes 20 graines moyennent trois parties mortes depuis des semaines**, et ces
  trois-là ne peuvent jamais départager deux bras dans un test des signes : elles gèlent avant que
  le réglage testé ait le temps d'agir. La puissance de détection réelle du banc est de **17
  graines**, pas 20.

  ⚠️ **PIÈGE DE MESURE PAYÉ UNE FOIS, consigné dans l'en-tête du script** : le premier jet du
  détecteur annonçait **19 gels sur 20**. Faux. Un `_ENTER` sans `_EXIT` ne prouve rien : une partie
  saine s'arrête forcément au milieu d'une tâche, puisque la partie se termine sur un nombre de
  ticks fixe et non sur une frontière de tâche. **C'est l'année de fin qui tranche ; l'appariement
  ne fait que nommer la phase.** L'auto-test du script couvre désormais les trois cas, dont
  celui-là nommément.

  ### Étapes restantes

  ### 🔴 ÉTAPE 1 sexies FAITE le 2026-09-11 — **LE GEL EST DANS MinchinWeb.Lakes**

  Jalons par paire autour des deux étages de la double boucle. Sur les graines 2026 **et** 1337,
  la dernière ligne du journal entier est **identique** :

  ```
  C56_TASK PAIR name=lakes_enter pair=1
  ```

  ⇒ L'IA entre dans `OpexWaterLakesConnected` (`lib_water.nut:557`) — donc dans
  **`_MinchinWeb_Lakes_`** — dès la **première paire**, et n'en ressort jamais. Le tri des villes et
  le scan de sites se terminent normalement (`towns=12`). **Le BFS maison n'est jamais atteint.**

  🔴 **CECI RÉFUTE LA PRÉMISSE DU CHANTIER « remplacer le module eau par MinchinWeb ».**
  `water_lakes_connectivity` vaut **1 par défaut** depuis le 2026-09-09 : la bibliothèque n'est pas
  le remède envisagé, elle est **déjà en place et c'est elle qui bloque**. Adopter davantage de
  MinchinWeb (`Pathfinder.Ship`) sans traiter ça reviendrait à étendre le composant fautif.

  **Ce qui reste à établir, et qui n'est PAS mesuré** : *où* exactement dans Lakes.
  `OpexWaterLakesConnected` fait deux choses (`lib_water.nut:561-562`) — `InitializePath`, puis
  `FindPath(WATER_LAKES_ITERATIONS)` avec un budget de **500** (`:535`). La boucle de `FindPath` est
  bornée (`lib_water.nut:191`), donc **le budget ne protège pas de ce gel** : soit `InitializePath`
  ne rend pas la main (c'est lui qui déclenche la découverte de bassin par inondation), soit **une
  seule itération** de `FindPath` est elle-même non bornée. 🔑 *Un budget d'itérations ne borne rien
  si une itération est non bornée.* Hypothèse la plus plausible, **non vérifiée** : une carte à
  vaste océan connecté fait explorer un bassin entier en un seul pas.

  ### ✅ ÉTAPE 1 septies FAITE le 2026-09-11 — c'est `FindPath`, et le budget est INOPÉRANT

  Trois jalons dans `lib_water.nut` : de part et d'autre d'`InitializePath`, de part et d'autre de
  `FindPath`, et à l'intérieur de la boucle d'itérations (les 3 premières puis une sur cent).
  Résultat **identique sur les graines 2026 et 1337** :

  ```
  lakes_init_enter → lakes_init_exit → lakes_find_enter → i=0 → i=1 → i=2 → i=100 → (silence)
  ```

  🔑 **1. `InitializePath` n'est PAS en cause** : il entre et sort. La découverte de bassin par
  inondation, hypothèse précédente, est **réfutée**.
  🔑 **2. Ce n'est pas non plus UNE itération non bornée** : la recherche franchit plus de **100**
  itérations. Elle s'arrête entre la 100ᵉ et la 200ᵉ.
  🔴 **3. Le budget `WATER_LAKES_ITERATIONS = 500` n'est JAMAIS atteint.** Il ne protège donc de
  rien : l'IA meurt avant de l'épuiser. **Le compter en itérations est l'erreur** — une itération de
  `FindPath` (`lib_water.nut:191`) appelle deux fois `_AllGroups` et balaie des tableaux qui
  grossissent à chaque tour, donc son coût croît avec l'avancement. Un budget en itérations ne borne
  pas un travail dont l'unité n'a pas de coût borné.
  ⚠️ Nuance à ne pas perdre : l'IA n'est probablement pas dans une boucle infinie. OpenTTD suspend et
  reprend un script à court d'opcodes, il ne le tue pas — `FindPath` consomme donc tout le budget de
  chaque tick pendant **huit années de jeu** sans aboutir. Effet pratique identique à un gel, cause
  différente, et le correctif doit viser celle-là.

  🔑 **Ce que le correctif doit faire, et il est déjà à moitié en place** : `OpexWaterLakesConnected`
  traduit déjà « budget épuisé » en `null` (`lib_water.nut:585`), et l'appelant fait
  `if (connected != true) continue;` — une paire non conclue est simplement sautée. **La mécanique
  d'abandon existe et est correcte ; seule l'unité du budget est fausse.** Le correctif à la source
  est donc de borner `FindPath` en **opcodes** et non en itérations.

  ⚠️ **Piège d'instrumentation payé TROIS fois dans cette fiche** : `LOOP_TICK` tous les 200 tours
  (trop espacé), puis les compteurs de paires tous les 500 (jamais atteints avant le gel), puis la
  granularité par paire — la seule qui ait parlé. *Un compteur périodique ne dit rien de l'unité en
  cours au moment où le journal se coupe ; seul un jalon « le dernier écrit gagne » nomme le
  coupable.*
  2. ⬜ **Décider : garde anti-blocage, ou remplacement du module eau** par
     `MinchinWeb.Lakes`/`Pathfinder.Ship`, déjà décidé le 2026-09-09 pour d'autres raisons
     (`AGENTS.md` §3). ⚠️ Décision de conception : ne pas la prendre seul.
  3. ⬜ **Sort des graines gelées dans le protocole de banc** : les détecter et les signaler plutôt
     que de les moyenner en silence. ⚠️ Retirer une graine change la comparabilité avec toutes les
     campagnes passées — décision de méthode.
  1 bis. ⬜ Faire journaliser les codes d'erreur en clair (`AIError` → nom), sans quoi chaque
     diagnostic de construction reste un numéro opaque.
  2. ⬜ **Corriger le bug n°2 : indexer l'abandon aérien par SITE en plus de la paire**, sous
     réglage dédié défaut 0, un seul changement, puis banc 20×10.
     ⚠️ Ne pas supposer que ça règle l'arrêt : ce sont deux sujets.
  2. ⬜ Selon la cause : correctif sous réglage dédié, ou garde anti-blocage.
  3. ⬜ **Décider du sort des graines mortes dans le protocole de banc** : les détecter et les
     signaler, plutôt que de les moyenner en silence. ⚠️ Décision de méthode, à ne pas prendre seul :
     retirer une graine d'un banc change la comparabilité avec toutes les campagnes passées.

  ### ✅ Suite C56, livrée le 2026-09-11 — protocole et erreur air

  `sweeps/bench_v2.py` enregistre désormais `last_year` et `expected_last_year`. Un dernier
  autosave antérieur à l'année attendue devient `incomplete_run`, donc invalide le banc et reste
  présent dans son JSON : aucune graine ni aucune observation n'est retirée silencieusement.

  Les refus de construction aérienne publient aussi `error_text` via
  `AIError.GetLastErrorString()`. La piste « abandon par site » a été implémentée sous
  `air_abandon_site=0` : seuls `PREA`/`PREB`/`AFAIL`/`BFAIL` mémorisent l'ancre physique, jamais
  un échec de trésorerie, d'avion ou d'ordres.

  ⚠️ Le premier banc `bench_c56_air_site_abandon_10y_20seeds.json` est une preuve contre une
  **mauvaise clé**, pas contre le principe : `air_site|anchor` bannissait une tuile pour tous les
  types d'aéroport, alors que l'emprise dépend du type. Corrigé le même jour en
  `air_site|airportType|anchor`, et limité aux erreurs physiques durables.
  Diagnostic corrigé 5×6, `results/diag_c56_air_site_abandon_typed_6y_5seeds.json`, 10/10 saines :
  le bras historique gagne seulement 3/5 en valeur (+5,0 %) et profit annuel (+5,1 %). **Inconclusif
  et non prometteur : pas de banc officiel, réglage conservé à 0.** Il faudrait d'abord observer,
  avec `error_text`, des bannissements durables réellement réutilisés avant de rouvrir ce levier.

- 🔴 **C52 — Finir le chantier des événements : en brancher le maximum.**
  📝 Noté le 2026-09-10 sur demande utilisateur. **État constaté dans le code** (`ai/OpexAI/main.nut`) :

  | événement | branché ? | ce qu'il fait réellement |
  |---|---|---|
  | `ET_VEHICLE_LOST` | oui, `main.nut:6142` | **entièrement sous sondes** (`C41_VEHICLE_LOST_PROBE`, `C41_RAIL_LOST_PROBE`), toutes à défaut 0 ; le réglage `event_vehicle_lost` est lui-même à **0** (`info.nut:186`). Il journalise, **il ne répare pas** |
  | `ET_VEHICLE_CRASHED` | oui, `main.nut:5960` | **uniquement `CRASH_TRAIN`** — un avion ou un camion détruit ne déclenche rien |
  | `ET_VEHICLE_WAITING_IN_DEPOT` | oui | présent |
  | **`ET_VEHICLE_UNPROFITABLE`** | **NON** | jamais écouté |
  | `ET_INDUSTRY_OPEN` / `ET_INDUSTRY_CLOSE` / `ET_TOWN_FOUNDED` / `ET_ENGINE_AVAILABLE` / famille `ET_SUBSIDY_*` | oui | déjà exploités (invalidation, C42) |

  🔑 **Conséquence en configuration par défaut : une desserte peut disparaître sans que l'IA le
  remarque.** Un véhicule perdu ne produit aucune réaction, un véhicule non rentable n'est jamais
  signalé, et un camion ou un avion détruit passe inaperçu. C'est un candidat direct pour les gares
  qui ont du fret mais aucune note (~46 sur 5 graines × 10 ans, C51/diagnostic qualité).
  ⚠️ Ne pas confondre avec C42 (subventions), déjà cadré à part.

  ### ✅ ÉTAPE 1 FAITE le 2026-09-10 — recensement, couverture, et les tâches candidates

  Recensement de l'`AIEventType` complet de l'API 15.3 (source lue :
  `src/script/api/script_event_types.hpp` d'OpenTTD 15.3) croisé avec `_processEvents`
  (`main.nut:5970-6435`). **Aucune campagne** : lecture de code et de source.

  **Ce que nous captons vraiment : 11 branches sur ~35 types d'événements.**

  | événement | branche | réglage / défaut | effet RÉEL |
  |---|---|---|---|
  | `ET_VEHICLE_CRASHED` | `main.nut:5977` | aucun réglage | ⚠️ **`CRASH_TRAIN` seulement** ; pose un panneau, **ne répare rien** |
  | `ET_VEHICLE_WAITING_IN_DEPOT` | `:5997` | `event_depot_sell` = **0** | vend un véhicule déjà marqué au rebut — **action réelle** |
  | `ET_INDUSTRY_CLOSE` | `:6018` | `event_industry_close` = **0** | `_triggerScrapLine()` sur les lignes liées — **action réelle** |
  | 4 × `ET_SUBSIDY_*` | `:6048`, `:6099`, `:6120`, `:6141` | `event_subsidy_probe` = **0** | comptage seul, **aucun candidat généré** (c'est C42) |
  | `ET_VEHICLE_LOST` | `:6159` | `event_vehicle_lost` = **0** + sondes C41 à 0 | **journalise, ne répare pas** |
  | `ET_INDUSTRY_OPEN` | `:6330` | `event_catalog_invalidate` = **1** | rafraîchit + invalide le portefeuille |
  | `ET_TOWN_FOUNDED` | `:6364` | `event_catalog_invalidate` = **1** | idem |
  | `ET_ENGINE_AVAILABLE` | `:6398` | inconditionnel (+ `c39_engine_refresh`) | recalcule les bornes d'époque |

  **Jamais écoutés, et qui comptent** : `ET_VEHICLE_UNPROFITABLE`, `ET_VEHICLE_AUTOREPLACED`,
  `ET_AIRCRAFT_DEST_TOO_FAR`, `ET_STATION_FIRST_VEHICLE`, `ET_DISASTER_ZEPPELINER_*`,
  `ET_ENGINE_PREVIEW`, `ET_ROAD_RECONSTRUCTION`, `ET_EXCLUSIVE_TRANSPORT_RIGHTS`.
  **Jamais écoutés, et à ignorer sans regret** : famille compagnie (fusion, faillite, renommage),
  `ET_ADMIN_PORT`, `ET_WINDOW_WIDGET_CLICK`, `ET_GOAL_QUESTION_ANSWER`, `ET_STORYPAGE_*` — interface
  joueur ou Game Script, hors IA autonome.
  ⚠️ **Aucun événement n'est rendu impossible par notre configuration figée** : `make_cfg`
  (`sweeps/bench_v2.py:46-57`) ne fixe que villes, industries, inflation, croissance, année et
  taille de carte — elle ne désactive ni les catastrophes ni un type de véhicule. Ce qu'on ne peut
  pas dire sans mesure, c'est la **fréquence** des événements rares (zeppelin, destination air trop
  loin) dans le banc.

  ### Tâches candidates, triées par valeur/risque décroissant

  Chacune = **un réglage booléen à défaut 0, un diagnostic 5×6, puis un banc 20×10 apparié**.
  ⛔ Jamais de lot « événements » global : l'effet ne serait pas attribuable.

  | # | famille | geste | symptôme visé | risque |
  |---|---|---|---|---|
  | 1 | `ET_VEHICLE_AUTOREPLACED` ⛔ **HORS FENÊTRE, voir ci-dessous** | remplacer l'ancien ID par le nouveau dans `line.vehicles`, `scrapVehicles`, `_vehiclesToScrap` | inventaires de flotte qui pointent vers un ID mort | **aucun** (cohérence d'état) |
  | 2 | `ET_VEHICLE_CRASHED` | étendre la branche existante aux autres motifs que `CRASH_TRAIN` et réveiller la reconstitution déjà écrite | camion détruit à un passage à niveau, avion détruit : ligne vidée sans réaction | faible |
  | 3 | `ET_VEHICLE_LOST` (rail) | armer **une seule** des micro-réparations déjà écrites (signal **ou** jonction), pas les deux | convois perdus/bloqués | faible |
  | 4 | `ET_VEHICLE_UNPROFITABLE` | compteur par ligne, puis `_triggerScrapLine()` au-delà d'un seuil | 🔑 **les 10 véhicules sur 191 jamais rentables, dont un qui perd de l'argent 9 ans de suite** | moyen |
  | 5 | `ET_AIRCRAFT_DEST_TOO_FAR` | mettre la ligne au rebut ou rétablir des ordres cohérents | avion aux ordres inexécutables | fort |
  | 6 | `ET_DISASTER_ZEPPELINER_*` | marquer l'aéroport bloqué, suspendre son expansion, lever au *cleared* | piste bloquée | faible en marquage, fort si les ordres changent |
  | 7 | `ET_STATION_FIRST_VEHICLE` | **sonde seule** : mode, cargo, ligne, note initiale | établir si les ~46 gares fret sans note ont jamais été desservies | **aucun** |
  | 8 | subventions | offre → candidat de portefeuille | rendement des subventions | fort — **c'est C42, pas C52** |
  | 9 | `ET_ROAD_RECONSTRUCTION` | sonde de corrélation ville / lignes routières / véhicules perdus | la voirie municipale explique-t-elle des pertes ? | **aucun** |

  🔑 **Les trois premières sont à coût de comportement quasi nul** : elles ne créent pas de
  stratégie, elles branchent une réaction **déjà écrite** sur un événement qui existe déjà. C'est là
  qu'il faut commencer — et #1 et #7 et #9 ne changent rien du tout au comportement, ce qui les rend
  adoptables sur un simple contrôle de non-régression.
  ⚠️ **Piège vérifié** : `ET_VEHICLE_LOST` est déjà capté et son code de réparation existe, mais il
  est **entièrement sous sondes à défaut 0** — « brancher » ici veut dire *promouvoir une sonde en
  action*, pas écrire du neuf. Ne pas les armer toutes d'un coup : le dépôt a déjà payé le prix d'un
  changement qui en faisait deux.

  ### ⛔ #1 EST HORS DE LA FENÊTRE DU BANC — instruit le 2026-09-11, avant tout code

  🔑 **L'événement `ET_VEHICLE_AUTOREPLACED` ne peut pratiquement pas se produire dans un banc
  1970→1980.** Trois faits qui convergent :
  - Le renouvellement automatique est bien **actif** et c'est notre seul déclencheur :
    `AICompany.SetAutoRenewStatus(true)` + `SetAutoRenewMonths(-6)` (`main.nut:8293-8295`).
    `AIGroup.SetAutoReplace` n'est **jamais** appelé (grep sur `ai/OpexAI/`).
  - `-6` veut dire « six mois **avant** l'âge maximal ». Le commentaire de ce même bloc, écrit
    d'après une **campagne 20 ans graine 42** (`main.nut:8280-8286`), mesure qu'**un camion vit
    ~12 ans** et une locomotive 20 à 30. Premier renouvellement possible : ~11,5 ans.
  - **OpexAI n'a aucune flotte au 1ᵉʳ janvier 1970** : elle construit après le démarrage. Le premier
    renouvellement tombe donc vers **1981-1982**, quand le banc officiel s'arrête en **1980**.
  ⇒ **La correction #1 serait invisible au banc 20×10.** Son classement en tête par valeur est
  incompatible avec notre protocole de mesure. Elle n'est pas fausse — elle n'est pas *mesurable*
  ici. Trois issues, à trancher avant d'y consacrer du temps : banc 20 ans (le `YEARS = 20` de
  `bench_v2.py` est d'ailleurs son propre défaut), sonde préalable qui compte les événements, ou
  passer à une tâche exposée dans la fenêtre.

  ### ✅ #1 ÉCRITE ET ADOPTÉE le 2026-09-11 — mais elle ne répare RIEN dans nos fenêtres

  Décision utilisateur : corriger sans banc, puisque aucun banc ne peut la valider. Livré en
  `f42a164` : `ET_VEHICLE_AUTOREPLACED` remappe désormais **toujours** l'ancien ID vers le nouveau dans
  `line.vehicles`, **`line.vehicle`** (le scalaire que la fiche oubliait), `line.scrapVehicles` et
  la table `_vehiclesToScrap` (ancienne clé supprimée, nouvelle posée avec le même `lineId`, donc
  un remplaçant n'échappe pas à une mise au rebut déjà décidée). L'ancien réglage
  `event_vehicle_autoreplaced` est conservé pour compatibilité mais ignoré : l'intégrité des IDs n'est pas optionnelle. Sonde séparée
  `c52_autoreplace_log` (défaut 0).

  **Trois validations, et ce qu'elles prouvent chacune :**

  | validation | résultat | ce qu'elle établit |
  |---|---|---|
  | smoke 3×2 | 3/3 | l'enum `AIEvent.ET_VEHICLE_AUTOREPLACED` existe (évalué à chaque tour de boucle) |
  | non-régression 5×6, OFF vs ON | **35 comparaisons, 0 différence**, journal de décisions identique | inertie stricte dans la fenêtre du banc |
  | fenêtre 16 ans, 3 graines, sonde à 1 | **33 événements**, 0 crash | `AIEventVehicleAutoReplaced.Convert` et `GetOldVehicleID`/`GetNewVehicleID` existent **et s'exécutent** |

  🔴 **MAIS : 33 événements sur 33 sont `untracked`, et 33 sur 33 sont des véhicules ROUTIERS**
  (`results/diag_c52_autoreplace_16y_3seeds.json`, ventilation par `AIVehicle.GetVehicleType` du
  nouvel ID). **Zéro remappage en seize ans.**
  **Pourquoi, et c'est structurel** : la route est précisément le seul mode qui **ne stocke pas**
  ses ID et reconstruit sa flotte par gare et par ordres (`main.nut:1646-1669`) — il n'y a rien à y
  réparer. Les modes qui stockent des ID (rail, air, eau) ont des véhicules qui vivent **20 à 30
  ans** et ne sont donc pas encore renouvelés à seize ans.
  ⇒ **La correction est saine, prouvée inoffensive, et sa valeur est LATENTE** : elle ne mordra que
  sur une partie de 20 ans et plus, quand une locomotive ou un avion sera renouvelé. Gardée à
  défaut 1 pour cette raison, **pas** parce qu'un gain a été mesuré — il n'y en a aucun.
  ⚠️ **Ne jamais citer #1 comme une amélioration mesurée.**

  🔑 **Leçon de méthode, la deuxième de la journée après C55** : un sous-cas de la sonde s'était
  révélé aveugle — la ventilation par mode était déduite de la **ligne** où l'ancien ID avait été
  retrouvé, donc toujours « unknown » quand rien n'est retrouvé, c'est-à-dire exactement dans le cas
  à diagnostiquer. Corrigée pour lire le **type du véhicule**. *Un compteur dont la valeur par défaut
  coïncide avec le cas intéressant ne mesure rien.*

  ### 🔑 EXPOSITION MESURÉE le 2026-09-11 — le classement de la fiche est refait

  `c52_event_exposure_probe` (défaut 0), comptage **avant toute branche** de `_processEvents` donc
  aucun `continue` ne peut masquer un événement. 5 graines × 10 ans, 0 échec,
  `results/diag_c52_event_exposure_10y_5seeds.json`.

  | # | événement | occurrences | verdict |
  |---|---|---:|---|
  | 4 | `ET_VEHICLE_UNPROFITABLE` | **183 véhicules distincts** | 🥇 **de loin la plus exposée** (~37/graine/10 ans) |
  | 7 | `ET_STATION_FIRST_VEHICLE` | **359** | 🥈 matière abondante pour la sonde |
  | 2 | `ET_VEHICLE_CRASHED` | 10 | 🥉 modeste mais voir le 🔑 ci-dessous |
  | — | `ET_ENGINE_PREVIEW` | 20 | hors fiche, existe |
  | 5 | `ET_AIRCRAFT_DEST_TOO_FAR` | **0** | ⛔ **aucune exposition** |
  | 9 | `ET_ROAD_RECONSTRUCTION` | **0** | ⛔ **aucune exposition** |
  | 1 | `ET_VEHICLE_AUTOREPLACED` | **0** | ⛔ confirme indépendamment le hors-fenêtre établi plus haut |
  | — | `ET_EXCLUSIVE_TRANSPORT_RIGHTS` | 0 | ⛔ |

  🔑 **1. La tâche #2 ne dit pas ce qu'on croyait : `crashed_train = 0`, `crashed_other = 10`.**
  **100 % des accidents sont aujourd'hui ignorés** — la seule branche écrite ne traite que
  `CRASH_TRAIN` (`main.nut:5977`), et il n'y a eu **aucun** accident de train en 50 années de jeu.
  La fiche présentait #2 comme « étendre aux autres motifs » ; c'est en réalité « la branche
  existante n'a jamais rien traité ».

  🔴 **2. `ET_VEHICLE_WAITING_IN_DEPOT` : 0 occurrence.** La branche `event_depot_sell`
  (`main.nut:5997`) ne peut donc **jamais** agir, quel que soit son réglage. C'est un réglage mort,
  pas un réglage à défaut 0 — à traiter comme tel.

  🔴 **3. Subventions : 81 offres, 0 obtenue, 0 expirée** (`subsidy_awarded = 0` sur les 5 graines).
  **Nous ne remportons jamais une subvention.** Entrée directe pour C42, et bien plus parlante que
  le comptage d'offres.

  🟡 **4. `other = 2` par graine, exactement**, sur les 5 graines : deux types non identifiés, une
  fois chacun, en début de partie. Bénin, mais non identifié — ne pas conclure que le recensement
  est exhaustif.

  ⇒ **Ordre de travail refait par la mesure : #4, puis #7, puis #2.** #5, #9 et
  `ET_EXCLUSIVE_TRANSPORT_RIGHTS` sont **abandonnées faute d'exposition** — les rouvrir demanderait
  d'abord de montrer que l'événement se produit.

  ⚠️ **Ce que la lecture a trouvé en chemin, et qui dépasse #1** (à garder même si #1 est reportée) :
  - La fiche oublie **`line.vehicle`**, doublon scalaire de l'ID stocké pour l'avion et le bateau
    (`main.nut:2007`, `:2989`, `:3143`), et lui aussi sérialisé.
  - 🔑 **Il n'existe aucune reconstruction périodique de `line.vehicles` pour rail, air et eau** :
    `OpexLineVehicleIds()` rend le tableau mémorisé tel quel (`main.nut:1671`). **Seule la route
    s'auto-guérit**, en reconstruisant par `AIVehicleList_Station` + ordres (`main.nut:1646-1669`).
    Le dégât d'un ID mort est donc borné sur la route et persistant ailleurs.
  - La purge d'après-rechargement (`main.nut:7979-7987`, appelée une fois dans `Start()`) est
    **destructive** : elle retire l'ID mort sans jamais retrouver le remplaçant, et ne traite ni
    `line.vehicle`, ni `scrapVehicles`, ni `_vehiclesToScrap`.

  ⚠️ **Réserve de méthode sur cette instruction** : l'investigation déléguée citait abondamment le
  source d'OpenTTD 15.3 (`src/vehicle.cpp:164`, `src/table/engines.h:223`, `src/autoreplace_cmd.cpp`)
  — **ce source n'est présent nulle part sur cette machine**, ni dans le dépôt (`src/` n'y contient
  que du Python), ni dans l'image Docker. Ces références n'ont pas pu être lues et ne sont pas
  vérifiables. La conclusion ci-dessus ne repose donc **que** sur les faits vérifiés dans le dépôt,
  qui suffisent et vont dans le même sens.

  ### ✅ #2 ET #4 IMPLÉMENTÉS ET DIAGNOSTIQUÉS le 2026-09-11

  Conformément aux règles du dépôt (`AGENTS.md`), les deux branches actives ont été instrumentées sous réglages booléens isolés à défaut 0 :
  - **`event_vehicle_crashed`** (défaut 0, sonde `c52_crash_log`) : purge les inventaires et les streaks, distingue les crashs confirmés du filet annuel `RX`, et réarme réellement les lignes route, air et eau. Air/eau conservent moteur, dépôt et destinations afin de recréer le dernier véhicule sans template vivant ; le rail est seulement signalé, car reconstituer correctement un consist complet est hors de ce handler.
  - **`event_vehicle_unprofitable`** (défaut 0, seuil `unprofitable_streak_threshold` = **3**, sonde `c52_unprofitable_log`) : garde de jeunesse (`age >= 365`), table de suivi des années consécutives en déficit `_unprofitableStreaks` (sérialisée et purgée dans `Save()`/`Load()`). Au seuil, un véhicule en surcapacité est envoyé au dépôt puis vendu par une file de retraite autonome (`UNPROFITABLE_RETIRE`), même avec `event_depot_sell=0`; le dernier véhicule suit toujours le chemin explicite de mise au rebut de ligne (`UNPROFITABLE_SCRAP`).
  - **Résolveur universel `OpexFindLineForVehicle`** : unifie la recherche de ligne pour tous les modes (tableaux de véhicules, scalaires, véhicules au rebut, et ordres de stations), rétablissant la détection de ligne dans `EVENT_VEHICLE_LOST` qui était aveugle pour tout le trafic routier.

  🔴 **Piège critique Squirrel découvert et corrigé :**
  En Squirrel, les tableaux natifs n'ont **pas** de méthode `.find()`. L'appel `line.vehicles.find(vehicle)` levait l'erreur `the index 'find' does not exist` et tuait la VM au premier crash de camion (graine 2026 en 1971). Remplacé par des boucles d'itération natives Squirrel. De plus, la colonne `Err` a été ajoutée au processeur du banc pour lever immédiatement tout crash silencieux de l'IA.

  **Résultats du diagnostic apparié 5 graines × 6 ans (`results/diag_c52_events_6y_5seeds.json`, 0 erreur) :**

  | Bras | Val. Cie | Profit/an | Véhicules | Stations | Gains appariés vs OpexAI |
  |---|---:|---:|---:|---:|---|
  | **OpexAI** (baseline) | 8 746 782 | 2 336 691 | 162.8 | 77.2 | — |
  | **`event_vehicle_unprofitable=1`** | 8 645 932 | 2 276 968 | 157.4 | 78.4 | **3/5 gains CV** (+216k g100, +170k g2026, +27k g7) ; flotte allégée de 5.4 véhicules |
  | **`event_vehicle_crashed=1`** | 8 640 857 | 2 311 463 | 164.8 | 81.8 | **3/5 gains CV** (+206k g2026, +18k g7, +15k g100), 3/5 gains profit |

  **Résultats du banc officiel apparié 20 graines × 10 ans (`results/bench_c52_events_10y_20seeds.json`, 60/60 runs OK, 0 échec, 0 blocage) :**

  | Bras | Val. Entreprise moy. | Profit annuel moy. | Perf. Hist. | Note gares | Bilan apparié vs OpexAI |
  |---|---:|---:|---:|---:|---|
  | **OpexAI** (baseline) | 17 157 468 £ | 2 790 495 £ | 865.8 | 162.1 | — |
  | **`event_vehicle_crashed=1`** | **17 312 119 £** | **2 816 262 £** | **868.0** | 161.6 | 🏆 **Gagnant : +154 650 £ (+0.89 %)**, profit **+25 767 £/an**, **12/20 victoires** (pics à +1.96M g2026, +1.26M g100, +1.26M g65537) |
  | **`event_vehicle_unprofitable=1`** | 16 952 881 £ | 2 745 808 £ | 865.0 | 155.8 | −204 587 £ (−1.21 %), 7/20 victoires (**résultat historique au seuil 2**, trop agressif pour lignes mono-véhicule) |

  🔑 **Conclusions du banc 20×10 et diagnostic du seuil 3 ans :**
  - **Zéro blocage :** Aucune suspension, aucun gel et 0 erreur sur les 60 runs de 10 ans. Les détecteurs confirment la parfaite robustesse de l'IA.
  - **`event_vehicle_crashed=1` : signal positif, insuffisant pour adoption par défaut.** Le delta apparié est **+154 650,55 £** (12/20 victoires), mais sa dispersion est forte (SD 957 485,71 £; SE 214 100,31 £; IC95 t19 ≈ **[−293 461 ; +602 763] £**; test des signes bilatéral p≈0,503). Le résultat brut est conservé, mais ne démontre pas un effet positif généralisable. Les correctifs de cohérence et de reconstitution doivent être re-diagnostiqués avant tout nouveau banc officiel.
  - **Diagnostic `event_vehicle_unprofitable=1` au seuil de 3 ans (`results/diag_c52_unprof_thresh3_6y_5seeds.json`) :**
    - Réduit la sévérité : le bilan passe de 2/5 à **3/5 victoires appariées** (+265k sur g100, +266k sur g7, +55k sur g2026), delta moyen ramené de -131k à -105k £.
    - **Mécanisme de fuite identifié (effet churn)** :
      1. Dans la version mesurée, si `have > 1`, `UNPROFITABLE_RETIRE` prétendait vendre le véhicule mais ne disposait pas de consommateur autonome avec `event_depot_sell=0`, et ne touchait pas à `line.predTrains`. La version corrigée vend via une file dédiée et abaisse la cible de flotte pour empêcher le rachat immédiat.
      2. Si `have <= 1`, `UNPROFITABLE_SCRAP` retirait prématurément la ligne logique et ses véhicules sur de simples creux conjoncturels. Les gares, voies et voirie ne sont pas démolies par `_scrapDeadLines`, mais l'infrastructure abandonnée et la perte de service restent coûteuses.
      3. La gestion au niveau de la ligne entière (`_scrapDeadLines` via `deadStreak` et `srcSuffering`) est déjà plus robuste.
    - Le réglage reste à défaut 0, seuil calibré à 3.


- 🔴 **C58 — Post-mortem et audit prédictif via `ET_VEHICLE_UNPROFITABLE` : analyser les mauvais choix d'investissement.**
  📝 Ouverte le 2026-09-11 sur demande utilisateur, suite aux leçons de C52.

  ### Origine et vocation
  L'étape d'exposition de C52 a établi qu'`ET_VEHICLE_UNPROFITABLE` est de loin l'événement le plus fréquent (~183 véhicules touchés sur 5 graines × 10 ans). Mais le diagnostic de C52 a aussi montré que s'en servir comme couperet réactif aveugle en jeu (retrait de véhicule ou démolition de ligne) est destructeur de capital (effet churn de rachat immédiat par `_refleetRoadLines`, casse prématurée de lignes d'infrastructure mono-véhicule).

  🔑 **La véritable valeur d'`ET_VEHICLE_UNPROFITABLE` n'est pas réactive en jeu : c'est l'instrument de vérité terrain par excellence pour disséquer les erreurs de nos modèles prédictifs amont.**
  Lorsqu'une ligne ou un convoi devient déficitaire, qu'est-ce que nos prédictions avaient mal estimé ?
  1. **Les profits réels vs estimés (`predRevenue`)** : décalage entre le barème théorique de paiement de la cargaison et l'encaissement effectif.
  2. **Les coûts d'exploitation réels vs estimés (`predRunning`)** : sous-estimation des coûts d'entretien/circulation (`runningCost / day`), détours de tracé, attente excessive.
  3. **Les flux entrants (`predCarried`)** : surestimation de la production des industries sources (`AIIndustry.GetLastMonthProduction`), de la captation municipale (catchment), ou concurrence/partage de bassin.
  4. **La vitesse d'aller-retour et temps de rotation (`predOneWayDays`)** : surestimation de la vitesse commerciale réelle (embouteillages routiers, feux, relief, temps d'attente à quai avec `OF_FULL_LOAD`).

  ### Architecture de l'audit
  1. ⬜ **Instrumentation passive** : sous réglage `c58_unprofitable_audit` (défaut 0), lors de la réception de `ET_VEHICLE_UNPROFITABLE` sur un convoi âgé de ≥ 365 jours :
     - Résoudre sa ligne via le résolveur universel `OpexFindLineForVehicle`.
     - Comparer les prédictions initiales stockées sur la ligne (`predRevenue`, `predRunning`, `predCarried`, `predOneWayDays`) aux métriques réelles mesurées par l'API :
       - `AIVehicle.GetProfitLastYear(v)` : relevé par véhicule, puis **somme de tous les véhicules de la ligne** avant comparaison à `predRevenue`/`predRunning`/`predTrains`; ne jamais opposer une prédiction de ligne à un seul véhicule.
       - `realWaiting = AIStation.GetCargoWaiting(station, cargo)`
       - `AIVehicle.GetRunningCost(v)` est un **coût nominal annuel**, pas une dépense réalisée : ne pas inventer une API `GetOperatingCostLastYear`. Comparer le profit annuel réel agrégé de la ligne à la prédiction agrégée au même périmètre; si un coût est nécessaire, en déduire une estimation explicitement étiquetée (`revenu implicite = profit + coût nominal`) plutôt que l'appeler « réel ».
       - Mesurer la rotation par instrumentation : horodater les passages/événements aux deux terminus (ou un cycle d'ordres observé), conserver les timestamps par véhicule puis agréger par ligne. Ce ratio est alors comparable à `predOneWayDays`, sans API imaginaire.
  2. ⬜ **Classification de l'erreur** dans le journal de diagnostic :
     - `ERR_SUPPLY_DEFICIT` : le gisement attendu n'est pas au rendez-vous (production industrielle effondrée ou captage surestimé).
     - `ERR_RUNNING_COST_PRESSURE` : le coût nominal agrégé ou le revenu implicite estimé est incohérent avec `predRunning` (signal indicatif, pas une dépense réellement observée).
     - `ERR_SLOW_TURNAROUND` : le convoi met beaucoup plus de temps que `predOneWayDays` pour boucler son trajet (blocage, encombrement).
     - `ERR_CAPACITY_MISMATCH` : convoi surdimensionné ou sous-rempli.
  3. ⬜ **Exploitation** : utiliser la distribution empirique des causes pour calibrer les coefficients de sécurité et corriger les formules de rentabilité dans `candidates.nut`, `builder_road.nut`, `builder_rail.nut`, et `builder_air.nut`.



- 🔴 **C53 — S'inspirer de `SuperLib.Order` pour la gestion des ordres de véhicules.**
  📝 Noté le 2026-09-10 sur demande utilisateur. `ai/library/SuperLib-41/` est **présente dans le
  dépôt** et contient `order.nut` et `vehicle.nut`. OpexAI **ne l'utilise pas** — elle n'apparaît
  que dans des commentaires (`builder_air.nut:380`).
  ⚠️ **Contrainte déjà tranchée, à ne pas rouvrir** : l'import live de SuperLib **n'est pas
  possible** (mismatch de `GetAPIVersion`, voir `AGENTS.md` et `lib_water.nut:28-37`). La décision
  du dépôt est de **transcrire le source utile**, comme cela a été fait pour MinchinWeb. Toute
  reprise passe donc par de la copie annotée, pas par `import(...)`.
  **Reste** : lire `order.nut` / `vehicle.nut`, lister ce qui manque à notre gestion d'ordres
  (partage d'ordres, dépôt, rendez-vous, refit), et dire ce qui vaut la transcription.
  🔗 Lien direct avec **C52** : si les ordres sont mal formés, le véhicule se perd — et l'événement
  qui le signale n'est pas branché.

  🔴 **AJOUT du 2026-09-10 (demande utilisateur) — l'origine de la fiche, et le vrai test à faire.**
  L'idée ne venait pas de SuperLib : elle vient de ce qu'**AAAHogEx donne des ordres différents des
  nôtres, avec beaucoup de chargement complet**. ⇒ **À tester : imiter les ordres d'AAAHogEx**, sous
  réglage dédié et au banc officiel 20×10, au lieu de se limiter à une revue de bibliothèque.
  ⚠️ **Attention, C54 ne réfute PAS cette piste** : il a montré que nos ordres sont bien *formés*
  (`distinct_dest = 2` partout, zéro exception) — il n'a rien dit de leurs **drapeaux**, qui sont
  précisément le sujet ici.
  📊 **Recensement statique fait le 2026-09-10** (`grep -rho "OF_[A-Z_]*"`), à prendre pour ce qu'il
  est — un comptage de **sites d'appel**, pas d'ordres réellement posés en partie :

  | drapeau | AAAHogEx | OpexAI |
  |---|---:|---:|
  | `OF_NON_STOP_INTERMEDIATE` | **14** | **0** |
  | `OF_FULL_LOAD_ANY` | 3 (conditionnels) | 14 (sous `pax_full_load` / `air_full_load`) |
  | `OF_NO_LOAD` | 6 | 0 |
  | `OF_UNLOAD` | 5 | 1 |
  | `OF_TRANSFER` | 2 | 8 |
  | `OF_SERVICE_IF_NEEDED` | 4 | 0 |
  | `OF_NONE` | 0 | 16 |

  🔑 **Deux différences structurelles sautent aux yeux, et aucune n'est celle qu'on croyait** :
  1. **`OF_NON_STOP_INTERMEDIATE` : 14 sites chez elle, ZÉRO chez nous.** Elle pose du non-stop
     partout ; nos ordres ne le portent jamais. C'est un candidat plus net que le chargement
     complet.
  2. **Le chargement complet est chez elle une DÉCISION PAR LIAISON** (`isSrcFullLoadOrder` /
     `isDestFullLoadOrder`, `route.nut:2137` et `:2163`, plus `trainroute.nut:1330` en dur pour le
     rail), alors que chez nous c'est un **drapeau global de configuration**. La question n'est donc
     pas « plus ou moins de full load » mais « **qui décide, et sur quel critère** ».
  ⚠️ **Ne pas conclure du tableau que nous en faisons déjà plus qu'elle** : 14 sites d'appel gardés
  par deux réglages peuvent produire moins d'ordres réels que 3 sites conditionnels appelés à chaque
  liaison.
  ### Étapes
  1. ⬜ **Mesurer les ordres réellement posés, pas les sites d'appel** — les drapeaux vivent dans le
     chunk `ORDR` des sauvegardes, et le banc 1v1 en produit déjà des dizaines : comptage par IA et
     par mode, sans lancer une seule partie neuve. ⚠️ [[banc_aaahogex_openttd15]] et la règle de
     méthode de C54 : `ORDR` est un enregistrement à variantes, publier les distributions brutes et
     une garde anti-dégénérescence avant d'y croire.
  2. ⬜ Lire `route.nut:2100-2180` d'AAAHogEx pour extraire **le critère** de `isSrcFullLoadOrder`.
  3. ⬜ Un réglage par différence (non-stop d'abord, critère de full load ensuite), défaut 0, un seul
     changement à la fois, banc 20×10 apparié.

- 🟢 **C51 — Validation et clôture du portefeuille v2 (défaut consolidé, legacy supprimé le 2026-09-11).**
  📝 Archéologie faite le 2026-09-10, banc lancé le même jour.

  **Les faits, avec leurs sources :**
  - `portfolio_v2=1` est devenu le défaut le **2026-09-07**, par la « Résolution G1 »
    (`docs/journal_2026-09-07.md:886-899`) — **une revue de code, pas une mesure**. Le journal écrit
    lui-même : *« Le banc 10 ans × 20 graines demandé doit être exécuté dans l'environnement qui
    contient OpenTTDLab ; l'environnement courant ne fournit pas ce paquet. »*
  - **Ce banc n'a jamais été exécuté.** Seul candidat, `bench_post_review_fixes_v2_10y_20seeds.jsonl`
    (2026-09-07) : **un seul bras** (`OpexAI`, 12 graines), pas de `.json` final — il ne compare
    rien. Vérifié aussi que les 4 archives `.tar.gz` de `results/` sont des diagnostics mono-bras
    `OpexAI[decision_log=1]` sans rapport.
  - La seule mesure appariée existante de ce réglage, **20 graines × 3 ans du 2026-09-02**
    (`results/bench_floor_3y_20seeds.json` ⛔ **ARCHIVÉ, chiffre à re-mesurer, voir AGENTS.md §2 bis**, `docs/journal_2026-09-02.md:317`), donnait
    **−16,2 % de valeur** contre le contrôle, sous le titre *« ❌ `portfolio_v2` NON ADOPTABLE,
    même réparé »*.

  ⚠️ **Ce n'est PAS établi comme une régression** : la mesure de −16,2 % porte sur l'arbre
  d'avant-G1, et G1 a corrigé de vrais défauts du chemin v2 (borne du sac à dos qui sous-estimait
  l'optimum fractionnaire, second tri revenu/opcode parasite, ordre de `capitalBudgetHistory`).
  **Le v2 d'après-G1 n'est pas le v2 mesuré** — même leçon que C47. Ce qui est établi, c'est que
  **le chemin par défaut d'aujourd'hui n'a jamais été mesuré**, et que tout ce qui a été mesuré
  depuis (C39.5, C39.6, C48, C48.1, C49) tourne dessus.

  ### 🔑 Confondant à connaître AVANT de lire le banc — écrit d'avance

  **Le bras `portfolio_v2=0` n'est pas « le même code sans v2 ».** Il emprunte la branche legacy,
  et c'est **la seule** où vivent `pool_financeable` et `knapsack_roi` — deux réglages à défaut 1,
  donc **inertes sous `portfolio_v2=1`** (vérifié le 2026-09-10, voir
  [[opexai_vivier_financabilite]]). Le banc compare donc en réalité :

  | bras | ce qui tourne vraiment |
  |---|---|
  | `portfolio_v2=1` | sélection V2, `pool_financeable` et `knapsack_roi` **morts** |
  | `portfolio_v2=0` | sélection legacy **+ `pool_financeable=1` + `knapsack_roi=1` actifs** |

  ⛔ **Un écart mesuré ne sera donc PAS attribuable à `portfolio_v2` seul.** Trois réglages changent
  d'état d'un bras à l'autre. Le banc répond à « le chemin par défaut est-il meilleur que le chemin
  legacy complet ? », ce qui est la question opérationnelle — mais **ne pas le rapporter comme
  l'effet de `portfolio_v2`**. Isoler demanderait un troisième bras
  `portfolio_v2=0,pool_financeable=0,knapsack_roi=0`.

  ### Lecture pré-enregistrée

  Banc en cours : `OpexAI[portfolio_v2=1]` contre `OpexAI[portfolio_v2=0]`, 20 graines × 10 ans,
  sortie `results/bench_portfolio_v2_10y_20seeds.json`. **Test des signes d'abord, moyennes
  ensuite** ([[banc_monograine_insuffisant]]).
  - ✅ **v2=1 gagne** (signes ≥ 15/20, p < 0,05 sur les métriques de volume) → le défaut est enfin
    justifié, question close.
  - 🔴 **v2=1 perd nettement** → régression sur le chemin par défaut depuis le 2026-09-07, à
    remonter en priorité absolue : toutes les fiches ouvertes reposent dessus.
  - 🟡 **Neutre** → le défaut n'est ni justifié ni nuisible ; on le conserve (incumbent) en actant
    que l'argument de G1 porte sur la **correction du code**, pas sur une mesure de valeur.
  ### ✅ VERDICT (2026-09-10) — le défaut est justifié, et le −16,2 % ne se reproduit pas

  `results/bench_portfolio_v2_10y_20seeds.json`, 20 graines × 10 ans apparié, **40/40 parties
  saines**. Lecture au test des signes d'abord, comme pré-enregistré :

  | métrique | v2=1 | v2=0 | écart | signes | p |
  |---|---:|---:|---:|---:|---:|
  | **`n_stations`** | 89 | 68 | **+30,4 %** | **18/20** | **0,0004** |
  | `performance_history` | 796 | 772 | +3,0 % | **17/20** | **0,0026** |
  | `n_vehicles` | 184 | 163 | +12,7 % | **16/20** | **0,0118** |
  | `median_station_rating` | 158 | 145 | +8,9 % | **15/19** | **0,0192** |
  | `profit_year` | 2 572 890 | 2 521 661 | +2,0 % | 12/20 | 0,50 |
  | `company_value` | 14 877 298 | 15 334 811 | −3,0 % | 9/20 | 1,00 |

  ✅ **Critère de fermeture atteint** : les deux métriques de volume passent le seuil pré-enregistré
  (≥ 15/20, p < 0,05). **Le défaut `portfolio_v2=1` est justifié**, et le **−16,2 % du 2026-09-02
  ne se reproduit pas** — l'argument de revue de code de G1 était bon, et les correctifs qu'il a
  apportés au chemin v2 ont changé la donne. **Cinquième illustration du jour** qu'une mesure
  d'archive ne se transporte pas : ici dans le sens favorable.
  🔑 **Et le gain porte exactement sur la métrique n°1** : +30,4 % de gares, ~85 % de l'écart avec
  AAAHogEx venant du volume.

  ⚠️ **Deux réserves à ne pas escamoter :**
  1. **Le confondant pré-enregistré tient** : trois réglages changent d'état entre les bras
     (`portfolio_v2`, plus `pool_financeable` et `knapsack_roi` qui ne vivent que dans la branche
     legacy). Le résultat dit « **le chemin par défaut bat le chemin legacy complet** », **pas**
     « `portfolio_v2` vaut +30 % de gares ». Isoler demanderait un bras
     `portfolio_v2=0,pool_financeable=0,knapsack_roi=0`.
  2. 🔑 **Le volume ne s'est PAS converti en valeur** : +30,4 % de gares et +12,7 % de véhicules,
     mais `profit_year` +2,0 % (12/20, non significatif) et `company_value` **−3,0 %** (9/20,
     p = 1,00). L'IA construit beaucoup plus sans gagner plus. **Ne pas citer ce banc comme un gain
     de valeur** — c'est un gain de volume neutre en valeur, et cette dissociation est en soi un
     résultat à instruire.

  ⚠️ Correctif de volume appliqué **à la copie isolée seulement** : le checkpoint n'écrit plus
  `openttd_output` (recopié sur ~36 lignes par partie). 92 Ko après une minute contre plusieurs
  centaines de Mo auparavant. **À porter proprement dans `sweeps/bench_v2.py` si le résultat le
  confirme** — c'est la cause des fichiers géants qu'on archive depuis des jours.

  ### 🟢 CLÔTURE ET SUPPRESSION DU LEGACY (2026-09-11)

  Décision utilisateur du 2026-09-11 : le résultat du banc 20×10 apparié consolidant le défaut
  (+30,4 % gares, 18/20, p=0,0004 ; +12,7 % véhicules, 16/20, p=0,0118), le chemin historique
  (`portfolio_v2=0`) et tout ce qui ne vivait que pour lui sont définitivement supprimés de l'arbre :
  1. **Algorithme de portefeuille unique** : `OpexBuildProjects`, `OpexReselectProjects` et
     `OpexIncrementalUpdateProjects` convergent sur la sélection v2 (profit par livre de capital
     finançable, élection modale après le test de capital, vivier non borné à `PROJECT_POOL_K`).
  2. **Suppression du code mort orphelin** : `OpexKnapsackSolve`, `OpexKnapsackSearch`,
     `OpexKnapsackComputeBound`, `OpexProjectConflictKeys`, `OpexBuildMultimodalBudgetPool`,
     `OpexProjectModeBetter`, `OpexProjectRemember`.
  3. **Suppression de la plomberie `capital_ceiling_cycles`** : suppression de `capitalBudgetHistory`
     et `capitalBudgetPeak` (qui ne servaient qu'à l'admission au vivier legacy), et des paramètres
     associés dans `OpexBuildProjects` / `_rebuildProjects`.
  4. **Suppression des réglages et flags obsolètes** : `portfolio_v2`, `knapsack_roi`,
     `pool_financeable`, `capital_ceiling_cycles` retirés de `main.nut`, `info.nut` et de la
     whitelist `bench_v2.py`.

- 🔴 **C49 — Dénominateur variable, piloté par la cause prochaine d'un non-chantier.**
  📝 **DÉCISION UTILISATEUR EXPLICITE du 2026-09-10** : on instruit cette piste. ⚠️ **Elle LÈVE le
  refus doctrinal du 2026-09-07** (« A1 / dénominateur variable selon la ressource rare — décliné
  pour raison de doctrine, converge vers l'aiguillage pauvre/riche d'AAAHogEx »,
  `taches_archive_2026-09-09.md:2144`). Comme pour `pool_financeable`, **c'est une décision, pas une
  conclusion de mesure** — ne pas la présenter comme validée par un banc.
  🐛 Rappel de méthode : j'avais reproposé A1 sans grep préalable, deuxième récidive après
  `fleet_before_new` ([[feedback_lire_refutes_avant_conseiller]]).

  ### Ce qu'AAAHogEx fait vraiment (vérifié dans le source, mécanisme VIVANT)

  `CalculateProfitModel()` est appelée **à chaque tour** de la boucle principale
  (`ai/AAAHogEx-115/main.nut:747`), et `GetValue()` (`main.nut:828`) applique le régime au
  classement des candidats (`main.nut:2858`) :

  | régime | dénominateur | déclencheur (`main.nut:781-806`) |
  |---|---|---|
  | `roiBase` | profit / **capital** | pas riche **ou** inflation |
  | `buildingTimeBase` | profit / **temps de chantier** | riche **et** un type de véhicule a ≥ 100 places libres **et** < 70 % du plafond |
  | `vehicleProfitBase` | profit / **véhicule** | sinon |

  🔑 **Trois faits qui orientent notre variante** :
  1. **Sa détection passe par des CONSTANTES** (`room >= 100`, `current < max * 7/10`, `IsRich()`).
     Il n'y a donc rien à copier si on veut un mécanisme auto-calibrant.
  2. **Sa ressource rare est le PLAFOND DE VÉHICULES**, pas l'argent : le basculement se lit sur
     `AIGroup.GetNumVehicles` contre `GetMaxTotalVehicles()`. La richesse n'est qu'une *condition
     d'entrée* dans les régimes non capitalistiques ; pauvre ou en inflation, il classe par capital
     — exactement comme nous, tout le temps.
  3. **Il sait déjà « ne rien construire ce tour »** : en régime ROI il arrête la boucle quand le
     candidat suivant a `estimate.value < 200` (`main.nut:1054`).
  ✅ Vérifié aussi que le bloc commenté après `main.nut:807` est une variante **antérieure** placée
  derrière un `return;` — le code en vigueur est bien celui du tableau, pas du code mort.

  ### Notre variante : l'argmax sur les blocages observés, sans constantes

  Registre glissant à un compteur par ressource, incrémenté quand elle est la **cause prochaine**
  d'un non-chantier. Dénominateur du classement = ressource en tête du registre. Aucun seuil : un
  `argmax` sur des faits, qui se recalibre quand la partie change de régime.

  | ressource | événement qui l'incrémente | dénominateur associé | déjà instrumenté ? |
  |---|---|---|---|
  | trésorerie | projet mieux classé prêt mais pas finançable | profit / £ (actuel) | oui (`insufficient_cash`) |
  | **décision** | projet prêt ET finançable, mais `projects` n'a pas eu son tour | **profit / décision** | oui (C39.5, C48) |
  | temps de chantier | chantier élu occupant N jours pendant lesquels rien d'autre ne se fait | profit / jour de chantier | partiellement |
  | terrain / site | `build_failed`, `too_close` | profit / tentative | oui |
  | **plafond de véhicules** *(ajout utilisateur)* | flotte proche de `GetMaxTotalVehicles()` | profit / véhicule | **non** |

  🔑 **La ressource « décision » est neuve et c'est le résultat de la journée** : notre débit chute
  d'un facteur 9,2 (C39.6b) et devient la contrainte dominante en fin de partie. Si les décisions
  sont rares, le bon dénominateur n'est plus le profit par livre mais le **profit par décision
  consommée** — et C48 en donne le prix : une passe qui bâtit paie ~2,7 M opcodes de régénération,
  une passe qui s'abstient ne coûte presque rien. **Construire consomme une décision future.**

  ### ⛔ Garde-fous imposés par l'archive — à lire avant d'écrire une ligne

  - **Ne pas refaire `shadow_pricing`** (−11,2 % valeur, −25,6 % profit) : des prix duaux 1-D
    indépendants sur tout le vivier sur-taxent des candidats qui ne peuvent pas être retenus
    ensemble. Le registre de blocages **ne calcule aucun prix**, il compte des faits — c'est
    précisément ce qui le distingue.
  - **Ne pas refaire « surplus capital-seul » ni « filtre densité < λ_argent »** : **7/7 défaites à
    6 ans** chacun, interdiction déjà écrite dans `ai/OpexAI/tension.nut:600-602`.
  - **Complementary slackness** : une ressource ne compte que si elle est réellement saturée par la
    décision du cycle en cours (`taches_archive_2026-09-09.md:340`). Le registre l'implémente
    empiriquement — c'est son principal argument théorique.
  - ⚠️ **Mode d'échec n°1, documenté** : une barre surestimée rend tous les coûts réduits négatifs
    et **plus rien ne se construit** (archive, point 4). **Un repli garantissant la construction
    après K cycles sans chantier est OBLIGATOIRE**, pas optionnel.
  - ⚠️ **Douze leviers sur douze ont perdu** sur l'axe « ce que le portefeuille choisit ». Celui-ci
    en est un. Contrat avant code, critère de fermeture pré-enregistré, banc **20×10 apparié**, test
    des signes avant les moyennes.

  ### Étapes

  ✅ **Contrat écrit le 2026-09-10 : [`docs/06_denominateur_variable.md`](06_denominateur_variable.md).**
  Trois points qu'il tranche et qui n'étaient pas acquis :
  **(a)** la cause prochaine se lit sur **le projet de plus haut rang NON bâti dans la passe**, un
  seul incrément par passe — compter tous les rejets mesurerait le bruit de `search_in_progress`
  (69,6 %), que C41.49 a montré bénin ;
  **(b)** `build_time` est **écarté de la v1** : on ne sait pas l'observer comme cause bloquante
  sans le confondre avec `decision`, et fabriquer une ressource fantôme fausserait l'argmax ;
  **(c)** 🔑 si la ressource rare est la **décision**, le dénominateur vaut 1 et le classement
  devient le **profit ABSOLU** — l'exact opposé de notre ratio permanent, et cohérent avec nos
  chantiers à 11–13 k£ contre les leurs à 180–220 k£.
  🔑 **Et une propriété qui rend C49 moins risqué que les réfutés** : un changement de dénominateur
  ne fait que réordonner, **il ne peut pas affamer le constructeur** — le mode d'échec « plus rien
  ne se construit » ne concerne que les seuils d'acceptation, hors périmètre.

  1. ✅ ~~Contrat écrit avant code~~ : définition exacte de chaque « cause prochaine », fenêtre du
     registre (proposition : depuis la dernière régénération, pas une constante de temps), règle de
     départage en cas d'égalité, et le repli anti-blocage.
  2. ⬜ **Sonde d'abord, levier ensuite** : un registre à défaut 0 qui **mesure** les causes
     prochaines **sans changer aucune décision**. Lire quelle ressource domine, et si elle change
     au cours de la partie. Si une seule ressource domine toujours, la piste se réduit à un
     dénominateur fixe — et il faudra le dire.
  3. ⬜ Seulement après lecture : le levier, un réglage, un seul changement.
  4. ⬜ Banc officiel 20×10 apparié.

  ⚠️ **Les deux `roi` ne sont pas comparables** (vérifié) : le sien vaut
  `routeIncome * 1000 / (véhicules + construction + coût d'opportunité)`
  (`estimator.nut:77`), le nôtre `profitAnnual * 1000 / (capital + immobilisé)`
  (`economy.nut:325-329`), et le nombre qu'il imprime entre parenthèses **omet le coût
  d'opportunité** (`estimator.nut:247`). Toute comparaison exige de recomposer les deux fractions
  sur une base homogène.

- 🔴 **C50 — Chronologie comparée 1v1, plus longue et non biaisée.**
  📝 Script écrit le 2026-09-10, **campagne pas encore lancée** :
  `sweeps/diag_1v1_chronology.py` (6 ans × 5 graines `100 12345 42 7 999`, `--max-workers 2` car un
  duel partagé fait tourner deux IA par partie).
  🔑 **Deux corrections de méthode par rapport à `diag_1v1_shared_timeline.py`** : `decision_log=0`
  chez nous (le journal nous coûtait des opcodes que l'adversaire ne paie pas, dans une mesure dont
  le sujet EST notre débit — auto-handicap intégré à l'instrument), et **comptage par delta d'état
  de jeu**, symétrique pour les deux compagnies, au lieu de compter nos chantiers depuis notre
  propre journal.
  **Ce que la version 2 ans / graine 42 disait déjà** (`results/diag_1v1_shared_timeline_2y_seed42.json`) :
  1970 → AAAHogEx 17 tentées / **10 réussies**, nous **10 chantiers** — jeu égal ; 1971 → 24 / **18**
  contre **5** — ils accélèrent de 80 %, on chute de 50 %. ⚠️ Une graine, deux ans, partie partagée
  (concurrence pour le terrain), et notre bras journalisait : indicatif, pas un banc.
  **Reste** : lancer la campagne (sur `/home`, jamais le tmpfs, avec garde-fou disque), puis voir si
  l'écart 1970/1971 se creuse comme le prédit le mécanisme C48.
  **Demandé en plus, à instrumenter** : chronologie côté nous avec trésorerie, profit par ligne,
  projets refusés pour trésorerie **avec leur ROI**, projets réalisés **avec coût et ROI**. ⚠️ Via
  une **sonde dédiée** (quelques dizaines de lignes/an), **pas** `decision_log=1` (plusieurs
  milliers — 1 070 lignes d'`AIR_TOWN_SERVED` sur 2 ans à lui seul), sinon on réintroduit
  l'auto-handicap qu'on vient de retirer.

- 🔴 **C48 — Le coût de `projects` n'est PAS le balayage : c'est la régénération qu'il déclenche.**
  📝 Ouverte et mesurée le 2026-09-10. Sonde `c48_project_attempt_ledger` (défaut 0, gate dédié
  `OpexC48ProjectAttemptLog`) : encadre les 5 sites de tentative de `_tryBuildProjects`
  (fleet/air/road/rail/eau) en opcodes et en jours, plus la fonction entière, plus la profondeur de
  balayage — ventilé **par année** dès la conception. Diagnostic 5 graines × 6 ans, 0 échec,
  `results/diag_c48_project_attempt_6y_5seeds.json`.

  | année | passes | tent./passe | `best_len` | bâti/passe | kops/passe | **% hors tentatives** |
  |---|---:|---:|---:|---:|---:|---:|
  | 1971 | 353 | 1,05 | 6,2 | 0,147 | 185 | **58,2 %** |
  | 1972 | 171 | 0,96 | 18,2 | 0,327 | 420 | 80,6 % |
  | 1973 | 55 | 1,80 | 64,0 | 0,891 | 1 693 | 83,3 % |
  | 1974 | 46 | 3,65 | 62,9 | 2 298 | 0,935 | 93,6 % |
  | 1975 | 36 | 6,89 | 55,0 | 0,944 | 2 750 | **93,5 %** |

  ❌ **Hypothèse de départ réfutée.** Je pensais que le coût venait d'un balayage plus profond
  payant une replanification complète par tentative ratée. Le balayage s'approfondit bien (1,05 →
  **6,89** tentatives par passe, ×6,6), **mais les tentatives ne sont que 6,5 % du coût en 1975** :
  **93,5 % des opcodes de `_tryBuildProjects` sont dépensés HORS des tentatives.**

  🔑 **Où ils vont, vérifié dans le code** (`main.nut:3802-3819`) : après un succès
  (`builtCount > 0`), `_tryBuildProjects` **régénère lui-même le portefeuille** —
  `_resizeAirFleets` à blanc puis `OpexIncrementalUpdateProjects` sous `portfolio_cache=1`
  (défaut), qui rebalaie les groupes de candidats et régénère feeders, plans de flotte et plans
  aériens (`projects.nut:1170-1249`).

  🔑 **Et c'est une BOUCLE DE RÉTROACTION**, la décomposition le montre : le coût de régénération
  par chantier croît ×3,7 (carte qui se remplit, cohérent avec C41.22 et les boucles en
  O(villes × lignes)), **et** la part des passes qui bâtissent monte de **0,147 à 0,944**. Moins de
  passes ⇒ chaque passe trouve presque toujours de quoi bâtir ⇒ chaque chantier paie une
  régénération ⇒ moins de passes. ×3,7 × ×6,4 = **×24 sur le coût hors tentatives par passe**, ce
  qui reconstitue le ×15 du coût par passe et le ×9,2 du débit de décision (C39.6b).

  ⚠️ **Réserves** : effectifs faibles en fin de partie (36 à 55 passes/an, 5 graines cumulées).
  Le champ `max_rank_per_pass` est **contaminé par la sentinelle −1** des passes sans tentative
  (d'où le −0,04 de 1972) — lire `attempts_per_pass`, pas lui.
  ⚠️ **Ne pas en déduire un levier** : `portfolio_max_batch` (−3,8 %) et `portfolio_dynamic_batch`
  (−36,0 %) ont déjà attaqué « bâtir plus par passe » et perdu ; `portfolio_cache` (C36.1, adopté)
  est déjà la version incrémentale de cette régénération. **Le sujet est le COÛT de la
  régénération incrémentale, jamais profilé, pas la fréquence des chantiers.**
  ✅ **C48.1 — profil livré et mesuré le 2026-09-10 : la cause racine est ALGORITHMIQUE.**
  Sonde `c48_incremental_profile` (défaut 0, gate dédié `OpexC48IncrementalLog`, 7 phases encadrées
  dans `OpexIncrementalUpdateProjects`), 5 graines × 6 ans, 0 échec,
  `results/diag_c48_1_incremental_profile_6y_5seeds.json`.

  **Deux phases font 94 % du coût, toutes les années** (`feeders`, `fleet`, `tension_ctx` : ~0 % ;
  reste de la fonction : 0,1–0,2 %) :

  | année | kops/appel | `air` | `groups_replay` | `selection` |
  |---|---:|---:|---:|---:|
  | 1971 | 573 | 48,7 % | 44,8 % | 6,3 % |
  | 1973 | 1 458 | 38,1 % | 51,9 % | 9,7 % |
  | 1975 | 2 355 | 50,0 % | 43,9 % | 5,9 % |

  🔑 **Le volume traité NE croît PAS — c'est le coût unitaire qui explose**, et il suit le nombre de
  **nos propres lignes** :

  | grandeur | 1971 | 1975 | facteur |
  |---|---:|---:|---:|
  | lignes existantes (par appel) | 9,4 | 56,8 | **×6,0** |
  | plans aériens traités / appel | 202 | 166 | ×0,8 |
  | **opcodes par plan aérien** | 1 379 | 7 078 | **×5,1** |
  | projets rejoués / appel | 297 | 236 | ×0,8 |
  | **opcodes par projet rejoué** | 863 | 4 371 | **×5,1** |

  🔑 **Vérifié dans le code, pas déduit** : `OpexIncrementalCandidateStillValid`
  (`projects.nut`) fait `foreach (line in lines)` pour **chaque** candidat retenu — le test de
  doublon balaie toutes les lignes bâties. Le rejeu est donc en **O(projets × lignes)**, et
  `OpexAirPlans` a la même forme (scans répétés sur villes et lignes, `builder_air.nut:835-1148`).
  Coût unitaire ×5,1 contre nombre de lignes ×6,0 : **linéaire en nombre de lignes**, à la mesure
  près.

  **La chaîne complète est refermée** : régénération en O(objets × lignes) (C48.1) × payée sur
  94 % des passes en fin de partie (C48) ⇒ coût par passe ×15 ⇒ **débit de décision ÷9,2**
  (C39.6b) ⇒ plafond de volume, la métrique n°1. **Plus l'IA construit, moins elle peut décider.**

  🆕 **Piste jamais tentée, et hors de la liste noire** : le balayage linéaire des lignes est une
  **structure de données**, pas une règle de décision. Un index exact (par cargo/origine/destination)
  rendrait le même verdict à coût constant. ⚠️ Mais ⛔ « un cache exact change quand même la
  trajectoire » (C41.30, C41.38, memo `origin_sitable`) : moins d'opcodes ⇒ cadence différente ⇒
  chiffres différents à calcul identique. **Ça se banche comme tout le reste (20×10 apparié), ça ne
  se suppose pas.** Les douze leviers déjà réfutés portaient tous sur *ce que* le portefeuille
  choisit ; celui-ci ne change *rien* à ce qu'il choisit.
  ⚠️ Effectifs faibles en fin de partie (29 à 47 appels/an, 5 graines cumulées).

  📋 **RESTE À FAIRE sur C48, par ordre :**
  1. ⬜ **Contrat avant code** pour l'index exact des lignes : quelle clé (cargo + origine +
     destination ? les deux sens ?), qui la maintient (construction, abandon, revente), et
     **comment prouver l'équivalence** du verdict avec le balayage actuel. Un index qui répond
     « déjà bâtie » différemment ne serait plus un changement de structure mais un changement de
     décision — et retomberait dans la liste noire.
  2. ⬜ **Sonde d'équivalence avant tout banc** : faire tourner les deux implémentations côte à côte
     sous un réglage, journaliser tout désaccord de verdict. Zéro désaccord attendu ; un seul
     suffit à arrêter la piste.
  3. ⬜ **Banc officiel 20 graines × 10 ans apparié**, lu au **test des signes** avant les moyennes.
     ⛔ Ne pas conclure d'un 5×6 : C41.47 est le précédent d'un diagnostic 5×6 NUL et sous-puissant
     démenti par un banc 20×10 net (19/20, p<0,0001).
  4. ⬜ **`OpexAirPlans` a la même forme** (`builder_air.nut:835-1148`, scans répétés sur villes et
     lignes) et pèse ~50 % du coût — au moins autant que `groups_replay`. **Ne pas traiter
     `groups_replay` seul en croyant avoir réglé le sujet** : à lui seul il ne rend que ~44 %.
  5. ⬜ Question non instruite : le coût unitaire suit le nombre de lignes **à la mesure près**
     (×5,1 contre ×6,0), mais rien ne prouve que la relation est causale plutôt que corrélée à la
     maturité. Une régression coût-unitaire contre `lines.len()` à âge de partie constant
     trancherait.

  ⚠️ **Deux réglages exposés sont du CODE MORT sous `portfolio_v2=1`** (vérifié 2026-09-10) :
  `pool_financeable` (adopté par décision utilisateur le 2026-09-03) et `knapsack_roi` (défaut 1)
  ne sont lus que dans la branche legacy, injoignable. **Leurs bancs comparaient deux bras
  identiques** — ne pas citer leurs résultats. Détail dans
  [`docs/journal_2026-09-10.md`](journal_2026-09-10.md) §3.

  📕 **Échecs et leçons de la journée** : [`docs/journal_2026-09-10.md`](journal_2026-09-10.md) —
  trois conclusions rétractées (erreur d'unité, confondant de maturité, mauvais coupable), une
  fiche bâtie sur un chiffre d'archive périmé, quatre défauts d'agent rattrapés en relecture, et
  les erreurs d'infrastructure (tmpfs, guetteurs, cohabitation de sessions).

- ⚪ **C47 — FERMÉE le 2026-09-10, prémisse RÉFUTÉE par sa propre mesure.** La fiche partait de
  `build_failed = 1 795` sur 5 graines × 6 ans (`results/diag_constants_binding_6y_5seeds_v2.json` ⛔ **ARCHIVÉ, chiffre à re-mesurer, voir AGENTS.md §2 bis**,
  2026-09-08) et d'un ratio annoncé de « ~9 chantiers ratés par ligne ». **Ce chiffre ne se
  reproduit plus.** Campagne `decision_log=1`, mêmes graines, même durée, code d'aujourd'hui
  (`results/diag_c47_build_failed_6y_5seeds.json`, 0 échec) :

  | motif | 2026-09-08 | 2026-09-10 |
  |---|---:|---:|
  | `search_in_progress` | 1 729 | **451** |
  | `plan_failed` | 56 | 80 |
  | **`build_failed`** | **1 795** | **50** |
  | `insufficient_cash` | (absent) | 44 |
  | `abandoned_pair` | 343 | 23 |
  | **total** | **3 923** | **648** |

  **`build_failed` a été divisé par 36, le total des rejets par 6.** Ratio réel : **0,21 échec de
  construction par ligne non-rail** (50 pour 234), pas 9. La cause la plus probable est
  l'adoption de **C41.47** (`c41_rail_cash_release=1`) le 2026-09-09, qui libère `_railSearch` dès
  le premier blocage trésorerie — mais l'écart n'a pas été attribué formellement.
  ⛔ **La leçon de méthode, à retenir** : une mesure vieille de deux jours dans un document n'est
  PAS une garantie qu'elle tient encore, exactement comme « un défaut adopté dans un document n'est
  pas une garantie que le code l'applique ». **Re-mesurer avant de bâtir une fiche sur un chiffre
  d'archive**, surtout après une adoption qui touche le même chemin.

  ✅ **Ce que la campagne apprend quand même, et qui vaut mieux que la fiche d'origine** :
  - **`build_failed` est désormais EXCLUSIVEMENT aérien** : 50/50 en `mode=air`, **0 eau, 0 route**
    (`detail=BFAIL` 38, `AFAIL` 12 ; `AIError` 263 → 44, 258 → 6). Volume trop faible pour être un
    gisement.
  - **`search_in_progress` domine à 69,6 %** (451/648). C'est le rejet en bloc de **tout** candidat
    rail tant qu'une recherche est en vol (`main.nut:2574`), pas seulement de celui qui est
    cherché.
  - 🔑 **Ça explique le `never_top` de C39.5** : le classement place des candidats rail au-dessus de
    ce qui est bâti, et ils sont rejetés en bloc. Cohérent avec l'asymétrie mesurée
    (`never_top_share` **67,8 %** sous recherche rail contre **24,7 %** hors), et compatible avec
    C41.48 (le top finançable n'est le candidat *cherché* que 19,3 % du temps — mais les AUTRES
    candidats rail sont rejetés par le même garde).
  - **L'IA construit presque exclusivement de l'aérien** : `PROJECT_CHOSEN` non-rail = air 206,
    route 28. À rapprocher de [[opexai_prix_rail_terrain]] (l'avion prend 64 % du capital).
  **Suite éventuelle** : le gel en bloc du canal rail est un sujet **C41**, pas une fiche
  `build_failed`. Ne pas rouvrir C47.

- 🟡 **C42 — Transformer les offres de subvention non attribuées en candidats.** Implémenté sur la branche `feat/c42-subsidies` (`c42_subsidies=1`).
  - **Génération opportuniste (`OpexGenerateSubsidyCandidates`)** : conversion des offres actives en candidats routiers scorés avec le multiplicateur de jeu `difficulty.subsidy_multiplier` (1,5× à 4×) lissé sur la durée `difficulty.subsidy_duration` (0 à 5000 ans) et l'horizon d'amortissement $\tau$.
  - **Invalidation réactive et purge événementielle** : écoute `ET_SUBSIDY_OFFER`, `ET_SUBSIDY_AWARDED`, `ET_SUBSIDY_OFFER_EXPIRED`, purge atomique des projets zombies (`_purgeSubsidyFromProjects`) et réévaluation immédiate du portefeuille.
  - **Gardes transactionnelles et correction `ResolveCompanyID`** : vérification de non-attribution et validité à l'entrée de `_tryBuildRoadProject` et juste avant pose. Comparaison de l'attribution avec `AICompany.ResolveCompanyID(AICompany.COMPANY_SELF)` pour reconnaître nos propres victoires.
  - **Double horizon économique et persistance** : maintien séparé de l'économie de base et de l'économie subventionnée dans le candidat, recalcul post-siting vivant et enregistrement dans `_lines`.
  - **Filtrage amont des offres déjà couvertes** : détection bidirectionnelle et inter-modes (`OpexSubsidyMatchingLineId`), élimination des doublons et gardes physiques dès la génération.
  - **Contrôle systématique de l'acceptation destination** : suppression du raccourci `pop < 200`, vérification stricte `AITile.GetCargoAcceptance >= ROAD_ACCEPTANCE_FULL_UNIT` (8) pour éviter les rejets `SITEB` et abandons injustifiés.
  - **Délai de chantier dérivé et urgence (`OpexSubsidyChantierDays`)** : remplacement du seuil fixe de 180j par l'estimation physique du temps de mise en service ($70\text{j} + \text{oneWayDays}$) et suivi de la marge d'urgence $\text{slackDays}$.
  - **Banc officiel 20×10 + duel AAAHogEx (`results/bench_c42_duel_10y_20seeds.json`, 2026-09-11)** :
    - 0 échec NoAI (60/60 parties saines).
    - **Solo C42 vs Solo Contrôle** : `company_value` -4,54 % (14 victoires contrôle), `profit_year` -7,10 % (15 victoires contrôle, p=0,0414, t=+2,34), `profit` trimestriel -9,51 % (17 victoires contrôle, p=0,0026, t=+2,92). Le volume de gares augmente (+6,2 gares, 102 vs 96) mais la flotte diminue (201 vs 214 véhicules) et la rentabilité globale baisse : les subventions éparses dispersent le capital et consomment le tour de cycle rare au détriment des lignes aériennes/ferroviaires denses (illustration directe de la règle C44).
    - **Duel partagé C42 vs AAAHogEx** : AAAHogEx l'emporte à 20/20 sur toutes les métriques. En présence d'AAAHogEx sur la carte partagée, OpexAI tombe à 5,67 M£ de valeur et 1,24 M£ de profit annuel (contre 17,20 M£ et 2,79 M£ en solo), tandis qu'AAAHogEx atteint 37,79 M£ de valeur et 10,26 M£ de profit annuel avec une flotte saturante de 1 077 véhicules (contre 158 pour OpexAI).
    - **Décision** : Fonctionnalité nettoyée et robuste, maintenue désactivée par défaut (`c42_subsidies = 0`).

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

- 🟡 **C45 — `Save()`/`Load()` : le symptôme était éteint, le fond ne l'était pas. Traité le 2026-09-10.**

  ⛔ **La prémisse de cette fiche était FAUSSE au moment où on l'a relue** : « `OpexAI::Save`/`Load`
  n'existent nulle part (vérifié par grep) ». Ils ont été ajoutés le **2026-09-09 à 17 h 24**
  (`1c12fd5`) ; le journal d'erreur qui avait motivé la fiche datait du **même jour à 06 h 50**
  (`[script:3] [0] [W] Save function is not implemented`, retrouvé dans
  `results/bench_c41_30_*.json`).
  ✅ **Contrôle explicite fait avant de coder**, même harnais sur deux arbres, 60 jours de jeu :
  arbre d'avant `1c12fd5` ⇒ **4 avertissements** ; arbre courant ⇒ **0 octet de sortie**.
  🔑 **Règle de méthode, troisième illustration en deux jours** : une fiche de backlog vieillit
  comme une mesure d'archive. Vérifier la prémisse avant d'ouvrir le chantier, pas après.

  ### Ce qui n'allait vraiment pas, et qui est corrigé

  1. 🐛 **`Start()` écrasait `_startYear`** (`main.nut`, ligne du `AIDate.GetYear(...)` initial) : au
     rechargement, l'année de départ sauvegardée était perdue et `yearsElapsed` repartait à **0**,
     donc toute la logique d'époque avec.
  2. 🐛 **`Start()` reprenait l'emprunt maximal** juste après : une partie rechargée qui avait
     remboursé se **réendettait d'office**, sans décision.
  3. 🐛 **`_lines` n'était ni sauvé ni reconstruit** : au retour de `Load()`, l'IA reprenait une
     partie **aveugle sur son propre réseau** — `OpexGetServedTowns(this._lines)` vide, exclusion
     des origines servies vide, ferraillage sans objet.
  4. 🐛 **`_loadedFromSave` était écrit et jamais lu** (3 sites). C'est lui qui manquait aux points
     1 et 2 ; il a maintenant un usage.

  **Livré** : réglage `save_full_state` (défaut 0) ; `Save()` inchangé à 0, et à 1 il ajoute
  `lines` (**par référence** : le sérialiseur du moteur parcourt la structure, une recopie coûterait
  des opcodes sous le budget qui tue le script), `abandonCounts`, `lastRepayMonth`, `taskCycle`,
  `taskCursor`, `vehiclesToScrap`, `taskDue` **clé par nom de tâche** (l'ordre de la file peut
  changer d'une version à l'autre) ; `Load()` range les lignes brutes dans `_pendingLines` sans
  toucher au monde ; nouvelle `_reconcileAfterLoad()` appelée depuis `Start()` qui valide chaque
  ligne contre le monde réel et journalise **une** ligne de preuve.

  ### Contraintes du moteur, vérifiées dans la source OpenTTD 15.3 (`src/script/script_instance.cpp`)

  Racine = table obligatoire ; types admis : entier, chaîne, tableau, table, booléen, `null` — **pas
  de flottant** (`You tried to save an unsupported type. No data saved.`) ; profondeur ≤ **25** ;
  chaînes ≤ **254** caractères ; `Save()` tourne **sous budget d'opcodes** (`This script took too
  long to Save.` tue le script) ; `Save()`/`Load()` s'exécutent sous `DisableDoCommandScope` ; et
  🔑 **l'ordre est constructeur → `Load()` → `Start()`** — c'est pourquoi la réconciliation ne peut
  pas vivre dans `Load()`.
  ⚠️ Le flottant est donc **arrondi**, pas jeté : une métrique prédite perdue en silence au
  rechargement serait pire que sa troncature.

  ### Preuve : test de rechargement réel, à harnais nouveau

  `sweeps/save_load_roundtrip.py` (nouveau) : phase A joue 3 ans en conservant les sauvegardes,
  phase B **recharge** une sauvegarde de milieu de partie et rejoue 2 ans, avec `-d script=4`.
  🔑 **`openttdlab` ne sait pas charger une sauvegarde** : le script remplace le `-g` nu par
  `-g <sauvegarde>` dans l'appel au binaire, et **retire `start_ai` du `game_start.scr`**, sans quoi
  une deuxième compagnie OpexAI démarre à côté de celle qu'on recharge.

  Même graine, même sauvegarde rechargée (1971-07-01, 44 gares / 56 véhicules / 491 368 £) :

  | | `save_full_state=0` | `save_full_state=1` |
  |---|---|---|
  | ligne de preuve au chargement | `LOAD_RECONCILE saved=0 kept=0` | **`saved=25 kept=25 dropped=0 vehicles_purged=1`** |
  | gares 2 ans après la reprise | 85 (**+41**) | **69 (+25)** |
  | véhicules | 136 | 111 |
  | valeur de compagnie | 3 091 320 £ | **3 223 325 £** |

  ✅ **`Load()` est prouvé appelé** — et il fallait ce marqueur : le moteur ne journalise **que les
  échecs** de chargement, il n'existe aucun message de succès. ✅ Aucun motif d'erreur
  (`unsupported type`, `too deep`, `too long to Save`, `script died`) dans aucune des deux phases :
  `_lines` passe le sérialiseur tel quel.
  ⚠️ **Ce que ce test ne dit PAS** : que les 41 gares du bras 0 sont des **doublons**. Il montre que
  sans persistance l'IA construit 64 % de gares en plus pour **moins** de valeur, ce qui est
  *cohérent* avec une reconstruction par-dessus son propre réseau — la nature des gares n'est pas
  mesurée, et c'est **une graine, un rechargement**.
  ⚠️ **Confondant trouvé par le harnais, à connaître** : recharger une sauvegarde en headless fait
  apparaître une **compagnie fantôme** (`is_ai=0`, ~100 000 £ jamais mouvementés) ; `-D` ne la
  supprime pas. Elle n'a rien construit ici, mais elle interdit de lire les agrégats « toutes
  compagnies » d'une phase B.

  ### ✅ Banc officiel : coût NUL, défaut passé à 1

  `results/bench_save_full_state_10y_20seeds.json`, 20 graines × 10 ans apparié, **40/40 parties
  saines**, `save_full_state=0` contre `=1` : **les VINGT graines sont identiques au bit près** sur
  `company_value`, `profit_year`, `performance_history`, `n_stations`, `n_vehicles` et
  `median_station_rating`. Écart 0,00 % partout, 20 égalités sur 20.
  🔑 **C'est le résultat attendu et c'est ce qui autorise l'adoption** : `Save()` construit sa table
  en temps quasi constant et la sérialisation est faite par le moteur, hors de l'horloge de décision
  de l'IA. Le réglage **ne peut se voir qu'au rechargement**, et le banc ne recharge jamais.
  ⚠️ **Le piège « deux bras identiques » ([[opexai_vivier_financabilite]]) est écarté par une mesure
  indépendante** : le même mécanisme d'armement produit `LOAD_RECONCILE saved=25` à 1 et `saved=0`
  à 0 dans le test de rechargement. Le réglage atteint bien l'IA ; s'il ne changeait rien, ce serait
  faute d'effet en partie neuve, ce qui est précisément la thèse.
  ⇒ **Défaut 1 adopté le 2026-09-10** (`info.nut` et `main.nut` alignés) : bénéfice mesuré au
  rechargement, coût mesuré nul.

  ### Reste
  - ⬜ Non persistés et assumés : `_staleness`, ledgers C41/C48/C49, `_railSearch`, `_projects`,
    `_catalog` (télémétrie ou reconstruits au premier cycle). `_activeSubsidies` reste **à trancher**
    (relisible par API, mais les compteurs historiques ne le sont pas).

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

  ### ✅ (a) FAIT le 2026-09-10 — **oui, le fret est resté quadratique**, et le plafond est pire qu'annoncé

  Vérifié par lecture de code (audit Codex + recoupement manuel des trois boucles). **Aucune
  campagne** : la forme se lit dans le source.

  | générateur | forme réelle | grille spatiale ? |
  |---|---|---|
  | `OpexPaxCandidates` | indexée | **oui** (`candidates.nut:1206`) |
  | route **pax** | indexée | **oui** (`candidates.nut:1820`) |
  | `OpexFreightCandidates` (rail) | `foreach (si in sources) { foreach (di in sinks) … }` par cargo, **produit cartésien** (`candidates.nut:1300-1315`) | **non** |
  | `OpexBuildRoadCandidates` → `OpexRoadFreightCandidates` | même produit cartésien (`candidates.nut:1911-1921`) | **non** |

  🔑 **Le chiffre de la fiche (~379 000) était optimiste** : le code ne casse pas la symétrie et les
  flux sont orientés, donc le pire cas industrie→industrie est **871 × 870 = 757 770** paires
  visitées, auxquelles s'ajoutent les livraisons industrie→ville, **871 × 731 = 636 701** — soit un
  **plafond de 1 394 471 paires visitées avant tout filtre**, pour le rail comme pour la route.
  🔑 **Le filtre de distance ne sauve rien** : `OpexRoadDistanceAllowed` est testé **à l'intérieur**
  de la boucle interne (`candidates.nut:1920`), donc il réduit les paires *retenues*, jamais les
  paires *visitées*. C'est exactement le défaut que `1c12fd5` a corrigé pour le pax.
  ⇒ **(a) est close : la cause du blocage en 1024² est encore présente dans les deux canaux fret.**

  ### Correctif proposé, et sa classification — à faire, pas encore fait

  Réutiliser `OpexSpatialGrid` (`spatial.nut:44`, elle n'a besoin que du champ `.tile` malgré son
  nom centré villes) sur les puits d'un cargo : maille `bounds.railMax` pour le fret rail,
  `roadGenMax` pour le fret routier, et ne demander que les 9 cellules voisines de chaque source.
  ⚠️ **Condition impérative pour que ce soit neutre** : remettre les indices retenus **dans l'ordre
  original de `sinks`** avant `OpexMakeCandidate`, sinon l'ordre d'insertion dans le vivier change
  et la trajectoire du banc bouge.
  📐 **Classification, à respecter avant d'adopter** (le dépôt confond souvent les deux) :
  - **correctif de complexité NEUTRE** — même ensemble et même ordre de candidats, seulement moins
    de paires visitées : contrôle de non-régression + diagnostic 5×6 suffisent ;
  - **heuristique** — tout ce qui change l'ensemble ou l'ordre : top-M par source, score
    revenu/distance, pré-score de profit non prouvé conservateur : **banc officiel 20×10 apparié
    obligatoire**.
  Le pré-score bon marché évoqué en (b) tombe dans la seconde catégorie **sauf** s'il est démontré
  qu'il ne peut écarter aucun candidat à profit positif.
  ⛔ **Ne pas confondre avec « l'eau fait déjà un pré-score »** : ce que fait `builder_water.nut` est
  un **pré-filtre de faisabilité** (distance minimale, portée du navire, connectivité), pas un score
  de profit bon marché.

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
  `results/diag_c41_3b_water_site_profile_6y_5seeds.json` ⛔ **ARCHIVÉ, chiffre à re-mesurer, voir AGENTS.md §2 bis** : 591 918 opcodes, **0 plan**, dont
  557 253 (94,1 %) dans la recherche de sites — 557 109 dans le seul scan/filtrage contre 144 dans
  les tests de quai. **Aucune paire n'atteint le BFS ni l'économie.** `OpexWaterFindSite` ne visite
  que `r <= coverage` autour de la tuile centrale : si aucune côte admissible n'est trouvée là, le
  moteur de connectivité est hors-sujet. Redessiner ou mesurer cette recherche **d'abord**.
  - 🔴 **Architecture à faire avant toute nouvelle tentative de défaut eau** : séparer la
    découverte maritime du portefeuille. Une tâche dédiée de l'ordonnanceur consomme une tranche
    bornée de tuiles et de `BuildDock`, reprend ses curseurs par ville et alimente un catalogue
    positif/négatif. `OpexWaterPlans` doit devenir un lecteur pur de ce catalogue : aucune
    exploration de carte ni `AITestMode` pendant la reconstruction mensuelle du portefeuille.
    Les premiers essais intégrés au portefeuille (catalogue, curseur Manhattan, fronts réels,
    plusieurs sites) ont été **rejetés** : `results/diag_water_catalog_fronts_multisite_6y_5seeds.json`,
    10/10 parties saines mais historique gagnant 5/5, valeur +181 % et profit annuel +89 %.
    Hypothèse à vérifier : le coût et le décalage de ticks du scan restent injectés dans le canal
    de décision général avant qu'une paire eau existe. Instrumenter d'abord la tâche dédiée
    (tuiles, villes terminées, sites, composants, première paire connectée), puis diagnostic 5×6
    **uniquement sur accord explicite** ; banc officiel 20×10 seulement si le diagnostic produit
    des paires connectées et de l'économie atteignable.
  - ✅ **VERDICT du banc officiel de `water_site_catalog` — dépouillé le 2026-09-10 au soir**, il
    dormait sur le disque depuis le matin sans être lu.
    `results/bench_water_site_catalog_20x10.json`, 20 graines × 10 ans apparié, **40/40 parties
    saines**, `water_site_catalog=0` (historique) contre `=1` (catalogue).
    Lecture au test des signes d'abord :

    | métrique | OFF (`0`) | ON (`1`) | écart | signes (OFF) | p |
    |---|---:|---:|---:|---:|---:|
    | **`n_stations`** | 93,5 | 84,5 | **+10,6 %** | **15/20** | **0,041** |
    | `n_station_ratings` | 106,3 | 97,3 | +9,2 % | 14/20 | 0,115 |
    | `n_vehicles` | 192,1 | 181,0 | +6,1 % | 11/20 (1 nul) | 0,82 |
    | `profit_year` | 2 714 331 | 2 536 495 | +7,0 % | 12/20 | 0,50 |
    | `company_value` | 15 973 360 | 15 354 327 | +4,0 % | 12/20 | 0,50 |
    | `performance_history` | 824,0 | 802,0 | +2,8 % | 13/20 | 0,26 |
    | `median_station_rating` | 161,5 | 155,1 | +4,1 % | 10/20 | 1,00 |
    | `profit` (trimestre) | 692 041 | 661 045 | +4,7 % | 7/20 | 0,26 |

    ❌ **`water_site_catalog=1` NON ADOPTABLE, et le défaut 0 est confirmé.** Aucune métrique de
    valeur n'est significative dans un sens ou dans l'autre (12/20 sur la valeur et le profit
    annuel, p = 0,50 ; le profit trimestriel va même **dans l'autre sens au signe** — ON gagne
    13/20 pour une moyenne inférieure, p = 0,26 : deux ou trois graines portent la moyenne, la
    mise en garde [[banc_monograine_insuffisant]] jouant ici sur 20 graines). Mais la
    **seule métrique qui passe le seuil est un coût** : −10,6 % de gares, 15/20, p = 0,041 — et
    c'est la métrique n°1 du projet. Le catalogue **paie son scan en volume sans rien rendre**,
    exactement comme le disait le diagnostic 5×6 ; le banc long le confirme en atténué (le 5×6 le
    voyait à +181 % de valeur pour l'historique, la version longue ne retient qu'un coût de
    volume).
    🔑 **Cohérent avec l'hypothèse déjà écrite ci-dessus** : le scan reste injecté dans le canal de
    décision général avant qu'une paire eau existe, donc il déplace l'horloge de décision des dix
    tâches (même mécanique que C48) pour un mode qui ne produit rien.
    📌 **Sort du code, décidé le 2026-09-10** : la branche expérimentale (`water_site_catalog`,
    `water_discovery_real_fronts`, `WATER_MAX_SITE_TILES`, `WATER_MAX_SITES_PER_TOWN`, curseur
    persistant + `Save`/`Load` du catalogue) est **commitée à défaut 0**, pas supprimée : c'est la
    moitié « lecteur de catalogue » de l'architecture visée ci-dessus, et elle est mesurée. Elle ne
    devient réutilisable que **le jour où la découverte passe dans une tâche dédiée** — la
    rebrancher telle quelle dans le portefeuille est déjà réfutée deux fois.
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
