# ROAD100-4 — flotte de bus intra-ville sous observation

Pré-enregistrement ROAD100-4, 27/10/2026, avant tout banc.

Le duel route seule graine 42 à un an constate AAAHogEx 53 véhicules bus,
8 gares routières de voyageurs ; OpexAI 8 camions, aucun bus (baseline).
`OpexRoadPhysicalVehicleCap(1,1)=2` limite actuellement le modèle à deux
véhicules pour une ligne à un arrêt à chaque bout, pour prévenir la congestion
documentée. Un tel plafond empêche a priori de reproduire des services ayant
6 bus ou plus pour chaque arrêt, dont les effets de bouchon et la capacité
**réellement livrée** restent à mesurer.

Variation strictement isolée : avec `road100_town_bus=1`,
`road100_pax_fleet_cap=0` conserve le plafond 2 (référence). La valeur
`8` autorise le modèle économique et le constructeur à considérer jusqu'à
huit véhicules sur UNE liaison de bus intra-ville, **sans** changer le site,
les paires, la demande, le score, les coûts unitaires, les ordres, la cadence,
ni les gardes financières. Interruption conservée si la flotte est non rentable
au modèle après le tracé réel, ou si la caisse/les slots manquent.

Le chemin garde `road100_solo_pax=0`, `road100_town_voirie=0`,
`road100_road_batch=0`. La valeur 8 n'est pas recommandée avant qualification :
un quai congestionné peut réduire le profit malgré une flotte plus grande.
La dimension N=8 est pré-sélectionnée pour tester explicitement le goulot,
aucune optimisation a posteriori du plafond avec les graines favorables.

Smoke causal 42×1 an avec `--script-debug --line-telemetry` et la même AAAHogEx
ROUTE seule, puis diagnostic 5×1 `42,100,7,999,2026` pour vérifier le nombre
de bus, les livraisons, revenus et coûts de chaque nouvelle ligne. Si le
profit Opex augmente clairement sur les 5 graines et santé complète,
effectuer un 40×5 apparié par année ; sinon NO-GO.

Le niveau 0 reste le défaut aux quatre difficultés, et la condition
`ROAD100_TOWN_BUS` interdit son activation multimodale. Qualification par
les portes V102 si un défaut est envisagé. Aucun commit ni publication.
