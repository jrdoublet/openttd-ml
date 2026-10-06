# Récupération Git — 01/10/2026

Publication demandée explicitement par l'utilisateur après installation de Git.
Le dossier de travail OneDrive ne contient pas de métadonnées `.git` ; le dépôt
`https://github.com/jrdoublet/openttd-ml.git` a été retrouvé dans la documentation
et l'historique de clonage, puis vérifié en lecture seule.

## Base et périmètre

- Clone neuf hors OneDrive : `C:/Users/BH6001/source/repos/openttd-ml-recovered`.
- Base : `origin/c121-catalog`, commit
  `79497c7498994d25c9f746c826cf2ad36f4e533c` ; trois commits au-dessus de master.
  C'est la base de récupération choisie, pas une preuve de la branche locale
  originelle dont les métadonnées sont absentes.
- 250 fichiers source, tests, workflows et documents transférés ; identité
  binaire vérifiée au transfert. Aucun fichier suivi manquant dans la source.
  Les refactorings et correctifs locaux des 30/09–01/10 sont publiés ensemble,
  pas présentés comme le seul lot cache C121.
- Aucun transfert des résultats locaux, certificats CA, caches, sauvegardes,
  IA adverses non versionnées ou fichier `.bak`. Les preuves déjà versionnées
  du clone restent intactes ; les résultats récents cités dans les documents
  restent dans le dossier OneDrive et ne sont pas inclus dans ce commit.
- Deux imports de tests corrigés dans le clone pour fonctionner avec
  `unittest discover -s sweeps`. Le dossier OneDrive reste inchangé.

## Vérifications avant commit

- Recherche des formats usuels de clés privées et jetons dans les fichiers
  transférés : aucun motif détecté (ce contrôle n'est pas un audit exhaustif).
- Réglages protégés examinés : C115 demeure activé, C121 et les nouvelles
  expériences restent désarmés par défaut.
- `unittest discover -s sweeps -p test_*.py` : **1152 tests réussis**.
- `unittest discover -s tests -p test_*.py` : **3 réussites, 1 skip**.
  Les messages d'adoption/smoke affichés par les fixtures sont des scénarios
  synthétiques : aucune partie ou qualification économique nouvelle.
- `git diff --cached --check` signale des blancs en fin de fichier dans
  `orchestrator.nut` et le journal du 30/09, ainsi que les fins de ligne de
  l'archive C117 corrompue, explicitement conservée comme non autoritaire.
  Ces avertissements préexistants au transfert ne sont pas corrigés au prix
  d'une modification de l'archive historique.
- Sur `c121-catalog`, les workflows automatiques examinés sont des contrats
  sans moteur ; les bancs restent à déclenchement manuel. Aucun succès Actions
  n'est revendiqué au moment de la préparation de ce commit.

Cette publication conserve les limites des diagnostics, notamment les témoins
contaminés du lot post-chantier : voir `c121_investments_20261001.md`.
Le commit de récupération ne constitue aucune adoption économique. Le push
est prévu sans force sur `origin/c121-catalog`, sans modification de master.