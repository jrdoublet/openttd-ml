/* difficulty.nut — Niveaux de difficulte et table centrale des capacites.
 *
 * Quatre niveaux :
 *   0 = facile (easy)
 *   1 = moyen (medium)
 *   2 = difficile (hard) — defaut : jeu complet sans geste anticoncurrentiel.
 *   3 = personnalise (custom) — autorise en plus les gestes anticoncurrentiels.
 *
 * Contrat :
 * - Aucune decision ne lit OPEX_DIFFICULTY directement hors de difficulty.nut et settings.nut.
 * - OpexLevelAllows(feature) est la fonction unique de consultation des capacites.
 * - Le niveau 3 n'a aucun bridage et reste strictement identique au comportement historique.
 * - Le niveau 2 autorise tout sauf les gestes anticoncurrentiels (V250, actions futures visant un rival).
 * - Les niveaux 0 et 1 appliquent aussi les gardes de courtoisie ci-dessous.
 */

OPEX_DIFFICULTY <- 2;

/* Vrai seulement aux niveaux 0 et 1 (leviers A et B). Lu en garde avant tout appel
 * de bridage pour que les niveaux 2 et 3 ne paient qu'une lecture de globale. */
OPEX_LEVEL_LIMITS <- false;

/* Niveaux minimums requis pour chaque fonctionnalite / comportement.
 * Une fonctionnalite est autorisee si OPEX_DIFFICULTY >= OPEX_DIFFICULTY_MIN_LEVEL[feature].
 */
OPEX_DIFFICULTY_MIN_LEVEL <- {
  /* Gestes anticoncurrentiels (droits exclusifs V250, actions futures ciblant un rival).
   * Reserve au niveau 3 (personnalise). Coupe en difficile (2), moyen (1), facile (0). */
  v250_rights = 3,
  anticompetitive = 3,

  /* V261b, decision utilisateur du 18/10 : courtoisie sans reglage public. */
  air_joined_road_stops = 2,
  water_depot_dock_front = 3,
  secondary_graft_rival_served = 3,

  /* Levier A : aeroports */
  preempt_last_airport_slot = 2,
  airport_rival_town = 1,

  /* Levier B : gares */
  compete_primary_industry = 2,
  encroach_rival_catchment = 1
};

/* Consultation unique d'autorisation d'une fonctionnalite selon le niveau actif. */
function OpexLevelAllows(feature)
{
  if (OPEX_DIFFICULTY >= 3) return true;
  if (feature in OPEX_DIFFICULTY_MIN_LEVEL) {
    return OPEX_DIFFICULTY >= OPEX_DIFFICULTY_MIN_LEVEL[feature];
  }
  return true;
}
