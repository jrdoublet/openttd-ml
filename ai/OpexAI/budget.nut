/* Comptabilite du budget d'opcodes.
 *
 * Le budget n'est pas un stock mais un DEBIT : OPS_PER_TICK opcodes par tick, non reportables,
 * perdus s'ils ne sont pas consommes. La seule decision d'une IA est donc de savoir OU part le
 * prochain tick de calcul, jamais s'il faut le depenser.
 *
 * GetOpsTillSuspend() rend le RESTE du tick courant. Un bloc de travail qui traverse des ticks se
 * compte donc : reste_au_depart + (ticks_traverses - 1) * OPS_PER_TICK + (OPS_PER_TICK - reste).
 * Verifie dans le binaire 15.3 : script_max_opcode_till_suspend = 10000.
 *
 * ATTENTION : non reentrant. Un seul begin()/end() a la fois, jamais imbrique.
 */

OPS_PER_TICK <- 10000;

/* Mesure d'opcodes sans passer par l'instance partagee OpexBudget : chaque appel cree son propre
 * "mark" local, donc aucun risque de reentrance meme dans une fonction qui ne recoit pas `budget`.
 * Meme formule que OpexBudget.end(). */
function OpexOpsMeasureBegin()
{
  return { tick = AIController.GetTick(), left = AIController.GetOpsTillSuspend() };
}

function OpexOpsMeasureEnd(mark)
{
  local left = AIController.GetOpsTillSuspend();
  local elapsed = AIController.GetTick() - mark.tick;
  return elapsed <= 0
    ? mark.left - left
    : mark.left + (elapsed - 1) * OPS_PER_TICK + (OPS_PER_TICK - left);
}

class OpexBudget {
  totals = null;   // categorie -> opcodes cumules
  _tick = 0;
  _left = 0;
  _open = false;
  /* Compteur d'imbrications detectees. L'en-tete documente la non-reentrance depuis toujours,
   * mais RIEN ne la verifiait : begin() ecrasait sans condition et end() rendait 0 en silence.
   * Avec ~40 sites d'appel, une imbrication future attribuerait le cout du bloc interne a la
   * categorie externe, sans exception ni trace (docs/taches.md S0 septies). */
  nested = 0;

  constructor()
  {
    totals = {};
  }

  _depth = 0;

  function begin()
  {
    /* Imbrication : on compte et on conserve la marque externe, afin que le
     * cout total reste impute a la categorie externe au lieu d'etre perdu. */
    if (this._open) { this.nested++; this._depth++; return; }
    this._tick = AIController.GetTick();
    this._left = AIController.GetOpsTillSuspend();
    this._open = true;
  }

  /* Cloture la mesure et l'impute a une categorie. Rend les opcodes consommes. */
  function end(category)
  {
    if (!this._open) return 0;
    if (this._depth > 0) { this._depth--; return 0; }
    local left = AIController.GetOpsTillSuspend();
    local elapsed = AIController.GetTick() - this._tick;
    local spent = elapsed <= 0
      ? this._left - left
      : this._left + (elapsed - 1) * OPS_PER_TICK + (OPS_PER_TICK - left);
    this._open = false;
    if (category in this.totals) this.totals[category] += spent;
    else this.totals.rawset(category, spent);
    return spent;
  }

  function get(category)
  {
    return (category in this.totals) ? this.totals[category] : 0;
  }

  function total()
  {
    local sum = 0;
    foreach (value in this.totals) sum += value;
    return sum;
  }

  /* Part du debit reellement consommee depuis startTick, en pour mille.
   * C'est l'instrument central : un tick non calcule est un tick perdu. */
  function utilisationPerMille(startTick)
  {
    local elapsed = AIController.GetTick() - startTick;
    if (elapsed <= 0) return 0;
    return (this.total() * 1000) / (elapsed * OPS_PER_TICK);
  }
}
