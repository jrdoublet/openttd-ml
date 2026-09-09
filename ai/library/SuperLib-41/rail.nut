/*
 * this file is part of superlib, which is an ai library for openttd
 * copyright (c) 2008-2012  Zuu
 *
 * superlib is free software; you can redistribute it and/or modify it
 * under the terms of the gnu general public license as published by
 * the free software foundation; version 2 of the license
 *
 * superlib is distributed in the hope that it will be useful,
 * but without any warranty; without even the implied warranty of
 * merchantability or fitness for a particular purpose.  see the
 * gnu general public license for more details.
 *
 * you should have received a copy of the gnu general public license
 * along with superlib; if not, see <http://www.gnu.org/licenses/> or
 * write to the free software foundation, inc., 51 franklin street,
 * fifth floor, boston, ma 02110-1301 usa.
 *
 */

/*
 * Thanks to krinn who contributed these two functions:
 *  - GetRailBitMask
 *  - AreRailTilesConnected
 *
 * Their source is from DictatorAI. I (Zuu) have changed the
 * coding style and added some comments as well as adopting it
 * to use the SuperLib ecosystem of utils, but the original code
 * is from krinn and DictatorAI.
 */

class _SuperLib_Rail {

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Rail tile info                                                  //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	// These bits correspond to if a tile have a rail bit that connect to
	// the given edge.
	static RAIL_BIT_NE = 1;
	static RAIL_BIT_SW = 2;
	static RAIL_BIT_NW = 4;
	static RAIL_BIT_SE = 8;


	// Return a nibble bitmask with each RAIL_BIT_NE,RAIL_BIT_SW,RAIL_BIT_NW,RAIL_BIT_SE direction set to 1
	// if there is a rail bit that connects to the given edge.
	//
	// The input of this function can eg. be the return from
	// AIRail.GetRailTracks(tile).
	function GetRailBitMask(rails);

	// This function check if two adjacent tiles are connected by rail.
	// It doesn't regard the forbid 90 degree turn setting, thus a true
	// result from this function does not guarantee that a train can travel
	// between the two tiles. (if you would like to improve this function
	// a patch is welcome)
	function AreRailTilesConnected(fromTile, toTile);
}

function _SuperLib_Rail::GetRailBitMask(rails)
// Return a nibble bitmask with each RAIL_BIT_NE,RAIL_BIT_SW,RAIL_BIT_NW,RAIL_BIT_SE direction set to 1
{
	if (rails == 255) return 0; // invalid rail

	local trackMap = AIList();
	trackMap.AddItem(AIRail.RAILTRACK_NE_SW,	_SuperLib_Rail.RAIL_BIT_NE + _SuperLib_Rail.RAIL_BIT_SW);	// AIRail.RAILTRACK_NE_SW
	trackMap.AddItem(AIRail.RAILTRACK_NW_SE,	_SuperLib_Rail.RAIL_BIT_NW + _SuperLib_Rail.RAIL_BIT_SE);	// AIRail.RAILTRACK_NW_SE
	trackMap.AddItem(AIRail.RAILTRACK_NW_NE,	_SuperLib_Rail.RAIL_BIT_NW + _SuperLib_Rail.RAIL_BIT_NE);	// AIRail.RAILTRACK_NW_NE
	trackMap.AddItem(AIRail.RAILTRACK_SW_SE,	_SuperLib_Rail.RAIL_BIT_SW + _SuperLib_Rail.RAIL_BIT_SE);	// AIRail.RAILTRACK_SW_SE
	trackMap.AddItem(AIRail.RAILTRACK_NW_SW,	_SuperLib_Rail.RAIL_BIT_NW + _SuperLib_Rail.RAIL_BIT_SW);	// AIRail.RAILTRACK_NW_SW
	trackMap.AddItem(AIRail.RAILTRACK_NE_SE,	_SuperLib_Rail.RAIL_BIT_NE + _SuperLib_Rail.RAIL_BIT_SE);	// AIRail.RAILTRACK_NE_SE
	local railmask = 0;
	foreach (tracks, value in trackMap)
	{
		if ((rails & tracks) == tracks) { railmask = railmask | value; }
		if (railmask == (_SuperLib_Rail.RAIL_BIT_NE + _SuperLib_Rail.RAIL_BIT_SW +
				_SuperLib_Rail.RAIL_BIT_NW + _SuperLib_Rail.RAIL_BIT_SE)) return railmask; // no need to test more tracks
	}
	return railmask;
}

function _SuperLib_Rail::AreRailTilesConnected(fromTile, toTile)
{
	// Check tile ownership
	local own_company = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
	if (AITile.GetOwner(fromTile) != own_company) return false; // not own by us
	if (AITile.GetOwner(toTile) != own_company)	  return false; // not own by us

	// Check that from and to tiles are the same rail type
	local from_rail_type = AIRail.GetRailType(fromTile);
	if (AIRail.GetRailType(toTile) != from_rail_type) return false; // not same railtype

	// Based on the direction between fromTile and toTile, set the required RAIL_BIT_* bits.
	local direction = _SuperLib_Direction.GetDirectionToAdjacentTile(fromTile, toTile);
	local from_tile_mask = _SuperLib_Rail.GetRailBitMask(AIRail.GetRailTracks(fromTile));
	local to_tile_mask = _SuperLib_Rail.GetRailBitMask(AIRail.GetRailTracks(toTile));
	local from_tile_need, to_tile_need = 0;
	switch (direction)
	{
		case _SuperLib_Direction.DIR_NW: // NW -> SE
			from_tile_need = _SuperLib_Rail.RAIL_BIT_NW;
			to_tile_need = _SuperLib_Rail.RAIL_BIT_SE;
			break;
		case _SuperLib_Direction.DIR_SE: // SE -> NW
			from_tile_need = _SuperLib_Rail.RAIL_BIT_SE;
			to_tile_need = _SuperLib_Rail.RAIL_BIT_NW;
			break;
		case _SuperLib_Direction.DIR_NE: // NE -> SW
			from_tile_need = _SuperLib_Rail.RAIL_BIT_NE;
			to_tile_need = _SuperLib_Rail.RAIL_BIT_SW;
			break;
		case _SuperLib_Direction.DIR_SW: // SW -> NE
			from_tile_need = _SuperLib_Rail.RAIL_BIT_SW;
			to_tile_need = _SuperLib_Rail.RAIL_BIT_NE;
			break;
		default:
			// Not a main direction or the tiles are not adjacent.
			return false;
	}
	// if we have a depot, make it act like it is a classic rail if its entry match where we going or come from
	if (AIRail.IsRailDepotTile(toTile)   && AIRail.GetRailDepotFrontTile(toTile) == fromTile)	to_tile_mask = to_tile_need;
	if (AIRail.IsRailDepotTile(fromTile) && AIRail.GetRailDepotFrontTile(fromTile) == toTile) from_tile_mask = from_tile_need;

	// Is toTile a bridge or tunnel?
	if (AIBridge.IsBridgeTile(toTile) || AITunnel.IsTunnelTile(toTile))
	{
		local end_at = null;
		end_at = AIBridge.IsBridgeTile(toTile) ? AIBridge.GetOtherBridgeEnd(toTile) : AITunnel.GetOtherTunnelEnd(toTile);
		local jumpdir = _SuperLib_Direction.GetDirectionToTile(toTile, end_at);
		if (jumpdir == direction) // if the bridge/tunnel goes the same direction, then consider it a plain rail
		{
			to_tile_mask = to_tile_need;
		}
	}
	// is fromTile a bridge or tunnel?
	if (AIBridge.IsBridgeTile(fromTile) || AITunnel.IsTunnelTile(fromTile))
	{
		local end_at = null;
		end_at = AIBridge.IsBridgeTile(fromTile) ? AIBridge.GetOtherBridgeEnd(fromTile) : AITunnel.GetOtherTunnelEnd(fromTile);
		local jumpdir = _SuperLib_Direction.GetDirectionToTile(end_at, fromTile); // reverse direction to find the proper one
		if (jumpdir == direction) // if the bridge/tunnel goes the same direction, then consider it a plain rail
		{
			from_tile_mask = from_tile_need;
		}
	}

	// Finally, check the bit masks of available track connections against the *_need variables.
	return (from_tile_mask & from_tile_need) == from_tile_need &&
			(to_tile_mask & to_tile_need) == to_tile_need;
}

