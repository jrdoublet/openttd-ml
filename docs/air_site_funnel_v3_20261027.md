# Entonnoir V3 — protocole pré-enregistré le 27/10/2026

Décision utilisateur : candidat de production prêt pour une porte A **air seul**,
sans adoption, push ni merge. Worktree `air-site-probe`, base de travail V2
`1dc82978`; arbre local modifié figé par les lanceurs avant chaque mesure.

## Intervention

`air_site_ranked=0` (défaut, quatre difficultés) : chemin existant intact.
`air_site_ranked=1` : listes natives par bandes 4..14 puis 15..25, tri C96,
CheapOk natif de l’hybride, admission 263/nivellement identique à la production.
Plafond de 12 tests dans la phase classée, au plus moitié de l’allocation de ville.
Repli C96 si aucun site ; budget BuildAirport et plafond de trois admissions de
nivellement partagés avec le repli. Cache historique seulement. Branchement du
générateur PO01C et des appels synchrones. `air_site_funnel=1` reste l’hybride actuel.

## Sondes, avant résultat

Protocole V2 conservé : une partie solo par méthode, sans construction/emprunt.
Schéma de journal V3 : admission après nivellement et acceptation passagers >=8.
Méthodes 1..10 : spiral, hybrid, initial, bands, border, funnel, strict,
strict_full, oracle, ranked. Les variantes strict restent témoins historiques.
Oracle exhaustif du domaine historique : BuildAirport sur chaque ancre ; les
refus 263/autorité ne sont admis au nivellement que si CheapOk natif accepte
l’emprise (même restriction que la production). Score C96 maximal, puis coût total
minimal connu. Aucun filtre plat. Les coûts des pentes sont des **estimations** :
LevelTiles en AITestMode ne modifie pas la carte. Le total estimé est le tarif
aéroport + devis natif de nivellement + devis natif de déblaiement initial ; un
recouvrement des déblaiements avec le nivellement est possible. Un devis inconnu
reste null. `quote_exact=1` uniquement pour un BuildAirport direct réussi.

Smoke graine 42 × 1 an × 10 méthodes. Après smoke sain seulement, graines
42, 100, 7 × 6 ans × 10 méthodes. Six ans : marge technique uniquement pour finir
la passe 01/01/1975 ; autres dates 02/01/1970 et 01/01/1972. Comparaison appariée
ville/type/graine/date, empreintes de début identiques, passe complète ; sinon
exclusion. La carte continue d’évoluer pendant les scans : limite documentée.
Contrôle opcodes cumulés par ticks, devis/admission, ratio oracle, villes manquées,
écarts appariés vs spirale et hybride. Critère descriptif du candidat : qualité
proche de la spirale ou supérieure et réduction nette des opcodes. Trois graines
ne qualifient aucun gain économique.

## Smoke réel et porte préparée

Smoke réel 42 × 1 an, run_c66_reference, référence/candidat OpexAI contre AAAHogEx,
air seul, probes=6 commun, 3 CPU / 2 Go RAM et swap / 3 workers VPS. Pas de porte A
lancée dans cette tâche. Commande 40×3 gain_short, seuil relatif4 %, garde valeur5 %,
air seul commun, sera fournie dans le rapport après lecture des résultats.

Aucune campagne simultanée sur le VPS ; image openttd-lab
sha256:a0e0a0727f5003532764eeaeee6b83e9ab96a7470df3c76208c6446d10b88c8c,
contexte Docker default, cache openttd-lab-home. Artefacts uniques sous results/.

Smoke réel pré-enregistré : deux duels graine42 × 1an ; OpexAI
`mode_air=1,mode_rail=0,mode_road=0,mode_water=0,probes=6`,
seule différence `air_site_ranked=0/1`. AAAHogEx identique dans les deux duels :
`disable_veh_train=1,disable_veh_roadveh=1,disable_veh_tram=1,disable_veh_ship=1,disable_veh_aircraft=0`.
`probes=6` active DECISION_LOG (bit4), ce qui vérifie AIR_RANKED_SITE ; la porte A
préparée revient à probes=2 (panneaux communs du harnais).
Le premier lancement réel a été refusé avant partie : `decision_log` n’est plus
un réglage déclaré, il est intégré au masque probes. Le second lancement enlève
ce seul argument obsolète ; code et instrumentation demandée inchangés.

## Correction mécanique après smoke réel (avant nouvelle mesure)

Le smoke02 réel est **1 an**, pas 2 (JSON `years=1`, dernier cliché 1970-12-01).
Référence : 17 AIR_BUILD et 1 AFAIL263 ; candidat : 10 AIR_BUILD, 1 AFAIL263 et
2 BFAIL263. L’AFAIL initial concerne la même ancre32411 dans les deux bras.
`airport footprint remains non-flat` vient du contrôle physique après LevelTiles,
non de BuildAirport. CmdLevelLand15.3 retourne `had_success ? cost : last_error` :
une réussite partielle suffit. Le tri C96 expose davantage des bords bloqués.

Correction limitée à air_site_ranked=1 : tester atomiquement chaque coin nord à
modifier vers la hauteur cible, rectangle inclusif (w+1)×(h+1), sous AITestMode
et AIAccounting imbriqués. CheapOk borne le relief à un niveau ; plus d’un niveau
est refusé sans simulation séquentielle fictive. L’autorité reste conditionnelle
au boost existant. Le prédicat est installé aussi pour le cache et le repli.
Ne pas substituer un filtre plat. Trace AIR_RANKED_LEVEL_REJECT avec corner/error
et bulk_ok pour vérifier la réussite partielle du test groupé.

Nouvelle validation autorisée : smoke réel42×1 puis diagnostic aérien seul
42,100,7×2 ans, deux duels par graine, probes6, profilVPS3CPU/2Go/3workers.
Même référence et réglages d’adversaire que smoke02. Pas de sélection d’une graine
favorable ni de porte A lancée ; rapporter chaque tentative et ses défauts.

Le smoke03, vérification atomique seule, confirme `32411 corner=32929 error=260
bulk_ok=1` et évite l’AFAIL. Il reste un BFAIL sur46286 : les modifications de
plusieurs coins touchant un même obstacle ne composent pas leurs autorisations
autoslope en mode test. Smoke03 : 7 AIR_BUILD et 1 BFAIL263, versus17/1 en référence.
Correction avant smoke04 : sur le bord externe uniquement, chaque coin qui doit
bouger exige des tuiles adjacentes libres (pas route/maison/eau). Aucun filtre plat
sur l’emprise, aucun rejet des bords qui ne doivent pas bouger. Les sondes mises à
jour utilisent le schéma4, qui distingue succès groupé (`levelable`) de contrôle
complet (`level_complete`) et admission ; les anciens journaux ne sont pas mélangés.

Le smoke de sonde corrigée a tronqué l’oracle à un an (pas d’erreur moteur).
Les tests atomiques complets étaient exécutés même pour les scores incapables de
battre le meilleur connu. Correction de mesure seulement : BuildAirport demeure
exhaustif, puis devis/nivellement seulement si le score C96 peut égaler ou dépasser
le meilleur. Les égalités restent évaluées pour le départage en coût. Aucune
modification du module de production pour cette correction de sonde ; la version
native suivante est pré-enregistrée ci-dessous.

Le diagnostic réel3×2 du contrôle sûr initial est complet et sans263 candidat,
mais négatif sur les trois graines (−649086, −96423, −30668 £/an). Il reste conservé.
Le smoke de sonde confirme le surcoût de la validation Squirrel. Dernière version
pré-enregistrée avant mesure : listes natives GetMaxHeight pour le même prédicat
plat, GetCornerHeight pour ne parcourir que les coins à modifier ; rejet des
obstacles extérieurs purs avant consommation du plafond de trois tests natifs de
nivellement. Même contrôle atomique final, même refus des interactions de bord.
Cette réorganisation change le budget consommé par les faux positifs géométriques,
pas le défaut. Nouveau smoke puis même3×2 ; ne pas sélectionner un résultat antérieur.

## Résultats finaux — commit de code cd9c7116

Candidat air_site_ranked, défaut0, techniquement bancable ; non qualifié.
Cause263 : LevelTiles accepte un succès partiel ; contrôle des coins mobiles,
bord extérieur protégé, validation atomique, listes natives et rejet géométrique
avant consommation du budget de nivellement. Aucun constructeur ni défaut modifié.

Sonde finale :30 parties,90 passes,3780 lignes,9 groupes graine/date valides,
2160 clichés sans activité, zéro erreur. Ranked : médiane score/oracle
1,000, p10 1,000, moyenne admissible
0,990, 0 ancres absentes malgré oracle,
14 107 001 opcodes (-1,9 % vs spirale ; 8,8 % vs hybride).
Le critère initial de réduction nette des opcodes n’est pas atteint par la
version sûre finale. Oracle conservateur sur le nivellement, devis après nivellement estimés et dérive
de date conservée dans les limites ; les chiffres initiaux−36 % ne sont pas ceux
du code final.

Smoke final42×1 : deux duels sains, zéro263 ON. Diagnostic3×2 final :6/6 sains,
zéro263 ON contre4 OFF ; profits annuels Δ42=−650731, Δ100=+139294,
Δ7=+149993 £/an ; moyenne−120481, médiane+139294 ; V/D/E2/1/0, Wilcoxonp=1,
IC95bootstrap [−650731 ; +149993], valeur ratio des moyennes−5,4943 %.
Verdict `diagnostic_only` ; aucune porte A exécutée, aucune adoption.

Tests :276 ciblés OK (2 attendus),48 lecteur/candidat OK ; suite3061 :7 erreurs
numpy absent,9 ignorés,2 attendus. Aucun autre échec. HashesOFF et syntaxe vérifiés.

Artefacts hôte : `/home/deploy/projects/openttd-ml/.worktrees/air-site-probe/results` ; préfixes finaux `air_site_funnel_v3_final_probe_3seeds_20261027`, `air_site_funnel_v3_final_real_3x2_20261027`, `air_site_funnel_v3_real_smoke05_20261027`.
Rapport complet : `/home/deploy/codex_runs/air_site_probe/rapport_funnel_v3.md` ; commande porte A40×3 aérien seul gain_short,
seuil4 %, garde5 %, profilVPS et probes2, préparée dans ce rapport et
`/home/deploy/projects/openttd-ml/.worktrees/air-site-probe/results/air_site_funnel_v3_gateA_command.txt`, non lancée. Aucun push/merge.
