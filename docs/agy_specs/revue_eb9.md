# Revue — suivi EB-9 du 12 novembre 2026

Revue de la lecture qui produit [EB9_suivi.md](EB9_suivi.md). Aucun diff Squirrel. Le classement et le stop sont ceux du HEAD `aa6ad5f9`.

## Chemins vérifiés

| Chemin | Effet au défaut `air_site_ranked=1`, `air_coverage_stop=0` |
|---|---|
| `settings.nut:675-678` | Installe `OpexAirRankedListed` pour tout appel ultérieur à `OpexAirFindSiteCatchmentListed`. |
| `projects.nut:351` et `:380` | Énumération initiale sans ville cible. Le classement parcourt le bassin. |
| `scheduler_tasks.nut:316` | Tranches suivantes, `targetTownId = -1`. Le retour anticipé du stop ne s'applique pas. |
| `event_handlers.nut:414-422` | `ET_TOWN_FOUNDED` marque le catalogue sale et enfile C77 sur la ville. La file du stop n'est alimentée qu'à réglage 1. |
| `events.nut:129-142` | La régénération ciblée reçoit `affectedKind` et `affectedId`. |
| `projects_generation.nut:204-206` | La tranche air passe l'identifiant de ville à `OpexAirPlans`. |
| `air_planning.nut:424-428` | La ville cible passe en tête ; le reste du bassin reste dans la liste. |
| `air_planning.nut:553-581` | Chaque ville encore dans la fenêtre appelle le chercheur classé. |
| `air_planning.nut:761-763` et `:820` | Les paires neuves se limitent à la ville cible quand son site est en tête. |
| `air_planning.nut:1791-1797` et `:2006` | Sommeil et file du stop, inertes au défaut 0. |

## Décision

Pas de correctif et pas de scan cyclique ajouté. Le classement multimodal de l'énumération initiale est déjà le défaut, qualifié seulement en air seul (+156,5 k£/an en A, +65,9 k£/an en B). Le smoke multimodal graine 42 à −183 k£/an reste une graine. Le 40×5 du 27 octobre a les deux réglages de sites déjà à 1 : il ne sépare pas le classement de la spirale.

Restreindre la recherche de sites à la seule ville de `ET_TOWN_FOUNDED` changerait l'ensemble des partenaires. La file `AIR_NEW_TOWN_QUEUE` ne porte pas cet identifiant jusqu'à `OpexAirPlans`. Le stop n'est donc pas isolé au sens de la tâche ouverte. Le code reste en l'état.

## Hors périmètre

Rail non lu pour en modifier le comportement. Aucun réglage. Aucune réactivation de passe « zéro candidat » par TTL, caisse ou calendrier.
