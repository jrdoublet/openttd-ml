# Liste des tâches

Backlog du projet depuis la bascule vers `OpexAI` (2026-08-28). Les tâches faites sortent de cette
liste ; l'historique reste dans les journaux `docs/journal_*.md`.

---

## 1. À lire et intégrer (demandé le 2026-08-28)

À traiter comme `docs/mecanique_jeu.md` : **pas une copie du wiki, mais règle + conséquence pour la
conception**, avec ce qui est vérifié et ce qui ne l'est pas.

| page | ce qu'on espère en tirer |
|---|---|
| [Manual/Tips](https://wiki.openttd.org/en/Manual/Tips) | heuristiques de joueur transposables en règles d'allocation |
| [Manual/Industries](https://wiki.openttd.org/en/Manual/Industries) | chaînes de production, cargos acceptés/produits par type — nourrit directement l'étage 1 fret |
| [Community/Pseudo canals](https://wiki.openttd.org/en/Community/Pseudo%20canals) | technique de terrain sur l'eau ; à évaluer surtout pour son coût en opcodes |
| [transporttycoon.net/rail1](https://www.transporttycoon.net/rail1) … [rail6](https://www.transporttycoon.net/rail6) | série sur la construction ferroviaire : signalisation, débit, tracés |
| [transporttycoon.net/junctions](https://www.transporttycoon.net/junctions) | conception de jonctions — pertinent dès qu'`OpexAI` aura plusieurs lignes qui se croisent |

⚠️ Le contenu de ces pages n'a **pas** été lu : les colonnes « ce qu'on espère » sont des
hypothèses de pertinence, pas des résumés.

---

## 2. Le prochain morceau de code

**✅ Étage 3 fait** (`ai/OpexAI/builder_rail.nut`, 2026-08-28) : 3 lignes sur 3 construites en
10 ans, 56 véhicules. Comptabilité d'opcodes branchée, rollback sur échec, réserve de trésorerie.

**Tout l'ancien blocage capital est résolu (session du 2026-08-28)** : pax (`b09f23e`), fret
(`abd641b`), `MIN_SEPARATION`/`ORIGIN_SEPARATION` (`5433518`), remboursement d'emprunt (`44e0b14`),
détection et vente des lignes fret mortes (`e884358`). Graine 42/20 ans : 3 lignes bloquées →
**15 lignes**, `company_value` 1 → **2 413 587**, emprunt à **0**. Détail dans
[[opexai_squelette]].

**Ce qui reste, par ordre d'impact mesuré :**

1. **Écart prédit/réel du fret encore ~4-6x**, indépendant de la fermeture d'industrie (déjà
   traitée) — voir §3 ci-dessous, non résolu.
2. **Ne pas enfermer la ville dans nos propres voies** — reporté faute de mesure : vérifier
   d'abord si la croissance des villes desservies stagne réellement (`docs/mecanique_jeu.md` §5).
3. **Origines épuisées dans la fenêtre `TOP_K`** : les stalles restants de la campagne 20 ans sont
   désormais mesurés comme une saturation réelle des candidats disponibles (`_tooClose` à
   `near=20/far=0`), pas un seuil mal réglé. À traiter dans `candidates.nut` (`TOP_K` plus large,
   ou exclusion des origines déjà servies à la génération plutôt qu'au filtrage).

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
- ⚠️ **Reste ouvert** : l'écart prédit/réel du fret reste ~4-6x même après `STATION_RATING_PCT`
  seul (le fret n'a pas le biais ville-entière du pax, donc `TOWN_CATCHMENT_SHARE_PCT` ne s'y
  applique pas — un autre facteur, non identifié, y joue un rôle comparable). Non mesuré.
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

1. Le réglage `plane_speed` réellement actif (le quart est le défaut).
2. Économie « lisse » ou TTD classique dans notre config gelée — les probabilités de changement de
   production en dépendent.
3. Le **rendement de vitesse effectif** d'un train (vitesse réelle / vitesse catalogue), sachant
   que le bridage en courbe descend à 61 km/h sur un virage à 90°.
4. La **courbe de montée de la note d'une gare neuve** (2 points par 2,5 jours ⇒ ~2 mois annoncés),
   pour escompter correctement le revenu des premiers mois.
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
- Élucider le **non-déterminisme propre à AAAHogEx** (la plateforme, elle, est déterministe).
  Hypothèse non testée : le `save` mensuel appelle son `Save()`, lourd et auto-instrumenté.

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
  le rapport du meilleur candidat non essayé. Évaluable hors ligne sur les données v3.

---

## 8. Hygiène

- ✅ **Session du 2026-08-28 committée** en 5 commits (`a227281` banc/15.3, `f6095de` sonde de
  catalogue, `212c532` mécanique du jeu, `826a6fa` OpexAI, `ee3e370` cette liste). Historique local
  uniquement : le dépôt n'a **aucun remote**.
- `README.md` et `docs/methode.md` ne mentionnent ni la bascule vers 15.3, ni `OpexAI`.
