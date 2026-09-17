/* Measurement-only fixture for review items 10.5 / M4-16.4.
 *
 * Mirrors the memory-dominant part of _MinchinWeb_Lakes_::constructor exactly:
 *   this._map = AIList();
 *   for (local i = 0; i < AIMap.GetMapSize(); i++) this._map.AddItem(i, -2);
 *
 * The object is retained as a controller field so the VM cannot reclaim it.  The empty arrays
 * below mirror the rest of the constructor; their fixed cost is negligible but keeps the probe
 * structurally faithful.  No transport decision or game command is issued.
 */
class WaterMemoryProbe extends AIController {
  _map = null;
  _connections = null;
  _areas = null;
  _open_neighbours = null;
  _group_tiles = null;

  function Start() {
    local startTick = AIController.GetTick();
    local startLeft = AIController.GetOpsTillSuspend();
    if (AIController.GetSetting("allocate") != 0) {
      this._map = AIList();
      for (local i = 0; i < AIMap.GetMapSize(); i++) {
        this._map.AddItem(i, -2);
      }
      this._connections = array(0);
      this._areas = array(0);
      this._open_neighbours = array(0);
      this._group_tiles = array(0);
    }
    local left = AIController.GetOpsTillSuspend();
    local elapsed = AIController.GetTick() - startTick;
    local ops = elapsed <= 0
        ? startLeft - left
        : startLeft + (elapsed - 1) * 10000 + (10000 - left);
    local signTile = AIMap.GetTileIndex(AIMap.GetMapSizeX() / 2, AIMap.GetMapSizeY() / 2);
    AISign.BuildSign(signTile, "WMP|" + ops + "|" + elapsed + "|" + AIMap.GetMapSize()
                              + "|" + AIMap.GetMapSizeX());
    while (true) AIController.Sleep(1);
  }
}
