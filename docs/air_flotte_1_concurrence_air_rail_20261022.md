# AIR-FLOTTE-1 — concurrence AIR / RAIL, mesure hors partie du 22/10/2026

## Décision

**Résultat : coexistence descriptive démontrée, éviction économique non identifiée.**
La mesure préalable demandée dans `docs/taches.md` a été menée sur les résultats
existants, sans lancer de partie. Aucun renfort AIR ni renouvellement ne peut être
qualifié à ce stade comme ayant **évincé** un projet RAIL réellement admissible,
finançable, constructible et plus rentable au même instant. Cela ne prouve pas que
le nombre d'évictions est nul. **AIR-FLOTTE-1 reste ouvert et aucun coefficient,
ordre du portefeuille ni défaut de l'IA n'est modifié.**

## Source et reproduction

- Base descriptive : les **40** journaux `reference_seed*_r0.log` (OpexAI de
  référence, pas le bras `rail_cal=1`) dans
  `results/rail_cal4_40x10_multimodal_pc_20261021_engine/`. Ce sont les dix
  années du banc multimodal **déjà achevé** le 21/10. L'analyse ne prétend pas
  requalifier cette campagne en intervention AIR-FLOTTE-1 ni remplacer ses
  critères économiques V102.
- Décodeur **hors jeu, sans mutation** : `sweeps/analyze_air_flotte1.py` ; tests
  de non-confusion des dates et de la chronologie :
  `sweeps/test_analyze_air_flotte1.py`.
- Commande locale depuis la racine :

  ```powershell
  python -B sweeps/analyze_air_flotte1.py 'results/rail_cal4_40x10_multimodal_pc_20261021_engine/reference_seed*_r0.log'
  python -B -m unittest discover -s sweeps -p test_analyze_air_flotte1.py -v
  ```

La jointure de classement est par **graine et date de jeu**, et ne prouve pas
qu'il s'agit de la même passe de sélection. Le décodeur distingue en plus
l'ordre d'apparition dans le journal pour éviter de prendre un classement
**postérieur** pour une opportunité antérieure. `PORTFOLIO_RANK` ne rapporte que
les cinq premiers projets et est émis lors de la publication du classement,
pas à chaque débit de trésorerie.

## Exposition effectivement observée

| Mesure dans les 40 références | Valeur |
|---|---:|
| `FLEET_PROJECT action=grow` avec avions effectivement ajoutés | **3 437** |
| Renouvellements `V252_REPLACE` | **1 680** |
| `RAIL_BUILD` | **1 086** |
| Lignes `PORTFOLIO_RANK` (tous modes, top 5) | **20 379** |
| Observations `C121_FLEET_MARGINAL` | **2 707** |
| Renforts avec au moins un RAIL dans le top 5 **le même jour** | **220 / 3 437** |
| Parmi ces 220, ROI **brut** du meilleur RAIL classé supérieur au ROI V161 AIR | **218 / 220** |
| Renforts précédés le même jour d'une publication `PORTFOLIO_RANK` quelconque | **1 / 3 437** |
| Renforts précédés le même jour d'une publication `PORTFOLIO_RANK` contenant du RAIL | **0 / 3 437** |
| V252 avec RAIL publié le même jour, avant ou après | **1 / 1 680** |

**Attention au sens chronologique :** les 220 comparaisons AIR / RAIL
par date mobilisent des classements publiés **après l'achat AIR**. Les
218 cas où le ROI brut RAIL est supérieur ne sont donc **pas** 218 rails
abandonnés ni 218 choix économiquement erronés. Parmi les 220, aucun
meilleur RAIL classé n'est construit ce même jour, mais l'absence de
construction n'établit ni son admissibilité au moment de l'achat, ni sa
constructibilité physique. Une sélection défensive C77 peut en outre primer
sur la comparaison des rendements.

**Renforts AIR :** ROI de classement publié par `FLEET_PROJECT` médian
**16 ‰** après V161 ; **2 987 / 3 437** ont un ROI publié inférieur à
100 ‰. Le ratio `1000 × v161_model / planePrice` (profit modèle *avant*
plafonnement V161, non rendement réalisé) a une médiane d'environ **462 ‰**.
Cela confirme que V161 affecte fortement l'estimateur : il ne suffit pas
d'invoquer une surévaluation du renfort AIR, ni de comparer les seuls `roi`.
Le vrai classement `fundScore` utilise la marge calibrée, le capital de
financement et `max(K_dec, capital)` ; le rang défensif C77 précède le score.

**Renouvellements V252 :** ces achats ne sont pas des projets `fleet` classés
avec le rail. `task_v252.nut` exige l'absence d'emprunt, l'absence de récent
arrêt projet faute de caisse, puis `cash − prix ≥ OpexCashReserve() +
OpexV249MaxListedCapital(projects)` ; cette réserve ne constitue pas un
test d'optimisation du ROI. `V252_REPLACE` fournit le prix, l'âge et le profit
historique de l'ancien avion, **pas** le gain marginal estimé du nouveau
ni sa revente effective. Impossible d'en calculer ici un ROI prédit/calibré
comparable au meilleur RAIL non financé.

## Réalisé à deux ans : ce qui est observable et ce qui ne l'est pas

Le journal `C121_FLEET_MARGINAL` mesure au rapport de l'année **achat+2**
un **écart de profit de ligne entière** par rapport à une baseline prise lors
du renfort, diminué de l'amortissement connu. Ce n'est ni une observation du
profit individuel de l'avion ni un bénéfice causal de deux années cumulées.

En liant **par ordre des lignes du journal** l'observation au **dernier renfort
antérieur de la même ligne**, en vérifiant `year = année_achat + 2`, et en
écartant tout remplacement V252 intermédiaire et toute observation ajoutant
plus d'un avion : **1 739** observations sur 2 707 restent liées, avec profit
différentiel médian **+10 044 £/an**, **567** différences négatives et ratio
indicatif médian `1000 × delta_profit_ligne / prix_avion` **+232,8 ‰**.
Les **958** observations avec renouvellement intermédiaire sont écartées ;
dix autres ne sont pas liées par ces conditions. Les changements de demande,
concurrence locale, flotte
voisine, effets d'âge et achats sur d'autres lignes rendent ce proxy **non
causal**. Ne surtout pas en inférer que V161 doit être relevé ou abaissé.
Une restriction sur les achats **postérieurs** au rapport pendant l'année
achat+2 produit en outre un biais de sélection : elle est incorrecte.

Pour un RAIL **jamais construit dans le monde observé**, `profit_year` de la
ligne hypothétique à +2 ans n'existe pas. Les mesures de lignes RAIL
effectivement construites ne sont pas des contrefactuels du candidat non
financé au moment de l'achat AIR. Le **ROI réalisé à deux ans des deux
options** demandé pour une comparaison causale ne peut pas être déduit des
seuls journaux historiques.

## Audit des canaux de décision

1. `scheduler_tasks.nut` et `projects_update.nut` : la passe `air_fleet` prépare
   des projets sans dépense immédiate ; les renforts sont injectés dans le
   portefeuille commun. `projects_builders.nut:143-252` utilise la marge
   C121 ou le réalisé, avec plafonnement V161 et provenance du profit.
2. `projects_selection.nut:741-850` : même sélection finançable pour AIR,
   flotte, RAIL et ROAD. `projects_selection.nut:959-1058` classe d'abord
   par classe défensive C77, puis `fundScore`. Le ROI brut de
   `PORTFOLIO_RANK` est distinct du score, et le coût de décision RAIL
   est affecté par les estimations pré-A*.
3. `task_projects.nut:202-323` : renfort construit par le chemin portefeuille,
   `FLEET_PROJECT` journalise prix et ROI. `task_v252.nut:7-165` : voie
   de modernisation hors portefeuille, filtre de caisse mais pas de ROI
   marginal. `task_report.nut:28-68` : observation marginale de ligne.

## Condition d'une suite défendable — sans changement de politique aujourd'hui

1. Si une nouvelle collecte devient nécessaire, commencer par une **sonde
   shadow à défaut 0**, sans modifier le tri ni acheter un avion de plus.
   Publier à **chaque achat AIR** un identifiant de passe et un instant commun
   (graine, tick, date, `_taskCycle`, version du portefeuille), le cash avant
   et après, la réserve, K_dec, les capitaux de décision et les scores de
   chacune des options. Publier les ROI **brut et calibré** séparément, avec
   provenance (C70, C121/V161, correction RAIL éventuelle). Inclure V252 et
   son coût net de remplacement / delta économique prédit, sans assimiler
   le profit de l'ancien avion au gain du nouveau.
2. L'alternative doit être le **meilleur RAIL de la même classe C77 qui n'a pas
   été financé au moment de l'achat**, pas simplement le premier RAIL du top 5
   publié plus tard. Journaliser ses filtres de budget, état du chercheur A*,
   faisabilité du site, raisons de rejet et durée de vie du cache. Ne pas
   calculer un ROI « réalisé » sur un rail non construit.
3. Pour le **réalisé** de l'alternative, seules des fourches du **même save**
   (AA/A/B, graines et horizon identiques, contrôle AA économiquement identique)
   peuvent établir une différence causale. Exiger le chemin complet
   sélection → tentative → construction/lineId → flotte → profit annuel
   après 24 mois ; qualifier explicitement les cas où le rail échoue à se
   construire. Ne pas inventer de rendement rail. Pré-enregistrer la cohorte,
   les seuils et la métrique avant tout nouveau banc.
4. Garder **RAIL-CAPEX-1** : pas de pénalisation AIR isolée. Sans effet
   d'éviction prouvé, aucune correction du score, du budget ni du défaut.
   Une éventuelle politique se qualifiera en multimodal selon V102 et les
   contraintes Docker de l'hôte ; les anciens résultats `rail_cal` demeurent
   `fail_primary`.

**Livré le 22/10 :** audit hors jeu, lecteur reproductible, tests ciblés,
documentation. **Non livré faute d'identification :** ROI marginal V252,
meilleur RAIL simultané et non financé, ROI réalisé du RAIL contrefactuel,
gain économique et changement de politique. Aucun Docker lancé.
