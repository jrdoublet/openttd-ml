# AIR — pistes après les essais du 2–3 octobre 2026

Analyse du checkout `c121-catalog`, HEAD `f6cc6ca`, le 03/10. **Propositions,
pas résultats de variantes.** Aucun code IA, réglage ou bundle modifié, aucune
partie lancée. Les modifications préexistantes du journal du 02/10 et les scripts
d'autopsie non suivis sont conservés.

La priorité proposée est de supprimer le travail refait entre deux décisions,
puis de réutiliser les alternatives économiques déjà calculées. Un modèle plus
physique ne garantit ni un meilleur ordre de construction, ni une meilleure
conversion du capital en revenus. C115 reste le témoin protégé.

## Ce que les preuves permettent réellement de dire

| Source | Lecture retenue | Limite |
|---|---|---|
| Autopsie `c121_autopsy_base_3x6_20261002_r1` | JSON/manifeste relus : 6/6 duels sains, 3/3 paires, couverture complète, `diagnostic_only`. C121−C115 : −579 114 / −329 287 / −918 069 £/an sur 42/100/999, moyenne −608 823. | **Ce bundle ne contient ni V96 ni l'option un/deux avions**, et `c121_catalog_air_first_year=0`. Il ne mesure donc pas le profil actuel. |
| Première pose, trace figée r4 du même bundle | Graine 42 : même première paire, 27/01 contre 16/04. Sur 100/999, C121 construit plus tôt. Snapshot top 8 : huit AIR chez C115 ; sous C121, sur 100/999, deux AIR puis six rails. | `POST_CAND` contient encore le projet construit : c'est le portefeuille photographié après la pose, **pas la preuve d'une resélection après pose achevée**. La trace devient instrumentée après ce premier succès. |
| V96, bilan dans `taches.md` | Diagnostic rapporté : planification AIR 44,7→25,7 M opcodes/partie sur six ans ; 20×10 rapporté : profit final −0,5 k£/an, IC95 [−171 ; +169] k£, valeur +4,1 %. Défaut 1 confirmé dans le code. | Les fichiers bruts indiqués ne sont pas présents à la racine locale de `results/`. Chiffres documentés, non recalculés ici ; aucune nouvelle qualification. |
| Chronologie 1970 instrumentée | Le profil AIR seul + amorçage plat rapporte 324 découvertes de hubs, 13 M opcodes, et 171 reconstructions de catalogue, 21 M opcodes en moyenne. | Ancien profil, avant V96 ; spans imbriquées et attentes de commandes incluses. Ne pas additionner les postes, ni annoncer ces montants comme économies réalisables sur HEAD. |

Le reçu de cette relecture, avec hashes des trois fichiers locaux, réglages
figés et deltas par graine, est dans
[`results/air_pistes_20261003_r1/lecture.json`](../results/air_pistes_20261003_r1/lecture.json)
(artefact local ignoré). Bundle d'autopsie :
`d1ac70560bd7715e2953819495c8935e30d538236f74e7b2175b696a4be2db48`.

Sources de contexte : [autopsie](c121_causal_autopsy_20261002.md),
[chronologie](chronologie_1970_c121_20261002.md),
[pistes du 01/10](c121_air_portfolio_optimizations_20261001.md),
[état courant](taches.md). L'ancien document d'autopsie a des défauts d'encodage ;
les nombres et paramètres ci-dessus viennent des JSON.

## 1. Publier les nouveaux plans sans reconstruire tout le portefeuille

**Priorité haute — simplification de la chaîne catalogue→construction.**

Dans `scheduler_tasks.nut:82`, chaque tranche qui ajoute des plans programme
`partialPending`. Au passage suivant, `_rebuildProjects(s.fleetPlan, partialAir,
false)` reçoit **tous** les plans accumulés. `projects.nut:466` les reconvertit
tous en projets, reconstitue les groupes, aplatit puis sélectionne le portefeuille.
La phase finale refait encore un rebuild. Ce n'est pas une absence de publication
progressive : elle existe, mais son application est complète.

**Intervention :** conserver les projets déjà matérialisés pendant le scan et
convertir seulement les nouveaux plans ou ceux dont les dépendances ont changé.
Première version limitée à l'assemblage AIR : garder les mêmes dates de publication,
le même sélecteur global, le même ordre des alternatives et tous les candidats.
La sélection finale reste entière tant qu'une mise à jour partielle de ses
statistiques n'a pas été prouvée correcte.

Cela vise les visites/allocation répétées du préfixe : avec un ajout par
publication, N plans peuvent provoquer 1+2+…+N conversions au lieu de N.
C'est une propriété du chemin, **pas un facteur de gain mesuré**. Il faut compter
les plans ajoutés, reconvertis et réellement invalidés sur le profil courant.

Différence avec `air_efficiency_reselect` rejeté : on ne supprime ni le réveil
mensuel ni le rafraîchissement des données. On accélère l'application d'une
publication qui aurait lieu de toute façon. Attention aux mises à jour de cash,
K_dec, plancher global, flotte, subventions et à la rotation des cargos : une
copie d'un ancien `best` ne serait pas équivalente.

**Porte de sortie :** mêmes groupes, mêmes valeurs et mêmes rangs sur des
publications rejouées à entrées identiques, moins d'opcodes d'assemblage nets,
puis mesure du délai plan admissible→mise en service.

## 2. Conserver la découverte des hubs avec ses curseurs

**Priorité haute — piste déjà identifiée le 01/10, toujours non traitée dans HEAD.**

`air_planning.nut:2157` appelle `OpexAirPlansDiscoverHubs` à chaque reprise,
avant les gardes `hubPhase`. Le code conserve `hubSiteI/J` et `hubHubI/J`, mais
recrée `ctx.hubs`. La découverte peut rechercher des sites supplémentaires,
reparcourir les lignes, rechercher les villes et lister les aéroports orphelins.
Le cache de site ne rend pas ce passage gratuit ; le chemin C83 ciblé contourne
même le cache ville/type pour préserver la bonne ville de créneau.

**Intervention :** snapshot ordonné des hubs et des sites supplémentaires dans
le curseur du scan, avec sa révision. Séparer géométrie/topologie et données
dynamiques de service. Revalider les extrémités effectivement utilisées ;
reconstruire ou redémarrer proprement les curseurs si la topologie change.
Ne jamais appliquer un index ancien à un nouveau tableau réordonné.

L'index de routes existe déjà (`c80_air_hub_index`). Cette proposition ne consiste
ni à le réinventer, ni à activer `c83_local_repair`, ni à supprimer la réaction C83.
La réparation locale n'économisait que 0,203 % du total AIR de son témoin,
selon son [bilan](c83_local_repair_20261002.md) : elle n'a pas résolu ce coût de reprise.

**Porte de sortie :** comptage découverte/reprise et coût de chaque sous-phase ;
fixtures avec construction/destruction, arrivée concurrente, orphelin, changement
de mois et Save/Load. Les gardes de fraîcheur font partie du coût candidat.

## 3. Terminer le raccourci V96 et fusionner précisément N=1/N=2

**Priorité haute pour un premier prototype court — deux interventions séparées.**

**3a. Borne calculée puis jetée.**
`OpexC121GameEngineTryShortcut` (`air_economics_c121.nut:1384`) calcule
`OpexC121InitialEngineUpperScore`. Au retour, le chemin `geMode=1` ne conserve
que l'avion et le contexte. La valeur de la borne n'est jamais comparée ;
l'économie exacte du gagnant est calculée ensuite.

Remplacer cette borne par les seules gardes nécessaires, ou réutiliser le
résultat exact pour décider du repli. Ne pas enlever aveuglément l'appel : sa
valeur `null` teste aussi capacités, tarifs, coûts et durée. Préserver les mêmes
conditions de repli, y compris les changements de mois et le MAIL inconnu.
Le gain viserait le travail répété **après V96**, pas les scans déjà supprimés.

**3b. Fusion devenue inopérante avec le nouveau profil.**
`OpexC121WinnerEconomics` retourne immédiatement `OpexC121OneOrTwoWinner`
quand l'option un/deux avions est active. Celle-ci appelle deux fois l'économie
complète, N=1 puis N=2 (`air_economics_c121.nut:1092`). La fusion adoptée de
l'ouverture et de la croisière ne s'applique donc pas à ce chemin.

Créer une évaluation spécialisée des **deux N**, préparant une seule fois les
invariants, conservant les deux résultats et construisant uniquement les objets
utiles. Ce n'est pas le contexte générique de tous les avions essayé le 02/10
(+9,88 % d'opcodes) : la portée est un seul avion, deux N, sans nouvelle table
de validation du contexte à chaque appel. L'effet des allocations doit néanmoins
être mesuré, pas supposé favorable.

**Porte de sortie :** fixture NoAI appariée, égalité des sorties/erreurs/départages,
PASS seul puis MAIL connu, inflation et frontière de mois, gain net sur le
chemin V96 actif. Pas de pourcentage promis avant cette mesure.

## 4. Ne plus jeter l'option d'ouverture N=1 déjà calculée

**Priorité haute côté comportement — construire une bonne ligne accessible.**

`OpexC121OneOrTwoWinner` calcule les deux économies, choisit celle de meilleur
score, puis ne retourne que `chosen`. Si N=2 gagne mais dépasse le budget, N=1
n'est plus disponible. `OpexProjectFitFleetToBudget` (`projects_selection.nut:922`)
ne redimensionne que `mode="fleet"` ; une création AIR passe sans ajustement.
`OpexC116ChooseBuildPlan` retourne également inchangé sous C121. Le constructeur
peut subir un achat partiel après échec de clone, ce qui n'est pas une sélection
préalable de l'alternative finançable.

**Intervention :** conserver N=1/N=2 dans un petit objet d'alternatives du même
projet physique. Au financement, publier **une seule** alternative : N=2 si elle
est retenue et finançable, sinon N=1 si elle est rentable et admissible. Employer
le vrai profit N=1, son capital et ses marges ; aucun classement N=2 suivi d'un
achat N=1 caché. Ne pas occuper deux places du top64 ni supprimer les autres
variantes O/D : la déduplication top64 précédente a échoué.

Le calcul économique des deux variantes est déjà payé. Le coût nouveau est
celui de leur conservation et du choix au budget, à mesurer. L'exposition
actuelle est inconnue ; l'ancien diagnostic ne retenait N=2 que 4 fois sur
45 poses. **Compter d'abord les projets perdus parce que C1≤budget<C2**,
leurs jours d'attente et les marchés devenus indisponibles. Zéro exposition
significative implique arrêt, pas un nouveau banc long.

Cette piste est distincte des profondeurs statiques rejetées : elle ne change
pas leur score ni leur cible à long terme ; elle empêche la disparition d'une
ouverture déjà évaluée et réellement finançable.

## 5. Invalider les données concernées, pas toute la géométrie

**Priorité moyenne — structure confirmée, fréquence/coût restant à mesurer.**

`air_catalog_c121.nut:185` invalide globalement la géométrie des extrémités sur
un miss `input` ou `age`. Or `input` mélange distance, demande et prix/entretien
d'aéroport. `air_coverage.nut:6` incrémente un epoch global et vide la couverture
des gares ; cet epoch fait ensuite périmer tous les snapshots d'extrémités.
Chaque plan âgé peut aussi déclencher cette invalidation à son tour.

**Intervention :** distinguer la géométrie, la production/concurrence locale,
les capacités du matériel et les tarifs. Une variation de prix peut imposer de
recalculer l'économie sans rechercher les arrêts ni la couverture. Réviser
ensemble les dépendances parent/enfant ; conserver un filet temporel pour les
mutations du monde sans événement fiable. Un simple retrait de l'invalidation
réintroduirait les défauts corrigés par le lot cache du 01/10.

**Porte de sortie :** distribution des motifs de miss, reconstructions évitables
par gare, coût net et fixtures de fraîcheur. Si le mécanisme est peu exposé sur
le profil courant, le garder derrière les pistes 1–4.

## 6. Choisir l'avion pour le service qui sera réellement ouvert

**Piste exploratoire pour de meilleures lignes/avions à budget constant.**

Le scan moteur normal et les contrôles V96 comparent les avions sur N=1
(`air_economics_c121.nut:1616`, hors option AAA à deux avions). Le choix entre
N=1 et N=2 intervient **après**, pour le seul moteur retenu. Un avion excellent
à N=1 n'est pas nécessairement le meilleur pour deux départs opposés. C'est une
incohérence de domaines de choix confirmée, pas encore une perte économique mesurée.

**Intervention candidate :** lors des scans de contrôle déjà prévus, garder
aussi un challenger, puis comparer un petit ensemble `(avion, N=1/N=2)` avec
le noyau fusionné. Commencer par des replays hors décisions. Évaluer la perte
de score maximale et les changements sur les projets réellement élus, et pas
seulement le pourcentage de moteurs identiques.

Le budget de cette recherche doit être financé par un gain mesuré de la piste 3,
et le **total planification**, cache/contrôle compris, doit rester au plus au
niveau du témoin V96. Deux moteurs évalués partout sans compensation seraient
une augmentation de coût. Ne pas imposer une table distance×demande : elle avait
déjà une mauvaise couverture du vrai meilleur plan. La proposition ne rouvre
pas les changements de régime capital/limite de véhicules différés par l'utilisateur.

## Réserves et choix de la première étape

La marge fixe +30 k£ pour deux aéroports, +12 k£ pour un et +2 k£ pour aucun
(`projects_builders.nut:302`) reste une piste secondaire d'accélération. Elle
s'ajoute à l'immobilisation du modèle et à la réserve de trésorerie : ces termes
ne sont **pas démontrés redondants**. Avant de la réduire, rapprocher prévision,
dépense réelle, échecs partiels et délai de première recette, en incluant les
échecs et pas seulement les chantiers réussis. Aucun nouveau devis coûteux par
paire, aucune suppression générale de sécurité financière proposée ici.

Ne pas relancer sous un autre nom les essais déjà conclus : contexte générique,
préflight global, déduplication top64, simple réveil sur seuil de cash, sommeil
global `air_fleet`, facteur unique de réalisation ou nouvelle profondeur de
flotte statique. Le fait que C115 soit imparfait ne qualifie pas leur remplacement.

**Ordre recommandé :** un lot court 3a, puis 3b ; préparer aussi le comptage des
reconstructions 1/2 et de l'exposition 4. Les pistes 1/2 ont le plus gros potentiel structurel ;
la piste 3 est la plus bornée à départager ; la piste 4 exploite un calcul
déjà payé. La piste 6 ne vient qu'après mesure de son budget disponible.

Pour chaque intervention retenue : témoin au profil C121 **courant**, une seule
différence et un bundle figé ; fixtures/opcodes à entrées appariées, smoke 1×1,
puis diagnostic 5×6 selon les conditions de `taches.md`. Rapporter séparément
profit Opex, revenu, gap AAA, slots/villes, nombre d'avions, dates de pose et
opcodes. Ne pas comparer les opcodes annuels de trajectoires différentes comme
une preuve de coût unitaire. Le passage éventuel au 20×10 respecte les portes
et interdictions du chantier ; cette analyse n'en lance ni n'en autorise un.

Une approximation sans perte établie reste incertaine : absence de significativité
n'est pas preuve d'égalité. Conserver le verdict brut et appliquer séparément
la règle de neutralité du dépôt, sans changer la métrique après lecture des résultats.
