# C121 — graines les plus perdantes des trois portes B (04/10/2026)

## Périmètre et décision

Campagne `c121_B3_20261004_075644` : trois comparaisons indépendantes, 20 graines
appariées × 10 ans chacune, référence C121 economics=1 et catalogue incrémental=1.
Les trois B sont complètes et saines, `pass non_erosion` ; les trois A conservent
`fail_primary`. L'utilisateur décide néanmoins d'adopter les trois réglages :
**adoption explicite, sans qualification V102 complète et sans mesure économique
de leur cumul**. C115=1 reste protégé ; C121 economics et catalogue restent OFF
dans les défauts livrés. Les conclusions de ces B concernent leur profil C121.

La fenêtre comparée est phase=0→4 **avec live=1 commun** : elle ne compare pas
l'activation live 0→1. Phase est un nombre d'années, pas un booléen. Pour conserver
la fenêtre de quatre ans choisie, les défauts sont live=1 et phase=4 ; interprétation
explicitée à l'utilisateur après la demande de clarification restée sans réponse.

## Classement descriptif

Critère de sélection fixé : les trois plus gros deltas négatifs de `profit_year`
Opex variante−référence à l'année terminale 1979, dans chacune des trois B.
Ce sous-ensemble explique les pertes ; il ne remplace aucun verdict ni échantillon.

| Réglage | Graine | Perte k£/an | Perte % | Avions réf.→var. | Aéroports réf.→var. | Première divergence du nombre d'avions |
|---|---:|---:|---:|---|---|---|
| Hub-hub | 73 | −311,54 | −10,04 | 200→200 | 30→31 | novembre 1971 |
| Hub-hub | 8191 | −262,08 | −11,95 | 200→153 | 29→26 | février 1971 |
| Hub-hub | 65537 | −220,10 | −14,26 | 121→148 | 23→20 | avril 1971 |
| Live 4 ans | 42 | −430,48 | −21,92 | 200→194 | 29→26 | janvier 1971 |
| Live 4 ans | 1 | −271,96 | −14,88 | 174→200 | 20→24 | juin 1971 |
| Live 4 ans | 999 | −197,72 | −11,21 | 99→136 | 18→17 | mars 1973 |
| Adaptatif | 73 | −579,06 | −18,73 | 200→200 | 30→26 | janvier 1971 |
| Adaptatif | 1024 | −374,68 | −24,88 | 199→193 | 30→26 | mai 1970 |
| Adaptatif | 8191 | −314,67 | −14,94 | 199→154 | 29→26 | novembre 1970 |

Les compteurs proviennent du décodeur physique déjà appliqué par le harnais :
aucun comptage de `VEHS` brut. Les dates sont celles des sauvegardes mensuelles,
pas des timestamps muraux des logs. Aucun des neuf cas ne fait faillite.
Les bras individuels ont chacun leur référence : ne pas confondre les références
des trois campagnes, même sur une graine identique.

## 1. Adaptatif : la correction économique n'est pas exposée

**Établi : 20/20 variantes verrouillent `regime=race`**, avec deux années observées.
`projects_models.nut::OpexC121RealizationFactor` renvoie alors 1.0 :
la réduction adaptative du revenu prévu n'est pas appliquée. L'écart de profit
ne démontre donc pas son utilité ou sa nocivité. Le classifieur est one-shot :
il ne change plus de régime après le verrouillage.

Les pires graines confirment des divergences précoces, antérieures au verrouillage :
1024 dès mai 1970, 8191 dès novembre 1970, 73 dès janvier 1971.
À la classification, 73 et 8191 n'ont aucune ville sous pression dans
l'échantillon consulté ; 1024 en a deux, en dessous du minimum de trois.
Le collecteur parcourt les villes déjà consultées par la sélection et conserve
leurs minimums de slots ; ce n'est pas un recensement représentatif de la carte.

**Hypothèse prioritaire :** les tables, boucles et branches supplémentaires
modifient la cadence des passes et constructions dans une course aux emplacements.
Le code l'autorise et les divergences précoces le rendent plausible ; les B
n'ont pas les compteurs d'opcodes nécessaires pour le prouver. Le verrouillage
précoce et l'échantillon de villes conditionné par la politique peuvent aussi
expliquer l'absence totale du régime efficiency. Ne pas appeler cela une
correction de profit trop forte.

**Piste :** commencer par un témoin de collecte à facteur forcé à 1, et comparer
les traces d'élection et dates de construction ainsi que les opcodes du collecteur.
Mesurer ensuite en shadow les seuils 3 villes / 650‰ contestables / ≤200‰ libres
et les classifications plus tardives. Ne pas abaisser les seuils immédiatement :
le one-shot évite une rétroaction documentée, que toute nouvelle règle doit préserver.

## 2. Hub-hub : effet différent du nom du réglage sous C121

**Établi :** `air_planning.nut` collecte les revenus moyens des hubs quand
`AIR_HUBHUB_MARGINAL` est actif (vers la ligne 1374), mais les deux déductions
de cannibalisation (1565/1583) exigent `!C121_AIR_ECONOMICS`.
Elles sont donc neutralisées dans ces B. Les gardes hub-hub des choosers C116
et C118 sont également derrière leur retour anticipé C121 : elles ne sont pas
une explication des différences de ces B. Reste notamment le travail de collecte
supplémentaire et ses effets possibles sur la cadence.

Les pertes n'ont pas une cause physique unique :

- **73 :** 200 avions dans les deux bras, mais moins d'événements de construction
  hub-hub (111→83), moins de véhicules rail (14→9), et 31 aéroports contre 30.
  Avoir atteint le plafond de flotte ne garantit pas les mêmes routes ni les mêmes revenus.
- **8191 :** 200→153 avions et 29→26 aéroports ; trésorerie 6,06→8,86 M£
  malgré le profit plus faible et une valeur terminale supérieure de 0,97 M£.
  Signal d'expansion ou d'allocation insuffisante, plutôt que preuve d'insolvabilité.
- **65537 :** 121→148 avions sur moins d'aéroports, et davantage d'événements
  hub-hub (61→85), pour moins de profit. Signal compatible avec concentration de
  capacité peu productive ; sans débit ni profit réalisé par ligne, congestion,
  dilution de la demande et choix des routes restent des hypothèses.

**Piste :** fixture à entrées identiques pour quantifier le scan marginal inutile
sous C121, puis témoin de cadence. Pour 65537 et 73, suivre les lignes et
renforcements avec profit réalisé, occupation et rotations avant toute pénalité
supplémentaire. Une optimisation supprimant le scan exige son propre gain mesuré
et la règle de neutralité opcodes ; aucune modification comportementale faite ici.

Hors C121, le réglage déduit effectivement la cannibalisation. Les B C121 ne
qualifient pas cet effet sur C115, qui reste le profil livré par défaut.

## 3. Live quatre ans : séparation du cutoff et des divergences antérieures

**Établi :** phase=4 limite seulement l'override live du premier passage 1→2 aux
quatre premières années globales de partie ; après, le chemin standard reste
disponible. Cette borne ne signifie pas « chaque ligne jusqu'à quatre ans ».

Pour les trois pires graines, le nombre d'avions diverge **avant 1974** :
1971 pour 42/1, 1973 pour 999. Sur 42, le delta annuel est déjà −141,00 k£ en
1971 et −140,48 k£ en 1972. On ne peut attribuer ces pertes initiales au cutoff
de la quatrième année. Une branche supplémentaire ou un décalage de scheduling
est plausible ; aucune mesure d'opcodes n'est disponible pour trancher.

- **42 :** capacité terminale proche (200→194 avions) mais trois aéroports de moins,
  plus de rail (5→14), davantage d'événements hub-hub (91→106).
  Piste de géographie/répartition des investissements, pas simple manque d'avions.
- **1 :** davantage d'avions et d'aéroports, moins de profit et une trésorerie
  inférieure d'environ 2,45 M£. Surinvestissement ou rendement des routes à examiner.
- **999 :** capacité passagers 29 700→40 800, flotte 99→136, un aéroport de moins,
  trésorerie 4,66→1,85 M£. Davantage de capacité ne se transforme pas en profit ;
  hypothèse de concentration/renforcement trop peu productif à mesurer.

Le critère `balanced90` accepte ≥50 jours, ≥2 trajets, profit positif et
(load≥0,40 **ou** attente normalisée≥0,50). Il n'exige pas un trajet par sens,
contrairement à `strict90`. L'attente est du cargo en station, pas le temps
d'attente d'un avion ; les observations mensuelles n'établissent ni départs pleins,
ni rotations ni congestion. Les compteurs `actual_profit` de construction sont
des prévisions du modèle et ne peuvent valider les profits réalisés.

**Pistes :** comparer les premiers événements qui divergent avant le cutoff ;
puis isoler les 1→2 post-année4 refusés/admis et leur contribution marginale réalisée.
Sur 1/999, shadow d'un critère de deux sens effectivement servis et du rendement
marginal avant/après 1→2. Tester séparément chaque correction, sans changer simultanément
seuils, durée et priorité AIR. Une fenêtre de quatre ans n'est pas à allonger
après sélection du meilleur horizon sur ces mêmes résultats.

## Ordre proposé et preuves à obtenir

1. **Attribution/cadence**, priorité haute : 1024 adaptatif, 8191 commun,
   42 live ; traces minimales, contrôle de perturbation ON/OFF et fixture opcodes.
   Objectif : premier choix/date divergent et coût du code activé sans correction.
2. **Productivité et allocation**, 65537 hub, 999 live, puis 73/1 :
   profit réalisé et capital par ligne, trafic par sens, flotte et emplacements.
   Objectif : séparer manque d'expansion, concurrence et renforcement non rentable.
3. **Correction isolée**, seulement après exposition : suppression de scan inutilisé,
   ou admission 1→2 mieux étayée, ou classifieur mieux exposé. Une seule intervention,
   pré-enregistrement et validation dédiée selon comportement/opcodes.

Aucun nouveau banc économique lancé pour ces pistes ; aucune cause de congestion
ou de cannibalisation démontrée. Les modifications livrées concernent les défauts
demandés ; les solutions restent des propositions.

## Provenance et lecteur

JSON/JSONL/manifestes/bundles/logs originaux préservés dans
`results/c121_nuit_20261003_203842/snapshot/results/`, préfixe
`c121_B3_20261004_075644_`, suffixes des trois paramètres ci-dessus.
Bundle commun :
`212039023d0c7ad37b36738c87f9fc7143bc17d99ee7dad0a6701870feefff5d`.

Lecteur hors ligne : `python -X utf8 -m sweeps.analyse_c121_b_losing_seeds`.
La sortie neuve `results/c121_adoption_20261004/losing_seeds.json` conserve
les hashes des trois JSON/JSONL et des logs inspectés, les deltas, les trajectoires
annuelles, les inventaires terminaux, les premiers écarts de flotte et les vingt
classifications. Le lecteur réutilise `diag_c121_postbuild.parse_fields` et
`inspect_c121_investments` pour les événements propriétaire 0. Les nombres
d'événements de construction ne sont pas un inventaire des lignes terminales.

Sources de code (identiques au bundle pour les méthodes étudiées) :
`projects_models.nut::OpexC121RealizationFactor`,
`projects_selection.nut::OpexC121PressureAdvanceYear/OpexC121RecordPressureSnapshot`,
`air_planning.nut`, `air_engine_choice.nut::OpexC116ChooseBuildPlan/OpexC118ChooseBuildPlan`,
`task_air.nut` et `probes.nut::OpexC121FirstLiveObserve`.
