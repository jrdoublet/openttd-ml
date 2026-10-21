# Bornes de distance : precision, opcodes et neutralite intermodale

21 octobre 2026. Etude hors ligne des 40x10 SOLO et DUEL sur 256x256.
Aucune modification du modele actif ni relance OpenTTD.

Scripts : sweeps/evaluer_bandes_roi_20261021.py et
sweeps/test_bandes_roi_20261021.py.
Donnees JSON : evidence/review/roi_calibration_predictors_20261021/bandes_distance_roi_20261021.json.

## Bornes existantes : oui, reutilisables sans appel API

OpexRefreshEpochBounds, dans ai/OpexAI/candidates.nut, stocke les
seuils dans catalog.bounds au refresh du catalogue. Les fonctions
OpexAirPairInBand, OpexRailPaxPairInBand et OpexRoadDistanceAllowed
les reutilisent. projects.nut, scheduler_tasks.nut et candidates_v276.nut
les emploient deja pour le bootstrap et le decoupage des calculs
de candidats.

Les 2109 evenements EPOCH_BOUNDS observes sur les 80 parties
contiennent tous la meme table :

| Borne | Valeur |
|---|---:|
| roadMin, roadMax, railMin | 7 |
| roadGenMax | 200 |
| railAirOverlapMin, railMax, airMin | 200 |
| airMax | 512 |

La bande AIR + RAIL voyageurs se reduit donc a Manhattan = 200,
et la zone ROUTE exclusive a 7. Toutefois ROAD explore jusqu'a
roadGenMax = 200 et le fret RAIL a ses propres regles. La cascade
historique ne cree donc PAS quatre populations statistiques
exploitables en tant que telles.

ATTENTION : AIR_BUILD.dist represente la distance de vol entre
ancres aeroportuaires, tandis que les bornes AIR s'appliquent
a Manhattan entre centres des villes. Notre analyse reconstruit
ce dernier a partir des tuiles source et destination sur la
carte 256x256, sans appel de jeu. Ainsi 1868/1892 lignes AIR
matures DUEL sont au-dela de railMax et 24 dans le chevauchement ;
les seules distances AIR_BUILD auraient donne une classification
incorrecte. Ne pas reappliquer cette reconstruction aux autres
tailles de carte sans verifier la largeur.

## Validation hors graine : les profits ne beneficient pas des bandes

Corrections statistiquement testees en gardant le ROI, le cargo,
le capital et la distance comme variables de base.

| MAE du ROI annuel, points (DUEL) | Base | + cascade | + 4 sous-bandes |
|---|---:|---:|---:|
| AIR | 13,891 | 13,887 | 13,889 |
| RAIL | 12,614 | 12,609 | 12,687 |
| ROAD | 53,818 | 53,818 | 53,818 |

Conclusion : pas de raison de changer le profit ou le score AIR,
ni de deployer une calibration de ROI par bande.

## Les memes bornes permettent de mieux predire le capital RAIL

Les sous-bandes divisent arithmetiquement l'intervalle
roadMax..railAir (7..200 ici) sans aucune geometrie de terrain.
Sous-bandes rail : coupures 55, 103 et 151.
Tous les modeles ci-dessous sont appris sur SOLO et evalues
sur DUEL, avec graines test absentes du pli d'apprentissage.
Echantillon : 958 constructions RAIL avec cout physique positif
et lignes matures. Aucun candidat non construit n'a de verite terrain.

| Methode pour le cout RAIL | MAE £ | MedAE £ | Erreur relative mediane |
|---|---:|---:|---:|
| Cout estime actuellement | 26 948 | 24 651 | 32,22 % |
| Un facteur global | 12 786 | 10 349 | 14,14 % |
| Cascade brute | 12 614 | 10 179 | 14,02 % |
| 2 sous-bandes | 11 348 | 8 497 | 12,08 % |
| 4 sous-bandes | 11 008 | 8 356 | 11,65 % |
| **Formule lineaire par distance** | **10 342** | **7 823** | **10,78 %** |

Gain moyen de la formule lineaire face au facteur global :
2408 £ de MAE par graine [IC95 bootstrap 1999 ; 2795],
39/40 graines favorables. Les quatre sous-bandes gagnent
1761 £ [1482 ; 2019] sur le facteur global, 40/40 graines.

Formule issue des 954 lignes SOLO matures :

    cout_prevu_physique = cout_modele * (1.051981 + 0.00306588 * distance)

Exemples de facteur : 1,205 a 50 tuiles ; 1,359 a 100 ;
1,512 a 150 ; 1,665 a 200. Une multiplication et une
addition pour le facteur (plus application au cout), aucune
requete de carte ni A*. Si l'on veut une borne de validite,
utiliser les limites deja memorisees dans catalog.bounds.
**Le nombre exact d'opcodes n'est pas encore mesure dans OpenTTD.**
Cette formule ne doit pas etre extrapolee a 1024x1024
ou a d'autres epoques sans preuve.

Validation de coherence temporelle : pente SOLO 1970-74
0,00309 (n=892) contre 1975-79 0,00296 (n=62).
Pente DUEL sur toutes les annees 0,00328 (n=958).
Les lignes tardives sont trop peu nombreuses pour conclure
a la stabilite complete.

ROAD : seulement 48 couts exploitables en DUEL, et les bornes
actuelles ne segmentent pas ces lignes. Pas de nouveau coefficient
ROAD defendable sur ce panel.

## Impact moyen et garantie de neutralite entre les modes

Corriger brutalement le denominateur cout du RAIL
impliquerait une baisse de ROI theorique moyenne de 31,3 %
dans les 13 695 entrees RAIL journalisees au top-5 DUEL,
**si** le score etait strictement profit / capital.
Ce n'est PAS la variation reelle de fundScore : K_dec, C70,
le cout financable, la priorite C77 et les marges changent
ce calcul. Il serait injustifie de penaliser le RAIL seul.

Pour pre-evaluer une correction de classement **uniquement shadow**,
nous avons construit un facteur differentiel RAIL selon la
distance et impose une meme moyenne, ponderee par le score
de chaque entree du top-5 :

    rel_rail(d) = correction_cout_globale / correction_cout_distance(d)
    score_rail_nouveau = score_rail * 0.8 * rel_rail(d) / moyenne_ponderee(rel_rail)
    score_air_nouveau = score_air * 0.8
    score_flotte_air_nouveau = score_flotte_air * 0.8
    score_road_nouveau = score_road * 0.8

La correction RAIL relative est bornee a [0,75 ; 1,25]
avant normalisation. Il ne s'agit PAS de modifier les
profits, les devis, le budget ou la finance.

| Famille | Nombre d'entrees top-5 | Variation moyenne de score |
|---|---:|---:|
| AIR et flotte AIR | 6831 | −20 % |
| RAIL | 13695 | −20 % |
| ROAD | 377 | −20 % |

En version lineaire, les multiplicateurs individuels vont de
0,640 a 1,011 en RAIL ; AIR/flotte et ROAD gardent 0,800.
Sur 4848 instantanes top-5, 1919 exposent plusieurs familles ;
on trouve **221 changements possibles du leader numerique**,
dont 192 changements RAIL→RAIL et 29 intermodaux
(16 AIR→RAIL, 13 RAIL→AIR).
En version sous-bandes : 133 changements numeriques possibles,
111 RAIL→RAIL et 22 intermodaux.

Il ne s'agit PAS de 221 constructions differentes.
Le score numerique n'est pas le comparateur complet : classes
C77, bonus AIR, candidats absents du top-5 et economie
contrefactuelle empechent toute conclusion de profit A/B.
Une multiplication strictement uniforme de 0,8 des scores
de toutes les familles conserve leur ordre relatif dans
chaque classe de priorite et n'apporte seule aucune precision.

L'alternative recommandee pour ne **pas toucher du tout AIR** :
centrer seulement le facteur relatif RAIL sur moyenne 1,0,
laisser AIR, sa flotte et ROAD a 1,0. Sans seuils absolus,
le classement relatif serait le meme que l'essai −20 %
sur les trois familles. Mais aucun de ces mecanismes
ne doit etre active sur les seules donnees hors ligne.

## Decision

1. Garder AIR, les profits, C70 et la selection intermodale
   inchanges. Ne pas introduire de penalisation AIR seule.
2. Retenir en observation la pente de cout RAIL par distance :
   c'est moins cher en opcodes qu'une exploration geometrique
   et plus precis que les subdivisions sur le 256x256.
3. Ne pas confondre correction du **cout economique**,
   qui touche aussi la financabilite, et correction
   **score-only centree**, qui ne change que les preferences.
4. Avant tout essai actif : banque de graines hors panel,
   controle du cout en opcodes, puis banc A/B mesurant
   nombre de constructions, repartition modale,
   profit annuel et cout physique. Les bornes sont
   dependantes de l'epoque et de la carte.
