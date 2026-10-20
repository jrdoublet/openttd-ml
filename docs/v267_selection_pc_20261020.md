# V267 — sélection de 40 graines sur le PC (19–20 octobre 2026)

**Résultat :** la commande `select` a abouti et a produit **40 graines uniques**, avec **aucun quota de couverture non satisfait**. Le grand banc n'est **pas intégralement sain** : **298 parties sur 300** ont atteint le relevé de décembre 1979. Les graines **711843** (dernier relevé avril 1978) et **816634** (juin 1978) sont tronquées ; le fichier global `v267_main_x10_pc_20261019.json` est absent. Le mécanisme automatique avait refusé `select` pour cette raison ; la sélection a ensuite été exécutée manuellement sur les 298 graines à horizons complets, avec code de sortie 0. Ne pas présenter ces 300 parties comme une qualification exhaustive.

## Périmètre et provenance

- Suite effectivement exécutée : `bash sweeps/run_v267_pc.sh smoke`, `pop`, `main`, puis `select` (reprise après échec de génération du JSON principal). Le criblage préalable de **3 000 cartes** était fourni dans `sweeps/v267_data/v267_maps_3000.jsonl.gz` ; l'étape `maps` n'a pas été rejouée.
- `pop` : 300 graines uniques parmi 3 000 (graine 73 exclue). `main` : OpexAI par défaut contre AAAHogEx, carte commune, un bras et une répétition, de 1970 à 1979, carte 256 × 256, Docker local 10 CPU, 8 Go, 10 workers. Pas de bras `CONTROL`.
- Code figé Git `7d30f145f9f5a6ce49279aae95fc5760f9af0575` (arbre propre), bundle SHA-256 `f52d3f29166f71fab0325081fa327ef32453a24f01334029b2611f600b101474`, image Docker `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
- Source brute conservée **localement** : `results/v267_main_x10_pc_20261019.jsonl` (599 596 569 octets, 71 924 enregistrements), SHA-256 `0d5845a4241290f6f4e3578c97b2834cb301b9698eb6a58cbddacf7d8fadd99d`. Trop volumineuse pour Git ; `v267_checkpoints_compact_20261020.json` archive les seuls relevés utiles (années 3/6/10) avec les métriques nécessaires et l'empreinte de la source. Manifeste et listes de graines sont archivés à côté.

## Population et sélection à dix ans

| Relevé moyen | Population (298) | Sélection (40) |
|---|---:|---:|
| Profit annuel OpexAI | 3 984 423 £ | 3 928 241 £ |
| Profit annuel AAAHogEx | 7 957 754 £ | 7 932 378 £ |
| Profit Opex / AAA (ratio des moyennes) | 50.07 % | 49.52 % |
| Valeur Opex / AAA (ratio des moyennes) | 70.21 % | 68.89 % |
| Graines où Opex gagne en profit | 0/298 | 0/40 |

La sélection finale couvre **46 variables** de carte et de résultat (relief, mers et rivières, villes, industries, profit aux années 3/6/10, parts des modes, gares, etc.). **11 graines** remplissent prioritairement les quotas des deux déciles extrêmes ; **29 autres** sont choisies par MMD glouton. Aucun quota ne reste non satisfait. La liste de 40 graines est dans `evidence/review/v267_pc_20261020/v267_selection_20261019.txt` ; le JSON donne les colonnes et la couverture.

**Limites de conclusion.** La représentativité est évaluée sur les mêmes jeux que ceux qui ont servi à choisir les graines (mesure *in-sample*). Une seule des 39 graines historiques est présente dans les 298 jeux évalués : il n'est donc pas possible de comparer sérieusement ici la nouvelle liste à l'ancienne. Le bras de contrôle V252 était désactivé ; l'aptitude à détecter un effet connu n'a pas été mesurée. Le bruit A/A n'a pas été mesuré faute de répétitions. Le fichier récapitulatif de santé du lanceur n'ayant pas été produit, les 298 horizons sont vérifiés dans le JSONL, sans pouvoir attester tous les contrôles de santé du harnais.

**Statut :** première liste opérationnelle de 40 graines, à valider sur une campagne indépendante et avec un contrôle avant d'en faire le remplacement autoritaire de `SEEDS_40`. Aucun défaut d'OpexAI et aucune graine canonique du harnais ne changent dans cette livraison.
