# Caisse 1970–1972 et leviers pour réduire l'écart avec AAAHogEx

Date : **2026-09-24**. Branche de travail : `v93-demand-residual`.

Cette fiche part du constat du duel de référence : l'écart avec AAAHogEx se
forme très tôt, OpexAI conserve encore de la trésorerie et de l'emprunt, puis
son réseau AIR cesse presque de s'étendre tandis qu'AAAHogEx ajoute du rail
fret et des lignes aériennes de courrier seul.

Le premier objectif est étroit : **expliquer la caisse non investie entre 1970
et 1972 avant de changer une règle de décision**. La seconde partie ordonne les
autres leviers à partir des preuves déjà acquises.

## 1. Instrumentation passive de la caisse

Le réglage existant `probe_portfolio=1` active déjà C49/C50/C63, la sonde de
réserve et l'entonnoir. Le diagnostic ajoute seulement des panneaux `SIGN`,
lisibles depuis la sauvegarde sans dépendre de `-d script=4` :

- `UC` : caisse, emprunt, réserve ;
- `UP` : capital disponible, capital du projet en tête, mode du projet ;
- `UR` : recherche rail active et capital du candidat ;
- `US` : causes C49 `cash/site/decision/none` ;
- `UT` : raison qui arrête la continuation C75 après un chantier :
  `k_pass/cash/rail_search/list_end/other` ;
- `UB` : passages `projects`, nombre de chantiers et passages multi-build.

`sweeps/diag_unused_cash_1970_1972.py` exécute OpexAI seul et lit ces panneaux
depuis le dernier save. Les sondes ne changent aucune branche de décision, mais
elles consomment des opcodes : comme les diagnostics C49/C69 antérieurs, **les
valeurs économiques absolues ne sont pas un banc causal**. Les causes observées
à l'intérieur d'une même partie restent la lecture utile.

## 2. Banc solo court

Configuration : graines `42 100 999 1234 5678`, départ 1970, quatre années
pour disposer du rapport qui ferme 1972, trois workers. Artifact principal :
`results/diag_unused_cash_final_1970_1972_5x4_20260925.json`.

### 2.1 Trésorerie aux rapports

Moyenne des cinq graines :

| rapport | caisse | emprunt | réserve | capital disponible | projet de tête | tête finançable |
|---|---:|---:|---:|---:|---:|---:|
| 1970 | 300 k£ | 300 k£ | 5 k£ | 295 k£ | 124 k£ | 5/5 |
| 1971 | 149 k£ | 300 k£ | 12 k£ | 137 k£ | 60 k£ | 5/5 |
| 1972 | 404 k£ | 168 k£ | 24 k£ | 380 k£ | 89 k£ | 5/5 |
| 1973 | 748 k£ | 0 k£ | 25 k£ | 723 k£ | 107 k£ | 5/5 |

La réserve de fonctionnement vaut donc seulement **5–25 k£**, très loin des
centaines de milliers de livres visibles en caisse. Aux quatre snapshots, le
projet classé en tête est finançable sur les cinq graines.

La recherche rail n'est active sur **aucune des cinq graines** aux snapshots
1970–1972. Cela ne prouve pas qu'aucun A* ne tourne entre deux rapports : les
compteurs de sortie montrent justement des blocages rail épisodiques en 1972.
Elle n'explique toutefois pas la caisse qui dort dès 1970–1971.

### 2.2 Ce qui arrête réellement le chantier suivant

`US`, `UT` et `UB` sont lus **avant** la remise à zéro annuelle et le parseur
les rattache à l'année close (`report 1971` → activité 1970). Le run final ne
contient plus la seconde émission C75 qui brouillait les premiers essais.

| période close | passes `projects` | chantiers | multi-build | `k_pass` | cash | rail search | fin de liste |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1970 | 289 | 47 | 0 | **42** | 0 | 1 | 5 |
| 1971 | 55 | 50 | 3 | **40** | 2 | 0 | 0 |
| 1972 | 25 | 79 | 11 | **12** | 9 | 7 | 0 |

Le registre C49 complète cette lecture. En 1970, **220/289 passes** se terminent
sans prochain projet (`none`) : le premier verrou est donc aussi l'**offre**.
En 1971, `none` tombe à 11 et `decision` monte à 24 : presque chaque passage a
quelque chose à faire, mais la continuation est coupée par `k_pass`. En 1972,
`none=0`, `decision=19`, tandis que les passages deviennent deux fois plus rares
et construisent davantage en lot ; cash et A* rail commencent alors à mordre.

Le mécanisme est net : après le premier chantier d'une passe,
`task_projects.nut` continue seulement si le projet suivant satisfait à la fois
`capital < K_pass` et `capital <= available`. Or

`K_pass = cash-flow d'exploitation × durée moyenne entre deux passages projects`.

En 1970, l'absence d'offre domine les passes vides ; lorsqu'un chantier existe,
`k_pass` coupe presque toujours la continuation. En 1971, le problème devient
nettement **débit de décision + `k_pass`** : seulement 11 passages `projects`
par partie en moyenne, projet de tête finançable 5/5 au snapshot, 40 arrêts
`k_pass` contre 2 cash. Ce n'est donc pas une réserve implicite pour un projet
rail. En 1972, C75 construit déjà en lot (79 chantiers pour 25 passes) et le
cash/A* rail deviennent de vrais verrous *pendant* certaines passes, sans
expliquer la sous-utilisation précoce de 1970–1971.

## 3. Conséquence : ne pas supprimer C75, tester un bypass « nouvelle source »

Le précédent C75 interdit une conclusion simpliste. C75 seul avait ajouté
**+42 véhicules (+45 %)** au 20×10 pour seulement **+23 k£/an**, 10/10 :
construire tout ce qui tient en caisse ajoute surtout de la capacité marginale
de faible valeur. C75 n'a été conservé que dans la pile C69 bis/C70 où profit,
valeur et volume montaient ensemble.

Le test causal suivant doit donc être plus étroit :

1. conserver `K_pass` pour `mode == fleet` ;
2. autoriser **au plus un bypass supplémentaire par passe** pour un projet qui
   ouvre une nouvelle ligne (`air`, `rail`, éventuellement `road/water`) lorsque
   son capital est réellement disponible, même s'il dépasse `K_pass` ;
3. ne pas réserver d'argent à un A* rail simplement parce qu'il existe dans le
   vivier ; une recherche rail effectivement en vol garde ses règles actuelles ;
4. gate expérimental défaut 0, puis smoke et 5×6 causal contre le défaut.

Cette variante attaque exactement les arrêts `k_pass` observés en 1970–71 sans
rouvrir le comportement « acheter encore des avions sur les mêmes lignes » que
le C75 brut avait montré peu rentable.

## 4. Vivier AIR après 1973

Le problème n'est **pas** que les villes sous 600 habitants soient absentes du
catalogue : sur la carte 256², le pool AIR couvre environ 43 villes, donc
pratiquement toute la carte. Le verrou est le filtre explicite des grands
aéroports sous 600 habitants et, ensuite, la disponibilité d'un site.

L'ablation V93 qui retire simplement le plancher a déjà répondu à la question :
elle ouvre beaucoup plus d'aéroports (**33 contre 24** au 5×6), mais ne donne
que **+33 k£/an** et détruit **≈15 % de valeur**. Le problème est donc la
**qualité des nouveaux sites/lignes**, pas seulement leur nombre.

La tentative de remplacer le proxy de demande par la production réelle n'a pas
réparé cela : V93.1 perd −421,5 k£/an au 20×10 ; V93.2 simplifié perd encore
−203,9 k£/an au 5×6. Il ne faut pas combiner ces modèles avec une nouvelle
ouverture du plancher.

En revanche, C83.1 montre qu'un **second créneau très ciblé** peut payer : avec
seulement six grandes villes surveillées, +165,3 k£/an, 15/5 et +6,78 % de
valeur au 20×10. L'extension à 24 villes diluait le bénéfice.

Suite la plus propre : ne pas « ouvrir toutes les petites villes ». Ajouter
d'abord une **sonde site-production** qui mesure la production PASS/MAIL
réellement couverte par les sites `<600` et les seconds sites possibles, tout
en laissant l'ancien modèle économique décider. Le premier levier à tester
ensuite est un candidat dédié seulement si le site a une production réelle
suffisante ; le seuil doit être fixé à partir de l'exposition, pas inventé.

## 5. Rail fret : plus gros gisement absolu

La télémétrie C87 reste le plus grand différentiel structurel : environ
**570 k£/an de rail fret chez AAAHogEx contre 15 k£ chez OpexAI** au 5×6 ; le
témoin C83 20×10 confirme ≈32 % du profit AAA en rail et seulement ~0,5 train
chez OpexAI.

Deux verrous distincts sont déjà identifiés :

- **mise en service** : une recherche A* reprenable peut monopoliser
  `_railSearch` et bloquer les autres candidats ; V89 est déjà implémenté pour
  utiliser le slack d'opcodes et augmenter le débit calendaire ;
- **offre** : les chaînes goods sont structurellement absentes du générateur
  historique. V88 est déjà implémenté pour valoriser conjointement intrant →
  usine puis goods → ville, avec quai joint et construction en deux étapes.

Depuis les premières mesures V89, le défaut a changé : V90 est actif et V91
poids 120 réduit le nombre d'itérations de recherche d'environ ×5. Il faut donc
**remeasurer V89 sur le défaut courant** avant un duel long. Un diagnostic
3 graines × 6 ans suffit : itérations/an, jours de recherche, délai jusqu'à
commission et nombre de lignes rail. Si les recherches restent étalées sur des
mois/années, V89 mérite un 5×6 causal ; sinon V91 a déjà absorbé l'essentiel du
problème.

V88 vient ensuite : smoke 1×1 jusqu'à une livraison `GOOD > 0`, puis 5×6. Il
ne faut pas mélanger V88 et V89 dans le premier test : l'un **crée des projets
rentables**, l'autre **accélère leur cheminement**.

Les trains mixtes céréales+bétail d'AAAHogEx sont une troisième étape. OpexAI
reste mono-cargo ; avant de généraliser les compositions, il faut déjà savoir
si V88 produit et met en service les deux tronçons de chaîne.

## 6. Lignes aériennes courrier seul

Le support bas niveau existe partiellement : le catalogue découvre le cargo
MAIL, OpexAI connaît sa capacité dans les avions déjà construits et le modèle
PASS ajoute actuellement un revenu MAIL auxiliaire. Mais le chemin de
construction AIR est explicitement passager :

- `OpexAirPlans` génère une demande `monthlyPax` ;
- `OpexAirEconomics` dimensionne sur la capacité passagers ;
- `OpexBuildAirRoute` construit/refit systématiquement le premier avion vers
  `catalog.paxCargo` ;
- les clones de secours sont eux aussi refittés PASS.

Il n'existe donc **aucun projet AIR MAIL-only** à élire aujourd'hui. Ce n'est
pas un simple changement de coefficient.

Le prototype minimal doit éviter de mélanger ce chantier avec la géométrie des
aéroports : générer d'abord des lignes MAIL-only **entre aéroports Opex déjà
existants**, avec production MAIL réelle des bassins, avion refitté MAIL et les
mêmes deux ordres. Cela teste la source de revenu supplémentaire sans consommer
de nouveaux créneaux. AAAHogEx en tire environ **267 k£/an**, 4,8 lignes et 10
avions au 5×6, soit ≈26,7 k£/avion : assez pour justifier un prototype isolé,
mais moins prioritaire que le fret rail.

## 7. Ordre expérimental proposé

1. **C75 nouvelle-ligne / cash** : petit levier directement issu du diagnostic
   1970–71 ; smoke puis 5×6 causal.
2. **V89 sur le défaut V91=120 courant** : diagnostic 3×6 seulement ; duel si
   le délai A* reste réellement exposé.
3. **V88 goods** : smoke avec biens livrés puis 5×6 causal.
4. **AIR post-1973** : sonde de production des sites `<600`/seconds slots,
   puis filtre ciblé ; ne pas réactiver V93 globalement.
5. **MAIL-only sur aéroports existants** : prototype isolé, puis 5×6 avec
   télémétrie par cargo.

Cette séquence traite d'abord le capital qui dort pendant la fenêtre où l'écart
se forme, puis le plus gros gisement absent (rail fret), avant d'élargir de
nouveau le réseau AIR.
