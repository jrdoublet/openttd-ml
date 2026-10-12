# Sauvegarde expérimentale AC-04/05/06 (11/10/2026)

Ce dossier **n'est pas un patch adopté** et ne doit jamais être appliqué à
`master` sans requalification. Il préserve la préparation isolée :

- `experimental_worktree.patch` : diff Git binaire du worktree sur
  `436e1b5`, y compris ajustement du contrat statique
  `test_air0310_2_hub_snapshot.py` ;
- `test_ac_catalogue_fixes.py` : nouveau test non suivi par Git dans le
  worktree (copie complète, hors patch `git diff`) ;
- `manifest.json` : tailles et empreintes SHA256 de toutes les preuves.

Worktree encore actif :
`results/ac_fixes_worktree_20261011/`,
branche `air-catalogue-fixes-staging`. Quatre toggles expérimentaux tous
à 0 : `ac04_hub_route_fix`, `ac04_extra_site_dedup`,
`ac05_skip_unused_hub_income`, `ac06_c76_snapshot_ack`.

Qualification et séquencement :
[plan par étapes](../../../docs/air_catalogue_correctifs_etapes_20261011.md).
Le banc C121 concurrent a terminé pendant la préparation. Une commande
de smoke Docker 1×1 a ensuite été bloquée **avant lancement** par
l'environnement ; aucun smoke, campagne A/B ou mise en production
n'a été effectué pour ces corrections.
