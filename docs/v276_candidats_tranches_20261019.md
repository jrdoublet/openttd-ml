# V276 — génération des candidats par unités reprenables

19 octobre 2026, branche `v276`, issue de master. Demande utilisateur : aucun
banc, Docker ou moteur ; commits locaux autorisés, aucun push ; C115 intact.

## Statut et frontière de la livraison

Prototype derrière `v276_cand_slices`, **0 aux quatre difficultés**. Il retire
les boucles quadratiques synchrones des appelants rail lorsque le réglage vaut
1 ou 2. **Le plafond strict demandé « aucune tranche au-delà du budget hors appels
natifs » n'est pas satisfait** : une évaluation économique et la publication
du portefeuille restent des atomes Squirrel. Le budget est un seuil de retour
entre opérations, comme pour le scan AIR existant. Ne pas présenter ce travail
comme une qualification économique ni comme une preuve de plafond dur.

## Implémentation

- `candidates_v276.nut` : demande coalescée et transaction sur la tâche
  `catalog`, photographie du catalogue et des révisions AC06 au démarrage.
  Depuis V276c, le worker utilise le reliquat en fin de chaque tick de la boucle
  principale, après la file, ses continuations et les hooks A*/C67, uniquement
  sous le réglage. Il n'a plus de créneau `v276_candidates` dans la file.
  Aucun redémarrage du curseur pendant une transaction.
- AIR actif : première publication AIR (ou fin du scan), fret rail par revenu,
  voyageurs rail par bande, puis fret route. Sans AIR : voyageurs rail, fret
  rail, route. La priorité porte sur la génération, pas sur une nouvelle
  priorité des constructions du portefeuille commun.
- Voyageurs : énumération reprenable des voisins par grille spatiale, score
  `popA * popB * sqrt(distance Manhattan)`, `AIList.Sort` natif décroissant,
  évaluation en ordre de score. Bandes disjointes du helper existant
  `OpexRailPaxPairInBand`. Fret : revenu sur 80 tuiles et délai calculé à
  `vRail`, cache annuel ; distance décroissante dans chaque cargo/bande.
  Aucun comparateur Squirrel sur la file de paires.
- Les évaluateurs historiques reçoivent un micro-catalogue de deux villes ou
  d'une source et d'un puits. Ils conservent les gardes métier et le courrier,
  notamment V163/V179/V264, sans réimplémenter l'économie. La route énumère
  aussi ses puits urbains via le filtre d'acceptation historique.
- TOP_K maintenu au fil des évaluations ; publication toutes les 50 évaluations
  et en fin d'unité (au plus 500 évaluations par unité et par scan), remplacement
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

Depuis V276c, les invariants et la grille sont construits une fois par unité.
La requête de voisinage matérialise les indices des neuf cellules et reste
atomique ; son coût dépend de leur population. L'énumérateur traite ensuite
plusieurs paires par appel, avec une garde entre chaque paire. Coût d'une tranche :
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
encore contenir O(n²) paires dans une zone très dense ; seules les alternatives
économiques conservées sont limitées à TOP_K par unité. Les valeurs de score sont converties en entiers
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

## V276b — pondération par la production

Extension demandée le 19 octobre : plage 0..2, défaut 0 aux quatre difficultés.
Le chargement conserve désormais la valeur entière ; tous les consommateurs
activent le découpage par `V276_CAND_SLICES > 0` (ou son complément pour OFF).
Le mode 1 conserve le tri fret par revenu unitaire à 80 tuiles, délai à vRail.
Le mode 2 multiplie ce revenu par la somme de
`AIIndustry.GetLastMonthProduction(catalog.industries[source].id, cargo)`
sur toutes les sources du cargo du catalogue. Ce calcul est effectué dans
`OpexV276CargoOrder`, après la garde du cache annuel existant : pas de somme
à chaque tranche. Les cargos sans sources et les voyageurs restent exclus.
Les unités voyageurs et leur score `popA * popB * sqrt(distance Manhattan)`
restent inchangés, comme les autres traitements entre les modes 1 et 2.

Les contrats V276 couvrent les deux classements, la somme multi-sources,
la production nulle, l'exclusion voyageurs, le cache annuel, le chargement
entier, les défauts 0, la borne 2 et le plafond de 100 `AddSetting`.
Aucun banc, Docker ou moteur pour V276b, conformément à la mission.
Les limites de compilation, santé moteur et mesure économique ci-dessus
restent applicables ; C115 et les défauts sont inchangés.

Validation V276b : 20 tests ciblés OK ; suite complète
`python3 -m unittest discover -s sweeps -p 'test_*.py'` : **2 102 tests OK**
(3 ignorés, 3 échecs attendus). `delim.py` et `git diff --check` propres ;
`undecl.py` retrouve uniquement les deux identifiants connus
`AICONFIG_BOOLEAN` et `CONFIG_BOOLEAN`.

## V276c — débit, grille et publications intermédiaires

Correction demandée après la mesure moteur communiquée par Claude le 19/10 :
copie figée de `632bd47`, mode 1, 1024², graine 42, un an ; 86 tranches restées
à `unit=0 phase=enumerate`, aucune publication. Cette observation concerne V276
initial, pas le code V276c. Aucun nouveau moteur, Docker ou banc autorisé ici.

`OpexV276Tick` est appelé après les tâches et continuations à chaque passage de
la boucle principale. Il conserve l'admission précédente : reliquat moins
2 000 opcodes, plafond de 6 000, aucun appel si le budget utile est ≤ 1 000.
La file garde son ordre et ses créneaux ; une opération atomique peut toujours
franchir un tick. Ce changement augmente les occasions de progresser, sans
preuve moteur de cadence ou d'absence de retard due à ces débordements.

Chaque unité mémorise villes, sources, puits industriels puis urbains, taille,
borne extérieure et grille `OpexSpatialGrid`. Cellule = borne maximale de sa
bande : `railMax`, `railAirOverlapMin - 1` pour voyageurs rail seuls, ou
`roadGenMax` (repli `roadMax`) pour route ; minimum technique 1. Une requête
3×3 conserve tous les voisins possibles en distance Manhattan, puis les filtres
de bande historiques retirent les faux positifs. Le fret interroge la grille
des puits depuis la tuile source, avec indices orientés conservés. Le ciblage
garde sa recherche reprenable et ses lignes/colonnes ; le voyageur ciblé peut
voir les indices inférieurs au sien, sans perte par symétrie. L'énumérateur
traite les voisins jusqu'au budget et conserve le curseur exact entre ticks.

Deux constantes littérales, sans nouveau réglage ni modification du défaut :

- `V276_PUBLISH_EVERY = 50` : rendre exploitable le TOP_K courant après les
  50 premières évaluations puis chaque lot de 50, tout en amortissant le coût
  atomique de fusion/application du portefeuille. Une évaluation sans candidat
  compte aussi ; les unités courtes publient leur reste, même vide.
- `V276_EVAL_CAP = 500` : limiter à dix lots l'économie coûteuse par unité et
  par scan, en conservant les 500 premiers scores du tri natif décroissant.
  Puis avancer à l'unité suivante pour qu'elle ait aussi accès aux évaluations.
  Le prochain scan réénumère et reprend **en tête du nouveau tri**, sans curseur
  économique résiduel. Les paires restantes redeviennent éligibles ; des scores
  inchangés ne garantissent pas qu'une paire classée au-delà de 500 sera évaluée.

Ces valeurs sont un compromis de débit demandé, pas un optimum mesuré.
La publication périodique ne fait pas avancer l'unité ; celle de fin n'est pas
doublée à 50/500. Elle remplace seulement le lot de l'unité courante avec son
TOP_K cumulé et conserve les autres lots. Les unités vides publient une fois.
Ordre selon MODE_AIR, score, modes 1/2, ACK sur photographie et abandon des
transactions au Load restent conservés.

Sous `decision_log`, `V276_SLICE` ajoute `enumerated`, `evaluated`,
`publications`, cumulés depuis le début du scan. `enumerated` compte les
voisins examinés avant les filtres exacts ; `evaluated` compte les appels
économiques terminés. `V276_PUBLISH unit= evaluated= kept=` rapporte l'index
d'unité, ses évaluations cumulées et la taille de son TOP_K, puis mode/cargo/bande.
Les compteurs sont transitoires, sans changement de Save/Load.

Validation V276c : 25 tests ciblés OK, couvrant créneau par tick/reliquat,
grille contre oracle exhaustif filtré (voyageurs, fret, cibles, bornes),
publication tous les N, plafond, unités courtes/vides, absence de doublon,
reprise aux petits budgets et nouveau tri au scan suivant. Ces modèles Python
et contrats statiques ne compilent pas Squirrel et ne remplacent pas une
mesure moteur. Le plafond dur, le débit en partie et l'économie restent non mesurés.

Suite complète : `python3 -m unittest discover -s sweeps -p 'test_*.py'`,
**2 107 tests OK** (3 ignorés, 3 échecs attendus). `delim.py` et
`git diff --check` propres ; `undecl.py` retrouve seulement les identifiants
connus `AICONFIG_BOOLEAN` et `CONFIG_BOOLEAN`.
