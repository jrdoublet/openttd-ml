# Plan d'implémentation C55 : Isolation et mesure causale de l'incohérence PAX routière

## Goal Description

L'objectif de ce plan est de traiter l'incohérence fonctionnelle de revalidation du mode passager routier identifiée dans la tâche **C55**, en répondant point par point aux faiblesses du premier diagnostic et aux exigences méthodologiques :

1. **Reconnaître le statut d'hypothèse** : Ne plus présupposer que cette incohérence explique les 58 % de viviers vides (C39) ni le plafonnement global, mais mesurer sa contribution réelle.
2. **Isoler rigoureusement le PAX du Fret** : Découpler l'interrupteur `c55_road_origin_relax` (qui mélangeait fret et pax) en créant un levier pur `c55_road_pax_origin_relax`.
3. **Traiter le sur-service et la péremption économique** : Après la construction d'une première ligne dans une ville, les candidats subséquents conservés en portefeuille risquent de porter des estimations de demande (`OpexTownBusCatchment`) et de rentabilité obsolètes. Le plan prévoit d'analyser et de neutraliser ce sur-service destructeur de valeur.
4. **Traçabilité causale de bout en bout** : Instrumenter le parcours complet des candidats pax (sauvés du filtre $\to$ élus $\to$ bâtis $\to$ rentabilité unitaire réelle).

```mermaid
flowchart TD
    subgraph Pipeline Actuel (Incohérent)
        A1[Génération Pax<br/>Plafond 4 + pop/300] --> B1[Portefeuille Incrémental<br/>OpexOriginServed: PURGE DU PAX]
        B1 --> C1[Construction<br/>Plafond 4 lignes]
    end
    subgraph Pipeline Proposé Isolé (C55 PAX)
        A2[Génération Pax<br/>Plafond 4 + pop/300] --> B2[Revalidation Incrémentale Isolée<br/>Exemption OriginServed Pax<br/>+ Plafond 4 + Anti-doublon]
        B2 --> D2[Contrôle Péremption Demande<br/>Garde anti-sur-service]
        D2 --> C2[Construction Pax<br/>Traçabilité ligne & rentabilité]
    end
```

---

## User Review Required

> [!IMPORTANT]
> **Arbitrage sur la divergence de plafond urbain** :
> - La génération autorise jusqu'à `4 + population / 300` lignes par commune (`candidates.nut:1856`).
> - La construction (`main.nut:3422`) et la revalidation actuelle plafonnent strictement à `4` lignes (`OpexTownRoadLineCount < 4`).
> - **Proposition** : Aligner la revalidation sur le plafond dur de construction (`< 4`), tout en documentant explicitement cet écrêtage par rapport au vivier initial.

> [!WARNING]
> **Le diagnostic 5×6 existant montre une destruction économique (−6,9 % de valeur)** :
> L'ajout brut de lignes routières non régulées dilue le capital et cannibalise les flux. Tout plan d'action doit prioriser la rentabilité des lignes additionnelles avant d'envisager un quelconque volume.

---

## Open Questions

1. **Réévaluation de la demande résiduelle en vol** :
   Faut-il recalculer `OpexTownBusCatchment` lors de la revalidation d'un candidat pax si une ligne a déjà été construite sur cette ville depuis sa génération, ou simplement décoter son score économique d'un facteur de congestion ?
2. **Périmètre du réglage `c55_road_origin_relax` existant** :
   Souhaitez-vous renommer le paramètre actuel en `c55_road_pax_origin_relax` (pour briser toute ambiguïté avec le fret) ou conserver deux commutateurs distincts (`c55_freight_origin_relax` et `c55_road_pax_origin_relax`) ?

---

## Proposed Changes

### Configuration et Découplage Modale (`ai/OpexAI`)

#### [MODIFY] `ai/OpexAI/info.nut`
- Déclarer le paramètre booléen isolé `c55_road_pax_origin_relax` (défaut `0`), distinct de `c55_freight_origin_relax`.
- Déclarer la sonde passive de traçabilité `c55_pax_trace_probe` (défaut `0`).

```squirrel
AddSetting({
  name = "c55_road_pax_origin_relax",
  description = "C55: Exempte le PAX routier d'OpexOriginServed dans la revalidation incrémentale. Défaut 0.",
  easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
  flags = AICONFIG_BOOLEAN
});
AddSetting({
  name = "c55_pax_trace_probe",
  description = "Sonde de traçabilité causale des candidats pax routiers (sauvés, élus, construits). Défaut 0.",
  easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
  flags = AICONFIG_BOOLEAN
});
```

#### [MODIFY] `ai/OpexAI/main.nut`
- Charger les variables globales `C55_ROAD_PAX_ORIGIN_RELAX` et `C55_PAX_TRACE_PROBE`.
- Découpler les contrôles de construction routière : le fret reste sous `C55_FREIGHT_ORIGIN_RELAX`, le pax reste sous ses propres règles.
- Tracer l'élection et la construction des lignes pax sauvées sous `C55_PAX_TRACE_PROBE`.

---

### Revalidation Incrémentale et Garde Anti-Sur-Service

#### [MODIFY] `ai/OpexAI/projects.nut`
- Nettoyer le code mort (`isFeeder` dans un sous-bloc déjà `!isFeeder`).
- Restructurer `OpexIncrementalCandidateStillValid` pour traiter le pax indépendamment :

```squirrel
if (p.kind == "pax") {
  if (C55_ROAD_PAX_ORIGIN_RELAX) {
    // 1. Anti-doublon strict A <-> B
    if (OpexRoadPairServed(lines, p.src, p.dst)) return false;

    // 2. Plafond d'alignement avec la construction (< 4)
    if (OpexTownRoadLineCount(lines, p.src) >= 4) return false;
    if (OpexTownRoadLineCount(lines, p.dst) >= 4) return false;

    // 3. Sonde passive / traçabilité causale
    if (C55_PAX_TRACE_PROBE && (OpexOriginServed(lines, p.src, true) || OpexOriginServed(lines, p.dst, true))) {
      OpexLogEvent("C55_PAX_SPARED", { src: p.src, dst: p.dst, profit: p.profit });
    }
  } else {
    // Règle legacy restrictive : purge dès qu'une extrémité est servie
    if (OpexOriginServed(lines, p.src, true)) return false;
    if (OpexOriginServed(lines, p.dst, true)) return false;
    if (OpexRoadPairServed(lines, p.src, p.dst)) return false;
  }
}
```

---

### Analyseur et Diagnostic Dédié

#### [NEW] `sweeps/diag_c55_pax_isolation.py`
Création d'un script de diagnostic 5 graines × 6 ans comparant 3 bras purs :
1. `Baseline` : `c55_road_pax_origin_relax=0`, `c55_freight_origin_relax=0`
2. `PaxRelax` : `c55_road_pax_origin_relax=1`, `c55_freight_origin_relax=0` (effet pur pax)
3. `FreightRelax` : `c55_road_pax_origin_relax=0`, `c55_freight_origin_relax=1` (effet pur fret)

Métriques enregistrées :
- Nombre de candidats pax rejetés par `OpexOriginServed` vs sauvés.
- Nombre de projets pax sauvés qui sont élus (`PROJECT_CHOSEN`) et construits (`ROAD_BUILD`).
- Évolution de la vacuité du vivier (`PORTFOLIO_EMPTY`).
- Rentabilité moyenne et profit par véhicule routier pax (`profit_per_vehicle`).
- Valeur de compagnie et profit annuel net.

---

## Verification Plan

### Automated Tests
1. **Selftest unitaire Python** :
   ```bash
   python3 sweeps/diag_c55_pax_isolation.py --selftest
   ```
2. **Smoke test Docker (1 an × 1 graine)** :
   ```bash
   docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 sweeps/bench_v2.py --arms "OpexAI[c55_road_pax_origin_relax=1]" --seeds 42 --years 1 --out /tmp/smoke_c55_pax.json
   ```

3. **Diagnostic 3 bras d'isolation (5 graines × 6 ans)** :
   ```bash
   docker run --rm --cpus=3 --memory=2g --memory-swap=2g -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab python3 sweeps/diag_c55_pax_isolation.py --seeds 100 12345 42 7 999 --years 6 --out results/diag_c55_pax_isolation_6y_5seeds.json
   ```

### Manual Verification
- Vérifier que `c55_road_pax_origin_relax=1` n'induit aucune variation sur le nombre de véhicules fret (isolation prouvée).
- Vérifier si les candidats pax sauvés présentent un profit unitaire positif ou s'ils cannibalisent les lignes existantes.
