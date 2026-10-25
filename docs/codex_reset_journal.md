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
