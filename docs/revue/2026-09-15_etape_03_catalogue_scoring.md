# Étape 03 — Catalogue et scoring

- **SHA revu** : `83dfcf4` (à corriger si la session revoit un autre commit)
- **Modèle / effort prévus** : Sonnet 5 / high
- **Périmètre** : `catalog.nut`, `economy.nut`, `tension.nut` — 2 280 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

G12 (matériel élu avant ROI) et G3 (cinématique rail sur distance candidate, pas sur le tracé A*).
`tension.nut` inerte : effort réduit, sauf code mort.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

### 03.1 — G12 tient : un seul wagon par cargo, choisi sur la seule capacité       [gravité : P2]
`catalog.nut:363-377` — `_refreshRail` ne garde qu'un wagon par cargo (`capacity >
this.wagonByCargo[cargo].capacity`), sans départage sur prix, coût d'exploitation ou poids (donc
vitesse), contrairement au départage locomotive à quatre critères juste en dessous (`catalog.nut:479-490`).
Toute l'économie rail (`economy.nut::OpexLineEconomics`) part ensuite de ce wagon unique
(`catalog.nut:437` `foreach (cargo, wagon in this.wagonByCargo)`) : un wagon moins capacitaire mais
moins lourd ou moins cher, qui aurait pu améliorer le ROI sur une ligne rapide ou à faible
volume, n'est jamais évalué. Aucune égalité n'est départagée non plus (le premier wagon trouvé à
capacité maximale gagne, ordre `AIEngineList` non garanti) — même absence de garde que celle déjà
corrigée pour le type de rail (`catalog.nut:337-341`), mais pas ici.

### 03.2 — G12 tient : un seul véhicule route par cargo, choisi sur la seule capacité       [gravité : P2]
`catalog.nut:713-728` — même schéma que 03.1 pour la route : `best` est retenu sur
`engine.capacity > best.capacity`, puis vitesse en second critère ; prix et coût d'exploitation ne
sont jamais comparés. Documenté comme un choix délibéré dans le commentaire de tête
(`catalog.nut:257-260`, « Un SEUL vehicule retenu par cargo (le plus capacitaire) ») mais la
justification donnée porte sur le type d'arrêt (bus vs camion), pas sur pourquoi la capacité prime
sur toute mesure économique.

### 03.3 — G12 tient : un seul avion par type d'aéroport, sur rang (gros > capacité > vitesse)       [gravité : P2]
`catalog.nut:533-536` (grands aéroports) et `catalog.nut:578-579` (petits aéroports) — pour
chacun des 5 types d'aéroport (`AT_INTERNATIONAL`, `AT_METROPOLITAN`, `AT_LARGE`, `AT_COMMUTER`,
`AT_SMALL`), un seul avion est retenu. Pour les grands aéroports la règle est stricte : `(isBig &&
!bestIsBig)` fait gagner N'IMPORTE QUEL gros avion sur N'IMPORTE QUEL petit avion avant même de
regarder la capacité (`catalog.nut:535-536`) ; aucun ROI n'intervient. `airCombos` garde bien un
combo par type (jusqu'à 5 entrées, `catalog.nut:558`, `:601`), donc l'arbitrage ROI existe
*entre* types d'aéroport en aval, mais jamais *entre* avions compatibles à l'intérieur d'un même
type — exactement la formulation du plan.

### 03.4 — Code mort confirmé : `OpexTensionMacroRegime` + `OpexProjectScoreForRegime`       [gravité : P3]
`tension.nut:311-470` (160 lignes, commentaires inclus) — grep sur tout `ai/OpexAI/*.nut` pour
`OpexTensionMacroRegime` et `OpexProjectScoreForRegime` : aucune occurrence hors de leur propre
définition dans `tension.nut`. Vérifié à la main : `projects.nut` construit le champ `ctx.regime`
qu'utiliserait `OpexTensionMacroRegime` par des **chaînes câblées en dur** — `tensionCtx.regime <-
"shadow"` (`projects.nut:1999`) et `tensionCtx.regime <- "continuous"` (`projects.nut:2024`), ainsi
que `"none"` par défaut aux 4 sites de lecture (`projects.nut:347,406,442,472`) — jamais par un
appel à la fonction. `OpexTensionMacroRegime` a donc été supplantée par le mécanisme
`OpexTensionComputeShadowPrices` / `OpexReducedCostScore` (tous deux réellement appelés depuis
`projects.nut:1997` et `:2013`) sans être retirée. Contrairement aux drapeaux d'expérience à 0
décrits dans `ai/OpexAI/CLAUDE.md`, ce n'est pas un code vivant mais inerte derrière un réglage :
même `tension_scoring=1` ou `shadow_pricing=1` ne l'atteint jamais. Confirme le signalement du
2026-09-06.

## Vérifié, n'est PAS un bug

**G3 ne tient plus dans `economy.nut` : rail et route recalent déjà tous deux sur le tracé réel.**
`economy.nut:159-169` (`OpexLineEconomics`) et `economy.nut:601-607` (`OpexRoadLineEconomics`)
traitent le paramètre optionnel `routeDistance` de façon strictement symétrique : quand fourni et
positif, il remplace `distance` pour `travelDist`/`infraDist` (temps de trajet, vitesse effective,
capacité en wagons/véhicules, coût d'infrastructure — `economy.nut:207,234,287` côté rail,
`:607-608,680-681` côté route) ; seul le tarif (`AICargo.GetCargoIncome`, `economy.nut:321` et
`:671`) garde la distance Manhattan (`distance`), documenté comme volontaire aux deux endroits
(« distance TARIFAIRE », `economy.nut:157-158` et `:600`) et cohérent avec la loi de paiement du
jeu. Vérifié aussi côté appelants (grep + lecture, hors périmètre strict mais nécessaire pour
trancher) : `builder_rail.nut:1484-1491` recalcule `routeDistance` en sommant
`AIMap.DistanceManhattan` sur les tuiles du tracé A* réellement trouvé puis rappelle
`OpexLineEconomics` avec ce `routeDistance`, exactement le patron déjà en place côté route
(`task_road.nut:208-223`, `task_feeders.nut:174-180` via `OpexApplyRoadEconomics`). Le commentaire
`economy.nut:155-158` (« G5§1 ») documente explicitement ce correctif. L'énoncé du plan (rail
jamais recalé sur le tracé réel) décrit un état antérieur à ce correctif, pas le code actuel.

**`tension_scoring` et `shadow_pricing` valent bien 0 par défaut.** `info.nut:1234-1240`
(`tension_scoring` : `easy_value = medium_value = hard_value = custom_value = 0`) et
`info.nut:1259-1265` (`shadow_pricing` : mêmes quatre valeurs à 0). Confirme la prémisse du plan :
`tension.nut` reste inerte par défaut, mais c'est un drapeau d'expérience délibéré au sens
d'`ai/OpexAI/CLAUDE.md`, pas un bug — à distinguer du code mort de 03.4, qui lui est inatteignable
même drapeau activé.

## Hors périmètre, à relire ailleurs

- `builder_rail.nut:1420-1500` (`OpexBuildRailCandidate` / `OpexCompleteRailRouteAfterSearch`) et
  `task_road.nut:190-230`, `task_feeders.nut:160-185` (`OpexApplyRoadEconomics` après site réel) :
  lus seulement pour trancher G3 depuis `economy.nut` ; à revérifier en détail dans l'étape qui
  couvre ces fichiers (construction rail / route), notamment si le rappel post-A* est bien
  systématique sur tous les chemins (fret compris) et pas seulement celui inspecté ici.
- `projects.nut:1990-2025` (bascule `shadow_pricing` / classement continu, champ `regime` câblé en
  dur) : révèle le mécanisme qui a remplacé `OpexTensionMacroRegime` (03.4) ; la cohérence de ce
  câblage (valeurs `"shadow"` / `"continuous"` / `"none"` jamais produites par une fonction dédiée)
  est à examiner dans l'étape qui couvre `projects.nut`.
- `candidates.nut:751`, `:2041`, `:3388` (premiers appels à `OpexLineEconomics` /
  `OpexRoadLineEconomics` avec `routeDistance = null`, au classement avant tout A*) : comportement
  attendu et documenté (`economy.nut:151-154`), mentionné ici seulement comme le pendant amont de
  la vérification G3 ; pas de lecture complète de `candidates.nut` faite dans cette étape.
- Choix locomotive (`catalog.nut:437-495`) : contrairement au wagon/véhicule route/avion (03.1–03.3),
  la locomotive est départagée sur 4 critères physiques et économiques (vitesse soutenue,
  accélération, coût d'exploitation, prix) sans réduire l'ensemble évalué — jugé hors du périmètre
  de G12 tel qu'énoncé par le plan, mais à garder en tête comme le contre-exemple « bien fait » si
  une correction de 03.1–03.3 est un jour engagée.
