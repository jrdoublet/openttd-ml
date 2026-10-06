# Autopsie causale C115 ↔ C121 AIR — 2 octobre 2026

## Portée et provenance

Objectif : remonter des performances finales aux premières divergences AIR
irréversibles, avec priorité stratégique au gap OpexAI−AAAHogEx plutôt qu'à la
`company_value`.

Preuve principale actuelle :

- campagne non instrumentée `c121_autopsy_base_3x6_20261002_r1` ;
- graines canoniques 42, 100, 999 ; 6 ans ; 6/6 duels sains ;
- bundle figé SHA256
  `d1ac70560bd7715e2953819495c8935e30d538236f74e7b2175b696a4be2db48` ;
- C115 : C121 économie/catalogue OFF ; C121 actuel : économie ON + catalogue
  incrémental ON, autres variantes cadence/profondeur OFF ;
- télémétrie de lignes mensuelle reconstruite **hors NoAI** depuis les saves
  `VEHS/ORDL/ORDR/STNN`, donc sans coût opcode ni changement de décision.

Trace de décision : `c121_autopsy_frozen_trace_3x1_20261002_r4.json`, construite
à partir du même bundle figé. La sonde compile-time n'exécute aucun travail avant
le premier AIR physiquement construit ; elle sérialise ensuite le snapshot déjà
calculé. Le premier succès est donc observable sans rejouer le sélecteur. La r1
de cette sonde est invalide (erreur de génération de source, 6/6 scripts morts)
et est explicitement exclue. Les r2/r3/r4 sont saines ; r4 ajoute seulement le
parsing hôte des logs existants.

`RTK.md` n'existe pas dans `/openttd-ml` ni dans son parent parcouru ; `AGENTS.md`,
`docs/taches.md`, les fiches/journaux C121 et le code courant ont été relus.

Le résultat phase4 est un indice historique propre mais vient d'un autre bundle
(`c121_first_live_growth_phase4_5x6_20261001_r1`). Il est donc utilisé pour
expliquer un mécanisme aval, pas fusionné comme s'il appartenait à la même
trajectoire exacte que la campagne ci-dessus.

## Résultat global actuel

Sur 42/100/999, C121 actuel perd contre C115 en `profit_year` de respectivement
−579,1 / −329,3 / −918,1 k£/an, soit −608,8 k£/an en moyenne. L'évolution du gap
Opex−AAA est −500,6 / −719,7 / −1 104,7 k£/an. C121 finit avec −8 / −4 / −13
slots AIR Opex et −7 / −4 / −13 villes AIR Opex. Ce déficit naît dès 1970.

Le premier gros scan AIR C121 coûte :

| Seed | C115 | C121 | Multiplicateur |
|---|---:|---:|---:|
| 42 | 3,12 M op / 4 j | 6,53 M op / 8 j | 2,09× |
| 100 | 1,62 M op / 2 j | 4,59 M op / 6 j | 2,84× |
| 999 | 4,18 M op / 5 j | 11,51 M op / 15 j | 2,76× |

Le surcoût est donc réel et structurel, mais ce n'est pas une explication unique :
C121 construit son premier AIR plus tôt que C115 sur 100 et 999.

## Graine 42 — même bon projet, beaucoup trop tard

**État identique.** Le 1er janvier 1970, les deux mondes Opex ont 100 k£, zéro
AIR et AAA a zéro avion AIR.

**Première divergence.** C115 construit son premier AIR le 27 janvier, rang 0,
paire cible `(2,30)`. `built_before=0`, `K_pass=0`, `K_pass_active=0` : K_pass
n'intervient pas. Au 1er février C115 a déjà 2 avions AIR et 144,7 k£ ; C121 a
0 AIR mais 299,1 k£. Le manque de cash est donc réfuté.

**Décision C121.** C121 finit par construire **la même paire cible `(2,30)`** le
16 avril, toujours rang 0 et toujours sans K_pass. Il ne s'agit donc pas d'un
mauvais OD ni d'un projet battu au classement final : c'est d'abord un bon projet
au mauvais moment. Son premier scan coûte 8 jours contre 4, mais l'écart total de
~79 jours implique aussi la cadence de génération/publication/réélection du
portefeuille, pas seulement un scan isolé.

**Concurrence et cascade.** AAA passe de 0 avion AIR en février à 4 en mars.
C121 conserve pourtant ~298 k£ et reste à 0 AIR jusqu'au 1er avril. Au 1er mai,
C115 est à 4 AIR / 0 rail, C121 à 2 AIR / 1 rail. Au 1er janvier 1971 : C115
11 AIR / 0 rail, C121 2 AIR / 5 rails ; AAA est à 16 avions dans le monde C115
et 17 dans le monde C121.

**Prévision → réalisé de la première ligne C121.** C121 prévoit pour le matériel
réel N=1 `actual_profit=232,6 k£/an`; la profondeur de décision vaut N=2
(`389,8 k£/an`) et la cible long terme N=6 (`634,5 k£/an`). La ligne associée
reste N=1 pendant au moins 12 mois puis N=2 à 24 mois. Profit réalisé reconstitué
depuis les véhicules : ~95,9 k£/an annualisés à +6 mois (0,41× la prévision N=1),
99,6 k£ la première année (0,43×), ~73,0 k£ la deuxième année (0,31×).

**Conséquence finale.** Δprofit = −579,1 k£/an, Δgap = −500,6 k£/an,
Δslots = −8, Δvilles = −7. Catégories dominantes : bon projet au mauvais moment,
erreur de prévision, effet en cascade et perte territoriale.

## Graine 100 — le premier projet est bon ; le portefeuille bifurque ensuite

**Première décision.** C121 construit le 9 janvier et C115 le 17 janvier. Les
deux choisissent la même paire cible `(21,25)`, rang 0 ; K_pass est inactif.
C121 n'est donc pas initialement trop tard sur cette graine.

**Première divergence significative.** Après le premier succès, le snapshot C115
conserve un top 8 entièrement AIR. Chez C121, il ne reste qu'un AIR au rang 1,
puis des projets rail dès les rangs 2–7. Au 1er février, C115 a 3 AIR pour
75,6 k£ de cash, C121 seulement 1 AIR mais 224,3 k£. Fin 1970, C115 a 13 AIR /
0 rail contre 6 AIR / 3 rails pour C121. Là encore, la sous-expansion AIR n'est
pas causée par le cash disponible mais par l'ordre et le débit du portefeuille.

**Qualité réelle.** La première ligne C121 est réellement productive :
prévision N=1 `230,7 k£/an`; réalisé ~124,9 k£/an à +6 mois annualisé (0,54×),
131,4 k£ année 1 (0,57×), ~53,0 k£ année 2 (0,23×). La même liaison physique
`air|22,26` produit même plus chez C121 sur la première année (~131,4 k£) que
chez C115 (~114,9 k£). Ce n'est donc pas un exemple de « mauvais projet ».

**Conséquence finale.** Δprofit = −329,3 k£/an, Δgap = −719,7 k£/an,
Δslots = −4, Δvilles = −4. La cause dominante est l'effet de cascade du
classement/débit portefeuille, renforcé par une prévision trop optimiste.

## Graine 999 — C121 part devant puis abandonne l'avantage

**Première décision.** C121 construit un AIR le 12 janvier, cible `(38,22)`, alors
que C115 ne construit son premier AIR que le 3 février, cible `(26,37)`. C121
choisit ici un projet différent et démarre **plus tôt**. K_pass est toujours
inactif. Le premier projet C121 n'est pas médiocre : il réalise ~158,2 k£/an à
+6 mois annualisé, 190,7 k£ année 1 et ~157,1 k£ année 2, tout en étant prévu à
306,7 k£/an pour N=1 (ratios 0,52 / 0,62 / 0,51). Il passe de N=1 à N=2 à 24 mois.

**Bifurcation.** Juste après ce premier succès, C121 n'a plus qu'un AIR au rang 1,
puis des rails aux rangs 2–7 ; C115 conserve huit AIR en tête. Au 1er mars, C115
a déjà 2 AIR alors que C121 reste à 1. Au 1er janvier 1971 : 8 AIR / 0 rail chez
C115, 4 AIR / 1 rail chez C121, malgré des trésoreries comparables.

**Projet supérieur différé.** La liaison `air|22,23` de C115 apparaît dès mars,
avec 2 avions ; elle réalise ~232,8 k£ sur sa première année et ~364,1 k£ cumulés
à 24 mois. C121 n'ouvre la même liaison qu'en septembre : ~133,3 k£ année 1 et
240,0 k£ cumulés à 24 mois. Le mécanisme est donc « bon projet arrivé trop tard / à
profondeur plus faible » plutôt qu'un échec du projet AIR choisi en janvier.

**Conséquence finale.** Δprofit = −918,1 k£/an, Δgap = −1 104,7 k£/an,
Δslots = −13, Δvilles = −13.

## Ce qui est probablement du bruit ou une cause secondaire

- **K_pass** : explicitement inactif au premier AIR sur 42/100/999. Le défaut
  K_pass existe plus tard, mais il n'explique pas la première divergence de ces
  trajectoires.
- **Manque de cash** : réfuté sur 42 et 100, où C121 dispose de beaucoup plus de
  cash tout en ayant moins d'AIR ; souvent réfuté aussi durant la suite de 1970.
- **ERR_AREA_NOT_CLEAR / préflight** : un ancien bundle montrait un échec précoce
  seed999. Sur le bundle figé actuel, aucun échec de construction ne précède le
  premier succès sur ces trois graines. Les échecs plus tardifs ne sont donc pas
  une cause dominante de la divergence initiale actuelle.
- **K_dec cold-start** : exposition réelle démontrée ailleurs, mais non isolée ici
  comme première cause. Les premiers AIR observés sont tous rang 0 et construits.
- **« C121 choisit toujours de mauvais OD »** : réfuté par 42/100 (même cible que
  C115 au premier succès) et par les bons profits réalisés de la première ligne
  C121 sur les trois graines.

## Calibration ex post

Les trois premières lignes C121 actuelles sont toutes surestimées même en
comparant le **N=1 réellement construit** à leur performance :

| Seed | Prévision N=1 | +6 mois annualisé | année 1 | année 2 |
|---|---:|---:|---:|---:|
| 42 | 232,6 k£ | 95,9 k£ (0,41×) | 99,6 k£ (0,43×) | 73,0 k£ (0,31×) |
| 100 | 230,7 k£ | 124,9 k£ (0,54×) | 131,4 k£ (0,57×) | 53,0 k£ (0,23×) |
| 999 | 306,7 k£ | 158,2 k£ (0,52×) | 190,7 k£ (0,62×) | 157,1 k£ (0,51×) |

Ces profits réalisés viennent de `AIVehicle` et n'incluent pas toute
l'infrastructure/amortissement C121 : ils ne rendent donc pas artificiellement
C121 pessimiste ; si quoi que ce soit, le vrai profit économique complet serait
encore plus bas.

Le signal n'est pas limité à ces trois lignes. L'ancien shadow C121, beaucoup plus
large (529 builds / 458 lignes matures), trouvait une médiane réalisé/prédit PASS
~0,656, revenu ~0,912 et profit modèle ~0,864. Mais le ratio change fortement avec
l'âge et le degré de hub : par exemple les `newpair` 4–6 mois sont bien mieux
calibrés que les mêmes lignes devenues hubs plus tard. Conclusion : le biais est
suffisamment systématique pour justifier une calibration ex post, mais **pas** un
coefficient global unique. La calibration doit dépendre de l'état observé de la
ligne / du hub et ne prendre autorité qu'après de vraies observations.

## Pourquoi phase4 gagne du terrain stratégique mais perd du profit Opex

Le 5×6 phase4 historique donne en moyenne : Δprofit Opex = −112,3 k£/an et
Δgap Opex−AAA = +265,6 k£/an. Par identité
`Δgap = ΔOpex − ΔAAA`, cela implique **Δprofit AAA ≈ −377,9 k£/an** en moyenne.
Le gain de gap vient donc principalement du fait que phase4 fait plus de dégâts à
AAAHogEx qu'il n'en coûte à Opex.

Par graine :

| Seed | ΔOpex | Δgap | ΔAAA implicite | Δslots Opex |
|---|---:|---:|---:|---:|
| 42 | −85,9 k£ | +140,2 k£ | −226,1 k£ | +3 |
| 100 | −54,7 k£ | +150,7 k£ | −205,4 k£ | −2 |
| 999 | −1,8 k£ | +554,2 k£ | −556,0 k£ | −3 |
| 1234 | −352,4 k£ | +441,7 k£ | −794,1 k£ | −7 |
| 5678 | −66,5 k£ | +41,1 k£ | −107,6 k£ | −1 |

Les cinq ΔAAA sont négatifs. Le mécanisme n'est donc pas simplement « Opex pose
plus d'aéroports » : 4/5 graines perdent des slots Opex. Phase4 publie tôt des
renforts 1→2 sur des lignes qui ont déjà montré du trafic réel. Seed42 : lignes 0
et 1 passent `balanced90=1` le 18 septembre 1970 avec profit récent positif,
charges/attentes élevées ; le bras phase4 expose ensuite des projets fleet ligne 0
rang 0 et ligne 1 rang 1 en octobre/novembre, alors que le bras de référence ne
publie pas ces opportunités. Cela consomme des occasions d'investissement et peut
réduire la création de nouvelles lignes — coût Opex — mais renforce plus tôt la
qualité/service sur des marchés partagés, ce qui modifie les revenus et décisions
d'AAA dans le monde commun. Le signe 5/5 sur ΔAAA est cohérent avec cette
externalité concurrentielle.

## Trois causes dominantes

1. **Débit/cadence du portefeuille AIR C121 trop faible.** Le calcul AIR initial
   est 2,1–2,8× plus coûteux ; seed42 montre le même projet rang 0 construit ~79
   jours plus tard. C121 conserve du cash pendant qu'AAA et C115 occupent les
   marchés. Le coût de calcul seul n'explique pas 100/999, mais la chaîne
   génération → publication → construction est clairement moins productive.
2. **Bifurcation de classement après les premiers succès.** Sur 100 et 999, le top
   portefeuille C121 passe presque immédiatement d'AIR à rail alors que C115 garde
   un top 8 entièrement AIR. Cette petite divergence initiale devient une cascade :
   moins d'AIR → moins de hubs/slots → autres candidats/rangs → avantage AAA.
3. **Prévision C121 structurellement trop optimiste avant observation.** Les trois
   premières lignes réalisent seulement ~0,23–0,62× de la prévision N=1 selon
   horizon ; les cibles N=5–6 sont très supérieures au service réellement atteint.
   Le biais peut fausser simultanément valeur absolue, profondeur et arbitrage
   multimodal, même quand l'OD choisi est bon.

## Ce que C115 et C121 font chacun mieux

C115 fait concrètement mieux : mise en service rapide, coût de recherche moindre,
maintien d'un vivier AIR profond, conversion du cash en présence territoriale avant
AAA, et ouverture précoce de plusieurs lignes qui se révèlent réellement
profitables. Sa fonction plus simple est moins ambitieuse mais produit un meilleur
**débit de décisions irréversibles utiles**.

C121 fait concrètement mieux : il peut identifier des lignes individuellement très
productives (seed999) et, sur la même liaison, obtenir parfois un réalisé supérieur
à C115 (seed100). Son modèle expose des informations utiles de demande, mail,
matériel et profondeur, et la sonde live phase4 montre qu'une observation réelle
peut repérer des lignes à renforcer bien avant deux ans. Son problème principal
n'est donc pas l'absence de signal, mais l'autorité donnée à une prévision froide
coûteuse et mal calibrée avant observation.

## Prochain mécanisme causal unique à tester

**Cold-start C115 prior → C121 posterior observé.** Pour une nouvelle ligne AIR,
ne pas laisser la prévision C121 froide gouverner l'admission/classement initial :
conserver le prior C115 (et donc son débit/territoire) jusqu'à ce que la ligne ait
une fenêtre réelle C117 suffisante ; ensuite seulement, recalibrer la valeur C121
à partir du réalisé et lui rendre l'autorité pour les renforts/arbitrages suivants.

Avant un causal, le test prioritaire doit être un replay/shadow du **même
portefeuille** : ordre C115 froid versus ordre C121 corrigé par réalisation sur les
lignes observées, sans nouveau scan ni décision. Le critère n'est pas « améliore un
coefficient », mais « aurait-il empêché les premières bifurcations AIR→rail de
100/999 et le retard de 42 tout en conservant les bons projets C121 ? ». C'est un
seul mécanisme et il dérive directement des trois constats ci-dessus.

## Artefacts

- `results/c121_autopsy_base_3x6_20261002_r1.json{,l}` — trajectoire actuelle ;
- `results/c121_autopsy_base_3x6_20261002_r1_analysis.json` — chronologie passive ;
- `results/c121_autopsy_frozen_trace_3x1_20261002_r4.json` — premier snapshot
  décisionnel, même bundle ;
- `results/c121_autopsy_prediction_realization_3x6_20261002_r1.json` — jointure
  prévision → réalisé ;
- `results/c121_first_live_growth_phase4_5x6_20261001_r1.json` — indice phase4
  historique, bundle distinct.

Aucun commit ni push n'a été effectué.
