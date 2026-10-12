# Revue OpexAI — plan en étapes du 12 octobre 2026

Préparée à la demande de l'utilisateur pour être lancée **étape par étape via le scheduler**.
Chaque étape est un prompt autonome dans [docs/revue/](revue/README.md) : une session neuve
le lit et l'exécute, sans contexte préalable.

## Périmètre

Le code modifié le 12/10, et les deux branches en attente de banc.

| Source | Référence | Contenu |
|---|---|---|
| master | `978d098^..d7055bc` (~1 100 lignes ajoutées, 20 fichiers) | catalogue AIR AC04-B/AC05/AC06, découpage CD01–CD06, V147 (phases du catalogue en entrées de file), retraits C121/C122 et des paramètres de classement AIR, V153 (`rail_end_jump_connect`), V154 (`select_bisect_insert`), V155 (`air_fleet_c121_preguard`, inerte), V156 (`incr_revalidate_index`) |
| `origin/v158-lazy-select` | `3d19c55` | V158 `air_publish_lazy_select` (resélection paresseuse à la publication AIR) |
| `origin/v160-fleet-routes-index` | `9830fc6` | V160 `air_fleet_routes_index` (index des routes par aéroport dans `fleet.resize`) |

Défauts au 12/10 : V147, V153, V154 et V156 à 1 ; V155, V158 et V160 à 0 (V158 et V160 passés à 1 le 12/10 au soir, après leur porte B).

## Étapes

Les étapes 01 à 06 sont **indépendantes** : elles peuvent tourner dans n'importe quel ordre, ou en
parallèle. L'étape 07 consolide et doit passer en dernier.

| Étape | Prompt | Sujet | Modèle / effort conseillés |
|---|---|---|---|
| 01 | [réglages et retraits](revue/2026-10-12_etape_01_reglages_retraits.md) | `info.nut` ↔ `globals_pre.nut` ↔ `settings.nut` ↔ tests ; lecteurs résiduels des réglages retirés | Sonnet / medium |
| 02 | [catalogue AIR et V147](revue/2026-10-12_etape_02_catalogue_air_v147.md) | phases du catalogue, entrées de file, instantanés AC06, persistance | Opus / high |
| 03 | [sélection : V154 et V158](revue/2026-10-12_etape_03_selection_v154_v158.md) | équivalence de la dichotomie ; lecteurs de `projects.best` sous V158 | Opus / high |
| 04 | [revalidation indexée V156](revue/2026-10-12_etape_04_revalidation_v156.md) | prédicats indexés contre historiques ; les 26 écarts résiduels | Opus / high |
| 05 | [rail V153](revue/2026-10-12_etape_05_rail_v153.md) | jonction en bout de pont/tunnel : faux positifs possibles | Sonnet / high |
| 06 | [flotte AIR : V155 et V160](revue/2026-10-12_etape_06_flotte_air_v155_v160.md) | index des routes, invalidation, coût résiduel de `fleet.resize` | Sonnet / high |
| 07 | [synthèse](revue/2026-10-12_etape_07_synthese.md) | classement des constats, entrées pour `docs/taches.md` | Sonnet / medium |

## Commande à donner au scheduler

> Exécute le prompt docs/revue/2026-10-12_etape_NN_<sujet>.md du dépôt openttd-ml, et lui seul.

Chaque étape écrit son rapport dans `docs/revue/2026-10-12_rapport_NN_<sujet>.md`, le commite seul
et le pousse sur master. L'étape 07 lit les six rapports.
