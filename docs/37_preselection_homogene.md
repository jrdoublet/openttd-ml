# Préselection homogène — audit du 2026-09-26

## État et provenance

Le défaut est celui de `docs/taches.md` au 25 septembre. Les résultats antérieurs au
9 septembre cités dans les commentaires éclairent la genèse, mais ne sont pas des
preuves de performance courante. Le constat des workers A* de la graine 100 (9/68)
est une mesure de divergence de classement, pas un résultat économique causal.
L'intervention est isolée par `homogeneous_preselect=0` au défaut.

| Mode / famille | Préclassement et filtres actuels | Origine des nombres / preuve récente | Verdict |
|---|---|---|---|
| Rail pax et fret | `candidates.nut:738-817` : profit/opcodes estimés ×1000, seuil `MIN_RATIO=500` (`:26`) ou fret 200, ROI ×15 et rotation 130/115/100/60 aux seuils 12/25/45 jours ; `OpexTopK` `:854`, `TOP_K=20` `:25`. | `git log -S MIN_RATIO` : `9f33e13`, `b22cb3e`, `358f0c8` et changements ultérieurs ; rotation : `358f0c8`. Le modèle d'itérations vient d'un banc OpenTTD 13.4 et les nombres de rotation d'une heuristique, sans validation postérieure au 9 septembre trouvée pour ce préclassement. | Score de préférence hétérogène. Top-K reste borne de coût ; seuil profit/opcodes demeure contrainte distincte du pathfinder, déjà active via `VIVIER_RATIO_FILTER` (`settings.nut:77`). Il faut mesurer combien elle rejette avant de l'abandonner. |
| `pax_near` | `candidates.nut:74-84,718-731,821-846` : distance ≤100, profit >−200, ratio 1, une tentative/an. | `git log -S PAX_NEAR_RATIO` : `27cce28`. Le commentaire rapporte 11/11 lignes rentables sur une sonde, mais ce n'est pas une mesure d'adoption actuelle. | Exception expérimentale à profit négatif ; le projet papier est refusé par `OpexProjectFromCandidate`. Ne pas la promouvoir avec un nombre magique. |
| Chaînes V88 | `candidates.nut:1350-1385` : ratio profit/opcodes + ROI×15, et 1 milliard si `v88_chain_force`. | `git log -S 'chainOpcodeRatio + (chainRoi * 15)'` : `d42128e` ; `docs/taches.md:47` : solo 5×8, seuil du duel non atteint. | Politique expérimentale explicite, défaut désarmé. Le nouveau tri ne reprend pas le milliard ; ne pas confondre avec les anciens bonus chaîne C32, retirés. |
| Route pax/fret | `candidates.nut:1610-1668` : profit ×1000 / itérations ; seuil `ROAD_MIN_PROFIT_ANNUAL` télémétré mais non éliminatoire ; `ROAD_TOP_K=48` `:1563`, top-K `:2077`. | `git log -S ROAD_TOP_K` et `-S ROAD_MIN_PROFIT_ANNUAL` : `2012860` ; aucune validation récente propre au ratio trouvée. | Même défaut de classement que rail ; distance, moteur, production, rentabilité positive et paire déjà servie restent des contraintes d'admission. |
| Fret par cargo | `candidates.nut:39-69` : tarif sur 20 tuiles et fret actif, tri par prix du cargo ; repli au prochain cargo actif `projects.nut:2620-2659`. | Code récent C77/C80 ; 20 tuiles sert à comparer les tarifs, pas les projets. | Ordre de génération, pas classement final des projets ; conserver. |
| AIR, plans et paires | `builder_air.nut:1918-1926` : ROI supérieur de 25 %, sinon profit absolu ; `OpexAirPlans` `:4192` et sous-routines classent/écrèment aussi les combinaisons de sites, avions et hubs. | Ancienne politique de débit/capital ; `docs/taches.md` V86 et V92 : variantes aériennes récentes perdantes. | Défaut distinct, hors de ce réglage rail/route : le plan est déjà agrégé par paire et sa réduction ne se remplace pas par un top-K sans revisiter la génération AIR reprenable. Contraintes de distance, site, créneau, desserte et abandon légitimes. |
| Eau | `builder_water.nut:18-25,330-483` : villes par population, au plus 12 ; paires connectées par BFS ; top 4 par ROI puis profit. | `git log -S WATER_PROJECT_POOL` : `3467851` ; commentaires G11 et C67 dans le journal du 21 septembre. Pas de mesure postérieure au 9 septembre justifiant le top 4 par ROI trouvée. | Même défaut de préférence que rail/route, mais génération et limite des paires couplées au BFS. À traiter séparément avec une duplication de la boucle ou dispatch hors boucle pour préserver l'identité du défaut. |
| Flotte AIR | `task_air.nut:613` : ordre `AIR_ROI_ORDER` pour les lignes ; projet de flotte construit via `projects.nut:463-523`. | C34.2 et C84/C85 dans `docs/taches.md` ; expériences récentes défavorables. | Ordre de traitement d'une flotte existante, distinct du top-K de nouvelles lignes. |

Filtres durs conservés : moteur et cargo disponibles, profit positif (hors
`pax_near`), géométrie/distance, site constructible, paire servie, origine
réutilisable, abandon et plafond réel du pathfinder. Les seuils de population,
distance et flotte des modèles restent propres à leurs modes ; ce travail ne
les présente pas comme des scores de préférence. Les feeders et Lakes sont
retirés ; les forfaits monopole +40 % et chaîne +35 % de C32 ne sont pas
réactivés. `V88_CHAIN_FORCE` reste une expérience distincte.

## Conception et mesure

Pour rail et route, `OpexTopKFund` construit le même projet papier que la
conversion du portefeuille (`OpexProjectFromCandidate`), calcule
`OpexProjectFinanceCapital`, puis `OpexProjectScore` sur le profit calibré
C70/C82 lorsque la sélection l'utilise. `homogeneous_preselect` substitue la
fonction de top-K au chargement des réglages ; au défaut, le corps historique
de `OpexTopK` et ses appels restent inchangés. Les égalités gardent l'ordre
d'énumération. Les seuils de coût d'A* restent des contraintes séparées ; la
sonde `ratioTooLow` et les compteurs C73 mesurent leur exposition. Aucun seuil
de préférence n'est ajouté.

Le coût additionnel est un projet papier et un calcul de capital/score par
candidat admis, à mesurer avec `probe_candidates_rail` / `probe_candidates_road`
sur les deux bras de même protocole. Le classement ne prouve aucun gain
économique. Mesurer aussi le recouvrement des top-K, le rang et `fundScore` des
projets construits et les lignes rail/route par graine avant le duel 5×6.

Limites : la sélection utilise aussi le plancher de profit relatif, la
finançabilité, les priorités défensives et éventuellement le dénominateur C69 ;
un score papier seul ne peut les prédire sans le portefeuille complet. Le
réglage ne change pas ces décisions. L'eau et AIR demandent des interventions
séparées pour conserver le chemin au défaut bit à bit.

## Lancements suivants (non exécutés ici)

Duel à confier à l'orchestrateur après diagnostic et vérification de santé :

```bash
rtk proxy python3 sweeps/run_c66_reference.py --campaign homog_preselect_duel_5x6 --reference "OpexAI[homogeneous_preselect=0]" --variant "OpexAI[homogeneous_preselect=1]" --variant-policy-id homogeneous_preselect_v1 --primary-metric profit_year --min-useful-primary-delta 50000 --value-guard-max-loss-pct 5 --max-workers 3 --seeds 42 100 999 1234 5678 --years 6
```

## Mesures solo (2026-09-26)

### 1. Identité au défaut sur code final
Vérification stricte de non-régression au défaut (`homogeneous_preselect=0`) :
- Graine 42 (1 an) : `427 019` valeur / `306 642` profit / 23 véh. / 20 gares (identité exacte bit à bit).
- Graine 100 (6 ans) : `6 014 565` valeur / `1 756 502` profit / 141 véh. / 56 gares (identité exacte).
- Graine 999 (6 ans) : `11 200 121` valeur / `3 685 733` profit / 138 véh. / 78 gares (identité exacte).

### 2. Instrumentation et sondes existantes
Extraction réalisée par `sweeps/diag_homog_preselect.py` (couvert par `test_diag_homog_preselect.py`) :
- Lignes construites par mode : tracées via `C50_CHRONO phase=project_built` et `C78_BUILD` sous `probe_portfolio=1,probe_events=1`.
- Véhicules primaires par mode : décodés via `physical_counters.py` / `bench_v2.py`.
- **Limites d'instrumentation des sondes existantes (aucun code Squirrel ajouté)** :
  - `fundScore` individuel des candidats rail/route : non journalisé dans `C50_CHRONO` (qui ne consigne que coût, profit et ROI).
  - Rang dans le top-K modal : le rang consigné dans `C50_CHRONO` est l'indice dans le portefeuille unifié (`this._projects.best`), pas le rang interne au top-K rail ou route.
  - Recouvrement des top-K ratio vs fundScore : aucune sonde n'émettant les listes complètes de candidats admissibles, ce recouvrement n'est pas mesurable sans sonde Squirrel dédiée.

### 3. Solo apparié 3×6 (graines 100, 999, 5678)

#### A. Solo propre sans sonde (`bench_v2.py`, résultats économiques non perturbés)

| Graine | Bras | Valeur (£) | Delta Val | Profit an (£) | Delta Prof | Véh (Rail/Rte/Air) | Gares |
|---|---|---|---|---|---|---|---|
| **100** | OpexAI (défaut) | 6 014 565 | réf. | 1 756 502 | réf. | 141 (9 / 12 / 120) | 56 |
| 100 | `homogeneous_preselect=1` | 6 435 764 | **+421 199 (+7,0 %)** | 1 887 682 | **+131 180 (+7,5 %)** | 137 (6 / 13 / 118) | 53 |
| **999** | OpexAI (défaut) | 11 200 121 | réf. | 3 685 733 | réf. | 138 (4 / 32 / 102) | 78 |
| 999 | `homogeneous_preselect=1` | 12 703 116 | **+1 502 995 (+13,4 %)** | 3 334 723 | −351 010 (−9,5 %) | 155 (2 / 35 / 118) | 75 |
| **5678** | OpexAI (défaut) | 12 730 467 | réf. | 4 004 709 | réf. | 157 (6 / 24 / 127) | 74 |
| 5678 | `homogeneous_preselect=1` | 12 990 679 | **+260 212 (+2,0 %)** | 3 845 253 | −159 456 (−4,0 %) | 142 (3 / 22 / 117) | 64 |
| **Moy.** | OpexAI (défaut) | 9 981 718 | réf. | 3 148 981 | réf. | 145,3 (6,3 / 22,7 / 116,3) | 69,3 |
| **Moy.** | `homogeneous_preselect=1` | 10 709 853 | **+728 135 (+7,3 %)** | 3 022 553 | −126 428 (−4,0 %) | 144,7 (3,7 / 23,3 / 117,7) | 64,0 |

Santé : 6/6 parties `run_ok=True`.

#### B. Solo instrumenté (`diag_homog_preselect.py`, `probe_events=1,probe_portfolio=1`)

| Graine | Bras | Lignes bâties (Air/Rail/Rte/Flotte) | Projets Rail bâtis (date, rang portefeuille, coût, profit, ROI) | Projets Route bâtis (date, rang portefeuille, coût, profit, ROI) |
|---|---|---|---|---|
| **100** | Défaut sondé | 72 air, 2 rail, 0 rte, 14 flotte | • 1970-07 : rang 62, coût 42,7k, prof 6,3k, ROI 148<br>• 1972-09 : rang 1, coût 46,1k, prof 46,5k, ROI 1009 | Aucun |
| 100 | Préselect=1 sondé | 101 air, 4 rail, 2 rte, 21 flotte | • 1972-12 : rang -1, coût 63,6k, prof 15,5k, ROI 244<br>• 1973-11 : rang -1, coût 46,2k, prof 19,8k, ROI 428<br>• 1974-01 : rang 1, coût 46,9k, prof 22,0k, ROI 468<br>• 1975-12 : rang -1, coût 46,8k, prof 13,2k, ROI 281 | • 1974-11 : rang 46, coût 13,9k, prof 3,2k, ROI 229<br>• 1975-03 : rang 3, coût 9,3k, prof 11,9k, ROI 1288 |
| **999** | Défaut sondé | 74 air, 2 rail, 0 rte, 17 flotte | • 1974-12 : rang -1, coût 51,4k, prof 47,8k, ROI 930<br>• 1975-11 : rang -1, coût 55,4k, prof 33,0k, ROI 596 | Aucun |
| 999 | Préselect=1 sondé | 67 air, 1 rail, 2 rte, 12 flotte | • 1970-12 : rang 52, coût 41,0k, prof 21,0k, ROI 512 | • 1970-07 : rang 1, coût 13,1k, prof 2,9k, ROI 224<br>• 1970-08 : rang 0, coût 13,1k, prof 2,7k, ROI 202 |
| **5678** | Défaut sondé | 54 air, 1 rail, 1 rte, 12 flotte | • 1970-06 : rang 0, coût 60,7k, prof 35,4k, ROI 582 | • 1970-06 : rang 0, coût 12,5k, prof 6,1k, ROI 488 |
| 5678 | Préselect=1 sondé | 52 air, 1 rail, 1 rte, 9 flotte | • 1970-06 : rang 0, coût 60,7k, prof 35,4k, ROI 582 (identique) | • 1970-06 : rang 0, coût 12,5k, prof 6,1k, ROI 488 (identique) |

### 4. Lecture et enseignements

1. **Volume rail réduit systématiquement** : sur les 3 graines au banc propre (sans sonde), le nombre de véhicules ferroviaires passe de 9 à 6 (graine 100), de 4 à 2 (graine 999) et de 6 à 3 (graine 5678), soit une réduction moyenne de 41 % du parc rail (3,7 vs 6,3 véhicules).
2. **Mécanisme d'évitement de mauvais chantiers précoces (graine 100)** : au défaut, un projet rail médiocre (ROI 148, profit 6,3 k£) est construit dès juillet 1970, mobilisant 42,7 k£ de capital initial au détriment de l'expansion aérienne. Sous `homogeneous_preselect=1`, ce projet n'est pas retenu ; le capital libéré permet une expansion aérienne continue (101 lignes air contre 72, +32 avions), générant un bond de +39,9 % de profit et +28,9 % de valeur d'entreprise sous instrumentation.
3. **Invariance lorsque le top rail/route est évident (graine 5678)** : les deux premiers projets rail et route construits en juin 1970 sont rigoureusement identiques (rang 0 dans les deux métriques). La trajectoire économique reste superposable (-0,3 % valeur, -1,3 % profit).
4. **Effet de cannibalisation de caisse par la route précoce (graine 999)** : le préclassement par `fundScore` fait émerger deux lignes routières dès l'été 1970 (rangs 0 et 1, profit ~2,8 k£, ROI ~210). Cette consommation de liquidité retarde l'investissement aérien précoce, se traduisant par un retard de profit final (-9,5 % sans sonde) malgré une forte valeur d'entreprise finale (+13,4 %).
5. **Valeur d'entreprise uniformément en hausse** : 3/3 graines gagnantes en valeur d'entreprise sans sonde (+7,0 %, +13,4 %, +2,0 %, moyenne +728 k£ / +7,3 %), ce qui traduit un bilan et une assise financière plus robustes, même lorsque le profit du dernier exercice clos fluctue.

