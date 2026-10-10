# Cible : classement unique des investissements — décision du 09/10/2026

## Règle de produit

**Tous les projets qui engagent du capital passent par le même système de classement et d'admission au financement, quel que soit leur mode ou leur nature.** Une tâche spécialisée peut *détecter* une opportunité ou *exécuter* un chantier déjà admis, mais ne peut pas engager une nouvelle dépense de croissance sur la seule base de sa cadence, de son mode ou de son ordre dans le scheduler.

Périmètre explicite : lignes nouvelles **AIR, rail, route, eau** ; renforts d'avions ; véhicules routiers supplémentaires ; wagons supplémentaires ; second train ; doublement de voie ; extension/croissance locale ; autres créations, extensions et remplacements capitalisés. Les opérations de sécurité et de remplacement indispensable demandent une classe de nécessité **visible dans le même arbitre**, avec coût et réservation de capital, plutôt qu'une dépense silencieuse hors portefeuille. Ne pas confondre cette classe documentée avec une préférence arbitraire pour un mode.

## Contrat d'un projet

- Identité persistante et idempotente (`kind`, `mode`, ligne/OD, version de l'état observé), stade `proposé / admissible / réservé / préparé / engagé / terminé / échoué / annulé`.
- **Capital de financement complet** (matériel, infrastructure, préparation, marges explicites) et contrainte de réserve ; même définition de capital disponible pour tous.
- **Gain économique *marginal net*** attendu par rapport au réseau existant, incluant charges et amortissement, avec signal de confiance et ancienneté du devis. Ne pas comparer la recette totale d'une ligne au gain d'un appareil supplémentaire.
- **Faisabilité** connue ou incertitude explicite (construction physique, contraintes d'emplacement, A*, commande de matériel), et délai/coût de préparation ; un projet non construit ne devient pas "constructible" sur la seule foi de son score.
- **Score, règles de priorité et départage communs** : toute politique de territoire, urgence ou fenêtre périssable doit être explicite, observable et appliquée dans le *même* comparateur intermodal ; aucune promotion ou achat modal caché après classement.
- Revalidation au moment d'engager le coût, budget et identités actualisés, réservation des travaux déjà engagés, comptabilisation des résultats et des refus dans une trace comparable entre tous les types.

Le tri seul ne suffit pas : le scheduler doit **respecter la décision du portefeuille**. Une recherche A* peut être préparée en avance sans dépenser du capital, mais sa construction finale doit rester soumise à une admission intermodale fraîche ; les recherches en cours ne doivent pas consommer silencieusement le prochain budget. Les projets multi-étapes sont des transactions identifiables avec engagements et reprises Save/Load, pas des achats indépendants invisibles.

## État vérifié du 09/10 : couverture partielle

| Investissement | Situation observée | Référence principale |
|---|---|---|
| Ligne nouvelle AIR / rail / route / eau | `OpexBuildProjects` constitue un vivier commun puis appelle `OpexProjectSelectAffordable` | `projects.nut:491–574` |
| Renfort d'avions | Sous `FLEET_PORTFOLIO`, injecté puis reclassé avec les autres projets | `projects.nut:526–535`, `projects_update.nut:5–41`, `scheduler_tasks.nut:917–946` |
| Wagon supplémentaire | Classement local au seul gain marginal puis transaction rail hors portefeuille | `task_rail.nut:728–806,925–969` |
| Second train / double voie | Boucle locale par lignes, achat ou recherche d'upgrade indépendants | `task_rail.nut:816–925`, `task_rail.nut:1921–1975` |
| Bus supplémentaires sur ligne existante | `ROAD_REFLEET` décide directement selon attente/capacité | `task_road.nut:310–457`, `scheduler_tasks.nut:997–1003` |
| Navire après crash | Refleet dédié hors classement commun | `task_water.nut:90–110` |
| Croissance urbaine / desserte locale | Tâche `town_growth` dédiée, chemin de construction propre | `scheduler_tasks.nut:1005–1069`, `task_town.nut:100–303` |

Même **au sein** du vivier commun, l'ordre courant n'est pas strictement économique : classes défensives AIR et chaînes forcées (`projects_selection.nut:1553–1659`), bonus territoriaux / de slot, promotions live (`projects_selection.nut:1667–1745`), reports / réservations à l'exécution (`task_projects.nut:1676–1866`). Ces mécanismes sont des règles à réconcilier avec le comparateur unifié, pas à désactiver sans preuve économique. Une préparation ou consommation A* rail peut également précéder la boucle du portefeuille (`task_projects.nut:1707–1719`).

## Livraison incrémentale attendue (sans changement de défaut avant banc)

1. **Inventaire exhaustif des débits capitalisés** et preuve d'une voie d'admission pour chacun ; distinguer dépenses de croissance, remplacement et entretien, sans exemption implicite.
2. **Normaliser les devis marginaux**, coûts, caducités, préconditions et identités pour rail-upgrade / wagons / bus / navires et nouvelles lignes ; compléter les marges froides AIR sans imposer de plafond arbitraire.
3. **Publier les projets locaux** dans `candidateGroups` ou registre unifié équivalent : génération/injection sans construction directe ; classement par le même sélecteur ; exécuteurs spécialisés déclenchés sur admission seulement.
4. **Unifier les promotions et la temporalité** : un seul comparateur, les contraintes de nécessité codifiées, sélection/revalidation avant toute dépense ; engagements A*, constructions multi-étapes, Save/Load, cache et réélection traités explicitement.
5. **Vérifier en A/B** l'absence de contournement puis la rentabilité finale contre AAAHogEx sur graines et horizons partagés, avec seuils de porte pré-enregistrés. Aucun passage au défaut sur une simple correction de couverture ou un smoke.

### Critères d'acceptation

- Pour chaque achat ou chantier capitalisé, la télémétrie lie **une identité projet, son rang dans le portefeuille, le score et capital pré-achat, sa réservation éventuelle, puis son débit réel**. Le taux de dépenses sans décision correspondante est **zéro**.
- Les mêmes deux projets affichés au même instant sont comparés par **la même fonction et la même politique d'arbitrage**, sans priorité liée au seul nom de la tâche ; un candidat perdant ne dépense pas avant le gagnant sans motif observé (impossibilité, caducité, obligation explicite).
- Un renfort aérien, wagon, second train ou bus nouvellement admissible peut **perdre** face à une nouvelle ligne rail, route, AIR ou eau, et réciproquement, selon les devis et contraintes vivants.
- Le chemin inactif de migration reste inchangé, les opérations engagées et Save/Load restent sûrs, et les mesures économiques sont réalisées avant toute activation par défaut.

**Statut : cible définie, non implémentée intégralement.** Ce document n'autorise pas à interpréter le classement actuel ou les anciens bancs comme une comparaison déjà équitable de tous les investissements. Aucune politique économique n'est modifiée par cette documentation.
