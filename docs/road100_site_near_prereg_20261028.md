# ROAD100-12 — priorité aux couples de villes proches et préflight constructible

Préréservation du 28 octobre 2026. Levier indépendant des ROAD100-10/11,
`road100_site_near=1` (quatre défauts zéro), actif seulement si
`road100_site_first=1` dans un jeu ROUTE seul. Tous les anciens réglages
ROAD100-8/9/10/11 restent zéro pour le diagnostic isolé.

## Hypothèse

ROAD100-11 a varié les rangs dans la shortlist sans gain robuste : 5×5
−5 432 £/an, 2V/3D. La grande majorité des couples classés par profit
urbain *proxy* échouent en `TRACEX` avant d'être admis, et les plans de
distance élevée ont davantage de tuiles ou d'obstacles à franchir.
Hypothèse distincte : tester en priorité **les distances physiques plus
courtes**, à l'intérieur des bornes 12–42 conservées, permettrait à la fois
de construire plus de dessertes et de moins payer d'infrastructure.

## Intervention

Nouveau comparateur Squirrel global nommé : les couples à proxy annuel
strictement positif précèdent ceux à proxy non positif, puis distance de
centre **croissante**, puis profit proxy décroissant, enfin IDs pour ordre
déterministe. La ligne ne peut être retenue qu'après validation du vrai
plan site-first et `profitAnnual>0` sur production des arrêts. Gardes
identiques d'occupation, de transport, caisse, abandon, construction,
profondeur et coûts. Pas de Pathfinder.Road ni d'augmentation de
`plans<6` ou `ops<2500000`. Aucune modification du chemin OFF.

## Validation

Projection OFF exacte, tests de contrat, smoke 1×3 et pilote 5×5
apparié 42/100/7/999/2026 (même bundle OFF/ON, AAA ROUTE seul), cinq
horizons. Établir admissions/constructions, opcodes, revenus, profit annuel,
valeur, cash et érosion antérieure. Porte A 40×5 seulement si exposition,
signal favorable et garde de valeur respectée ; critères préenregistrés
delta ≥4 %, Wilcoxon p<0,05, IC95 bootstrap bas >0, garde −5 %.
Sinon expérimentation rejetée sans défaut modifié.
