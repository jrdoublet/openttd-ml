# Journal des passes Codex Reset

## 25 octobre 2026 — V262 T10/T15 : contrats du lecteur des orphelins

Branche locale : `codex-reset-20261025_0620`. Arbre initial propre, départ
`269ec7bc`. Commit de la tâche : `4c61ce3a`
(`test(v262): cover orphan report game isolation and missing data`).

**Tâche choisie :** compléter les contrats manquants du lecteur associé à la
mesure ouverte des infrastructures orphelines V262 T10/T15, dans
`docs/taches.md`. L'audit `fair_play`, déjà livré, n'a pas été recommencé.

**Fichiers :**

- `sweeps/test_analyze_v262_orphans.py` : trois tests sur journaux synthétiques.
  Ils vérifient la séparation référence/variante/répétition pour une même graine
  et un même StationID, en texte et gzip ; la priorité des dernières lignes de
  gare et de résumé après rechargement, sans confondre gare et installations ;
  la distinction entre entretien absent (`None`) et zéro observé dans le rapport.
- `docs/taches.md` : avancement des contrats T10/T15, mesure moteur laissée ouverte.
- `docs/codex_reset_journal.md` : création de ce journal dans un second commit.

Aucun code IA, lecteur d'analyse, défaut ou hash de contrat modifié.

**Tests exécutés :**

| Commande | Résultat |
|---|---|
| `python3 -m unittest discover -s sweeps -p 'test_v262_orphans.py'` avant édition | 6 tests OK |
| `python3 -m unittest discover -s sweeps -p 'test_*v262_orphans.py' -v` | 9 tests OK |
| `python3 -m unittest discover -s sweeps -p 'test_*.py'` avant édition | 2 427 tests OK, 9 ignorés, 2 échecs attendus |
| `python3 -m unittest discover -s sweeps -p 'test_*.py'` après édition | 2 430 tests OK, 9 ignorés, 2 échecs attendus |
| `git diff --check` et `git diff --cached --check` | OK |

Commandes lancées via `rtk proxy`. Journaux temporaires de la suite complète :
`/tmp/codex_reset_20261025_0620_before.log` et
`/tmp/codex_reset_20261025_0620_after.log`.

**Reste à valider en banc :** aucune partie nécessaire pour cet ajout de tests.
Le chantier T10/T15 conserve son besoin d'exposition réelle de la sonde sous
`decision_log=1`, avec capture des journaux, contrôle de santé et couverture
annuelle complète avant de mesurer les orphelins. L'entretien publié concerne
toute l'infrastructure de la compagnie : aucune part « orpheline » ni conclusion
économique ne découle de ces fixtures. Aucun Docker ni partie lancé dans cette
passe ; aucun push, merge ou changement de configuration Git.

## 25 octobre 2026 — V309 : contrats du lecteur des tours d'attente

Branche locale : `codex-reset-20261025_0620`. Arbre initial propre, départ
`ad6ebfe4`. Commit de la tâche : `b0ec1a3d`
(`test(v309): cover idle log isolation and incomplete observations`).

**Tâche choisie :** compléter les contrats manquants du lecteur de journaux
du chantier ouvert V309 dans `docs/taches.md`, sans rouvrir son étape de mesure
close le 21/10 ni introduire de cartographie comportementale.

**Fichiers :**

- `sweeps/test_diag_v309_idle.py` : trois tests sur journaux synthétiques.
  Ils vérifient le comptage unique de chaque mois par graine, répétition, bras
  et année malgré les copies texte/gzip, ainsi que la pondération du taux par
  les tours ; le rejet des champs obligatoires absents, illisibles ou incohérents
  sans masquer une observation valide ultérieure du même mois ; la conservation
  de `None` en cas de couverture optionnelle partielle, distincte des zéros
  observés, sans extrapoler les mois manquants ni annuler une attente connue nulle.
- `docs/taches.md` : avancement des contrats V309, préalables métier laissés ouverts.
- `docs/codex_reset_journal.md` : ajout de cette entrée après le commit de la tâche.

Aucun code IA, lecteur d'analyse, défaut ou hash de contrat modifié.
RAIL-LONG-EARLY-1, AIR-FLOTTE-1 et C115 non modifiés.

**Tests exécutés :**

| Commande | Résultat |
|---|---|
| `python3 -m unittest discover -s sweeps -p 'test_v309_idle.py' -v` avant édition | 8 tests OK |
| `python3 -m unittest discover -s sweeps -p 'test_*v309_idle.py' -v` | 11 tests OK |
| `python3 -m unittest discover -s sweeps -p 'test_*.py'` avant édition | 2 430 tests, OK avec 9 ignorés et 2 échecs attendus |
| `python3 -m unittest discover -s sweeps -p 'test_*.py'` après édition | 2 433 tests, OK avec les mêmes 9 ignorés et 2 échecs attendus |
| `git diff --check` et `git diff --cached --check` | OK |

Commandes lancées via `rtk` / `rtk proxy`. Journaux temporaires de la suite :
`/tmp/codex_reset_v309_20261025_before.log` et
`/tmp/codex_reset_v309_20261025_after.log`.

**Reste à valider en banc :** aucune partie nécessaire pour cet ajout de contrats.
V309 conserve ses préalables avant toute version comportementale : comparaison
de financement avec la réserve effective, qualification du coût réel short6
(le plafond historique à 430 opcodes/bloc sous-estime le coût), consommateur de
carte et exposition adaptée. Ces fixtures ne démontrent ni des tours entièrement
récupérables ni la neutralité économique de la sonde. Aucun Docker ni partie
lancé ; aucun push, merge, changement de configuration Git ou accès à un autre
worktree ou au dépôt principal.

## 25 octobre 2026 — V308 : rejet des compteurs de sondage impossibles

Branche locale : `codex-reset-20261025_0620`. Arbre initial propre, départ
`b6962e68`. Commit de la tâche : `236bbfa8`
(`fix(v308): reject impossible cartography probe counts`).

**Tâche choisie :** fiabiliser le lecteur de diagnostic du chantier ouvert V308
dans `docs/taches.md`. Défaut reproduit sur fixtures avant correction : une ligne
annonçant sept tuiles fluviales pour six points lus, un compteur négatif ou un
relief négatif était acceptée et pouvait contribuer aux taux et aux coûts.
La mesure des motifs achevée le 21/10 n'a pas été recommencée.

**Fichiers :**

- `sweeps/diag_v308_carto.py` : validation des compteurs de chaque motif entre
  zéro et son nombre réel de points (4, 5 ou 6), et rejet des reliefs négatifs
  pour la vérité exhaustive comme pour les motifs.
- `sweeps/test_diag_v308_carto.py` : quatre tests de régression. Ils couvrent
  les compteurs hors bornes dans chaque motif, les reliefs négatifs, l'exclusion
  des lignes invalides avant agrégation en texte et gzip, ainsi que la conservation
  des zéros, des bornes valides et de deux tirages du même bloc avec des indices
  distincts (échantillonnage avec remise).
- `docs/taches.md` : suivi du correctif, consommateur de carte et invalidation
  laissés ouverts.
- `docs/codex_reset_journal.md` : ajout de cette entrée après le commit de la tâche.

Aucun code IA, défaut ou hash de contrat modifié. RAIL-LONG-EARLY-1,
AIR-FLOTTE-1 et C115 non modifiés.

**Tests exécutés :**

| Commande | Résultat |
|---|---|
| `python3 -m unittest discover -s sweeps -p 'test_diag_v308_carto.py' -v` avant correction du lecteur | Défaut reproduit : 4 tests, 78 échecs de sous-tests/assertions |
| `python3 -m unittest discover -s sweeps -p 'test_*v308*.py' -v` après correction | 22 tests, OK avec 1 ignoré |
| `python3 -m unittest discover -s sweeps -p 'test_*.py'` avant édition | 2 433 tests, OK avec 9 ignorés et 2 échecs attendus |
| `python3 -m unittest discover -s sweeps -p 'test_*.py'` après édition | 2 437 tests, OK avec les mêmes 9 ignorés et 2 échecs attendus |
| `git diff --check` et `git diff --cached --check` | OK |

Commandes lancées via `rtk` / `rtk proxy`. Journaux temporaires de la suite :
`/tmp/codex_reset_v308_20261025_before.log`,
`/tmp/codex_reset_v308_20261025_red.log` et
`/tmp/codex_reset_v308_20261025_after.log`.

**Reste à valider en banc :** aucune partie nécessaire pour ce filtre Python ;
ni intégration moteur ni schéma collecté ne changent. Le test de non-régression
sur le smoke historique est ignoré, car son journal moteur n'est pas présent
sur cet hôte. Les fixtures ne requalifient donc pas les mesures historiques.
V308 conserve son attente d'un consommateur de carte et d'une invalidation avant
toute utilisation dans les décisions ; aucun gain économique n'est démontré ici.
Aucun Docker ni partie lancé ; aucun push, merge, changement de configuration
Git ou accès à un autre worktree ou au dépôt principal.

## 25 octobre 2026 — V306 : évaluer aussi les graines nouvelles

Branche locale : `codex-reset-20261025_0620`. Arbre initial propre, départ
`20328514`. Commit de la tâche : `9c14a016`
(`fix(v306): evaluate calibration on unseen test seeds`).

**Tâche choisie :** fiabiliser la validation croisée hors ligne du chantier ouvert
V306 dans `docs/taches.md`, en préparation de son évaluation sur graines nouvelles.
Défaut reproduit avant correction : les plis étant définis sur les graines
d'apprentissage, les graines présentes seulement en test étaient omises. Les
fixtures observaient 0 ligne-année évaluée sur 6 pour deux jeux disjoints, et
3 sur 6 pour un chevauchement partiel.

**Fichiers :**

- `sweeps/analyse_calibration_projets.py` : plis définis sur les graines de test,
  chacune évaluée une fois ; exclusion des mêmes graines de l'apprentissage,
  tous bras et répétitions confondus. Les graines propres à l'apprentissage
  restent utilisables dans les deux plis. À jeux de graines identiques, découpage
  historique conservé. Contrat documenté dans le module et la fonction.
- `sweeps/test_analyse_calibration_projets.py` : trois contrats sur données
  synthétiques, sans dépendance optionnelle : couverture de toutes les graines
  nouvelles jusque dans le rapport `analyse`, chevauchement partiel et absence
  de fuite entre bras/répétitions d'une même graine. Les facteurs par mode et
  par cellule sont vérifiés, avec suffisamment de lignes d'apprentissage.
- `docs/taches.md` : avancement V306, validation réelle et ablation laissées ouvertes.
- `docs/codex_reset_journal.md` : cette entrée dans un second commit.

Aucun code IA, défaut, hash de contrat ou rapport historique modifié.
RAIL-LONG-EARLY-1, AIR-FLOTTE-1 et C115 non modifiés.

**Tests exécutés :**

| Commande | Résultat |
|---|---|
| `python3 -m unittest discover -s sweeps -p 'test_analyse_calibration_projets.py' -v` avant correction | 3 tests, 2 échecs reproduisant les observations omises |
| Même commande après correction | 3 tests OK |
| `python3 sweeps/analyse_calibration_projets.py --selftest` | OK |
| `python3 -m unittest discover -s sweeps -p 'test_*.py'` avant édition | 2 437 tests, OK avec 9 ignorés et 2 échecs attendus |
| Même suite complète après correction | 2 440 tests, OK avec les mêmes 9 ignorés et 2 échecs attendus |
| `git diff --check` et `git diff --cached --check` | OK |

Commandes lancées via `rtk` / `rtk proxy`. Journaux temporaires :
`/tmp/codex_reset_v306_20261025_before.log`,
`/tmp/codex_reset_v306_20261025_red.log` et
`/tmp/codex_reset_v306_20261025_after.log`.

**Reste à valider en banc :** aucune partie nécessaire pour ce correctif de
découpage Python ; ni intégration moteur ni schéma collecté ne changent. V306
reste ouverte : ablation par variables disponibles au choix et évaluation sur
de vraies graines nouvelles avant toute proposition de table. Les fixtures
ne valident aucun gain économique ; aucune table adoptée et aucune preuve
historique recalculée ou requalifiée. Aucun Docker ni partie lancé ; aucun
push, merge, changement de configuration Git ou accès à un autre worktree
ou au dépôt principal.

## 25 octobre 2026 — V262 T10/T15 : entretien partiel conservé inconnu

Branche locale : `codex-reset-20261025_0620`. Arbre initial propre, départ
`fdb22dd2`. Commit de la tâche : `68edcdd3`
(`fix(v262): preserve unknown totals for incomplete orphan costs`).

**Tâche choisie :** fiabiliser le lecteur du chantier ouvert de mesure des
infrastructures orphelines V262 T10/T15, dans `docs/taches.md`. Défauts
reproduits sur journaux synthétiques avant correction : un résumé auquel
manque un coût provoquait un `KeyError` ; des valeurs comme `11.5`, `11oops`
ou `1e3` étaient réduites à leur préfixe entier et entraient dans le total.
La mesure T04 des sauvegardes, déjà réalisée, n'a pas été recommencée.

**Fichiers :**

- `sweeps/analyze_v262_orphans.py` : lecture des champs entiers complets,
  délimités par des espaces ; entretien `None` si le résumé ou un de ses
  six coûts manque, sans addition partielle. Le comptage des orphelins reste
  disponible et un coût observé à zéro reste zéro.
- `sweeps/test_analyze_v262_orphans.py` : trois régressions couvrant chaque
  catégorie de coût absente ou illisible, les journaux texte/gzip, le
  remplacement d'un ancien total par un relevé partiel après rechargement,
  puis la restauration d'un total complet, y compris nul.
- `docs/taches.md` : avancement du lecteur, mesure moteur laissée ouverte.
- `docs/codex_reset_journal.md` : cette entrée dans un second commit.

Aucun code IA, défaut, schéma de sonde ou hash de contrat modifié.
RAIL-LONG-EARLY-1, AIR-FLOTTE-1 et C115 non modifiés.

**Tests exécutés :**

| Commande | Résultat |
|---|---|
| `python3 -m unittest discover -s sweeps -p 'test_analyze_v262_orphans.py' -v` avant correction du lecteur | 6 tests, défauts reproduits : 18 échecs et 20 erreurs de sous-tests |
| `python3 -m unittest discover -s sweeps -p 'test_*v262_orphans.py' -v` après correction | 12 tests OK |
| `python3 -m unittest discover -s sweeps -p 'test_*.py'` avant édition | 2 440 tests, OK avec 9 ignorés et 2 échecs attendus |
| Même suite complète après correction | 2 443 tests, OK avec les mêmes 9 ignorés et 2 échecs attendus |
| `git diff --check` et `git diff --cached --check` | OK |

Commandes lancées via `rtk` / `rtk proxy`. Journaux temporaires :
`/tmp/codex_reset_v262_costs_20261025_before.log`,
`/tmp/codex_reset_v262_costs_20261025_red.log` et
`/tmp/codex_reset_v262_costs_20261025_after.log`.

**Reste à valider en banc :** aucune partie nécessaire pour ce correctif de
lecture Python ; ni intégration moteur ni schéma collecté ne changent.
T10/T15 conserve son besoin d'exposition réelle sous `decision_log=1`,
avec capture des journaux, contrôle de santé et couverture annuelle complète.
L'entretien concerne toute l'infrastructure de la compagnie ; aucune part
« orpheline », aucun gain économique et aucune requalification de résultats
historiques ne découlent des fixtures. Aucun Docker ni partie lancé ; aucun
push, merge, changement de configuration Git ou accès à un autre worktree
ou au dépôt principal.
