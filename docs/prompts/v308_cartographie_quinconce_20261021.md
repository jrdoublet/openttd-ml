# Prompt — V308 : valider le quinconce à 6 points contre la vérité des 64 tuiles (moyenne)

À coller dans une session d'agent sur le PC, dans le checkout `openttd-ml`, **sur master**.
Peut tourner en parallèle des prompts 1 et 2 de
[`v307_extremites_et_calibration_rail_20261021.md`](v307_extremites_et_calibration_rail_20261021.md),
**pas** pendant le banc du prompt 3 ni pendant le prompt 4 (tous modifient `ai/OpexAI` ou lancent un banc).

```
Dépôt openttd-ml, master : git pull --rebase origin master. Ne travaille que sur master, dans ce dossier.
D'autres agents travaillent ici : ne modifie que ai/OpexAI/probe_v308.nut (nouveau), les lignes de
réglage V308 dans ai/OpexAI/info.nut, settings.nut, globals_pre.nut, le crochet dans main.nut et probes.nut,
sweeps/test_v308_carto.py, sweeps/diag_v308_carto.py, docs/v308_cartographie_quinconce_20261021.md ;
git add de ces seuls fichiers. Lis AGENTS.md §4/§4.1 et docs/v308_cartographie_quinconce_20261021.md.

But : mesurer, sans changer aucune décision de l'IA, si le quinconce à 6 points voit mieux le terrain
que les 5 points de V307, pour un coût comparable.

Sonde passive, sur le modèle de la sonde V307 (ai/OpexAI/probe_v307.nut, OpexV307MaybeRun) :
- réglage v308_carto_probe (défaut 0 aux 4 niveaux ; lu une fois ; globale déclarée) : à 1, une seule
  exécution bloquante à l'année de départ + v307_probe_year, jamais après un chargement ; crochet dans
  les deux boucles (main.nut et la boucle profilée de probes.nut), comme V307 ;
- tire 400 blocs 8×8 au hasard (AIBase.RandRange), hors bord de carte ;
- pour chaque bloc, lit les 64 tuiles (vérité) : IsSeaTile, IsRiverTile, IsWaterTile (lac = eau non mer
  non rivière), IsCoastTile, IsHouseTile, GetTownAuthority, GetMinHeight/GetMaxHeight,
  IsBuildable, AIRoad.IsRoadTile ;
- évalue sur les mêmes tuiles, en mesurant ses opcodes avec AIController.GetOpsTillSuspend() :
  (a) V307 5 points (4,4),(2,2),(6,2),(2,6),(6,6) ;
  (b) quinconce 6 points : périphériques (3,1),(6,2),(1,5),(4,6) puis centraux (2,3),(5,4) toujours lus ;
  (c) comme (b), avec court-circuit : centraux sautés seulement si les 4 périphériques classent le
      bloc en mer/lac (≥2), ville (≥2 maisons ou autorité ≥3) ou montagne (max−min ≥ 4) ;
  (d) comme (b), motif décalé d'une tuile quand (bx+by) est impair ;
  (e) variante de l'utilisateur : centraux lus seulement si les 4 périphériques sont plats et secs.
- journalise une ligne V308_BLOCK par bloc : vérités (comptes par classe, rivière traversante oui/non :
  une composante de rivière qui touche deux bords opposés), et pour chaque motif : classes vues, ops.
Squirrel : aucune closure, pas de .find(, pas d'identifiants clone/base/parent/pass. Tout nouvel appel
X.Valuate(...) va dans les inventaires de sweeps/test_v261_forum_behaviours.py et
sweeps/fixtures/v262_valuate_inventory.json.

Tests : sweeps/test_v308_carto.py (défaut 0, lu une fois, crochet unique dans les deux boucles,
positions du quinconce = une par ligne et colonne 1..6, transcription Python des motifs) ;
python3 -m pytest sweeps -q OK (3 tests ROI peuvent exiger numpy).
Banc : smoke 1×1 puis 3 graines (42 7 100) × 2 années de sonde (v307_probe_year=0 et =6) :
  python3 sweeps/run_c66_reference.py --campaign v308_carto_<date> \
    --reference "OpexAI[v308_carto_probe=1]" --variant "OpexAI[v308_carto_probe=1,v307_probe_year=6]" \
    --variant-policy-id y6 --decision-rule gain_short --primary-metric profit_year \
    --min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5 --map-size 8 --repeats 1 --years 7 \
    --seeds 42 7 100 --script-debug --max-workers 3 --network host
0 ligne "[0] [S] Your script made an error".

sweeps/diag_v308_carto.py : par motif, taux de manqués par classe (rivière traversante, lac, mer, ville,
montagne), faux positifs, opcodes médians et p90 par bloc. Ajoute la table et une recommandation
(motif à retenir pour une carte partagée) dans docs/v308_cartographie_quinconce_20261021.md, section
« Résultats ». Ne change aucun défaut. Commit, pull --rebase, push sur master.
```
