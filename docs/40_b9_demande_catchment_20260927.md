# B9/G4 — requalification demande / catchment AIR (2026-09-27)

## Statut

Diagnostic passif terminé sur le défaut courant, avec C115 et C96 laissés à
leurs valeurs par défaut. Aucun changement de politique AIR n'est adopté.

Les sondes B9 sont désormais isolées derrière
`b9_air_catchment_probe=0` et `b9_air_demand_shadow=0` par défaut. Le runner
diagnostique n'active plus le groupe général `probe_events`.

Validation :

- B9 + campaign freeze Docker après correction géométrique :
  **29 tests OK, 1 skip** ;
- smoke final graine 42 × 1 an :
  `results/b9_demand_shadow_smoke_1x1_20260927_r2.json`,
  **2/2 runs**, **10/10 builds appariés**, 20 endpoints, zéro invariant cassé ;
- qualification finale 5 graines × 6 ans :
  `results/b9_demand_shadow_final_5x6_20260927.json`, **10/10 runs**,
  **539 événements shadow, 461 builds réussis, 461/461 appariés, 923
  endpoints, 0 build orphelin et 0 invariant cassé**. Les **78 shadows non
  appariés** correspondent à des plans instrumentés avant tentative mais sans
  `AIR_CATCHMENT_BUILD` réussi. Un endpoint de sonde supplémentaire reste
  orphelin ; il n'est associé à aucun build réussi.

Le probe post-build coûte environ **59 k opcodes par build** (médiane 59,6 k
sur 461 mesures). Son 5×6 reste
donc une autorité descriptive, jamais une autorité économique.

## Demande par bras

`base_monthly` est le proxy historique de population. Les estimations
`airport_est` et `union_est` convertissent la production mensuelle réelle
de la ville par la fraction de ses tuiles productrices couverte. Pour les hubs
réutilisés, la comparaison économiquement cohérente applique le même diviseur
`routes + 1` que le modèle historique.

Sur la qualification finale, le résumé embarqué applique le même partage
`routes+1` au shadow et à l'union post-build. Pour isoler l'erreur physique
du shadow de l'évolution de production entre sélection et chantier, le shadow
est aussi **renormalisé à la production du mois du build** :

| bras | builds appariés | base / union post-build, moy. / méd. | shadow renormalisé / union post-build, moy. / méd. | erreur physique médiane |
|---|---:|---:|---:|---:|
| newpair | 17 | **1,930 / 2,200** | **1,026 / 1,006** | **+0,63 %** |
| hubsite | 97 | **2,225 / 1,975** | **1,035 / 1,005** | **+0,51 %** |
| hubhub | 347 | **2,274 / 2,078** | **1,004 / 1,004** | **+0,35 %** |

Une fois le partage des hubs remis dans la même unité, le proxy historique est
**systématiquement environ deux fois supérieur** à l'estimation de production
mensuelle capturable par l'union réelle de la station.

## Placement

Dans le sous-ensemble STNN réellement comparable, les deux IA utilisent
uniquement des aéroports type 1, **6×6**. Le rayon observé côté Opex vaut 5.

| | OpexAI | AAAHogEx |
|---|---:|---:|
| snapshots | 606 | 918 |
| sous-ensemble placement comparable | 600 | 518 |
| distance rectangle → centre, moyenne | 6,340 | 6,006 |
| distance rectangle → centre, médiane | 6 | 6 |
| centre dans le catchment réel | **74,0 %** | **73,2 %** |

La première lecture 34,2 % / 40,9 % était fausse : elle assimilait
`distance Manhattan au rectangle <= rayon` au catchment. OpenTTD étend en
réalité l'emprise du station tile area de `radius` sur X et Y ; les coins font
donc partie du bassin. Après correction, Opex est légèrement plus excentré en
distance descriptive, mais **ne présente plus de déficit de couverture du
centre** face à AAAHogEx. Le placement Opex n'est donc plus un suspect B9 fort
depuis C96.
Cette comparaison **ne mesure pas la production captée par AAAHogEx** : STNN
ne donne pas sa production exacte tuile par tuile.

## Stations jointes et unités

Sur 131 extrémités nouvelles avec mesure de jointure de la qualification
finale :

- `OpexAirJoinedMarginalProduction` égale exactement
  `union - airport` dans **131/131** cas ;
- erreur du modèle marginal : **0** partout ;
- la somme brute des arrêts double-compte le catchment dans **114/131
  (87,0 %)** cas ;
- double compte brut : moyenne **12,49** et médiane **12** tuiles productrices ;
- sur l'ensemble des 923 endpoints, l'aéroport seul couvre le centre de ville
  dans **74,1 %** des cas et l'union réelle dans **87,4 %**.

Les anciens champs `joinedMonthlyPax*` sont historiquement mal nommés : ils
contiennent des **comptes de tuiles productrices**, pas des passagers/mois.
Ils n'entrent cependant plus dans l'économie du défaut :
`OPEX_AIR_PLAN_PAD` est forcé à `false`. La télémétrie B9 publie désormais
des alias explicites `*_pax_tiles`.

La réserve pré-chantier des stops est volontairement **0**. Sur les 461 builds
mesurés, 100 ont un coût de stops positif ;
l'écart réserve - réel vaut **−574 £** par build en moyenne, médiane 0,
minimum −7 200 £. Le coût réel est réconcilié après construction.

## Décision B9

Le cas observé est le troisième du protocole : **biais systématique du proxy
historique** au sens physique. Mais ce biais n'est pas une preuve que
`monthlyPax` doit être diminué immédiatement :

- V93.1 a perdu **−421,5 k£/an** au 20×10 et −18,24 % de valeur ;
- V93.2 a encore perdu **−203,9 k£/an** au 5×6 et −10,98 % de valeur ;
- C98 a montré que l'économie AIR courante sous-prédit souvent revenu/profit
  réalisés malgré ce proxy de demande élevé.

### Shadow pré-build union-aware

Le shadow `b9_air_demand_shadow=1` implémente maintenant, sans participer au
score ni à l'admission, la formule :

`capturable_monthly = town_last_month_production
                       * union_producer_tiles / town_producer_tiles`

puis :

- hub réutilisé : division par `routes + 1` ;
- nouveau site : pas de division artificielle ;
- borne haute naturelle : production mensuelle de la ville ;
- hub existant : union exacte via `AITileList_StationCoverage` ;
- site neuf : estimation pré-build de l'union aéroport + futurs stops joints,
  et non simple catchment aéroport comme V93.2.

Le hook est placé immédiatement avant la tentative réelle de construction,
donc après sélection/revalidation du projet. Le chemin direct et le chemin
portefeuille sont tous deux couverts. Le shadow n'est jamais relu par
`OpexAirEconomics`, le portefeuille ou le chantier.

La première qualification 5×6 a révélé une erreur dans **le shadow lui-même** :
sa géométrie pré-build utilisait une distance Manhattan. Or OpenTTD recalcule
le catchment comme l'union, pour chaque tuile de station, d'un carré
`TileArea(...).Expand(radius)`. Le shadow a donc été corrigé sans toucher au
placement ni au chantier.

Qualification 5×6 finale :
`results/b9_demand_shadow_final_5x6_20260927.json`.
**10/10 runs**, 461 builds réussis et **461/461 appariés** au shadow.
Les 78 shadows sans build correspondent à des tentatives qui n'aboutissent pas
à un `AIR_CATCHMENT_BUILD`, et non à des builds réussis sans mesure.

Après renormalisation à la production du mois du build, le cas `hubhub`, où
aucune pièce future n'est à prédire, est quasi exact :
shadow/post-build vaut **1,004 en moyenne, 1,004 en médiane**. `hubsite`
reste également très proche (**1,035 / 1,005**). `newpair`, plus dépendant
des futurs arrêts joints, vaut **1,026 / 1,006**. L'erreur moyenne de part de
tuiles couvertes n'est que **+1,22 point** sur `newpair`, **+1,82 point** sur
`hubsite` et pratiquement **0** sur `hubhub`.

Le compte exact de stops prédit reste imparfait : **35,3 %** des `newpair`
et **58,8 %** des `hubsite` seulement, contre 100 % pour `hubhub` où il
n'y a aucun stop nouveau à prévoir. La mesure physique reste néanmoins
suffisamment proche du post-build pour confirmer l'ordre de grandeur du biais.

Cette qualification confirme le facteur physique ≈×2 sans créer de signal
économique positif. Employer immédiatement le shadow comme `monthlyPax`
réduirait toujours fortement la demande admise, alors que V93.1/V93.2 ont déjà
montré qu'une baisse isolée coupe l'expansion et la valeur.

La télémétrie annuelle disponible expose capacité, rating, attente et profit,
mais pas un débit passagers mensuel par ligne suffisamment direct pour appeler
cela une demande « réalisée ». C98 montre en outre que l'économie AIR courante
sous-prédit souvent profit et revenu réalisés. On ne transforme donc pas ce
shadow physique en traitement causal tant qu'un débit passagers réellement
transporté n'est pas mesuré séparément.

## Verdict

- **Demande** : biais physique systématique d'environ ×2, mais pas de
  causalité économique positive démontrée. Le shadow pré-build corrigé
  reproduit l'union réelle, à production du mois du build identique, avec une
  erreur médiane de seulement **+0,63 % newpair, +0,51 % hubsite et +0,35 %
  hubhub**, tout en confirmant le facteur ≈×2 du
  proxy historique.
- **Placement/catchment** : aucun déficit de couverture du centre n'est visible
  face à AAAHogEx sur le sous-ensemble STNN comparable (**74,0 % vs 73,2 %**).
  La distance descriptive reste légèrement plus grande chez Opex, sans preuve
  de moindre production captée. C96 est déjà le levier causal validé de cette
  famille.
- **Jointures** : mécanisme marginal correct ; elles compensent fortement le
  placement et ne sont pas la source de l'écart.
- **Levier B9 exploitable maintenant** : aucun nouveau levier causal. Pas de
  correction active, donc pas de 5×6 causal supplémentaire et pas de 20×10.
