/*
 * This file is part of SuperLib, which is an AI Library for OpenTTD
 * Copyright (C) 2010  Zuu
 *
 * SuperLib is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 2 of the License
 *
 * SuperLib is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with SuperLib; If not, see <http://www.gnu.org/licenses/> or
 * write to the Free Software Foundation, Inc., 51 Franklin Street,
 * Fifth Floor, Boston, MA 02110-1301 USA.
 *
 */

class _SuperLib_Industry
{
	/* Returns true if the given cargo is produced by the industry.
	 * That is if the industry lists the cargo in the GetProducedCargo list.
	 * No checking is done of the actual production levels.
	 */
	static function IsCargoProduced(industry_id, cargo_id);
}


function _SuperLib_Industry::IsCargoProduced(industry_id, cargo_id)
{
	local industry_type = AIIndustry.GetIndustryType(industry_id);
	local prod_list = AIIndustryType.GetProducedCargo(industry_type);
	return prod_list != null? prod_list.HasItem(cargo_id) : false;
}
