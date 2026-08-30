# Diagnostic : plafonnement d'OpexAI et tresorerie dormante

Mesure : [opexai_plafonnement_mesure.json](opexai_plafonnement_mesure.json), produite par
sweeps/opex_full_campaign.py sur 20 ans, graines 12345, 999, 100 et 4096, OpenTTD 15.3,
carte 256x256, depart 1970, inflation desactivee.

Cette campagne etablit des mecanismes, pas un gain de performance. Les panneaux ajoutes modifient
les ticks et peuvent donc modifier le chemin deterministe d'une graine ; ses valeurs finales ne
sont pas comparables chiffre a chiffre au banc. `docs/bench_v2.json` n'est plus
la reference de l'arbre ; l'arbre courant est
`docs/bench_double_track.json`. Aucun reglage de production n'a ete modifie.
Les totaux 1989 ci-dessous (dont 45,2 % `profit<=0`) sont un mecanisme d'alors ;
le 45,2 % est marque perime dans `docs/taches.md` item 7.

## Instrumentation ajoutee et methode

Ajouts :

- CG, CR, CD, CE et CK : compteurs de filtres avant TOP_K ;
- PC et PM : label cargo et mode d'une ligne reussie ;
- OB|A : opcodes reels de chaque tentative rail.

Le releve de ligne compte aussi le type de vehicule du mode, afin que les avions et bateaux aient un
revenu mesurable comme le rail. Les quatre graines se terminent sans erreur AI. Les chiffres de fin
viennent de runs[].yearly["1989"] et ceux des lignes de
runs[].lines[].actual_series["1989"] dans le JSON.

## Q1 — Pourquoi l'IA cesse-t-elle de construire avec du cash ?

**Reponse : le classement n'a presque plus de candidat constructible. Le cash n'est pas le frein
initial et la mesure ne montre pas de manque general de debit ; le vivier est vide par le profit
predit non positif, les origines deja desservies et MAX_DISTANCE, puis les rares survivants sont
souvent bloques par _tooClose.**

### Cause classee par contribution

Le tableau additionne les quatre pipelines de generation en 1989. Chaque paire est comptee une fois
au premier filtre qui la rejette, soit exactement 4 216 paires.

| Rang | Issue de la paire | Paires | Part | Interpretation |
|---:|---|---:|---:|---|
| 1 | profit annuel predit <= 0 | 1 905 | 45,2 % | le modele ne voit plus de transaction rentable |
| 2 | origine deja desservie | 1 188 | 28,2 % | surtout des origines industrielles raccordees |
| 3 | distance > 200 | 940 | 22,3 % | couples restants hors de la fenetre rail |
| 4 | MIN_RATIO = 500 | 114 | 2,7 % | filtre reel, mais minoritaire |
| 5 | distance < 25 | 28 | 0,7 % | effet negligeable |
| 6 | production mensuelle nulle | 9 | 0,2 % | effet negligeable |
| — | candidats encore acceptes | 32 | 0,8 % | 6, 19, 5 et 2 suivant la graine |

TOP_K n'en retire aucun en 1989 : tous les candidats acceptes sont sous 20 par graine. Le plafond
n'est donc pas une fenetre de 20 trop etroite, ni le plancher de ratio seul.

La carte n'est pas a court de villes : villes totales / non desservies vaut 43/37, 45/39, 39/39 et
45/38 (12345, 999, 100, 4096). Les industries non desservies restent 25/51, 25/52, 33/47 et 36/48.
L'epuisement est celui des paires economiquement admissibles, non des villes presentes.

Le verrou final est la proximite. Apres la derniere construction de 12345 (1986), les 4, 3 puis
6 candidats de 1987--1989 sont tous rejetes par _tooClose, dont 3--4 par le filet lointain. Pour
999, arretee en 1981, les 19 candidats de 1989 sont tous rejetes : 1 proche et 18 lointains.

**Regle de conception :** creer des opportunites nouvelles ou exploiter les origines deja rentables
(augmentation de capacite, branchement compatible, autre mode) avant de baisser des seuils. Ne pas
simplement baisser MIN_RATIO : il ne represente que 2,7 % des rejets de fin.

### Suspects secondaires

- **Tresorerie.** Les evenements GC cessent avant 1978 (12345), 1976 (999), 1983 (100) et 1981
  (4096). Ils ne causent donc pas les plafonds posterieurs. Le cash vaut 80,5--86,4 % de la valeur
  finale, soit 1,29--3,56 M : il est dormant, sans etre le frein initial.
- **Budget d'opcodes.** OS donne une utilisation cumulee des categories mesurees, pas une fraction
  annuelle. En fin de campagne : 25,2 %, 35,1 %, 6,7 % et 57,7 %. Cela ne suggere pas un manque
  general de debit, mais ne permet pas d'exclure une saturation ponctuelle dans une seule annee.
- **MAX_TRAINS = 8.** Cinq des 52 lignes rail touchent ce plafond. Elles portent 0 %, 10,6 %,
  18,7 % et 25,6 % du revenu rail selon la graine. Il borne des lignes longues mais pas le
  lancement d'une nouvelle ligne.
- **Vieillissement.** La stagnation de 999 date de 1981, onze ans apres le depart. Le seul retrait
  observe est la ligne 15 de 999, declaree morte en 1981, envoyee au depot en 1982 puis retiree
  en 1983 ; 12345 ne declare une ligne morte qu'en 1989. Cela ne soutient pas l'age comme cause du
  plafond de 1981. L'age individuel des trains n'est cependant pas conserve.

## Q2 — Quels cargos et quels modes transportons-nous ?

**Reponse : 52 lignes rail et 4 liaisons aeriennes reussissent ; aucun bateau ni bus. Les
compagnies ont 5, 6, 6 et 5 types de cargo a revenu positif en 1989, pas les huit requis de facon
certaine pour le bonus trimestriel.**

Le tableau agrege le revenu reel 1989 des quatre parties. C'est le revenu des vehicules des lignes,
et non le income_last_year de compagnie.

| Cargo | Lignes construites | Lignes a revenu positif | Revenu 1989 | Part |
|---|---:|---:|---:|---:|
| COAL | 17 rail | 17 | 554 539 | 37,4 % |
| PASS | 9 rail + 4 air | 13 | 382 235 | 25,8 % |
| IORE | 6 rail | 6 | 190 766 | 12,9 % |
| WOOD | 6 rail | 5 | 159 964 | 10,8 % |
| GRAI | 5 rail | 5 | 118 749 | 8,0 % |
| LVST | 2 rail | 2 | 52 529 | 3,5 % |
| VALU | 3 rail | 2 | 16 333 | 1,1 % |
| OIL_ | 4 rail | 1 | 7 875 | 0,5 % |

Le rail fait 1 201 883 (81,0 %) et l'air 281 107 (19,0 %) ; eau et route font zero. Les huit
labels apparaissent dans l'agregat, mais le score demande une diversite par compagnie et par
trimestre. Les panneaux prouvent le revenu annuel, pas le nombre exact de labels de chaque
trimestre : 5/6/6/5 est une borne annuelle, pas la mesure du bonus.

**Regle de conception :** la diversification est un effet de bord du fret, pas un objectif.
Instrumenter le transport trimestriel avant de viser le bonus.

## Q3 — Comment la rentabilite et la priorite sont-elles calculees ?

**Reponse : le candidat est classe par profit annuel predit / iterations A* predites, pas par
revenu brut. A vingt ans, le fret est calibre a 1,001 ; le revenu passagers est surestime de
22,2 % (1,222).**

1. Pour les passagers, le volume mensuel est la production de deux villes multipliee par
   TOWN_CATCHMENT_SHARE_PCT = 22 % ; pour le fret, la production de la source. Bornes 25--200 et
   origines servies sont appliquees avant le modele.
2. OpexLineEconomics applique vitesse effective 70 %, note supposee 50 % et frequence cible de
   sept jours. Le nombre de trains est le maximum du besoin de frequence et capacite, borne a 1--8.
   Le revenu est 12 * cargo transporte * AICargo.GetCargoIncome(...).
3. Le profit soustrait cout courant et amortissement du materiel et de l'infrastructure sur 30 ans.
4. OpexRailIterations(distance) estime le cout A* par interpolation. Le ratio
   profitAnnual * 1000 / iterations doit atteindre 500, puis OpexTopK conserve les 20 meilleurs.
   Le budget de construction compare la ligne au candidat suivant, ou a MIN_RATIO pour le dernier.

| Type | Lignes | Revenu predit | Revenu reel 1989 | Predit / reel |
|---|---:|---:|---:|---:|
| Passagers | 9 | 123 600 | 101 128 | 1,222 |
| Fret | 40 | 1 101 708 | 1 100 755 | 1,001 |

Le repere a dix ans de docs/opex_predict_vs_actual*.json est environ 1,18 (pax) et 0,98 (fret).
A vingt ans, le fret tient a l'incertitude de ce petit echantillon pres ; le pax reste optimiste.
Ce n'est pas une validation de changement de constante.

**Regle de conception :** garder le classement par rendement de calcul, mais recalibrer le pax
separement sur un banc appaire. Ne pas contaminer le fret, ici presque a l'equilibre en aggregate.

## Q4 — Combien de temps et d'opcodes coutent les constructions ?

**Reponse : 52 lignes sortent en 57 tentatives (1,10 tentative par ligne), mais les 5 abandons
absorbent 56,5 % des opcodes de toutes les tentatives rail et coutent 13,5 fois une reussite
moyenne.**

| Issue | Tentatives | Iterations totales | Iterations / tentative | Opcodes totaux | Opcodes / tentative |
|---|---:|---:|---:|---:|---:|
| Ligne reussie | 52 | 210 500 | 4 048 | 702 585 238 | 13 511 255 |
| Abandon ABND | 5 | 300 000 | 60 000 | 913 209 144 | 182 641 829 |

Le classement et OpexBuildLine sont dans le meme cycle annuel ; OR est pose apres construction,
donc aucune file d'attente inter-annuelle n'est mesuree. YT borne le delai classement--service par
le temps _tryBuild : sur 51 reussites dont la fin de cycle est ecrite, 69--38 765 ticks, mediane
768. La reussite 1989 de 100 n'a pas de YT final, le scenario s'arretant avant son ecriture ;
la latence individuelle exacte dans un cycle reste inconnue.

Les longues tentatives franchissent parfois le calendrier (999 : 1977--1980 ; 4096 : sept annees).
Rapports, rebut et emprunt sont rattrapes, mais aucun classement/construction historique n'est
rejoue : c'est un cout de cadence, distinct d'un manque d'opcodes.

**Regle de conception :** verifier en premier la politique d'abandon : un abandon au plafond de
60 000 iterations est tres cher. Toute modification doit passer par le banc appaire.

## Q5 — Le plancher de remboursement est-il defensible ?

**Reponse : 1 000 000 est une reserve trop large au vu des candidats mesures. A 5 %, conserver
300 000 d'emprunt coute 15 000 par an. Un plancher de 300 000 est une proposition coherente, pas
une constante validee.**

Le cout est une estimation mensuelle loan * 5 % / 12 pour les mois ou le cash est <= 1 000 000.

| Graine | Mois sous le plancher | Mois a 300 000 | Interets estimes |
|---:|---:|---:|---:|
| 12345 | 132 | 131 | 164 167 |
| 999 | 127 | 126 | 157 917 |
| 100 | 205 | 204 | 255 417 |
| 4096 | 172 | 171 | 214 167 |

Les candidats reels bloques par cash demandaient au maximum 246 831. CASH_RESERVE = 50 000 plus
cette borne donne 296 831 : un plancher de **300 000** laisserait la reserve et couvrirait le
plus gros candidat bloque observe, sans conserver un million improductif. Cette proposition est
non validee : une autre carte peut proposer plus cher et le calendrier est non lineaire.

Le changement, s'il est retenu, doit etre une variante explicite de LOAN_REPAY_FLOOR evaluee par
sweeps/bench_v2.py sur 20 graines appairees. Cette enquete ne modifie pas la constante.

## Ce qui reste non tranche

- OS est cumulatif : pas de fraction exacte consommee dans la seule derniere annee.
- Les revenus annuels ne comptent pas les huit labels exacts de chaque trimestre.
- DL explique les retraits volontaires observables, mais aucune distribution d'age par vehicule
  n'est conservee.
- Ces quatre graines expliquent l'arret de construction ; elles ne quantifient ni un gain de
  correction, ni sa robustesse inter-graines.
