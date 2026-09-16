# Étape 05 — Candidats 2/2 — assemblage, route, subventions

- **SHA revu** : `67c5eae` (HEAD vérifié au moment de la revue ; la consigne de départ indiquait `83dfcf4`, qui ne correspond pas au HEAD réel de la branche — corrigé ici)
- **Modèle / effort prévus** : Sonnet 5 / high
- **Périmètre** : `ai/OpexAI/candidates.nut:1853-3472` — 1 620 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

`OpexBuildCandidates`, `OpexBands`, famille route complète (pax, fret, extensions, rabattement),
notation municipale, subventions C42. Interaction vivier ↔ `abandon_gen_filter` ↔ cooldown (G0).

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

### 05.1 — G0 (09-06) toujours ouvert : `abandon_gen_filter`/`abandon_cooldown_days` actifs sans banc isolé        [gravité : P1]
`ai/OpexAI/info.nut:1648-1670` déclare `abandon_cooldown_days` (défaut 365) et `abandon_gen_filter`
(défaut 1) comme « défaut adopté », cité C33.3/C22. `ai/OpexAI/settings.nut:21-24` confirme que ces
deux globales (`ABANDON_MEMORY`, `ABANDON_COOLDOWN_DAYS`, `ABANDON_GEN_FILTER`) sont bien actives par
défaut. Or `docs/revue_code_2026-09-06_correctifs.md:17-26` (constat G0) a explicitement jugé C22 et
C33.3 « non établis isolément, et penchent contre en combo », et a décidé de remettre ces deux
réglages à 0 « tant qu'ils n'ont pas leur propre banc officiel 20×10 isolé », décision qui devait être
confirmée avant d'éditer `info.nut`. Neuf jours plus tard, `info.nut` porte toujours les défauts
d'avant G0, sans qu'aucun commentaire ne référence la décision. Dans le périmètre de cette étape,
`ABANDON_GEN_FILTER` (combiné à `ABANDON_MEMORY`) coupe le vivier à cinq sites indépendants —
`ai/OpexAI/candidates.nut:2295` (pax ville-ville), `:2603` (fret industrie-industrie), `:2674` (fret
industrie-ville), `:2935` (feeder), `:3353` (subvention C42) — donc toute la forme du vivier généré
ici repose sur une décision documentée comme non tranchée. **G0 n'est pas caduc, il est toujours
d'actualité.**

### 05.2 — La « famille route » de l'enjeu (pax, extensions, feeders, subventions) est coupée par défaut, seul le fret est vivant        [gravité : P1]
Vérification à la main des quatre réglages qui gardent les fonctions nommées par l'enjeu de cette
étape (`grep -n "name = " info.nut` puis lecture du bloc) : `road_pax_build` = 0 par défaut
(`info.nut:1881-1886`, « disabled by default to preserve airport demand »), `road_pax_extensions` = 0
(`info.nut:1889-1894`), `feeder_candidates` = 0 (`info.nut:1191-1196`) et `air_split_feeder_test` = 0
(`info.nut:2510-2515`), tous confirmés dans `settings.nut:34-35,127,341`. Dans
`ai/OpexAI/candidates.nut:3098-3122` (`OpexBuildRoadCandidates`), `OpexRoadPaxCandidates` n'est appelé
que si `ROAD_PAX_BUILD_ENABLED`, `OpexRoadExtensionCandidates` que si `ROAD_PAX_EXTENSIONS`, et
`OpexRoadFeederCandidates` retourne immédiatement en tête de fonction
(`candidates.nut:2794`, `!FEEDER_CANDIDATES_ENABLED && !AIR_SPLIT_FEEDER_TEST`). Les subventions
(`OpexGenerateSubsidyCandidates`) ne sont invoquées que si `c42_subsidies` = 1, or ce réglage est à 0
par défaut (`info.nut:185-190`, confirmé `projects.nut:1950-1953`). Au défaut, sur les cinq fonctions
citées par l'enjeu de cette étape, seule `OpexRoadFreightCandidates` (industrie↔industrie,
industrie↔ville) génère réellement des candidats ; `OpexBuildCandidates`/`OpexBands` (rail) tournent
toujours. Ce n'est pas un bug — chaque réglage porte sa justification (préserver la demande
aéroportuaire, banc 20 graines défavorable, stratégie legacy) — mais ça reclasse fortement l'enjeu
annoncé : les constats 05.4/05.5/05.7/05.8 ci-dessous portent sur du code aujourd'hui **dormant**.

### 05.3 — `stats.profitTooLow` mélange candidats réellement rejetés et candidats conservés        [gravité : P2]
`ai/OpexAI/candidates.nut:2049-2053` (`OpexMakeRoadCandidate`, chemin toujours actif via le fret) :
`stats.profitTooLow++` est incrémenté à la fois quand `economics.profitAnnual <= 0` (rejet réel,
`return null`) et quand `0 < profitAnnual < ROAD_MIN_PROFIT_ANNUAL` (candidat conservé, ajouté à
`out` par l'appelant). Le compteur combiné est ensuite publié tel quel à `candidates.nut:3146-3148`
sous l'étiquette `OpexDecide("VIVIER_REJECT", "reason=road_profit_too_low n=" + stats.profitTooLow)`.
Conséquence : le journal de décision annonce comme « rejeté du vivier » un nombre qui inclut des
candidats qui y sont réellement restés — quiconque lit `VIVIER_REJECT` pour compter l'attrition du
vivier surestime les rejets économiques réels.

### 05.4 — `OpexRoadPaxCandidates` ignore `roadGenMax`, contrairement au fret/feeders/subventions        [gravité : P3, dormant tant que `road_pax_build=0` (05.2)]
`ai/OpexAI/candidates.nut:2290` borne les candidats pax ville-ville avec
`distance > roadBounds.roadMax` en dur, sans passer par `OpexRoadDistanceAllowed`
(`candidates.nut:489-502`), qui utilise `roadGenMax` (toujours ≥ `roadMax`, cf. `candidates.nut:413-423`)
et que les trois autres familles utilisent bien — fret (`:2602`, `:2673`), feeders
(`:2921-2924`), subventions (`:3349`, `roadGenMax` en dur). Or `roadGenMax` est calculé
(`candidates.nut:410-423`) précisément à partir de l'horizon de transit du **bus** passagers
(`bestBus`, `pax`) : le commentaire dit explicitement vouloir laisser les véhicules routiers
concourir « jusqu'a l'horizon de transit du bus » au-delà du repère ROI `roadMax` — c'est
exactement le domaine de la famille 1 (pax ville-ville), qui est la seule à ne pas en bénéficier.
Si `road_pax_build` est un jour remis à 1 pour un banc, cette famille sous-génèrera silencieusement
les paires dans la bande `[roadMax, roadGenMax]` que sa propre logique de bornes visait à admettre.

### 05.5 — Calcul mort dans `OpexRoadFeederCandidates` : `remainingHouses` est toujours égal à `houses`        [gravité : P3, dormant (05.2)]
`ai/OpexAI/candidates.nut:2944-2945` : `local remainingHouses = houses;` puis
`marginalProd = (produced * remainingHouses) / houses;` — `remainingHouses` n'est jamais modifié
entre les deux lignes, donc le résultat vaut toujours `produced`. Le garde `existingCount >= 1
continue` juste au-dessus (`:2931`) garantit d'ailleurs qu'on ne voit jamais qu'un premier feeder
par (ville, hub), donc la logique de décompte que le nom de la variable suggère (maisons déjà
couvertes par un feeder précédent) n'a jamais d'effet ici. Sans conséquence fonctionnelle (multiplier
puis diviser par la même valeur), mais trompeur pour la relecture.

### 05.6 — `OpexBands` ne voit jamais les candidats rail < 25 ou ≥ 200 tuiles        [gravité : P3]
`ai/OpexAI/candidates.nut:1958-1972` : `BAND_EDGES <- [25, 45, 70, 110, 200]`, boucle `for (i=0;
i<4; i++)` sur les 4 intervalles `[25,45) [45,70) [70,110) [110,200)`. Un candidat rail de distance
< 25 (le rail descend maintenant à 5 tuiles, cf. commentaire `candidates.nut:1976`) ou ≥ 200 ne
tombe dans aucun `best[i]` et n'apparaît dans aucun panneau diagnostic. Le commentaire du fichier dit
lui-même « Diagnostic, pas decision » (`:1955`) : aucun effet sur la construction, mais le signal de
diagnostic est aveugle précisément sur la partie la plus récente et la plus courte du domaine rail.

### 05.7 — Le plafond de lignes pax du garde-fou subvention est un seuil fixe, pas le seuil proportionnel à la population utilisé ailleurs        [gravité : P3, dormant tant que `c42_subsidies=0` (05.2)]
`ai/OpexAI/candidates.nut:3375` : `if (OpexTownRoadLineCount(lines, srcTile) >= 4 ||
OpexTownRoadLineCount(lines, dstTile) >= 4) continue;` compare à une constante `4`, alors que la
famille pax ordinaire (`candidates.nut:2274,2279`) utilise `4 + (towns[a].pop / 300)`, un plafond qui
croît avec la population. Une grande ville qui aurait droit à plus de 4 lignes pax ordinaires peut
donc se voir refuser un candidat subvention alors qu'un candidat pax ordinaire équivalent serait
accepté. Pas nécessairement un bug (garde-fou volontairement plus conservateur pour un chemin rare),
mais l'incohérence n'est pas documentée.

### 05.8 — Commentaire de `OpexBoostTownRating` cite un réglage `tree_planting` qui n'existe pas        [gravité : P3]
`ai/OpexAI/candidates.nut:3184-3188` explique l'effet nul au défaut par « La plantation preventive
est coupee (tree_planting = 0) ». `grep -in "tree" ai/OpexAI/info.nut ai/OpexAI/settings.nut
ai/OpexAI/builder_air.nut` ne trouve aucun `AddSetting` ni aucune globale de ce nom — ce réglage
n'existe pas dans le dépôt actuel. Le comportement décrit reste correct pour une autre raison,
vérifiée à la main : les 5 sites d'appel dans `builder_air.nut` (lignes 432, 1390, 1514, 1597, 1622)
sont tous des recours réactifs après `AIError.ERR_LOCAL_AUTHORITY_REFUSES`, jamais un appel préventif
— mais le nom de réglage cité dans le commentaire est un fantôme, à corriger ou retirer.

## Vérifié, n'est PAS un bug

- **`OpexBoostTownRating` (`candidates.nut:3167-3209`)** : comparaison corrigée à l'énum
  `AITown.GetRating` (`TOWN_RATING_*`, 0..8) au lieu de l'ancienne comparaison à une note brute
  −1000..1000 — correspond exactement au piège documenté dans `ai/OpexAI/CLAUDE.md`. Vérifié contre
  les 5 sites d'appel réels dans `builder_air.nut` : tous réactifs (après refus municipal), jamais
  préventifs, donc le garde `currentRating > TOWN_RATING_MEDIOCRE` ne bloque jamais ces appels en
  pratique (note déjà très négative au moment de l'appel). Seul le nom de réglage cité en
  commentaire est erroné (05.8).
- **G9 (revue 09-06) semble fermé dans ce périmètre** : la clé de paire fret→ville inclut maintenant
  l'identité de ville (`candidates.nut:2674-2677`, commentaire « G9§1 », `"t" + towns[t].id`, cohérent
  avec `OpexAbandonedPairKey`), et `OpexRoadFeederCandidates` respecte désormais `ABANDON_GEN_FILTER`
  (`candidates.nut:2932-2938`, commentaire « G9§2 ») au lieu de consulter `abandonedPairs`
  inconditionnellement. Fermeture complète à confirmer côté `OpexAbandonedPairKey` elle-même
  (`lines.nut`, étape 2) — non rouverte ici, conformément à la consigne du plan.
- **`ROAD_MIN_PROFIT_ANNUAL` (`candidates.nut:1998-2004`) et `ROAD_ACCEPTANCE_FULL_UNIT`
  (`candidates.nut:2006-2012`)** : les deux se comportent exactement comme leurs commentaires le
  disent — un repère de mesure historique qui ne rejette plus rien, et une règle moteur (unité
  d'acceptation pleine) plutôt qu'un seuil réglable. Pas de code mort, pas de nom trompeur.
- **Chevauchement des bandes rail/route 5–25 tuiles (`candidates.nut:1974-1990`)** : explicitement
  voulu par le commentaire (le mode gagnant se décide au ROI dans `projects.nut`, pas par bande de
  distance figée) — pas un doublon de logique à corriger.
- **`FLAT_BONUS`/`CLEAN_DENSITY_SCORE`** : les branches historiques (`freightBonus = 140`,
  `feederBonus = 160`) sont bien gardées par `if (FLAT_BONUS)` (`candidates.nut:2056-2059,3048-3069`)
  et `flat_bonus` vaut 0 par défaut (`info.nut:1274-1279`) — code mort volontaire (drapeau
  d'expérience à défaut 0), pas un bug.

## Hors périmètre, à relire ailleurs

- Fermeture définitive de G9 (`OpexAbandonedPairKey`) : `ai/OpexAI/lines.nut` — étape 2.
- `OpexRoadDistanceAllowed`, `OpexCatalogBounds`, `OpexRoadLineEconomics`,
  `OpexRoadFreightServedIndex/BusyIndex/AcceptedTowns`, `OpexOriginServed`,
  `OpexSpatialGrid`/`OpexDirectedSpatialGrid` : définis avant la ligne 1853, donc étape 4 (et
  `spatial.nut`, étape 2) — seulement consultés ici en lecture pour comprendre les bornes de
  distance utilisées dans ce périmètre (constat 05.4).
- Les 5 sites d'appel de `OpexBoostTownRating` et la logique de contournement
  `ERR_LOCAL_AUTHORITY_REFUSES` dans son ensemble : `builder_air.nut` — étape 8.
- Traitement des candidats de subvention une fois générés (`subCandidates`, arbitrage portefeuille) :
  `projects.nut:1950-1953` et suite — étape 6.
- Décision effective à prendre sur G0 (remettre `abandon_gen_filter`/`abandon_cooldown_days` à 0 ou
  bancher isolément) : synthèse, étape 20 — cette étape ne fait que constater que rien n'a bougé côté
  `info.nut`/`settings.nut` depuis le 09-06.
