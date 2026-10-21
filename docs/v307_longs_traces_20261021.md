# V307 — longs tracés rail : mesure et plan (21 octobre 2026)

Demande utilisateur du 21/10 : devenir bien meilleur sur les longs tracés, qui rapportent beaucoup
et sont sous-estimés, sans rester bloqué des mois dans un A*, en anticipant une taille de
segmentation adaptée à ces projets.

Branche `v307` (base master `d50d1d7a`). Trois réglages de mesure seule, défaut 0 :
`v307_long_probe` (N paires par tranche), `v307_probe_year` (année de la sonde),
`v307_abnd_autopsy` (autopsie des abandons de production). Module `ai/OpexAI/probe_v307.nut`,
contrats `sweeps/test_v307_long_probe.py`, lecteur `sweeps/diag_v307_long_paths.py`.

## 1. Le banc de mesure

**Sonde de paires longues** (`v307_long_probe`). Au 1er janvier de l'année choisie, la partie est
gelée (rien n'est construit pendant la sonde). On tire N paires de villes (les 40 plus grandes,
au plus 3 paires par ville) et N paires fret (les 15 industries qui produisent le plus pour chaque
cargo, vers toute industrie acceptante) par tranche Manhattan 120-179, 180-249 et 250-349. Les
quais sont posés par `OpexStationPlans`, comme en production. Trois bras par paire :

- **base** : la recherche segmentée de production (poids, coûts V294 et moteur natif V296 aux
  défauts de master), budget 20 000 itérations au lieu de 5 000. `cap_ok` = réussi en moins de
  `HARD_ITERATION_CAP` = 5 000, donc au plafond actuel.
- **coarse** : A* sur des blocs de 8×8 tuiles, chacun échantillonné en 5 points (hauteur, eau,
  obstacles), 8 voisins, heuristique octile admissible.
- **guided** : la même recherche de production, avec le couloir grossier (dilaté d'un bloc) en
  `guideTiles` : coût ×0,5 dedans, ×2 dehors.

Chaque tracé est repricé par la fonction de coût commune sans guide, ce qui rend les bras
comparables. On journalise itérations, opcodes, jours de jeu et segments.

**Autopsie des abandons** (`v307_abnd_autopsy`). Après chaque `ABND` d'une recherche primaire de
production, deux A* frais, non segmentés et bloquants, sont lancés à 20 000 itérations : aller
(A→B) et inverse (B→A), avec les mêmes quais, interdictions, poids et moteur. Une file ouverte
vidée (`NOPA`) prouve que le but est inaccessible sous ces contraintes ; `CAP` signifie budget
épuisé ; `OK` signifie que le plafond de production manquait.

## 2. Résultats

### 2.1 Sonde 1970-1971 (smokes, graine 42)

9 paires de 158 à 314 tuiles, toutes trouvées en un segment, en 120 à 290 itérations, 0,3 à
0,8 M opcodes et 1 à 5 jours de jeu. Le guidage donne des tracés plus chers dans 6 cas sur 9.

### 2.2 Sonde 1973, duel, 6 graines (`v307_long_y3_6x7_20261021`)

107 paires, 2 sans quai.

| Type | Tranche | n | Trouvés | Sous 5 000 it. | Itérations (médiane) | Itérations (max) | Jours (médiane) | Jours (max) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| villes | 120-179 | 18 | 18 | 18 | 691 | 1 318 | 5,5 | 11 |
| villes | 180-249 | 18 | 17 | 16 | 333 | 9 743 | 3 | 53 |
| villes | 250-349 | 18 | 18 | 18 | 508 | 1 900 | 5 | 15 |
| fret | 120-179 | 17 | 15 | 15 | 261 | 2 642 | 3 | 15 |
| fret | 180-249 | 18 | 17 | 16 | 356 | 5 396 | 4 | 31 |
| fret | 250-349 | 16 | 14 | 14 | 535 | 4 314 | 5,5 | 25 |

- **Un long tracé vers un site neuf est facile** : 99 sur 105 sont trouvés, dont 97 sous le
  plafond actuel. La médiane est de 3 à 5,5 jours de jeu, même au-delà de 250 tuiles. La longueur
  réelle vaut 0,94 à 1,02 fois la distance Manhattan.
- **Quand un tracé échoue, il échoue cher** : 20 000 itérations, 18 à 22 M opcodes, **100 à 118
  jours de jeu**. Au plafond de production (5 000), un abandon coûte donc environ un mois.
- Les 6 échecs se rangent en deux familles :
  - **extrémité enclavée (4 sur 6)** : la destination 15 de la graine 100 échoue depuis deux
    sources, dont une fois en `NOPA` (preuve) ; la source 23 de la graine 7 échoue vers deux
    destinations. Le guidage ne change rien.
  - **piège avec grand détour (2 sur 6)** : 171 tuiles à vol d'oiseau donnent un tracé réel de
    296 tuiles. La recherche de production échoue à 20 000 itérations, le couloir grossier la
    sauve en 11 743 et 3 845 itérations.
- **Le guidage par défaut est rejeté** : sur 98 paires trouvées par les deux bras, le tracé
  guidé coûte en médiane 1,23 fois le tracé de base (11 seulement sont moins chers), avec 16 %
  d'opcodes en plus.
- **Le grossier** coûte 0,2 M opcodes en médiane. Il prédit bien le coût du tracé (corrélation
  0,85), mais mal son surcoût dû au terrain (0,40). Il surestime la longueur (réel/grossier
  0,87). Une seule paire est déclarée `NOPA` par le grossier, alors que la base la trouve (île à
  bords étroits).

### 2.3 Sonde 1976 (`v307_long_y6_6x10_20261021`)

101 paires, 5 sans quai, 95 cherchées par les deux bras.

| Type | Tranche | n | Trouvés | Sous 5 000 it. | Itérations (médiane) | Itérations (max) | Jours (médiane) | Jours (max) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| villes | 120-179 | 18 | 15 | 12 | 1 632 | 14 533 | 10 | 80 |
| villes | 180-249 | 18 | 17 | 15 | 631 | 14 399 | 6 | 85 |
| villes | 250-349 | 18 | 17 | 14 | 867 | 18 419 | 8 | 92 |
| fret | 120-179 | 11 | 11 | 11 | 1 141 | 1 895 | 8 | 13 |
| fret | 180-249 | 17 | 14 | 12 | 1 120 | 8 392 | 8 | 54 |
| fret | 250-349 | 14 | 13 | 10 | 1 274 | 11 279 | 11 | 62 |

- **Trois ans plus tard, la carte s'est refermée.** Les recherches restent faciles en médiane
  (6 à 11 jours), mais **13 tracés faisables sur 86 dépassent le plafond de 5 000** (2 sur 99
  en 1973). Ils demandent de 5 271 à 18 419 itérations, soit 32 à 92 jours : la production les
  abandonne aujourd'hui alors qu'ils existent. Ce sont surtout des tracés de villes (8 sur 13),
  longs en réalité (186 à 410 tuiles posées).
- **9 échecs sur 95** (6 en 1973). 8 échouent aussi en guidé, et ils se regroupent par
  extrémité : la source fret 23 de la graine 7 trois fois (vers 25 et 50), la destination 50
  deux fois, et plusieurs villes en graine 100. **L'enclavement d'extrémité domine toujours**,
  côté source comme côté destination. Une seule paire est sauvée par le guidage (228 tuiles,
  1 181 itérations).
- **Le couloir grossier n'est plus un secours fiable** : des 13 tracés lents, le guidé en
  trouve 6 plus vite, mais en perd 7 (`ABND` à 20 000). Sur l'ensemble, le guidé trouve 74
  paires contre 86 en base, avec un tracé 1,14 fois plus cher en médiane.
- Le grossier reste fidèle : corrélation de 0,87 avec le coût réel, 0,58 avec le surcoût dû au
  terrain, 0,24 M opcodes, un seul faux `NOPA`.

### 2.4 Abandons de production : quatre campagnes à `decision_log` déjà faites

`v302_mech`, `v303_before`, `v304_before` et `v304_mech` : 12 parties de 10 ans, 745 tentatives
rail (`RAIL_ATTEMPT`, appariées à `PROJECT_CHOSEN` par src/dst).

- 460 `OK`, 68 `ABND`, 159 `SITEAB`, 28 `TRKFAIL`, 5 `NOPA`.
- **Durée du choix à la fin de la tentative** : `OK` 10 jours en médiane (q90 29), `ABND`
  **75 jours** (q90 122). Les abandons cumulent 5 391 jours contre 7 492 pour les réussites :
  **42 % du temps des tentatives rail part dans des abandons.**
- **Taux d'abandon par année** : 1972 2 %, 1973 10 %, 1974 23 %, 1975 38 %, 1976 33 %,
  1977 47 %, 1978 29 %, 1979 52 %. Ce taux suit l'encombrement de la carte, pas la longueur :
  dans `v304_before`, des tracés de 23 et 67 tuiles sont abandonnés en 1977.
- **Répétitions** : 27 abandons sur 68 retombent sur une destination déjà abandonnée, et 19 sur
  une source déjà abandonnée. Dans `v304_before`, la destination 23317 (graine 100) a été
  desservie une fois en 1972, puis abandonnée 6 fois depuis 4 sources entre 1972 et 1979. Les
  paires sont aussi reprises après expiration de la mémoire d'abandon (1972→1975, 1973→1978,
  1975→1979).
- **Jointures** : 30 abandons sur 68 visent une destination partagée (`join_end=B`,
  `shared_dest=1`, V178/V179), contre 153 réussites sur 460. Le taux d'abandon est de 16 % en
  jointure contre 11 % hors jointure.

### 2.5 Autopsies (`v307_autopsy_3x10_20261021`)

3 graines × 10 ans, duel, `decision_log`. Chaque `ABND` primaire de production (budget 5 000,
segmenté) est rejoué deux fois avec un pathfinder neuf à 20 000 itérations : **aller** (des
quais A vers les quais B, comme la production) et **inverse** (de B vers A). 12 abandons
autopsiés ; 102 tentatives rail, dont 75 `OK` et 10 `ABND`. L'autopsie est bloquante, elle
rallonge chaque abandon d'environ 150 jours : les durées et la trajectoire de cette campagne ne
sont pas celles de la production.

| Graine | Année | Type | Dist. | Jointure | Quais A / B | Aller (20 k) | Inverse (20 k) |
|---|---|---|---:|---|---|---|---|
| 42 | 1972 | fret | 101 | — | 12 / 12 | échec | **OK, 2 672 it.** |
| 42 | 1974 | fret | 172 | B | 12 / 7 | échec | **OK, 6 540 it.** |
| 100 | 1975 | fret | 186 | — | 12 / 4 | échec | **OK, 3 225 it.** |
| 100 | 1976 | fret | 177 | B | 12 / **1** | échec | **OK, 8 316 it.** |
| 42 | 1976 | fret | 133 | — | 12 / 8 | échec | **OK, 5 006 it.** |
| 100 | 1977 | fret | 207 | B | 12 / **1** | échec | **OK, 5 900 it.** |
| 100 | 1978 | fret | 196 | — | 12 / **1** | échec | `NOPA` en **4 it.** |
| 7 | 1976 | villes | 28 | — | 12 / 12 | échec | échec |
| 7 | 1978 | villes | 65 | — | 12 / 12 | OK, 4 860 it. | OK, 9 906 it. |
| 7 | 1979 | villes | 68 | — | 12 / 12 | échec | échec |
| 100 | 1979 | villes | 77 | — | 12 / 12 | OK, 12 352 it. | — |

- **Fret : la recherche part du mauvais côté.** Les 7 abandons fret échouent à 20 000
  itérations en aller. En inverse, 6 sont trouvés en 2 700 à 8 300 itérations, et le 7e est
  prouvé impossible en 4 itérations. La destination fret est le côté étroit : 1 à 8 quais contre
  12 à la source, et ce sont des puits déjà rejoints (`join=B`, destination 29140 deux fois).
  Partie de la source, l'A* inonde le pourtour de la poche où se trouve la destination. Partie
  de la destination, elle sort de la poche par le seul passage, puis file vers une source
  ouverte. **C'est le problème de destination que l'utilisateur a pointé**, et il a un remède
  presque gratuit : chercher depuis le côté étroit.
- **Le côté étroit se reconnaît à l'avance** : `nb` (nombre de quais B) est petit, et la
  destination est jointe.
- **Villes** : la ville 53372 de la graine 7 est enclavée dans les deux sens (deux fois). Deux
  autres tracés existent, en 4 860 et 12 352 itérations ; le premier tient sous 5 000 avec un
  pathfinder neuf, mais il a échoué en production. Le préfixe figé de la segmentation coûte donc
  aussi des tracés.
- Une seule preuve d'enclavement (`NOPA`) tombe, et elle tombe en 4 itérations : la sonde
  inverse V294f (300 itérations) l'aurait vue, si elle distinguait `null` de `false` (tâche 1.3).

### 2.6 Chercher depuis le côté étroit : diagnostics 3×10 (tâche 1.0, branche `v307n`)

Graines 42, 7 et 100, 10 ans, duel, `decision_log`. Référence : `v303_before_3x10_20261021`
(défauts de master). Les recherches primaires passent surtout par le vivier stock
(`_startRailStockSearch`), sans sonde inverse : le premier smoke l'a montré, et les deux
chemins sont branchés.

| Variante | Abandons | Jours d'abandon | Recherches réussies | Jours des réussites (médiane) | Profit 3 graines |
|---|---:|---:|---:|---:|---:|
| Référence (mode 0) | 8 | 718 | 77 | 9 | 12,08 M£ |
| Mode 4 : A* continu inverse, poids de base | 20 | 1 985 | 70 | 13 | 12,36 M£ |
| **Mode 6 : recherche segmentée de production, quais échangés** | **2** | **125** | 78 | 8 | 11,93 M£ |
| Mode 5 : idem, côté étroit strict (B a moins de quais), sans tout le fret | 6 | 430 | 76 | 9 | 12,48 M£ |

- **Mode 4, négatif** : 7 des paires qu'il abandonne étaient trouvées par l'aller de
  production. L'A* continu au poids de base, sans le poids adaptatif 200→400 ni les retours en
  arrière de la recherche segmentée, est moins bon que la production, même depuis le bon côté.
- **Mode 6** : c'est la même recherche, mais partie de la destination (quais B moins nombreux,
  ou fret). **Les abandons tombent de 8 à 2, et leurs jours de 718 à 125.** Le profit sur 3
  graines (−1 %) ne dit rien : c'est un diagnostic.
- **Mode 5** : 31 recherches inversées seulement, 6 abandons. Le gain du mode 6 vient surtout
  du fret à quais égaux (12/12), comme la graine 42 de 1972 dans l'autopsie : la destination
  fret est le côté étroit même quand le nombre de quais ne le montre pas.
- Porte A 40×3 du mode 6 : GitHub run 39613351704.

## 3. Ce que la mesure change

1. **La longueur n'est pas le problème en 1973, elle le devient en 1976.** Sur la carte de 1973,
   l'A* actuel trouve en quelques jours 97 longs tracés sur 105 vers des sites neufs. En 1976,
   15 % des tracés faisables dépassent le plafond de 5 000 itérations (jusqu'à 18 k et 92
   jours). Le budget redevient une question, mais seulement en tâche de fond : 92 jours dans le
   créneau principal, c'est le coût d'un abandon.
2. **Le problème, ce sont les extrémités impossibles, de plus en plus nombreuses avec le temps.**
   Elles coûtent 75 jours chacune, et une fois sur deux la même extrémité avait déjà échoué.
3. **L'avertissement du 03/10 s'applique** (mémoire « le créneau rail n'est pas la
   contrainte »). Le plafond de 90 jours et la mémoire d'échec d'upgrade ont libéré du temps de
   créneau, aussitôt ravalé par d'autres abandons primaires. Le seul levier non réfuté est
   **amont** : reconnaître un candidat impossible **avant** de le chercher, pour retirer la
   demande au lieu de la déplacer. Le succès se juge donc au **nombre et à la durée totale des
   `ABND` primaires**, pas au temps libéré.
4. **Le couloir grossier n'est ni un bon défaut ni un secours fiable.** Il sauve des pièges à
   détour (2 sur 2 en 1973, 6 sur 13 tracés lents en 1976), mais il en perd autant en 1976, et
   il renchérit les tracés ordinaires (×1,14 à ×1,23). Un guidage plus doux reste à tester
   (2.2) avant d'en faire quoi que ce soit.
6. **Les extrémités elles-mêmes** (proposition de l'utilisateur du 21/10, vérifiée dans le code) :
   `OpexStationPlans` (`builder_rail.nut:283`) ne passe pas par un `AIList`. C'est une spirale
   d'anneaux de rayon 0 à 30 qui **s'arrête aux 12 premiers quais valides** (`MAX_STATION_PLANS`,
   le classement V207 qui en échantillonne davantage est à 0). Les 12 plans sont donc les plus
   proches du centre, collés les uns aux autres et souvent du même côté. Si cette poche est
   enclavée, les 12 extrémités le sont toutes, et le rayon de 30 n'est jamais atteint.
   Ensuite, une destination rejointe reçoit un quai parallèle serré contre l'existant (V178,
   V179, V264), d'où les 16 % d'abandons en jointure contre 11 %. **Mise en garde** : V296c
   (21/10) a construit tout le carré en `AITileList` natif, et c'était 10 fois plus cher, parce
   que la spirale sort tôt. Une liste plus généreuse doit être plus petite que le carré : la
   zone de captage de l'industrie (`AITileList_IndustryAccepting/Producing`), et non le carré
   de 61 tuiles de côté.
5. **Taille de segmentation** : aujourd'hui 2 000 itérations, avec un préfixe figé à chaque
   coupure. Les tracés faisables n'en ont pas besoin (un segment). Les échecs passent par 7 à 11
   segments : chaque coupure fige un préfixe qui peut s'enfoncer dans le piège. Le remède est le
   secours par couloir, pas un autre découpage. Le découpage géographique (étape 5) ne reste
   utile que si les tracés faisables dépassent un jour le plafond.

## 4. Plan

Complexité : **C1** = une fonction, moins d'une heure, délégable (agy, codex) ; **C2** = un module
et ses contrats, une demi-journée ; **C3** = plusieurs modules ou un risque de comportement, un
jour et plus, conception requise ; **C4** = architecture, plusieurs jours.
Priorité : **P1** maintenant ; **P2** après les mesures de P1 ; **P3** conditionnel.

Chaque levier suit le protocole : contrats, smoke 1×1, diagnostic de mécanisme 3×10 avec
`decision_log` sur le VPS, porte A 40×3 GitHub, porte B 20×10 par l'utilisateur sur son PC. Les
petits leviers d'une même famille sont évalués ensemble sur une branche d'intégration (règle du
20/10). Le critère de mécanisme commun à toutes les étapes est **le nombre d'`ABND` primaires et
leurs jours cumulés**, lus dans `RAIL_ATTEMPT`.

### Étape 0 — Mesurer (branche `v307`)

| # | Tâche | P | C | État |
|---|---|---|---|---|
| 0.1 | Sonde de paires longues (villes et fret, 3 tranches, 3 bras) | P1 | C2 | ✅ codée, smokes 1970/1971, campagne 1973 lue |
| 0.2 | Sonde 1976 (6 graines, duel) | P1 | C1 | ✅ lue (§ 2.3) |
| 0.3 | Autopsie des `ABND` de production (aller et inverse, 20k) | P1 | C2 | ✅ 3×10 lue (§ 2.5) |
| 0.4 | Lecteur `diag_v307_long_paths.py` (bras, grossier, guidage, autopsies) | P1 | C1 | ✅ |
| 0.5 | Inventaire des `RAIL_ATTEMPT` : durée, année, jointure, répétitions par extrémité (`sweeps/diag_v307_rail_attempts.py`) | P1 | C1 | ✅ sur 12 parties (§ 2.4) |
| 0.6 | ✅ (§ 2.5) Classer chaque `ABND` de l'autopsie : but enclavé (`NOPA`), budget (`OK` à plus de 5 000), piège (`CAP` aller, mais `OK` guidé) ; croiser avec la jointure, la distance, l'année et le type | P1 | C1 | après 0.3 |

### Étape 1 — Ne jamais chercher deux fois une extrémité impossible

| # | Tâche | P | C | Dépend de |
|---|---|---|---|---|
| 1.0 | **Chercher depuis le côté étroit** (autopsie § 2.5) : si la destination a moins de quais que la source (`plansB.len() < plansA.len()`, ou destination jointe), lancer la recherche de B vers A et retourner le tracé. La voie est sans sens, il suffit d'inverser la liste et d'échanger les rôles des quais pour la pose. Réglage à 0. Mesure : `ABND` fret primaires et jours cumulés, diagnostic 3×10 puis porte A 40×3. Cas particulier de V303 (b), la recherche alternée de codex ; mais l'alternance ne laisse à l'inverse qu'environ 2 650 itérations (plafond partagé 5 300), trop peu pour 3 des 6 cas. **Codée** (branche `v307n` `30f2ab21`, sur V303 `0bf8d611`) : `v303_reverse_mode` = 3 (B a moins de quais que A) ou 4 (3, plus tout le fret) ; hors côté étroit, chemin historique. Diagnostics 3×10 en cours, référence `v303_before_3x10_20261021` (8 `ABND`, 718 jours). | **P1** | C2 | — |
| 1.1 | **Mémoire d'échec par extrémité** : tuile source ou destination → date du dernier `ABND`/`NOPA`. Tout candidat qui la touche est écarté pendant M mois, sauf si un événement de carte proche a eu lieu (rectangle d'invalidation C76, gare neuve ou retirée). Réglage à 0 ; sauvegarde à traiter (sinon la mémoire est perdue au rechargement, accepté au premier essai). | P1 | C2 | 0.5 |
| 1.2 | **Abandon de paire persistant** : `_abandonedPairs` (clé `type|cargo|src|dst`, `lines.nut:279`) expire après `ABANDON_COOLDOWN_DAYS` × nombre d'échecs, soit 1 an puis 2 ans, plafonné à 5 (`globals_post.nut:38`, `_pruneAbandonedPairs`) : d'où les reprises 1972→1975, 1973→1978, 1975→1979. Ne reprendre une paire abandonnée en `ABND` que sur un événement de carte proche d'une extrémité. | P1 | C1 | 0.5 |
| 1.3 | **Preuve d'enclavement bon marché avant l'aller** : la sonde inverse V294f (`FindPath(300)`) confond `null` (file vidée = inaccessible) et `false` (budget). Retourner une issue `NOPA` définitive sur `null`, et mesurer à quel budget inverse (300, 800, 2 000) la preuve tombe pour les `NOPA` de l'autopsie. | P1 | C1 | 0.3 |
| 1.4 | **Même preuve côté source** : sonde aller courte, file vidée ⇒ source enclavée, mise en mémoire 1.1. | P2 | C1 | 1.3 |
| 1.5 | **Jointure bloquée** (V178/V179/V264) : si les quais joints d'une gare existante sont enclavés par la première voie, essayer les quais en éventail V264 ou une gare neuve voisine avant d'abandonner. Diagnostic d'abord : part des `NOPA` de l'autopsie en `join=B`. | P2 | C3 | 0.6 |
| 1.7 | **Diagnostic des extrémités échouées** : pour chaque `ABND`/`NOPA` (autopsie et sonde), journaliser la dispersion des plans (distance max au centre, nombre d'octants couverts) et ce qui borde chaque quai dans un rayon de 3 tuiles : notre rail, rail rival, eau, maisons, relief. Il répond à deux questions : la poche est-elle enclavée par nous, et un autre octant aurait-il été libre ? | P1 | C1 | 0.3 |
| 1.8 | **Sites dispersés** : fret, on part de `AITileList_IndustryAccepting/Producing` (rayon de captage), on filtre plat et constructible par valuateurs, puis on garde au plus 3 plans par octant au lieu des 12 plus proches. Villes, la spirale continue au-delà de 12 plans jusqu'à couvrir 4 octants ou le rayon. Contrat d'opcodes : rester sous le coût actuel ×1,5, à mesurer comme V296c (`OpexStationPlans` 48,7 k par appel aujourd'hui). | P1 | C2 | 1.7 |
| 1.9 | **Gares de puits à 2-4 quais dès la construction** (proposition de l'utilisateur du 21/10) : pour une destination qui accepte plusieurs lignes (centrale, usine, grande ville), poser N quais parallèles d'un coup (`BuildRailStation(..., N, longueur, ...)`) ; réserver leurs entrées (tuiles interdites à l'A* de la première ligne, sinon notre propre voie les enclave) ; enregistrer les quais libres sur la gare. V178/V179 utilisent ensuite un quai réservé avant tout quai parallèle improvisé. À chiffrer au smoke : surcoût de pose (quais et terrain), entretien des quais vides. Différent de V190 (double voie, close à −103 k) : ni seconde voie, ni boucle, ni signaux. | P2 | C3 | 1.7 (si l'enclavement de puits vient de notre propre voie) |
| 1.10 | **Choix du N de 1.9** : nombre de lignes rejointes par destination dans les campagnes `decision_log` (`join_end=B`, `shared_dest`). Si 80 % des puits ne reçoivent jamais de 2e ligne, on réserve les quais seulement aux catégories qui en reçoivent. | P2 | C1 | 0.5 |
| 1.6 | Branche d'intégration 1.1 + 1.2 + 1.3 : diagnostic 3×10 (`ABND` primaires et jours cumulés), puis porte A 40×3. Si l'effet n'apparaît qu'après 1973, ajouter un 40×5 diagnostic, sans changer la règle. | P1 | C1 | 1.1-1.3 |

### Étape 2 — Sortir des pièges au lieu d'y rester

| # | Tâche | P | C | Dépend de |
|---|---|---|---|---|
| 2.1 | **Détecteur de stagnation** : meilleure distance au but atteinte toutes les 500 itérations ; sans progrès sur 2 000 itérations, la recherche est déclarée piégée. Journal seul d'abord : précision sur les `ABND` contre les `OK` lents (seuils calés sur 0.2 et 0.3). | P2 | C2 | 0.3 |
| 2.2 | **Secours par couloir grossier** : sur piège (2.1), ou à l'abandon, une seule relance guidée par le couloir. Le guidage actuel coûte 1,23 fois en coût de tracé : tester un guidage plus doux (×1,25 hors couloir, couloir de 2 blocs) sur les paires V307 avant toute partie. | P2 | C2 | 2.1 |
| 2.3 | **Abandon précoce** : un piège sans secours possible (grossier `NOPA`, ou secours échoué) s'arrête tout de suite. On économise le reste du budget, et l'extrémité va en mémoire 1.1. | P2 | C1 | 2.1, 1.1 |
| 2.4 | **Budget selon la valeur** : `HARD_ITERATION_CAP` = 5 000 pour tous. Laisser jusqu'à 20 000 itérations aux lignes longues à fort ROI tant que 2.1 voit du progrès (en 1976, 13 tracés faisables sur 86 demandent 5 k à 18 k). Seulement après l'étape 1, sinon l'absorption du 03/10 se reproduit ; de préférence dans un worker (6.1), puisqu'un tel tracé dure jusqu'à 92 jours. | P2 | C1 | 1.6, 2.1 |
| 2.5 | Journaliser la durée en jours de chaque recherche (`RAIL_SEARCH days=`), pour exprimer les budgets en jours. | P2 | C1 | — |

### Étape 3 — Chiffrer les longues lignes avant de les engager

| # | Tâche | P | C | Dépend de |
|---|---|---|---|---|
| 3.1 | **Coût de pose par le grossier** : le coût réel du rail vaut 1,53 fois le prédit entre 160 et 250 tuiles. Régression hors partie, sur les paires V307, du coût réel du tracé contre le coût grossier, la distance, les blocs d'eau et les obstacles. On ne l'adopte que si elle bat la formule actuelle en validation croisée. | P2 | C2 | 0.2 |
| 3.2 | **Profit des longues lignes** : appliquer le facteur réalisé/prédit par tranche de distance du banc de calibration PC (fret brut au-delà de 160 tuiles : 1,31 dans l'avant-goût). Lié à V306. | P2 | C2 | banc PC |
| 3.3 | **Carte grossière partagée** : échantillonnage creux des blocs dans le reliquat de tick (C67 `OpexTerrainMap`, ou une table plus légère), pour ne plus payer 0,2 M opcodes par candidat. | P3 | C3 | 3.1 ou 2.2 adoptés |
| 3.4 | Filtre de faisabilité grossier (grossier `NOPA` ⇒ candidat écarté). Rare : 1 cas sur 107, et c'était un faux `NOPA`. À ne faire qu'avec 3.3. | P3 | C1 | 3.3 |

### Étape 4 — Ouvrir les liaisons longues plus tôt

Cette étape vient seulement après les étapes 1 et 2. Avancer V269 (`v269_rail_late_relax=3`) ou
V305b a été neutre le 21/10 : ouvrir plus tôt ne paie pas tant qu'un essai sur deux finit en
abandon de 75 jours.

| # | Tâche | P | C | Dépend de |
|---|---|---|---|---|
| 4.1 | Rejouer `v269_rail_late_relax=3` sur la branche d'intégration de l'étape 1. | P2 | C1 | 1.6 |
| 4.2 | Borne de distance rail en rampe (200 → 350 entre 1972 et 1978), V305 d'origine. | P3 | C2 | 4.1, 3.2 |

### Étape 5 — Découpage géographique (conditionnel)

À ne lancer que si la sonde 1976 ou les autopsies montrent des tracés **faisables** qui dépassent
régulièrement 5 000 itérations. Sur la carte de 1973, ce n'est pas le cas (2 sur 105, sauvés par
le couloir).

| # | Tâche | P | C |
|---|---|---|---|
| 5.1 | Points de passage tous les L tuiles le long du trace grossier ; chaque segment est un A* vers l'ensemble des tuiles du bloc suivant. | P3 | C3 |
| 5.2 | L adaptatif : 40 à 60 tuiles en plaine, 20 à 30 en relief ; un segment qui échoue est coupé en deux. | P3 | C3 |
| 5.3 | Comparaison sur les paires V307 (solo, déterministe) contre la base : itérations, jours, coût du tracé. | P3 | C2 |

### Étape 6 — Recherches de fond (conditionnel)

| # | Tâche | P | C |
|---|---|---|---|
| 6.1 | Secours (2.2) et grosses recherches dans un worker du reliquat, sans tenir le créneau principal. V149 a échoué en porte A, et l'absorption du 03/10 s'applique : à envisager seulement si l'étape 1 a fait baisser les `ABND`. | P3 | C3 |

## 5. Ordre proposé

1. ✅ 0.2, 0.3 et 0.6 lus. **En premier : 1.0 (chercher depuis le côté étroit)**, seul ou contre
   V303 (b) si codex la livre, avec 1.3 (preuve `NOPA` bon marché) sur la même branche.
2. Coder 1.1, 1.2 et 1.3 sur une branche d'intégration (C1/C2 ; 1.2 et 1.3 délégables).
   Diagnostic 3×10 sur les `ABND` primaires, puis porte A 40×3.
3. En parallèle, en mesure seule : 2.1 (stagnation) et 3.1 (régression du coût sur les paires
   V307).
4. Selon 0.6 et 1.7 : 1.8 (sites dispersés) si un autre octant était libre ; 1.9 et 1.10
   (gares de puits à plusieurs quais) si les puits sont enclavés par notre propre voie ; 1.5
   (jointure) si les `NOPA` en jointure dominent ; 2.2 (secours) si les pièges dominent.
5. Puis 4.1, et 2.4 seulement si les `ABND` ont baissé.
