# Liste des tâches

Backlog du projet depuis la bascule vers `OpexAI` (2026-08-28). Les tâches faites sortent de cette
liste ; l'historique reste dans les journaux `docs/journal_*.md`.

---

## 🔴 Où en est vraiment OpexAI (mesuré le 2026-09-01) — À LIRE AVANT TOUT LE RESTE

**OpexAI perd contre AAAHogEx, très largement, et ce document contient plusieurs passages plus
anciens qui donnent l'impression inverse.** Mesure de référence actuelle :
`docs/bench_1v1_3y_1aeefe1_20seeds.json` — 20 graines × 3 ans, départ 1970, lecture appariée,
0 échec de script :

| métrique | écart apparié OpexAI vs AAAHogEx | graines gagnées |
|---|---:|---:|
| `company_value` | **−87,8 %** (602 750 £ contre 4 947 586 £) | **0/20** |
| `profit_year` | **−91,5 %** | **0/20** |
| `performance_history` | −71,0 % | 0/20 |
| `median_station_rating` | −12,0 % | 0/20 |

Décomposition : `8,5 % de profit = 12,4 % de volume × 68,6 % de rendement unitaire`. Donc **~85 %
de l'écart vient du volume** (8× moins de véhicules et de gares) et ~15 % du rendement par
véhicule. La note de gare presque au niveau ne veut PAS dire que l'IA est presque au niveau.

Goulot identifié, et ce n'est **pas** la trésorerie : avec ≥300 k£ en caisse, OpexAI ne construit
rien dans **61,2 %** des transitions mensuelles, contre 2,8 % chez AAAHogEx ; 19,2 mois actifs sur
36 contre 32,4 ; 9,6 mois entièrement figés. AAAHogEx passe même *plus* de mois sous 50 k£ que nous
(14,6 contre 13,55). Le goulot est le **débit du contrôleur** — sélection, planification et
exécution des projets.

### 🧭 Où mène la piste au 2026-09-03 au soir

Journée de mesure : `air_hub_fix` adopté (défaut de type, §0 octovicies), `tree_planting` infirmé
une seconde fois (D1), `air_demand_cap` et `air_demand_plan` **tous deux rejetés** (§3 undecies
bis, §0 trigesies), lecture d'AAAHogEx sur le dimensionnement aérien (§0 novemvicies).

**Historique au 2026-09-03 : l'item de tête était A1**, le dénominateur du classement dépendant de
la ressource rare. Trois mesures indépendantes y convergeaient et, à 10 ans, 18 graines sur 20
passaient le test `_IsRich` d'AAAHogEx.

**Décision du 2026-09-07 : ne pas implémenter A1 sous cette forme.** L'approche par délai de la
ressource dominante — ROI quand l'argent manque, profit par temps de VM quand les opcodes mordent,
profit brut quand les deux abondent — reste techniquement cohérente, mais elle est trop proche de
l'aiguillage pauvre/riche d'AAAHogEx. OpexAI ne doit pas converger vers sa doctrine pour combler
l'écart. La proposition et ses prérequis sont archivés dans `docs/journal_2026-09-07.md` ;
`tension_scoring` et `shadow_pricing` restent à 0. **C38 a depuis été mesuré et rejeté ; le
prochain candidat est C39.**

### 🔍 Détail archivé (2026-09-08) — pourquoi les prix d'ombre (C35) n'ont pas marché, et ce qu'il
faudrait pour que ça marche

Réponse détaillée à la question « pourquoi shadow_pricing a-t-il échoué, et quel est le cadre
théorique correct ? ». Trois strates de causes, à ne pas confondre entre elles.

**1. Échec empirique mesuré (C35.3, `docs/bench_c35_3_shadow_pricing_3y.json`, 2026-09-05).**
Score officiel **+29,4 pts** (357,6 vs 328,2, 3/5 victoires), note de gare **+13,5 pts**, réseau
plus étendu (+7,6 gares), résilience spectaculaire sur la graine aride 2026 (+166 % valeur,
+114 % profit, +138 pts score) — **mais valeur moyenne −11,2 % et profit −25,6 % sur les cartes
riches.** Mécanisme identifié (C35.4, `journal_2026-09-05.md` §0 trenonagies point 7) :
`OpexKnapsackComputeBound` (`projects.nut:468`) calcule bien un vrai prix d'ombre pour le capital
— le ratio profit/capital du candidat critique dans le tri par densité, la borne de Dantzig
classique sur un sac à dos fractionnel. Mais la généralisation aux 4 ressources (capital, opcodes,
slots véhicules, foncier) résout **quatre relaxations 1D indépendantes sur tout le vivier de
candidats**, pas sur la décision réelle du cycle (`portfolio_max_batch=1`, alternatives modales en
conflit sur un même O-D). Une ressource peut donc recevoir un prix strictement positif parce que
le vivier hypothétique la sature, alors qu'aucune décision réalisable de ce cycle ne la sature. Les
quatre taxes s'additionnent sans coordination → **triple taxation** sur les cartes riches (plusieurs
contraintes semblent actives ensemble sans l'être réellement), effet inverse sur les cartes pauvres
(une seule contrainte compte vraiment, d'où le +166 % sur 2026). `shadow_pricing` reste à 0 pour
cette raison précise — pas une hygiène de réglage, un défaut structurel identifié et non corrigé.

**2. Bugs d'implémentation trouvés ensuite** (revue de code 2026-09-06/07,
`journal_2026-09-07.md`, section « étape 4 : tension et prix d'ombre »). Même la théorie juste
serait cassée par le code livré :
- 🔴 **Mélange de scores dans des contextes et unités différentes.** Après le premier chantier,
  `portfolio_cache` (C36.1) recopie l'ancien `tensionScore` des candidats conservés (coût réduit
  £/an) à côté du score neuf des candidats régénérés (formule continue sans unité) —
  triés ensemble comme si c'était comparable (`projects.nut:1000-1108`). Sous `shadow_pricing`,
  le chemin incrémental ne rappelle même jamais `OpexTensionComputeShadowPrices()`
  (`projects.nut:1250-1311`).
- 🟠 **`moneyFlow` réintroduit les dépenses de chantier passées** dans un calcul censé ne
  représenter que les engagements futurs (`tension.nut:125-131`, `GetQuarterlyIncome +
  GetQuarterlyExpenses`), ce qui peut rendre la tension infinie juste après un investissement —
  précisément la réaction retardée que le code dit vouloir interdire.
- 🟡 **`capitalBudget = 0` est remplacé par une valeur positive** (`ctx.moneyAvailable` ou 1000,
  `tension.nut:535-540`) dans le calcul du dual, donc le prix d'ombre peut annoncer que l'argent ne
  mord pas exactement quand aucun capital n'est mobilisable.
- 🟡 **154 lignes mortes** de l'ancien régime macro rejeté (`OpexTensionMacroRegime`,
  `OpexProjectScoreForRegime`, `tension.nut:311-472`) restent en place, sans appel mais trompeuses
  pour la maintenance.

Aucun de ces bugs n'a été corrigé. Ils s'ajoutent à C35.4, pas à sa place.

**3. Le cadre théorique correct** (`journal_2026-09-05.md` §0 trenonagies point 4-6). Un prix
d'ombre valide est le **multiplicateur de Lagrange** de la contrainte $r$ dans le programme
**réellement résolu à chaque cycle** — pas dans une relaxation artificielle du vivier entier.
Conditions nécessaires, aucune actuellement remplie ensemble :

1. **Dualiser le vrai problème.** Sac à dos 0/1 multi-contraintes (capital, opcodes, slots,
   foncier) avec **conflits** (alternatives modales exclusives sur un même O-D) et **débit
   unitaire** (`portfolio_max_batch=1`, bientôt dynamique avec C38) — jamais quatre relaxations 1D
   séparées sur un ensemble de candidats qui ne seront jamais tous choisis ensemble.
2. **Respecter la complementary slackness** : $\lambda_r > 0$ **seulement si** la contrainte $r$
   est effectivement saturée par la solution du cycle en cours. C'est exactement la condition que
   C35.3/C35.4 viole.
3. **Corriger le biais de prédiction avant, pas après** — voir D4 ci-dessous. En ratio, une
   surestimation du profit se compense en partie entre numérateur et dénominateur ; en coût réduit
   (`profit − Σ λ_r a_ir`), le profit est au numérateur nu.
4. **Se prémunir contre la surestimation des λ** (problème classique du sous-gradient
   lagrangien) : si les λ sont surestimés, tous les coûts réduits deviennent négatifs et plus rien
   ne se construit — il faut un repli sur le profit brut ou un facteur d'amortissement.

La plomberie de base existe déjà (`OpexKnapsackComputeBound` fait un dual correct pour le capital
seul). Ce qui manque n'est pas le calcul, c'est la **coordination jointe des quatre duaux sur le
problème réel avec conflits** — c'est-à-dire C35.4, jamais fait.

**4. D4 — le prérequis prédiction est fait, mais seulement pour un mode.** `D4` (recalibrage
physique de l'estimateur **routier passagers**, `journal_2026-09-05.md` §0 quattuornonagies, banc
10 ans × 5 graines, 1980 enregistrements) est **fait et validé le 2026-09-05** : ratio revenu
réel/prédit **0,31 → 0,94**, profit réel/prédit **0,13 → 0,93**, part sous la moitié écrasée
**83 % → 2 %**. Le texte source précise explicitement : *« sans jamais toucher au rail fret ni à
l'aérien »*. Portée réelle :

| mode | biais mesuré | statut |
|---|---|---|
| pax routier | 0,31–0,55 avant D4 | ✅ corrigé par D4 (2026-09-05) |
| fret | ~0,98 (2026-08-28) | déjà correct, rien à faire |
| pax rail | corrigé par la traction (§0 bis, `4a8e15e`) | déjà correct |
| aérien | **1,16 à 1,48** (sur-performe sa prédiction) | ❌ jamais corrigé, sens de biais opposé |

D4 lève donc le blocage précis identifié §0 trenonagies point 6.1 (le pax routier était le mode qui
mentait le plus dans le sens dangereux — sur-optimiste). L'aérien reste biaisé dans l'autre sens
(sous-optimiste), ce qui est moins dangereux pour un coût réduit (ça pénaliserait l'air, pas
l'inverse) mais reste non corrigé si quelqu'un rouvre ce dossier.

**Conclusion : même avec D4 acquis, rien ne relance `shadow_pricing` tel quel.** Il resterait à
rouvrir C35.4 (coordination jointe des duaux) et les 4 bugs de contexte de la revue 2026-09-06/07,
ce que la décision stratégique du 2026-09-07 (ci-dessus) ferme explicitement — le motif de
l'abandon final n'est pas technique (les blocages techniques restent d'ailleurs non résolus, pas
prouvés insurmontables), c'est le refus de faire converger OpexAI vers la doctrine pauvre/riche
d'AAAHogEx. **Ne pas rouvrir cette piste sans une décision explicite de l'utilisateur sur ce point
précis.**

### Comment lire les chiffres de ce document sans se tromper

1. **Un banc à 5 graines ne tranche rien**, et un banc **à 1 an** encore moins : AAAHogEx monte en
   puissance lentement, donc le battre à l'an 1 ne dit rien sur 3 ans. Plusieurs sections
   ci-dessous annoncent des victoires sur ce type de banc — elles sont **contredites** par la
   mesure 20 graines × 3 ans ci-dessus. Elles sont conservées comme historique, pas comme preuve.
2. **Plancher de détection du banc à n=20** : ~15 % sur `company_value`, ~12 % sur
   `performance_history`. Sous ça, un résultat non significatif ne prouve **pas** l'absence d'effet.
3. **Contre AAAHogEx, `performance_history` est inutilisable** (saturée chez lui, CV 0,5 %). Seuls
   `company_value` et `profit_year` parlent. Entre deux variantes d'OpexAI, c'est l'inverse.
4. **Une valeur absolue sans l'adversaire sur les mêmes graines ne veut rien dire.** « Valeur
   moyenne 1,40 M£ » n'est pas un résultat tant qu'on ne sait pas ce qu'AAAHogEx fait sur ces
   graines-là (il fait ~4,9 M£ à 3 ans).
5. **« Solvabilité 100 % » n'est pas une performance** : ne pas faire faillite est un plancher, pas
   un objectif. Voir l'ordre des objectifs ci-dessous.

---

## 🆕 Candidats identifiés le 2026-09-06 (avant la revue de code / A1)

Deux idées initialement posées en discussion avant l'étape 3 de
`docs/revue_code_2026-09-06_plan.md` (portefeuille/sac à dos). C38 est désormais close ; C39
reste à trancher indépendamment.

- ❌ **C38 — Batch de portefeuille dynamique par filtre + re-classement, au lieu d'un plafond
  fixe — implémenté, mesuré et rejeté le 2026-09-07.** `portfolio_max_batch` (plafond fixe 1 à 8) a été **mesuré et rejeté**
  (`docs/journal_2026-09-02.md` §0 vicies : −3,8 % valeur, **11/20 graines en nuls exacts**). Le
  mécanisme identifié à l'époque : (a) un passage réussi régénère de toute façon tout le
  portefeuille, donc empiler N projets dans un seul passage fusionne des cycles au lieu d'en
  ajouter ; (b) le batch ne dépassait jamais 2 même à plafond 8, parce que `capitalBudget` est
  figé à la génération et que la caisse était vidée entre deux passages par des tâches
  concurrentes (l'aérien avait alors son propre `maxBatch` séparé, hors comptabilité du
  portefeuille). Depuis, **C36.2 a fait disparaître la cause (b)** : `air_portfolio=1` (défaut
  adopté) désactive la tâche aérienne dédiée et fait passer l'aérien par le **même** appel de
  portefeuille (`main.nut:4631-4636`) — donc plus de tirage de caisse hors comptabilité de ce
  côté-là. Reste la cause (a).

  Proposition : remplacer la boucle `while (builtCount < maxBatch)` par une boucle qui, après
  chaque construction réussie, (1) retire le projet construit et les candidats devenus invalides
  (déjà fait par `OpexIncrementalCandidateStillValid`, cf. `portfolio_cache`), (2) recalcule la
  trésorerie mobilisable réelle (`AICompany.GetBankBalance` + emprunt disponible, pas un
  instantané figé), (3) re-classe le reste du vivier sur ce budget frais, et continue tant qu'un
  projet finançable reste — pas de N fixe. C'est le pendant, à l'intérieur d'un seul passage, de
  ce que `portfolio_cache` (C36.1) fait déjà entre deux passages.

  ⚠️ **Ne pas reproposer un plafond fixe plus grand** — c'est exactement la piste rejetée. Mesurer
  la nouvelle version contre le défaut actuel (combo intégral + `air_portfolio=1`), pas contre le
  vieux banc de 2026-09-02 qui datait d'avant C36.2.

  **Préparation d'implémentation — 2026-09-07.** C38 doit être un réglage isolé
  `portfolio_dynamic_batch`, défaut `0`. À `0`, `_tryBuildProjects()` conserve littéralement son
  passage actuel et `portfolio_max_batch=1`; aucun re-classement ou appel d'API supplémentaire ne
  doit être payé. À `1`, le plafond fixe ne décide plus de l'arrêt. Le passage devient une petite
  machine d'état :

  1. élire le premier projet finançable du portefeuille courant ;
  2. tenter ce projet une seule fois et mémoriser son identité dans un ensemble local
     `attempted`, afin qu'un refus non quarantainé ne puisse pas boucler ;
  3. après un succès, recalculer immédiatement le capital mobilisable réel (caisse + emprunt
     encore disponible − réserve), filtrer le vivier avec `OpexIncrementalCandidateStillValid`,
     puis rejouer `OpexReselectProjects` sur ce budget frais ;
  4. continuer tant qu'un projet non tenté reste finançable ; arrêter sur vivier vide, balayage
     sans succès, recherche rail A* suspendue, ou budget d'opcodes de sécurité atteint.

  Le rail reprenable impose de conserver l'état logique du batch (`attempted`, nombre construit,
  budget initial) entre `_startRailSearch()` et `_consumeRailSearch()`. Une recherche `pending`
  rend la main ; elle ne doit ni être comptée comme un échec, ni autoriser un deuxième projet rail.
  À son retour, succès ou abandon déclenche le même filtre + re-classement que les constructions
  synchrones. En revanche un arrêt volontaire du batch clôt l'état : le cycle suivant repart d'un
  portefeuille normal, sans liste noire persistante.

  **Invariants à préserver :** une identité O/D/mode n'est tentée qu'une fois par batch ; la caisse
  est relue après chaque mutation ; les plafonds annuels par mode restent applicables ; aucun plan
  rail déjà calculé n'est réutilisé après une autre construction ; les plans air/eau repassent leur
  préflight vivant ; les abandons alimentent toujours C22/C33.3 ; `IB|...|B<n>` reste la source de
  vérité du nombre construit. Ajouter un événement `DYNAMIC_BATCH` avec `action=continue|stop`,
  `reason`, `built`, `attempted`, `budget_before`, `budget_after` et `remaining`.

  **Découpage recommandé :** (1) extraire un helper unique de capital mobilisable ; **fait le
  2026-09-07 :** `OpexAvailableCapital()` centralise `caisse + emprunt disponible − réserve`,
  borné à zéro, et remplace les cinq duplications de génération, re-sélection, cache et
  rafraîchissement. Cette extraction est volontairement neutre : aucun réglage C38 n'est encore
  lu et le batch reste unitaire. (2) extraire du grand `for` une tentative qui retourne `built`,
  `pending`, `rejected` ou `no_candidate` ; **premier sous-lot fait le 2026-09-07 :** le rail est
  sorti dans `_tryBuildRailProject()`. Son résultat explicite laisse le balayage traiter la
  suspension A* sans ambiguïté, et restitue aussi la liste de refus pour préserver le journal.
  Les sous-lots eau, flotte, air et route sont sortis dans leurs tentatives synchrones le
  2026-09-07 : l'étape 2 est terminée. Le balayage ne possède plus les chantiers par mode ; il
  consomme uniquement les résultats `built`, `pending`, `rejected` ou `no_candidate`, met à jour
  le compteur et conserve l'ordre historique des refus dans le journal ;
  (3) ajouter l'état C38 et le filtre/re-classement, défaut `0` ; (4) seulement ensuite écrire le
  banc. Ne pas mélanger C38 avec C39, A1 ou une modification du score : le contraste doit mesurer
  exclusivement la cadence de consommation d'un même vivier.

  **Étape 3a — fondation (2026-09-07).** Le réglage booléen
  `portfolio_dynamic_batch` est exposé, défaut `0`, lu une fois au démarrage et accepté par
  `sweeps/bench_v2.py`. `_dynamicBatch` réserve l'état qui devra survivre à une suspension A*.
  Le réglage est encore inerte : les smokes du défaut et du bras `=1` passent tous deux avant le
  raccordement de la machine de batch.

  **Validation avant adoption :** diagnostic 5 graines × 6 ans avec `decision_log=1`, qui doit
  montrer des batches `built > 1`, zéro répétition d'identité et des motifs d'arrêt bornés ; puis
  banc apparié 20 graines × 10 ans, `portfolio_dynamic_batch=0` contre `1`, sur les défauts du
  commit courant. Rejeter si le mécanisme reste presque toujours inerte, réduit significativement
  valeur/profit, augmente les erreurs de script, ou reproduit la baisse de volume du batch fixe.

  **Verdict.** L'implémentation complète garde une identité par projet, relit
  `OpexAvailableCapital()`, revalide le même vivier, appelle `OpexReselectProjects()`, survit au
  rail suspendu et s'arrête sur budget d'opcodes ou 64 tentatives de sécurité. Le diagnostic
  5×6 est fonctionnel : 0 erreur, `max_built=2..6` et batches multiples sur les cinq graines
  (`docs/diag_c38_dynamic_batch_6y_5seeds.json`). Mais le banc apparié 20×10 est nettement
  défavorable (`docs/bench_c38_dynamic_batch_10y_20seeds.json`) : contre le bras dynamique, le
  défaut gagne 19/20 graines en valeur et 17/20 en score et profit annuel ; le dynamique vaut en
  moyenne 7,44 M£ contre 11,63 M£ (−36,0 % brut), produit 1,55 M£ contre 2,01 M£ de profit annuel
  (−22,7 % brut), 142,2 contre 176,0 véhicules et 73,4 contre 85,0 gares. Les différences
  appariées en faveur du défaut sont +56,3 % valeur (t≈5,98), +13,1 % score (t≈4,17), +29,4 %
  profit annuel (t≈3,22). La note médiane seule est légèrement meilleure pour le dynamique
  (+0,5 %). Le mécanisme n'est donc ni inerte
  ni instable : il accélère réellement les batches, mais cannibalise la trajectoire économique.
  `portfolio_dynamic_batch` reste à `0` par défaut ; ne pas l'activer sans nouvelle hypothèse.

  ### 🔬 Post-mortem C38 (2026-09-08) — pourquoi ça a échoué, et par où reprendre

  Deux faits cadrent tout le diagnostic et écartent les explications faciles. **Le mécanisme
  n'est pas inerte** (6 à 18 batches multiples par partie, `max_built` 3 à 6). Et **la note de
  gare médiane est légèrement meilleure** sous C38 (167,2 contre 166,3), avec une CV plus basse
  (1,41 % contre 1,74 %). Ce n'est donc pas « il construit n'importe quoi » : c'est « il construit
  moins ». Le déficit est purement en volume (−19,2 % véhicules, −13,6 % gares) — exactement la
  métrique que C38 devait augmenter. La CV explose par ailleurs : valeur 27,4 → 36,6 %,
  `performance_history` 5,1 → **14,9 %**.

  **Raison 1 — le batch dégénère en balayage quasi exhaustif du vivier** *(vérifié dans le code)*.
  `attemptLimit = PROJECT_TOP_K`, et `PROJECT_TOP_K = 64` (`projects.nut:16`). C38 ne remplace donc
  pas un plafond de 1 par un plafond adaptatif : il le remplace par **64**. Le « pas de N fixe » de
  la spec s'est traduit par N = tout le vivier. Le diag le confirme : **62 tentatives pour 4
  constructions** (graine 999), 51 pour 6 (graine 42), 49 pour 3 (graine 2026). Taux de réussite
  8 à 23 %.

  **Raison 2 — c'est l'opcode qui ferme le batch, pas l'épuisement du vivier** *(vérifié au diag)*.
  Motifs de clôture agrégés sur les 5 graines : `opcode_budget` **52/112 (46 %)**, `rail_pending`
  41/112 (37 %), `no_financeable` seulement **15/112 (13 %)**, `no_success` 4/112. Le batch ne
  s'arrête pas parce qu'il a fini son travail, il s'arrête parce qu'il a brûlé le débit du tick.
  Sous la philosophie flux (10 k opcodes/tick, non reportables, cf. [[philosophie_opcodes_ressource]]),
  chaque tentative ratée est un tick où rien ne se construit. **C38 a augmenté le coût en opcodes
  par décision**, alors que le goulot déclaré du projet est précisément le débit du contrôleur.

  **Raison 3 — le filtre de finançabilité ment dès la première construction** *(hypothèse forte,
  cohérente avec le code et une mesure existante ; à confirmer au journal de décision)*.
  `OpexDynamicBatchReselect` re-classe via `OpexReselectProjects(projects, capitalBudget)` sur le
  capital **modèle** du candidat ; le devis réel n'arrive que pendant la tentative. Or la revue du
  2026-09-06 l'avait déjà noté (§5 item 4 🟠, « le devis réel rail protège la trésorerie, pas le
  classement économique ») et le rail est mesuré à **1,7× son prix modèle**
  ([[opexai_prix_rail_terrain]]). Caisse pleine, l'erreur de 70 % ne mord pas ; caisse vidée par la
  première construction, **toutes** les décisions suivantes tombent dans la bande d'erreur : le
  re-classement rend des dizaines de projets « finançables » qui échouent un par un au devis réel.
  C'est exactement la signature observée aux raisons 1 et 2.

  **Raison 4 — un cycle vaut par son observation, pas par son re-classement** *(structurel)*. La
  spec supposait que le coût d'un passage unitaire était le re-tri. Entre deux passages mensuels il
  se passe autre chose : les villes grandissent, le fret s'accumule, la ligne construite commence à
  produire, les notes de gare bougent. Six constructions dans un même passage sont décidées sur
  **une seule observation du monde**, seule la caisse étant rafraîchie — six décisions sur
  information gelée au lieu de six décisions informées. C'est la même cause que le rejet du plafond
  fixe (« fusionner des chantiers réduit le nombre de cycles de décision ») : C38 croyait ne laisser
  que la cause (a) après C36.2, mais **(a) était la cause dominante** et C38 ne l'a pas traitée.

  **Raison 5 — la valeur d'option de la trésorerie est dépensée.** Vider la caisse en un passage
  supprime la capacité de saisir le mois suivant un meilleur projet (nouvel avion disponible, ville
  qui franchit un seuil). Cadre : investissement irréversible sous information qui arrive ⇒
  l'optimum investit **moins** que le NPV myope (valeur d'option d'attente, Dixit–Pindyck). Le cash
  laissé par `batch=1` n'est pas de l'oisiveté, c'est une option. Cohérent avec l'explosion de la
  CV : C38 rend la trajectoire bien plus dépendante du hasard des premiers mois.

  #### Perspectives, par rapport coût/information

  **P1 — corriger le devis avant toute reprise du batch** (prérequis, pas variante). Faire porter le
  filtre de finançabilité sur un capital corrigé du biais **par mode** (rail ×1,7 déjà mesuré), ou
  sur le devis réel quand il existe. C'est la doctrine D4 — recalibrage physique par mode, jamais de
  multiplicateur global — appliquée au **capital** au lieu du revenu. Gain indépendant de C38 :
  améliore aussi le classement du chemin par défaut et ferme un 🟠 de la revue jamais corrigé.
  Mesurable seul.

  **P1.1 — supprimer le facteur rail ×1,7 au profit d'un devis physique avant l'élection**
  (prérequis de pérennisation de P1). Le facteur est aujourd'hui une valeur historique affirmée dans
  le backlog et le journal du 2026-09-04, mais son artefact source
  `docs/opexai_prix_rail_terrain` n'est plus présent : il ne doit donc pas devenir une constante de
  modèle durable. Concevoir un passage en deux étages : (1) préfiltre économique bon marché ; (2)
  pour les seuls rails encore compétitifs, calcul du tracé puis `AITestMode`/`AIAccounting` avant le
  filtre de finançabilité et la réélection. Le devis obtenu devient `quotedCapital` du candidat et
  remplace toute correction empirique. Mesurer séparément le coût d'opcodes, les ratios
  devis-réel par mode et l'effet apparié de `capital_calibration=0` contre le devis physique ; ne
  pas étendre le devis anticipé à tous les candidats sans borne d'opcodes. Tant que P1.1 n'est pas
  fait, ×1,7 reste un repli temporaire rail-only, jamais une règle globale.

  **Implémentation (2026-09-08), non adoptée.** `rail_prequote=1` lance, avant l'élection, un
  `OpexPlanRailRoute` puis le même devis `AITestMode`/`AIAccounting` que le constructeur pour au
  plus les deux meilleurs candidats rail sans `placeJoin`, avec un plafond de 2 500 itérations par
  devis. Le montant est porté dans `quotedCapital`, appliqué à `capital` avec
  `capitalIsActual=1`, puis lu par le filtre de finançabilité ; le plan est jeté, afin de ne pas
  réutiliser un tracé potentiellement périmé au chantier. Un échec ou un join garde le repli ×1,7.
  `P1_1_QUOTE` et `P1_1_QUOTE_SUMMARY` journalisent les ratios et opcodes. Le diagnostic
  5 graines × 6 ans est sain (0 erreur / 0 faillite,
  `docs/diag_p1_1_prequote_6y_5seeds.json`), mais ne constitue pas un verdict de performance : le
  réglage reste à `0` jusqu'au banc apparié requis.

  🔴 **Diagnostic comparatif fait le 2026-09-08 — verdict net, pas besoin du banc officiel.**
  `OpexAI[rail_prequote=0]` contre `OpexAI[rail_prequote=1]`, 5 graines × 6 ans
  (`docs/diag_p1_1_prequote_paired_6y_5seeds.json`) : `company_value` **−30,7 %** en moyenne
  (−18,4 / −48,8 / −34,2 / −9,7 / −42,2 % par graine, **5/5 négatives**), `profit_year` −29,6 %,
  `performance_history` −19,5 %, `n_vehicles` −39,7 %, `n_stations` −26,6 %. Magnitude 2 à 3× le
  plancher de détection (~15 %) sur les cinq graines : le signe est tranché sans test des signes,
  le banc apparié 20×10 n'aurait rien ajouté. `rail_prequote` reste à `0`.

  **Mécanisme identifié.** `OpexPrequoteRailCandidates()` est appelée dans `OpexBuildProjects()`
  — le rebuild **complet** du portefeuille, pas le chemin incrémental — et paie pour jusqu'à 2
  candidats un A\* borné (2 500 itérations) plus un vrai devis `AITestMode`, puis **jette le
  plan** (« afin de ne pas réutiliser un tracé potentiellement périmé au chantier », commentaire
  ci-dessus). Si le candidat est ensuite élu, le pathfinder repart de zéro. Ce coût était pensé
  pour un rebuild complet rare ; P3 (`event_catalog_invalidate`, adopté juste avant) rend
  justement ces rebuilds fréquents (ouverture d'industrie, fondation de ville, abandon de paire).
  Chaque déclenchement de P3 fait donc payer une recherche + un devis qui partent à la poubelle —
  une composition non anticipée entre deux des cinq leviers P1-P5, pas un bug isolé de P1.1.

  🔴 **P1.3 — garder le plan calculé, et le calculer par petits morceaux plutôt qu'en un bloc
  synchrone ; ne classer un candidat qu'une fois son trajet entièrement calculé et costé.**
  Proposition de l'utilisateur (2026-09-08), pas codée, pas mesurée. Deux volets :

  1. **Ne plus jeter le plan.** La raison du jet (staleness au chantier) est réelle mais traitée
     ailleurs dans ce code par une revalidation à l'usage, pas par le jet systématique — le même
     principe que `OpexIncrementalCandidateStillValid` pour le vivier incrémental (C36.1). Garder
     `plan` sur le candidat (`quotedPlan`), et au moment de la construction réelle, revalider
     qu'il reste applicable (quais toujours libres, tracé toujours sans obstacle nouveau) avant de
     le réutiliser ; ne recalculer que si la revalidation échoue. Coupe le double paiement de l'A\*
     sur le chemin qui aboutit, sans réintroduire le risque qui justifiait le jet.
  2. **Calculer par petits morceaux, classer seulement une fois costé** — l'idée de
     `docs/cible.md` §6 (« EXÉCUTION INCRÉMENTALE ») appliquée au devis lui-même, pas seulement à
     la construction. Au lieu de payer 2 500 itérations + un devis `AITestMode` d'un coup pendant
     le rebuild (un bloc synchrone qui vole le débit du contrôleur au moment précis où P3 le
     sollicite déjà plus souvent), fractionner le calcul en tranches réutilisant la machinerie
     existante (segments de `rail_segmented_search`/A5, état repris comme `rail_search_resumable`)
     et le brancher sur le canal de délestage opportuniste de **C41** (ci-dessous) : une tranche de
     devis avance quand l'IA n'a rien de mieux à faire de son budget d'opcodes du tick, jamais en
     bloquant un rebuild. **Le candidat n'entre dans le classement du portefeuille qu'une fois son
     devis physique complet** — jamais sur une estimation partielle — ce qui élimine par
     construction le problème du plan périmé entre le devis et l'élection : s'il est classé, son
     devis est frais par définition.

  ⛔ **Piège déjà payé deux fois à ne pas reproduire** : `rail_search_resumable` a été rejeté
  précisément parce qu'une **échéance globale posée à l'entrée** amputait la recherche au lieu de
  la redistribuer (−23,1 % puis −13,3 %/−27,5 % gares, [[pathfinder_budget_contrainte]],
  `docs/cible.md` §2.1). Toute reprise de P1.3 doit donner à **chaque tranche sa propre échéance**,
  jamais une échéance globale sur l'ensemble du devis — c'est la même leçon, pas une nouvelle.

  Dépend de C41 (le canal de délestage n'existe pas encore) pour le volet 2 ; le volet 1 (garder
  le plan + revalider) est indépendant et peut être fait seul, avant C41, comme premier correctif
  mesurable de P1.1.

  **Volet 1 implémenté (2026-09-08), non adopté.** Sous
  `rail_prequote=1, rail_prequote_keep_plan=1`, le candidat conserve `quotedPlan`. À l'exécution,
  `OpexRailQuotedPlanStillBuildable()` rejoue gares, voie et dépôt en `AITestMode`, sans A*, avant
  de remettre le plan à `OpexBuildLine`; un join tardif ou une revalidation négative le jette et
  force le chemin normal. `P1_3_PLAN` journalise `reuse` ou `invalidate`. Smoke 3×2 sain, puis
  diagnostic apparié 5×6 contre `rail_prequote_keep_plan=0` : 0 erreur et métriques exactement
  identiques sur les cinq graines (`docs/diag_p1_3_keep_plan_paired_6y_5seeds.json`). Ce dernier
  ne collecte pas les opcodes : il établit la non-régression fonctionnelle, pas encore le gain de
  débit qui déciderait de l'adoption.

  🔴 **P1.1 + P1.3 volet 1 — REJETÉS ENSEMBLE, banc officiel fait (2026-09-08).**
  `docs/bench_p1_3_keep_plan_10y_20seeds.json`, 20 graines × 10 ans, 0 échec :
  `OpexAI` (défaut livré) contre `OpexAI[rail_prequote=1,rail_prequote_keep_plan=1]`.

  | métrique | delta (défaut vs P1.1+P1.3) | t | victoires du défaut |
  |---|---:|---:|---:|
  | `company_value` | **+47,87 %** | **7,86** | **20/20** |
  | `profit_year` | +43,52 % | 10,96 | 20/20 |
  | `performance_history` | +18,47 % | 7,83 | 19/20 |
  | note de gare | +2,46 % | 2,02 | 9/20 |

  **Le défaut gagne sur les 20 graines sans exception, magnitude énorme.** Confirme et aggrave
  même le diagnostic 5×6 de P1.1 seul (−30,7 %) : garder le plan (P1.3 volet 1) **ne sauve pas**
  la régression de P1.1. C'est cohérent avec le mécanisme identifié — volet 1 n'évite que la
  double recherche pour un candidat *effectivement élu* après devis, une part mineure du
  problème ; le gros du dégât vient des devis payés à **chaque** rebuild déclenché par P3 pour des
  candidats jamais élus, que volet 1 ne touche pas. Seul le volet 2 (calcul par tranches sur le
  canal de délestage de C41, classement uniquement une fois costé) s'attaquerait à la vraie cause
  — et il reste bloqué sur C41, qui n'existe pas.

  ⚫ **P1.1 clos, faute de piste restante actionnable.** `rail_prequote` et
  `rail_prequote_keep_plan` restent tous deux à `0`. Ne pas rouvrir ce fil sans construire C41
  d'abord — toute nouvelle tentative sur le volet 1 seul reproduirait ce même verdict, la cause
  dominante n'étant pas dans ce volet.

  **P1.2 — proposition du 2026-09-08, non codée, non mesurée : rendre le « préfiltre économique bon
  marché » de P1.1 sensible au terrain, par sonde en ligne quasi droite.** Aujourd'hui ce préfiltre
  est `candidate.distance` (Manhattan/vol d'oiseau) + `RAIL_TERRAIN_FACTOR = 170` fixe
  (`economy.nut:29,247`) — **aucune lecture de terrain**, vérifié : ni `AITile.GetHeight`, ni
  `IsWaterTile/IsCoastTile`, ni aucun scan de corridor n'existe dans `ai/OpexAI` en amont du
  pathfinding rail (`candidates.nut:98-121` n'utilise que la distance). L'idée : avant de lancer
  P1.1 étape (2) (le devis physique complet, cher), parcourir le trajet direct ou quasi-direct
  tuile par tuile avec `AITile.GetHeight`/`IsWaterTile`/`IsCoastTile` (coût négligeable, pas de
  pathfinding, pas de mutation), classer chaque tuile plat/complexe (pente à franchir, eau, relief),
  et dériver du **nombre de segments complexes** — pas de leur résolution — une estimation de coût
  et d'itérations attendues bien meilleure que la distance seule, sans jamais faire tourner l'A\*
  sur ces segments.

  ⚠️ **Deux précédents à connaître avant de recoder ceci, tous deux montrent que le principe est
  valide mais jamais allé jusqu'au bout :**
  - [[ponts_tunnels_v3]] (décision 2026-08-27) : `estimated_cost`, un candidat pour ce rôle de
    « proxy de terrain gratuit », a été écarté précisément parce qu'un signal calculé *avant* le
    pathfinding **ne peut structurellement contenir aucune information de terrain** s'il n'inclut
    pas lui-même une lecture de tuiles — sa linéarité en distance (R² = 0,995) l'a confirmé. Toute
    version de P1.2 doit donc lire le terrain elle-même (via `AITile`), jamais dériver un proxy
    d'une formule économique existante.
  - Les features `corridor_water`/`corridor_height` de la campagne v3 (même mémoire) : échantillon
    de tuiles le long du corridor direct, **AUC univariée 0,72–0,76** pour prédire `PATHLIM` (eau,
    inconstructible, dénivelé) — donc un signal réel, pas nul. Mais jamais branché comme sonde
    vivante dans une IA : utilisé hors-ligne, en ML, sur les lignes déjà construites de la campagne
    v3 (`ai/TrainLineAI`, aujourd'hui gelée). **Jamais porté dans `ai/OpexAI`, jamais utilisé pour
    piloter un classement ou un budget d'itérations en jeu.** C'est donc une piste neuve pour
    OpexAI, pas une piste réfutée.

  ⛔ **Doit répondre à l'objection [[pathfinder_budget_contrainte]] avant tout code.** « Le
  pathfinder n'est pas le goulot » ; les trois voies de réduction du **coût d'exécution** du
  pathfinder sont épuisées (relever le budget ❌, redistribuer ❌ A4 −23 %, segmenter 🟡 A5 nul).
  P1.2 n'est **pas** une quatrième voie de ce type : son objectif n'est pas de rendre l'A\* moins
  cher à exécuter, c'est de rendre le **classement pré-pathfinding** plus juste (P1/P1.1), pour que
  moins de tentatives coûteuses soient lancées sur des candidats mal notés — un objectif différent,
  mais qui doit être démontré au banc, pas supposé.

  **Protocole suggéré, à écrire avant tout code de production :** (1) mesurer d'abord hors-ligne le
  coût opcodes d'un scan `AITile` le long du Manhattan pour un échantillon de candidats déjà connus
  (comparer au coût d'un A\* complet sur les mêmes) ; (2) vérifier que le nombre de segments
  complexes corrèle avec l'écart devis-modèle réel mesuré par P1.1 mieux que la distance seule ;
  seulement alors (3) le brancher comme étage 0 du préfiltre à deux étages de P1.1, jamais comme
  remplacement du devis physique complet.

  🔴 **Étapes 1+2 faites (2026-09-08), verdict : REFUTÉ tel que conçu.** `OpexRailTerrainScanProbe()`
  implémentée (`builder_rail.nut`), marche le trajet quasi-direct en L avant tout pathfinding
  (`AITile.GetSlope`/`IsWaterTile`/`IsCoastTile`, aucun A\*, aucune mutation), branchée dans
  `OpexPrequoteRailCandidates()` derrière `rail_terrain_probe` (défaut 0, lecture seule). Journal
  `P1_2_TERRAIN` apparié à `P1_1_QUOTE` par (graine, src, dst) et corrélé hors-ligne
  (`sweeps/diag_p1_2_terrain_probe.py`, `docs/diag_p1_2_terrain_probe_6y_5seeds.json`, 5 graines ×
  6 ans, n=23 paires candidat/devis) :

  | signal | corrélation avec l'écart devis/modèle |
  |---|---:|
  | `complex_segments` (pente + eau combinées) | **−0,12** — quasi nulle, **pire que la distance seule** |
  | `distance` seule | −0,23 |
  | `water_tiles` seuls | **+0,43** — à la limite de la significativité pour n=23 |

  **Étape 2 échoue : compter pente et eau ensemble dilue le signal au lieu de le renforcer.**
  Cohérent avec [[ponts_tunnels_v3]] (campagne v3 : l'eau était déjà le prédicteur dominant de
  `PATHLIM`, AUC 0,76 contre 0,72 pour le dénivelé — la pente porte moins d'information que
  l'eau). Le seul signal qui tient est **l'eau seule**, à la frontière de la significativité — une
  piste étroite qui rejoint une intuition déjà documentée, pas une découverte, et trop faible pour
  justifier une suite immédiate.

  **Étape 1 échoue aussi, et pour une raison inattendue.** `scan_opcodes_mean = 2495` contre
  `quote_pass_total_opcodes_mean = 1677` pour 2 candidats (≈838/candidat) — **la sonde coûte plus
  cher par candidat que le vrai devis A\*+`AITestMode`** sur cet échantillon. Explication probable :
  à 6 ans, les candidats prequotés sont encore courts et faciles, donc le vrai A\* converge presque
  aussi vite qu'une marche linéaire ; la prémisse « scan quasi-gratuit » suppose implicitement des
  candidats où l'A\* est cher, pas ceux qu'on observe tôt en partie.

  ⚫ **P1.2 clos, refuté tel que conçu.** Ne pas brancher en production (étape 3). Ne pas rouvrir
  sans un signal neuf — par exemple isoler l'eau seule sur un échantillon plus grand, ou mesurer
  sur des candidats plus tardifs/plus longs où l'A\* est réellement coûteux — plutôt que de refaire
  la même mesure en espérant un résultat différent.

  🔚 **Famille P1 close.** P1 (`capital_calibration`) adopté et dominant (+8,69 %, factoriel). P1.1
  (`rail_prequote`), P1.3 volet 1 (`rail_prequote_keep_plan`) et P1.2 (`rail_terrain_probe`) tous
  les trois testés et rejetés. Le seul chemin restant théoriquement ouvert — P1.3 volet 2, calcul
  par tranches via le canal de délestage de C41 — reste bloqué sur un prérequis qui n'existe pas ;
  ne pas le reprendre sans construire C41 d'abord.

  **P2 — piloter la tentative, pas la construction.** La ressource rare n'est pas le nombre de
  constructions mais le nombre de **tentatives** (chaque tentative = planification payée). Deux
  gardes, et surtout **pas** un plafond fixe : (a) abandon du batch après *k* refus **consécutifs**
  — le refus consécutif est le signal du régime d'erreur de devis ; (b) budget d'opcodes réservé au
  batch plutôt que la totalité du tick. Sans P1, P2 ne masque que le symptôme.

  **Implémentation P2 (en attente de mesure).** Sous `portfolio_dynamic_batch=1` seulement,
  `dynamic_batch_reject_limit=3` arrête après trois refus consécutifs (un succès remet le compteur
  à zéro ; un rail `pending` ne compte pas) et `dynamic_batch_ops_budget_pct=50` limite le batch à
  la moitié du tick courant. Les deux réglages acceptent `0` comme contrôle historique. Il n'y a
  plus de plafond fixe de 64 tentatives : l'ensemble local `attempted` et le vivier fini bornent la
  passe. `DYNAMIC_BATCH` publie maintenant la série de refus et le plancher d'opcodes. Mesurer P2
  contre C38+P1, jamais contre le chemin unitaire.

  **P3 — retourner l'hypothèse : plus de passages, pas des passages plus gros.** Le goulot mesuré
  (61,2 % des transitions mensuelles sans construction malgré ≥300 k£) ne se remplit pas en
  épaississant le passage — C38 vient de le prouver à −36 %. La direction opposée était pointée par
  deux constats de la revue étape 2 : item 1 🔴 « une paire abandonnée ne déclenche pas la
  réélection incrémentale par défaut », item 3 🟡 « l'invalidation événementielle ne force pas la
  reconstruction mensuelle du portefeuille ». Ce sont des défauts de **fréquence** de décision,
  pas de taille de lot ; ils sont désormais implémentés ci-dessous et restent à mesurer.

  **Implémentation P3 (en attente de mesure).** Un abandon pose `_hadAbandonsThisPass`, ce qui
  déclenche `OpexIncrementalUpdateProjects()` à la fin du passage même sans journal de décision.
  `event_catalog_invalidate=1` devient le défaut : une ouverture d'industrie ou fondation de ville
  marque le portefeuille obsolète, réveille `catalog` et `projects`, et contourne le garde mensuel
  pour appeler `OpexBuildProjects()` immédiatement. `PORTFOLIO_REFRESH` expose le motif
  `event|capital|month` au journal. Mesurer `event_catalog_invalidate=0` contre `1` sur le chemin
  unitaire P1, sans `portfolio_dynamic_batch`.

  **P4 — pollution de la mémoire d'abandon, corrigée (à mesurer).** Les gardes explicites
  `insufficient_cash` sortaient déjà sans appeler C22/C33.3. En revanche, après ce garde, les
  constructeurs air et route pouvaient encore retourner `CASH` (ou `ERR_NOT_ENOUGH_CASH`, si le
  devis était devenu trop bas) ; le chemin générique les mémorisait alors comme échecs durables.
  `OpexBuildFailureIsAbandonable()` exclut maintenant ces deux cas, dans le batch C38 **et** le
  chemin unitaire. Le journal C38 historique contient 792 refus `insufficient_cash`, aucun
  `detail=CASH`, et 47 232 occurrences de `abandoned_pair` : il ne journalise pas l'événement
  d'écriture C22, donc il ne permet pas d'attribuer ces occurrences aux refus de caisse. Mesurer
  P4 avec `abandon_memory=1`, avant/après ce correctif, sur le chemin unitaire P1 ; C38 ne doit
  être repris qu'après P1.

  **P5 — ⛔ deux pistes fermées et garde-fou appliqué.** Un seuil de réservation sur le ratio qui
  monte quand la caisse baisse — la formalisation naturelle de la raison 5 — **est** un prix
  d'ombre du capital : famille A1/`shadow_pricing`, fermée stratégiquement le 2026-09-07.
  `shadow_pricing=0`, `portfolio_dynamic_batch=0` et `portfolio_max_batch=1` restent les défauts.
  Les interrupteurs demeurent seulement des contrôles de banc ; ne pas les activer ni relever le
  plafond fixe sans décision explicite de l'utilisateur. Le plafond supérieur est déjà réfuté
  (−3,8 %, 11/20 nuls exacts).

  **Banc conjoint P1--P5 (2026-09-08).** Contrôle `HEAD` pré-P1--P5 contre le paquet courant,
  20 graines appariées × 10 ans, tous les 40 runs valides : valeur moyenne 11,63 M£ → 12,86 M£
  (**+9,62 %**, traitement gagnant 15/20), score 818,1 → 839,4 (+2,54 %, 14/20), profit annuel
  2,01 M£ → 2,18 M£ (+7,92 %, 16/20) et note médiane 166,3 → 166,7 (+0,20 %, 14/20).
  Voir `docs/bench_pstar_10y_20seeds.json`. C'est une validation du **paquet** seulement : elle
  ne permet pas d'attribuer le gain à P1, P3 ou P4 séparément ; P2 reste éteint par défaut et P5
  ne modifie pas le comportement d'exécution.

  **Banc factoriel 2³ P1×P3×P4 — attribution faite (2026-09-08).** P4 n'était pas un réglage au
  moment du banc conjoint (fonction inconditionnelle) ; exposé pour l'occasion derrière
  `abandon_memory_transient_guard` (défaut 1, reproduit bit-à-bit le comportement livré, vérifié
  au smoke). Les 8 bras tournent sur le **même dossier** `ai/OpexAI`, aucun arbre Git dupliqué.
  20 graines × 10 ans, 160 parties, **0 échec** (`docs/bench_p1p3p4_factorial_10y_20seeds.json`,
  `sweeps/bench_p1p3p4_factorial_10y_20seeds.py`).

  | facteur | Δ `company_value` | Δ `profit_year` | Δ score | t (CV) | victoires/80 |
  |---|---:|---:|---:|---:|---:|
  | **P1 `capital_calibration`** | **+8,69 %** | **+8,21 %** | **+3,28 %** | **4,70** | **59/80** |
  | P3 `event_catalog_invalidate` | +0,79 % | +1,83 % | +0,56 % | 1,76 (limite) | 54/80 |
  | P4 `abandon_memory_transient_guard` | −0,03 % | −0,11 % | +0,03 % | −0,89 | **1/80** |

  **P1 porte pratiquement tout le paquet.** Effet fort et significatif sur les 4 paires appariées
  × 20 graines, quel que soit l'état de P3 (+8,88 % à P3=0, +9,28 % à P3=1) : corriger le devis
  rail (biais ×1,7) était bien le bon prérequis, exactement la raison 3 du post-mortem C38.
  Comparaison directe des coins extrêmes (tout à 1 contre tout à 0, sur le même dossier) : +9,05 %
  valeur (15/20), +9,43 % profit (14/20) — cohérent avec le +9,62 %/+7,92 % du banc conjoint par
  diff d'arbre Git, bon signe de robustesse méthodologique entre les deux approches.

  **P3 a un effet réel mais marginal**, à la limite de la significativité (t≈1,76-1,95), et
  légèrement plus fort quand P1 est déjà actif (+0,60 % → +0,97 % de synergie, pas une interaction
  dramatique).

  🔴 **P4 est mesurablement inerte.** Sur les 4 paires appariées, **2 sont bit-à-bit identiques** :
  quand `event_catalog_invalidate=1`, activer ou non P4 ne change strictement rien, pas une seule
  graine sur 40. Le mécanisme que P4 corrige (mémoriser à tort un refus de caisse transitoire)
  semble déjà neutralisé par le rafraîchissement événementiel de P3 avant d'avoir l'occasion de
  mordre — cohérent avec 1/80 victoires sur l'ensemble du plan, un niveau d'inertie qu'on ne voit
  nulle part ailleurs dans ce document. Reste actif par défaut (aucun coût mesuré), mais ne
  justifie pas d'effort supplémentaire.

  **Conséquence : P1.1 (devis physique rail, remplacer le facteur ×1,7) redevient la suite
  logique évidente** — c'est le seul des trois leviers dont l'effet est assez fort pour mériter
  d'être approfondi. P3 mérite d'être gardé sans urgence de le pousser plus loin. P4 n'a plus
  besoin d'être défendu ni creusé.

  **Ordre suggéré, mis à jour : P1.1 devient la priorité**, pas un nouveau candidat du backlog.
  L'ancien « P1 seul au banc, puis P4, puis P3 » est **caduc** — l'attribution est faite, l'ordre
  suggéré répondait à une question maintenant tranchée.

- 🔴 **C39 — Détecter quand un rafraîchissement (catalogue, candidats, portefeuille, sac à dos)
  est réellement nécessaire, plutôt que de coupler les quatre.** Aujourd'hui chaque couche a sa
  propre règle de fraîcheur bricolée séparément : le catalogue se rafraîchit sur un cycle annuel
  fixe (`catalog` task), les candidats sont regénérés en bloc ou filtrés un par un
  (`OpexIncrementalCandidateStillValid` sous `portfolio_cache`), et le sac à dos est refait à
  chaque appel de `OpexBuildProjects`/`OpexIncrementalUpdateProjects` sans distinguer « rien n'a
  changé qui justifie un nouveau classement » de « une ligne vient de fermer, tout le paysage a
  bougé ». `portfolio_cache` (C36.1) a montré que l'incrémental peut remplacer un rebuild complet
  sans perte (cf. banc factoriel), mais seulement au niveau portefeuille. L'idée : généraliser le
  principe aux 4 couches avec un critère de staleness propre à chacune (le catalogue n'a pas
  besoin d'être refait à la même cadence que le sac à dos), pour ne payer le rafraîchissement
  cher que là où il change réellement la décision. Rejoint
  [[catalogue_churn_et_cout]] (rafraîchir richement, ne pas optimiser — donc le gain visé ici est
  la *décision de déclenchement*, pas la réduction du coût d'un rafraîchissement individuel).

  Pas de mesure, pas de code : à spécifier (quel signal de staleness par couche) avant l'étape 3.

- ✅ **C40 — Option de désactivation des nouvelles lignes bus passagers, mesurée.** Raison : elles peuvent
  cannibaliser le bassin des aéroports, alors que le fret routier et le rabattement vers les hubs
  restent complémentaires. Le réglage `road_pax_build` ne retire que les candidats
  ville-à-ville de `OpexRoadPaxCandidates` (`0`), sans couper ni camions, ni feeders, ni lignes
  existantes. Banc apparié 10 ans × 20 graines (`docs/bench_road_pax_build_10y_20seeds.json`) :
  à `0`, valeur +2,53 % et profit trimestriel +3,26 %, mais seulement 13/20 et 12/20 graines,
  respectivement ; score historique −1,73 % (10/20). Les écarts sont sous le seuil de détection,
  mais le défaut est désormais `0` afin de privilégier le profit et de préserver le bassin aérien ;
  `1` reste disponible pour les prochaines mesures ciblées.

- 🔴 **C41 — Scheduler opportuniste : découpage de toutes les tâches (catalogue, candidats,
  pathfinding, portefeuille) en micro-tâches, avec « je n'ai pas de projet intéressant, je fais
  autre chose ».** Idée retrouvée le 2026-09-08 : une architecture cible existe déjà pour ça,
  `docs/cible.md` (2026-09-03), **jamais intégrée au backlog actif ni retouchée depuis** — c'est
  pour ça qu'elle avait disparu de vue. Sa section 6 (« GÉNÉRATION D'INTENTIONS ») pose un
  « canal de délestage », armé par une **tension relative** plutôt qu'un seuil absolu, et son
  étape 6 (« EXÉCUTION INCRÉMENTALE ») pose la règle `while (GetOpsTillSuspend() > coût de la
  micro-étape suivante) { avancer } sinon Sleep(1)`, avec l'exigence que **chaque micro-étape
  porte sa propre échéance**, jamais une échéance globale posée à l'entrée — leçon tirée du rejet
  mesuré deux fois de `rail_search_resumable` (−23,1 % puis −13,3 % de valeur, échéance globale
  amputant la recherche au lieu de la redistribuer).

  **Ce qui est déjà livré, plus étroit que l'idée générale :** `preplan_queue` (§9, fait le
  2026-08-31) précalcule tracés A\*/quais/dépôts rail, mais seulement pendant les phases de
  trésorerie faible (où 87 % des opcodes étaient dormants) — un cas particulier rail-only
  déclenché par la caisse, pas un scheduler général catalogue/candidats/pathfinding.

  **Ce qui est le complément direct, déjà backlogué et non fait :** C39 ci-dessus (détecter
  *quand* rafraîchir chaque couche) répond à la moitié « quoi faire » ; C41 répond à la moitié
  « avec le temps libéré, fais quoi d'autre ». Les deux devraient être spécifiés ensemble : un
  signal de staleness par couche (C39) alimente naturellement la liste des micro-tâches
  disponibles pour le canal de délestage (C41).

  ⚠️ **`docs/cible.md` est partiellement périmé, à corriger avant toute reprise.** Son étape 1
  (« vecteur de tension, instrumentation seule », 🔄 en cours au 2026-09-03) est devenue A1 →
  `tension_scoring`/`shadow_pricing` (C35) → mesurée, puis **fermée stratégiquement le
  2026-09-07** (pas par échec technique : refus de converger vers la doctrine `_IsRich`
  d'AAAHogEx). L'étape 5 du document (« dénominateur composé, conditionné au résultat de
  l'étape 1 ») est donc caduque telle quelle. Le reste du document (étapes 0, 2, 3, 4, 6, 7 et
  les sections 5/8 de vérification API) n'est pas concerné par cette fermeture et reste
  exploitable — mais relire `docs/cible.md` en entier avant de coder, pas seulement la section 6,
  et vérifier au passage qu'aucune autre référence à la famille tension/prix d'ombre ne s'est
  glissée ailleurs dans le document.

  Pas de code, pas de mesure : à spécifier (quelles tâches sont éligibles au canal de délestage,
  comment mesurer leur coût en opcodes, comment garantir qu'une micro-tâche interrompue reste
  reprenable sans échéance globale) avant tout banc.

- 🔴 **C42 — Reprendre C17 au-delà de la sonde : transformer les offres de subvention non
  attribuées en candidats, pas seulement les mesurer.** Trouvé le 2026-09-08 en cherchant
  pourquoi ce sujet avait disparu du backlog : il n'a pas disparu, il est resté **coincé à
  mi-chemin**. `A7.3`/`C17` (`event_subsidy_probe`, `info.nut:162-169`, `main.nut:4634-4729`) est
  **fait et marqué ✅ le 2026-09-02** (`journal_2026-09-02.md`) : écoute réelle par événement —
  `AIEventSubsidyOffer`, `SubsidyOfferExpired`, `SubsidyAwarded`, `SubsidyExpired` — aucun
  sondage de `AISubsidyList` en boucle, donc le push fonctionne bien comme prévu. Mais c'est une
  **sonde en lecture seule**, réglage à `0` par défaut : elle mesure les offres et leur adéquation
  au réseau/vivier existant, elle **ne génère et ne priorise aucun candidat**. Aucun banc de
  valeur n'existe. C'est resté invisible dans `taches.md` parce que la règle du fichier retire les
  tâches faites de la liste active — la sonde est sortie parce qu'elle est faite, mais l'étape
  suivante n'a jamais été écrite comme item ouvert.

  L'étape suivante existe déjà en spécification dans `docs/cible.md` §6 (« GÉNÉRATION
  D'INTENTIONS », canal *opportuniste* : « subventions non attribuées, si temps restant >
  chantier estimé ») et §5 (« Les subventions comme opportunité datée : leur grandeur limitante
  est un temps avant fermeture »). Repli documenté si besoin d'une constante de secours :
  `180 jours`, emprunté à AdmiralAI (`road/buslinemanager.nut:232-235`), mais à dériver du temps
  de chantier estimé plutôt qu'à coder en dur.

  ⚠️ **Rappel de contexte, toujours vrai** : AAAHogEx a **0 occurrence** d'`AISubsidy` sur
  37 531 lignes — ce n'est pas un signal qu'il exploite, donc pas un terrain déjà occupé par
  l'adversaire de référence. Pas de code, pas de mesure au-delà de la sonde existante : à
  spécifier (comment une offre de subvention devient un candidat scoré, comment elle rivalise
  avec le vivier régulier sans lui voler son classement) avant tout banc.

- 🔶 **C43 / E3 — Audit de toutes les constantes en dur, jamais fait.** Retrouvé le 2026-09-08 :
  demandé le 2026-09-02, documenté en détail dans `journal_2026-09-02.md` §3 ter, référencé comme
  item **E3** dans la table d'hygiène du même journal mais **jamais marqué ✅** contrairement à
  ses voisins E1/E6/E10, et jamais synthétisé dans `taches.md` — même mécanisme de disparition
  que `docs/cible.md` et C17/C42 ci-dessus.

  **46 `const` dans `ai/OpexAI/`, contre 35 réglages exposés au banc — aucune revue systématique
  jamais faite.** Chaque constante doit être classée en trois issues : **exposer** (décisionnelle,
  le banc doit pouvoir la faire varier), **vérifier** (prétend traduire une règle du jeu, à
  confronter au source), ou **étalonner** (posée à vue, jamais mesurée). ⚠️ **Ne pas toutes
  exposer** — 46 réglages de plus, c'est 46 configurations mortes de plus, leçon déjà tirée de la
  suppression de `tree_planting`/`preplan_queue` devenus inutiles.

  **Preuve de priorité, accumulée le jour même** — six constantes révélées fausses ou inertes en
  une seule revue : `MAX_ROAD_VEHICLES = 8` (son propre commentaire dit « = 2 est la traduction
  directe de la règle du jeu ») ; `ROAD_SPEED_EFFICIENCY_PCT = 60` (justifiée contre une constante
  rail supprimée depuis) ; `PROJECT_TOP_K = 64` (jette 81,6 % des candidats acceptés, mesuré) ;
  `PROJECT_POOL_K = 128` (tronqué à 64 juste après : la moitié du vivier n'est jamais vue) ;
  `TARGET_HEADWAY_DAYS = 7` (tombe exactement sur une frontière de palier de note) ; `maxBatch = 1`
  (même pas une constante — un `local` — et c'est le plafond structurel de toute la croissance).

  **4 familles.** Plafonds (14, dont `PROJECT_TOP_K`, `PATHFINDER_MAX_COST`, `CASH_RESERVE_MAX`) ;
  planchers (13, dont `MIN_SEPARATION`, `ATTEMPT_FLOOR`, `CASH_RESERVE_MIN`) ; calibrations
  économiques (6, dont `STATION_RATING_PCT`, `TARGET_HEADWAY_DAYS`, `INFRA_LIFE_YEARS`) ; coûts
  d'opcodes (11, dont `PROJECT_RAIL_OPS_PER_ITERATION` — une erreur de dimension déjà avérée : les
  itérations route facturées au tarif du pathfinder rail).

  **Méthode proposée** (journal, non retouchée) : (1) instrumenter avant d'étalonner — compter
  combien de fois chaque plafond/plancher mord réellement, c'est ainsi que `PROJECT_TOP_K` a été
  confondu ; (2) confronter au source tout ce qui prétend traduire une règle du jeu ; (3) n'exposer
  au banc que ce qui reste décisionnel après les deux étapes précédentes.

  ✅ **Statut vérifié le 2026-09-08 : l'audit n'a jamais été fait.** Spot-check de 9 constantes de
  la liste dans le code actuel : **8 sur 9 bit-à-bit identiques** à leur valeur du 2026-09-02
  (`MAX_ROAD_VEHICLES`, `ROAD_SPEED_EFFICIENCY_PCT`, `PROJECT_TOP_K`, `PROJECT_POOL_K`,
  `TARGET_HEADWAY_DAYS`, `MIN_SEPARATION`, `STATION_RATING_PCT`, `CASH_RESERVE_MAX/MIN`). Seule
  `PROJECT_RAIL_OPS_PER_ITERATION` a bougé (2700 → 3105, recalibrée ailleurs), mais toujours pas
  exposée ni documentée comme telle.

  🔴 **Preuve fraîche que le coût de l'inaction est réel, pas théorique.** `PROJECT_TOP_K = 64` est
  exactement la cause de la raison 1 de l'échec de C38 (post-mortem ci-dessus, 2026-09-07) :
  `attemptLimit = PROJECT_TOP_K` a fait dégénérer le batch dynamique en balayage quasi exhaustif du
  vivier (62 tentatives pour 4 constructions, graine 999). La même constante, le même défaut,
  prédits par cet audit six jours avant qu'ils ne coûtent une régression mesurée de −36,0 % de
  valeur. **C38 aurait pu être évité, ou mieux conçu dès le départ, si E3 avait été fait avant.**

  Pas de code, pas de mesure au-delà du spot-check ci-dessus : reprendre la méthode proposée en
  commençant par les constantes des familles 1 et 2 déjà connues pour mordre (`PROJECT_TOP_K`,
  `PROJECT_POOL_K`, `MIN_SEPARATION`), avant d'attaquer les 40 restantes.

---

## Ordre des objectifs

1. **Maximiser le profit attendu par opcode.**
2. **Maximiser la performance de compagnie.**
3. **Maximiser les notes.**
4. **Maximiser la valeur de compagnie.**

Un objectif inferieur ne justifie jamais de sacrifier un objectif superieur. Les bancs doivent
donc etre lus dans cet ordre, et pas en prenant `company_value` comme arbitre unique.

---

## Fonctionnalités livrées le 2026-09-01 — ⚠️ livrées, PAS validées contre AAAHogEx

⚠️ **Titre corrigé le 2026-09-01.** Cette section s'intitulait « Tâches Récentes Validées au Banc »,
ce qui est faux et trompeur : aucun de ces items n'a été opposé à AAAHogEx en lecture appariée sur
20 graines. Les chiffres cités sont les valeurs **absolues d'OpexAI seul**, sans l'adversaire sur
les mêmes graines. Le banc 1v1 qui a suivi (voir le bloc rouge en tête de document) donne **0/20
graines gagnées et −87,8 %**. Ces fonctionnalités existent et tournent ; elles n'ont pas fermé
l'écart.

✅ **Multiplication des Corridors Longue Distance & Réseau Hub-to-Hub Dès 30 000 £** — Interconnexion directe des aéroports du réseau (Hub-to-Hub à coût marginal d'1 avion seul ~30k £) et extensions étoilées (Hub-and-Spoke à 1 aéroport + 1 avion ~92k £), portant le plafond de routes par grand aéroport à 12.
  ✅ **Validé isolément le 2026-09-08** — voir le bloc ci-dessous, `air_hub` : +104,7 % de valeur,
  20/20 graines, banc officiel 20×10.
✅ **Toile de Feeder Buses Satellites Vers les Hubs** — Raccordement systématique des 3 à 5 villages satellites (dès 200 habitants dans un rayon de 40 tuiles) avec ordres de transfert OpenTTD (`AIOrder.OF_TRANSFER | AIOrder.OF_UNLOAD`), saturation des lignes mères et bonus d'évaluation de +60 % ROI.
  🔴 **Réglage censé l'isoler prouvé mort le 2026-09-08** — voir le bloc ci-dessous, `feeder_enabled` :
  0,0 % d'écart, 20/20 graines bit-à-bit identiques. Le mécanisme lui-même reste non testé, faute
  de levier fonctionnel.
✅ **Montée en Flotte Agressive & Clonage Fiable** — Algorithme de redimensionnement de flotte mensuel en continu, acquisition automatique d'avions supplémentaires dès rentabilité/fonds disponibles, et fallback résilient `BuildVehicleWithRefit` + `ShareOrders`.
  ⚫ **Toujours non testable** — aucun réglage n'a jamais existé pour isoler ce mécanisme (vérifié
  dans le commit d'origine `b4ef8dd` : aucun ajout à `info.nut`).
⚠️ **Banc 1v1 Face-à-Face Multi-Graines 5 Ans** — Performance moyenne de **1 135 658 £** de valeur d'entreprise (pics à **1,72 M£** et **1,63 M£**), **331 903 £/an** de bénéfices nets ($+116\%$), flotte moyenne de **42,6 véhicules** ($+255\%$) et solvabilité **100% (5/5 sans faillite)**.
  **Ces chiffres ne comparent rien** : ils décrivent OpexAI seul, sur 5 graines, sans les valeurs
  d'AAAHogEx sur ces mêmes graines, et les pourcentages sont relatifs à une baseline OpexAI
  antérieure — pas à l'adversaire. À 3 ans sur 20 graines, AAAHogEx est à 4,9 M£ contre 0,60 M£
  pour nous. Ne pas citer cette ligne comme une victoire.

### 🔬 Retest officiel des trois items, 2026-09-08

Demandé pour tester correctement les paramètres du 2026-09-01, isolément et au seuil officiel
(20 graines × 10 ans). `docs/bench_sep01_features_10y_20seeds.json`, 3 bras, 0 échec sur 60 parties.

**`air_hub` (corridors hub-to-hub) — validé, effet énorme.**

| métrique | delta (défaut vs `air_hub=0`) | t | victoires |
|---|---:|---:|---:|
| `company_value` | **+104,7 %** | **10,22** | **20/20** |
| `profit_year` | **+133,8 %** | **13,59** | **20/20** |
| `performance_history` | +21,8 % | 6,07 | 20/20 |
| note de gare | +3,0 % | 1,42 | 9/20 |

Le plus gros effet mesuré dans toute cette campagne de bancs. Réutiliser une gare aéroport
existante pour une nouvelle destination, au lieu d'en construire deux neuves, plus que **double**
la valeur d'entreprise à 10 ans, sur les 20 graines sans exception — vérifié sur plusieurs graines
individuelles : ni faillite ni run dégradé, juste structurellement plus de véhicules et de gares.
C'était affirmé depuis le 2026-09-01 sans jamais avoir été mesuré isolément ; c'est maintenant fait.

**`feeder_enabled` (toile de feeders) — réglage mort, ne teste rien.** 0,0 % d'écart sur toutes les
métriques, les 20 graines bit-à-bit identiques entre `OpexAI` et `OpexAI[feeder_enabled=0]`. Ce
n'est pas un bug du banc : vérifié dans le code (`main.nut:5060-5064`), `feeder_portfolio=1`
(adopté depuis C32/C36.2) désactive la tâche dédiée que gate `feeder_enabled`, et génère les
feeders **inconditionnellement** par le chemin portefeuille (`OpexRoadFeederCandidates`,
`candidates.nut:1709`). Commentaire du code lui-même : « sous feeder_portfolio, le rabattement est
arbitré par le portefeuille. Laisser AUSSI la tâche dédiée active bâtirait la même ligne deux
fois ». **Le mécanisme des feeders lui-même n'a donc pas été testé** — il n'existe actuellement
aucun levier propre pour le désactiver (`feeder_portfolio=0` ne coupe pas les feeders, il bascule
juste vers l'ancienne tâche dédiée). Candidat direct au nettoyage de code mort, dans l'esprit de
E2 (`rail_refleet`/`air_starter`, §8) : `feeder_enabled`, sa lecture dans `Start()` et son entrée
`info.nut` peuvent sortir sans risque de régression, puisqu'ils ne changent déjà plus rien.

**Montée en flotte agressive** — toujours non testable, aucun levier n'a jamais existé.

---

## 1. À lire et intégrer (demandé le 2026-08-28)

À traiter comme `docs/mecanique_jeu.md` : **pas une copie du wiki, mais règle + conséquence pour la
conception**, avec ce qui est vérifié et ce qui ne l'est pas.

✅ **[Manual/Tips](https://wiki.openttd.org/en/Manual/Tips) lue et intégrée (2026-08-28)** — voir
`docs/mecanique_jeu.md` §9. La plupart des heuristiques utiles étaient déjà couvertes ailleurs dans
le document (note de gare §3, note d'autorité §7, vitesse/virages §2) ; l'apport net : ordres
partagés (`AIOrder.ShareOrders`, non exploité), boucles de gare routière pour le futur mode Route,
et une piste non vérifiée sur les avions qui diffuseraient mieux leur influence que le rail.

✅ **[Manual/Industries](https://wiki.openttd.org/en/Manual/Industries) lue et intégrée
(2026-08-28)** — voir `docs/mecanique_jeu.md` §10. La table des chaînes de production ne change
rien au code : `catalog.nut` interroge déjà l'API dynamiquement plutôt que coder les chaînes en
dur. L'apport net : (1) ✅ croissance d'une primaire = % transporté, relu en
15.3 (`ChangeIndustryProduction`, `mecanique_jeu.md` §4) — pas un terme de
classement, pas de retuning ; l'écart fret ~4-6x est réfuté ; (2)
`difficulty.economy = false` : récession **sans objet** chez nous.

✅ **[transporttycoon.net/rail1](https://www.transporttycoon.net/rail1) … [rail6](https://www.transporttycoon.net/rail6)
et [junctions](https://www.transporttycoon.net/junctions) lus et intégrés (2026-08-30)** — voir
`docs/mecanique_jeu.md` §12. Série TTD + TTDPatch, pas le wiki 15.3. Apport net : OpexAI *est*
le point-à-point que la page moque, et `JOINPATH` doit le rester tant que la jointure ne paie
pas ; `trains > 1` exige une **deuxième voie dédiée** (un convoi par chemin, plafond 2), pas
des PBS sur voie unique ; si `station_join` / `join_place`, PBS sur les approches **simples**
d'une jointure — jamais sur `TracksOverlap` ; quai déjà calé sur la rame ; les jonctions se résument à trois principes (séparer
avant de fusionner, sortie avant entrée, train+2 tuiles) — l'index Junctionairy n'est qu'un
catalogue d'images, on ne copie pas de cloverleaf. Waypoints natifs OpenTTD, utiles seulement
le jour des branches. Pré-signaux TTDPatch = path signals chez nous.

✅ **[Community/Pseudo canals](https://wiki.openttd.org/en/Community/Pseudo%20canals) lue et
intégrée (2026-08-30)** — voir `docs/mecanique_jeu.md` §13. Apport net : ce n'est pas un canal,
c'est une inondation au niveau de la mer (terraform **à sec**, ouvrir en dernier). Le trick ne
monte pas une colline ; un vrai canal existe précisément là où baisser le terrain coûterait
plus. OpexAI eau v1 ne terraform jamais ; une paire sans composante d'eau naturelle reste
ignorée. ❓ Coût opcode/argent de l'inondation vs `BuildCanal` non mesuré. **Pas de canal pour
un bateau pax.**

La liste de lecture demandée le 2026-08-28 est **vide**.

---

## 0. Le vivier de candidats : rouvert, mesuré, et **il ne paie pas** (2026-08-29, seconde tranche)

**Fait, et le mécanisme marche.** La règle « un seul raccordement par origine » n'est plus une
guillotine à la génération : une paire dont **une seule** extrémité est servie passe désormais, et
c'est `_tooClose` / `OpexFindStationJoin` qui tranche — quai joint, ou rejet. Les deux extrémités
servies restent coupées sans appel. La règle de fond est intacte : **jamais deux gares à nous sur
la même origine**. Toute la relaxation est commandée par le réglage `station_join`, donc `0`
reproduit exactement le comportement d'avant.

Graine 42, 20 ans (`docs/opex_join_20y_42.json` contre `docs/opex_road_20y_42.json`) :

| | avant | après |
|---|---|---|
| candidats classés 1984-89 | 0 à 3 | **4 à 28** |
| lignes rail | 15 | 23 |
| `station_join` tentatives / réussies | 0 / 0 | 82 / 10 |
| `company_value` | 2 391 044 | 3 385 161 |
| utilisation du budget d'opcodes | ~29 % | ~46,5 % |

**Et le banc apparié, 20 graines × 20 ans** (`docs/bench_v2_vivier.json`, bras
`OpexAI[station_join=0]` contre `OpexAI`) **dit non** :

| métrique | delta | t | graines gagnées | verdict |
|---|---|---|---|---|
| `n_vehicles` | **+37,2 %** | **5,94** | **18/20** | l'IA bâtit massivement plus |
| `company_value` | −0,3 % | −0,03 | 9/20 | nul |
| `performance_history` | +6,5 % | 1,45 | 11/20 | sous le plancher (~12 %) |
| emprunt non remboursé | 2 → 4 graines | | | dégradé |

La variance explose : de −54,8 % (graine 12345) à +330,5 % (graine 100). **On construit beaucoup
plus pour la même valeur, en immobilisant plus de capital.** C'est exactement le piège que la
graine 42 seule aurait fait manquer (cf. « banc mono-graine insuffisant »).

⚠️ **Défaut `station_join` repassé à 0.** Le code, l'instrumentation et la mesure restent ; le
comportement par défaut ne change pas tant que la cause ci-dessous n'est pas corrigée.

**La cause supposée a été mesurée, et ce n'est pas elle** (2026-08-29,
`sweeps/opex_join_bias.py`, 10 graines × 20 ans, 155 lignes rail,
`docs/opex_join_factor_20y_10seeds.json` → `docs/opex_join_bias.json`).

Le rapport brut *revenu réel / revenu prédit* semblait donner **×1,53** en défaveur des lignes à
origine servie (IC 95 % [1,23 ; 2,02]), soit exactement le facteur cherché. C'est une illusion de
composition : ces lignes sont aussi **plus longues** (distance médiane **84 tuiles contre 47**) et
**plus tardives** (1981 contre 1975). Une fois type, distance et époque neutralisés **ensemble** :

| terme | effet | IC 95 % |
|---|---|---|
| `log(distance)` | ×0,76 | [0,53 ; 1,13] |
| `origine_servie` | **×0,81** | **[0,63 ; 1,03]** |
| type `freight` | ×0,97 | [0,70 ; 1,31] |
| époque (par décennie) | ×0,98 | [0,77 ; 1,22] |

L'intervalle de `origine_servie` **contient 1**. Le double comptage de `monthly` existe peut-être,
mais il ne dépasse pas le bruit à cet effectif et **n'explique pas le verdict du banc**. Corriger
`monthly` serait traiter le mauvais terme.

### 🔴 Ce que la mesure désigne à la place : l'étage 1 s'effondre avec la DISTANCE

`profit réel / profit prédit`, première année pleine, toutes lignes confondues :

| distance | rapport médian | n |
|---|---|---|
| < 50 tuiles | **1,47** | 62 |
| 50-75 | 0,41 | 37 |
| 75-100 | 0,44 | 40 |
| > 100 | **0,00** | 16 |

Au-delà de 100 tuiles, **la ligne médiane ne dégage aucun profit** — le modèle en promettait un.
Croisé avec l'époque, les deux effets s'ajoutent : sous 50 tuiles on passe de 1,51 (avant 1980) à
0,58 (1980+) ; au-delà de 100 tuiles on est à 0,00 dans les deux cas.

**Et c'est l'explication du banc.** Rouvrir le vivier ne fournit pas des jointures courtes et
rentables : il fournit des lignes **longues**, parce que les extrémités encore libres sont loin.
La population construite passe d'une médiane de 47 tuiles à 84. L'IA bâtit donc +37 % de véhicules
sur exactement le segment où `OpexLineEconomics` se trompe le plus — d'où « plus de construction,
pas plus de valeur ».

**Ce qu'il faut faire, dans l'ordre :**

1. ✅ **Recalibrer `OpexLineEconomics` en distance** — fait par la traction (§0 bis, `4a8e15e`) :
   quai, wagons, loco et vitesse réelle, plus le `ceil` des trajets. Ce n'est pas un facteur
   empirique en distance (écarté). Sur la graine 42 après traction, `profit réel / prédit` (année
   2) ne tombe plus à 0,00 au-delà de 100 tuiles (médianes 2,40 / 1,49 / 0,89 / 0,72, n petit).
   Le classement n'est plus celui du banc vivier.
2. ✅ **Rejouer le banc apparié `station_join` sur cet étage 1** — fait
   (`docs/bench_join_after_traction.json`, paire
   `docs/bench_join_after_traction_paired.json`). Même v1, `origin_sitable=0`.

   | métrique | delta | t | graines | verdict |
   |---|---|---|---|---|
   | `n_vehicles` | **+23,6 %** | **3,50** | **17/20** | l'IA bâtit encore plus |
   | `n_stations` | **−11,9 %** | **−3,61** | 4/20 | moins de gares (réemploi) |
   | `company_value` | +5,9 % | 0,96 | 11/20 | sous le plancher (~15 %) |
   | `performance_history` | +4,3 % | 1,34 | 12/20 | sous le plancher (~12 %) |
   | emprunt résiduel | 1 → 0 | | | petit plus |
   | minimum | 1,68 M → 1,27 M | | | le plancher recule |
   | CV | 0,31 → 0,36 | | | plus dispersé |

   L'effet de construction **survit à la traction** (un peu plus petit qu'à +37,2 %, t = 5,94,
   mais toujours massif). Moins de gares pour plus de véhicules : c'est le mécanisme de la
   jointure, pas un bug. **La valeur ne passe toujours pas le plancher.** La graine 42 recule
   de 18 %. ⚠️ **Défaut `station_join` reste 0.** Le partage de bassin (§2.9.3) est mesuré et
   ne paie pas davantage. Le spread n'est pas la suite.
3. ✅ **Rendement des jointures — parallèle 1–4, mesuré, défaut 0** (2026-08-30).
   Le colle unique (offset 1) était 658/692 SITE à `nClear=0`. Offset 1–4, même
   orientation : 39 → **71** OK (5,5 % → 15,7 %), SITE 692 → 393, JOINPATH 0.
   Il reste **361** SITE au quai joint à `nClear=0` — c'est le spread, et le
   spread n'est pas la suite. 5/5 plus de véhicules, 4/5 moins de valeur (cinq
   graines, pas un banc). `docs/opex_join_parallel_20y_5seeds.json`.
4. ⚠️ Ne **pas** corriger `monthly` pour une origine servie sur la foi du chiffre brut : c'est le
   piège que cette mesure vient de désamorcer. Le partage de stock **une fois la gare jointe**
   (plusieurs lignes, même `StationID`) est un autre terme, lui encore ouvert (§2.9.3).
5. ✅ **Étape 0 + H1 porte 50 tuiles** (2026-08-30). Population
   (`docs/opex_join_pop.json`) : jointes 63 tuiles / 0,80 vs neuves 43 / 1,19.
   <50 paie (1,12) ; ≥100 : 0,07. `join_max_distance` défaut 0 ; à 50, 5 graines
   (`docs/opex_join_cap50_20y_5seeds.json`) : 29 jointures, dist. 37, D=1035.
   Coupe le vivier (véhicules − vs parallèle). **Ne bat pas `join=0`** (2 graines
   −30 %). Pas de banc n=20.
6. ✅ **H2 joindre au lieu + signaux PBS** (2026-08-30). `join_place` défaut
   **0**. Candidats depuis une gare rail OpexAI vers une origine libre
   (bande 25–75), join attaché à la génération, quai parallèle 1–4,
   `JOINPATH` dédié. PBS devant les quais joints et sur l'aiguillage
   dépôt (1 jonction / jointure : le dépôt). 5 graines
   (`docs/opex_join_place_20y_5seeds.json`) : 50 jointures, dist. 50,
   réel/prédit an 2 **−0,16**. Médiane valeur **−64 %** vs `join=0`
   (5/5, graine 100 −92 %). Le TOP_K se remplit de H2 (43–143 classés,
   7–14 OK), SITEA explose (spread au quai joint). Moins de véhicules
   **et** moins de valeur. ⚠️ **Pas de banc n=20. Pas de spread.**
   Signaux (mesure H2) : 77 OK / 128 fail / 50 junc — le PBS du dépôt passe, le
   front de quai vers la gare refuse souvent. Placement **périmé** le soir même :
   plus de signal sur l'aiguillage (item 9.4).
7. ✅ **Rejeu join + double voie** (2026-08-30). La 2e voie dédiée s'applique
   aussi à une jointure (quai voisin ignoré, `JOINPATH`). 5 graines × 20 ans
   contre `docs/opex_double_track_20y_5seeds.json` (join=0, médiane **5,73 M**) :

   | | médiane | vs join=0 | graines | jointures | DT |
   |---|---:|---:|---:|---:|---:|
   | `station_join=1` | 3,59 M | −2,14 M | 3/5 | 64/427 | 70/122 |
   | + `join_max_distance=50` | 4,43 M | −1,30 M | 1/5 | 21/88 | 52/77 |
   | `join_place=1` | 3,69 M | −2,04 M | 2/5 | 52/266 | 63/109 |

   0 `XC`/`RX`, emprunt 0, pas deux trains sur une voie. Même piège : plus de
   construction, moins de valeur. ⚠️ **Défauts 0.** Pas un banc n=20. Pas de spread.
   Preuves : `docs/opex_join_dt_20y_5seeds.json`,
   `docs/opex_join_cap50_dt_20y_5seeds.json`,
   `docs/opex_join_place_dt_20y_5seeds.json`.

⚠️ **Effet de bord à ne pas attribuer au mode route :** le rail affamé reprend la trésorerie, et
les lignes routières passent de 6 à 3 sur la graine 42. Le +9,3 % du mode route a été mesuré avec
`station_join` inerte ; il faudra le revérifier si ce réglage repasse à 1.

⚠️ **Ce que ce diagnostic dit AUSSI, et qu'il ne faut pas confondre avec l'item ci-dessus.** Le mur
de trésorerie des onze premières années n'est **pas** l'absence de réemprunt notée dans `info.nut` :
sur ces onze années **l'emprunt est déjà au maximum**. C'est le plafond d'emprunt lui-même face au
prix d'une ligne rail (82 000 à 240 000 pour 87 000 à 264 000 en caisse). La croissance précoce est
donc fixée par les bénéfices non distribués, et le seul levier est **la ligne bon marché** — ce qui
explique après coup pourquoi le mode route gagne au banc. Une hypothèse s'en déduit, **non
mesurée** : `_tryBuild` fait `break` sur la trésorerie en invoquant le « classement décroissant »,
or le classement est sur le **rapport**, pas sur le capital — un candidat moins bien classé mais
abordable n'est jamais examiné. Le préalable est d'instrumenter `candidate.capital` du `TOP_K` au
moment du `break` ; le correctif (`continue` borné plutôt que `break`) ne vaut d'être écrit
qu'ensuite.

---

## 2. Le code, par ordre d'impact mesuré

**✅ Étage 3 fait** (`ai/OpexAI/builder_rail.nut`, 2026-08-28) : 3 lignes sur 3 construites en
10 ans, 56 véhicules. Comptabilité d'opcodes branchée, rollback sur échec, réserve de trésorerie.

**Tout l'ancien blocage capital est résolu (session du 2026-08-28)** : pax (`b09f23e`), fret
(`abd641b`), `MIN_SEPARATION`/`ORIGIN_SEPARATION` (`5433518`), remboursement d'emprunt (`44e0b14`),
détection et vente des lignes fret mortes (`e884358`), exclusion d'origine + plancher de ratio
(`candidates.nut`, ce jour). Graine 42/20 ans : 3 lignes bloquées → **17 lignes**, `company_value`
1 → **2 716 098**, emprunt à **0**. Détail dans [[opexai_squelette]] et
`docs/opexai_croissance.md` §6.

**Ce qui reste, par ordre d'impact mesuré :**

1. ✅ **Écart prédit/réel du fret : retiré, c'était une fausse alerte (2026-08-28).** L'affirmation
   « ~4-6x » n'était appuyée par aucune donnée citée dans `docs/opexai_croissance.md`. En creusant :
   la mesure existait déjà, commise dans `abd641b` en même temps que le correctif du puits fret
   (`docs/opex_predict_vs_actual_postfix_freight_v2.json`), simplement jamais recroisée avec
   l'affirmation écrite ensuite. Sur les 5 lignes fret à ≥3 ans de données stables : ratio
   prédit/réel moyen **0,98** (0,79-1,30) — `STATION_RATING_PCT = 50` calibré sur le pax tient
   aussi pour le fret, sans facteur correctif propre. Les 2 ratios à 1,8-2,4x observés sont des
   lignes à 1 an de données (ligne neuve ou industrie en fin de vie), pas un biais de modèle.
   Détail dans `docs/opexai_croissance.md` §2 et §8.
2. **Ne pas enfermer la ville dans nos propres voies** — la mesure existe
   (`docs/opex_town_growth.json`, 2026-08-30) : les villes desservies n'estagnent **pas**
   comme classe. Le barème 15.3 accélère avec 1–5 gares actives. ⚠️ **Reste dernier** :
   pas de contrainte de tracé rail. Un effet local (maisons coincées par nos voies) n'est
   pas isolé.
3. ✅ **Origines épuisées dans la fenêtre `TOP_K` : résolu (2026-08-28), en deux temps.** Exclusion
   des origines déjà servies à la génération (`OpexOriginServed` dans `candidates.nut`) plutôt
   qu'au filtrage — mais **seule, cette exclusion dégradait le résultat** (`company_value`
   2 067 089 contre 2 413 587 avant, emprunt non remboursé) : une fois les bonnes origines
   épuisées, l'IA s'engageait sur des candidats marginaux qu'un `TOP_K` engorgé bloquait
   *accidentellement* avant. Ajout d'un plancher `MIN_RATIO = 500` (profit/1000 itérations) qui
   corrige : **17 lignes** (contre 15), `company_value` **2 716 098** (+12,5 % vs avant tout
   correctif), emprunt remboursé. Détail dans `docs/opexai_croissance.md` §6, y compris le
   rattrapage du cycle annuel qui remplace la fausse piste du plafond `AISign`.

4. ✅ **RÉSOLU le 2026-08-29 : `LOAN_REPAY_FLOOR` abaissé de 1 000 000 à 300 000 après banc
   apparié — voir le verdict en fin d'item.** L'emprunt n'était pas remboursé sur 3 graines / 20 — mode d'échec découvert le 2026-08-29
   par le banc multi-graines, invisible sur la graine 42.** Les graines 100 et 4096 finissent
   20 ans au plafond de **300 000** d'emprunt, la graine 8675309 à 90 000 — et ce sont exactement
   les trois pires parties de la campagne (`company_value` 719 619 / 933 323 / 1 372 258, notes
   **194-206** contre ~430 ailleurs). Ce n'est pas une nuance mais un régime d'échec qualitatif.
   Le remboursement avait été déclaré corrigé par `44e0b14` sur la seule graine 42, où il tombe
   bien à zéro : c'est précisément le biais que le banc mono-graine masquait.

   🔴 **Reformulé le 2026-08-29 par le re-baselinage (§8), et c'est plus grave que décrit
   ci-dessus.** En rejouant les mêmes 20 graines sur un arbre dont **aucune décision ne change**
   (seul le profil d'opcodes bouge), l'échec passe de **3 graines à 6**, et surtout **la liste
   change presque entièrement** :

   | | graines à emprunt non remboursé à 20 ans |
   |---|---|
   | avant | 100 (300 k), 4096 (300 k), 8675309 (90 k) |
   | après | 1 (300 k), 100 (80 k), 1024 (300 k), 65537 (180 k), 123456 (300 k), 8675309 (300 k) |

   La graine 4096 s'en échappe complètement (300 k → 0) pendant que quatre autres y tombent. **Ce
   n'est donc pas une propriété de la carte mais une instabilité latente de la trajectoire** : il
   n'y a pas « trois mauvaises graines » à diagnostiquer, il y a un régime dans lequel *n'importe
   quelle* partie peut basculer, et qui touche 15 à 30 % d'entre elles. Toute analyse qui part des
   graines nommément (« qu'y a-t-il de particulier sur 100 et 4096 ? ») est donc une impasse : la
   cause est dans la règle, pas dans la carte. `LOAN_REPAY_FLOOR = 1 000 000` reste le suspect —
   une compagnie qui ne franchit jamais le seuil ne rembourse jamais — mais il faut le tester comme
   une règle, pas expliquer trois cas.

   Ce résultat pèse aussi sur le §5 : les graines en échec portent une grande part de la
   dispersion (moyenne 1 248 532 contre 2 907 102 pour les saines), donc **corriger l'emprunt
   resserrerait le banc lui-même** et abaisserait le plancher de détection de tout ce qui vient
   après. Données dans `docs/bench_v2.json`.

   ### Diagnostic (`docs/opexai_emprunt.json`, 6 graines × 20 ans, panneaux `LB`/`LF`)

   ❌ **Une hypothèse réfutée d'abord.** `_tryRepayLoan` est appelé à `main.nut:828`, juste après
   `_tryBuild`, donc au creux annuel de trésorerie — on pouvait croire que la construction lui
   volait son argent. **Faux** : `blocked_by_floor_only = 0` sur les six graines, pas une seule
   année où le sommet passait le plancher mais pas le creux. L'ordre n'est pas en cause.

   ✅ **La cause est le seuil, seul.** La trésorerie d'OpexAI reste entre 50 000 et 400 000 pendant
   **dix à quatorze ans** : le million n'est atteignable à aucun moment de la phase de croissance.
   La règle, elle, est saine — dès que la trésorerie franchit le seuil, le remboursement part
   immédiatement et solde tout (graine 65537 : 1 751 216 en 1981 → zéro). Deux illustrations : la
   graine 123456 est restée entre 954 017 et 956 875 **cinq années consécutives**, 4,5 % sous le
   seuil (et ces cinq années sont des années *franchies*, ce qui la relie à l'item 6) ; la graine
   100 a passé vingt ans à 300 000 d'emprunt sans jamais dépasser 774 797 à un contrôle annuel.

   **Pourquoi 300 000**, sur deux mesures indépendantes : le plus gros candidat jamais bloqué faute
   de trésorerie coûte **248 106** (médiane 136 760), et la construction annuelle draine 95 172 en
   médiane, 183 101 au 90e centile. La courbe de déblocage est **plate entre 300 et 500** (même
   année sur 4 graines / 6) et descendre à 200 passerait sous le prix de la plus grosse ligne :
   300 est le genou.

   ### Verdict du banc apparié (`docs/bench_v2_emprunt.json`, 20 graines × 20 ans)

   | | plancher 1 M | plancher 300 k |
   |---|---:|---:|
   | graines à emprunt résiduel | 3 / 20 | **1 / 20** |
   | emprunt total résiduel | 900 000 | **230 000** |
   | `company_value` appariée | — | −0,17 %, t = −0,12 |
   | `performance_history` appariée | — | +1,91 %, t = +1,18 |

   Les graines 100 et 4096 passent de 300 000 à zéro et leur **note** bondit (170 → 245, 269 → 309)
   pendant que leur valeur d'entreprise ne bouge quasiment pas — exactement le comportement prévu,
   rembourser avec du cash étant neutre en valeur et ne gagnant que l'intérêt plus la composante
   « emprunt à zéro ». Les deux métriques globales restent sous le plancher de détection (~15 % et
   ~12 %) : **c'était prévu**, d'où la lecture sur `current_loan`.

   🔶 **Preuve que le changement est chirurgical** : sur 4 graines (17, 999, 2026, 8675309) les deux
   bras sont **bit à bit identiques**. Là où la trésorerie franchissait le million d'un coup,
   abaisser le plancher ne change littéralement rien — le correctif ne touche que les parties qu'il
   vise.

   ⚠️ **Reste 1 graine (42) à 230 000 SUR CE BANC.** Sur l'arbre courant elle solde tout en 1975
   (`docs/opex_reborrow_20y_42.json`). Descendre le plancher sous 300 passerait sous le coût de
   la plus grosse ligne ; l'item 8 (réemprunt) ne paie pas : le trou est vide.

8. ✅ **Réemprunt à la demande : écrit, mesuré, défaut 0 — le trou est vide** (2026-08-29, nuit).
   `OpexTryReborrow` tire le palier manquant aux quatre portes de cash, derrière `reborrow`.
   5 graines × 20 ans (`docs/opex_reborrow_20y_42.json`, `docs/opex_reborrow_20y_4seeds.json`) :
   **412 `GC`, 0 tirage `GL`, 0 `GC` avec de l'emprunt encore disponible.** Tous les blocages
   cash sont des années où l'emprunt est déjà au plafond 300 000. Dès que le remboursement
   commence, plus aucun `GC`. Le mur n'est pas l'absence de réemprunt, c'est le plafond
   d'emprunt lui-même (mur n° 1). Pas de banc apparié n=20 : ce serait mesurer un mécanisme
   inerte. Le code reste ; `OpexAI[reborrow=1]` rallume. La graine 42 à 230 000 d'emprunt
   résiduel du banc `loan_repay_floor` est **périmée** sur cet arbre : elle solde tout en 1975.

5. ⚪ **Régler `MIN_SEPARATION` : piste ÉCARTÉE le 2026-08-29, alors même que la mesure la
   désigne comme le verrou.** L'investigation de plafonnement (`docs/opexai_plafonnement.md`) a
   établi que le vivier ne meurt pas au classement mais à `_tooClose` : sur la graine 999, arrêtée
   en 1981, **les 19 candidats de 1989 sont tous rejetés — 1 par réutilisation d'origine et 18 par
   le filet physique seul**. La carte n'est pourtant pas épuisée (37 à 39 villes non desservies sur
   39 à 45). `MIN_RATIO` n'écarte que 2,7 % des paires et `TOP_K` n'en écarte aucune : les deux
   suspects initiaux sont faux.

   **Pourquoi on ne règle pas le seuil pour autant.** `MIN_SEPARATION` ne garde pas contre une
   collision de voies mais contre la **cannibalisation de bassin** (`main.nut:50`) : deux gares trop
   proches partagent leur zone de captation. L'agrandissement de gare et les jonctions (§9) ne
   suppriment pas ce recouvrement — il reste physiquement là — mais ils changent **l'action
   disponible face à lui**. Aujourd'hui « trop proche » n'a qu'une sortie possible : renoncer. Avec
   le raccordement, la même détection devient un aiguillage — se brancher sur la gare existante
   plutôt que d'en poser une seconde. Le test survit, sa branche de sortie change : `return null`
   devient `join`.

   Calibrer le seuil maintenant serait donc régler une constante dont la sémantique va changer :
   travail perdu, et pire, un seuil relâché à l'avance **masquerait** le gain de l'agrandissement en
   ayant déjà ouvert le vivier par un autre moyen. Ne pas passer de banc apparié `MIN_SEPARATION`
   avant que §9 ne soit tranché.

6. ✅ **IMPLÉMENTÉE le 2026-08-29, non commitée. Banc appairé 3 bras × 20 graines : NON CONCLUANT, voir le verdict en fin d'item.**
   **La politique d'abandon coûtait plus que tout le reste de la construction.** Mesure du
   2026-08-29 sur 4 graines : 52 lignes bâties en 57 tentatives, mais les **5 abandons absorbent
   56,5 % des opcodes de construction** — 182 M chacun contre 13,5 M pour une réussite, soit
   **13,5×**, tous au plafond dur de 60 000 itérations. Ceci ne contredit pas le §7 (la forme
   fermée du rendement marginal est bien en place) : c'est le **plafond dur** qui mord, pas la règle
   d'arrêt anticipé. À traiter avec l'item 4 — les deux sont indépendants de l'architecture de §9,
   donc ni l'un ni l'autre ne sera invalidé par l'agrandissement de gare.

   **Correctif livré**, en deux réglages indépendants pour que le banc attribue le gain à chacun :
   `pathfinder_hard_cap_k` (défaut **40**, `60` = bras de contrôle) remplace le `const
   HARD_ITERATION_CAP` de `builder_rail.nut` ; `abandon_memory` (défaut **1**) mémorise les paires
   qui ont rendu `ABND` pour ne pas repayer le plafond deux fois. Le second domine le premier :
   **3 des 5 abandons mesurés étaient le même échec rejoué** (graine 4096, 1978 puis 1981/1983/1986,
   rang 0 sur `ranked_len` 1), donc la mémoire enlève 60 % des abandons **sans perdre une ligne**,
   là où aucun réglage du plafond n'y arrive.

   **Le plafond à 40 000 vient de la mesure** : sur les 52 réussites, la plus longue a coûté 36 600
   itérations et seules 3 dépassent 20 000 (134-168 tuiles, profits prédits 23,8k / 46k / 54k). À
   40 000 on ne perd aucune réussite in-sample et on coupe ~20 % des itérations ; à 20 000 on
   économise 48 % mais on perd ces 3 lignes.

   🔴 **Piste ÉCARTÉE — et attention, la première raison publiée était FAUSSE.** Un plafond relatif
   à la distance (`α × OpexRailIterations(distance)`) est écarté **parce que la dispersion du modèle
   est trop grande**, pas parce qu'il ne mordrait pas. `KNOT_DISTANCE` vaut `[23, 33, 48, 63, 81,
   105, 150]`, PAS `[10..70]` — lire `KNOT_ITERATIONS` sans lire `KNOT_DISTANCE` juste à côté fait
   surestimer le modèle d'un facteur 5 à 10 et mène à la conclusion inverse. Chiffres corrects sur
   les 52 réussites : ratio réel/modèle **médian 0,41**, étalé de **0,016 à 3,40** (facteur 200). Le
   modèle prédit un coût moyen amorti, pas la queue d'une tentative isolée : à `α = 2` on perd
   encore 4 réussites, contre **0 pour le plafond plat à 40 000**.

   ⚠️ **Interaction non anticipée entre les deux réglages, à surveiller au banc.** Le plafond
   abaissé **crée** des abandons chez les paires qui aboutissaient entre 40 000 et 60 000
   itérations, et la mémoire rend chacun de ces abandons **définitif** : une paire qui réussissait à
   45 000 est désormais bannie pour la partie. Si le bras `station_join=0` ressort sous le bras de
   contrôle, c'est la première suspecte — la réponse serait de ne mémoriser que les abandons
   atteints à l'ancien plafond, ou de n'interdire qu'une seule re-tentative au lieu de toutes.

   **Validation graine 4096 / 20 ans** (une graine, donc aucune conclusion de valeur) : abandons
   **4 → 1**, itérations gaspillées **240 000 → 40 000**, années franchies **7 → 0**, 7 candidats
   écartés par la mémoire. La cadence annuelle est entièrement récupérée, ce qui était l'objet.

   **Verdict du banc (`docs/bench_v2_join.json`, 3 bras × 20 graines × 20 ans, ~25 min) : AUCUN
   EFFET DÉCELABLE, dans aucune comparaison.** Bras A = contrôle `[60,0,0]`, B = `[40,1,0]`,
   C = défauts `[40,1,1]`.

   | comparaison | `company_value` | `performance_history` |
   |---|---|---|
   | A − B (plafond + mémoire) | +2,06 % · t=+0,31 · 10/20 | +3,62 % · t=+0,80 · 12/20 |
   | B − C (raccordement) | −2,94 % · t=−0,47 · 11/20 | −1,79 % · t=−0,39 · 12/20 |
   | A − C (les deux) | −0,94 % · t=−0,16 · 10/20 | +1,77 % · t=+0,49 · 12/20 |

   **C'était le résultat attendu**, pas une infirmation : le plancher de détection est de ~15 % sur
   `company_value` et ~12 % sur `performance_history` (§8), et les effets observés valent 0,2 à
   3,6 %. Le banc établit **l'absence de dégât mesurable**, et rien de plus. La justification du
   correctif repose donc entièrement sur les métriques directes ci-dessus, comme `current_loan`
   l'avait fait pour l'item 4.

   ⚠️ **Un point aberrant à ne pas surinterpréter, mais à ne pas oublier** : graine 100, bras B,
   `company_value = 1` avec 121 véhicules, 18 gares, emprunt au plafond de 300 000 et un revenu
   annuel de 14 207 contre 56 032 au contrôle — une compagnie qui a beaucoup bâti et rien gagné,
   pas une compagnie inerte. Elle porte à elle seule le CV du bras B (42 % contre 26 % pour A). Le
   bras C, qui a pourtant le même plafond ET la même mémoire, s'en sort à 919 065 : ce n'est donc
   pas un effet systématique des deux réglages mais, très probablement, la divergence de
   trajectoire déjà documentée. **Retirer cette graine ne change pas la conclusion** — tous les
   |t| tombent alors sous 0,54.

7. ✅ **Le biais de sélection du modèle de profit : mesuré, défaut 0** (2026-08-30).
   Réglage `probe_negative` : après `_tryBuild`, au plus une paire rail rejetée pour
   profit prédit ≤ 0 est force-construite sur le cash restant, budget `ATTEMPT_FLOOR`.
   PX marque la ligne ; elle ne contamine pas la calibration des lignes classées.
   5 graines × 20 ans (`docs/opex_probe_negative_20y_5seeds.json`) :

   | | |
   |---|---|
   | paires-années `profit≤0` | 14 001, dont **13 918 pax** et 83 fret |
   | bandes | 2 010 / 1 987 / 1 998 / **8 006 >100 tuiles** |
   | « presque admis » (prédit > −1000) | 5 546 |
   | tentatives | 52 (médiane prédit **−39,5**, médiane **123 tuiles**) |
   | issues | **48 ABND**, 4 OK |
   | OK : distance | 63, 64, 67, 73 (médiane 65,5) — le court du stash |
   | OK : prédit | −146, −143, −16, −39 |
   | OK : profit réel, 2e année | 22 798 / −53 / 20 436 / 13 695 — **3/4 > 0** |
   | OK : profit réel, dernière année | **4/4 > 0**, médiane 18 972 |

   Le 45,2 % de `docs/opexai_plafonnement.md` est **périmé** (avant traction) : en 1989
   sur les 4 graines d'origine, `profit≤0` = 608 / 4 217 = **14,4 %**, toujours presque
   tout du pax. L'origine déjà desservie est devenue le premier filtre (62 %).

   **Ce que ça tranche.** On ne peut plus conclure que les paires rejetées sont
   réellement non rentables. Les 4 qui passent A\* à 2 000 itérations (60–75 tuiles,
   pax) rapportent 10–20 k/an pour un prédit ~−100. **Ce que ça ne tranche pas :**
   48/52 ABND, médiane 123 tuiles — `ATTEMPT_FLOOR` censure le long, qui est le
   volume (57 % des rejets >100 tuiles). n=4 n'est pas un retuning.

   ⚠️ **Défaut 0.** `OpexAI[probe_negative=1]` rallume. Ne pas recalibrer
   `OpexLineEconomics` ni baisser le filtre `profit≤0` sur cet échantillon.

   ✅ **Suite : même sondage, plafond dur 40 000** (2026-08-30, soir).
   `alternativeRatio = 0` → chemin Z, `HARD_ITERATION_CAP`. Aucun paramètre
   ajouté à `OpexBuildLine` : le classement ne change pas d'opcodes.
   5 graines × 20 ans (`docs/opex_probe_negative_hardcap_20y_5seeds.json`) :

   | | plancher 2 000 | plafond 40 000 |
   |---|---:|---:|
   | tentatives | 52 | 29 |
   | OK / ABND | 4 / 48 | **20 / 8** |
   | médiane dist. tentées | 123 | 120 |
   | médiane dist. OK / ABND | 65,5 / 124,5 | **94,5 / 163,5** |

   | bande | n | OK | last year > 0 | médiane last |
   |---|---:|---:|---:|---:|
   | ≤50 | 2 | 2 | **2/2** | 12 737 |
   | 50–75 | 4 | 4 | **4/4** | 17 231 |
   | 75–100 | 6 | 5 | **5/5** | 11 980 |
   | >100 | 17 | 9 | **3/8** | **0** |

   **≤100 tuiles : 11/11 rentables** en dernière année, pax, prédit ~−40. Le n=4
   du plancher se reproduit et s'étend. **>100 tuiles : médiane 0**, 3/8 > 0
   (123, 163, 164 tuiles à +15–28 k ; 109 et une 123 à 0 ; 160 à −2 132).
   Deux 146 tuiles n'ont qu'une année partielle. Les 8 ABND restants sont
   du très long (110–195 tuiles) au plafond.

   ⚠️ **Ne pas lever `profit≤0` globalement** : ce serait réadmettre le long
   qui ne paie pas, le piège du vivier. Défaut `probe_negative` **0**.

   ✅ **Retuning pax borné : écrit, mesuré, défaut 0** (2026-08-30, nuit).
   Réglage `pax_near` : pax, ≤100 tuiles, prédit dans (−200, 0], ratio = 1,
   au plus 1 tentative/an au plafond dur. 5 graines
   (`docs/opex_pax_near_20y_5seeds.json`) : 21 lignes, toutes pax, 38–97 tuiles,
   prédit −197…−13. Le mécanisme est chirurgical.

   Banc apparié 20 graines × 20 ans (`docs/bench_pax_near.json`) :

   | métrique | delta | t | graines | verdict |
   |---|---|---|---|---|
   | `company_value` | +0,6 % | 0,10 | 8/20 | nul |
   | `performance_history` | +4,7 % | 1,42 | 14/20 | sous le plancher (~12 %) |
   | véhicules | +1,3 % | 0,20 | 9/20 | nul |
   | gares | **+10,5 %** | **4,27** | **17/20** | **établi** — plus de construction |

   Même piège que le vivier : on construit plus, pour la même valeur. Variance
   pire (CV 0,25 → 0,33), minimum 1,70 M → 1,56 M, une graine à emprunt
   résiduel. Graine 42 +64 %, 512 −42 %. ⚠️ **Défaut 0.** `OpexAI[pax_near=1]`
   rallume. Ne pas élargir les bornes (distance, −200) sans banc.

9. 🔴 **Les suites de la tranche v1 du raccordement de gare** (commité, défaut `station_join=0`).
   Le quai parallèle joint au même `StationID` avec sa propre entrée est en place et contourne à
   la fois la question des jonctions et le blocage sur voie unique ; note de conception dans
   `docs/opexai_raccordement_gare.md`. Le banc vivier a dit non ; le banc post-traction aussi
   pour la valeur (§0.2), malgré un effet de construction toujours solide. Cinq suites, dans
   cet ordre :

   1. ✅ **Instrumenter le REFUS de jointure — fait (2026-08-30).** `OpexFindStationJoin` rend
      `{ refuse = M|K|R|N|E }` au lieu de `null`. Panneau `OB|R` (multi / kind / role / other),
      gated comme `OB|J`. 5 graines × 20 ans, `station_join=1`
      (`docs/opex_join_refuse_20y_5seeds.json`) :

      | | M | K | R | other | tentatives | OK | JOINPATH |
      |---|---:|---:|---:|---:|---:|---:|---:|
      | total | **196** | **75** | **0** | 41 | **705** | **39** | **0** |

      La jointure n'est **pas** inerte. La « graine 4096, 5 `too_close_far`, 0 tentative » est
      périmée (165 tentatives / 7 OK ; les far sans tentative sont 1970-72, toutes K).
      **R = 0** : `OpexOriginJoinable` a déjà coupé les rôles fret à la génération.
      ⚠️ **Défaut 0.** Pas un changement de classement.
   2. ✅ **`JOINPATH` : mesuré vide.** 0 / 808 tentatives rail. `OpexJoinPathIsDedicated` ne
      rejette rien sur cet arbre ; les 666 échecs de jointure sont SITEA/SITEB, pas un A\*
      payé puis invalidé. Pas de mémoire à ajouter, pas de contrainte à pousser dans le
      pathfinder. Le rendement site a été mesuré ensuite (parallèle 1–4, 39 → 71 OK) :
      JOINPATH reste 0, le reste est le spread, et ce n'est pas la suite.
   3. ✅ **Le profit prédit d'une ligne jointe — `basin_share` mesuré, défaut 0.** La production
      de l'extrémité jointe est divisée par (n+1). Banc apparié 20 graines × 20 ans
      (`docs/bench_basin_share.json`, paire `docs/bench_basin_share_paired.json`), les deux
      bras à `station_join=1` :

      | métrique | delta | t | graines | verdict |
      |---|---|---|---|---|
      | `company_value` | +5,5 % | 0,89 | 11/20 | sous le plancher (~15 %) |
      | `performance_history` | +3,8 % | 1,11 | 11/20 | sous le plancher (~12 %) |
      | véhicules | +0,2 % | 0,04 | 12/20 | **nul** — pas moins de trains |
      | gares | **+12,9 %** | **3,67** | **15/20** | les jointures sont déclassées |

      Ce n'est pas « moins de trains sur un bassin partagé ». C'est un **autre classement** :
      les candidats à jointure reculent, l'IA repose des gares neuves, les véhicules du bras
      join restent. Graine 42 : tentatives 228 → 40, véhicules 221 → 238. ⚠️ **Défaut 0.**
      Le spread n'est **pas** débloqué : joindre plus, sur un terme qui ne paie pas, recréerait
      le banc vivier.
   4. ✅ **PBS capacité + jointure hors `TracksOverlap`** (2026-08-30). Pas un
      changement de classement. Lignes `trains > 1` : PBS tous les 8 slots dès le
      slot 8, `SIGFAIL` avant les convois. Jointure : approches voie simple
      (gares 2–8, deux côtés du dépôt), jamais la tuile d'aiguillage.
      `CmdBuildSingleSignal` refuse tout `TracksOverlap` (erreur 2050). Pont /
      tunnel → `SJ` skip ; commande refusée → `JF` + rollback. Détecteurs `RX`
      (perte annuelle hors rebut) et `XC` (`CRASH_TRAIN`).
      Capacité 5×20 ans (`docs/opex_capacity_signal_fix_20y_5seeds.json` contre
      `docs/opex_capacity_signal_failures_v2_20y_5seeds.json`) : 33 `SF` au slot
      1 → **148/148**, 0 `SF`, 0 `RX`. Jointure `station_join=1`
      (`docs/opex_junction_signal_fix_20y_5seeds.json` contre
      `docs/opex_station_junction_baseline_20y_5seeds.json`) : 5 PBS / 11 refus
      → **9 / 0**, 3 skip, 0 `JF`, 0 `SIGFAIL`, 0 `XC`. ⚠️ **Défaut
      `station_join` 0.** Ce n'est pas une jonction de voie. Pas de spread.
      🔴 **La commande réussit, la valeur non.** 20 graines × 20 ans contre
      `bench_road_current` (`docs/bench_after_pbs.json`) : −94,9 % / t = −20,9 /
      0/20. PBS bidirectionnels sur voie unique dédiée. Ne pas en faire une
      baseline. Remplacé par la double voie (item 9.5).
   5. ✅ **Double voie v1** (2026-08-30). Deux trains sur une voie se rencontrent.
      `OpexTryDoubleTrack` : quai parallèle, A* avec `ignored_tiles`, dépôt
      propre, un convoi par voie, plafond 2. Échec → un train. Pas de PBS de
      capacité. 5 graines × 20 ans
      (`docs/opex_double_track_20y_5seeds.json`) : **64/92** doubles, 128
      trains, 0 ligne à deux convois sur une voie, 0 `XC` / `RX`, emprunt 0.
      Médiane valeur **5,73 M** (5/5 au-dessus de `opex_town_growth_20y_5seeds`).
      Skip : 17 quai, 9 chemin, 2 voie.
      Banc apparié 20×20 vs `bench_road_current`
      (`docs/bench_double_track.json`) : valeur **+55,5 %**, t = 5,27, 17/20 ;
      note **−9,0 %**, t = −2,32, 8/20 ; véhicules −39 %. **Gardé** ; la note
      s'améliorera plus tard.
      ⚠️ Ce banc est pré-correctif : le premier convoi était démarré dans
      `OpexBuildTrains`, puis arrêté par le second `StartStopVehicle` du commit :
      44/44 lignes restées à un train avaient un profit nul.
      ✅ **Banc corrigé** (`docs/bench_double_track_startfix.json`, 20×20 contre
      `bench_road_current`) : valeur **+125,1 %**, t = **13,31**, **20/20** ; note
      **+17,6 %**, t = **6,05**, 18/20 ; revenu dernière année **+49,2 %**,
      t = **7,61**, 19/20 ; véhicules −34,1 %, t = −8,19 ; gares +1,8 %, nul.
      Emprunt et insolvabilité 0/20. C'est la baseline courante. Son smoke 5×20
      (`docs/opex_double_track_startfix_20y_5seeds.json`) a 35/39 lignes à un train
      profitables, 64/93 doubles, 0 `RX` / `XC` / `SIGFAIL`.

**Priorité de fait, révisée le 2026-08-30 (join H2, rejeu DT)** : H1, H2 et
le rejeu avec double voie **aucun ne paie**. Défauts `station_join` /
`join_max_distance` / `join_place` = 0. Pas de spread, pas de jonction de
voie, `JOINPATH` tient. `MIN_SEPARATION` gelé. L'item 2 reste dernier.

*Priorité précédente, conservée pour la trace* : ~~le rendement join~~ (✅ mesuré,
défaut 0) était la tête. ~~l'item **9.1**~~ (✅) était la tête. ~~le retuning pax
borné~~ / ~~l'item **7**~~ / ~~l'item **4**~~.

---

## 3. Calibrations en attente

- ✅ **Le modèle économique, volet PASSAGERS** (`economy.nut`/`candidates.nut`) : mesuré et corrigé
  le 2026-08-28 sur 9 lignes pax réelles (2 campagnes de 10 ans, graine 42, 15.3) — voir
  `docs/opex_predict_vs_actual.json` et `sweeps/opex_predict_vs_actual.py`. Le gap ~10x se
  décompose en `STATION_RATING_PCT` trop optimiste (75 supposé contre ~53 mesuré, facteur ~1,4x
  seulement) ET, dominant, `AITown.GetLastMonthProduction` compté sur la ville ENTIÈRE alors
  qu'une gare n'en capte qu'un rayon local (facteur ~4,5x résiduel, mesuré 8-37 % selon la ligne).
  Corrigé par `STATION_RATING_PCT = 50` et un nouveau `TOWN_CATCHMENT_SHARE_PCT = 22` appliqué
  uniquement aux paires de villes dans `OpexPaxCandidates`. Vérification in-sample sur les 9
  lignes : ratio prédit/réel resserré de 3,75-17,3x à 0,55-2,54x (moyenne ~1,18x contre ~8x avant).
- ✅ **Note de gare fret à -1 : résolu, DEUX causes distinctes démêlées.**
  1. **Train coincé** (`abd641b`, 2026-08-28) : `OF_FULL_LOAD_ANY` aux deux arrêts bloquait le
     convoi au puits fret (structurellement à sens unique) sur une gare à une voie. Corrigé par
     `OF_NONE` au puits.
  2. **Fermeture d'industrie source** (`e884358`, 2026-08-28) : confirmée réelle sur certaines
     lignes (via `AIIndustry.IsValidIndustry`, pas déduite), mais PAS systématique — une gare peut
     rester rentable via une industrie voisine du même cargo (`srcAlive=0` n'implique pas la mort).
     Détection sur performance réelle (note + revenu, 2 ans consécutifs) puis vente des convois une
     fois le seuil confirmé.
- ✅ **Le modèle économique, volet FRET** : le « reste ouvert ~4-6x » précédemment noté ici est
  **retiré (2026-08-28)**, faute de fondement — `docs/opex_predict_vs_actual_postfix_freight_v2.json`
  (commis dans `abd641b`, jamais recroisé avec l'affirmation avant cette relecture) donne un ratio
  prédit/réel moyen de **0,98** sur les 5 lignes fret à ≥3 ans de données stables.
  `STATION_RATING_PCT = 50` (calibré sur le pax) tient donc aussi pour le fret, sans facteur
  correctif propre à identifier. Détail dans `docs/opexai_croissance.md` §2 et §8.
- ✅🔶 **Le modèle de coût A\*** (`candidates.nut`) : préalable distance ✅, recalibrage conjoint
  ✅ mesuré, **défaut `astar_cost=0`**. 5 graines × 20 ans
  (`docs/opex_attempt_distance_20y_5seeds.json`) : **227/227** tentatives avec distance, 101 OK,
  12 ABND, 111 SITEA/B/AB. **Chiffré d'abord sur 52 succès, puis sur 227 tentatives :**

  | bande | n | P(OK) | P(OK\|A\*) | SITE | ABND | itér. amorties / succès | ratio réel/modèle |
  |---|---:|---:|---:|---:|---:|---:|---:|
  | ≤ 35 | 32 | 0,63 | 1,00 | 12 | 0 | **308** | 0,20 |
  | 35-50 | 59 | 0,49 | 0,94 | 28 | 1 | 1 383 | 0,56 |
  | 50-70 | 30 | 0,77 | 0,82 | 2 | 3 | 5 676 | 0,66 |
  | 70-105 | 43 | 0,42 | 1,00 | 25 | 0 | 9 797 | 0,94 |
  | > 105 | 63 | 0,17 | 0,58 | 44 | **8** | **51 900** | 0,69 |

  Profit réel (1re année) / 1000 itérations des succès : 26 027 / 13 760 / 3 241 / 1 209 / **0**.
  L'optimum est au plus court. 8 des 12 ABND sont au-delà de 105 tuiles et font exploser le
  coût amorti (250 900 itérations de succès, 320 000 d'abandons). Le commentaire 13.4 « lignes
  MOYENNES à 48-63 tuiles » est **retiré** de `candidates.nut`.

  ✅ **Biais de censure : le préalable est fait.** `OB|A` porte la distance. 227/227.

  ✅ **Recalibrage conjoint fait, défaut 0** (2026-08-30). Nœuds v2 = itérations amorties
  (+/−12 tuiles) ; `ATTEMPT_MULTIPLIER` **reste 4** (p95/amort ≤ 2,7). Réglage `astar_cost`.

  5 graines × 20 ans (`docs/opex_astar_cost1_20y_5seeds.json`) : 13–20 lignes, médiane 51→47
  tuiles, tentatives 227→149, ABND 12→7. Le piège « budgets 50–400, zéro ligne » est évité.

  **Banc apparié 20 graines post-traction 20 ans** (`docs/bench_astar_cost.json`) :
  - `company_value` : −8,9 % (t = −1,86, 7/20)
  - `gares` : −7,9 % (t = −3,23, 4/20)

  **Ré-évaluation sur architecture continue (2026-08-31, `docs/bench_astar_cost_5y.json`, 20 graines × 5 ans)** :
  
  | métrique | Contrôle (`astar_cost=0`) | Traitement (`astar_cost=1`) | Delta | t | Graines | Verdict |
  |---|---|---|---|---|---|---|
  | `company_value` | 536 000 £ | 522 500 £ | −2,52 % | −0,73 | 8/20 | Défavorable à astar_cost=1 |
  | `profit` (dernier trim.) | 44 800 £ | 42 770 £ | −4,75 % | −0,80 | 9/20 | Défavorable à astar_cost=1 |
  | `profit_year` (annuel) | 174 200 £ | 172 080 £ | −1,23 % | −0,38 | 10/20 | Défavorable à astar_cost=1 |
  | `performance_history` | 260,2 | 261,8 | +0,61 % | +0,21 | 13/20 | Neutre |

  **Conclusion** : Même avec le précalcul continu et la boucle sans sleep, `astar_cost=1` (table v2) sur-pénalise inutilement les corridors à moyenne/longue distance au ranking annuel, retardant la construction de lignes très rentables.
  ⚠️ **Défaut `astar_cost=0` STRICTEMENT MAINTENU.**
- ✅ **Constantes HYPOTHÈSE `SPEED_EFFICIENCY_PCT = 70` et `WAGONS_PER_TRAIN = 5`** : remplacées
  le 2026-08-29 par la traction dimensionnée (`4a8e15e`). Rendement réel mesuré le 2026-08-30
  (§4.3) : 0,96 vs catalogue, 1,18 vs traction — le 70 % était trop pessimiste, pas de
  retuning.
- ✅ **`ROAD_SPEED_EFFICIENCY_PCT = 60` : mesuré, pas retuné** (2026-08-30). Panneau `RY`,
  5 graines × 20 ans (`docs/opex_road_speed_yield_20y_5seeds.json`,
  `docs/opex_road_speed_yield.json`). n = **53** ligne-années en marche (6 lignes,
  0 sur 12345). Fret **1,00** vs catalogue, pax **0,75**. Réel / 60 % :
  **1,27** pax, **1,71** fret. Instantané, pas un temps de trajet. Le 60 % est
  pessimiste en croisière, comme le 70 % rail. ⚠️ **Pas de retuning.** Ce n'est
  pas le 3,91 pax (`TOWN_CATCHMENT_SHARE_PCT`). `docs/opexai_route.md`.
- ✅ **Accélération route 15.3** (2026-08-30). Wiki 37 km-ish/h/jour =
  `AM_ORIGINAL` (`DoUpdateSpeed(256)`, une fois/tick, unité 0,5).
  `vehicle.roadveh_acceleration_model` défaut **1 = réaliste**, absent du
  CFG. Virage d'axe : plafond 3/4. Le 0,75 pax de `RY` est ce plafond sur
  le L, pas un retuning. Pas de modèle de traction route.

---

## 5. Banc

- ✅ **Banc multi-graines construit et exécuté (2026-08-29)** — `sweeps/bench_v2.py`,
  résultats dans `docs/bench_v2.json` : 20 graines × 20 ans, OpexAI et AAAHogEx (campagne
  interrompue volontairement avant AdmiralAI et trAIns, jugées obsolètes). Le script apporte la
  notion d'**arm** (une IA OU une variante paramétrée d'OpexAI via `ai_params`, ex.
  `OpexAI[pathfinder_sleep_ticks=1]`), le nettoyage des sauvegardes, un checkpoint `.jsonl`, les
  stats de dispersion et les **comparaisons appariées par graine**. Les deux items ci-dessous
  (20 ans, 20 graines) sont absorbés par lui. Indicateurs de succès : `company_value`,
  `performance_history` (score 0-1000, pas le profit ni la note de gare), **profit** du
  trimestre et de l'année (`income`+`expenses`), **note de gare** médiane (`STNN`, 0-255).

  | arm | company_value | CV | SE | note | CV |
  |---|---:|---:|---:|---:|---:|
  | OpexAI *(arbre courant, `bench_double_track_startfix`, 2026-08-30)* | **7 034 590** | **24,7 %** | 5,5 % | **623** | 12,2 % |
  | OpexAI *(route, `bench_road_current`)* | 3 125 439 | 22,3 % | 5,0 % | 530 | 12,0 % |
  | OpexAI *(re-baseliné le 2026-08-29, `bench_v2`)* | 2 409 531 | 48,8 % | 10,9 % | 396 | 27,6 % |
  | OpexAI *(mesure d'origine, archivée)* | 2 527 171 | 32,6 % | 7,30 % | 408 | 20,4 % |
  | AAAHogEx | 225 430 986 | 16,2 % | 3,62 % | 897 | 0,5 % |

  ✅ **Référence de l'arbre : `docs/bench_double_track_startfix.json`.** Apparié
  20×20 contre `bench_road_current` : `company_value` **+125,1 %**, t = **13,31**,
  **20/20** ; `performance_history` **+17,6 %**, t = **6,05**, 18/20 ; revenu
  dernière année **+49,2 %**, t = **7,61**, 19/20 ; véhicules **−34,1 %**, t =
  **−8,19**, 0/20. Emprunt / insolvabilité 0 / 0. La double voie est gardée ;
  `docs/bench_double_track.json` reste le bras pré-correctif. `docs/bench_v2.json` et
  `docs/opexai_plafonnement_mesure.json` restent historiques.

  ✅ **Contrat rail 1--2 trains aligne (2026-08-31).** Le modele ne cote plus 3--8
  rames que le constructeur ne peut pas poser; `rail_cost_probe` confirme 62/97
  sur-evaluations de flotte avant correction. Banc apparié 20x20
  `bench_rail_cap2.json` : valeur +3,6 % (t=0,97), profit annuel +0,6 % (t=0,18),
  note +0,5 % (t=0,23), note de gare +2,1 % (t=1,10), sans emprunt ni insolvabilité.
  Tous sous le plancher de détection : correctif gardé pour la cohérence, mais baseline
  inchangée (`bench_double_track_startfix`).

  🔴 **HEAD + PBS (`e027037`) n'est pas une baseline.** 20 graines contre
  `bench_road_current` (`docs/bench_after_pbs.json`) : `company_value` **−94,9 %**,
  t = **−20,9**, **0/20** ; `performance_history` **−77,7 %**, t = **−25,0**.
  9 graines à `company_value=1`, 20/20 encore empruntées, 5 insolvables, 0 erreur
  de script. Les campagnes 5 graines « 148/148, 0 SF » mesuraient la commande,
  pas la valeur (graine 42 : 3,24 M → **1**). Ne pas fusionner ça dans `bench_v2`.

  ⚠️ Les deux lignes OpexAI *de 2026-08-29* mesurent le **même comportement** sur les **mêmes
  graines** : seul le profil d'opcodes diffère (§8). L'écart entre elles n'est pas significatif
  en lecture appariée (t = −0,60) — mais il chiffre le **bruit de trajectoire irréductible**, et
  c'est lui qui fixe le plancher de détection du banc : **~15 % sur `company_value`, ~12 % sur
  `performance_history`**. `bench_road_current` n'est plus ce comportement (route, traction,
  bassin 86). `bench_after_pbs` non plus.

  **Quatre acquis, dont trois corrigent ce qui était écrit ici :**
  1. ❌ **Le n=20 ne donne PAS 5,9 %.** Cette projection supposait un CV de 26 % ; le CV mesuré
     d'OpexAI était **32,6 %** (48,8 % après re-baselinage), donc 7,30 % à 10,9 % d'erreur-type.
     La différence de deux moyennes indépendantes porte ~10,3 % à ~13,1 % de SE : il faudrait un
     effet de **~21 % à ~26 %** pour trancher à 2σ.
     **La lecture appariée n'est donc pas un raffinement mais le seul chemin praticable.**
     🔶 **Précisé le 2026-08-29 par le re-baselinage** : l'appariement marche, mais ne divise la SE
     que par ~1,7 (13,1 % → 7,70 %). Il ne rend pas le banc sensible, il le rend *praticable* — le
     plus petit effet décelable reste ~15 % sur `company_value`, ~12 % sur `performance_history`.
     Un correctif qui gagne 8 % restera invisible à n=20.
  2. **Deux métriques, deux usages.** `performance_history` est **saturée chez AAAHogEx**
     (897, CV 0,5 %) : inutilisable pour se comparer à lui, où seule `company_value` parle. Mais
     elle est **moins bruitée que `company_value` chez nous** (20,4 % contre 32,6 %) : c'est la
     bonne métrique pour opposer deux variantes d'OpexAI entre elles.
  3. ❌ **Porter le banc à 20 ans nous dessert**, contrairement à l'argument ci-dessous. L'écart
     avec AAAHogEx passe de ~19× à 10 ans (banc v1) à **88× à 20 ans**. L'allongement ne révèle pas
     notre multimodalité, il révèle notre plafonnement pendant qu'il compose. On garde 20 ans (la
     mesure est plus honnête), mais sans en attendre un avantage.
  4. **La graine 42 est 14e sur 20** (2 336 785 pour une médiane de 2 740 070) ; l'écart
     meilleure/pire graine est de **5,5×**. Toutes les décisions antérieures ont été prises sur une
     graine sous la médiane.

  ⚪ **`pathfinder_sleep_ticks` ne sera PAS mesuré au banc — décision arrêtée le 2026-08-29, ne pas
  rouvrir.** Le défaut reste 0. Le banc sait pourtant l'opposer (`OpexAI[pathfinder_sleep_ticks=1]`),
  mais le Sleep est **strictement dominé** : le moteur suspend déjà le script dès qu'il épuise son
  budget d'opcodes du tick, donc `Sleep(n)` n'achète aucun opcode supplémentaire plus tard — il
  fait seulement qu'OpexAI ne fait rien pendant n ticks pendant qu'un adversaire continue. Il n'y a
  aucun mécanisme par lequel il puisse aider ; le 13-contre-13 de la graine 42 était du bruit de
  trajectoire. Raisonnement écrit à côté du réglage dans `ai/OpexAI/info.nut`.

- ⚪ *(absorbé par le banc v2)* **Porter le banc de 10 à 20 ans.** Toute l'évolution multimodale
  arrive après 1980 : aéroport METROPOLITAN (1980), COMMUTER (1983), parc routier +83 %, parc
  avion +38 %. Un banc à 10 ans mesure une partie où le rail est presque le seul mode qui
  progresse. ⚠️ Argument **retourné par la mesure**, voir le point 3 ci-dessus.
- ⚪ *(absorbé par le banc v2)* **Augmenter le nombre de graines, pas les répétitions.**
  Bruit intra-graine 4,1 % contre dispersion inter-graines de 26 %. Erreur-type de la moyenne à
  n=5 : 11,8 % ; à n=20 : 5,9 % — ⚠️ **chiffre réfuté**, la vraie SE à n=20 est 7,30 %.

  **Pourquoi c'est désormais un préalable et plus une amélioration.** Trois changements *sans aucun
  effet décisionnel* ont produit le même jour des écarts pluri-lignes sur la graine 42 :
  1. la liaison route, qui coûte 0,04 % des opcodes de la campagne (§6.4) ;
  2. le franchissement d'une année de calendrier (`docs/opexai_croissance.md` §6) ;
  3. le simple fait d'interposer un appel de fonction (`OpexSign`) devant les 57 panneaux —
     **3 lignes rail perdues, 16 → 13**, alors qu'aucune décision de l'IA ne change.

  Toute perturbation du rythme d'opcodes déplace les frontières de ticks, donc *quand* les choses
  arrivent, et la trajectoire entière diverge. **Une graine unique ne distingue donc pas un vrai
  gain d'un déplacement de trajectoire**, y compris pour des écarts de 16 %. Conséquence pratique :
  tant que le banc multi-graines n'existe pas, aucune décision de conception ne peut être tranchée
  par la campagne graine 42 seule — ni le défaut de `pathfinder_sleep_ticks`, ni la réactivation du
  mode route, ni le coût réel du mode route pour le rail (§6.4).
  ⚠️ Corollaire de méthode : « reproduit deux fois à l'identique » ne prouve rien ici — la
  plateforme est déterministe, donc même graine ⇒ même résultat.
- Le **face à face** dans une partie partagée, aux jalons seulement (décidé le 2026-08-28).
- ✅ **Hypothèse d'un plafond `AISign` réfutée (2026-08-28).** Ni la tuile `(1,1)` ni le nombre
  de signs de la campagne ne sont en cause : `CmdPlaceSign` ne peut échouer ici que par nom de
  32 caractères ou plus, ou par pool global de 64 000 entrées, très au-dessus des ~2 000 signs.
  Le trou non monotone (1984 absent, 1985-1989 présents) vient du cycle annuel de `Start()` qui
  franchit une année pendant `_tryBuild` puis fixe directement `lastYear` à l'année courante.
  Ce n'était pas une perte d'observabilité : les tâches annuelles ne s'exécutaient pas (seul le
  `_tryBuild` déjà lancé pouvait continuer). Le rattrapage exécute désormais rapport des lignes,
  traitement des lignes mortes et remboursement pour chaque année franchie ; détail et mesure
  directe dans `docs/opexai_croissance.md` §6.

---

## 6. Modes de transport, dans l'ordre décidé

1. ✅ **Rail** — étage 3 ci-dessus.
2. ✅ **Avion** — une liaison passagers entre deux grandes villes, validée sous OpenTTD 15.3.
   Aucun pathfinding ; son avantage n'est toutefois **pas** la vitesse : il vole au quart de sa
   vitesse affichée.
3. ✅ **Bateau** — une liaison passagers entre deux grandes villes côtières, avec validation
   bornée du graphe d'eau et dépôt construit sur la même composante. Voir
   `docs/opexai_multimodal.md`.
4. ✅ **Route** — adoptée le 2026-08-29, `road_mode` défaut 1. Ce n'est plus la liaison bus
   unique désactivée du 2026-08-28 (notes −1, `ROAD_BUILD_ENABLED = false`) : c'est une phase
   annuelle, bus et **camions**, bande 5–25 tuiles. Banc apparié : `performance_history` **+9,3 %**,
   t = 2,03, 16/20. SITE, TRACEX, classement et multistop sont mesurés (défauts inchangés sauf
   le mode lui-même). Détail : **`docs/opexai_route.md`** et §1 bis ci-dessus.

Ne pas oublier deux composantes gratuites de la note de compagnie : **emprunt à zéro** (5 %) et
**8 types de cargo par trimestre** (5 %) — cette dernière plaide contre une IA 100 % passagers.

---

## 7. Reprises de l'ère `TrainLineAI` encore ouvertes

- **La reprise sur préfixe façon `RetryToBuild`**, en clean-room.
  Les **64 `TRKFAIL` / ~145 M** (453 par itération contre 156) sont **TrainLineAI 13.4**,
  campagne v3 une ligne par compagnie (2026-08-28), pas OpexAI 15.3. Sur l'arbre
  courant, 5 graines × 20 ans : **2/173** (`docs/opex_road_multistop_20y_5seeds.json`),
  **2/175** (TRACEX), **3/227** (distance). `abandon_memory` ne retient que `ABND` :
  graine 4096, 1988, deux tentatives à 69 tuiles (10 000 puis 27 950 itérations).
  Ce n'est plus le meilleur rendement identifié. Ne pas copier AAAHogEx pour deux
  échecs par campagne.
- ✅ **La politique d'abandon** : la forme fermée coupe une recherche lorsque son rendement
  marginal attendu passe sous le rapport du meilleur candidat non essayé. Le trou du dernier rang
  (absence de suivant = budget maximal) est corrigé : son alternative est `MIN_RATIO`, rapport
  minimal déjà acceptable au prochain classement annuel, pas une constante nouvelle. Campagne
  instrumentée graine 42/20 ans : 5 derniers candidats passaient auparavant par le chemin zéro,
  mais 0 tentative ABND ; le vieux ABND à 60 000, antérieur à l'instrumentation, ne peut donc pas
  être attribué rétrospectivement à ce chemin plutôt qu'au plafond. Détail dans
  `docs/opexai_croissance.md` §6.

---

## 8. Hygiène

- 🔶 **Workflow GitHub avec OpenTTDLab : smoke test à chaque PR, banc à la demande (demandé le
  2026-09-02).** Le dépôt est désormais sur GitHub (`jrdoublet/openttd-ml`, privé), donc
  l'intégration continue devient possible. Deux étages, et **surtout pas un seul** :

  **Étage 1 — porte de PR, obligatoire, ~2 à 5 min.** Smoke test 3 graines × **2 ans**, échec du
  job si une partie remonte `run_ok = false` ou un marqueur fatal NoAI (`Your script made an
  error`, `The script died unexpectedly`).

  ⚠️ **Deux ans, pas un.** Paramètre payé le 2026-09-02 : le plantage `station_exit` de
  `OpexUpgradeRailLineToDoubleTrack` **passe le smoke à 1 an** et ne tue l'IA qu'à 2 ans, quand le
  refleet rail se déclenche pour la première fois. Un smoke d'un an aurait laissé passer une IA qui
  meurt en cours de partie.

  ⚠️ **La porte doit aussi vérifier un PLANCHER DE PLAUSIBILITÉ**, pas seulement l'absence
  d'erreur : au moins une gare et un profit non nul sur chaque graine. Sans ça, une IA qui ne
  construit RIEN passe le test en silence — c'est la règle du projet, *une IA morte ressemble
  exactement à une IA nulle*, et un job vert la maquillerait.

  **Étage 2 — banc apparié, manuel ou nocturne, PAS une porte de PR.** 20 graines × 3 ans contre le
  bras de contrôle courant, JSON publié en artefact. Il ne peut pas être bloquant, pour deux
  raisons de fond :
  1. il dure ~20 min sur 3 cœurs, et bien plus sur un runner GitHub à 2 vCPU ;
  2. son **plancher de détection est de ~15 % sur `company_value`** — il est structurellement
     incapable de valider un petit changement, donc l'utiliser comme porte produirait surtout des
     échecs et des succès aléatoires.

  **Points de mise en œuvre à ne pas redécouvrir :**
  - OpenTTD **15.3 obligatoire** (AAAHogEx exige ≥ 14, OpenTTDLab ne supporte pas 14.x) ;
  - l'image exige `libgomp1` et `libglib2.0-0`, sinon `exit 127` silencieux — c'est déjà dans le
    `Dockerfile` du dépôt, le réutiliser plutôt que d'en écrire un autre ;
  - **mettre en cache les téléchargements OpenTTDLab** (binaire OpenTTD + OpenGFX), sinon chaque
    job les retélécharge ; clé de cache = version d'OpenTTD ;
  - le dépôt est **privé** : les minutes Actions sont facturées, ce qui plaide pour un étage 1
    court et un étage 2 déclenché à la main.


- 🔶 **Supprimer aussi `rail_refleet` et `air_starter`, PROUVÉS INERTES par la mesure
  (2026-09-02).** Écart-type des différences appariées = **0,0** sur 20 graines : basculer l'un ou
  l'autre ne change pas un bit du résultat (`bench_rail_refleet_vs_aaahogex_5y.json` et `_v2`).
  C'est la confirmation indépendante de la revue de code (§0 nonies : « TOUTE la fonctionnalité
  `rail_refleet` est du code injoignable »). Même traitement que `tree_planting` ci-dessous :
  retirer le code gardé, la constante, sa relecture dans `Start()`, l'entrée `info.nut` et la
  liste blanche de `bench_v2.py`. ⚠️ Retirer le code **mort** ne décale pas les trajectoires
  (vérifié le 2026-09-02 : 20/20 graines bit-identiques après suppression de 766 lignes) — mais
  retirer une **lecture de réglage** en décale, donc prévoir un banc de non-régression.

- 🔶 **Supprimer le réglage `tree_planting` et le chemin préventif qu'il garde (demandé le
  2026-09-01).** La question est **tranchée**, le réglage n'a donc plus de raison d'exister : la
  plantation ne doit avoir lieu **que** quand une ville nous refuse un aéroport. Laisser un
  paramètre inutile encombre `info.nut` et la liste blanche du banc.

  Ce qu'il faut retirer :
  1. les **sept sites préventifs** gardés par `TREE_PLANTING` dans `main.nut`
     (`542`, `707`, `864`, `1204`, `1518`, `1594`, `1699` au 2026-09-01) — ils appellent
     `OpexBoostTownRating` *avant* toute tentative de construction ;
  2. la constante `TREE_PLANTING` (`main.nut:68`) et sa relecture (`main.nut:3050`) ;
  3. la déclaration `AddSetting` dans `info.nut` ;
  4. l'entrée `"tree_planting"` de la liste blanche de `sweeps/bench_v2.py` (~ligne 141).

  ✅ **Débloqué le 2026-09-03.** La seule raison de garder le réglage était que le −22,1 % qui l'avait condamné portait sur un garde mort (`AITown.GetRating` est un enum 0-8). Le garde réparé, D1 a refait la mesure : `tree_planting=1` reste **négatif** (−12,1 % de `company_value`, −13,4 % de `profit_year`, 13/20 graines perdantes, `docs/bench_tree_planting_recalibrated_3y.json`). La question est tranchée deux fois, par deux mesures indépendantes dont l'une sur un mécanisme réparé : **le chemin préventif part, la plantation au refus municipal reste**. Suivi en E8.

  ⚠️ **Ne PAS toucher** au recours réactif de `builder_air.nut` (`517` et `540`) : il n'est pas
  derrière le drapeau, il ne se déclenche qu'après un vrai `ERR_LOCAL_AUTHORITY_REFUSES` renvoyé
  par `BuildAirport`, et c'est le seul comportement qu'on garde. `OpexBoostTownRating`
  (`candidates.nut`) reste donc en place, seul son usage préventif disparaît.

  ⚠️ Suppression **sans effet attendu sur le comportement** : le défaut est déjà à 0 depuis le
  banc ci-dessous. Mais toute perturbation du rythme d'opcodes décale les frontières de ticks
  (voir §5) — donc si le banc bouge après ce nettoyage, ce n'est pas une régression de décision,
  c'est une divergence de trajectoire. Ne pas re-mesurer pour « valider » la suppression.

  Motivation mesurée : banc apparié 20 graines × 3 ans
  (`docs/bench_treeplanting_3y_20seeds.json`), couper la plantation préventive vaut
  `company_value` **+22,1 %** (t = 2,42, 17/20 graines), `profit` +26,8 % (t = 2,09),
  `profit_year` +20,1 %, et resserre la dispersion (CV 63,8 % → 50,7 %).

- ✅ **Session du 2026-08-28 committée** en 5 commits (`a227281` banc/15.3, `f6095de` sonde de
  catalogue, `212c532` mécanique du jeu, `826a6fa` OpexAI, `ee3e370` cette liste). Historique local
  uniquement : le dépôt n'a **aucun remote**.
- ✅ `README.md` mentionnait déjà OpexAI/15.3 ; `docs/methode.md` a reçu une note en tête renvoyant
  vers le `README.md` (2026-08-28) — le corps du document reste volontairement celui de la
  campagne 13.4, il décrit un protocole historique.
- ✅ **Re-baseliner le bras `OpexAI` du banc après l'instrumentation de plafonnement — FAIT le
  2026-08-29** (résultat en fin d'item). Le diff non commité dans `ai/OpexAI/` — celui qui a produit
  `docs/opexai_plafonnement.md` — contient trois choses :
  1. les **compteurs de rejet** (`candidates.nut`, table `stats` passée en paramètre à travers
     `OpexMakeCandidate`/`OpexPaxCandidates`/`OpexFreightCandidates`, ressortie par
     `OpexBuildCandidates`, déversée dans les panneaux annuels `CG`/`CR`/`CD`/`CE`/`CK`) — sans
     eux, `ranked.all` dit combien de candidats survivent mais pas pourquoi les autres meurent ;
  2. trois **panneaux** dans `main.nut` : `PM|` pour les lignes avion/bateau (elles n'en avaient
     aucun), `PC|` pour le label cargo, et `OB|A|` qui porte le coût réel en opcodes d'une
     tentative — `OR` est déjà à 31 caractères pile, d'où le panneau compagnon ;
  3. une **vraie correction de bug** dans `_reportLines` : la boucle sur les véhicules filtrait en
     dur sur `AIVehicle.VT_RAIL`, donc les lignes avion et bateau rapportaient un profit de **0**
     depuis leur création (2026-08-28). Le `vehicleType` est maintenant déduit de `line.mode`.
     Aucune décision n'en dépend : `deadStreak` est le seul retour de `_reportLines` vers le
     comportement, et il est verrouillé derrière `isFreight`.

  **Le jeu de candidats produit est identique** (vérifié ligne à ligne : `served[a] || served[b]`
  est équivalent aux deux `continue` d'origine, et le `if (monthly <= 0) continue;` du fret est
  compensé à l'intérieur d'`OpexMakeCandidate`). **Mais le profil d'opcodes ne l'est pas**, et de
  signe inconnu : côté pax `OpexOriginServed` est sorti des boucles imbriquées (O(n²) → O(n),
  ~1 000 appels → 45, une économie), côté fret toutes les industries sont évaluées d'avance et
  `OpexMakeCandidate` est appelée même à `monthly = 0` (un surcoût) ; les compteurs eux-mêmes sont
  du bruit (~8 400 incréments/an, ~0,02 % du budget annuel). Comme un décalage d'opcodes déplace
  les frontières de tick, la trajectoire diverge : **`docs/bench_v2.json` n'est plus la baseline de
  l'arbre courant.**

  **Fait** : 20 graines × 20 ans rejouées sur le seul bras `OpexAI`
  (`docs/bench_v2_opex_rebaseline.json`), fusionnées dans `docs/bench_v2.json` — `AAAHogEx` est
  conservé tel quel, il n'a pas bougé. Statistiques et comparaisons appariées recalculées par les
  fonctions de `sweeps/bench_v2.py` elles-mêmes. L'ancien bras est archivé dans le bloc
  `rebaseline.previous_opexai` du même fichier (stats + les 20 valeurs par graine).

  **Trois résultats, dont deux inattendus :**

  1. ✅ **L'instrumentation est bien neutre en décision.** Différence appariée sur `company_value`
     **−117 640** pour une SE de **194 709**, soit **t = −0,60** — non significatif ; 9 graines sur
     20 s'améliorent. Sur `performance_history`, t = −0,50. Rien ne permet de dire que le diff
     dégrade l'IA, ce qui était l'hypothèse à écarter.
  2. **L'appariement fonctionne, mais le plancher de détection reste haut.** La différence de deux
     moyennes indépendantes porterait ici ~13,1 % de SE ; l'appariement la ramène à **7,70 %** sur
     `company_value` — un facteur 1,7, pas davantage. Conséquence chiffrée : **le plus petit effet
     décelable à 2σ est ~15 % sur `company_value` et ~12 % sur `performance_history`**
     (SE appariée 5,79 %). Ceci confirme le point 2 du §5 par une seconde voie :
     `performance_history` est la bonne métrique pour opposer deux variantes d'OpexAI.
  3. 🔴 **La dispersion a doublé et le mode d'échec s'est déplacé** — voir §2.4, que ce résultat
     reformule entièrement. CV de `company_value` **32,6 % → 48,8 %** (~2σ, l'erreur-type d'un CV
     à n=20 valant ~7,9 points : suggestif, pas concluant à lui seul).

- ✅ **Committer la session du 2026-08-29 (seconde moitié)** — le plafond d'abandon et le
  raccordement v1 sont dans `154409b` / `e39685a` / `8b50f12`. Join après traction,
  `basin_share` et `reborrow` suivent : trois mesures, trois défauts à 0.

- ✅ **Re-baseliner les durcissements inconditionnels du raccordement** (2026-08-30).
  `AreTilesConnected` après chaque `BuildRail` et `StartStopVehicle` reporté s'appliquent
  aussi à `station_join=0`. Ils sont dans `docs/bench_road_current.json`, puis
  dans l'arbre courant `docs/bench_double_track.json` (20×20, défauts, double voie).
  `docs/bench_v2.json` (vs AAAHogEx) et `docs/opexai_plafonnement_mesure.json`
  restent historiques. ⚠️ **Ne pas prendre `docs/bench_after_pbs.json` pour
  successeur** : c'est le banc HEAD+PBS, 20/20 sous `bench_road_current`, voir §5.

- ✅ **Chemin d'API dans `docs/opexai_raccordement_gare.md`** : la note citait
  `src/script/api/script_rail.hpp` comme s'il était dans ce dépôt. Corrigé : le `src/` d'ici
  n'est que du Python ; les `@pre` restent ceux des en-têtes NoAI 15.

---

## 9. Idées de fonctionnalités à évaluer (notées le 2026-08-28)

🔴 **Les deux premières ne sont plus des idées : la mesure du 2026-08-29 les a chiffrées, et elles
commandent désormais §2.5.** Le plafonnement d'OpexAI n'est pas un défaut de classement, c'est un
**mur géométrique** : l'IA se mure elle-même. Chaque gare bâtie interdit un disque de
`MIN_SEPARATION = 10` tuiles autour d'elle, et comme les villes et industries sont exactement là où
elle a déjà bâti, elle épuise l'espace admissible bien avant d'épuiser la carte — sur la graine 999,
**18 des 19 derniers candidats sont tués par ce seul filet**, avec 37 à 39 villes encore non
desservies. Détail dans `docs/opexai_plafonnement.md`.

Ces candidats-là ne sont pas du rebut à filtrer plus finement : ce sont **les meilleurs candidats
qui restent**. Ils sont proches d'une infrastructure déjà payée, donc leur coût marginal de
construction est le plus bas de tout le vivier — un raccordement sur gare existante coûte une
fraction du pathfinding d'une ligne neuve. Sous le principe « l'opcode est une ressource »
([[philosophie_opcodes_ressource]]), c'est exactement ce qu'on veut acheter. D'où l'ordre : ces deux
items d'abord, le réglage de `MIN_SEPARATION` jamais (§2.5).

- 🔴 **Agrandir une gare existante** — deux motifs désormais, dont le second est le plus lourd :
  (a) le motif d'origine, le stock d'un cargo déjà exploité qui dépasse la capacité captée ;
  (b) **le raccordement** — transformer le rejet `_tooClose` en jonction sur la gare voisine.
  C'est (b) qui débloque le vivier chiffré ci-dessus.
- 🔴 **Gérer les jonctions de rails** — condition technique de (b) : sans jonction, deux lignes ne
  peuvent pas partager une gare. Pertinent aussi dès qu'`OpexAI` a plusieurs lignes qui se croisent.
  Lecture faite : `docs/mecanique_jeu.md` §12 — trois principes, pas un cloverleaf ; `JOINPATH`
  tient tant que la jointure ne paie pas. PBS de capacité et de jointure posés (item 9.4) :
  hors gorge, hors aiguillage, fail-closed, `RX`/`XC`. Ce n'est **pas** une fusion de flux.

**Périmètre de mode, vérifié le 2026-08-29, à jour le 2026-08-30** : `_tooClose` ne filtre
**que le rail**. L'avion et le bateau ne le subissent pas (une liaison unique chacun) mais
**l'alimentent** : ils rejoignent `_lines`, un aéroport ou un quai bloque le rail sur 10 tuiles.
Les lignes **routières** sont dans `_lines` (rapport, rebut, `RF`) mais
`OpexOriginServed(..., includeRoad = false)` et `_tooClose` les ignorent : une desserte de
12 tuiles n'épuise pas une ville. Le plafond v1 « une seule liaison bus » est levé (jusqu'à
3/an). Le non-chargement de la v1 était la façade du dépôt, pas le type d'arrêt. Rentabilité
mesurée : `docs/opexai_route.md`, banc PH **+9,3 %**.
- ✅ **Gérer des voies aller-retour** (double voie v1, 2026-08-30). Voir item 9.5.
  Banc 20×20 vs `bench_road_current` : valeur +55 %, note −9 %. **Gardé.**
  Jointure aussi (item 0.7) : ne paie pas, défauts 0.
- 🔴 **File dynamique `catalogue -> lignes rentables -> reste de la file` rejetee en l'etat**
  (2026-08-31). Le premier essai round-robin payait toutes les taches tous les dix jours et perdait
  11,1 % de valeur (`docs/bench_continuous_queue.json`). La correction `dueYear`/`enabled` reporte
  bien les taches inutiles au cycle futur, mais son banc 5 graines x 20 ans baisse l'utilisation
  mesuree des opcodes de 9,6 % **et** le profit d'exploitation de 7,2 %, la performance de 9,6 %
  (0/5) et la valeur de 18,3 % (0/5) : ne pas l'adopter sur ce seul argument
  (`docs/opex_queue_deferred_20y_5seeds.json`).

  L'idee inspiree d'AAAHogEx a ensuite ete testee directement : catalogue, classement rentable,
  construction sans pause de la ligne 1 puis 2 puis 3, file circulaire, et conservation du
  classement lorsque la premiere ligne manque de cash. Banc apparie 5 graines x 5 ans :
  **profit attendu/Gopcode rail +28,9 %**, mais seulement 4/5 et `t = 1,29` (non etabli) ; en
  contrepartie **lignes -27,2 %**, revenu brut -26,7 %, performance -14,8 % et valeur -33,5 %.
  Le blocage strict sur une ligne bien classee mais chere immobilise le capital et casse la
  croissance composee.

  ✅ **Pipeline de précalcul sans blocage financier — FAIT (2026-08-31)** : découplage du calcul de tracé
  (`OpexPlanRailRoute`) et de l'exécution financière (`OpexExecuteRailPlan`). Pendant les périodes
  d'accumulation de cash (où 87 % des opcodes étaient dormants), l'IA précalcule les tracés A*, les quais
  et la double voie des meilleurs candidats. Dès que la trésorerie atteint le capital requis, la construction
  s'effectue instantanément.
  **Banc apparié 5 graines × 5 ans (`docs/bench_preplan_queue_5y.json`)** :
  - Valeur d'entreprise : **+3,63 %** (+11 374 £), **5/5 graines gagnantes**
  - Profit annuel : **+4,86 %** (+5 194 £), **5/5 graines gagnantes**
  - Profit dernier trimestre : **+4,85 %** (+1 293 £), **5/5 graines gagnantes**
  - Réglage `preplan_queue`, défaut 1.
- ✅ **Contribuer à la croissance d'une ville via des stations de bus/camions — FAIT (2026-08-31)** :
  Tâche basse priorité `town_growth` intégrée en fin de file annuelle (juste avant `repay`). Pour chaque
  ville desservie comptant $n$ gares ferroviaires/aéroports ($n < 5$), l'IA construit $5 - n$ stations de
  bus intra-urbaines pour atteindre le plafond maximal de 5 stations actives d'OpenTTD (`CountActiveStations = 5`)
  et maximiser l'accélération de croissance démographique sans pénaliser les investissements lourds.
  Réglage `town_growth`, défaut 1. Signe diagnostic `TG|year|townId|nBefore|nAfter`.
- ✅ **Réserve de trésorerie dynamique (`dynamic_cash_reserve`) et déploiement du cash — FAIT (2026-08-31)** :
  Remplacement de la constante statique `CASH_RESERVE = 50 000` par la fonction `OpexCashReserve()` :
  - **Dimensionnement dynamique** : calculé sur 3 mois de coûts d'exploitation de la flotte active, borné entre 15 000 £ (au démarrage) et 50 000 £ (en régime de croisière). Libère jusqu'à 35 000 £ de capital dès l'an 1.
  - **Déploiement du cash excédentaire** : levée du plafond mono-avion (`AIR_MAX_LINES_PER_YEAR = 1`, jusqu'à 5 liaisons aéroportuaires rentables) et remboursement de la dette via `_tryRepayLoan` quand la trésorerie dépasse `LOAN_REPAY_FLOOR` (300 000 £).
  - Réglage `dynamic_cash_reserve` (défaut 1) dans `info.nut`.
- ✅ **Limite d'opcodes de pathfinding dynamique (`dynamic_pathfinder_cap`) — FAIT (2026-08-31)** :
  Calibrage automatique du plafond d'itérations A* selon l'état de la compagnie :
  - **Démarrage / Réseau jeune** : Plafond modéré à **30 000 itérations** pour éviter d'épuiser des opcodes sur des tracés complexes quand des corridors directs faciles existent.
  - **Précalcul & Attente de trésorerie** : Plafond ouvert à **60 000 itérations** pour exploiter les opcodes dormants.
  - **Maturité du réseau** : Échelle de 30 000 à 60 000 itérations proportionnelle au nombre de lignes pour contourner les obstacles.
  - Réglage `dynamic_pathfinder_cap`, défaut 1 dans `info.nut`.
- ✅ **Exécution continue sans blocage (Suppression du Sleep(10 jours)) — FAIT (2026-08-31)** :
  Remplacement du `AIController.Sleep(74 * 10)` inconditionnel de la boucle principale par `AIController.Sleep(1)` (1 tick NoAI).
  - Élimine les latences de 10 à 130 jours in-game entre les tâches.
  - Cadencement annuel de `catalog` et `report`, et mensuel de `repay`.
  - **Banc 20 graines × 5 ans** : Valeur d'entreprise moyenne en hausse de **+17,5 %** (**298 631 £** vs **254 040 £**).
- ⚪ **Planter des arbres pour augmenter la réputation municipale (`tree_planting`) — ÉCARTÉ (2026-08-31)** :
  Implémentation du module `OpexBoostTownRating` (plantant des arbres pour relever la note locale au-dessus de 100).
  **Banc apparié 20 graines × 5 ans (`docs/bench_tree_planting_5y.json`)** :
  - `company_value` : **−17,05 %** (−84 572 £), $t = −6,62$, **0/20 graines gagnantes** (20/20 défavorables).
  - `profit` : **−31,57 %** (−12 490 £), $t = −7,19$, **0/20 graines gagnantes**.
  - `profit_year` : **−25,94 %** (−40 051 £), $t = −6,57$, **0/20 graines gagnantes**.
  
  **Cause de l'échec** : La note d'autorité locale initiale dans OpenTTD est déjà suffisante ($\ge -200$) pour construire des gares et arrêts sans refus. Planter des arbres de façon préventive draine inutilement la trésorerie au démarrage sans débloquer aucun nouveau corridor.
  ⚠️ **Réglage `tree_planting`, défaut 0 (ÉCARTÉ).**

  🔴 **RÉGRESSION : ce défaut a été perdu, puis remesuré et rétabli le 2026-09-01.** Entre le
  2026-08-31 et le 2026-09-01, le code est repassé à `TREE_PLANTING <- true` (`main.nut:68`) et
  `custom_value = 1` (`info.nut`) — **ce document disait 0 pendant que le code faisait 1**, et
  personne ne l'a vu pendant une journée entière de travail bâti sur cette base. Remesuré à
  3 ans, la perte est confirmée (`docs/bench_treeplanting_3y_20seeds.json`, 20 graines) :
  `company_value` **+22,1 %** en coupant (t = 2,42, **17/20 graines**), `profit` +26,8 %
  (t = 2,09), `profit_year` +20,1 %, et la dispersion se resserre (CV 63,8 % → 50,7 %). Défaut
  remis à **0** partout.

  **Leçon de méthode** : un défaut « adopté » dans ce document n'est PAS une garantie que le code
  l'applique. Avant de bâtir sur un réglage, **lire sa valeur dans `info.nut` et `main.nut`**, pas
  seulement ici. Une régression de défaut est invisible au banc si on ne mesure que des variantes
  entre elles.

  **Ce qui reste vivant, et qui n'est pas derrière ce réglage** : le recours **réactif** de
  `builder_air.nut` (`517` et `540`), qui appelle `OpexBoostTownRating` puis réessaie l'aéroport
  uniquement après un vrai `ERR_LOCAL_AUTHORITY_REFUSES`. C'est la règle voulue : **on ne plante
  que si une ville nous refuse un aéroport**. Le nettoyage du réglage devenu inutile est en §8.
- ⚪ **Ordre de chargement passagers rail (`pax_full_load`) — MAINTENU PAR DÉFAUT (2026-08-31)** :
  Comparaison entre le plein chargement forcé aux deux bouts (`pax_full_load=1`, `OF_FULL_LOAD_ANY`) et le départ partiel rapide (`pax_full_load=0`, `OF_NONE`).
  **Banc apparié 20 graines × 5 ans (`docs/bench_pax_full_load_5y.json`)** :
  - `company_value` : **+0,21 %** (+1 055 £), $t = +0,61$, 8/20 wins pour A, 8/20 wins pour B, 4 nuls.
  - `performance_history` : **+0,31 %** (+0,8 pt), $t = +0,63$.
  - `profit` : **−0,16 %**, $t = −0,06$.
  
  **Conclusion** : Le dimensionnement de la longueur des convois par OpexAI (`trainsForVolume` / `OpexRailNominalMaxWagons`) est déjà ajusté au tonnage mensuel des villes reliées. Le départ partiel immédiat fait rouler des convois à demi-vides dont les coûts de fonctionnement fixes absorbent le léger gain de rotation.
  ⚠️ **Défaut `pax_full_load=1` strictement maintenu.**
- ⚠️ **Gestion des marchandises complexes et chaînes de transformation secondaire (`complex_cargo`) — adopté le 2026-08-31 sur un banc sous le seuil officiel, NE RÉPLIQUE PAS à 10 ans (retest 2026-09-08).**
  Indexation au catalogue des villes acceptatrices pour les marchandises transformées (`Goods`, `Food`, `Water`, `Mail`) et génération des corridors Industrie $\rightarrow$ Ville dans `OpexFreightCandidates`.
  Permet d'alimenter les industries secondaires (Aciérie, Scierie, Raffinerie, Usine) et d'évacuer les marchandises à haute valeur ajoutée vers les centres urbains.

  🔴 **Chiffre d'origine périmé.** Banc apparié 20 graines × **5 ans seulement** (`docs/bench_complex_cargo_5y.json`) — sous le seuil officiel de validation du projet (`AGENTS.md` : « banc officiel 20 graines × 10 ans apparié avant toute adoption par défaut ») : `company_value` +4,27 % ($t=2,29$, $p<0,05$), `performance_history` +5,38 % ($t=3,10$, $p<0,01$, 16/20 graines gagnantes), `profit` +4,85 % ($t=1,71$), `profit_year` +3,81 % ($t=1,90$).

  ✅ **Retest officiel 20 graines × 10 ans (2026-09-08, `docs/bench_complex_cargo_10y_20seeds.json`), `OpexAI[complex_cargo=0]` contre `OpexAI[complex_cargo=1]` sur le dossier courant, 0 échec sur 40 parties : AUCUN EFFET SIGNIFICATIF.**

  | métrique | delta (0 vs 1) | t | victoires de `0` sur 20 |
  |---|---:|---:|---:|
  | `company_value` | −3,98 % | −1,14 | 9 |
  | `profit_year` | −4,42 % | −1,30 | 8 |
  | `profit` | −3,32 % | −0,73 | 9 |
  | `performance_history` | −1,06 % | −1,28 | 9 |
  | note de gare | −0,69 % | −0,90 | 6 |

  Le signe penche pour `complex_cargo=1` en moyenne, mais aucun $t$ n'approche la
  significativité, et le compte de victoires (9/20, 9/20, 8/20, 6/20) est proche du hasard pur —
  la signature d'une moyenne tirée par quelques graines à forte variance, pas d'un effet réel.
  Même motif que le pathfinder segmenté (A5, [[pathfinder_segmente_prototype]]) : un gain mesuré
  tôt (ici à 5 ans) qui s'évapore à l'horizon officiel. Pas de mode d'échec identifié — le
  mécanisme tourne, il ne rapporte simplement pas ce qu'annonçait le premier banc.

  ⚠️ **`complex_cargo = 1` reste le défaut** — résultat nul, pas négatif, et la fonctionnalité ne
  coûte rien de mesurable ; pas de raison de désactiver un vrai mécanisme de jeu sur un null
  result. Non exploré : si la carte 8×8 à `industry_density=4` du banc limite le nombre
  d'industries secondaires générées, ce qui bornerait structurellement l'effet mesurable ici sans
  que ça dise quoi que ce soit sur une carte plus dense.

---


---

## 📓 Journal détaillé (diagnostics et mesures de banc)

Les entrées datées (diagnostics, bancs, décisions adopté/rejeté) ont été archivées le 2026-09-06 dans `docs/journal_*.md`, un fichier par jour, pour que ce document reste chargeable. Rien n'est perdu : les références `§0 xxx` du reste de ce document restent valables, il suffit de grepper leur nom d'ordinal latin dans les journaux ci-dessous.

- `docs/journal_2026-08-29.md`
- `docs/journal_2026-09-01.md`
- `docs/journal_2026-09-02.md`
- `docs/journal_2026-09-03.md`
- `docs/journal_2026-09-04.md`
- `docs/journal_2026-09-05.md`
- `docs/journal_2026-09-06.md`

Commande : `grep -rn "0 <ordinal>" docs/journal_*.md` pour retrouver une section citée ailleurs (ex. `§0 undecies ter`).
