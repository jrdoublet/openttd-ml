# AIR-PELOTON-1 — essai opt-in « full load » AIR, préparé le 25/10/2026

## Objectif et pré-enregistrement

Sur la base de `master` `83e436cc3db35ff18efb685ace4f97eb569f77b1`,
worktree `.worktrees/nuit75-air-full-load`, branche `nuit75-air-full-load` :
comparer la politique AIR d'OpexAI à celle d'AAAHogEx, qui active
`isSrcFullLoadOrder=true` dans `route.nut:1871`, puis
`isDestFullLoadOrder=true` pour l'AIR dans `air.nut:201` et affecte
`AIOrder.OF_FULL_LOAD_ANY` dans `route.nut:2137,2163`.
AAAHogEx est **le concurrent des deux bras** ; cette expérience ne le modifie pas.

L'unique variante est `air_peloton_full_load=1` contre référence explicite
`air_peloton_full_load=0`. Valeur par défaut : **0** aux quatre profils,
aucun autre paramètre métier changé. L'option vaut pour les **deux gares AIR**,
indépendamment de l'origine initiale de l'avion. Le comportement de référence
reste `OF_NONE` sur les deux gares.

## Mise en œuvre et couverture

- `info.nut`, `globals_pre.nut`, `settings.nut` : une option booléenne 0/1,
  initialisée à false puis lue une seule fois dans `OpexLoadSettings()`.
  Inventaire des `AddSetting` : **58 → 59** ; plafond justifié dans
  `sweeps/test_v251_inventory.py`. Les cinq autres assertions
  d'inventaire à 58 réglages (`test_v246_fixed_policies.py`,
  `test_parameter_retirements_20261023.py`, `test_v259_bridge_renew.py`,
  `test_v276_candidate_slices.py`, `test_v284_rail_growth.py`)
  passent également au plafond 59 avec commentaire d'attribution.
  Les empreintes intégrales de
  `info.nut` et `settings.nut` dans
  `sweeps/test_po01c_regen_split.py` sont réancrées explicitement à
  **47195e78…** et **5698caff…** ; les sept autres fichiers épinglés
  par ce test ne changent pas.
- `air_construction.nut` : `AppendOrder` aux deux aéroports à
  `OF_FULL_LOAD_ANY` sous option. Le second avion cloné ou construit en secours
  **copie des ordres indépendants** sous ON ; validation avant démarrage.
  Le traitement `ORDFAIL` utilise le rollback existant.
- `air_fleet.nut` : création d'un appareil après crash avec deux nouveaux
  ordres, également conditionnels. Pour le renfort, le clonage du même modèle,
  le repli après échec du clonage, le changement d'appareil et le repli sur
  l'ancien moteur, les clones utilisent `CloneVehicle(..., false)` et les
  achats directs `CopyOrders` sous ON. Une fonction commune valide et applique
  `OF_FULL_LOAD_ANY` sur **les ordres indépendants du nouvel avion** avant
  son démarrage.
- `task_v252.nut` : après `ShareOrders` ou `CopyOrders` sur le nouvel
  avion (uniquement `CopyOrders` sous ON), même normalisation avant démarrage.
  Échec traité comme refus de
  remplacement, avant retrait de l'ancien véhicule.

La fonction commune exige exactement deux ordres de type « aller à la gare ».
Elle évite les appels `SetOrderFlags` lorsque les deux sont déjà chargement
complet ; elle refuse de modifier un ordre de dépôt ou un cycle inattendu.
**Sécurité transactionnelle :** l'option ON ne crée jamais d'ordres partagés
avant de poser les flags, même en repli de construction, remplacement V252 ou
clonage. Si le premier ou second `SetOrderFlags` échoue, ou si le nouvel avion
ne démarre pas, sa vente / rollback n'altère pas les ordres de la flotte
existante. L'option OFF conserve exactement les partages d'ordres historiques.
Des avions anciens conservent leurs ordres après activation de l'option
jusqu'à leur remplacement ; un nouveau renfort a sa **propre** liste d'ordres.
Ce choix peut modifier la synchronisation ultérieure des corrections d'ordres
entre avions d'une ligne sous ON.

**Persistance :** la politique n'ajoute aucune donnée à `OpexAI.Save/Load`.
Le moteur OpenTTD sauvegarde les ordres de véhicule. `OpexLoadSettings()`
relit le réglage au redémarrage, et un appareil créé après chargement passe
par les mêmes chemins. Désactiver l'option après des constructions ON ne
convertit pas rétroactivement les ordres déjà posés.

## Risques et preuve attendue

L'AIR est majoritairement en surcapacité d'après
`peloton_diag_5x5_20261024` (10 497 départs, charge médiane 9–12 %).
`OF_FULL_LOAD_ANY` peut donc immobiliser longtemps un avion à chaque
extrémité, surtout sur une gare peu productrice : le trafic, la fréquence,
le revenu, les villes desservies et l'équilibre intermodal peuvent **baisser**.
Le chargement complet peut aussi réduire des départs « peloton », mais
aucun gain économique n'en découle automatiquement. Le passage ON modifie
les timings et la demande desservie ; ne pas confondre
une diminution de vols avec une meilleure politique. `SetOrderFlags` peut
échouer et sa réussite réelle doit être validée sous OpenTTD 15.3.

**Antécédent défavorable majeur : C81, 22/09/2026, même paire de flags.**
`docs/journaux/20_nuit_2026-09-22.md` §§1.1–1.3 montre que
`air_full_load=1` posait déjà `OF_FULL_LOAD_ANY` **aux deux aéroports**,
avec héritage des ordres partagés lors des renforts. En SOLO 3 graines × 6 ans
(100/42/12345), profit annuel terminal **2,20 M£ → 1,01 M£ (−54 %, 0/3)**,
73 → 44 lignes AIR, 105 → 91 avions, profit par place 144 → 67 £.
La version départ seul (`air_full_load=2`) perdait 37 %. Une autre variante
combinant 2 avions initiaux et chargement complet aux deux bouts, en DUEL
5×3 sous C121, chutait à 279 k£ contre 1 280 k£ pour Opex
(`docs/catalogue_decoupe_phase2_20260929.md`, § « Ligne à la AAAHogEx »).
**Ce n'est donc pas une nouvelle hypothèse de politique** : la différence
technique porte surtout sur le moteur OpenTTD et la base 2026-10-24,
et sur les ordres indépendants des nouveaux renforts/V252. Ces changements
ne démontrent pas que le plein chargement devient rentable.

Le contrat Python vérifie la présence des deux ordres et de tous les chemins
de copie, mais ne compile ni n'exécute le Squirrel. Aucune simulation Docker
pendant la baseline nocturne `nuit75_master83e_baseline20x10_20261024`.
Sur ce worktree, `ai/AAAHogEx-115` est absent : le prime devra fournir
l'adversaire figé comme dans les autres worktrees avant tout smoke.

### Bancs préparés pour le prime, sans lancement

Prérequis : suite Python verte, baseline Docker terminée, validation du
worktree et de son SHA/code figé, budget Docker disponible, OpenTTD 15.3 /
OpenGFX 7.1 / AAAHogEx-115, carte **256×256**, départ **1970**.
Conserver la même source, mêmes paramètres et même adversaire entre les bras.

Smoke causal de santé **1 graine × 1 an**, 2 duels, `seed=42`,
`air_peloton_full_load=0` vs `1`, `gain_short`, `required-seeds=40`,
`required-years=3`, métrique `profit_year`, seuil 4 %, garde valeur 5 %.
Contrôler erreurs Squirrel, 2/2 jeux complets et, **si une lecture des
ordres est disponible**, `AIOrder.GetOrderFlags` aux **deux terminus**
dans au moins un service ON et `OF_NONE` en OFF. Sans inspection des
ordres réels, l'exposition ne sera pas directement vérifiée et il ne faut
pas inférer les flags de la seule différence de profits.
Le smoke un an peut ne pas exercer V252 ; une exposition ultérieure est
indispensable avant toute affirmation sur ce chemin.

Commande préparée sur le PC (après libération Docker, non exécutée) :

```powershell
python -X utf8 sweeps/run_c66_reference.py --campaign air_peloton_full_load_smoke_1x1_20261025 --reference "OpexAI[air_peloton_full_load=0]" --variant "OpexAI[air_peloton_full_load=1]" --variant-policy-id air_peloton_full_load --decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 40 --required-years 3 --primary-metric profit_year --value-guard-max-loss-pct 5 --years 1 --repeats 1 --seeds 42 --script-debug --cpus 10 --memory 8g --max-workers 10
```

L'ancien rejet C81 impose un **point de décision avant la porte A** :
le prime vérifiera si le smoke met au jour une exposition ou un mécanisme
matériellement différent de C81 (notamment des achats V252 sur lignes
anciennes et les ordres indépendants), et si un nouveau duel est justifié.
Si ce fait nouveau est établi, porte A V102 **40 graines × 3 ans**,
un seul passage, `gain_short`, `profit_year`, Wilcoxon bilatéral
`p < 0,05`, borne basse IC95 bootstrap moyenne positive,
delta moyen ≥4 % de la référence, garde valeur ≥−5 %.
Nom de campagne proposé :
`air_peloton_full_load_porteA_40x3_20261025`.
Les graines sont les 40 graines canoniques du harnais, non sélectionnées
après résultats. Bootstrap **20 000** rééchantillonnages, graine **0**.
Commande préparée, conditionnée au point de décision ci-dessus :

```powershell
python -X utf8 sweeps/run_c66_reference.py --campaign air_peloton_full_load_porteA_40x3_20261025 --reference "OpexAI[air_peloton_full_load=0]" --variant "OpexAI[air_peloton_full_load=1]" --variant-policy-id air_peloton_full_load --decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 40 --required-years 3 --primary-metric profit_year --value-guard-max-loss-pct 5 --years 3 --repeats 1 --cpus 10 --memory 8g --max-workers 10
```
En cas de passage complet et sain de A, lancer ensuite **B 20×10
`non_erosion`** avec les 20 graines canoniques et garde de valeur 5 %.
Ne changer le défaut qu'après les deux portes complètes et qualifiées,
sur décision utilisateur. Aucun lancement, commit, push ni merge autorisé ici.
