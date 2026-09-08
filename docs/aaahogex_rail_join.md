# AAAHogEx — comment il joint une gare rail

Lu dans `ai/AAAHogEx-115/` (surtout `station.nut`, plus `place.nut` et `trainroute.nut`). **Idées et
méthode seulement** : rien de ce fichier n'est à recopier. OpexAI a déjà une tranche v1
(`docs/opexai_raccordement_gare.md`) qui n'emprunte presque rien de ce modèle.

**Quand s'en servir.** La v1 OpexAI a été retestée après traction (construction +23,6 % de
véhicules, valeur nulle) **et** après partage de bassin (`results/bench_basin_share_paired.json`) :
valeur toujours sous le plancher, véhicules nuls, gares +12,9 %. Le spread convertirait des
`NOPLAN` en jointures sur ce classement-là. Ne pas l'allumer tant que la v1 ne paie pas.

AAAHogEx ne « raccorde » pas une ligne à une gare comme un repli après un rejet `_tooClose`. La
jointure est **un mode de placement** : on cherche un nouveau quai **dans l'enveloppe d'une gare
logique déjà à nous**, et on le construit avec le même identifiant de gare.

---

## 1. L'unité n'est pas une tuile, c'est un groupe

Une gare logique (`StationGroup`) est une collection de quais physiques qui partagent un
`StationID`. Les lignes qui l'utilisent (source, destination, ou les deux si la route est
bidirectionnelle) sont enregistrées sur le groupe.

Conséquences :

- **Ajouter un quai, ce n'est pas réutiliser la voie.** Le nouveau rectangle est un bâtiment
  distinct, dans le `station_spread` du groupe. La voie de la nouvelle ligne a ses propres
  sorties.
- **La production est celle du groupe, pas du quai.** L'offre attendue additionne les lieux
  couverts et les correspondances qui y aboutissent, puis **divise par le nombre de lignes qui
  exportent déjà ce cargo**. Joindre une gare occupée, c'est en prendre une part, pas tout.
- Un groupe **virtuel** (aucun quai encore posé) n'est pas une jointure.

OpexAI a maintenant ce compte, derrière `basin_share` (défaut 0) : production de l'extrémité
jointe divisée par (n+1). **Mesuré, et ça ne paie pas** (`results/bench_basin_share_paired.json`) :
les jointures sont déclassées, l'IA repose des gares neuves, les véhicules ne baissent pas.

---

## 2. Deux API, un seul piège

Le moteur offre deux façons de joindre. AAAHogEx lit `station.distant_join_stations` une fois
(`UpdateSettings`) et n'en mélange pas les sémantiques.

| réglage du jeu | ce qu'il passe à `BuildRailStation` | où il cherche |
|---|---|---|
| distant join **allumé** | l'identifiant du premier quai du groupe | tout rectangle dans le `station_spread` restant |
| distant join **éteint** | `STATION_JOIN_ADJACENT` | seulement les tuiles **autour** des quais déjà là |

Piège qu'il a nommé et qu'il refuse **avant** de poser : avec `JOIN_ADJACENT`, si **deux** gares
à nous touchent déjà le rectangle candidat, le moteur crée une **nouvelle** gare au lieu de
joindre. Ils comptent les `StationID` voisins (propriété à nous) sur le pourtour du quai ; dès
qu'il y en a deux, le site est mort.

Après construction en mode adjacent, ils revérifient que le `StationID` posé est bien celui du
groupe. Un succès de commande qui n'a pas joint est un échec.

---

## 3. Où chercher : l'enveloppe de spread, pas les deux côtés du quai

Le groupe a une boîte englobante (union des rectangles de quais). L'espace restant jusqu'à
`station.station_spread` (lu dans le jeu, 12 si le réglage vaut −1) est la zone candidate, bornée
pour ne pas tout balayer (longueur/largeur de quai + une marge).

Ce n'est **pas** « coller un quai parallèle au nôtre ». OpexAI v1 ne propose que les deux
translatés d'une tuile, même longueur, même orientation. AAAHogEx accepte n'importe quelle
orientation et n'importe quel ancrage dans l'enveloppe, y compris un quai plus loin qui agrandit
le bassin (surtout en ville, si le distant join est allumé et qu'ils n'ont pas interdit
d'étendre la couverture urbaine).

---

## 4. Quand ils choisissent de joindre

`CreateBest` sur un **lieu** (ville ou industrie), pas sur un conflit géométrique :

1. Si le lieu a déjà une gare de ce mode de transport, on part de celle-là.
2. Si le lieu **produit**, on essaie d'abord les groupes qui produisent déjà ce cargo.
3. Sinon on scanne les tuiles du bassin (production / acceptation) et on pose une gare neuve.
4. Puis les groupes qui **acceptent** déjà ce cargo.
5. En ville, un repli « petits morceaux » d'arrêts pour étendre la couverture — surtout route ;
   le rail passe surtout par (2)–(4).

Filtres sur le groupe, avant même la géométrie :

- pas un arrêt de ville (bus interne) ;
- le groupe doit déjà produire (resp. accepter) le cargo du lieu ;
- optionnellement, le cargo « étiquette » du premier quai doit coincider.

La destination de la **nouvelle** ligne sert à orienter le quai (score de direction) et à
choisir le coin du groupe le plus proche (distant join). Ce n'est pas un pathfinder : c'est un
score de site.

---

## 5. Ce qu'ils refusent de mélanger (cargo et rôle)

Deux règles économiques, distinctes de la géométrie :

**Ne pas importer ce que le groupe exporte déjà.** Quand on joint, les cargos déjà emportés par
une ligne *non-transfert* depuis ce groupe, et que le groupe n'accepte pas *ici*, sont
interdits comme nouvelles acceptations. Une gare charbon-source ne devient pas un puits charbon
par accident.

**Ne pas voler une autre industrie.** Pour une gare **neuve** (pas une jointure) qui accepte un
cargo d'industrie, ils vérifient que l'industrie réellement préférée dans le bassin est bien
celle visée (le moteur tranche par identifiant). Sur une jointure, ils sautent ce test : le
groupe a déjà un lieu.

OpexAI v1 est plus étroit et plus local : même `kind`, même cargo, et pour le fret **même rôle**
(source avec source, puits avec puits). Il ne modélise pas le partage ni le vol d'industrie.

---

## 6. Le quai joint a sa propre voie

Avant `BuildRailStation`, ils regardent les tuiles **devant et derrière chaque voie du nouveau
quai**. S'ils y trouvent **notre** rail portant le même bit de direction que le quai, le site est
refusé. Ils ne branchent pas le nez du quai sur une ligne existante.

C'est le même invariant qu'OpexAI v1 (`JOINPATH` : le chemin ne doit toucher aucun rail déjà
là), mais AAAHogEx le teste **à la sortie du quai**, pas sur tout l'A\*. Chez lui le pathfinder
vient après, et une jointure ratée de voie est un autre problème (`RetryToBuild` sur le tracé,
pas sur la gare).

Les gares destination rail partent souvent sur **plusieurs voies** (trois par défaut), les
correspondances sur deux. Joindre, c'est encore ajouter un rectangle, pas élargir le quai
abstraitement — l'API n'a pas d'autre primitive.

---

## 7. Comment un site gagne

Dans l'enveloppe :

1. Préfiltre d'emprise : rectangle constructible, **écart de hauteur des coins ≤ 2** (pas
   `SLOPE_FLAT` tuile par tuile).
2. Score : orientation vers l'autre bout, distance des coins à un point d'intérêt (quai existant
   et/ou destination), plus production ou acceptation du **nouveau** rectangle.
3. En ville, l'acceptation pèse beaucoup moins si on a le droit d'étendre la couverture : on
   cherche plutôt un site joignable qu'un maximum local d'acceptation.
4. Premier site qui passe `Build` sous `AITestMode` **gagne** ; ils coupent la queue, trop chère.
5. Longueur de quai : on part long (borné par `vehicle.max_train_length` et une formule en
   distance) et on **raccourcit par fractions**, pas nécessairement de 1 en 1.

Construction réelle : attendre l'argent ; si l'autorité locale refuse, planter des arbres une
fois puis réessayer. NewGRF : s'ils connaissent le cargo, ils posent une gare NewGRF avec type
d'industrie et drapeau source, pas seulement `BuildRailStation`.

---

## 8. Ce que ça change pour OpexAI (sans le copier)

| | OpexAI v1 | AAAHogEx |
|---|---|---|
| Déclencheur | filet `_tooClose` / `MIN_SEPARATION` | placement au lieu, avant le pathfinder |
| Géométrie | un quai parallèle, même longueur | tout ancrage dans le spread du groupe |
| Voie | chemin dédié, rejet si un rail existant est touché | sorties de quai libres de notre rail |
| Économie | gare neuve par défaut ; `basin_share=1` → 1/(n+1), mesuré, n'a pas payé | offre du groupe **divisée** par les exportateurs |
| Cargo | kind + cargo + rôle fret | groupe déjà producteur/accepteur ; interdiction d'importer un export |
| Réglage jeu | ignoré | `distant_join_stations` change l'API **et** la zone de recherche |
| Défaut projet | `station_join = 0` (le banc n'a pas payé) | toujours, c'est comme ça qu'il pose les gares |

Pistes **utiles** si on rouvre la jointure, sans reprendre leur usine à scores :

1. ~~Traiter le groupe / `StationID` comme bassin partagé, et **diviser** `monthly` par les
   lignes déjà dessus~~ — **fait** (`basin_share`), mesuré, défaut 0, ne paie pas (§2.9.3).
2. Chercher dans le spread, pas seulement les deux translatés. Le banc join a tué 68/82 en
   `NOPLAN` : beaucoup de ces échecs sont « pas de parallèle libre », pas « pas de gare
   joignable ».
3. Gérer explicitement les deux API (identifiant vs adjacent) et le cas « deux voisins ».
4. Interdire le retournement de rôle (source qui se met à accepter le même cargo).
5. Ne pas joindre si les sorties du nouveau quai sont déjà nos rails — chez nous `JOINPATH` le
   fait trop tard, après l'A\*.

Pistes **à ne pas importer telles quelles** : le score d'orientation tuile par tuile, le
« premier test-build gagne », la formule d'offre urbaine au spread (non mesurée chez nous),
NewGRF station, et le pathfinder-puis-construction global d'AAAHogEx.

Rien de tout ça n'a été mesuré dans *notre* banc. La v1 OpexAI reste le seul chemin jointure
instrumenté, et il est éteint par défaut.
