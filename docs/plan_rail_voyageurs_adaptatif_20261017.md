# Rail voyageurs adaptable — V207/V212, époques et configurations

**17 octobre 2026 — analyse et plan révisé, sans implémentation ni banc.**
L'utilisateur demande une solution plus intelligente, flexible et adaptable,
incluant un départ en **1950**, les réglages non standard, les **NewGRF et
CargoDist** (périmètre confirmé). Ce plan remplace la proposition RPX de garde
« rail seul strict ». [Suivi autoritaire](taches.md).

## 1. Orientation proposée

Faire de V207 un ensemble d'options évaluées **pour chaque projet** : voyageurs
seuls, ajout de courrier, extension de couverture par arrêts joints. Leur
intérêt dépend du matériel, du site, de la desserte et du réseau existant.
Remplacer progressivement les coefficients globaux V212 par une prévision
physique et une correction des erreurs mesurables, assorties d'incertitude.

Le nombre de modes autorisés ne décide plus de l'activation. En rail seul,
les voyageurs peuvent compléter le fret ; en multimodal, ils peuvent desservir
une autre zone, soulager une liaison saturée ou au contraire déplacer des
revenus déjà gagnés. Aucun bonus lié à l'année 1950 ou au mode « rail seul ».
Les modes désactivés restent des contraintes de faisabilité.

**Contrat économique à viser :**

```text
profit_ligne = revenus voyageurs + courrier - exploitation - amortissement
gain_compagnie = profit_ligne
                 + variation du profit des dessertes existantes affectées
```

Le deuxième terme peut être positif ou négatif. Ne pas soustraire des coûts
fixes d'un avion comme s'ils disparaissaient dès qu'il perd des passagers.
Capital à engager et trésorerie restent des contraintes séparées ; on ne
soustrait pas directement un investissement au profit annuel. Comparer les
alternatives au même horizon et avec les contrats d'admission/score du dépôt.

**Deux grandeurs séparées :** la demande de la ligne dimensionne les trains ;
le gain supplémentaire de la compagnie éclaire le choix du projet. Réduire
la demande physique à la seule clientèle nouvelle sous-dimensionnerait une
ligne qui transporte aussi des voyageurs déplacés depuis une autre desserte.
Cette séparation était une intention du plan V216 ; elle doit être vérifiée
dans le calcul et l'admission, pas présumée acquise.

## 2. Ce que l'analyse actuelle établit

Base : `master@fc884e167625223113f98023b73370e81e237b19` ; code IA propre,
travaux documentaires locaux préservés. V207 est désarmé, V212 vaut 100/100.
V172=200, V214=300/1500, V216a=1, V216f=100 et V217=1 sont les défauts
observés, pas tous des adoptions issues d'un parcours V102 complet.

| Constat dans le code ou les bilans | Conséquence |
|---|---|
| `settings.nut:165`, `economy.nut:490` : part V207 et recalage V212 globaux | Les valeurs 40/150/85 historiques ne constituent pas un modèle universel. |
| `probe_v216.nut:435` : note future fixée à 35 % ; `:428` : concurrence adverse multipliée par 0,5 ; `:454` : moyenne des deux extrémités | Ces proxys ne décrivent ni tous les matériels, ni les capacités, ni les destinations CargoDist. |
| `probe_v216.nut:31` : séjour mécanique à 5 unités par tranche ; `catalog.nut:18` : longueur nominale des wagons | Hypothèses standard à isoler ; ne pas les appliquer silencieusement à tout NewGRF. |
| `catalog.nut:460` : rail disponible de plus grand identifiant ; `:479` : wagon par cargo par défaut, plus capacitaire | Auditer la compatibilité des voies, les matériels articulés/refittables et les automotrices. Un identifiant n'est pas une mesure économique. |
| Catalogue : prix, coûts, puissance, traction et disponibilité déjà lus ; builder : longueur réelle vérifiée | Réutiliser ces mécanismes et C41 ; aucune reconstruction simpliste à vitesse maximale. |
| `projects_models.nut` : C70/C82/C121 ; `capital_quote_learning.nut` : infrastructure de calibration des devis | Éviter une seconde calibration de la même erreur ; inventorier ce qui est effectivement actif. |
| Bilan EST/V216 : gain net non mesuré directement, test d'invariance historique en échec, rang changé ≠ achat changé | La nouvelle piste doit établir ses observables et ses décisions exécutées avant les portes économiques. |
| `bench_1v1_5y_20seeds.py:87` : `STARTING_YEAR=1970` ; lanceur sans option dédiée d'année/configuration/NewGRF | Le harnais doit évoluer avant une validation honnête à 1950 et hors configuration standard. |

Les pertes historiques de V207/V212 en multimodal restent acquises dans
leur contexte ; V216a + paquet fixe a déjà échoué. Il ne s'agit pas de rejouer
ce paquet ni d'en changer simplement les coefficients. L'analyse s'appuie
sur le bilan EST/V216 local (`docs/est_v216_bilan_20261016.md`, non publié
dans ce lot), le [plan V216 historique](plan_v216_scores_avant_premier_rail_20261016.md)
et les [diagnostics sondés versionnés](v216_sondes_20261016.md).

## 3. Données accessibles et limites confirmées

Vérification sur les sources officielles **OpenTTD 15.3**, et non sur la seule
documentation générée de master. Ces lectures établissent le contrat API ;
elles ne remplacent pas une vérification dans le runtime du banc.

| Besoin | Accès utilisable | Limite à porter dans le modèle |
|---|---|---|
| Matériel disponible, coût, puissance, refit, compatibilité voie | `AIEngine`, listes de matériels et types de voie | Capacité principale/par défaut ≠ capacité de toute composition après refit ; compatibilité déclarée ≠ succès garanti de tous les assemblages. |
| Capacité après refit, longueur physique | `AIVehicle.GetBuildWithRefitCapacity` avec dépôt existant ; `GetCapacity`/`GetLength` sur véhicules existants | Pas de dépôt virtuel gratuit ni de longueur exacte générale avant construction. Les contrôles du builder restent nécessaires. |
| Tarifs et mode de distribution | `AICargo.GetCargoIncome`, `GetDistributionType`, classes de cargos | Tarif unitaire disponible ; volumes futurs et revenu net réseau restent à prévoir. Résoudre les cargos par propriétés, pas IDs fixes. |
| Couverture et production locale | Emprises réelles, rayons de gare, acceptation, totaux de production des villes/industries | `AITile.GetCargoProduction` donne un nombre de producteurs, **pas des voyageurs mensuels**. Une conversion en volume est une estimation à valider. |
| CargoDist sur le réseau existant | `AIStation.GetCargoPlanned*`, `GetCargoWaiting*`, notamment origine et prochain arrêt | Flux planifiés ≠ livraisons réalisées ; API sur nos gares valides ; aucune demande contrefactuelle exacte pour une gare non construite. |
| Réglages et NewGRF | `AIGameSettings.IsValid/GetValue`, `AINewGRFList`, nom/version | Informations partielles : version GRF parfois absente ; paramètres complets et hashes à figer côté harnais. Un réglage illisible reste inconnu. |

Sources proches des contrats :
[moteurs](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_engine.hpp),
[véhicules](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_vehicle.hpp),
[cargos](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_cargo.hpp),
[tuiles](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_tile.hpp),
[flux des gares](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_station.hpp),
[réglages](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_gamesettings.hpp),
[NewGRF](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_newgrf.hpp).

Le débit de chargement de tout matériel NewGRF et certains callbacks ne
sont pas intégralement exposés par `AIEngine`. Les observations peuvent
réduire cette incertitude après mise en service. Les données détaillées des
sauvegardes servent au diagnostic hors ligne ; elles ne doivent pas devenir
des entrées fictivement disponibles à l'IA pendant le jeu.

## 4. Architecture adaptable, à construire progressivement

### 4.1 Décrire la partie et les possibilités réelles

Un contexte contient cargos, distribution par cargo, options accessibles,
matériels constructibles, railtypes compatibles, prix courants et provenance
des données. Distinguer temps économique et temps calendaire : les coûts
annuels et les âges n'utilisent pas nécessairement la même horloge.

1950 doit fonctionner par les matériels alors disponibles, sans table
« avant/après 1970 ». Réexaminer les candidats lorsque matériel, prix,
géométrie ou desserte changent. Réutiliser le rafraîchissement du catalogue
et les événements existants ; cacher les résultats par contexte et invalider
les entrées concernées. Aucune énumération mondiale à chaque sélection.

### 4.2 Évaluer des plans physiques réalisables

Réutiliser le modèle C41 et les devis. Pour une composition déterminée,
conserver séparément trajet, séjour mécanique, attente de production,
capacité, fréquence, note, revenus et coûts. Recalculer ensemble les termes
couplés ; ne pas ajouter une seconde fois `loadDays` ni multiplier le profit
par un facteur de volume. Traiter le courrier comme un cargo à capacité,
tarif, chargement et place dans la rame propres.

Les plans détaillés doivent porter sur une liste bornée de candidats ; on
ne lance pas un A* ni une recherche complète d'arrêts pour chaque paire de
villes. Affiner après le choix du site et du tracé, puis revérifier admission
et financement. Les quotas de calcul sont à mesurer avant de les fixer.

### 4.3 Estimer la demande de ligne et l'effet sur notre réseau

Partir de la zone effectivement couverte par les gares prévues et les
extensions possibles, en dédupliquant les producteurs. Estimer les deux
directions séparément. Tenir compte des autres gares, de leur offre et des
capacités ; un aéroport présent ne signifie pas que toute la demande est
déjà satisfaite. La concurrence adverse est partiellement observée et
devient une incertitude, pas un partage 50/50 présenté comme une mesure.

Calculer séparément la fréquentation de la nouvelle ligne et les variations
des dessertes propres affectées. Ne pas pénaliser deux fois le même
chevauchement via V216a puis un nouveau facteur. Vérifier aussi le contrat
des alternatives AIR/fret/renfort dans le classement : comparer un gain
marginal rail à un revenu brut AIR introduirait un nouveau biais.

### 4.4 Prévoir un traitement CargoDist explicite

La distribution est propre au cargo : voyageurs et courrier peuvent suivre
des règles différentes. Pour les gares existantes, exploiter flux planifiés,
origine/prochain arrêt, stocks et capacité ; pour une nouvelle liaison,
construire une prévision bornée de connectivité et de demande, avec délai de
mise en place du graphe. Un flux absent avant ouverture n'est pas la preuve
qu'une liaison restera vide.

Éviter les doubles comptes sur un trajet avec correspondance : le revenu
de transfert attribué à un véhicule n'est pas un revenu supplémentaire
encaissé par la compagnie. Un éventuel effet de correspondance reste une
hypothèse à mesurer ; **ce lot ne réintroduit pas les feeders ni une nouvelle
politique de correspondances**.

### 4.5 Choisir les options V207 par leur apport supplémentaire

Pour un projet prometteur, comparer un petit ensemble réalisable :
voyageurs seuls, voyageurs+courrier, puis extensions de gare légales.
Chaque option doit justifier son coût et la capacité qu'elle consomme.
Les arrêts joints sont évalués par couverture additionnelle et faisabilité,
sans imposer toujours deux arrêts ni un captage de 40 %. Une extension vide,
redondante ou refusée ne doit pas laisser le projet crédité de son gain prévu.

Les options s'inscrivent dans un même dossier de projet, afin d'éviter
plusieurs achats concurrents du même axe. La borne de longueur du train,
le devis réel et le nettoyage après échec partiel restent obligatoires.

### 4.6 Apprendre les erreurs identifiables, avec un démarrage autonome

Démarrer avec le calcul physique et ses limites ; il faut pouvoir choisir
un premier projet sans attendre une ligne mature. Apprendre ensuite des
écarts effectivement observables : durée de rotation, séjour, capacité
après refit, coût du chantier, réalisation du revenu de ligne. La variation
causale du profit réseau ne se déduit pas automatiquement de ces observations.

Regrouper seulement des observations comparables (matériel/composition,
cargo, distribution, service, âge et contexte), réduire le poids des données
anciennes après changement de contexte et rapprocher les corrections peu
documentées du modèle initial. Ne pas appliquer simultanément V212,
V216a, C70 et une nouvelle correction de la même erreur. Le rôle exact des
calibrations existantes doit être explicite pour chaque champ.

Pas de table de bonus par année, pas d'apprentissage global « rail × k »
confondu avec la concurrence locale. Les projets normaux fournissent les
premières observations ; aucune construction déficitaire d'exploration
n'est décidée par ce plan. Les réglages d'incertitude et de lissage seront
pré-enregistrés, pas ajustés jusqu'à obtenir un bon banc.

### 4.7 Dégrader proprement la précision

Chaque estimation porte valeur, unité, source et statut : connu, mesuré,
estimé ou non couvert. Une donnée absente n'est ni zéro ni un réglage vanilla.
Sans modèle suffisamment couvert, conserver une décision de référence
compatible quand elle existe ; sinon reporter le projet et exposer la cause.
Un silence ou une IA inactive ne constitue pas une compatibilité réussie.

L'objectif est un comportement utile sur des configurations variées. Une
garantie de performance pour toute combinaison arbitraire de NewGRF serait
invérifiable ; il faut publier les profils couverts et les limites restantes.

## 5. Petites tâches proposées

Échelle de complexité 1–5. Les tâches à 4/5 demandent une conception/mesure
soignée, pas une réécriture globale. **Les trois premières sont en lecture
seule** ; chaque tâche produit un livrable vérifiable avant la suivante.

| ID | Livrable borné | Complexité | Dépendance / porte |
|---|---|---:|---|
| RVA-01 | Matrice des capacités : 1950/époques ultérieures, options, NewGRF, CargoDist ; données disponibles/manquantes et hypothèses standard du code. | 2/5 | Approfondir l'inventaire présent, sans code ni partie. |
| RVA-02 | Contrat des grandeurs : demande de ligne, revenu, gain compagnie, capital, horloges, incertitude ; carte C70/C121/V216/V212 pour éviter les doubles corrections. | 3/5 | 01 ; formules cohérentes en unités et dépendances. |
| RVA-03 | Audit des traces existantes et de leur lecteur : sites, composition, flux, décisions réellement exécutées ; liste précise des observations manquantes. | 3/5 | 02 ; pas de nouvelle grande campagne pour redécouvrir V216. |
| RVA-04 | Année configurable dans lanceur, moteur du duel, gel, contrôles d'horizon et lecteurs. | 3/5 | 01 ; fixtures 1950/1970 et un changement d'époque, défaut de banc 1970 conservé. |
| RVA-05 | Configuration et NewGRF reproductibles : fichiers, ordre, paramètres, hashes, versions et montage identiques dans les deux bras. | 4/5 | 04 ; refus des ressources absentes, pas de remplacement silencieux ; smoke de chargement seulement. |
| RVA-06 | Descripteur matériel/cargo/voie utilisable par un candidat ; exposer refit, capacité incertaine et contraintes d'assemblage. | 3/5 | 01–03 ; identifier les gaps du catalogue, traiter un gap à la fois. |
| RVA-07 | Calcul à blanc d'un cycle complet pour une composition : trajet/séjour/offre/note/débit, puis courrier mixte. | 4/5 | 02/06 ; comparer aux observations, aucune modification de score. |
| RVA-08 | Demande par extrémité sur emprise réelle ; distinguer compte de producteurs et volume, voyageurs et courrier. | 4/5 | 03/07 ; cas sans recouvrement, partiel, saturé et volume inconnu. |
| RVA-09 | Estimation séparée du gain compagnie et des effets sur nos lignes ; audit de comparabilité avec les alternatives du portefeuille. | 4/5 | 02/08 ; le revenu de ligne ne sert pas de preuve de gain net. |
| RVA-10 | Branche de calcul CargoDist : réseau existant, nouveau lien, graphe en formation, origine/via et traitement des transferts. | 4/5 | 05/08/09 ; couverture établie pour distributions manuelle, symétrique et asymétrique. |
| RVA-11 | Alternatives V207 dans un dossier unique : courrier optionnel, arrêts utiles, réévaluation après échec partiel. | 3/5 | 06–10 ; coûts et capacité supplémentaires explicites, pas de paquet fixe. |
| RVA-12 | Évaluateur passif OFF par défaut et mesures bornées des champs manquants ; rattachement candidat→tentative→construction. | 3/5 | 03/11 ; contrôle de la sonde sur quelques lignes et mesure de son coût en opcodes. |
| RVA-13 | Correction des seules erreurs observables sur séquences temporelles séparées ; test du démarrage sans données et des changements de matériel. | 4/5 | 12 ; aucune fuite de données futures ni seconde correction C70/V212. |
| RVA-14 | Rejeu complet de l'admission, de la finançabilité et du choix sur les clichés exploitables. | 3/5 | 09–13 ; distinguer rang, achat simulé et achat réellement modifié. |
| RVA-15 | Persistance minimale et invalidation : apprentissage utile, version du modèle, reprise après chargement. | 3/5 | 13/14 ; contrats et `save_load_roundtrip.py`, caches reconstructibles. |
| RVA-16 | Activation expérimentale d'une intervention isolée, défaut OFF ; contrats, smoke causal et preuve d'achats modifiés. | 3/5 | 14/15 ; ne pas activer d'un coup tous les modules non qualifiés. |
| RVA-17 | Qualification économique puis robustesse par profils pré-enregistrés, avec résultats séparés. | 3/5 | 16 ; arrêt au premier échec de la séquence concernée. |
| RVA-18 | Décision d'adoption et éventuel retrait des coefficients devenus inutiles, après validation du défaut livré. | 2/5 | 17 ; suppression/commit/publication restent des décisions distinctes. |

**Premier jalon : RVA-01 à RVA-03.** Il doit dire si les entrées nécessaires
permettent un modèle défendable et quel premier changement tester. Ne pas
transformer ce plan en chantier monolithique ; les dépendances non couvertes
restent nommées, sans prétendre avoir déjà trouvé la formule gagnante.

## 6. Validation sur les époques et options

Une validation en 1970 sans NewGRF ne couvre pas 1950 ou CargoDist. Construire
la matrice ci-dessous avant les essais ; sélectionner des jeux NewGRF précis
et disponibles avec leurs paramètres, sans installation implicite.

| Axe | Cas à couvrir progressivement |
|---|---|
| Époque | Départs 1950, 1970, 2000 et 2050 ; plus une partie traversant un changement de matériel réellement observé dans le jeu de véhicules retenu. |
| Modes et concurrence | Rail seul, multimodal complet, combinaison partielle ; AAA identique entre les deux bras et lui-même capable de jouer dans la configuration. |
| Physique/coûts | Accélération et pente, chargement progressif, longueur de quai/rames, couverture et jonction des gares, coûts et inflation, pannes et horloges. |
| NewGRF | Matériel refittable/articulé, capacité/longueur inhabituelles, nouveaux railtypes ; cargos/industries/maisons modifiant production ou acceptation. |
| Distribution | Manuelle, symétrique, asymétrique ; voyageurs et courrier réglés différemment ; réseau neuf puis réseau avec flux établis. |

Cette matrice n'impose pas le produit cartésien de tous les cas. Faire d'abord
des contrats et scénarios techniques ciblés, puis un plan de couverture des
interactions à risque. Distinguer **exécution compatible**, **prévision
contrôlée** et **gain économique qualifié**. Un NewGRF sans matériel utilisable
à 1950 doit être identifié comme tel, sans attribuer ce cas au modèle de score.

Pour chaque intervention comportementale et contexte revendiqué : contrats,
smoke sain, exposition, puis protocole V102 A 40×3 (`gain_short`, 4 %, garde
5 %) et B 20×10 (`non_erosion`) après A passée. Le modèle agit désormais
aussi en multimodal : le seul contrôle d'inertie du plan RPX ne suffit plus.
Le périmètre d'adoption dépend des portes réellement franchies ; aucune
moyenne regroupant des contextes ne doit masquer un échec en multimodal
ou en 1950. La robustesse sur des configurations nouvelles reste à mesurer.

Figer les profils et les séquences temporelles d'apprentissage/validation
avant résultats ; aucune recherche du meilleur départ ou du meilleur NewGRF
après coup. Quarante graines d'un profil ne sont pas quarante preuves de
compatibilité avec d'autres profils. Pré-enregistrer les campagnes nécessaires
et leur budget au jalon RVA-17, sans lancer d'avance toute la matrice.

Réutiliser `run_c66_reference.py`, `campaign_freeze.py`, `game_health.py`,
les compteurs qualifiés et les conditions de santé/couverture d'AGENTS.md.
Vérifier ressources et campagnes actives : PC 10 CPU/8 Go/10 workers,
VPS 3 CPU/2 Go/3 workers ; cache partagé, swap plafonné à la RAM.

## 7. Bornes du chantier

V215 et la garde automatique RPX restent hors file active. V207/V212 fixes,
site 50, revenu 250, ancienne pile B, P2/P4 H1/H2/H3, bonus froid par époque
et report d'achats AIR ne sont pas réactivés. Le nouvel apprentissage vise
d'abord des composantes physiques observables du rail ; il ne relance pas
la calibration AIR ou les cohortes C70 rejetées. Voir le
[bilan des pistes suspendues](p2_p4_bilan_final_et_suspension_20261014.md).

Le catalogue et le harnais ont des dépendances plus larges que V207/V212 :
les corrections de compatibilité nécessaires seront des changements séparés,
avec leurs témoins. Aucun résultat de score ne qualifiera implicitement une
refonte des voies, du fret, du financement ou du renouvellement de flotte.

**Statut :** architecture proposée, API et points de code inspectés ; aucun
gain nouveau mesuré. Documents et liens locaux vérifiés, `git diff --check`.
À la clôture de l'analyse : aucun code IA/harnais modifié, aucun banc ni
commit/push. Prochaine tâche :
**RVA-01**, inventaire concret des capacités et limites, en lecture seule.

**Publication demandée le 17/10 :** le plan et son entrée dans `docs/taches.md`
sont préparés sur `origin/master@17de2074`, dans un worktree isolé. Les
changements documentaires EST et les deux commits V217 propres au checkout
local ne font pas partie de ce lot. Les constats ci-dessus conservent leur
base d'analyse explicite ; RVA-01 devra relire l'état courant avant exécution.
