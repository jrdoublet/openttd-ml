# Autopsie causale C115 â†” C121 AIR â€” 2 octobre 2026

## PortÃ©e et provenance

Objectif : remonter des performances finales aux premiÃ¨res divergences AIR
irrÃ©versibles, avec prioritÃ© stratÃ©gique au gap OpexAIâˆ’AAAHogEx plutÃ´t qu'Ã  la
`company_value`.

Preuve principale actuelle :

- campagne non instrumentÃ©e `c121_autopsy_base_3x6_20261002_r1` ;
- graines canoniques 42, 100, 999 ; 6 ans ; 6/6 duels sains ;
- bundle figÃ© SHA256
  `d1ac70560bd7715e2953819495c8935e30d538236f74e7b2175b696a4be2db48` ;
- C115 : C121 Ã©conomie/catalogue OFF ; C121 actuel : Ã©conomie ON + catalogue
  incrÃ©mental ON, autres variantes cadence/profondeur OFF ;
- tÃ©lÃ©mÃ©trie de lignes mensuelle reconstruite **hors NoAI** depuis les saves
  `VEHS/ORDL/ORDR/STNN`, donc sans coÃ»t opcode ni changement de dÃ©cision.

Trace de dÃ©cision : `c121_autopsy_frozen_trace_3x1_20261002_r4.json`, construite
Ã  partir du mÃªme bundle figÃ©. La sonde compile-time n'exÃ©cute aucun travail avant
le premier AIR physiquement construit ; elle sÃ©rialise ensuite le snapshot dÃ©jÃ 
calculÃ©. Le premier succÃ¨s est donc observable sans rejouer le sÃ©lecteur. La r1
de cette sonde est invalide (erreur de gÃ©nÃ©ration de source, 6/6 scripts morts)
et est explicitement exclue. Les r2/r3/r4 sont saines ; r4 ajoute seulement le
parsing hÃ´te des logs existants.

`RTK.md` n'existe pas dans `/openttd-ml` ni dans son parent parcouru ; `AGENTS.md`,
`docs/taches.md`, les fiches/journaux C121 et le code courant ont Ã©tÃ© relus.

Le rÃ©sultat phase4 est un indice historique propre mais vient d'un autre bundle
(`c121_first_live_growth_phase4_5x6_20261001_r1`). Il est donc utilisÃ© pour
expliquer un mÃ©canisme aval, pas fusionnÃ© comme s'il appartenait Ã  la mÃªme
trajectoire exacte que la campagne ci-dessus.

## RÃ©sultat global actuel

Sur 42/100/999, C121 actuel perd contre C115 en `profit_year` de respectivement
âˆ’579,1 / âˆ’329,3 / âˆ’918,1 kÂ£/an, soit âˆ’608,8 kÂ£/an en moyenne. L'Ã©volution du gap
Opexâˆ’AAA est âˆ’500,6 / âˆ’719,7 / âˆ’1 104,7 kÂ£/an. C121 finit avec âˆ’8 / âˆ’4 / âˆ’13
slots AIR Opex et âˆ’7 / âˆ’4 / âˆ’13 villes AIR Opex. Ce dÃ©ficit naÃ®t dÃ¨s 1970.

Le premier gros scan AIR C121 coÃ»te :

| Seed | C115 | C121 | Multiplicateur |
|---|---:|---:|---:|
| 42 | 3,12 M op / 4 j | 6,53 M op / 8 j | 2,09Ã— |
| 100 | 1,62 M op / 2 j | 4,59 M op / 6 j | 2,84Ã— |
| 999 | 4,18 M op / 5 j | 11,51 M op / 15 j | 2,76Ã— |

Le surcoÃ»t est donc rÃ©el et structurel, mais ce n'est pas une explication unique :
C121 construit son premier AIR plus tÃ´t que C115 sur 100 et 999.

## Graine 42 â€” mÃªme bon projet, beaucoup trop tard

**Ã‰tat identique.** Le 1er janvier 1970, les deux mondes Opex ont 100 kÂ£, zÃ©ro
AIR et AAA a zÃ©ro avion AIR.

**PremiÃ¨re divergence.** C115 construit son premier AIR le 27 janvier, rang 0,
paire cible `(2,30)`. `built_before=0`, `K_pass=0`, `K_pass_active=0` : K_pass
n'intervient pas. Au 1er fÃ©vrier C115 a dÃ©jÃ  2 avions AIR et 144,7 kÂ£ ; C121 a
0 AIR mais 299,1 kÂ£. Le manque de cash est donc rÃ©futÃ©.

**DÃ©cision C121.** C121 finit par construire **la mÃªme paire cible `(2,30)`** le
16 avril, toujours rang 0 et toujours sans K_pass. Il ne s'agit donc pas d'un
mauvais OD ni d'un projet battu au classement final : c'est d'abord un bon projet
au mauvais moment. Son premier scan coÃ»te 8 jours contre 4, mais l'Ã©cart total de
~79 jours implique aussi la cadence de gÃ©nÃ©ration/publication/rÃ©Ã©lection du
portefeuille, pas seulement un scan isolÃ©.

**Concurrence et cascade.** AAA passe de 0 avion AIR en fÃ©vrier Ã  4 en mars.
C121 conserve pourtant ~298 kÂ£ et reste Ã  0 AIR jusqu'au 1er avril. Au 1er mai,
C115 est Ã  4 AIR / 0 rail, C121 Ã  2 AIR / 1 rail. Au 1er janvier 1971 : C115
11 AIR / 0 rail, C121 2 AIR / 5 rails ; AAA est Ã  16 avions dans le monde C115
et 17 dans le monde C121.

**PrÃ©vision â†’ rÃ©alisÃ© de la premiÃ¨re ligne C121.** C121 prÃ©voit pour le matÃ©riel
rÃ©el N=1 `actual_profit=232,6 kÂ£/an`; la profondeur de dÃ©cision vaut N=2
(`389,8 kÂ£/an`) et la cible long terme N=6 (`634,5 kÂ£/an`). La ligne associÃ©e
reste N=1 pendant au moins 12 mois puis N=2 Ã  24 mois. Profit rÃ©alisÃ© reconstituÃ©
depuis les vÃ©hicules : ~95,9 kÂ£/an annualisÃ©s Ã  +6 mois (0,41Ã— la prÃ©vision N=1),
99,6 kÂ£ la premiÃ¨re annÃ©e (0,43Ã—), ~73,0 kÂ£ la deuxiÃ¨me annÃ©e (0,31Ã—).

**ConsÃ©quence finale.** Î”profit = âˆ’579,1 kÂ£/an, Î”gap = âˆ’500,6 kÂ£/an,
Î”slots = âˆ’8, Î”villes = âˆ’7. CatÃ©gories dominantes : bon projet au mauvais moment,
erreur de prÃ©vision, effet en cascade et perte territoriale.

## Graine 100 â€” le premier projet est bon ; le portefeuille bifurque ensuite

**PremiÃ¨re dÃ©cision.** C121 construit le 9 janvier et C115 le 17 janvier. Les
deux choisissent la mÃªme paire cible `(21,25)`, rang 0 ; K_pass est inactif.
C121 n'est donc pas initialement trop tard sur cette graine.

**PremiÃ¨re divergence significative.** AprÃ¨s le premier succÃ¨s, le snapshot C115
conserve un top 8 entiÃ¨rement AIR. Chez C121, il ne reste qu'un AIR au rang 1,
puis des projets rail dÃ¨s les rangs 2â€“7. Au 1er fÃ©vrier, C115 a 3 AIR pour
75,6 kÂ£ de cash, C121 seulement 1 AIR mais 224,3 kÂ£. Fin 1970, C115 a 13 AIR /
0 rail contre 6 AIR / 3 rails pour C121. LÃ  encore, la sous-expansion AIR n'est
pas causÃ©e par le cash disponible mais par l'ordre et le dÃ©bit du portefeuille.

**QualitÃ© rÃ©elle.** La premiÃ¨re ligne C121 est rÃ©ellement productive :
prÃ©vision N=1 `230,7 kÂ£/an`; rÃ©alisÃ© ~124,9 kÂ£/an Ã  +6 mois annualisÃ© (0,54Ã—),
131,4 kÂ£ annÃ©e 1 (0,57Ã—), ~53,0 kÂ£ annÃ©e 2 (0,23Ã—). La mÃªme liaison physique
`air|22,26` produit mÃªme plus chez C121 sur la premiÃ¨re annÃ©e (~131,4 kÂ£) que
chez C115 (~114,9 kÂ£). Ce n'est donc pas un exemple de Â« mauvais projet Â».

**ConsÃ©quence finale.** Î”profit = âˆ’329,3 kÂ£/an, Î”gap = âˆ’719,7 kÂ£/an,
Î”slots = âˆ’4, Î”villes = âˆ’4. La cause dominante est l'effet de cascade du
classement/dÃ©bit portefeuille, renforcÃ© par une prÃ©vision trop optimiste.

## Graine 999 â€” C121 part devant puis abandonne l'avantage

**PremiÃ¨re dÃ©cision.** C121 construit un AIR le 12 janvier, cible `(38,22)`, alors
que C115 ne construit son premier AIR que le 3 fÃ©vrier, cible `(26,37)`. C121
choisit ici un projet diffÃ©rent et dÃ©marre **plus tÃ´t**. K_pass est toujours
inactif. Le premier projet C121 n'est pas mÃ©diocre : il rÃ©alise ~158,2 kÂ£/an Ã 
+6 mois annualisÃ©, 190,7 kÂ£ annÃ©e 1 et ~157,1 kÂ£ annÃ©e 2, tout en Ã©tant prÃ©vu Ã 
306,7 kÂ£/an pour N=1 (ratios 0,52 / 0,62 / 0,51). Il passe de N=1 Ã  N=2 Ã  24 mois.

**Bifurcation.** Juste aprÃ¨s ce premier succÃ¨s, C121 n'a plus qu'un AIR au rang 1,
puis des rails aux rangs 2â€“7 ; C115 conserve huit AIR en tÃªte. Au 1er mars, C115
a dÃ©jÃ  2 AIR alors que C121 reste Ã  1. Au 1er janvier 1971 : 8 AIR / 0 rail chez
C115, 4 AIR / 1 rail chez C121, malgrÃ© des trÃ©soreries comparables.

**Projet supÃ©rieur diffÃ©rÃ©.** La liaison `air|22,23` de C115 apparaÃ®t dÃ¨s mars,
avec 2 avions ; elle rÃ©alise ~232,8 kÂ£ sur sa premiÃ¨re annÃ©e et ~364,1 kÂ£ cumulÃ©s
Ã  24 mois. C121 n'ouvre la mÃªme liaison qu'en septembre : ~133,3 kÂ£ annÃ©e 1 et
240,0 kÂ£ cumulÃ©s Ã  24 mois. Le mÃ©canisme est donc Â« bon projet arrivÃ© trop tard / Ã 
profondeur plus faible Â» plutÃ´t qu'un Ã©chec du projet AIR choisi en janvier.

**ConsÃ©quence finale.** Î”profit = âˆ’918,1 kÂ£/an, Î”gap = âˆ’1 104,7 kÂ£/an,
Î”slots = âˆ’13, Î”villes = âˆ’13.

## Ce qui est probablement du bruit ou une cause secondaire

- **K_pass** : explicitement inactif au premier AIR sur 42/100/999. Le dÃ©faut
  K_pass existe plus tard, mais il n'explique pas la premiÃ¨re divergence de ces
  trajectoires.
- **Manque de cash** : rÃ©futÃ© sur 42 et 100, oÃ¹ C121 dispose de beaucoup plus de
  cash tout en ayant moins d'AIR ; souvent rÃ©futÃ© aussi durant la suite de 1970.
- **ERR_AREA_NOT_CLEAR / prÃ©flight** : un ancien bundle montrait un Ã©chec prÃ©coce
  seed999. Sur le bundle figÃ© actuel, aucun Ã©chec de construction ne prÃ©cÃ¨de le
  premier succÃ¨s sur ces trois graines. Les Ã©checs plus tardifs ne sont donc pas
  une cause dominante de la divergence initiale actuelle.
- **K_dec cold-start** : exposition rÃ©elle dÃ©montrÃ©e ailleurs, mais non isolÃ©e ici
  comme premiÃ¨re cause. Les premiers AIR observÃ©s sont tous rang 0 et construits.
- **Â« C121 choisit toujours de mauvais OD Â»** : rÃ©futÃ© par 42/100 (mÃªme cible que
  C115 au premier succÃ¨s) et par les bons profits rÃ©alisÃ©s de la premiÃ¨re ligne
  C121 sur les trois graines.

## Calibration ex post

Les trois premiÃ¨res lignes C121 actuelles sont toutes surestimÃ©es mÃªme en
comparant le **N=1 rÃ©ellement construit** Ã  leur performance :

| Seed | PrÃ©vision N=1 | +6 mois annualisÃ© | annÃ©e 1 | annÃ©e 2 |
|---|---:|---:|---:|---:|
| 42 | 232,6 kÂ£ | 95,9 kÂ£ (0,41Ã—) | 99,6 kÂ£ (0,43Ã—) | 73,0 kÂ£ (0,31Ã—) |
| 100 | 230,7 kÂ£ | 124,9 kÂ£ (0,54Ã—) | 131,4 kÂ£ (0,57Ã—) | 53,0 kÂ£ (0,23Ã—) |
| 999 | 306,7 kÂ£ | 158,2 kÂ£ (0,52Ã—) | 190,7 kÂ£ (0,62Ã—) | 157,1 kÂ£ (0,51Ã—) |

Ces profits rÃ©alisÃ©s viennent de `AIVehicle` et n'incluent pas toute
l'infrastructure/amortissement C121 : ils ne rendent donc pas artificiellement
C121 pessimiste ; si quoi que ce soit, le vrai profit Ã©conomique complet serait
encore plus bas.

Le signal n'est pas limitÃ© Ã  ces trois lignes. L'ancien shadow C121, beaucoup plus
large (529 builds / 458 lignes matures), trouvait une mÃ©diane rÃ©alisÃ©/prÃ©dit PASS
~0,656, revenu ~0,912 et profit modÃ¨le ~0,864. Mais le ratio change fortement avec
l'Ã¢ge et le degrÃ© de hub : par exemple les `newpair` 4â€“6 mois sont bien mieux
calibrÃ©s que les mÃªmes lignes devenues hubs plus tard. Conclusion : le biais est
suffisamment systÃ©matique pour justifier une calibration ex post, mais **pas** un
coefficient global unique. La calibration doit dÃ©pendre de l'Ã©tat observÃ© de la
ligne / du hub et ne prendre autoritÃ© qu'aprÃ¨s de vraies observations.

## Pourquoi phase4 gagne du terrain stratÃ©gique mais perd du profit Opex

Le 5Ã—6 phase4 historique donne en moyenne : Î”profit Opex = âˆ’112,3 kÂ£/an et
Î”gap Opexâˆ’AAA = +265,6 kÂ£/an. Par identitÃ©
`Î”gap = Î”Opex âˆ’ Î”AAA`, cela implique **Î”profit AAA â‰ˆ âˆ’377,9 kÂ£/an** en moyenne.
Le gain de gap vient donc principalement du fait que phase4 fait plus de dÃ©gÃ¢ts Ã 
AAAHogEx qu'il n'en coÃ»te Ã  Opex.

Par graine :

| Seed | Î”Opex | Î”gap | Î”AAA implicite | Î”slots Opex |
|---|---:|---:|---:|---:|
| 42 | âˆ’85,9 kÂ£ | +140,2 kÂ£ | âˆ’226,1 kÂ£ | +3 |
| 100 | âˆ’54,7 kÂ£ | +150,7 kÂ£ | âˆ’205,4 kÂ£ | âˆ’2 |
| 999 | âˆ’1,8 kÂ£ | +554,2 kÂ£ | âˆ’556,0 kÂ£ | âˆ’3 |
| 1234 | âˆ’352,4 kÂ£ | +441,7 kÂ£ | âˆ’794,1 kÂ£ | âˆ’7 |
| 5678 | âˆ’66,5 kÂ£ | +41,1 kÂ£ | âˆ’107,6 kÂ£ | âˆ’1 |

Les cinq Î”AAA sont nÃ©gatifs. Le mÃ©canisme n'est donc pas simplement Â« Opex pose
plus d'aÃ©roports Â» : 4/5 graines perdent des slots Opex. Phase4 publie tÃ´t des
renforts 1â†’2 sur des lignes qui ont dÃ©jÃ  montrÃ© du trafic rÃ©el. Seed42 : lignes 0
et 1 passent `balanced90=1` le 18 septembre 1970 avec profit rÃ©cent positif,
charges/attentes Ã©levÃ©es ; le bras phase4 expose ensuite des projets fleet ligne 0
rang 0 et ligne 1 rang 1 en octobre/novembre, alors que le bras de rÃ©fÃ©rence ne
publie pas ces opportunitÃ©s. Cela consomme des occasions d'investissement et peut
rÃ©duire la crÃ©ation de nouvelles lignes â€” coÃ»t Opex â€” mais renforce plus tÃ´t la
qualitÃ©/service sur des marchÃ©s partagÃ©s, ce qui modifie les revenus et dÃ©cisions
d'AAA dans le monde commun. Le signe 5/5 sur Î”AAA est cohÃ©rent avec cette
externalitÃ© concurrentielle.

## Trois causes dominantes

1. **DÃ©bit/cadence du portefeuille AIR C121 trop faible.** Le calcul AIR initial
   est 2,1â€“2,8Ã— plus coÃ»teux ; seed42 montre le mÃªme projet rang 0 construit ~79
   jours plus tard. C121 conserve du cash pendant qu'AAA et C115 occupent les
   marchÃ©s. Le coÃ»t de calcul seul n'explique pas 100/999, mais la chaÃ®ne
   gÃ©nÃ©ration â†’ publication â†’ construction est clairement moins productive.
2. **Bifurcation de classement aprÃ¨s les premiers succÃ¨s.** Sur 100 et 999, le top
   portefeuille C121 passe presque immÃ©diatement d'AIR Ã  rail alors que C115 garde
   un top 8 entiÃ¨rement AIR. Cette petite divergence initiale devient une cascade :
   moins d'AIR â†’ moins de hubs/slots â†’ autres candidats/rangs â†’ avantage AAA.
3. **PrÃ©vision C121 structurellement trop optimiste avant observation.** Les trois
   premiÃ¨res lignes rÃ©alisent seulement ~0,23â€“0,62Ã— de la prÃ©vision N=1 selon
   horizon ; les cibles N=5â€“6 sont trÃ¨s supÃ©rieures au service rÃ©ellement atteint.
   Le biais peut fausser simultanÃ©ment valeur absolue, profondeur et arbitrage
   multimodal, mÃªme quand l'OD choisi est bon.

## Ce que C115 et C121 font chacun mieux

C115 fait concrÃ¨tement mieux : mise en service rapide, coÃ»t de recherche moindre,
maintien d'un vivier AIR profond, conversion du cash en prÃ©sence territoriale avant
AAA, et ouverture prÃ©coce de plusieurs lignes qui se rÃ©vÃ¨lent rÃ©ellement
profitables. Sa fonction plus simple est moins ambitieuse mais produit un meilleur
**dÃ©bit de dÃ©cisions irrÃ©versibles utiles**.

C121 fait concrÃ¨tement mieux : il peut identifier des lignes individuellement trÃ¨s
productives (seed999) et, sur la mÃªme liaison, obtenir parfois un rÃ©alisÃ© supÃ©rieur
Ã  C115 (seed100). Son modÃ¨le expose des informations utiles de demande, mail,
matÃ©riel et profondeur, et la sonde live phase4 montre qu'une observation rÃ©elle
peut repÃ©rer des lignes Ã  renforcer bien avant deux ans. Son problÃ¨me principal
n'est donc pas l'absence de signal, mais l'autoritÃ© donnÃ©e Ã  une prÃ©vision froide
coÃ»teuse et mal calibrÃ©e avant observation.

## Prochain mÃ©canisme causal unique Ã  tester

**Cold-start C115 prior â†’ C121 posterior observÃ©.** Pour une nouvelle ligne AIR,
ne pas laisser la prÃ©vision C121 froide gouverner l'admission/classement initial :
conserver le prior C115 (et donc son dÃ©bit/territoire) jusqu'Ã  ce que la ligne ait
une fenÃªtre rÃ©elle C117 suffisante ; ensuite seulement, recalibrer la valeur C121
Ã  partir du rÃ©alisÃ© et lui rendre l'autoritÃ© pour les renforts/arbitrages suivants.

Avant un causal, le test prioritaire doit Ãªtre un replay/shadow du **mÃªme
portefeuille** : ordre C115 froid versus ordre C121 corrigÃ© par rÃ©alisation sur les
lignes observÃ©es, sans nouveau scan ni dÃ©cision. Le critÃ¨re n'est pas Â« amÃ©liore un
coefficient Â», mais Â« aurait-il empÃªchÃ© les premiÃ¨res bifurcations AIRâ†’rail de
100/999 et le retard de 42 tout en conservant les bons projets C121 ? Â». C'est un
seul mÃ©canisme et il dÃ©rive directement des trois constats ci-dessus.

## Artefacts

- `results/c121_autopsy_base_3x6_20261002_r1.json{,l}` â€” trajectoire actuelle ;
- `results/c121_autopsy_base_3x6_20261002_r1_analysis.json` â€” chronologie passive ;
- `results/c121_autopsy_frozen_trace_3x1_20261002_r4.json` â€” premier snapshot
  dÃ©cisionnel, mÃªme bundle ;
- `results/c121_autopsy_prediction_realization_3x6_20261002_r1.json` â€” jointure
  prÃ©vision â†’ rÃ©alisÃ© ;
- `results/c121_first_live_growth_phase4_5x6_20261001_r1.json` â€” indice phase4
  historique, bundle distinct.

Aucun commit ni push n'a Ã©tÃ© effectuÃ©.
