# N75 EARLY C75 — seconde exception de ligne neuve en 1971–1972 (25/10/2026)

## Hypothèse et base figée

Worktree indépendant `.worktrees/nuit75-early-c75-second`, HEAD `83e436cc3db35ff18efb685ace4f97eb569f77b1`, aucun changement des réglages historiques. La campagne de référence `results/nuit75_master83e_baseline20x10_20261024.jsonl` contient 20 graines × 10 ans, départ 1970 sur carte 256². Aux 20 clôtures de décembre 1972, `profit_year` Opex moyen = **2 104 034,2 £/an**, et 4 % = **84 161,37 £/an** (ce n'est pas la base exacte de la future porte A). Les chantiers enregistrés par année et par partie sont en moyenne 11,8 (1970), 30,45 (1971) et 26,4 (1972).

Sur la télémétrie annuelle cumulée à fin 1979 de ces mêmes 20 parties : 1971, **147 arrêts `k_pass`**, 338 `cash`, 50 éligibilités C75 et 35 bypass consommés ; 1972, **333 arrêts `k_pass`**, 123 `cash`, 329 éligibilités et 184 bypass consommés. Toutes les 20 graines ont au moins un `stop_k_pass` en 1971 et en 1972. **Ces nombres décrivent des passes/événements, pas des couples source-destination distincts constructibles ni un revenu recouvrable.** La campagne n'est pas une comparaison ON/OFF et n'établit aucun gain causal. Le contournement C75 historique a déjà été adopté ; V104/réemprunt, V105b et V309 ne sont pas réouverts.

Hypothèse isolée : après qu'une passe a déjà consommé l'exception C75 habituelle, un second projet de **nouvelle ligne** encore réellement finançable peut être construit plus tôt. Un supplément d'au moins ~84 k£/an à trois ans exigerait, à titre d'ordre de grandeur, plusieurs lignes de ~30 k£ net/an moyen en plus dans les mondes concernés ; leur existence et leur disponibilité simultanée restent **à démontrer**, et les délais/économies sont particulièrement sensibles aux opcodes.

## Implantation

Le réglage `n75_second_newline_bypass` a trois valeurs, déclarées dans `ai/OpexAI/info.nut` **0 aux quatre difficultés** et chargées une fois depuis `settings.nut` :

- `0` **OFF** : le chemin normal de sélection et la consommation unique historique de `c75BypassConsumed` restent ceux de master. Aucune génération de signe/log N75 ni recalcul d'éligibilité N75.
- `1` **SHADOW** : lorsqu'une passe aurait été arrêtée par le plafond `K_pass` *après consommation du premier bypass*, mesurer l'éligibilité du second, publier `N75_EARLY_C75` et son signe `N5`, puis exécuter le **break historique**. Aucun second projet n'est lancé.
- `2` **ON** : même prédicat, mais autoriser **une seconde et dernière** exception `K_pass` pour ce passage. Le compteur `n75SecondConsumed` est propre à `_tryBuildProjects` et n'est posé qu'après le garde C80 ; les passes suivantes le réinitialisent. La construction normale peut continuer si le capital est *sous* `K_pass`, comme auparavant.

Le mécanisme ne s'ouvre qu'aux années **`OPEX_START_YEAR+1` et `+2`** (1971–1972 si départ 1970), après `c75BypassConsumed=true`, jamais pour `fleet`. Il recalcule `OpexAvailableCapital`, puis vérifie `OpexProjectFinanceCapital <= available`, le **plancher marginal C80**, la priorité des AIR défensifs C77 encore financés en aval, et pour AIR la vivacité de la paire et les sites physiques (`OpexAirBatchPlanStillLive`, `OpexAirBatchSiteStillBuildable`), en plus des vérifications normales de l'exécuteur. Aucun dépassement de réserve ni contournement de rollback n'est créé.

Pour RAIL, seuls les candidats munis de `c121PrepStock` **et** d'un `railPlan` prêt peuvent être sélectionnés par cette exception. L'argument `n75NoNewSearch` de `_tryBuildRailProject` interdit alors de lancer un nouvel A* si la validation du plan échoue et supprime le plan ; le chemin standard utilise `false` et demeure fonctionnel. Les candidats routiers et maritimes sont soumis aux mêmes gardes habituelles de construction après leur éligibilité.

Le journal `AILog.Info("N75_EARLY_C75 ...")` est actif uniquement avec ce réglage 1 ou 2, même si `DECISION_LOG=0` avec `probes=2`. Champs : `phase`, `mode`, `date`, `year`, `pass_tick`, `rank`, `key`, `profit`, `finance`, `cash`, `available`, `k_pass`, `reason`, `line`, `policy`. Les panneaux compacts `N5|pass_tick|rank|mode|phase|lineId` suivent le même identifiant de passe, avec E=éligible, T=tentative d'exécution, B=ligne bâtie, X=refus, P=en attente. Un candidat éligible en SHADOW n'est pas un chantier ; un T n'est pas une ligne bâtie ; **seul B avec identifiant de ligne atteste la construction dans la même passe**. Un B ne prouve pas que la référence n'aurait pas construit cette ligne à la passe suivante.

Décodage exploratoire hors jeu :

```powershell
python -X utf8 sweeps/analyse_n75_early_c75.py results/<campagne>_engine/variant_seed42_r0.log --out results/<campagne>_n75_exposition.json
```

Le script déduplique par fichier/année/clé de projet (`unique_candidate_keys`, `unique_built_keys`) et par passe/rang/clé pour les occurrences de E/T/B. `screen_rejected` distingue les refus d'éligibilité des `executor_rejected` après tentative. Il reconnaît aussi les panneaux `N5` s'ils sont fournis dans une transcription texte. Le nombre de signes présents dans les sauvegardes du harnais doit être vérifié ultérieurement ; l'analyseur de logs ne prétend pas lire lui-même le binaire de sauvegarde.

## Contrôles et limitations

Contrats Python ciblés `sweeps/test_n75_early_c75.py` : bornes et quatre défauts, OFF/SHADOW/ON, consommation historique inchangée et second compteur local, fenêtre relative au départ, exclusion flotte, C77/C80/sites AIR/cash, rail prétracé sans nouvel A*, issues AIR/ROAD/RAIL/WATER, contrôle statique de persistance et déduplication des journaux. Compléments existants : `test_c75_kpass_bypass.py`, `test_c75bis_v89_railfactor.py`, `test_c77_air_defensive_slot.py` et `test_v251_inventory.py` (plafond `AddSetting` corrigé 58 → 59 pour **ce seul nouveau réglage**). Le protocole runtime Save/Load n'est pas exécuté puisque Docker est exclu ; le nouvel état est **local à une passe** et n'ajoute aucun champ de sauvegarde, tandis que les dates et l'état historiques C75 restent persistés.

À vérifier en jeu avant toute conclusion : existence de projets *distincts* admissibles après le premier bypass, répartition AIR/RAIL/ROAD, taux `eligible→attempt→built`, capital réellement consommé, nouveaux `lineId` et revenus mûrs, retard de la référence au projet identique, événements de recherche rail et coût réel en opcodes/jours. Le SHADOW peut déplacer les ticks par son instrumentation et n'est pas un témoin causal.

Validation économique pré-enregistrée si exposition exploitable : duel OFF=0 / ON=2 sur **même bundle** 1970, carte 256², 40 graines × 3 ans, `gain_short`, métrique primaire `profit_year`, gain moyen relatif ≥4 %, Wilcoxon bilatéral exact `p<0,05`, IC95 bootstrap inférieur >0, perte maximale de valeur ≤5 %. Si porte A `pass`, porte B 20×10 `non_erosion`, garde de valeur 5 %. Ne pas inférer les profits d'un examen SHADOW ; ni modifier le défaut, ni créer une porte B après A ratée. **Aucun Docker/bench/commit/push/merge dans cette livraison.**
