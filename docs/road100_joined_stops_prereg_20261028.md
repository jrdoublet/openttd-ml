# ROAD100-8 — couverture des gares de bus par arrêts satellites joints

Préréservation du 28/10/2026, postérieure aux résultats négatifs v4,
**avant toute expérience ROAD100-8**.

## Question

Le site-first v3 admet 12 plans sur 5 graines à 21–34 voyageurs/mois, tous
dimensionnés à un autobus (prévision de profit annuel 26–866 £) ; la variante
v4 refuse le fallback qui produisait de faux plans site-first, mais ne gagne
que +37,2 £/an (p=1) et perd 61,2 % de valeur d'entreprise sur 5×1. AAAHogEx
étend ses stations routières avec des quais joints, et TownBus peut avoir
plusieurs arrêts indépendants avec plusieurs ordres : ces comportements sont
distincts et ne permettent pas de supposer une augmentation automatique du
profit par bus.

## Intervention isolée et règles

- Nouveau réglage `road100_joined_stops=1`, défaut **0 aux 4 difficultés**,
  seulement si `road100_site_first=1`, `road100_solo_pax=1`, et ROAD seul.
- Une liaison site-first dont les deux vrais terminaux sont construits avec
  succès peut tenter **au maximum un satellite passagers supplémentaire par
  terminus**, joint au *même StationID* ; la ligne reste à **deux ordres** et
  conserve ses champs historiques de persistance. Ne pas toucher au fret.
- Sélectionner sur routes existantes, proche de la gare principale dans
  `station.station_spread` (rayon de recherche borné), sans autre station
  occupant la tuile. Exiger captage **marginal non recouvrant**, et une
  connexion via le graphe de route (BFS borné). Tester un essai de construction
  `AITestMode` puis vérifier réellement station ID, dépense, caisse et
  chemin après pose. Aucun tracé de route long ni fermeture Squirrel.
- ROI marginal conservateur >=20 % annuel, et >=25 k£ de trésorerie après
  la station. Un satellite non constructible n'est pas un échec de ligne :
  préserver la route et les véhicules existants, ne pas laisser une gare
  étrangère accidentelle. Ne **pas relever** le plafond initial de 2 autobus :
  les satellites accroissent le bassin de collecte, pas nécessairement
  la capacité du bus ni des ordres.
- Sonde `ROAD100_JOINED` : sites examinés/acceptés, stations jointes,
  captation marginale, distance/rayon et chevauchement, cash/quote/payé,
  opcodes, échecs de liaison/refus et revenu réalisé ultérieur. La
  production dans une zone couverte n'est pas à elle seule une preuve de
  recette ou de cargaison effectivement transportée.

## Séquence et décisions

Tests de contrat/ON/OFF exact, projection des hunks dans
`sweeps/road100_off_projection.py`, smoke 42 1×1 et dépouillement de la
station réellement jointe, puis diagnostic 5×1 apparié OFF/ON en gardant
`road100_site_first=1` sur les deux bras pour isoler l'intervention.
Si aucune jointure, aucune hausse de captage, opcodes disproportionnés,
forte baisse de valeur, ou gains négatifs/non concluants, ne pas qualifier
le mécanisme. Seulement en présence d'un signal robuste et d'une garde
de valeur acceptable : 40×5 apparié même bundle, analyse de chaque horizon,
p<0,05, IC95 et seuil primaire +4 %, garde valeur >=−5 %, puis porte B
suivant AGENTS. Un smoke 1×1 ou 5×1 ne peut atteindre l'objectif final de
parité ≥100 % du profit AAA à chacun des 5 horizons.
