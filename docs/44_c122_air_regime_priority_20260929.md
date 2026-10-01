# C122 — stratégie AIR par régime : priorité de projets

Date des travaux : 2026-09-29. Revue documentaire statique : **2026-09-30**.

**Provenance :** résultats locaux C122 et index de preuves absents. Tous les
chiffres, comptes de tests et identités de bundles ci-dessous sont des éléments
historiques **rapportés, non revalidés** lors de cette revue. Aucune partie ni
suite de tests n'a été exécutée ici. L'empreinte du smoke passif C122.4 est
contradictoire aux deux occurrences : aucune des deux formes n'est authentifiée.

## Objectif

Utiliser le classifieur C121 `race/efficiency` comme signal de politique sans
modifier l'économie intrinsèque C121 : ni revenu/profit prédit, ni capital/ROI,
ni moteur, ni flotte, ni C69, ni autre mode.

Le point d'insertion retenu est la sélection finale :

`génération AIR -> OpexProjectFromAir -> alternatives -> OpexProjectSelectAffordable -> OpexProjectInsertDefensive -> build`.

Les informations nécessaires existent déjà avant le tri :

- `project.payload.arm` : `newpair`, `hubsite`, `hubhub` ;
- annotations `earlySlot*` et `defensive*` calculées sur les projets AIR déjà
  finançables ;
- `profitAnnual`, capital de décision, ROI et `fundScore` restent inchangés.

## C122.1 — priorité topologique minimale

Toggle : `c122_air_regime_priority`, défaut **0**.

Première formulation volontairement minimale :

- observation / `efficiency` : ordre économique C121 brut ;
- `race` : ordre AIR-versus-AIR `newpair > hubsite > hubhub` ;
- les tiers défensifs C77 restent comparés avant C122 ;
- C122 ne compare jamais AIR contre rail/route/eau ;
- le score économique existant départage les projets dans une même classe.

Le classifieur conserve son contrat one-shot : deux années complètes observées,
puis verrou `race/efficiency`. C122 réutilise exactement l'accumulation C83 déjà
présente ; aucun scan carte/site/moteur supplémentaire.

Validation statique après correction du raccord du classifieur :

`rtk python -m unittest sweeps.test_c122_air_regime_priority sweeps.test_c121_air_economics sweeps.test_c121_hub_delay sweeps.test_c121_engine_replay sweeps.test_c77_air_defensive_slot`

=> **54/54 OK** ; `rtk git diff --check` => OK.

## Smoke causal seed42 x3 ans

Campagne : `results/c122_regime_priority_smoke_seed42_1x3_20260929.json`.

Référence : C121 courant, C122=0. Variante : identique, C122=1. Un worker /
un CPU, harnais Docker, deux parties complètes et saines.

Le verrou est bien causal :

`C121_STRATEGY_LOCK source_year=1971 observed_years=2 ... regime=race`.

Résultat variante - référence :

- `profit_year` Opex : **-340,7 k£/an** ;
- `company_value` : **-434,7 k£**, soit **-20,52 %** ;
- gap `profit_year` Opex-AAAHogEx : **-343,8 k£/an** (dégradation) ;
- slots Opex : **19 -> 16** ;
- villes Opex présentes : **18 -> 16** ;
- monopoles AAA `2-0` : **4 -> 6** ;
- villes partagées `1-1` : **13 -> 11** ;
- véhicules primaires Opex : **40 -> 34**.

Le triplet de qualification échoue donc dans les trois dimensions : gap AAA,
territoire et soutenabilité. **Pas de 5x6, pas de 20x10.**

## Interprétation C122.1

Le signal `race/efficiency` reste utile ; c'est la traduction `newpair` =>
priorité territoriale qui est trop grossière. Un `newpair` n'est pas en soi une
preuve que le projet prend le bon territoire au bon moment, et une priorité
lexicographique dure peut écarter un projet hub économiquement beaucoup plus
productif, ralentissant ensuite l'expansion globale.

## C122.2 — audit des signaux territoriaux

L'audit du chemin de sélection donne la frontière suivante :

- C77 couvre déjà le vrai second slot concurrent : `defensiveCompetitorClaims > 0`
  et `preemptClaims > 0` sont tier 2 ; `defensiveOwnClaims > 0` est tier 1. C122
  ne doit donc pas dupliquer C77 ;
- `earlySlotClaims` décrit une extrémité neuve absente de `servedTowns`, mais
  seulement dans la fenêtre early-slot. Il alimente déjà `earlySlotBonusPct` et
  `OpexProjectSelectionScore`, donc une classe dure sur ce même champ n'ajoute pas
  d'information territoriale ;
- `OpexAirProjectNewSlotTowns` donne les TownID des extrémités non réutilisées,
  sans prouver qu'elles sont absentes d'Opex ;
- C118/C120 reconstruisent des villes nouvelles par couverture uniquement derrière
  leurs toggles et avec leur propre travail de couverture : C122 ne les réactive pas ;
- `OpexDefensiveSlotSelectionState` possède déjà `servedTowns`, issu du scan unique
  des aéroports Opex de la passe, et `OpexProjectRefreshDefensiveSlot` connaît déjà
  les TownID physiques A/B. Leur croisement fournit une ville réellement nouvelle
  sans nouveau scan carte/site/moteur.

## C122.2 — règle finale

La formulation finale ajoute `defensiveNewTownClaims` dans
`OpexProjectRefreshDefensiveSlot` : nombre de villes de slot distinctes, sur des
extrémités neuves, absentes du `servedTowns` déjà calculé. Hors C122 et hors
`c121_air_pressure_probe`, le set auxiliaire n'est pas alloué et le champ n'est
pas écrit.

Ordre :

- C77 reste comparé en premier ;
- en `race`, à tier C77 égal seulement, `defensiveNewTownClaims > 0` passe devant
  un projet sans nouvelle ville ;
- en `efficiency` / observation, ordre économique C121 brut ;
- uniquement AIR<->AIR ; aucun revenu/profit, capital, ROI, `fundScore`, moteur,
  flotte ou C69 n'est modifié ;
- la trace autonome `C122_PROMOTE` n'est émise que lorsque C122 contredit
  réellement l'ordre économique `fundScore`; elle ne nécessite pas la probe C78.

Validation statique finale :

`rtk python -m unittest sweeps.test_c122_air_regime_priority sweeps.test_c121_air_economics sweeps.test_c121_hub_delay sweeps.test_c121_engine_replay sweeps.test_c77_air_defensive_slot`

=> **58/58 OK** après ajout de la sonde C122.3 et des contrats matched-shadow.

### Intermédiaire `earlySlotClaims` — rejeté

Le premier C122.2 a utilisé directement `earlySlotClaims`. Campagne
`results/c122_2_regime_priority_smoke_seed42_1x3_20260929.json`, 2/2 complète :

- `profit_year` Opex : **-276,0 k£/an** ;
- valeur : **-292,1 k£**, soit **-13,78 %** ;
- gap Opex-AAAHogEx : **-361,0 k£/an** ;
- slots **19->16**, villes **18->16**, monopoles AAA `2-0` **4->7**,
  partagées `1-1` **13->10**.

Un run de trace ultérieur sur ce proxy n'a observé aucune inversion effective de
l'ordre économique sur sa trajectoire. Il sert uniquement au diagnostic et ne
remplace pas le smoke causal.

### Smoke causal final seed42 x3 — `defensiveNewTownClaims`

Campagne : `results/c122_2_regime_priority_smoke_seed42_1x3_20260929_r4.json`.
Bundle : `34110127e92a6b586c5a38e1f71e244c0bcaea984dec17fb41e3f0434dd1d5ae`.
Deux parties complètes, 1 worker / 1 CPU. Le classifieur verrouille bien :

`C121_STRATEGY_LOCK source_year=1971 observed_years=2 pressured=1 contestable_permille=1000 open_permille=500 regime=race`.

Référence C121 courant -> C122.2 :

- `profit_year` Opex : **1 260 805 -> 1 317 206 £/an**, soit **+56,4 k£/an** ;
- `company_value` : **2 394 985 -> 2 442 085 £**, soit **+1,97 %** ;
- AAAHogEx `profit_year` : **2 179 778 -> 2 509 179 £/an** ;
- gap Opex-AAAHogEx : **-918 973 -> -1 191 973 £/an**, soit **-273,0 k£/an** ;
- slots Opex : **18 -> 16** ;
- villes Opex présentes : **17 -> 16** ;
- monopoles AAA `2-0` : **3 -> 5** ;
- villes partagées `1-1` : **14 -> 16** ;
- véhicules primaires Opex : **50 -> 47**.

Le profit nominal et la valeur Opex sont sains, mais les critères stratégiques
prioritaires échouent : gap AAA nettement pire et monopoles `2-0` en hausse.
Surtout, avec la télémétrie autonome active, le log variante contient **zéro
`C122_PROMOTE`** : `defensiveNewTownClaims` n'a inversé aucun couple de projets AIR
sur seed42. Les écarts de trajectoire ne sont donc pas attribuables à une décision
C122 observée ; le mécanisme recherché n'est pas exposé sur ce smoke.

**Décision : C122.2 non qualifié au smoke ; aucun 5x6, aucun 20x10.** Le toggle
reste défaut 0. Conserver le classifieur et C77. Avant une C122.3, mesurer dans le
portefeuille financé la fréquence et la position des `defensiveNewTownClaims` par
rapport à l'ordre économique, ou identifier un signal causal plus directement lié
à une perte de territoire au profit d'AAAHogEx.

## C122.3 — exposition réelle du signal

La sonde demandée a été ajoutée sans nouveau scan : quand
`c121_air_pressure_probe=1`, `OpexProjectRefreshDefensiveSlot` expose aussi
`defensiveNewTownClaims`, puis `OpexC122ProbeExposure` parcourt uniquement la liste
`affordable` déjà construite. Elle mesure le rang AIR/global du meilleur candidat,
le nombre de candidats territoriaux et les projets AIR de même tier C77/V88 qui les
précèdent économiquement. Elle ne modifie aucun score ni aucun ordre.

Smoke passif seed42 x3 :
`results/c122_3_exposure_probe_seed42_1x3_20260929_r2.json`.

- **36** snapshots de sélection ;
- `defensiveNewTownClaims > 0` dans **32/36** snapshots ;
- **980** occurrences de candidats territoriaux cumulées ;
- au moins une inversion potentielle dans **23/36** snapshots, **158** candidats
  concernés au total ;
- en 1972, **8/10** snapshots portent un candidat territorial et chacun se trouve
  derrière **1 à 16** AIR de même tier économique/défensif.

Le signal n'est donc pas rare. Le problème est sa position : une priorité
lexicographique dure doit souvent sauter plusieurs projets AIR mieux classés.

### Contrôle matched-shadow

Les premiers smokes C122.2 mélangeaient activation du classifieur, annotation,
trace et politique. Pour isoler ce point, le contrôle C122.3 fait tourner dans les
deux bras le même `c121_air_pressure_probe`, la même annotation, le même
classifieur one-shot et la même `C122_EXPOSURE`. Le chemin pré-verrouillage est
ordonné de façon identique. La trace `C122_PROMOTE` est maintenant bornée à huit
exemples et un compteur cumulatif évite des milliers de `AILog.Info`.

Le run intermédiaire r2 a confirmé que l'ancienne trace n'était pas neutre : la
variante avait émis **1 364** `C122_PROMOTE` et le coût de log était asymétrique ;
ses deltas ne sont donc pas utilisés pour qualifier la politique.

Run final :
`results/c122_3_shadow_control_smoke_seed42_1x3_20260929_r3.json`, bundle
`d8b7dd2123f72d8b14430554dea6d9191937085d43f2a41e7a1074078f321883`.
Les deux bras verrouillent exactement :

`source_year=1971 observed_years=2 pressured=3 contestable_permille=1000 open_permille=250 regime=race`.

Les agrégats d'exposition utiles sont identiques : **17** snapshots avec nouvelle
ville, **11** avec inversion potentielle, **632** candidats territoriaux cumulés et
**83** candidats potentiellement promouvables. Pourtant le compteur final est
**0 `C122_PROMOTE` dans les deux bras** : une fois le régime effectivement
verrouillé, la règle C122.2 n'a modifié aucun ordre `fundScore` observé sur ce
smoke.

Les métriques finales divergent malgré cela (`profit_year` variante-référence
**+29,1 k£/an**, valeur **+3,16 %**, gap AAA **+8,1 k£/an**, slots **19->20**,
villes **18->19**, monopoles AAA `2-0` **5->2**). Puisqu'aucune promotion C122 n'a
eu lieu, ces écarts sont des effets de timing/opcodes d'un chemin actif
supplémentaire dans une simulation concurrente, pas une preuve d'effet métier.

**Décision C122.3 : diagnostic terminé, aucune qualification 5x6/20x10.** Le
signal `defensiveNewTownClaims` est bien exposé, mais la clé lexicographique C122.2
est placée/timée de façon à ne pas convertir cette exposition en décision causale
sur le smoke propre. La suite doit agir au niveau d'une décision territoriale
explicite et bornée (par exemple une opportunité réellement menacée), pas renforcer
globalement `defensiveNewTownClaims` ni réintroduire `newpair`/`earlySlotClaims`.

### Confirmation par shadow exact

Un dernier contrôle retire le coût bavard de `c121_air_pressure_probe` : le nouveau
toggle diagnostique `c122_air_regime_shadow` (défaut **0**) exécute le même verrou,
la même annotation `defensiveNewTownClaims` et la même comparaison AIR<->AIR que
C122 actif, mais ne réordonne jamais le portefeuille. Il ne journalise que les
inversions qu'une C122.2 active aurait réellement produites.

Campagne : `results/c122_3_exact_shadow_seed42_1x3_20260929.json`, bundle
`9dccc24ea844b0a5d87d4fbe4c250309dfab433472505ead582b4d996dd0156b`.
Le verrou est `race` : `source_year=1971`, `observed_years=2`, `pressured=2`,
`contestable_permille=500`, `open_permille=500`. Le log contient **0
`C122_SHADOW`**. Donc, même avec le chemin de classification/comparaison payé sans
la sonde d'exposition verbeuse, aucune inversion économique C122.2 n'est disponible
après le verrou sur seed42. Cela confirme la conclusion du matched-shadow r3 : ne
pas durcir ce signal ; changer de niveau de décision pour C122.4. Validation finale
de cette instrumentation : **59/59 tests OK**, `git diff --check` OK.

## C122.4 — menace locale et fenêtre réellement périssable

L'audit descend d'un niveau : le bon point causal n'est plus le tri global du
portefeuille, mais le watcher C83 puis la tentative de build. C83 sait déjà quand
un TownID physique passe à `GetAllowedNoise()==1` sans aéroport Opex, et
`OpexAirC83FundedRaceCoversTown` sait déjà si un projet AIR vivant, rentable et
finançable couvre ce TownID. C122.4 réutilise uniquement cet état et les ancres des
projets `PROJECT_TOP_K`; aucun scan carte/site/moteur supplémentaire n'est ajouté.

La sonde passive `c122_air_threat_probe` (défaut **0**) ouvre une observation quand
la ville est à un slot restant et sans présence Opex. Elle enregistre le projet
finançable exact, son rang, son bloqueur éventuel, les tentatives réelles
`_tryBuildAirProject`, le motif d'échec et la fermeture du même TownID en
`opex_claimed` ou `competitor_monopoly`, avec le délai détection→fermeture.

Smoke passif : `results/c122_4_threat_probe_seed42_1x3_20260929_r2.json`, seed42
×3 ans, 1 worker / 1 CPU, rapporté complet et sain. **Bundle non authentifié** :
la transcription `e13491db599923e4234c7d8e9dff19e12354b5d910b4dbb26b9847a79dbaf35`
compte **63 caractères**, contre **64** pour la forme terminée par `baf35c`
plus bas. La longueur correcte ne suffit pas à authentifier cette autre forme.
**Empreinte exacte inconnue : consulter le manifest du bundle de cette campagne
passive**, non disponible localement ; ne choisir ni compléter arbitrairement
l'une des transcriptions. Le bundle du smoke causal retry est distinct.

- **4** menaces réelles observées ; toutes deviennent finançables ;
- **3** sont finalement prises par Opex ;
- **1** est perdue à AAAHogEx : TownID **18** ;
- le projet perdu est déjà **rang 0** et finançable ;
- tentative dès J+1, rejet `siteA_unbuildable`, puis aucune nouvelle tentative
  avant `competitor_monopoly` **228 jours** après la détection ;
- aucun bloqueur économique n'est présent sur ce cas.

Le trou causal est donc local : un projet territorial déjà prioritaire peut devenir
physiquement périmé entre sélection et réalisation, sans recréation de site assez
rapide avant la fermeture du second slot.

### Intervention active minimale

`c122_air_threat_retry` (défaut **0**) implique la sonde et ne change aucun score,
revenu, capital, moteur, sizing ou priorité. Seulement si le projet qui touche le
TownID menacé échoue précisément par `siteA_unbuildable` ou `siteB_unbuildable`,
C122.4 réarme **une seule fois** la file C77 ciblée sur ce TownID
(`c122_threat_retry`). Un endpoint réutilisé n'est pas éligible et la clé réactive
C77 conserve la coalescence.

Smoke causal apparié : `c122_4_threat_retry_smoke_seed42_1x3_20260929`, contrôle
et variante avec la même sonde passive, seule différence effective
`c122_air_threat_retry=0→1`, seed42 ×3, 1 worker / 1 CPU. Le retry produit exactement
**1** décision active : TownID 18, après `siteA_unbuildable`. Une nouvelle
génération ciblée ramène le projet en tête ; il est construit et la ville ferme
`opex_claimed` à **J+39**, contre `competitor_monopoly` à **J+228** dans le contrôle.

La trajectoire globale n'est toutefois pas qualifiée :

- Opex `profit_year` : **1 095 073 -> 1 289 378 £/an**, soit **+194,3 k£/an** ;
- company value : **1 990 509 -> 2 313 781 £**, soit **+16,24 %** ;
- AAAHogEx `profit_year` : **1 932 495 -> 2 421 170 £/an** ;
- gap Opex-AAAHogEx : **-837,4 -> -1 131,8 k£/an**, soit **-294,4 k£/an** ;
- slots Opex : **17 -> 16** ; villes AIR Opex : **17 -> 16** ;
- monopoles AAA `2-0` : **5 -> 2** ; monopoles Opex `2-0` : **0 -> 0** ;
- villes partagées `1-1` : **12 -> 14** ;
- véhicules primaires Opex : **43 -> 37**.

Le retry sauve l'occasion précise qui motivait C122.4 et réduit les monopoles AAA,
mais le critère stratégique principal échoue : AAAHogEx accélère davantage et le
gap se dégrade de ~294 k£/an ; l'empreinte Opex baisse aussi d'un slot et d'une ville.

**Décision C122.4 : intervention locale démontrée mais non qualifiée. Aucun 5x6 et
aucun 20x10.** Conserver sonde et retry à défaut 0. La suite doit expliquer pourquoi
la trajectoire qui sécurise TownID 18 accélère encore davantage AAAHogEx, plutôt que
généraliser le retry.

## C122.4 — menace locale réellement périssable

L'audit descend sous le tri du portefeuille, jusqu'au watcher C83 et à la tentative
réelle de construction. Une menace n'est retenue que lorsque C83 observe un TownID
physique avec **un seul slot restant**, sans aéroport Opex, et qu'un projet AIR du
petit portefeuille financé couvre physiquement ce TownID. La sonde suit ensuite le
même TownID jusqu'à `opex_claimed`, `competitor_monopoly` ou disparition de la
menace. Aucun scan carte/site/moteur supplémentaire n'est ajouté ; seul
`PROJECT_TOP_K` déjà financé est relu.

Toggle passif : `c122_air_threat_probe`, défaut **0**. La télémétrie
`C1224_THREAT` suit `detected`, `funded`, `attempt`, `outcome` et `closed` avec le
rang, la finance, le bloqueur économique, le motif de rejet et la fenêtre en jours.

### Smoke passif seed42 x3

Campagne : `results/c122_4_threat_probe_seed42_1x3_20260929_r2.json`.
**Bundle non authentifié** : la transcription
`e13491db599923e4234c7d8e9dff19e12354b5d910b4dbb26b9847a79dbaf35c`
compte **64 caractères**, mais l'autre occurrence se termine par `baf35`
et n'en compte que **63**. **Empreinte exacte inconnue : seule la consultation
du manifest du bundle passif permettra de trancher** ; ce manifest est absent
localement et aucune forme n'est retenue ici. Ne pas lui substituer le hash
du smoke causal retry ci-dessous. Partie rapportée complète, 1 worker / 1 CPU.

- **4** menaces réelles ; toutes deviennent finançables/sélectionnables ;
- **3/4** sont sécurisées par Opex ;
- TownID **18** est perdue après **228 jours** ;
- son projet est déjà **rank 0**, finançable, sans bloqueur économique et tenté dès
  le lendemain ;
- la tentative échoue sur `siteA_unbuildable`, puis aucune nouvelle tentative ne
  vise Town 18 avant `competitor_monopoly` ;
- TownID 11, initialement non financée, devient finançable **15 jours** plus tard.

Le trou causal est donc local : après une transition `2->1`, un site invalidé entre
sélection et tentative peut laisser la ville durablement à `remaining=1` sans
nouvelle génération ciblée.

### Intervention active minimale

`c122_air_threat_retry`, défaut **0**, implique la sonde passive. Il ne change ni
score, ordre, revenu, moteur, flotte, C69 ni autre mode. Après une tentative réelle
menacée rejetée pour `siteA_unbuildable` ou `siteB_unbuildable`, il récupère le
TownID physique exact, exige que la menace soit toujours vivante, autorise au plus
un retry, coalesce la file existante puis enfile
`_c77EnqueueEntity(["air"], "town", townId, true, "c122_threat_retry")`.

### Smoke causal matched seed42 x3

Campagne : `results/c122_4_threat_retry_smoke_seed42_1x3_20260929.json`, bundle
`126f33e5743368b48f4f32ce3fc584a1495ad233091cc6b595a4394c656aa11e`.
Les deux bras paient `c122_air_threat_probe=1`; seule la variante active le retry.

Une seule intervention métier réelle : **1 `phase=retry queued=1`**, sur TownID 18
après `siteA_unbuildable`. Elle réussit localement : Town 18, perdue dans le
contrôle, est reconstruite puis `opex_claimed` **39 jours** après détection.

Variante - contrôle :

- Opex `profit_year` : **+194 305 £/an** ;
- Opex company value : **1 990 509 -> 2 313 781 £**, soit **+16,24 %** ;
- gap Opex-AAAHogEx : **-837 422 -> -1 131 792 £/an**, soit **-294 370 £/an** ;
- slots Opex : **17 -> 16** ; villes AIR Opex : **17 -> 16** ;
- monopoles AAA `2-0` : **5 -> 2** ; monopoles Opex `2-0` : **0 -> 0** ;
- partagées `1-1` : **12 -> 14** ;
- véhicules primaires Opex : **43 -> 37**.

Le mécanisme est démontré localement, mais le smoke échoue au garde-fou global :
AAAHogEx accélère encore davantage, le gap se dégrade fortement et Opex termine
avec un slot/une ville et six véhicules primaires de moins. **Pas de 5x6 et aucun
20x10** pour cette formulation. Le retry reste expérimental, défaut 0.

Validation au jalon : **60/60 tests OK**, `git diff --check` OK.
