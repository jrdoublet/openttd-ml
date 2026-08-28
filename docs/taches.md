# Liste des tâches

Backlog du projet depuis la bascule vers `OpexAI` (2026-08-28). Les tâches faites sortent de cette
liste ; l'historique reste dans les journaux `docs/journal_*.md`.

---

## 1. À lire et intégrer (demandé le 2026-08-28)

À traiter comme `docs/mecanique_jeu.md` : **pas une copie du wiki, mais règle + conséquence pour la
conception**, avec ce qui est vérifié et ce qui ne l'est pas.

| page | ce qu'on espère en tirer |
|---|---|
| [Community/Pseudo canals](https://wiki.openttd.org/en/Community/Pseudo%20canals) | technique de terrain sur l'eau ; à évaluer surtout pour son coût en opcodes |
| [transporttycoon.net/rail1](https://www.transporttycoon.net/rail1) … [rail6](https://www.transporttycoon.net/rail6) | série sur la construction ferroviaire : signalisation, débit, tracés |
| [transporttycoon.net/junctions](https://www.transporttycoon.net/junctions) | conception de jonctions — pertinent dès qu'`OpexAI` aura plusieurs lignes qui se croisent |

✅ **[Manual/Tips](https://wiki.openttd.org/en/Manual/Tips) lue et intégrée (2026-08-28)** — voir
`docs/mecanique_jeu.md` §9. La plupart des heuristiques utiles étaient déjà couvertes ailleurs dans
le document (note de gare §3, note d'autorité §7, vitesse/virages §2) ; l'apport net : ordres
partagés (`AIOrder.ShareOrders`, non exploité), boucles de gare routière pour le futur mode Route,
et une piste non vérifiée sur les avions qui diffuseraient mieux leur influence que le rail.

✅ **[Manual/Industries](https://wiki.openttd.org/en/Manual/Industries) lue et intégrée
(2026-08-28)** — voir `docs/mecanique_jeu.md` §10. La table des chaînes de production ne change
rien au code : `catalog.nut` interroge déjà l'API dynamiquement plutôt que coder les chaînes en
dur. L'apport net, deux pistes non vérifiées : (1) la croissance d'une industrie source dépend du
% de sa production transportée — mécanisme jamais modélisé, à rapprocher de l'écart fret ~4-6x
encore ouvert (§3) ; (2) `difficulty.economy = false` confirme que la réduction de moitié de la
production primaire en récession est **sans objet** chez nous.

⚠️ Le contenu des pages restantes n'a **pas** été lu : les colonnes « ce qu'on espère » sont des
hypothèses de pertinence, pas des résumés.

---

## 2. Le prochain morceau de code

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
2. **Ne pas enfermer la ville dans nos propres voies** — reporté faute de mesure : vérifier
   d'abord si la croissance des villes desservies stagne réellement (`docs/mecanique_jeu.md` §5).
3. ✅ **Origines épuisées dans la fenêtre `TOP_K` : résolu (2026-08-28), en deux temps.** Exclusion
   des origines déjà servies à la génération (`OpexOriginServed` dans `candidates.nut`) plutôt
   qu'au filtrage — mais **seule, cette exclusion dégradait le résultat** (`company_value`
   2 067 089 contre 2 413 587 avant, emprunt non remboursé) : une fois les bonnes origines
   épuisées, l'IA s'engageait sur des candidats marginaux qu'un `TOP_K` engorgé bloquait
   *accidentellement* avant. Ajout d'un plancher `MIN_RATIO = 500` (profit/1000 itérations) qui
   corrige : **17 lignes** (contre 15), `company_value` **2 716 098** (+12,5 % vs avant tout
   correctif), emprunt remboursé. Détail dans `docs/opexai_croissance.md` §6, y compris un effet
   de bord découvert (plafond d'instrumentation des `AISign`, sans rapport avec ce correctif).

**Nouvelle priorité de fait** : l'item 2 (verrouillage de ville) devient le prochain morceau de
code — nécessite d'abord une mesure (croissance des villes desservies stagne-t-elle réellement ?)
avant tout changement de code.

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
- **Le modèle de coût A\*** (`candidates.nut`, table de nœuds) : ajusté sous OpenTTD 13.4 avec le
  pathfinder de `TrainLineAI`. La forme se transporte, les coefficients doivent être réajustés sur
  `OpexAI` sous 15.3.
- **Constantes HYPOTHÈSE restantes** : `SPEED_EFFICIENCY_PCT = 70` et `WAGONS_PER_TRAIN = 5` —
  ni l'une ni l'autre n'a été isolée par la mesure ci-dessus (le nombre de trains prédit a toujours
  matché le nombre réel exactement sur les 9 lignes, mais c'est la contrainte de fréquence
  `TARGET_HEADWAY_DAYS` qui dominait à chaque fois, jamais la capacité — `WAGONS_PER_TRAIN` reste
  donc non testé).

---

## 4. Mesures à faire dans le jeu plutôt qu'à citer

Reprend le §8 de `docs/mecanique_jeu.md`, complété.

1. ✅ Le réglage `plane_speed` réellement actif : `4`, le défaut, non surchargé — vérifié dans
   l'`openttdlab.cfg` d'un run `OpexAI` réel du 2026-08-28, pas supposé.
2. ✅ Économie « lisse » (`economy.type = 1` = `ET_SMOOTH`) confirmée dans notre config gelée, le
   défaut, non surchargé — vérifié dans l'`openttdlab.cfg` du 2026-08-28. À distinguer de
   `difficulty.economy` (recessions, réglage différent malgré le nom). Les probabilités de
   changement de production restent à recalibrer sur ce régime précis.
3. Le **rendement de vitesse effectif** d'un train (vitesse réelle / vitesse catalogue), sachant
   que le bridage en courbe descend à 61 km/h sur un virage à 90°.
4. ✅🔶 La **courbe de montée de la note d'une gare neuve**, dérivée de la source 13.4
   (`UpdateStationRating` dans `station_cmd.cpp`) — départ à `175/255` (pas 0), mise à jour tous
   les 2,5 jours (`185/74` ticks), pas de ±2 points vers la cible calculée une fois le premier
   ramassage enregistré ; ~2 mois pour résorber un écart de 50 points. Détail dans
   `docs/mecanique_jeu.md` §8.4. **Pas encore confirmé inchangé en 15.3** — lu sur la seule source
   locale disponible (13.4).
5. Le **barème croissance de ville / nombre de gares actives** : absent du wiki, présent dans le
   source (`town_cmd.cpp`, `UpdateTownGrowRate`) — à mesurer, pas à recopier de mémoire.
6. **Sonde de catalogue de 1950 à 2000** (`ai/CatalogProbe/`, changer `starting_year` et la durée) :
   les chiffres actuels ne couvrent que 1970-1989 et ratent l'électrification, l'aéroport
   INTERNATIONAL (1990) et le début du parc.

---

## 5. Banc

- **Porter le banc de 10 à 20 ans.** Toute l'évolution multimodale arrive après 1980 : aéroport
  METROPOLITAN (1980), COMMUTER (1983), parc routier +83 %, parc avion +38 %. Un banc à 10 ans
  mesure une partie où le rail est presque le seul mode qui progresse — ce qui nous désavantage
  précisément là où on veut se distinguer.
- **Augmenter le nombre de graines, pas les répétitions** : bruit intra-graine 4,1 % contre
  dispersion inter-graines de 26 %. Erreur-type de la moyenne à n=5 : 11,8 % ; à n=20 : 5,9 %.
- Le **face à face** dans une partie partagée, aux jalons seulement (décidé le 2026-08-28).
- **Plafond d'instrumentation `AISign` découvert (2026-08-28), non expliqué.** Tous les signs de
  diagnostic d'`OpexAI` sont posés sur la même tuile `(1,1)`, jamais nettoyés. Sur une campagne
  20 ans/graine 42, le rapport annuel (`OX`/`OW`/`OS`) s'est arrêté silencieusement 4 années avant
  la fin dans une mesure, 1 seule dans une autre — sans lien apparent avec le nombre total de
  signs déjà posés (pas un plafond fixe évident). La construction elle-même continue derrière
  (vérifié via le chunk `PLYR`, indépendant des signs) : seule l'observabilité est perdue. Risque
  latent pour tout banc porté à 20 ans (point ci-dessus) sur une IA qui construit beaucoup. Détail
  dans `docs/opexai_croissance.md` §6.
- Élucider le **non-déterminisme propre à AAAHogEx** (la plateforme, elle, est déterministe).
  🔶 Mécanisme confirmé par lecture de source (pas encore de test A/B, donc la causalité sur le
  non-déterminisme reste ouverte) :
  - `openttdlab.py:376-393` (mode `console-script`, celui utilisé en 15.3) programme un `save`
    console à chaque mois de jeu via des scripts `.scr` — ce n'est pas l'autosave du moteur
    (`autosave = off` dans notre `openttdlab.cfg`), mais un déclenchement externe mensuel.
  - Chaque `save` console appelle `Save()` d'AAAHogEx (`main.nut:4032-4105`), qui sérialise des
    caches volumineux (`landConnectedCache`, `cargoVtDistanceValues`, `estimateTable`, toutes les
    statics de route) ET s'auto-instrumente : un `AIController.GetOpsTillSuspend()` avant/après
    chaque sous-`Save()` plus un `HgLog.Info(...)` de concaténation de chaîne à chaque étape.
  - Donc l'hypothèse est confirmée **mécaniquement plausible** (travail réel et non trivial
    déclenché chaque mois, hors du chemin de décision normal de l'IA) mais pas encore **prouvée
    causale** : reste à faire tourner deux campagnes identiques avec/sans le `save` mensuel
    (ou avec logging désactivé) et comparer la dispersion.

---

## 6. Modes de transport, dans l'ordre décidé

1. ✅ **Rail** — étage 3 ci-dessus.
2. ✅ **Avion** — une liaison passagers entre deux grandes villes, validée sous OpenTTD 15.3.
   Aucun pathfinding ; son avantage n'est toutefois **pas** la vitesse : il vole au quart de sa
   vitesse affichée.
3. ✅ **Bateau** — une liaison passagers entre deux grandes villes côtières, avec validation
   bornée du graphe d'eau et dépôt construit sur la même composante. Voir
   `docs/opexai_multimodal.md`.
4. **Route** — prochain mode. Une desserte légère suffit aussi à déclencher la croissance d'une
   ville (une unité de cargo par 50 jours, jusqu'à 5 gares), pour un coût en opcodes sans commune
   mesure avec le rail.

Ne pas oublier deux composantes gratuites de la note de compagnie : **emprunt à zéro** (5 %) et
**8 types de cargo par trimestre** (5 %) — cette dernière plaide contre une IA 100 % passagers.

---

## 7. Reprises de l'ère `TrainLineAI` encore ouvertes

- **La reprise sur préfixe façon `RetryToBuild`**, en clean-room : 64 `TRKFAIL` dont la recherche
  était déjà payée pour zéro profit ; ~145 M récupérables estimés, soit 453 par itération contre
  156 en moyenne.
- **La politique d'abandon** : couper une recherche quand son rendement marginal attendu passe sous
  le rapport du meilleur candidat non essayé. Évaluable hors ligne sur les données v3. Motivation
  concrète mesurée sur `OpexAI` le 2026-08-28 : une tentative fret à 70 tuiles, ratio prédit correct
  (573, dans la zone acceptée par `MIN_RATIO`), a consommé **60 000 itérations pour rien** avant
  d'être abandonnée — `MIN_RATIO` (§2 ci-dessus) ne protège pas contre ce cas, seul un abandon en
  cours de recherche le peut. Détail dans `docs/opexai_croissance.md` §6.

---

## 8. Hygiène

- ✅ **Session du 2026-08-28 committée** en 5 commits (`a227281` banc/15.3, `f6095de` sonde de
  catalogue, `212c532` mécanique du jeu, `826a6fa` OpexAI, `ee3e370` cette liste). Historique local
  uniquement : le dépôt n'a **aucun remote**.
- ✅ `README.md` mentionnait déjà OpexAI/15.3 ; `docs/methode.md` a reçu une note en tête renvoyant
  vers le `README.md` (2026-08-28) — le corps du document reste volontairement celui de la
  campagne 13.4, il décrit un protocole historique.

---

## 9. Idées de fonctionnalités à évaluer (notées le 2026-08-28, pas encore priorisées)

- **Agrandir une gare existante** quand le stock d'un cargo déjà exploité devient trop important
  (capacité insuffisante face à la production captée).
- **Gérer les jonctions de rails** — pertinent dès qu'`OpexAI` a plusieurs lignes qui se croisent ;
  voir aussi la lecture en attente sur les jonctions en section 1.
- **Gérer des voies aller-retour** (double voie) pour permettre plusieurs trains simultanés sur le
  même parcours, plutôt qu'une seule voie à sens unique par ligne.
- **Gérer une file d'attente de tâches** (queue) plutôt que le déroulement actuel, pour ordonnancer
  les constructions/décisions.
- **Contribuer à la croissance d'une ville via des stations de bus/camions** (jusqu'à 5 gares,
  une unité de cargo par 50 jours) — recoupe le mode Route déjà prévu en section 6, mais posé ici
  comme objectif de croissance plutôt que comme mode de transport en soi.
- **Planter des arbres pour augmenter la réputation** (note de compagnie) — déjà identifié dans
  `docs/mecanique_jeu.md` comme le levier de rattrapage bon marché si la note stagne à cause du
  terrassement/destruction de bâtiments.
- **Budget de construction d'une ligne proportionnel au cash** (idée notée le 2026-08-28) : plafonner
  à ~90 % de la trésorerie disponible plutôt qu'à une valeur fixe, pour que le plafond suive la
  compagnie au lieu de la brider quand elle est riche.
  ⚠️ **Vérification faite : la valeur fixe de 200 000 soupçonnée existe bien, mais ce n'est pas un
  budget en argent.** C'est `PATHFINDER_MAX_COST` (`builder_rail.nut:24`), un plafond de *coût A\**
  (unités de pathfinding), sans rapport avec la trésorerie. Côté argent, `_tryBuild`
  (`main.nut:255`) compare déjà `GetBankBalance` au `candidate.capital` calculé par ligne, moins
  `CASH_RESERVE = 50 000` — donc déjà proportionnel au cash, pas un plafond fixe. L'idée reste
  évaluable, mais sur les bons paramètres : soit rendre `CASH_RESERVE` proportionnel (au lieu de
  50 000 fixes), soit revoir `PATHFINDER_MAX_COST` — deux choses distinctes, à ne pas confondre.
