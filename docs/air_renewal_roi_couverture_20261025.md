# AIR-ROI-RENOUVELLEMENT-1 — couverture des remplacements V252

25 octobre 2026 — **audit hôte hors moteur**, avec les 40 journaux du duel de
calibration `results/calibration_pc_20261021/results/calib_duel_40x10_pc_20261021_engine`.
Pas de changement de code Squirrel, de paramètres ou de sélection de flotte.

Reproduction :

```powershell
python -X utf8 sweeps/diag_air_renewal_coverage.py `
  --logs results/calibration_pc_20261021/results/calib_duel_40x10_pc_20261021_engine `
  --out results/air_renewal_coverage_20261025.json
python -X utf8 -m unittest discover -s sweeps -p test_diag_air_renewal_coverage.py
```

## Couverture observée

| Signal | Nombre |
|---|---:|
| Parties distinctes examinées | **40** |
| `V252_REPLACE` | **1 737** |
| Prix d'achat du nouvel appareil renseignés | **1 737 / 1 737** |
| Remplacements avec relevé `LINE_REVENUE` AIR ultérieur de la même ligne, âge ≥ 2 | **1 670** |
| Remplacements sans tel relevé ultérieur | **67** |
| Épisodes suivis d'un second V252 sur la ligne avant le premier relevé mûr | **35** |
| `V252_SKIP reason=loan` | 1 625 |
| `V252_SKIP reason=no_candidate` | 864 |
| `V252_SKIP reason=cost` | 191 |
| `V252_SKIP reason=order_failed` | 115 |
| `V252_SKIP reason=cash_stop` | 62 |
| CAPEX net achat moins revente effectivement enregistré | **0** |
| Profit marginal du V252 avec témoin contrefactuel | **0** |

`V252_REPLACE` (`task_v252.nut`) contient `old_engine`, `new_engine`,
`old_veh`, `new_veh`, **prix brut d'achat**, âge et profit historique
de l'ancien véhicule. Il ne donne pas le produit effectif de revente ni le
coût de l'investissement évincé. La retraite peut être différée par
`_vehiclesToRetire`. `LINE_REVENUE.real_prof` est **le profit de la ligne
entière**, pas le gain imputable au nouvel appareil ; flotte, technologie,
époque et demande peuvent changer entre les deux dates. La présence d'un
relevé ne valide donc **pas** le ROI du renouvellement.

L'outil joint au plus un suivi descriptif par épisode après la date de
remplacement, distingue les événements censurés, les remplacements V252
intermédiaires et les motifs de refus. Il refuse les copies texte/gzip
contradictoires même si leurs comptages sont identiques. Trois tests hôte
prouvent ces invariants.

**Décision : tâche maintenue ouverte.** Avant un classement commun AIR/RAIL
ou une nouvelle politique V252, instrumenter le coût réel net, l'historique
des véhicules retirés/revendus et un contre-monde de même sauvegarde
(remplacer vs ne pas remplacer) pour 24 mois, sans confondre le profit complet
de la ligne avec le profit incrémental de l'appareil. Aucun banc nouveau
ni adoption économique dans cet audit.
