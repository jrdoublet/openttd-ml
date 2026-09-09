Ces deux sources — la page de comparaison du Wiki OpenTTD et surtout le grand banc d'essai mené par **Redirect Left** sur *Transport Tycoon Forums* (qui teste et note méthodiquement toutes les IA sur des cartes $1024 \times 1024$) — donnent un retour d'expérience précieux. Très peu d'IA survivent longtemps sans planter : **AAAHogEx** (par Samu/xarick), **NoNoCAB** et **SuperSimpleAI** sont parmi les rares références de stabilité.

Voici la synthèse des pièges éliminatoires, des réglages attendus et de la gestion CPU.

---

### 1. Ce qu'il faut absolument ÉVITER

Ces défauts représentent 90 % des crashs et des plaintes de joueurs dans les tests de Redirect Left :

* **Le crash *« excessive CPU usage in valuator function »* :** L'erreur n°1. Si tu passes une fonction Squirrel personnalisée à `AIList.Valuate(MaFonction)` sur une liste de plusieurs centaines d'éléments, Squirrel boucle côté C++ sans pouvoir rendre la main via `Sleep()`. Si le quota interne explose, le moteur tue net ton script.
* **Ignorer les options de jeu du joueur :**
* *Virages à 90° interdits :* Beaucoup d'IA (*MailAI*, *Denver & Rio Grande*) crashent ou créent des boucles infinies dès que l'option de réalisme `forbid 90 degree turns` est cochée. Ton pathfinding ferroviaire et routier doit impérativement interdire les virages à 90°.
* *Véhicules désactivés :* Si le joueur met `max_trains = 0` ou désactive les avions dans sa partie, l'IA ne doit pas crasher à l'initialisation parce qu'une liste d'engins est vide.


* **Hardcoder les identifiants (incompatibilité NewGRF) :**
* Ne jamais supposer que `cargo 0 = passagers` ou `cargo 1 = charbon`. Avec des sets comme FIRS, ces ID changent. Utilise toujours `AICargo.CC_PASSENGERS` via `AICargoList`.
* Ne jamais supposer que le type de rail `0` existe (des sets comme NuTracks modifient les types de voies par défaut). Utilise `AIRailTypeList()`.


* **Comportements toxiques pour le joueur :**
* *Spam d'arrêts en pleine rue (on-road) :* Saturer les rues municipales de bus qui bloquent les véhicules du joueur humain crée un rejet immédiat. Privilégie les gares hors voirie (*off-road*) dès que l'espace le permet.
* *Acheter les droits exclusifs municipaux :* Verrouiller le transport dans une ville via l'autorité locale (*LudAIAfterFix*) est considéré comme anti-jeu en solo comme en multijoueur.
* *Raser le centre-ville :* Détruire des dizaines de maisons fait chuter la note municipale sous *Appalling*, bloquant toute construction future.


* **Gares orphelines et voies en cul-de-sac :** Si un chantier échoue à mi-parcours faute de cash ou d'espace, ne laisse pas des rails fantômes et des gares vides qui consomment de la maintenance et polluent la carte.

---

### 2. Les options indispensables à rendre paramétrables (`info.nut`)

Pour qu'une IA soit adoptée, elle doit s'adapter au scénario du joueur via `AIInfo::GetSettings()` :

* **Interrupteurs modaux (Booléens) :**
* Autoriser / interdire individuellement : `enable_rail`, `enable_road`, `enable_air`, `enable_water`. Si un joueur crée une carte 100 % îles, il veut pouvoir forcer navires et avions ; sur une carte montagneuse, il voudra peut-être couper l'aérien.


* **Gestion du niveau de log / Verbose :**
* Une option `log_level` (0 = Muet, 1 = Actions majeures, 2 = Débogage complet). Les joueurs détestent voir la console de debug polluée de messages toutes les trois secondes.


* **Agressivité / Profil d'investissement :**
* Le fameux ratio $\alpha$ (Bâtisseur rapide vs Gestionnaire prudent à fort ROI), ou un choix multiple (AddLabels) avec profils.


* **Politique d'aménagement urbain :**
* Autoriser ou non les arrêts de bus traversants sur la voirie municipale (*allow_drive_through_town_roads*).


* **Marge de sécurité financière :**
* Trésorerie minimale à conserver en banque avant d'engager un nouveau chantier (ex. slider de 10 000 £ à 100 000 £).



---

### 3. Comment prévenir les problèmes de CPU

OpenTTD est mono-threadé : une IA mal optimisée fait chuter les IPS (images par seconde) du jeu entier. Voici l'arsenal technique pour rester sous les radars du scheduler :

#### A. Bannir les fonctions Squirrel dans `Valuate`

* **À faire :** Utiliser uniquement des méthodes C++ natives dans `AIList.Valuate()` (ex. `list.Valuate(AITown.GetPopulation)` ou `list.Valuate(AITile.GetSlope)`). Elles s'exécutent en code machine compilé à la vitesse du C++.
* **À proscrire :** `list.Valuate(MonScriptSquirrel.CalculCustom)`. Si tu dois exécuter une logique Squirrel sur des milliers d'éléments, fais une boucle manuelle avec un lotissement (*chunking*) et cède la main :
```squirrel
local count = 0;
for (local item = list.Begin(); !list.IsEnd(); item = list.Next()) {
    // Ton calcul custom ici...
    if (++count % 50 == 0 && AIController.GetOpsTillSuspend() < 3000) {
        AIController.Sleep(1); // Rend la main au moteur
    }
}

```



#### B. Généraliser le Tick Budgeting sur les boucles de recherche

Dans tout pathfinder ou scan de zone (comme la recherche d'aéroports ou de côtes navigables) :

```squirrel
if (AIController.GetOpsTillSuspend() < 250 adversaries_threshold) {
    AIController.Sleep(1);
}

```

Si le quota d'opcodes restants sur le tick tombe sous les 2 500 – 3 000, fais un `Sleep(1)`. Le jeu restera à 60 IPS fluide pour l'utilisateur, et ton IA n'aura aucun à-coup de calcul.

#### C. Fail-Fast géométrique (éliminer 90 % des candidats pour zéro opcode)

Avant de lancer un A* ou d'évaluer la rentabilité d'une liaison :

1. Calculer la distance Manhattan : si elle est hors limites, élimination directe.


2. Vérifier les tuiles de départ/arrivée avec `AITile.IsBuildable` ou la pente sans instancier `AITestMode`.


3. Ne réserver les calculs d'itinéraires complets qu'aux paires ayant passé tous les filtres légers.



#### D. Surveiller la mémoire vive (RAM de la VM)

Redirect Left relève que certaines IA font grimper leur empreinte RAM à plus de 50 Mo (au lieu de 5 à 10 Mo pour une IA saine comme AAAHogEx). En Squirrel, cela arrive quand on stocke de gigantesques listes de tuiles ou des historiques de logs dans des tables globales. Détruis (`null`) tes tables intermédiaires dès qu'un chantier est achevé ou abandonné pour soulager le ramasse-miettes (*garbage collector*).




Ces deux bibliothèques sont les boîtes à outils les plus complètes de l'écosystème NoAI d'OpenTTD. Elles ont été conçues pour éviter aux développeurs de réécrire des milliers de lignes de fonctions utilitaires (*boilerplate*) autour de l'API Squirrel.

---

### 1. SuperLib (par Zuu)

Créée par **Zuu** (développeur historique d'OpenTTD et auteur d'IA réputées comme *CluelessPlus* et *DictatorAI*), **SuperLib** est le standard de fait de la communauté. Pratiquement la moitié des IA publiées sur BaNaNaS reposent sur elle.

Elle rassemble des dizaines de fonctions utilitaires découpées en sous-espaces de noms :

* **`SuperLib.Tile` & `SuperLib.Direction` :** Simplifie la manipulation spatiale. Convertit les deltas $(x, y)$ en directions OpenTTD, calcule les virages (45°, 90°, demi-tour), détecte les pentes complexes et vérifie la constructibilité sans multiplier les blocs `AITestMode`.
* **`SuperLib.OrderList` :** L'un des modules les plus précieux. Manipuler la classe native `AIOrder` est réputé piégeux (gestion des drapeaux de chargement, ordres conditionnels, passage au dépôt). `SuperLib.OrderList` offre une abstraction robuste pour construire, cloner et vérifier les listes d'ordres sans provoquer d'erreurs de script.
* **`SuperLib.Station` & `SuperLib.Airport` :** Fonctions pour tester le captage d'une gare (*catchment area*), bâtir des terminus routiers, des arrêts traversants (*drive-through*) ou détecter l'orientation idéale d'un aéroport.
* **`SuperLib.Engine` :** Filtres prêts à l'emploi pour sélectionner le meilleur véhicule d'une époque selon le ratio puissance/poids, la capacité ou le coût d'achat.
* **`SuperLib.Money` & `SuperLib.Log` :** Gestion unifiée des messages de débogage avec niveaux de sévérité et calcul simplifié des réserves de sécurité bancaire.

**Licence :** **GPLv2**.

---

### 2. MinchinWeb's MetaLibrary (par Wm. Minchin)

Conçue par **Wm. Minchin** pour son IA **WmDOT** (une IA spécialisée dans la voirie et l'aménagement du territoire façon ministère des transports), la **MetaLibrary** adopte une approche très différente : là où SuperLib s'occupe de la logistique du jeu, MetaLibrary se concentre sur **la géométrie, la topologie de la carte et le maritime**.

Ses modules phares sont particulièrement originaux :

* **`MinchinWeb.Lakes` (remplaçant de `WaterbodyCheck`) :** Vérifie si deux tuiles d'eau appartiennent au même plan d'eau navigable. Contrairement à un BFS naïf tuile par tuile, `Lakes` **mémorise le travail déjà effectué** : une fois qu'un bassin maritime est exploré, toutes les requêtes suivantes entre n'importe quel point de cette mer s'exécutent en $O(1)$.


* **`MinchinWeb.Marine` & `MinchinWeb.ShipPathfinder` :** L'une des très rares implémentations NoAI de recherche de chemin pour navires. Elle trace des trajectoires maritimes géométriques et pose automatiquement des bouées à intervalles réguliers et dans les virages pour éviter que le moteur du jeu ne perde les bateaux au large.


* **`MinchinWeb.Atlas` :** Un générateur de paires Origine-Destination. À partir d'une liste de sources (mines, forêts) et d'attractions (usines, centrales), il pondère les combinaisons possibles et sort une liste classée de liaisons à bâtir.
* **`MinchinWeb.SpiralWalker` & `MinchinWeb.LineWalker` :** Des itérateurs spatiaux très efficaces en opcodes :
* `LineWalker` avance en ligne droite ou selon une pente pour tester un corridor (*raycasting*).


* `SpiralWalker` parcourt le terrain en spirale à partir d'un centre donné (idéal pour chercher un emplacement plat de $4 \times 3$ ou $6 \times 6$ tuiles pour un aéroport ou un dépôt sans scanner toute la ville).




* **`MinchinWeb.DLS` (*Dominion Land System*) :** Un wrapper pour le pathfinder routier contraignant le réseau à se calquer sur une grille orthogonale propre.

**Licence :** Licence permissive de type **MIT / Expat** pour la quasi-totalité de la bibliothèque (à l'exception de son wrapper `RoadPathfinder` qui est sous **LGPLv2.1**).

---

### Comparatif direct

| Caractéristique | SuperLib (Zuu) | MetaLibrary (MinchinWeb) |
| --- | --- | --- |
| **Philosophie** | Boîte à outils logicielle, logistique et API-wrapper. | Outils géométriques, maritimes et topologiques. |
| **Point fort n°1** | Gestion des ordres de véhicules (`OrderList`) et des gares. | Gestion de l'eau (`Lakes`, `ShipPathfinder`) et itérateurs (`SpiralWalker`). |
| **Impact CPU / Opcodes** | Moyen (beaucoup de code Squirrel, parfois des boucles évitables).

 | Faible à moyen (structures géométriques optimisées et caches). |
| **Popularité** | Omniprésente, maintenue et documentée. | Moins répandue, pensée initialement pour *WmDOT*. |
| **Licence** | **GPLv2** | **MIT / Permissive** (sauf module route sous LGPL). |

---

### Intérêt pour ton IA

Au vu de ton code actuel :

1. **Pour ton builder maritime (`builder_water.nut`) :** `MinchinWeb.Lakes` résout exactement le problème de tes BFS répétitifs qui saturent tes opcodes sur l'eau libre. Son `ShipPathfinder` gère nativement le placement des bouées.


2. **Pour ta recherche de sites aériens ou de gares :** `MinchinWeb.SpiralWalker` évite de scanner des rectangles complets à la main avec `AITestMode`.


3. **Pour la gestion de flotte :** `SuperLib.OrderList` évite les déraillements de logique lors de l'attribution des ordres aux véhicules ou du remplacement de matériel vieilli.

À noter : comme ton constructeur ferroviaire importe déjà `pathfinder.rail` (qui est sous GPLv2), le fait d'importer SuperLib ou MetaLibrary ne changera plus ton statut de licence : ton projet est déjà lié au copyleft GPLv2.