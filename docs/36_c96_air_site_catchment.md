# C96 — choisir le site AIR par qualité de catchment

État au 2026-09-26 : **première variante implémentée et qualifiée en 3×3 mécaniste + 5×6 causal + 20×10 ; adoptée par décision utilisateur, réglage défaut 1**.

## Hypothèse isolée

Le diagnostic B9 courant montre que le premier site constructible d'OpexAI est souvent moins
central que celui d'AAAHogEx et que le proxy de population ne représente pas le bassin physique du
site. C96 teste uniquement le premier mécanisme : **à ville, type d'aéroport, demande, avion et
économie identiques, choisir une meilleure ancre physique**.

C96 ne réactive ni V93.1 ni V93.2 et ne remplace pas `monthlyPax`. Il ne change pas la génération
des paires, `OpexAirEconomics`, C68, C84/C85, ni les contraintes physiques C83.

## Variante initiale

Réglage : `c96_air_site_catchment`, booléen, défaut **1** depuis le 2026-09-26.

Le chemin expérimental réutilise les anneaux et filtres V94 :

1. recherche `r = 4..AIR_SITE_RADIUS` par `AITileList` ;
2. mêmes filtres et même validation `AITestMode + BuildAirport` que V94 ;
3. au premier anneau contenant un site constructible, ne plus retourner immédiatement ;
4. conserver au plus **4 sites constructibles** et explorer au plus **un anneau supplémentaire** ;
5. classer ces sites par `OpexAirAirportCatchmentProduction(..., paxCargo)`, utilisé seulement
   comme **nombre relatif de tuiles productrices PASS couvertes** ;
6. à score égal, conserver le premier site de l'ordre V94.

Ce score n'est jamais converti en passagers mensuels et n'entre pas dans le profit prédit. Le but
est précisément d'isoler le placement du modèle de demande qui a rendu V93.1/V93.2 défavorables.

Quand C96 est actif, `C96_SITE` journalise pour chaque recherche aboutie l'ancre et le score du
premier site constructible V94, l'ancre et le score finalement retenus, le gain, le nombre de sites
valides examinés, les anneaux du premier et du meilleur site, leur distance au centre et le nombre
de sondes physiques. `sweeps/diag_c96_air_site.py` agrège ce signal en solo court.

Le budget partagé de sondes reste la borne dure : si le budget expire après au moins un site valide,
le meilleur site déjà vu est rendu ; sinon l'échec historique `no_site_budget` reste applicable.

## Validation prévue

- contrats statiques : réglage défaut 0, bornes de recherche, score physique seulement, chemin par
  défaut V94 intact ;
- smoke Docker 1 graine × 1 an pour compilation/exécution ;
- diagnostic court avant causalité : vérifier que C96 augmente réellement les tuiles PASS couvertes
  et relever distance au centre, centre couvert, nombre de sondes et coût en opcodes ;
- si le mécanisme est exposé, 5×6 apparié avant toute qualification économique ;
- aucun passage du défaut à 1 sans 20×10 complet et sain.

Point de vigilance : C96 augmente volontairement le nombre de validations physiques par ville. Un
gain de catchment qui consommerait trop d'opcodes ou ferait perdre des opportunités aux villes
suivantes serait un effet causal de cette première variante, pas un motif pour modifier V94.

## Validation du premier jalon

- contrats C96 + V94 + gel des réglages : **25 tests, 0 échec, 1 ignoré** ;
- régressions C83/C77/C78/V95 : **35/35** ;
- smoke Docker `c96_air_site_catchment=1`, graine 42 × 1 an : **OK**, valeur 349 197 £,
  `profit_year` 287 456 £, 15 véhicules, 17 stations ;
- télémétrie `C96_SITE` ajoutée : premier site, site choisi, score PASS, distance au centre,
  anneaux et nombre de sondes physiques.

## Mesures du 2026-09-26

### Diagnostic mécaniste 3 graines × 3 ans

`results/diag_c96_air_site_3x3_20260926.json`, graines 42/100/999, 3 workers.

- **124 recherches** C96 observées ;
- ancre changée dans **42/124 = 33,9 %** des cas ; ces 42 changements ont tous un gain de score ;
- tuiles productrices PASS couvertes : moyenne **14,58 → 15,90**, soit environ **+9,1 %** ;
- distance rectangle au centre : moyenne **6,57 → 6,22** tuiles ;
- sites valides examinés : moyenne **3,50**, médiane 4 ;
- sondes physiques : moyenne **6,94**, médiane 4 ;
- `best_ring-first_ring` : moyenne **+0,12**, médiane 0.

Le mécanisme est donc réellement exposé : C96 améliore le bassin physique choisi sans réactiver
V93 ni transformer le score de placement en demande économique.

### 5×6 apparié contre le défaut

Campagne `c96_air_site_catchment_vs_default_5x6_20260926_r1`, référence
`c96_air_site_catchment=0`, variante `=1`, 5 graines × 6 ans, 3 workers. **5/5 paires complètes**.

- `profit_year` : **+83,5 k£/an** en moyenne, médiane **+181,9 k£**, **4 V / 1 D**,
  `p_signes=0,375`, IC95 Student **[−114,9 ; +281,9] k£/an** ;
- `company_value` : ratio des moyennes **−3,37 %**, garde de valeur −5 % tenue ;
- verdict harnais : `diagnostic_only`, normal avec seulement cinq paires.

Le signal justifie un 20×10 de qualification si l'on veut envisager le défaut 1. Ce 5×6 ne suffit
pas à une adoption : le défaut reste **0**.

### 20×10 de qualification

Campagne principale `c96_air_site_catchment_vs_default_20x10_20260926_r1`, 20 graines canoniques,
10 ans, 10 workers / 10 CPU. Les 40 parties ont atteint l'horizon. Une seule paire, seed **12345**
côté variante, a été invalidée par un marqueur générique `The script died unexpectedly` apparu après
le checkpoint final 1979-12 ; le harnais a donc rendu la campagne principale `incomplete` avec
19/20 paires qualifiées.

Cette seule paire a été rejouée dans
`c96_air_site_catchment_seed12345_retry_20260926_r1` avec le **même `source_bundle_sha256`** ; le
replay est sain (`failed_runs=[]`). En remplaçant uniquement la paire invalide par ce replay, l'agrégat
20 paires donne :

- `profit_year` : **+211,3 k£/an** en moyenne ; médiane **+262,3 k£** ; **15 V / 5 D / 0 E** ;
  test exact des signes bilatéral **p=0,041389** ; IC95 Student **[+31,3 ; +391,3] k£/an** ;
- `company_value` : moyenne référence **9,029 M£**, variante **10,061 M£** ; ratio des moyennes
  **+11,43 %**, très au-dessus de la garde −5 % ;
- seed 12345 rejoué : `profit_year` **+398,5 k£/an**, `company_value` **+1,861 M£**.

La règle d'adoption `signs20` est donc satisfaite sur 20 paires saines : au moins 15 victoires,
`p<0,05`, gain moyen supérieur au seuil utile +50 k£/an et garde de valeur tenue. L'utilisateur a
ensuite décidé explicitement de l'adopter : le réglage passe à **défaut 1**.
