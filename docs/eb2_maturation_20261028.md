# EB-2 — maturation des lignes et horizon de trois ans

## Pré-enregistrement du diagnostic complémentaire (28/10/2026)

Demande utilisateur : analyser si trois ans suffisent pour voir les effets d'EB-2.
La porte A `eb2_new_station_gateA_40x3_20261028` reste `fail_primary` ;
ce diagnostic ne la remplace pas et ne constitue aucune porte d'adoption.

- Code : worktree `.worktrees/eb2-gateA`, branche `eb2-gateA`,
  SHA `f5132a52ebd646ec92870b3f002ee30ba66b8e35`, état propre avant lancement.
- Intervention : `eb2_new_station_fallback=0` contre `1`, autres défauts identiques ;
  `mode_air=0,mode_road=0,mode_water=0` dans les deux bras.
  AAAHogEx : trains seuls, même configuration que la porte A.
- Graines **42, 100, 7, 999, 2026**, reprises du diagnostic initial 5×3,
  sans sélection des perdantes de la porte A ; une répétition, 1970–1974,
  carte 256², **10 duels**, aucun essai supplémentaire prévu dans cette analyse.
- Instrumentation identique : `probes=6` (active `DECISION_LOG`), `--script-debug`,
  `--line-telemetry --line-telemetry-monthly --station-supply-telemetry`.
  Les trajectoires instrumentées ne sont pas les parties exactes de la porte A.
- Campagne neuve : `eb2_maturation_diag_v2_5x5_20261028`.
  Le premier identifiant sans `v2` a échoué avant toute partie : `decision_log`
  n'est plus un réglage déclaré sur cet arbre ; le canal est activé par `probes=6`.
  Correction technique pré-mesure, aucun résultat économique réutilisé.
- Runtime : Docker local `unix:///var/run/docker.sock`, image `openttd-lab`
  `sha256:a0e0a0727f5003532764eeaeee6b83e9ab96a7470df3c76208c6446d10b88c8c`,
  volume `openttd-lab-home`, dépôt monté par le lanceur courant.
  Profil VPS : **3 CPU, 2 Gio RAM, swap plafonné à 2 Gio, 3 workers**,
  une seule campagne. Aucun conteneur de banc actif au contrôle ; derniers runs
  GitHub consultés terminés, aucune campagne EB-2 concurrente connue.
- Hypothèse de maturation soutenue descriptivement si le delta moyen de
  `profit_year` de 1974 devient positif **et** supérieur à celui de 1972,
  avec exposition effective et contribution positive des lignes de repli mûres.
  Une ligne mûre possède au moins une année civile entière après sa construction.
  Lire `profit_this_year` au décembre suivant avec la réserve des onze mois,
  ou `profit_last_year` au décembre d'après ; ne pas additionner profits véhicule
  et profit société comme s'ils étaient équivalents.
- Mesures : tentatives uniques par graine × OD, replis puis constructions,
  dates, coût déclaré au chantier (à distinguer d'un CAPEX complet), profit
  net des véhicules présents par groupe, trésorerie/prêt et autres constructions.
  Santé et couverture contrôlées avant interprétation.
- Paramètres du verdict mécanique : `gain_short`, seuil 4 %, garde valeur 5 %,
  **échantillon requis 40×5** : les 5×5 restent `diagnostic_only`.
  Aucune porte B ni changement de défaut autorisé par ce diagnostic.

## Porte A existante : l'attente ne suffit pas à expliquer les observations

Campagne `eb2_new_station_gateA_40x3_20261028`, même SHA et même bundle source
`d81de837575b6d61c4e9856d2aaa79ba2ba92c11c5bc3880e980df28838aabaf`.
40/40 paires complètes, couverture complète, 80 jeux `complete`, aucun
`failed_runs`. Les deux IA jouent en rail seul. Cette porte utilise `probes=2`,
sans télémétrie de ligne et avec journaux moteur vides : aucune attribution
précise des profits aux lignes EB-2 n'est possible dans ces parties.

| Cliché | Δ profit annuel Opex (£/an) | Δ dernier trimestre clos (£) |
|---|---:|---:|
| Décembre 1970 | −71,93 | +48,20 |
| Décembre 1971 | −3 623,33 | −1 077,18 |
| Mars 1972 | −7 052,63 | −3 059,38 |
| Juin 1972 | −12 742,43 | −6 632,60 |
| Septembre 1972 | −16 545,28 | −5 776,13 |
| Décembre 1972 | **−19 101,75** | **−3 633,65** |

La première année est incomplète et n'est pas annualisée. Les clichés mensuels
ne sont pas des observations indépendantes ; les profits annuels glissants se
recouvrent. Les clichés de décembre n'intègrent pas le trimestre courant.
Le dernier trimestre montre une réduction du déficit, mais reste négatif ;
la moyenne annuelle ne montre pas encore de retournement.

À l'année terminale : −1,78 % du témoin, médiane 0, 12V/15D/13E,
Wilcoxon p=0,324220, IC95 bootstrap [−38 690,95 ; −2 016,68] £/an,
valeur −0,6245 % (garde tenue), verdict brut **`fail_primary`**.
L'IC et Wilcoxon répondent à des critères différents ; ne pas présenter
Wilcoxon comme une preuve de perte significative.

### Ancienneté de la divergence

Sur les six métriques `profit_year`, `profit`, `money`, `current_loan`,
`primary_vehicles`, `n_stations`, la première divergence mensuelle apparaît
avant 1972 pour **11 graines**, et pendant 1972 pour **19** ; les dix autres
ne divergent pas sur ces métriques. Ce classement est descriptif, a posteriori,
et **ne date ni un repli ni une construction**.

Les 11 trajectoires modifiées avant 1972 contribuent à **−20 110,08 £/an**
sur la moyenne globale (somme de leurs deltas divisée par 40) ; les 19 tardives
à **+1 008,33 £/an**. Le déficit n'est donc pas principalement porté par
les divergences les plus récentes. Ce constat justifie de rechercher le
coût d'opportunité et la productivité des nouveaux projets, tout en laissant
ouverte la possibilité d'une récupération après 1972.

### Constructions et calcul observés

Panneaux conservés au cliché terminal, **pas journal exhaustif de tentatives
uniques** ; les clés n'identifient ni le cargo ni l'OD.

| Année | `OK` référence → EB-2 | `SITEAB` référence → EB-2 |
|---|---:|---:|
| 1970 | 384 → 385 | 12 → 0 |
| 1971 | 368 → 369 | 11 → 0 |
| 1972 | 407 → 392 | 66 → 0 |
| Total | **1 159 → 1 146** | **89 → 0** |

Les refus disparaissent dans les signes observés, mais les constructions
réussies nettes n'augmentent pas. À décembre 1972 : **−0,45 véhicule primaire**,
**−0,375 gare** et **+5 523,55 £ de trésorerie** en moyenne, sans différence
moyenne de prêt. Il n'y a pas, à ce cliché, de signature d'un stock net
supplémentaire de flotte/infrastructure en attente de maturation. Cela
n'exclut ni une substitution vers du fret ni des dépenses intra-annuelles.

Les sommes d'opcodes OR/OB appariés une fois sont 1,236 G contre 1,229 G,
avec respectivement 28 et 25 panneaux OR non appariables/ambigus. La clé
unique dans le cliché reste un proxy ; ces sommes ne couvrent pas tout le CPU
et ne prouvent ni gain global ni surcoût causal d'EB-2. Les signes `SITEAB`
appariés du témoin ne pèsent que **118 868 opcodes** : éliminer ces refus
pré-A* ne représente pas en soi une réserve majeure de calcul.

Reproduction :

```bash
python3 sweeps/diag_eb2_maturation.py \
  .worktrees/eb2-gateA/results/eb2_new_station_gateA_40x3_20261028.json \
  --out results/eb2_maturation_gateA_analysis_20261028.json
```

Le lecteur reprend les métriques déjà décodées par le harnais courant,
rejette les doublons de clichés et recoupe sa moyenne terminale avec celle
du comparatif. Cas synthétiques vérifiés : métriques absentes conservées,
panneaux répétés entre mois non additionnés, doublon rejeté.

## Diagnostic complémentaire cinq ans

**Contrôle du diagnostic initial `diag_eb2_railseul_5x3_20261027` :**
son JSON porte `aaahogex_settings=[]`. Opex seul est contraint au rail ;
AAAHogEx conserve ses modes par défaut. Le +27 847,40 £/an de cette ancienne
exposition ne se compare donc pas directement au 40×3 rail seul des deux IA.
Le code et les sondes diffèrent aussi. Les dates de ses constructions donnent
des exemples de mécanisme, pas la cause des trajectoires de la porte A.
Le diagnostic complémentaire fixe explicitement les cinq réglages AAAHogEx
dans le manifeste, et réutilise exactement le bundle de la porte A.

### Résultat : effet tardif plausible, gain non qualifié

Campagne terminée : **10/10 duels, 5/5 paires complètes**, couverture des
métriques complète, aucun `failed_runs`, horizon atteint dans tous les bras.
Six statuts de jeu `complete`, quatre `stagnation_suspect` (diagnostic
d'activité sans troncature, conservés dans l'analyse). Les deux politiques
et AAAHogEx sont bien en rail seul. Bundle identique à la porte A, manifeste
SHA256 `1294915cd1fb6e2551ae401ca513a624eafdbbdc7aed2ee46cf911496006a114`.
Les sommes de contrôle du JSON et du JSONL sont enregistrées par le lecteur.

| Cliché | Profit témoin moyen | Profit EB-2 moyen | Δ (£/an) |
|---|---:|---:|---:|
| Décembre 1970 | 203 356,20 | 203 155,80 | −200,40 |
| Décembre 1971 | 684 347,40 | 678 002,40 | −6 345,00 |
| Décembre 1972 | 1 058 724,00 | 1 039 439,80 | **−19 284,20** |
| Décembre 1973 | 1 427 702,20 | 1 438 187,80 | **+10 485,60** |
| Décembre 1974 | 1 538 819,20 | 1 577 142,80 | **+38 323,60** |

À cinq ans : **+2,49 %**, médiane +21 031 £/an, 3V/2D,
Wilcoxon p=0,4375, IC95 bootstrap **[−9 579,20 ; +106 691,80] £/an**,
valeur **+4,1436 %**, garde tenue. Bootstrap : 20 000, graine 0.
Verdict brut **`diagnostic_only`**, échantillon d'adoption incomplet (5/40).
Même la moyenne descriptive est sous le seuil de 4 % pré-enregistré.

| Graine | Δ à trois ans | Δ à quatre ans | Δ à cinq ans |
|---|---:|---:|---:|
| 42 | +344 | +28 647 | −24 698 |
| 100 | −114 246 | −145 321 | +21 031 |
| 7 | 0 | +34 647 | +35 701 |
| 999 | +17 481 | +108 918 | +169 087 |
| 2026 | 0 | +25 537 | −9 503 |

Les cinq graines sont celles décidées avant la mesure, sans recherche des
perdantes du 40×3. La graine 999 porte **169 087 des 191 618 £/an** de
delta total. Ce petit échantillon ne représente donc pas une preuve robuste
de rattrapage. Il répond néanmoins à la question du délai : un déficit à
trois ans peut devenir positif à cinq ans sur un protocole constant.

### Le mécanisme se prolonge après trois ans

Les journaux donnent **27 déclenchements**, sur **23 OD graine × source ×
destination distinctes** :

- **17 constructions**, dont une le 16/12/1974, après le dernier cliché ;
- cinq arrêts explicites `cash_at_build` ;
- cinq tentatives finales échouées : 3 `TRKFAIL`, 1 `ABND`, 1 `STNFAIL`.

Le compteur de replis n'est donc pas assimilé à un compteur de constructions.
`PROJECT_DISCARD reason=search_in_progress` est une suspension intermédiaire,
pas une issue d'échec : l'appariement attend le `RAIL_ATTEMPT` final.

Les constructions se répartissent en **2 en 1970, 0 en 1971, 3 en 1972,
8 en 1973 et 4 en 1974**. Seulement cinq existent avant la fin de la porte
à trois ans ; le mécanisme n'est cependant pas inerte pendant cette porte.

Sur les **13 groupes bâtis avant 1974**, les profits nets des véhicules
encore présents au 01/12/1974 sont tous positifs, total **410 930,51 £**
sur les cinq cartes (cumul janvier–novembre 1974, non annualisé).
Il s'agit de correspondances géométriques : un seul groupe rail avec chaque
extrémité à ≤16 tuiles de l'OD journalisée au premier cliché correspondant,
puis suivi de la même clé locale de gares. Les 16 constructions antérieures
au dernier cliché trouvent chacune une correspondance unique ; celle du
16/12 n'est pas observable. Ce n'est pas une identité NoAI exacte.

**Point décisif :** les cinq premiers groupes passent de **133 471,52 £**
en janvier–novembre 1973 à **133 497,07 £** en janvier–novembre 1974,
soit presque le même montant. Les huit groupes bâtis en 1973 passent de
**39 427,65 £** (année de lancement partielle) à **277 433,44 £** en 1974.
Le retournement est donc compatible surtout avec **de nouvelles conversions
tardives, suivies de leur maturation**, plutôt qu'avec la seule montée en
charge continue des cinq premières lignes. Les remplacements de véhicules
et la disparition des véhicules vendus empêchent de traiter ces sommes
comme un compte de résultat exhaustif de ligne.

Par exemple, graine 100 : la liaison charbon `52591→29140`, bâtie le
21/08/1973, passe de −916,82 £ au cliché de décembre 1973 à +64 370,18 £
au cliché de décembre 1974. Les deux sorties bois de novembre 1973,
`43817→58979` et `50491→58979`, passent de petits résultats négatifs à
+30 873,18 £ et +29 024,18 £. Elles n'existaient pas à trois ans.

À l'inverse, graine 2026 : les deux replis charbon bâtis en 1973 rapportent
ensemble **94 436,36 £** en janvier–novembre 1974, mais le delta société
est **−9 503 £/an**. Les recettes de ces nouveaux services ne représentent
donc pas intégralement du gain additionnel : effets sur les autres services,
concurrence, investissement et rythme restent à apparier causalement.
Ne pas soustraire directement ces deux métriques aux périmètres différents.

### Fait nouveau exploitable : le financement retarde des replis bâtissables

Les cinq arrêts `cash_at_build` sont sur la graine 100 :

| OD | Dates des refus de caisse | Construction ultérieure |
|---|---|---|
| `9424→29140` | 07/07/1970, 17/12/1971, 31/10/1972 | **26/01/1974**, coût 66 003 £ |
| `26668→29140` | 28/12/1970 | Pas de construction EB-2 associée observée |
| `52591→29140` | 17/11/1972 | **21/08/1973**, coût 93 445 £ |

Les journaux montrent un tracé trouvé avant le rejet `cash_at_build`.
Un repli physique existe donc parfois longtemps avant son financement.
La première OD finit par rapporter +20 249,71 £ au cliché de décembre 1974,
la seconde OD finalement bâtie +64 370,18 £. Ces exemples ne prouvent pas
qu'il aurait été préférable de les financer plus tôt : leur projet évincé
doit être évalué. Ils fournissent toutefois une voie de travail précise,
**EB-2 avec EB-4 : devis de gare indépendante et financement effectif avant
engagement**, puis classement face aux autres projets finançables.

### Limites et décision de travail

- 1 200 clichés de télémétrie valides ; 25 occurrences mensuelles de véhicules
  à ordres non résolus (`unresolved_order_list`) dans l'ensemble des deux IA,
  **aucune au cliché terminal**. Ce ne sont pas 25 véhicules distincts et
  ils ne sont pas convertis en lignes à profit nul.
- Les coûts des `RAIL_BUILD` sont recoupés avec `RAIL_ATTEMPT actual` quand
  présents ; ils ne couvrent pas tous les investissements ultérieurs,
  renouvellements, véhicules disparus ni toute l'histoire de trésorerie.
- Aucun appariement contrefactuel exact du capital déplacé n'est établi.
  Le +38,3 k£ ne peut être attribué exclusivement aux 13 groupes mûrs.
- **Hypothèse de délai soutenue descriptivement** selon le critère décidé :
  delta cinq ans positif et supérieur à trois ans, exposition réelle,
  contributions des groupes mûrs positives. Aucun gain statistiquement
  qualifié ; le 40×3 reste `fail_primary` et le défaut reste 0.
- Investissement conseillé : analyser/corriger le passage du devis de
  rattachement au devis de gare neuve et la caisse réellement disponible,
  avec comparaison des alternatives au même instant. Les seules recherches
  de quai supplémentaires ne répondent pas aux cinq rejets de caisse.
  Une future porte cinq ans demande un protocole distinct décidé avant
  lancement ; aucune relance de porte ni porte B dans cette mission.

Reproduction du complément :

```bash
python3 sweeps/diag_eb2_maturation.py \
  .worktrees/eb2-gateA/results/eb2_maturation_diag_v2_5x5_20261028.json \
  --out results/eb2_maturation_diag_analysis_20261028.json
```

Les JSON/JSONL, manifeste, bundle, logs et sortie du lanceur sont conservés
dans `.worktrees/eb2-gateA/results/` sous le préfixe de campagne exact.
Les analyses compactes sont sous `results/eb2_maturation_*_analysis_20261028.json`.
