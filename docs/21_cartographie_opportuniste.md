# C67 — Cartographie par blocs, lazy et opportuniste : plan

**Plan écrit le 2026-09-21, avant tout code.** Reprend la décision de conception du 2026-09-17
(`docs/taches.md`, section C67 ; `docs/revue_code_2026-09-15_correctifs.md`, section B7) et la
branche sur l'orchestrateur C80 (`docs/18_orchestrateur_double_registre.md`).

## 1. Ce qu'on veut, et pourquoi maintenant

Une représentation grossière de la carte, par blocs réguliers (5×5 ou 10×10 tuiles), qui résume le
terrain de chaque bloc et sert à **prévoir avant de calculer cher**. Elle n'est **jamais** construite
d'un bloc au démarrage : un bloc est calculé quand un projet en a besoin, puis gardé en cache ; le
reste de la carte ne se remplit que sur du temps réellement libre.

Les consommateurs visés, liés à des défauts mesurés :

| consommateur | défaut mesuré aujourd'hui | source |
|---|---|---|
| **coût du rail** | le terrain n'est pas pricé : le capital rail est multiplié par un facteur fixe de **1,70** (`biasPct = 170`, `projects.nut:258`) | `opexai_prix_rail_terrain`, `taches.md` |
| **pré-tracé pour l'A\*** | la recherche rail coûte des opcodes et allonge le tour de file (`16_bilan_volume.md` §7) | C41, C74 |
| **implantation des aéroports** | les aéroports d'AAAHogEx sont plus centraux (37,9 % de centre couvert contre 20 %) ; nous captons 5 fois moins par place | `taches.md` B9, `16_bilan_volume.md` §1 |
| **eau** | `MinchinWeb.Lakes` abandonné, `WATER_LAKES_CONNECTIVITY` forcé à 0 | `taches.md` C57/C67 |

## 2. Ce qui existe

- `spatial.nut` : grille de cellules pour indexer les **paires de villes** (aucun terrain) ; reconstruite
  à chaque génération. À ne pas confondre, mais sa structure plate est un modèle.
- `AIR_SITE_CACHE` : cache des sites d'aéroport par ville et type.
- C76 : révisions par couche et invalidations (villes, industries, lignes). La couche physique de C67
  s'y ajoutera comme une couche de plus.
- C80 : registre de travailleurs résumables avec échéance locale, file réactive et file de fond.
  C'est le support naturel du calcul paresseux et du remplissage opportuniste.

## 3. Modèle de données

- **Bloc** : identifiant = (x / taille, y / taille). Stockage **uniquement des blocs calculés**
  (table clé → vecteur) : aucune structure par tuile, aucune grille pleine.
- **Couche physique** (stable) : `water_ratio`, `buildable_ratio`, altitude min / max / moyenne,
  amplitude de relief, densité de pente, bords côtiers. Le **type** (eau, côte, plat, vallonné,
  montagne) est dérivé de ce vecteur, jamais stocké à sa place ; ses seuils sont calibrés en phase 0,
  pas posés à la main.
- **Couche dynamique** (volatile, séparée) : présence de villes et d'industries, densité de maisons,
  infrastructures OpexAI et adverses. Invalidation par les couches C76 correspondantes.
- **Coût mémoire borné** : au pire 42 025 blocs (10×10) ou 168 100 (5×5) sur 2 048², mais en pratique
  seuls les corridors étudiés sont calculés.
- **Sauvegarde** : non. La couche physique se recalcule à la demande après chargement (carte
  partielle = état valide). À réviser si la phase 0 montre un coût de recalcul prohibitif.

## 4. Exécution : paresseux d'abord, opportuniste ensuite

1. **À la demande** : un consommateur demande les blocs d'un corridor
   (`OpexMapBlocksFor(tuileA, tuileB, marge)`). Les blocs connus sont rendus tout de suite ; les
   manquants sont calculés dans la limite du budget de l'appel, le reste part en **intention
   réactive** `map:<corridor>` (C80) et le consommateur continue avec une carte partielle.
2. **Travailleur `map_blocks`** (C80) : curseur sur une liste de blocs manquants, une tranche
   bornée par son échéance locale, préemptible par toute intention réactive, reprise exacte.
3. **Remplissage opportuniste** : intention de **fond** de plus basse priorité, jouée seulement quand
   rien d'utile n'est prêt — définition mesurée, pas une constante : la dernière passe `projects` n'a
   trouvé aucun candidat constructible (vivier vide ou non finançable). Ordre de remplissage : autour
   des villes et industries déjà servies, puis des candidats non construits. Leçon de C41.13/14 :
   ne **jamais** compter sur le reliquat d'opcodes d'un tick ; le remplissage a son propre tour.
4. **Invalidation** : nos chantiers connaissent leurs tuiles → invalider les blocs touchés ; les
   changements adverses ne sont pas notifiés → un bloc est revérifié avant tout calcul exact qui s'en
   sert (tracé A\*, implantation).

## 5. Phases et critères écrits d'avance

Chaque phase derrière un réglage à défaut 0. Les bancs d'autorité sont des 20×10 en duel sur le PC
de l'utilisateur ; le 5×6 solo ne sert qu'à vérifier les mécanismes.

| phase | contenu | critère de passage |
|---|---|---|
| **0 — mesure** | construire les deux grilles sous sonde sur 256², 512², 1 024², 2 048² ; mesurer mémoire Squirrel, opcodes par bloc, jours de jeu ; vérifier le typage sur un échantillon de blocs contre la vérité tuile ; connectivité eau contre un oracle BFS borné | granularité retenue = meilleure précision du consommateur 1 **par opcode dépensé** ; mémoire à 2 048² mesurée et compatible avec la limite de script |
| **1 — API et travailleur** | `OpexMapBlocksFor`, cache, travailleur `map_blocks`, remplissage opportuniste, invalidation par nos chantiers | aucun consommateur branché : décisions identiques au bit près entre réglage 0 et 1 **à opcodes près** ; carte partielle sans erreur ; selftest en jeu |
| **2 — coût du rail** | remplacer le facteur fixe 1,70 par une prévision de surcoût tirée du corridor de blocs (relief, eau, pente) | erreur relative médiane de la prévision de coût (contre le coût réel mesuré par `AIAccounting`, déjà journalisé par C63) **au moins 25 % plus basse** que celle du facteur fixe ; puis 20×10 duel |
| **3 — pré-tracé A\*** | chercher d'abord un corridor dans le graphe de blocs, restreindre l'A\* exact à ce corridor | opcodes par recherche rail **−30 %** au moins, sans hausse des échecs (`ABND`, `NOPA`) ; puis 20×10 duel |
| **4 — aéroports** | classer les sites d'aéroport par couverture de la densité de maisons (couche dynamique) plutôt que par le premier site constructible | à décider après C78 : si le diagnostic ligne par ligne confirme que l'exploitation (captage) perd l'argent face à AAAHogEx ; critère : profit par place des nouvelles lignes |
| **5 — eau** | connectivité maritime par blocs, retrait du code Lakes et de ses réglages | parité avec l'oracle BFS sur l'échantillon de la phase 0 |

## 6. Risques

- **Coût par bloc** : lire 25 ou 100 tuiles par bloc coûte des appels API ; la phase 0 dit si un
  échantillonnage est nécessaire pour 10×10.
- **Une meilleure prévision ne garantit pas un meilleur profit** : leçon de C75 (plus de volume,
  pas de gain) et de C72 (un meilleur choix d'avion au solo, neutre en duel). D'où un 20×10 à chaque
  consommateur, pas seulement à la fin.
- **Données périmées** : la couche physique change peu, mais les constructions adverses changent la
  constructibilité ; la revérification avant calcul exact est obligatoire.
- **Concurrence avec les tâches métier** : le remplissage opportuniste ne doit jamais retarder une
  construction ; il n'a lieu que lorsque la passe `projects` n'a rien trouvé.

## 7. Ce que le plan ne fait pas

- Pas de scan complet au démarrage, jamais.
- Pas de remplacement du pathfinder exact : la carte par blocs le **guide**, elle ne décide pas du
  tracé.
- Pas de changement de défaut avant les bancs de chaque phase.

## 8. Ordre proposé

Phase 0 dès maintenant (mesure pure, indépendante de C76/C77 en cours sur le PC de l'utilisateur).
Phase 1 après la fusion de la version de C76 retenue (la couche physique s'y greffe). Phase 2 ensuite.
La phase 4 attend le verdict de C78.
