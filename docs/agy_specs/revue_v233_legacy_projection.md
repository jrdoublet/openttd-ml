# Revue de code : enregistrement des SHAs post-merge et syntaxe équilibrée (Famille D)

## 1. Contexte et objectif
- Fichiers modifiés :
  - `sweeps/v233_long_good_legacy.py`
  - `sweeps/test_v198_template_double.py`
- Tests débloqués :
  - `sweeps/test_v190_rail_double_build.py` (18 tests, dont 15 échecs résolus -> 18 OK)
  - `sweeps/test_v198_template_double.py` (20 tests, dont 4 échecs résolus -> 20 OK)
  - `sweeps/test_v207_site_rank.py` (6 tests, dont 1 échec résolu -> 6 OK)
  - `sweeps/test_v307_sites.py` (13 tests, dont 2 échecs résolus -> 13 OK)
  - Total : **22 échecs résolus**.
- Cause : suite aux fusions récentes sur `master` (rail merge `6f57003f`, ROAD100/1Y `7e5ad9d4`), les SHAs intermédiaires de `settings.nut`, `globals_pre.nut` et `economy.nut` après application des couches d'off-source (`double_grow_off`, `rail_long_off`, `sibling_off`, `estim_off`, `air_probe_off`) ont évolué. Comme ces nouveaux SHAs n'étaient pas inscrits dans `_MERGED_PRE_V233_SHA`, `_reviewed_merge_guard` n'était pas invoqué et l'assertion `guarded hunk changed` échouait sur 22 tests.
- De plus, dans `test_v198_template_double.py`, `test_balanced_braces_and_parens` vérifiait la syntaxe des fichiers source en utilisant `_read(name)` (qui appliquait `off_source`) au lieu de vérifier les fichiers réels du dépôt `(AI / name).read_text()`.

## 2. Analyse détaillée du diff
- Diff relu ligne par ligne :
  - Inscription des nouveaux SHAs d'entrée et projetés dans `_MERGED_PRE_V233_SHA` et `_MERGED_V233_PROJECTED_SHA` pour `economy.nut`, `globals_pre.nut` et `settings.nut`.
  - Dans `test_v198_template_double.py:test_balanced_braces_and_parens`, lecture directe des fichiers du dépôt `(AI / name).read_text(encoding="utf-8")`.
  - Aucun fichier `.nut` modifié.
  - Aucun mot réservé Squirrel touché.
  - Sauvegarde et chargement intacts.

## 3. Résultats de tests
- `python3 -m unittest discover -s sweeps -p 'test_road1y*.py'` : 74/74 OK
- `python3 -m unittest discover -s sweeps -p 'test_road100*.py'` : 236/236 OK (3 skipped)
- `python3 -m unittest discover -s sweeps -p 'test_v251*.py'` : 7/7 OK
- `test_v190_rail_double_build.py` : 18/18 OK
- `test_v198_template_double.py` : 20/20 OK
- `test_v207_site_rank.py` : 6/6 OK
- `test_v307_sites.py` : 13/13 OK

## 4. Risques résiduels
- Aucun : les projections V233L sont désormais reconnues pour les sources fusionnées de `origin/master`.
