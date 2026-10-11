# C121 territoire d'abord — comparaison isolée 40×3 du 11/10

Demande utilisateur : retester `c121_territory_first` sur C121 courant, 40 graines × 3 ans. Évaluation uniquement ; défaut 0 conservé, aucun commit/push ni adoption. L'ancien 5×3 du 30/09 face à C115 reste historique et n'est pas remplacé.

## Pré-enregistrement

- Dépôt courant, branche master, SHA initial `9168404`. Arbre initial propre ; seules les notes de ce banc seront modifiées avant le gel, aucun changement IA.
- Intervention : référence `OpexAI[c121_territory_first=0]`, variante `OpexAI[c121_territory_first=1]`. Tous les autres réglages aux défauts actuels, notamment économie/catalogue C121 à1 ; mêmes sources et même adversaire AAAHogEx figé, carte partagée et places identiques.
- Catégorie comportement : réserver la trésorerie du prochain nouveau projet AIR territorial et refuser un autre chantier qui consommerait cette réserve. Globale chargée uniquement sous C121, deux helpers et garde portefeuille vérifiés ; aucun nouvel état Save/Load.
- Contrats ciblés : économie C121, cohérence du cache, investissement, 80/80 verts.
- Smoke causal : graine42 ×1 an, deux duels, `decision_log=1` identique dans les deux bras pour vérifier exécution et chercher les refus `c121_territory_reserve`. Ces duels instrumentés ne sont pas dans l'échantillon économique ; les refus logués sont tronqués aux trois premiers dans une passe sans construction. Une absence de log ne prouve pas une absence de visite.
- Porte demandée : `gain_short`, **40 graines canoniques ×3 ans**, une répétition, 80 duels / 240 années de jeu, budget de cette campagne unique ; aucune répétition favorable.
- Primaire : `profit_year` Opex variante − Opex référence à l'année terminale, quatre trimestres valides. Passage : Wilcoxon exact bilatéral p<0,05, borne basse IC95 bootstrap moyenne >0, delta moyen ≥4 % du profit moyen de référence ; garde ratio des moyennes `company_value` ≥0,95. Bootstrap courant 20 000 rééchantillonnages, graine0.
- Télémetrie OFF sous A ; le seul réglage explicite différant entre les bras est territoire0/1. Compilation, santé, exposition et verdict statistique seront rapportés séparément. Aucun jugement causal sur la baisse d'AAAHogEx seule.
- Campagnes : `c121_territory_smoke_20261011_1618_r1`, puis `c121_territory_A40x3_20261011_1618_r1` si smoke sain. Résultats, JSONL, manifests, bundles et logs dans des chemins neufs de `results/`.
- Docker Desktop local `desktop-linux`, image exacte à vérifier après démarrage du daemon ; profil 10 CPU/8 Go RAM/swap plafonné à8 Go/10 workers, cache `openttd-lab-home`, dépôt monté à `/work`. Daemon initialement arrêté, Docker Desktop démarré ; contrôle de disponibilité avant lancement.
- Pas de B automatique pour cette demande limitée au 40×3 ; ce résultat seul n'autorise pas l'adoption du défaut.

## État

**Docker rétabli, smoke sain et porte A terminée : fail_primary.** Le 11/10, reprise sur SHA bfdb2b9 (les commits depuis 9168404 ne changent que la documentation). Smoke : 2/2 duels sains, comparaison complète, verdict attendu diagnostic_only. Exposition réelle dans territory_on_seed42_r0.log : PROJECT_DISCARD du 1970-11-29, mode=fleet, reason=c121_territory_reserve, reserve=101364. Profit terminal identique sur cette seule graine, aucune conclusion économique. Bundle commun smoke/A : cf065a29e3a660107adaf09e20c78c0f97e4aec49e7b96b746ed1bf2efedb2de. Image : sha256:f4b2b9b3b7399cbfecacfe03b3b8dda49bff2921de36a61fed4e9441e5d44659. Porte A : 80 duels, 10 CPU/8 Go/10 workers, télémétrie OFF, 80/80 duels complets et sains. Journal en conflit Git laissé intact. Aucun code IA, défaut, commit ou push modifié par cette reprise.

### Réparation préalable du démarrage Docker

Le daemon était arrêté et refusait son démarrage : erreur de renommage du socket AF_UNIX vsock1999 `C:\Users\jr\AppData\Local\Docker\vm-data\00000002.000007cf` vers `.stale`. Docker et WSL contrôlés arrêtés ; les deux entrées étaient des points de réanalyse (attribut1056). Retrait ciblé de ces deux sockets transitoires par `os.unlink`, après vérification des chemins et attributs, sans retrait d'image, volume, cache ou disque de VM. `docker desktop start --detach` accepté ; vérification de disponibilité du daemon en cours. Aucun duel n'a démarré pendant l'incident.

Après cette réparation, le backend a recréé le socket et annoncé sa VM démarrée, mais le daemon est resté injoignable plusieurs minutes. Le redémarrage contrôlé a reproduit l'erreur de renommage du nouveau socket. Dernière action : `docker desktop stop --force --timeout 20`, arrêt accepté. Services hns/vmcompute observés Running, aucune distribution WSL Running. `vm-data` contient également `DockerDesktop.vhdx` (28 461 498 368 octets) : aucune suppression/réinitialisation ou déplacement de ce disque/dossier entrepris. Prochaine étape proposée : redémarrage Windows puis reprise des contrôles Docker ; aucune relance du banc économique effectuée.

## Résultat de la porte A

Campagne c121_territory_A40x3_20261011_1618_r1, SHA bfdb2b91d4b2cc58d2f29ea6ef9d2389367ff2f3. 80/80 duels sains, 40/40 paires ; comparison_complete, adoption_sample_complete et metric_coverage_complete vrais. Les 80 observations Opex terminales ont quatre trimestres valides, aucune partie échouée.

- Profit annuel ON moins OFF : +17 781,80 £/an (+0,9053 %), médiane +30 999 £/an ; 24 victoires / 16 défaites / 0 égalité.
- IC95 bootstrap de la moyenne : [−45 573,425 ; +79 400,85] £/an, 20 000 rééchantillonnages, graine0. Wilcoxon exact bilatéral p=0,412534.
- Gain utile requis : +78 565,202 £/an (+4 %). Gain moyen inférieur au seuil, borne basse négative et p supérieur à0,05 : verdict brut fail_primary.
- Valeur de compagnie : ratio des moyennes 1,007486, soit +0,7486 % ; garde −5 % tenue.
- Exposition : refus territorial effectivement observé dans le smoke instrumenté, pas de sonde sous A. Aucun gain d'opcodes mesuré. L'essai ne démontre ni gain économique utile ni équivalence ; aucune perte significative établie sur cette mesure.

Défaut0 conservé, pas de porte B après cet échec, aucune adoption/relance favorable/commit/push. Les données brutes restent dans results/c121_territory_A40x3_20261011_1618_r1.json et .jsonl, avec manifest, bundle figé et logs. Manifest SHA256 : 84e1f7c20abaed67cf63514341ef2d514ee9b9ec1e37ce9754a6aa241fd9fc59. JSON SHA256 : 842410dae1c403d1e533697248d901801fb70ce521229e7436206167ca660e14. Les deltas par graine sont dans archives/c121_territory_first_A40x3_20261011.csv.

## Clôture utilisateur après les deux essais

Le11/10, rejet explicite puis suppression du réglage et de son code exclusif. Les verdicts et bundles ci-dessus restent historiques, intacts. Comportement de l'ancien défaut0 conservé ; 78 contrats verts et smoke du nettoyage42×1 sain. Voir [journal du retrait](journaux/journal_2026-10-11.md#rejet-et-retrait-c121--territoire-dabord). Aucun commit/push.
