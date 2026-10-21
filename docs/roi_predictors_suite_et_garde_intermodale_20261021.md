# ROI : exploration complementaire, formules actuelles et garde intermodale

Date : 21 octobre 2026. Branche de publication :
review/roi-calibration-predictors-20261021.

**Aucune modification du modele economique ou de la politique n'est proposee
comme defaut**. L'objectif est de diagnostiquer les variables de classement
sur les 40x10 deja termines, puis preparer l'instrumentation shadow.

## Formules actuellement en production (code inspecte)

Fichiers : ai/OpexAI/economy.nut, air_economics_c121.nut,
air_route_economics.nut, projects_models.nut, projects_finance.nut,
projects_selection.nut, projects_builders.nut.

Les estimateurs emploient :

    profitAnnual = revenueAnnual - runningAnnual - amortAnnual
    ROI_economique_pour_mille = 1000 * profitAnnual / (capital + immobilise)

Les modes RAIL et ROAD renvoient un ROI nul si profit <= 0.
Les couts de capital incluent les vehicules et les infrastructures du mode.
Les recettes tiennent compte du tarif OpenTTD lie au cargo, a la distance de
paiement et aux jours de transport. Production/offre est bornee par l'evaluation
de la note de gare et la flotte. Les recettes/revenu ne sont pas le profit.

Reglages verifies : STATION_RATING_PCT=50 (reference RAIL/ROAD),
RAIL_TERRAIN_FACTOR=100, MAX_RAIL_TRAINS=2,
ROAD_SPEED_EFFICIENCY_PCT=60 ; INFRA_AMORT_PCT=0 et
TRANSIT_COST_PERMILLE=0 dans les parametres actifs.
V275_RAIL_PAX_MM peut modifier apres calcul le revenu PAX RAIL
(+50%) et le capital (-15%) si le bit 2 est actif dans ce profil.

- **AIR C121** : demande de PASS et MAIL, rotation avion, capacites,
  notes et contraintes des hubs, concurrence et cannibalisation, service
  existant, moteur et aerodrome. Capital = prix avions + nouveaux aerodromes ;
  exploitation = cout des avions + maintenance aeroportuaire ; amortissement
  = avions / vie utile (+ part infra actuellement nulle). Le ROI utilise
  profit / capital economique. Le cout *physique* AIR ne figure pas comme
  depense constatee dans AIR_BUILD des journaux de calibration.
- **RAIL** : offre cargo * note prevue, portage borne par
  trains × wagons × capacite × rotations ; revenu annuel par cargo
  et barème OpenTTD ; capital = locomotives + wagons + voies, gares,
  depot, signaux suivant la variante de voie ; cout courant =
  locomotives + amortissement des vehicules. Le A* puis le devis physique
  peuvent reviser le capital, l'amortissement, le profit et le ROI.
- **ROAD** : vitesse effective (60% catalogue), demande captable,
  capacité et rotations, duree aux arrets pour les bus, plafond physique
  de vehicules, prix trajet OpenTTD ; capital = routes + arrets + depot +
  vehicules ; cout courant = moteur/vehicules + amortissement des vehicules.
  Le devis et la distance apres sites peuvent reviser l'economie.

Mais le classement d'investissement utilise essentiellement :

    fundScore = 1000 * OpexC70Profit(project) /
                 max(decisionFinanceCapital, K_dec)

Le facteur C70 depend du mode et est appris en cours de partie ; exemptions
si profit deja observe ou cas specifiques de flotte/C121. Le capital
financable ajoute les marges ; pour ROAD le repli utilise 121% du
capital hors marge lorsque non constate. Le symbole RAIL_FINANCE_BIAS_PCT
est actuellement initialise a **100**, contrairement a une ancienne
mention de 170 dans un commentaire. Le seuil K_dec amortit les variations
de petits projets. Les priorites AIR C77 et primes temporaires de slots
ne sont pas de simples multiples economiques communs aux autres modes.
La variable project.roi reste distincte du score de classement.

### Regle de preservation de l'equilibre entre modes

L'utilisateur souhaite explicitement eviter qu'une surestimation absolue
du ROI AIR serve a affaiblir un mode economiquement performant.
En particulier, **une attenuation de 20% du score AIR doit avoir le
meme multiplicateur pour RAIL et ROAD**, si cet essai est un jour demande.
L'appliquer au *score final* pour tous les modes avec le meme facteur
ne change pas leur ordre relatif a tier C77 egal. Les bonus defensifs
AIR restent prioritaires et les seuils de financement inchanges.
L'appliquer seulement au profitAnnual ou au ROI interne serait une
modification **differente**, touchant l'admissibilite et la flotte.
Il n'y a ici aucune modification active ou meme implementee de ce type.
La calibration statistique servira d'abord a expliquer et trier les
projets **au sein d'un mode**, sans changer la competition intermodale.

## Nouvelles variables tentees hors ligne

Le script sweeps/analyse_roi_extra_predictors_20261021.py joint
les PROJECT_CHOSEN aux BUILD et RAIL_ATTEMPT, puis aux profits matures.
Il reconstruit, juste avant chaque PROJECT_CHOSEN, l'etat du reseau
**historique de constructions** du mode (nombre de projets deja bâtis,
nombre de liaisons aux deux extremites, nouveaute source/destination,
paires deja liees). Ce signal n'est pas une photographie parfaite du
reseau actif : aucune suppression de ligne ou occupation des gares n'est
simulee, et il ne suit que les projets journalises.

Variables supplementaires :

- **Disponibles par construction au moment de la selection** :
  mois, capital prevu, profit prevu ; nombre de constructions
  precedentes / degres des deux extremites, calcule sur l'historique.
- **Potentiellement disponibles dans le plan mais journalisees seulement
  apres selection** : variante AIR newpair/hubsite/hubhub, engine choisi,
  reutilisation du reseau, nombre de vehicules et de wagons.
- **Posterieurs au choix, non utilisables tels quels pour classer le
  catalogue** : longueur du trace retenu par A*, iterations, devis
  et cout physique reel. Ces derniers sont des diagnostics / cibles
  pour un futur predicteur *ex ante*, pas des features deployables.

Validation : 5 plis par graines, et controle **solo → duel** :
chaque graine test duel est retiree des graines solo qui entrainent
le modele. Une observation = une ligne mature, mediane des annees
age >=2 (normalisee a sa flotte initiale). ROI RAIL/ROAD mesure
sur capital physique positif ; ROI AIR sur le devis et ne peut
donc pas evaluer l'erreur de cout physique AIR.

### Gains de prediction du ROI (erreur absolue moyenne, points)

| Nouvel ajout (au modele existant) | DUEL → DUEL AIR | SOLO → DUEL AIR | DUEL → DUEL RAIL | SOLO → DUEL RAIL |
|---|---:|---:|---:|---:|
| Base existante (ROI, cargo, capital, distance, type) | 13,89 | 19,50 | 12,61 | 17,71 |
| + anciennete du reseau (nb constructions) | 13,72 | 19,52 | 12,64 | 17,74 |
| + degre de destination | 13,90 | **18,58** | 12,63 | 17,71 |
| + nouvel etat reseau complet | **13,65** | **18,52** | 12,72 | 17,72 |
| + longueur A* (apres choix) | 13,89 | 19,50 | **12,44** | **17,34** |
| + geometrie A* (apres choix) | 13,89 | 19,50 | **12,48** | **17,09** |

L'incertitude des differences SOLO→DUEL a ete bootstrappee
par graine. Pour AIR, les variables de reseau ajoutent un gain moyen
de 0,95 point de ROI par graine [0,68 ; 1,26], 36/40
graines favorables ; le degre de destination seul +0,93
[0,65 ; 1,22], 31/40. Dans le controle DUEL→DUEL,
le modele complet de reseau gagne +0,23 point [0,09 ; 0,36].
Ces intervalles sont exploratoires (familles et variantes multiples
comparees sur les memes jeux), pas une qualification economique.

RAIL : les variables de reseau simples ne montrent aucun gain stable
dans le transfert SOLO→DUEL. La geometrie A* apporte
un gain +0,65 point [0,43 ; 0,87], 32/40 graines.
Mais ce signal n'existe dans les logs qu'**apres** la
recherche de construction ; le classement initial ne peut pas le lire.

ROAD : 48 lignes DUEL seulement ; plusieurs ajouts de variables font
empirer la MAE. Ne pas promettre de coefficients calibrables sur ce panel.

### Pourquoi la geometrie du RAIL merite une sonde avant decision

Par quartile de rapport **longueur A* / Manhattan**, 958 lignes
construites RAIL DUEL :

| Quartile detour | Rapport longueur / Manhattan median | Capital reel / prevu median | Profit reel / prevu median |
|---|---:|---:|---:|
| Q1 | 0,893 | 1,222 | 0,823 |
| Q2 | 0,957 | 1,455 | 1,038 |
| Q3 | 1,009 | 1,540 | 1,026 |
| Q4 | 1,103 | 1,691 | 0,939 |

Plus de detour coïncide avec davantage de depense physique,
independamment du seul sens de l'erreur de profit. Il faut une
approximation rapide du relief/obstacles/route realisable au
**catalogue**, plutot qu'injecter apres coup la longueur A* parfaite.

## Suites recommandees : lecture seule puis shadow

1. **AIR maintenu en l'etat** : etudier les differences de demande captable
   et de partage des hubs (C121 dispose de paxRaw, existingPaxBefore,
   service, rating, piste), uniquement a titre explicatif.
   Ne pas modifier le gain relatif AIR dans le portefeuille.
2. **RAIL : predire le surcout du trace**, avec pente, relief,
   obstacles, usage de voie existante, sites/stations possibles et
   estimation du detour ex ante ; separer capital physique et profit.
3. **RAIL : expliquer le profit**, avec cargo, volume disponible,
   pourcentage deja transporte, attente, note probable, vitesse
   effective et flotte initiale. Les sondes de LINE_REVENUE apres
   construction ne sont pas des features de selection.
4. **ROAD : collecter davantage de lignes** et le plafond physique
   des vehicules avant de chercher un coefficient.
5. Verification finale hors panel sur graines disjointes,
   et surtout **impact A/B economique sur le portefeuille**,
   sous contrainte de neutralite intermodale.

Les valeurs presentes ne demontrent pas de causalite et ne donnent
aucune justification a une penalisation relative de l'AIR.
