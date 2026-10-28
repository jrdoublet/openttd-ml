# ROAD100-7 — sélection de sites routiers, résultats exploratoires (28/10/2026)

**Décision : NON QUALIFIÉ, ne pas activer par défaut, aucune porte 40×5
justifiée sur cette version.** Les cinq objectifs OpexAI/AAAHogEx ≥100 % en
ROAD-only aux horizons 1–5 ans restent ouverts.

## Hypothèse et construction

Sélectionner les projets passagers *après* recherche physique d'arrêts
constructibles et d'une liaison routière, puis mesurer le débit réellement
couvert (`stopA.value+stopB.value`), les véhicules, la trésorerie et le ROI
avant classement. Opt-in `road100_site_first=1`, défaut 0, ROAD seul et
`road100_solo_pax=1`. Le producteur coopératif `PO01C` inclut le même
générateur ; le chantier replanifie et recalcule à nouveau le débit et les
gardes de trésorerie. Les hunks ROAD100-7 sont soustraits *avant* les sept
opt-ins précédents par la projection OFF exacte, sans changer les empreintes
historiques.

## Smokes : exposition et coût d'exploration

| Version | Bundle | Plans physiques | Admis | Construits via site-first | OpCodes de planification |
| --- | --- | ---: | ---: | ---: | ---: |
| v1, 1×1 graine 42 | `793b0908f836ba189bd4b56b635eadbafbca39fa17b50f8bdf766286e5bdc3d2` | 12 | 0 | 0 | 10 293 477 |
| v2, 1×1 graine 42 | `35dc70f1a03c7c5ca8ea9bc0b0ddc1857af097fd23ea0f42086908a507b4c70e` | 4 | 0 | 0 | 2 524 890 |
| v3, 1×1 graine 42 | `7e7ce50eebbe050598a57d5a127291caf5cc4bf1e038bdb2ba41cc116a30b4d9` | 4 | 3 | 2 | 2 539 595 |

v1 : 12 refus `TRACEX`, sites à 86–197 cases. v2 : 4 refus `TRACEX`,
sites à 56–63 cases. Le resserrement v3 à des centres de villes séparés
de 12–42 cases a permis 3 admissions et 2 constructions passagers, avec
`game_ok=True` pour les deux bras.

Sur la graine 42, les projets site-first admis avaient **26, 25 et 21
voyageurs/mois**, pour des recettes nettes attendues de **170, 74 et
98 £/an** respectivement. Les deux constructions passagers issues
directement de ces projets ont des profits prévus de seulement **170 et
98 £/an** : très faible rendement pour des capitaux prévus de 8–9 k£
par ligne, même si le duel entier évolue favorablement. Le profit global
v3 à un an est 20 167 £ contre 3 328 £ pour l'OFF de ce smoke, mais le
seul échantillon ne permet aucune attribution robuste ni qualification.

## Diagnostic exploratoire apparié 5×1 (version v3)

- Campagne : `results/road100_site_first_v3_expo_5x1_20261028.json`,
  logs `results/road100_site_first_v3_expo_5x1_20261028_engine/`.
  Bundle partagé `7e7ce50eebbe050598a57d5a127291caf5cc4bf1e038bdb2ba41cc116a30b4d9`.
  Graines 42, 100, 7, 999, 2026 ; 1970 ; deux politiques Opex ROAD-only
  (`estim_unifie=31`, `road100_solo_pax=1`, site-first 0 contre 1),
  duels 1v1 contre AAAHogEx désactivé hors ROAD, carte 256².
- Cinq paires achevées, toutes `game_ok=True`. Profit annuel moyen
  Opex OFF **15 965 £**, ON **17 660 £** ; delta moyen **+1 695 £**
  avec **3 victoires/2 défaites**, médiane **+7 859 £**, Wilcoxon
  **p=0,8125**, IC95 bootstrap **[−9 819,4 ; +11 809,8] £**.
- Valeur entreprise moyenne : OFF **24 986,6 £**, ON **12 396,8 £**
  soit **−50,39 %**, en violation de la garde de −5 %.
- Opex/AAAHogEx (ratio des profits moyens) : OFF **12,31 %**,
  ON **13,72 %** à un an ; aucun duel Opex ON ne rattrape AAA.
- Deltas de profit par graine ON−OFF : 42 **+16 839 £**, 100
  **+7 859 £**, 7 **−16 484 £**, 999 **−8 495 £**, 2026
  **+8 756 £**. Les effets ne sont ni homogènes ni statistiquement
  concluants.

L'exposition existe : 1–3 plans admis par graine, mais leurs profits
prévus sont généralement de **26 à 866 £/an**. Le planificateur consomme
environ **2,54–3,16 millions d'opcodes** par génération dans les cinq
traces étudiées. Un plafonnement vérifié *entre* plans laisse parfois
déroger au budget de 2,5 millions ; ce n'est pas un plafond dur.

## Interprétation et suite

La sélection physique corrige une erreur de classement, mais les arrêts
retenus captent toujours seulement **quelques dizaines de passagers/mois**.
Une augmentation du nombre d'autobus ne résout pas cette pénurie :
une station unique par extrémité a un plafond physique de deux véhicules
dans le modèle Opex. AAAHogEx peut ajouter des arrêts aux lignes de bus
et créer des dessertes de transfert (`ai/AAAHogEx-115/road.nut:1753-1774`),
une capacité structurelle absente de ces nouvelles lignes Opex.

La prochaine hypothèse est **une desserte multi-arrêts bornée** avec
stations passagers supplémentaires et lieux desservis non chevauchants,
liaisons réelles et véhicules dimensionnés sur le flux total plutôt que
relever artificiellement un plafond. Mesurer l'incrément de demande,
les recettes par ligne et les coûts des dessertes avant d'étendre un réseau.
Définir un nouveau protocole opt-in et ne pas confondre les smokes avec
une validation économique. Une vraie amélioration doit survivre à 40×5
et progresser séparément à chaque horizon de 1 à 5 ans.
