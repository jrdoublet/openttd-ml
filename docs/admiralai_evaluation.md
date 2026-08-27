# AdmiralAI — évaluation comme source d'idées

**Date : 2026-08-27.** Évaluation statique de l'IA tierce AdmiralAI (version 26,
Thijs Marinussen, 2010) comme source de mesures pour l'étage 1 de TrainLineAI.

Le clone local ai/AdmiralAI/ est **volontairement exclu du dépôt** : son en-tête place le
programme sous GPL v2 « ou, au choix, toute version ultérieure »
(ai/AdmiralAI/info.nut:2-17), et l'IA annonce l'API OpenTTD "1.0"
(ai/AdmiralAI/info.nut:21-31). Ce document est notre analyse ; il ne reproduit pas son code ni
ne propose d'en copier. *(Ceci n'est pas un avis juridique.)*

**Conclusion en une phrase** : le graphe, qui était la piste la plus originale, ne décrit pas le
terrain et ne vaut pas un essai ; la seule mesure neuve qui mérite un petit essai est le **nombre
d'issues de gare réellement praticables aux deux extrémités**, à condition de le mesurer sans
construire. Le reste confirme surtout que la sonde A* est le bon niveau de détail.

---

## 1. Ce qu'AdmiralAI construit réellement

AdmiralAI n'est pas une IA « villes → train ». Son train relie des **industries** : il classe les
sources par production non transportée, puis les destinations acceptant le cargo par distance
Manhattan, entre 50 et une borne dépendant notamment de la trésorerie
(ai/AdmiralAI/rail/trainmanager.nut:340-381). Il construit les deux gares industrielles **avant**
de chercher la voie (ai/AdmiralAI/rail/trainmanager.nut:512-646), puis appelle le builder
ferroviaire (ai/AdmiralAI/rail/trainmanager.nut:382-390). Cette différence de pipeline interdit
d'attribuer à son succès une feature de sélection de paires de villes.

Le builder crée des ensembles de départs/buts aux sorties de gare, après quelques tests de
rectangles libres (ai/AdmiralAI/rail/railroutebuilder.nut:183-290). Il fait ensuite :

1. une recherche inverse, limitée à 200 itérations, avec le sens des signaux inversé ;
2. une recherche aller jusqu'à 200 000 itérations, avec un coût maximal de 1,5 × distance ×
   coût de tuile ;
3. au plus trois essais « améliore le profil → teste la pose en AITestMode → pose »
   (ai/AdmiralAI/rail/railroutebuilder.nut:292-319, puis retour symétrique
   ai/AdmiralAI/rail/railroutebuilder.nut:328-428).

Le point délicat est important pour notre barrière : l'« amélioration » du profil appelle bien
RaiseTile/LowerTile **avant** le test de pose (ai/AdmiralAI/rail/railroutebuilder.nut:490-536).
Seul TestBuildPath() encapsule BuildPath() dans AITestMode
(ai/AdmiralAI/rail/railroutebuilder.nut:538-543). Ce n'est donc pas un
préflight non mutant réutilisable tel quel, même conceptuellement, et ses gares existent déjà.

---

## 2. Les grandeurs candidates

Les verdicts ci-dessous appliquent le filtre qui a éliminé les autres idées : une grandeur doit
pouvoir varier fortement à distance_straight constante. « Passe » ne signifie pas « utile » ;
c'est seulement le droit d'être considérée. Les coûts sont des ordres de grandeur d'appels API,
pas une mesure exécutée ici.

### 2.0 Le « valuator » n'est pas un score composite — **aucun candidat**

**Lu dans le code.** Utils_Valuator.Valuate() est uniquement un adaptateur : il appelle une
fonction fournie pour chaque élément d'une liste et y inscrit l'entier retourné
(ai/AdmiralAI/utils/valuator.nut:71-108). Ses trois valuators génériques sont constant, identité
et distance Manhattan plus aléa (ai/AdmiralAI/utils/valuator.nut:110-123). Il n'y a donc pas de
score caché à décomposer. Le seul score ferroviaire rencontré est bien le valuator local de
§2.2 : distance vers l'autre industrie, bruit borné, et bonus de sortie libre
(ai/AdmiralAI/rail/trainmanager.nut:496-510).

**Redondance avec la distance : sans objet pour l'utilitaire ; échec pour son valuator générique.**
DistancePlusRandom ne contient que la distance et du bruit. Le bonus d'issue libre, lui, est
traité séparément en §2.2 car il passe le filtre. **Verdict : ne rien tester sous le nom
« valuator ».**

### 2.1 Rang de voisin et détour via un troisième point — **passe le filtre, mais à classer**

**Lu dans le code.** CreateSpanningTree() ne découvre aucune composante du sol. Pour chaque
point, il prend au plus les cinq voisins Manhattan les plus proches dans chacun des quatre
quadrants (ai/AdmiralAI/network/graph.nut:57-68). Une arête candidat p–q est retirée s'il
existe un troisième point r tel que d(p,q) × 1,4 > d(p,r)+d(q,r) et que les deux morceaux sont
plus courts (ai/AdmiralAI/network/graph.nut:69-86). Les points sont seulement tile,value, et une ville y prend sa population
comme valeur (ai/AdmiralAI/network/point.nut:22-48).

**Mesure possible.** Pour une paire, compter ses voisins géométriques plus proches, ou prendre le
meilleur ratio de détour géométrique par une troisième ville. API : AIMap.DistanceManhattan et les
coordonnées de villes. Coût : O(V) par paire pour le meilleur tiers-point ; reproduire le graphe
complet est au pire cubique dans chaque sous-ensemble, donc hors de propos.

**Redondance avec la distance : passe.** À distance égale, une paire peut avoir zéro ou beaucoup
de villes intermédiaires ; le ratio de détour peut varier de près de 1 à bien davantage. C'est la
seule vraie quantité de graphe qui survit formellement au filtre.

**Verdict : ne pas tester.** C'est une densité/centralité géométrique, non une connectivité ou une
distance de graphe du terrain. Plus décisif : CreateSpanningTree() n'est appelé que par
RoadNetwork.InitNetwork() (ai/AdmiralAI/road/roadnetwork.nut:32-94), jamais par le gestionnaire
de trains. Les segments qui se croisent sont ensuite supprimés selon leur seule longueur
Manhattan (ai/AdmiralAI/network/graph.nut:119-156). Rien de lu ne relie ce score au franchissable ferroviaire.
Le coût de données et le risque de réintroduire indirectement population/densité ne justifient pas
un sweep à n=380.

### 2.2 Nombre de sites de gare et d'issues orientées — **passe ; seule recommandation**

**Lu dans le code.** Pour ses gares à quais de longueur 4 par défaut
(ai/AdmiralAI/rail/trainmanager.nut:39-47), AdmiralAI énumère les tuiles sous couverture
de l'industrie, déplace les rectangles au format de gare, et garde les orientations ayant une zone
de dégagement 4×2 ou 2×4 à au moins une extrémité
(ai/AdmiralAI/rail/trainmanager.nut:474-484,
ai/AdmiralAI/rail/trainmanager.nut:542-568). Il rejette aussi les emplacements dont
l'aire ne peut être nivelée : rectangle constructible, écart de hauteur maximal 2, puis essais de
terrassement sous AITestMode (ai/AdmiralAI/utils/tile.nut:133-177 ; appel
ai/AdmiralAI/rail/trainmanager.nut:574-580). Enfin son valuator préfère la gare proche de l'autre industrie et
retire 20 au score lorsqu'une sortie du bon côté est libre
(ai/AdmiralAI/rail/trainmanager.nut:496-510,
ai/AdmiralAI/rail/trainmanager.nut:582-597).

**Mesure à dériver, sans copier l'implémentation.** Pour chaque ville de notre paire, énumérer les
sites et orientations de gare que *notre* preflight autorise, puis enregistrer au minimum :

- station_site_count par extrémité ;
- outward_exit_count : nombre d'orientations/sites ayant une sortie libre dans le demi-plan de
  l'autre ville ;
- un agrégat symétrique prudent, par exemple min(outward_exit_count_a, outward_exit_count_b)
  plutôt qu'une somme qui masquerait une extrémité bloquée.

Les API observées qui motivent cette famille sont AITile.IsBuildableRectangle,
AITile.GetMaxHeight, AITile.GetSlope, et les opérations de construction en mode test ; la
définition exacte du gabarit doit rester celle de TrainLineAI, pas celle d'AdmiralAI. Coût :
O(K × A) lectures/tests pour K sites locaux et A orientations (quatre au plus) ; les essais de
nivellement font croître le coût avec l'aire de gare, mais restent locaux. Ne pas exécuter de
mutation réelle avant la barrière.

**Redondance avec la distance : passe nettement.** À distance de centres identique, une ville peut
offrir quatre sorties, une seule, ou aucune ; bâtiments, pente et orientation locale changent ces
comptes sans changer la distance inter-ville. C'est aussi une cause directe d'échec : le builder
retourne immédiatement quand sources ou goals est vide
(ai/AdmiralAI/rail/railroutebuilder.nut:288-290).

**Verdict : tester en premier, mais petit.** Ce n'est pas l'inventaire cargo/moteur/quai déjà
écarté avec AAAHogEx : c'est la **multiplicité locale des sorties** et son orientation vers le
but. Elle rejoint l'observation déjà ouverte dans cette évaluation sans la dupliquer. Commencer
par les trois comptes ci-dessus, pas par un score composite ; avec 380 exemples, les bins 0/1/2+
sont plus défendables qu'une pseudo-précision de coût de terrassement.

### 2.3 Faisabilité bidirectionnelle en 200 expansions — **passe, mais déjà couverte**

**Lu dans le code.** Avant chaque recherche complète, le builder vérifie le sens retour avec
reverse_signals = true et FindPath(200) (ai/AdmiralAI/rail/railroutebuilder.nut:292-302,
ai/AdmiralAI/rail/railroutebuilder.nut:396-405). Cette recherche fait partie de son pathfinder maison. AyStar maintient une frontière
prioritaire _open et un fermé _closed (ai/AdmiralAI/aystar.nut:170-194) ; une tranche inachevée
renvoie false sans nettoyer cet état (ai/AdmiralAI/aystar.nut:196-270).

**Mesure possible.** Issue à 200 expansions dans les deux sens, et — si l'instrumentation est sous
notre contrôle — taille du fermé, taille de la frontière, meilleur coût et distance restante.
APIs : le pathfinder/les listes, plus les tests de voisins AIRail.BuildRail, AIBridge.BuildBridge
et AITunnel.BuildTunnel qu'il effectue sous AITestMode
(ai/AdmiralAI/rail/railpathfinder.nut:166-178,
ai/AdmiralAI/rail/railpathfinder.nut:294-391,
ai/AdmiralAI/rail/railpathfinder.nut:425-449). Coût : exactement le budget de
la sonde ; deux directions doublent à peu près la recherche courte.

**Redondance avec la distance : passe.** À même distance, eau, relief, contraintes d'entrée,
routes et obstacles changent radicalement la taille et la forme de la recherche. C'est précisément
le type de variation que le scan linéaire ne voit pas.

**Verdict : ne pas ajouter une seconde feature.** C'est une confirmation indépendante de la sonde
A* tronquée déjà prometteuse, non une nouvelle mesure. La seule variation raisonnable serait
d'ajouter une tranche très précoce et le sens retour **aux mêmes sondes**, avec validation
appariée ; elle ne mérite pas un modèle ni un preflight distinct.

### 2.4 Coût de côte, route, pente, pont et tunnel — **passe, mais pas mesurable séparément**

**Lu dans le code.** Le coût de chemin pénalise une côte, une tuile routière, les pentes, les
tours, les ponts et tunnels ; une tuile de hauteur maximale zéro est rendue invalide
(ai/AdmiralAI/rail/railpathfinder.nut:207-285). Ponts/tunnels sont des voisins de l'A*, avec
longueurs plafonnées à 8/10 dans cette IA (ai/AdmiralAI/rail/railpathfinder.nut:49-65,
ai/AdmiralAI/rail/railpathfinder.nut:425-449), pas un corridor préalable.

**Mesure possible.** Les compteurs de ces événements sur le meilleur préfixe, ou le coût g du
meilleur nœud, après un budget de recherche fixé. API : AITile.IsCoastTile,
AITile.HasTransportType, AITile.GetSlope, AIBridge et AITunnel, via l'exploration A*. Coût :
celui de l'A* ; il n'existe pas ici de version locale bon marché qui conserve les détours.

**Redondance avec la distance : passe.** Ces événements varient à distance constante. Mais ils ne
sont observables qu'après avoir choisi un chemin ; les remplacer par un balayage de la droite
retomberait dans les mesures déjà infirmées (corridor_*).

**Verdict : ne pas tester isolément.** Le meilleur coût, la distance restante et la taille de
frontière de la sonde contiennent déjà une version moins arbitraire de cette information. Ajouter
un compteur par obstacle multiplierait les degrés de liberté pour un échantillon trop petit.

### 2.5 Test exact de pose et retries du builder — **rejeté avant test**

**Lu dans le code.** Après un chemin complet, BuildPath() pose réellement rail, pont ou tunnel
et échoue au premier problème non résolu ; seul un véhicule bloquant est retenté jusqu'à 20 fois
avec attente (ai/AdmiralAI/rail/railroutebuilder.nut:545-628). Le route builder recommence au
plus trois fois (ai/AdmiralAI/rail/railroutebuilder.nut:303-318,
ai/AdmiralAI/rail/railroutebuilder.nut:406-420).

**Mesure imaginable.** Booléen « la pose test du chemin complet réussit », ou nombre de retries.
API : AIRail.BuildRail, AIBridge.BuildBridge, AITunnel.BuildTunnel, sous AITestMode pour le
booléen. Coût : une recherche complète plus une simulation de chaque segment ; élevé et
indisponible sur les PATHLIM sans déplacer la barrière.

**Redondance avec la distance : passe**, puisqu'il encode l'obstacle exact. **Mais verdict :
rejeté.** C'est presque la variable cible, calculée trop tard, et la phase précédente peut muter
le terrain (§1). Ce n'est pas une feature de l'étage 1 comparable entre succès et limites de
pathfinding.

### 2.6 RailFollower, TownManager et StationManager — **pas de candidat rail neuf**

Le nom RailFollower suggère un parcours incrémental, mais le code le réserve à la conversion
d'une ligne existante (ai/AdmiralAI/rail/trainline.nut:269-340). Il ne parcourt que les rails
possédés, compatibles et sans station/signal dans le mauvais sens
(ai/AdmiralAI/rail/railfollower.nut:113-161), puis est appelé d'un coup avec 200 000 itérations
(ai/AdmiralAI/rail/trainline.nut:319-325). **Redondance : sans objet** pour une ligne non construite ; aucun test.

TownManager gère seulement les arrêts routiers et aéroports, non le choix d'une gare ferroviaire
(ai/AdmiralAI/townmanager.nut:20-95). Ses comptes de routes voisines et son filtre
d'acceptation sont spécifiques aux bus (ai/AdmiralAI/townmanager.nut:387-395,
ai/AdmiralAI/townmanager.nut:398-505) ; StationManager plafonne de même la
charge de bus/camions (ai/AdmiralAI/stationmanager.nut:215-297). **Redondance : sans objet**
pour notre cible rail ; aucun test. Leur présence ne constitue donc pas une seconde source
indépendante de features de ville.

---

## 3. Ce qui n'a pas d'équivalent chez AAAHogEx

La nouveauté réelle de cette lecture est le **graphe géométrique de voisinage** : AAAHogEx n'avait
pas cette sélection explicite d'arêtes par quadrants, tiers-points et suppression de croisements.
Mais l'absence d'équivalent n'est pas un argument de valeur : AdmiralAI l'emploie pour préparer
son réseau routier, et il ne code ni régions, ni composantes, ni flood-fill, ni distance de graphe
du terrain. La réponse à la question initiale est donc nette : **non, AdmiralAI ne fournit pas de
notion de connectivité pré-construction qui capterait ce que manque un scan linéaire.**

Son autre apport est plus modeste mais exploitable : il rend visible que l'extrémité d'une ligne
n'est pas un point. Avant l'A*, il y a un petit ensemble orienté de sorties possibles, dont le
cardinal peut être zéro. AAAHogEx avait déjà motivé l'idée générale de sites de gare faisables ;
AdmiralAI en fournit la forme la plus parcimonieuse pour notre problème : compter les **issues
dirigées vers l'autre extrémité**, plutôt que d'ajouter un grand score de gare.

---

## 4. Recommandation franche

Ne pas lancer de piste « graphe de régions » : elle n'existe pas dans AdmiralAI. Ne pas séparer les
coûts de relief/eau/route ni recopier son test de pose : la sonde A* les agrège déjà, et le builder
est trop tardif et partiellement mutant.

Faire **un unique essai apparié** de station_site_count et outward_exit_count aux deux bouts, en
conservant strictement la règle de non-mutation avant le tick 11000. Si ces quelques variables ne
battent pas la distance hors des mêmes plis, classer définitivement AdmiralAI comme piste de
mesure : la lecture aura alors fourni une impasse claire, plus la confirmation que l'effort doit
rester sur l'instrumentation A*.
