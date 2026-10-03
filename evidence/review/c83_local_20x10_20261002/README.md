# C83 réparation locale — 20×10 du 02/10/2026

Évaluation explicitement demandée après le diagnostic 5×6, même candidat et
bundle figés, `c83_local_repair=0` contre `=1`. Quarante duels sains, vingt paires
et couverture complète. Δprofit +64 429,2 £/an, 11/9/0, p=0,823803 ; IC95 Student
[−67 828,84 ; +196 687,24], valeur +5,399673 %. Verdict `fail_primary`, défaut OFF.

Estimation descriptive sur 38 travaux par bras : environ 110 670 opcodes/travail
économisés (−18,059 %), différence C83 =0,203 % de la planification AIR témoin.
Le total AIR augmente de 1,91 % entre trajectoires ; pas de gain net/global ou
à entrées identiques qualifié. Cette intervention reste de catégorie comportement.

`summary.json` conserve provenance, santé, couverture, statistiques, résultats par
graine, observations C83 et hashes des quarante logs. `index.json` contient les
tailles et SHA-256 des quatre JSON compressés : campagne, manifeste, estimation
préalable et estimation affinée. Les archives ont été décompressées et vérifiées.
JSONL, bundle et logs bruts restent dans le worktree local ignoré. Le paquet
global historique et la preuve 5×6 ne sont pas remplacés.

Protocole et limites : [bilan](../../../docs/c83_local_repair_20261002.md).
