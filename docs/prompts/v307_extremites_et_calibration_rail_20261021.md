# Prompts — tâches simples et moyennes du 21/10 (V307 extrémités, RAIL-CAL-1)

Cinq prompts à coller dans une session d'agent sur le PC, **dans le même checkout `openttd-ml`, sur master**
(pas de worktree ni de branche). Codex est réservé aux tâches complexes. `v307` (sonde, réglages à 0) et la
branche de calibration sont fusionnées dans master depuis le 21/10.

**Règles communes, pour travailler à plusieurs dans le même dossier :**
- lire AGENTS.md §4/§4.1 ; ne changer aucun défaut ; ne lancer aucune porte B ;
- ne modifier QUE les fichiers listés dans son prompt ; `git add <ses fichiers>` (jamais `git add -A` ni `.`) ;
- avant de pousser : `git pull --rebase origin master`, puis `git push origin master` ;
- vérifier chaque citation `fichier:ligne`.

| # | Tâche | Difficulté | Fichiers modifiés | Banc local |
|---|---|---|---|---|
| 1 | V307 1.10 — lignes reçues par puits | simple | `sweeps/diag_v307_sink_joins.py`, `sweeps/test_v307_sink_joins.py`, `docs/v307_puits_lignes_20261021.md` | aucun |
| 2 | RAIL-CAL-1 étape 1 — baisse moyenne du ROI rail, hors ligne | simple | `sweeps/demo_calibration_rail_jointe_20261021.py`, `docs/calibration_rail_jointe_20261021.md`, `evidence/review/roi_calibration_predictors_20261021/calibration_rail_jointe_20261021.json` | aucun |
| 3 | V307 1.7 — pourquoi les extrémités échouent | moyenne | `ai/OpexAI/probe_v307.nut`, `sweeps/test_v307_long_probe.py`, `sweeps/diag_v307_long_paths.py`, `docs/v307_extremites_20261021.md` | 3×10 |
| 4 | RAIL-CAL-1 étape 2 — variante active, rail seul | moyenne | `ai/OpexAI/` (réglage `rail_cal`), `sweeps/test_rail_cal.py` | 1×1 puis 3×3 |
| 5 | RAIL-PROFIT-1 — expliquer les erreurs de revenu, exploitation et profit RAIL | simple | `sweeps/diag_rail_profit_components_20261021.py`, `sweeps/test_rail_profit_components_20261021.py`, `docs/diag_rail_profit_components_20261021.md` | aucun |

**En parallèle : 1, 2, 3 et 5.** Les fichiers ne se recouvrent pas ; 1, 2 et 5 ne lancent pas de banc.
**4 attend la fin de 2 et la lecture des conclusions de 5** (il lui faut les constantes et la vérification du profit),
**ainsi que la fin du banc de 3** : un banc embarque
`ai/OpexAI` tel qu'il est dans le dossier au moment du lancement.

---

## Prompt 1 — V307 1.10 : combien de lignes rejoignent un même puits (simple)

```
Dépôt openttd-ml, master : git pull --rebase origin master. Ne travaille que sur master, dans ce dossier.
D'autres agents travaillent en même temps ici : ne modifie que sweeps/diag_v307_sink_joins.py,
sweeps/test_v307_sink_joins.py et docs/v307_puits_lignes_20261021.md ; git add de ces seuls fichiers.
Lis docs/taches.md (entrée V307) et docs/v307_longs_traces_20261021.md, tâches 1.9 et 1.10 du §4.

But : décider si des gares de puits à 2-4 quais dès la construction (tâche 1.9) valent la peine.
Question : sur les gares de DESTINATION rail (le puits : centrale, usine, raffinerie, ville…), quelle
part reçoit une 2e, 3e, 4e ligne au cours d'une partie de 10 ans ?

Données, sans lancer de banc : results/calibration_pc_20261021/results/calib_duel_40x10_pc_20261021_engine
(40 parties duel de 10 ans ; .log ou .log.gz, lire avec gzip en Python). Vérifie d'abord qu'elles contiennent
les lignes utiles (OPEX ... RAIL_ATTEMPT, join_end=, shared_dest : lis dans ai/OpexAI/task_rail.nut et
ai/OpexAI/projects*.nut comment V178/V179 journalisent la destination partagée). Si elles ne les contiennent
pas, arrête-toi et dis-le : on utilisera les journaux du banc du prompt 3 (results/v307_endpoints_3x10_*_engine).

Écris sweeps/diag_v307_sink_joins.py (+ sweeps/test_v307_sink_joins.py sur un extrait de journal fabriqué) :
- repère chaque ligne rail construite et sa gare de destination ;
- compte par gare de destination le nombre de lignes reçues, par catégorie d'industrie acceptante
  (nom de l'industrie ou "ville") et par graine ;
- table : catégorie | puits | % à 1 ligne | 2 | 3 | ≥4 | délai médian entre 1re et 2e ligne (jours).

Livrable : docs/v307_puits_lignes_20261021.md, avec la table et une recommandation : N quais par catégorie,
ou « pas de quais réservés » si 80 % des puits restent à 1 ligne. Commit, pull --rebase, push sur master.
```

---

## Prompt 2 — RAIL-CAL-1 étape 1 : baisse moyenne du ROI rail calibré, hors ligne (simple)

```
Dépôt openttd-ml, master : git pull --rebase origin master. Ne travaille que sur master, dans ce dossier.
D'autres agents travaillent en même temps ici : ne modifie que sweeps/demo_calibration_rail_jointe_20261021.py,
docs/calibration_rail_jointe_20261021.md et
evidence/review/roi_calibration_predictors_20261021/calibration_rail_jointe_20261021.json ; git add de ces seuls fichiers.
Lis docs/demo_recentrage_rail_20261021.md (section « Remarques du 21/10 » en tête),
docs/calibration_cout_profit_quartiles_20261021.md et l'entrée RAIL-CAL-1 de docs/taches.md.

Contexte : le devis rail est sous-estimé et le profit rail est plutôt sous-estimé sur les grandes distances
(mais surestimé sur plusieurs petites lignes), de sorte que leurs biais se compensent en partie dans le ROI.
**Ne jamais déduire le facteur de profit du facteur de coût : ce sont deux modèles distincts.**
Décision utilisateur : on calibre le RAIL seul (**coût ET profit**, séparément), l'AIR reste inchangé ; on mesure
d'abord de combien baisse en moyenne le ROI rail calibré ; si c'est environ −20 %, on baissera l'AIR de 20 %.

Aucun code ai/OpexAI, aucun banc : réutilise les journaux PC
results/calibration_pc_20261021/results/calib_solo_40x10_pc_20261021_engine et calib_duel_40x10_pc_20261021_engine
(lignes PORTFOLIO_RANK, lues par sweeps/demo_recentrage_rail_20261021.py, dont tu peux importer les fonctions).

Écris sweeps/demo_calibration_rail_jointe_20261021.py (+ --selftest) :
1. Ajuste sur SOLO, applique sur DUEL (et par 5 plis de graines disjoints, comme le script existant) :
   - coût : devis × (a + b·d), droite de RAIL-CAPEX-1 (a=1,051981, b=0,003066 ; ré-ajuste-la sur SOLO) ;
   - profit : facteur réel/prédit par cargo × quartile de distance (≤90, 91–127, 128–172, ≥173), rétréci
     vers le facteur du quartile tous cargos : k = (n·r_cellule + 50·r_quartile)/(n + 50) ;
   - ROI calibré = ROI × facteur_profit / facteur_coût, pour les seules entrées RAIL ; AIR, flotte AIR, ROAD = 1.
   - En plus de la baisse du score, vérifier la **précision du profit lui-même** : MAE et biais monétaires
     de `profitAnnual` corrigé, par cargo et quartile de distance, par ligne mature (`age >= 2`), et
     résultats du modèle RAIL **coût seul / profit seul / coût + profit / brut** sur les mêmes plis.
     Ne pas qualifier le modèle combiné si le facteur de profit ne réduit pas réellement l'erreur de profit
     hors échantillon, ou si la correction du ROI se dégrade.
   - Garde de robustesse : `pred_prof <= 0`, profit réel négatif, cellules rares et `capitalIsActual`
     doivent être traités explicitement ; pas de ratio invalide ou de double correction du devis après A*.
2. Sur les entrées RAIL du top-5 DUEL : baisse moyenne du score pondérée par le score, globale, par quartile
   de distance, par cargo et par époque (année). C'est LE chiffre attendu par l'utilisateur.
3. Changements possibles du leader numérique (RAIL→RAIL, RAIL→AIR, AIR→RAIL), en rappelant que ce ne
   sont pas des constructions contrefactuelles (classes C77, bonus AIR).
4. Contrôle : vérifie que le ROI calibré est à peu près plat en distance (ratio au plus court / au plus long).
   Vérifie aussi les quartiles de ROI **prédit** : ne pas améliorer uniquement le niveau moyen tout en
   continuant de surestimer les faibles projets et sous-estimer les meilleurs. Indique la qualité du classement.
5. Écris en tête du livrable les constantes finales (a, b, table cargo × quartile) : le prompt 4 les recopiera.

Livrable : docs/calibration_rail_jointe_20261021.md (tables, chiffre global de baisse avec IC95 bootstrap
sur les graines, recommandation : facteur AIR à appliquer à l'étape 3) et le JSON. Commit, pull --rebase,
push sur master.
```

---

## Prompt 3 — V307 1.7 : pourquoi les extrémités échouent (moyenne)

```
Dépôt openttd-ml, master : git pull --rebase origin master. Ne travaille que sur master, dans ce dossier.
D'autres agents travaillent en même temps ici : ne modifie que ai/OpexAI/probe_v307.nut,
sweeps/test_v307_long_probe.py, sweeps/diag_v307_long_paths.py et docs/v307_extremites_20261021.md ;
git add de ces seuls fichiers.
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
coût en opcodes seulement sur les échecs. Tout nouvel appel X.Valuate(...) doit être ajouté aux inventaires
de sweeps/test_v261_forum_behaviours.py et sweeps/fixtures/v262_valuate_inventory.json (préviens si c'est le cas).
Contrats dans sweeps/test_v307_long_probe.py, lecture dans sweeps/diag_v307_long_paths.py
(table côté × cause dominante ; octants couverts ; autre octant libre ?).

Smoke : python3 -m pytest sweeps -q OK ; puis 3×10, graines 42 7 100 :
  python3 sweeps/run_c66_reference.py --campaign v307_endpoints_3x10_<date> \
    --reference "OpexAI[decision_log=1,v307_abnd_autopsy=1]" \
    --variant "OpexAI[decision_log=1,v307_abnd_autopsy=1]" --variant-policy-id same \
    --decision-rule gain_short --primary-metric profit_year --min-useful-primary-delta-pct 4 \
    --value-guard-max-loss-pct 5 --map-size 8 --repeats 1 --years 10 --seeds 42 7 100 \
    --script-debug --max-workers 3 --network host
0 ligne "[0] [S] Your script made an error". Annonce dans ta sortie quand le banc a démarré et quand il a fini
(le prompt 4 ne doit pas modifier ai/OpexAI pendant ce banc).

Livrable : docs/v307_extremites_20261021.md (table des causes, part des échecs où un autre octant était
libre, recommandation sur 1.8 sites dispersés et 1.9 quais réservés). Commit, pull --rebase, push sur master.
```

---

## Prompt 4 — RAIL-CAL-1 étape 2 : variante active, rail seul (moyenne)

```
À lancer seulement quand le prompt 2 a poussé docs/calibration_rail_jointe_20261021.md ET que le banc du
prompt 3 est terminé.
Dépôt openttd-ml, master : git pull --rebase origin master. Ne travaille que sur master, dans ce dossier.
Ne modifie que les fichiers ai/OpexAI cités ci-dessous et sweeps/test_rail_cal.py ; git add de ces seuls fichiers.
Lis AGENTS.md §4/§4.1, l'entrée RAIL-CAL-1 de docs/taches.md et docs/calibration_rail_jointe_20261021.md.

Ajoute le réglage entier rail_cal (défaut 0 aux quatre niveaux easy/medium/hard/custom dans info.nut,
lu une fois dans settings.nut, globale déclarée dans globals_pre.nut). Sous rail_cal=1, pour les seuls projets
RAIL dont le capital n'est pas déjà physique (capitalIsActual absent ou faux, voir builder_rail.nut et economy.nut) :
- coût de classement = devis × (a + b·distance) ;
- profit de classement = profit × table cargo × quartile de distance (constantes en tête de
  docs/calibration_rail_jointe_20261021.md, recopiées en table Squirrel littérale, pas de calcul en jeu) ;
appliqués au score de classement fundScore dans OpexProjectSelectAffordable
(ai/OpexAI/projects_selection.nut, les deux affectations de fundScore), SANS changer le devis,
le budget, OpexProjectFinanceCapital, K_dec, C70, ni AIR / flotte AIR / ROAD.
**Contrat obligatoire : appliquer effectivement les DEUX facteurs, coût ET profit**, et vérifier par test
qu'un facteur de profit non neutre déplace le score même lorsque le coût est laissé à 1 ; un correctif
qui ne touche que le dénominateur serait incorrect. Ne pas substituer le profit corrigé au profit réel
de l'entreprise ni recalculer la recette par un nouvel appel API. Le ratio du score doit être
`facteur_profit / facteur_coût` dans le cas où le dénominateur financier estimé est pertinent ; si
`K_dec` domine, expliciter la convention score-only retenue, et l'évaluer séparément hors ligne.
Coût visé : une recherche de table et deux multiplications par candidat RAIL, pas de recherche géométrique.

Tests : contrats dans sweeps/test_rail_cal.py (défaut 0, lu une fois, seuls les projets rail, pas de correction
si capitalIsActual, AIR inchangé, transcription Python de la table) ; python3 -m pytest sweeps -q OK.
Smoke local 1×1 puis 3×3 (graines 42 7 100), variante OpexAI[rail_cal=1] contre OpexAI : 0 erreur Squirrel ;
rapporte le nombre de lignes rail, leur distance médiane et leur cargo, par bras.
N'ouvre pas de porte A toi-même : rapporte, Claude la lancera sur GitHub. Commit, pull --rebase, push sur master.
```

---

## Prompt 5 — RAIL-PROFIT-1 : d'où vient l'erreur de profit (simple, hors ligne)

```
Dépôt openttd-ml, master : git pull --rebase origin master. Ne travaille que sur master, dans ce dossier.
D'autres agents travaillent ici : ne modifie que sweeps/diag_rail_profit_components_20261021.py,
sweeps/test_rail_profit_components_20261021.py et docs/diag_rail_profit_components_20261021.md.
Lis docs/taches.md (RAIL-PROFIT-1 et RAIL-CAL-1),
docs/calibration_cout_profit_quartiles_20261021.md et sweeps/analyse_calibration_projets.py.

Objectif : comprendre et prévoir le PROFIT ANNUEL RAIL, et non seulement corriger le CAPITAL ou le ROI.
Aucun changement ai/OpexAI, aucun Docker, aucune relance. Lis les 40×10 SOLO et DUEL existants ;
une observation par ligne RAIL construite et mature (âge >= 2), médiane des années pleines,
normalisation cohérente à la flotte de construction. Apparie PROJECT_CHOSEN, RAIL_BUILD,
LINE_REVENUE ; signale les lignes non appariées et les biais de sélection.

1. Décompose les erreurs : revenu annuel prédit/réalisé (`pred_rev`, `real_rev`), coût courant
   (`pred_run`, `real_run`), profit net (`pred_prof`, `real_prof`), et amortissement si réellement
   identifiable dans les journaux. Vérifie les unités et l'égalité comptable avant d'attribuer
   un écart de profit au revenu, à l'entretien ou à l'amortissement. Ne devine pas une variable
   absente : indique les données supplémentaires qui nécessiteraient une sonde passive.
2. Par fret/cargo, PASS, distance, capital prévu et ROI prévu : quelles composantes expliquent
   la surestimation des faibles profits et la sous-estimation des meilleurs ? Distingue les
   quartiles selon ROI PRÉDIT et selon ROI RÉALISÉ, pour éviter la régression vers la moyenne.
3. Sur SOLO entraînement → DUEL évaluation avec cinq plis de graines disjointes, compare les
   modèles de profit : brut ; facteur global ; facteur cargo ; cargo × bande de distance
   rétréci ; et au maximum un ou deux signaux déjà disponibles au classement (sans scans).
   Publie MAE £/an, biais, calibration par quartile et qualité du rang ; retiens un facteur
   uniquement s'il améliore HORS ÉCHANTILLON le profit prévu. Garde les profits réels négatifs
   dans les métriques, et ne divise pas par des prévisions nulles/négatives.
4. Confronte les résultats au modèle de coût du prompt 2, sans faire dépendre artificiellement
   le profit du coût ; chiffrer si la correction conjointe stabilise effectivement le ROI.
5. Propose, en séparant preuve et hypothèse, les prochains signaux peu chers (cargo, demande
   captable déjà calculée, production, charge/capacité, temps de cycle, note des gares,
   concurrents, wagons/trains prévus), avec estimation du coût d'opcodes et interdiction
   d'appels coûteux par candidat. Ne change pas l'AIR qui reste la référence performante.

Livrable : tableau d'attribution des écarts de PROFIT, comparaison hors graines et recommandation
de correcteur profit léger ou verdict « pas qualifié ». Écris les limites des logs. Tests sur
extraits synthétiques, commit de ces seuls fichiers, pull --rebase, push sur master.
```
