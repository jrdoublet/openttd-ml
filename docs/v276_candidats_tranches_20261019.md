# V276 — génération des candidats par unités reprenables

19 octobre 2026, branche `v276`, issue de master. Demande utilisateur : aucun
banc, Docker ou moteur ; commits locaux autorisés, aucun push ; C115 intact.

## Statut et frontière de la livraison

Prototype derrière `v276_cand_slices`, **0 aux quatre difficultés**. Il retire
les boucles quadratiques synchrones des appelants rail lorsque le réglage vaut
1. **Le plafond strict demandé « aucune tranche au-delà du budget hors appels
natifs » n'est pas satisfait** : une évaluation économique et la publication
du portefeuille restent des atomes Squirrel. Le budget est un seuil de retour
entre opérations, comme pour le scan AIR existant. Ne pas présenter ce travail
comme une qualification économique ni comme une preuve de plafond dur.

## Implémentation

- `candidates_v276.nut` : demande coalescée et transaction sur la tâche
  `catalog`, photographie du catalogue et des révisions AC06 au démarrage.
  Le worker a un créneau `v276_candidates` ajouté en fin de file, actif
  uniquement sous le réglage. Les autres tâches, notamment AIR, gardent leurs
  créneaux ; aucun redémarrage du curseur pendant une transaction.
- AIR actif : première publication AIR (ou fin du scan), fret rail par revenu,
  voyageurs rail par bande, puis fret route. Sans AIR : voyageurs rail, fret
  rail, route. La priorité porte sur la génération, pas sur une nouvelle
  priorité des constructions du portefeuille commun.
- Voyageurs : énumération reprenable des paires, score
  `popA * popB * sqrt(distance Manhattan)`, `AIList.Sort` natif décroissant,
  évaluation en ordre de score. Bandes disjointes du helper existant
  `OpexRailPaxPairInBand`. Fret : revenu sur 80 tuiles et délai calculé à
  `vRail`, cache annuel ; distance décroissante dans chaque cargo/bande.
  Aucun comparateur Squirrel sur la file de paires.
- Les évaluateurs historiques reçoivent un micro-catalogue de deux villes ou
  d'une source et d'un puits. Ils conservent les gardes métier et le courrier,
  notamment V163/V179/V264, sans réimplémenter l'économie. La route énumère
  aussi ses puits urbains via le filtre d'acceptation historique.
- TOP_K maintenu au fil des évaluations ; à la fin de chaque unité, remplacement
  de son lot et conservation des lots des unités encore non recalculées,
  application via `OpexApplyGeneratedModeProjects` et resélection sur le
  capital courant. Les candidats devenus invalides sont filtrés avant application.
- `OpexBuildCandidates`, `OpexBuildRoadCandidates`, C121, C80/C76 et les
  reconstructions complètes recyclent la publication courante. Le chemin OFF
  conserve les corps historiques, avec les gardes et un argument interne
  optionnel pour l'évaluation d'une paire route.
- C76 ciblé voyageurs : recherche reprenable de la ville, puis seulement les
  paires qui la touchent, O(n). Fret ciblé : recherche reprenable du rôle de
  l'entité puis ligne/colonne correspondantes, O(sources + puits), sans
  parcourir le produit cartésien pour ensuite le filtrer.
- Les ACK synchrones ne consomment plus les modes différés. Une transaction
  complète acquitte leur photographie initiale ; les événements plus récents
  restent détectables par les révisions consommées par mode. Une transaction
  ciblée n'acquitte pas tout le mode. Load jette transaction, requête, lots et
  cache publié ; le filet C76 existant reconstruit.

## Budget et limites

Admission du worker : reliquat du tick moins 2 000 opcodes, au plus 6 000 ;
aucun appel si le reliquat utile est ≤ 1 000. Contrôle du budget, du tick
initial, de `deadlineTick` et du reliquat entre deux étapes ; un atome commencé
est terminé avant retour. Le curseur avance avant l'évaluation et reprend
exactement, sans répéter la paire après une suspension VM.

Une étape d'énumération est O(1), hors indexation native ; estimation statique
de l'ordre de quelques centaines d'opcodes, **non mesurée**. Coût d'une tranche :
seuil utile (≤ 6 000) + dernière opération + retour/instrumentation. Aucun
majorant numérique honnête du coût économique/publication n'est établi ici.
`V276_SLICE` sous `DECISION_LOG` rapporte ops, budget, ticks, dernier atome et
`overrun`, pour rendre cette limite observable lors d'une future validation
autorisée. Les tris et clones de conteneurs sont natifs atomiques. La préparation
initiale des unités parcourt aussi les cargos (nombre borné par le moteur).

La publication et l'évaluation d'une paire appellent encore des helpers qui
parcourent les lignes, le voisinage constructible et le portefeuille. Pour un
plafond strict, il faut des curseurs supplémentaires sur ces parcours et sur
la sélection/application ; une simple garde autour de l'appel ne suffirait pas.
Le rafraîchissement du catalogue, la génération eau et les autres traitements
historiques ne sont pas découpés par cette livraison. La file bon marché peut
encore contenir O(n²) paires ; seules les alternatives économiques conservées
sont limitées à TOP_K par unité. Les valeurs de score sont converties en entiers
pour `AIList`, avec les arrondis flottants ordinaires du moteur.

## Ordre AIR vérifié, non modifié

`air_towns.nut::OpexAirSortedTowns` commence par population décroissante.
`air_planning.nut::OpexAirPlansPrepare` applique ensuite la priorité de cache
C121 (ou place la cible en tête), puis `OpexAirPlansFindSites` parcourt les
villes dans cet ordre et revalide les sites. `OpexAirPlansNewPairs`
énumère les paires par curseur `a/b`, et non par produit des populations et
racine de distance. Les chemins hubs et C83 ont leurs propres parcours.

Changer seulement le tri des villes ne donne pas le score demandé des paires.
Il faudrait ajouter une phase reprenable d'énumération de paires après
revalidation des sites, une AIList native ordonnée par score, puis adapter
les curseurs `a/b`, les snapshots/replays, les retours C83 ciblés et les chemins
hubs. Ce n'est pas une modification simple isolée : aucun changement de cet
ordre ni commit AIR séparé dans cette livraison. Le recyclage AIR de C78.4 est
étendu sous le réglage V276 pour éviter sa réentrée synchrone depuis un rebuild.

## Validation sans moteur

17 tests V276 : contrats statiques et modèles de reprise à chaque petit
budget, oracle de score indépendant, partitions de bandes, ciblage linéaire,
publication incrémentale, ACK et rotation de file. Le contrat V166 est adapté
au nouvel évaluateur rail, avec vérification de sa garde `MODE_RAIL`.

Suite hôte : **2 099 tests, OK**, 3 ignorés et 3 échecs attendus existants.
`undecl.py` ne signale que `AICONFIG_BOOLEAN` et `CONFIG_BOOLEAN`, également
présents avant V276 ; `delim.py` et `git diff --check` sans anomalie.
Ces contrôles ne compilent pas Squirrel, ne prouvent pas la santé moteur,
Save/Load réel, absence de famine en partie ni gain économique. Aucun de ces
résultats n'est revendiqué. Aucun banc lancé conformément à la demande.
