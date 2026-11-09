# Revue de code : Alignement des assertions probes=2 résiduelles (Famille B-bis)

Date : 2026-11-07
Auteur : Agent agy (tour 2)
Périmètre : `sweeps/test_event_backlog_probe.py`, `sweeps/test_m3_equipment_roi.py`, `sweeps/test_normal_play_probe_gates.py`, `sweeps/test_sched_idle.py`

## 1. Contexte et objectif
Lors du commit `b246017e`, la valeur par défaut publique du réglage `probes` dans `info.nut` a été promue à 2 (`DEBUG_SIGNS`, affichage des panneaux de débogage sans surcharge CPU).
Le tour 1 avait aligné quatre premiers tests (`test_v167_probes.py`, `test_b9_air_catchment.py`, `test_publication_probes_default.py`, `test_signs_default_off.py`).
Quatre tests supplémentaires contenaient encore des attentes codées en dur `probes == 0` ou `custom_value = 0` dans les spécifications d'`info.nut`.

## 2. Analyse ligne à ligne du diff
- `sweeps/test_event_backlog_probe.py` :
  - `defaults["probes"] == 2` au lieu de `0` (défaut public promu).
  - Vérification supplémentaire `defaults["probes"] & 8 == 0` pour garantir que la sonde d'arriéré d'événements (masque bit 3) reste désactivée par défaut.
- `sweeps/test_m3_equipment_roi.py` :
  - `defaults["probes"] == 2` au lieu de `0`.
  - La vérification existante `defaults["probes"] & (1048576 | 128) == 0` confirme que les sondes d'équipements ROI restent désactivées par défaut.
- `sweeps/test_normal_play_probe_gates.py` :
  - Les 4 difficultés (`easy`, `medium`, `hard`, `custom`) vérifient désormais la présence de `= 2` pour le réglage `probes` dans `info.nut`.
- `sweeps/test_sched_idle.py` :
  - Vérification `custom_value = 2` dans le bloc `probes` d'`info.nut`.

## 3. Contrôles de conformité
- Fichiers `.nut` modifiés : **AUCUN**.
- Identifiants réservés Squirrel : N/A (Python uniquement).
- Respect du comportement économique : inchangé.
- Suites de non-régression obligatoires (`test_road1y*.py`, `test_road100*.py`, `test_v251*.py`) : **317 tests OK**.
- Tests de la famille : **38 tests OK** (0 échec, 0 erreur).
- `git diff --check` : **propre**.

## 4. Risques résiduels
Néant. Ces modifications corrigent des assertions d'inspection statique de `info.nut` devenues obsolètes suite à la promotion validée de `probes=2`.
