# Priorisation des correctifs — revue de code du 2026-09-06

Source : `docs/journaux/journal_2026-09-07.md` (10 étapes de revue, consignées le 2026-09-07). 40 constats
au total (hors ✅ vérifiés non-bugs). Regroupés ici par fichier/mécanisme pour permettre un
correctif par groupe plutôt qu'un par constat, avec les sujets du backlog (`docs/taches.md`) qui
touchent le même mécanisme et peuvent être traités dans la même passe.

Barème d'effort : niveau du skill `/code-review` (low/medium/high/xhigh/max) appliqué ici à la
**correction**, pas à la relecture — un correctif touchant un mécanisme économique partagé par
tout un mode de transport mérite plus d'effort qu'un renommage de constante, même si le diff est
petit. Équivalent Codex entre parenthèses (mapping : sol≈Opus, terra≈Sonnet).

---

## Tier 0 — Avant tout nouveau banc (fiabilité de la mesure elle-même)

### G0. Décision d'adoption + reproductibilité du banc factoriel
**Constats** : étape 1, #1 (script non reproductible), #2/#3 (C33.3, C20/A4, C22 non établis
isolément, et penchent contre en combo), #4 (C20 cache 2 réglages), #8 (`info.nut` décrit encore
les anciens défauts).

**Décision déjà rendue par la revue** : garder `air_joined_stops=1` (C33.2) et `portfolio_cache=1`
(C36.1) ; **remettre à 0** `abandon_cooldown_days`, `abandon_gen_filter` et le couple
`rail_search_resumable`/`rail_micro_deadline` tant qu'ils n'ont pas leur propre banc officiel
20×10 isolé face au nouveau contrôle (C33.2+C36.1). ⚠️ **Ceci défait une partie de ce qui a été
committé le 2026-09-06 — à confirmer avec vous avant d'éditer `info.nut`.**

**Correctifs mécaniques** : épingler explicitement les 6 réglages dans chaque bras de
`sweeps/bench_factorial_10y_20seeds.py` (y compris le bras de contrôle) ; corriger les
descriptions `info.nut`/commentaires `main.nut` qui annoncent encore l'ancien défaut.

- **Modèle : Sonnet 5, effort medium** (Codex terra, medium) — travail mécanique une fois la
  décision confirmée ; pas de nouvelle mesure à concevoir, juste rendre le protocole honnête.
- **Opportuniste** : aucun sujet backlog à greffer ici — c'est un prérequis, pas un lieu
  d'extension.

### G0bis. Le banc ne mesure pas l'objectif n°1 du projet (profit par opcode)
**Constat** : étape 1, #7. `SUCCESS_METRICS` et le JSON factoriel ne contiennent aucun coût
d'opcodes ni densité profit/opcode, alors que c'est l'objectif n°1 de `docs/taches.md` et la
métrique nord de [[objectif_ia_performante]] (profit par itération, qui remplace AUC/MAE).

- **Modèle : Sonnet 5, effort medium** (Codex terra, medium) — instrumentation, pas de nouvelle
  théorie ; brancher un compteur d'opcodes déjà existant (les panneaux `IP|`/`IB|`) sur le
  harnais de banc.
- **Opportuniste** : à faire **avant** de rebancer G1/G3 ci-dessous, sinon on optimise encore une
  fois sur un artefact qui ne voit pas le coût que A1 doit précisément faire apparaître.

---

## Tier 1 — Bugs actifs par défaut à fort impact

### G1. Portefeuille & sac à dos : objectif, borne, élection modale, fenêtre de cache
**Constats** : étape 3, #1 (la borne du branch-and-bound n'est pas une borne supérieure valide —
optimum non garanti), #2 (élection modale avant test de capital, confirmée toujours active), #3
(le sac à dos optimise le revenu, le tri exécuté reclasse encore par revenu/opcode — ni l'un ni
l'autre n'est le profit annoncé), #4 (le cache n'avance plus la fenêtre `capitalCeiling`).

C'est le nœud identifié par trois audits indépendants maintenant (soupçons de l'étape 3
d'origine du 2026-09-01, C31 sur un autre paquet, et cette revue) : **le code ne classe pas sur
ce qu'il prétend classer**, et c'est exactement le terrain sur lequel A1 (dénominateur de
classement selon la ressource rare) doit être construit — pas la peine de bâtir A1 sur un
objectif déjà incohérent.

- **Modèle : Opus 5, effort max** (Codex sol, high) — le plus gros et le plus risqué du lot :
  toucher l'objectif du sac à dos et l'ordre d'élection change quel projet est construit à
  *chaque* cycle de toute la partie. À traiter comme plusieurs commits séquentiels mesurés
  séparément (borne d'abord, puis objectif, puis élection modale), pas un seul gros diff — sinon
  aucun banc ne pourra attribuer l'effet.
- **Opportuniste, à greffer dans la même série de commits (pas le même commit)** :
  - **A1** (`docs/taches.md`, dénominateur de classement selon la ressource rare) — une fois le
    sac à dos aligné sur le profit, c'est le terrain naturel pour brancher la bascule
    argent/temps-de-chantier/véhicules.
  - **C38** (batch dynamique par filtre + re-classement) — a besoin exactement de ce que #4
    corrige (fenêtre de budget qui avance) pour recalculer un capital frais entre deux
    constructions du même passage.
  - **C39** (staleness catalogue/candidats/portefeuille/sac à dos), volet portefeuille — la
    fenêtre `capitalCeiling` figée (#4) est un cas particulier du problème que C39 pose en
    général.

### G2. Réélection incrémentale après abandon + invalidation événementielle
**Constats** : étape 2, #1 (`hadAbandons` ne se déclenche jamais avec les défauts — les vrais
échecs n'alimentent pas `passDiscards`), #3 (l'invalidation événementielle rafraîchit le
catalogue mais pas le portefeuille dérivé dans le même mois).

- **Modèle : Sonnet 5, effort high** (Codex terra, high) — deux points de câblage distincts mais
  du même ordre (« un événement se produit, la mise à jour en aval ne suit pas ») ; risque
  contenu à `main.nut`, pas de changement d'algorithme.
- **Opportuniste** : volet non-portefeuille de **C39** — c'est la moitié « détection de
  l'événement qui rend un rafraîchissement nécessaire » du sujet, à spécifier main dans la main
  avec ce correctif plutôt qu'en théorie d'abord.

### G3. Économie rail : recalcul post-tracé et devis réel
**Constats** : étape 5, #1 (le rail chiffre sa cinématique sur la distance candidate, jamais sur
le tracé A* trouvé — capacité, fréquence et temps de paiement restent optimistes dès que le tracé
dévie du Manhattan), #4 (le devis réel protège la trésorerie mais ne recalcule pas le classement
économique).

- **Modèle : Opus 5, effort high** (Codex sol, high) — le blast radius touche le dimensionnement
  de **chaque** ligne rail livrée, donc chaque véhicule et chaque revenu prévisionnel du mode
  dominant. La route fait déjà cette remise à l'échelle après choix des arrêts
  (`main.nut:1683-1691`) : c'est le patron à répliquer côté rail, pas une nouvelle conception.
- **Opportuniste** : **rebancer `road_multistop`** seulement *après* ce correctif, pas avant — le
  cap physique à 2 bus et son évaluation économique dépendent de la même famille de calculs
  (capacité/fréquence sur distance réelle) ; le rebancer maintenant mesurerait encore le biais de
  distance candidate côté route si le rail change entre-temps de base de comparaison.

### G4. Économie aérienne : refléter le trafic réellement capté par C33.2
**Constats** : étape 5, #2 (le plan air fixe la demande à 22 % avant construction ; les arrêts
C33.2 changent le captage réel après coup sans jamais revenir dans le modèle), #3 (le budget/ROI
air exclut le coût des arrêts C33.2 effectivement payés) ; étape 9, #3 (C33.2 classe la
production brute du bassin, pas le captage marginal ajouté par-dessus l'aéroport).

C'est le mode qui porte +104 % de valeur au banc officiel — l'écart entre ce qui a été mesuré et
ce que le modèle *dit* qu'il mesure est le risque le plus coûteux du lot si on continue de
piloter dessus sans le fermer.

- **Modèle : Opus 5, effort high** (Codex sol, high) — nécessite de faire remonter le nombre et
  le coût des arrêts posés dans `result`/la ligne, puis de reboucler sur la demande estimée ; pas
  un simple ajout de champ, ça change ce que `OpexAirEconomics()` doit produire.
- **Opportuniste** : aucun sujet backlog direct, mais **tout rebanc futur de C33.2** (variantes,
  extensions) doit attendre ce correctif pour être interprétable — à noter dans le prochain
  journal si un banc C33.x est relancé avant.

### G5. `rail_refleet` reste inatteignable
**Constat** : étape 6, #1 — `fleet_fix=0` par défaut bloque le chemin qui rendrait `rail_expand`
utile ; le second train et la double voie restent injoignables malgré la promesse du réglage
public. C'est le bug historique de l'étape 5 de la revue de 2026-09-01, jamais réellement fermé.

- **Modèle : Sonnet 5, effort high** (Codex terra, high) — correctif localisé (deux gardes à
  reconnecter), mais avec un historique de régression silencieuse (cf. `tree_planting`) : prévoir
  un banc de non-régression après coup, pas seulement un test de fumée.
- **Opportuniste** : aucun.

### G6. Recherche A* bloquée par un échec qui ne libère jamais le pipeline
**Constats** : étape 8, #1 (un `ABND`/`NOPA`/`DEAD` passe en phase `build` et attend un capital
qui ne servira jamais, gelant tout nouveau candidat rail), #2 (la branche « faible trésorerie /
précalcul » du plafond A* dynamique est du code mort — toujours appelée avec `false`).

- **Modèle : Sonnet 5, effort high** (Codex terra, high) — machine à états à corriger
  (`_continueRailSearch`/`_consumeRailSearch`), risque de repasser d'un blocage silencieux à un
  autre si mal testé ; prévoir le cas `ABND` explicitement dans la suite de test.
- **Opportuniste** : aucun.

### G7. Rollback aérien non transactionnel (destructeur sur le bras hub-à-hub)
**Constat** : étape 9, #1 — `OpexAirRollback` ignore A, et `PLANE`/`ORDFAIL`/`START` ne protègent
pas B par `reuseB`. Un échec sur un plan hub-à-hub (`reuseA=true, reuseB=true`) peut démolir un
aéroport existant et casser ses lignes antérieures.

- **Modèle : Sonnet 5, effort xhigh** (Codex terra, high) — pas complexe algorithmiquement, mais
  **destructeur** si mal corrigé : six sites d'appel (`STNFAIL`, `HANGAR`, `BFAIL`, `PLANE`,
  `ORDFAIL`, `START`) doivent tous recevoir la même règle `reuseA`/`reuseB`. Vérifier chacun
  explicitement plutôt que de généraliser par pattern-matching.
- **Opportuniste** : aucun — à isoler dans son propre commit vu le risque, sans rien y mélanger.

### G8. Terrassement d'exploration aérienne non attribué
**Constat** : étape 9, #2 — `OpexAirFindSite` nivelle réellement le terrain (et peut abattre des
arbres) pour des sites qui ne seront jamais élus, avant que le sac à dos n'ait rien choisi ; le
coût n'apparaît dans aucun ROI ni sonde.

- **Modèle : Sonnet 5, effort high** (Codex terra, medium-high) — soit rendre l'exploration
  purement en `AITestMode` (si l'API le permet pour ce test), soit attribuer le coût au projet
  qui a déclenché l'exploration plutôt qu'à personne. Choix de conception à trancher avant de
  coder — voir avec vous lequel des deux avant de lancer.
- **Opportuniste** : aucun.

### G9. Quarantaine fret→ville cassée + filtre feeders qui ignore le réglage C22
**Constats** : étape 7, #1 (`OpexAbandonedPairKey` renvoie -1 pour une destination ville, donc un
seul échec bannit tout le producteur pour toutes les villes du même cargo), #2
(`abandon_gen_filter=0` ne désactive pas le filtre des feeders, qui consultent la table sans
condition).

- **Modèle : Sonnet 5, effort medium** (Codex terra, medium) — correctif de clé localisé
  (`OpexAbandonedPairKey` doit inclure l'identité de ville) + un `if` manquant côté feeders.
- **Opportuniste** : aucun sujet backlog direct, mais ce correctif change le comportement
  effectif de **C22 et C33.3** (déjà remis à 0 par G0) — à re-mesurer avec eux si/quand ils sont
  un jour réévalués, pas avant.

---

## Tier 2 — Impact réel mais surface plus petite ou déjà conditionnel

### G10. Cycle de vie flotte air/route mineur
**Constats** : étape 6, #2 (ligne aérienne déficitaire ne rejoint jamais le rebut normal), #3
(sous-comptage de la flotte aérienne avant le premier rapport annuel).

- **Modèle : Sonnet 5, effort medium** (Codex terra, medium).
- **Opportuniste** : à faire dans le même passage que G5 (même zone de code, cycle de vie de
  flotte), sans le bloquer.

### G11. Constructeur maritime + feeder postal
**Constats** : étape 9, #4 (le navire construit n'est pas celui chiffré par le portefeuille), #5
(l'économie maritime ignore la longueur réelle du trajet navigable), #6 (feeder postal enregistré
même si le camion ne démarre pas), #7 (repli du feeder postal peut laisser une arête orpheline).

- **Modèle : Sonnet 5, effort medium** (Codex terra, medium) — surface bornée : le mode eau est
  limité à une ligne, le feeder postal est un mécanisme secondaire.
- **Opportuniste** : aucun — ce n'est pas là que le levier de volume se trouve, à ne pas
  sur-investir.

### G12. Catalogue : le choix de matériel avant ROI
**Constats** : étape 10, #1 (le catalogue aérien ne garde qu'un avion par type d'aéroport, sur
rang plutôt que ROI), #2 (route et rail réduisent chaque cargo à son matériel le plus capacitaire
avant même le calcul de ROI), #3 (le filtre de feeders utilise le mauvais objet catalogue —
premier type d'aéroport retenu, pas le hub réel ni l'extension C33.2 posée).

- **Modèle : Sonnet 5, effort high** (Codex terra, medium-high) — actuellement peu visible en
  vanilla homogène (dit explicitement par la revue), mais **c'est la porte d'entrée si le projet
  ajoute un jour des NewGRF** ; traiter maintenant pendant que le mécanisme est encore frais en
  mémoire coûte moins cher qu'y revenir après coup.
- **Opportuniste** : #3 (filtre feeders) partage son terrain avec **G4** (C33.2/aéroports) — à
  faire dans la foulée de G4 plutôt que dans un passage catalogue isolé.

---

## Tier 3 — Hygiène, à faire uniquement en passant

Jamais en tâche dédiée — greffer sur le commit du groupe qui touche déjà le fichier :

- Étape 4 #4 : 154 lignes de code mort (`OpexTensionMacroRegime`, `tension.nut:311-472`) — à
  supprimer si `tension.nut` est un jour rouvert (G14 ci-dessous), pas avant.
- Étape 5 #5 : `MAX_ROAD_VEHICLES` constante morte, commentaires trompeurs — à corriger en
  passant par **G3** ou **G12** (même fichier, `economy.nut`).
- Étape 10 #4 : type de rail « le plus récent » identifié par ID numérique — à corriger en
  passant par **G12** (même fichier, `catalog.nut`).

**Modèle pour ce tier, si isolé un jour : Haiku (Codex luna), effort low.** Ne mérite pas un
passage dédié à effort plus élevé.

---

## Tier « ne pas toucher maintenant »

### G14. Tension / prix d'ombre (étape 4, constats #1, #2, #3, #5)
Tous conditionnels à `tension_scoring=1` ou `shadow_pricing=1`, **tous les deux à 0 par défaut**.
C35.3/C35.4/C35.5 ont déjà été mesurés et rejetés au banc officiel (`docs/journaux/journal_2026-09-06.md`).
Corriger ces bugs ne changerait rien au comportement livré aujourd'hui.

**Ne pas ouvrir de tâche ici.** Seule exception : si A1 (dans **G1**) finit par vouloir
réutiliser une forme de prix d'ombre pour la bascule de dénominateur — auquel cas ces quatre
constats deviennent des prérequis de conception, à relire à ce moment-là avec **Opus 5, effort
high** (Codex sol) vu la subtilité de dualité LP déjà notée dans le plan de revue.

---

## Ordre d'exécution recommandé

1. **G0 + G0bis** — décision de revert à confirmer avec vous, puis banc rendu auto-contenu et
   instrumenté en profit/opcode. Sans ça, tout ce qui suit se mesure sur un artefact qui ment.
2. **G1** — le sac à dos et l'élection modale, en plusieurs commits mesurés séparément. C'est le
   préalable direct à A1.
3. **G3 + G4** en parallèle (fichiers disjoints : rail vs air) — fermer l'écart modèle/réalité sur
   les deux modes qui portent le plus de valeur avant de rebancer quoi que ce soit dessus.
4. **G5, G6, G7, G9** en parallèle (fichiers disjoints, chacun un correctif localisé à risque
   contenu) — G7 dans son propre commit vu le risque destructeur.
5. **G8, G10, G11, G12** quand la bande passante le permet — impact réel mais surface plus petite.
6. **G13** en passant, jamais seul. **G14** hors sujet tant que A1 ne le rouvre pas explicitement.
