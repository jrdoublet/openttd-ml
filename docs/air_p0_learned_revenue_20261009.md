# P0 AIR — calibrage des recettes par observation (09/10/2026)

**Versionnement :** le prototype à corroboration par signe est figé au commit
`fb6868d3` de la branche `codex/p0-air-learned-revenue`. L'étude qui suit
propose une seconde règle, *leave-one-out*, implémentée localement après ce
commit. Aucun chiffre des anciens pilotes ne valide cette seconde règle.

## Périmètre et diagnostic

- Code de base local : `a0556ab685177480a38d4fe0062685bd33b8c640`, arbre de travail **non propre**, campagnes/patches concurrents à conserver. Le bundle du banc, et non ce SHA seul, établira la provenance.
- `OpexAirFarePerPax` applique en legacy `(PASS + 15 % MAIL) × 104 %`. Son équivalent dans la marge hub/hub est dans `air_planning.nut`. Le modèle causal C121 applique des tarifs distincts PASS/MAIL avec les capacités mesurées ; il **n'inclut ni 104 % ni 15 %** dans ce calcul principal.
- Au défaut : C121 `=1`, C70 `=1`, C121 réalisation adaptative `=1`. Les hubs C121 amortissent l'écart observé avec `0.75 + 0.25 × learned`. Le classement de nouvelles lignes applique ensuite C70 au **profit** déjà calculé par C121. Double correction structurellement possible, signe économique non établi.
- La recette réellement observée est `sum(GetProfitLastYear(vehicle) + GetRunningCost(vehicle))` par ligne au rapport annuel. `c121RawRevenueAnnual` est la prévision brute PASS+MAIL enregistrée à la construction. L'API utilisée ne fournit pas de comptage annuel exact des livraisons PASS et MAIL **séparées par ligne** : les volumes C121 sont des prédictions et ne seront pas présentés comme livrés.

## Intervention expérimentale unique

Réglage `air_p0_learned_revenue=0` aux quatre difficultés. Avec `=1` et C121 actif :

1. Pour les recettes AIR C121, ne retenir que les lignes âgées d'au moins deux ans, ayant toujours exactement leur flotte de construction. L'exigence initiale de deux années consécutives **sur la même ligne** ne produisait aucun échantillon admis sur cinq ans (`r1` et `r2`, graine42). La règle intermédiaire du commit `fb6868d3` exigeait deux lignes matures de même signe : c'était encore un seuil arbitraire de cohérence. La nouvelle règle vérifie directement la qualité prédictive par validation croisée.
2. Par bras AIR (`newpair`, `hubsite`, `hubhub`), le candidat est `somme(recettes observées) / somme(recettes brutes prévues)` des lignes admissibles. Pour chaque ligne tenue à l'écart, calculer ce ratio **à partir de toutes les autres** puis prédire sa recette. Comparer la **somme des erreurs absolues en £** à celle du modèle physique non corrigé (`k=1`). Appliquer le candidat seulement si sa prédiction hors-échantillon est strictement meilleure. **Exactement 1.0** sans seconde ligne indépendante, en cas d'égalité ou de défaite du candidat. Aucune pseudo-ligne, aucun lissage `75/25` ou `50/50`, aucune borne arbitraire. Révisé au rapport annuel et reconstruit après Load depuis les petits scalaires de chaque ligne. La correction porte sur la **recette brute** avant coûts opérationnels et amortissement. Elle ne prétend pas apprendre distinctement les quantités PASS/MAIL.
3. Pour une nouvelle liaison AIR dont l'économie C121 a déjà été calculée avec une correction de recette **effectivement différente de 1**, éviter la calibration C70/C82 supplémentaire du score de profit. À froid, C70 continue de calibrer le profit, comme sous OFF ; son arrêt dès la naissance d'une partie entraînerait une dérive sans relation avec l'apprentissage. Les projets flotte observés et les autres modes restent sur leur chemin existant. Les éventuelles corrections engine-only sont désamorcées sous le réglage afin de ne pas multiplier la correction de recettes.
4. Les deux chemins legacy `104 % / MAIL 15 %` utilisent, sous le réglage, le tarif brut PASS et la part MAIL d'une capacité réellement connue (zéro contribution MAIL si capacité inconnue) sans 104 %. Les capacités connues par ligne sont conservées à Save/Load sous ON. Sous OFF, les anciennes formules demeurent identiques.

## Protocole pré-enregistré (avant simulation)

- Comparaison figée sur **le même arbre** `OpexAI[air_p0_learned_revenue=0]` vs `OpexAI[air_p0_learned_revenue=1]`. Tous les autres paramètres aux valeurs courantes communes. Pas de modification du défaut pendant l'expérience.
- Santé : tests ciblés, smoke apparié 1 graine × 1 an (42), contrôle du bundle, exécution Squirrel, ligne Save/Load selon disponibilité et observation effective du facteur distinct de 1.
- Avant la porte A : diagnostic d'exposition apparié **graine 42 × cinq ans**, sans rôle dans la décision statistique, pour vérifier qu'au moins deux lignes matures d'un bras fournissent une validation croisée favorable et que le facteur quitte 1. Sinon, ne pas attribuer à l'apprentissage le moindre gain observé à la porte A.
- L'apprentissage exige deux exercices complets *après* la construction, potentiellement sans exposition pendant la porte A standard de trois ans. Pour cette expérience, **porte A pré-enregistrée à 40 graines × 5 ans**, `gain_short`, 80 parties, seuil +4 % sur `profit_year` terminal, Wilcoxon bilatéral p<0,05, borne inférieure IC95 bootstrap >0, garde valeur -5 %. Aucun choix a posteriori de l'horizon ; cinq ans sont nécessaires pour mesurer la correction apprise.
- Seulement après A complète/sainte/pass et exposition démontrée, porte B standard **20 graines × 10 ans**, `non_erosion`, borne haute IC95 bootstrap ≥0, valeur ≥ -5 %. Arrêter en cas d'échec A, état incomplet ou erreur de preuve.
- Profil Docker local : contexte `desktop-linux`, image `openttd-lab` (`sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`), `--cpus 10 --memory 8g --max-workers 10`, volume `openttd-lab-home:/home/lab`, **une seule campagne à la fois**.
- Mesures finales : delta Opex `profit_year`, moyenne/médiane/IC95/garde `company_value`, achats et nouvelles lignes AIR, répartition `C121_REALIZATION` des facteurs et nombre de lignes stables, opcodes. Les quantités effectivement livrées PASS/MAIL nécessitent une extraction physique supplémentaire, à déclarer non mesurées si indisponible. Un smoke sain n'est pas un verdict économique.

## Mesures et décision

Essais sous Docker local, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659` :

| Étape | Artefact / bundle | Mesure | Conclusion |
| --- | --- | --- | --- |
| Smoke première version 1×1, 1970 | `results/air_p0_learned_revenue_smoke_1x1_20261009_r1.json`, `45b797ab30dc…` | 2 duels complets ; Opex variante−référence +8 426 £/an et valeur +2,54 % | `diagnostic_only`, année initiale partielle ; santé Squirrel OK |
| Diagnostic première version 1×5, 1970–74 | `results/air_p0_learned_revenue_exposure_1x5_20261009_r1.json`, `76d03fe1b948…` | 2 duels complets ; +115 186 £/an, valeur −1,11 % ; *zéro* paire d'années stables admises, tous facteurs 1 | **Pas de preuve d'apprentissage** : le C70 retiré à froid suffisait à modifier le comportement |
| Diagnostic C70 conservé à froid 1×5, 1970–74 | `results/air_p0_learned_revenue_exposure_1x5_20261009_r2.json`, `6421111a5edd…` | 2 duels complets ; −96 092 £/an, valeur −6,75 % ; zéro ligne stable admise, facteurs 1 jusqu'en 1974 | **Pas de preuve d'apprentissage** ; ancienne règle de stabilité rejetée car sans exposition |
| Save/Load sous ON | `results/air_p0_learned_revenue_save_load_20261009.json` | 4 ans initiaux (48 saves), rechargement de janvier 1972, 2 ans de reprise (24 saves), `LOAD_RECONCILE` présent, aucun motif fatal requis | Charge et continue ; le test signale une compagnie fantôme sans attribution aux statistiques OpexAI ; aucun facteur appris à vérifier dans cet essai |

Tests : `sweeps/test_air_p0_learned_revenue.py` 5/5 verts ; `sweeps/test_c121_postbuild.py` 13/13 verts avant révision du critère d'exposition. La suite `test_c121_air_economics.py` a 2 échecs d'assertions statiques préexistantes (signature `OpexC121EngineEconomics` élargie par le patch concurrent du marginal 2→3) ; le troisième échec initial lié à notre réécriture de `persist.nut` a été corrigé. Aucun commit/push.

La **seconde règle leave-one-out** a été implémentée **après** les deux diagnostics 1×5 : ils ne qualifient donc pas ce code. `git diff --check` et les 5 contrats P0 passent sur hôte. Nouveau smoke moteur/Save-Load, exposition et porte A/B encore à effectuer ; Docker reste occupé par d'autres campagnes. Aucun verdict de gain ou de rejet statistique n'est tiré de 1 graine : **statut actuel non validé, défaut OFF inchangé**. Les comptages livrés PASS/MAIL séparés par ligne et les opcodes par décision ne sont pas présents dans ces artefacts ; seuls les revenus globaux des véhicules et les capacités physiques sont observables.

### Pourquoi cette alternative reste expérimentale

- La validation croisée porte sur les erreurs de **recette** des avions, pas sur le profit marginal du réseau. Les pertes de recettes sur les lignes voisines, la pression concurrentielle et les modifications de flotte intermédiaires peuvent rendre les lignes d'un bras non échangeables.
- `GetProfitLastYear + GetRunningCost` donne une estimation de revenu total de la ligne, sans séparer les tonnes de MAIL des passagers ni attribuer les variations au volume, au délai ou au tarif. L'apprentissage ne doit donc s'appliquer qu'à **une** grandeur : la recette brute agrégée, et seulement aux lignes à flotte de construction identique.
- Les points d'observation sont annuels ; une ligne construite en 1970 ne livre son premier exercice civil entier qu'au rapport de 1972. Le facteur demeure 1 jusqu'à une validation prédictive réelle. La présence de deux lignes est une exigence mathématique du test leave-one-out (chacune doit pouvoir être tenue hors apprentissage), pas un seuil de rentabilité choisi au hasard.
- Une validation croisée sur deux lignes peut encore surestimer la capacité de généralisation. Avant adoption, comparer les erreurs **de prévision future** à la référence, puis le profit et la valeur sur les deux portes appariées. Conserver le OFF actuel jusqu'à preuve contraire.

## P0 AIR — observation par époques de flotte (continuation du 09/10)

Le sous-échantillonnage sur la flotte strictement initiale écartait toutes les
lignes renforcées, précisément celles qui fournissent souvent le plus de
recettes. Le suivi ci-dessous étend l'échantillon **sans extrapoler de N0 à N** :

1. À la construction, mémoriser le revenu C121 **brut prédit**, le nombre exact
   d'avions livrés, leur moteur, les capacités PASS/MAIL mesurées et l'année.
   Les six scalaires `c121P0Epoch*` sont persistés avec la ligne.
2. À chaque ajout, remplacement complet ou reconstitution de crash, **fermer
   l'époque** en invalidant ses observations, puis reconstruire une cotation
   C121 à `fixedPlanes=N` pour la flotte effectivement en service.
   Réutiliser `OpexC121RefreshVisibleFleet` mais seulement sa branche à
   profondeur fixe : pas d'argmax, pas de modification de `targetAirPlanes`.
   La ligne étudiée est exclue des services préexistants aux hubs pour éviter
   le double comptage des appareils. Une cotation impossible **n'admet aucun
   ratio** ; aucun coefficient supplétif n'est utilisé.
3. Au rapport annuel, comparer moteurs, capacités PASS/MAIL et nombre
   d'avions de **chacun des appareils** avec l'époque retenue. En cas de
   variation non détectée (crash, refit externe, ancien savegame), invalider
   la cohorte et tenter une nouvelle cotation à partir du monde courant.
   N'admettre la recette du rapport d'année `Y` que si l'époque remonte
   au plus tard à `Y-2`. `GetProfitLastYear` porte sur `Y-1` :
   `Y+1` peut mélanger deux flottes, `Y+2` est le premier exercice entier.
4. Une ligne contribue **une seule observation récente** au bras
   `newpair/hubsite/hubhub`, indépendamment des observations antérieures
   d'époques abandonnées. La correction conserve la validation croisée
   leave-one-out avec départ strict `k=1`. Le OFF n'appelle aucune
   recotation ni comparaison additionnelle.

**Mesures préliminaires, non qualificatives :**

| Contrôle | Résultat |
| --- | --- |
| Contrats sous Docker `test_air_p0_learned_revenue.py` | **7/7 verts** ; `git diff --check` vert |
| Exposition appariée 1×5 seed42 | `results/air_p0_learned_revenue_epoch_exposure_1x5_20261009_r1.json`, bundle `6f19f9fb…`, deux parties complètes |
| Observations rapport annuel | 1972 : `newpair=3, hubsite=1, hubhub=0` ; 1973 : `6/10/6` ; 1974 : `4/4/18`, facteurs leave-one-out non neutres pour les trois bras |
| Delta économique exploratoire 1974 | Variante – référence **+150 368 £/an** ; ratio valeur **−5,587 %** : la garde −5 % serait dépassée sur cette graine seule ; **`diagnostic_only`** |
| Save/Load ON | `results/air_p0_learned_revenue_epoch_save_load_20261009_r1.json`, 60 sauvegardes phase A, rechargement du 01/04/1974, 24 sauvegardes phase B, `LOAD_RECONCILE` et aucun fatal ; facteur au reload `hubhub=0.6839419` (17 lignes), `hubsite=0.57352465` (4 lignes), `newpair=1` (9 lignes), variante d'arm rejetée en LOO ; compagnie fantôme du harness explicitement signalée |

**Qualification économique :** conformément au protocole enregistré avant
les nouveaux tests, la porte A reste **40 graines × 5 ans**, référence
`OpexAI[air_p0_learned_revenue=0]`, variante
`OpexAI[air_p0_learned_revenue=1]`, même bundle. Le seuil de gain terminal est
+4 % avec Wilcoxon bilatéral p<0,05, IC95 bootstrap inférieur >0, valeur
au moins −5 %. La mesure des passagers et sacs de courrier *livrés*
par ligne reste impossible à extraire des rapports financiers utilisés.

### Porte A terminée — `fail_primary`, rejet de la variante

- Campagne **`air_p0_learned_revenue_epoch_gateA_40x5_20261009_r1`**,
  résultat `results/air_p0_learned_revenue_epoch_gateA_40x5_20261009_r1.json`,
  bundle identique à l'exposition : **`6f19f9fb8fb76577d1acf23244b5ea3ec63f75ca5afc79c565c5a661d8279b09`** ;
  manifeste `f41212bd37d52fe47cc2a24da9321acfafa556549bbb44ed6a5b0f29114ffe34`.
- **40/40 paires et 80/80 parties complètes**, mêmes sources et graines
  canoniques V102. Profit terminal variante moins référence : **moyenne
  −20 488,4 £/an**, médiane **+12 509 £/an**, **21 victoires, 19 défaites**,
  Wilcoxon bilatéral **p=0,69482667** ; IC95 bootstrap
  **[−109 676,75 ; +73 408,975] £/an** ; gain exigé
  **+76 854,815 £/an** (+4 % du profit de référence).
- Ratio des moyennes de valeur d'entreprise **0,995618**, soit
  **−0,438197 %** ; garde −5 % satisfaite **en moyenne**, mais le gain
  principal et sa significativité **échouent**.
- Verdict calculé par le harness : **`fail_primary`**. **Pas de porte B**,
  aucune adoption, **`air_p0_learned_revenue=0` demeure le défaut**.
  Ces résultats réfutent un gain démontré du *lot* (époques de flotte,
  validation leave-one-out et retrait des forfaits legacy sous ON).
  Ils **n'isolent pas** la contribution propre de chaque sous-mécanisme ;
  la meilleure prédiction de recette n'assure pas de meilleurs investissements.
- Ces deux bancs étaient figés sur un arbre de travail partagé et sale
  (`HEAD 3a68c6e`), provenance vérifiable par leurs bundles/manifests ;
  le commit de ce chantier est volontairement **isolé des autres chantiers**.
  Ne pas assimiler son seul SHA à l'ensemble des sources simulées.
