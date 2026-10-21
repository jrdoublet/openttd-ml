# Variables predictives du ROI : enquete sur les 40x10 (21 octobre 2026)

Source : journaux des 40 parties solo et 40 parties duel de
calib_solo_40x10_pc_20261021 / calib_duel_40x10_pc_20261021.
Recalcul : sweeps/analyse_roi_predictors_20261021.py.
Sorties :

- results/calibration_pc_20261021/results/roi_predictors_20261021.json
- results/calibration_pc_20261021/results/roi_predictors_20261021.md

## Question : le modele ecrase-t-il les extremes ?

Ne pas confondre deux regressions conditionnelles :

1. **Par quartile du ROI realise** : une prediction moyennisante a tendance
   a surestimer les faibles et sous-estimer les forts ; l'effet apparait
   meme sous bruit de mesure et ne prouve pas qu'une nouvelle variable
   soit predictive au moment du choix.
2. **Par quartile du ROI prevu** : test plus utile pour classer les investissements.
   Les vrais revenus/couts des lignes construites permettent de mesurer
   le biais conditionnellement a ce que le catalogue savait alors.

Une ligne agee d'au moins deux ans fournit une observation par ligne,
profit annualise median de ses mesures age >= 2, normalise a la flotte
initiale. Le ROI realise est ce profit / capital * 100 :
capital reel de RAIL_BUILD / ROAD_BUILD lorsque strictement positif,
devis de AIR_BUILD pour AIR (donc **ROI AIR approximatif**).
Le ROI prevu est le profit de PROJECT_CHOSEN / capital de PROJECT_CHOSEN
* 100, et non le champ de classement "roi" qui peut avoir une autre echelle.
Il s'agit de **lignes construites** et mures : on ignore les projets
refuses ou non construits (biais de selection).

## Evidence de l'asymetrie sur le profit

Quartiles de ROI *realise*, 958 lignes RAIL matures en duel :

| Quartile de ROI reel | ROI prevu median | ROI reel median | Profit reel / prevu median |
|---|---:|---:|---:|
| Q1 faible | 31,05 % | 12,89 % | 0,671 |
| Q2 | 49,42 % | 28,61 % | 0,905 |
| Q3 | 61,12 % | 42,88 % | 1,077 |
| Q4 eleve | 82,44 % | 64,78 % | 1,109 |

Les profits faibles sont surestimes, les forts sous-estimes.
**Mais le ROI capitalise n'est PAS sous-estime dans le Q4** :
le devis de construction RAIL sous-estime le capital physique,
ce qui masque le gain de profit. Ne jamais fusionner les deux biais.

Quartiles du ROI *prevu*, sur les memes 958 lignes :

| Quartile du ROI prevu | ROI prevu median | ROI reel median | Profit reel / prevu median |
|---|---:|---:|---:|
| Q1 | 28,44 % | 15,34 % | 1,031 |
| Q2 | 48,49 % | 31,58 % | 1,049 |
| Q3 | 64,46 % | 42,62 % | 0,996 |
| Q4 | 93,38 % | 58,08 % | 0,836 |

Cela dit que, dans l'univers des lignes selectionnees, une grande partie
du classement RAIL est preservee mais les predictions de ROI tres haut
ne sont pas toujours fiables ; la capitalisation vraie compte.

AIR, 1 892 lignes et capital de devis seulement :
par Q1/Q2/Q3/Q4 de ROI prevu, ROI prevu median =
37,30/116,79/191,03/276,80 %, ROI mesure sur devis =
20,19/26,66/38,28/64,52 %. Le tri fonctionne grossierement,
mais les niveaux de profit sont tres surestimes.

## Test des variables observables avant decision

Une regression ridge simple, sur les 40 graines DUEL seulement, avec
**5 plis par graines distinctes** et aucun reeentrainement sur une
graine de test. Les gains s'entendent par rapport a un ROI seul avec
terme quadratique, lui-meme calibre sur les autres graines.

| Correction | AIR MAE ROI (points) | RAIL MAE ROI (points) |
|---|---:|---:|
| Aucun recalibrage (brut) | 119,34 | 25,12 |
| Facteur global appris sur train | 15,50 | 14,02 |
| ROI seul affine | 14,93 | 14,16 |
| ROI seul quadratique | 14,47 | 13,40 |
| + distance et interaction ROI × distance | 14,52 | 13,32 |
| + cargo et interaction ROI × cargo | n/a (AIR PASS seul) | **12,55** |
| + capital prevu et interaction | **14,10** | 13,24 |
| + annee et interaction | 14,41 | 13,39 |
| + rang dans la liste | 14,48 | 13,49 |
| + sous-type de projet / reutilisation | **13,78** | 13,47 |
| Toutes variables | 13,88 | **12,48** |

Bootstraps a 1 500 tirages de graines, gain de MAE moyen **par graine**
contre ROI seul quadratique (positif = mieux), IC95 exploratoires :

| Variable ajoutée | Gain moyen (points) | IC95 | Graines favorables |
|---|---:|---:|---:|
| AIR type de projet (newpair/hubsite/hubhub) | +0,72 | [+0,51 ; +0,94] | 33/40 |
| AIR capital prevu | +0,40 | [+0,21 ; +0,60] | 33/40 |
| AIR distance | −0,05 | [−0,10 ; 0,00] | 16/40 |
| RAIL cargo | +0,79 | [+0,35 ; +1,21] | 32/40 |
| RAIL capital prevu | +0,14 | [+0,03 ; +0,25] | 30/40 |
| RAIL distance | +0,07 | [−0,11 ; +0,25] | 23/40 |
| RAIL annee | −0,01 | [−0,23 ; +0,19] | 20/40 |
| RAIL rang | −0,08 | [−0,19 ; +0,02] | 15/40 |

Ces intervalles quantifient la variabilite entre graines des corrections
choisies sur ce meme panel. Il faut une confirmation sur graines
independantes, non utilisees pour choisir le modele.

### Capacite de trier les projets (rho de rang median intra-graine)

- AIR : ROI seul **0,706** ; ROI + capital **0,750** ;
  ROI + type de projet **0,740**.
- RAIL : ROI seul **0,711** ; ROI + cargo **0,747** ;
  toutes variables **0,744**.

Ce score est calcule sur les seules lignes construites et suivies :
il ne dit pas comment se classeraient les milliers de candidats non choisis.

ROAD : 48 lignes dans seulement 29 graines ; on voit une separation
PAX/fret mais l'echantillon est trop faible pour choisir un ensemble de
coefficients. Le modele toutes variables surajuste fortement.

## Variables candidates a instrumenter *au moment du choix*

Les donnees historiques ne journalisent pas encore assez de mecanismes
pour identifier le meilleur predicteur de demande / capacite.
Proposer une **sonde shadow uniquement**, avec le meme identifiant
stable de candidat dans catalogue → selection → constructor → ligne :

1. **AIR : risque de demande / hub**. Mensuels PASS/MAIL attendus par
   extremite, activite deja transportee, couverture de chaque station,
   offre concurrente connue, nouveaux aeroports contre reuse, type
   d'aeroport, saturation de piste, delais prevus vs effectifs.
   Les fonctions OpexC121PrepareEngineStatic / OpexAirEconomics calculent
   deja plusieurs termes (existingPaxBeforeA/B, rating, carried,
   monthlyCapacity, tripDays, service runway) qui peuvent etre exposes
   dans un log sans modifier la politique.
2. **RAIL fret : production captable et goulets**. Production recente
   a la source et part deja transportee, attente et rating a la gare,
   capacite initiale prevue (wagons, charge utile, vitesse, rotation),
   demande/acceptation a destination, ligne nouvelle ou partagee.
   Il faut capter les valeurs **avant la decision** ; task_report.nut
   expose parfois ces quantites apres construction, ce qui ne suffit pas.
3. **RAIL capital : difficultes de chantier**. Devis geometrie,
   relief, obstacle, boucle detour, longueur effective/devis Manhattan,
   reutilisation d'infrastructure, gares/raccordements et ecart entre
   cout prevu / cout reel. RAIL_ATTEMPT enregistre deja pre/model/quote/
   actual et longueur mais intervient plus tard : ne pas utiliser ce
   dernier cout comme predicteur disponible au catalogue.
4. **Horizon et opportunite**. Distinguer profit mature, cout physique,
   delai de mise en service, flotte designee et opportunite perdue par
   immobilisation du capital. Verifier le classement sur la fenetre
   2–5 ans, et non seulement une mediane annuel selectionnee a posteriori.

### Protocole propose

1. Coupler identifiants immuables projet → tentative → ligne et journaliser
   toutes les features shadow connues au classement (y compris rejets).
2. Sur de nouvelles graines disjointes : cross-validation groupee par
   graine, MAE en ROI, calibration par decile de ROI **prevu**,
   et corrélation de rang *dans chaque tour de catalogue* si des labels
   contrefactuels sont disponibles. Seuls les projets construits ont
   normalement une verite terrain.
3. Ablation par groupe de variables (demande, capacité, capital, reseau,
   temps, contexte) conditionnellement au ROI de depart.
4. Promouvoir une modification de classement uniquement apres un banc
   economique A/B aux memes graines montrant un gain de profit annuel,
   et non seulement un bon ajustement statistique.

**Aucun changement de politique ni nouveau banc OpenTTD dans cette analyse.**
