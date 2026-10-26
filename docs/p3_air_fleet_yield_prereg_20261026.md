# P3 — pré-enregistrement avant exposition (worktree isolé)

**Base figée :** `98c8568d`, branche `p3_air_fleet_yield_20261026`.
Cette note n'est ni une qualification ni une décision d'adoption. Aucun banc P3
n'a été lancé pendant le smoke/porte A P6.

## Intervention et bras

- `air_fleet_yield_rightsize=0` : **OFF par défaut aux quatre profils**. Aucun
  getter P3, sondage supplémentaire de véhicule, log P3 ni veto. Les chemins
  C121 1→2, crash, V252, score V161 et décisions historiques restent inchangés.
- `=1` : **shadow**. Agrège les fenêtres C117 déjà disponibles et trace la
  proposition de veto dans `P3_FLEET_YIELD` si `DECISION_LOG` est actif ;
  ne modifie ni le score ni les achats.
- `=2` : **ON conservateur**. Refuse uniquement un nouveau projet d'extension
  de flotte AIR mature **2→3+** répondant à *toutes* les preuves suivantes,
  avant sélection puis en revalidation au moment de l'achat. La voie directe
  hors portefeuille suit le même veto. Aucun refus si le renfort permet la
  migration V252 vers un autre moteur constructible.

## Définition de la preuve, fixée avant la mesure

1. Ligne de **730 jours minimum** et `year - line.year >= 2`, flotte stable
   de **2 avions ou plus**, dernier renfort vieux de **2 à 3 années civiles** ;
   aucune liquidation, reconstruction après crash, mesure marginale annuelle
   encore pendante ou changement de flotte/moteur.
2. **Trois fenêtres C117 closes** d'âge-bucket, **20 à 35 jours chacune**,
   consécutives, total **65–105 jours**, dernière clôture vieille d'au plus
   35 jours. L'identité combine LineID, date de création, gares, cargo,
   véhicules, types de moteur et capacités ; chaque échantillon du bucket
   doit être couvert. Après Save/Load, cache effacé et statut inconnu jusqu'à
   reconstitution ; **aucune sérialisation de cache** ni surcoût de Save().
3. Au moins **six vols réellement observés** lors de transitions d'ordres,
   dont **deux dans chaque sens**, au moins un par fenêtre ; sièges réellement
   présents, passagers dans `[0, sièges]`, capacité constante, attente
   valide dans les trois fenêtres à **chaque** gare. Les sentinelles de charge
   `-1`, zéro siège, zéro vol, lacunes, changements de flotte ou ancien cache
   donnent **UNKNOWN** : *pas de veto*.
4. Conditions simultanées du veto :

   | Signal | Seuil inclusif, sauf mention |
   |---|---|
   | Voyageurs livrés / sièges sur vols terminés | **≤ 15 %** |
   | Stock moyen observé gare A et gare B / capacité d'**un avion** | **≤ 25 %** pour chacune |
   | Profit C117 annualisé des véhicules, divisé par le nombre d'avions / prix avion | **≤ 10 %** |
   | Dernière marge **observée** C121 par avion / prix avion | **strictement > 0** et **strictement < 8 %**, au moins un échantillon réel |

**Prudences :** la marge C121 est le delta de bénéfice de la ligne entière après
renfort et amortissement, **pas une causalité individuelle**. Le stock en gare
peut être partagé entre lignes. Les seuils sont une hypothèse de test
pré-enregistrée, non des valeurs optimisées. La combinaison de signaux
réduit le risque de reproduire AIR-LOAD-1 (charge seule, perte de profit et
trésorerie non réinvestie). Le moteur doit rester capable de préférer des
investissements alternatifs réellement finançables ; aucune telle opportunité
n'est encore démontrée.

## Exposition et critères de poursuite (aucun lancement ici)

Première exposition descriptive, après smoke Squirrel et fin des bancs P6 :
**5 graines `42 100 7 999 2026` × 5 années** (1970–1974), même base P3
et autres défauts identiques ; bras OFF 0 contre shadow 1, instrumentation
`DECISION_LOG` équivalente. Conserver pour chaque ligne/graine/date :
nombre de projets fleet 2→3+ évalués, nombre de trois-fenêtres C117
**valides**, causes UNKNOWN, `tripsA/B`, `pax/seats`, pression A/B,
profit C117, dernier marginal C121, V252 upgrade, `would_veto`, achat
effectivement réalisé ou rejeté, prix et caisse au moment pertinent.
Dédupliquer les scans répétitifs ; ne **jamais** présenter un projet proposé
comme un avion construit ou comme un investissement alternatif réalisé.

La cohorte peut être rare : archive antérieure sur trois graines,
**117/117** achats sous cible C121, **107/117** sans mesure marginale ;
seulement **19 renforts 2→3** vus sur 1973–1974. Si l'exposition ne produit
pas d'occasions réellement achetées qui auraient été refusées avec preuve
complète, arrêter : **NO-GO** économique, sans ajustement opportuniste du
seuil sur les mêmes graines.

Si présence et plausibilité économique de projets *effectivement* substitués :
smoke moteur 1×1, contrôle OFF/SaveLoad et, uniquement après décision de
lancement, **A 40×5 multimodale** selon la tâche P3 `docs/taches.md`
(choix de cet horizon fixé avant mesure ; seuil `gain_short` de V102 :
Wilcoxon exact p<0,05, IC95 bootstrap borne basse >0, gain annuel ≥4 %,
valeur ≥−5 %) ; **B 20×10** `non_erosion` seulement après A pass.
Les résultats ne qualifient pas d'emblée le défaut 2.

## Validation hôte autorisée ici

`sweeps/test_p3_air_fleet_yield.py` : contrats OFF/shadow/ON, préconditions
C117 et verdicts sur fixtures, fenêtre/sentinel, V252, revalidation.
`sweeps/test_c117_air_throughput.py`,
`sweeps/test_v159_c117_lean.py`,
`sweeps/test_c121_air_economics.py`,
`sweeps/test_r1_partial_fleet.py`,
`sweeps/test_po01c_regen_split.py`,
`sweeps/test_n75_multi_cargo.py` et inventaires de paramètres.
Le `SaveLoad` réel `sweeps/save_load_roundtrip.py` et la compilation
Squirrel nécessitent un moteur, **interdit ici tant que Docker P6 tourne**.
Après reload, les trois fenêtres de preuve sont volontairement perdues :
les achats reprennent selon le chemin historique en attendant leur reconstitution.

## Validation mécanique réalisée le 26/10

Le code comportemental a été figé au commit `5e9c7266`, réglage `0` aux
quatre difficultés. Après restauration à l'identique de la copie locale
ignorée `ai/AAAHogEx-115` dans le worktree, la suite hôte complète a passé
**2 874 tests**, avec six ignorés et deux échecs attendus ; les 11 contrats P3
et les suites C117/C121/N75 sont verts, `git diff --check` est conforme.

Smoke réel `p3_yield_smoke_42x1_20261026_r1`, code Git propre `5e9c7266`,
bundle `bf263ee0d42b38eb310abb2f4f41f3f73148fc5518172625dbebceabf58b311d`,
manifeste `07e3017bae883aaa9a810e1ff078b177e19d514983cc2e7cdbb50b47477d79b2`,
image `openttd-lab:latest` SHA256 `f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659` :
deux duels 1970 complets et sains, aucune erreur ou partie invalide ;
`0` contre `2`, un seul monde graine 42, delta annuel +1 478 £, strictement
**diagnostique** (`diagnostic_only`).

Save/Load moteur `=2`, court (`save_full_state=0`) puis complet
(`save_full_state=1`) :
`results/p3_yield_saveload_{short,full}_42_20261026.json`. Dans chaque essai,
13 sauvegardes à chacune des deux phases, rechargement du **01/07/1970**,
`LOAD_RECONCILE` positif et aucun marqueur d'erreur script. Le harnais de
rechargement fait apparaître une compagnie humaine fantôme connue, sans
activité construite : les résultats valident la reprise du script, **pas**
un bilan de gain économique ou une équivalence de trajectoire.

L'exposition des décisions shadow 5×5 et, si admissible, la porte A sont des
étapes distinctes à documenter avec leurs propres bundles et résultats.

## Verdict d'exposition shadow — 26/10/2026

Campagne `p3_yield_expo_5x5_20261026_r1`, code propre `87931643`,
bundle `bf263ee0d42b38eb310abb2f4f41f3f73148fc5518172625dbebceabf58b311d`,
manifeste SHA256 `3331c72fbf4194fa81ddfcb1675aeaecebcd69a2294b5743e388ecb1890b7548`,
même image Docker que le smoke, carte 256², 1970–1974. Bras de référence
`air_fleet_yield_rightsize=0` et shadow `=1`, `probes=6` identique dans les
deux bras, cinq graines **42, 100, 7, 999, 2026**. Les **5/5 paires**, soit
dix parties, sont terminées et saines, `comparison_complete=true`,
`metric_coverage_complete=true`, zéro `failed_runs`. Le rapport donne
`diagnostic_only` (l'échantillon de 40 graines de A n'est pas présent).

Les journaux moteur du bras shadow contiennent les événements de décision
`P3_FLEET_YIELD stage=score` suivants :

| Graine | Évaluations de portefeuille 2→3+ | Avec preuve C117 complète | `would_veto=1` |
|---|---:|---:|---:|
| 42 | 546 | 0 | 0 |
| 100 | 285 | 0 | 0 |
| 7 | 987 | 81 | 0 |
| 999 | 577 | 0 | 0 |
| 2026 | 427 | 40 | 0 |
| **Total** | **2 822** | **121** | **0** |

Les **121** évaluations positives pour la disponibilité de preuve sont des
passages répétés du portefeuille, couvrant **neuf LineID dans seulement deux
mondes** (sept graine 7, deux graine 2026), et **aucune ne franchit les quatre
conditions simultanées** du veto conservateur. Exemple authentique, graine
2026 le 17/05/1974 : ligne 6, deux avions, sept vols, 153 voyageurs sur
700 sièges, marge C121 `29 260` £, `evidence=1 veto=0`.
Il n'existe donc **aucun achat effectivement substitué par un veto observé**
sur le chemin du portefeuille de cette cohorte ; le journal de score seul
ne prouve pas exhaustivement l'absence d'autres opportunités hors portefeuille.

Le delta `profit_year` shadow moins OFF à cinq ans vaut **+69 127,6 £/an**
(3V/2D, Wilcoxon p=0,8125, IC95 bootstrap
`[−105 228,6 ; +295 078,8]` £/an), chiffre **diagnostique** : le shadow
n'applique aucun veto, donc cette différence ne constitue pas un gain P3.

**Décision pré-enregistrée : NO-GO d'exposition pour P3 sous ces seuils.**
Ne pas lancer la porte A 40×5 ni la porte B 20×10, et ne pas adapter les seuils
aux cinq graines inspectées. Réglage laissé à `0` aux quatre difficultés.
L'implémentation opt-in reste disponible pour un essai ultérieur avec une
nouvelle hypothèse indépendante et une exposition suffisante.
