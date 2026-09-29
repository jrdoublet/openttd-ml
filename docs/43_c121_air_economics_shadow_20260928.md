# C121 — modèle AIR physique unifié : shadow multi-seed

Date : 2026-09-28.

## Verdict courant — 2026-09-29

C121 est maintenant **causal et stabilisé**, mais ne remplace pas encore C115.
Le cold start moteur reste **PASS-only puis PASS+MAIL exact après observation** ;
le scan moteur a été ramené d'environ 10–14 M à ~0,6–0,8 M opcodes sur les gros
cycles. L'objectif de qualification est désormais le rattrapage AAAHogEx sous
contrainte de valeur et de territoire.

Le classifieur passif C83 `race/efficiency` est prometteur, mais les variantes
actives restent non qualifiées : adaptatif 50 % = gap AAA **+651,8 k£/an** mais
valeur **-8,32 %** ; adaptatif soft25 = gap **+451,5 k£/an**, valeur **-3,32 %**
mais territorial légèrement pire (**+1,8 ville AAA 2-0**) ; soft25 + floor
défensif seulement en `efficiency` = gap **+578,8 k£/an** mais valeur
**-11,27 %**, `profit_year` **-200,8 k£/an** et **+2,0 monopoles AAA 2-0**.
Tous ces leviers restent **OFF par défaut** ; C115 reste le témoin ; **pas de
20×10 C121**. La prochaine piste doit agir sur la priorité d'expansion par régime
plutôt que réduire encore la valeur économique des projets.

Campagne :

- `results/c121_air_economics_stationcomp_covcache_5x6_20260928.json` ;
- résumé : `results/c121_air_economics_stationcomp_covcache_5x6_20260928_summary.json` ;
- timing : `results/c121_air_economics_stationcomp_covcache_5x6_20260928_timing.json` ;
- fenêtres d'âge : `results/c121_air_economics_stationcomp_covcache_5x6_20260928_age_windows.json`.

Santé : **5/5 runs OK**, seeds `42 100 999 1234 5678`, 6 ans,
**529 builds C121**, **458 lignes matures** appariées.

Le point principal est double :

1. le rating, le revenu et la flotte sont désormais globalement plausibles ;
2. les ratios matures mélangent la qualité du modèle au build avec une forte
   **dérive du réseau après construction**. Une ligne initialement isolée peut
   devenir un hub partagé par plusieurs lignes, ce qui change ensuite sa part de
   production et son temps de parcours. Il ne faut donc surtout pas fitter une
   constante sur `actual/pred` mature.

## 1. Ratios matures 5×6

| Ratio actual / predicted | moyenne | médiane | p25 | p75 |
|---|---:|---:|---:|---:|
| PASS | 0,791 | **0,656** | 0,416 | 1,001 |
| MAIL | 1,258 | **1,013** | 0,696 | 1,601 |
| total cargo | 0,860 | **0,747** | 0,485 | 1,066 |
| revenu | 1,025 | **0,912** | 0,627 | 1,266 |
| profit modèle-like | 1,256 | **0,864** | 0,536 | 1,332 |
| rating | 1,017 | **0,941** | 0,873 | 1,094 |
| headway | 1,373 | **1,196** | 0,815 | 1,518 |
| leg days | 1,697 | **1,537** | 1,348 | 1,823 |
| flotte décision | 1,039 | **1,000** | 0,547 | 1,000 |
| capacity-share PASS | 0,710 | **0,567** | 0,344 | 0,906 |
| capacity-share MAIL | 1,044 | **0,873** | 0,564 | 1,359 |
| capacity-share total | 0,763 | **0,630** | 0,391 | 0,962 |
| capacity-share revenu | 0,906 | **0,769** | 0,494 | 1,203 |
| payment yield C121 | 1,234 | **1,168** | 1,017 | 1,334 |

Médianes par seed :

| seed | PASS | MAIL | total | revenu | profit | rating | headway | leg | flotte | cap PASS | cap MAIL | cap total | cap rev | yield |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 42 | 0,674 | 1,113 | 0,761 | 0,900 | 0,857 | 0,947 | 1,257 | 1,553 | 1,000 | 0,561 | 0,958 | 0,649 | 0,763 | 1,185 |
| 100 | 0,706 | 1,147 | 0,804 | 0,887 | 0,812 | 0,957 | 1,016 | 1,387 | 1,000 | 0,629 | 0,964 | 0,704 | 0,752 | 1,015 |
| 999 | 0,612 | 0,989 | 0,760 | 0,934 | 0,922 | 0,932 | 1,209 | 1,443 | 1,000 | 0,578 | 0,811 | 0,615 | 0,794 | 1,189 |
| 1234 | 0,720 | 1,252 | 0,819 | 0,990 | 0,944 | 0,932 | 1,128 | 1,568 | 1,000 | 0,574 | 1,005 | 0,627 | 0,796 | 1,193 |
| 5678 | 0,568 | 0,849 | 0,579 | 0,853 | 0,815 | 0,942 | 1,370 | 1,777 | 1,000 | 0,453 | 0,643 | 0,514 | 0,744 | 1,293 |

Le signal est donc multi-seed : PASS est systématiquement sur-prédit, MAIL est
beaucoup plus proche de 1, et le yield réel est systématiquement supérieur au
yield C121. Ces deux erreurs opposées compensent partiellement le revenu.

## 2. Coût opcode

Sur les 529 builds :

- `demand_ticks` : moyenne **4,59**, médiane **5**, p25/p75 **4/5** ;
- `demand_ops_same_tick` : moyenne **50,98 k**, médiane **51,25 k** ;
- `eval_ticks` : moyenne **0,021**, médiane **0** ;
- `eval_ops_same_tick` : moyenne **3,24 k**, médiane **3,27 k**.

Les étapes B9 restent dominées par l'union de catchment : environ 0,70/0,98 tick
PASS A/B et 0,90/0,85 tick MAIL A/B en moyenne. Le coût multi-seed est un peu
plus élevé que le smoke seed42 (~3,84 ticks/build, médiane 2), mais reste très
loin du snapshot global rejeté (~112 ticks/build). Ne pas réintroduire ce
snapshot de ratings/concurrence.

## 3. Temps de trajet : le biais n'est pas une constante de vitesse

Le diagnostic timetable compte **1 284** observations, toutes sur City Airport
`AT_LARGE` :

- vol physique corrigé : médiane **20,48 j** ;
- `ORDL.travel_time` : médiane **43,0 j** ;
- résidu `travel - flight` : médiane **21,57 j** ;
- `travel / flight` : médiane **2,075×** ;
- OLS descriptive : `travel ~= 21,12 j + 1,271 × flight`.

Dans le shadow mature :

- `timetable_travel / pred_oneway` : médiane **1,196×** ;
- `(travel-flight) / pred_maneuver` : **1,450×** ;
- `(travel+wait) / pred_oneway` : **1,256×** ;
- `C117 leg / timetable cycle` : **1,234×**.

Mais ce dernier ratio ne doit pas être transformé en coefficient C121. C117
échantillonne l'ordre courant tous les **2 jours** et mesure d'un changement
d'ordre au suivant. Le timetable final est une photo du savegame final ; C117
agrège la vie de la ligne. Surtout, le réseau évolue fortement entre les deux.

Les fenêtres d'âge le montrent :

| âge ligne | total actual/pred | revenu | leg | headway | rating | flotte |
|---|---:|---:|---:|---:|---:|---:|
| mois 1–3 | 0,567 | 0,650 | **0,928** | 0,804 | 0,889 | 1,000 |
| mois 4–6 | 0,623 | 0,863 | **1,235** | 1,101 | 0,938 | 1,000 |
| mois 7+ | 0,747 | 0,912 | **1,537** | 1,196 | 0,941 | 1,000 |

Le trajet de base n'est donc pas uniformément 54 % trop court : l'écart apparaît
avec l'âge et la charge du hub. La piste physique prioritaire est la congestion /
FTA / attente créée par les autres lignes, pas un multiplicateur arbitraire de
`flightDays`.

## 4. Le shadow mature est longitudinalement confondu

La croissance du degré des deux endpoints est très fortement associée au biais :

| croissance endpoint max | lignes | total actual/pred médian | revenu médian |
|---|---:|---:|---:|
| 0 | 5 | **1,124** | **1,536** |
| 1 | 14 | **0,922** | **1,199** |
| 2+ | 439 | **0,726** | **0,899** |

Le cas `newpair` est le plus parlant. Aux mois 4–6 il atteint un revenu
actual/pred médian **1,024** et un total **0,864** ; à 7+ mois ils tombent à
**0,445** et **0,377**, alors que le rating monte à **1,460×** et la flotte à
**1,276×**. C'est cohérent avec une ligne initialement seule dont les stations
deviennent ensuite des hubs et dont la production est répartie entre davantage
de services. Le modèle de concurrence peut être exact au build tout en donnant
un mauvais ratio plusieurs années plus tard si on garde la prédiction initiale.

Le code C121 confirme en parallèle une limite physique réelle pour les hubs déjà
existants : `OpexC121ExistingStationService` reconstruit leur cadence à partir de
`distance / vitesse + OpexC100AirManeuverDays`, donc d'un cycle sans congestion
observée. La limitation piste courante conserve le débit par un `runwayScale`,
mais n'ajoute pas le temps d'attente/holding sous saturation partielle. Ce point
doit être étudié avec une source physique ou une mesure d'état, pas calibré sur
les résultats économiques du 5×6.

## 5. Matérialité pour les décisions

Le replay avec le **cycle timetable mesuré**, à flotte fixée, déplace :

- total cargo actual/pred : **0,747 → 0,801** médian ;
- revenu actual/pred : **0,912 → 1,008** médian.

Le temps de cycle a donc un impact matériel sur la prédiction de revenu et, par
conséquence, sur le profit et le score économique du projet. En revanche la
flotte est beaucoup plus robuste : `actual / decision_fleet` reste **1,00** en
médiane, y compris sous replay timetable ; la distribution change néanmoins sur
une fraction des lignes (`p25=0,5` sous replay timetable), donc ce n'est pas un
invariant absolu.

L'impact sur le **choix moteur** n'est pas encore identifiable proprement : le
5×6 ne mesure le timetable que du moteur réellement construit. Appliquer le
résidu du moteur construit à tous les moteurs concurrents recréerait une
calibration empirique. Il faut d'abord un modèle de congestion aéroport
source/state-based commun aux moteurs, puis rejouer le classement moteur.

## 6. Adaptation en ligne du délai de hub

Le diagnostic suivant abandonne la recherche d'une formule statique parfaite de
congestion et conserve le modèle physique uniquement comme **cold start**. C117
observe déjà les changements d'ordre des avions toutes les 2 journées. Lorsqu'un
leg se termine vers une station, C121 calcule :

`résidu = leg observé - one-way physique du moteur`.

Le résidu reste **signé** pendant l'accumulation afin de ne pas biaiser la
quantification C117. Par station, une fenêtre récente de **91 jours** est publiée
si elle contient au moins **2 observations** ; l'estimation publiée est ensuite
bornée à `>= 0` car elle représente un délai additionnel. Aucun alpha EWMA ni
coefficient empirique n'est calibré sur le 5×6. Pour un candidat :

`roundTrip = 2 * physicalOneWay(engine) + hubDelay(A) + hubDelay(B)`.

Le terme de hub est donc identique pour tous les moteurs et la lecture lors du
scoring est O(1) par endpoint. Un nouvel aéroport sans historique reste sur le
modèle physique.

### 6.0 Principe à retenir : cold start exact, puis moyenne glissante observée

Cette expérimentation fixe une règle d'architecture à réutiliser au-delà de C121
quand un bon estimateur statique devient trop coûteux en opcodes :

1. calculer **une fois** au démarrage / à la création l'estimation physique ou
   exacte la plus défendable disponible ;
2. conserver cette valeur comme **cold start** tant qu'il n'existe pas assez de
   mesures réelles ;
3. dès que les observations existent, ne plus recalculer toute la physique à
   chaque décision : mettre à jour un état compact par **moyenne glissante sur une
   fenêtre récente** ;
4. lire ensuite cet état en O(1) dans le scoring, et ne recalculer l'estimation
   initiale que lors d'un changement structurel qui l'invalide réellement.

Le point important n'est pas la durée de 91 jours en elle-même : c'est le motif
**« calcul initial coûteux + apprentissage incrémental bon marché »**. Il évite à
la fois les coefficients empiriques globaux et les recalculs NoAI lourds. Une
revue de code ultérieure doit chercher les autres estimateurs coûteux ou fragiles
où ce motif peut remplacer des scans répétés ou des formules statiques difficiles
à calibrer.

Campagne finale batchée :

- `results/c121_hubdelay_batch_5x6_20260928.json` ;
- résumé : `results/c121_hubdelay_batch_5x6_20260928_summary.json` ;
- âge : `results/c121_hubdelay_batch_5x6_20260928_age_windows.json` ;
- diagnostic/replay même moteur :
  `results/c121_hubdelay_batch_5x6_20260928_hub_delay.json`.

Santé : **5/5 runs OK**, **534 builds**, **466 lignes matures**, **1 655**
publications de délai sur 169 couples seed/station. La fenêtre publiée contient
**5 observations** en médiane ; délai médian **14,01 j**, p25/p75
**4,94/25,82 j** et 86,5 % des publications sont positives. Au build,
**71,2 %** des projets disposent déjà d'un historique sur au moins un endpoint
et **34,5 %** sur les deux.

### 6.1 Timing : dérive largement supprimée en adaptation live

| âge ligne | leg / prédiction au build | leg / prédiction live adaptée |
|---|---:|---:|
| mois 1–3 | 0,840 | **0,805** |
| mois 4–6 | 1,100 | **1,039** |
| mois 7+ | 1,374 | **1,034** |

Le premier trimestre reste un vrai cold start. Dès le trimestre suivant, la
lecture du délai réellement appris par les hubs suit presque exactement le temps
opérationnel. L'ancienne dérive **0,928 → 1,235 → 1,537** n'est donc pas une
constante de vitesse à fitter ; elle est principalement un état de hub évolutif.

Les médianes matures du 5×6 final sont PASS **0,645**, MAIL **1,143**, total
**0,734**, revenu **0,904**, profit **0,871**, rating **0,957**, headway
**1,084**, leg au build **1,374**, leg live adapté **1,034** et flotte décision
**1,00**. Le timing est donc bien recentré ; le cargo ne l'est pas.

Pour croissance endpoint `0/1/2+`, le total mature vaut respectivement
**1,705 / 1,261 / 0,719** et le revenu **1,734 / 1,679 / 0,889** ; **450/466**
lignes sont encore en `2+`. En revanche le leg live adapté vaut
**1,130 / 0,980 / 1,034** dans ces mêmes buckets. Le learner corrige donc le
timing même là où l'économie mature reste biaisée par l'évolution ultérieure du
réseau. Production/partage longitudinal des hubs restent un problème séparé.

### 6.2 Coût opcode

Sur les **534 builds** de la campagne finale : `demand_ticks` vaut **4,67** en
moyenne / **5** en médiane, `demand_ops_same_tick` **51,76 k** en moyenne,
`eval_ops_same_tick` **3,52 k** en moyenne et `eval_ticks` reste **0** en médiane
(6 suspensions seulement sur 534 builds). Le scoring courant est donc
pratiquement inchangé.

Le batching des résidus C117 est en revanche efficace : la fusion station coûte
**128,5 ops par leg observé** sur **9 912** observations, contre ~**296,5
ops/leg** sur le premier 5×6, soit environ **−57 %**. Le smoke seed42 ×2 ans
donnait déjà ~149 ops/leg ; le 5×6 confirme donc que le gain est multi-seed.

### 6.3 Matérialité économique du timing live

Un replay passif à 7+ mois, en gardant le **même moteur réellement construit**
mais en remplaçant le timing du build par le timing hub live, couvre **466**
lignes :

- cycle one-way live/build : médiane **1,316×** ;
- **186/466** lignes changent de flotte optimale ;
- revenu : médiane **0,908×** du replay initial ;
- profit : médiane **0,879×**, delta médian **−5,78 k£/an** ;
- score ROI : médiane **0,771×**.

Le timing adaptatif doit donc alimenter l'économie courante, pas seulement une
sonde de diagnostic.

### 6.4 Cold start moteur et apprentissage PASS/MAIL

Le catalogue externe construit par `run_c121_air_capacity_catalog.py` a été
abandonné comme dépendance de C121. Il peut rester comme outil diagnostique
indépendant, mais le runner C121 normal ne l'injecte plus et le code de décision
ne contient aucun `EngineID`/couple PASS-MAIL OpenGFX hardcodé. L'enquête sur
EngineID 233 n'est donc plus nécessaire.

La règle est désormais :

1. moteur jamais observé : capacité PASS du catalogue moteur, `mailCapacity=0` ;
   tout le sous-modèle MAIL est neutralisé (revenu, rating, partage, capacité et
   fleet scan), sans coefficient empirique ;
2. après le premier avion réellement construit et refitté PASS : lecture exacte
   de `AIVehicle.GetCapacity(..., paxCargo)` et `AIVehicle.GetCapacity(...,
   mailCargo)`, puis mémorisation dans `C121_AIR_ENGINE_CAPACITY_OBS` ;
3. évaluations ultérieures : `OpexC121EngineEconomics()` relit ce couple exact et
   utilise normalement PASS+MAIL.

`GetBuildWithRefitCapacity` n'est pas réintroduit. C'est le même motif que le
learner hub : **cold start physique/simple, puis observation réelle mise en cache
et lecture O(1)**.

### 6.5 Shadow de stabilité du classement après apprentissage MAIL

Le shadow `c121_air_engine_replay_shadow=1` ne tourne plus à chaque build : il
est déclenché seulement lorsqu'un **nouveau moteur** acquiert pour la première
fois son couple PASS/MAIL exact. Sur le même sous-ensemble de moteurs réellement
observés dans la partie, il compare alors :

- argmax C121 en **PASS-only** ;
- argmax C121 en **PASS+MAIL exact**.

Campagne finale : `results/c121_mail_learning_5x6_20260928.json`, résumé
`results/c121_mail_learning_5x6_20260928_engine_stability.json`.

- **5/5 runs sains**, 514 builds C121 ;
- **32** événements d'apprentissage moteur ;
- **27** comparaisons éligibles avec au moins deux moteurs observés ;
- meilleur moteur modifié par MAIL : **1/27 = 3,7 %** ;
- flotte optimale : delta médian **0** avion ;
- revenu/profit : delta médian **+35,88 k£/an** quand MAIL est ajouté ;
- score C121 : ratio MAIL/PASS médian **1,576×** ;
- argmax PASS-only : moteur 223 sur 26/27 cas et 217 sur 1/27 ; avec MAIL,
  moteur 223 sur 27/27 cas.

Le signal utile est donc : **MAIL est matériel pour la valeur absolue, mais a
rarement changé l'ordre moteur dans les cas observables de ce 5×6**.

Limite de couverture : aucun des 32 événements ne connaît tous les candidats.
La fraction connue est **33,3 % en médiane**, soit typiquement **4 moteurs connus
sur 12**. Le **3,7 %** mesure donc la stabilité sur le sous-ensemble réellement
appris ; ce n'est pas une estimation exhaustive de la probabilité de bascule sur
tout le catalogue. Cette limite est désormais explicite plutôt que masquée par
un catalogue externe.

Coût du shadow de stabilité : moyenne **132,2 k opcodes** et médiane **140,1 k
opcodes** par événement d'apprentissage, **14 ticks** en médiane. Il n'y a que
32 événements sur 514 builds, soit environ **4,23 M opcodes au total** ou
**8,2 k opcodes/build amortis** sur la campagne. Ce coût reste séparé du learner
hub, qui reste à **128,5 ops/leg** après batching.

## 7. Suite

**Ne pas lancer de 20×10 causal et ne pas remplacer C115 maintenant.**

Le timing hub batché est validé en shadow. Avant un chemin causal C121 complet :

1. **ne pas chercher à rendre le cache PASS/MAIL exhaustif à froid** : le cold
   start PASS-only puis enrichissement réel est maintenant la règle ;
2. raccorder progressivement `OpexC121EngineEconomics()` au vrai classement
   moteur/projet C121. Le chooser legacy actuel n'a volontairement pas été
   remplacé dans cette étape ;
3. conserver le délai appris lors des Save/Load si C121 devient décisionnel,
   sans alourdir le budget `Save()` ;
4. traiter séparément le biais cargo des hubs en croissance `2+`, sans fitter
   les ratios matures ;
5. lorsqu'économie, score projet et choix moteur utilisent réellement C121,
   lancer d'abord un smoke causal C121-vs-C115 ; **pas de 20×10 à ce stade**.

Un shadow du **classement projet** PASS-only vs PASS+MAIL n'a pas été ajouté ici :
la question moteur est déjà mesurée et le coût du replay n'est pas négligeable.
L'ajouter seulement lorsque C121 entre effectivement dans le score projet.

## 8. Qualification causale du chemin complet (2026-09-28)

Le chemin causal C121 est désormais raccordé de bout en bout : demande préparée
une fois par projet, scan des moteurs de `airPlaneChoicesByAirport`, filtres
validité/buildabilité/compatibilité/range, économie C121, flotte cible, capital,
profit, score projet et admission. C116/C118 ne peuvent plus substituer un moteur
legacy après classement lorsque C121 est actif. C115 reste disponible comme
témoin lorsque C121 est désactivé.

Le cold start attendu est observé en jeu : sur seed 42, le premier choix du
moteur 223 est évalué avec `mailKnown=0`, puis la construction apprend la soute
réelle (`postbuild_mail_known=1`) ; la décision suivante relit le cache avec
`mailKnown=1`.

Smoke pairé `c121_causal_smoke_seed42_2y_20260928_r6`, même HEAD
`6110ad0af2439d64921a7416b727bd31d855a2dd` : `profit_year`
**836 526 -> 317 606 £/an** (-518 920), `company_value`
**1 129 884 -> 320 527 £** (-809 357), véhicules primaires **37 -> 16**,
slots aéroport Opex **18 -> 4**, villes AIR **17 -> 4**. Le rating médian monte
de 135 à 174,5 : l'échec principal est une forte sous-expansion, pas une simple
dégradation du service.

5x6 `c121_causal_5x6_20260928_r1`, seeds 42/100/999/1234/5678, 6 ans,
6 workers/6 CPU : **10/10 parties terminées**. Variante - référence sur
`profit_year` : moyenne **-395,7 k£/an**, médiane **-471,3 k£**, **1/4**,
`p_signes=0,375`, IC95 **[-700,8 ; -90,6] k£/an**. Le ratio des moyennes de
`company_value` vaut **0,7433**, soit **-25,67 %** ; le garde de valeur à -5 %
échoue largement. Verdict harnais : `diagnostic_only` sur 5 paires.

Conclusion : **ne pas lancer de 20x10 et ne pas remplacer C115 par C121** dans
cet état. La prochaine étape doit expliquer pourquoi l'économie/score C121
rejette ou dévalorise trop de projets : comparer les mêmes candidats C115/C121
sur revenu, profit, flotte, capital, `decisionScore`, `fundScore`, motif de rejet
et chronologie de cash. Toute correction repasse d'abord par un smoke seed42.

## 9. Stabilisation causale et stratégie AIR par régime (2026-09-29)

Le diagnostic causal a ensuite corrigé plusieurs défauts structurels avant de
réévaluer C121 : achat initial limité à **1 avion**, flotte cible renvoyée aux
renforts incrémentaux, absence d'exemption `C69_FLEET_EXEMPT` pour les renforts
C121, économie post-build conservée en C121, et neutralisation des substitutions
moteur C116/C118 après classement. Le scan moteur causal a aussi été fortement
réduit : les gros passages observés sont descendus d'environ **10–14 M opcodes**
à **~0,6–0,8 M** après factorisation/pruning, sans réintroduire de proxy MAIL.

Le 5x6 stabilisé `c121_current_5x6_jr5_20260929` est très différent du premier
5x6 causal : `profit_year` variante-témoin **-116 k£/an** en moyenne, médiane
**+19 k£/an**, **3/2**, IC95 large **[-439 ; +207] k£/an** ; la valeur est en
revanche **+90 k£** en moyenne, **4/1**, ratio des moyennes **+1,6 %**. Le garde
de valeur n'est donc plus le défaut principal. C121 reste toutefois insuffisant
pour remplacer C115 car son avantage contre AAAHogEx n'est pas robuste.

Le critère stratégique AIR retenu pour cette phase est désormais explicite :
**empêcher les monopoles AAAHogEx et réduire le gap Opex-AAAHogEx tout en gardant
assez de valeur/capital pour continuer l'expansion**. Le delta nominal C121-C115
est secondaire s'il achète un vrai rattrapage concurrentiel durable.

Trois familles de correction ont été qualifiées :

- `c121_air_project_realization=1`, correction globale douce des projets
  `hubsite/hubhub` : 5x6 propre `c121_projectreal_5x6_clean_20260929_r2`,
  **+49 k£/an** nominal en moyenne, valeur ~**+0,2 %**, environ **-3,6 slots AAA**,
  **-1,2 monopole AAA 2-0**, **+1 slot Opex** ; mais le gap `profit_year` face à
  AAAHogEx se dégrade de **-234 k£/an** en moyenne, seulement **2/5** graines
  l'améliorent. Diagnostic utile, **pas d'adoption**.
- `c121_air_engine_realization=1` : 5x6 avec gap AAA apparemment **+62 k£/an**,
  **4/5**, valeur ~**+2,37 %** ; mais l'audit des logs montre un mix moteur
  pratiquement identique dans les deux politiques (moteur 223 quasi exclusif,
  mêmes rares 220). Les écarts viennent surtout du coût opcode/timing du scan,
  pas d'un changement économique moteur réel. **Artefact diagnostique, rejeté**.
- stratégie adaptative de pression : la probe passive `C121_PRESSURE` réutilise
  uniquement le cache C83 `slotRemaining` déjà calculé, sans scan de carte ni
  effet décisionnel. Le 5x2 `c121_pressure_5x2_20260929` montre qu'en 1971 le
  classifieur `pressured>=6` et `contestable>=65 %` sépare rétrospectivement les
  deux graines où `project_realization` aidait le gap final (**100, 1234**) des
  trois où il le dégradait (**42, 999, 5678**). Le signal de phase/carte est donc
  réel et observable en jeu, mais son branchement causal n'est pas encore bon.

Le 5x6 causal de cette stratégie,
`c121_projectreal_adaptive_pressure_5x6_20260929`, réduit effectivement le gap
`profit_year` face à AAAHogEx de **+651,8 k£/an** en moyenne, médiane
**+334,4 k£**, **3/5** graines. Mais Opex paie **-104,0 k£/an** nominal en
moyenne et surtout **-8,32 %** de valeur (ratio des moyennes), avec **4/5** pertes
de valeur. Le territorial reste modérément positif (**+0,8 slot Opex**, **+0,6
ville Opex** en moyenne) mais ne compense pas ce coût. Une variante encore plus
douce à 25 % de l'écart appris échoue déjà au smoke 42/100 ; sur seed 100 :
**-260,7 k£/an**, **-1,109 M£** de valeur et gap AAA **-192,3 k£/an**. Le défaut
n'est donc pas seulement l'intensité du coefficient : utiliser directement ce
classifieur pour déformer le score projet reste trop instable.

### Décision finale de cette étape

- conserver le **C121 causal stabilisé** comme base de recherche, mais
  `c121_air_economics` reste désactivé par défaut et **C115 reste le témoin
  opérationnel** ;
- garder `project_realization`, `engine_realization`, `project_realization_adaptive`,
  `pressure_probe`, `defensive_floor` et les autres variantes comme diagnostics
  **OFF par défaut** ;
- conserver `C121_PRESSURE` comme observation de phase/carte : le signal est
  intéressant, mais ne pas l'utiliser directement pour scaler le revenu/profit
  d'un projet dans l'état actuel ;
- **ne pas lancer de 20x10 C121 maintenant**. La prochaine recherche doit séparer
  explicitement politique de **course territoriale** et politique de **rendement**
  (par exemple en agissant sur l'ordre/priorité d'expansion plutôt que sur la
  valeur économique intrinsèque des projets), avec smoke puis 5x6 avant toute
  qualification 20x10.

## 9. Stabilisation causale et stratégie de phase (2026-09-29)

Le premier causal ci-dessus n'est plus représentatif. Le chantier initial est
limité à **1 avion**, les renforts passent par les projets flotte, l'économie
post-build reste C121, les renforts C121 n'utilisent plus l'exemption
`C69_FLEET_EXEMPT`, et la marge observée démarre à `c121MarginalSamples=0`.

`c121_current_5x6_jr5_20260929` est **10/10 sain**. Face à C115,
`profit_year` est encore dispersé (~**-116 k£/an** moyen, médiane **+19 k£**,
3/2), mais la valeur revient dans le garde-fou : ~**+90 k£**, **4/1**, ratio des
moyennes **+1,6 %**. Le défaut n'est donc plus l'effondrement de flotte initial.

Le critère stratégique AIR devient : réduire le gap `OpexAI-AAAHogEx` et les
monopoles AAA, tout en conservant assez de valeur/cash pour poursuivre
l'expansion. Le garde de valeur -5 % reste une contrainte de soutenabilité.

Le `project_realization` global ne corrige que `hubsite`/`hubhub`. Sur
`c121_projectreal_5x6_clean_20260929_r2`, le territorial s'améliore (~**-1,2**
monopole AAA `2-0`, **+1** slot Opex) et le nominal Opex gagne ~**+49 k£/an**,
mais le gap face à AAA se dégrade d'environ **-234 k£/an**. **Rejet global.**

Le toggle `engine_realization` semblait meilleur (~**+62 k£/an** de gap, 4/5),
mais le mix moteur construit reste quasi identique (223 presque exclusif dans
les deux politiques) : les écarts viennent surtout du timing/opcodes. **Ne pas
l'interpréter comme un gain causal de choix moteur.**

Une probe passive `C121_PRESSURE` réutilise uniquement le cache C83
`slotRemaining`; aucun scan de carte supplémentaire. Le 5×2
`c121_pressure_5x2_20260929` est **10/10 complet** et classe exactement les
régimes observés : **100/1234 = efficiency**, **42/999/5678 = race**. Règle :
au moins 6 observations sous pression, part contestable >=65 % et part ouverte
>=72 % dans l'agrégat de l'année précédente.

L'adaptatif pression applique la correction hub uniquement en `efficiency`.
Smoke seed42 : `1970=efficiency`, puis `1971+=race`; évolution finale du gap
**-68,6 k£/an** et valeur **+160 k£** vs C121 courant.

5×6 `c121_projectreal_adaptive_pressure_5x6_20260929`, **10/10 complet** : gap
`profit_year` face à AAA **+651,8 k£/an** moyen, médiane **+334,4 k£**, 3/5 ;
mais `profit_year` Opex **-104,0 k£/an** et valeur **-423,6 k£**, **1/4**, ratio
des moyennes **-8,32 %**. Slots Opex **+0,8**, villes Opex **+0,6** ; monopoles
AAA `2-0` non robustes (moyenne **+0,4**, médiane **-1**). Le garde -5 % échoue.

Un soft à 25 % de l'écart appris est pire sur 42/100 : **0/2**, delta moyen
`profit_year` **-138,1 k£/an**, ratio de valeur **-13,98 %**. **Rejeté** ; retour
au facteur 50 % diagnostique, toujours OFF par défaut.

**Décision : C115 reste le témoin temporaire. Tous les toggles adaptatifs C121
restent OFF. Pas de 20×10.** La prochaine piste doit conserver le classifieur
`race/efficiency` mais agir sur le choix/l'ordre des types de projets, pas sur un
simple multiplicateur de revenu hub.

## 10. Qualification finale de l'adaptatif pression soft25 (2026-09-29)

**Ce bloc est autoritaire et remplace les conclusions soft25 antérieures de ce
document.** Les anciens probes 42/100 ont été produits sur des états intermédiaires
du classifieur et ne doivent plus servir de verdict.

Le classifieur causal finalement qualifié observe la pression C83 pendant deux
années complètes, puis verrouille le régime pour éviter une boucle de
rétroaction où la politique modifierait son propre signal. `efficiency` est
retenu si, sur l'année source : `pressured >= 3`, au moins **65 %** des villes
sous pression restent contestables (`1` slot restant), et au plus **20 %** des
villes utiles observées sont encore totalement ouvertes. Sinon le régime est
`race`. Aucun seed, moteur, montant d'argent ou année absolue n'est codé en dur.

En régime `race`, l'économie projet C121 reste brute. En régime `efficiency`,
la correction des bras `hubsite/hubhub` est volontairement douce :
`realization = 0.75 + 0.25 * learned`. Le `project_realization` global historique
reste à 50 % de l'écart appris et demeure un diagnostic séparé.

Qualification contre **C121 courant** :
`c121_projectreal_adaptive_pressure_soft25_5x6_20260929`, 5 graines x 6 ans,
**10/10 sain**. Le coût nominal est stable : `profit_year` **-77,9 k£/an** moyen,
médiane **-76,2 k£**, 0/5. La valeur reste dans le garde : ratio des moyennes
**-3,32 %**. En contrepartie, le gap `profit_year` Opex-AAAHogEx s'améliore de
**+451,5 k£/an** en moyenne, médiane **+176,6 k£**, 3/5 ; les véhicules Opex
sont **+2,0** en moyenne (~+1,76 %). Cette variante est donc un meilleur
compromis que la version 50 %, qui gagnait davantage de gap mais perdait
**-8,32 %** de valeur.

Qualification décisive contre **C115 historique** :
`c121_soft25_vs_c115_5x6_20260929`, **10/10 sain**. C121 soft25 réduit encore
le gap `profit_year` face à AAAHogEx de **+342,2 k£/an** en moyenne, médiane
**+558,7 k£**, 3/5. Mais ce rattrapage est acheté trop cher : `profit_year`
Opex **-287,0 k£/an** moyen (médiane **-385,2 k£**, 1/4), ratio des moyennes
**-17,55 %** ; `company_value` **-949 k£** moyen, ratio des moyennes
**-15,81 %**, garde -5 % largement échoué. La flotte primaire recule de
**13,8 véhicules** en moyenne (~-10,7 %).

Le territorial confirme que le gain de gap n'est pas une conquête plus rapide :
par rapport à C115, C121 soft25 termine avec **-4,2 slots Opex**, **-4,4 villes
Opex présentes** et **-2,6 villes partagées 1-1** en moyenne ; AAAHogEx a au
contraire **+2,2 slots** et **+1,2 monopole 2-0**. Le rating Opex est meilleur
(+2,8 points en moyenne), mais cela ne compense pas la sous-expansion.

Un dernier essai a combiné soft25 avec le `defensive_floor` prudent seulement en
régime `efficiency` :
`c121_projectreal_adaptive_pressure_soft25_defeff_5x6_20260929`, **10/10 sain**.
Il améliore encore le gap `profit_year` face à AAAHogEx de **+578,8 k£/an** en
moyenne (médiane **+15,4 k£**, 3/5), mais détruit la soutenabilité :
`profit_year` Opex **-200,8 k£/an** moyen, médiane **-188,3 k£**, **0/5** ;
`company_value` **-596 k£** moyen, ratio des moyennes **-11,27 %**, **0/5**.
Le territorial est également pire : **+3,0 slots AAA**, **-2,0 slots Opex**,
**+2,0 monopoles AAA 2-0** et **-2,6 villes Opex présentes** en moyenne.
**Rejet définitif du couplage score économique + floor défensif.**

### Verdict final de C121 à ce jalon

- **C115 reste le témoin opérationnel temporaire** ; `c121_air_economics` reste
  à 0 par défaut.
- `c121_air_project_realization_adaptive`, `project_realization`,
  `engine_realization`, `pressure_probe`, `defensive_floor` et les variantes de
  qualification restent **OFF par défaut**.
- Le classifieur `race/efficiency` est conservé comme **signal diagnostique de
  phase/carte** : il est observable sans scan de carte supplémentaire et peut
  guider une future politique.
- **Pas de 20x10 C121** : le 5x6 final échoue la soutenabilité et le territorial
  face à C115 malgré un gap AAA moyen meilleur.
- Prochaine piste : utiliser le régime pour **choisir/ordonner les types de
  projets AIR** (course territoriale vs rendement) tout en gardant l'économie
  intrinsèque du projet inchangée, puis smoke et 5x6 avant toute qualification
  plus large.

## 11. C122.1 — premier essai de priorité par régime (2026-09-29)

Le premier branchement C122 respecte bien ce contrat structurel : toggle
`c122_air_regime_priority` défaut 0, aucune modification de l'économie C121,
du moteur, de la flotte, du capital/ROI ou de C69. C122 n'agit qu'entre projets
AIR déjà admissibles, après les tiers défensifs C77. En `race`, il teste
`newpair > hubsite > hubhub`; en `efficiency`, il laisse l'ordre économique brut.

Smoke causal seed42 x3 ans :
`results/c122_regime_priority_smoke_seed42_1x3_20260929.json`, 2/2 sain. Le
classifieur verrouille bien `race` après deux années complètes, mais le résultat
est nettement défavorable : `profit_year` **-340,7 k£/an**, valeur **-20,52 %**,
gap Opex-AAAHogEx **-343,8 k£/an**, slots Opex **19->16**, villes Opex
**18->16**, monopoles AAA `2-0` **4->6**. **Pas de 5x6.**

Conclusion : le classifieur n'est pas remis en cause ; c'est `newpair` comme
proxy de conquête qui est trop grossier. La suite C122 doit utiliser les
annotations territoriales/slots déjà calculées plutôt qu'un tier topologique dur.
Voir `docs/44_c122_air_regime_priority_20260929.md`.
