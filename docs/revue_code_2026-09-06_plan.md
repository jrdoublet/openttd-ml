# Plan de revue de code — 2026-09-06

Demandée avant de rouvrir A1 (dénominateur de classement). Découpage en étapes comme la dernière
fois (commits `27630dc`, `89929f3`, `13d21bb`, `8a9f7c7`, `1d088c6`, 2026-09-01/02) : un fichier ou
un bloc fonctionnel par étape, un écrit de constats par étape, rien de corrigé au passage.

## Méthode (reprise de la dernière fois)

- **Diagnostic seulement.** Aucun correctif dans cette passe, même évident — noter, ne pas coder.
- **Vérifier à la main, pas par grep seul.** La dernière fois, `preplan_queue` était *lu* par
  `info.nut` mais son seul site d'appel était dans du code mort (`_tryPreplan`, jamais invoqué) :
  un réglage actif en apparence peut être inatteignable. Vérifier pour chaque réglage touché
  récemment que le code qui le lit est bien exécuté, pas seulement déclaré.
- **Noter aussi ce qui N'EST PAS un bug**, pour ne pas le relitiger à la passe de correction (ex.
  étape 5 : les wagons vanilla à coût de fonctionnement nul, vérifié dans les sources du jeu, pas
  un bug côté OpexAI).
- **Ne pas répéter le mode d'échec C31/C29.3** : un réglage a été adopté par défaut sur un banc
  5 graines × 6 ans qui ne s'est pas répliqué à 20 × 10 (médiane en baisse malgré une moyenne
  positive, `p = 0,82`). Pour tout réglage actuellement à 1 par défaut, retrouver le banc qui l'a
  fait basculer et vérifier qu'il s'agit bien du banc **officiel** (n=20, victoires + p, pas
  seulement une moyenne).

## Périmètre (`ai/OpexAI/`, 17 190 lignes, par ordre de traitement proposé)

| étape | fichier(s) / fonctions | lignes | pourquoi maintenant |
|---|---|---:|---|
| 1 | **Audit des adoptions récentes** — `info.nut`, en regard des bancs cités dans `docs/journaux/journal_2026-09-06.md` | 1671 | 5 réglages viennent de passer à 1 (C20, C22, C33.2, C33.3, C36.1) ; C20/C22/C33.3/C36.1 seuls sont **sous le plancher de détection** au banc officiel 20×10 — seul C33.2 est significatif isolément. C'est exactement la configuration qui a produit l'erreur C29.3. Priorité 1, pas cher, à faire avant de committer le flip. |
| 2 | Boucle de contrôle et ordonnancement (`main.nut` : `Start()`, `_runNextTask`, budget d'opcodes/tick) | — (sous-ensemble de 4919) | Étape 2 d'origine avait trouvé le budget non reportable comme cause principale du sous-effectif de gares. Revérifier après `rail_micro_deadline` (C20) et `portfolio_cache` (C36.1), qui touchent tous deux au rythme de la boucle. |
| 3 | Portefeuille & sac à dos (`projects.nut`, `budget.nut`) | 1457 + 75 | 4 soupçons confirmés la dernière fois (élection modale avant test de capital, objectif du sac à dos en revenu, `maxBatch=1`, 6 métriques de diagnostic jamais lues). Revérifier avec `abandon_gen_filter`, `abandon_cooldown_days` et `portfolio_cache` désormais actifs. |
| 4 | Tension / prix d'ombre (`tension.nut`) | 689 | **Jamais revu** — fichier créé après la dernière revue. Trois tentatives dessus (C35.3/4/5) ont toutes été rejetées au banc officiel ; vérifier qu'il ne reste pas de code mort, de branche dupliquée ou d'effet de bord des versions abandonnées. |
| 5 | Économie & modèle de profit (`economy.nut`) | 598 | Vérifier la cohérence du modèle de traction/distance après tous les correctifs empilés depuis la dernière revue (C33.2 change le trafic capté, donc les hypothèses de charge). |
| 6 | Flotte, entretien, réutilisation (`main.nut` : `_reportLines`, `_resizeAirFleets`, `_resizeRoadFleets`, `_scrapDeadLines`, `_refleetRoadLines`, `_expandRailLines`, `_continueRailExpansion`) | — | Étape 5 d'origine avait trouvé `rail_refleet` **totalement inatteignable** (return anticipé + tâche désactivée en dur). Vérifier si c'est toujours vrai, et comment `air_joined_stops` (C33.2) s'articule avec la gestion de flotte aérienne existante. |
| 7 | Génération de candidats (`candidates.nut`) | 1739 | `abandon_gen_filter` (C22) et le cooldown (C33.3) touchent directement la génération ; vérifier l'interaction avec le vivier et `station_join` (resté à 0). |
| 8 | Constructeur rail (`builder_rail.nut`) | 2035 | `rail_micro_deadline` (C20) et `rail_search_resumable` (A4) changent le découpage en tranches de la recherche A* ; vérifier qu'aucune tranche ne fuit d'itérations ou de budget calendaire. |
| 9 | Constructeurs air / route / eau (`builder_air.nut`, `builder_road.nut`, `builder_water.nut`) | 1464 + 1332 + 456 | `air_joined_stops` (C33.2, le plus gros gain mesuré : +104 % valeur au banc officiel) mérite une lecture ligne à ligne — c'est le morceau qui pèse le plus si un bug s'y cache. |
| 10 | Catalogue (`catalog.nut`) | 755 | Vérifier la fraîcheur/coût sous le nouveau volume de trafic capté par C33.2 ; le combo intégral construit parfois *moins* de véhicules/gares pour *plus* de valeur (cf. tableau du banc factoriel) — vérifier si c'est un choix du catalogue ou un effet de bord. |

## Ordre recommandé

1. **Étape 1 d'abord** — c'est un audit de risque bon marché sur une décision qui vient d'être
   prise (le flip des 5 défauts dans `info.nut` est encore non commité). S'il révèle un problème
   à la C29.3, ça change ce qu'il faut committer avant même de lire le reste.
2. Puis 2 → 10 dans l'ordre du tableau (main.nut d'abord, car c'est lui qui orchestre tout le
   reste ; les constructeurs modaux en dernier car ce sont les plus gros et les plus isolés).

## Sortie attendue par étape

Comme la dernière fois : un écrit (nouvelle section dans le journal du jour ou fichier dédié),
constats numérotés, gravité indiquée, rien de corrigé. Une fois les 10 étapes closes, trancher
ensemble ce qui passe en correctif (probablement plusieurs tâches numérotées à ajouter à
`docs/taches.md`), avant de rouvrir A1.

## Modèle et effort par étape (2026-09-06)

Repère : la dernière revue (2026-09-01/02) a été faite fichier par fichier par **Sonnet 5** et a
donné de bons résultats (bug du budget d'opcodes, `rail_refleet` inatteignable, 4 soupçons du
sac à dos). Le seul cran au-dessus, l'audit statistique **C31** qui a rattrapé l'adoption de
C29.3 sur un banc non répliqué, a été fait par **Opus 5** — c'est le seul type de tâche ici où
Sonnet avait laissé passer quelque chose. Les niveaux d'effort renvoient au réglage du skill
`/code-review` (low/medium/high/xhigh/max ; `ultra` = revue cloud multi-agent, facturée,
déclenchée par vous, pas par moi).

| étape | contenu | Claude | effort | Codex (mapping fourni) | effort Codex | pourquoi |
|---|---|---|---|---|---|---|
| 1 | Audit des adoptions récentes | **Opus 5** | high | **sol** | high | Exactement le type de tâche où Opus a rattrapé Sonnet la dernière fois (C31/C29.3). À faire une fois de chaque côté et comparer si possible — c'est l'étape la plus sensible aux angles morts. |
| 2 | Boucle de contrôle (`main.nut`) | Sonnet 5 | high | terra | high | Format identique à l'étape 2 d'origine, déjà réussie par Sonnet. |
| 3 | Portefeuille/sac à dos (`projects.nut`, `budget.nut`) | Sonnet 5 | high | terra | high | Idem étape 3 d'origine (4 soupçons confirmés par Sonnet). |
| 4 | Tension / prix d'ombre (`tension.nut`) | **Opus 5** | high | **sol** | high | Jamais revu, raisonnement de dualité LP (complementary slackness) plus subtil, et trois tentatives dessus ont déjà échoué au banc — le fichier le plus dense en pièges. |
| 5 | Économie (`economy.nut`) | Sonnet 5 | high | terra | medium-high | Taille/nature comparables à l'étape 4 d'origine. |
| 6 | Flotte/entretien (fonctions `main.nut`) | Sonnet 5 | high | terra | medium-high | Idem étape 5 d'origine. |
| 7 | Génération de candidats (`candidates.nut`) | Sonnet 5 | high | terra | high | Deuxième plus gros fichier après `builder_rail.nut` ; garder l'effort haut. |
| 8 | Constructeur rail (`builder_rail.nut`) | Sonnet 5 | **xhigh** | terra | high | Plus gros fichier isolé (2035 lignes), et C20 vient de changer le découpage en tranches de la recherche A*. |
| 9 | Air / route / eau (`builder_air/road/water.nut`) | **Opus 5** | high | **sol** | high | C'est là que vit C33.2 (+104 % de valeur au banc officiel) — le morceau le plus coûteux si un bug s'y cache ; mérite la double lecture Claude + Codex (voir note ci-dessous). |
| 10 | Catalogue (`catalog.nut`) | Sonnet 5 | medium | terra | medium | Fichier le plus petit (755 lignes), enjeu plus faible ; remonter l'effort seulement si l'étape 9 fait douter de la fraîcheur/coût. |

Non retenus : **astra/fable** (rien n'indique que Fable soit calibré pour ce type d'audit de
code — pas de donnée fiable trouvée, je ne le recommande pas à l'aveugle) ; **luna/haiku**, trop
léger pour une tâche de recherche de bug qui doit lire des centaines de lignes en contexte.

### Ce que la recherche dit, honnêtement

Peu de sources indépendantes fiables comparent précisément Codex/GPT-5.6 et Claude 5 sur la
revue de code seule — la plupart des comparatifs trouvés sont des blogs marketing (morphllm,
dupple, superblocks, duet…), à prendre avec prudence. Le signal qui revient le plus souvent et
qui a du sens mécaniquement :

- Sur les benchmarks bruts (SWE-bench Verified, Terminal-Bench), **GPT-5.6 Sol et Opus 5 sont
  proches**, chacun en tête sur un leaderboard différent selon la source — pas d'écart net.
- Plusieurs sources créditent **Claude** d'une meilleure tenue sur les **très gros diffs** et
  d'un meilleur respect du style existant du code (conventions de nommage, idiomes du projet).
- Le point le plus solide, et le plus utile ici : **une revue croisée entre fournisseurs attrape
  une classe d'erreurs différente qu'une auto-relecture par le même modèle qui a écrit ou déjà
  revu le code.** Ce n'est pas "Codex meilleur" ou "Claude meilleur" dans l'absolu — c'est que
  les angles morts des deux familles ne se recouvrent pas.

**Conclusion pratique** : je ne trouve pas de raison solide de basculer tout le lot sur Codex.
Là où ça vaut vraiment le coût (étapes 1 et 9, les deux à plus fort enjeu), faire tourner Codex
en plus de Claude plutôt qu'à sa place — c'est le seul point de la littérature qui tienne
au-delà du marketing.
