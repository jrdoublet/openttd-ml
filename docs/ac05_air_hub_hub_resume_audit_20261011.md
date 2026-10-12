# AC-05 — catalogue AIR hub → hub : audit de reprise (11 octobre 2026)

**Verdict : parcours `hubHubI/J` correct sur snapshot figé, sans correction
de production.** La fixture est exhaustive sur les paires d'indices
non orientées, pas sur l'identité métier de deux aéroports distincts. Elle
signale un **travail marginal V86 vraisemblablement inutile au défaut C121**,
mais ne chiffre pas les opcodes de ce sous-calcul : aucune optimisation
qualifiée ou adoptée. Les rebalayages volontaires après changement de
topologie restent conformes au comportement retenu après le rejet V143.

## Qualification corrective AC05 postérieure à l'audit

`ac05_skip_unused_hub_income=1` supprime exclusivement le pré-calcul
`hubAvgIncome` lorsque C121 est actif et rend la valeur inutilisée ; le
chemin V86 avec C121 désactivé reste historique. Les tests de source
et modèles passent. La qualification séparée est **ACCEPTÉE sous la
règle utilisateur de non-dégradation**, sous réserve du cumul :

- B20×10 économie : profit +29 990 £/an, IC95 [−149 152 ; +192 701],
  valeur +1,48 %, 40/40 parties saines ; pas de perte démontrée.
- 10×4 opcode initial : −610 645 opcodes VM, IC95 franchissant zéro ;
  profit terminal −64 392 £/an, IC95 strictement négatif dans ce petit
  échantillon, donc extension nécessaire et effectivement menée.
- 40×4 (les dix graines initiales et trente graines supplémentaires,
  bundle identique, toutes paires saines) : profit 1973 **−6 472 £/an**,
  IC95 **[−66 494 ; +54 951]** ; opcode VM global 1970–1972
  **−899 693** (−0,467 %), IC95 **[−1 860 639 ; +39 784]**.

Le signal négatif économique 10×4 n'est pas confirmé sur les 40 ;
pas d'équivalence mathématique prétendue. Aucun gain requis.
[Rapport des campagnes et limites](air_catalogue_validation_finale_20261011.md).

## 1. Déroulement et invariants du code actif

| Étape | Source `ai/OpexAI/air_planning.nut` | Résultat |
|---|---|---|
| Pré-calcul marginal | `:1634–1690` | `hubAvgIncome` initialisé et sommes des lignes AIR recalculées quand `AIR_HUBHUB_MARGINAL=1`, **avant** chaque invocation de boucle, y compris les reprises |
| Initialisation | `:1692–1702`, `:2501–2504` | Curseur initial `hubHubI=0`, `hubHubJ=1`; hub suivant démarre à `j=i+1`, donc jamais `i=j` |
| Budget | `:1703–1713` | Avant la prochaine paire, uniquement après une paire parcourue sur cette invocation ; yield inscrit `(i,j)` non encore consommé et préserve `bestPlan` |
| Rejets | `:1714–1791` | V133, validité V119/paires publiées, cible, préfiltre, liaison existante, distances, bande, abandon ; chaque rejet suit la progression |
| Choix | `:1792–1927` | Demande, avion C121 ou legacy, éventuelle marge V86 legacy, profit puis `OpexAirStoreRoutePlan` dans l'ordre existant |
| Fin | `:1928–1935`, `:2470–2510` | `(len(hubs),0)` marque la fin ; le combo suivant remet `(0,1)` |
| Snapshot V119 | `:1104–1171`, `:2423–2439` | Même combo/signature : mêmes tableaux ordonnés ; changement de signature : curseur/phase au départ, saut des paires déjà publiées |

Le produit cartésien n'est **pas** `hubs×hubs` : le parcours est le triangle
strict `0≤i<j<n`, soit `n(n−1)/2` indices distincts pour une liste
stable. Un yield après la dernière paire d'une ligne reprend au premier
`j=i+1` suivant ; la dernière paire globale peut dépasser le budget de
tranche sans être rejouée. Une tranche ne bloque pas indéfiniment sur une
paire rejetée.

L'exclusion de liaison existante est **symétrique** : l'index C80 écrit
`oA|oB` et `oB|oA` (`:315–329`) ; sans index, la boucle teste
`(st1,st2)` et son inverse (`:1740–1763`). Le préfiltre C80 des
centres-villes est distinct, optionnel et rejeté historiquement ; aucune
réactivation. La clé des paires publiées V119 combine bras, type d'aéroport et
`OpexAirPairKey` ; les éventuels projets de même paire provenant d'autres
combos ne relèvent pas de cette preuve d'unicité d'indices.

**Attention au mot « finit » :** la boucle termine sur **un snapshot qui reste
stable**. La signature V119 n'est qu'un effectif de lignes vivantes et de
stations aéroport, donc peut confondre deux topologies de mêmes cardinalités.
En cas de signature différente, V119 relance intentionnellement le balayage ;
l'essai V143 visant à le conserver a perdu **63,9 k£/an** en porte A
40×3, en particulier des opportunités hub-hub. Il est interdit de déduire de
la parité sur snapshot figé qu'il faudrait supprimer les redémarrages.

## 2. Preuve de parité, filtrage et garde de marge

`sweeps/test_ac05_air_hub_hub_resume.py` : **11 tests** dont **2 880
comparaisons** monolithique/tranché (6 nombres de hubs 0/1/2/3/5/9,
5 cibles, 4 profils de coût, 4 masques de rejet et 6 budgets).
Pour toutes ces combinaisons : **mêmes indices visités une fois, dans le même
ordre, mêmes rejets ordonnés, mêmes admissions et même coût *synthétique par
paire*.** Le pré-calcul de marge, quand activé, est facturé à chaque appel
dans le modèle séparément ; contrairement au travail des paires, il peut
croître avec le découpage. La fixture ne reproduit pas une VM ni le prix des
appels `AICargo`.

Cas explicites : première et dernière paire, frontière de ligne,
budget=1 avec toutes paires coûteuses et rejetées, deadline après une
paire, `already_connected` dans les deux orientations, `hubPhase`, reset
V119 et skip des paires déjà publiées.

Pour illustrer les rejets sur une même fixture (9 hubs, 36 couples,
budget=1, masques de rejet tous actifs) :

| Cas synthétique | Visités | Admis | Rejets (premier motif applicable) |
|---|---:|---:|---|
| Sans cible | 36 | 9 | V133 5, snapshot 4, préfiltre 3, déjà connecté 7, distance 6, bande 1, économie 1 |
| Cible premier hub | 36 | 4 | V133 5, snapshot 4, cible 21, déjà connecté 1, bande 1 |
| Cible absente | 36 | 0 | V133 5, snapshot 4, cible 27 |

Ce tableau **ne mesure pas** les rejets d'une partie réelle : les motifs,
identités et coûts sont figés artificiellement. Une ville ciblée filtre les
admissions, pas le nombre de paires de l'arm déjà parcourues.

**Déchet d'opcodes à isoler, sans politique nouvelle :**
`AIR_HUBHUB_MARGINAL` vaut 1 par défaut (`info.nut:1774–1780`) et le
pré-calcul `hubAvgIncome` se lance sous ce seul booléen
(`air_planning.nut:1634–1690`). Pourtant, les **seules utilisations pour
retrancher la marge** sont sous
`AIR_HUBHUB_MARGINAL && !C121_AIR_ECONOMICS`
(`:1833–1865`). Avec l'économie C121 active par défaut, le calcul initial
ne contribue donc pas au choix/admission et se répète même sur les reprises
qui traitent peu de paires. C'est un **candidat ponctuel d'économie
d'opcodes** : conditionner le pré-calcul à `!C121_AIR_ECONOMICS`, sans
modifier la formule legacy, le MAIL15, la calibration, les admissions ni
les cadences. Aucun coût marginal réel de cet appel, gain ni neutralité
économique n'est prouvé. **Pas de correctif `.nut` ni activation** sans
isoler son exposition puis respecter la qualification opcode 20×10 de
`AGENTS.md`.

## 3. Mesures VM réutilisées hors ligne

Le profil historique C121 du 02/10
([source](opcode_profile_c121_20261002.md)) donnait environ **10,5 M
d'opcodes hub_hub sur six ans par graine**, toutes évaluations et reprises
comprises. Une série plus récente (AC-04) fournit les spans `AIR_LIGHT` de
la **graine 42 / 3 années**. Cette campagne avait déjà eu lieu : **aucun
nouveau conteneur lancé pour AC-05** (un C121 100×3 concurrent est en cours).

Analyseur reproductible :
`sweeps/analyse_ac05_hubhub_cost.py`, exécuté sur
`results/ac04_hubsite_cost_42_3y_20261011.artifacts/reference_42.log`
(SHA256 du log brut
`a73fbd1571276a8a7f1d9924009621a834d42bd79584e31826f19ce67cc580b7`).
Archive compacte des totaux :
`evidence/review/ac05_hubhub_20261011/phase_summary.json`.
Provenance du bras : diagnostic AC-04 sur `bfdb2b9`, image OpenTTDLab,
un seul bras sondé, 1/1 partie saine, pas d'A/B de politique ; le master
courant au début d'AC-05 est `3bccc8b`. La source complète et le
protocole AC-04 sont documentés dans
[AC-04](ac04_air_hub_site_resume_audit_20261011.md).

| Année | Invocations de phase | Opcodes `hub_hub` | Spans en ticks | Sorties `hub_hub_yield` |
|---|---:|---:|---:|---:|
| 1970 | 2 | 2 745 | 0 | 1 |
| 1971 | 164 | 5 125 855 | 533 | 164 |
| 1972 | 232 | 7 372 194 | 693 | 232 |
| **Total** | **398** | **12 500 794** | **1 226** | **397** |

**Interprétation bornée :** `hub_hub_yield` est un motif d'arrêt de tranche,
pas une preuve de même paire recalculée, d'échec de construction ou de boucle
infinie. Le temps et le coût sont significatifs sur cette **unique
trajectoire instrumentée**, sans démontrer le coût du pré-calcul marginal.
Les 0 enregistrements `CATALOG_COST` finaux ne sont **pas** zéro paire :
le dénominateur `air_hub_hub_pairs` par tranche n'est pas aligné sur
`AIR_LIGHT`. Le coût unitaire par paire est donc **non identifiable**
(`per_pair_opcode_cost: null`). Il serait incorrect de diviser
12 500 794 par 398 en annonçant des opcodes par paire.

## 4. Validation et décision

```powershell
python -X utf8 -m unittest -q sweeps.test_ac05_air_hub_hub_resume sweeps.test_ac04_air_hub_site_resume sweeps.test_ac03_air_new_pairs_resume sweeps.test_ac02_air_site_resume sweeps.test_air0310_2_hub_snapshot sweeps.test_c78_air_candidate_hygiene sweeps.test_c83_fixes sweeps.test_v93_small_airport sweeps.test_v133_air_build_retry sweeps.test_v134_air_p2p_saturated_hub sweeps.test_c120_air_territorial_ranking
# 82/82 OK
python -X utf8 -m unittest discover -s sweeps -p 'test_c83_local_repair.py' -q
# 6/6 OK : 88/88 au total
python -X utf8 sweeps/analyse_ac05_hubhub_cost.py results/ac04_hubsite_cost_42_3y_20261011.artifacts/reference_42.log --out evidence/review/ac05_hubhub_20261011/phase_summary.json
```

La fixture Python ne compile pas Squirrel et ne prouve pas les décisions
économiques/opcodes réels. **Clore AC-05 sur le curseur et les filtres,
maintenir sans changement le code de production.** Hypothèse de réduction
du pré-calcul V86 ouverte **pour une expérience isolée ultérieure**, seulement
si coût VM démontré et Docker libre, avec parité cible et 20×10 économique
si la variante est poursuivie. Garder le V143 rejeté et toutes les
priorités/scores existants. Aucun commit ni push.
