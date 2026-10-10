# AIR — diagnostic de marge résiduelle multi-graines (8 octobre 2026)

## Protocole et décision

**Verdict : devis V126 conservé OFF ; aucune marge nouvelle validée.**
Campagne diagnostique `air_site_quote_residual_6x3_20261008_r1`, 6 graines
pré-enregistrées (42, 100, 999, 1234, 5678, 2026) × 3 ans, 12 duels
OpexAI/AAAHogEx, **12/12 complets et sains**. Le bundle figé
`406219ec402ce1547a382008ae91c2e0fbd758a33d6fbe118588af1d7fe6f2de`
et son manifeste
`2504c6cc42c088576d274fca85d96949643483604d22e318eae7c31845de1686`
incluent les modifications locales présentes au lancement, sans réécrire
les travaux concurrents. Image `openttd-lab:latest` sha256
`f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Docker local : 10 CPU, 8 Gio RAM/swap, 10 workers, une campagne à la fois.

Référence `OpexAI[air_site_cost_quote=0,probe_air_finance_margin=1]`, variante
`OpexAI[air_site_cost_quote=1,probe_air_finance_margin=1]`,
`air_site_cost_margin_pct=0` commun, tous autres réglages aux défauts.
`--script-debug` identique aux deux bras. Politique du harnais : `gain_short`,
seuil 4 % du profit `profit_year` de référence, garde de valeur −5 %, mais
**6 graines ne remplacent pas la porte A obligatoire de 40**. Verdict brut
`diagnostic_only`, sans permission d'adoption ni passage en porte B.

## Économie OpexAI

| Graine | Delta `profit_year` variante−référence fin 1972 | Delta slots AIR Opex en 1970 | Delta slots AIR Opex fin 1972 |
|---|---:|---:|---:|
| 42 | −165 538 £/an | +4 | 0 |
| 100 | +79 987 £/an | +1 | +1 |
| 999 | +52 362 £/an | +1 | 0 |
| 1234 | −109 582 £/an | 0 | 0 |
| 5678 | +430 880 £/an | +2 | 0 |
| 2026 | −712 483 £/an | −5 | −4 |

Moyenne **−70 729 £/an**, médiane −28 610, V/D/E=3/3/0,
Wilcoxon bilatéral p=0,6875 ; IC95 bootstrap moyenne
[−361 773 ; +187 743] £/an, bootstrap 20 000 tirages/graine 0.
Valeur de compagnie : ratio des moyennes **−0,81 %**.
Le smoke à un an de la graine 42 donnait +58 662 £/an,
mais cette même graine perd −165 538 £/an au terme des trois ans :
la dynamique de financement modifie les projets et leurs trajectoires.
La forte perte à la graine 2026 ne prouve pas seule une causalité précise.
Un échantillon de six graines ne permet de conclure ni gain ni régression
statistiquement établie ; la hausse de construction ne suffit pas à qualifier
une politique économique.

## Comptabilité des chantiers, par bras et année

La sonde `AIR_FINANCE_TRY` et le décodeur dédié
`sweeps/analyse_air_site_residual.py` produisent :

| Sur 6 graines / 3 ans | Référence devis OFF | Variante devis ON |
|---|---:|---:|
| Événements TRY | 630 | 344 |
| Routes AIR construites (`built`) | 219 | 230 |
| Construites à 0 / 1 / 2 aéroports neufs | 65 / 100 / 54 | 81 / 93 / 56 |
| Échecs `failed` | 62 | 58 |
| Échecs à dépenses `actual` positives | 30 | 28 |
| Dépenses d'échec comptabilisées | 462 266 £ | 271 538 £ |
| Refus `refused_*` journalisés | 349 | 56 |
| Cash sous la réserve avant recette (couverture connue) | 11/194 | 4/212 |
| `built` avec devis dans la sonde | 219 | 230 |
| Événements à devis impossible | 0 | 0 |

Par année, variantes vs référence : constructions 1970 **48 vs 45**,
1971 **112 vs 113**, 1972 **70 vs 61** ; coût comptabilisé des échecs
1970 **102 002 vs 200 460 £**, 1971 **97 194 vs 178 604 £**, 1972
**72 342 vs 83 202 £**. Les 349/56 refus peuvent être des candidats
réexaminés et des rangs d'une même passe : **pas 349/56 projets uniques**.
`built` désigne une construction de ligne (0 nouveaux aéroports possible
en cas de hub→hub), pas le nombre d'aéroports physiques posés.

Un `actual` d'échec correspond aux commandes comptabilisées au chantier ;
rollback différé, reprises sur orphelins, valeurs récupérées et capital
immobilisé ne sont pas isolés dans ce chiffre. Les 58 événements `failed`
de la variante ne signifient pas 58 dépenses positives (28 seulement).
Les dénominateurs des brèches comptent uniquement les recettes pour lesquelles
`cash_min` et `reserve` sont connus. Variantes et références choisissent
des projets différents : les totaux d'échecs et de financement ne constituent
pas des effets causaux sur des chantiers appariés individuellement.

## Devis réel, bornes de risque et opcodes

Les **149 succès variante avec au moins un nouvel aéroport** ont un devis
V126 renseigné, sans `-1`. L'écart `nivellement réel − devis` a p90 et maximum
**0 £**, compatible avec un devis plutôt conservateur *sur ces succès*.
Le défrichage/les surcoûts au moment de poser l'aéroport peuvent atteindre
**12 375 £** par extrémité. Le résidu après prix catalogue, devis de
nivellement et arrêts joints **modélisés** a un p90 de **−2 011 £** et un
maximum de **+7 515 £** ; **7/149** succès dépassent le plancher actuel du
prototype à **2 000 £**. Ventilation : N=1 **4/93** succès, maximum
**+7 515 £** ; N=2 **3/56**, maximum **+4 458 £**.

À titre descriptif, le pourcentage de `coût_site` qui aurait couvert
**uniquement** les dépassements observés de ces succès au-delà de 2 000 £
atteint **34,1 % pour N=1** et **7,6 % pour N=2**. Cela **n'est pas** une
proposition de régler `air_site_cost_margin_pct` à ces valeurs : pas de
quantile fiable de risque total, ni garantie hors échantillon, ni prise en
compte de pertes d'échec/rollback et du délai de premier revenu. Les
réglages prototypes restent 0 ; en particulier l'absence de `quote_fail` dans
le jeu ne dispense pas de son test de contrat.

Le forfait adopté dans le prototype de 2 × 2 250 £ par nouvel aéroport
est intentionnellement élevé au regard des arrêts joints observés dans cet
échantillon (coût **par aéroport** dans un projet réussi, maximum calculé
**371 £**, moyennes de projets). La surestimation explique les résidus
souvent négatifs et ajoute un coût d'opportunité possible au budget de
sélection, à mesurer plutôt qu'à corriger par tâtonnement.

Les journaux `AIR_PLAN_PERF` fournissent des compteurs de scans pour chaque
bras, mais les entrées et le nombre de scans divergent ensuite. Leur somme
ne mesure donc pas une différence **causale** de coût en opcodes à charge
identique. Le premier scan comparable du smoke r3 :
`c121_static_ops` 41 584→42 000 (+416), `total_ops`
1 248 937→1 246 609 (−2 328). Le coût d'ensemble à décisions égales
et son bénéfice opcode restent indémontrés.

Sur le 6×3, les premiers scans ne peuvent être comparés qu'à entrées
homogènes (`c121_calls`, `sites`, `combos`, `plans`, évaluations moteur,
hits/misses d'extrémités, coût site). Deux graines seulement ont ces
compteurs identiques : **42 (+416 opcodes C121 statiques)** et
**5678 (+709)** pour le devis ON. Les quatre autres divergent déjà au
premier scan ; aucun delta de campagne à décisions identiques n'est établi.

## Reproductibilité, limitations et décision

Rapport brut du harnais :
`results/air_site_quote_residual_6x3_20261008_r1.json`, `.jsonl`,
`.manifest.json`, dossier `_engine/`, et bundle figé. Rapport détaillé par
**bras/graine/année/N=0,1,2** :
`results/air_site_quote_residual_6x3_20261008_r1_breakdown.json`.
Décodeur : `sweeps/analyse_air_site_residual.py`, testé par
`sweeps/test_analyse_air_site_residual.py` ; réutilise
`sweeps/parse_air_finance_margin.py`, conserve les valeurs inconnues.
L'absence d'identifiant immuable de projet interdit un appariement exact
des refus et des premières recettes. Les remboursements de rollback sont
seulement inclus dans certains comptes `actual`, sans ventilation propre.
La sélection est modifiée conjointement par le devis et la baisse de marge
de 12/30 k£ à 2 k£ : **l'effet économique de ces deux mécanismes n'est pas
identifié séparément** par cette campagne.

**Décision :** conserver `air_site_cost_quote=0`,
`air_site_cost_margin_pct=0` ; conserver les règles historiques de
30/12/2 k£. Aucune adoption ni porte V102 A/B sur la variante testée.
Si le chantier continue, isoler les conséquences de devis seul sur le
capital/les classements et la marge résiduelle, documenter les pertes nettes
de rollback et les refus par projet unique, puis préparer une règle de
protection vérifiable avant un vrai essai de qualification.
