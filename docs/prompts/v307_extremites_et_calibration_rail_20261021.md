# Prompts — tâches simples et moyennes du 21/10 (V307 extrémités, RAIL-CAL-1)

Quatre prompts indépendants, à coller dans une session d'agent (agy, Claude Code PC…) à la racine d'un
checkout à jour d'`openttd-ml`. Codex est réservé aux tâches complexes. Règles communes à tous :
lire AGENTS.md §4/§4.1 ; ne changer aucun défaut ; ne rien fusionner ; ne lancer aucune porte B ;
un worktree par agent ; vérifier chaque citation `fichier:ligne` ; commit sur la branche indiquée.

| # | Tâche | Difficulté | Branche de départ | Code IA |
|---|---|---|---|---|
| 1 | V307 1.10 — lignes reçues par puits | simple | `v307` | non |
| 2 | RAIL-CAL-1 étape 1 — baisse moyenne du ROI rail, hors ligne | simple | `review/roi-calibration-predictors-20261021` | non |
| 3 | V307 1.7 — pourquoi les extrémités échouent | moyenne | `v307` | sonde, défaut 0 |
| 4 | RAIL-CAL-1 étape 2 — variante active rail seul | moyenne | `master` | réglage, défaut 0 |

Ordre conseillé : 1 et 2 en parallèle ; 3 ensuite ; 4 seulement après le résultat de 2.

---

## Prompt 1 — V307 1.10 : combien de lignes rejoignent un même puits (simple)

```
Dépôt openttd-ml. git fetch ; worktree depuis origin/v307 (branche v307-sinks).
Lis docs/taches.md (entrée V307) et docs/v307_longs_traces_20261021.md, tâches 1.9 et 1.10 du §4.

But : décider si des gares de puits à 2-4 quais dès la construction (tâche 1.9) valent la peine.
Question : sur les gares de DESTINATION rail (le puits : centrale, usine, raffinerie, ville…), quelle
part reçoit une 2e, 3e, 4e ligne au cours d'une partie de 10 ans ?

Données : des journaux decision_log de 10 ans. S'il n'en existe pas localement (results/*_engine avec
des lignes "OPEX ... RAIL_ATTEMPT" / "join_end=" / "shared_dest"), lance un banc de diagnostic :
  python3 sweeps/run_c66_reference.py --campaign v307_sinks_3x10_<date> \
    --reference "OpexAI[decision_log=1]" --variant "OpexAI[decision_log=1]" --variant-policy-id same \
    --decision-rule gain_short --primary-metric profit_year --min-useful-primary-delta-pct 4 \
    --value-guard-max-loss-pct 5 --map-size 8 --repeats 1 --years 10 --seeds 42 7 100 \
    --script-debug --max-workers 3 --network host
(seule la référence sert ; lire les .log ou .log.gz avec zcat -f).

Écris sweeps/diag_v307_sink_joins.py (+ un test unitaire minimal sur un extrait de journal fabriqué) :
- repère chaque ligne rail construite et sa gare de destination (lire dans ai/OpexAI/task_rail.nut et
  projects*.nut comment V178/V179 journalisent la destination partagée : join_end=B, shared_dest) ;
- compte par gare de destination le nombre de lignes reçues, par catégorie d'industrie acceptante
  (nom de l'industrie ou "ville") et par graine ;
- table : catégorie | puits | % à 1 ligne | 2 | 3 | ≥4 | délai médian entre 1re et 2e ligne (jours).

Livrable : section « 1.10 » ajoutée à docs/v307_longs_traces_20261021.md, avec la table et une
recommandation : N quais par catégorie (ou « pas de quais réservés » si 80 % des puits restent à 1 ligne).
Commit sur v307-sinks, pousse la branche.
```

---

## Prompt 2 — RAIL-CAL-1 étape 1 : baisse moyenne du ROI rail calibré, hors ligne (simple)

```
Dépôt openttd-ml, worktree depuis origin/review/roi-calibration-predictors-20261021 (branche rail-cal-shadow).
Lis docs/demo_recentrage_rail_20261021.md (section « Remarques du 21/10 » en tête),
docs/calibration_cout_profit_quartiles_20261021.md et l'entrée RAIL-CAL-1 de docs/taches.md de cette branche.

Contexte : le devis rail est sous-estimé et le profit rail aussi, tous deux d'autant plus que la ligne est
longue. Décision utilisateur : on calibre le RAIL seul (coût ET profit), l'AIR reste inchangé ; on mesure
d'abord de combien baisse en moyenne le ROI rail calibré ; si c'est environ −20 %, on baissera l'AIR de 20 %.

Aucun code ai/OpexAI, aucun banc : réutilise les journaux PC calib_solo_40x10_pc_20261021_engine et
calib_duel_40x10_pc_20261021_engine (lignes PORTFOLIO_RANK, lues par sweeps/demo_recentrage_rail_20261021.py).

Écris sweeps/demo_calibration_rail_jointe_20261021.py (+ --selftest) :
1. Ajuste sur SOLO, applique sur DUEL (et par 5 plis de graines disjoints, comme le script existant) :
   - coût : devis × (a + b·d), droite de RAIL-CAPEX-1 (a=1,051981, b=0,003066 ; ré-ajuste-la sur SOLO) ;
   - profit : facteur réel/prédit par cargo × quartile de distance (≤90, 91–127, 128–172, ≥173), rétréci
     vers le facteur du quartile tous cargos : k = (n·r_cellule + 50·r_quartile)/(n + 50) ;
   - ROI calibré = ROI × facteur_profit / facteur_coût, pour les seules entrées RAIL ; AIR, flotte AIR, ROAD = 1.
2. Sur les entrées RAIL du top-5 DUEL : baisse moyenne du score pondérée par le score, globale, par quartile
   de distance, par cargo et par époque (année). C'est LE chiffre attendu par l'utilisateur.
3. Changements possibles du leader numérique (RAIL→RAIL, RAIL→AIR, AIR→RAIL), en rappelant que ce ne
   sont pas des constructions contrefactuelles (classes C77, bonus AIR).
4. Contrôle : vérifie que le ROI calibré est à peu près plat en distance (ratio au plus court / au plus long).

Livrable : docs/calibration_rail_jointe_20261021.md (tables, chiffre global de baisse avec IC95 bootstrap
sur les graines, recommandation : facteur AIR à appliquer à l'étape 3). JSON dans
evidence/review/roi_calibration_predictors_20261021/. Commit sur rail-cal-shadow, pousse la branche.
```

---

## Prompt 3 — V307 1.7 : pourquoi les extrémités échouent (moyenne)

```
Dépôt openttd-ml. worktree depuis origin/v307 (branche v307-endpoints).
Lis AGENTS.md, docs/taches.md (entrée V307) et docs/v307_longs_traces_20261021.md (§2.5-2.6, §4 tâches 1.7-1.9).

Contexte : les abandons rail (ABND, 20 000 itérations) fret viennent surtout de la destination (côté
étroit, 1 à 8 quais candidats contre 12). OpexStationPlans (ai/OpexAI/builder_rail.nut) est une spirale
qui s'arrête aux 12 plans les plus proches, sans AIList. Question : la poche est-elle enclavée par notre
propre voie, par un rival, l'eau ou le relief, et un autre octant aurait-il été libre ?

Code (sonde seulement, sous le réglage existant v307_abnd_autopsy, défaut 0 ; ne rien changer d'autre) :
dans ai/OpexAI/probe_v307.nut, pour chaque autopsie (OpexV307Autopsy) et chaque bras V307_ARM en échec
(NOPA/ABND), journalise une ligne V307_ENDPOINT par côté (A et B) :
  nombre de plans ; distance max des plans au centre (industrie ou ville) ; octants couverts (8 secteurs) ;
  dans un carré de 3 tuiles autour de chaque quai : tuiles de notre rail (AICompany.IsMine(AITile.GetOwner)),
  rail rival, eau, maisons/bâtiments de ville, non plates, libres constructibles ; somme et min sur les plans.
Squirrel : aucune closure (function( interdit), pas de .find(, pas d'identifiants clone/base/parent/pass,
coût en opcodes seulement sur les échecs. Contrats dans sweeps/test_v307_long_probe.py, lecture dans
sweeps/diag_v307_long_paths.py (table côté × cause dominante ; octants couverts ; autre octant libre ?).

Smoke : python3 -m pytest sweeps -q -x OK ; puis 3×10, graines 42 7 100 :
  python3 sweeps/run_c66_reference.py --campaign v307_endpoints_3x10_<date> \
    --reference "OpexAI[decision_log=1,v307_abnd_autopsy=1]" \
    --variant "OpexAI[decision_log=1,v307_abnd_autopsy=1]" --variant-policy-id same \
    --decision-rule gain_short --primary-metric profit_year --min-useful-primary-delta-pct 4 \
    --value-guard-max-loss-pct 5 --map-size 8 --repeats 1 --years 10 --seeds 42 7 100 \
    --script-debug --max-workers 3 --network host
0 ligne "[0] [S] Your script made an error".

Livrable : section « 1.7 » dans docs/v307_longs_traces_20261021.md (table des causes, part des échecs où
un autre octant était libre, recommandation sur 1.8 sites dispersés et 1.9 quais réservés). Commit sur
v307-endpoints, pousse la branche.
```

---

## Prompt 4 — RAIL-CAL-1 étape 2 : variante active, rail seul (moyenne)

```
À lancer seulement quand le prompt 2 a livré docs/calibration_rail_jointe_20261021.md.
Dépôt openttd-ml, worktree depuis origin/master (branche rail-cal). Lis AGENTS.md §4/§4.1, l'entrée
RAIL-CAL-1 et docs/calibration_rail_jointe_20261021.md (branche rail-cal-shadow).

Ajoute le réglage entier rail_cal (défaut 0 aux quatre niveaux easy/medium/hard/custom, info.nut,
settings.nut lu une fois, globale déclarée dans globals_pre.nut). Sous rail_cal=1, pour les seuls projets
RAIL dont le capital n'est pas déjà physique (capitalIsActual absent ou faux) :
- coût de classement = devis × (a + b·distance) ;
- profit de classement = profit × table cargo × quartile de distance (constantes du prompt 2, en table
  Squirrel littérale, pas de calcul en jeu) ;
appliqués au score de classement fundScore dans OpexProjectSelectAffordable
(ai/OpexAI/projects_selection.nut, les deux affectations de fundScore), SANS changer le devis,
le budget, OpexProjectFinanceCapital, K_dec, C70, ni AIR / flotte AIR / ROAD.
Coût : une recherche de table et deux multiplications par candidat RAIL.

Tests : contrats dans un nouveau sweeps/test_rail_cal.py (défaut 0, lu une fois, seuls les projets rail,
pas de correction si capitalIsActual, AIR inchangé, transcription Python de la table) ; suite complète OK.
Smoke local 1×1 puis 3×3 (graines 42 7 100), variante OpexAI[rail_cal=1] contre OpexAI : 0 erreur Squirrel ;
journalise et rapporte le nombre de lignes rail, leur distance médiane et leur cargo, par bras.
N'ouvre pas de porte A toi-même : rapporte, Claude la lancera sur GitHub.
Commit sur rail-cal, pousse la branche.
```
