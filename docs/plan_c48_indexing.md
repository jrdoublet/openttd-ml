# Plan d'implémentation C48 : Indexation exacte du vivier et de la planification aérienne

## Goal Description

La tâche **C48** s'attaque au verrou algorithmique fondamental d'OpexAI, établi empiriquement par le diagnostic C48.1 :
* **La cause racine** : En fin de partie, 94 % des passes de construction réussissent et déclenchent immédiatement la régénération incrémentale du portefeuille (`OpexIncrementalUpdateProjects`).
* **Le coût unitaire explose** : Chaque candidat retenu ($C \approx 300$) re-balaie linéairement l'ensemble des lignes existantes ($L \approx 60$), et `OpexAirPlans` répète ce balayage pour chaque combinaison aéroport/avion ($K$) et chaque ville ($T$).
* **L'impact mesuré** : Le coût par passe est multiplié par 15 (passant de 185 kops à 2 750 kops), le débit de décision s'effondre d'un facteur 9,2, plafonnant artificiellement le volume de l'IA.
* **La solution** : Remplacer les balayages linéaires $O(C \times L)$ et $O(K \times T \times L_{air})$ par une structure d'indexation exacte (`OpexLineIndex`) construite à la volée en début de passe en $O(L)$ (< 1 000 opcodes), ramenant toutes les requêtes de revalidation et d'éviction en $O(1)$.

```mermaid
flowchart TD
    subgraph Existant O(C x L + K x T x L)
        L1[Lignes existantes L] --> S1[Rejeu Groupes: 300 candidats x L]
        L1 --> S2[OpexAirPlans: K combos x T villes x L_air]
        S1 --> P1[Coût: 2 355 kops/appel]
        S2 --> P1
    end
    subgraph Optimisé C48 O(L + C + T)
        L2[Lignes existantes L] --> IDX[Construction OpexLineIndex en O(L)<br/>~1 000 opcodes]
        IDX --> O1[Rejeu Groupes: 300 candidats x O(1)]
        IDX --> O2[OpexAirPlans: Précalcul villes desservies en O(T x L_air)<br/>Combos en O(1)]
        O1 --> P2[Coût estimé: ~50-150 kops/appel<br/>Gain: ÷15 à ÷40]
        O2 --> P2
    end
```

---

## User Review Required

> [!IMPORTANT]
> **Choix d'architecture de l'index : Éphémère par passe vs Persistant dans `main.nut`** :
> - **Option retenue (Recommandée)** : Construire l'objet `OpexLineIndex` localement à la volée au début de `OpexIncrementalUpdateProjects` (et au début de `OpexAirPlans`).
>   - *Justification* : Avec $L \le 60$ (et $L \le 100$ en fin de partie), construire l'index prend moins de 1 000 opcodes, soit **0,04 %** des 2 355 kops dépensés par passe.
>   - *Avantage décisif* : Zéro risque de désynchronisation d'état (8 sites d'append de lignes et 1 site de suppression dans `main.nut`), zéro modification des structures de sauvegarde/persistance, isolation totale des effets de bord.

> [!CAUTION]
> **Protocole d'équivalence stricte obligatoire (Shadow Mode)** :
> Conformément aux enseignements du projet (C41.30, C41.38), un index qui modifierait d'un seul booléen le verdict d'éligibilité d'un candidat ne serait plus un changement de structure de données mais un changement de comportement décisionnel non maîtrisé.
> Un mode miroir (`c48_index_shadow=1`) exécutera en parallèle l'ancien parcours linéaire et la consultation indexée, déclenchant une assertion immédiate en cas de divergence.

---

## Open Questions

1. **Activation du commutateur** :
   Le réglage `c48_indexed_regeneration` sera introduit avec la valeur par défaut `0` (OFF) conformément aux règles du dépôt.
2. **Gestion de `OpexRoadPairServed`** :
   Pour deux tuiles $A$ et $B$, `OpexRoadPairServed` vérifie si une ligne routière a son origine à distance Manhattan $< 3$ de $A$ et son autre extrémité à distance $< 3$ de $B$.
   - *Option 1* : Indexer toutes les paires possibles ($13 \times 13 = 169$ paires par ligne routière, soit ~5 000 entrées de hash table).
   - *Option 2 (Recommandée)* : Indexer par tuile $A$ la liste restreinte des lignes routières dont une extrémité est à distance $< 3$ (généralement 1 ou 2 lignes), puis ne tester que cette sous-liste pour $B$. Complexité quasi-$O(1)$, 26 insertions par ligne seulement.

---

## Proposed Changes

### 1. Déclaration des réglages et instrumentation (`ai/OpexAI`)

#### [MODIFY] `ai/OpexAI/info.nut`
- Déclarer `c48_indexed_regeneration` (défaut `0`).
- Déclarer `c48_index_shadow` (défaut `0`, mode vérification d'équivalence stricte).

```squirrel
AddSetting({
  name = "c48_indexed_regeneration",
  description = "C48: Index exact O(1) pour la revalidation incrémentale et les plans aériens au lieu des balayages O(L). Défaut 0.",
  easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
  flags = AICONFIG_BOOLEAN
});
AddSetting({
  name = "c48_index_shadow",
  description = "C48: Mode miroir vérifiant l'équivalence exacte entre index et balayage linéaire. Défaut 0.",
  easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
  flags = AICONFIG_BOOLEAN
});
```

#### [MODIFY] `ai/OpexAI/main.nut`
- Charger les globales `C48_INDEXED_REGENERATION` et `C48_INDEX_SHADOW`.

---

### 2. Structure d'indexation exacte (`ai/OpexAI/candidates.nut` & `projects.nut`)

#### [NEW] Implémentation de `OpexBuildLineIndex(lines)` dans `candidates.nut`
Construit en un seul passage $O(L)$ sur `lines` les structures de consultation directe :

```squirrel
function OpexBuildLineIndex(lines)
{
  local idx = {
    servedAny = {},         // tuile -> true (DistanceManhattan < 3 sur rail ou road)
    servedRail = {},        // tuile -> true (DistanceManhattan < 3 sur rail seul)
    townRoadCounts = {},    // townId -> count
    tileToRoadLines = {},   // tuile -> [ligne1, ligne2] pour OpexRoadPairServed
    roadFreightBusy = {},   // cargo + "|" + tile -> true
    airOriginTowns = {},    // townId -> true
  };

  if (lines == null || lines.len() == 0) return idx;

  local width = AIMap.GetMapSizeX();
  local height = AIMap.GetMapSizeY();
  local radius = ORIGIN_SEPARATION - 1; // 2

  foreach (line in lines) {
    if (!("mode" in line)) continue;
    local mode = line.mode;

    // 1. Décompte de lignes routières par ville
    if (mode == "road") {
      local isPax = !("cargo" in line) || line.cargo < 0 || AICargo.HasCargoClass(line.cargo, AICargo.CC_PASSENGERS);
      if (isPax) {
        local townA = AITile.GetClosestTown(line.originA);
        idx.townRoadCounts[townA] <- (townA in idx.townRoadCounts) ? idx.townRoadCounts[townA] + 1 : 1;
        local isFeeder = (("isFeeder" in line) && line.isFeeder) || (("purpose" in line) && line.purpose == "feeder");
        if (!isFeeder) {
          local townB = AITile.GetClosestTown(line.originB);
          if (townB != townA) {
            idx.townRoadCounts[townB] <- (townB in idx.townRoadCounts) ? idx.townRoadCounts[townB] + 1 : 1;
          }
        }
      }
    }

    // 2. Indexation spatiale de proximité (losange de rayon 2)
    if (mode == "rail" || mode == "road") {
      local origins = [line.originA, line.originB];
      foreach (origin in origins) {
        local ox = AIMap.GetTileX(origin);
        local oy = AIMap.GetTileY(origin);
        for (local dx = -radius; dx <= radius; dx++) {
          local x = ox + dx;
          if (x < 0 || x >= width) continue;
          local dyLimit = radius - abs(dx);
          for (local dy = -dyLimit; dy <= dyLimit; dy++) {
            local y = oy + dy;
            if (y < 0 || y >= height) continue;
            local tile = AIMap.GetTileIndex(x, y);
            idx.servedAny.rawset(tile, true);
            if (mode == "rail") idx.servedRail.rawset(tile, true);
            if (mode == "road") {
              if (!(tile in idx.tileToRoadLines)) idx.tileToRoadLines[tile] <- [];
              idx.tileToRoadLines[tile].append(line);
            }
          }
        }
      }
    }

    // 3. Fret routier occupé
    if (mode == "road" && ("cargo" in line) && line.cargo >= 0) {
      idx.roadFreightBusy[line.cargo + "|" + line.originA] <- true;
      idx.roadFreightBusy[line.cargo + "|" + line.originB] <- true;
    }
  }

  return idx;
}
```

---

### 3. Intégration dans `OpexIncrementalUpdateProjects` (`ai/OpexAI/projects.nut`)

#### [MODIFY] `ai/OpexAI/projects.nut`
- En début de `OpexIncrementalUpdateProjects`, si `C48_INDEXED_REGENERATION` est actif (ou en shadow mode), instancier `local lineIndex = OpexBuildLineIndex(lines);`.
- Passer `lineIndex` à `OpexIncrementalCandidateStillValid(p, lines, abandonedPairs, lineIndex)`.
- Dans `OpexIncrementalCandidateStillValid` :
  - Remplacer les appels linéaires par les lectures $O(1)$ dans `lineIndex`.
  - En mode shadow (`C48_INDEX_SHADOW`), évaluer les deux versions et vérifier l'égalité stricte :
    ```squirrel
    if (C48_INDEX_SHADOW) {
      local legacyVerdict = OpexLegacyCheck(p, lines);
      local indexVerdict = OpexIndexedCheck(p, lineIndex);
      if (legacyVerdict != indexVerdict) {
        AILog.Error("C48 EQUIVALENCE MISMATCH on project " + OpexProjectAttemptKey(p));
        throw "C48 Equivalence violation";
      }
    }
    ```

---

### 4. Réindexation de `OpexAirPlans` (`ai/OpexAI/builder_air.nut`)

#### [MODIFY] `ai/OpexAI/builder_air.nut`
- Casser le produit cartésien $K \text{ combos} \times T \text{ villes} \times L_{air} \text{ lignes}$ :
- Avant la boucle `foreach (combo in combos)` :
  - Extraire la liste des tuiles d'aéroports aériens existants.
  - Précalculer une table `airServedTowns = {}` pour les $T$ villes du pool ($O(T \times L_{air})$ fait **une seule fois** au lieu de $K$ fois).
- À l'intérieur de la boucle des combos :
  - Le test `OpexAirTownServed(towns[i], lines)` devient un test instantané `if (towns[i].id in airServedTowns) continue;`.
  - En mode shadow, vérifier l'identité exacte du verdict avec la fonction historique.

---

## Verification Plan

### Automated Tests

1. **Selftest unitaire & Compilation Squirrel** :
   - Vérifier l'absence d'erreurs de syntaxe Squirrel.
   ```bash
   python3 sweeps/diag_c48_1_incremental_profile.py --selftest
   ```

2. **Preuve d'équivalence stricte (Shadow Test 1 an × 1 graine)** :
   - Exécuter avec `c48_indexed_regeneration=1` et `c48_index_shadow=1`. Si le conteneur termine avec le code 0 sans lever d'exception, l'équivalence est prouvée sur la première année.
   ```bash
   docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 sweeps/bench_v2.py --arms "OpexAI[c48_indexed_regeneration=1,c48_index_shadow=1]" --seeds 42 --years 1 --out /tmp/smoke_c48_shadow.json
   ```

3. **Preuve d'équivalence complète (Shadow Test 5 graines × 6 ans)** :
   - Exécuter sur 5 graines et 6 ans avec assertion shadow active. Zéro divergence tolérée.
   ```bash
   docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 sweeps/bench_v2.py --arms "OpexAI[c48_indexed_regeneration=1,c48_index_shadow=1]" --seeds 100 12345 42 7 999 --years 6 --out results/diag_c48_shadow_proof_6y_5seeds.json
   ```

4. **Mesure du gain en opcodes (`sweeps/diag_c48_1_incremental_profile.py`)** :
   - Comparer `Baseline` vs `Indexed` (sans shadow) sur 5 graines × 6 ans :
   ```bash
   docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 sweeps/diag_c48_1_incremental_profile.py --years 6 --seeds 100 12345 42 7 999 --out results/diag_c48_indexed_profile_6y_5seeds.json
   ```
   - Vérifier la réduction attendue de 80 % à 95 % des opcodes dans les phases `groups_replay` et `air`.

5. **Banc officiel de non-régression (20 graines × 10 ans)** :
   - Mesure appariée au test des signes pour valider l'absence de régression économique et la hausse du volume décisionnel.

### Manual Verification
- Examiner les logs de `C48_INCREMENTAL` pour constater l'effondrement des kops consommés par passe de régénération.
- S'assurer que le nombre de chantiers réalisés par an en fin de partie (1974-1975) ne subit plus l'effet de saturation.
