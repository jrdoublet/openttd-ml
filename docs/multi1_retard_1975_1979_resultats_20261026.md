# MULTI-1 — autopsie tardive C63, bilan descriptif 1975–1979 (26/10/2026)

**Statut : diagnostic terminé et intègre ; aucun cinquième levier ON qualifié.**
Le symptôme dominant est un portefeuille de projets qui ne débouche plus sur
des chantiers neufs, malgré la trésorerie. La classe C63 « invalid » est une
classification **résiduelle de la passe**, pas une preuve de faisabilité
physique ni une mesure directe des refus par type de site. Aucun mécanisme
nouveau suffisamment exposé ne permet encore une porte A, qui reste réservée
à une variante pré-enregistrée et effectivement construite.

## Références et qualité

- Protocole [figé et publié **avant** la simulation](multi1_retard_1975_1979_protocole_20261026.md),
  commit `340545cc`, cible 1975–1979, 256² et cinq graines appariées
  `42,100,7,999,2026` ; 11 ans simulés pour vider l'année 1979 en janvier
  1980. Source gelée `340545cc3f0a56f0d1231b4d2b4e997498cf7078`.
- Bras témoin `OpexAI[probes=2]`, bras C63 `OpexAI[probes=131074]` ;
  AAAHogEx-115 sur chaque carte partagée. Campagne
  `multi1_late_c63_5x11_20261026`, bundle SHA256
  `7aeeaec516aef86236a16cc25e05e8a7c702deafab0e61247a8e57834d0414f1`,
  manifest SHA256
  `8e70dfb4ea61adc33c4a4eff5bfbc4a2ebd87c50e2d1a2f89f85485991365be3`,
  image `openttd-lab:latest` SHA256
  `f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`.
  Résultat `results/multi1_late_c63_5x11_20261026.json`, journal par
  politique/graine sous `results/multi1_late_c63_5x11_20261026_engine/` ;
  agrégat reproductible
  `results/multi1_late_c63_5x11_20261026_analysis_v2.json` issu de
  `python -X utf8 sweeps/analyse_multi1_late_c63.py --engine-dir results/multi1_late_c63_5x11_20261026_engine --seeds 42 100 7 999 2026 --out results/multi1_late_c63_5x11_20261026_analysis_v2.json`.
- **10/10 parties complètes, cinq paires sur cinq, 0 échec de simulation,
  couverture métrique complète, zéro erreur Squirrel trouvée**. Les 25
  vidanges `phase=opp`/`phase=opp_absent` et les 125 `phase=spend`
  (cinq modes × cinq années × cinq graines) ont été vérifiées sans
  avertissement ; aucune année 1975–1979 manquante et aucune identité de
  ligne dupliquée dans ses relevés annuels. Smoke 1×2 sain
  `multi1_late_c63_smoke_20261026`, source identique.

## Vieillissement économique mesuré sur les cinq mondes C63

Moyennes **par monde**, années comptables closes. Une nouvelle ligne
correspond à un `n_ok` de chantier d'infrastructure, tandis que `fleet`
compte des interventions de flotte réussies, pas le nombre de véhicules.

| Année | Caisse décembre | AIR neufs | RAIL neufs | Jours « invalid » | Jours « unaffordable » | AIR mature réel/prédit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1975 | 3,31 M£ | 0,4 | 1,2 | 146,8 | 5,8 | 51,2 % |
| 1976 | 6,12 M£ | 0,2 | 0,2 | 230,0 | 0,0 | 58,6 % |
| 1977 | 9,09 M£ | 0,4 | 0,4 | 138,6 | 0,0 | 65,0 % |
| 1978 | 12,50 M£ | 0,0 | 0,8 | 148,0 | 0,0 | 69,5 % |
| 1979 | 16,27 M£ | 0,2 | 1,6 | 172,2 | 0,0 | 76,3 % |

Sur 1975–1979 **cumulés, moyenne par monde** : **1,2 AIR**,
**4,2 RAIL**, **0,2 ROUTE** construits ; dépense de construction réelle
réussie **46,8 k£ AIR**, **296,2 k£ RAIL**, **2,5 k£ ROUTE**, et
**2,310 M£ pour 39,6 interventions de flotte**. Ne pas imputer les
interventions de flotte à un mode sans leur décomposition véhicule/ligne.

Répartition des jours entre passes C63, **cumul moyen sur les cinq années**
(des états mutuellement exclusifs au cours du temps, pas des projets
uniques) :

| État | Jours / monde, 1975–1979 | Lecture possible |
| --- | ---: | --- |
| `invalid` | **835,6** | Projet restant rejeté ou invalide selon raison résiduelle |
| `absent` | **273,0** | Aucune alternative éligible retenue dans la passe |
| `waiting_compute` | **134,2** | Recherche encore occupée, borne de latence |
| `unaffordable` | **5,8** | Financement observé comme obstacle |
| `demand` | **0,0** | Aucune classe dominante explicite de cette sorte |
| `launched` | **572,4** | Une ou plusieurs constructions au cours de la passe |

`invalid` représente ~**45,9 %** des ~1 821 jours classés et
~**66,9 %** des jours sans construction classés. Ce n'est **pas**
un taux de chantier impossible : `OpexC63ClassifyOpportunity()`
(`ai/OpexAI/probes.nut:1358-1367`) convertit tout motif non explicitement
reconnu en `invalid`, et `OpexC63NotePass()` (1453–1523)
n'examine qu'un premier reliquat et les raisons collectées dans
`passDiscards`. La classe ne prouve ni le coût CPU ni le type de
contrainte physique. Sous `absent`, les sous-motifs moyens cumulés sont
notamment `cache_exhausted` ~99,8 jours et
`abandon_filtered` ~135,8 jours : des filtres/abandons déjà intégrés
au moteur contribuent à rétrécir le vivier.

**Profits des lignes matures (âge ≥2 ans) en 1979, par monde** :
AIR ~**43,4 lignes**, prédiction initiale **4,668 M£/an**, profit réel
**3,561 M£/an** (**76,3 %**) ; RAIL ~**27,2 lignes**,
prédit **0,822 M£/an**, réel **0,924 M£/an** (**112,4 %**),
~2,2 lignes déficitaires. ROUTE ~1,6 ligne, profit réel ~6,4 k£/an.
Ce sont des bénéfices annuels par ligne, **pas la mesure causale du gain
marginal de l'achat d'un train ou d'un avion supplémentaire**. La
prédiction AIR est celle stockée à la création, alors que les flottes
et les conditions changent jusqu'en 1979 ; interpréter l'écart
uniquement comme une surestimation initiale serait abusif.

Sur les **cinq graines** de l'instrumentation, fin 1979,
les caisses sont **7,74 à 21,73 M£**, et
`unaffordable_d=0` sur chacune. Ce résultat réfute ici l'idée que la
trésorerie empêche généralement les nouveaux investissements **observés**.
Il ne garantit pas l'existence d'alternatives physiquement constructibles.

## Confirmation et limites de la compétition

Le témoin sans C63 de **cette même petite cohorte**, fin 1979,
réalise **4,142 M£/an** Opex contre **7,385 M£/an** AAA,
soit **56,08 %**. Le bras instrumenté est à **4,487 M£/an**
contre **6,989 M£/an** AAA (**64,20 %**). L'écart **ne mesure pas le gain
d'une politique** : activer les sondes modifie les opcodes, la cadence
et parfois la trajectoire du concurrent de cette autre partie.
À la fin de la 11e année simulée, l'écart instrumenté−témoin Opex
est **+255 016 £/an** sur cinq paires,
`diagnostic_only`, 4/1/0, IC95 bootstrap incluant zéro
(~[−13 129 ; +429 945] £/an). Ni `gain_short` ni
`non_erosion` n'ont été réalisés ou pré-enregistrés pour ce bras.

L'**ancien contrôle 20×10**, référence historique différente
`83e436cc`, reste le meilleur constat descriptif de l'écart
stratégique : **87,44 % en 1974**, **74,48 % en 1975** et
**56,55 % en 1979** (voir
[analyse dix ans](multi1_horizon_10ans_20261026.md)).
Entre 1974 et 1979, Opex gagne seulement **4,75 trains par monde**
contre **31,60 AAA** ; la hausse du bénéfice annuel
**+1,423 M£ Opex** est loin de **+4,203 M£ AAA**.
Les panneaux ferroviaires retenus présentent 133 `SITEAB` parmi
277 observations `OR` de 1975 à 1979, mais sont **échantillonnés et
non uniques** : ils ne certifient pas 133 paires indépendantes
impossibles. Les journaux moteur de cette cohorte historique sont vides,
et elle n'est pas interchangeable avec la nouvelle cohorte instrumentée.

## Décision technique et suite de MULTI-1

**Diagnostic qualitatif renforcé : manque d'expansion neuve malgré caisse
abondante ; priorité aux motifs de validité / vivier / faisabilité, avec
possibilité concurrente de performance AIR insuffisante.** H1 (éviction
de l'AIR par le RAIL faute de capital) ne rend pas compte des années
1975–1979 ; H2 (opcodes) n'est pas démontrée par le seul classement
`waiting_compute` ; H3 (la croissance d'AAAHogEx) reste un facteur
de comparaison réel. Le tableau ne départage pas la part du filtrage
logique, de l'impossibilité physique du tracé, de la saturation de site,
des plafonds de modes, ni du revenu d'une ligne supplémentaire.

**Aucun nouveau levier ON admissible à ce stade** : la préqualification
historique ROUTE n'avait trouvé aucun plan physique valide ; les
vidanges C63 ne contiennent pas d'identité de couple rentablement
constructible. La prochaine expérience défendable serait un **SHADOW
étroit sur les projets RAIL/ AIR rejetés après 1974**, avec motif exact,
identité unique, coût d'opcode, financement, validité de site et trace
physique `AITestMode` bornée ; ne pas réutiliser les filtres RAIL
déjà refusés, ni toucher le travail P1 géré sur VPS. Ce sous-lot
doit faire l'objet d'un pré-enregistrement autonome avant code et
d'une preuve de candidat constructible/exécutable avant tout ON.
Les portes historiques A 40×5 / B 20×10 et le seuil stratégique
≥75 % restent inchangés. **MULTI-1 ouvert, zéro adoption, aucun défaut
modifié.**
