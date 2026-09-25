# C94 — Vers un arbitrage économique unifié

**Note d'architecture — 2026-09-25.**

Cette fiche décrit une **direction de convergence**, pas un chantier à implémenter d'un bloc.
La priorité immédiate reste de rattraper AAAHogEx avec des changements simples, mesurables et
réversibles sur les tâches déjà présentes. Le score économique plus riche décrit ici sera raffiné
seulement quand l'ordonnanceur et le débit de décisions ne constitueront plus le principal écart.

## 1. Point de départ : trois mécanismes aujourd'hui séparés

Le code courant possède déjà trois niveaux distincts :

1. **File réactive C80** : FIFO avec coalescence par clé. Elle ne possède pas de score entre
   intentions. Les producteurs actuels incluent notamment C77 (`c77_entity`, `c77_build`,
   `c77_subsidy`).
2. **Travailleurs résumables** : un seul worker actif (`rail_search`, `town_growth`,
   `regen_candidates`, etc.). Le registre d'exécution décide comment fractionner le calcul ; il ne
   compare pas la valeur économique de plusieurs workers concurrents.
3. **File de fond** : round-robin historique avec `dueCycle`. `catalog`, `air_fleet`, `projects`,
   `expand`, `refleet`, `town_growth`, `repay`, etc. ne sont pas classés par score.

Le **score existe déjà surtout à l'intérieur du portefeuille de projets**. Au défaut courant, le
classement final repose sur `fundScore`, avec C69/C70 :

```text
fundScore = profit_calibré × 1000 / max(financeCapital, K_dec)

K_dec = F × tau
F     = flux de trésorerie opérationnel observé
tau   = intervalle observé entre décisions de construction
```

Les projets AIR ajoutent aujourd'hui deux couches stratégiques qui ne sont pas encore unifiées avec
ce score :

- `earlySlotBonusPct`, qui modifie le score de sélection ;
- C83, qui utilise une **classe lexicographique** avant le score (`competitorClaims` puis
  `ownClaims`) pour protéger une ressource périssable : le slot aéroportuaire.

Conclusion : il n'existe pas encore de « score des tâches ». Il existe un **score des projets**, plus
des exceptions stratégiques et un ordonnanceur séparé.

## 2. Architecture cible : séparer information, décision et exécution

La cible à long terme n'est pas de donner un gros score opaque à chaque fonction du scheduler.
Elle est de séparer trois responsabilités :

```text
MONDE / ÉVÉNEMENTS / ÉTAT COURANT
              │
              ▼
PRODUCTEURS D'INFORMATION ET D'OPPORTUNITÉS
  catalog, scan slots, air_fleet, générateurs rail/route/air/eau,
  tension des lignes, renouvellement, croissance urbaine, subventions...
              │
              ▼
REGISTRE COMMUN D'OPPORTUNITÉS ÉCONOMIQUES
  nouvelle ligne, +avion, refleet, expansion, slot, subvention, etc.
              │
              ▼
1. contraintes dures / validité
2. urgence ou péremption
3. score économique commun
              │
              ▼
MEILLEURE ACTION CONNUE À CET INSTANT
              │
              ▼
REGISTRE D'EXÉCUTION / WORKER
```

Le scheduler de calcul répond alors surtout à :

> **Quelle information est assez importante ou assez périmée pour mériter du CPU maintenant ?**

Le moteur économique répond séparément à :

> **Parmi les actions connues et encore valides, laquelle doit consommer notre prochain capital et
> notre prochain créneau de décision ?**

Cette séparation est cohérente avec le mandat initial C80 : découpler la décision de l'effort de
calcul.

## 3. Premier étage : contraintes dures, pas de pénalités molles

Une action impossible ou invalide doit être éliminée avant tout classement. Exemples :

- capital réellement insuffisant ;
- slot déjà fermé ;
- projet devenu stale ;
- moteur non disponible ;
- ligne en liquidation ;
- ville ou station non constructible ;
- géométrie devenue invalide ;
- action déjà satisfaite ou dupliquée.

Ces états ne doivent pas devenir de simples « mauvais scores ». Une impossibilité reste une
impossibilité.

## 4. Deuxième étage : urgence et péremption

Certaines actions perdent leur valeur si elles attendent. Le score économique seul ne suffit pas à
représenter proprement une deadline dure ou quasi dure.

Conserver une petite hiérarchie d'urgence est donc souhaitable, par exemple :

```text
classe 3 : intégrité / réparation critique
classe 2 : ressource périssable ou occasion temporelle
classe 1 : investissement économique normal
classe 0 : administratif / confort
```

Exemples typiques :

- crash ou infrastructure cassée : intégrité ;
- course au deuxième slot C83 : ressource périssable ;
- subvention proche de l'expiration : occasion temporelle ;
- nouvelle ligne rentable ou renfort de flotte : investissement normal ;
- remboursement de dette ou rapport : administratif.

Le classement économique s'applique **à l'intérieur d'une même classe**. Cette structure évite
qu'un avantage minime de ROI fasse perdre irréversiblement une ressource rare.

## 5. Troisième étage : score économique commun

À terme, le score devrait comparer des actions aujourd'hui traitées dans des tâches différentes.
La forme cible conceptuelle est :

```text
Valeur(action)
 = profit futur calibré
 + valeur stratégique observable
 + valeur d'option préservée
 - coût du capital
 - coût du délai
 - coût de calcul / décision
 - risque d'échec
```

Le but n'est **pas** d'empiler immédiatement des coefficients magiques. Chaque terme doit être relié
à une quantité mesurable ou à un contre-factuel observable.

### 5.1 Capital et débit de décision

C69 constitue déjà une première forme de coût d'opportunité : `K_dec = F × tau`. Une décision chère
est comparée non seulement au capital qu'elle immobilise, mais aussi à ce que l'entreprise produit
pendant l'intervalle entre deux décisions.

Cette base doit être conservée tant qu'un banc ne démontre pas mieux.

### 5.2 Slots et ressources rares

La présence d'un slot ne doit pas se traduire durablement par « +X % au score » choisi à la main.
La bonne question économique est :

> **Quelle valeur future devient inaccessible si nous ne prenons pas cette ressource maintenant ?**

La valeur d'un slot dépend donc au minimum de :

- la demande et le profit potentiel de la ville ;
- le nombre de slots restant ;
- notre présence actuelle ;
- la présence concurrente ;
- l'existence d'un projet réellement rentable et constructible ;
- la probabilité observable que la ressource soit consommée avant notre prochain passage.

C83 reste pour l'instant une classe lexicographique explicite. À long terme, elle peut devenir le
premier cas concret d'une valeur d'option mesurée.

### 5.3 Concurrence : comportement observé avant identité supposée

La concurrence doit affecter la valeur **par ce qu'elle change dans le monde**, pas par une simple
étiquette de joueur.

Signaux exploitables :

- slots déjà consommés ;
- cadence récente de prise de marchés ;
- présence concurrente dans la même ville ou sur la même relation ;
- temps entre première et deuxième implantation ;
- ressources encore accessibles ;
- évolution de la part territoriale ou du nombre de stations.

Cette approche permet de réagir naturellement à un adversaire agressif comme AAAHogEx sans dépendre
de son nom. Si C88 fournit plus tard un moyen fiable de distinguer humain et IA, cette information
pourra servir de **prior/calibration**, pas de fondation du modèle.

Ne jamais identifier AAAHogEx ou un humain par le nom de compagnie, le niveau de trésorerie ou une
heuristique fragile.

### 5.4 Opcodes et temps de décision

Le coût pertinent n'est pas « beaucoup d'opcodes = mauvais ». Le coût pertinent est :

> **Combien d'autres décisions de valeur sont retardées par ce calcul ?**

Une approximation future pourra donc relier :

```text
coût_calcul ≈ expectedOps × valeur marginale du temps de décision
```

ou travailler directement en jours de jeu consommés lorsqu'ils sont mesurables. Un A* ferroviaire
coûteux peut rester optimal s'il ouvre un projet exceptionnel ; une régénération de catalogue qui
recalcule l'identique doit tendre vers une valeur nulle et donc ne pas être admise.

### 5.5 Deuxième architecture opcodes : les workers consomment le reliquat du tick

Le coût des opcodes ne doit pas seulement apparaître comme une pénalité dans le score économique.
Il existe une seconde architecture, complémentaire : **prendre d'abord la décision utile du tick,
puis dépenser le reliquat d'opcodes sur des workers résumables** au lieu de le perdre avant
`Sleep(1)`.

V89 constitue déjà un prototype spécialisé de ce mécanisme pour l'A* rail :
`_advanceRailSearchThroughput()` avance des tranches supplémentaires tant que
`AIController.GetOpsTillSuspend()` permet de payer une tranche avec marge de sécurité. La cible est de
généraliser ce principe à un petit ensemble de workers, pas de réserver le slack au rail.

```text
tick
 │
 ├─ événements / watcher léger
 ├─ décision réactive ou économique prioritaire
 ├─ tâche de fond réellement due
 │
 └─ tant qu'il reste un budget sûr :
       choisir le worker marginalement le plus utile
       exécuter UNE tranche bornée
       mettre à jour son état / ses sorties prêtes
       réarbitrer
 │
 └─ Sleep(1)
```

Cette architecture est **différente de `loop_budget`**, historiquement rejeté. `loop_budget`
enchaînait des tâches complètes et pouvait brûler du CPU sans faire progresser le jeu. Ici, seules des
**tranches résumables et bornées** consomment le reliquat déjà alloué au tick ; elles s'arrêtent avant
la suspension et ne déclenchent pas une nouvelle rafale de décisions économiques.

À terme, le registre d'exécution doit donc pouvoir conserver plusieurs travaux prêts à avancer, au
lieu d'un unique `_activeWorker` monopolistique. Exemples naturels :

- `rail_search` : avancer un A* ;
- `town_growth` : préparer/continuer l'analyse d'une ville ;
- `regen_candidates` : régénération ciblée ;
- C67 : calcul d'un bloc de cartographie demandé ou remplissage opportuniste.

L'arbitrage entre workers ne doit pas être un simple ordre fixe. Il dépend de **l'état du pipeline** :

- travail bloquant une décision économique immédiate ;
- nombre de résultats déjà prêts en aval ;
- demandes métier en attente ;
- proximité d'achèvement d'une unité qui débloque une sortie utilisable ;
- âge d'une demande ;
- coût estimé de la prochaine tranche face au reliquat réellement disponible.

Exemple central :

```text
aucun tracé rail prêt + projet rail bloqué
    → rail_search très utile

plusieurs tracés / plans rail déjà prêts à consommer
    → valeur marginale d'un A* supplémentaire baisse
    → le reliquat peut aller à town_growth ou à C67

bloc C67 demandé par le projet actuellement en tête
    → cartographie demandée prioritaire

aucune demande C67 métier
    → remplissage cartographique seulement avec le reliquat vraiment libre
```

Le **travail déjà dépensé n'est pas à lui seul une raison de continuer** : éviter le biais de coût
irrécupérable. Ce qui compte est ce que l'état d'avancement change dans la valeur marginale de la
prochaine tranche. Un A* presque fini peut recevoir une prime de complétion s'il débloque réellement
un projet ; un A* à moitié calculé mais dont plusieurs alternatives sont déjà prêtes peut attendre.

La première version ne doit pas chercher une formule parfaite. Elle peut utiliser des classes
explicites et observables :

1. worker qui **débloque** l'action économique courante ;
2. worker avec demande métier explicite ;
3. worker qui alimente un stock devenu insuffisant ;
4. travail opportuniste de fond.

À égalité, vieillissement/FIFO suffit. Les coefficients plus fins ne viennent qu'après mesure.

Cette politique rend C67 beaucoup plus naturelle : la cartographie n'a pas besoin d'un tour
monolithique propre. Ses `Request()` métier créent du travail prioritaire ; son remplissage de fond
consomme les petits reliquats que ni l'A* ni les autres workers n'utilisent utilement.

## 6. Ce que cela implique pour les tâches actuelles

L'évolution souhaitée est progressive : transformer autant que possible les tâches économiques en
**producteurs d'opportunités**, puis laisser un registre commun les arbitrer.

Exemples :

| tâche actuelle | cible progressive |
|---|---|
| `air_fleet` | produit « ajouter N avions à telle ligne, coût C, gain P » ; le portefeuille arbitre |
| générateurs AIR/rail/route/eau | produisent de nouvelles lignes comparables |
| `expand` | produit une opportunité d'expansion avec coût et gain attendu |
| `refleet` | produit un remplacement avec coût, gain et urgence technique |
| C83 watcher | produit une occasion périssable ciblée, sans construire lui-même |
| `town_growth` | à terme, produit une action avec valeur économique estimée plutôt qu'un bloc autonome |
| `repay` | reste d'abord administratif ; éventuelle comparaison économique beaucoup plus tard |
| `catalog` / scans | restent des tâches d'information, non des investissements |

Le passage doit être incrémental : **ne pas convertir toutes les tâches en même temps**.

## 7. Stratégie de mise en œuvre : commencer doucement

La priorité actuelle est le rattrapage d'AAAHogEx. On ne cherche donc pas encore la fonction objectif
finale. On applique d'abord les principes ci-dessus aux structures existantes avec le minimum de
nouveaux degrés de liberté.

### Phase A — maintenant : débit, admission, réactivité

1. Éliminer les tours `no-op` sûrs (`skip-not-due`).
2. Sortir le watcher C83 de `projects` pour qu'il alimente réellement la file réactive.
3. Faire viser à C83 l'occasion précise plutôt qu'un `_tryBuildProjects()` générique.
4. Mesurer le reliquat réel après les tâches courtes et généraliser prudemment le mécanisme V89 :
   une tranche d'un worker existant peut consommer ce reliquat avant `Sleep(1)`, sans enchaîner une
   seconde décision économique.
5. Rendre progressivement les maintenances conditionnelles lorsque l'éligibilité est bon marché.
6. Conserver le score de portefeuille C69/C70 et les règles C83 actuelles, sauf mesure causale
   contraire.

**Objectif de Phase A : plus de décisions utiles par année et moins de latence, sans nouveau modèle
économique général.**

### Phase B — une fois le scheduler assaini : producteurs d'opportunités

Migrer une famille à la fois vers le registre commun :

1. `air_fleet` en premier, car `FLEET_PORTFOLIO` fait déjà une grande partie du travail ;
2. expansion/refleet ;
3. faire évoluer le registre d'exécution d'un `_activeWorker` unique vers un petit ensemble de
   workers arbitrables si l'exposition le justifie ;
4. intégrer C67 comme premier nouveau consommateur natif de cette allocation du reliquat ;
5. éventuellement `town_growth` si son coût d'opportunité reste matériel.

Chaque migration doit montrer qu'elle réduit une duplication d'arbitrage ou améliore le résultat au
banc. Pas de « grand rewrite ».

### Phase C — seulement après rapprochement d'AAAHogEx : enrichir le score

À ce stade seulement, mesurer puis introduire progressivement :

- valeur d'option des slots ;
- pression concurrentielle observable ;
- coût de calcul/opcodes ;
- valeur du délai ;
- risque de péremption ;
- éventuel prior humain/IA si C88 donne une information fiable.

Chaque terme doit commencer comme **sonde passive** : calculer et journaliser le contre-classement
sans modifier la décision. Une variante ne devient active qu'après exposition démontrée et banc
causal.

## 8. Garde-fous

1. **Pas de score monolithique arbitraire.** Aucun empilement de coefficients sans mesure.
2. **Pas de régression vers `fleet_before_new`.** La flotte et les nouvelles lignes doivent être
   comparées comme opportunités, pas servies dans un ordre fixe ; le précédent a été négatif.
3. **Pas de boucle chaude `projects`.** `k_pass` reste une protection générale tant qu'un autre
   mécanisme n'est pas qualifié.
4. **Pas de dépendance au nom d'AAAHogEx.** Mesurer le comportement concurrentiel observable.
5. **Pas d'optimisation CPU isolée.** Une baisse d'opcodes sans gain économique n'est pas un succès.
6. **Pas de mélange de plusieurs nouveaux termes de score dans un même banc.** Isoler les effets.
7. **Les urgences dures restent explicites.** Une deadline physique ne doit pas être noyée dans un
   ratio économique approximatif.

## 9. Critère pratique de priorité

Tant qu'OpexAI reste nettement derrière AAAHogEx en volume, la règle de travail est :

> **Préférer les améliorations qui augmentent le nombre et la vitesse des bonnes décisions déjà
> connues, avant de raffiner la fonction de valeur de chaque décision.**

Autrement dit : d'abord mieux utiliser le portefeuille existant et rendre les occasions périssables
réellement réactives ; ensuite seulement chercher un score stratégique plus fin.

Cette fiche doit être relue comme une **cible d'architecture**, pas comme une liste de tâches à
enchaîner automatiquement.
