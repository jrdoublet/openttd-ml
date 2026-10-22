# AIR-FLOTTE-1 — photographie AIR/RAIL au point d'achat (22/10/2026)

## Statut

Après la mesure rétrospective des 40 références multimodales (voir
[audit](air_flotte_1_concurrence_air_rail_20261022.md)), une **sonde
shadow dédiée, à défaut 0**, est ajoutée. Elle ne change aucun score,
ordre du portefeuille, filtre de caisse ou projet exécuté. Son noyau
de collecte, les états de recherche RAIL, K_dec et les raisons de
refus ont désormais passé des tests OpenTTD : smoke 1×1, expositions
1×3, **5×3 puis 5×6**. Les anciens incidents HTTP 502 BaNaNaS sont
conservés comme échecs d'infrastructure préalables au moteur.

Configuration : **air_flotte1_shadow=1** pour le diagnostic, 0 sur les
quatre profils par défaut. La sonde ne nécessite pas decision_log=1 et
son journal reste inerte au défaut. Déclaration dans info.nut, chargement
unique dans settings.nut, globale AIR_FLOTTE1_SHADOW dans globals_pre.nut.

## Contenu du snapshot

Module : ai/OpexAI/air_flotte1_shadow.nut (requis par task_projects.nut).

- Renfort C121/V161 : achat capturé après validation de la flotte et de
  la caisse, immédiatement avant OpexAirAddPlane. Conserve le rang et le
  prix, le profit brut, calibré C70 et plafonné V161, le score de sélection,
  la réserve, le cash et la réussite ou l'échec réel du renfort.
- Renouvellement V252 : snapshot après les filtres prêt, caisse et hangar,
  immédiatement avant BuildVehicleWithRefit. Seuil de caisse protégé et
  ancien profit **historique**, mais aucun ROI marginal inventé. Issues
  distinctes : built, build_failed, order_failed, start_failed.
- AIRF1_BUY : ID local à la partie, tick, cycle, ligne, coût et économie
  du projet AIR, K_dec mémorisé depuis la vraie sélection antérieure
  (tick de sélection conservé, valeur susceptible d'être périmée), et état
  de recherche ferroviaire en cours (kind, phase, clé de candidat).
- AIRF1_LIST + AIRF1_RAIL (listed_best_remaining) : premier RAIL encore
  listé, dans l'ordre **effectif** (C77 puis fundScore). Ignore les RAIL
  déjà construits dans le batch. Indique budget disponible avant/après
  l'achat AIR, ROI brut, ROI calibré sur capital de financement et score
  de classement stocké, si la recherche A* en cours vise ce même RAIL,
  et la dernière raison de rejet relevée **dans cette même passe**.
  **Admissibilité instantanée non garantie.**
- AIRF1_POOL + AIRF1_RAIL (pool_best_raw_roi_unverified) : exploration
  du vivier hors top-K, avec un maximum de 256 RAIL ou 512 candidats
  examinés (tous modes), et un drapeau
  truncated. Le meilleur ROI brut du vivier n'est pas forcément un RAIL
  exécutable ; une candidature hors classement peut être périmée.
- AIRF1_CLOCK puis AIRF1_READY : contrôle du tick et du cash jusqu'au
  point transactionnel pour détecter les suspensions provoquées par la
  sonde. Les données sont capturées **avant l'achat**, mais les logs
  sont **émis après son retour** pour ne pas suspendre l'IA avant la
  commande. AIRF1_OUTCOME publie l'issue et le cash final.

L'ID (tick-cycle-canal-ligne) est valable uniquement dans **une partie**.
Les sondes consomment des opcodes et peuvent décaler la trajectoire
d'OpenTTD. Deux bras comparés devront donc utiliser exactement le même
instrumentation, ainsi qu'un contrôle AA/AA du même save avant une
inférence causale.

## Décodeur hors partie

Le lecteur sweeps/analyze_air_flotte1_shadow.py assemble les événements
par partie et ID, et refuse les doublons, échecs et snapshots ayant subi
un changement de tick ou de cash. Le compteur rail_cash_crossing_proxy
ne désigne qu'un RAIL devenu non finançable après débit AIR ; le
lecteur distingue les passages ayant déjà été rejetés au constructeur.
Le ROI réalisé de ce RAIL non construit demeure inconnu.

Commande locale (depuis la racine) :

    python -B -m unittest discover -s sweeps -p test_air_flotte1_shadow.py -v
    python -B sweeps/analyze_air_flotte1_shadow.py "results/CAMPAGNE_ENGINE/*.log"

Le revenu réalisé à deux ans d'un RAIL **non construit**, l'effet
causal du remplacement V252 et le profit contrefactuel restent
explicitement inconnus dans la sortie JSON.

## Campagnes de santé et exposition effectivement obtenue

- **Premier smoke 1x1** : campaign air_flotte1_shadow_smoke_1x1_20261022,
  graine 42, 1970, terminé sans erreur Squirrel. 75 tentatives de
  renfort, toutes rejetées ; aucun projet RAIL présent dans le vivier
  des achats observés. Sous cette première version, la sonde publiait
  encore les logs avant l'achat ; 46/75 snapshots avançaient le tick.
- **Sonde bufferisée, exposition 1x3** :
  air_flotte1_shadow_buffered_1x3_20261022, graine 42, années
  1970-1972, 1 worker, 2 CPU, code sale partagé par tous les bras,
  exécution complete/complete, **aucune erreur Squirrel**. 417
  snapshots C121, dont **18 renforts réussis**, 9 à tick/cash stables,
  6 avec un RAIL encore classé et finançable juste avant, et **3
  franchissements du seuil financier** où son ROI calibré sur capital
  financier dépasse celui du renfort AIR. Ces trois événements
  concernent seulement **deux clés RAIL distinctes** et une unique
  graine ; ils ne sont pas indépendants.
- **Recherche de cause** : les RAIL étaient en tête de best (rang 0),
  alors que les renforts construits étaient aux rangs 13, 7 et 9.
  Cela suggère des contraintes d'exécution RAIL (A* en cours, données
  de site périmées, recherche différée) plutôt qu'un simple choix
  d'un ROI inférieur. Le dernier ajout de diagnostics rail_search_*,
  search_same_best et K_dec_selection_tick permettra de le vérifier.

| Date 1972, seed 42 | Renfort AIR | RAIL classé rang 0 | Trésorerie avant | ROI AIR (‰) | ROI RAIL calibré/financement (‰) |
|---|---|---|---:|---:|---:|
| 28/03 | ligne 0, rang 13 | fret 58083→33442 | 90 674 £ | 16,3 | 1 346,6 |
| 07/04 | ligne 12, rang 7 | fret 58083→48086 | 72 158 £ | 16,3 | 1 050,6 |
| 14/04 | ligne 1, rang 9 | fret 58083→48086 | 94 408 £ | 16,3 | 1 050,6 |

L'écart économique n'est **pas** prouvé : la dépense exacte ne se résume
pas au prix théorique de l'appareil, le cash évolue durant la
construction, les RAIL ne sont pas garantis constructibles et aucun
profit du RAIL non construit n'est connu. Ces ROI ne sont pas des ROI
réalisés. Le résultat 1x3 ne constitue pas un test statistique.

**Échec indépendant du code lors du contrôle ultérieur :** deux
tentatives (air_flotte1_shadow_search_state_1x3_20261022 et
...search_state_retry...) se sont arrêtées à la préparation des
bibliothèques OpenTTD, avec HTTP 502 Bad Gateway provenant de
bananas-api.openttd.org (package ai-library/51554648). Aucune partie
jouée ni erreur Squirrel ; ne pas les agréger aux preuves de santé.

## Mesure du refus ferroviaire : 5 graines × 3 ans

La révision qui trace les refus au constructeur a été éprouvée
en OpenTTD sur la graine 42 en 1×3, puis sur le panel
**42, 100, 999, 1234, 5678** pendant trois ans
(campagne air_flotte1_shadow_causes_5x3_20261022, **5/5 jeux terminés**,
5 workers / 5 CPU, aucun crash Squirrel). Bundle de référence :
b7b8696e4c2f16b3e56ed7f1edf140c77550e1f12f794c7472bc6ea03ead2113.

| Indicateur observé | Nombre |
|---|---:|
| Tentatives AIR (renforts et renouvellements) | 1 728 |
| Renforts AIR tentés | 1 724 |
| Renouvellements V252 tentés | 4 |
| Achats effectivement réussis | 85 |
| Achats réussis avec tick et caisse stables | 47 |
| Dont RAIL encore classé et finançable | 19 |
| Dont RAIL déjà rejeté dans la même passe | 16 |
| Dont raison too_close_no_join | 14 |
| Cas de franchissement théorique de trésorerie RAIL | **5** |
| Dont RAIL refusé pour too_close_no_join | **5/5** |
| Projets RAIL distincts parmi ces cinq | **2** |
| Renouvellements V252 stables sans ROI marginal fiable | 3 |

Les cinq croisements concernent uniquement les graines **42** (deux
achats) et **5678** (trois achats), chacun répétant la même paire
RAIL. Les projets étaient mieux classés et théoriquement finançables,
mais le constructeur les avait **déjà rejetés pour too_close_no_join**
(extrémité ferroviaire trop proche sans jointure admissible). Il n'y
a donc **aucun cas prouvé d'éviction d'un RAIL constructible** dans
ces cinq croisements. Cela ne prouve pas qu'il n'existe aucun cas
ailleurs ni après trois ans.

La meilleure piste explicative est désormais la cohérence entre
vivier RAIL et constructeur, **pas** une sur-priorisation des renforts
AIR. Les cas de refus ne sont pas des témoins valables pour une
fourche causale AIR contre RAIL. La rentabilité marginale des
modernisations V252 reste non mesurée.

## Extension de la collecte et limites de qualification

### Extension à six ans — verdict final de cette collecte

Pour éviter de conclure seulement sur les premières années, la
campagne **air_flotte1_shadow_causes_5x6_20261022** reprend exactement
les cinq graines précédentes, sur **six ans**, avec le **même bundle**
b7b8696e4c2f16b3e56ed7f1edf140c77550e1f12f794c7472bc6ea03ead2113,
un seul conteneur, 5 workers et 5 CPU. Résultat : **5/5 parties
complètes** et aucune erreur Squirrel liée à la sonde.

| Indicateur, cinq graines × six ans | Nombre |
|---|---:|
| Tentatives d'achats AIR instrumentées | 2 506 |
| Dont tentatives de renfort C121 | 2 388 |
| Dont tentatives de modernisation V252 | 118 |
| Achats AIR réussis | 429 |
| Clichés d'achats réussis, tick et caisse stables | 179 |
| Clichés stables avec un RAIL encore listé | 87 |
| RAIL déjà rejetés dans cette passe | 67 |
| Dont refus too_close_no_join | 58 |
| Franchissements du seuil financier RAIL après AIR | **21** |
| Projets RAIL distincts touchés par ces franchissements | **10** |
| Ces franchissements déjà refusés pour too_close_no_join | **21/21** |
| Modernisations V252 réussies, clichés stables, sans ROI marginal fiable | 38 |

Répartition des 21 franchissements : graine 1234 = 11, 42 = 3,
5678 = 3, 999 = 4, 100 = 0. Les dix clés RAIL sont distinctes
au sens paire géographique et cargo. Aucun des 21 épisodes ne
constitue une occasion constructible attestée ; le filtre
too_close_no_join a refusé le candidat **avant** l'achat AIR.
Le suivi reste incomplet pour les 249 achats réussis ayant changé de
tick avant le point transactionnel, ainsi que pour un achat dont la
caisse a changé : cette sélection interdit toute généralisation
à toutes les dépenses AIR.

Le profit économique du duel à six ans n'est **pas** l'effet de la
sonde : elle est un instrument à opcodes non neutres et il n'existe
pas ici de paire de bras même-save. L'analyse ne qualifie donc ni
un multiplicateur AIR, ni un changement d'ordre C77/C69, ni une
intervention V252.

**Conclusion opérationnelle :** AIR-FLOTTE-1 n'a révélé aucune
éviction constructible sur cette cohorte. Ne pas lancer de fourches
AIR/RAIL pour des RAIL refusés ; analyser en priorité la
discordance entre sélection et constructeur RAIL
(too_close_no_join). La réponse à la question générale du ROI
réalisé à deux ans pour des rails hypothétiques demeure non
identifiable sans alternative physiquement exécutable.

1. Traiter séparément les candidats ferroviaires maintenus au classement
   alors que le constructeur refuse leur raccordement too_close_no_join.
   Ne pas faire de ce défaut une raison de pénaliser l'AIR.
2. Si nécessaire, pré-enregistrer un panel plus long / plus large pour
   rechercher des occasions réellement constructibles, en conservant
   le même diagnostic et des garde-fous d'horloge.
3. Pour un résultat économique : fourches de **même sauvegarde**
   AA/AA/AIR/RAIL, puis profit annuel terminal à +24 mois et preuve
   sélection → tentative → constructeur → lineId. Les cas où le RAIL
   échoue à se construire doivent rester comptés, et non exclus.

**Vérification de la collecte :** 6 tests du décodeur et
des hooks shadow, 4 tests de l'analyse rétrospective et 7 tests
d'inventaire réussis. Le réglage `air_flotte1_shadow` demeure à **0 par
défaut** dans tous les profils. Les **21 franchissements** de la cohorte
finale concernent des RAIL déjà refusés.
**Aucune adoption de politique AIR/RAIL.**
