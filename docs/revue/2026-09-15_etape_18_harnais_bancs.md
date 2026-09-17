# Étape 18 — Harnais — banc officiel et diagnostic P1

- **SHA revu** : `4963cb0`
- **Modèle / effort prévus** : Sonnet 5 / high
- **Périmètre** : `sweeps/bench_v2.py`, `bench.py`, `head_to_head.py`, `diag_c63_c58.py` — 2 159 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Appariement par graine, test des signes, et G0 : épinglage explicite des réglages dans CHAQUE
bras, contrôle inclus. G0bis : aucun coût d'opcodes dans les JSON de banc.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

### 18.1 — Bras de contrôle « OpexAI » nu : aucun épinglage, aucun enregistrement des défauts réellement joués        [gravité : P1]
`sweeps/bench_v2.py:238-239` — pour le nom d'arm brut `"OpexAI"` (sans crochets), `parse_opex_variant`
renvoie `None` et `build_arms` construit l'arm avec `opex_params or ()`, c'est-à-dire un tuple de
réglages **vide** : le bras hérite silencieusement de tout ce que `ai/OpexAI/info.nut` déclare comme
défaut au moment du run. Le payload final ne pallie pas ce trou : `"arms": args.arms` (`bench_v2.py:667`)
n'enregistre que la chaîne `"OpexAI"`, jamais la liste résolue des réglages effectivement en jeu. Le
JSON de sortie ne permet donc pas, a posteriori, de savoir quelle configuration de référence a
tourné le jour du banc — exactement le constat G0 : le bras de contrôle n'épingle pas une
configuration figée, il pointe vers une cible mouvante (`info.nut`) sans laisser de trace.

### 18.2 — Aucun garde-fou contre un réglage hors-défaut épinglé identiquement dans les deux bras        [gravité : P1]
`sweeps/bench_v2.py:90-228` (`parse_opex_variant`) valide les bornes de chaque `cle=valeur` mais ne
compare jamais la valeur fournie au défaut réellement déclaré dans `ai/OpexAI/info.nut`. Rien
n'empêche donc d'épingler la même valeur non standard dans les deux bras d'une comparaison. C'est
précisément le cas documenté à l'étape 1 pour `feeder_mail_strict_orders` : les deux bras pinnent
`feeder_candidates=1, feeder_portfolio=0, feeder_hub_check=0`, alors que
`ai/OpexAI/info.nut:1191-1196` (`feeder_candidates`, défaut `0`), `:1180-1185`
(`feeder_portfolio`, défaut `1`) et `:1365-1370` (`feeder_hub_check`, défaut `1`) montrent que les
trois valeurs pinnées divergent du défaut livré dans les deux bras à la fois. Le résultat mesuré ne
se transporte donc pas au comportement par défaut : `parse_opex_variant` ne peut pas le détecter, et
rien dans `bench_v2.py` ne journalise un écart entre « valeur pinnée » et « valeur par défaut du
moment ».

### 18.3 — `staged_bootstrap` inexprimable par le harnais ; quatre autres réglages pinnable-mais-jamais-forcés        [gravité : P2]
`ai/OpexAI/info.nut:2432` déclare le réglage `staged_bootstrap`, absent de la liste blanche de
`parse_opex_variant` (ni parmi les branches nommées `sweeps/bench_v2.py:111-218`, ni dans les deux
gros tuples de booléens `:219` et `:222`) : toute tentative de l'épingler via
`OpexAI[staged_bootstrap=...]` lève `ValueError("reglage OpexAI inconnu: staged_bootstrap")`. Ce
réglage ne peut donc être pinné dans AUCUN bras par ce harnais — il suit silencieusement le défaut
d'`info.nut`, sans que le nom de l'arm ni le JSON n'en disent rien. `vivier_ratio_filter`
(`bench_v2.py:219`), `feeder_hub_wait_max` (`:192-194`), `feeder_hub_min_days` (`:195-197`) et
`air_joined_stop_limit` (`:207-209`), eux, sont bien reconnus par le harnais mais restent
optionnels : un run qui omet de les citer explicitement les laisse hériter du défaut courant sans
avertissement, dans les deux bras.

### 18.4 — Aucun test des signes automatisé (seuil ≥15/20, p<0,05) dans les 4 scripts        [gravité : P1]
`paired_comparisons()` (`sweeps/bench_v2.py:556-607`) ne calcule et n'expose qu'un compte de
victoires strictes, `"arm_a_beats_arm_b": sum(difference > 0 ...)` (ligne 599), et un `"n"` qui est
le nombre de paires valides (métrique non nulle des deux côtés) — ce `n` **inclut** les ex æquo, il
n'isole pas un dénominateur propre au test des signes. Aucun champ n'expose le nombre de défaites de
`arm_a`, le nombre d'ex æquo, une p-valeur, ni un verdict par rapport au seuil ≥15/20 documenté dans
`ai/OpexAI/CLAUDE.md:97-100`. Une recherche complète des quatre fichiers du périmètre (lecture
intégrale + grep ciblé sur `sign|p_value|0.05|15/20`) ne trouve aucune implémentation de test des
signes ni dans `bench.py`, ni dans `head_to_head.py`, ni dans `diag_c63_c58.py`. Le seuil décisif du
protocole officiel — celui qui doit trancher avant les moyennes — n'est donc appliqué par aucun
script : un humain doit reconstruire wins/losses/ties à la main, et les pertes/égalités ne sont même
pas dérivables du JSON produit (seules les statistiques agrégées sont écrites, pas les différences
brutes par graine).

### 18.5 — Aucun coût d'opcodes ni densité profit/opcode dans aucun JSON de sortie        [gravité : P1]
Confirmation de G0bis sur l'ensemble du périmètre : `SUCCESS_METRICS` (`sweeps/bench_v2.py:68-74`),
`keep()` (`:340-368`), `keep_c63()` (`diag_c63_c58.py:921-937`), `keep()` de `bench.py:65-83` et
`keep()` de `head_to_head.py:87-120` ne lisent aucune donnée d'opcodes (pas d'appel à
`AIController.GetOpsTillSuspend`/équivalent, aucun champ `ops`, `opcode`, `cpu`) et ne calculent
aucun ratio profit/opcode. La seule mesure de coût de calcul présente dans le périmètre est indirecte
et qualitative : `diag_c63_c58.py` inventorie des sondes de dépense financière (`C63_INVEST`,
`OpexC63RecordSpend...`) mais rien qui rapporte un profit à un budget d'opcodes. La métrique nord du
projet (coût/opcode) n'apparaît donc dans aucun des quatre scripts.

## Vérifié, n'est PAS un bug

- **Appariement par graine (correct)** : `experiments()` (`sweeps/bench_v2.py:410-424`) construit une
  partie isolée par `(arm, seed, repeat)` en réutilisant explicitement la même valeur `seed` pour
  chaque `arm` de la boucle externe — ce n'est pas un tirage indépendant par bras.
  `paired_comparisons()` (`:556-607`) apparie ensuite par clé `(arm, seed)` dans le dict `per_seed`
  et calcule `shared_seeds` comme l'intersection réelle des graines couvertes par les deux bras
  (`:571-573`), jamais par ordre de ligne ou d'index. Le calcul de différence apparié
  (`a - b` par graine, moyenne des différences plutôt que différence des moyennes, `:582-588`)
  correspond exactement à ce que la docstring du fichier annonce (`bench_v2.py:1-6`).
- **Exclusion des ex æquo de la victoire (correct, mais partiel)** : `arm_a_beats_arm_b =
  sum(difference > 0 for difference in differences)` (`bench_v2.py:599`) exclut bien une différence
  nulle du compte de victoires — un ex æquo n'est jamais compté comme une victoire de `arm_a`. Ce
  point précis, demandé explicitement par la tâche, est correct. Ce qui manque n'est pas ce
  décompte lui-même mais tout le reste du test des signes (voir 18.4).
- **`head_to_head.py` et `diag_c63_c58.py::run_campaign` ne sont pas le banc officiel apparié** :
  le premier joue une seule partie partagée 1v1 (`shared_game: true`, aucun pairing par graine
  nécessaire puisque les deux bras sont dans la même partie) ; le second est un diagnostic 5×6
  non apparié, un seul arm contre AAAHogEx en partie partagée, explicitement positionné comme
  étape de diagnostic (`diag_c63_c58.py:1,940-946`) et non comme le banc décisif. L'absence de
  test des signes ou de pairing par graine y est cohérente avec leur rôle documenté, ce n'est pas
  une lacune du banc officiel lui-même.

## Hors périmètre, à relire ailleurs

- Les valeurs de défaut réelles de `feeder_candidates` / `feeder_portfolio` / `feeder_hub_check` /
  `staged_bootstrap` dans `ai/OpexAI/info.nut` n'ont été vérifiées que par grep ciblé pour recouper
  l'étape 1 ; une lecture intégrale d'`info.nut` (2 643 l.) est hors périmètre de l'étape 18.
- `sweeps/bench.py` (« Étape 0 ») ne fait jamais jouer OpexAI (`opponents()` ne liste que `trAIns`,
  `AdmiralAI`, `AAAHogEx`, `bench.py:58-62`) et sa docstring l'annonce lui-même comme une étape
  antérieure au face-à-face. Il n'y a donc pas de pairing ou d'épinglage OpexAI à juger dans ce
  fichier ; savoir s'il doit être supprimé ou archivé relève du journal (`docs/taches.md`), pas de
  cette étape.
- La correction de `parse_opex_variant` (18.1-18.3) et l'ajout d'un test des signes automatisé
  (18.4) toucheraient le format même des JSON de banc consommés par d'autres scripts d'analyse
  (`analyse_c50b_*.py`, hors périmètre de l'étape 18) : tout correctif devra vérifier leur
  compatibilité, à traiter dans une étape ultérieure dédiée au correctif plutôt qu'ici.

## Passe de correction ? H5/G0bis, 2026-09-16

Le constat 18.5 est corrig? dans `bench_v2.py` sans pr?tendre disposer d'un compteur
CPU global. Le JSON contient d?sormais `opcode_observation` avec
`complete_cpu_measurement=false`, le d?tail des composantes mesur?es, et les
statistiques/?carts appari?s sur `observed_opcodes_total`,
`final_profit_year_per_observed_mopcode` et `company_value_per_observed_mopcode`.

Sources r?elles consomm?es : `IG|` (s?lection), `OB|A` (tentative rail plan+build),
`RB|` (plan/build route), `OA|` (plan air) et `OM|W` (plan eau des succ?s). Les
anciens `IG|` ? sept champs restent lisibles et sont simplement d?pourvus de la
composante s?lection H5. `OB|...` du rapport historique est explicitement distingu?
de `OB|A|...`.

Preuves : `test_campaign_freeze.py` 10/10 ; smoke 2?3
`review_h5_final_smoke_2x3.json` PASSED ; `review_h5_observed_ops_2x3.json` complet,
z?ro ?chec, somme des composantes exactement ?gale au total pour chaque run.
Une r?gression locale de `paired_comparisons()` d?couverte pendant cette passe
(masquage du param?tre `metrics`) a ?t? corrig?e avant cl?ture et poss?de maintenant
un test d?di?.
