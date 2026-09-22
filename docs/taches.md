# Tâches — réduire l'écart avec AAAHogEx

État courant actualisé le **2026-09-22**. Ce fichier est la **seule liste autoritaire du
travail restant**. Les travaux terminés, résultats et décisions sont dans les journaux ;
une ancienne mention « à faire » ne remet pas un chantier dans cette liste.

## État courant

Le défaut comprend C68 et C69 bis/C70/C75. C76/C77, les travailleurs C80, le mémo de
croissance urbaine, C81 et C82 sont implémentés mais restent expérimentaux à défaut 0.
La version C76 retenue saute la régénération complète sans changement, avec filet annuel.
Les bancs C77 seul et C82 du 22 septembre sont terminés et non adoptés : ils ne sont plus
à lancer. Les feeders et Lakes sont retirés ; la cartographie C67 n'est pas implémentée.

Les preuves, limitations et décisions correspondantes sont dans les journaux des
[20 septembre](journal_2026-09-20.md), [21 septembre](journal_2026-09-21.md) et
[22 septembre](journal_2026-09-22.md). La [source historique intégrale transférée](journal_2026-09-22_transfert_historique.md)
conserve les comptes rendus auparavant empilés ici. Consulter aussi le
[journal du 13](journal_2026-09-13.md) et l'[archive du 9](taches_archive_2026-09-09.md)
avant toute réouverture. Les résultats antérieurs au 9 septembre ne font pas preuve actuelle.

## Travail restant

| Chantier | Statut | Prochaine étape / condition |
|---|---|---|
| **C67 — carte par blocs** | C67.3 à commencer | Prototype C67.2 validé par smoke canonique 1×1, consigné au journal du 22. Prochaine étape : comparaison 5×5/10×10, mémoire/opcodes/précision. [Contrat](c67_cartographie_contrat.md). |
| **C78 — occasions présentes chez AAAHogEx, absentes chez OpexAI** | Suites du diagnostic | Identifier les filtres qui éliminent les paires absentes, expliquer un premier rang finançable non construit et séparer couverture du vivier/rendement par avion. [Fiche](22_c78_lignes_vs_aaa.md). |
| **C80 — ordonnanceur** | Qualification et découpage restants | Socle et travailleurs rail/ville déjà intégrés. Reprendre le respect des bornes par tranche (`town_growth`), l'équité entre files et le coût réel incluant les travailleurs ; ne pas réécrire les tranches livrées. [Contrat et mesures](18_orchestrateur_double_registre.md). |
| **`town_growth_plan_memo`** | À qualifier économiquement | Banc dans la pile C80 sur référence courante ; distinguer économie d'opcodes et gain propre d'OpexAI. [Bilan](16_bilan_volume.md) §11. |
| **C76/C77 — régénération et événements** | Reliquats ciblés | Vérifier la perte de candidats injectés lors d'une régénération complète sous C77 sans C76, signalée au journal du 22. Pas de nouveau 20×10 identique à celui déjà terminé. Toute nouvelle variante exige une hypothèse distincte. |
| **C81 — chargement complet AIR** | Priorité basse | Éventuel duel après examen des résultats solo défavorables ; protocole dans la [fiche nuit](20_nuit_2026-09-22.md). Le simple achèvement du banc C82 n'impose pas ce lancement. |
| **Revue du code** | Reprise à réconcilier avec les travaux en cours | Le [plan du 21](revue_code_2026-09-21_plan.md) est historique ; vérifier les corrections de chargement et intégrations du 22 avant de reprendre un constat. Ne pas traiter la revue locale en cours comme un ensemble de correctifs déjà validés. |
| **C61 AIR** | En pause | Mesurer rotations, attente, demande et occupation avant modification des délais/capacités d'aéroport. |
| **C61 Route / croissance urbaine** | Travail séparé en cours | Réconcilier le reliquat sur les stations actives avec la session concernée avant intervention. |
| **C61 Rail** | Conditionnel | Examiner les `NOSPOT`/`TRACKFAIL` sur lignes rentables demandant réellement un second train avant un chantier de géométrie. |
| **C59 — ordres contextuels** | Non démarré | Corréler remplissage au départ, attente et profit ; une photographie du chargement ne suffit pas. |
| **C68 — cinq graines défavorables** | Suivi sans urgence | Analyse causale de 7, 42, 1337, 12345 et 424242 dans le banc d'adoption, graine 7 d'abord ; distinguer géométrie, investissement et pré-filtres catalogue. Historique dans l'annexe, section « clôture C68 » ; ne pas relancer l'adoption. |

<a id="c76-c77"></a>
### C76/C77 — limites du reliquat

L'implémentation et son intégration sont journalisées le 22. Les anciens contrats de
régénération par mode ne décrivent pas nécessairement la version C76 retenue. Pour le
reliquat des candidats injectés, vérifier la conservation du vivier et les contrats de
Save/Load sur cette version avant de proposer un correctif. La prise opportuniste de slots
adverses ou le renfort déclenché par attente durable restent des possibilités à exposer,
pas des fonctionnalités implicitement livrées ni une autorisation de les ajouter ensemble.

<a id="c61"></a>
<a id="c59"></a>
### Exploitation des lignes — contraintes de mesure

AIR : `airportDelayDays = 3.0` est une hypothèse à mesurer ; une table estimée par type
ne suffit pas à la remplacer. Route : séparer fret, passagers interurbains et croissance
urbaine ; ne pas rouvrir les feeders retirés. Rail : conserver le modèle d'accélération
`OpexRailEffectiveSpeed` (C41). C59 : longue distance ne signifie pas automatiquement
que le chargement complet est supérieur ; intégrer demande, attente et congestion.

<a id="c64"></a>
<a id="c63"></a>
<a id="c58"></a>
<a id="c39"></a>
<a id="c41"></a>
<a id="c44"></a>
## Suites conditionnelles, sans lancement automatique

| Sujet | Condition de reprise |
|---|---|
| C63/C58 — investissement et recettes | Partir d'une erreur de coût/recette ou d'une occasion actuelle identifiée, en tenant compte du ledger C63 corrigé. Ne pas reprendre la conclusion historique « capital exclu » ni réintroduire les prédevis retirés. |
| C39/C41/C44 — calcul et fraîcheur | Occasion finançable retardée par un coût mesuré ; articuler avec C76/C77/C80, sans rouvrir les optimisations rejetées sur la seule foi d'un ancien profil. |
| C64 — politique adaptative | Mécanisme établi, règle pré-enregistrée et graines nouvelles ; pas de nouvelle recherche de seuil sur les graines ayant servi à le découvrir. |
| C43/E3 — constantes | Réserve, `pax_near` ou seuil de rebut impliqué dans une erreur mesurée ; aucun balayage général. |
| C42 bis — subventions | Exposition et rendement du producteur C77 courant ; ne pas restaurer les anciens drapeaux C42 supprimés. |
| C55 — bassins de demande | Sur-service ou partage de flux concurrents effectivement observé ; ne pas rouvrir le filtre d'origine. |
| Compatibilité NewGRF / M3 | Le diagnostic vanilla ne qualifie pas les choix de refit ni leurs capacités ; qualification dédiée si ce runtime entre dans le périmètre. |
| M2, M5/G2, M6, M7/11.3, B6/06.12 | Risques historiquement dormants : vérifier que leur chemin existe encore et devient exposé avant tout lot. |
| Placement/catchment, bruit aéroport, extension de gare, `station_join`, RAM Squirrel | Besoin démontré dans le code courant ; pas de reprise automatique depuis une ancienne liste de revue. |

## C67 — carte par blocs et connectivité

Le chemin actuel est le BFS borné de `builder_water.nut::OpexWaterFindConnection`.
`lib_water.nut` et les réglages Lakes ont été supprimés le 21 septembre, **avant C67**.
Voir le [journal du 21](journal_2026-09-21.md) pour la décision et le commit ; l'analyse
du code est dans le [journal du 22](journal_2026-09-22.md). Ne pas programmer un second retrait.
La consigne d'accord explicite avant un nouveau diagnostic de découverte maritime est conservée.

### Étapes et critères de passage

Les étapes sont séquentielles ; l’analyse initiale est consignée au journal du 22 septembre, sans qualification runtime.
Le [contrat initial C67.1](c67_cartographie_contrat.md) fixe les API proposées et le protocole ;
sa livraison est consignée au journal du 22.

| Étape | Livrable et périmètre | Validation avant passage |
|---|---|---|
| **C67.3 — qualification 5×5 / 10×10** | Harnais dérivé des outils courants, entrées figées. Mesurer 256²/512²/1024²/2048² : demandes localisées à froid puis à chaud, couverture progressive et complète uniquement dans le banc. Comparer RSS avec témoin sans cache, nombre d'entrées, opcodes, ticks, pic par tranche et exactitude des résumés. | Rapport par carte/graine avec dispersion et couverture ; distinguer RSS du processus et estimation du cache Squirrel. Choisir la granularité selon C67.1, ou constater qu'aucune ne convient. Aucun seuil de typage adopté par intuition. |
| **C67.4 — cycle de vie et ordonnanceur** | Intégrer demandes prioritaires et remplissage opportuniste, interruption immédiate aux frontières de tranche, reprise et annulation. Définir invalidation locale après travaux propres et rafraîchissement/revalidation pour changements externes non signalés. Décider quoi reconstruire ou sauvegarder et comment reprendre les demandes après Load. | Vérifier absence de famine métier, borne de tranche, reprise sous pression mémoire et après événement prioritaire. Smoke 1×1 et Save/Load adapté ; mesurer le surcoût même sans consommateur. Ne pas activer implicitement C80 ou un autre réglage expérimental. |
| **C67.5 — graphe et oracle de connectivité** | Graphe de passages/composantes construit à la demande, sans table persistante par tuile sur toute la carte. Corridors proposés au niveau bloc, confirmation fine au niveau tuile ; inconnus conservés quand l'exploration est incomplète. | Comparer à une exploration exacte sur domaines maîtrisés et à un oracle borné qui rend explicitement « inconnu » hors budget/domaine. Cas adverses de côtes, frontières, bassins disjoints, détours et modifications locales ; aucun connecté/déconnecté affirmé à tort sur les fixtures. Mesurer aussi coût et couverture des réponses. |
| **C67.6 — premier consommateur isolé** | Choisir selon exposition observée un seul usage, eau ou corridor d'un autre mode. Mesurer d'abord en observation la prédiction face au chemin exact, puis brancher sous réglage à défaut 0. Préserver distinction distance tarifaire/navigable et contrôles de construction. | Tests de contrat, smoke 1×1, Save/Load si nécessaire puis diagnostic apparié 5 graines × 6 ans contre AAAHogEx. Rapporter taux d'utilisation, erreurs, faux rejets, coût de décision, délais et résultats propres d'OpexAI. Une absence d'exposition ne qualifie pas le consommateur. |
| **C67.7 — adoption puis extensions conditionnelles** | Fixer avant le banc métrique primaire, effet minimal utile et garde-fou de valeur. Qualifier le consommateur retenu ; ouvrir séparément coûts/ROI, choix du mode, implantation et régions naturelles seulement si leur besoin est démontré. | Banc officiel apparié 20 graines × 10 ans complet et sain, verdict effectif du harnais et preuves figées. Adoption du défaut seulement après succès ; un gain de mémoire/opcodes seul ne prouve pas un gain économique. |

**Prochain lot : C67.3.** Mesurer mémoire, opcodes, précision et réemploi sur les tailles
prévues par le contrat. Le smoke C67.2 valide l'exécution, pas ces seuils ni un gain économique.

### Contraintes de conception

**Contrat de conception retenu.** Construire une représentation de carte propre à
OpexAI, commune à l’analyse du terrain et à la future connectivité hiérarchique. La carte
est découpée en blocs carrés réguliers ; deux granularités candidates sont à mesurer, **5×5** et
**10×10 tuiles**. La taille n'est pas fixée par intuition : le premier livrable de C67 doit comparer
coût mémoire/opcodes, précision et utilité pour les décisions.

Chaque bloc porte un résumé compact calculé depuis ses tuiles, au minimum : part eau/terre,
altitudes min/max/moyenne, amplitude de relief, proportion de terrain plat et indicateur de
pente/irrégularité. À partir de ces mesures, le bloc reçoit un type principal tel que **eau**,
**côte/mixte**, **plat**, **vallonné** ou **montagne**. Les seuils exacts et l'éventuel typage
secondaire sont à calibrer sur cartes réelles ; ils ne doivent pas devenir des constantes métier
avant mesure.

Les blocs forment ensuite un graphe spatial léger de voisinage. Ce niveau grossier doit pouvoir
servir à plusieurs consommateurs sans dupliquer des scans de carte : présélection de corridors,
coût/complexité de terrain, détection de grandes zones d'eau et connectivité grossière. Les tests
fins restent au niveau tuile lorsque la construction l'exige ; C67 n'a pas vocation à remplacer un
pathfinder exact par une classification grossière.

**Principe d'exécution : cartographie lazy et opportuniste.** C67 ne doit jamais lancer une grosse
tâche monolithique de cartographie complète au démarrage. Un bloc est calculé lorsqu'un projet a
besoin de l'étudier ; son résultat est ensuite mis en cache et réutilisé. En dehors de ces demandes,
la couverture de la carte peut progresser en tâche de fond par petits lots uniquement quand le
contrôleur dispose d'un budget d'opcodes réellement libre — par exemple lorsqu'aucun projet utile
n'est constructible faute de trésorerie — sans retarder les tâches métier prioritaires. Le scheduler
doit donc pouvoir interrompre/reprendre ce remplissage, lui imposer un budget strict par tranche et
abandonner immédiatement la cartographie de fond dès qu'un travail plus prioritaire apparaît.

La carte peut ainsi rester **partielle** pendant longtemps : les zones pertinentes pour les projets
réels seront naturellement cartographiées en premier. Aucune décision ne doit supposer que 100 % de
la carte est déjà connue ; une donnée de bloc absente signifie « à calculer si nécessaire », pas
« terrain neutre ». Le remplissage opportuniste est un bonus de temps mort, jamais une condition de
démarrage de l'IA ni un motif pour immobiliser des opcodes qui pourraient servir à une décision ou
une construction immédiatement utile.

Usages visés au-delà de la connectivité maritime :

- **prévision économique par projet** : utiliser le corridor de blocs pour estimer plus tôt le coût
  réel probable de construction, le délai avant mise en service et donc un ROI plus réaliste que les
  facteurs fixes actuels ;
- **prévision du coût de décision** : estimer avant le pathfinding exact le nombre d'opcodes et le
  temps/ticks nécessaires pour étudier puis construire un projet, afin d'ordonner les candidats par
  valeur attendue mais aussi par coût de calcul ;
- **pré-pathfinding hiérarchique** : chercher d'abord un corridor grossier dans le graphe de blocs,
  puis limiter l'A* exact aux zones plausibles au lieu d'explorer la carte sans information globale ;
- **risque de faisabilité** : dériver un indicateur de difficulté/échec probable à partir du relief,
  de l'eau, des pentes, de la constructibilité et de la fragmentation du corridor ;
- **choix du mode de transport** : comparer rail/route/eau/air à partir de la structure physique du
  corridor avant de lancer des devis lourds pour chaque famille ;
- **implantation et extensibilité** : repérer les zones adaptées aux gares, dépôts, quais et axes
  d'approche, ainsi que la place disponible pour double voie, allongement ou branches futures ;
- **détection de régions naturelles** : agréger les blocs en plaines, massifs, bassins, îles,
  péninsules ou corridors côtiers pour améliorer la génération même des candidats.

Le **type principal** d'un bloc est seulement une vue simplifiée. La représentation doit conserver
un vecteur de caractéristiques réutilisable, par exemple `water_ratio`, `buildable_ratio`,
`height_min/max/mean`, amplitude de relief, densité de pente, bords côtiers et densité
d'infrastructure. Le typage `eau/plat/montagne/...` est dérivé de ces mesures et ne doit pas faire
perdre l'information brute nécessaire aux modèles de coût, ROI ou temps.

La carte est conceptuellement séparée en deux couches : une **couche physique** relativement stable
(eau, altitude, pente, constructibilité) et une **couche dynamique** (villes, industries,
infrastructures Opex/adverses, gares, voies, routes). Les modifications locales de carte doivent
invalider seulement les blocs concernés. La cible architecturale devient donc :
`candidat -> corridor de blocs -> prévision £ / ROI / opcodes / durée / risque -> portefeuille ->
pathfinding exact seulement pour les candidats retenus`.

Contraintes de conception :

- **aucune structure persistante à une entrée par tuile de la carte entière**, contrairement à
  Lakes ; à 2048², une grille 5×5 représente au plus ~168 100 blocs et une grille 10×10 ~42 025,
  contre 4 194 304 tuiles ;
- construction interruptible/mesurable en opcodes et mémoire, compatible avec les grandes cartes ;
- représentation indépendante de MinchinWeb, réutilisable par eau **et** analyse générale du
  terrain ;
- stratégie explicite de rafraîchissement/invalidation des blocs affectés par les modifications de
  carte, plutôt qu'une reconstruction globale aveugle ;
- migration en deux temps : valider la représentation et ses oracles, puis seulement brancher les
  consommateurs sur le code courant.

Premier protocole attendu : construire les deux grilles sur 256²/512²/1024²/2048², mesurer
RAM/opcodes/temps, comparer 5×5 et 10×10, puis vérifier le typage sur un échantillon de blocs et la
connectivité eau contre un oracle BFS borné/exact. **Aucun default de jeu ou de politique n'est à
changer avant cette qualification.**

## Validation et clôture d'une tâche

Appliquer [AGENTS.md](../AGENTS.md) : documentation seule → diff et liens ; Squirrel →
tests pertinents et smoke 1×1 ; comportement → diagnostic apparié 5×6 ; adoption →
20×10 complet et sain, avec métrique, effet minimal et garde-fou fixés avant les résultats.
Ajouter la validation Save/Load quand nécessaire. Figer les entrées, conserver les limites
et ne pas confondre absence de significativité et équivalence.

Docker : `--cpus=3 --memory=2g --memory-swap=2g`, volume `openttd-lab-home:/home/lab`,
dépôt réellement monté dans `/work`, trois workers maximum et une seule campagne VPS à la fois.

À la clôture, transférer le compte rendu dans `journal_YYYY-MM-DD.md` avec les preuves,
la décision et les réserves ; retirer l'action terminée de cette liste. Pour un chantier
partiellement livré, ne conserver ici que son reliquat et un lien vers le journal.
