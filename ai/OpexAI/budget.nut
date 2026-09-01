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

class OpexBudget {
  totals = null;   // categorie -> opcodes cumules
  _tick = 0;
  _left = 0;
  _open = false;

  constructor()
  {
    totals = {};
  }

  function begin()
  {
    this._tick = AIController.GetTick();
    this._left = AIController.GetOpsTillSuspend();
    this._open = true;
  }

  /* Cloture la mesure et l'impute a une categorie. Rend les opcodes consommes. */
  function end(category)
  {
    if (!this._open) return 0;
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
