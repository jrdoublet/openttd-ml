# Phase 3 — Le ML

Objectif : deux modèles entraînés proprement, une comparaison honnête arbres / réseau, et une
note d'erreur qui explique où le modèle se trompe. Pas un notebook, un résultat défendable.

> **Révision 2026-08-26.** Ce plan a été écrit avant la phase 2. Les sections marquées **[RÉSOLU]**
> décrivent des verrous qui ont été levés depuis ; les sections marquées **[NOUVEAU]** couvrent des
> problèmes découverts en phase 2 qui n'existaient pas dans le plan d'origine. L'ordre de bataille
> en fin de document a été recalé en conséquence.

Prérequis : phase 2 terminée (✅), campagne de graines lancée (✅), jeu de données brut disponible
(en cours de production).

---

## 3.0 — Verrou préalable : descendre le profit au niveau ligne — **[RÉSOLU]**

Le verrou est levé. Ce qui suit documente la réponse obtenue, pas un travail à faire.

**Les champs `VEHS` existent bien**, vérifiés sur un savegame réel (`sweeps/phase2_vehs_explore.py`,
dump filtré dans `results/phase2_vehs_explore.json`) : `VEHS.<id>.train[0].common[0]` expose
`profit_this_year` et `profit_last_year`. Nuance qui n'était pas anticipée : **seul le véhicule de
tête** du convoi porte ces champs, les wagons les ont à 0 — il faut donc filtrer sur
`unitnumber != 0`, sinon on somme des zéros.

**C'est `profit_last_year` qui est retenu, pas `profit_this_year`** : ce dernier couvre l'année *en
cours* au moment de la sauvegarde, donc potentiellement partielle, alors que l'amortissement est
une figure annuelle complète. Mélanger les deux, c'est comparer des durées différentes.

**La cible retenue**, implémentée et en production :

```
profit_ligne = Σ(profit_last_year des véhicules de tête)
             − (coût véhicules / max_age du matériel)
             − (coût infrastructure / INFRA_LIFE_YEARS)
```

avec `INFRA_LIFE_YEARS = 30`, hypothèse explicite et documentée (OpenTTD ne modélise aucune durée
de vie pour la voie et les gares, contrairement au matériel roulant qui a un `max_age` connu du
jeu). Décision assumée de séparer les deux horizons plutôt que d'amortir tout sur `max_age`.

**Le coût de construction est mesuré par `AIAccounting`, pas par `GetBankBalance`.** La piste
`AICompany.GetBankBalance()` avant/après suggérée dans le plan d'origine a été essayée et
**rejetée** : elle est polluée par les intérêts du prêt maximal emprunté au premier tick
(`GetBankBalance` dérive de 2100 sur ~27 jours sans aucune construction, là où
`AIAccounting.GetCosts()` rapporte correctement 0 sur la même fenêtre).

**Deux pièges `AIAccounting` trouvés en chemin**, tous deux coûteux et non évidents :
1. `AIAccounting` **ne s'imbrique pas**. Un second instrument ouvert pendant qu'un premier est
   encore vivant ne repart pas de zéro : il reflète le même cumul. La part véhicules est donc
   mesurée par *différence* sur la même instance, avant/après l'achat.
2. Un `AIAccounting` ouvert **avant** le pathfinding capte les évaluations de coût de pont/tunnel
   que le pathfinder fait en interne, sans rien construire — un échec `no_path_found` rapportait
   plus de 55 millions. Il est désormais ouvert seulement après que le chemin est trouvé.

**L'affectation véhicule → ligne ne passe pas par `ORDR`.** Le chaînage des ordres reste possible
et documenté, mais il est inutile ici : **une ligne par compagnie**, donc grouper par `owner`
suffit. Ce que le plan d'origine décrivait comme un « repli coûteux » est devenu le design retenu,
délibérément — voir 3.0bis.

**Le format de panneau est réglé, mais pas comme proposé.** Le plan suggérait un panneau unique
enrichi. Ça ne peut pas marcher : `AISign.BuildSign` accepte **31 caractères maximum** et échoue
**silencieusement** au-delà (pas d'exception, pas de log, aucune entrée dans le chunk `SIGN`) —
vérifié par recherche binaire. Le format proposé
`TRLN|<line_idx>|<stage>|<raison>|<construits>/<demandés>|<town_a>|<town_b>|<cout>` dépasserait
largement. D'où un découpage en plusieurs panneaux courts :

| Panneau | Contenu |
|---|---|
| `TRLN\|<idx>\|<stage>\|<raison>\|<n>/<n>` | statut, toujours posé |
| `TRLN\|<idx>\|T<a>-<b>\|D<dist>\|C<coût>` | paire de villes, distance, coût total |
| `TRLN\|<idx>\|V<coût>` | part véhicules du coût |
| `TRLN\|<idx>\|B<tick>\|M\|O` | tick de première mutation + conformité barrière — voir 3.0bis |

Les raisons d'échec sont abrégées en codes courts (`NOPATH`, `PATHLIM`, `TRKFAIL`, `STNFAIL`,
`DEPFAIL`, `MINPOP`, `NODISJ`, `PAIROOR`…) pour la même raison de budget.

---

## 3.0bis — **[NOUVEAU]** Le vrai verrou : la reproductibilité temporelle

Ce problème n'existait pas dans le plan d'origine et a failli invalider toute la cible.

**Le constat.** Sur une même ligne, construction rigoureusement identique (même paire, même
distance, même coût, même matériel), en ne changeant *que* le décalage de timing de l'IA,
`profit_ligne` variait de plus d'un million. Un balayage `Sleep(0/25/50/75/100/150/200)` donnait
des profits erratiques allant de −564 114 à +103 022, sans palier ni périodicité — donc chaotique,
pas un effet de calendrier identifiable.

**Ce que ça signifiait pour le ML.** Deux observations aux features identiques séparées d'un
million sur la cible : aucune régression ne peut prédire les deux. C'était un plancher d'erreur
irréductible, et il rivalisait avec l'écart entre deux lignes réellement différentes (ratio ~1/5).

**Les fausses pistes écartées, chacune mesurée** : ce n'est pas du bruit de relance (deux runs
strictement identiques sont byte-identiques, écart 0 partout), ce n'est pas la taille des villes
(médiane réelle 664 habitants, pas ~300 comme supposé — et l'amplitude *augmente* avec des villes
plus grandes), ce n'est pas un artefact de calendrier ou d'âge du matériel (date de capture
identique, âges variant de 11 jours sur toute la plage).

**La correction : une barrière de preflight.** Toute la préparation (choix de paire, pathfinding,
plans de quais) se fait d'abord ; puis l'IA attend jusqu'à un tick absolu fixe **avant** de toucher
la moindre tuile. `BARRIER_BASE = 11000`, choisi sur la distribution réelle du preflight (110 runs,
rangs 0-150 : médiane 1930, p90 7703, max 9916), coût ~4,1 % de la partie.

**Résultat : amplitude exactement 0** sur les trois lignes testées, les sept points de délai
donnant un `profit_ligne` rigoureusement identique. Le plancher d'erreur dû au timing passe du
million à zéro.

**Conséquences directes pour la suite de ce plan :**

- **La colonne `barrier_flag` (`M`/`O`) est une colonne de qualité de données, pas une feature.**
  `M` = ligne normalisée, `O` = le preflight avait déjà dépassé la cible, donc **non comparable**
  aux autres. Toute analyse doit filtrer sur `M` ou traiter les `O` à part. Sur la baseline v3 :
  81 `M`, 0 `O` — mais ce n'était pas le cas avant le relèvement de la barrière (18 `O` sur 81).
- **Pas besoin de répéter chaque configuration pour modéliser la moyenne.** C'était la conclusion
  quand le bruit semblait irréductible ; la barrière la rend inutile. Un essai par configuration
  suffit, ce qui divise le coût de campagne d'autant.
- **Deux ruptures de campagne à ne jamais mélanger** : 1950/densité 2 → 1970/densité 3, puis
  pré-barrière → post-barrière (les profits changent en valeur puisque la construction tombe au
  tick 11000 et non vers 950). Les `results/phase2_*.json` antérieurs sont des artefacts historiques.
- **Réserve honnête** : normaliser *quand* la construction démarre rend les runs comparables entre
  eux ; ça ne rend pas la simulation insensible au timing absolu. Le mécanisme exact de la
  sensibilité chaotique reste non identifié.

---

## 3.1 — Assemblage du jeu de données

Sources à joindre, une ligne de table finale par **tentative** :

| Source | Apporte |
|---|---|
| `SIGN` | la tentative : index, échec/succès, raison, villes, distance, coûts, tick/barrière |
| `AIPL.settings` | les paramètres réellement reçus (contrôle anti-clamping) |
| `VEHS` | profit par véhicule de tête, `max_age` |
| Sonde population | populations des deux villes — **voir l'avertissement ci-dessous** |
| `old_economy` | contexte compagnie (contrôle de cohérence, pas cible) |

**[NOUVEAU] Le chunk `CITY` n'expose aucune population en 13.4.** Vérifié directement sur un vrai
savegame. Les populations — qui sont pourtant une feature centrale — ne peuvent pas être lues
depuis les chunks. Elles doivent être écrites par l'IA elle-même (`AITown.GetPopulation` posé dans
un panneau) ou mesurées par une sonde dédiée. C'est le genre de détail qui coûte une campagne si on
le découvre après.

Sortie : un Parquet, une ligne par tentative, colonne `built` (booléen) et colonne `profit_ligne`
(renseignée seulement si `built`), plus les colonnes de qualité (`barrier_flag`,
`first_mutation_tick`).

**Contrôle de cohérence obligatoire** : le nombre de tentatives récupérées doit égaler le nombre de
lignes demandées. Un écart signifie que l'IA est morte en route — ces parties doivent être écartées
et **comptées**, pas ignorées silencieusement. (La baseline v3 lève déjà si le compte ne tombe pas
juste, et vérifie qu'il y a exactement une IA par expérience.)

---

## 3.2 — Features

Règle absolue : **une feature doit être connue avant de construire**. La question est « peut-on
prédire sans simuler ». Toute grandeur produite par la simulation est une fuite.

Autorisé :

- Distance entre les deux villes (à vol d'oiseau, et distance de Manhattan)
- Populations des deux villes au moment de la construction *(via sonde — voir 3.1)*
- **[RÉVISÉ] `pair_rank`** — le rang de la paire dans le classement gravitaire
  (`population_a × population_b / distance`). **Remplace `town_a_rank`/`town_b_rank`**, qui sont
  morts : la sélection de paire est désormais entièrement automatique, ces deux paramètres ne sont
  plus lus par l'IA. C'est `pair_rank` qui pilote la difficulté, et donc la classe négative.
- Dénivelé, nombre de tuiles d'eau sur le trajet direct, nombre de tuiles non constructibles
- Caractéristiques du moteur : vitesse max, capacité, prix, coût de roulement, puissance
- `num_trains`, `wagons_per_train`, capacité totale du convoi
- Date de construction, type de cargo
- **Coût de construction *estimé*** : légitime et déjà calculé par l'IA avant de construire
  (`estimatedCost` dans `main.nut`, utilisé pour filtrer les paires inabordables). À ne pas
  confondre avec le coût réalisé, qui est un résultat.

Interdit (ce sont des résultats, pas des causes) :

- `delivered_cargo`, `performance_history`, note de station
- Temps de trajet réel, taux de remplissage
- Longueur du chemin **effectivement** trouvé par le pathfinder — c'est un résultat de la
  construction. La distance à vol d'oiseau, elle, est légitime.
- **[NOUVEAU]** Coût de construction **réalisé**, `vehicle_cost`, `infra_cost` — ce sont des
  composantes de la cible, pas des entrées.
- **[NOUVEAU]** `barrier_flag`, `first_mutation_tick` — colonnes de qualité de données (3.0bis).
- **[NOUVEAU]** Le code de raison d'échec — c'est la sous-catégorisation de la classe négative,
  connue seulement après la tentative. Utile pour l'analyse d'erreur, jamais en entrée.

Le point sur la longueur de chemin mérite toujours son paragraphe dans le README : c'est exactement
le genre de fuite qui gonfle un R² et qu'un jury cherche.

**[FAIT] Note sur `engine_rank`.** Sa borne `[0,2]` était héritée du démarrage 1950, où seuls 3
moteurs étaient constructibles. Élargie à `[0,6]` — mesurée sur les 50 graines de la campagne v1 :
le rang 7 sort de la plage réelle sur 6 graines (moins de 8 moteurs constructibles) et produit
alors `ENGOOR`, un échec de configuration qui pollue la classe négative.

### Backlog d'enrichissement des features — **[LIVRÉ le 26/08 — mais le bloc terrain est inexploitable, voir 3.3]**

> **Avertissement.** Les items haute priorité ci-dessous ont tous été livrés dans la campagne v2
> (19 features contre 7 en v1). L'audit de fuite 3.3 montre néanmoins que **les features de terrain
> et de chalandise sont mesurées après le pathfinding**, donc absentes précisément sur les
> `PATHLIM` qu'elles devaient expliquer. Lire 3.3 avant de s'appuyer sur ce tableau.

Le jeu de données v1 (`data/phase2_hurdle_v1.csv`) n'émet que **7 features** : `pair_rank`,
`engine_rank`, `num_trains`, `wagons_per_train`, `town_a_population`, `town_b_population`,
`distance_straight`. Tout le reste de la liste « autorisé » ci-dessus reste à produire.

**Coût commun à tous ces items : c'est l'IA qui doit émettre ces valeurs, donc chaque
enrichissement impose de relancer la campagne (~4 h de wallclock pour 1000 lignes).** Il vaut donc
mieux les regrouper en une seule passe plutôt que de les ajouter un par un.

| Priorité | Feature | Justification |
|---|---|---|
| **Haute** | Distance gare↔centre-ville, pour les deux gares | `_makeStationPlans` cherche un emplacement plat **jusqu'à 30 tuiles** du centre (`main.nut` l. 218-219) et retient le premier viable : selon le relief, une gare atterrit à 2 tuiles du centre ou à 25. La zone de chalandise étant locale, c'est un déterminant de **premier ordre** du remplissage. Absent du jeu v1. |
| **Haute** | Production/acceptation de la zone de chalandise (`AITile.GetCargoProduction` / `GetCargoAcceptance` autour de la gare retenue) | Mesure **directe** de « combien de passagers cette gare peut capter », préférable au proxy géométrique ci-dessus. Ces deux appels ont déjà servi au débogage du bug de chargement (`docs/methode.md`), donc l'API est connue et disponible. |
| **Haute** | Bloc topographique : dénivelé, tuiles d'eau, tuiles non constructibles sur le trajet direct | **82 % des échecs sont des `PATHLIM`**, donc topographiques. Le modèle n'a actuellement *rien* sur le terrain et doit deviner le relief depuis `pair_rank` et la distance. C'est le manque le plus coûteux. |
| **Haute** | Caractéristiques du moteur : vitesse max, capacité, prix, coût de roulement, puissance | `engine_rank` n'est qu'un index ordinal — le modèle sait que 3 est plus lent que 2, pas de combien. Probablement déterminant pour l'étage 2 (profit). |
| **Haute** | Capacité totale du convoi en passagers | `num_trains × wagons_per_train × capacité d'un wagon`. Le remplissage est un rapport **demande/capacité** : sans la capacité en valeur absolue, ce rapport est inobservable. Feature dérivée à privilégier sur les propriétés moteur prises isolément. |
| Moyenne | Distance de Manhattan | Complète `distance_straight` ; l'écart entre les deux est un indice de détour imposé par le terrain. |
| Basse | Coût de construction **estimé** | L'IA le calcule déjà avant de construire (`estimatedCost`) mais ne l'émet pas. Quasi gratuit à ajouter. |
| Basse | Croissance des villes | **Effet mesuré faible** : +45 habitants médian par ville sur dix ans, hétérogène, certaines régressent. À n'ajouter que dans une passe groupée, pas pour elle-même. **Piège de fuite, voir ci-dessous.** |
| Nulle en l'état | Date de construction, type de cargo | Constants dans le design actuel (1970, passagers) : features inutiles tant qu'on ne les fait pas varier. |

**Pourquoi la proximité de gare n'est pas du bruit — et pourquoi son absence coûte cher.** Elle
est systématique et parfaitement connue avant de construire : l'IA choisit sa tuile de gare pendant
le preflight et pourrait l'émettre gratuitement. Laissée dehors, elle reproduit exactement la
pathologie que la barrière de preflight vient d'éliminer (3.0bis) : deux lignes aux features
identiques — mêmes populations, même distance — mais aux gares placées différemment donnent des
profits très différents. Le modèle voit alors des entrées identiques avec des cibles
contradictoires, et cette erreur est irréductible pour lui. Différence avec le chaos de timing :
cette cause-ci est **mesurable**, donc supprimable.

**Avertissement de fuite sur la croissance des villes.** La population *au moment de la
construction* est une feature légitime (déjà présente). La croissance **réalisée pendant la partie**
n'en est pas une : elle est postérieure à la décision, et surtout **endogène** — une ville bien
desservie grandit, donc la ligne cause en partie la croissance qui la nourrit (voir 3.7). L'utiliser
comme entrée reviendrait à prédire le profit avec une conséquence du profit. Si on veut capter une
dynamique de croissance, la seule forme admissible est une **tendance antérieure à la construction**
(ex. évolution de population sur l'année précédant la pose), qui elle est bien pré-connue.

**Stratégie recommandée : modéliser d'abord avec les 7 features actuelles, enrichir ensuite.**
Trois raisons : ça respecte l'ordre « sans sauter d'étape » de 3.5 ; ça coûte des minutes contre
4 h ; et surtout ça transforme l'enrichissement en **ablation propre** (« +X points de F1 apportés
par les features de terrain »), résultat bien plus intéressant à présenter qu'un modèle qui les
aurait eues d'emblée. C'est aussi le test direct de l'hypothèse CNN de 3.6.

### Dettes mineures de l'assemblage 3.1 — **[À FAIRE]**

- `AIPL.settings` n'est pas utilisé comme contrôle anti-clamping (le tableau de sources de 3.1 le
  prévoyait). Les paramètres reçus ne sont donc pas vérifiés contre les paramètres demandés.
- `old_economy` n'est pas récupéré comme contrôle de cohérence au niveau compagnie.
- Sortie en CSV et non en Parquet — écart assumé et documenté (1000 lignes, aucune colonne
  imbriquée, inspectable directement), à revoir si le volume augmente d'un ordre de grandeur.

---

## 3.3 — Audit de fuite

Avant tout entraînement, une passe systématique :

1. Pour chaque feature, écrire en une phrase *comment elle serait connue* au moment de décider.
   Si la phrase contient « après avoir construit », la feature saute.
2. Entraîner un modèle sur chaque feature isolément. Une feature seule qui atteint un score
   suspect est presque toujours une fuite déguisée.
3. Vérifier qu'aucune feature n'est une fonction déterministe de la graine (sinon vous mémorisez
   la partie, pas la ligne).
4. **[NOUVEAU]** Vérifier qu'aucune feature n'est une fonction déterministe de `pair_rank`. Le rang
   est construit *à partir* des populations et de la distance ; il les résume donc partiellement.
   Ce n'est pas une fuite (il est connu avant construction) mais c'est une colinéarité forte qui
   peut fausser l'interprétation SHAP en 3.7.

### Résultat de l'audit sur le jeu v2 — **[FAIT le 27/08]**

Sur les 2000 lignes de `data/phase2_hurdle_v2.csv`. **Trois familles, pas une.** La plus grave
n'est pas détectable par un audit de valeurs manquantes.

| Famille | Colonnes | Symptôme | Verdict |
|---|---|---|---|
| **Valeur sentinelle** | `construction_cost`, `infra_cost`, `vehicle_cost` | valent **0 ssi la ligne échoue** ; présentes à 100 % dans toutes les classes | **Fuite.** `construction_cost` seul → AUC 0,9986 ; réintroduit dans le modèle → **AUC 1,0000** |
| **Post-pathfinding** | `terrain_dh/water/unbuildable`, `station_a/b_{town_dist,cargo_prod,cargo_acc}`, `barrier_flag`, `first_mutation_tick` | `None` **ssi `PATHLIM`** (382/382) | **Fuite par absence.** Indisponibles au moment où l'étage 1 décide |
| **Post-construction** | `profit_ligne`, `sum_profit_last_year`, `*_amortization_annual`, `n_lead_vehicles`, `avg_max_age_years` | `None` sur tout échec | **Légitimes, étage 2 seulement.** Cible et covariables |

Plus : `stagger_slot` (constante 0) et `wagon_capacity` (constante 40) ; `line_index` est un
identifiant, pas une feature ; `estimated_cost` est redondant — mesuré
`= 2862,8 + 224,40 × distance_straight + ~570 × wagons_per_train`, R² 0,9954 contre la seule
distance. Il ne porte **aucun contenu topographique**, ce qui prouve que l'IA ne pose que du rail
à plat, et explique mécaniquement les 82 % de `PATHLIM`. Décision : le garder de côté jusqu'à
l'ajout des ponts et tunnels, où il deviendra un proxy de terrain quasi gratuit.

**Le défaut structurel.** Le bloc topographique était spécifié « sur le trajet direct », justifié
par « 82 % des échecs sont des PATHLIM, donc topographiques […] c'est le manque le plus coûteux ».
Il est mesuré **après** le pathfinding : la feature conçue pour expliquer les `PATHLIM` est
systématiquement absente sur les `PATHLIM`. Preuve dans les panneaux bruts — une tentative
`PATHLIM` n'en émet que 8 et s'arrête après `F`, un `TRKFAIL` ou un succès en émettent 13.

Correctif retenu : **mesurer le corridor direct avant le pathfinder, émettre au même endroit
qu'aujourd'hui** (les panneaux sont émis après la première mutation pour ne pas allonger le
preflight — c'est ce qui garantit `barrier_flag == "M"`, et ça ne doit pas changer).

**Régression annexe.** 3 lignes `PAIROOR` (graine 1089, rangs 160/170/180) : la borne
`pair_rank ≤ 180` est une constante globale calibrée sur les 50 graines de v1, alors que le nombre
de paires disponibles dépend de la carte de chaque graine. `consolidate()` ne les filtre pas, donc
elles polluent la classe négative en `built=False`.

---

## 3.4 — Découpage

`GroupKFold` avec la graine comme groupe. Jamais de `train_test_split` aléatoire.

Réservez en plus un **jeu de test final** de graines jamais touchées, mis de côté avant toute
exploration, et ouvert une seule fois à la fin. Le reste sert à la validation croisée.

Si vous réglez des hyperparamètres, il faut une validation croisée imbriquée : un `GroupKFold`
interne pour le réglage, externe pour l'estimation. Sinon votre score de validation est optimiste.

**[NOUVEAU] Dimensionner en graines, pas en lignes.** Puisque le split est par graine, la taille
d'échantillon effective pour généraliser est plus proche du nombre de graines distinctes que du
nombre de lignes. 50 graines × 20 rangs généralise bien mieux que 5 graines × 200 rangs, à nombre
de lignes égal. Les campagnes de phase 2 (5 graines × 20 rangs) étaient dimensionnées pour
diagnostiquer, pas pour entraîner.

---

## 3.5 — Progression des modèles

Dans cet ordre, sans sauter d'étape.

**Étage 1 — classifieur « constructible ? »**

1. Baseline : taux de base (`DummyClassifier(strategy='prior')`)
2. Régression logistique sur features standardisées
3. `HistGradientBoostingClassifier`

Métrique : F1, mais regardez aussi la courbe précision-rappel et surtout la **calibration**. Un
classifieur mal calibré casse l'étage suivant, puisque vous allez multiplier sa probabilité par un
profit attendu.

**[NOUVEAU] La classe négative est fabriquée, pas subie.** `pair_rank` est le bouton qui la produit
— rang 0 quasi toujours constructible, rangs élevés majoritairement en échec. Taux de succès
mesurés par bucket de rang sur la baseline : **88 % / 88 % / 68 % / 56 %** (rangs 0-24 / 25-49 /
50-74 / 75-120), et la frontière est nette au-delà : 1/5 au rang 300, 0/5 au rang 400. Le design de
campagne doit viser un équilibre exploitable : un jeu à 95 % de succès rend le taux de base
imbattable et le classifieur inutile.

### Résultat de la ligne de base étage 1 — **[FAIT le 27/08]**

`sweeps/phase3_stage1_baseline.py`, résultats complets dans `results/phase3_stage1_baseline.json`.
1997 lignes (les 3 `PAIROOR` exclues), `GroupKFold(5)` par graine, 12 features pré-construction.

| Modèle | AUC ROC (moy. ± é.-t. sur 5 plis) |
|---|---|
| Toujours « construite » | 0,5000 ± 0,0000 |
| **Régression logistique, `distance_straight` seule** | **0,8546 ± 0,0389** |
| **Régression logistique, 12 features** | **0,8567 ± 0,0399** |
| `HistGradientBoostingClassifier`, 12 features | 0,8251 ± 0,0322 |

**Les 11 features supplémentaires apportent +0,0021 d'AUC**, pour un écart-type de 0,0055 et une
amélioration sur 3 plis sur 5 : c'est du bruit. Trois indices concordants et indépendants :

- le **boosting fait pire** que la régression logistique — quand un modèle plus expressif dégrade
  le score, il n'y a pas de structure complexe à trouver, seulement 446 échecs à surapprendre ;
- l'**importance par permutation** (sur les plis de validation) est un désert : `distance_manhattan`
  0,2446, tout le reste sous 0,025, et quatre features en importance **négative** ;
- le **bloc moteur ne dit rien même en interaction**, confirmant son AUC univariée de 0,50.
  Cohérent : le moteur choisi n'influence pas la possibilité de poser des rails.

**Conclusion : l'étage 1 plafonne au niveau de la distance seule.** Le plafond n'est pas un
problème de modèle mais d'information — il tombera avec le correctif terrain de 3.3, pas avec un
meilleur classifieur. Ce chiffre est le point de comparaison qui rendra le gain de la v3
démontrable plutôt que supposé.

Note de métrique : l'AUC prime ici sur le F1 annoncé plus haut, parce que le taux de base est de
77,6 % — un modèle qui répond « construite » systématiquement affiche 77,6 % de justesse sans rien
savoir, quand son AUC vaut 0,5000, ce qu'il mérite.

**Étage 2 — régression du profit, conditionnelle à la construction**

1. Baseline : médiane du train (`DummyRegressor(strategy='median')`)
2. Régression linéaire, puis Ridge
3. `HistGradientBoostingRegressor`

Métrique : MAE, comme fixé. Ajoutez le MAE relatif à la baseline, c'est ce qui parle.

**Composition des deux étages**

```
profit_attendu = P(constructible) × E[profit | construit]
```

C'est cette quantité composée qui a une valeur décisionnelle, et c'est elle que vous présentez.
Évaluez-la de bout en bout sur le test final, pas seulement les deux étages séparément.

---

## 3.6 — Le chapitre deep learning

C'est ici que la 3060 sert, et c'est ici qu'il faut être honnête.

**Réseau tabulaire.** Un MLP sur les mêmes features, PyTorch, normalisation des entrées, embeddings
pour le cargo et le type de moteur. Attendez-vous à ce qu'il **perde** contre le gradient boosting.
C'est le résultat normal sur données tabulaires et il faut le présenter comme tel.

Ce qui compte n'est pas la victoire mais la comparaison chiffrée : performance, temps
d'entraînement, coût en énergie, interprétabilité, sensibilité aux hyperparamètres. Un tableau à
cinq colonnes qui conclut « le boosting gagne, et voici pourquoi c'est attendu » vaut mieux qu'un
réseau vainqueur par construction.

**Réseau convolutif sur le terrain.** Le chapitre qui justifie vraiment le GPU. Extrayez du
savegame la fenêtre de carte entre les deux villes sous forme de tenseur (hauteur, type de tuile,
eau, pente) et faites-le passer dans un petit CNN, en concaténant les features tabulaires en tête
de couche dense.

C'est le seul modèle qui peut voir *pourquoi* un terrain est infranchissable, là où vos features
agrégées ne voient qu'un compte de tuiles. S'il bat le boosting sur l'étage 1, vous tenez le
résultat le plus intéressant du projet. S'il perd, vous avez quand même une comparaison
architecture-adaptée-à-la-donnée à raconter.

Augmentation par symétries : rotations de 90° et miroirs. La carte n'a pas d'orientation
privilégiée, ce sont des augmentations exactes et gratuites.

**[NOUVEAU] Argument renforcé pour le CNN.** Les échecs de la baseline sont à 76 % des `PATHLIM`
(le pathfinder épuise son budget) et à 24 % des `TRKFAIL`. Ce sont des échecs *topographiques* :
exactement ce qu'une carte en entrée peut voir et qu'un compte agrégé de tuiles d'eau ne voit pas.
Si le CNN doit gagner quelque part, c'est sur l'étage 1.

---

## 3.7 — Interprétation et analyse d'erreur

- SHAP sur le modèle gagnant de chaque étage.
- Vérification de cohérence physique : la distance et la capacité doivent dominer. Si une feature
  absurde domine, cherchez la fuite avant de célébrer.
- **Analyse des pires erreurs** : sortez les vingt lignes les plus mal prédites et regardez-les une
  par une. C'est la section que personne n'écrit et que tout le monde apprécie.
- **[NOUVEAU] Un confondant identifié à garder en tête ici : la croissance endogène.** Une ville
  bien desservie grandit. Une ligne influence donc les villes qui la nourrissent — la rentabilité
  cause en partie la croissance qui cause la rentabilité. Et deux lignes voisines peuvent
  s'entraîner mutuellement, même sur des villes disjointes : la contrainte de villes disjointes
  empêche le partage de villes, pas le partage d'effets de croissance. Non mesuré à ce jour.
- **[NOUVEAU] Un mode d'échec déjà documenté et quantifié** : la cannibalisation de passagers
  quand plusieurs lignes partagent une partie (profit de la ligne de référence : −154 257 seule,
  −690 833 avec 14 concurrentes, soit 348 % pire). Corrigé par la contrainte de villes disjointes,
  mais c'est un résultat à citer, pas à redécouvrir.
- Courbe d'apprentissage : score en fonction du nombre de graines. Elle vous dit si relancer une
  campagne apporterait quelque chose, et c'est un argument de dimensionnement, pas une figure
  décorative.

---

## 3.8 — Outillage

- **MLflow** en local, à partir du moment où vous comparez plus de trois configurations. Loggez
  features, hyperparamètres, métriques et le hash du jeu de données.
- Un `Makefile` ou quelques scripts : `make dataset`, `make train`, `make report`. La
  reproductibilité de bout en bout vaut autant que le score.
- Pas de DVC : vos données se régénèrent depuis une graine, c'est précisément l'avantage du projet.
  **[NUANCE]** Vrai, mais à une condition désormais explicite : la régénération n'est fidèle que si
  la version de `main.nut` et la configuration OpenTTD sont les mêmes. Une constante de l'IA (la
  barrière, par exemple) vit dans le code, pas dans le script de campagne — le hash du jeu de
  données doit donc inclure le hash du commit, sinon « régénérable depuis une graine » est faux.

---

## 3.9 — Livrables

- `README` : la question, le protocole, les résultats, les limites — dans cet ordre.
- Quatre figures : distribution du profit, calibration du classifieur, comparaison des modèles,
  SHAP du gagnant.
- Une **model card** courte : données, features, limites, ce que le modèle ne doit pas servir à faire.
- Le tableau de comparaison boosting / MLP / CNN.
- Une section « ce qui n'a pas marché » — **[RENFORCÉ]** elle est déjà largement écrite par la
  phase 2 et c'est le différenciateur du projet. Matière disponible : les quatre bugs de
  construction (quai d'une tuile, dépôt mal raccordé, coût contaminé par le pathfinder, navigation
  bloquée), les sept hypothèses testées et écartées sur le blocage de navigation, la traque du
  plancher d'erreur de timing en cinq contrôles successifs, la prémisse « villes trop petites »
  réfutée par la mesure, et le piège de comparaison de ratios à dénominateurs de designs
  différents. Tout est daté et chiffré dans `docs/methode.md`.

---

## Ordre de bataille — **[RECALÉ]**

| Étape | Charge | État |
|---|---|---|
| ~~3.0 verrou profit par ligne~~ | ~~1 soirée (bloquant)~~ | ✅ résolu en phase 2 |
| 3.0bis reproductibilité temporelle | — | ✅ résolu (barrière à 11000) |
| 3.1 assemblage | 1 week-end | en cours |
| 3.2–3.4 features, audit, splits | 1 week-end | |
| 3.5 baselines et boosting | 1 week-end | |
| 3.6 deep learning | 2 week-ends | |
| 3.7–3.9 analyse et restitution | 1 week-end | |

Si le temps manque, coupez le CNN — pas l'analyse d'erreur ni l'audit de fuite.

**[NOUVEAU] Une étape à insérer avant 3.5 si l'équilibre des classes est mauvais.** La campagne de
phase 2 était dimensionnée pour diagnostiquer (5 graines), pas pour entraîner. Si le jeu de données
final sort à 90 % de succès ou plus, il faut re-dimensionner la campagne (plus de graines, rangs
poussés au-delà de 110) avant de perdre du temps à modéliser — le taux de base serait imbattable.
