# P0 / Top-K stable : essai isolé du 12 octobre 2026

**Statut avant moteur : hypothèse, aucune adoption.** Stage détaché
`results/p0_topk_binary_stage_20261012` au HEAD `f6139d8`. Seul
`probes.nut` préexistant modifié dans le principal a été copié pour
garder sa parité `probe_loop_ops` (diff initial +31/-2), sans toucher
au reste du worktree principal. Les autres changements ne concernent
que les quatre fichiers IA de réglages/sélection et un test du stage.

## Hypothèse causale

Profil spans indépendant (graines 42 et 999 en 1973, instrumentation
coûteuse, **non neutralisée économiquement**) :
`OpexProjectSelectAffordable` a un intervalle `select.full` de
23,55 M et 24,52 M opcodes tick par partie ; les sous-intervalles
`pub.select.score.insert` de 14,45 M et 14,46 M couvrent 7 247 et
8 091 insertions. Ces chiffres incluent le prix du profilage, les
franchissements de ticks et les comparateurs ; leur somme n'est pas
une économie possible en tant que telle.

Au défaut C118/C122 désactivé, `OpexProjectInsertDefensive` recherche
la position d'une nouvelle alternative par une boucle remontant le
Top-K (maximum 64). L'ordre lexicographique historique reste :
`(C77 priorité + V88 chaîne, score avec prime AIR early-slot, revenu)`
descendant, avec égalités *stables*. La recherche binaire du premier
élément à insérer après les clés égales effectue O(log K) comparaisons
au lieu de O(K), tout en conservant `best.insert` et son coût O(K).

Le chemin P0 ne change ni score, ni plancher, ni seuil C75, ni Top-K,
ni projet AIR/Rail, ni règles de financement. Flags `p0_topk_binary=0`
et `p0_topk_binary_check=0` aux quatre difficultés ; fallback explicite
pour C118 actif, C122 priority/shadow, AIR_EFFICIENCY_DEDUPE et
PROBE_SELECT_REJECT. Aucune table d'état persistée. En check=1,
l'original et la binaire sont exécutés sur deux tableaux contenant
les mêmes références, et seul le résultat historique est conservé ;
les listes finales sont comparées à chaque insertion, coûts old/new
agrégés annuellement sans log par candidat. Check et optimisation
sont désactivés au défaut et ne doivent jamais être activés simultanément
pendant un banc de qualification.

## Pré-enregistrement des bancs

1. Tests hôte de tri stable sur flux randomisés avec égalités, niveaux
   C77, scores flottants et revenus, et contrôle source de defaults,
   fallback, sites d'insertion. Cette fixture mathématique n'est **pas
   une VM Squirrel** : smoke moteur réel obligatoire.
2. `p0_topk_binary_check=1` seul, référence historique livrée, 42×2 ans
   et puis 5 graines×5 ans si aucun `mismatches`, avec `--script-debug` ;
   rendement old/new par entrée identique, coût propre de la sonde et
   divergence de trajectoire signalés. Aucune attribution économique.
3. `p0_topk_binary=1`, check=0 : smoke causal C66 42×1, exposition
   et comparaison de coût sur `LOOP_OPS` par référence/variante aux
   paramètres identiques. Si gain d'opcodes local et global effectivement
   démontré, protocole opcode AGENTS §4, **20 graines×10 ans** en C66
   apparié et sans instrumentation de check, profit/valeur, no famine,
   construites AIR/RAIL et Save/Load. Aucune adoption avant cela.

La mesure `GetTick/GetOpsTillSuspend()` donne des **fenêtres de 10 000
opcodes**, y compris attente et yields, et non une comptabilité des
instructions Squirrel réellement exécutées. Toute divergence de
`mismatches` ou de sélection fera rejeter le chemin P0 et conserver
l'insertion historique.

## Parité complète 1970–1973 sur cinq graines (sonde check)

`p0_topk_check5_5y_20261012`: **10/10 parties et cinq paires
complètes**, bundle `def46d6313e572fa4b4067b383b64e841009cec22c8d03c855ea563f33cb8d80`,
manifeste `94bcf9a017b556b7ae0508199097e763da114528af8b546329cc9bf56df824f2`.
Recalcul hors moteur :
`sweeps/analyse_p0_topk_check.py results/p0_topk_check5_5y_20261012_engine
--out results/p0_topk_check5_5y_20261012_parity.json`.

Sur les 20 couples graine/année : **57 859 comparaisons d'insertion
old/new, zéro mismatch de tableau** ; même liste de références,
ordre exact et longueur après chaque insertion. Sous-sondes mesurées
sur les **mêmes entrées**, ancien **103 690 025 opcodes de fenêtre**,
nouveau **34 584 049**, soit **−66,65 %**. Chaque graine/année est
favorable en coût local, réduction allant de 44,36 % à 74,46 %.
Ces valeurs appartiennent aux deux calculs exécutés consécutivement
dans un *shadow* ; le test économique de cette sonde vaut
`diagnostic_only` (delta +30 956 £/an, 2 V/3 D, IC95 très large).
Ne pas les transformer en économie globale mesurée avant l'A/B réel
binary OFF vs ON, sans check.

## Première preuve moteur, contrôle uniquement

`p0_topk_check42_2y_20261012`, duels C66 sains 2/2 ; bundle
`def46d6313e572fa4b4067b383b64e841009cec22c8d03c855ea563f33cb8d80`.
Graine 42, contrôle ancien/nouveau sur même entrée en 1970 : **1 648
insertions**, `mismatches=0`, `old_ops=4 234 277`,
`new_ops=1 081 537` (−74,46 % d'opcodes de fenêtres attribuées au
scanner). L'A/B économique de cette sonde de contrôle est
`diagnostic_only` : profit variante − référence **−56 301 £/an**
et valeur −9,87 % à horizon deux ans. Ce désaccord de trajectoire est
attribuable à la surcharge/ordonnancement du contrôle ; il ne permet
pas de conclure sur l'optimisation binaire en production.

Prochaine campagne de PARITÉ, toujours sans adoption :
`p0_topk_check5_5y_20261012` cinq graines canoniques
42/100/999/1234/5678, cinq ans de simulation pour fermer 1970–1973,
référence `p0_topk_binary=0,check=0` ; variante `binary=0,check=1`,
`--script-debug`, dix CPU, dix workers, 8 Go. Analyser `mismatches`
par année/graine, logs santé, effort old/new. Un seul mismatch
interdit l'A/B d'optimisation jusqu'à diagnostic.

Si cette étape passe, protocole qualifiant préenregistré opcode :
smoke `binary=0` vs `binary=1` graine42×1 an avec mêmes autres
réglages, puis **20 graines canoniques ×10 ans**, un duel C66 par bras
sur chaque carte, `--decision-rule non_erosion` pour enregistrer
la comparaison brute, `--primary-metric profit_year`, garde valeur 5 %,
seuil relatif4 % enregistré mais sans exigence de gain économique,
`--cpus10 --memory8g --max-workers10`, `--script-debug` et
`probe_loop_ops=1` **identiques dans les deux bras** pour mesurer les
opcodes globaux. La qualification opcode ne sera évaluée qu'après
vérification des années clôturées, disponibilité LOOP_OPS, contrôle
par graine, IC95/bootstrap, test des signes et rythme des constructions.
Le profilage `probe_span_trace=1` et le check=1 seront désactivés dans
ces deux bras. Gain économique positif non requis, mais aucune
dégradation démontrée acceptée.
