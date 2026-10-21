"""V307 1.9b, tests de contrat AVANT implementation du builder.

Les tests purs de geometrie definissent les cas attendus sans lancer OpenTTD.
Les tests de raccordement Squirrel restent volontairement ROUGES tant que
v307_sink_room et ses fonctions ne sont pas codes. Ne pas les marquer xfail :
une implementation doit les faire passer et etre validee par un smoke reel.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read_ai(name):
    return (AI / name).read_text(encoding="utf-8")


def squirrel_function(source, name):
    """Bloc top-level, sans parser les accolades imbriquees dans Squirrel."""
    match = re.search(rf"(?m)^function\s+{re.escape(name)}\s*\(", source)
    if match is None:
        return ""
    next_function = re.search(r"(?m)^function\s+", source[match.end():])
    stop = match.end() + next_function.start() if next_function else len(source)
    return source[match.start():stop]


@dataclass(frozen=True)
class Platform:
    """Plan B de reference : ancre, sens longitudinal, longueur, sortie voie."""

    x: int
    y: int
    axis: str  # 'x' = NE_SW, 'y' = NW_SE (convention actuelle)
    length: int
    far_exit: bool


def eligible_initial_freight(kind, cargo, producers, shared_dest=False, joined=False):
    """Oracle du filtre : sources DISTINCTES du meme cargo, gare B encore neuve."""
    return (kind == "freight" and not shared_dest and not joined
            and len(set(producers.get(cargo, ()))) >= 2)


def parallel_room(plan, source, clear, max_side=2):
    """Oracle du quai reserve, oppose au cote transversal de la source.

    clear(x,y) represente les trois controles carte : tuile valide,
    constructible ET plate. La simulation BuildRailStation reste requise dans
    le code Squirrel reel. Pour largeur 2, seul le cote adjacent (dist=1)
    permet d'agrandir directement la gare.
    """
    if plan.axis == 'x':
        shift = (0, 1)
        along = (1, 0)
        source_offset = source[1] - plan.y
    elif plan.axis == 'y':
        shift = (1, 0)
        along = (0, 1)
        source_offset = source[0] - plan.x
    else:
        raise ValueError('Orientation de quai inconnue')
    if source_offset == 0:
        return []  # Le cote oppose n'est pas determine par le seul centre source.
    flip = -1 if source_offset > 0 else 1
    far = plan.length - 1 if plan.far_exit else 0
    lead_dist = plan.length if plan.far_exit else -1
    plans = []
    for distance in range(1, max_side + 1):
        x = plan.x + shift[0] * distance * flip
        y = plan.y + shift[1] * distance * flip
        tiles = [(x + along[0] * i, y + along[1] * i)
                 for i in range(plan.length)]
        lead = (x + along[0] * lead_dist, y + along[1] * lead_dist)
        if all(clear(*t) for t in tiles) and clear(*lead):
            plans.append((distance, flip, tiles, lead))
    return plans


def room_filter(plans, source, clear, bit):
    """Spec : si tous les plans echouent, retour EXACT des plans originaux."""
    if bit not in (1, 2):
        return list(plans)
    tested = [(p, parallel_room(p, source, clear)) for p in plans]
    kept = [p for p, room in tested if any(
        bit == 1 or dist == 1 for dist, _, _, _ in room)]
    return kept if kept else list(plans)


def station_anchor_for_two(plan, flip):
    """BuildRailStation largeur=2 s'etend sur l'axe transverse positif.

    La premiere ligne doit conserver son quai et son station_exit ; seule
    l'ancre du RECTANGLE de la gare change quand le deuxieme quai est du cote
    negatif. Le Squirrel devra appliquer le meme decalage au devis et a la pose.
    """
    if flip not in (-1, 1):
        raise ValueError('Cote invalide')
    if flip > 0:
        return plan.x, plan.y
    return (plan.x, plan.y - 1) if plan.axis == 'x' else (plan.x - 1, plan.y)


class TestPolicyReference(unittest.TestCase):
    def test_only_initial_freight_two_distinct_producers_same_cargo(self):
        sources = {'COAL': [11, 12], 'WOOD': [13]}
        self.assertTrue(eligible_initial_freight('freight', 'COAL', sources))
        for kwargs in ({'kind': 'pax', 'cargo': 'COAL', 'producers': sources},
                       {'kind': 'freight', 'cargo': 'WOOD', 'producers': sources},
                       {'kind': 'freight', 'cargo': 'OIL_', 'producers': sources},
                       {'kind': 'freight', 'cargo': 'COAL', 'producers': sources, 'shared_dest': True},
                       {'kind': 'freight', 'cargo': 'COAL', 'producers': sources, 'joined': True},
                       {'kind': 'freight', 'cargo': 'COAL', 'producers': {'COAL': [11, 11]}}):
            with self.subTest(kwargs=kwargs):
                self.assertFalse(eligible_initial_freight(**kwargs))

    def test_axis_x_opposite_side_both_distances_and_lead_checked(self):
        platform = Platform(15, 20, 'x', 4, True)
        occupied = {(17, 19)}
        result = parallel_room(platform, (9, 30), lambda x, y: (x, y) not in occupied)
        self.assertEqual([(distance, flip) for distance, flip, _, _ in result], [(2, -1)])
        self.assertEqual(result[0][2], [(15, 18), (16, 18), (17, 18), (18, 18)])
        self.assertEqual(result[0][3], (19, 18))
        self.assertEqual(parallel_room(platform, (10, 20), lambda x, y: True), [])

    def test_axis_y_opposite_side_and_exit_clearance(self):
        platform = Platform(25, 30, 'y', 3, False)
        room = parallel_room(platform, (9, 30), lambda x, y: x >= 0 and y >= 0)
        self.assertEqual([(distance, flip) for distance, flip, _, _ in room], [(1, 1), (2, 1)])
        self.assertEqual(room[0][2], [(26, 30), (26, 31), (26, 32)])
        self.assertEqual(room[0][3], (26, 29))
        # Une bande de quai plate sans TUile de sortie ne suffit pas.
        no_lead = {(26, 29), (27, 29)}
        self.assertEqual(parallel_room(platform, (9, 30),
                                       lambda x, y: (x, y) not in no_lead), [])

    def test_filter_fallback_and_two_platforms_require_adjacent_band(self):
        p = Platform(20, 40, 'x', 3, True)
        blocked = {(20, 39), (21, 39), (22, 39), (23, 39)}
        clear = lambda x, y: (x, y) not in blocked
        self.assertEqual(room_filter([p], (10, 50), clear, 1), [p])  # dist=2
        self.assertEqual(room_filter([p], (10, 50), clear, 2), [p])  # repli historique 1 quai
        self.assertEqual(room_filter([p], (10, 50), lambda x, y: False, 1), [p])
        self.assertEqual(room_filter([p], (10, 50), lambda x, y: False, 2), [p])

        p_blocked = Platform(20, 50, 'x', 3, True)
        clear_selective = lambda x, y: y not in (48, 49)
        self.assertEqual(room_filter([p_blocked, p], (10, 60), clear_selective, 1), [p])

    def test_two_platform_station_rectangle_keeps_original_platform_end(self):
        x_axis = Platform(15, 20, 'x', 4, True)
        y_axis = Platform(25, 30, 'y', 3, False)
        self.assertEqual(station_anchor_for_two(x_axis, -1), (15, 19))
        self.assertEqual(station_anchor_for_two(x_axis, 1), (15, 20))
        self.assertEqual(station_anchor_for_two(y_axis, -1), (24, 30))
        self.assertEqual(station_anchor_for_two(y_axis, 1), (25, 30))


class TestSquirrelIntegrationContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = read_ai('info.nut')
        cls.settings = read_ai('settings.nut')
        cls.globals = read_ai('globals_pre.nut')
        cls.rail = read_ai('builder_rail.nut')

    def test_setting_bitmask_default_zero_and_single_read(self):
        setting = re.search(r'name\s*=\s*"v307_sink_room"\s*,(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(setting, 'Ajouter v307_sink_room dans AddSetting')
        body = setting.group(1)
        for level in ('easy', 'medium', 'hard', 'custom'):
            with self.subTest(level=level):
                self.assertRegex(body, rf'\b{level}_value\s*=\s*0\b')
        self.assertRegex(body, r'\bmin_value\s*=\s*0\b')
        self.assertRegex(body, r'\bmax_value\s*=\s*3\b')
        self.assertEqual(self.settings.count('AIController.GetSetting("v307_sink_room")'), 1)
        self.assertRegex(self.globals, r'(?m)^V307_SINK_ROOM\s*<-\s*0\s*;')

    def test_only_first_new_freight_destination_and_cargo_producer_count(self):
        eligible = squirrel_function(self.rail, 'OpexV307SinkRoomEligible')
        self.assertTrue(eligible, 'Garde explicite du bitmask et du premier fret attendue')
        self.assertTrue('V307_SINK_ROOM' in eligible, 'Garde du bitmask absente')
        self.assertTrue(re.search(r'candidate\.kind\s*(?:==|!=)\s*"freight"', eligible), 'Fret seul')
        self.assertTrue('catalog.producers' in eligible, 'Sources dans le catalogue')
        self.assertTrue('candidate.cargo' in eligible, 'Filtre par cargo')
        self.assertTrue(re.search(r'\.len\(\)\s*(?:<|>=)\s*2', eligible), 'Deux sources au moins')
        self.assertTrue(re.search(r'shared_dest|joinPlatform|joinEnd', eligible), 'Pas de jointure existante')
        self.assertIn('AIIndustry.GetIndustryID(candidate.dst)', eligible,
                      'Seulement la premiere gare de destination INDUSTRIELLE')
        # V178 garde son choix de quai historique ; sa SEULE extension est
        # de reutiliser le quai deja construit par le bit 2.
        join = squirrel_function(self.rail, 'OpexJoinPlatformPlans')
        self.assertNotIn('OpexV307SinkRoomFilterPlans', join)
        self.assertIn('V307_SINK_ROOM & 2', join)

    def test_only_free_destination_plans_filtered_with_historical_fallback(self):
        site = squirrel_function(self.rail, 'OpexRailTryPlatformLength')
        self.assertTrue('OpexV307SinkRoom' in site, 'Filtre V307R absent du choix B')
        self.assertTrue('plansB' in site, 'B non gere')
        self.assertTrue('V307_SINK_ROOM' in site, 'Le defaut zero doit etre garde')
        filtered = squirrel_function(self.rail, 'OpexV307SinkRoomFilterPlans')
        self.assertTrue(filtered, 'Choix des plans B et repli intact si aucun site eligible')
        self.assertTrue('plans.len()' in filtered, 'Liste initiale indispensable')
        self.assertTrue(re.search(r'\.len\(\)\s*==\s*0', filtered), 'Verifier aucun plan retenu')
        self.assertTrue(re.search(r'(?s)if\s*\([^)]*\.len\(\)\s*==\s*0\)\s*return\s+plans',
                                  filtered), 'Fallback exact sur plans B historiques')

    def test_reserved_geometry_uses_one_or_two_perpendicular_tiles_and_lead(self):
        room = squirrel_function(self.rail, 'OpexV307SinkRoomParallel')
        self.assertTrue(room, 'Geometrie d emprise avant premier chantier requise')
        self.assertTrue(re.search(r'\b(?:dist|offset)\s*<=\s*2\b', room), 'Limite a deux tuiles')
        for invariant in ('AIMap.IsValidTile', 'AITile.IsBuildable', 'AITile.GetSlope',
                          'AITile.SLOPE_FLAT', 'AITestMode', 'AIRail.BuildRailStation',
                          'station_exit', 'lead'):
            with self.subTest(invariant=invariant):
                self.assertTrue(invariant in room, f'{invariant} manque de la verification du quai')
        self.assertTrue(re.search(r'flip|side', room), 'Orientation du quai reserve absente')

    def test_reserved_strip_survives_path_search_on_both_rail_runners(self):
        # Le site est examine AVANT l'A*. Sans tuiles interdites, la recherche
        # peut tracer la premiere ligne sur l'emprise de la seconde ligne.
        # Les appels bloquant et reprenable convergent dans ces constructeurs
        # du builder ; task_rail.nut est hors du perimetre d'edition V307R.
        for fn in ('OpexCreateRailPathfinder', 'OpexCreateSegmentedSearch'):
            with self.subTest(function=fn):
                section = squirrel_function(self.rail, fn)
                self.assertTrue(section)
                self.assertTrue('OpexV307SinkRoomIgnoredTiles' in section,
                                'Emprise B reservee a injecter parmi les ignoredTiles de A*')
        complete = squirrel_function(self.rail, 'OpexCompleteRailRouteAfterSearch')
        self.assertIn('OpexV307SinkRoomPathClear', complete,
                      'La voie choisie ne doit pas finalement traverser son quai reserve')

    def test_built_spare_platform_must_be_reusable_on_later_v178_join(self):
        # Critique pour bit 2 : IsBuildable est FAUX pour une tuile deja gare.
        # OpexJoinPlatformPlans doit accepter le quai libre prebati pour la
        # 2e ligne ; sinon BuildRailStation(..., 2) ne debloque aucune jointure.
        # Ce test exige une decision de perimetre, car le prompt limite les
        # modifications de comportement au choix B de la premiere ligne.
        join = squirrel_function(self.rail, 'OpexJoinPlatformPlans')
        self.assertTrue('OpexV307SinkRoom' in join or 'v307RoomPlatforms' in join,
                        'Reuse du 2e quai deja construit manquant')
        reused = squirrel_function(self.rail, 'OpexV307SinkRoomPrebuiltPlan')
        self.assertIn('OpexV307SinkRoomPrebuiltPlan', join)
        self.assertIn('AIRail.IsRailStationTile', reused,
                      'Reconnaitre le quai deja pose appartenant a la gare')
        self.assertIn('AIStation.GetStationID(tile)', reused)
        self.assertIn('AITile.IsBuildable(lead)', reused,
                      'Un quai prebati ne peut accueillir 2 lignes si sa sortie est occupee')

    def test_second_platform_quoted_and_built_in_both_executor_paths(self):
        for fn in ('OpexSimulateRailInfraCost', 'OpexExecuteRailPlan',
                   'OpexV190ExecuteRailPlan'):
            with self.subTest(function=fn):
                section = squirrel_function(self.rail, fn)
                self.assertTrue(section)
                self.assertIn('AIRail.BuildRailStation', section)
                self.assertTrue(re.search(r'OpexV307SinkRoom.*(?:Platforms|Width)|v307RoomPlatforms',
                                          section),
                                'Largeur de B doit suivre le meme plan cote simulateur/constructeurs')
        # Un second quai ne doit pas survivre au rollback et la gare historique
        # deja jointe ne doit jamais subir de suppression supplementaire.
        rollback = squirrel_function(self.rail, 'OpexRollback')
        self.assertTrue(re.search(r'v307RoomPlatforms|OpexV307SinkRoom', rollback),
                        'Rollback des deux quais de B obligatoire')
        self.assertIn('AIRail.RemoveRailStationTileRectangle', rollback)
        self.assertIn('v307Prebuilt', rollback,
                      'Une tentative V178 echouee ne doit jamais detruire une gare B reutilisee')
        self.assertIn('OpexV307SinkRoomDemolishExtra', self.rail)
        self.assertIn('OpexV307SinkRoomStationAnchor', self.rail)

    def test_second_platform_marginal_maintenance_repriced_once(self):
        estimate = squirrel_function(self.rail, 'OpexV307SinkRoomAnnualMaintenance')
        self.assertIn('AIInfrastructure.INFRASTRUCTURE_STATION', estimate)
        self.assertIn('AIInfrastructure.GetInfrastructurePieceCount', estimate)
        self.assertIn('AIInfrastructure.GetMonthlyInfrastructureCosts', estimate)
        self.assertIn('economy.infrastructure_maintenance', estimate)
        self.assertIn('n + 2 * plan.length', estimate)
        self.assertIn('n + 3 * plan.length', estimate)
        self.assertIn('V307R_MAINT', estimate)
        apply = squirrel_function(self.rail, 'OpexV307SinkRoomApplyMaintenance')
        self.assertIn('candidate.runningAnnual - old + annual', apply)
        self.assertIn('candidate.profitAnnual', apply)
        for fn in ('OpexExecuteRailPlan', 'OpexV190ExecuteRailPlan'):
            self.assertIn('OpexV307SinkRoomApplyMaintenance(candidate, planB)',
                          squirrel_function(self.rail, fn))

    def test_decision_log_site_before_after_side_bits_and_opcodes(self):
        self.assertTrue('V307R_SITE' in self.rail, 'Log V307R_SITE absent')
        log = self.rail[self.rail.index('OpexDecide("V307R_SITE"'):]
        log = log.split(');', 1)[0]
        for field in ('before=', 'after=', 'side=', 'bit=', 'ops='):
            with self.subTest(field=field):
                self.assertIn(field, log)
        self.assertTrue(re.search(r'(?s)if\s*\(DECISION_LOG\).*?OpexDecide\("V307R_SITE"', self.rail),
                        'Le log doit etre derriere DECISION_LOG')


if __name__ == '__main__':
    unittest.main()
