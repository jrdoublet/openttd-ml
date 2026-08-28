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

**Ce qui vient maintenant, par ordre d'impact mesuré :**

1. **Rendre les lignes rentables.** Profit réel ~4 000/an par ligne contre ~40 000 prédits, et
   l'IA s'arrête à 3 lignes sans jamais rembourser son emprunt. `company_value = 1` : dernière du
   banc. **Le goulot n'est plus le calcul mais le capital** — l'utilisation du budget d'opcodes est
   tombée à 12 ‰.
2. **Calibrer `STATION_RATING_PCT`** : mesuré 22-82, typiquement ~50, contre 75 supposé.
3. **Comprendre la sur-estimation d'un facteur 10** de l'étage 1 (volume capté ? revenu unitaire ?
   frais réels ?). L'instrument existe désormais : notes de gare et profit réel par ligne.
4. **Ne pas enfermer la ville dans nos propres voies** — reporté faute de mesure : vérifier
   d'abord si la croissance des villes desservies stagne réellement (`docs/mecanique_jeu.md` §5).
5. **Desserrer `MIN_SEPARATION = 15`** — à évaluer : il peut être responsable de l'arrêt à 3 lignes
   autant que la trésorerie.

---

## 3. Calibrations en attente

- **Le modèle économique** (`economy.nut`) : niveau ~10× trop bas, et son classement préfère la
  bande 25-45 tuiles là où la campagne place l'optimum en 45-70. **Bloqué** par la mesure de volume
  de l'étage 3.
- **Le modèle de coût A\*** (`candidates.nut`, table de nœuds) : ajusté sous OpenTTD 13.4 avec le
  pathfinder de `TrainLineAI`. La forme se transporte, les coefficients doivent être réajustés sur
  `OpexAI` sous 15.3.
- **Les trois constantes marquées HYPOTHÈSE** : `SPEED_EFFICIENCY_PCT = 70`,
  `STATION_RATING_PCT = 75`, `WAGONS_PER_TRAIN = 5`.

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

1. **Rail** — étage 3 ci-dessus.
2. **Avion** — aucun pathfinding, donc le meilleur profit par opcode. ⚠️ Son avantage n'est **pas**
   la vitesse : il vole au quart de sa vitesse affichée.
3. **Route** — et pas seulement comme mode de transport : une desserte légère suffit à déclencher
   la croissance d'une ville (une unité de cargo par 50 jours, jusqu'à 5 gares), pour un coût en
   opcodes sans commune mesure avec le rail.
4. **Bateau** — en dernier.

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
