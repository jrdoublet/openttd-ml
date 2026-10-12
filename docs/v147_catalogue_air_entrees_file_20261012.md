# V147 — CD07/B : phases du catalogue AIR en entrées autonomes de la file

12 octobre 2026. Dernière étape différée du découpage du catalogue AIR
(`docs/taches.md`, « À poursuivre ») ; décision A et risques de B dans
[cd07_air_catalogue_ordonnanceur_20261012.md](cd07_air_catalogue_ordonnanceur_20261012.md).

## Ce qui change (réglage `v147_air_catalog_tasks`, défaut 0)

- **Trois entrées ajoutées en FIN de `_taskQueue`** dans `Start()`, juste après
  `OpexLoadSettings()` et seulement sous le réglage : `air_cat_scan`,
  `air_cat_publish`, `air_cat_apply`. La file historique (14 entrées, `catalog`
  à l'index 0) n'est pas modifiée : un `_taskCursor` sauvegardé garde son sens,
  les `dueCycle` sont restaurés par nom ; un curseur ≥ 14 relu sans le réglage
  retombe sur le passage au cycle suivant.
- **L'état reste `task.c78AirRebuild` sur l'entrée `catalog`.** Les consommateurs
  existants (continuation C121 du même tick, recyclage du lot AIR dans
  `_rebuildProjects`, ledgers) sont inchangés. Pas de nouvelle persistance :
  un Save/Load abandonne la transaction comme avant.
- `catalog` garde la garde de cadence, le rafraîchissement et le démarrage du
  rebuild. Pendant un rebuild, son créneau rend la main ; la phase courante
  s'exécute dans sa propre entrée, qui appelle le même `_dispatchCatalog`
  (même tranche, même publication V141, même apply/ACK AC06 v2, même queue de
  traitement après apply). Une seule entrée de phase est active à la fois
  (`OpexV147ArmPhases`), due au tour suivant, ou au cycle courant avec le
  curseur sur elle tant qu'aucun portefeuille n'existe (équivalent du requeue
  historique de l'index 0, neutralisé sous le réglage).
- Les entrées de phase sont dispatchées **avant** la porte `_projects == null`
  du scheduler, comme `catalog`. La continuation C121 du même tick appelle la
  phase courante au lieu de `catalog`.
- Ni cadence, ni budget de tranche, ni V142/V143 : le seul changement de
  comportement attendu est la position du créneau de phase dans le tour.

## Contrôles déjà passés

- 10 tests `sweeps/test_v147_air_catalog_tasks.py` (contrats statiques +
  modèle d'armement) ; suite hôte 1 962/1 965 verts, les 3 erreurs existent à
  l'identique sur master (artefacts `results/` absents, module manquant).
- Smoke 1×1 graine 42 (`v147_smoke_20261012b`) : 2/2 parties complètes, aucune
  erreur de script ; décisions journalisées sous `air_cat_scan` et
  `air_cat_publish` dans le bras ON.
- Save/Load (`results/v147_saveload_42`, sauvegarde 1970-07-01, 1 an + 1 an) :
  `LOAD_RECONCILE` présent, aucune erreur, 26 mentions `air_cat_*` après
  rechargement (régénération « reload » servie par les nouvelles entrées).

## Plan pré-enregistré (critère utilisateur : absence de dégradation, pas de gain exigé)

1. **Opcodes, 40×4** C66.4 même source, bras `v147_air_catalog_tasks=0/1`,
   `probe_loop_ops=1` aux deux, `--script-debug`, 40 graines canoniques du
   lanceur. Mesure : `LOOP_OPS` exécutés 1970–1971 et 1970–1972 (année 1973
   censurée), delta apparié, IC95 bootstrap, hausses/baisses.
   Dégradation démontrée = IC95 entièrement > 0 sur l'une des deux fenêtres.
2. **Économie, B20×10 `non_erosion`** sans sonde ni `--script-debug`, sur les
   20 graines indépendantes de la porte B de CD
   (`random.Random(20261013)`). Critère : 20/20 paires saines, borne haute
   de l'IC95 du profit annuel ≥ 0, ratio des valeurs ≥ 0,95.
3. Si les deux tiennent : V147 qualifié, **défaut laissé à 0 jusqu'à décision
   utilisateur** (aucun gain attendu d'une refonte structurelle). Sinon :
   rejet documenté, CD07/A conservé.

VPS : 3 CPU, 3 workers, 2 Go, une seule campagne à la fois.

## Résultats (12/10, VPS, une campagne à la fois)

**1. Opcodes 40×4** (`results/v147_ops_40x4_20261012*`, 80/80 parties saines,
analyse `sweeps/analyse_v147_loop_ops.py`) :

| Fenêtre | Δ LOOP_OPS moyen | IC95 bootstrap | hausses/baisses |
|---|---:|---|---:|
| 1970–1971 | **−1 339 454 (−1,06 %)** | [−1 718 985 ; −976 955] | 5/35 |
| 1970–1972 | **−1 410 801 (−0,74 %)** | [−2 665 119 ; −216 962] | 14/26 |

Pas de dégradation : baisse démontrée sur les deux fenêtres. Ventilation
1970–71 par poste (moyenne/graine) : continuation catalogue −0,2 % alors
qu'elle tourne plus souvent (1 381 entrées contre 1 180), orchestrateur
−1,11 M, budget laissé au sommeil +1,30 M. Les rebuilds ne sont pas bloqués :
mêmes volumes construits (87 véhicules, 48–49 gares). Économie du même banc :
+38 921 £/an, IC95 [−38 652 ; +115 032], 23V/17D, valeur −0,56 %.

**2. B20×10 `non_erosion`** (`results/v147_B20x10_20261012*`, 40/40 parties,
20/20 paires) : profit −52 259 £/an (médiane +7 931), IC95
[−193 578 ; +85 150], 10V/10D, p=0,60 ; valeur ratio des moyennes 0,970
(−3,0 %), garde 5 % tenue. Véhicules 162,1 → 163,3, gares 61,1 → 63,8.
**Verdict lanceur : `pass`.**

## Verdict

**V147 qualifié selon le critère d'absence de dégradation** : opcodes en
baisse démontrée, économie sans perte démontrée aux deux horizons. Aucune
équivalence stricte ni gain économique revendiqués. **Défaut laissé à 0** :
le passage à 1 et la fusion sur master relèvent de la décision utilisateur.
