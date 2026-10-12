# C122 retry — devenir des six relances et recherche de site

[Preuves versionnées des cinq graines exposées, ON/OFF](../evidence/review/parameter_cleanup_20261012/README.md). Publication documentaire demandée le12/10 ; aucune réparation ni nouvelle campagne n'est incluse.

Audit du12/10 demandé après le [40×5](c122_threat_retry_40x5_20261012.md). Analyse des logs existants et du code, aucun changement comportemental ni partie supplémentaire. Même bundle `d7ac47625b0bba4d71065469b2ae9cabd01b48eb2fc87af4ff6ce652bce3a219`. Verdict économique `fail_primary` inchangé.

## Ce que les relances ont donné

Suivi par graine/TownID/numéro de menace, depuis la ligne exacte `phase=retry queued=1`, y compris les autres tentatives du même jour. Une construction ultérieure observée ne prouve pas à elle seule que le worker C77 a causé ce succès ; ses étapes ne sont pas instrumentées dans cette campagne.

| Graine / ville | Construction observée après relance | Suite locale ON | Contrôle OFF, même ville |
|---|---|---|---|
| 1 /12 | Aucune ;56 rejets suivants, dont55 siteA/B et1 build_failed | Monopole adverse J+185 après retry | Monopole adverse |
| 1 /4 | Aucune ;4 rejets de site le jour du retry, aucun outcome suivant | Monopole adverse J+157 | Pas de fermeture de cette ville dans les traces de menace OFF |
| 2026 /37 | Aucune ;7 rejets suivants, dont6 siteA/B et1 build_failed | Monopole adverse J+278 | Monopole adverse |
| 232037 /25 | `outcome=built` J+19 | Opex prend la ville J+23 | Monopole adverse |
| 314 /18 | `outcome=built` J+45 | Opex prend la ville J+48 | Opex la prend aussi, plus tard dans cette trajectoire |
| 65537 /17 | `outcome=built` J+582, après5 autres rejets | Opex prend la ville J+622 | Opex la prend aussi, plus tard dans cette trajectoire |

Donc trois constructions ultérieures sur six cas, dont une très tardive. Un cas présente une prise Opex ON contre monopole adverse OFF ; les deux autres prises existent aussi sous OFF. Cela précise l'exposition locale, sans fabriquer trois sauvetages causaux ni réanalyser économiquement le seul sous-ensemble exposé.

[Extraction des événements et résultats](../results/c122_retry_40x5_20261012_r1_source/results/c122_retry_40x5_20261012_r1.retry_followup.json), recalcul par `results/audit_c122_retry_followup_20261012.py`. Les clés `air|src|dst|cargo|kind` sont fondées sur les villes des projets, **pas les ancres d'aéroport** (`OpexProjectAttemptKey`/constructeurs). Répéter cette clé ne prouve pas qu'une même ancre invalide est retentée.

## Réparation et limites observables

Le retry enfile une régénération C77 ; `queued=1` ne certifie ni fin de régénération, ni nouveau site valide, ni construction. Après56 rejets dans le cas1/12, un problème de validation/recherche ou de délai est une hypothèse plausible, pas une cause démontrée.

Le rejet `siteA_unbuildable`/`siteB_unbuildable` est générique : il peut venir du filtre cheap, de la géométrie, du changement de ville/état, d'une limite de stations ou d'un test de construction. Le champ erreur reste souvent0 ici ; il manque le motif fin et l'ancre du site rejeté. Des outcomes de construction portent `BFAIL error=263`, soit `ERR_FLAT_LAND_REQUIRED` dans [l'API OpenTTD15.3](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_error.hpp) : cohérence du pré-test/nivellement/pose à examiner, sans conclure qu'elle explique tous les rejets.

Le motif `c122_threat_retry` ne passe pas `c83Race=true` au worker, contrairement à `c83_slot_race`. **Ce n'est pas une perte démontrée du ciblage au défaut courant** : `c83Race` commande notamment le prototype local `c83_local_repair=0`, tandis que `OpexAirPlans` reçoit dans les deux cas le TownID cible et lui applique la contrainte physique. Le prototype C83 local reste non qualifié et ne doit pas être réactivé par assimilation.

## Rectangle et API

Chercheur courant : `AIR_SITE_RADIUS=25`, couronnes4..25, contrainte supplémentaire de distance ville–emprise≤25. V94 utilise déjà `AITileList.AddRectangle`/`RemoveRectangle` et les filtres natifs de liste (`air_sites.nut::OpexAirFindSiteRing`). C96 actif s'arrête après4 sites valides, ou au plus1 couronne supplémentaire après le premier succès, sous budget de sondes. Une simple hausse du rayon ne change donc ni le plafond de distance ni l'arrêt anticipé sur des sites jugés valides.

L'[API native15.3 des aéroports](https://github.com/OpenTTD/OpenTTD/blob/15.3/src/script/api/script_airport.hpp) offre dimensions, autorité/ bruit et `BuildAirport` à une ancre, mais pas de recherche automatique d'emplacement. `BuildAirport` sous `AITestMode` est déjà utilisé. La [liste native de tuiles](https://docs.openttd.org/ai-api/classAITileList) permet de construire un rectangle de recherche, pas de certifier automatiquement un site.

**Une fonction de bibliothèque existe localement** : `ai/Library/SuperLib-41/airport.nut::_SuperLib_Airport::FindInTownAirportPlacement`. Elle cherche sur les tuiles de ville fournies par `Tile.GetTownTiles` (rayon20+population/1000), filtre ville/cargo/bruit, estime le nivellement, impose un coût inférieur à1/10 de la caisse et ajoute une randomisation. C'est du Squirrel vendorisé, pas une primitive native ni un remplacement identique du contrat Opex. Son résultat exige une validation compatible C83/catchment/nivellement ; aucune importation ni copie effectuée.

## Intervention à spécifier avant tout nouveau test

Première preuve à obtenir au rejet : ancre/type/emprise, motif cheap ou erreur API exacte, état du slot, puis étapes du worker C77 et site réellement choisi. Distinguer absence d'alternative, faux positif de pré-test et délai de réparation. Les logs actuels ne permettent pas de tester rétroactivement un rectangle plus grand au même état de carte.

Ensuite seulement, comparer en diagnostic local une recherche d'alternative sur **l'endpoint en échec**, avec exclusion de l'ancre rejetée et exploration plus large/plus complète si nécessaire. Conserver l'autre endpoint et la même ville physique, vérifier catchment/bruit/coût, puis recalculer les devis affectés avant admission. C'est une hypothèse à exposer, pas une adoption du défaut ni un motif pour élargir globalement toutes les recherches.

V133, déjà non qualifié, met une ville entière en quarantaine730 jours : ne pas le réarmer pour cette hypothèse. Travaux parallèles préservés ; aucun changement IA, campagne, commit ni push.
