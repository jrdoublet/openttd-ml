# ESTIM-31 : validation du nouveau défaut (30/10/2026)

## Décision et identité

- Le vainqueur est `v161/mix_a200_r075_w15_slope`, **66,557726256 %**
  après 20 graines × 10 ans (OpexAI `profit_year` moyen 4 255 528 £,
  AAAHogEx-115 6 393 740,05 £). Les deux autres finalistes, sur duels
  indépendants et sains, obtiennent 65,921947052 % et 65,188575006 %.
- Les trois sources sont gelées depuis les 40×5, chacune avec 40/40 parties
  saines sur les véritables 20×10, 20 graines identiques, dix points annuels
  et manifestes, politiques, dates et SHA conformes. Les valeurs et l'évolution
  annuelle figurent dans `estim31_top3_20x10_20261030.json` et
  `estim31_top3_decade_trajectory_20261030.json`.
- Les seuls paramètres publics changés dans `info.nut` sont
  `estim_unifie=31`, `eb14_progressive=3` et `probes=2`. Les coefficients
  embarqués dans le bundle testé sont AIR2,00 / RAIL0,75 / poids15, profil
  RAIL incliné, V161 renfort *same-engine*, scan C121 complet N1, V249=2,
  EB2=0, charge AIR min=0. Les anciennes options restent accessibles par
  choix explicite (dont `estim_unifie=0`, EB14=0 et `probes=0`).
- Un seul mécanisme a effectué la promotion :
  `sweeps/estim31_promote_default_20261030.py`, dans
  `experiments/estim31-default-promotion-20261030` uniquement. Il revalide
  les trois duels et recalcule la SHA du bundle 20×10 réellement exécuté ;
  tous les fichiers OpexAI installés sont ceux du bundle qualifié, hors les
  trois réglages publics et leurs descriptions, et les quatre bibliothèques
  NoAI sont copiées et vérifiées par SHA. Preuve structurée :
  `estim31_default_promotion_20261030.json`.

## Contrôles réels et régression

- `sweeps.estim31_default_c121_contract_20261030` : PASS. Les fonctions
  historiques `OpexC121ChooseRoutePlane` et
  `OpexC121ScanRoutePlaneEngines` sont identiques octet pour octet à leur
  version Git `99f29d9c`. La substitution FullScan est limitée au bit 1
  d'ESTIM ; elle n'exploite ni l'élagage économique non prouvé ni le raccourci
  historique C121_GE sous ESTIM. Voir
  `estim31_default_c121_verified_20261030.json`.
- Vrai OpenTTD 15.3, NoAI 15, OpenGFX 7.1, image Docker figée, graine999 :
  `OpexAI` **sans aucun réglage explicite** et
  `OpexAI[estim_unifie=31,eb14_progressive=3,probes=2]` ont chacun réussi
  une sauvegarde et un rechargement (phase A un an, phase B un an,
  `LOAD_RECONCILE` présent). Le harnais crée une compagnie humaine fantôme ;
  on n'affirme donc pas une égalité numérique déterministe des deux runs.
  Les résultats réels sont sous
  `results/estim31_promoted_default_saveload20261030/default/` et
  `.../explicit/`.
- Tests ciblés promotion + C121 + ranking + trajectoires : **12 OK**.
  Suites de CI exécutées avec leur chemin d'import correct :
  `test_github_bench.py` **53 OK**, `test_qualification.py` **38 OK**,
  `tests/test_*.py` **4 OK dont 1 ignoré**. `git diff --check` : OK.
- **Limite de la grande suite de tests historiques :** `unittest discover
  -s sweeps -p 'test_*.py'` directement sur les nouveaux fichiers promus
  retourne **3175 tests, 84 échecs et 16 erreurs** (6 ignorés,
  2 échecs attendus). Beaucoup de tests comparent les chaînes exactes du
  *défaut historique 0*, les instantanés `ESTIM-1` et les anciens marqueurs
  C121 à la source désormais installée. Certaines autres erreurs viennent de
  fixtures avec fichier absent. Ce résultat **ne peut pas être annoncé vert**
  ni effacé ; il faut revoir ces attentes de tests séparément, en préservant
  les invariants historiques OFF. Les suites ciblées sur le nouveau défaut
  et les suites de CI ci-dessus passent. Journal local non publié :
  `.scratch_estim31_default_fullsuite_20261030.log`.

## Comptabilité et limites économiques

Les 40 sauvegardes finales de chacun des trois finalistes ont été contrôlées
par SHA pour les postes PLYR 1979. Achats de véhicules **nets de ventes**,
pas achats bruts ; le poste « Autres » inclut des dépenses municipales et ne
mesure pas les statues seules. Les nombres de moteurs 223/228/220 sont des
**stocks physiques**, pas des transactions. Voir
`docs/estim31_phase_combinatoire_20261030.md` et les trois fichiers
`docs/estim31_ten_*_accounts_1979_20261030.json`. Le ratio décennal reste
inférieur à 100 % ; le nouveau défaut est le meilleur des trois finalistes
qualifiés, pas un dépassement décennal d'AAAHogEx.

## Publication

**Publication effectuée avec succès à 11 h 14 environ le 30/10/2026** :
le commit de promotion `7160c6f57b6c10b66f5b83dd589693194aba58be`
a été poussé vers **`origin/master`** par fast-forward normal depuis
`99f29d9c858f390de6193978a4f12d3fbdb48127`, puis vers
`origin/experiments/estim31-default-promotion-20261030`. `git ls-remote`
a confirmé les deux références au commit `7160c6f5`. **Aucun push forcé,
checkout, reset ou écrasement du `master` local sale** n'a eu lieu.
Le nouveau défaut est donc effectivement publié sur le `master` distant ;
la copie locale sale de `master` peut rester à l'ancien commit tant que son
propriétaire ne l'a pas synchronisée en préservant ses travaux.

La grande suite historique sous le nouveau défaut n'est **pas** verte :
les tests qui supposent encore les anciens défauts et instantanés sont une
dette de compatibilité de tests à corriger indépendamment, sans annuler le
nouveau comportement validé par les trois duels, les deux Save/Load et les
suites de CI. La fullsuite a aussi été exécutée dans un worktree distinct
sur l'ancienne source de `origin/master` : **3124 tests, 2 échecs et
12 erreurs**, ce qui confirme que sa découverte globale comportait déjà
des difficultés hors promotion. Ne pas présenter cette situation comme une
réussite générale ni comme un blocage du push déjà réalisé.
