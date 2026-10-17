"""Shared retirement assertions for the adopted AIR paths (V237)."""
from pathlib import Path
import re

AI = Path(__file__).resolve().parents[1] / "ai/OpexAI"


RETIRED = (
    'air_site_min_catchment',
    'c96_air_site_catchment',
    'c117_lean_sampling',
    'air_c121_physical_payment_days',
    'c121_air_winner_fusion',
    'c121_air_game_engine',
    'c121_catalog_incremental',
    'c121_catalog_air_first_year',
    'c121_flat_bootstrap',
    'c121_air_first_year_rail_prep',
    'c121_air_one_or_two_planes',
    'c121_air_first_live_growth',
    'air_p0_direct_realization',
    'air_route_plane_selection',
    'air_early_slot',
    'air_fleet_cooldown_prefilter',
    'air_fleet_routes_index',
    'v161_fleet_net_marginal',
    'c80_air_hub_index',
    'c80_marginal_floor',
    'v94_air_site_list',
    'air0310_v96_shortcut_lean',
    'air0310_one_two_fused',
    'air0310_incremental_publish',
    'air0310_hub_snapshot',
    'air0310_site_validity_cache',
    'v141_catalog_incremental',
    'v147_air_catalog_tasks',
    'ac04_extra_site_dedup',
    'ac05_skip_unused_hub_income',
    'ac06_c76_snapshot_ack',
    'ac04_hub_usage_gate',
    'air_publish_lazy_select',
)


def assert_retired(case, names):
    info = (AI / "info.nut").read_text(encoding="utf-8")
    settings = (AI / "settings.nut").read_text(encoding="utf-8")
    globals_pre = (AI / "globals_pre.nut").read_text(encoding="utf-8")
    for name in names:
        with case.subTest(retired=name):
            case.assertNotIn(f'name = "{name}"', info)
            case.assertNotIn(f'GetSetting("{name}")', settings)
            case.assertNotRegex(globals_pre, rf'(?m)^{re.escape(name.upper())}\s*<-')
