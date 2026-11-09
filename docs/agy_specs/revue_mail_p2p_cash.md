# Revue de code — Réglages `road1y_mail_p2p_cash` et `road1y_mail_p2p_start`

**Date :** 9 novembre 2026  
**Branche :** `road1y-night`  
**Base :** `5ff4f241`  
**Auteur :** Antigravity  

---

## 1. Contexte et motivation

L'analyse de la campagne porte A 40×3 sous `road1y_mail_p2p=10` avec assouplissement de voirie `road1y_mail_p2p_missing=14/30/45` a donné des résultats strictement identiques (+6,9 / +7,0 / +7,0 k£) avec seulement 4 lignes ouvertes sur 40 parties, toutes concentrées en 1972.
Ce constat confirme que la voirie manquante n'est pas le facteur bloquant l'émergence des lignes de courrier autonomes. Deux gardes statiques codées en dur dans `OpexRoad1yMailP2PStep` (`ai/OpexAI/bus_districts.nut:1020-1050`) restreignaient l'activité :
1. **Garde temporelle stricte :** `if (year <= 1970) return;` interdisait toute ouverture durant toute l'année 1970, retardant l'exploitation du vivier au plus tôt à 1971.
2. **Garde de trésorerie de démarrage :** `cashReserve 25000 + 12000` = 37 000 £ au lancement, puis `money < cashReserve + 4000 + 2*prix` lors de la construction.

Cette intervention paramètre ces deux gardes derrière des réglages déclarés sous `info.nut`, tous deux à **défaut 0** (neutralité absolue, chemin historique inchangé).

---

## 2. Conception et analyse des modifications

### 2.1. Réglage `road1y_mail_p2p_cash`
- **Déclaration :** `info.nut` avec plage `0..60`, 4 valeurs à 0 (`easy`, `medium`, `hard`, `custom`), `flags = 0`.
- **Globale :** `globals_pre.nut` (`ROAD1Y_MAIL_P2P_CASH <- 0;`).
- **Chargement :** `settings.nut` dans `OpexLoadSettings()` avec borne `[0, 60]` et forçage à 0 hors route seule (`if (!road1yRoadOnly) ROAD1Y_MAIL_P2P_CASH = 0;`).
- **Mécanique économique :**
  - Si `ROAD1Y_MAIL_P2P_CASH == 0` : le seuil de démarrage reste strictement 37 000 £ (`need=37000`) et la réserve transmise à `OpexRoad1yBuildMailP2P` est de 25 000 £.
  - Si `ROAD1Y_MAIL_P2P_CASH > 0` : le seuil de démarrage devient `threshold = ROAD1Y_MAIL_P2P_CASH * 1000`. La réserve transmise devient `min(25000, max(0, threshold - 12000))`, garantissant que la condition de construction `money < cashReserve + 4000 + 2 * prix` reste cohérente avec le seuil initial sans avortement systématique.

### 2.2. Réglage `road1y_mail_p2p_start`
- **Déclaration :** `info.nut` avec plage `0..12`, 4 valeurs à 0 (`easy`, `medium`, `hard`, `custom`), `flags = 0`.
- **Globale :** `globals_pre.nut` (`ROAD1Y_MAIL_P2P_START <- 0;`).
- **Chargement :** `settings.nut` dans `OpexLoadSettings()` avec borne `[0, 12]` et forçage à 0 hors route seule (`if (!road1yRoadOnly) ROAD1Y_MAIL_P2P_START = 0;`).
- **Mécanique calendaire :**
  - Si `ROAD1Y_MAIL_P2P_START == 0` : interdiction absolue en 1970 (`year <= 1970`), exactement identique à l'ancien comportement.
  - Si `ROAD1Y_MAIL_P2P_START > 0` : en 1970, les ouvertures sont autorisées dès que le mois courant atteint `ROAD1Y_MAIL_P2P_START` (`curMonth >= ROAD1Y_MAIL_P2P_START`). En 1971 et au-delà, les ouvertures restent autorisées sans restriction mensuelle.

### 2.3. Traçabilité des rejets sous `DECISION_LOG`
- Tout rejet calendaire sous `ROAD1Y_MAIL_P2P > 0` est tracé une fois par mois (`ym` dé-bouncé) :
  `action=reject reason=START year=... month=... start=...`
- Tout rejet de trésorerie au démarrage du mois est tracé :
  `action=reject reason=CASH bank=... need=...`

---

## 3. Revue de conformité et règles Squirrel

| Critère | Statut | Justification |
|:---|:---:|:---|
| **Comportement à 0 strictly identique** | **CONFORME** | À `ROAD1Y_MAIL_P2P_CASH = 0`, seuil = 37 000 £ et réserve = 25 000 £. À `ROAD1Y_MAIL_P2P_START = 0`, rejet en 1970. À `ROAD1Y_MAIL_P2P = 0`, sortie immédiate à la première ligne. |
| **Mots réservés Squirrel** | **CONFORME** | Aucun identifiant réservé utilisé (`clone`, `base`, `parent`, `static`, `delegate`, `resume`, `yield`, `constructor`, `instanceof`). |
| **Closures et lambdas** | **CONFORME** | Aucune closure ni fonction imbriquée capturant une variable locale englobante. |
| **Appels `Valuate`** | **CONFORME** | Aucun nouvel appel `Valuate`. |
| **Plafond AddSetting** | **CONFORME** | Le nombre d'`AddSetting` passe de 73 à 75, sous le plafond contractuel ajusté à 77 dans `sweeps/test_v251_inventory.py`. |
| **Garde multimodale** | **CONFORME** | Forçage à 0 hors route seule dans `settings.nut` et validation exhaustive dans `sweeps/test_road1y_multimodal_gate.py`. |
| **Projections ROAD100 / SHA** | **CONFORME** | Empreintes SHA256 mises à jour dans `sweeps/road100_off_projection.py`, `sweeps/rail_open_legacy.py` et `sweeps/rail_sibling_legacy.py`. |
| **Persistance Save/Load** | **CONFORME** | Aucun état persistant supplémentaire requis sur disque ; les réglages sont chargés via `AIController.GetSetting`. |

---

## 4. Résultats des tests hôte

Tous les tests unitaires et de régression sont au vert complet :
- `test_road1y*.py` : **97 tests réussis** (0 échec, 0 erreur).
- `test_road100*.py` : **236 tests réussis** (0 échec, 0 erreur, 3 ignorés).
- `test_v251*.py` : **7 tests réussis** (0 échec, 0 erreur).
- `test_road1y_mail_p2p.py` : **9 tests réussis** (0 échec, 0 erreur).
- `test_road1y_multimodal_gate.py` : **7 tests réussis** (0 échec, 0 erreur).
- `git diff --check` : **0 avertissement, formatage propre**.

---

## 5. Défauts trouvés et corrigés lors de la revue

1. **Tentative d'insertion dans `OpexLoadBusDistrictSettings` :**
   *Constat :* L'insertion de nouvelles variables dans `OpexLoadBusDistrictSettings()` altérait le hunk historique B2 figé dans `sweeps/fixtures/road100_bus_districts_hunks.json`, ce qui brisait la reconstruction exacte de la projection historique.
   *Correction :* Conformément aux chantiers précédents post-B2 (`road1y_freight_adm`, `road1y_loan_floor`, `road1y_alt_load_cond`, `road1y_mail_p2p`, `road1y_mail_p2p_missing`), les nouveaux réglages sont chargés dans `OpexLoadSettings()`, préservant la stabilité du loader historique sans effet de bord.

---

## 6. Risques résiduels

Les deux réglages sont inactifs au défaut 0. Lorsqu'ils seront activés pour exploration (ex. `road1y_mail_p2p_start=6` ou `road1y_mail_p2p_cash=20`), ils permettront d'isoler l'impact respectif du démarrage anticipé en 1970 et de l'abaissement du matelas de trésorerie sur le volume de lignes déployées et sur la rentabilité à 3 ans.
