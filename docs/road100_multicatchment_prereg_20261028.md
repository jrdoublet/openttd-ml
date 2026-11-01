# ROAD100-9 — paires de villes déjà desservies, bassins indépendants

Préréservation du 28/10/2026 avant les premiers smokes ROAD100-9.

## Question et diagnostic préalable

ROAD100-7 v4 trouve des sites constructibles mais la garde
`town_already_bus_served` bloque toute nouvelle liaison de voyageurs
si l'une des villes possède déjà un bus OpexAI. Le 5×1 v4 donne
+37,2 £/an et −61,22 % de valeur : non qualifié. ROAD100-8,
un satellite joint par terminus, a une exposition physique (+5 pax/mois
sur certains terminus), mais son pilote 5×5 perd 5 002,2 £/an à
l'horizon 5, p=0,8125, valeur −6,24 %, et n'atteint pas la parité AAA
à aucun horizon. Il est NO-GO.

## Intervention ROAD100-9 isolée

- Réglage `road100_multicatchment=1`, désactivé à 0 dans les quatre
  difficultés, actif uniquement en ROAD seul avec `road100_solo_pax=1`
  et `road100_site_first=1`. Les autres opt-ins, notamment
  `road100_joined_stops`, sont maintenus à 0.
- Autoriser au générateur à **considérer** une autre liaison dans une
  ville déjà desservie ; conserver le cap existant de quatre lignes,
  les gardes de paire abandonnée et desservie, la connectivité, le
  financement et le profit réalisé. Le fret reste inchangé.
- Le planiteur réel, à la génération et au chantier, ne doit accepter
  une nouvelle station que si sa zone de couverture ne rencontre aucune
  zone d'une station de bus OpexAI existante : pour des arrêts 1×1,
  séparation de Chebyshev strictement supérieure à **deux rayons de
  collecte**. Ne jamais élargir la flotte simplement grâce au nombre
  de projets admis.
- Préserver la génération site-first bornée à 6 plans et environ
  2,5 millions d'opcodes de préflight mesurés ; le plafond est
  contrôlé entre recherches physiques, donc non strict à l'opcode.
- Sonde d'exposition : nombre de projets nouveaux dans des villes
  existantes, arrêts physiques, recouvrements rejetés, captation
  réellement supplémentaire, lignes construites, ROI de génération
  versus chantier, échecs TRACEX/DEPOTX, coût/opcodes, cash et
  recette réellement transportée à âges comparables.

## Mesures et décision

Même carte et bundle OFF/ON, `multicatchment=0` contre 1 avec
`site_first=1` dans les deux bras. Smoke 1×1 graine42, petit
diagnostic apparié 5×1 puis 5×5 si la construction est exposée et
les premiers gains crédibles. Si négatif ou aucune exposition,
ne pas lancer 40×5 ; corriger les causes démontrées sans
relâcher la contrainte de non-chevauchement. Si positif et
garde valeur ≥−5 %, porte 40×5 appariée, cinq horizons 1–5 ans,
gain utile ≥4 %, p Wilcoxon <0,05 et borne basse IC95 >0.
Ne déclarer 100 % atteint qu'après mesure séparée Opex/AAAHogEx
≥100 % à **chacun** des horizons, sans érosion des années précédentes.
