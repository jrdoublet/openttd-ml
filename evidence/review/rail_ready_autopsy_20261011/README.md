# P0 RAIL — mesure de frontière et autopsie, 11 octobre 2026

[Autopsie historique](../../../docs/rail_ready_autopsy_20261011.md) ·
[Mesure de sonde](../../../docs/rail_ready_measure_20261011.md) ·
[Journal](../../../docs/journaux/journal_2026-10-11.md)

Ce sous-ensemble versionné conserve **deux expériences distinctes** :

- `autopsy/` : extractions hors ligne du 40×5 historique
  `rail_ready_readmission_diag_40x5_20261010_r1`, bundle
  `250223deaebfb849cde5717888fd2b16942de22798c1385158d4a5ad51757ff8`.
  Verdict brut `fail_primary`, aucune réactivation ou adoption.
- `measurement/` : diagnostic indépendant 5×5 OFF/ON de la sonde
  `rail_ready_measure_5x5_20261011_r1`, bundle
  `ea8391ed6a86ccc282be1d87d83e3870d960f9116661e33f843e93b529b7fcaf`.
  Verdict brut `diagnostic_only` ; neutralité économique ±1 % et opcode
  global non démontrés. La modification de sonde appartient exclusivement
  à sa copie isolée ; son patch archivé n'est pas appliqué à la production.

L'[index local](index.json) reprend le format du paquet général
`opex-review-evidence-v1` : chemins originaux, tailles et SHA256 des octets
bruts et gzip. Compression déterministe avec le helper existant
`sweeps/package_review_evidence.py::gzip_deterministic`. Le grand index
`evidence/review/index.json` n'est ni remplacé ni régénéré ; les autres
preuves et citations ne font pas partie de cette publication.

**Couverture limitée :** 33 artefacts sélectionnés, environ 1 Mo gzip.
Le diagnostic 5×5 inclut JSON final, checkpoints JSONL, manifeste, smoke,
rapports, pré-enregistrement et patch testé. L'autopsie inclut analyse,
tableaux, chronologie, scripts et empreintes ; elle ne recopie pas les
95,97 Mo de JSON historique, les 88,86 Mo de JSONL, les 80 logs moteur ou
les bundles. Leurs chemins et SHA256 sont conservés dans
`autopsy/inputs_before.json.gz`. Les sources historiques citées ont des
[extraits numérotés et hashes de fichiers complets](source_excerpts.json).
Le `missing: []` du sous-index concerne ses seules archives sélectionnées,
pas la disponibilité d'un jeu historique complet sur une nouvelle machine.

Les rapports `.md.gz` préservent les textes originaux byte pour byte,
y compris les liens locaux et les constats de préservation **avant** le
commit documentaire. Les éditions `docs/` rendent les liens portables.
Les scripts archivés sont les extracteurs exécutés ; pour reproduire
l'autopsie, décompresser dans la disposition originale `results/`, disposer
des entrées historiques et choisir un nouveau dossier de sortie. Ils
ne constituent pas un harnais moteur ou un changement de production.

Contrôle du sous-paquet, sans moteur et sans écriture :

```text
python -B -X utf8 evidence/review/rail_ready_autopsy_20261011/verify.py
```

Ce contrôle décompresse chaque archive, vérifie octets/hash, confronte les
originaux s'ils sont disponibles et contrôle les extraits contre le bundle
local s'il est présent. Il ne mesure ni rentabilité, neutralité de sonde,
coût VM global ou constructibilité d'un projet concurrent.
