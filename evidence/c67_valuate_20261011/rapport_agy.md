# Rapport de mission C67 — Lecteur de cartographie par Valuate

**Date :** 11 octobre 2026  
**Branche / Worktree :** `wt-c67-valuate`  
**Référence documentaire :** `docs/taches.md` (ligne « C67 lecteur par Valuate ») et `docs/c67_cartographie_contrat.md`

---

## 1. Contexte et objectifs

La tâche **C67 « lecteur par Valuate »** vise à évaluer le remplacement de la lecture de terrain tuile par tuile (qui invoque 6 à 8 fonctions NoAI et manipule des tables Squirrel pour chaque case) par l'utilisation native des méthodes `AITileList` / `Valuate` du moteur OpenTTD.

Les objectifs fixés par la demande et le contrat C67 sont :
1. **Exactitude** : vérifier l'équivalence stricte, champ par champ, entre le résumé produit par le lecteur par `Valuate` et le lecteur de référence tuile par tuile, sur les deux granularités contractuelles de blocs : **5×5** et **10×10**.
2. **Coût en opcodes** : mesurer la réduction d'opcodes Squirrel permise par la délégation des prédicats au C++ du moteur.
3. **Borne non suspendable** : `Valuate` et les primitives NoAI associées s'exécutant de manière atomique en C++, déterminer le coût maximal d'un appel individuel (`max_single_call`) et vérifier qu'il respecte strictement le plafond d'opcodes par tick de la machine virtuelle (borne ≤ 10 000 opcodes).
4. **Périmètre d'ingénierie** : pas de carte entière ni de partie longue ; aucun consommateur économique ; aucun changement de comportement ni de valeur par défaut.

---

## 2. Fichiers créés

Quatre composants ont été créés, sans modifier aucun fichier de production existant :

| Fichier | Rôle |
|---|---|
| [`ai/OpexAI/terrain_valuate.nut`](ai/OpexAI/terrain_valuate.nut) | Module d'implémentation du lecteur par Valuate (`OpexTerrainValuateReader`). Fournit `ReadBlock` (haute performance), `ReadBlockInstrumented` (mesure fine de chaque appel atomique) et `ReadBlockReference` (lecture miroir tuile par tuile), ainsi que `CompareSummaries`. |
| [`sweeps/fixtures/TerrainValuateProbe/info.nut`](sweeps/fixtures/TerrainValuateProbe/info.nut) | Déclaration NoAI de l'IA de diagnostic `TerrainValuateProbe` (version API 15, paramètre `blocks` = 64). |
| [`sweeps/fixtures/TerrainValuateProbe/main.nut`](sweeps/fixtures/TerrainValuateProbe/main.nut) | Contrôleur de mesure in-game. Échantillonne 64 blocs par granularité (coins, bords avec tuiles invalides, intérieur déterministe), compare l'exactitude de tous les champs du contrat §3, relève les opcodes et le coût atomique maximal, et émet des panneaux `< 31` caractères ainsi que des logs structurés `C67V_SUMMARY`. |
| [`sweeps/fixtures/TerrainValuateProbe/README.md`](sweeps/fixtures/TerrainValuateProbe/README.md) | Guide d'exécution de la fixture et des harnais. |
| [`sweeps/bench_c67_valuate.py`](sweeps/bench_c67_valuate.py) | Harnais Python autonome réutilisant l'infrastructure `bench_v2` et `game_health`. Stage les sources figées avec SHA-256 (`sources.json`), parse les panneaux/logs, valide les critères (exactitude, opcodes, borne non suspendable) et supporte un mode `--selftest` offline. |
| [`sweeps/test_c67_valuate.py`](sweeps/test_c67_valuate.py) | 10 tests unitaires hôte (staging, décodage, évaluation, cas d'échec, invariants syntaxiques Squirrel, formules géométriques contractuelles). |

### Respect des invariants Squirrel
- Aucun mot réservé (`clone`, `base`, `parent`, `resume`) utilisé comme identifiant.
- Aucune closure avec capture de variables locales.
- Déclaration `const` utilisant exclusivement un littéral (`const OPEX_TERRAIN_VALUATE_VERSION = 1;`).
- Panneaux `AISign` strictement bornés à 18 caractères au maximum (limite moteur = 31).

---

## 3. Comment exécuter

### A. Contrôles hôtes offline (sans OpenTTD ni Docker)

1. **Selftest du harnais :**
   ```bash
   python3 sweeps/bench_c67_valuate.py --selftest
   ```
   *Résultat :* `selftest passed`

2. **Tests unitaires dédiés :**
   ```bash
   python3 -m unittest sweeps/test_c67_valuate.py -v
   ```
   *Résultat :* 10/10 tests passent avec succès en 0.01s.

### B. Mesures in-game via OpenTTD (à exécuter par l'orchestrateur)

La fixture exige une partie OpenTTD (1 an de jeu, graine 42, 64 blocs échantillonnés par taille). La simulation dure moins de 2 jours virtuels pour les calculs effectifs.

**Profil VPS (limites 3 CPU, 2 Go RAM, pas de swap) :**
```bash
docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab python3 sweeps/bench_c67_valuate.py --out results/c67_valuate_measure_20261011_r1.json --seed 42 --blocks 64
```

**Profil PC local (10 CPU, 8 Go RAM) :**
```powershell
docker run --rm --cpus=10 --memory=8g --memory-swap=8g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab python3 sweeps/bench_c67_valuate.py --out results/c67_valuate_measure_20261011_r1.json --seed 42 --blocks 64
```

Le résultat produira atomiquement :
- `results/c67_valuate_measure_20261011_r1.json` (rapport structuré complet avec verdict et métriques)
- `results/c67_valuate_measure_20261011_r1.jsonl` (enregistrements mensuels bruts)
- `results/c67_valuate_measure_20261011_r1_fixture/` (bundle figé des sources avec `sources.json`)

---

## 4. Ce qui reste à mesurer (par l'orchestrateur)

Les tests unitaires et le selftest ont validé la structure, les interfaces et la chaîne de traitement. Les mesures in-game suivantes doivent être relevées lors de l'exécution Docker :

1. **Exactitude absolue (a)** : confirmation que sur les 64 blocs en 5×5 et les 64 blocs en 10×10, `errors == 0` (zéro divergence sur `sample_count`, `invalid_count`, `water_count`, `coast_count`, `flat_count`, `buildable_count`, `height_min`, `height_max`, `height_min_sum` et les ratios associés).
2. **Gain net d'opcodes (b)** : relève du ratio `(ref_total - val_total) / ref_total`. L'estimation théorique anticipe une réduction de ~80 à 90 % du coût en opcodes par bloc.
3. **Plafond non suspendable réel (c)** : vérification du pic réel `max_single_call` dans la VM Squirrel NoAI 15.3 d'OpenTTD. La valeur doit demeurer largement inférieure à la réserve de sécurité de 3 000–4 000 opcodes par tick.

---

## 5. Résultat de la suite de tests complète

Exécution de la commande requise :
```bash
python3 -m unittest discover -s sweeps -p "test_*.py"
```

**Sortie :**
```text
Ran 1870 tests in 20.111s

FAILED (failures=1, skipped=1)

FAIL: test_preexisting_builder_entirely_preserved (test_parallel_fleet_amort_shadow.SourceTests.test_preexisting_builder_entirely_preserved)
```

**Analyse de la sortie :**
- Le nombre total de tests est passé de 1860 à **1870**, confirmant que les **10 nouveaux tests** de `sweeps/test_c67_valuate.py` sont découverts et **100 % passants**.
- La seule défaillance observée (`test_preexisting_builder_entirely_preserved`) est pré-existante dans le dépôt (contrôle d'empreinte SHA-256 sur `builder_air.nut`, non lié à C67).
- Zéro régression induite par les ajouts C67.
