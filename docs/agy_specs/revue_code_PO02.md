# Revue de Code — PO-02 (Échéance de Publication Propre à Chaque Vivier Modal)

## 1. Périmètre du Diff Inspecté

- **Réglage introduit :** `po02_independent_expiry` (min=0, max=1, défaut 0, 4 difficultés à 0, flags 0).
- **Fichiers modifiés :**
  - `ai/OpexAI/globals_pre.nut` : déclaration `PO02_INDEPENDENT_EXPIRY <- 0;`, `PO02_LAST_PUBLISH_DATE <- { air = 0, rail = 0, road = 0, water = 0 };`.
  - `ai/OpexAI/info.nut` : déclaration du réglage public avec description et bornes.
  - `ai/OpexAI/settings.nut` : lecture unique `PO02_INDEPENDENT_EXPIRY = AIController.GetSetting("po02_independent_expiry") == 1 ? 1 : 0;`.
  - `ai/OpexAI/po01c_regen.nut` : dans `OpexPO01CStart`, si `PO02_INDEPENDENT_EXPIRY` est actif et qu'un mode activé n'a pas été marqué nécessaire par la logique globale, vérification du TTL écoulé depuis sa dernière publication (30j pour rail/route, 90j pour water) ; dans `OpexPO01CAcknowledge`, mise à jour de la date de publication pour les modes couverts.
  - `ai/OpexAI/persist.nut` : sauvegarde et restauration de `PO02_LAST_PUBLISH_DATE` sous garde `if (PO02_INDEPENDENT_EXPIRY)`.
  - `sweeps/test_po02_expiry.py` : test de contrat hôte validant AddSetting, globales, persistance et TTL.
  - `sweeps/road100_off_projection.py`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/test_v251_inventory.py` : mise à jour des projections et SHA.

---

## 2. Relecture Critique "Œil Neuf" et Vérification des Invariants

1. **Innocuité au défaut 0 :**
   - À `po02_independent_expiry = 0`, `PO02_INDEPENDENT_EXPIRY` vaut 0.
   - Les blocs conditionnels dans `OpexPO01CStart` et `OpexPO01CAcknowledge` ne s'exécutent pas.
   - Le chemin par défaut de régénération PO01C est rigoureusement identique au bit près.
2. **Découplage modal :**
   - Chaque vivier modal dispose de sa propre date d'échéance sans forcer l'expiration des viviers tiers.
3. **Hygiène Squirrel & Non-rail :**
   - Aucun tableau `.find(`, aucune fonction anonyme.
   - Fichiers touchés limités au portefeuille PO01C/PO02 sans toucher à `builder_rail.nut` ni au moteur de construction rail.

---

## 3. Conclusion

Le code est conforme à la spécification PO-02, inoffensif au défaut 0, et validé par les tests de contrat.
