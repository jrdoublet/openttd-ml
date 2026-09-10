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
  `build_failed = 1 795` sur 5 graines × 6 ans (`results/diag_constants_binding_6y_5seeds_v2.json`,
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
