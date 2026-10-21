# V309 — temps d'attente et cartographie, étape 0 hors partie

21 octobre 2026. Aucun nouveau banc, aucune modification du comportement IA.
Diagnostic reproductible :

```powershell
python -X utf8 sweeps/diag_v309_idle.py --selftest
python -X utf8 sweeps/diag_v309_idle.py
```

La campagne `v299_regen_3x10` avec `probes=10` n'est pas présente dans les
résultats PC accessibles. En remplacement, on a exploité l'archive **valide et
figée** `results/ac04v3_usage_B20x10_holdout_20261012_r1_opcode.json`, issue
d'une campagne **20 paires × 10 ans du 12/10** sous `probe_loop_ops=1`. Le
lecteur ne prend que le bras de référence (20 parties indépendantes), sans
doubler les observations avec les variantes. `LOOP_OPS post=sleep_left`
comptabilise les opcodes disponibles au moment de `Sleep(1)` et abandonnés
par le tick ; les agrégats annuels sont émis l'année suivante.

## Budget laissé au Sleep(1)

| Année close | Parties | Sleep moyen (M opcodes/partie) | Part du budget journalisé | Appels Sleep/partie | Blocs V308 à 430 ops (plafond théorique) | Cartes 256² équivalentes |
|---|---:|---:|---:|---:|---:|---:|
| 1970 | 20 | 3,87 | 5,74 % | 715 | 9 006 | 8,79 |
| 1971 | 20 | 4,24 | 6,32 % | 741 | 9 869 | 9,64 |
| 1972 | 20 | 2,09 | 3,04 % | 339 | 4 856 | 4,74 |
| 1973 | 20 | 0,85 | 1,27 % | 130 | 1 979 | 1,93 |
| 1974 | 20 | 1,25 | 1,85 % | 212 | 2 909 | 2,84 |
| 1975 | 20 | 1,60 | 2,38 % | 280 | 3 713 | 3,63 |
| 1976 | 20 | 1,37 | 1,95 % | 247 | 3 193 | 3,12 |
| 1977 | 20 | 1,24 | 1,90 % | 216 | 2 872 | 2,80 |
| 1978 | 20 | 1,27 | 1,89 % | 228 | 2 952 | 2,88 |

1979 est **censurée par le flush annuel**, donc absente du tableau. Le
reliquat moyen est de **3,40 M opcodes/an en 1970–1972** contre environ
**1,26 M en 1973–1978**. La conversion est volontairement un **plafond** :
`sleep_left / 430` suppose que l'intégralité du reliquat peut être utilisée
sans surcharge de dispatch, mise à jour, ni allocation de temps aux autres
workers ; elle peut compter plusieurs fois les mêmes 1 024 blocs d'une carte
256². Elle n'indique ni les blocs nouveaux effectivement lisibles, ni la
validité du cache, ni les jours pendant lesquels une boucle est inoccupée.

## Les deux autres mesures demandées ne sont pas identifiables

| Mesure demandée | Résultat hors partie | Pourquoi |
|---|---|---|
| Régénérations C76 dont les clés candidates sont toutes inchangées (`cand_*_same_keys_pct`) | **Indisponible** | Les seuls agrégats `LOOP_OPS` archivés n'ont pas ces champs ; les logs `v299_regen_3x10` requis manquent sur ce PC |
| Opcodes de `pub.select` alors que les clés restent identiques | **Indisponible** | Les spans d'opcodes ne sont pas corrélés à une comparaison des mêmes clés au même instant |
| Jours avec caisse inférieure au coût du plus petit projet sélectionné | **Indisponible** | Ni un coût minimal quotidien du portefeuille ni une synchronisation journalière avec la caisse ne figurent dans l'archive |
| Tours réellement inutiles (révisions inchangées, meilleur projet identique, caisse insuffisante) | **Indisponible** | Il faut observer les trois conditions **simultanément à chaque tour** ; `sleep_left` seul ne les démontre pas |

Le script accepte `--logs <répertoire>` si une archive
`reference_seed*_r0.log[.gz]` munie de `C76_REGEN` est récupérée. Il compte
alors seulement les régénérations ayant tous les pourcentages de clés à
100 % et un `best_same_top1=1` documenté ; les données sans ces champs
restent inconnues et ne sont pas assimilées à des régénérations inchangées.

## Décision de suite

Le budget d'opcodes de `Sleep(1)` est suffisant, **sur le plan arithmétique**,
pour cartographier au moins une carte 256² chaque année de l'échantillon ;
les données disponibles ne disent pas quelle part correspond à une attente
financière. En 1970–1972 le déficit de caisse est une hypothèse plausible à
instrumenter ; après 1973, la documentation V309 signale au contraire une
caisse de 14 à 21 M£ et un vivier sec. Un déclencheur limité à « caisse
insuffisante » serait donc particulièrement mal adapté à cette période.

**Ne pas introduire le comportement V309 sur la seule base de cette archive.**
La sonde passive `v309_idle_probe` de l'étape 1 doit mesurer les tours, leur
coût, le meilleur projet, les révisions et la financabilité au même instant
dans les deux boucles (`main.nut` et `_mainLoopProfiled`), après coordination
avec PO-01c. L'exploitation des blocs demande également la validation du
quinconce V308 et un consommateur de la carte. Aucun nouveau défaut ni porte
économique n'est décidé ici.
