# MULTI-1 — quatrième piste ROAD cargo alternatif : diagnostic SHADOW sans gisement physique (26 octobre 2026)

**Verdict : `NO-GO_PREQUALIFICATION_PHYSIQUE` pour un quatrième levier ON issu
de ce sondage.** Ce n'est **pas** une porte A économique ni une démonstration
qu'il n'existe aucun fret ROUTE profitable sur la carte. Le diagnostic
pré-enregistré ne prouve **aucun plan alternatif constructible** dans
la fenêtre 1971–1973 ; la porte A 40×5 `gain_short` et la B 20×10
`non_erosion` n'ont donc pas été déclenchées. MULTI-1 demeure ouvert,
aucun changement de défaut ou adoption.

## Provenance et intégrité du protocole

- [Pré-enregistrement SHADOW](multi1_road_cargo_shadow_protocol_20261026.md)
  publié **avant code** au commit `e458132c`; audit des journaux antérieurs
  [publié auparavant](multi1_rejets_1974_20261026.md) sous `842e15b8`.
  Instrumentation indépendante à défaut `0`, source `98f11b5e`.
- Le mode `1` examine au plus **16 couples par mois** (deux sources,
  quatre puits industriels, quatre villes), et jusqu'à **trois**
  planifications physiques en `AITestMode` parmi les candidats
  rentables et finançables. Le chemin classique et PO-01c restent
  inchangés pour la sélection et la construction. Sur 256²,
  `v276_cand_slices=3` se résout à `0`.
- Contrats ciblés et suite complète sur la source livrée :
  **2 931 tests réussis** (5 ignorés, 2 échecs attendus), `git diff --check`
  propre. Les empreintes gelées historiques de PO-01c sont conservées
  après soustraction stricte et vérifiée des seuls fragments SHADOW.
- Smoke préalable `multi1_roadcargo_shadow_smoke_1x2_20261026` :
  graine 42, 1970–1971, OFF/SHADOW, **2/2 parties** complètes,
  sans erreur détectée. Aucun déclenchement dans cette fenêtre ;
  Δ descriptif de profit +20 998 £/an, sans attribution causale.
- Save/Load réel `results/multi1_roadcargo_shadow_saveload_20261026.json` :
  graine 42, quatre ans initiaux et reprise du **1er janvier 1973**
  pour un an, **48+13 sauvegardes**, `LOAD_RECONCILE` positif,
  aucune erreur Squirrel. Sur la phase A : deux mois écartés pour
  `ordinary_financeable`, une observation `arm/done` avec zéro
  couple admissible ; sur la phase B : un mois écarté.
  **Limite :** la sauvegarde choisie n'était pas au milieu d'un
  plan physique SHADOW en cours. La compagnie fantôme inerte du
  harnais est également présente : ce Save/Load teste la reprise,
  pas l'équivalence économique même monde.

L'exposition proprement dite est
`results/multi1_roadcargo_shadow_exposure_5x5_20261026.{json,jsonl,manifest.json}`
et ses dix journaux
`results/multi1_roadcargo_shadow_exposure_5x5_20261026_engine/`.
**Graines 42,100,7,999,2026, 1970–1974, 256², `probes=258`,
OpenTTD 15.3, OpenGFX 7.1, AAAHogEx-115, 10 workers, un seul
Docker, 10 CPU et 8 Gio.** Les bras ne diffèrent que par
`multi1_road_cargo_shadow=0/1`. **10/10 parties, 5/5 paires
complètes** et aucune erreur script/Squirrel dans les dix logs.
Le bundle source gelé vaut
`7aeeaec516aef86236a16cc25e05e8a7c702deafab0e61247a8e57834d0414f1` ;
manifeste `fadea943e59d303367b6e591ef6e4df5e35654dd46432a948a7e5ef7437a56a5`.
Le manifeste porte `git_dirty=1`, **du seul dossier scratch
Save/Load non suivi**, créé après le commit `98f11b5e` :
aucun fichier source suivi n'était modifié. Ce dossier est conservé
et dorénavant ignoré par Git ; ne pas déclarer le manifeste propre
rétroactivement.

## Résultat de préqualification : cinq mondes

Les nombres d'échantillons sont des **observations ponctuelles par mois**,
pas des couples exhaustifs du marché. Un candidat `financeable` a
un profit brut prédit positif et passe le devis ROUTE avec marge 121 %
et caisse mobilisable ; il reste **non constructible** tant que
`OpexRoadPlanFor` n'a pas trouvé ses sites, son tracé et son dépôt.

| Graine | Déclenchements | Mois sautés (ROUTE ordinaire finançable) | Couples dans la bande | Positifs/finançables | Plans physiques essayés | Plans OK | Observations censurées |
|---|---:|---:|---:|---:|---:|---:|---:|
| 42 | 3 | 6 | 0 | 0 | 0 | 0 | 0 |
| 100 | 4 | 9 | 7 | 3 | 1 | 0 | 1 |
| 7 | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| 999 | 3 | 1 | 6 | 6 | 2 | 0 | 0 |
| 2026 | 1 | 5 | 1 | 1 | 1 | 0 | 1 |
| **Total** | **12** | **23** | **14** | **10** | **4** | **0** | **2** |

Deux refus `TRACEX` (graines 100 et 2026), deux `SITEB`
(graine 999) et **deux autres candidats devenus `STALE` avant
leur planification** (même monde 999). Zéro résultat
`phase=plan reason=OK`, zéro profit positif de plan physiquement
admissible ; **0/5 mondes** peuvent servir de preuve à la construction
d'une liaison issue du deuxième cargo.

Les deux censures sont matérielles : un unique `OpexRoadPlanFor`
coûte **255 274** ou **473 213 opcodes** dans les mondes concernés,
au-delà du budget nominal de 200 000 par observation.
Un plan est atomique ; le protocole avait pré-enregistré **une borne
souple**, et ces excès sont des mesures, ni des dépassements cachés
ni une autorisation d'augmenter après coup la borne. Aucun résultat
négatif ne porte sur toutes les autres paires non échantillonnées.

## Économie descriptive, distincte des critères A/B

| Graine | Δ profit annuel SHADOW−OFF fin 1974 (£/an) |
|---|---:|
| 42 | −71 610 |
| 100 | −37 911 |
| 7 | −287 221 |
| 999 | +14 261 |
| 2026 | +77 681 |

**Moyenne −60 960 £/an**, médiane −37 911, **2 V / 3 D** ;
ratio des valeurs de compagnie moyennes `SHADOW/OFF = 0,997823`
(−0,218 %). Ce résultat n'est **pas une porte A** : seulement cinq
graines, `probes=258`, aucun plan réussi, comparateur de diagnostic
et trajectoires pouvant diverger à cause des opcodes de la sonde.
Il n'existe aucun gain de route attribuable au quatrième mécanisme.

## Décision et suite du chantier

La condition préenregistrée — plusieurs mondes avec plans ROUTE
**physiquement** admis, marge marginale plausible au moins du
seuil de +4 % de A — **n'est pas satisfaite**. Le bras ON du
deuxième cargo **n'a pas été implémenté** ; les trois
`NO-GO_NON_EXPOSE` précédents restent définitifs, les quatre
défauts MULTI-1 restent à `0`. Pas de porte A/B ni d'adoption.

L'ancienne cohorte 20×10 situe l'écart stratégique en **1975–1979**
avec trésorerie Opex élevée et flotte ferroviaire stagnante
([chronologie](multi1_horizon_10ans_20261026.md)). Le pas suivant
de MULTI-1 doit analyser **les projets réalisables et effectivement
financés après 1974**, puis leur profit marginal comparé à AAAHogEx :
une exploration SHADOW tardive distincte pourrait la mesurer,
mais aucun réglage ou nouvelle porte n'est pré-enregistré ici.
La porte A **40×5 fixée pour les leviers précoces** ne doit pas
être allongée rétroactivement pour qualifier une hypothèse de
1975–1979. MULTI-1 demeure une tâche ouverte.
