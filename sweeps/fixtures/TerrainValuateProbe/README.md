# C67 — fixture de mesure « lecteur par Valuate »

Cette IA de diagnostic évalue le lecteur par Valuate (`terrain_valuate.nut`) contre
le lecteur de référence tuile par tuile de C67 (`terrain_map.nut`).
Voir [contrat de cartographie](../../../docs/c67_cartographie_contrat.md) et [tâches](../../../docs/taches.md).

## Objectifs de la fixture

1. **Exactitude** : vérifie champ par champ l'égalité stricte du résumé Valuate avec la
   lecture de référence tuile par tuile sur blocs 5×5 et 10×10 (comptes de tuiles,
   eau, côte, constructibilité, plat, altitudes min/max/somme et ratios dérivés).
2. **Coût en opcodes** : mesure comparative des opcodes consommés par bloc (référence vs Valuate).
3. **Borne non suspendable** : mesure du pic maximal d'un appel atomique non suspendable
   (`Valuate` / `AddRectangle` / `Sort`) pour confirmer son respect de la limite par tick
   (borne ≤ 10 000 opcodes).

## Exécution

La fixture s'exécute dans une partie courte (1 an, graines de diagnostic) via le harnais
dédié `sweeps/bench_c67_valuate.py` :

```powershell
python -X utf8 -m unittest discover -s sweeps -p test_c67_valuate.py -v
```

Commande Docker à lancer par l'orchestrateur pour la mesure in-game (profil VPS) :

```powershell
docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab python3 sweeps/bench_c67_valuate.py --out results/c67_valuate_measure_20261011_r1.json --seed 42 --blocks 64
```

Sur PC local (10 cœurs) :

```powershell
docker run --rm --cpus=10 --memory=8g --memory-swap=8g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab python3 sweeps/bench_c67_valuate.py --out results/c67_valuate_measure_20261011_r1.json --seed 42 --blocks 64
```
