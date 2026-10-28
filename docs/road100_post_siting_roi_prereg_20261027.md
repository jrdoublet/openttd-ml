# ROAD100-5 — filtre de rendement après tracé des lignes de bus locales

Pré-enregistrement avant code ou mesure du lot ROAD100-5, 27 octobre 2026.

Les diagnostics ROAD100-2 et 2b ont prouvé l'exposition du générateur local
mais n'ont pas fait croître le profit moyen OpexAI. Plusieurs `ROAD_BUILD`
locaux portent un profit annoncé inférieur à 500 £/an pour un investissement
de 6 à 10 k£. Une vérification de rentabilité seulement positive après
calcul du tracé permet encore ces acquisitions peu productives.

**Hypothèse isolée :** après `OpexRoadPlanFor` et
`OpexRoadLineEconomics` avec distance réellement trouvée, rejeter une
candidate `kind=pax` dont `srcTown == dstTown` si le profit annuel net
estimé est inférieur à **25 % du capital calculé**. Le réglage nouveau
`road100_town_roi_post=0` aux quatre difficultés ; la valeur `1` ne s'active
que dans les parties ROAD seule avec `road100_town_bus=1` et
`road100_town_voirie=1`. Aucune modification de l'estimation, du
constructeur ou de la cadence : le trajet est d'abord tracé et testé,
le coût réel d'exécution de la recherche reste à la charge du candidat.

Sondes sous `DECISION_LOG`: `ROAD100_TOWN_ROI action=reject|keep` avec
profit, capital, ROI en ‰, ligne source/destination, et motif de rejet
`road100_town_roi_post`; aucune dépense ni construction pour les refus.

La référence du duel utilise `road100_town_bus=1,road100_town_voirie=1`
et filtre post-site OFF ; seul le filtre est ON en variante. Les deux bras
ont `road100_solo_pax=0`, `road100_road_batch=0`, `road100_pax_fleet_cap=0`
et `estim_unifie=31`, adversaire AAAHogEx ROUTE seule. Smoke 1×1 graine42,
puis diagnostic 5 graines × 1 an (42,100,7,999,2026), mêmes réglages et
bundle dans chaque campagne. Poursuivre vers 40×5 uniquement avec effet
positif plausible, santé et exposition démontrées. L'objectif est le
profit réel Opex, pas le nombre de refus ni la valeur de compagnie.

L'ancien `road100_town_bus=1` reste non qualifié. La qualification éventuelle
du nouveau filtre dépendrait aussi des portes V102, dont B sur autorisation
spécifique. Aucun défaut changé, aucun commit/push implicite.
