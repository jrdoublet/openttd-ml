# C121 : contexte commun par paire et avion (item 1)

Demande du 2 octobre : réaliser le contexte commun après la fusion du gagnant.
Référence : arbre `c121-catalog`, HEAD `52ab555…` et changements locaux préservés.
Les journaux/cache ont été consultés : aucun nouveau cache global, aucune
réactivation des profondeurs ou politiques C121 rejetées. Fusion du gagnant=1
conservée dans les deux bras. C115=1, économie C121=0 au défaut.

## Intervention isolée et plan avant mesure

Nouvelle gate `c121_air_engine_context`, ancien défaut 0, candidat 1.
Le contexte étend le candidat sortable pendant une invocation du chooser.
Cycle physique, tarifs PASS/MAIL, temps de paiement et amortissement déjà
calculés pour la borne sont transmis à l'évaluation exacte et au gagnant.
Les capacités restent lues selon le contrat cold-start PASS-only / observations
exactes ; les facteurs de réalisation et les points de vitesse restent calculés
par leurs fonctions courantes aux mêmes endroits. Le tri, les départages et
l'élagage exact sont conservés. Aucun changement de flotte ni de profondeur.

Vie du contexte : une paire et une invocation, jamais dans le plan, ni Save/Load,
ni les caches inter-tranches. Retour au chemin courant si la date change, si les
identités de paire/avion/catalogue ou des snapshots parent changent, si vitesse,
âge/prix, cargos, distance, capacité ou temps de paiement changent. Les snapshots
parent restent immuables selon leur contrat actuel. Pas de prolongation de leur
fraîcheur. La préparation invalide son contexte si elle traverse une journée.

Validation technique : tests ciblés, fixture VM à sorties récursivement identiques,
matrice 72 cas (caps1/6/13, MAIL inconnu/zero/positif, quatre modes de profondeur,
AAA0/1), garde d'invalidation et absence d'alias ; comparaison naturelle du chooser
sur les mêmes snapshots préparés, samples traversant une date non comparés.
Pilotage moteur avec les drivers actuels, bibliothèques figées vérifiées, pas
d'appel direct OpenTTD. Mesure du scan et du gagnant, puis sonde catalogue annuelle
42/100 ×1 an, mêmes sources/config et une seule différence de gate.

Catégorie définie avant mesure : **opcodes**. Si gain net exposé, validation
économique isolée comme pour la fusion : C121=1 commun, fusion=1 commune,
contexte0→1 uniquement, sonde coût OFF. Smoke apparié, 5×6 puis 20×10 conditionnel
selon neutralité : IC95 Student non entièrement négatif, p des signes≥0,05 ou
majorité de victoires, garde de valeur −5 %. Verdict brut ordinaire conservé.
Cette séquence vise l'optimisation demandée, pas l'adoption de l'économie C121.
Défaut maintenu à0 jusqu'aux preuves requises ; pas de commit/push/merge implicite.

Docker local autorisé par l'utilisateur : 10 CPU/10 workers maximum, mémoire
2 Go et volume de cache conservés. Une seule campagne au lancement. Le VPS
reste limité à3 CPU/3 workers. Le runtime actuel est celui du pilote précédent.

## Historique de réalisation avant reprise Docker

Prototype livré derrière `c121_air_engine_context=0` aux quatre difficultés.
Le chemin témoin reste disponible ; la fusion du gagnant demeure activée.
Le contexte ne sort pas du chooser et ne crée aucun état à sauvegarder.
Les contrôles de fraîcheur renvoient au calcul courant dès qu'une entrée change.

**101 tests Python réussis** : contrats C121 existants, staging byte-identique
du core, lecteurs de fixtures et comparaison annuelle isolée contexte0→1.
Ces tests ne compilent pas Squirrel. Le contrôle du chargement effectif inclut
désormais la gate contexte ; le comparateur annuel vérifie fusion=1 et C121=1
communs et mesure aussi le scan qui inclut la création du contexte.

La tentative VM `20261002_context_fixture42_r1` n'a pas démarré : le CLI Docker
est resté en attente sans créer le conteneur nommé
`c121-context-fixture42-20261002`, ni dossier de sortie. Docker `info`, l'image
figée et `ps` répondent, mais `events` et la liste filtrée des conteneurs expirent.
Seuls les deux CLI de cette tentative ont été arrêtés ; une autre demande
Docker en attente a été préservée. Aucun redémarrage du daemon ni doublon lancé.

**Non validé à ce stade** : compilation/exécution Squirrel, égalité en VM et
gain net d'opcodes ne sont pas encore mesurés. Prochaine porte : fixture VM
dans un dossier neuf `…_r2` lorsque Docker peut créer des conteneurs et que
l'autre lancement est terminé, puis mesures annuelles 42/100 si saine.
Aucun banc économique ni changement de défaut du contexte n'a été effectué.
L'interdiction courante de qualifier l'économie C121 reste applicable ; les
résultats de la fusion ne qualifient pas cette nouvelle intervention.

## Vérification demandée : protocole économique complémentaire

Demande explicite « vérifie le gain en opcode et la neutralité éco » du 02/10.
Après redémarrage de Docker par l'utilisateur, fixture r3 saine : 72 cas et
399 choix naturels identiques sur snapshots communs ; coût scan+gagnant
12 802 796→14 067 928 opcodes, soit **+9,8817 %**. Cette version n'est donc
pas adoptable comme optimisation. Les mesures annuelles sont complétées sous
deux gates explicites, mêmes copies figées, puis répétées r2 après stabilisation
du comparateur/provenance ; les r1 restent conservées, sans modification du core.

Pour satisfaire la demande économique indépendamment de ce rejet en opcodes,
la séquence smoke→5×6→20×10 est préparée comme **évaluation**, sans possibilité
d'adoption en l'absence de gain. Bras identiques sauf
`c121_air_engine_context=0/1`, `c121_air_economics=1` et fusion=1 communs,
sonde=0 ; AAAHogEx figée, profit_year, garde valeur 5 %, règle de neutralité
inchangée, verdict signs20 brut conservé. Un diagnostic non neutre ou malsain
arrête la séquence ; aucune relance pour obtenir un résultat favorable.
Source : copie mesurée `20261002_context_off42_r1/ai/OpexAI`, vérifiée par hash.
Qualification du modèle C121 et changements concurrents restent exclus.

## Résultat final : version non retenue

Le gain d'opcodes n'est pas confirmé : **+9,881685 %** sur le scan+gagnant,
399 mêmes entrées naturelles, sorties identiques. Préparation et gardes du
contexte sont incluses dans le coût. Les pilotes annuels r2 sains montrent
des trajectoires et volumes différents : AIR +99,6047 % sur42, −6,9862 % sur100,
appels494→879 et692→599. Ne pas confondre ces deltas avec une vitesse pure.
Preuve : `results/c121_winner_integration/20261002_context_summary_r1/report.json`.

Économie : smoke2/2 sain, puis diagnostic5×6 **10/10 duels sains, 5/5 paires**,
comparaison/couverture complètes, horizon décembre1975, quatre trimestres
disponibles et valides pour toutes les compagnies à la dernière collecte.
Une seule différence effective de réglage attestée par le manifeste : contexte0→1.

| Graine | Delta profit annuel (£) | Delta valeur Opex (£) |
|---|---:|---:|
| 42 | −92 921 | −1 161 479 |
| 100 | +8 050 | −63 705 |
| 999 | +49 738 | −235 425 |
| 1234 | −158 643 | −13 190 |
| 5678 | −52 907 | −4 584 |

Delta moyen **−49 336,6 £/an**, médiane−52 907 £/an, IC95 Student
**[−151 291,57 ; +52 618,37]**, 2 victoires/3 défaites, p des signes=1.
Le profit seul ne prouve pas une perte significative ; la **garde de valeur
échoue** : ratio des moyennes0,942267, soit **−5,773329 %**, limite−5 %.
La moyenne des ratios (−4,864408 %) n'est pas le critère de garde.

Verdict brut `diagnostic_only`, porte de neutralité séparée=false. Arrêt prévu
après le diagnostic : **pas de20×10, pas de qualification de neutralité**, pas
de relance économique. Défaut contexte=0 conservé aux quatre difficultés.
108 tests Python réussis et compilation/exécution NoAI validée par les fixtures
et parties. Aucun changement du modèle/défaut économique C121, aucun commit.

Campagne exacte :
`results/c121_context_economics/20261002_context_neutrality_r1/inputs/results/20261002_context_neutrality_r1_diagnostic.json`.
Bundle `9a545b60323baf74d847e26c52f9ed7fc67aa8e74fc16d68e81e2f865fb31214`,
manifeste `b11185e2b75cbcccd204d1c3e39e75736a664060c340957af84460a208852566`.
[Audit dérivé versionnable](../evidence/review/c121_engine_context_20261002/README.md),
avec hashes et chemins des preuves brutes dans sa synthèse JSON.
