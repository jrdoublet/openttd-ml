# AIR — réemploi des aéroports A conservés après BFAIL/HUBB (09/10/2026)

## Question et données antérieures

Lorsqu'un chantier AIR construit A mais échoue à construire B, le constructeur
conserve A si `economy.infrastructure_maintenance == 0`. Ce coût n'est ni une
perte définitive prouvée ni une restitution de trésorerie. Le planificateur
redécouvre plus tard les aéroports possédés sans ligne comme hubs `routes=0`.
Il manque la preuve que l'aéroport conservé est **celui** ensuite réutilisé.

La campagne ancienne `air_site_quote_residual_6x3_20261008_r1` comptait, dans
les deux bras additionnés, 18 BFAIL à deux nouveaux sites, 394 225 £ de coût
A conservable, et 12 services ultérieurs de la **même ville**. Il s'agit d'un
proxy ; la ville ne prouve aucune identité physique.

## Protocole préenregistré avant nouveau moteur

- Dépôt : `/openttd-ml`, `master`, `HEAD cb23a172fa6f7b79e50d0392e526a061c130259b`,
  arbre dirty partagé. Aucun défaut nouveau ni correctif décisionnel.
- Sonde existante `probe_air_finance_margin=1` dans tous les runs, par défaut
  0 en production. `AIR_ORPHAN_RETAIN` à la conservation effective de A ;
  `AIR_HUB_REUSE` à chaque succès de construction réutilisant A ou B, avant
  l'insertion dans les lignes. Aucun état persistant ni Save/Load nouveau.
- Identité : nom de bras, graine, répétition, ancre physique, StationID et ordre
  temporel des événements. Si la station est invalide, manque ou semble
  recyclée, laisser le réemploi **incertain**, sans appariement par ville.
- Référence d'observation unique :
  `OpexAI[air_site_cost_quote=1,air_site_quote_keep_legacy_margin=1,probe_air_finance_margin=1]`.
  Les seuils/profits d'une éventuelle nouvelle politique ne sont **pas** testés.
- Smoke moteur : graine 42 × 1 an, `--script-debug`, campagne
  `air_orphan_reuse_smoke_42x1_20261009_r1`.
- Observation principale : 6 graines fixes **42, 100, 999, 1234, 5678, 2026**,
  trois ans, une répétition, campagne `air_orphan_reuse_6x3_20261009_r1`,
  `--script-debug` ; six parties solo. Une seule campagne moteur à la fois.
  Sur le PC Windows Docker local : 10 CPU, 8 Go, 10 workers et volume
  `openttd-lab-home`, image `openttd-lab:latest` dont le digest est figé
  dans le manifeste du harnais.
- Succès technique : six parties complètes/saines, logs exploitables avec
  champs obligatoires, coûts et dates vérifiables. L'absence de cas BFAIL
  conservé reste un résultat sans estimation du taux de réemploi.
- Sortie observationnelle : nombre d'orphelins conservés, actifs activés par
  première ligne de **même ancre et StationID**, délais en jours jeu,
  coût A historiquement immobilisé puis utilisé, actifs non activés et
  coûts A × jours écoulés (jusqu'à la borne de censure **si connue**),
  répartition par graine et incertitudes de jointure. Les lignes suivantes
  sont des usages supplémentaires, pas de nouvelles activations.

Cette télémétrie n'isole pas un effet causal sur le profit : instrumenter
peut déplacer le calendrier en consommant des opcodes. Le coût A réalloué
analytiquement à une ligne active n'est ni un revenu ni un remboursement.
Les seuls coûts de chantier n'établissent pas la valeur liquidable du terrain
ou de la station, et les observations sur trois ans sont censurées.

## Résultats

**Observation terminée** : smoke 42×1 `complete`, puis 6/6 parties `complete`
sur trois ans ; moteur `openttd-lab:latest`, image
`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
Même bundle smoke/6×3 :
`75c2ef599e6032693c6cdf9ffb06bba5b7da0126a5245b8f4a437b9b924823e1`.
Source : `results/air_orphan_reuse_6x3_20261009_r1.json`, JSONL,
manifeste, `results/air_orphan_reuse_6x3_20261009_r1_engine/` et
`results/air_orphan_reuse_6x3_20261009_r1_breakdown.json`.
Décodage : `sweeps/analyse_air_orphan_reuse.py`, jointures indépendantes par
fichier `reference_seedNN_r0.log`, sans mélange des bras/graines.

| Graine | A retenus | Première ligne confirmée | A sans usage observé | Coût A total | Coût A activé |
|---:|---:|---:|---:|---:|---:|
| 42 | 0 | 0 | 0 | 0 £ | 0 £ |
| 100 | 0 | 0 | 0 | 0 £ | 0 £ |
| 999 | 1 | 0 | 1 | 20 960 £ | 0 £ |
| 1234 | 1 | 1 | 0 | 17 415 £ | 17 415 £ |
| 5678 | 3 | 2 | 1 | 70 278 £ | 43 385 £ |
| 2026 | 3 | 2 | 1 | 59 879 £ | 42 779 £ |
| **Total** | **8** | **5** | **3** | **168 532 £** | **103 579 £** |

**5/8 (62,5 %) des actifs retenus ont alimenté une ligne AIR réellement
construite sur la même ancre et la même StationID**, avec 0 ligne antérieure
sur cette station au moment de cette construction. Réemplois à 214, 423, 484,
695 et 995 jours (médiane **484 jours**), trois fois comme endpoint B,
deux fois A. Aucun doublon ambigu ni avertissement de parser. Tous les huit
échecs de conservation naturels sont `BFAIL` ; la sonde prend aussi `HUBB`
en charge, non exposé ici.

Les **64 953 £** restants sont attribués à trois actifs sans première ligne
observée avant l'horizon ; leur perte, valeur à cette date et existence
physique finale n'ont pas été mesurées. `AIR_HUB_REUSE` a aussi détecté
**207 réutilisations ordinaires** sans provenance orpheline appariable ; ce
ne sont pas des faux positifs revendiqués ni des orphelins.

Pour calculer le proxy de temps immobilisé, le décodeur reçoit
`--end-date 720624`, **début exclusif de 1973** après trois années 1970–72.
La conversion est étalonnée sur les journaux de la même partie : événement
`AIR_FINANCE_TRY` 1970-04-15 et `AIR_HUB_REUSE` du même chantier
`date=719632` ; année 1972 bissextile. Les 5 délais avérés représentent
**61 377 726 £×jours** de capital A entre échec et première ligne.
Pour les 3 cas censurés : 168, 246 et 543 jours jusqu'au seuil, soit
**20 105 904 £×jours supplémentaires comme proxy conditionnel à la
conservation de l'aéroport jusqu'à la fin**, qui n'est pas prouvée par ces
événements. Total descriptif **81 483 630 £×jours**, sans taux d'intérêt,
actualisation ni conversion en pertes financières.

**Verdict diagnostique : la réutilisation d'A après BFAIL est réelle et
fréquente dans ce petit échantillon exposé.** Considérer tout `cost_a` des
BFAIL comme perte finale surestime les pertes ; considérer l'activation
comme remboursement surestime le cash. Aucun progrès économique causal
contre AAAHogEx n'est revendiqué, et aucune porte V102 ne s'applique à la
sonde. Il reste à vérifier la persistance des trois actifs censurés et les
profits réellement générés par les cinq lignes réutilisatrices ; le maintien
de la marge historique et des réglages de production est inchangé.
