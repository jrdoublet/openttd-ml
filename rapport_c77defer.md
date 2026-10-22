# Rapport C77 defer — 22/10/2026
Commit local po03_c77_defer : 8c9c9e1a1a596d52d6e3a17c9f76bb062c2f3137 (socle 190b4ba1).
T5 confirmé conditionnellement : main.nut:128 initialise _projects=null ; persist.nut:860 restaure la file, sans vivier.
persist.nut:1042 et :1060 réconcilient recherche abandonnée et worker ; aucune reconstruction synchrone du vivier.
orchestrator.nut:703 et :727 : sous 0, trois reports puis perte au quatrième dispatch si le vivier reste null.
Ce n'est pas une perte systématique de toute sauvegarde : elle dépend du délai et de la file restaurée.
Reconstruction : scheduler_tasks.nut:95 (phases bootstrap dues au cycle courant), :153/:172 (publication), :242–315 (scan/apply).
Le scan AIR est plafonné à 150000 ops/pas ; publication au passage suivant ou apply après scan/fallback ; durée en jours non garantie.
T3 confirmé : orchestrator.nut:703/:727 et :930–964 permettent injection/réselection/construction sous rail_search ou rail_stock.
La garde regen_candidates existe déjà (orchestrator.nut:659) ; le correctif l'étend aux autres workers pour build/subsidy seulement.
Conception : c77_intent_defer=0 aux quatre difficultés ; ancien dispatch conservé octet pour octet hors bloc ON (contrat SHA256).
Sous 1 : attente si vivier null ou worker actif, sans consommer retries ; FIFO réenfilée avec retour false.
Anti-famine locale : orchestrator.nut:996 dépile une seule intention ; :1013/:1080 donnent ensuite accès worker/fond.
Borne choisie : 365 jours depuis premier report, marge au timeout stock nominal de 180 jours (:300), pas durée mesurée du rebuild.
Expiration dès delta >=365, même si disponible tardivement ; abandon C77_INTENT_EXPIRE sous DECISION_LOG.
c77DeferDate est un entier AIDate ; coalescence conserve la première date (:43), même quand la cause du blocage change.
Persistance : persist.nut:78–113 transmet le payload intégral ; :728/:860 sauvent/restaurent la file ; format court :617 omet les deux.
Tests : 8 nouveaux tests modèle/contrats réussis ; frontière 364/365, ticks à date constante, workers, FIFO, coalescence et sérialisation.
Suite complète : 2387 tests, 1 échec + 12 erreurs test_v166_* (AAAHogEx absent), 7 skips, 2 expected failures ; aucun nouvel échec.
Les deux échecs connus de comptage sont corrigés en actualisant les inventaires à 99 ; diff --check réussi.
Comparaison origin/master local 1c7d3e22 : archive sous results/c77defer_validation/baseline, 2383 tests ; mêmes problèmes V166/comptages.
L'archive produit aussi un échec V279 dû à son test git diff relatif hors racine ; ce test passe dans le worktree réel.
Logs : results/c77defer_validation/{before,baseline,final}.log ; tests ciblés rejoués après derniers ajustements.
Aucun Docker, partie, push ; compilation Squirrel/Save-Load moteur non validés. Rapport hors commit.
Configuration principale vérifiée après commit : aucun core.worktree ; user.email=jrdoublet@gmail.com ; aucune configuration modifiée.

## Thème 4
Commit local : `8d8e277e9f2d3cec9ef5cef89d9b6c7ef4135859`, parent `8c9c9e1a` ; références ci-dessous relatives à `ai/OpexAI/`, après correctif.
Événement → suivi : `events.nut:348`, `event_handlers.nut:163` valident l’ID, mémorisent cargo/extrémités/expiration puis enfilent `c77_subsidy` (:176), sans interrupteur C77 historique.
Défaut confirmé sous 0/1 : `orchestrator.nut:698` appelle l’injection (:942), refusée sous `MODE_AIR && C121_CATALOG_FIRST_YEAR_ACTIVE` (:948) ; retry seulement si vivier null (:707), sinon intention acquittée sans tentative.
Nuance à l’audit : l’offre n’est pas définitivement perdue ; `task_projects.nut:2005` / `scheduler_tasks.nut:322` actualisent l’année AIR (année initiale, avion constructible), puis `task_projects.nut:2070` et `projects.nut:493` peuvent recréer les candidats des offres encore suivies hors année AIR.
Hors blocage AIR : `orchestrator.nut:959` génère les candidats, remplace ceux du même ID, resélectionne avec le capital disponible (:968), puis enfile `c77_build` (:975), même si aucun candidat de l’offre n’a survécu aux filtres.
Sans candidat : `candidates.nut:2022` exclut offre invalide/attribuée ou ≤30 jours restants ; :2030 exige moteur ; :2040–2085 vérifie lieux, production/acceptation ; :2088 filtre distance Manhattan dans roadMin…roadGenMax (repli roadMax), :2093–2128 abandon/desserte/saturation, profit positif et délai de chantier suffisant.
Mode non autorisé : `settings.nut:99–104` applique mode_road et permission moteur, :223 fixe ROAD_BUILD_ENABLED ; `catalog.nut:1054` ne remplit le catalogue route que si activé ; `task_road.nut:7` refuse encore route désactivée/type absent. Les candidats de subvention sont routiers, pas AIR/rail.
Injection ≠ tentative : `projects_selection.nut:1442` sélectionne les projets finançables ; `orchestrator.nut:720–769` abandonne l’intention si portefeuille invalidé, best vide ou tête d’un autre projet (dont priorité AIR défensive), puis seulement appelle `_tryBuildProjects` ; le candidat peut rester disponible à la passe normale.
Construction : `task_projects.nut:1558–1581` contrôle capital/budget de passe puis :1752 appelle `task_road.nut:3` ; offre/chantier revalidés :22, caisse réelle + réserve + marge :85, plan :97, rentabilité après siting :123, offre revalidée :156, construction :171 ; échec physique possible, succès enregistré et offre retirée du suivi :262–278 (`C42_SUBSIDY_BUILD`), pas encore un gain.
Gain/expiration : `event_handlers.nut:210` reçoit l’attribution (possible via une ligne existante, même sans chantier C77), retire le suivi et marque la ligne trouvée avant `C42_SUBSIDY_WON` ; attribution rivale :217, expiration offre :201, fin de subvention :236 passent par purge/réselection :187. Les compteurs fournis 6/4/1 ne permettent pas d’attribuer les quatre expirations à un filtre précis ni de prouver quatre absences de tentative.
Correctif : `orchestrator.nut:641` ajoute uniquement sous 2 le blocage AIR de c77_subsidy ; même c77DeferDate entier, conservé par coalescence/Save-Load, même limite ≥365 jours, retour false vers worker/fond ; garde validité/attribution/expiration pour les deux intentions liées à une offre, sans toucher aux builds ordinaires (ID absent ou −1).
API [AISubsidy OpenTTD 15.3](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_subsidy.hpp#L68) : GetExpireDate donne le dernier jour valide de l’offre non attribuée, change après attribution ; IsValidSubsidy précède IsAwarded/GetExpireDate. Arrêt conservateur dès ce dernier jour (aucun chantier nouveau réalisable), aucun report au-delà ; pas d’extension de vie de l’offre.
Réglage 0 par défaut aux quatre niveaux, max=2 et flags numériques ; 2 inclut PO-03, chargement unique. Contrat SHA256 : orchestrator identique octet pour octet à 8c9c9e1a après retrait du seul bloc 2 ; chemins 0/1 et consommateurs métier conservés, sans promesse d’identité du rythme d’opcodes.
Validation : 14 tests modèle/contrats ; suite exacte demandée, référence 2387 → finale 2393, zéro échec/erreur, 7 skips et 2 expected failures inchangés ; logs `results/c77_theme4/{before,final}.log`, diff --check OK. Aucun Docker/partie/push ; compilation Squirrel, Save/Load moteur et gain économique non validés. Rapport préexistant préservé, ajout hors commit ; configuration principale contrôlée à la clôture.

## Pré-enregistrement porte A (Claude, 22/10, avant résultat)
Smokes 1×1 VPS (graine 42, 2 ans) : valeur 1 (`po03_c77defer_smoke_1x1`) et valeur 2 (`po03b_c77defer2_smoke_1x1`) 2/2, 0 erreur Squirrel ; valeur 2 : 1 C42_SUBSIDY_BUILD + 1 C42_SUBSIDY_WON contre 0 (4 offres expirées) en référence, une seule partie, descriptif.
Porte A V102 `po03_c77defer2_porteA_40x3_20261022`, code `8d8e277e`, VPS (`--cpus 3 --memory 2g --max-workers 3 --network host`), 40 graines habituelles, 3 ans,
référence `OpexAI[c77_intent_defer=0]` (= défauts master) contre `OpexAI[c77_intent_defer=2]`. Règle `gain_short` : Wilcoxon p < 0,05, borne basse IC95 bootstrap > 0, gain ≥ 4 %, garde de valeur 5 %.
Échec ⇒ défaut 0, branche non fusionnée. Succès ⇒ porte B 20×10 seulement avec l'accord de l'utilisateur. Aucun changement de défaut.

## Porte A — résultat (22/10)
`po03_c77defer2_porteA_40x3_20261022`, 40/40 paires complètes : profit/an +2,2 k£ (médiane −25,0 k), 16 V / 22 D / 2 E, Wilcoxon p = 1,0,
IC95 bootstrap [−70,4 k ; +78,5 k], valeur −0,98 % (garde tenue). Verdict **`fail_primary`** : neutre, aucun gain. Défaut 0, branche non fusionnée.
Le correctif Save/Load (T5) n'est de toute façon pas exercé par un banc (aucun rechargement) : adoption éventuelle = décision utilisateur, comme correctif de bogue neutre.

## Thème 1
Relecture du 23/10 sur `8d8e277e9f2d3cec9ef5cef89d9b6c7ef4135859` : audit **caduc sur le défaut et les subventions**, arrêt au rapport selon la consigne explicite ; aucune valeur 3 ajoutée.
Références suivantes relatives à `ai/OpexAI/`. `c77_opportunistic_candidates` et `C77_OPPORTUNISTIC_CANDIDATES` sont absents du code actuel : l'alternative « seulement sous 1 » n'existe plus.
AU DÉFAUT, `events.nut:58` et :129–142 routent les événements d'entité pertinents vers `_c77EnqueueEntity` (`orchestrator.nut:776`), sans cet ancien interrupteur ; les producteurs AIR ciblés existent aussi (`task_projects.nut:641`, :762, :872, :983).
Le worker applique la génération ciblée (`orchestrator.nut:472`, :495 ; `projects_generation.nut:123`), conserve les autres entités et insère les nouveaux projets (:140), puis peut enfiler un build (`orchestrator.nut:373`).
AU DÉFAUT, l'offre mémorisée enfile `c77_subsidy` (`event_handlers.nut:163–176`), qui injecte et resélectionne (`orchestrator.nut:942–975`) hors année AIR ; `c77_build` n'injecte rien : il vérifie la tête ciblée et appelle `_tryBuildProjects` (:720–769).
Les clés `c77|*` sont celles des intentions, pas du vivier : `projects_models.nut:4–26` produit `subsidy|ID` ou des clés origine/destination ; `projects_builders.nut:335` y ajoute les alternatives, sans marque de provenance C77.
Complète : `task_projects.nut:2012` met prior=null hors bootstrap, mais :2070–2079 transmet `_activeSubsidies` ; `projects.nut:493–501` recrée les offres via le MÊME générateur que l'injection, avec les gardes courantes, hors année AIR. Pas de perte systématique des subventions valides.
C76 complète passe aussi par `_rebuildProjects` (`orchestrator.nut:1313`, `scheduler_tasks.nut:460`) ; C76 par mode (:1387) remplace les candidats ordinaires du mode, conserve les autres et les subventions via `projects_generation.nut:134` / `projects_selection.nut:1546`.
PO-01c split : `po01c_regen.nut:299–312` remplace chaque mode mais protège les subventions par le même prédicat ; aucune protection spécifique des projets ordinaires d'entité.
Publication AIR : premier lot et apply final passent par rebuild (`scheduler_tasks.nut:170`, :219) ; les publications incrémentales intermédiaires préservent les autres modes (`projects_update.nut:489–498`) et revalident l'AIR.
Limite réelle AU DÉFAUT : un candidat ordinaire d'entité non régénéré disparaît lors du remplacement complet/de son mode ; la rotation fret (`task_projects.nut:2048–2066`, :2088–2092) suffit à l'expliquer. Ni disparition définitive de l'opportunité, ni perte économique démontrée ; ne pas confondre ce reliquat avec les subventions protégées.
Conclusion : réfutation de l'atténuation « C77 désactivé au défaut » et de l'extension aux subventions ; le reliquat d'entité subsiste au défaut. L'arrêt demandé si l'audit est caduc prime ici sur l'étape conditionnelle de codage ; code, réglage 0/1/2 et tests inchangés.
Validation : commande complète demandée, 2393 tests, zéro échec/erreur, 7 skips, 2 expected failures, identiques à `results/c77_theme4/final.log` sur 8d8e277e ; log `results/c77_theme1/suite.log`. Aucun Docker, partie ni push ; aucune qualification moteur/économique.
