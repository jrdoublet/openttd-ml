# RAIL-LONG-EARLY — fenetre progressive et signaux pax/fret (22/10/2026)

## Statut

**Prototype de politique hors-jeu et contrat testable ; non raccorde au constructeur.**
Le module Python `sweeps/rail_long_window_policy.py` produit des evenements
`WindowEvent` a partir de mesures, sans lancer OpenTTD ni modifier l'IA.
Il ne faut pas presenter ses resultats comme une qualification economique.
L'etat actuel du depot et les modifications concurrentes AIR-FLOTTE sont preserves.

## Bande de recherche

Distance = Manhattan, non la longueur d'un rail construit ni le rayon A*.
Le centre reste **256 cases** sur toutes les cartes pour eviter d'extrapoler
l'A* vers 512/1024 tuiles sans mesure. La borne haute est limitee a
`map_width + map_height - 2`.

| Etape | Fenetre totale | **Seules nouvelles distances** | Observation |
|--:|:--|:--|:--|
| 0 | 224-288 | 224-288 | Premiere fenetre |
| 1 | 208-304 | 208-223, 289-304 | ±16 |
| 2 | 201-320 | 201-207, 305-320 | tranche <201 deja couverte par rail normal a 200 |
| 3 | 201-336 | 321-336 | plus aucune recherche a gauche |
| 4 | 201-352 | 337-352 | et ainsi de suite |

`288 - 224 = 64`, mais la plage inclusive comporte **65 distances entieres**.
Le module represente ces intervalles inclusifs sans doublons. Si le plafond
normal est different de 200, on recalcule le clamp depuis ce plafond, plutot
que de remesurer des distances courtes. Les fenetres peuvent etre vides sur
les petites cartes, notamment 64².

## Deux signaux, deux curseurs et deux caches distincts

**Rail voyageurs, en multimodal.** Mesurer la proportion des **30 % de villes
les plus peuplees** deja atteintes par les lignes AIR, sur une cohorte de
villes figee au debut de partie. Premiere activation lorsque la proportion
atteint au moins 80 % et progresse d'au plus **5 points de pourcentage sur
12 mois**. Ne pas exiger 100 %, qui ne survient pas en duel. Une activation
ne supprime pas la concurrence economique de l'AIR.

**Rail voyageurs, en rail seul.** Le meme indicateur porte sur les villes
atteintes par nos lignes **RAIL pax** et non par l'AIR inexistant. Comme ce
mode peut construire tres peu de lignes pax, un **repli** doit exister :
moins de 2 projets RAIL pax courts encore demarrables pendant deux observations
mensuelles consecutives, avec >=100 k£ de capital mobilisable. C'est une
hypothese de declencheur **non calibree** : les logs rail-seul archives
`v207v212_current_railonly_40x3` et `v217_default_railonly_vs_aaa_40x3`
sont de taille zero. Aucun taux de declenchement reel n'est revendique.

**Rail fret, tous modes.** Le bassin industriel et ses cargos sont independants
de la couverture des villes passagers. Premier signal propose : moins de
2 projets RAIL **fret courts** demarrables pendant deux mois consecutifs et
capital mobilisable >=100 k£. Il reutilise l'intuition de V217, mais n'exige
pas le seuil de 1 M£ de V269 : on recherche les opportunites **avant** de
pouvoir les financer. Ne pas reduire le vivier "demarrable" aux seules
constructions financees ; verifier les motifs de rejet.

**Garde commune exploratoire :** pas d'ouverture pendant les 24 premiers mois.
Elle empeche de promouvoir le RAIL long en pleine expansion AIR initiale
(porte A), mais ne doit pas etre confondue avec une bascule de date fixe :
une seule garde d'age ne peut pas declencher l'ouverture. Un palier au plus
par 12 mois et par famille, si son signal reste present. Les deux fenetres
peuvent donc etre a des etapes differentes.

## Mesures 256² qui motivent le signal pax

Depuis les 40 graines appairees de
`results/calibration_pc_20261021/results/calib_{solo,duel}_40x10_pc_20261021_engine/`
(1970-73, population de la cohorte C96 de 1970), la couverture moyenne
du top 30 % est :

| Regime | 1970 | 1971 | 1972 | 1973 |
|:--|--:|--:|--:|--:|
| Solo | 67,7 % | 89,9 % | 92,7 % | 97,1 % |
| Duel | 66,7 % | 80,0 % | 84,0 % | 85,1 % |

Declencheur historique de fin d'annee ">=80 % et croissance <=5 points" :
solo **27/40** declenchent d'abord en 1972, **6/40** d'abord en 1973,
**7/40** jamais sur la fenetre ; duel **2/40** en 1971,
**16/40** en 1972, **7/40** en 1973, **15/40** jamais.
La garde d'age de 24 mois repousse naturellement les cas precoces.
Ce sont des **comparaisons annuelles de l'historique**, pas une simulation
rejouee avec effet RAIL.

L'indicateur historique "atteinte" repose sur `AIR_BUILD.src_town/dst_town`
et ne mesure ni tous les aeroports ennemis, ni les slots libres dans les
villes. `C96_SITE` ne donne pas necessairement toutes les petites villes :
avant une adoption comportementale, capturer la **liste exhaustive** des
villes/populations et l'occupation de slots. Stabiliser le denominateur entre
deux snapshots, ou conserver une cohorte initiale.

## Chaine de pre-calcul cible : SHADOW, pas le portefeuille actif

1. Creer un controleur independant des deux types `pax`/`freight`, chaque
   curseur portant palier, dernier epoch, bornes deja visitees, invalidations
   de terrain, villes/industries et moteurs, et un faible nombre de projets.
2. Enumerer **les nouveaux anneaux seulement**, partitions par cargo et
   bande ; filtrer distance avant l'evaluation economique. Une recherche
   resumable controle le budget d'opcodes et les quotas de production.
   Pour les plus grandes cartes, imposer quotas/echantillonnage par source,
   sans fausser le TOP par un classement des grandes distances seulement.
3. Sauver les quelques candidats admissibles dans un **stock shadow
   distinct de `candidateGroups`**, y compris s'ils ne sont pas encore
   finançables. Ne faire aucune construction sur cette passe.
4. Une recherche physique A* de pre-calcul en arriere-plan peut, pour le
   meilleur candidat par famille, reutiliser le worker `rail_stock` C80 :
   un seul chemin en vol, tranche d'opcodes bornee, controle de stale/TTL,
   jamais de pose anticipée. Il faudra faire differer les priorites du rail
   stock courant sans le perturber.
5. Au signal correspondant, **revalider** le candidat (origine/puits, lignes,
   abandons, sites, ancien trace) et **recalculer** ses couts/profits avec le
   modele du jour ; ensuite seulement le soumettre au budget et au
   portefeuille par **fusion additive**, sans effacer les RAIL courts.
   Si l'argent manque, conserver le precalcul tant qu'il est valide.

### Pourquoi pas simplement V269 / V276 ?

- `OpexV276Publish` injecte immediatement des projets dans
  `candidateGroups`. Ce n'est pas un cache shadow. Le reselect/tri actif
  peut changer des le pre-calcul, meme sans depense immediate.
- `OpexApplyGeneratedModeProjects(mode="rail")` remplace le rail genere ;
  une publication du seul anneau long effacerait des candidats courts.
- V276 prend au maximum **500 evaluations par unite**, mais enumere puis
  trie toutes les paires avant ce cap : la memoire, `AIList.Sort` atomique
  et le nombre de voisins sont les risques majeurs sur 1024².
- Le cap normal `catalog.bounds.railMax` ne doit pas etre eleve globalement :
  il controle aussi les decoupages AIR_ONLY et RAIL_ONLY. Utiliser une copie
  locale ou un intervalle explicite pour la passe longue.
- Les filtres `OpexMakeCandidate` existants de profit/opcodes ne sont
  **pas qualifies** pour les distances >250 ; les diagnostics precedents
  ont trouve 0 construction au-dela de 250 en 1x10 suivi. Le ROI va changer :
  ne pas modifier ces filtres sur cette seule hypothese de rentabilite.
- Sur 256², le V276 auto est OFF, donc ne pas rendre le nouveau signal
  dependant de `V276_CAND_SLICES>0`. Un scan shadow dedie doit fonctionner
  en incremental sans activer la generation integrale V276.
- L'IA expose deja **100 settings**. Ne pas creer un 101e sans etudier la
  limite OpenTTD et les options de consolidation : garder le prototype
  hors-jeu ne modifie donc aucun parametre utilisateur.

## Garde de qualification avant integration

Test synthétique de machine d'etats, puis journalisation sur 256² avec
selection/portefeuille *strictement identiques* a la reference (shadow).
Suivre par famille et par anneau : paires disponibles, distance, par source,
enfilees, econ evaluee, candidats conserves, candidats invalides, recherche
A* lancee/terminee, iterations et opcodes, budget par tick, choix et
constructions effectives apres promotion, projets AIR/RAIL courts evacues.
Comparer solo, duel et **rail seul**, et enfin 512²/1024², avant activation
economique. Sans exposition et construction causale, aucun accroissement
du plafond courant ne peut etre qualifie.
