# Tâches — réduire l'écart avec AAAHogEx

Revue du **2026-09-13**. Ce fichier contient les décisions actuelles et le prochain travail
utile. Les travaux terminés et leurs dossiers, y compris C65 (`19609f8`), sont transférés
dans [le journal du 13 septembre](journal_2026-09-13.md). Les développements antérieurs y sont
conservés intégralement pour la traçabilité ; seul ce fichier prescrit le travail restant.

Avant de rouvrir une piste, rechercher son nom et ses réglages dans ce journal **et** dans
[l'archive du 9 septembre](taches_archive_2026-09-09.md). L'archive sert à retrouver les
implémentations et les raisons des décisions ; **aucun résultat antérieur au 09/09 ne prouve
la performance actuelle**. Les journaux quotidiens conservent le détail des expériences.

## Où nous en sommes

**Le retard économique est établi ; sa cause dominante ne l'est pas encore.** Le duel partagé
20 graines × 5 ans du 13 septembre donne les résultats suivants, recalculés depuis les
20 paires de [la référence](../results/bench_1v1_5y_20seeds_reference.json) :

| Dernier checkpoint : 1974-12-01 | OpexAI, moyenne | AAAHogEx, moyenne | Écart des moyennes Opex/AAAHogEx | Victoires Opex |
|---|---:|---:|---:|---:|
| Valeur de compagnie | 2,189 M£ | 7,698 M£ | −71,56 % | 0/20 |
| Profit annuel | 676 k£ | 4 000 k£ | −83,09 % | 0/20 |
| Score de performance | 483 | 807 | −40,09 % | 0/20 |
| Moyenne des notes médianes de gare | 167,6 | 186,8 | −10,28 % | 0/20 |
| Gares possédées | 64,5 | 177,6 | −63,68 % | — |
| Caisse | 364 k£ | 1 650 k£ | — | — |
| Emprunt restant | 223,5 k£ | 0 £ | — | — |

Ces pourcentages sont des **rapports de moyennes**, pas la moyenne des pourcentages par graine.
Le harnais annonce zéro échec et les 40 lignes finales atteignent bien décembre 1974.
Il ne renseigne toutefois pas `expected_last_year` et ne transmet pas la sortie du moteur au
contrôle d'échec d'AAAHogEx : sa validation automatique reste à compléter (P0).

**Retrait du diagnostic « 93 % de rendement par véhicule, donc presque uniquement du volume ».**
Le harnais [du duel](../sweeps/bench_1v1_5y_20seeds.py), dans `extract_company_record`, compte
les entrées `VEHS` par propriétaire sans filtrer les composants. Les 102,4 contre 564,35 sont
ces entrées ; C54 a déjà identifié le piège wagons/ombres/rotors. Les décodeurs
`vehicle_breakdown` et `physical_telemetry`, malgré le nom `primary_vehicles_by_mode` de ce dernier,
ne filtrent eux aussi que type et propriétaire. Leur comptage demande la même qualification.
Même avec de vrais véhicules, une moyenne mélangeant bus, avions et trains ne prouverait pas
une équivalence de rendement. **Ne pas dériver de productivité ni de cible de flotte de ces comptes.**

L'emprunt nul d'AAAHogEx **à l'arrivée** ne veut pas dire qu'elle n'a jamais emprunté.
La dette élevée et la caisse positive d'OpexAI ne suffisent pas non plus à désigner le capital
ou le contrôleur comme goulot : il faut observer les occasions réellement disponibles et leur
financement au moment du refus. Les relevés économiques restent utiles malgré le problème de flotte.

La [chronologie C50](../results/diag_1v1_chronology_6y_5seeds.json) situe une rupture à examiner
dès **1971** : sur cinq graines, les créations nettes de gares passent de 148 contre 72 en 1970
à 57 contre 241 en 1971. Ce sont des sommes sur cinq parties, et des variations nettes de stock,
pas un comptage des chantiers. Le volet véhicules reste soumis à la réserve ci-dessus.

## Pourquoi le travail donne une impression de surplace

1. **La mesure du progrès a glissé vers le volume et les opcodes.** C51 augmente le nombre de
   gares sans gain économique démontré ; C50b augmente la flotte routière et dégrade la valeur.
   Une optimisation locale ou un réseau plus gros n'est pas encore un rattrapage.
2. **Les essais sont surtout arbitrés en solo.** Une victoire contre notre propre référence
   sur une carte séparée ne démontre pas une meilleure résistance à AAAHogEx sur carte partagée.
   Nous n'avons pas ici une série homogène de duels entre versions permettant de mesurer une
   vitesse de rattrapage. Le duel récent établit le retard, pas l'absence de tout progrès passé.
3. **Les mêmes hypothèses réapparaissent après leur réfutation.** Exemples : supprimer les
   plafonds après C50b ; proposer P1.1 comme inédit en C63 ; expliquer le rail improductif avec
   le comptage invalidé de C54 ; conserver le « facteur 15 inexpliqué » après sa correction C39.6.
4. **Les statuts confondaient livré, adopté et rentable.** C56 a corrigé un gel réel ; C65 facilite
   le développement. Ce sont des acquis. C60 n'a qu'un smoke de son filtre ; C53 non-stop est
   adopté mais son gain économique n'est pas établi statistiquement par le banc cité.

**Objectif de la prochaine séquence : augmenter le profit et la valeur en duel, en expliquant
le mécanisme qui permet de réinvestir.** Le nombre de véhicules, les gares et les opcodes restent
les instruments de diagnostic. Ils ne remplacent pas cet objectif.

## Ordre de travail

| Rang | Chantier | Question qui doit être tranchée | Livrable / condition de passage |
|---|---|---|---|
| **P0** | **C66 : duel fiable et référence reproductible** | Quelle est la trajectoire économique actuelle face à AAAHogEx, avec une flotte correctement comptée ? | Harnais qualifié, référence figée ; réutiliser les données valides avant de relancer |
| **P1** | **C63 + C58 : investissement et réinvestissement** | Où se perd la croissance à partir de 1971 : coût, revenu capté, occasions absentes ou décisions lentes ? | Un diagnostic commun 5×6, attribution par mode/âge de ligne, puis **un seul** correctif causal |
| **P2** | C61 + C59 : exploitation des infrastructures rentables | Quelles lignes profitables disposent de demande non servie et d'une capacité réellement disponible ? | Cibler le mode exposé par P1 ; un levier isolé, sans rejouer la suppression brute des plafonds |
| **P2 conditionnelle** | C39/C41 : coût des décisions utiles | Reste-t-il des projets valides et finançables que le contrôleur traite trop tard ? | Montrer un délai et une occasion perdue sur l'arbre courant avant de modifier la cadence ou les caches |
| **P3** | C52/C60, eau/C57, autres | Quel effet matériel subsiste hors des priorités ci-dessus ? | Remontée seulement sur exposition mesurée ou défaut bloquant reproductible |

La première action est P0, puis le diagnostic commun C63/C58. **Ne pas lancer simultanément
une nouvelle famille de plafonds, un nouveau score et un orchestrateur général.** Les rangs P2
restent des suites conditionnelles ; rien ne prouve encore que l'un d'eux est le meilleur levier.

<a id="c66"></a>
## P0 — C66 : fiabiliser le duel et rendre le rattrapage mesurable

**Statut : à faire.** Fiche ouverte le 2026-09-13 à la demande de l'utilisateur ; elle reprend
le volet « référence fiable » de C64. C64 conserve uniquement la piste adaptative, différée.
**But :** pouvoir dire si une modification d'OpexAI améliore son résultat économique **contre
AAAHogEx**, avec des mesures correctes, des parties complètes et une comparaison reproductible.
Cette fiche porte sur le harnais et ses preuves ; elle ne change aucune stratégie de jeu.

### C66.1 — Corriger et qualifier les compteurs physiques

**Défaut localisé :** `extract_company_record` dans
[`bench_1v1_5y_20seeds.py`](../sweeps/bench_1v1_5y_20seeds.py) compte les entrées `VEHS`
possédées. `vehicle_breakdown` dans `diag_1v1_monthly.py` et `physical_telemetry` dans
`bench_c50b_physical.py` ne filtrent pas davantage les composants internes. Le champ `type`
distingue les modes, pas nécessairement la tête d'un véhicule de ses composants.

- ⬜ Définir **un décodeur partagé**, avec un schéma de sortie versionné. Garder le compte brut
  sous un nom explicite (`vehicle_pool_entries`) ; ajouter les unités pilotables par mode
  (`primary_vehicles_by_mode`) et le nombre d'entrées non classées. Ne pas changer silencieusement
  la signification de `n_vehicles` dans les anciens résultats.
- ⬜ Qualifier les discriminants de tête/composant sur les chunks **réellement produits par
  OpenTTD 15.3**. Confronter les IDs comptés à un inventaire API pris au même état de jeu : train
  avec plusieurs wagons, avion avec ses composants, véhicule routier articulé si disponible,
  bateau. Ne pas deviner une valeur de `subtype`, filtrer sur profit nul ou sur capacité non nulle.
- ⬜ Compter un train comme une unité pilotable tout en additionnant correctement la capacité
  de ses wagons. Séparer les capacités **par cargo**, sans additionner passagers et tonnes comme
  une grandeur comparable. Inclure les véhicules au dépôt dans la flotte possédée ; distinguer
  « possédé » et « en service » si ce dernier état est effectivement mesurable.
- ⬜ Vérifier aussi les propriétaires des gares, les gares multimodales et les représentations
  dictionnaire/liste des chunks. Un champ requis absent doit être signalé, pas transformé en
  zéro crédible. Une gare multimodale reste une gare dans le total de compagnie.

**Preuve attendue :** fixtures minimales conservées, IDs API et IDs décodés identiques dans
les cas qualifiés, bilan des composants exclus et zéro entrée inexpliquée. Si un mode n'a pas
été exercé, le publier comme non qualifié. L'inventaire API sert à qualifier le décodeur sur une
partie de contrôle ; il n'impose pas une sonde Squirrel lourde dans chaque partie économique.
Les JSONL du duel actuel ne contiennent pas les chunks nécessaires pour corriger rétroactivement
sa flotte : préserver les anciens chiffres avec leur avertissement, sans inventer un recomptage.

### C66.2 — Séparer santé du moteur, santé des compagnies et activité de l'IA

**Défauts localisés :** le duel appelle `summarise(rows)` sans `expected_last_year` ; `keep`
transmet toute la sortie du moteur à OpexAI et une chaîne vide à AAAHogEx. Le détecteur commun
cherche des marqueurs fatals sans attribution de compagnie. Une erreur d'AAAHogEx pourrait donc
être imputée à OpexAI, tandis que la ligne AAAHogEx serait déclarée saine.

- ⬜ Conserver le journal moteur **une seule fois par partie**, avec son chemin dans le résultat.
  Extraire séparément les erreurs de chaque script à partir des identifiants vérifiés du log
  et de la correspondance script/compagnie du manifeste. Garder une catégorie « non attribuée »
  si le moteur ne permet pas de trancher ; ne pas affecter l'erreur arbitrairement au joueur 0.
- ⬜ Contrôler les deux compagnies attendues, l'absence de doublons de checkpoints, les dates
  réellement disponibles et l'horizon demandé. Passer au minimum `starting_year + years - 1`
  à `summarise`, puis contrôler le dernier checkpoint attendu selon la cadence de sauvegarde :
  une sauvegarde de janvier de la dernière année ne suffit pas à prouver une année complète.
- ⬜ Distinguer les statuts : erreur moteur/timeout, données manquantes, erreur NoAI attribuée,
  faillite en jeu, fin complète et suspicion de stagnation. La faillite est une issue économique
  à conserver ; elle ne doit pas disparaître d'une moyenne comme une erreur de collecte.
- ⬜ Définir un indicateur d'activité à partir des observations disponibles : changements de
  réseau/flotte, événements ou progression d'une tâche lorsque celle-ci est observable.
  **Aucune construction pendant plusieurs mois n'est pas une preuve de gel** ; des véhicules
  peuvent aussi continuer à gagner de l'argent alors que le contrôleur ne progresse plus.
  Une absence de signal devient une suspicion à diagnostiquer, pas une exclusion automatique.

**Preuve attendue :** cas de contrôle avec erreur OpexAI seule, erreur AAAHogEx seule, log
ambigu, compagnie absente et horizon tronqué ; attribution correcte et aucune partie manquante
silencieusement déclarée saine. Les contrôles négatifs peuvent utiliser des fixtures de logs
réels et des copies tronquées de résultats, sans faire crasher les IA de production.

### C66.3 — Figer une référence réellement reproductible

- ⬜ Créer un manifeste contenant : SHA Git, état modifié, empreinte et copie isolée des sources
  effectivement exécutées, version/empreinte d'AAAHogEx et des bibliothèques, versions
  OpenTTD/OpenGFX/OpenTTDLab et image Docker, configuration effective, réglages IA explicites
  **et défauts**, année initiale, durée, graines, répétitions et places des compagnies.
- ⬜ Figer les sources **avant** de lancer les parties ; les modifications de l'arbre de travail
  pendant le banc ne doivent pas contaminer les graines suivantes. C65 illustre pourquoi un
  SHA sans le contenu modifié ne suffit pas à décrire le programme exécuté.
- ⬜ Identifier séparément la politique testée, la compagnie et la partie : par exemple
  `(campaign, policy, seed, repeat, company_slot)`. Les noms « OpexAI » et « AAAHogEx » ne sont
  pas les deux variantes de stratégie. Refuser les paires dont les configurations diffèrent
  sur autre chose que l'intervention annoncée.
- ⬜ Conserver résultats compacts, checkpoints, manifeste, logs uniques et fixtures de décodage.
  Sorties sous un nom de campagne nouveau ; ne pas écraser la référence 20×5 ni ses JSONL.
  Les empreintes servent à relier une mesure à son code, pas à affirmer l'équivalence de deux codes.

**Preuve attendue :** deux relances courtes de la même référence isolée produisent les mêmes
métriques aux mêmes checkpoints. Si elles divergent, documenter et traiter la source de variation
avant d'attribuer une petite différence à une stratégie ; ne pas sélectionner la meilleure relance.

### C66.4 — Comparer deux politiques, chacune contre le même adversaire

Étendre le harnais existant avec la validation des réglages de `bench_v2.py`, sans écrire un
nouveau lanceur ad hoc. Pour chaque graine, exécuter **deux parties distinctes** :

| Partie | Compagnie OpexAI | Adversaire | Conditions |
|---|---|---|---|
| Témoin | Référence figée | AAAHogEx figée | Même graine, configuration, durée et place |
| Variante | Même référence + intervention isolée | Même AAAHogEx | Seule l'intervention annoncée diffère |

L'évolution ultérieure d'AAAHogEx peut différer entre les parties parce qu'OpexAI agit autrement :
c'est une conséquence du duel, pas un défaut d'appariement. Ne pas comparer deux OpexAI jouant
ensemble, ni la variante seule à une référence jouant contre AAAHogEx. Garder les places fixes
pour le premier protocole ; une inversion des places serait un bloc de robustesse distinct.

- ⬜ Fixer avant le banc la métrique primaire — **proposition : profit annuel final d'OpexAI** —,
  l'effet minimal utile et le garde-fou sur la valeur. Conserver les trajectoires annuelles,
  notamment 1970–1972, pour distinguer gain précoce et destruction de croissance à long terme.
- ⬜ Rapporter deux comparaisons différentes : `Opex_variante − Opex_témoin` sur chaque graine,
  puis l'écart `Opex − AAAHogEx` dans chacune des deux parties et son évolution. Une réduction
  du retard obtenue seulement en dégradant les deux compagnies n'est pas un gain économique
  d'OpexAI. Rapporter aussi les victoires directes contre AAAHogEx.
- ⬜ Publier deltas par graine, moyenne et médiane **des deltas**, intervalle d'incertitude,
  V/D/égalités et test des signes excluant les égalités. Les ratios demandent un dénominateur
  positif et doivent distinguer rapport de moyennes et moyenne des rapports.
- ⬜ Garder toutes les graines prévues et tous les statuts. Les erreurs de collecte doivent
  être résolues ou rendre la comparaison incomplète ; ne pas recalculer discrètement le verdict
  sur les seules réussites. Les analyses par mode, richesse ou déclenchement restent secondaires.

### C66.5 — Validation progressive et critères de clôture

1. ⬜ **Hors jeu :** fixtures des compteurs, erreurs par compagnie, horizon, appariement et calculs
   statistiques ; vérifier aussi qu'un réglage inconnu est rejeté et qu'une erreur interrompt
   proprement le rapport de validation sans effacer les résultats.
2. ⬜ **Smoke 1 graine × 1 an :** le duel démarre, les deux compagnies et leurs métriques sont
   présentes. Les scénarios physiques manquants sont qualifiés séparément ; un smoke sans train
   ne valide pas le compteur des trains. Conserver le tuple de dictionnaires retourné par `keep`.
3. ⬜ **Contrôle de répétabilité court**, puis **diagnostic 5 graines × 6 ans** sur référence figée.
   Ce diagnostic peut être partagé avec C63/C58 pour éviter une campagne supplémentaire ;
   distinguer sa télémétrie instrumentée du résultat économique sans sonde lourde.
4. ⬜ **Banc officiel 20 graines × 10 ans** quand une variante causale est prête : 40 parties
   partagées au total, chacune avec deux compagnies, soit 20 paires de politiques. Il valide
   l'intervention ; un nouveau 20×10 sans variante n'est pas requis pour clore le harnais.

**C66 est close lorsque** le décodeur a sa preuve indépendante, les contrôles négatifs détectent
et attribuent les échecs, la référence est figée et répétable, le diagnostic 5×6 est complet,
et le rapport distingue progrès d'OpexAI et évolution du duel. Tout gel suspect non expliqué ou
mode non qualifié doit être indiqué comme limite, jamais transformé en validation générale.
Le livrable est un harnais réutilisable et une référence qualifiée pour P1, pas une nouvelle IA.
Respecter les limites Docker et l'unique campagne consommatrice à la fois, comme en fin de fichier.

<a id="c64"></a>
## C64 — Politique adaptative : en attente d'un mécanisme établi

Le duel 20×5 et le banc `< 50 industries` sont terminés, consignés dans
[le journal du jour](journal_2026-09-13.md). Leur qualification et le futur comparateur relèvent
désormais de **C66**. Le défaut adaptatif reste à 0 : 9 V / 2 D / 9 égalités, p=0,06543,
sur des graines déjà utilisées pour découvrir le seuil, sans validation indépendante.

Pas de nouvelle recherche de seuil sur les mêmes 40 graines. Une reprise demande un mécanisme
identifié par C63/C58, une règle pré-enregistrée et des graines nouvelles. La mesure primaire
porte sur toutes les graines prévues ; les seules graines déclenchées restent une analyse
secondaire, particulièrement si le déclenchement dépend de l'état produit par la politique.

<a id="c63"></a>
<a id="c58"></a>
## P1 — C63 + C58 : comprendre le rendement de l'investissement

**Hypothèse ouverte :** l'expansion rentable ne s'auto-entretient pas assez vite face à la
concurrence. Le coût de construction n'est qu'une explication possible ; une recette trop
optimiste, un mauvais captage ou une occasion non traitée peuvent produire le même symptôme.

**Correction de C63.** Le devis anticipé rail existe :
[`OpexPrequoteRailCandidates`](../ai/OpexAI/projects.nut), `rail_prequote` et
`rail_prequote_keep_plan`, tous deux à défaut 0 dans `info.nut` et lus dans `settings.nut`.
P1.1/P1.3 ont été implémentés et rejetés avant le 09/09 ; leur histoire est dans l'archive,
**leurs anciens chiffres ne sont pas une preuve actuelle**. Ne pas réécrire ce mécanisme ni
réactiver son coût à chaque rebuild en le présentant comme une nouveauté. Les facteurs rail
170 % / route 121 % sont toujours dans le code ; leur justesse actuelle reste à mesurer.

**Un seul diagnostic commun, 5 graines × 6 ans, sur carte partagée**, en examinant d'abord
1970–1972 puis la suite. Réutiliser les sondes coût `RC|`, `AC|`, les événements de construction,
les sauvegardes et les prédictions enregistrées sur les lignes. Vérifier leur couverture
avant de supposer qu'elles suffisent : les succès seuls ne donnent pas les dépenses d'échec.
Ne pas activer aveuglément `decision_log` partout.

**Inventaire du 2026-09-13** (`sweeps/diag_c63_c58.py --selftest`) : les sources existantes
**ne ferment pas** le tableau joint. `OpexSign` écrase la tuile (1,1) ; un chunk `SIGN` ne
garde que le dernier nom, donc `RC|` (succès route, coût réel seulement), `AC|`/`RP|`/`DC|`
(sondes coût défaut 0, panneaux et non AILog) et `OY|`/`OZ|` ne reconstituent pas une série.
C50 a `pred_profit` pas `pred_revenue`, et `project_built.cost` est le modèle. C49 compte des
passes, pas des jours. `LINE_REVENUE` est derrière `decision_log`. L'eau n'a pas d'`actualCost`
(`predicted = 0`). `len(VEHS)` n'est pas une flotte. Quatre trous nommés : dépense prévue vs
réelle y compris échecs ; recette prédite vs réelle avec témoins profitables ; jours
d'occasion via `OpexAvailableCapital` ; une sorte de reliquat par passe. Sonde
`c63_invest_probe` (défaut 0) ajoutée pour ces trous ; agrégation hors-jeu dans
`sweeps/diag_c63_c58.py`.

**Smoke 2×3 ON/OFF** (`results/c63_c58_probe_onoff_3y_2seeds.json`) : **pas bit-identique**.
Graine 42 : +0,60 % de valeur ; graine 100 : **−37,6 %**. 0 échec script. Les conclusions
économiques se lisent sur le bras OFF ; le tableau C63 du diagnostic 5×6 est de la
télémétrie du bras ON, pas une preuve de performance du défaut.

**Diagnostic 5×6 partagé, reliquat corrigé** (`results/diag_c63_c58_6y_5seeds.json`) :
5/5 jusqu'à 1975-12-01, 0 échec script. `c63_invest_probe=1` contre AAAHogEx. Années C63 :
1970–1974 (flush de janvier ; 1975 absent, arrêt au 1er décembre). `len(VEHS)` non utilisé.
Le classifieur ne mappe plus une raison vide vers `waiting_compute` ; les
`passDiscards` (dont `build_failed` / `insufficient_cash`) sont enregistrés sous le gate
C63, pas seulement `decision_log`/`c49`. Une passe A* en vol avec un échec air/route
compte l'échec, pas l'attente. Les totaux leftover+lancé 342–375 j et l'année 1969
sur 5/5 graines viennent d'un flush au 28 décembre qui mélangeait les années : retiré.
Le ledger se ferme au 1er janvier suivant (`OpexC63EnsureYear`) ; la dernière année
d'une partie qui s'arrête en décembre n'est publiée que si le calendrier passe le
1er janvier. Capital immobilisé jusqu'au premier revenu : non mesuré. Eau : 0 ligne.

Jours de reliquat 1970–1972 : absent / invalid / unaffordable / wait / lancé.
Graine 42 = seule graine du smoke 2×3 dont la valeur n'a pas chuté.

| Graine | 1970 | 1971 | 1972 | 1970 | 1971 |
|---:|---|---|---|---|---|
| 42 | 158 / 45 / 0 / 5 / 143 | 70 / 74 / 0 / 67 / 158 | 208 / 30 / 0 / 47 / 76 | portefeuille vide | **mixte** (inv 35 %, abs 33 %, wait 32 %) ; 6 échecs air, `invalid_n=4` |
| 100 | 210 / 71 / 0 / 16 / 55 | 207 / 61 / 0 / 10 / 87 | 207 / 56 / 0 / 0 / 99 | portefeuille vide | portefeuille vide (sonde −38 % à 3 ans) |
| 999 | 86 / 46 / 0 / 17 / 203 | 110 / 50 / 29 / 42 / 133 | 175 / 43 / 0 / 36 / 108 | portefeuille vide | mixte |
| 1234 | 136 / 50 / 18 / 29 / 109 | 155 / 60 / 0 / 30 / 130 | 60 / 97 / 0 / 0 / 190 | portefeuille vide | portefeuille vide |
| 5678 | 202 / 67 / 0 / 0 / 83 | 172 / 23 / 0 / 28 / 140 | 27 / 28 / 0 / 26 / 261 | portefeuille vide | portefeuille vide |

`unaffordable` reste rare (18 j en 1970 sur 1234, 29 j en 1971 sur 999). `demand` = 0.
Recettes, témoins profitables du même mode/âge : air et route en 1970 âge 1, médiane
réel/prévu **≥ 0,91** (air 1,41 / 1,34 ; route 1,10 / 0,91). Rail âge 1 en 1971 :
médiane 0,13 / 0,31, **n=7**. Les lignes positives air/route ne sont pas le trou de 1971.

**Décision.** Ce n'est **pas le capital**. Ce n'est **pas le modèle de revenu** air/route.
Ce n'est pas « caisse ≥ 300 k£ ⇒ CPU ». Ce n'est **pas** « 1971 = attente de calcul » :
sur la graine 42 le reliquat 1971 se partage entre site/échec (`invalid`), portefeuille
vide et A*. En 1970, 5/5 graines ont un reliquat **portefeuille vide**. En 1971 la
pluralité reste le portefeuille vide, sans majorité sur 42 et 999. **Donnée manquante**
pour un levier : *pourquoi* `best` est vide les jours d'absent (vivier, seuil, déjà
construit), mesuré **sans** sonde qui déplace la trajectoire. **Pas de correctif, pas
de C61/C59, pas de C39/C41, pas de devis rail synchrone.** `c63_invest_probe` reste à 0.

Sortie attendue : **un tableau par mode, année et cohorte de lignes**, contenant :

- coût prévu, coût engagé, dépenses d'échec/rollback et capital immobilisé jusqu'au premier
  revenu ; couverture et montants non attribués explicités ;
- revenu/profit attendu contre profit observé à périmètre comparable, âge depuis la mise en
  service, rotations/remplissage lorsque mesurables ; distinguer résultat d'exploitation
  d'une ligne et résultat de compagnie, qui n'ont pas les mêmes charges ;
- nouvelles lignes et renforts, demande effectivement captée, partage de gares/bassins et
  présence concurrente ; un stock à quai est un symptôme, pas une preuve de revenu récupérable ;
- trésorerie **mobilisable selon `OpexAvailableCapital`** : caisse + emprunt effectivement
  accessible − réserve, face au besoin réel du projet ;
- sur les occasions où une décision peut être prise : candidat absent, invalide/site refusé,
  non finançable, demande/capacité insuffisante, en attente de calcul ou effectivement lancé.
  Rapporter séparément occurrences et **jours de jeu** ; aucune double attribution silencieuse.

**Deux corrections de méthode indispensables :**

- « Caisse ≥ 300 k£ et rien construit » ne prouve pas un manque de débit. Il faut un projet
  rentable, réalisable et finançable qui attend. Réciproquement, un surcoût modèle de 30 % ne
  prouve pas qu'une baisse du coût résoudrait le problème. Le bilan peut rester mixte ou inconclusif.
- C58 ne doit pas observer seulement `ET_VEHICLE_UNPROFITABLE` : cela sélectionne les perdants
  et rate les lignes positives qui rapportent bien moins que prévu. Comparer aussi des lignes
  profitables du même mode et du même âge. Pas de ferraillage automatique dans cet audit.

Les deltas de solde bancaire peuvent inclure revenus, entretien ou emprunts pendant un chantier :
ne pas les appeler coûts purs sans réconciliation. Deux smokes identiques sondes ON/OFF sont
un contrôle préliminaire, **pas une preuve de neutralité sur six ans**. Privilégier l'extraction
hors jeu ; si une instrumentation est nécessaire, mesurer sa perturbation et séparer son
résultat du banc économique final, exécuté sans instrumentation lourde.

**Décision à la sortie, avant tout autre diagnostic :**

| Fait observé sur des lignes/occasions identifiées | Suite autorisée par le diagnostic |
|---|---|
| Dépenses d'infrastructure/échecs immobilisant matériellement le capital | Un correctif de placement, réutilisation ou estimation sur le mode concerné ; pas de devis rail synchrone généralisé |
| Lignes positives mais recettes très inférieures au modèle | Corriger une hypothèse de demande, captage ou rotation ; C58/C59 |
| Demande non servie sur une infrastructure rentable ayant de la capacité | C61 ciblée, avec dépense et congestion observées |
| Projets valides finançables retardés pendant un coût de calcul identifié | C39/C41 ciblée |
| Pas de cause dominante ou données insuffisantes | Publier les limites et nommer la seule donnée manquante ; ne pas déclarer arbitrairement « capital » ou « CPU » |

**Fin de P1 (2026-09-13) :** hypothèse « capital » close. Hypothèse « modèle de revenu
air/route » close sur les témoins 1970–1971. L'attente A* n'est pas le reliquat 1971
(graine 42 mixte après correction du classifieur). La seule donnée manquante est
**pourquoi le portefeuille est vide** les jours `absent`, sans sonde qui déplace. Pas
de second levier.

<a id="c61"></a>
<a id="c59"></a>
## P2 — C61/C59 : mieux exploiter les lignes, si P1 le justifie

**Acquis causal C50b**, [banc consolidé](../results/bench_c50b_levers_10y_40seeds.json) :
supprimer la réserve de demande aérienne détruit de la valeur sur 20/20 graines ; relever le
plafond routier perd 27 paires sur 40 en valeur ; supprimer le cap de cadence aérien est
inconclusif à 21/40. Ajouter des véhicules n'est donc pas en soi le chantier prioritaire.

- **Air :** mesurer rotations, attente, demande et occupation aux deux aéroports avant de
  remplacer le partage égal de cadence entre lignes. `airportDelayDays = 3` et la table par
  type sont des modèles à qualifier, pas des capacités mesurées. Le modèle mutualisé proposé
  dans le dossier C61 reste un candidat, pas une spécification validée.
- **Route :** séparer fret, feeders et passagers interurbains. **`road_pax_build=0` au défaut** :
  une réforme visant les bus interurbains ne résoudra pas le duel courant. Le fret en chargement
  complet demande une mesure d'attente distincte du dwell passagers ; ne pas diviser par son
  `dwellDays=0`. La cible est du trafic rentable supplémentaire, pas le passage de 2 à 8 véhicules.
- **Rail :** la relaxation du seuil de backlog a déjà été inerte. C50b rapporte 39 `NOSPOT`
  pour 28 `OK` et 2 `TRACKFAIL` sur les références d'extension : inspecter les échecs de géométrie
  **si** les lignes concernées sont profitables et demandent réellement un second train.
  Cela ne justifie pas encore un chantier global de jonctions et gares partagées.
- **Ordres C59 :** corréler chargement, attente et profit avant une politique contextuelle.
  Retirer la prémisse « longue distance ⇒ full load mathématiquement supérieur » : attente,
  demande, prix du transport et congestion doivent entrer dans la comparaison. Une photographie
  de `cargo_count` ne mesure pas à elle seule le remplissage au départ ni une rotation.

<a id="c39"></a>
<a id="c41"></a>
<a id="c44"></a>
## P2 conditionnelle — C39/C41/C44 : traiter une occasion perdue, pas une lenteur abstraite

Les profils C39/C48 du 10 septembre montrent une augmentation du coût de génération avec
la maturité du réseau. Ils ne prouvent pas à eux seuls le gain d'une optimisation aujourd'hui.
Le [banc C48 final](../results/bench_c48_indexed_regeneration_10y_20seeds.json) donne
**10 victoires / 10 défaites en valeur**, +0,53 % en moyenne : gain économique non démontré,
`c48_indexed_regeneration=0` conservé. C46 reste également à 0 malgré un coût fret réduit en 1024².

Reste utile : critère de fraîcheur par couche, invalidation et recomputations évitables,
**sur le chemin où P1 aura montré des occasions finançables retardées**. Les modules actuels
sont `scheduler_tasks.nut`, `task_projects.nut`, `projects.nut` et `catalog.nut` ; les anciens
numéros de ligne de `main.nut` sont périmés après C65.

Ne pas relancer `portfolio_max_batch`/`portfolio_dynamic_batch`, un prix d'opcode ajouté au
score, ni un orchestrateur général sur la seule foi d'anciens profils. La fiche C39.5 est
close sur son levier testé ; « construit au premier tour » ne signifie cependant pas qu'un
intervalle entre tours est gratuit. Mesurer en jours, à âge de partie comparable, et vérifier
ce qui devient effectivement constructible. **Le titre catégorique de C44 (« ni capital ni
opcodes : le tour ») est retiré**, tout comme le « facteur 15 inexpliqué » déjà corrigé par C39.6.

## Autres tâches ouvertes, hors séquence prioritaire

Les travaux clos C45/C46/C47/C48/C49/C50/C51/C53/C54/C55/C56/C62/C65 et les étapes déjà
livrées des autres fiches sont consignés dans [le journal du jour](journal_2026-09-13.md).
Ne pas les remettre dans la file active sans fait nouveau.

| Fiche | Travail restant | Condition de reprise |
|---|---|---|
| C52 | Revalider les corrections crash/non rentable postérieures au banc ; exploiter la sonde de première arrivée si nécessaire | Défaut de service observé ; pas un objectif de nombre d'événements branchés |
| C60 | Exposition actuelle route/rail puis diagnostic 5×6 du filtre, encore à 0 après son smoke | Refus municipaux matériellement coûteux ; ne pas inférer cette exposition des seuls refus air, qui incluent le bruit |
| C57 | Calibrer les 50 000 opcodes de Lakes | Distribution des recherches eau et coût des paires perdues ; conserver la protection contre le gel |
| C43 / E3 | Constantes non tranchées : réserve, `loop_budget`, `pax_near`, seuils de mise au rebut | Constante impliquée par le diagnostic ; pas de balayage général |
| C45, reliquat | Décider de la persistance des compteurs de subventions | Besoin au rechargement ; secondaire pour des parties neuves |
| C42 bis | Filtrage/rendement des subventions | Exposition rentable démontrée ; les subventions brutes restent à 0 |
| C55, reliquat | Partage de demande et sur-service des bassins | Flux concurrents observés par P1 ; ne pas rouvrir le filtre d'origine |

## Eau, bibliothèques et robustesse — conservés, différés

Le code utilise déjà la transcription MinchinWeb dans `lib_water.nut`, avec budget en opcodes.
Ne pas proposer de recommencer son intégration. La bibliothèque n'apporte pas à elle seule des
lignes rentables ; le catalogue de sites intégré aux rebuilds a été testé sans justifier son adoption.
L'ancien essai Lakes du 09/09 précède le correctif de gel C56 : il ne tranche pas à lui seul
le défaut combiné actuel. Aucune modification de défaut eau n'est décidée par cette revue.

Le dossier eau conserve : découverte de sites séparée du portefeuille, distance navigable au
lieu du minorant Manhattan, revalidation des fronts réels sans réintroduire le faux négatif du
BFS borné, rotations fractionnaires et qualification mémoire sur grandes cartes. **Réexaminer
ces points dans le code au moment de la reprise**. Leur poids dans le retard courant n'est pas
mesuré ; un gel reproductible reprendrait immédiatement la priorité. C57 conserve le calibrage
du budget, pas un retour au budget en itérations. La consigne existante d'accord explicite avant
un nouveau diagnostic de découverte maritime est conservée ; aucun n'est lancé ici.

Les autres sujets restent disponibles : catchment réel des gares, placement/bruit d'aéroport,
jonctions/agrandissement de gare, `station_join`, coût A*, réglages de partie avec mode désactivé,
RAM Squirrel et automatisation GitHub. Ils remontent sur un besoin démontré, pas parce qu'une
bibliothèque propose une fonction. Le temps de trajet rail reste hors périmètre de SuperLib
(cf. C41 et `AGENTS.md`). `origin_sitable` et `complex_cargo` conservent leurs défauts ; ne pas
présenter leur conservation comme un nouveau gain mesuré.

## Règles pour la prochaine expérience

- **Une hypothèse, une intervention, une décision attendue.** Écrire le coût d'essai et le critère
  d'arrêt avant de coder. Ne pas prolonger un résultat nul en explorant des seuils jusqu'à gagner.
- Smoke 1×1, diagnostic physique **5×6**, puis **20×10 apparié avant adoption**. Pour revendiquer
  un rattrapage, le banc doit comparer les deux politiques OpexAI **face au même AAAHogEx**.
  Le 20×5 actuel est une référence descriptive, pas une exception à la règle d'adoption.
- Pré-enregistrer la métrique économique primaire, l'effet minimal utile et les garde-fous
  sur l'autre métrique économique, les échecs et le service. Publier les deltas par graine,
  moyenne et médiane appariées, incertitude et V/D/égalités. Exclure les égalités du test des
  signes ; un résultat non significatif n'est ni une preuve d'équivalence ni une adoption.
- Garder les graines d'échec dans les résultats avec leur statut. Distinguer validation d'un
  correctif fonctionnel, maintien d'un défaut et démonstration d'un gain économique.
- Exploiter les résultats déjà présents avant de lancer une campagne. Après verdict, remplacer
  la fiche active par sa décision et archiver le détail : ne pas empiler les conclusions opposées.
- Docker : toujours `--cpus=3 --memory=2g --memory-swap=2g`, cache
  `-v openttd-lab-home:/home/lab`, source montée dans `/work`. Une seule campagne consommatrice
  à la fois sur le VPS ; ces limites par conteneur ne bornent pas leur consommation cumulée.

**Portée de cette revue :** lecture du code courant et des archives, recomptage hors ligne des
JSON récents, réorganisation documentaire. Aucun changement de comportement IA, aucun défaut
modifié, aucun nouveau banc lancé. L'[architecture après C65](architecture_opexai.md) donne les
nouveaux emplacements des fonctions.
