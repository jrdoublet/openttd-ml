# Nuit 75 % — pré-enregistrement des variantes comportementales (25/10/2026)

## Clôture de la nuit et décision du 25 octobre (mise à jour)

**Vérification finale après adoption (20×10, 1970–1979) :** la campagne
`nuit75_multicargo_default_20x10_seedsfix_20261025` est complète et
saine (20/20 paires, 40 duels, 80 compagnies, manifeste SHA conforme),
ancien défaut OFF contre multicargo ON sur le même bundle figé. La règle
`non_erosion` rend **`pass`** : Δ moyen privé Opex **+76 417,10 £/an**,
médiane +43 630,50, 11V/9D, Wilcoxon p=0,621513,
IC95 bootstrap [−158 453,90 ; +318 370,15] £/an,
valeur compagnie **+5,63979 %** (garde −5 % satisfaite). Ratios
Opex/AAA de décembre 1979, ratio des moyennes / médiane appariée :
OFF **58,9786 % / 59,7217 %**, ON **58,4889 % / 61,1192 %**.
Gain privé moyen Opex descriptif, sans significativité ; objectif
75 % **non atteint**. Il s'agit du comparatif explicitement commandé
après adoption, aucune porte A historique n'est requalifiée. Analyse
reproductible : `sweeps/analyse_nuit75_multicargo_default_20x10.py`,
preuve `results/nuit75_multicargo_default_20x10_seedsfix_20261025_analysis.json`.

La baseline 1970–1979 sur `master 83e436cc` reste **56,5519 %** de ratio des
profits moyens Opex/AAAHogEx et **58,9112 %** de médiane des vingt ratios par
graine. Les six variantes ont ensuite été revérifiées en portes **A40×5
multimodales** (1970–1974, 256², 40 paires saines chacune, même bundle OFF/ON,
`gain_short`, seuil +4 %, Wilcoxon exact bilatéral p<0,05, IC95 bootstrap
bas >0 et garde de valeur −5 %). Toutes les portes sont `fail_primary` :

| Variante ON (contre 0) | Δ Opex £/an | V/D/E | p Wilcoxon | IC95 bootstrap £/an | Valeur | A |
|---|---:|---:|---:|---|---:|---|
| N75-CAP `n75_freight_capacity=1` | −9 137,625 | 21/18/1 | 0,928548 | [−80 415,725 ; +61 403,3] | −0,177 % | `fail_primary` |
| GOOD `good_source_rail_join=1` | −40 727,5 | 13/27/0 | 0,091824 | [−101 369,38 ; +21 796,25] | −2,176 % | `fail_primary` |
| AIR-GROW corrigé `air_grow_marginal=2` | −23 434,75 | 19/21/0 | 0,509914 | [−100 394,5 ; +54 630,7] | −0,347 % | `fail_primary` |
| C75-REFUND `n75_c75_refund=2` | −11 117,975 | 13/12/15 | 0,957845 | [−59 567 ; +33 388,9] | −0,536 % | `fail_primary` |
| AIR TRUE QUOTE `n75_air_true_quote=2` | +6 856,725 | 26/14/0 | 0,397424 | [−96 318,1 ; +102 589,875] | +0,252 % | `fail_primary` |
| MULTICARGO `n75_multi_cargo=2` | **+91 191,925** | 24/16/0 | 0,138680 | [−16 568,375 ; +197 955,75] | +2,646 % | `fail_primary` |

La file `results/nuit75_newformat_queue_20261025.jsonl` s'est terminée avec
six verdicts A, zéro A `pass`, zéro B conditionnelle. Les audits indépendants
confirment manifestes/SHA, 40 paires/80 duels/160 bilans par A, absence
d'erreur script dans les bilans, et logs moteur vides. Les ratios à cette
porte se rapportent à **1974**, sans preuve de 75 % à dix ans ; pour MULTICARGO
OFF ratio des moyennes/médiane **91,9412 % / 96,5730 %**, ON **96,7286 % /
99,6565 %**. Un A40×10 GOOD antérieur de 1979 avait `fail_primary` malgré
+127 819,45 £/an et 28V/12D (p=0,05481, seuil +170 929,1 £/an), ratios
OFF 56,4832 % / 55,3267 % et ON 59,1088 % / 60,0331 %.

Les diagnostics passifs FRONT-PAX-2 (9 810 évaluations de paires sous 200,
ni projets ni gains prouvés) et FREIGHT-ATTRITION (attrition du fret long,
observations non causales) sont consignés avec leurs limites dans le
[journal](journaux/journal_2026-10-24_nuit_75pct.md). Les expositions GOOD,
N75-CAP, AIR-GROW corrigé, C75-REFUND, le contournement C75 précoce,
TRUE QUOTE et MULTICARGO, ainsi que les anciennes portes 40×3, figurent au
même endroit. L'utilisateur avait approuvé A40×10 pour les leviers
postérieurs à 1973, puis A40×5 multimodal ou rail seul et A40×3 rail seul ;
aucun résultat d'une porte n'a été substitué rétroactivement à un autre.

**Décision utilisateur ultérieure :** adopter **`n75_multi_cargo=2` par
défaut aux quatre difficultés**, malgré `fail_primary`, documenter et publier
les résultats de la nuit, puis exécuter explicitement un **nouveau 20×10
comparatif** ON/OFF avec Wilcoxon, IC95 et garde −5 %. Cette décision
modifie le défaut ; elle **ne change ni les verdicts ni le protocole V102**.
Voir [rapport multicargo](nuit75_multi_cargo_20261025.md). Les sections
ci-dessous conservent le **pré-enregistrement historique initial**.

## Référence figée et périmètre

- Objectif utilisateur : atteindre au moins 75 % du profit AAAHogEx, ratio des profits moyens ou médiane des ratios par graine appariée, sur 20×10 ou 40×10 ; départ 1970, 256×256.
- Référence master `83e436cc3db35ff18efb685ace4f97eb569f77b1` : 20×10 complet, moyenne Opex `4 122 708,10 £/an`, AAA `7 290 134,25 £/an`, ratio des moyennes `56,5519 %`, médiane des ratios appariés `58,9112 %`, déficit privé vers 75 % `1 344 892,59 £/an` à AAA inchangé. La référence ne doit pas être relancée sans justification.
- Deux modifications comportementales indépendantes dans deux worktrees détachés issus du même HEAD : `.worktrees/nuit75-good-source-variant` et `.worktrees/nuit75-freight-capacity-variant`. Pas de modification des anciens diagnostics ; aucun changement de réglage par défaut, commit, push ou merge.
- Les 5×10 GOOD instrumentés sont des références non appariées à master : leurs ratios ne sont pas des uplifts. Les 33 usines échantillonnées et les 9 lignes GOOD matures ne garantissent ni faisabilité, ni profit marginal.

## Interventions isolées à vérifier avant smoke

1. GOOD sortant d'une usine avec station ferroviaire Opex utilisée pour des intrants non-GOOD : contrat source A strict, vraie station existante et capture GOOD, destination B non desservie, sites et coûts réels, réservation financière et rollback. Pas de simple levée de `origin_served`, pas de rejeu V233.
2. Renfort de ligne ferroviaire fret déjà rentable et durablement saturée : nouvelle politique sélectionnant un renfort physique marginal réellement admissible, sans supprimer les gardes V284 de traction, vitesse, voie/boucles et rollback ; arbitrer dépenses avec AIR/V252. V284 existant reste à son défaut courant 3.

Identifiants des options expérimentales retenus pour la revue et les bancs :

- GOOD : `good_source_rail_join=0` contre `good_source_rail_join=1` (policy ID `n75goodsource`).
- Capacité fret : `n75_freight_capacity=0` contre `n75_freight_capacity=1` (policy ID `n75freightcap`).

Les empreintes de code, l'intégrité des tests et les critères d'exposition seront figés et ajoutés **avant** une campagne économique. OFF doit rester le comportement courant dans les quatre difficultés. Toute instrumentation d'exposition est différente d'une preuve de profit causal.

## Protocoles V102 décidés avant résultat

- Smoke pour chaque changement Squirrel : un duel apparié à `--years 1 --seeds 42`, référence `OpexAI[réglage=0]`, variante `OpexAI[réglage=1]`, `--decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 40 --required-years 3`, hors adoption. Vérifier deux compagnies, santé technique et chemin réellement exercé, éventuellement par diagnostic ciblé plus tardif séparé si le mécanisme est dormant la première année.
- Porte A **40 graines canoniques × 3 ans**, règle **`gain_short`**, métrique primaire profit terminal privé Opex variante moins référence, Wilcoxon bilatéral exact `p < 0,05`, IC95 bootstrap inférieur `> 0`, delta moyen `>= 4 %` du profit moyen de référence, et perte maximale de valeur société `5 %`.
- Porte B **20 graines canoniques × 10 ans**, uniquement après porte A complète, saine et `pass` ; règle **`non_erosion`**, IC95 bootstrap supérieur `>= 0`, garde de valeur `5 %`. Le passage B ne prouve pas en soi un gain économique à 10 ans.
- Les deux bras de chaque porte viennent du **même worktree et bundle**, avec uniquement le nouveau réglage différent. Horizon 1970, 256² ; `--repeats 1 --primary-metric profit_year --cpus 10 --memory 8g --max-workers 9 --probes 2`; télémétrie supplémentaire seulement pour exposition exploratoire sur les deux bras de manière explicite.
- Graine canonique A : `42 100 7 999 2026 1 17 73 314 512 1024 1337 4096 8191 12345 54321 65537 123456 424242 8675309 423960 613553 515222 781335 375172 999533 442018 746035 455216 230185 706990 983759 802204 232037 723002 313707 701256 292001 841478 59527`. B : les vingt premières.
- Un Docker maximum, contrôle `docker ps` juste avant chaque lancement ; pas de seuil modifié après inspection des résultats ; verdict `fail` ou erreur technique termine la séquence en le documentant, sans adoption.

## Exécutions vérifiées (en cours)

### Contrats et smokes 1×1

- GOOD : tests ciblés **108/108** OK, régénération PO01C synchronisée, `git diff --check` sans erreur (seul warning CRLF) ; worktree détaché conservé, code figé. Duel graine42, année1970, `nuit75_goodsource_smoke_1x1_20261025` : **2/2 parties saines**, différence de profit Opex ON−OFF **0 £/an**, pas de candidat GOOD (horizon trop court). Bundle `4da09e927f64bc110ee2da6752131226a2ab9fdd792e0670f2b80bcc1790b808`, manifeste `a516740d7c55fa2d924e1046657ff9870808d3c3670d1c8101d359bd80ee2b80`.
- N75-CAP : tests ciblés spécifiques et de compatibilité V284/PO01C/C77 verts, garde V284 historique différée à 1973 indépendamment du nouveau chemin N75 ouvert en 1972. Duel graine42, année1970, `nuit75_freightcap_smoke_1x1_20261025` : **2/2 parties saines**, delta ON−OFF **0 £/an** (attendu), aucun renfort à cet âge. Bundle `7814fbdcfcc9a93a8dffc2b0a5b4e996ae238d134d69945f0f3dc69913c2ddcc`, manifeste `ef31b4332e376feeaab0de02d65788713687b911ab4dadc44a59d9553f117497`.

### Exposition tardive GOOD (un seul monde : jamais une porte)

`nuit75_goodsource_exposure_seed100_1x10_20261025`, seed100, 1970–1979, référence OFF vs variante ON, même bundle `4da09e...`, manifeste `1a434d78d1817d6b3a2c9e96d454a19646c212814a929d42c01baf8ff2c9439b`, sondes activées symétriquement (`probes=258`). **2/2 parties saines.** En décembre1979 : **+838 426 £/an** de profit privé Opex dans la variante, valeur de compagnie **+16,98 %**, Opex ON `2 464 872 £/an` contre AAA `6 714 980 £/an` (seulement **36,71 %** du profit d'AAA sur ce monde). Verdict V102 `diagnostic_only` : un échantillon, ni preuve statistique, ni atteinte 75 %.

Le nouveau chemin produit **28 événements `GOOD_SOURCE_RESULT`**, dont **6 constructions effectives sur 6 couples source/destination distincts** avec `actual StationID == join StationID` (2 en 1972, 1 en 1973, 1 en 1977, 2 en 1979). Échecs 22 : `SITEAB=16`, `SITEB=3`, `STNFAIL=1`, `TRKFAIL=1`, `ABND=1`. Les événements `GOOD_SOURCE_KEEP` (3 328 répétitions de génération) ne sont pas des usines ou opportunités indépendantes, ni des profits acquis. Aucun rattachement de gare nouvelle à la place de la gare source n'est compté comme succès.

### Portes de qualification

- GOOD : porte A `nuit75_goodsource_porteA_40x3_20261025`, bundle `4da09e...`, manifeste `9021c1f90b718facfa426c5000602342d03e5e5fb8e580ebe67d4d03cadc4549`, **40/40 paires et 80/80 compagnies terminées**. Delta profit moyen Opex **+4 262,075 £/an**, médiane **0**, V/D/E **12/13/15**, p exact Wilcoxon bilatéral **0,9789153**, IC95 bootstrap **[−11 334,4 ; +22 239,825] £/an**, seuil 4 % **+89 549,093 £/an** ; company_value ratio des moyennes `1,004634` (+0,4634 %) : garde −5 % satisfaite. **Verdict V102 `fail_primary`** : pas de significativité, IC95 bas non positif, seuil de gain non atteint. **Porte B GOOD NON LANCÉE**, puisqu'elle exige A `pass`. Aucun changement de défaut. Le gain de +838,4 k£ en seed100 10 ans reste un diagnostic tardif isolé et ne justifie pas adoption.
- N75-CAP : smoke terminé. Diagnostic d'exposition tardive `nuit75_freightcap_exposure_seed100_1x10_20261025`, bundle `7814fbdcfcc9a93a8dffc2b0a5b4e996ae238d134d69945f0f3dc69913c2ddcc`, manifeste `387fd3e177a8f48bf04a7c5b950a5b153adb1cab9a910c1b0dc8b3517757ecd0` : **1/1 paire complète, diagnostic_only**. À dix ans : Opex ON `3 170 057 £/an`, AAA ON `5 155 555 £/an`, ratio ON `61,49 %`; delta privé ON−OFF **−190 538 £/an**, ratio de valeur moyenne **1,011207** (+1,12 %). Dans le journal ON : **aucun** événement `N75CAP action=screen/pick/done` (0/0/0), donc aucune nouvelle seconde rame construite par le chemin spécifique N75 pour cette graine. La différence économique entre bras ne démontre donc pas de bénéfice du renfort N75 ; le bruit de trajectoire et les coûts d'opcodes restent possibles. Pas de qualification sur une graine.
- N75-CAP : porte A `nuit75_freightcap_porteA_40x3_20261025` après libération du Docker GOOD, bundle `7814fbdcfcc9a93a8dffc2b0a5b4e996ae238d134d69945f0f3dc69913c2ddcc`, manifeste `c260fe921f630a772703e3a35894d8c3900b3d280c47b948f0a9a4fe32325e9c`, **40/40 paires complètes, 80/80 compagnies saines**. Delta profit moyen Opex **+6 794,725 £/an**, médiane **+2 102 £**, V/D/E **21/16/3**, Wilcoxon bilatéral **p=0,5016458**, IC95 bootstrap **[−8 269,775 ; +23 215,575] £/an**, seuil 4 % **+90 301,657 £/an** ; company_value ratio des moyennes **0,986312** (−1,3688 %) donc garde −5 % satisfaite. **Verdict `fail_primary`** : pas de significativité, borne basse négative, seuil de +4 % non atteint. **Porte B N75-CAP NON LANCÉE**. L'exposition N75 dans cette porte non sondée n'a pas été vérifiée ; le diagnostic seed100 10 ans ne montre aucun N75 `pick/done`. Pas de changement de défaut.

## Bilan des deux interventions

Les deux options nouvelles sont distinctes et restent **désactivées aux quatre difficultés** : `good_source_rail_join=0`, `n75_freight_capacity=0`. **Deux portes A `fail_primary`**, aucune porte B autorisée par le protocole, aucun commit/push/merge. La cible utilisateur de **75 % sur 20×10 ou 40×10 n'est pas atteinte ni démontrée**. La seule baseline 20×10 qualifiée reste master `83e436cc` à **56,5519 %** des profits moyens AAA et **58,9112 %** de médiane des ratios appariés (manque théorique **1 344 892,59 £/an** Opex à AAA constant). Les campagnes individuelles à dix ans renseignent exposition et faisabilité, pas une nouvelle mesure de performance générale.

Levier GOOD : six vraies jonctions de gare A et un +838,4 k£/an sur **une seule graine** en dix ans, mais gain insuffisant et non robuste à trois ans, refus physiques SITEAB fréquents. Levier N75 : second train potentiel conforme aux gardes V284, mais **aucun `N75CAP screen/pick/done` dans le diagnostic 1×10** et +6,8 k£/an seulement à A3 avec intervalle contenant zéro. Aucun ajustement de défaut ni nouvelle porte B ne découle de ces résultats.
