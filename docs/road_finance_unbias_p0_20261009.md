# P0 Capital — isolation du biais ROAD 121 % (09/10/2026)

## Question causale

Après l'échec de la variante monolithique `capital_quote_learning=1`
(`docs/capital_quote_p0_20261009.md`), tester **uniquement** la suppression
du 121 % appliqué au besoin de financement ROAD, sans toucher aux devis
physiques, réserves, classements économiques, règles AIR/RAIL/WATER ou
scheduler. Aucune variante nouvelle n'est adoptée par défaut.

Le 121 % **n'était pas un nombre purement inventé** :
`docs/archives/taches_archive_2026-09-09.md` rapporte 109 succès ROAD réels
sur 145 tentatives, cinq graines × six ans, ratio réel/devis moyen 1,238,
médian 1,183, écart-type 0,304. L'ancien décompte 4 812 provenait de
checkpoints SIGN dupliqués et est invalide. Le 121 % reste une approximation
globale, non une estimation physique fiable pour chaque route.

## Contrat de la variante

- `road_finance_unbias_p0=0` par défaut à toute difficulté ; si ON, remplace
  exclusivement `biasPct = 121` par `biasPct = 100` pour `mode=road` dans
  `OpexProjectFinanceCapital`. Ne s'applique pas si `capital_quote_learning=1`
  (retour prioritaire), `policy_portfolio=0`, ni si `capitalIsActual`.
- Le prix historique de sélection est
  `floor(1,21 × construction) + max(0, budgetCapital − construction)` ;
  la variante est `construction + max(0, budgetCapital − construction)`.
  `budgetCapital` contient notamment `ROAD_CAPITAL_MARGIN` et, s'il existe,
  le capital de transit. Le multiplicateur n'est **pas une dépense**.
- `budgetScore`, `candidate.capital`, ROI, prix des moteurs et `OpexCashReserve`
  ne sont pas modifiés. L'admission et `fundScore` peuvent changer ; cela peut
  modifier indirectement la politique du portefeuille et le classement modal.
- Aucune garde de construction nouvelle dans cette expérience. En particulier
  `task_road.nut` compare l'ancien `candidate.capital` à la caisse avant le
  plan; il révise `candidate.capital` après le siting, mais ne garde sur la
  nouvelle estimation que si `CAPITAL_QUOTE_LEARNING=1`. Avec seulement
  `road_finance_unbias_p0=1`, le risque `cash < devis révisé + réserve` existe.
  Ajouter une garde ici créerait **une autre intervention** et requiert un
  autre A/B ; la sonde se contente donc de le mesurer.

## Mesures isolées

`road_finance_gate_shadow_p0=0` par défaut : sonde passive, à activer dans
**les deux bras** uniquement dans un diagnostic à `--script-debug`.
Sur les projets ROAD du même passage dans `OpexProjectSelectAffordable`, elle
compare les besoins de financement 121/100 avec `capitalBudget`, sans
rejouer le classement ou la construction :

- `ROAD_FINANCE_P0` : candidats visités et admissibles à 121/100, bascules
  d'admission, ROAD retenus dans le vivier local ; compte des **visites**,
  pas des OD uniques.
- `ROAD_FINANCE_UNLOCK_P0` : OD, cargo, nature, date, besoins 121/100,
  budget et présence dans la sélection finale ; dédoublonnage possible.
- `ROAD_FINANCE_POSTPLAN_P0` : ancien devis, devis recalculé après choix
  géométrique, caisse, besoin recalculé, déficit de cash indicatif.
- `ROAD_FINANCE_BUILD_P0` : devis révisé, coût débité `actualCost` à son
  retour, succès/échec. L'échec ne mesure pas la perte finale en présence
  de remboursements différés ou d'actifs conservés.

L'extracteur `sweeps/analyse_road_finance_p0.py` travaille sur les logs
moteur avec `--script-debug`, distingue visites et OD uniques, et marque
**inconnue** une partie sans marqueur ROAD (elle peut aussi n'avoir aucun
candidat ROAD). Le signal Info est vérifié sur le smoke ci-dessous ; hors
`--script-debug`, une absence de marqueur ne prouve rien.

La mesure `unlocked` ne prouve pas la constructibilité d'une route qui n'a
jamais été tentée, ni les effets exacts des filtres de profit, TOP_K et tiers
de classement. Les projets feeder V139 (s'ils sont activés) font partie des
ROAD, à distinguer si l'option n'est plus au défaut.

## Validation acquise

Tests statiques et de collecte :
`python -m unittest -q sweeps.test_road_finance_unbias_p0
sweeps.test_analyse_road_finance_p0 sweeps.test_capital_quote_learning`
→ **15/15 verts**. Auto-test du banc C66.4 : vert.
La sélection étendue comprenant également les tests d'extraction CQ et de
son agrégation donne **20/20 verts**. `git diff --check` ciblé : propre.

Smoke instrumenté `p0_road_finance_smoke_20261009_r3`, seed 42,
3 ans, `--script-debug`, 2 workers, 3 CPU, 4 GiB,
bundle `dcd75dcb1dede76d526ddf273b820927cbeb10413bb5c6fdd3b4aab5173df562`,
2/2 duels complets. Référence et variante ont les mêmes résultats :
`profit_year` 2 187 169 £, `company_value` 4 201 687 £, écart 0.
Les logs sont bien décodés par
`results/p0_road_finance_smoke_20261009_r3_analysis.json` :

| Mesure, graine 42 | Référence | Variante |
|---|---:|---:|
| Passes de sélection ayant des projets ROAD | 42 | 42 |
| Visites de candidats ROAD | 114 | 114 |
| Visites admises à 121 % | 114 | 114 |
| Visites admises à 100 % | 114 | 114 |
| Visites déverrouillées par 100 % | 0 | 0 |
| Tentatives planifiées | 3 | 3 |
| Déficits de cash après plan | 0 | 0 |
| Constructions réussies | 2 | 2 |

**Verdict du smoke : `diagnostic_only`**. Aucune exposition au retrait du
121 % sur la graine 42. Une graine sans bascule ne démontre rien sur les
autres graines ni sur la nécessité du tampon historique.

## Porte A à qualifier

Protocole V102 `gain_short` : 40 graines canoniques × 3 ans, bundle unique
figé, référence `road_finance_unbias_p0=0`, variante `=1`, toutes les autres
options identiques et sonde shadow OFF pour la performance. Mesurer
`profit_year`, Wilcoxon exact, IC95 bootstrap, `company_value` et opcodes.
La commande hôte dérive de `sweeps/run_c66_reference.py` avec :
`--campaign p0_road_finance_A40x3_20261009_r1 --reference
OpexAI[road_finance_unbias_p0=0] --variant
OpexAI[road_finance_unbias_p0=1] --variant-policy-id road_unbias_p0
--decision-rule gain_short --primary-metric profit_year
--min-useful-primary-delta-pct 4 --value-guard-max-loss-pct 5
--required-seeds 40 --required-years 3 --years 3 --max-workers 10
--cpus 10 --memory 8g --engine-timeout 1800` (avec guillemets autour
des spécifications OpexAI, graines canoniques par défaut). Vérifier que
Docker est libre avant lancement ; un autre chantier l'occupait après le
smoke. Ne pas lancer deux campagnes simultanément.
La porte B 20×10 ne doit suivre **que si A passe**. Si aucune exposition
ROAD mesurable n'apparaît, classer le résultat comme absence d'effet
observable dans ce périmètre, pas comme preuve qu'un devis physique couvre
les dépenses réelles. Ne pas chercher un pourcentage optimum.

Les expériences ultérieures (devis physique détaillé, puis apprentissage
du résiduel) restent distinctes et ne sont pas implémentées ici.

## Porte A exécutée — rejet de la suppression du 121 %

Campagne `p0_road_finance_A40x3_20261009_r1` sous image
`openttd-lab:latest` (digest de l'image archivé dans le manifeste),
**40/40 paires, 80/80 parties saines**, mêmes 40 graines V102 canoniques,
3 ans, 10 CPU / 10 workers / 8 GiB ; `probe_cost=0` et sonde ROAD shadow
OFF dans les deux bras. Source commune figée sous SHA256
`686fe965c7a5ea4bbfb67ed80d83340cd75bbf0ef1f4826cadc538924ff4dfcf`.
Le manifeste `results/p0_road_finance_A40x3_20261009_r1.manifest.json`
certifie une **unique différence effective**, `road_finance_unbias_p0`.

Variante moins référence à trois ans :

| Mesure | Résultat |
|---|---:|
| `profit_year`, moyenne | **+5 915,65 £/an** |
| `profit_year`, médiane | 0 £/an |
| Victoires / défaites / égalités | 7 / 7 / 26 |
| Wilcoxon exact bilatéral | **p = 0,6697998** |
| IC95 bootstrap du delta moyen | **[−3 003,975 ; +16 456,775] £/an** |
| Gain moyen minimal V102 (`+4 %` référence) | +77 547,651 £/an |
| `company_value`, ratio des moyennes | +0,159149 % |

Verdict harnais **`fail_primary`**. Le retrait ROAD 121 % est **rejeté** ;
pas de porte B20×10 et aucun changement du défaut. Le gain moyen est
inférieur au seuil économique et l'IC95 inclut zéro. Les 26 égalités de
résultat terminal suggèrent peu de décisions significativement altérées,
mais ne constituent **pas** à elles seules une mesure de zéro exposition :
les logs de porte A n'activaient pas la sonde et deux parcours peuvent
converger. Le smoke instrumenté seed42 confirme zéro bascule sur cette
seule graine ; le nombre d'OD débloquées parmi les 40 graines reste
**inconnu** sans diagnostic shadow supplémentaire.

La campagne A possède un bundle différent du smoke (arbre partagé en
évolution) ; **chaque comparaison intra-campagne** reste appariée sur son
propre bundle identique. Ce test attribue au seul retrait de 121 %
les éventuels changements de sélection, mais pas une éventuelle économie
de construction : le capital réellement débité reste inchangé.

**Suite :** analyser séparément les composants physiques manquants dans
les devis, en conservant 121 % et les réserves de risque historiques
tant qu'une politique de liquidité n'est pas elle-même évaluée.
