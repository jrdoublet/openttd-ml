# Mémoire des échecs d'upgrade RAIL — 40×10

Pré-enregistrement du 10 octobre 2026, demandé explicitement par l'utilisateur.
Évaluation uniquement, sans adoption automatique ni commit/push.

- Référence : `OpexAI[rail_upgrade_failure_memory=0]`.
- Variante : `OpexAI[rail_upgrade_failure_memory=1]`.
- Même arbre local `95a6ad2`, dirty, figé par le harnais ; autres réglages aux défauts actuels.
- Catégorie : comportement. Mécanisme : mémoriser les échecs de doublement et différer leurs reprises ; exposition historique établie au diagnostic du 03/10, exposition actuelle à vérifier dans les résultats disponibles, sans ajouter de sonde intrusive.
- Campagne : `upgmem_40x10_20261010_r1`, 40 graines canoniques `SEEDS_40`, une répétition, 80 duels contre AAAHogEx, dix ans.
- Règle brute : `gain_short`, `required-seeds=40`, `required-years=10`, seuil relatif 4 %, garde de valeur 5 %, métrique terminale `profit_year` variante moins référence. Horizon dix ans explicitement choisi avant résultats ; ne pas présenter ce diagnostic comme le parcours canonique A3/B10.
- Wilcoxon exact bilatéral p<0,05, borne basse IC95 bootstrap moyenne >0 et gain moyen >=4 % ; bootstrap du harnais 20 000 tirages, graine 0. Aucun rejeu favorable ni seconde campagne automatique.
- Docker Desktop local, image `sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659`, 10 CPU, 8 Go RAM/swap, 10 workers, volume `openttd-lab-home`. Docker libre au contrôle initial.
- Contrats : `test_v100_rail_upgrade_failure_memory.py`, 5/5 OK.
- Smoke : `upgmem_smoke_20261010_r1`, 42×1, deux duels terminés, delta nul, verdict attendu `diagnostic_only`. Bundle `226368a5c6b141daac700569a4165cc2e0205a0394a1156de884ea3c88296e0c`.
- Sorties : `results/upgmem_40x10_20261010_r1.json`, manifeste, bundle, JSONL et logs associés. Après fin : vérifier 40/40 paires, santé/horizon/couverture, empreinte du code, deltas annuels et verdict brut ; aucune conclusion avant ces contrôles.

Statut : **TERMINÉ, `fail_primary`**. Bundle identique au smoke : `226368a5c6b141daac700569a4165cc2e0205a0394a1156de884ea3c88296e0c` ; manifeste `8d4d3e11bad9bcfbaa84f05d8e77da67a9711cd999e6bcd758b71718ce8afa31`.

## Résultat final vérifié

## Adoption explicite après résultat

L'utilisateur valide le paramètre par défaut le 10/10, pour sa logique et son impact économique jugé neutre. Décision d'ingénierie explicite : le verdict statistique `fail_primary` du 40×10 est conservé, sans preuve d'équivalence revendiquée. `rail_upgrade_failure_memory=1` dans les quatre difficultés ; retour à 0 disponible. Chargement inchangé par `GetSetting`, mémoire commune `abandonedPairs` déjà sauvegardée/restaurée, aucun schéma modifié.

Validation du défaut livré : 5/5 contrats, smoke `upgmem_default_smoke_20261010_r2` (42×1, un duel au défaut sans override) complet/sain. Bundle `2847a30db049a96d5a65c01117102676c00f3d2de30cb5302903f35a500157f1`. Première commande r1 refusée avant partie car `--reference OpexAI` n'est pas une syntaxe acceptée ; r2 omet cette option et utilise les défauts. Aucun nouveau roundtrip Save/Load exécuté pour ce changement de preset. Aucun commit/push.

### Résultat économique antérieur à l'adoption

80/80 parties saines, aucun failed_run, 40/40 paires complètes ; comparaison, échantillon et couverture métrique complets à dix ans.
Profit annuel terminal ON−OFF : moyenne +43 435,975 £/an (+1,407857 %), médiane +10 394,5 £/an ; 21V/18D/1E ; Wilcoxon p=0,6142546308 ; IC95 bootstrap [-36 025,325 ; +129 681,275] £/an (20 000 tirages, graine 0).
Seuil pré-enregistré +4 % = +123 410,212 £/an non atteint ; IC traversant zéro. Valeur de compagnie +1,308326 % (ratio des moyennes), garde -5 % tenue. Verdict brut `fail_primary` : gain utile non démontré, sans perte statistiquement établie ni preuve d'équivalence. Défaut 0 inchangé, aucune adoption ni relance. L'exposition mécanique actuelle et le coût opcode ne sont pas quantifiés par ces agrégats économiques.


Validation avant publication : copie exacte du tree indexé `9a191224d0298b921a836b7cfd84aa35a9949b9c`, 10/10 contrats ciblés OK, smoke solo 42×1 via bench_v2 terminé OK, défauts effectifs AIR paiement=1 et mémoire upgrade RAIL=1 confirmés. Résultat local `results/adoption_publish_tree_20261010/results/defaults_publish_smoke.json`. Les prototypes locaux exclus du commit ne sont pas inclus dans cette copie ; les mesures économiques antérieures restent attachées à leurs propres bundles.
