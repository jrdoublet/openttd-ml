# AIR-LOAD resélection : preuve dérivée, 24 octobre 2026

Voir [le rapport](../../../docs/air_load_reselect_20261024.md) pour la décision,
les unités, la censure et les limites.

- `diagnostic.json` : agrégats et témoins recalculés sur les dix journaux
  existants ; provenance du résultat, du manifeste, du bundle complet et des
  logs. Ce fichier n'est pas une nouvelle campagne.
- `validation.json` : suite complète avant/après, intitulés des échecs et
  erreurs préexistants, SHA-256 des deux logs locaux et environnement.

Le paquet historique `evidence/review/index.json` reste inchangé : aucune
archive de campagne n'est réécrite. Les originaux volumineux restent en lecture
seule dans le worktree `wt_airload`, au chemin enregistré dans le diagnostic.
