# Archivage du nettoyage local P0 — 11 octobre 2026

Cet archivage précède la restitution des fichiers de production au HEAD de
`master` (`1033239` au moment de l'inventaire). Il permet de retrouver les
expériences locales **non adoptées** sans réactiver leurs flags. Le HEAD
contient déjà la réalisation directe AIR, le paiement physique C121 et la
mémoire des échecs d'upgrade RAIL adoptés précédemment.

## Sources préservées

| Archive | Contenu | SHA256 |
|---|---|---|
| `uncommitted_patch.zip` | Diff Git complet des **37 fichiers suivis** de l'inventaire sous l'entrée `uncommitted.patch`, dont les 27 sources `ai/OpexAI/*.nut`, les tests et les modifications documentaires | ZIP : `c7fd561b159ebbae3653e99f655d7269a190fd6e19fabafdb12d56cbd538975e` |
| `untracked_scripts.zip` | **52 fichiers** `sweeps/` et `tests/` non suivis, chemins relatifs et noms d'origine préservés, dont analyseurs, tests de prototypes refusés et microbench du classement RAIL | `dba0125c157da00cd39c8a08c6a338370d1ff1ecf3d702a65f0082dcb3ba9bba` |

Les huit rapports/pré-enregistrements `docs/` non suivis et les paquets de
preuve `evidence/review/rail_ready_guard_{vm,exposure}_20261011/` sont
versionnés **séparément** comme documents et preuves consultables.
Les anciens chemins de scripts cités dans les rapports désignent maintenant
les entrées de `untracked_scripts.zip` ; les extraire dans une copie isolée
si une reproduction historique est nécessaire. Ne pas les réinstaller dans
`sweeps/` au cours de la validation du code courant : certains tests
attendent précisément des flags expérimentaux retirés.

L'empreinte SHA256 de l'entrée originale `uncommitted.patch` est
`2210b4377933327496e3e97cfc825e67d56c6e2237d313bae57bcc4ad26a95a4`.
Cette entrée conserve exactement les espaces et octets du diff initial ;
le conteneur ZIP empêche les vérifications de style sur le code archivé
de masquer les défauts éventuels du code courant.

L'archive contient des preuves de travaux et des prototypes, **aucune
qualification économique nouvelle**. Elle ne doit pas être réappliquée au
HEAD comme correctif : les deux scores RAIL `simple_roi` et `simple_opcode`
sont rejetés définitivement, de même que l'adoption des variantes P0
RAIL N=2/réadmission, AIR learner/production exacte et V139. V126 reste
expérimental sans preuve économique d'adoption.

Le protocole, les métriques et les verdicts d'origine demeurent dans
`docs/taches.md`, les journaux et les rapports thématiques. Aucun nouveau
Docker/A-B n'a été nécessaire au nettoyage : la production a été restaurée
à un état déjà livré, sans introduire de nouveau comportement.
