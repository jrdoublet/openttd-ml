# Session cloud 1 — courrier sur les lignes de bus, puis renfort corrigé

Lire d'abord `docs/cloud/README.md`. Branche : `cloud/courrier-bus` depuis `road1y-s17`.

## Partie 1 — `road1y_mail_on_pax` (prioritaire)

Constat : AAA route seule gagne ~297 k£/an de courrier à 3 ans sur la graine
613553 (133-154 k£ sur 781335 et 100) ; OpexAI 0.

1. Analyse (données + `AAAHogEx-115_source.tar.gz`, `road.nut`, `estimator.nut`) :
   comment AAA choisit ses lignes MAIL (même paire que ses bus ? arrêts
   partagés ? distance ? nombre de fourgons ? ordres de chargement ?), profit
   par fourgon et par ligne dans `road1y_3ans_defaut_3graines.jsonl.gz`
   (`service_key` `cargo=2`). Chiffrer avant de coder.
2. Code OpexAI derrière `road1y_mail_on_pax` (défaut 0) : sur une paire de villes
   déjà desservie par nos bus PAX, ajouter des fourgons postaux qui réutilisent la
   route et le dépôt existants, avec arrêts camion (ou arrêts communs si l'API le
   permet) couvrant la production MAIL réelle des deux villes. Estimation du
   profit sur le volume MAIL capté réel ; achat seulement si profit prédit ≥
   seuil et ROI comparable aux nouvelles lignes PAX ; renfort plafonné.
   Ne pas réutiliser le générateur ROAD100-27 (rejeté). Sauvegarde/chargement
   des lignes MAIL, abandon/rollback propres.
   Points d'entrée probables : `ai/OpexAI/bus_districts_overrides.nut`
   (`_refleetRoadLines`, sites de bus), `builder_road.nut` (ordres ~5245, achat
   de véhicules), `catalog.nut` (`mailCargo`, `roadEngineByCargo`).
3. Coût en opcodes estimé par tour, et journal `ROAD1Y_MAIL` (paire, arrêts,
   volume, fourgons, profit prédit) pour la mesure.

## Partie 2 — `road1y_fleet_unlock` v2 (si le temps le permet)

Reprendre `diag_fleet_unlock_agy.md` : (a) plafond = 
`ROAD1Y_FLEET × min(arrêts A, arrêts B)` (actuellement la somme, bit 4 de
`bus_districts_overrides.nut` ~2054) ; (b) renfort seulement si le profit marginal
estimé d'un bus ajouté dépasse un seuil ET si la caisse reste au-dessus du coût
d'ouverture de la meilleure ligne du vivier (ou si le vivier est vide). Nouveau
bit (16) plutôt que modifier les bits mesurés.

## Fin

Rapport `docs/cloud/rapport_courrier_bus.md` + commandes de mesure VPS pour
`road1y_mail_on_pax=1` et le nouveau bit.
