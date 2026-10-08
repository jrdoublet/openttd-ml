# AIR — pourquoi V133 et V134 n'apportent pas le gain attendu (08/10/2026)

**Statut : diagnostic statique et analyse des bancs terminés ; aucun correctif de
comportement appliqué.** Les deux réglages restent à **0 par défaut**. Cette
note distingue les propriétés **établies dans le code**, les **observations**
appariées et les **hypothèses causales non encore attribuées par graine**.
Elle ne remplace pas les protocoles ni les verdicts des campagnes.

## Périmètre, preuves et verdicts

- V133 `v133_air_build_retry` : code figé `11261de`, référence `=0`,
  variante `=1`, 40 graines × 5 ans, 80/80 parties complètes,
  40/40 paires valides. `profit_year` terminal variante − référence :
  **−45 801 £/an** de moyenne ; médiane **−73 788 £/an** ;
  V/D/E **15/25/0** ; Wilcoxon **p=0,077** ; IC95 bootstrap
  **[−96 406 ; +7 295] £/an** ; ratio des moyennes de
  `company_value` **−2,15 %**. Verdict **`fail_primary`**.
  La porte A historique 40×3 avait aussi échoué : −10,3 k£/an
  (cf. `docs/taches.md` de `origin/master` au `11261de`).
  Preuve : [V133 40×5](v133_air_build_retry_40x5_20261008.md) et
  `results/v133_air_build_retry_40x5_20261008_r1.json`.
- V134 `v134_air_p2p_saturated_hub` : code AIR `7e01b8e`, référence
  `=0`, variante `=1`. **40×5 :** 40/40 paires, profit moyen
  **+2 201 £/an**, médiane −21 583 £/an, V/D/E 19/21/0,
  Wilcoxon p=0,826, IC95 [−44 964 ; +51 485] £/an, valeur +0,54 % :
  **`fail_primary`**. **20×10 supplémentaire demandé :**
  20/20 paires, 40/40 parties complètes, profit **−4 317 £/an**,
  médiane −34 441 £/an, V/D/E 7/13/0, IC95
  [−88 186 ; +84 389] £/an, valeur +1,36 % :
  **`pass non_erosion` uniquement** (absence de perte démontrée,
  **pas** preuve de gain ou d'équivalence).
  Preuves : [V134 40×5](v134_air_p2p_40x5_20261008.md),
  [V134 20×10](v134_air_p2p_20x10_20261008.md) et leurs JSON
  `results/v134_p2p_diag_40x5_20261008_1746.json` et
  `results/v134_p2p_diag_20x10_20261008.json`.
- Les deux 40×5 sont des diagnostics à cinq ans, **pas** la porte A
  officielle V102 à trois ans. Les valeurs positives ou négatives de
  moyennes ne sont pas significatives au sens des IC95 indiqués.
  Ne pas qualifier ou activer un défaut sur ces observations.

## Évolution physique et économique

Mesures dans `policy_comparison.per_pair[].annual_trajectory` des
rapports figés. L'axe annuel correspond au `profit_year` relevé par
le harnais, pas au profit cumulé. Valeurs moyennes variante − référence :

| Année | V133 profit £/an | V133 Δ aéroports Opex | V133 Δ villes Opex avec aéroport | V134 profit £/an | V134 Δ aéroports Opex | V134 Δ villes Opex avec aéroport |
|---|---:|---:|---:|---:|---:|---:|
| 1970 | +6 965 | +0,03 | −0,05 | +691 | −0,08 | −0,08 |
| 1971 | −2 731 | 0 | −0,18 | −12 846 | +0,40 | +0,18 |
| 1972 | −31 337 | −0,38 | −0,53 | +13 736 | +0,40 | +0,08 |
| 1973 | −45 114 | −0,50 | −0,63 | +29 686 | +0,73 | +0,38 |
| 1974 | −45 801 | −0,63 | −0,75 | +2 201 | +0,75 | +0,43 |

V133 réduit progressivement la couverture après 1971 ; son recul de
profit est compatible avec des occasions d'expansion perdues.
V134 augmente les aéroports, mais moins les **villes nouvellement
couvertes**, sans effet de profit robuste. À dix ans, V134 ajoute encore
en moyenne **+0,90 aéroport** pour **+0,35 ville couverte** et
son delta terminal est **−4 317 £/an**. Ce sont des **associations**,
pas un bilan causal des lignes directement issues de V133/V134.

## V133 — bénéfice de « salvage » surestimé, exclusion de villes trop large

**Établi dans le code figé `11261de` :**

1. `air_towns.nut:429–452` — `OpexV133CountBatchSalvage` calcule
   `kept`/`dropped` sur les candidats ultérieurs du lot ; il ne les
   réinsère pas, ne les reclasse pas, ne construit pas de ligne.
   `task_projects.nut:1730–1744` faisait déjà `continue` après
   `batch_plan_dead` quand V133 est OFF : le « sauvetage » n'est
   **pas** une opportunité nouvelle prouvée. Les **28 salvages**
   du smoke comptent des candidats jugés conservables, **pas**
   28 constructions supplémentaires.
2. `task_air.nut:474–490` appelle
   `OpexV133NoteUnbuildableEndpoint` sur un échec de simple revalidation ;
   `air_towns.nut:536–546` traite aussi une erreur non reconnue comme
   `unbuildable`. Or `air_sites.nut:800–840` peut refuser un **site**
   pour ancre, récupération, ville la plus proche, contrainte C83,
   empreinte, quota ou `AITestMode` : ce n'est pas forcément la preuve
   que **tous les sites de la ville** sont condamnés.
3. `air_towns.nut:455–464` bloque pourtant le **townId entier
   pendant 730 jours**, avec Save/Load
   (`air_towns.nut:572–591`). En génération
   (`air_planning.nut:501–503,794–797`) et en sélection
   (`task_projects.nut:1713–1725`), ce blocage s'étend au
   **hub existant** : `OpexV133EndpointBlocked`
   (`air_towns.nut:509–517`) teste la quarantaine avant `!reuse`.
   Des paires constructibles ou du hub→site indépendant du mauvais
   site peuvent ainsi disparaître.
4. Les échecs physiques `PREA/PREB/AFAIL/BFAIL` d'un endpoint
   **neuf** sont reconnus séparément
   (`air_towns.nut:398–415,548–569`) ; les erreurs de caisse,
   d'avion ou du hub ne déclenchent pas directement la quarantaine.
   L'impact global exact dépend donc de la distribution de raisons.

**Hypothèse forte, non quantifiée par événement :** le coût de la
quarantaine à l'échelle de la ville, de sa durée et du blocage des
hubs réutilisés dépasse les tentatives inutiles économisées.
L'effet physique observé en 1972–1974 la soutient ; il ne permet
pas d'imputer chaque écart à un `V133_QUARANTINE`.
Le surcoût éventuel en opcodes demeure non mesuré.

## V134 — non-additivité C83, dépense d'infrastructure et marge réseau

**Établi dans le code AIR :**

1. `OpexAirV134SaturatedHubState`
   (`air_towns.nut:109–123,223–259`) exige notamment une ville
   d'au moins 1 000 habitants, le **second slot** disponible
   (`GetAllowedNoise()==1` dans le régime C83 compatible),
   un aéroport Opex de la ville déjà à **au moins 3 routes**
   (défaut `air_hub_max_routes=3`, `info.nut:1679–1686`).
   `air_planning.nut:870–889` crée une `newpair` avec
   `reuseA=false`, `reuseB=false` : en pratique il faut financer
   **deux nouveaux aéroports et un avion** ; le hub saturé n'est pas
   directement réutilisé. Le candidat reste soumis au TOP-K, au cash,
   à la revalidation et aux conditions de construction.
2. **Non-additivité réelle ON/OFF avec C83 :**
   `air_planning.nut:510–560` marque aussi `v134Eligible` des
   villes déjà admises par `c83OwnSecondSlot` ou `v126Reuse`.
   Sur une ville C83 du témoin, ON peut forcer
   `requiredSlotTownId=town.id` (`:541–559`) alors que
   `c83_fixes=0` par défaut. `air_sites.nut:181–186,561–574`
   restreint alors la recherche à cette ville physique et neutralise
   le cache ordinaire. `air_planning.nut:870–877` rejette
   certaines combinaisons de deux extrémités servies. **V134 ON peut
   retirer des candidats admissibles sous OFF** : ce n'est pas
   une simple ouverture de nouvelles possibilités. Sa fréquence et
   son coût économique n'ont pas été journalisés.
3. **Angle mort de marge réseau :** la concurrence des autres
   stations est **déjà comptée dans l'allocation de trafic au
   nouveau projet** (via `OpexC121StationCompetitionBuckets`,
   `air_coverage.nut:547–651,665–694`) :
   il serait inexact d'affirmer que tout le nouveau trafic est
   double-compté. Mais `air_economics_c121.nut:175–186`
   fixe `existingPaxBefore` et `existingMailBefore` à zéro
   pour `reuse=false`, comme dans `newpair` V134.
   La perte de revenu des **anciennes lignes Opex qui partagent
   la même ville/catchment** n'entre alors pas dans
   `cannibalLossAnnual` (`:772–812`), même si elle est
   susceptible d'exister. C121 peut ainsi surestimer le
   **profit marginal du réseau** par rapport au profit propre
   de la nouvelle ligne. L'ampleur de l'externalité reste inconnue.
4. Ce changement ne modifie ni toute la logique de sélection
   C77 ni directement la génération hub→hub ; il n'assure pas que
   les candidats supplémentaires soient **finançables, classés et
   construits**. La sonde indépendante `probe_select_reject`
   mentionnée dans le backlog distant comptait beaucoup plus de
   refus `cash` que `topk` (environ 50 000 contre 240 par
   partie) : ce sont des **événements récurrents**, pas autant de
   projets distincts ni une mesure spécifique de V134.

**Hypothèses à départager :** (a) perte de candidats témoins
due à la contrainte de site et aux exclusions C83 ; (b) nouveaux
projets écartés par site, cash ou score ; (c) nouveaux aéroports
construits mais rendement marginal réseau plus faible que prévu.
La hausse moyenne de slots ne suffit pas à choisir entre elles.

## Preuve manquante et suites prioritaires

Les journaux moteur des campagnes consultées sont vides, les
sondes `decision_log` étaient OFF, et les JSON/JSONL n'enregistrent
pas les événements détaillés `V133_QUARANTINE` /
`V133_BATCH_SALVAGE` ni la chaîne
`V134_P2P` → admis → finançable → élu → tentative → construction,
ni les recettes des lignes Opex affectées. Pas d'attribution
causale du premier écart par graine ; ne pas inventer de fréquences.

Ordre proposé pour un **prochain travail, non autorisé ici comme
changement de production** :

1. **V133, instrumentation passive OFF par défaut** :
   raison exacte et site/ville de quarantaine ; exclusions ultérieures
   `reuse`/nouveau site ; candidats « kept » effectivement
   tentés puis construits ; coûts d'opcodes. Vérifier les faux
   blocages avant de modifier durée/granularité.
2. **V134, audit d'additivité** : distinguer les villes déjà
   `c83OwnSecondSlot`/`v126Reuse` de celles **nouvellement**
   rendues éligibles par V134 ; comparer les sites et paires
   présents sous OFF, puis étape d'échec exacte
   (site / économie / financement / rang / construction).
   Candidat de correctif à évaluer : ne porter le marquage V134
   que sur les villes **non déjà admises** via C83 ou V126.
3. **V134, marge réseau** : pour chaque ligne réellement ajoutée,
   enregistrer prix de deux aéroports/avion, profit propre
   prévisionnel, trafic PASS/MAIL de la nouvelle ligne et
   pertes de recettes des lignes existantes de la ville.
   Éviter une correction forfaitaire non validée de la
   cannibalisation (risque de double décompte).
4. Après exposition et mécanisme isolés seulement :
   proposer une variante minimale, conserver défaut OFF,
   smoke puis portes V102 40×3 et 20×10 **si la première passe**.

**Décision conservée :** V133 et V134 rejetés pour adoption aux
défauts courants. Le `pass non_erosion` V134 à 20×10 ne
compense pas l'échec de la porte de gain. Aucune conclusion
de « perte significative » n'est établie par les IC95 actuels.
