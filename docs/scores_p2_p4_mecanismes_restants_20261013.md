# P2/P4 OpexAI — investigation complémentaire des mécanismes restants

**Date : 13 octobre 2026.** Cette étude complète, sans remplacer, la
qualification indépendante `docs/scores_p2_p4_qualification_independante_20261013.md`.
Le rejet de la garde AIR P4 sur 40×5 indépendant reste acquis
(**−52 352,375 £/an**, 14V/25D/1E) ; les autres politiques rejetées n'ont
pas été relancées. La clôture antérieure du plan ne constitue pas une preuve
universelle qu'aucun estimateur futur ne pourrait gagner.

## Nouvelle preuve

Nouvel audit hôte sur cinq graines P4 matched, basé sur les journaux originaux
`AIR_BUILD` / `RAIL_BUILD` / `LINE_REVENUE` : parmi les routes appariées
de même jour de construction et de même nombre de véhicules au rapport,
**110/150 ont un profit différent au rapport 1973**, puis **132/140 au
rapport 1974** (AIR 121/122 et RAIL 11/18 dans ce dernier groupe).
Ces rapports portent sur l'exercice précédent, pas sur le profit terminal
1974. La comparaison met en évidence des confondeurs majeurs (ordres,
historique de flotte, rival, hubs, notes, calendrier et bruit A/A), **pas
une externalité causale chiffrable**.

Les autres obstacles ont été recoupés : **18 crashes AIR** sur les cinq
graines P4 matched ON (dont dix en 1974), 311/546 lignes-années AIR
acceptées et 35/81 RAIL pour vyear ; seulement **43 lignes P2 strictes**,
55 descriptives, 102 lignes tôt construites ; trois flips C77 froids
admissibles sans construction de leur alternative dans le témoin. Des
**3 319 `.sav`** physiques retrouvés dans d'autres campagnes, aucun
n'appartient au bundle P2 nécessaire pour ces contrefactuels, ni au P4
matched 5×5. Les sauvegardes d'autres mondes/bundles ne sont pas
interchangeables.

## Décision économique

**Aucun nouvel estimateur comportemental sans coefficient arbitraire ne
franchit actuellement la porte d'identification** : il manque profit des
sortants, historique complet de flotte, effet sur services voisins et,
surtout, rendement net de l'alternative non construite à partir du même
état. Les mécanismes proches effectivement testables (`fresh_equal`,
`partial`, garde AIR, stable-cohort) avaient déjà échoué à leurs portes
économiques. Les informations nouvelles ne justifient ni un nouveau
40×5 ni une micro-variante choisie après résultats.

**Rapport complet, protocole de collecte contrefactuelle minimale, script
reproductible, reçu JSON et tests :**

`results/scores_p2_p4_network_stage_20261013/docs/scores_p2_p4_mechanismes_restants_20261013.md`

Worktree créé exclusivement depuis V166 `7ecbabe` ; **aucun `.nut` modifié**,
aucun Docker supplémentaire, aucun commit/merge/push. Cette décision est
bornée par les archives disponibles et **ne démontre pas l'impossibilité
d'une amélioration future** : une intervention sur un état sauvegardé
avant un vrai flip C77 et des replays A/A appariés pourraient la rouvrir.
