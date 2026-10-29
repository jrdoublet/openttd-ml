# Session cloud 2 — pourquoi un bus AAA rapporte 2× plus, outil de ventilation, revue

Lire d'abord `docs/cloud/README.md`. Branche : `cloud/rendement-aaa` depuis `road1y-s17`.
Pas de modification de `.nut` dans cette session sauf corrections de bugs
avérés trouvés en revue (partie 3), chacune derrière un réglage à 0.

## Partie 1 — outil `sweeps/compare_vs_aaa.py`

Entrée : un JSONL du harnais (gz accepté). Sortie (texte + JSON) par graine et
par IA au dernier cliché et par année : profit par mode / cargo / tranche de
distance (0-31, 32-63, 64-95, 96-127, 128+) / âge de ligne ; véhicules par
ligne ; profit par véhicule ; lignes ouvertes par trimestre ; écart Opex−AAA
décomposé (effet volume de véhicules × effet rendement × effet cargo). Tests
unitaires sur un extrait. Le lancer sur les fichiers de `docs/cloud/data/`.

## Partie 2 — rendement par bus PAX (6,4 k£ AAA contre 2,9 k£ Opex)

À partir des données et du source AAA (`road.nut`, `estimator.nut`, `place.nut`,
`main.nut`) : distance des paires, taille des villes, placement des arrêts
(centre, transfert, captage), ordres (chargement complet ?), choix du modèle,
fréquence, règle de renfort d'AAA (sur quel signal ajoute-t-il un bus ; jusqu'à
32 bus sur une ligne), attente et note de gare. Comparer avec le code OpexAI
correspondant (`candidates.nut`, `bus_districts*.nut`, `builder_road.nut`,
`economy.nut`). Classer les causes en £/an et proposer 3 corrections
fichier:ligne, sans les coder.

## Partie 3 — revue de code de `road1y-s17` contre `master`

`git diff master...road1y-s17 -- ai/OpexAI` : bugs Squirrel, Save/Load des
nouveaux champs, réglages à 0 réellement inertes, opcodes, gardes de trésorerie
incohérentes (la réserve de 50 000 £ des arrêts joints, `bus_districts.nut:236`),
`AIIndustry.GetIndustryID` comparé à −1. Liste priorisée P1/P2/P3.

## Fin

Rapport `docs/cloud/rapport_rendement_aaa.md`.
