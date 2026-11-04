/* RAIL-KEEP (rail_expand_keep=1, defaut 0).
 *
 * Fait nomme le 04/11 (docs/cloud_portefeuille_20261104.md) : des que V284
 * a cree son etat (3 ans et 1 M£ de caisse au defaut, 250 k£ sous RAIL-FILL),
 * la garde historique de _expandRailLines saute TOUTES les lignes fret, ce qui
 * coupe le doublement « Cas 2 » (seconde voie independante + second train) et
 * le « Cas 1 » (second train sur double existante) au moment exact ou la caisse
 * devient oisive. RAIL-SEARCH-PRIO a montre le prix de ce canal : ses 64
 * preemptions d'upgrades ont coute 24 trains et -325 k£/an sur le 4x6.
 *
 * Sous RAIL-KEEP, seule la ligne de la transaction V284 en cours est exclue :
 * les autres lignes fret gardent le parcours historique, avec toutes ses
 * gardes (attente, caisse, recherche A* libre, abandon memorise). V284 de son
 * cote ne choisit jamais pendant une recherche d'upgrade
 * (task_v284.nut, garde `_railSearch.kind == "upgrade"`) et ne prend que des
 * lignes simples a une rame : les deux mecanismes ne touchent pas la meme
 * ligne au meme moment. */

function OpexRailExpandKeepSkip(owner, line)
{
  if (!("kind" in line) || line.kind != "freight") return false;
  if (!OpexV284Busy(owner) || !("lineId" in line)) return false;
  return owner._v284State.pending.lineId == line.lineId;
}
