# RAIL-LONG-FENETRES — RLW-03, declencheurs observables (22/10/2026)

## Etat : RLW-03 terminee sur le plan fonctionnel ; **non qualifiee economiquement**

Seule **RLW-03** est implementee ici. RLW-01/02 etaient deja disponibles,
RLW-04..11 ne sont **pas** raccordees. Aucun catalogue de longues liaisons,
promotion, recherche A* ni construction n'est ajoute. Ne pas assimiler les
conditions `eligible=1` a un investissement physiquement faisable.

## Fonctionnement

- `ai/OpexAI/rail_long_window_probe.nut`, charge apres la classe `OpexAI` :
  `RLW03_SHADOW <- false` est **OFF au defaut** dans `globals_post.nut`.
  La sonde ne tourne que si ce drapeau *source* et `DECISION_LOG` sont tous
  deux actifs, et si RAIL est autorise. Aucun 101e setting OpenTTD n'est cree.
- Une fois le **premier catalogue complet disponible**, la sonde fige les
  identifiants des 30 % de villes les plus peuplees (arrondi superieur, ex aequo
  par identifiant). La cohorte n'est jamais recomptée apres croissance des
  villes. L'instant exact du snapshot doit etre verifie par smoke : ce n'est
  pas une promesse de snapshot au jour 1 si le catalogue est differe.
- Une fois par mois, l'atteinte voyageurs est calculee sur **nos** lignes
  AIR si AIR est actif, et sur **nos** lignes RAIL voyageurs sinon. Les villes
  reliees sont celles des origines/destinations reelles, indexees en
  `O(n_lignes + n_cohorte)` ; on ne considere pas les gares ennemies ni les
  villes simplement a moins de 15 cases d'un aeroport.
- Un plateau passagers est candidat au declenchement seulement avec couverture
  `>= 800/1000`, croissance `<= 50/1000` mesuree entre **M et M−12 exacts**,
  et au moins 24 mois de jeu. Si une observation manque, le plateau est
  **inconnu**, pas zero. En rail seul, alternative : moins de deux projets
  pax courts finançables sur deux mois consecutifs, caisse mobilisable
  `>= 100 000 £`.
- Le fret est **independant** de la couverture AIR et des voyageurs : moins
  de deux projets fret courts financables, filtres abandon/proximite V217
  respectes, sur deux mois consecutifs avec caisse `>= 100 000 £`, age >=24
  mois. Les paires identiques sont dedupliquees et `2` signifie `>=2`.
- Le vivier court est **le vivier deja publie**. Son « startable » est un proxy
  (finançable, non abandonne, non bloque par `_tooClose`), **sans preuve de
  site, trace A* ni devis reel**. Ce compteur peut manquer des projets encore
  non publies ou sous-estimer la faisabilite physique. RLW-07 devra traiter
  cela avant toute substitution a un achat AIR.

## Journaux et sauvegardes

`RLW03_TRIGGER` contient `family`, `month`, `cohort`, `served`,
`coverage_pm`, `growth12_pm`, `short_startable`, `streak`, `capital`,
`age_months`, `eligible`, `reason` et `ops` pour pax ; le fret partage la mesure
d'opcodes de la passe et journalise ses compteurs. `-1` = manque de couverture
ou de vivier ; `growth12_pm=-1001` = pas de point comparable M−12.

L'etat serialisable `rlw03State` contient les identifiants de la cohorte, son
mois de fixation, l'historique de couverture borne a treize mois, les deux
compteurs de penurie et le dernier mois observe. Il est enregistre dans les
deux variantes de `Save()` **uniquement lorsque la sonde est active** et lu
par `Load()` sans acces au monde ; le controle effectif attend `Start()`.

## Validation et limites

Executer :

```powershell
python -m unittest sweeps.test_rail_long_window_probe sweeps.test_rail_long_window_policy sweeps.test_rail_long_early1 sweeps.test_analyze_rail_long_early1 -q
```

Les tests verifient garde OFF, modes independants, inconnus, cadence M−12,
liaisons des modules, et champs de Save/Load ; **ils ne compilent pas le
Squirrel et ne font pas un rechargement reel**. Un smoke opt-in en
multimodal puis RAIL seul est requis pour verifier les opcodes, erreurs
Squirrel, dates de snapshot, absence d'effet observateur, persistance
et qualite des signaux avant de cocher RLW-03 ou lancer RLW-04.

## Validation OpenTTD reelle (22/10, carte 256², seed 42)

Tous les essais sont realises dans le **worktree isole**
`results/rlw03_runtime_stage_20261022`, image `openttd-lab:latest`,
10 CPU maximum, un conteneur a la fois ; source figee par campagne.
Les fichiers de production conservent `RLW03_SHADOW <- false`.

| Essai | Bundle C66 (debut) | Resultat |
|---|---|---|
| `rlw03_probe_multi_42_3y_fix1_20261022` | `6bae66e0e449` | 3 ans complets, **72** `RLW03_TRIGGER` (36 pax, 36 fret), 0 erreur Squirrel, **9** mois `eligible=1` pour le plateau AIR/top30, **0** fret |
| `rlw03_probe_railonly_42_3y_20261022` | `6bae66e0e449` | 3 ans complets, **72** evenements (36/36), 0 erreur Squirrel, aucun signal passe (vivier court generalement non rare ou seuil de couverture non atteint) |
| `rlw03_probe_off_multi_42_3y_20261022` | `9eac05e96363` | Controle multimodal OFF, 3 ans complets, **0** `RLW03_TRIGGER` ; meme graine et settings de journal |

La cohorte figee comprend **13 villes** sur les smokes de la graine 42 ; elle
est constituee des le 03/01/1970 dans le premier essai multimodal.
La premiere comparaison de couverture a douze mois produit bien une pente
M−12, pas une valeur inventee en l'absence de temoin.

**Cout mesure, exclure toute conclusion de neutralite du sondage :**
`ops` par observation mensuelle atteint **63 815** en multimodal et **98 200**
en rail seul. Le compteur couvre le classement initial des villes, la
couverture et le comptage des projets courts ; le fret partage ce total.
Le scan n'est pas fait a chaque tick mais peut consommer plusieurs ticks
lors d'une observation. La garde OFF ne fait aucun de ces calculs.

**Effet observateur explicite :** l'essai OFF en multimodal donne
`profit_year=2 367 659 £`, `company_value=4 440 936 £`, contre
`2 463 221 £` et `4 537 192 £` avec la sonde ON. Ecart ON−OFF :
**+95 562 £/an** et **+96 256 £** sur **une seule graine**. Les deux bras
utilisent `probes=6`, mais des bundles distincts car le flag est un opt-in
*source* ; la difference n'est ni un rendement ni un gain a adopter.
Le panel ON altere potentiellement l'ordonnancement, y compris celui d'AAA.
Les futures mesures economiques RLW-10/11 devront etre sans cette sonde.

### Save/Load moteur

Campagne solo `results/rlw03_runtime_stage_20261022/results/rlw03_saveload_42_2plus1_fix1_20261022.json`,
`OpexAI[probes=6,save_full_state=1]` avec flag ON dans le worktree :
**25 sauvegardes en phase A**, rechargement effectif de `000000011.sav`
au 01/01/1971, **13 sauvegardes en phase B**, marqueur positif
`LOAD_RECONCILE`, aucun motif d'erreur Save/Load du moteur.
La phase B journalise **24** evenements RLW-03. Des son premier mois
(`month=23653`), `growth12_pm=769`, **et non `-1001`** : la cohorte
et l'historique mensuel anterieurs au rechargement ont donc ete conserves.

Premier lancement BLOQUE : le harnais historique injectait `-g` avec un
chemin de sauvegarde relatif a son propre dossier au lieu du dossier
temporaire d'OpenTTD. Le fix **uniquement dans le worktree** convertit
ce chemin en absolu (`Path(load_savegame).resolve()`) et donne la reprise
positive ci-dessus ; aucun changement de harnais partage n'est impose.
Une compagnie fantome (`is_ai=0`) apparait au rechargement, comme dans
les autres essais historiques de ce harnais. Elle interdit de traiter ce
roundtrip comme un test economique symetrique ; il reste une validation
technique de persistance.

## Conclusion RLW-03 et suite

**RLW-03 peut etre cochee comme instrumentation livree et validee en
execution** : les trois signaux sont distincts, l'observation mensuelle est
reproductible, OFF est inerte et les historiques survivent a Save/Load.
Ses seuils (top30/80%/5 points/2 observations) et la proxy de projets
`startable` sont toujours des hypotheses **non calibrees**. Le cout de la
sonde et son effet observateur sont etablis, pas elimines.

Avant de lancer RLW-04, prevoir **sonde desactivee dans toute campagne
economique**, budgets d'opcodes stricts pour l'enumerateur, et un protocole
d'exposition sans inference sur la simple presence du signal RLW-03.
Les autres fichiers et modifications concurrentes, y compris
RAIL-LONG-EARLY-1, sont conserves. Aucun commit ni push dans ce lot.
