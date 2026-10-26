# MULTI-1 — pré-enregistrement immuable, pilote ROUTE, 26 octobre 2026

**État : décision avant l'ajout de code et avant tout résultat ON.** Le constat
observable dans `multi1_analyse_20261026.md` est **147,12 véhicules ROAD AAA
contre 4,15 Opex en 1974**, quand le résultat AIR Opex reste productif. Cela
favorise H3, sans prouver que les nouvelles routes seraient aussi rentables.

## Contraste et mécanisme choisi

Nouveau réglage **`multi1_road_priority`**, déclaré aux quatre profils, **défaut
0** ; `0=OFF` historique ; `1=shadow` (éligibilité journalisée, ordre de choix
inchangé) ; `2=ON` (promotion bornée dans le TOP-K financé). Le pilote ne lit
aucune information de classement ou de financement d'AAAHogEx.

Intervention strictement localisée à la **fin** de
`OpexProjectSelectAffordable` dans `projects_selection.nut`, après classement
économique et politique P2 déjà appliqués ; ne ni recalculer les candidats,
ni altérer leur `profitAnnual`, `fundScore`, capital ou C77. Le mécanisme est
éligible seulement si `MODE_AIR && MODE_RAIL && MODE_ROAD` et années civiles
**1971 à 1973 incluses** (1970 protège le premier AIR ; 1974 sert à mesurer
l'effet). Chercher le premier projet ROUTE déjà financé aux rangs **1 à 7**
inclus du TOP-K (`best[0]` est la tête initiale). Le candidat doit être
strictement positif, **score économique `fundScore` ≥ 85 % de la tête** et
`profitAnnual` **≥ 60 % du profit annuel prédit de la tête** ; finance
`OpexProjectFinanceCapital(route) <= capitalBudget`. La tête doit avoir
`fundScore > 0`, `profitAnnual > 0` et **`OpexProjectDefensiveAirPriority(head)
== 0`** ; une tête défensive C77 reste prioritaire sans exception. Si la tête
est déjà ROUTE, ne rien modifier. Parmi plusieurs routes admissibles, prendre
la plus haut classée d'origine ; en `2`, la déplacer à l'index 0 une seule fois
dans le portefeuille courant ; en `1`, émettre l'éligibilité mais conserver
l'ordre. Aucune mémoire persistante : le TOP-K est déjà reconstruit à la
reprise et le réglage est relu au démarrage.

Journal d'exposition `MULTI1_ROAD_PRIORITY` : enregistrer uniquement quand un
véritable conflit conforme existe (année, action=shadow/promote, rang initial,
score/profit/capital route et tête), sans journal/logique supplémentaire sous
`0`. Le journal atteste une sélection modifiée, **pas** un chantier terminé.
Les constructions doivent être recoupées avec les parties et les véhicules
ROAD supplémentaires ; une différence de parc seule ne prouve pas l'identité
d'une paire construite.

## Validation à enchaîner, seuils figés

- **Contrat hôte** : `multi1_road_priority=0` n'ajoute aucune lecture d'API,
  aucune réorganisation ; `1` ne fait aucun déplacement ; `2` seulement dans
  la fenêtre ci-dessus, garde C77, marge économique et financement ; aucun
  changement des autres modes ou des défauts. Vérifier `Save/Load` court et
  complet (éventuelles fenêtres transitoires supprimées/reconstruites) et tous
  les tests Python. Smoke réel apparié **1×1**, graine **42**, années
  **1970** (`probes=2` dans les deux bras) pour compilation et santé.
- **Exposition** : cinq graines fixées **42, 100, 7, 999, 2026** × **5 ans**
  (1970–1974), OFF=0 contre ON=2, Opex vs même AAA en duels distincts,
  `--script-debug`, journaux et snapshots. Il faut **au moins 3/5 graines**
  avec promotion effectivement journalisée et **au moins 2/5** avec une route
  nouvelle dont la construction est traçable/attribuable. Sans cette exposition,
  conclure **NO-GO non exposé**, **ne lancer aucune porte A/B** ; ne jamais
  retoucher les seuils pour sauver le pilote.
- **Porte A** : uniquement après exposition, **40 graines canoniques × 5 ans**,
  une répétition, carte 256², début 1970, mêmes réglages aux défauts autres que
  le seul `multi1_road_priority` (0 vs 2), mêmes source/bundle et AAAHogEx.
  Règle officielle **`gain_short`** sur `profit_year` Opex ON − OFF à fin
  **1974** : **Wilcoxon exact bilatéral p < 0,05**, **IC95 bootstrap 20 000
  rééchantillonnages, graine 0, borne inférieure > 0**, delta moyen
  **≥ 4 % du profit moyen témoin**, garde ratio de moyennes
  `company_value(ON)/company_value(OFF) ≥ 0,95` ; 40/40 paires et quatre
  trimestres valides, `comparison_complete`, santé parfaite. Un échec de
  porte A donne `fail_primary` ou verdict brut correspondant, **pas de B**.
- **Porte B uniquement si A `pass`** : **20 graines canoniques × 10 ans**
  (1970–1979), une répétition, mêmes bras, règle `non_erosion` : IC95
  bootstrap **borne supérieure ≥ 0** et garde valeur ≥0,95, couverture et
  santé **20/20**. Le passage B autorise seulement une proposition à
  l'utilisateur ; **aucune adoption ni changement de défaut**. En complément
  reporter le ratio des profits Opex/AAAHogEx (moyennes et médianes de ratios
  appariés) face à l'objectif stratégique **75 %**, séparé du verdict A/B.

Un seul Docker simultané, **10 workers**, `--cpus 10 --memory 8g` sur ce PC,
manifeste/bundle figés, noms de campagnes nouveaux, conservation des artefacts
bruts. `git diff --check` et `python -X utf8 -m unittest discover -s sweeps
-p "test_*.py"` après chaque étape ; publication `origin/master` autorisée,
mais **aucun défaut modifié**. Ne pas rouvrir P1, P6 ni LATE-GAME-1.
