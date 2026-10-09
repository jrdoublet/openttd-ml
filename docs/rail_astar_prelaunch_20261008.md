# Rail 1972–1975 — autopsie des plafonnements A* avant lancement (08/10/2026)

**État examiné :** `/openttd-ml`, `master`, HEAD `878fc56`, arbre local modifié
par d'autres chantiers. Audit du code courant et des journaux existants ;
aucune nouvelle partie pour ce diagnostic. Objectif : éviter les A* sans issue
en préservant les recherches `OK` et le profit réel d'OpexAI.

## Ce que signifie une issue A*

- `ABND` : `FindPath` a rendu `false` jusqu'au **budget d'itérations**.
  Cela ne prouve ni l'absence d'un chemin ni une impossibilité géométrique.
  La borne usuelle est 10 000, mais le budget de chaque candidat peut être
  inférieur ; garder la valeur réellement journalisée par recherche.
- `NOPA` : frontière épuisée (`FindPath == null`) ou préparation sans
  accès/pathfinder. Dans le second cas, aucune recherche A* n'a démarré.
  `DEAD` est une échéance de ticks ; `CONT` signifie tranche en cours.
- `OK` d'A* : tracé trouvé, **pas** chantier livré. `TRKFAIL`/`STNFAIL`
  sont des échecs après recherche, et `CASH` peut retenir un plan prêt.
- `search_in_progress` : refus de présenter une **autre** recherche dans le
  créneau `this._railSearch` ; les passages répétés de la même OD ne sont
  pas des recherches distinctes.

Sources : `ai/OpexAI/builder_rail.nut:446-478,1787-1829,1834-1926` ;
`ai/OpexAI/task_rail.nut:1153-1240,1243-1397,1401-1525,1664-1720` ;
`ai/OpexAI/pathfinder_v90/rail.nut:444-550`. Les coûts du pathfinder,
la voie existante, les virages, les pentes, ponts et tunnels importent.

## Mesures sur les tentatives réellement achevées

`results/rail_failure_audit_5x6_20261008_r1_engine/`,
`rail_failure_audit=1`, cinq graines `42,100,999,1234,5678`,
bras `reference` (`rail_cached_proximity_gate=0`) et
`rail_cached_proximity` (`=2`), 6 ans : **10 parties complètes**.
Extraction des seuls `RAIL_AUDIT stage=attempt` : **174 tentatives**, dont
**119 OK**, **21 ABND**, **20 TRKFAIL**, **10 STNFAIL**, **3 NOPA**, **1 SITEB**.
Les 21 ABND concernent **17 clés** `(partie, cargo, src, dst)` ; ni les
refus précoces ni les compteurs annuels de passages ne gonflent ce total.
Ce rejeu porte déjà la sonde ; il ne réhabilite pas le garde de proximité
ayant échoué économiquement à la porte A 40×5.

La concentration est réelle, mais ne fonde pas une interdiction de
destination :

| Partie | Événements observés sur la même destination | Interprétation |
|---|---|---|
| Référence seed42, `dst=33442`, PASS | 7 `ABND` entre 1972-12-09 et 1975-12-11 depuis plusieurs `src`, plus `TRKFAIL` et `STNFAIL` | Destination difficile sur ce parcours ; les gares exactes ne sont pas enregistrées |
| Référence seed999, `dst=44867`, PASS | `ABND` 1972-06-12 et 1972-10-29, puis `STNFAIL` 1973-07-22 | Même centre de destination, issue différente après la recherche |
| Référence seed1234, PASS | `27505→20901` `ABND` 1972-06-16, puis **`34710→20901` OK** 1973-06-23 | Contre-exemple à une mémoire par destination |
| Variante seed999, COAL | `21119→3445` `ABND` 1974-07-17, puis **`5260→3445` OK** 1975-01-01 | Contre-exemple fret |
| Variante seed5678, PASS | `56545→36830` `ABND` 1972-09-22 et 1974-07-31, puis **`44995→36830` OK** 1974-10-17 | Même **après deux ABND**, une autre origine réussit |

Un filtre fictif « même cargo et destination après un premier ABND » aurait
écarté **8 ABND ultérieurs** mais **3 vrais `OK` ultérieurs** sur ces dix
parties. Même un seuil de deux échecs écarterait le `OK` de seed5678.
Un filtre sur l'OD **exacte** n'aurait retiré que **4 ABND répétés**
et aucun `OK` observé ; il recouvre toutefois la mémoire de paire
`_abandonedPairs` déjà présente et ne prédit **aucun premier ABND**.
Ces comptages sont descriptifs, issus de deux politiques qui divergent ;
ce ne sont pas des observations indépendantes de vingt et une cartes.

### Recherches dont les 10 000 itérations sont directement attestées

Le diagnostic **distinct** `rail_freight_select_choice_real_3x6_20261008_r3_engine`
(graines 42/100/999, `decision_log=1`) conserve 77 `RAIL_ATTEMPT` :
35 `OK`, 34 `TRKFAIL`, 5 `ABND`, 2 `STNFAIL`, 1 `SITEB`.
**Quatre** des cinq `ABND` atteignent exactement `iters=10000` :

| Graine, date | Cargo, centres `src→dst` | Manhattan | Prédiction `pred_astar` | Profit/ROI prédits | Issue |
|---|---|---:|---:|---:|---|
| 42, 1972-10-26 | PASS `40153→33442` | 81 | 7 745 | 5 802 £ / 137 | `ABND` 10 000 |
| 42, 1973-10-13 | PASS `7810→10926` | 56 | 3 189 | 1 626 £ / 41 | `ABND` 10 000 |
| 100, 1974-07-02 | COAL `9424→29140` | 81 | 7 745 | 27 375 £ / 632 | `ABND` 10 000 |
| 100, 1974-10-15 | GOOD `11399→12595` | 89 | 10 266 | 66 103 £ / 1 369 | `ABND` 10 000 |

Le cinquième `ABND`, seed42 le 1973-11-15 sur
PASS `9157→10926`, consomme seulement **2 448 itérations** : il a un
budget moindre et n'appartient pas au groupe 10 000. Pour les quatre
plafonnements, `search_ops` vaut environ **10,8–13,3 millions**,
aucun devis final ni pose. La distance `≥56` aurait supprimé les quatre,
mais aussi **22/35 OK** ; `≥81` en supprime trois et perd **4/35 OK**.
Des `OK` atteignent Manhattan **90 et 94** après 235–4 108 itérations.
`pred_astar` ne sépare pas mieux ces trajectoires puisqu'il est lui
aussi dérivé d'une estimation préalable grossière. Les `ROI` montrent
qu'une recherche plafonnée peut correspondre à un projet pourtant
estimé très rentable ; le ROI ne détecte pas une absence de chemin.

Le rejeu `rail_freight_current_5x6_20261008_r1.jsonl` conserve aussi
**six** panneaux `OR/OB` avec `ABND`, budget et consommé à 10 000,
distances `[84,77,78,80,86,88]` ; leurs clés
`(seed, année, line_id, posPacked)` sont respectivement
`(100,1972,29,30)`, `(100,1974,41,274)`, `(1234,1972,27,31)`,
`(5678,1972,41,524)`, `(5678,1973,48,31)` et
`(5678,1975,60,87)`. Les panneaux **ne portent ni cargo, ni OD,
ni accès aux gares** et leur rétention n'assure pas l'exhaustivité ;
une clé OR/OB de seed5678 reste ambiguë. Ne pas réunir ces six
panneaux et les quatre tentatives instrumentées en un échantillon
apparié : ce sont des parcours distincts.

Sur `rail_blocker_seed999_1x6_20261008_r1`, une recherche primaire fret
`35675→55122` occupe le créneau pendant **432 jours observés** et atteint
**9650/10000** au 1975-12-25. Elle est **encore en cours** à cette date :
ne pas la compter comme `ABND` achevé. Les **232 blocages pax** sont des
présentations répétées face à cet occupant. Sur l'autre trajectoire du
rejeu, les upgrades dominent l'occupation ; ce ne sont pas des preuves
sur une même recherche ou un même terrain.

## Évaluation des prédicteurs disponibles *avant* A*

| Signal | Observation et risque | Décision |
|---|---|---|
| Distance Manhattan | Distributions `OK` et `ABND` presque superposées dans V100 | Réfuté ; aucun seuil |
| 16 points de relief sur la droite V101 (`rough`, `steps`, `hspread`) | `rough≥10` écarte 2/6 ABND pour 0/29 OK ; `rough≥4` écarte 6/6 mais **16/29 OK** ; ne représente pas le corridor d'un vrai tracé | Insuffisant selon le critère préenregistré |
| Historique d'échec sur le centre de destination | 8 ABND repérés, mais 3 OK supprimés ; variation d'origine et de plateforme | Rejet du filtre |
| Historique d'échec sur la paire OD exacte | 4 ABND répétés, 0 OK supprimé dans cet échantillon ; mémoire/cooldown de paire déjà existants | Pas de nouveau mécanisme |
| Accès de quai, voisins constructibles, corridor élargi, obstacles/ponts/tunnels | Faisables à sonder localement mais **pas journalisés en entrée** pour les ABND et OK actuels ; accès de station testé avant A* sans garantir la voie | Aucun seuil validable actuellement |

`OpexRailPlatformPlans` (`builder_rail.nut:160-215,280-404`) produit des
quais candidats avec `[lead,station_exit]` et teste le placement de gare
en `AITestMode`. Le pathfinder reçoit **plusieurs** départs et buts
(`:415-438`). `src`/`dst` dans `RAIL_AUDIT` désignent les centres du
candidat, **pas** les quais effectivement proposés, encore moins les
obstacles rencontrés. Le code ne consigne pas la frontière A* ou la
part du détour effectué. Une difficulté corrélée à `dst` n'établit
donc pas quel obstacle, quel relief ni quel choix de quai la cause.

## Décision et condition de réouverture

**Aucun prédicteur ex ante nouveau n'est assez précis pour autoriser un
filtre. Aucun correctif comportemental, aucune sonde NoAI supplémentaire
ni campagne Docker ne sont justifiés par les données présentes.** Les
réglages existants conservent leurs défauts ; le 40×5 de la garde
`rail_cached_proximity_gate` conserve son verdict `fail_primary`.

Si une preuve **nouvelle** d'échec d'accès apparaît, mesurer d'abord, sous
un seul réglage de sonde OFF au défaut, les `nA/nB`, `length`, couples
ordonnés `[lead,station_exit]`, possibilités locales et contraintes
de voisinage **avant** A*, puis un identifiant de recherche stable,
`stop/iters/budget` à l'issue et le résultat de construction. Couvrir
primary **et** upgrade sans joindre par date/OD seuls (réessais), mesurer
les opcodes ON et l'identité des décisions OFF. Séparer graines de
développement et graines de validation avant de choisir tout seuil.
Exiger une part substantielle des plafonnements éliminés pour **au plus
un `OK` perdu** sur graines indépendantes. Ensuite seulement, un réglage
de filtre à défaut 0, smoke et porte A appariée **40×5** (gain V102
≥4 %, Wilcoxon p<0,05, IC95 bootstrap bas >0, valeur ≥−5 %) puis B20×10
si A passe. Une libération de créneau sans plus de constructions rentables
reste une non-qualification.

## Suite du 09/10 — mesure des accès avant A*

La suite autorisée a été exécutée sous **`probe_rail_preastar=1`**
uniquement en observation, avec identifiant de recherche et accès
réels aux quais avant `FindPath`. Le smoke OFF/ON 1×1 est sain et
la collecte cinq graines × six ans comprend **43 A* OK, 7 ABND au
plafond de 10 000 et 4 recherches en cours**. Les mesures de voisins
constructibles ne discriminent toujours pas les abandons sans perdre
des réussites : `nb≤1` donne 2/4 ABND et 1 OK perdu en développement,
puis 0/3 et 1 OK perdu sur les graines réservées ; `bmin≥3` ne se
transfère pas davantage. [Rapport complet et protocole](rail_preastar_probe_20261009.md).
**Aucune activation comportementale ni porte économique.**
