# Décisions et résultats antérieurs — synthèse au 30 septembre 2026

**Statut : journal de synthèse, pas une file de tâches.** Ce document remplace les
récits répétés dans l'ancien `taches.md`, sans nouvelle mesure ni adoption.
Les fiches liées restent les sources détaillées ; les chiffres rapportés ne sont
pas revalidés ici. Les résultats antérieurs au 9 septembre ne font plus preuve.
Actions courantes : [taches.md](../taches.md). Navigation : [index des journaux](README.md).

## 1. Défauts adoptés et décisions dérogatoires

| Famille | Décision conservée | Source des mesures et limites |
|---|---|---|
| C68 | Choix d'avion par route adopté ; ne pas relancer son adoption | [Journal du 20](journal_2026-09-20.md), [revue AIR](../revue_air_c68_c69_c84_c85_v92_2026-09-24.md) |
| C69 bis / C70 / C75 | Dénominateur de capital, calibration par mode et chantiers multiples adoptés le 21 ; exception utilisateur à 14/20, pas `signs20` réussi | [Goulot](../11_goulot_decision.md), [calibration](../12_calibration_par_mode.md), [volume §10](../16_bilan_volume.md) |
| C76 / mémo urbain / régénération par mode | Actifs par défaut ; adoption au titre des opcodes, pas du seuil +50 k£/an | [Nuit du 24](24_nuit_2026-09-24.md) : mémo −4,2 k£/an, 9/11 ; mode regen +52,2 k£/an, 11/9 ; garde valeur tenue |
| C77 corrigé | Chemin permanent, anciens trois drapeaux supprimés ; injection de flotte et mise à jour AIR ciblée permanentes également | [Nuit du 23](23_nuit_2026-09-23.md) ; cumul C77 exploratoire 60 graines, 34/26, p=0,366294, pas qualification `signs20` par ce cumul |
| Index hub C80 | Actif ; gain d'opcodes et neutralité économique | [Nuits du 23](23_nuit_2026-09-23.md) et [24](24_nuit_2026-09-24.md) |
| C75 bis | Bypass unique de `K_pass` pour nouvelle ligne finançable, jamais flotte ; défaut 1 par décision du 25 | [Caisse](../33_caisse_1970_1972_et_leviers_aaa.md) ; 80 paires exploratoires +44,4 k£/an, 46/34, p=0,218518 : gain non significatif |
| Rail : finance / V89 | Biais de financement 100, distinct du facteur terrain 170 ; V89=1 par décision du 26 comme dépendance de V88 | [V89](../28_v89_debit_recherche_rail.md), [C67](../c67_cartographie_contrat.md) ; finance +47,3 k£/an 12/8 ; V89 −7 k£/an 11/9, note −12,25 points ; décisions utilisateur malgré `fail_primary` |
| V90 / V91 | Pathfinder rapide=1, poids A*=120 ; poids 150 rejeté | [V90](../29_v90_pathfinder_rail.md) : −8 % opcodes/itération, adoption utilisateur sans duel ; [V91](../30_v91_astar_pondere.md) : 20×10 neutre à 120 |
| C83.1 | Six villes surveillées ; ne pas confondre avec `c83_fixes` | [C78/C83](../22_c78_lignes_vs_aaa.md) ; +165,3 k£/an, 15/5, valeur +6,78 % |
| C87 / V94 / C96 | Garde de rentabilité des bus, préfiltre de sites AIR et placement catchment actifs | [C87](../26_c87_bus_et_lignes_aaa.md), [V94](../30_v94_air_site_list.md), [C96](../36_c96_air_site_catchment.md) ; C96 20 paires saines après reprise d'une paire sur même bundle, +211,3 k£/an, 15/5 |
| C115 | Défaut 1 **temporaire**, décision utilisateur du 27 ; protégé le 30 | [C100–C115](../39_c100_c101_air_physical_engine_choice.md) ; +154,9 k£/an, 13/7, p=0,263176, valeur +18,29 %, verdict `fail_primary` : activation n'est pas qualification statistique |
| C121 aérien seul 1re année / prépa rail / 1 ou 2 avions | `c121_catalog_air_first_year=1`, `c121_air_first_year_rail_prep=1` et `c121_air_one_or_two_planes=1` par défaut, **décisions utilisateur du 2 octobre** sur la branche `c121-catalog`, sans banc de qualification ; inertes hors bras C121 (exigent `c121_air_economics` et `c121_catalog_incremental`, à 0 par défaut) ; `c121_flat_bootstrap` reste à 0 | [Journal du 2](journal_2026-10-02.md), [tâches](../taches.md) ligne « Construire plus vite en 1970 » ; diags locaux non qualifiants : prépa rail 3 tracés sur 15 servis sur 5×2, 1 ou 2 avions Δ `profit_year` +112 k£ en 1970 (4/5) mais −53 k£ en 1975 (2/5) sur 5×6 |

## 2. Diagnostics terminés et pistes non retenues

| Sujet | Résultat / décision finale | Source |
|---|---|---|
| C56 / eau | Ancien gel Lakes corrigé puis bibliothèque retirée le 21 ; BFS borné actuel, pas de graine à retirer du banc | [Journal du 21](journal_2026-09-21.md) |
| C67.3–.6 | Services carte/oracle livrés ; S=5 provisoire ; aucun consommateur métier assez exposé. Eau : 6 paires en 256², aucune en 512² ; rail : 16 lignes sur 20 parties, coût pré-A* proche du réel | [Contrat et mesures](../c67_cartographie_contrat.md), [23](journal_2026-09-23.md), [24](journal_2026-09-24.md) |
| C80 workers | Pile rail/ville 20×10 +32,6 k£/an, 12/8, non qualifiée selon C80-6 ; défauts 0 | [C80](../18_orchestrateur_double_registre.md) |
| Stock A* / préclassement | Worker complet duel 5×6 −202,5 k£/an, 0/5, valeur −10,8 % ; préclassement 20×10 −39,2 k£/an, 9/11 ; pause, défauts 0 | [Workers](../36_astar_workers_conception.md), [préclassement](../37_preselection_homogene.md) |
| V88 | Solo débloqué jusqu'à 5/5 graines livrant des biens, mais trois duels perdants ; financement étape 1/profit deux étapes et faux `builtCount` après simple lancement A* à revoir avec les workers | [V88](../27_v88_chaines_biens.md) ; suspension maintenue |
| C83 variantes | Préemption et réserve par ville non retenues ; `c83_fixes` en bloc −28,8 k£/an 10/10 au 20×10 ; portée du filtre corrigée mais pas cause unique du recul | [C78/C83](../22_c78_lignes_vs_aaa.md) |
| C76 lean / rotation fret / C80 marginal | Mesurés et non retenus ; l'horloge réactive/workers est déjà implémentée | [Nuit du 23](23_nuit_2026-09-23.md) ; ne pas réintroduire les étapes historiques comme travaux à faire |
| V86 / V92 / V93 | Corrections de cannibalisation, service AIR et demande/plancher perdantes ; V93.2 non fusionné selon les comptes rendus | [Nuit du 24](24_nuit_2026-09-24.md), [V92](../31_v92_choix_service_air.md), [V93](../32_v93_petits_aeroports.md) |
| C84 / C85 | Deux prototypes non adoptés ; C85 doit précéder C84 si reprise autorisée | [C84](../24_c84_air_target_fleet.md), [C85](../25_c85_air_equipment_frontier.md) |
| C81 / C82 / dépôt rail | Aucun lancement dû du seul fait de la fin d'un autre banc ; dépôt rail neutre, défaut 0 | [Nuit du 22](20_nuit_2026-09-22.md), [nuit du 24](24_nuit_2026-09-24.md) |
| V95 AIR / C97 | Sonde terminée, mécanisme économique non démontré ; pas de causal sous cette forme | [V95 AIR](../35_v95_air_post1973.md), [C97](../37_c97_air_c69_engine_probe.md) |
| C98 / C99 | Modèle sous-prédictif observé ; vitesse seule sur-prédit ; pas de correction de vitesse isolée | [C98](../38_c98_air_realized_probe.md) |
| B9/G4 | Diagnostic clos, pas de traitement actif ; fiche finale canonique : 461 builds, 923 endpoints dont un endpoint de sonde orphelin | [B9](../40_b9_demande_catchment_20260927.md) ; chiffres rapportés, non recalculés |
| C100 / C101 / C103 / C114 | Physique et choix moteur isolés rejetés ; replay complet positif mais 20×10 non qualifié | [C100–C115](../39_c100_c101_air_physical_engine_choice.md) |
| C119 | Paiement Manhattan/temps améliorent la prédiction ; 20×10 +70,9 k£/an, 11/9, `fail_primary`, défaut 0 | [C119](../42_c119_air_income_model_20260928.md) |

## 3. C116, C118 et C120 — chronologie condensée

C116.1 marginal/gate : −176,5 k£/an en 5×6 ; score C69 direct : −234,4 k£/an.
C116.2 projet débloquable : −330 k£/an ; exception graine 100 +623,7 k£/an,
à analyser face à 999/1234/5678 avant nouvelle règle. C116.3 : texte chiffré
corrompu, aucune valeur restaurée par supposition. C116.4 post-sélection :
portefeuille C68 conservé, clone d'exécution moins capitalistique ; smoke
`smoke_c116_decoupled_1x3_20260927_r1` contre C115 −166,6 k£/an, valeur −11,55 %,
mais contrôle `smoke_c116_decoupled_vs_c68_1x3_20260927_r1` positif face à C68.
Les capacités rapportées −305/−95 restent **non réconciliées**. Source conservée :
[extraits originaux](../archives/c116_extraits_originaux_non_autoritaires_2026-09-30.md).
Décision : C116=0, aucun nouveau 5×6/20×10 sous ces formulations ; C115 conservé.

C118 mêlant équipement et objectif territorial : smoke r2 −50,3 % de profit,
−56,9 % de valeur ; retard dès le premier mois avec le même moteur, donc pas
uniquement une cause équipement. Analyse `sweeps/analyse_c118_territorial_smoke.py`.
C120 isole le classement AIR↔AIR : r4 comportait encore un mélange des modes,
donc non qualifiant malgré la couverture accrue. R8 préparé, non lancé selon le
dernier compte rendu ; gel jusqu'à amélioration du modèle, pas de 5×6.

L'interprétation « replay C100 = régulariseur de capital » reste une hypothèse
de mécanisme, pas une preuve causale. Les variantes ne justifient pas un détour
automatique vers MAIL-only ou une désactivation de C115.

## 4. C121/C122 — dernières décisions des 29–30 septembre

La [fiche C121](../43_c121_air_economics_shadow_20260928.md) et le
[journal du 29](journal_2026-09-29.md) remplacent les étapes shadow initiales.
Le causal C121 est raccordé, mais non adopté. `soft25` contre C115 améliore le
gap AAA tout en dégradant Opex (−287 k£/an, valeur −15,81 %) ; `defeff` perd
également. Pas de 20×10 ; classifieur `race/efficiency` conservé comme diagnostic,
pas permission d'altérer l'économie ni de promouvoir un réglage.

[C122](../44_c122_air_regime_priority_20260929.md) : priorités topologiques et
territoriales .1–.3 non qualifiées ; certaines versions n'ont aucune promotion
effective. .4 sauve localement Town 18 après `siteA_unbuildable` par un retry C77
borné, mais le bilan global ne qualifie pas cette règle. **Stop au smoke, défauts 0,
ni 5×6 ni 20×10.** Identifiant de bundle ambigu : récupérer le manifeste, pas deviner.

[Catalogue C121](../catalogue_decoupe_phase2_20260929.md) : phases 2/3 mesurées,
cadence et trésorerie initiales améliorées mais décrochage en 1972. Renforts stock,
territoire d'abord et deux avions + chargement complet ne rattrapent pas la référence.
Deux avions sans chargement complet restent non isolés, pas essai autorisé d'office.
Save/Load non vérifié, identité au défaut non exacte ; **ne pas toucher C115**.

## 5. Diagnostic ordonnanceur P1/P2/P5 — distinct de V95 AIR

Synthèse des tableaux retirés de la liste de tâches, mesures historiques sous
`probe_scheduler=1`, sensibles au décalage des suspensions NoAI :

- P1 `results/diag_v95c_idle_4y_s42_100_999.json` : 3 860 sélections complètes
  1970–72, 256 utiles / 3 604 no-ops ; catalogue 102 régénérations, projets 102
  passages utiles. Les 29 jours initialement annoncés comme cadence utile étaient
  faux ; P2 bis trouve environ **4 jours** en construction. Ne pas créer une boucle
  chaude `projects` sur ce faux diagnostic.
- P2 `results/diag_p2_lifecycle_4y_s42_100_999.json` : portefeuille non vide après
  70/102 constructions ; les 32 vides sont tous `all_unaffordable`, pas épuisement
  du cache. Retour médian 15 j, manque de capital médian 5 475 £. D'où C75 bis,
  depuis adopté : ce n'est plus une étape « à implémenter ».
- P5 `results/diag_p5b_defaut_probe1_6y.json` et
  `results/diag_p5b_v89_probe1_6y.json` : l'ancien « 0/5 NOPA » était un artefact
  (`plan.path` au lieu de `plan.tiles`/`plan.ok`). Succès réels 16/16 et 13/13 ;
  durée médiane 118,5→32 j sous V89, épisodes d'attente médiane 15 j ; opportunité
  de préplanification, pas qualification économique du worker.
- La double majoration financière rail 170 décrite à l'époque est remplacée par
  le défaut 100 ; V89=1. Ne pas reprendre les contrefactuels comme état courant.
- Restent des pistes séparées : watcher C83 léger avant dépilage réactif, arbitrage
  des workers et maintenance `skip-not-due`, chacune à mesurer sans famine.
  `fleet_before_new` et l'augmentation générale du batch restent écartés.

## 6. Antériorité, conventions et autres limites

- R1–R26 désignent la [revue du 30](../revue_code_2026-09-30.md), pas des numéros C/V.
  Leur implémentation locale et validation sont dans le [journal du 30](journal_2026-09-30.md).
- C88 = compagnies humaines/IA ; V88 = chaînes goods. V95 AIR ≠ V95 scheduler
  P1/P2/P5. Garder ces alias, ne pas renommer rétroactivement les campagnes.
- `mean40` a déjà été utilisé ; ce qui reste à décider est sa généralisation,
  **pas un premier essai**. `signs20` reste le défaut, choix avant toute mesure.
- Le réseau rail partagé « toile d'araignée » reste différé à la toute fin : trains
  directs sur voies partagées, pas réintroduction de feeders/transbordement.
- Pour le passé plus ancien : [transfert du 22](journal_2026-09-22_transfert_historique.md),
  [journal du 13](journal_2026-09-13.md), [archive du 9](../archives/taches_archive_2026-09-09.md).