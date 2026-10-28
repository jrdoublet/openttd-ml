# ROAD100 — contre-audit PAX sur 40 graines, sans changement de modèle (28/10/2026)

## Corpus reproductible et définitions

Recalcul : `python -X utf8 sweeps/diag_road100_pax_baseline40_20261028.py` ;
tests `sweeps/test_road100_pax_baseline40_20261028.py`. Les 40 journaux
`results/road100_baseline_40x5_20261027_engine/road100_baseline_seed*_r0.log`
proviennent de la **baseline 1v1 ROUTE seule** figée ; vérifier son manifeste
`results/road100_baseline_40x5_20261027.manifest.json` (seed 73 projetée
en 373684). Ce sont les événements Opex `LINE_REVENUE mode=road kind=pax`.
L'unité *mature* est un couple `(graine, ligne, âge)` avec âge ≥ 2 ; une
même ligne peut fournir plusieurs âges et **ils ne sont pas indépendants**.

Le « ratio des sommes » est `Σreal_rev/Σpred_rev` (ou `Σreal_prof/Σpred_prof`),
pas la moyenne des ratios individuels ; la **médiane** est celle des ratios
strictement positifs par observation ligne-âge. Les événements utilisent
`real_prof` fondé sur les profits des véhicules, **pas** `profit_year` de
société. `real_rev` est reconstruit en ajoutant les coûts d'exploitation à
ces profits. L'amortissement et la flotte de `pred_prof` ne sont donc pas
nécessairement comptabilisés sur la même assiette que `real_prof`.

| Cohorte de la baseline | Observations | Lignes distinctes | Graines exposées | Ratio sommes recette | Ratio sommes profit | Médiane ratio recette | Médiane ratio profit |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Mature, âge ≥2** | **108** | **47** | **28/40** | **0,818** | **0,797** | **0,851** | **0,794** |
| Âge exactement 2 | 47 | 47 | 28/40 | 1,244 | 1,268 | 1,419 | 1,454 |
| Âge ≥3 | 61 | 36 | 24/40 | 0,539 | 0,492 | 0,602 | 0,546 |
| Tous âges publiés, **non mature** | 164 | 55 | 31/40 | 0,828 | 0,805 | **0,864** | **0,882** |

Les valeurs **0,87–0,88** mentionnées dans la première lecture sont donc
des **médianes approximatives tous âges**, **pas** la calibration mature
des 40 graines. Huit profits réalisés non positifs sont exclus de la
médiane profit « tous âges » ; aucune observation mature n'en est exclue.
En comparant les âges, un multiplicateur constant est manifestement
fragile : le ratio recette des sommes passe de 1,244 à l'âge 2 à 0,539
aux âges ≥3, avec une évolution des cohortes et de la concurrence.

Autre confusion de flotte : dans les 108 événements matures, **24**
observent deux bus prédits et deux bus réels (8 lignes/7 graines), avec
ratio de sommes recette/profit **0,479/0,467** ; **84** observent un bus
prédit puis deux réels, ratios **1,106/1,090**. Sans même-flotte,
même assiette comptable et split par graine, « réalisé/prédit » n'est
pas une erreur de tarif corrigeable par `×6,45` ou `×18,81`.

## Pourquoi l'ancienne lecture V24 ne se transporte pas

Le script distinct `sweeps/diag_road100_pax_heldout_20261028.py` porte sur
**une autre politique**, `road100_v24_freight_berths` ON (5 graines),
non sur la baseline : 36 lignes-âges matures, 16 lignes et 5 graines.
Les facteurs **6,453704** (recette) et **18,809434** (profit) sont les
**médianes de ratios positifs ajustées sur seulement 19 observations / 9
lignes des graines 7,42,100**. Les deux graines 999,2026 de test ont
17 observations / 7 lignes ; le score de test est dominé par seed2026,
seed999 régresse. Le ratio des **sommes** du V24 ON complet est lui-même
**3,772545 / 5,003710**, différent des médianes entraînées.

Dans le V24 ON, les 36 observations matures ont toutes **un seul bus
prédit**, et 32 en ont 2 réels, 2 en ont 4 et 2 en ont 6 ; elles
ne sont pas comparables à demande, flotte et sélection égales à la
baseline. Dans la baseline, les graines 42 et 100 n'ont **aucun**
événement PAX mature, alors qu'elles ont respectivement 7 et 6
observations V24 ON. C'est un biais structurel de sélection/survie,
pas une preuve de sous-estimation généralisée ni un levier préchantier.

**Verdict : pas de calibration PAX `×6,45`, `×18,81` ou `×0,88` dans
OpexAI et aucune qualification économique.** Garder les priorisations
fondées sur des marchés physiquement admissibles et des coûts réels.

## Audit de causalité V29 et échelle de marché pour V30

V29 `road100_pax_intercity_roots=1` est un observateur SHADOW :
aucun chantier, aucune flotte ni aucun candidat injecté. Il consomme
21–24k opcodes/an et quatre suspensions dans le générateur partagé
synchrone/PO01C. Comparaison de la campagne H2 appariée, mêmes données :
seed42 **−6 131 £/an** ON−OFF (9 constructions dans chaque bras mais
substitutions de lignes), seed2026 **−3 801 £/an** (12 constructions OFF
contre 10 ON, deux lignes PAX perdues). La moyenne **−4 966 £/an**
est une divergence d'ordonnancement **sans revenu V29 construit**.
H1 +3 325 £/an sur 5 graines, p=0,0625, ne démontre pas davantage
un gain. Un contrôle avec observateur dans une **copie diagnostique
séparée** est nécessaire avant d'inférer la neutralité ; décaler
l'observateur dans le même bras scoré ne garantit pas l'invariance.

Le mécanisme AAA est d'une autre échelle : seed42, villes Danville et
Little Sintburg, production de ville déclarée 355/327 PASS/mois,
27 bus prévus, 28 bus effectifs en fin 1970, 119 082 £ de profit
**cumulé des véhicules** en 1970 (pas profit annuel de société).
**Rectification dimensionnelle :** l'API officielle
AITile.GetCargoProduction compte les **producteurs**, pas les
unités de PASS/mois. LONG v19b 31–35, V29 d43..80 7–12
et V20 +2–15 mesurent des **producteurs couverts** ;
les plafonds de revenu qui en ont été déduits sont invalides.
Au tarif optimiste de d63,
zéro jour de transit, 25 000 £ de recette **brute** annuelle requièrent
au moins 87 voyageurs effectivement livrés/mois, avant véhicule,
route, trésorerie, risque et congestion. Les tracés de LONG v19b ne
franchissent pas non plus les obstacles physiques. À l'inverse,
les 355/327 PASS/mois de ville AAA viennent
d'AITown.GetLastMonthProduction, une grandeur différente ;
il était incorrect de comparer directement ces deux API.

Un simple agrandissement du scanner V16, l'union de 2–3 quais V20
ou le relèvement de la flotte n'a pas de support économique suffisant.
**V30a**, prioritaire, convertira de manière explicitement estimative
la fraction des **producteurs de la ville** réellement couverts
par le site en unités PASS/mois, sur le modèle AIR B9
(production mensuelle ville × part physique, ratio plafonné).
La piste **V30b** de nouveaux quartiers reste une hypothèse :
rechercher un réseau de **plusieurs quartiers distincts hors du
`station_spread`**, avec production marginale, vrais arrêts/devis,
transferts physiques et véhicules de rabattement *construits et
vérifiés avant de compter leur recette*. Les volumes de ville servent
seulement à ordonner la visite. Un préflight doit trouver, sur des
mondes distincts, une marge plausible de l'ordre de ≥25–30k£/an
**par liaison** après coût réel et opcodes ; sans cela, ne pas
répéter V20/V26/V29. Une copie diagnostique non scorée peut tester
la faisabilité sans polluer l'OFF, mais ne prouve jamais le profit
de société d'une future variante.

Le manque à H5 de V26 reste **2 037 540 £/an** en moyenne sur ses
cinq graines (baseline 40 graines : environ **2,132 M£/an**). Les
5/5 seuils de parité ROUTE seule restent **ouverts et non atteints**.
Pas de nouveau réglage, défaut changé, commit ni push dans ce contre-audit.

## Résultat V30a en moteur, distinct du contre-audit initial

Le **nouveau réglage** road100_pax_producer_units (défaut0)
a été essayé en gardant le modèle historique OFF.
Source figée **e39edc170152411978049d578501e6618d83d2484c0d7e8b7c0e821c2a6d4f98**,
bras identiques hors ce réglage, AAA ROAD-only,
cinq graines 7,42,100,999,2026, cinq ans, 10/10 parties :
résultats **results/road100_v30a_pax_units_roadonly_5x5_20261028**
(.json, .jsonl, .manifest.json et _engine).

| Profit annuel de société, moyenne cinq graines | H1 | H2 | H3 | H4 | H5 |
|---|---:|---:|---:|---:|---:|
| OFF Opex (£/an) | 17 400 | 51 003 | 58 123 | 62 553 | 70 622 |
| **ON V30a Opex (£/an)** | **23 997** | **65 915** | **68 822** | **71 400** | **76 123** |
| AAAHogEx-115 (£/an) | 134 488 | 566 189 | 1 096 555 | 1 802 155 | 2 131 265 |
| **ON / AAA %** | **17,84** | **11,64** | **6,28** | **3,96** | **3,57** |
| ON−OFF (£/an) | +6 597 | +14 912 | +10 699 | +8 847 | +5 500 |

Le smoke 1×1 seed42 H1 a réellement construit une ligne
PAX deux bus, avec estimation root **152 PASS/mois**
contre 26 **producteurs** bruts : 80/95 unités mensuelles
de ville, 10/10 et 16/21 producteurs couverts, profit
de ligne prédit 5 091 £/an. Le gain **ON−OFF +11 088 £**
sur une seule graine n'est pas un taux de livraison
réalisé ni une parité H1 avec AAA (19 592 vs 99 167 £/an).

À H5 : **3 gagnantes, 2 perdantes**, delta moyen +5 500 £/an,
Wilcoxon **p=0,625**, IC95 bootstrap [−4 568 ; +16 598] £/an.
Gain de valeur ON/OFF +23,86 %, non substituable au profit
de société. **0/5 parités de groupe, 0/5 graines
individuellement paritaires à H5 ; pas de Gate A**.

Sur les journaux ON : **31 lignes PASS construites** et
**52 bus initiaux** (OFF 26 lignes / 26 bus).
Pour LINE_REVENUE PAX, à l'âge 2, 20 observations ON
présentent profit réel de véhicules moyen **10 959 £**
contre prédit **7 695 £**, ratio des sommes **1,424** ;
OFF 15 observations, réel 10 218 £ contre prédit 1 209 £,
ratio **8,452**. À l'âge 4, le ratio ON retombe à
**0,830** (8 observations) : la calibration reste
incertaine avec âge et compétition.

Le portefeuille ON a joint **20 quais physiques** sur
12 chantiers, dont seulement **4 avec au moins un quai
joint à chaque extrémité**. Le constructeur plafonne
toujours la flotte initiale PORTFOLIO à **deux bus**,
même après construction des quais supplémentaires.
Ce verrou et le rythme très faible de nouvelles
liaisons motivent un éventuel levier V31, **seulement**
sur deux StationIDs avec quais construits, devis
réel, coût et ROI, trésorerie, circulation, livraison,
rollback et Save/Load ; ne pas gonfler les prévisions
sans flotte physiquement exploitable.

Suite hôte après projection OFF exacte nouvelle fixture
V30a séparée des fixtures historiques : **3 198 tests OK**,
5 skipped, 2 expected failures ; git diff --check OK.
Les empreintes historiques ne changent pas.
**Aucun commit, push ni adoption de défaut.**
