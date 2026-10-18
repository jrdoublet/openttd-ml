/* difficulty.nut — Niveaux de difficulte et table centrale des capacites.
 *
 * Quatre niveaux :
 *   0 = facile (easy)
 *   1 = moyen (medium)
 *   2 = difficile (hard)
 *   3 = personnalise (custom) — profil de reference des bancs.
 *
 * Contrat :
 * - Aucune decision ne lit OPEX_DIFFICULTY directement hors de difficulty.nut et settings.nut.
 * - OpexLevelAllows(feature) est la fonction unique de consultation des capacites.
 * - Le niveau 3 n'a aucun bridage et reste strictement identique au comportement historique.
 * - Le niveau 2 autorise tout sauf les gestes anticoncurrentiels (V250, actions futures visant un rival).
 * - Les niveaux 0 et 1 brident les comportements agressifs selon la table des capacites.
 */

OPEX_DIFFICULTY <- 3;

/* Niveaux minimums requis pour chaque fonctionnalite / comportement.
 * Une fonctionnalite est autorisee si OPEX_DIFFICULTY >= OPEX_DIFFICULTY_MIN_LEVEL[feature].
 */
OPEX_DIFFICULTY_MIN_LEVEL <- {
  /* Gestes anticoncurrentiels (droits exclusifs V250, actions futures ciblant un rival).
   * Reserve au niveau 3 (personnalise). Coupe en difficile (2), moyen (1), facile (0). */
  "v250_rights": 3,
  "anticompetitive": 3,

  /* Bridages simples pour niveaux 0 et 1 (ne coutent rien au niveau 3) :
   * - "preempt_last_airport_slot" : prendre le dernier creneau aeroport d'une ville dispute (niveau 2+)
   * - "encroach_rival_catchment" : construire dans le bassin d'une gare rivale (niveau 2+)
   * - "aggressive_expansion" : developpement rapide continu (niveau 1+)
   */
  "preempt_last_airport_slot": 2,
  "encroach_rival_catchment": 2,
  "aggressive_expansion": 1,
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

/* Helper pour tester un niveau minimum sans exposer la variable OPEX_DIFFICULTY */
function OpexDifficultyAtLeast(level)
{
  return OPEX_DIFFICULTY >= level;
}

/* Nom du niveau pour affichage ou journalisation */
function OpexDifficultyName(level = null)
{
  if (level == null) level = OPEX_DIFFICULTY;
  if (level == 0) return "easy";
  if (level == 1) return "medium";
  if (level == 2) return "hard";
  return "custom";
}
