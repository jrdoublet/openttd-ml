# AIR-ROI-RENFORT-1 — étape 2b : arrêt au prérequis de sauvegarde transactionnelle (22/10/2026)

> **ARCHIVE HISTORIQUE — WIP LOCAL NON INTÉGRÉ (22/10/2026).** Constat réalisé sur l'arbre `master` local au HEAD `41031a7f` et ses modifications Squirrel non commitées. Le protocole de fourches transactionnelles documenté est **bloqué dans cette tentative historique** : aucun contrôle causal AA/AA puis renfort/sans renfort n'y a été validé. Aucun code expérimental ou mécanisme de fourche n'est **adopté** par la branche d'archive, et aucune qualification causale ou économique n'en découle. Les chemins `results/` évoqués renvoient aux données **locales WIP non archivées ici** ; des outils Python versionnés distincts peuvent être présents.

**Statut : BLOQUÉ, `not_identifiable`. Aucune fourche causale lancée ; aucune mesure à 24 mois.**

## Constat bloquant

Le protocole pré-enregistré (`docs/air_roi_renfort1_protocole_fourches_20261022.md`, §§2.2, 3, 6) exige un même fichier `.sav` créé exactement au point précédent **une commande** `OpexAirAddPlane`, avec état décisionnel de l'IA et commande encore pendante, puis un contrôle AA0/AA1 identique à chaque checkpoint jusqu'à +24 mois. L'outillage actuellement présent ne sait pas garantir cette coupure.

1. `ai/OpexAI/task_projects.nut::_tryBuildFleetProject` effectue ses dernières vérifications de ligne/flotte/caisse (lignes 203–245), puis appelle `OpexAirAddPlane` dans une boucle (vers 269–270), **sans suspension ou point d'arrêt transactionnel explicite**. `ai/OpexAI/task_air.nut` possède en outre un chemin d'appel historique (vers 752–761) à contrôler pour l'exhaustivité. Les traces `AIRR1_PRE` et `AIRR1_CONTEXT` sont volontairement publiées *après* la tentative (`air_flotte1_shadow.nut::OpexAirR1After`) pour éviter qu'un log bloque l'IA avant l'achat ; elles ne sont pas des sauvegardes.
2. `ai/OpexAI/persist.nut::Save()` sérialise les lignes et des compteurs de l'ordonnanceur lorsque `save_full_state=1`, mais **ne sérialise ni le projet `project` en cours d'exécution ni la pile de l'appel `_tryBuildFleetProject`**. `Load()` initialise une nouvelle exécution puis `Start()` réconcilie l'état ; une reprise d'une sauvegarde ordinaire ne garantit donc pas la même transaction. La documentation API OpenTTD indique en outre que le moteur appelle `AIController::Save()` lors d'une sauvegarde du jeu, sans avertir l'IA, et que seul l'objet retourné est conservé : <https://docs.openttd.org/ai-api/classAIController> (§Save/Load).
3. Le lanceur existant `results/v217_autopsy_841478_fork_stage_20261016/sweeps/c77_savefork_host_20261013.py` est explicite : `scope=MONTHLY_CHECKPOINT_NOT_C77_TICK`, `causal_claim=false` (lignes 215–232). Sa reprise dédiée `-D` évite la compagnie fantôme, mais les sauvegardes sont produites par `schedule on-next-calendar-month`, puis `save`/`quit` (lignes 285–325). L'implémentation de `ConSchedule` publiée par OpenTTD n'accepte que `on-next-calendar-month` : <https://docs.openttd.org/source/d3/d09/console__cmds_8cpp_source> (§ConSchedule). Un tel checkpoint mensuel n'est pas le `t0` avant la commande.
4. Il faut également un canal démontré pour choisir `RENFORT` ou `SANS_RENFORT` **sur la même sauvegarde et avec le même bundle**. Le jeu conserve les réglages de l'IA active dans la sauvegarde (`AIPL`/`running_settings`) ; changer seulement `[ai_players]` dans une configuration de nouvelle partie ne prouve pas qu'un bras chargé lit l'action demandée. Le précédent C77 utilisait deux arbres IA et ne constitue pas une validation du protocole à quatre bras strictement identiques.

Le simple ajout d'un flag et d'une entrée Save/Load, ou une pause `AIController.Sleep()`, ne règle pas le point 1 : `Sleep()` laisse passer des ticks du jeu et donc des commandes/autres flux entre la sélection et la sauvegarde. Une reprise reconstruisant arbitrairement le projet introduirait une intervention antérieure au renfort.

## Travaux et résultats de cette tentative

Inspection en lecture seule des points de transaction, des deux boucles d'exécution, de `Save()/Load()/Start()`, des réglages existants et du précédent lanceur C77. `git status --short` examiné avant l'audit : de nombreux fichiers IA et RAIL étaient déjà modifiés dans le dépôt partagé. Aucun code Squirrel, aucune configuration ni aucun fichier RAIL n'a été changé pour ce chantier ; aucun conteneur ou banc supplémentaire lancé. **Aucun nouveau test pytest de contrat n'a pu valider un mécanisme de checkpoint absent.**

| Mesure pré-enregistrée | Résultat | Motif |
|---|---|---|
| Sources éligibles et sauvegardes transactionnelles | 0 prouvée | Pas de capture `t0` atomique ni de reprise de projet courant |
| Smoke `added=1`, coût réel | non exécuté en étape 2b | Pas de source qualifiable à fourcher ; le smoke 2a n'avait que des `CASH` |
| AA0/AA1 sur 24 mois | non exécuté | Source transactionnelle manquante |
| RENFORT − SANS_RENFORT (`profit_year`, 12 mois nets) | `null` | Aucune paire causale |
| Achats évincés, charges, valeur résiduelle, caisse/dette, IC | `null` | Aucune comparaison causale ; nombre de grappes = 0 |

## Conditions de déblocage avant exécution

Implémenter et valider **dans le moteur ou son harnais** un arrêt atomique du monde au site de commande AIR, capable de sauvegarder le monde et de reprendre sans avancer d'un tick ni altérer les autres compagnies. Définir un état transactionnel explicite, borné et sérialisable (`episode_id`, tick/date, cycle, lineId, ordinal, candidat, tier, rank, financement, identité du moteur, étape exacte de l'exécuteur), puis prouver que `Load` reprend *la même* tentative sans re-sélection préalable et sans commande dupliquée. Prévoir un moyen vérifié de sélectionner une seule action par bras à la reprise, en conservant le SHA256 de la sauvegarde et les octets du bundle identiques ; refuser une action manquante, répétée ou discordante.

Une fois ces prérequis prouvés, appliquer dans l'ordre le protocole **smoke de renfort réussi avec achat physique**, **AA0/AA1 identiques au point source et aux 24 checkpoints mensuels**, puis **RENFORT/SANS_RENFORT** sur les graines pré-enregistrées 42, 100, 999, 1234, 5678, avec au plus deux lignes distinctes par graine et sans sélectionner les succès a posteriori. Toute sauvegarde seulement mensuelle reste `coarse_checkpoint_diagnostic` et est exclue de l'estimand primaire. Les défauts de score, priorité, V161/C70 et sonde restent inchangés.
