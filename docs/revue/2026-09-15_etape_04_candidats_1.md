# Étape 04 — Candidats 1/2 — cinématique, index, pax et fret

- **SHA revu** : `6698d8c` (HEAD au moment de la revue)
- **Modèle / effort prévus** : Sonnet 5 / high
- **Périmètre** : `ai/OpexAI/candidates.nut:1-1852` — 1 852 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Budget d'itérations A* et bornes d'époque, index de lignes et jointure, `OpexMakeCandidate`,
`OpexTopK`, `OpexPaxCandidates`, `OpexFreightCandidates`.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

### 04.1 — Le rabattement H2 (`join_place`) est mort de naissance, pax et fret     [gravité : P1]
`ai/OpexAI/candidates.nut:1361` (`OpexPlaceJoinPax`) et `ai/OpexAI/candidates.nut:1420`
(`OpexPlaceJoinFreight`) — les deux fonctions filtrent les lignes RAIL déjà bâties avec
`if (("mode" in line) || !("kind" in line) || line.kind != "pax"/"freight") continue;` : elles
sautent toute ligne qui **possède un champ `mode`**, quelle que soit sa valeur.
Or `ai/OpexAI/task_rail.nut:1012` montre que **toute** ligne rail enregistrée porte
`mode = "rail", kind = candidate.kind` explicitement (même schéma que route/air/eau, confirmé par
le seul site de construction `_lines.append` pour le rail). Le prédicat correct existe ailleurs
dans le même fichier — `("mode" in line) && line.mode != "rail")` (`candidates.nut:993`, `:1012`,
`:1284`) — mais ces deux fonctions ont perdu le test de *valeur* et ne gardent que le test de
*présence*.

Conséquence : dans `OpexPlaceJoinPax`, `stations` reste toujours vide (`candidates.nut:1359-1374`)
et la fonction retourne immédiatement sans rien produire ; dans `OpexPlaceJoinFreight`, `sources`
et `sinks` restent toujours vides (`candidates.nut:1417-1437`), donc les deux boucles
(`candidates.nut:1439-1474` et `:1476-1510`) ne trouvent jamais de `best` et n'ajoutent aucun
candidat. **Le mécanisme H2 entier (jointure d'une extrémité libre sur une gare déjà bâtie,
décrit en détail par les commentaires C29/2026-08-29 « DE LA GUILLOTINE AU FILET »,
`candidates.nut:1255-1276`) est un no-op complet**, pax et fret, quelle que soit l'activation de
`JOIN_PLACE`. Réglage `join_place` à défaut `false` (`globals_post.nut:77`) : aucun impact en
production aujourd'hui, mais si `join_place=1` est un jour banqué (le code laisse penser que
c'est le sens de tout ce bloc), le banc mesurera silencieusement « zéro effet » — un artefact de
mesure, pas une conclusion sur le mérite de l'idée.

### 04.2 — `OpexShareBasin` ne partage jamais rien : même bug de prédicat sur `mode`     [gravité : P1]
`ai/OpexAI/candidates.nut:1310-1322` — `OpexStationCargoLineCount` compte « combien de lignes
RAIL utilisent déjà ce StationID », avec le commentaire « les modes avec un champ `mode` (air,
eau, route) n'ont pas de quai rail à partager » : le code traduit ça par
`if (("mode" in line)) continue;` (ligne 1317), sans jamais regarder la valeur du champ. Comme
pour 04.1, toute ligne rail porte pourtant `mode = "rail"` (`task_rail.nut:1012`), donc cette
condition saute **toutes** les lignes sans exception et `n` vaut toujours 0.
`OpexShareBasin` (`candidates.nut:1326-1330`) fait alors `amount / (n + 1)` = `amount / 1` =
`amount` : la division « part du nouvel arrivant, 1/(n+1) de la production » n'a jamais d'effet,
c'est une fonction identité déguisée. Appelée depuis `OpexPaxCandidates`
(`candidates.nut:1588-1589`) et `OpexFreightCandidates` (`candidates.nut:1667`) sous
`if (BASIN_SHARE ...)`. `BASIN_SHARE` à défaut `false` (`globals_post.nut:86`) : pas d'effet
mesurable aujourd'hui, mais si `basin_share=1` est activé pour un banc, le partage de bassin que
le code prétend appliquer ne s'appliquera jamais — encore un flag qui semblerait « testé et
neutre » alors qu'il n'a jamais tourné.

### 04.3 — Le `ratio` qui classe un candidat au TOP_K n'est pas le `roi` qu'il expose ensuite     [gravité : P2]
`ai/OpexAI/candidates.nut:791-809` — le score composite `ratio` (utilisé par `OpexTopK`,
`candidates.nut:951-964`, et par le seuil `MIN_RATIO`/`isLowRatio`) intègre un
`turnoverBonus` inconditionnel de 60 à 130 % selon `oneWayDays` (lignes 793-797), appliqué à
`adjustedRoi` puis à `ratio` (ligne 808). Mais le champ `roi` réellement stocké sur le candidat
(ligne 841, `roi = effectiveRoi`) est calculé séparément à partir de `economics.roi` et de
`freightBonus` **seul** — sans `turnoverBonus` (ligne 809 : `effectiveRoi = (economics.roi *
freightBonus) / 100`). Un candidat à rotation rapide (≤ 12 jours) peut ainsi être classé devant un
autre grâce à un bonus de 130 % que rien dans le champ `roi` transmis à `economy.nut`/
`projects.nut` ne reflète : la raison de son classement et la valeur qu'il expose divergent. Sous
`flat_bonus` à son défaut `false` (`freightBonus = 100`, confirmé `globals_pre.nut:320`),
`roi == economics.roi` brut alors que `ratio` reste ajusté par le turnover — ce n'est donc pas un
résidu d'un autre flag, l'écart existe par défaut.

### 04.4 — Seuil d'acceptation en dur (8) au lieu de `ROAD_ACCEPTANCE_FULL_UNIT`     [gravité : P3]
`ai/OpexAI/candidates.nut:549` — `OpexRailOriginSitable` teste `value >= 8` pour le mode
acceptance, alors que ce même seuil est nommé ailleurs dans le fichier
`ROAD_ACCEPTANCE_FULL_UNIT` (`candidates.nut:2012`, valeur 8, réutilisé
`candidates.nut:1250`, `:2683`, `:2700`, `:3344`). Valeur actuellement identique donc aucun
comportement divergent aujourd'hui, mais un futur changement de `ROAD_ACCEPTANCE_FULL_UNIT`
laisserait ce site de côté sans avertissement — exactement le genre de duplication que ce fichier
n'a plus les moyens de relire à l'œil.

## Vérifié, n'est PAS un bug

- `OpexRailIterations` / `OpexRailDistanceForIterations` (`candidates.nut:129-172`) : la
  extrapolation quadratique au-delà du dernier nœud (`vLast * distance² / dLast²`) et son inverse
  (`OpexIsqrt(dLast² * maxIter / vLast)`) sont algébriquement l'inverse exacte l'une de l'autre ;
  vérifié à la main, pas seulement par grep.
- `OpexComputeRoadToRailDistance` (`candidates.nut:304-352`) : la formule `d = num / denom` avec
  `denom = 12·M·deltaPerTile·2,5 − cTile` est la résolution correcte de
  « capital extra justifié par le ROI cible 0,40 = capital extra réel », vérifiée terme à terme —
  ce n'est pas un nombre magique mal câblé malgré sa densité.
- `OpexTopK` (`candidates.nut:951-964`) : le tri par insertion borné à `k` avec `floor` est
  correct (liste triée décroissante, purge du surplus, mise à jour du plancher) ; la comparaison
  stricte `<= floor` en fast-path ne fait que privilégier le premier candidat entré en cas d'égalité,
  ce n'est pas une perte de candidats.
- `OpexPlaceJoinFreight` (`candidates.nut:1413-1511`) : l'affectation `candidateEnd = "A"` pour un
  puits libre qui rejoint une source existante et `candidateEnd = "B"` pour une source libre qui
  rejoint un puits existant correspond exactement au commentaire (`candidates.nut:1410-1412`) —
  soupçonné inversé à la première lecture, vérifié correct à la deuxième (mais rendu inatteignable
  par 04.1).
- `bounds.airMin` et `bounds.railAirOverlapMin` (`OpexRefreshEpochBounds`, `candidates.nut:446-460`)
  sont toujours égaux après les clamps des lignes 443-444 : deux noms pour la même valeur, pas une
  incohérence.

## Hors périmètre, à relire ailleurs

- Le même bug de prédicat que 04.1/04.2 (`("mode" in line)` sans test de valeur) ne réapparaît PAS
  dans les filtres route au-delà de la ligne 1852 (`candidates.nut:2098,2115,2141,2165,2210,2366`
  utilisent tous la forme correcte `!("mode" in line) || line.mode != "road"`) — vérifié par
  lecture, pas seulement par grep, pour éviter de rouvrir un faux soupçon à l'étape 5.
- La validation « shadow » C46 (`candidates.nut:1716-1844`) compare l'ordre des candidats issus de
  `OpexDirectedSpatialGrid.GetSortedCandidates` à un balayage linéaire qui ne trie PAS par
  distance : la garantie d'ordre repose sur `spatial.nut` (étape 2), hors périmètre ici — à
  confirmer que l'étape 2 a bien vérifié que `GetSortedCandidates` rend un ordre stable identique
  au balayage linéaire d'origine.
- L'usage réel de `candidate.roi` en aval (04.3) — est-ce qu'`economy.nut` ou `projects.nut`
  recalculent leur propre ROI ou consomment ce champ tel quel — appartient aux étapes 3 et 6, pas
  vérifié ici.
- Les références de distance hétérogènes utilisées comme proxys de calibration
  (`OpexComputeRoadToRailDistance` : refD=20 ; `OpexRefreshEpochBounds` : busHorizon sur
  refD=25 ; `OpexComputeAirMaxDistance` : horizon sur refD=100) ne sont pas incohérentes en soi,
  mais leur justification respective n'est documentée que pour la première ; à confirmer qu'aucun
banc n'a mesuré de sensibilité à ce choix avant de les considérer acquises.

## Réconciliation B6 — 2026-09-16

Le constat 04.3 est corrigé côté **vérité de mesure**, pas par un changement de classement.
`turnoverBonus` et `generationRatio` sont propagés comme télémétrie ;
`PORTFOLIO_RANK` publie séparément `roi`, `turnover_bonus`,
`generation_ratio`, `rank_score` et `finance_capital`.
Le 5×6 B6 observe 592/2 214 rangs avec bonus non neutre et 164/476 top-5 dont l'ordre de ROI
diffère de l'ordre `rank_score`. Le bonus de rotation reste un mécanisme amont du TopK rail ;
aucun alignement comportemental n'est adopté sur cette seule mesure.
