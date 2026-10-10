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

Statut : **80 duels lancés**, conteneur `upgmem-40x10-20261010-r1`. Bundle identique au smoke : `226368a5c6b141daac700569a4165cc2e0205a0394a1156de884ea3c88296e0c` ; manifeste `8d4d3e11bad9bcfbaa84f05d8e77da67a9711cd999e6bcd758b71718ce8afa31`. Aucun verdict disponible au lancement.
