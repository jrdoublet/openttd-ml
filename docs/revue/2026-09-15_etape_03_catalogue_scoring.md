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

### Fermeture de la vérification résiduelle G3 — 2026-09-16

La réserve « vérifier que le recalcul post-A* est systématique, fret compris » est maintenant
fermée. Les deux orchestrations rail convergent vers le même helper :

- le chemin bloquant `OpexPlanRailRoute` termine par
  `OpexCompleteRailRouteAfterSearch(...)` ;
- le chemin reprenable appelle le même `OpexCompleteRailRouteAfterSearch` quand ses tranches A*
  sont terminées ;
- ce helper somme les tuiles du tracé réel en `routeDistance`
  (`builder_rail.nut:1484-1487`) puis rappelle **inconditionnellement pour tout candidat**
  `OpexLineEconomics(..., candidate.kind, ..., routeDistance)` (`:1489-1497`).

`OpexLineEconomics` branche ses détails fret sur `kind == "freight"` mais utilise le même
`travelDist = routeDistance` pour pax et fret. Il n'existe donc pas de chemin fret qui évite le
recalage post-tracé. G3 est fermé sans patch supplémentaire.

## Clôture M3 / G12 — workspace du 2026-09-16

La relecture du code courant nuance le constat historique sans le renier :

- **03.1 rail** : la locomotive n'est plus le vieux « fastest wins » ; elle est déjà couplée au
  nombre de wagons et départagée sur vitesse soutenable, accélération, coût courant puis prix.
  Le résidu G12 est le **wagon unique par cargo**, encore pré-élu sur capacité ;
- **03.2 route** : un véhicule unique reste pré-élu par capacité puis vitesse avant
  `OpexRoadLineEconomics`. La capacité réellement refittée est néanmoins relue après
  construction ; ce n'est donc pas un mensonge de mesure post-build, mais une réduction amont de
  l'espace de choix ;
- **03.3 air** : un appareil unique reste pré-élu par type d'aéroport. Le code conserve aussi une
  préférence de type séparée : dès qu'un plan sur grand aéroport est viable,
  `if (bestPlan != null && bestPlan.airport.allowBig) break;`. Le diagnostic M3 **ne mélange pas**
  cette politique d'aéroport avec la question du choix d'appareil ;
- le vieux §3 G12 feeder n'est plus actif sous sa forme historique : le catchment du hub est lu
  sur le hub/station réel (`OpexHubPaxCatchmentRadius(hub)`), pas sur un objet catalogue erroné.

### Instrumentation passive

`equipment_roi_probe` a été ajouté **default-off** ; le contrat de réglages passe de 229 à
**230**. Quand il vaut 1 uniquement, le catalogue conserve les alternatives
`wagonChoicesByCargo`, `roadEngineChoicesByCargo` et `airPlaneChoicesByAirport`.
Les décisions livrées continuent à lire les sélections historiques
`wagonByCargo` / `roadEngineByCargo` / `airCombos`.

Les événements `M3_EQUIP` séparent :

- `pre_admission` : contrefactuel avant le rejet économique initial ;
- `post_route` / sélection portfolio : même route/site réel déjà choisi ;
- `post_refit` : capacité réellement observée après
  `BuildVehicleWithRefit`, distincte de la capacité catalogue ;
- `native_choices` et `refit_proxy_choices` : une capacité de cargo d'origine n'est jamais
  présentée comme une capacité refit exacte.

Le rail peut passer un wagon alternatif + son propre cache de locomotives à
`OpexLineEconomics` **uniquement pour la sonde**. Route et air réutilisent leurs fonctions
économiques réelles. Aucun résultat contrefactuel ne revient au générateur, au portefeuille ou au
constructeur.

### Validation

Contrats :

- `python -m unittest sweeps.test_campaign_freeze sweeps.test_m3_equipment_roi sweeps.test_b9_air_catchment`
  → **23/23 OK** ;
- `python sweeps/diag_m3_equipment_roi.py --selftest` → OK ;
- `python sweeps/bench_1v1_5y_20seeds.py --selftest` → OK ;
- `py_compile` des tests/runner/analyseur → OK ;
- `git diff --check` → exit 0, hors avertissements CRLF déjà connus.

Le smoke obligatoire après la dernière modification `.nut`,
`results/review_m3_equipment_roi_smoke_2x3_v5.json`, est sain sur **4/4 bras**
(2 graines × 3 ans, OpexAI + AAAHogEx). Il expose 32 320 événements M3, sans erreur NoAI.

Le diagnostic final
`results/review_m3_equipment_roi_5x6.json` (graines 42/100/999/1234/5678, 6 ans,
6 workers, lab 6 CPU / 2g / 2g) est **10/10 sain et complet** et contient 135 887 événements :

- **rail** : 55 106 comparaisons, **0 cas multi-choix**, 0 regret, 0 flip d'admission ;
- **route** : 736 comparaisons, 18 cas multi-choix, **0** différence contre meilleur
  profit/ROI, 0 flip ; 80 observations post-refit, `capacity_delta=0` partout ;
- **air** : 79 807 comparaisons, toutes multi-choix ; 75 742 choix courants diffèrent du meilleur
  profit, 77 884 du meilleur ROI ; sur 78 077 événements pré-admission, **2 371**
  (~3,0 %) auraient franchi le seuil de profit avec un autre appareil.
  Le regret de profit contrefactuel moyen est **7 776,81 £/an**, maximum **31 825 £/an**.
  Les 158 constructions observées ont `capacity_delta=0`.

Le catalogue vanilla choisit l'appareil **228** sur toutes les évaluations M3, alors que le meilleur
profit dépend réellement de la route : 218 (33 777 cas), 217 (17 823), 223 (13 985), puis plusieurs
autres IDs. Le bon correctif éventuel n'est donc pas « remplacer 228 par un autre avion statique » :
ce serait une **politique de sélection économique par route**.

### Mesure vs classement vs politique

**Aucun P1 de vérité de mesure n'est démontré en vanilla.** Le banc ne voit aucun
`refit_proxy_choice` route/air et aucune différence entre capacité catalogue et capacité
post-refit sur les véhicules effectivement construits. Rail/route sont presque mono-équipement dans
ce set. Le risque NewGRF reste néanmoins réel par construction : un GRF peut introduire plusieurs
engins, modifier capacité après refit, masse, coûts et compatibilités. La sonde est prête à le
mesurer, mais **ce 5×6 OpenGFX ne mesure pas un NewGRF**.

Le défaut AIR observé est donc un **P2 de pré-sélection/classement**, pas un P1 technique. Une
politique concrète se dégage — évaluer les appareils compatibles par route avec l'économie réelle —
mais elle n'est **ni implémentée ni adoptée** dans cette passe. Conformément à la règle de la revue
(seuls les P1 techniques sont corrigés après ce diagnostic, et aucune adoption depuis un simple
5×6), aucun 20×10 n'est lancé.

### Correctifs de harnais découverts pendant M3

Le premier smoke a révélé deux défauts du harnais, sans lien avec le comportement OpexAI :
`keep()` dépendait de globals non sérialisables proprement sous Windows quand le bench était lancé
comme `__main__`, et son selftest attendait l'ancien schéma sans le champ additif
`endpoint_cargo_stats.airport`. Le callback CLI est désormais réimporté depuis un module
sérialisable, le chemin de log est injecté dans l'expérience, les runners créent explicitement leur
dossier moteur, et le selftest accepte le champ géométrique. Le contrôle CLI
`results/review_m3_harness_cli_check_1x1.json` passe.
