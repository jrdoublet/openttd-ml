# ROAD100-31 — flotte initiale après construction des quais doubles

**En qualification. Nouveau réglage opt-in défaut 0, aucune
adoption, aucune parité encore prouvée.**

## Pré-enregistrement

V30a OFF/ON 5×5 a posé en ON **20 quais supplémentaires
sur 12 lignes PASS**, dont **4 lignes avec au moins un
quai réellement joint à chacun des deux terminus**.
Le constructeur plafonne néanmoins à deux bus même
quand les deux StationIDs ont une capacité de quatre.
V31 teste une extension *après chantier*, sans
inventer de voyageurs aux quais satellites.

Le réglage **road100_pax_initial_berth_fleet** vaut
0 par défaut et ne s'active que si les options
V30a correction des unités et V20 portfolio sont
actives en ROUTE seule ; V26/V28 ne se combinent pas.
Les préplans, TopK, C75/C78 et l'ordre des candidats
utilisent la rentabilité V30a des **racines seules** :
aucun arrêt satellitaire non construit ne vaut
ni revenu ni capacité avant chantier.

Après construction de la route, des deux terminus,
des satellites effectivement joints, du dépôt et du
premier bus refitté, vérifier les deux StationIDs
physiques, propriétaires et capacité refit.
Le plafond de bus devient **2 × min(quais A, quais B)**
avec un maximum de huit. La demande estimée demeure
celle des **racines V30a**, jamais la couverture
satellite ajoutée. Comparer économie de base et
économie avec vraies places ; n'acheter un bus
supplémentaire que si Δprofit annuel ≥25 % du prix
des bus additionnels, avec 50k£ de caisse conservée,
slots disponibles et circulation valide. Le prix
des quais est déjà effectivement payé à cette étape,
sans attribution de recettes satellites.

Cloner les deux ordres historiques partagés et
contrôler la commande moteur, la caisse, la
capacité et le succès de démarrage de chaque bus.
Ne publier le nouvel effectif ou le profit estimé
qu'après achat **réel** ; les échecs de construction
remontent au rollback du réseau et des véhicules.
Mémoriser les deux tuiles supplémentaires et,
après Save/Load ou démolition, corriger les
plafonds de stations pour interdire tout
recrutement sur quai fantôme.
**Limite reconnue :** cette récupération ne liquide
pas encore automatiquement les véhicules déjà
sur la ligne lorsque des quais disparaissent.

Tests contractuels du modèle, projection OFF exacte
avec nouvelle fixture séparée V31, suite complète,
Save/Load, sync/PO01C, stationID/finance/ordres/
rollback et smoke strictement apparié seed100 H2
(la référence V30a possède déjà des quais joints
aux deux bouts dès janvier 1970). Si exposition
physique et profit réel substantiels, pilote
cinq graines × cinq ans avec **même bundle source
figé**, puis Gate A uniquement sur Δmoyen profit_year
≥4 %, Wilcoxon p<0,05, valeur ≥−5 %,
non-érosion H1–H4 et parité AAA aux cinq horizons
vérifiée indépendamment.

**Aucune ligne ni gain V31 ne constitue déjà une
parité : 0/5 jusqu'à preuve moteur contraire.**

## V31b — correction dimensionnelle + fréquence réelle, préenregistrement

Le smoke V31 seed100 H2 a ajouté **zéro bus** malgré de vrais quais
satellites aux deux extrémités d'une ligne. L'audit de code a établi
deux défauts de calcul indépendants, sans spéculer sur leur effet final :

1. `OpexRoad100PaxPortfolioBuild` cumule dans `portfolioSummary.monthly`
   **44 producteurs** au cas seed100 (26→1), alors que le constructeur
   compare ce nombre à `capacity*30/roundTripDays`, une **capacité en
   PASS/mois**. Le proxy V30a LIVE des seules racines de cette ligne
   donne **146 PASS/mois** estimés. Sur la voie V31 exclusivement,
   comparer des PASS/mois à des PASS/mois, sans ajouter la production
   des satellites non desservis.
2. `OpexRoadLineEconomics` déduit la note de gare d'une cadence fixe de
   **deux bus**, même lorsqu'on évalue N=3 ou N=4 bus sur deux quais
   réellement construits. Dans V31b seulement, calculer explicitement
   les scénarios N entiers de la flotte de base jusqu'au plafond
   `min(8,2*min(quaisA,quaisB))` avec une note liée au headway N,
   volume livré plafonné par la flotte N, prix moteurs, running et
   amortissement existants. Ne jamais augmenter la production de ville,
   ni comptabiliser la couverture satellite comme passagers livrés.

Adopter N uniquement si `profitAnnual(N)>profitAnnual(base)`, le gain
net marginal est >=25 % du prix réel des bus additionnels, slots,
trésorerie après achats >=50k£, prix et refit réels, ordres, stations
jointes bilatérales et démarrage vérifiés. Publication des nouveaux
chiffres seulement après `AIVehicle.CloneVehicle` réussi ; rollback
inchangé. **V31 reste un opt-in à défaut zéro**, V31b ne change aucun
classement/préplan OFF, fret ni mode multimodal.

Smoke nouveau seed100 strict ROAD-only apparié avec source OFF/ON
identique et seul `road100_pax_initial_berth_fleet` différent ; si
aucun bus supplémentaire effectivement acheté, NO-EXPOSURE sans 5×5.
Si achat et PASS livrés, tester cinq graines × cinq ans et n'envoyer
en A40×5 que sur seuils de `profit_year` société, p<0,05, IC95,
valeur et non-érosion des horizons antérieurs. **0/5 parités** jusqu'à
preuve contraire.

### V31b — résultat moteur et rejet (28/10)

Campagne saine, deux parties même bundle
`42ac85ddb5a92bde8124c73682a275fa54949dda75fd482679d90db32feb84a9`,
graine 100 × 2 ans :
`results/road100_v31b_units_headway_smoke_roadonly_seed100_2x1_20261028`.
AAAHogEx-115 strict ROUTE seule, seuls réglages OFF/ON différents :
`road100_pax_initial_berth_fleet=0/1`. Le 26 janvier 1970, vrais
quais joints A2/B3, quote **3 bus vs 1**, deux clones effectivement
achetés, coût additionnel prix de véhicules **11 484 £**, profit
annuel prédit +3 446 £, marge quote >=25 %. Source : journal ON
`ROAD100_PAX_INITIAL_FLEET phase=quote` puis `phase=built` et
`ROAD100_REPRICE ... bought=3`.

**Le réalisé contredit la prévision :** `profit_year` compagnie H1
OFF **10 740 £** vs ON **8 554 £** (−2 186) ; H2 OFF **19 219 £** vs
ON **11 483 £** (−7 736). Valeur entreprise H2 OFF **24 594 £** vs
ON **1 199 £**, perte relative **−95,1 %**. Parc H2 identique
10 véhicules, alors que les marchés changent. PASS livrés dernier
trimestre H2 OFF **761** vs ON **461**. Sur la première route
`road|2,4` au 1970-12-01, profit des véhicules OFF **17 797 £**
contre ON **14 860 £**, note des arrêts OFF 197/203 contre
ON 159/170. Ces profits de groupe sont des observations de ligne,
non le profit de société. À H2, le marché `road|21,26` est PASS en
OFF (2 bus, profit groupe 4 978 £) mais COAL en ON
(2 camions, profit groupe 1 852 £) ; la comparaison causale inclut
donc les déplacements de portefeuille, pas seulement les clones.

**NO-GO**, non-érosion H1/H2 et garde valeur échouées, même si
l'exposition mécanique est réelle. Ne pas lancer 5×5/A40×5, ne
pas activer par défaut. La fonction de prévision de note par flotte
ne capture pas congestion/reallocation : ne pas la « corriger » par
facteur de profit dérivé d'AAAHogEx, et ne jamais prétendre que plus
de bus implique plus de voyageurs livrés.
