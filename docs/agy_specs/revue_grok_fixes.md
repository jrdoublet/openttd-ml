# Revue des correctifs grok-fixes (PO-02, MULTI-1, EB-4)

Travail local sur `grok-fixes`. Aucun défaut de réglage n'est modifié.
Au défaut 0, les nouvelles branches sont fausses : le corps décisionnel
historique n'est pas exécuté. Load est l'exception demandée : il précède
`OpexLoadSettings`, donc il ne peut pas dépendre de la globale encore à 0.

## PO-02 — slot `fleet` et save complet

Défaut : `PO02_LAST_PUBLISH_DATE` n'avait pas de clé `fleet`, alors que
`OpexPO01CStart` parcourt `rail`, `road`, `water`, `fleet`, `air`. À
`po02_independent_expiry=1`, l'affectation `PO02_LAST_PUBLISH_DATE[mode] = now`
sans `<-` lève « the index 'fleet' does not exist » et tue l'IA.

Correctif :

- Initialiseur à cinq slots, `fleet = 0`. Le TTL de fleet reste la branche
  existante `(mode == "water") ? 90 : 30`, donc 30 jours. La spec ne nommait
  pas fleet ; on n'invente pas un TTL.
- Save complet (`save_full_state=1`, défaut) écrit `saveObj.po02LastPublishDate`
  sous le même `if (PO02_INDEPENDENT_EXPIRY)` que le short save, même clé.
- Load copie les cinq entiers dès que la clé est une table, sans lire
  `PO02_INDEPENDENT_EXPIRY`. Une sauvegarde à quatre modes reçoit `fleet = 0`
  et ne réinjecte pas la table brute. Clé absente : la table reste à zéro
  (le premier passage PO-02 estampille `now` sans forcer une régénération).

Risques :

- Au défaut 0, le save complet évalue un `if` faux de plus, et chaque Load
  évalue `("po02LastPublishDate" in data)`. Aucune clé n'est écrite, aucune
  date n'est restaurée si la sauvegarde n'en a pas.
- Les pins SHA de `globals_pre.nut` (ROAD100-B2, RAIL-OPEN, RAIL-SIBLING,
  RAIL-DEPOT-SIGNAL) acceptent le nouvel initialiseur. La ligne est hors des
  hunks ROAD100. L'empreinte gelée précédente reste dans les listes pour
  `origin/master`.
- EB-7 et AIR-COVERAGE restent écrits seulement sur le short save. Hors sujet.

## MULTI-1

(à compléter)

## EB-4

(à compléter)
