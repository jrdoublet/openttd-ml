# ROAD100-30 — pré-enregistrement multi-quartiers (28/10/2026)

**Statut : V30a correction d'unité prioritaire ; V30b
multi-quartiers différée. ROAD100 reste à 0/5 parités
de profit_year de société en duel ROUTE seule.**

## Préenregistrement V30a — correction de l'unité PAX avant chantier

La documentation officielle de NoAI confirme :
**AITile.GetCargoProduction = nombre de producteurs** (maisons
et industries), **pas unités mensuelles**. Le comptage 18/17
ne s'oppose donc pas à 355/327 PASS/mois de ville ;
ces derniers sont de vraies unités mesurées par
AITown.GetLastMonthProduction. Les plafonds monétaires
issus directement des comptages V16/V19/V20/V29 sont invalides.

Un nouveau réglage indépendant **road100_pax_producer_units**
(booléen défaut 0) corrigerait uniquement les préplans PAX
site-first ROAD-only ; toute autre politique et tout OFF
restent inchangés. Comme le modèle AIR B9 existant,
il calcule séparément, à chaque extrémité :
production PASS/mois de la ville × nombre de producteurs
PASS du site appartenant à cette ville / nombre total de
producteurs PASS autour du centre de ville, ratio plafonné
à 1. Le rayon total suit le modèle AIR B9, croissant
avec population et borné à 20 ; si les données sont
nulles ou invalides, ne pas inventer de volume. **Cette
estimation n'est pas un revenu observé ni un plafond
causal fiable**, car les maisons n'ont pas toutes la
même production et la concurrence reste incertaine.

Garder les gardes physiques existantes : AITest stations,
connectivité de chaque tronçon et dépôt, capacité/berth
et note par fréquence, recettes uniquement aux destinations,
costing et trésorerie revalidés juste avant construction.
V30a doit utiliser la même demande corrigée **dans
le préflight, la génération sync/PO01C et la revalidation
LIVE**, journaliser producteurs / PAX/mois / coût d'opcodes.
Ne pas compter de satellite ou de flotte non construits.
Qualifier par smoke apparié puis 5×5 avant toute Gate A ;
aucun défaut basculé, aucune preuve de parité anticipée.

## Hypothèse distincte et réfutations préalables

Le [contre-audit PAX 40 graines](road100_calibration_pax_40graines_20261028.md)
prouve que les facteurs V24 de 6,454/18,809 ne sont pas transportables
au profit ex ante ; la baseline donne 0,818/0,797 en ratios de sommes
réel/prédit sur lignes PAX matures. Aucune calibration multiplicative
ne constitue un gain démontré.

Le scanner V16/V19b (31–35 producteurs sur les deux extrémités),
le SHADOW V29 (7–12 producteurs source), les quais joints V20
(2–15 producteurs supplémentaires, H5 ON−OFF −11 676 £)
et le renfort de quais V26/V28 n'ont pas mis en évidence de nouvelle
source générant 25–30k£ nets/an par ligne. Les erreurs LONG
1281/260 démontrent aussi que AITest d'une station ne prouve pas
une route longue constructible. En multimodal, les rabattements
V139/V139b/V139c ont échoué : créditer le billet du transporteur
parent au feeder qui ne livre pas était incorrect. Ne pas reproduire.

La nouvelle hypothèse **V30b à différer après qualification V30a**
est l'existence de plusieurs bassins de production PAX disjoints
**hors de la boîte station.station_spread** d'une seule StationID,
physiquement raccordables et capables de payer leur réseau de
transport complet. Le volume global par ville sert exclusivement
à classer les villes à observer, jamais à prédire le volume capté.

## Conditions d'une préqualification crédible

1. Par exercice, prétrier un couple de grandes villes d43..190,
   puis inspecter des quartiers réellement distincts sur les
   routes existantes, hors zones déjà couvertes par **toutes**
   les stations Opex. Un producteur natif 1×1 ne compte qu'une
   fois dans l'union. Exiger des façades BUS passées en AITest,
   sans prétendre qu'elles sont déjà construites, jointes,
   connectées, ni dotées de dépôt.
2. Publier la production marginale par StationID futur
   et par sens, sans la multiplier par le nombre de quartiers,
   ni utiliser waiting/profit d'AAAHogEx postconstruction.
   Un plafond de recette à transit zéro jour peut **éliminer**
   un marché, pas qualifier une prévision. À d63 et tarif
   maximal 24£/PASS, 25k£ de **recette brute** nécessitent déjà
   au moins 87 voyageurs *livrés* par mois, sans frais.
3. N'envisager un chemin coûteux qu'après une offre capable
   d'expliquer ≥25–30k£ de **profit marginal annuel net**
   par ligne, ROI ≥25 %, avec coût réel de route, stations,
   dépôt et bus, amortissement, congestion, temps de rotation,
   paiement et immobilisation. Le déficit H5 moyen face à AAA
   étant ~2,0–2,13M£/an, le nombre de lignes nécessaires
   doit être chiffré avant l'essai, sans additionner deux
   couvertures communes.
4. **Deux solutions physiques distinctes** : soit chaque
   quartier comporte sa ligne complète avec vraie destination
   acceptante et ordres livrant réellement, soit une navette
   de rabattement apporte au terminus une cargaison transférée
   sur un véhicule parent. Pour cette seconde solution, la
   valeur ne se réalise qu'au **dernier déchargement**, et
   jamais une deuxième fois sur la navette. Les StationIDs
   des quartiers hors spread doivent être distincts.
5. Examiner la connexité routière aller/retour, le dépôt et
   les capacités réelles avant chaque chantier ; rollback
   exact en cas d'échec, vérification des ordres et de la
   livraison, Save/Load et démolition externe. Ne compter
   aucun arrêt ou revenu d'un quartier non construit.
6. **Limiter les opcodes, sans recherche atomique longue.**
   Les préplans V26 étaient à 518k opcodes en moyenne et les
   recherches LONG à ~100–180k par paire ont échoué ; PO01C
   découpe à 40k mais ne sauve pas automatiquement un préflight
   monolithique. Séparer budget d'inventaire, AITest, devis
   et chemin, pouvoir suspendre/reprendre à chaque tranche,
   et ne pas dégrader les investissements précoces.

## Contrat moteur si et seulement si la preuve existe

Le futur réglage isolé **road100_pax_multidistrict** serait
opt-in **défaut 0**, actif uniquement sous air0/rail0/road1/eau0.
Une sonde SHADOW, même sans chantier, peut décaler PO01C
et modifier profit_year : mesurer le marché sur une copie
diagnostique non scorée, puis comparer OFF/ON sur **un seul
bundle figé** avec paramètres AAA train/tram/ship/aircraft
désactivés et les mêmes graines.

Contrats obligatoires : projection OFF et V262 intactes,
voies synchrone/PO01C équivalentes, TopK, C75/C78, vraies
StationIDs, devis/prix/finance, dépôts, véhicules et ordres,
livraisons, congestion, rollback et Save/Load ; tests Squirrel
réels et suite complète. Après construction rentable réellement
exposée : smoke apparié strict ROAD-only puis 5 graines ×5 ans.
Gate A40×5 uniquement si **gain moyen ON−OFF profit_year ≥4 %**,
Wilcoxon p<0,05, garde de valeur ≥−5 % et non-érosion des
horizons antérieurs ; ne déclarer 5/5 parités que sur le
profit annuel de société effectivement constaté face à AAA
aux cinq horizons.

**NON-LANCEMENT au 28/10 :** aucun corridor actuel ne satisfait
ces conditions physiques et économiques. Ne pas coder un
ON multi-quartiers ou lancer une Gate A sur un seuil desserré
ou un revenu hypothétique. Chercher d'abord un bassin
multi-StationID quantitativement suffisant et connecté.
