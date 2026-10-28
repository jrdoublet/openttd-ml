# ROAD100-34 — marchés PAX LONG avant tracé (28 octobre 2026)

## Préenregistrement avant code et avant moteur

L'objectif reste 5/5 parités sur le `profit_year` **de société** OpexAI
contre AAAHogEx-115, en 1v1 **strictement ROUTE seule**, aux horizons
1, 2, 3, 4 et 5 ans sans érosion. État démontré 0/5.

**Rectification déterminante** : le `site.value` de
`OpexRoad100LongBuildSites` est une mesure
`AITile.GetCargoProduction(...coverage)` de **producteurs**, PAS
une quantité de PASS/mois. Les 14–18 producteurs V33 et les 31–35
producteurs V19b ne permettent aucune conclusion de rentabilité.
Le diagnostic V30a observe ailleurs 26 producteurs pour 152 PASS/mois
estimés après conversion. V33 a échoué par `OPCAP/NO_CORRIDOR`
**avant** de convertir sa demande : aucun corridor construit, aucun
devis ni rendement réalisé de ces marchés. Sa baisse de profit ON−OFF
ne prouve pas que ces marchés ne sont pas viables.

Hypothèse testable V34 : mesurer **avant** les traces LONG la demande
mensuelle approximativement couverte par **les seules racines de quais
réellement testées**. Réutiliser à l'identique
`OpexRoad100PaxSiteMonthly(townId,cargo,site.tile,coverage)` qui
combine la production mensuelle de la ville et la part de producteurs
attribués à cette ville dans la zone du site, sans inventer de
satellites ni copier d'observations AAA. Pour chaque couple déjà
shortlisté par le scanner de façades (max 3), journaliser les unités
`root_monthly_a/b`, `town_monthly_a/b`, `site_producers_a/b`,
`town_producers_a/b`, positions des **vrais** tiles/fronts et la
consommation d'opcodes. Toute mesure n'est qu'un potentiel ex ante,
encore non filtré par rating, concurrence marginale ni coût de tracé.

Intervention : nouveau opt-in `road100_long_market_probe` à **0 aux
quatre profils**, actif seulement avec `road100_long_build=1` en
ROUTE seule. **SHADOW strict** : aucun changement de score, liste de
candidats, limites de recherche, tracé, devis, quai, dépôt, bus,
ordres, Save/Load ni flux de construction ; pas d'usage de
`GetCargoWaiting` AAA. Délai d'instrumentation volontairement
borné par **6 appels maximum** à la mesure (3 couples × 2 bouts),
sans recalcul si même tuile déjà rencontrée. Si le budget partagé
est trop bas, `skipped=OPCAP` est journalisé sans forcer le calcul,
et **aucune prétention de marché nul** ne peut en être déduite.
Le comportement OFF doit être byte-exact par couche de projection
source, et aucune fixture historique (dont V262) ne change.

Qualification V34 : tests opt-in/default/guards et logs/limite 3
couples/cache ; projection OFF puis suite Python complète et
`git diff --check`; ensuite **un smoke apparié seed42 × 1 an**,
`road100_long_market_probe=0/1` seul changement effectif,
AAAHogEx strict ROUTE seule, même bundle source et mêmes autres
settings. Constater dans le log les PASS/mois racines avant trace,
ainsi que les opcodes et un éventuel échec moteur. Les variations
de `profit_year` entre bras SHADOW restent des divergences de
scheduling et **pas** un gain causal d'un chantier V34.

**Règle de décision** : V34 est une sonde, **jamais candidate Gate A**.
Si des sites ex ante à 80–200 PASS/mois apparaissent, ils
justifieront d'étudier séparément une liaison réellement constructible,
son nombre de quais, sa flotte/cadence, son coût, son dépôt et son
profit net. Si la mesure est nulle ou incomplète, préciser la cause
sans tricher sur les unités. Aucune autorisation de changer les
défauts ni de commit/push/merge ; respecter CPU10, ≤9 workers,
8 Gio et un seul Docker à la fois.

## Résultats du smoke apparié et décision diagnostique

Campagne `road100_v34_market_pretrace_shadow_roadonly_seed42_1x1_20261028`
en 1970, deux parties **complete/complete**, un même bundle source
SHA256 `da7671fed4b8d5c2fa7121e5a27f104fe7d4965fd2b2af3c29e5c17a663376be`.
Manifeste : seule différence effective `road100_long_market_probe` 0→1,
AAAHogEx désactive train/tram/navire/avion. Suite Python préalable
**3 222 tests OK**, 5 ignorés, 2 échecs attendus, 4/4 tests V34 et
projection OFF, `git diff --check` OK. OpenTTD confirme compilation.

La sonde lit, **avant tracé**, la production mensuelle de ville, les
producteurs réellement attribués à cette ville et la part couverte par
un site de quai passé en AITest (ce n'est ni le `waiting` concurrent ni
le nombre de PASS effectivement livrés) :

| Couple LONG seed42 | Root A | Root B | Total estimé | Coût probe rang0 |
|---|---:|---:|---:|---:|
| villes 18→2, centres d158 | 18/46 producteurs de 355 PASS/mois = **138** | 17/46 de 327 = **120** | **258 PASS/mois** | 1 726 opcodes |
| villes 26→10, centres d154 | 17/49 producteurs de 332 = **115** | 13/24 de 112 = **60** | **175 PASS/mois** | 1 661 opcodes |

Sur 18→2, un second couple de quais est censuré par le budget restant
`reason=OPCAP` après 1 845 opcodes de sonde. Sur 26→10, trois
couples shortlistés sont mesurés : 175, 175 et 120 PASS/mois,
**4 conversions de sites distincts** et **2 lectures de cache** pour
3 481 opcodes ; pas de dépassement des limites fixées ni de branche
qui utilise ces mesures pour classer, bâtir ou prédire la rentabilité.

**Attention** : ces productions mensuelles sont des *estimations
ex ante de demande de racine* calculées sur un ratio de producteurs.
Elles ne retranchent pas à coup sûr toutes les couvertures concurrentes,
ne valident pas un corridor entre villes et n'impliquent nullement
que deux bus peuvent transporter 258 ou 175 PASS/mois. En particulier,
`OpexRoadPhysicalVehicleCap(1,1)=2` et la durée de trajet de ~150
tuiles limitent sévèrement le débit. Le coût de route, le dépôt, les
deux StationIDs et la flotte supplémentaire restent non cotés faute
de plan physique complet. La rentabilité nette est **inconnue**.

OFF et ON ont exactement le même `profit_year` de société H1
**19 103 £**, valeur **15 449 £**, 16 véhicules, 16 gares. AAA
`profit_year=97 693 £`, soit Opex/AAA **19,55 %**, sans parité.
Les journaux confirment 0 plan LONG admissible/0 construction LONG.
Cette stricte neutralité observée sur une graine ne prouve pas que
l'observateur est toujours neutre, seulement qu'aucune différence de
profit n'a été introduite ici. Aucun 5×5 ou Gate A40×5 n'a de sens
pour une sonde pure.

**Verdict V34 : diagnostic utile, preuve de marché approximatif, pas
de preuve de construction ni de profit ; aucun changement de défaut.**
La thèse `LONG seed42 <35 PASS/mois` était fondée sur une confusion
avec les producteurs et est **réfutée comme mesure**. La priorité
suivante est la préqualification économique **réaliste** du débit
transportable par 2, 4, 8 bus et des arrêts supplémentaires *réellement
constructibles*, puis la faisabilité d'un corridor complet à coût
vérifié dans les 180k/400k opcodes. Ne pas transformer 258 ou 175
en un `profit_year` imaginé. L'objectif ROAD100 reste **0/5**.
