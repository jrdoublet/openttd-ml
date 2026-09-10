# C49 — Dénominateur variable, piloté par la cause prochaine d'un non-chantier

**Contrat écrit avant code, 2026-09-10. Aucun code, aucun banc, aucun diagnostic dans ce document.**

## 0. Statut, et d'où vient l'autorisation

⚠️ **Décision utilisateur explicite du 2026-09-10.** Elle **lève** le refus du 2026-09-07 (« A1 /
dénominateur variable selon la ressource rare — décliné pour raison de doctrine, converge vers
l'aiguillage pauvre/riche d'AAAHogEx », `taches_archive_2026-09-09.md:2144`). Le refus était
**doctrinal, jamais mesuré** : rien n'a été réfuté, une direction avait été écartée.

⛔ **Ne pas présenter cette fiche comme validée par un banc.** C'est une décision, au même titre que
l'adoption de `pool_financeable` le 2026-09-03 contre un banc neutre — et on a découvert le
2026-09-10 que ce réglage-là ne faisait rien du tout. La leçon vaut ici : **ce qui autorise
l'instruction, c'est un choix ; ce qui autorisera l'adoption, c'est un banc 20×10.**

---

## 1. Ce que fait AAAHogEx, vérifié dans le source (mécanisme vivant)

`CalculateProfitModel()` est appelée **à chaque tour** de sa boucle principale (`main.nut:747`) ;
`GetValue()` (`main.nut:828`) applique le régime au classement (`main.nut:2858`).

| régime | dénominateur | déclencheur (`main.nut:781-806`) |
|---|---|---|
| `roiBase` | profit / **capital** | pas riche **ou** inflation |
| `buildingTimeBase` | profit / **temps de chantier** | riche **et** un type de véhicule a ≥ 100 places libres **et** < 70 % du plafond |
| `vehicleProfitBase` | profit / **véhicule** | sinon |

✅ Le bloc commenté après `main.nut:807` est une variante **antérieure**, derrière un `return;` — ce
n'est pas du code mort qui piloterait le comportement.

**Trois faits qui orientent notre variante :**

1. 🔑 **Sa détection repose sur des CONSTANTES** (`room >= 100`, `current < max * 7/10`, `IsRich()`).
   Il n'y a rien à copier si l'on veut un mécanisme auto-calibrant — c'est précisément la demande.
2. 🔑 **Sa ressource rare est le PLAFOND DE VÉHICULES**, pas l'argent. La richesse n'est qu'une
   *condition d'entrée* : pauvre ou en inflation, il classe par capital, exactement comme nous le
   faisons en permanence.
3. Il possède aussi un **seuil d'acceptation** (`estimate.value < 200` arrête la boucle,
   `main.nut:1054`), donc il sait « ne rien construire ce tour ». ⛔ **Hors périmètre de cette
   fiche** — voir §8.

---

## 2. Le principe : mesurer la rareté, ne pas l'estimer

**Une ressource est rare si c'est elle qui, en pratique, empêche le prochain chantier.**

Registre à un compteur par ressource, incrémenté quand elle est la **cause prochaine** d'un
non-chantier. Le dénominateur du classement est celui de la ressource en tête. Aucun seuil : un
`argmax` sur des faits observés.

🔑 **L'argument théorique, et il vient de l'archive** : un prix d'ombre n'est valide que si la
contrainte est **effectivement saturée par la décision du cycle en cours** — la *complementary
slackness*, condition que `shadow_pricing` violait (`taches_archive_2026-09-09.md:340`). Un compteur
de blocages réellement observés **est** une mesure empirique de saturation. C'est ce qui distingue
structurellement C49 de C35.

---

## 3. 🔑 Définition exacte des causes prochaines — le cœur du contrat

**Le point d'observation est une passe de la tâche `projects`.** À chaque passe, on balaie
`this._projects.best` par rang. On classe **le projet de plus haut rang qui n'a PAS été bâti dans
cette passe**, et lui seul : un seul incrément par passe, sur une seule ressource.

⚠️ **Pourquoi « le plus haut rang non bâti » et pas « tous les rejets »** : la distribution des
rejets est écrasée par `search_in_progress` (**69,6 %**, mesuré C47), or C41.49 a montré que ce
rejet est **bénin** — le fallthrough construit l'alternative dans la même passe. Compter tous les
rejets mesurerait le bruit du canal rail, pas la rareté.

| ressource | cause prochaine, telle qu'observée | dénominateur associé |
|---|---|---|
| **`cash`** | le projet est **non finançable** : `project.capital > OpexAvailableCapital()` | profit / capital *(comportement actuel)* |
| **`vehicles`** | finançable, mais ses véhicules feraient franchir le plafond du type (`AIGroup.GetNumVehicles(GROUP_ALL, vt)` contre le maximum du jeu) | profit / véhicule |
| **`site`** | finançable, **tenté**, échoué sur la carte (`build_failed`, `too_close`, `plan_failed`) | profit / gare consommée |
| **`decision`** | finançable **et** constructible **et** non tenté parce que la passe était déjà consommée (`PORTFOLIO_MAX_BATCH = 1`) | **profit absolu** — voir §4 |

**Non retenu en v1 : `build_time`.** AAAHogEx s'en sert, mais nous ne savons pas l'observer comme
cause *bloquante* : un chantier long consomme des jours **et** une passe, donc il est confondu avec
`decision`. L'inclure sans savoir le distinguer fabriquerait une ressource fantôme. À rouvrir si la
sonde montre que `decision` domine — il faudra alors les séparer.

**Si aucune de ces causes ne s'applique** (rien n'était disponible : `best` vide, ou tout déjà
bâti), **on n'incrémente rien.** L'absence d'offre n'est pas une rareté de ressource — c'est le
sujet du vivier vide (58,6 % des tours, C39.5b), une autre fiche.

---

## 4. 🔑 La conséquence remarquable : décisions rares ⇒ profit absolu

Si la ressource rare est la **décision**, chaque chantier coûte exactement **une** décision. Le
dénominateur vaut donc 1, et le classement devient **le profit annuel absolu**, pas un ratio.

C'est l'exact opposé de notre comportement actuel, qui divise **toujours** par le capital. Et ça
recoupe une observation de la chronologie 1v1 : nos chantiers sont majoritairement routiers à
**11–13 k£**, les leurs des liaisons aériennes à **180–220 k£**. Un classement par ratio préfère
structurellement le petit projet ; si les décisions sont la ressource rare, c'est une erreur.

Le prix de cette décision est **mesuré**, pas supposé : une passe qui bâtit paie ~2,7 M opcodes de
régénération de portefeuille en fin de partie, une passe qui s'abstient ne coûte presque rien
(C48). **Construire consomme une décision future.**

---

## 5. Fenêtre, départage, amorçage — sans constante inventée

- **Fenêtre = l'année de jeu en cours.** Ce n'est pas un nombre magique : c'est une période que le
  système utilise déjà (la tâche `report` publie par année). Le régime est recalculé **à la
  frontière d'année**, comme AAAHogEx le recalcule à chaque tour.
- **Départage** : en cas d'égalité, **le régime en place est conservé**. Hystérésis sans paramètre.
- **Amorçage** : avant la première frontière d'année, régime `cash` — le comportement actuel.
  Aucune régression possible sur la première année.
- **Pas de repli anti-blocage nécessaire**, et c'est une propriété importante : ⛔ le mode d'échec
  documenté (« barre surestimée ⇒ plus rien ne se construit », archive point 4) concerne les
  **seuils d'acceptation**. **Un changement de dénominateur ne fait que RÉORDONNER : il ne peut pas
  affamer le constructeur.** C'est ce qui rend C49 structurellement moins risqué que les
  formulations réfutées.

---

## 6. ⛔ Réfutés, et ce qui distingue cette fiche

| formulation réfutée | résultat | ce qui diffère ici |
|---|---|---|
| `shadow_pricing` (C35.3) | −11,2 % valeur, −25,6 % profit | prix duaux 1-D sur tout le vivier, violant la complementary slackness. Ici : **aucun prix calculé**, un comptage de blocages réels |
| « surplus capital-seul » (C35.4) | **7/7 défaites** à 6 ans, interdiction écrite `tension.nut:600-602` | retenait du **capital**. Ici : on ne retient rien, on réordonne |
| « filtre densité < λ_argent » (C35.4) | **7/7 défaites** | idem |
| `tension_scoring` | −11,6 % valeur | score continu ; ici, un régime discret piloté par des faits |
| `portfolio_max_batch=4` | −3,8 % valeur | « bâtir plus par passe » ; ici, rien ne change au débit |

⚠️ **Douze leviers sur douze ont perdu sur l'axe « ce que le portefeuille choisit ».** C49 en est un
treizième. Le fait qu'il soit mieux fondé théoriquement ne le protège pas : **banc obligatoire.**

---

## 7. Étapes et critère de fermeture, écrits d'avance

### Étape 1 — la sonde seule, aucune décision changée

Réglage `c49_scarcity_ledger` (défaut 0, gate dédié). À chaque passe de `projects`, classer la cause
prochaine selon §3 et accumuler ; publier par année, avec les comptes par ressource **et** le régime
qui *aurait* été choisi. **Aucun classement n'est modifié.**

Diagnostic 5 graines × 6 ans, mêmes graines que les autres fiches (`100 12345 42 7 999`).

**Critère de fermeture, pré-enregistré :**

- ⛔ **FERMER la fiche** si `cash` domine (> 80 % des passes classées) **sur les 5 graines et sur
  toutes les années**. Le dénominateur variable se réduirait alors au dénominateur fixe actuel :
  il n'y aurait rien à changer, et il faudra l'écrire plutôt que d'habiller le résultat.
- ✅ **INSTRUIRE l'étape 2** si le régime dominant **change au cours de la partie** sur ≥ 4 graines
  sur 5 — c'est la seule configuration où un dénominateur *variable* peut battre un fixe.
- 🟡 Si une ressource **autre que `cash`** domine de façon stable, la conclusion n'est pas un
  dénominateur variable mais un **dénominateur fixe différent** — plus simple, et à bencher comme
  tel.

### Étape 2 — le levier, un seul changement

Réglage `c49_variable_denominator` (défaut 0). Le régime calculé à l'étape 1 pilote le champ de
score utilisé au classement. **Rien d'autre ne change** — ni le vivier, ni les seuils, ni le débit.

### Étape 3 — banc officiel

20 graines × 10 ans apparié. **Test des signes avant les moyennes** ([[banc_monograine_insuffisant]]).
⛔ Ne pas conclure d'un 5×6 : C41.47 est le précédent d'un diagnostic 5×6 nul et sous-puissant
démenti par un banc 20×10 net (19/20, p < 0,0001).

---

## 8. Ce que ce contrat ne fait pas

- **Il n'introduit AUCUN seuil d'acceptation.** L'idée « ne rien construire ce tour pour attendre un
  meilleur projet » est adjacente à « surplus capital-seul » (**7/7 défaites**) et porte le mode
  d'échec « plus rien ne se construit ». Elle mérite sa propre fiche, son propre repli
  anti-blocage, et son propre banc. **Ne pas la glisser dans C49** : deux changements dans une même
  implémentation ont déjà failli faire rejeter un réglage valable ([[seuils_tresorerie_et_sac_a_dos]]).
- **Il ne touche pas au vivier.** Le vivier vide 58,6 % des tours est un problème d'**offre**, pas
  de classement.
- **Il ne compare pas notre `roi` au sien.** Vérifié : le sien vaut
  `routeIncome * 1000 / (véhicules + construction + coût d'opportunité)` (`estimator.nut:77`), le
  nôtre `profitAnnual * 1000 / (capital + immobilisé)` (`economy.nut:325-329`), et le nombre qu'il
  imprime entre parenthèses **omet le coût d'opportunité** (`estimator.nut:247`). Toute comparaison
  exige de recomposer les deux fractions sur une base homogène.
- **Il ne copie pas AAAHogEx.** Ses déclencheurs sont des constantes ; l'intérêt de C49 est
  précisément de s'en passer.


---

## 9. ✅ Étape 1 mesurée (2026-09-10) — la rareté bascule, mais pas comme un dénominateur *variable*

`c49_scarcity_ledger=1`, 5 graines × 6 ans, **0 échec**,
`results/diag_c49_scarcity_ledger_6y_5seeds.json`. 683 passes de `projects` classées.

**Cumul 5 graines** — 422 passes sur 683 (**61,8 %**) sont `none` (offre absente, rien à classer),
cohérent avec les 58,6 % de vivier vide de C39.5b. Sur les 261 passes classées :

| ressource | compte | part |
|---|---:|---:|
| **`decision`** | 151 | **57,9 %** |
| `cash` | 69 | 26,4 % |
| `site` | 41 | 15,7 % |
| **`vehicles`** | **0** | **0,0 %** |

**Par année (5 graines cumulées)** :

| année | passes | `none` | `cash` | `site` | `decision` | régime |
|---|---:|---:|---:|---:|---:|---|
| 1971 | 367 | 290 | 25 | 15 | 37 | `decision` |
| 1972 | 205 | 130 | **40** | 18 | 17 | **`cash`** |
| 1973 | 48 | 2 | 4 | 5 | 37 | `decision` |
| 1974 | 34 | 0 | **0** | 2 | 32 | `decision` |
| 1975 | 29 | 0 | **0** | 1 | 28 | `decision` |

🔑 **La trésorerie tombe à ZÉRO comme cause prochaine en 1974 et 1975.** En fin de partie, ce qui
empêche le chantier suivant n'est plus jamais l'argent.

### 9.1 Verdict contre le critère pré-enregistré du §7

- ⛔ **Fermeture refusée** : `cash` ne domine pas (26,4 % en cumul, **0 %** sur les deux dernières
  années). Le dénominateur fixe actuel n'est pas justifié par les faits.
- ✅ **Étape 2 instruite** : le régime change au cours de la partie sur **4 graines sur 5**
  (100, 12345, 42, 999 ; seule la graine 7 reste `decision` du début à la fin), soit exactement le
  seuil du contrat.
- ⚠️ **Mais la forme du changement n'est PAS celle d'un dénominateur oscillant** : sur 4 graines
  sur 5, la bascule est **monotone** — `cash` tôt, `decision` tard, sans retour. **C'est une
  transition de phase, pas une alternance.** Conséquence pratique : un régime à deux phases
  suffirait peut-être, et il serait plus simple à implémenter et à bencher qu'un argmax annuel.
  À trancher à l'étape 2.

### 9.2 ⚠️ La réserve principale, et elle porte sur le résultat dominant

`decision` (57,9 %) est **la classe la plus exposée au biais connu** du §3 : pour un projet
**non tenté**, on ne peut pas savoir s'il aurait échoué sur la carte, donc les échecs de carte non
observés tombent dans `decision`. `site` capte 15,7 % (les échecs réellement tentés), mais le
résidu non observé est d'ampleur inconnue. **Le résultat va dans le sens que la fiche espérait :
c'est précisément le cas où il faut être le plus prudent.**
Mesure de contrôle possible avant l'étape 2 : sous `portfolio_max_batch > 1` (⛔ réglage réfuté au
banc, mais utilisable en *diagnostic*), les rangs suivants sont réellement tentés — la part qui
migre de `decision` vers `site` borne le biais.

### 9.3 🔑 Le plafond de véhicules ne mord JAMAIS

**`vehicles` = 0 sur 683 passes, 5 graines, 6 ans.** L'ajout demandé au périmètre est mesuré, et il
est inerte : à cet horizon, notre flotte n'approche jamais `vehicle.max_*`. **Le déclencheur
d'AAAHogEx (`room >= 100 && current < max * 7/10`) ne se déclencherait jamais dans nos parties** —
copier son mécanisme n'aurait rien changé. Ne pas instrumenter cette ressource plus avant sans une
partie beaucoup plus longue.

### 9.4 Anomalies à connaître

- **Graine 42 : seulement 2 années publiées** sur 6 demandées (0 échec déclaré). Cause non
  établie. Sa contribution au « 4/5 » est donc fragile — **le critère est atteint de justesse**.
- Le champ `regime_change_count` du script rend **3**, ma recomputation en rend **4** : le script
  compte différemment (probablement en incluant l'année d'amorçage sans données, ou en écartant
  une graine trop courte). **C'est ma recomputation qui suit la lettre du §7** ; le champ du script
  est à corriger avant tout usage ultérieur.


---

## 10. ✅ Biais borné (2026-09-10) — `decision` survit à une correction conservatrice

Deux bras, 5 graines × 6 ans, **0 échec**, `results/diag_c49_bias_bound_6y_5seeds.json`.
Témoin `c49_scarcity_ledger=1` ; traitement `+ portfolio_max_batch=4`.
⚠️ `portfolio_max_batch=4` est **réfuté au banc** (−3,8 % valeur, −7,9 % gares) : il sert ici
**d'instrument**, parce qu'il fait réellement tenter les rangs suivants. Aucune conclusion de valeur
n'en est tirée.

✅ **L'instrument a fonctionné** : dans le bras traitement, `decision_unattempted` vaut **0** — la
cible est toujours tentée. Le taux conditionnel est donc mesurable :

**`p_map` = site / (site + decision_attempted) = 31 / (31 + 78) = 0,284.**
Parmi les cibles réellement tentées, **28,4 % échouent sur la carte**.

**Correction appliquée au réservoir non testé du témoin** (79 cas) :

| classe | part brute | **part corrigée** |
|---|---:|---:|
| `decision` | 57,9 % | **49,2 %** |
| `site` | 15,7 % | **24,3 %** |
| `cash` | 26,4 % | 26,4 % |
| `vehicles` | 0,0 % | 0,0 % |

🔑 **`decision` reste la classe dominante après correction** (49,2 % contre 24,3 % et 26,4 %). Et la
correction est **conservatrice dans le sens qui nous dérange** : les rangs tentés du bras traitement
sont plus profonds que la cible typique du témoin, donc `p_map` est plutôt **surestimé**. La
conclusion tient malgré un correctif qui lui est défavorable.

**Par année, la structure de phase se durcit** :

| année | `p_map` | `cash` brut | `decision` brut | **`decision` corrigé** |
|---|---:|---:|---:|---:|
| 1971 | 0,415 | 0,325 | 0,481 | 0,367 |
| 1972 | 0,615 | **0,533** | 0,227 | 0,112 |
| 1973 | 0,273 | 0,087 | 0,804 | **0,680** |
| 1974 | 0,000 | **0,000** | 0,941 | **0,941** |
| 1975 | 0,130 | **0,000** | 0,966 | **0,921** |

🔑 **Deux phases nettes, et non une alternance** : jusqu'en 1972 la trésorerie pèse (jusqu'à 53 %) ;
à partir de 1973 elle s'effondre et **tombe à zéro en 1974-1975**, où `decision` explique 92–94 %
des non-chantiers **même après correction**.

### 10.1 Ce que ça décide pour l'étape 2

- ✅ Le dénominateur fixe actuel (profit / capital) **n'est pas justifié en fin de partie** — c'est
  le résultat le plus robuste, il ne dépend d'aucune correction.
- ✅ La ressource rare tardive est bien la **décision** ⇒ dénominateur = **profit annuel absolu** (§4).
- 🔑 **Deux phases suffisent** : `cash` tôt, `decision` tard. L'argmax annuel du §5 reste le
  mécanisme de détection (il est sans constante), mais il n'a en pratique qu'une bascule à trouver.
  **Ne pas sur-concevoir une alternance qui n'existe pas.**
- ⚠️ **`vehicles` reste à 0 dans les deux bras — mais c'est un ARTEFACT D'HORIZON, pas une
  propriété du mécanisme.** Décision utilisateur du 2026-09-10 : **on l'implémente quand même.**
  Trois raisons :
  1. **Une partie peut durer 100 ans.** Notre fenêtre de mesure fait 6 ans et le banc officiel 10 ;
     le plafond de véhicules mordra forcément en fin de très longue partie, et c'est précisément le
     régime pour lequel le dénominateur profit/véhicule existe.
  2. 🔑 **On conçoit pour l'IA réparée, pas pour l'IA cassée.** Tout le résultat de la journée dit
     que notre débit s'effondre à mesure qu'on construit (C48, ÷9,2). Si ce défaut est corrigé, la
     flotte grossit bien plus vite et le plafond devient atteignable très tôt. Mesurer l'inertie du
     plafond sur une IA qui construit dix fois trop peu, c'est mesurer la conséquence du défaut
     qu'on cherche à corriger.
  3. Le coût d'implémentation est nul : le test existe déjà dans la sonde et tient en deux appels
     d'API sous garde.

  ⛔ **MAIS le risque doit être traité, pas ignoré** : une branche qui ne s'exécute dans aucun banc
  est exactement le piège trouvé deux fois le 2026-09-10 (`pool_financeable` et `knapsack_roi`,
  réglages « adoptés » pilotant du code injoignable, dont les bancs comparaient deux bras
  identiques).
  ✅ **Test obligatoire avant adoption, et il ne demande pas 100 ans : ABAISSER LE PLAFOND.**
  `make_cfg` (`sweeps/bench_v2.py`) génère l'`openttd.cfg` de la partie ; un diagnostic peut y
  écrire `max_aircraft` / `max_roadveh` / `max_trains` / `max_ships` à une valeur basse et **forcer
  le régime `vehicles` en 6 ans**. Même chemin de code, atteignable dans nos moyens.
  **Aucune adoption de C49 sans que cette branche ait été exécutée au moins une fois.**


---

## 11. 🔑 Le mécanisme de C49 est déjà connu — et déjà bencé sur 3 ans (trouvé le 2026-09-10)

Avant de coder l'étape 2, relecture de `OpexProjectSelectAffordable` (`projects.nut:516`). Son
commentaire décrit **mot pour mot** l'argument du §4 : *« un ratio favorise les tout petits projets
bon marché… comme on n'en bâtit qu'UN par cycle, chaque cycle est consommé par une ligne médiocre
et les gros projets rentables ne sont jamais atteints »*.

Le correctif existe déjà : **`portfolio_floor_pct`**, un plancher de profit absolu **relatif** au
meilleur projet finançable (donc sans constante d'époque, de carte ni d'inflation). Il a été bencé
— 20 graines × 3 ans, `results/bench_floor_3y_20seeds.json`, `docs/journal_2026-09-02.md:317` :

| plancher | valeur vs contrôle |
|---|---:|
| 0 % (défaut actuel) | **−16,2 %** |
| 25 % | −8,8 % |
| 50 % | **+0,1 %** |
| 75 % | −0,9 %, `performance_history` **−12,4 %** |

Verdict de l'époque : *« le plancher répare bien ce qu'il devait réparer, mais ne produit aucun
gain »*. Défaut maintenu à 0.

### 11.1 Pourquoi ça ne ferme pas C49 — et ce que ça lui impose

🔑 **Ce banc fait 3 ans.** Or C49 mesure que `cash` domine jusqu'en 1972 et que la bascule vers
`decision` se produit **à partir de 1973** (§9, §10). Un banc de 3 ans teste donc exactement la
phase où la trésorerie **est** la ressource rare — celle où le dénominateur par capital est
**correct**. Il est structurellement aveugle au régime que C49 vise.

✅ **Prédiction falsifiable, à écrire dans le contrat de l'étape 2** : l'effet de C49 doit être
**nul ou négatif sur les trois premières années** et n'apparaître que dans la seconde moitié d'un
banc 10 ans. **Si on l'observe dès l'année 1, on mesure autre chose** — et il faudra le dire au
lieu d'encaisser le gain.

⚠️ **Et une mise en garde que la courbe impose** : 0 → −16,2 %, 25 → −8,8 %, 50 → +0,1 %,
75 → −0,9 % avec `performance_history` −12,4 %. **Elle culmine vers 50 et redescend.** Or un
classement au profit purement absolu équivaut à un plancher de 100 — **du côté descendant de la
courbe**. L'étape 2 ne doit donc **pas** basculer sur le profit absolu nu ; le régime `decision`
doit viser un dénominateur **intermédiaire** entre le ratio et le profit absolu. La forme exacte
est à trancher dans le contrat de l'étape 2, pas à l'implémentation.

### 11.2 Piste connexe, moins chère, à ne pas confondre avec C49

`portfolio_floor_pct` est **déjà implémenté, déjà sur le chemin par défaut, et c'est un seul
entier**. Le rebencer sur **10 ans** (et non 3) répondrait à la même question que C49 pour une
fraction du coût, et testerait la même intuition. ⚠️ Ce n'est pas C49 — un plancher **filtre**
l'admission au classement, un dénominateur **réordonne**. Mais si le plancher à 50 % rend un gain
net sur 10 ans, C49 devient un raffinement d'un problème déjà résolu, et il faudra le dire.
