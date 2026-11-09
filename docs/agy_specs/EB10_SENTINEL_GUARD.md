# Spécification Technique — EB-10 (Garde Sentinelle 65535 et Acceptation Express Fictive)

## 1. Objectif et critère de succès chiffré

- **Constat du bug sentinelle 65535 :**
  Dans `lines.nut:255` et `bus_districts_overrides.nut:445`, la fonction `OpexAbandonedPairKey` cherche à identifier l'industrie de destination via `AIIndustry.GetIndustryID(candidate.dst)`. Or, en OpenTTD NoAI, si la tuile ciblée n'héberge pas d'industrie (cas classique d'une livraison urbaine de biens ou de vivres vers une ville), l'API OpenTTD ne retourne pas `-1`, mais la constante sentinelle `AIIndustry.INDUSTRY_INVALID = 65535`.
  Comme le code vérifie `if (dst < 0)`, la condition échoue (`65535 < 0` est faux). La clé d'abandon devient alors :
  $$\text{freight}|\text{cargo}|\text{srcIndustryId}|65535$$
  Cette clé erronée est partagée par **toutes les villes desservies depuis le même producteur**. L'échec de construction d'une ligne vers une seule ville bannit instantanément toutes les autres villes de ce producteur pendant un an !
- **Constat de l'acceptation express fictive :**
  Dans `catalog.nut:873` et `po01c_generators.nut:1016`, une ville est indexée dans `townAcceptors[cargo]` si sa population $\ge 300$ dès que la marchandise appartient à la classe `AICargo.CC_EXPRESS` (Marchandises / Courrier), même si l'acceptation sur sa tuile centrale est strictement inférieure au seuil de service ($\text{acceptance} < 8/8$). Des projets fantômes sont générés puis avortent ou ne transportent aucun fret.
- **Objectif :**
  1. Sécuriser la sentinelle `INVALID_INDUSTRY` pour affecter le préfixe ville `"t" + candidate.dstTown`.
  2. N'indexer dans `townAcceptors` que les villes ayant une acceptation réelle avérée ($\ge 8/8$).
- **Critère de succès chiffré :**
  - **Clés d'abandon :** Zéro clé contenant `|65535` générée lors des échecs de lignes vers ville.
  - **Projets viables :** 100% des lignes de fret urbain construites disposent d'une acceptation locale $\ge 8/8$ au déchargement.
  - **Économie :** Amélioration mesurée du profit fret urbain sans régression aux deux portes V102.

---

## 2. État du code vérifié dans le worktree

- **`ai/OpexAI/lines.nut:253-267` :**
  ```squirrel
  } else if (candidate.kind == "freight") {
    src = AIIndustry.GetIndustryID(candidate.src);
    dst = AIIndustry.GetIndustryID(candidate.dst);
    /* G9§1 : Pour du fret vers une ville, GetIndustryID retourne -1 (invalide).
     * La cle devenait freight|cargo|sourceId|-1, partagee par TOUTES les villes du
     * meme producteur/cargo : un seul echec bannissait la famille entiere pendant
     * au moins un an. On utilise dstTown (pose par les generateurs) prefixe "t"
     * pour distinguer ville/industrie sans collision d'identifiants. */
    if (dst < 0 && ("dstTown" in candidate) && candidate.dstTown >= 0) {
      dst = "t" + candidate.dstTown;
    }
    if (src < 0 && ("srcTown" in candidate) && candidate.srcTown >= 0) {
      src = "t" + candidate.srcTown;
    }
  }
  ```
- **`ai/OpexAI/bus_districts_overrides.nut:443-457` :**
  - Même bloc dupliqué verbatim avec le test insuffisant `if (dst < 0)`.
- **`ai/OpexAI/catalog.nut:870-877` :**
  ```squirrel
  foreach (cargo in this.cargos) {
    if (cargo == this.paxCargo) continue;
    local acceptance = AITile.GetCargoAcceptance(tile, cargo, 2, 2, this.railCoverage > 0 ? this.railCoverage : 4);
    if (acceptance >= 8 || (pop >= 300 && AICargo.HasCargoClass(cargo, AICargo.CC_EXPRESS))) {
      if (!(cargo in this.townAcceptors)) this.townAcceptors.rawset(cargo, []);
      this.townAcceptors[cargo].append(townObj);
    }
  }
  ```
- **`ai/OpexAI/po01c_generators.nut:1012-1020` :**
  - Même condition dupliquée dans le générateur asynchrone PO-01c.

---

## 3. Conception proposée

### Correction de la sentinelle dans `lines.nut` et `bus_districts_overrides.nut`
Remplacer le test fragile par un contrôle complet de validité d'industrie OpenTTD :
```squirrel
if ((dst < 0 || dst == 65535 || !AIIndustry.IsValidIndustry(dst))
    && ("dstTown" in candidate) && candidate.dstTown >= 0) {
  dst = "t" + candidate.dstTown;
}
if ((src < 0 || src == 65535 || !AIIndustry.IsValidIndustry(src))
    && ("srcTown" in candidate) && candidate.srcTown >= 0) {
  src = "t" + candidate.srcTown;
}
```

### Correction du filtrage d'acceptation catalogue
Dans `catalog.nut` et `po01c_generators.nut`, subordonner l'exemption `pop >= 300` à l'activation d'un réglage de garde :
```squirrel
local acceptValid = EB10_GUARDS ? (acceptance >= 8)
    : (acceptance >= 8 || (pop >= 300 && AICargo.HasCargoClass(cargo, AICargo.CC_EXPRESS)));
if (acceptValid) {
  if (!(cargo in this.townAcceptors)) this.townAcceptors.rawset(cargo, []);
  this.townAcceptors[cargo].append(townObj);
}
```

### Réglage et Plafond de paramètres
- **Nom proposé :** `eb10_guards` (défaut 0, 4 niveaux à 0).
- **Contrainte impérative :** Actuellement, le nombre de réglages déclarés dans `info.nut` est de 68, ce qui correspond exactement au plafond vérifié par `sweeps/test_v251_inventory.py`. L'introduction de ce réglage nécessite soit la suppression/retraite préalable d'un réglage obsolète désarmé, soit l'intégration directe de la correction de la sentinelle `65535` au titre de correctif de bug pur (sans réglage).

### Interaction avec Save / Load
- Les clés de `_abandonedPairs` sont sauvegardées sous forme de chaînes de caractères.
- Lors de `OpexLoadPersist(owner)` : ajouter un filtre nettoyant les éventuelles clés résiduelles polluées par `|65535` provenant d'une version antérieure du jeu.

---

## 4. Pièges connus et historique

- **Plafond des réglages (`sweeps/test_v251_inventory.py`) :** Tout nouvel `AddSetting` échoue immédiatement dans la suite de tests de contrat si le plafond n'a pas été rehaussé avec justification économique.
- **Impact sur le volume de candidats fret :** Supprimer l'exemption `pop >= 300` sans acceptation va réduire le nombre de candidats urbains générés. C'est un effet assainissant (évite des projets non viables), mais cela peut décaler légèrement les dates de premier projet fret dans les petites cartes.

---

## 5. Plan de test

1. **Tests unitaires et de contrat hôte (`sweeps/test_eb10_guards.py`) :**
   - Injecter un candidat fret avec `dst = 65535` et `dstTown = 12` : vérifier que la clé générée est `freight|cargo|srcId|t12` et non `freight|cargo|srcId|65535`.
   - Tester l'acceptation sur tuile avec acceptation = 4 et pop = 500 : vérifier qu'à `eb10_guards=1`, la ville est rejetée de `townAcceptors`.
2. **Smoke test local 1×1 :**
   - Vérifier la génération et l'exécution sans erreur Squirrel.
3. **Qualification V102 :**
   - Porte A 40 graines $\times$ 3 ans (seuil relatif $+4\%$).
   - Porte B 20 graines $\times$ 10 ans (non-érosion, garde de valeur $\ge 0{,}95$).

---

## 6. Estimation de difficulté et d'effet attendu

- **Difficulté :** **Faible** (1.5/5) pour le code Squirrel, mais moyenne sur le plan du processus (gestion du plafond de settings et synchronisation de 4 fichiers).
- **Effet attendu :** Déblocage immédiat de routes de fret urbain légitimes auparavant bannies par collision d'identifiant, gain de **$+15$ à $+40\text{ k£/an}$** sur les lignes de biens manufacturés.
- **Source des données :** Audit de code `lines.nut:255`, inventaire des abandons erronés C66/EB-10 (`docs/taches.md`).
