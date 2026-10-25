# AIR-GROW — correction du contrefactuel ancien/nouveau moteur (25/10/2026)

Travail limité au worktree `.worktrees/nuit75-air-grow-corrected`, branche
`nuit75-air-grow-corrected`, base `25f40f8e` (`origin/air-grow-marginal`).
Réglage `air_grow_marginal` conservé à **0** aux quatre difficultés. Des
diagnostics Docker ont été terminés, sans commit, push ni merge.

## Défaut corrigé

Dans `OpexAirGrowMarginalEstimate` (`ai/OpexAI/air_fleet.nut`), lorsque
`OpexAirBestEngineForLine` choisissait un moteur différent, `K_N` était évalué
comme si **tous** les avions déjà en ligne avaient gratuitement adopté la
capacité et la vitesse du moteur neuf. Le revenu marginal était donc mesuré
contre une flotte fictive ; biais de signe non garanti (une flotte supposée
plus rapide peut faire disparaître un gain pourtant réel).

Pour chaque sens et cargo PASS/MAIL, le calcul devient :

```
K_N  = (somme des capacités actuelles des N avions vivants) × R_existant
K_N1 = K_N + capacité du moteur acheté × R_acheté
ΔR   = tarif × (min(demande, K_N1) − min(demande, K_N))
```

`R_existant` vient des legs C117 complets observés (avec temps de chargement)
ou, faute de données, du modèle C121 **de l'ancien moteur**. `R_acheté`
réutilise la rotation observée pour le même moteur, sinon le modèle C121
**du nouveau moteur**. Les capacités existantes sont sommées par véhicule et
par cargo ; le nouvel avion utilise les capacités du moteur effectivement
sélectionné, selon les replis déjà présents. Le budget et l'amortissement
restent ceux d'un seul achat ; les quatre demandes restent indépendantes.

## Vérifications locales

- `python -X utf8 -m unittest discover -s sweeps -p test_air_grow_marginal.py -v` : **15/15 OK**, dont nouveaux cas moteur plus grand/rapide, plus petit/lent et capacités PASS/MAIL différentes ; contrat d'empreinte OFF réussi.
- `test_v161_fleet_net_marginal.py` : 7/7 OK ; `test_c121_engine_replay.py` : 2/2 OK ; `test_air_flotte1_shadow.py` : 6/6 OK ; `test_c121_air_economics.py` : 31/31 OK.
- `git diff --check` : OK. Revue des branches de calcul et des appels dans `task_air.nut`, `task_projects.nut`, `projects_builders.nut` et `OpexAirAddPlane`.

**Limites :** les contrats Python ne compilent pas le Squirrel. Il reste à
valider en moteur un achat effectif `oldEngine != targetEngine`, le repli
`clone_fallback` vers `oldEngine`, le chargement des deux cargos, l'absence
d'erreur et le coût d'opcodes avant tout banc économique. L'annualisation du
stock sur une fenêtre courte et le biais de demande partagée ne sont pas
réglés ici ; l'estimateur peut encore différer du ROI marginal réel. La porte
A 40×3 antérieure (`40131984205`, code non corrigé) avait donné `fail_primary`
(+4,16 k£/an, IC95 [−93,23 ; +92,68] k£/an, p=0,501). Elle ne qualifie pas
ce correctif. Exposition instrumentée, puis nouvelle porte A V102 appariée et
porte B si recevable sont nécessaires avant toute adoption.

## Instrumentation du choix moteur — après smoke corrigé 1×3

Le smoke corrigé annoncé par l'utilisateur (graine 42, trois ans) s'est achevé
**2/2 sans erreur de script**, avec un écart diagnostic ON−OFF de **+249 517 £/an**.
Dans le bras actif, 13 traces `phase=purchase decision=accept` et 159 traces
`phase=rank decision=accept` ont `K_N1 ≈ K_N × (N+1)/N` : **aucune exposition
prouvée à un nouveau moteur de capacité/rotation différente**. Ce résultat
économique n'est ni une validation de la formule corrigée ni une porte A.

Sous `DECISION_LOG` uniquement, chaque événement `AIR_GROW_MARGINAL` comporte
désormais quatre champs supplémentaires, sans nouvelle interrogation NoAI :

| Champ | Sens |
|---|---|
| `old_engine` | EngineID numérique de l'avion vivant utilisé comme ancien modèle ; `-1` si le garde retourne avant identification |
| `buy_engine` | EngineID numérique **prévu** par le sélecteur ou imposé en repli ; `-1` si inconnu |
| `rot_old` | `c117` si temps des legs existants observés, sinon `c121` si modèle ancien disponible ; `unknown` avant ce calcul |
| `rot_buy` | `c117`/`c121` selon le temps utilisé pour **l'avion ajouté** ; `unknown` avant ce calcul |

Ces deux EngineID représentent l'**estimation**, pas la preuve qu'un avion a
effectivement été construit. Le repli `clone_fallback` publie son propre moteur
acheté après refus du modèle visé. Les ID ne sont stockés dans `r` que si le
journal est activé ; ni Save/Load, ni score, ni décision ne les utilisent.

### Diagnostic préparé : 5 graines × 3 ans (ne pas lancer pendant la baseline PC)

Objectif : détecter une différence **réellement identifiée par EngineID**
entre ancien et nouveau moteur en phases `rank`, `execute`, `purchase` et
`clone_fallback`, et vérifier la politique sur plusieurs cartes. Protocole
figé : 42, 100, 7, 999, 2026 ; départ 1970, carte 256², 3 ans, une répétition ;
AAAHogEx-115 inchangé ; mêmes sondes `probes=258` et mêmes paramètres sur les
deux bras, `air_grow_marginal=0` contre `2`. Garder `--script-debug` pour
conserver `OPEX ... AIR_GROW_MARGINAL` et `--line-telemetry` pour interpréter
la trajectoire. Le verdict du lanceur **ne compte pas comme une porte A** :
`signs20` est utilisé ici seulement pour un diagnostic de cinq graines.

```powershell
python -X utf8 sweeps/run_c66_reference.py `
  --mount-root ../.. `
  --campaign airgrow_mixed_diag_5x3_20261025 `
  --reference "OpexAI[air_grow_marginal=0,probes=258]" `
  --variant "OpexAI[air_grow_marginal=2,probes=258]" `
  --variant-policy-id airgrow_mixed_diag `
  --decision-rule signs20 --min-useful-primary-delta 0 `
  --primary-metric profit_year --value-guard-max-loss-pct 5 `
  --seeds 42 100 7 999 2026 --years 3 --repeats 1 `
  --start-year 1970 --map-size 8 `
  --max-workers 5 --cpus 10 --memory 8g `
  --script-debug --line-telemetry
```

Une fois le banc terminé, lecteur **sans Docker** (logs moteur du bras actif) :

```powershell
python -X utf8 sweeps/analyse_air_grow_engine_choices.py `
  "results/airgrow_mixed_diag_5x3_20261025_engine/*.log"
```

Le lecteur affiche par phase le nombre de traces, d'acceptations, de paires
d'EngineID valides, de `old_engine != buy_engine`, de telles acceptations, et
la provenance des deux rotations. Un `fallback` ou un ID `-1` ne compte pas
comme exposition valide. **Ne pas additionner les phases** : une proposition
peut apparaître successivement en `rank`, `execute` et `purchase`.
Même `phase=purchase decision=accept` prouve l'estimation, pas l'achat réussi ;
vérifier `V252_ENGINE action=reinforce`, les états de flotte / tickets d'achat
et les savegames pour attester le changement physique de moteur. Examiner les
erreurs Squirrel et la complétude des dix duels avant tout raisonnement
économique. En l'absence d'exposition observée aux moteurs différents,
**ne pas engager une nouvelle porte A 40×3** sur ce correctif.

### Coût d'opcodes et limites de neutralité

- `DECISION_LOG=0` : seulement deux nouveaux tests du drapeau (un après
  sélection des moteurs, un après calcul des rotations) ; **aucun** `rawset`,
  concaténation ni appel API supplémentaire.
- `DECISION_LOG=1` : quatre `rawset` de scalaires/chaînes par estimation
  suffisamment avancée, quatre contrôles d'existence/lectures en sortie, et
  concaténation d'environ 60–80 caractères par log. **Zéro appel NoAI et zéro
  parcours supplémentaire**, nombre de messages `OpexDecide` inchangé.
- Pas de coût algorithmique significatif attendu face aux accès C117/stations
  et au journal moteur existant. **Le coût précis d'opcodes n'est pas mesuré**
  sans exécution : même une instrumentation pure peut décaler les ticks et
  changer la trajectoire d'un duel. Les deux bras du diagnostic doivent utiliser
  exactement le même code instrumenté et les mêmes sondes.

## Diagnostic 5×3 terminé — exposition réelle et décision

Campagne effective `nuit75_airgrowfix_exposure_5x3_20261025`, bundle `20aed72968d8ab7a5afdabad3ce9aeea15f6c7f42b482ac5f509717dea88e389`, manifest `2cbeeb135ac24622d38af4ce66daff9e1da504bd05a462b5ab6cbad323dcdadd` : **5/5 paires et 10/10 parties complètes, zéro erreur de script, aucun `failed_runs`**.

Le lecteur `sweeps/analyse_air_grow_engine_choices.py` sur les logs moteur de cette campagne a compté, dans le bras actif, **1 623 décisions `rank` acceptées avec `old_engine != buy_engine`** parmi 1 686 acceptations à deux moteurs identifiés, et surtout **39 acceptations `purchase` ancien/nouveau moteur différents** sur 54 achats à identifiants valides. Répartition des 39 : 7/4/14/6/8 pour graines 42/100/7/999/2026. Les 39 montrent `rot_old=c117`, `rot_buy=c121`, et au moins une capacité annuelle `K_N1` divergent de `K_N × (N+1)/N` de plus de 0,5. Le correctif est donc réellement **exposé à trois ans**, contrairement à l'échantillon plus étroit du smoke initial. Sur 55 événements `V252_ENGINE action=reinforce` du bras actif, 37/39 intentions `purchase` différentes ont une correspondance même ligne/moteur à 0–1 jour ; 2 ne sont pas rapprochées sous trois jours. Cela ne démontre pas à soi seul une construction causée par la correction.

Économie descriptive ON−OFF OpexAI : **−99 333,6 £/an**, médiane **−77 261**, **1 V / 4 D**, Wilcoxon **p=0,3125**, IC95 bootstrap **[−258 223,8 ; +68 255,2]**, valeur compagnie **−8,3866 %** (garde de −5 % non tenue). La sortie reste `diagnostic_only` : ces cinq graines ne constituent pas une porte A V102. La version initiale avait déjà une porte A 40×3 `fail_primary` (+4,16 k£/an, p=0,50137), qui n'est pas requalifiée.

**Décision : suspendre la nouvelle porte A du correctif**, à défaut de fait causal favorable suffisant et compte tenu du diagnostic défavorable. Ne rien adopter ni changer le défaut 0. La correction reste isolée et testée, mais **aucun gain économique n'est établi**.
