# Revue de code — Correctif ciblé de `road1y_mail_p2p` et ajout de `road1y_mail_p2p_missing`

**Date :** 9 novembre 2026  
**Branche :** `road1y-night`  
**Base :** `63b6c2aa`  
**Auteur :** Antigravity  

---

## 1. Contexte et objectif du correctif

L'analyse de la campagne porte A 40×3 (`$T/agy_mail_journaux.md`) a révélé que le levier `road1y_mail_p2p=10` a ouvert exactement **0 ligne sur 40 parties**.
La cause principale identifiée dans `OpexRoad1yMailP2PStep` (`ai/OpexAI/bus_districts.nut:1037-1095`) était :
- L'incrémentation inconditionnelle de `attempts` avant même de trouver des sites de station ou de tester un chemin.
- Le plafond `attempts > 4` qui coupait la fonction dès les 4 premières paires.
- L'absence de mémoire d'exploration d'un mois sur l'autre (les boucles `i` et `j` repartaient systématiquement de 0).
- L'absence totale de traces télémétriques sur les rejets (`DECISION_LOG` muet sur les causes).

Ce correctif résout ces défauts sans modifier les gardes économiques (1970, 37 k£, missing <= 14) et introduit le paramètre `road1y_mail_p2p_missing` (défaut 0 = 14) pour autoriser des essais ultérieurs d'assouplissement de voirie.

---

## 2. Analyse détaillée des modifications

### 2.1. Curseur tournant interurbain (`ROAD1Y_MAIL_P2P_CURSOR`)
- **Déclaration :** `globals_pre.nut:138` (`ROAD1Y_MAIL_P2P_CURSOR <- 0;`).
- **Mécanique :**
  - Au début de `OpexRoad1yMailP2PStep`, si `nTowns > 0`, l'indice de départ est calculé : `local startI = (ROAD1Y_MAIL_P2P_CURSOR >= 0) ? (ROAD1Y_MAIL_P2P_CURSOR % nTowns) : 0;`.
  - Le curseur avance immédiatement pour l'appel suivant : `ROAD1Y_MAIL_P2P_CURSOR = (startI + 1) % nTowns;`.
  - La boucle externe parcourt les villes en rotation : `local i = (startI + stepI) % nTowns;` pour `stepI` allant de 0 à `nTowns - 1`.
  - La boucle interne `j` teste tous les partenaires potentiels (`j = 0` à `nTowns - 1` avec `i != j`).
  - Une table locale `testedPairs` garantit qu'aucune paire $\{ta, tb\}$ n'est évaluée plus d'une fois au cours du même mois.
- **Règles Squirrel :** Aucune closure imbriquée, aucune variable locale capturée.

### 2.2. Comptage ciblé des tentatives (`attempts`)
- Les rejets rapides (population $< 350$, paire active existante, paire déjà testée ce mois, distance hors $[24, 128]$) ne consomment aucun opcode lourd et ne sont **pas** comptabilisés dans `attempts`.
- La recherche des sites de station `siteA` et `siteB` ne compte **pas** dans `attempts` (les paires sans site constructible ne coûtent pas de pathfinding).
- `attempts++` n'intervient qu'une fois les deux sites trouvés, immédiatement avant le pathfinding (`OpexRoadBfsPath` et `OpexRoadTrace`).
- Plafond fixé à 6 pathfindings par mois (`if (attempts > 6) return;`).

### 2.3. Traçabilité des rejets sous `DECISION_LOG`
Toutes les causes de rejet sont désormais émises via `OpexRoad1yMailP2PLog` (`OpexDecide("ROAD1Y_MAIL_P2P", ...)` sous `DECISION_LOG`) :
1. **Trésorerie globale insuffisante au démarrage du mois :** `action=reject reason=CASH bank=... need=...`
2. **Trésorerie insuffisante à la construction (véhicules + infrastructure) :** `action=fail pair=ta:tb reason=CASH money=...`
3. **Sites de station introuvables :** `action=reject pair=ta:tb reason=SITE_A` ou `reason=SITE_B`
4. **Voirie manquante dépassant le seuil :** `action=reject pair=ta:tb reason=MISSING missing=N max=M`
5. **Absence totale de chemin constructible :** `action=reject pair=ta:tb reason=NO_TRACE`
6. **Dépôt routier introuvable :** `action=reject pair=ta:tb reason=DEPOT`

### 2.4. Nouveau réglage `road1y_mail_p2p_missing`
- **Déclaration :** `info.nut` avec plage `min_value = 0, max_value = 60`, `easy/medium/hard/custom_value = 0`, `flags = 0`.
- **Globale :** `globals_pre.nut` (`ROAD1Y_MAIL_P2P_MISSING <- 0;`).
- **Chargement :** `settings.nut` dans `OpexLoadSettings()` avec borne `[0, 60]` et neutralisation hors route seule (`if (!road1yRoadOnly) ROAD1Y_MAIL_P2P_MISSING = 0;`).
- **Comportement :** `local maxMissing = (ROAD1Y_MAIL_P2P_MISSING > 0) ? ROAD1Y_MAIL_P2P_MISSING : 14;`. Au défaut 0, la limite est strictement de 14 tuiles, garantissant l'identité stricte avec le comportement d'origine.

---

## 3. Revue de conformité et règles de sécurité

| Critère | Statut | Justification |
|:---|:---:|:---|
| **Comportement par défaut inchangé à 0** | **CONFORME** | À `road1y_mail_p2p=0`, retour immédiat à la ligne 1023. À `road1y_mail_p2p_missing=0`, `maxMissing` est fixé à 14 tuiles. |
| **Plafond AddSetting** | **CONFORME** | Nombre de `AddSetting` passe de 72 à 73, respectant le plafond de 75 de `sweeps/test_v251_inventory.py`. |
| **Mots réservés Squirrel** | **CONFORME** | Aucun identifiant réservé (`clone`, `base`, `parent`, `static`, `delegate`, `resume`, `yield`, `constructor`, `instanceof`). |
| **Fonctions anonymes / closures** | **CONFORME** | Aucune fonction imbriquée ou lambda capturant une variable locale englobante. |
| **Appels `Valuate`** | **CONFORME** | Aucun appel `Valuate` ajouté. |
| **Impact Save/Load** | **CONFORME** | `ROAD1Y_MAIL_P2P_CURSOR` est un état transitoire de rotation mensuelle qui ne nécessite aucune persistance disque (repart proprement de 0 à chaque initialisation). |
| **Projections ROAD100 / SHA figés** | **CONFORME** | `sweeps/road100_off_projection.py`, `sweeps/rail_open_legacy.py`, et `sweeps/rail_sibling_legacy.py` mis à jour avec les SHA256 exacts des fichiers modifiés et de leurs stages intermédiaires. |

---

## 4. Résultats des tests hôte

Tous les tests de contrat et de régression sont au vert complet :
- `test_road1y*.py` : **97 tests réussis** (0 échec, 0 erreur).
- `test_road100*.py` : **236 tests réussis** (0 échec, 0 erreur, 3 ignorés).
- `test_v251*.py` : **7 tests réussis** (0 échec, 0 erreur).
- `test_road1y_mail_p2p.py` : **9 tests dédiés réussis** (0 échec, 0 erreur).
- `git diff --check` : **0 avertissement, arbre parfaitement propre**.

---

## 5. Risques résiduels

Le correctif déverrouille l'exploration de toutes les villes de la carte et compte équitablement les pathfindings sans gaspiller le budget sur des paires infaisables. Cependant, comme les gardes de caisse (37 k£), temporelle (1970) et de voirie (14 tuiles) n'ont pas été modifiées dans ce commit (conformément à la consigne « une variable à la fois »), l'ouverture effective de lignes lors de la porte A dépendra de l'existence sur la graine de paires de villes dont le réseau routier municipal préexistant offre une continuité naturelle ($\le 14$ tuiles de raccordement). Le paramètre `road1y_mail_p2p_missing` permettra d'évaluer directement l'assouplissement nécessaire lors des campagnes suivantes.
