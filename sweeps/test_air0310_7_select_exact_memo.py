#!/usr/bin/env python3
"""Contrat V124 : memo exact de la selection, defaut 0.

air0310_select_exact_memo vaut 0 aux quatre difficultes et n'est pas barre
par C121_CATALOG_INCREMENTAL. A 1, une passe reutilise la ville la plus
proche, la validite et la population, le tier C77 et le score de classement
lorsque leurs entrees n'ont pas change. slotRemaining n'est pas memoize.
A 0, le corps historique suit le garde. Aucune partie n'est lancee.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from sweeps.campaign_freeze import parse_ai_setting_specs

ROOT = Path(__file__).resolve().parents[1]

SETTING = "air0310_select_exact_memo"
GLOBAL = "AIR0310_SELECT_EXACT_MEMO"
MEMO = "AIR0310_SELECT_MEMO"


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _setting_block(info, name):
    start = info.index(f'name = "{name}"')
    return info[start:info.index("});", start)]


def _brace_body(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    i = brace
    n = len(source)
    while i < n:
        ch = source[i]
        if ch == '"':
            i += 1
            while i < n and source[i] != '"':
                if source[i] == "\\":
                    i += 1
                i += 1
        elif ch == "'":
            i += 1
            while i < n and source[i] != "'":
                if source[i] == "\\":
                    i += 1
                i += 1
        elif source.startswith("//", i):
            nl = source.find("\n", i)
            i = n if nl < 0 else nl
        elif source.startswith("/*", i):
            end = source.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
        i += 1
    raise AssertionError(f"unterminated function: {signature}")


def _brace_balance(text):
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\\":
                    i += 1
                i += 1
        elif ch == "'":
            i += 1
            while i < n and text[i] != "'":
                if text[i] == "\\":
                    i += 1
                i += 1
        elif text.startswith("//", i):
            nl = text.find("\n", i)
            i = n if nl < 0 else nl
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return depth
        i += 1
    return depth


def c77_tier(project, preempt_open):
    """Miroir de OpexProjectDefensiveAirPriority. slotRemaining n'est pas lu."""
    if project is None:
        return 0
    if "mode" not in project or project["mode"] != "air":
        return 0
    if "profitAnnual" not in project or project["profitAnnual"] <= 0:
        return 0
    if project.get("defensiveCompetitorClaims", 0) > 0:
        return 2
    if preempt_open and project.get("preemptClaims", 0) > 0:
        return 2
    if project.get("defensiveOwnClaims", 0) > 0:
        return 1
    return 0


def selection_score(project, field, air_early):
    if project is None:
        return 0.0
    score = project[field]
    if not air_early or project.get("mode") != "air":
        return score
    if "earlySlotBonusPct" not in project:
        return score
    bonus = project["earlySlotBonusPct"]
    if bonus <= 0:
        return score
    return score * (100.0 + float(bonus)) / 100.0


def displayed_score(project, field, apply_early, air_early):
    if apply_early:
        return selection_score(project, field, air_early)
    return project[field]


class RankMemo:
    def __init__(self):
        self.rank = {}
        self.tier_misses = 0
        self.score_misses = 0

    def tier(self, project, preempt_open):
        if project is None:
            return c77_tier(project, preempt_open)
        key = id(project)
        mode = project["mode"] if "mode" in project else None
        profit = project["profitAnnual"] if "profitAnnual" in project else 0
        comp = project["defensiveCompetitorClaims"] if "defensiveCompetitorClaims" in project else 0
        own = project["defensiveOwnClaims"] if "defensiveOwnClaims" in project else 0
        preempt = project["preemptClaims"] if "preemptClaims" in project else 0
        slot = self.rank.get(key)
        if (
            slot is not None
            and slot["tierStored"]
            and slot["mode"] == mode
            and slot["profit"] == profit
            and slot["comp"] == comp
            and slot["own"] == own
            and slot["preempt"] == preempt
        ):
            return slot["tier"]
        self.tier_misses += 1
        tier = c77_tier(project, preempt_open)
        if slot is None:
            slot = {"tierStored": False, "packEarly": None, "packRaw": None}
            self.rank[key] = slot
        slot["mode"] = mode
        slot["profit"] = profit
        slot["comp"] = comp
        slot["own"] = own
        slot["preempt"] = preempt
        slot["tier"] = tier
        slot["tierStored"] = True
        return tier

    def score(self, project, field, apply_early, air_early):
        if project is None:
            return displayed_score(project, field, apply_early, air_early)
        key = id(project)
        slot = self.rank.get(key)
        if slot is None:
            slot = {"tierStored": False, "packEarly": None, "packRaw": None}
            self.rank[key] = slot
        pack = slot["packEarly"] if apply_early else slot["packRaw"]
        raw = project[field]
        mode = project["mode"] if "mode" in project else None
        has_bonus = "earlySlotBonusPct" in project
        bonus = project["earlySlotBonusPct"] if has_bonus else 0
        if (
            pack is not None
            and pack["field"] == field
            and pack["raw"] == raw
            and pack["mode"] == mode
            and pack["hasBonus"] == has_bonus
            and pack["bonus"] == bonus
        ):
            return pack["score"]
        self.score_misses += 1
        score = displayed_score(project, field, apply_early, air_early)
        stored = {
            "field": field,
            "raw": raw,
            "mode": mode,
            "hasBonus": has_bonus,
            "bonus": bonus,
            "score": score,
        }
        if apply_early:
            slot["packEarly"] = stored
        else:
            slot["packRaw"] = stored
        return score


def _full_tier(base, project, chain_force):
    if chain_force and project is not None and project.get("isChain"):
        return base + 1000
    return base


def insert_order(projects, field, limit, apply_early, air_early, preempt_open, chain_force, memo):
    """Meme boucle que OpexProjectInsertDefensive, C118 et C122 eteints."""
    best = []
    for project in projects:
        if memo is None:
            base = c77_tier(project, preempt_open)
            project_score = displayed_score(project, field, apply_early, air_early)
        else:
            base = memo.tier(project, preempt_open)
            project_score = memo.score(project, field, apply_early, air_early)
        project_tier = _full_tier(base, project, chain_force)
        pos = len(best)
        while pos > 0:
            prior = best[pos - 1]
            if memo is None:
                prior_base = c77_tier(prior, preempt_open)
                prior_score = displayed_score(prior, field, apply_early, air_early)
            else:
                prior_base = memo.tier(prior, preempt_open)
                prior_score = memo.score(prior, field, apply_early, air_early)
            prior_tier = _full_tier(prior_base, prior, chain_force)
            if prior_tier > project_tier:
                break
            if prior_tier < project_tier:
                pos -= 1
                continue
            if prior_score > project_score:
                break
            if prior_score == project_score and prior["revenueAnnual"] >= project["revenueAnnual"]:
                break
            pos -= 1
        best.insert(pos, project)
        if len(best) > limit:
            best.pop()
    return [project["id"] for project in best]


def finance_capital(project, calibration=True, rail_bias=170):
    if project is None or "budgetCapital" not in project:
        return 0
    finance = project["budgetCapital"]
    if not calibration or "mode" not in project:
        return finance
    mode = project["mode"]
    if mode == "rail":
        bias = rail_bias
    elif mode == "road":
        bias = 121
    else:
        return finance
    capital = project.get("capital", 0)
    model_capital = capital
    if capital <= 0:
        return finance
    capital_is_actual = bool(project.get("capitalIsActual"))
    payload = project.get("payload")
    if not capital_is_actual and payload is not None and payload.get("capitalIsActual"):
        capital_is_actual = True
        if payload.get("capital", 0) > 0:
            capital = payload["capital"]
    non_construction = finance - model_capital
    if non_construction < 0:
        non_construction = 0
    if capital_is_actual:
        return capital + non_construction
    return ((capital * bias) // 100) + non_construction


class FinanceMemo:
    def __init__(self):
        self.finance = {}
        self.full_calls = 0

    def value(self, project, calibration=True, rail_bias=170):
        if (
            project is not None
            and "budgetCapital" in project
            and "mode" in project
            and project["mode"] not in ("rail", "road")
        ):
            return project["budgetCapital"]
        if project is None:
            self.full_calls += 1
            return finance_capital(project, calibration, rail_bias)
        budget = project["budgetCapital"] if "budgetCapital" in project else None
        mode = project["mode"] if "mode" in project else None
        capital = project["capital"] if "capital" in project else None
        actual = bool(project.get("capitalIsActual"))
        payload = project.get("payload")
        payload_capital = payload.get("capital") if payload is not None and "capital" in payload else None
        payload_actual = bool(payload.get("capitalIsActual")) if payload is not None else False
        slot = self.finance.get(id(project))
        if (
            slot is not None
            and slot["budget"] == budget
            and slot["mode"] == mode
            and slot["capital"] == capital
            and slot["actual"] == actual
            and slot["payload"] is payload
            and slot["payloadCapital"] == payload_capital
            and slot["payloadActual"] == payload_actual
            and slot["calibration"] == calibration
            and slot["railBias"] == rail_bias
        ):
            return slot["value"]
        self.full_calls += 1
        value = finance_capital(project, calibration, rail_bias)
        self.finance[id(project)] = {
            "budget": budget,
            "mode": mode,
            "capital": capital,
            "actual": actual,
            "payload": payload,
            "payloadCapital": payload_capital,
            "payloadActual": payload_actual,
            "calibration": calibration,
            "railBias": rail_bias,
            "value": value,
        }
        return value


class TownWorld:
    def __init__(self):
        self.tick = 1
        self.date = 100
        self.closest = {}
        self.valid = set()
        self.pop = {}
        self.closest_calls = 0
        self.valid_calls = 0
        self.pop_calls = 0
        self.date_reads = 0

    def get_closest(self, anchor):
        self.closest_calls += 1
        return self.closest[anchor]

    def is_valid(self, town_id):
        self.valid_calls += 1
        return town_id in self.valid

    def get_pop(self, town_id):
        self.pop_calls += 1
        return self.pop[town_id]


class TownMemo:
    def __init__(self):
        self.tick = -1
        self.date = -1
        self.by_anchor = {}
        self.valid = {}
        self.pop = {}
        self.rank = {"kept": True}

    def _sync(self, world):
        if world.tick == self.tick:
            return
        world.date_reads += 1
        if world.date != self.date:
            self.by_anchor = {}
            self.valid = {}
            self.pop = {}
            self.date = world.date
        self.tick = world.tick

    def closest(self, world, anchor):
        if anchor is None:
            return world.get_closest(anchor)
        self._sync(world)
        if anchor in self.by_anchor:
            return self.by_anchor[anchor]
        town_id = world.get_closest(anchor)
        self.by_anchor[anchor] = town_id
        return town_id

    def town_valid(self, world, town_id):
        self._sync(world)
        if town_id in self.valid:
            return self.valid[town_id]
        ok = world.is_valid(town_id)
        self.valid[town_id] = ok
        return ok

    def town_pop(self, world, town_id):
        self._sync(world)
        if town_id in self.pop:
            return self.pop[town_id]
        pop = world.get_pop(town_id)
        self.pop[town_id] = pop
        return pop


def fit_fleet(project):
    if project is None or project["mode"] != "fleet":
        return project
    return {"id": "fitted", "mode": "fleet", "source": id(project)}


def fit_memo(project, enabled):
    if enabled and project is not None and "mode" in project and project["mode"] != "fleet":
        return project
    return fit_fleet(project)


class TestAir0310SelectExactMemo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("ai/OpexAI/info.nut")
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.persist = _read("ai/OpexAI/persist.nut")
        cls.selection = _read("ai/OpexAI/projects_selection.nut")
        cls.towns = _read("ai/OpexAI/air_towns.nut")
        cls.select = _brace_body(
            cls.selection, "function OpexProjectSelectAffordable(alternatives, capitalBudget, limit)"
        )
        cls.early = _brace_body(cls.selection, "function OpexProjectRefreshEarlySlot(project, state)")
        cls.defensive = _brace_body(
            cls.selection, "function OpexProjectRefreshDefensiveSlot(project, state)"
        )
        cls.insert = _brace_body(
            cls.selection,
            "function OpexProjectInsertDefensive(best, project, field, limit, applyEarlySlot = false)",
        )
        cls.memo_insert = _brace_body(
            cls.selection,
            "function OpexAir0310InsertDefensive(best, project, field, limit, applyEarlySlot = false)",
        )
        cls.tier = _brace_body(cls.selection, "function OpexAir0310CachedTier(project)")
        cls.score = _brace_body(
            cls.selection, "function OpexAir0310CachedScore(project, field, applyEarlySlot)"
        )
        cls.towns_sync = _brace_body(cls.selection, "function OpexAir0310MemoTowns()")
        cls.slot = _brace_body(cls.towns, "function OpexAirSlotTownId(anchor)")

    def test_setting_defaults_to_zero_and_is_not_persisted(self):
        self.assertEqual(self.info.count(f'name = "{SETTING}"'), 1)
        block = _setting_block(self.info, SETTING)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 1", block)
        self.assertIn("step_size = 1", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{key} = 0", block)
            self.assertNotIn(f"{key} = 1", block)
        spec = parse_ai_setting_specs(ROOT / "ai/OpexAI/info.nut")[SETTING]
        self.assertTrue(spec["boolean"])
        self.assertEqual(spec["default"], 0)
        self.assertEqual(self.globals.count(f"{GLOBAL} <- false;"), 1)
        self.assertEqual(self.globals.count(f"{GLOBAL} <-"), 1)
        self.assertEqual(self.globals.count(f"{MEMO} <- null;"), 1)
        self.assertEqual(self.settings.count(f'AIController.GetSetting("{SETTING}")'), 1)
        load = next(
            line for line in self.settings.splitlines() if f'GetSetting("{SETTING}")' in line
        )
        self.assertNotIn("C121_CATALOG_INCREMENTAL", load)
        self.assertNotIn(SETTING, self.persist)
        self.assertNotIn(GLOBAL, self.persist)
        self.assertNotIn(MEMO, self.persist)

    def test_zero_path_keeps_the_historical_body_behind_one_guard(self):
        for body, call in (
            (self.early, "return OpexAir0310RefreshEarlySlot(project, state);"),
            (self.defensive, "return OpexAir0310RefreshDefensiveSlot(project, state);"),
            (
                self.insert,
                "return OpexAir0310InsertDefensive(best, project, field, limit, applyEarlySlot);",
            ),
        ):
            guard = f"if ({MEMO} != null) {call}"
            self.assertEqual(body.count(guard), 1)
            after_brace = body[body.index("{") + 1:].lstrip()
            self.assertTrue(after_brace.startswith(guard), body[:80])
        self.assertIn("AITile.GetClosestTown(plan.siteA.anchor)", self.early)
        self.assertIn("AITile.GetClosestTown(plan.siteB.anchor)", self.early)
        self.assertIn("AITown.IsValidTown(townA)", self.early)
        self.assertIn("AITown.GetPopulation(townA)", self.early)
        self.assertIn("AITile.GetClosestTown(plan.siteA.anchor)", self.defensive)
        self.assertIn("AITile.GetClosestTown(plan.siteB.anchor)", self.defensive)
        self.assertIn("AITown.IsValidTown(townA)", self.defensive)
        self.assertIn("AITown.GetPopulation(townA)", self.defensive)
        self.assertIn("AITile.GetClosestTown(anchor)", self.slot)
        self.assertNotIn("GetNearestTown", self.slot)
        self.assertIn(f"if ({MEMO} != null) return OpexAir0310SlotTownId(anchor);", self.slot)
        self.assertLess(self.slot.index(f"if ({MEMO} != null)"), self.slot.index("AITile.GetClosestTown(anchor)"))
        self.assertIn(
            "local projectC77Tier = OpexProjectDefensiveAirPriority(project);", self.insert
        )
        self.assertIn(
            "local priorScore = applyEarlySlot ? OpexProjectSelectionScore(prior, field) : prior[field];",
            self.insert,
        )
        self.assertNotIn("OpexAir0310CachedTier", self.insert)
        self.assertNotIn("OpexAir0310CachedScore", self.insert)
        self.assertLess(
            self.insert.index("OpexProjectDefensiveAirPriority(prior)"),
            self.insert.index("OpexProjectSelectionScore(prior, field)"),
        )
        self.assertLess(
            self.insert.index("if (priorTier > projectTier) break;"),
            self.insert.index("local priorScore ="),
        )

    def test_rank_memo_does_not_read_slot_noise_or_write_the_project(self):
        for body in (self.tier, self.score, self.memo_insert):
            self.assertNotIn("slotRemaining", body)
            self.assertNotIn("GetAllowedNoise", body)
            self.assertNotIn("project.rawset", body)
            self.assertNotIn("project.tier", body)
        self.assertNotIn("OpexSpan", self.memo_insert)
        self.assertIn("OpexProjectIsForcedChain", self.memo_insert)
        self.assertIn("OpexC122AirRegimeTier(project)", self.memo_insert)
        self.assertIn("c118NewTowns", self.memo_insert)
        self.assertIn("if (tick == memo.tick) return;", self.towns_sync)
        self.assertLess(
            self.towns_sync.index("if (tick == memo.tick) return;"),
            self.towns_sync.index("AIDate.GetCurrentDate()"),
        )
        flushed = self.towns_sync[self.towns_sync.index("if (date != memo.date)"):]
        self.assertIn("memo.townByAnchor = {}", flushed)
        self.assertIn("memo.townValid = {}", flushed)
        self.assertIn("memo.townPop = {}", flushed)
        self.assertNotIn("memo.rank", flushed)
        self.assertNotIn("memo.finance", flushed)

    def test_memo_is_pass_local_and_cleared_on_the_way_out(self):
        self.assertIn(
            f"{MEMO} = {GLOBAL} ? OpexAir0310SelectMemoNew() : null;",
            self.select,
        )
        self.assertLess(
            self.select.index(f"{MEMO} = {GLOBAL} ? OpexAir0310SelectMemoNew() : null;"),
            self.select.index("OpexProjectFitFleetToBudget(project, capitalBudget)"),
        )
        self.assertIn(f"{MEMO} = null;", self.select)
        self.assertLess(
            self.select.index("if (spEpilogue != null) OpexSpanEnd(spEpilogue);"),
            self.select.index(f"{MEMO} = null;"),
        )
        self.assertIn("} catch (err) {", self.select)
        catch = self.select[self.select.index("} catch (err) {"):]
        self.assertIn(f"{MEMO} = null;", catch)
        self.assertIn("throw err;", catch)
        self.assertNotIn("OpexSpanEnd", catch)

    def test_spans_are_probe_gated_inside_select_full(self):
        names = (
            "pub.select.score.fit",
            "pub.select.score.states",
            "pub.select.score.refresh_slots",
            "pub.select.score.fund_score",
            "pub.select.score.insert",
            "pub.select.score.epilogue",
        )
        for name in names:
            self.assertIn(name, self.select)
        # L'ouverture est gardee. La fermeture peut etre loin : c'est le travail mesure.
        begin_at = 0
        while True:
            begin_at = self.select.find("OpexOpsMeasureBegin()", begin_at)
            if begin_at < 0:
                break
            window = self.select[max(0, begin_at - 40):begin_at]
            self.assertIn("PROBE_SPAN_TRACE", window)
            begin_at += 1
        for name in ("pub.select.score.states", "pub.select.score.epilogue"):
            at = self.select.index(f'OpexSpanBegin("{name}")')
            self.assertIn("PROBE_SPAN_TRACE", self.select[max(0, at - 40):at])
        for name in (
            "pub.select.score.fit",
            "pub.select.score.refresh_slots",
            "pub.select.score.fund_score",
            "pub.select.score.insert",
        ):
            at = 0
            seen = 0
            token = f'OpexSpanAgg("{name}"'
            while True:
                at = self.select.find(token, at)
                if at < 0:
                    break
                window = self.select[max(0, at - 80):at]
                self.assertIn("!= null", window, name)
                seen += 1
                at += len(token)
            self.assertGreater(seen, 0, name)
        self.assertLess(
            self.select.index('OpexSpanBegin("select.full")'),
            self.select.index("pub.select.score.fit"),
        )
        self.assertLess(
            self.select.index("pub.select.score.fit"),
            self.select.index('OpexSpanBegin("pub.select.score.states")'),
        )
        self.assertLess(
            self.select.index("if (spStates != null) OpexSpanEnd(spStates);"),
            self.select.index("pub.select.score.refresh_slots"),
        )
        self.assertLess(
            self.select.index("pub.select.score.refresh_slots"),
            self.select.index('OpexSpanBegin("pub.select.score.epilogue")'),
        )
        self.assertLess(
            self.select.index("if (spEpilogue != null) OpexSpanEnd(spEpilogue);"),
            self.select.index('OpexSpanEnd(spSelect)'),
        )
        self.assertIn(
            'OpexSpanAgg("pub.select.score.fit", fitMark)', self.select
        )
        self.assertIn(
            'OpexSpanAgg("pub.select.score.fund_score", fundMark)', self.select
        )
        self.assertIn(
            'OpexSpanAgg("pub.select.score.insert", insertMark)', self.select
        )
        self.assertIn(
            "if (PROBE_AIR0310_N1_FALLBACK && financeCapital > capitalBudget)\n"
            '      OpexAir0310N1FallbackProbe(project, capitalBudget, "select", "lost");\n'
            "    if (financeCapital > capitalBudget) continue;",
            self.select,
        )
        self.assertEqual(self.select.count("if (financeCapital > capitalBudget) continue;"), 3)
        self.assertEqual(_brace_balance(self.selection), 0)

    def test_python_mirror_keeps_the_same_order_with_and_without_memo(self):
        projects = [
            {"id": "plain", "mode": "air", "profitAnnual": 100, "revenueAnnual": 80,
             "fundScore": 10, "c69Score": 4, "earlySlotBonusPct": 0,
             "defensiveCompetitorClaims": 0, "defensiveOwnClaims": 0, "preemptClaims": 0,
             "slotRemaining": 2},
            {"id": "bonus", "mode": "air", "profitAnnual": 100, "revenueAnnual": 50,
             "fundScore": 10, "c69Score": 1, "earlySlotBonusPct": 50,
             "defensiveCompetitorClaims": 0, "defensiveOwnClaims": 0, "preemptClaims": 0,
             "slotRemaining": 1},
            {"id": "tie-low", "mode": "air", "profitAnnual": 80, "revenueAnnual": 20,
             "fundScore": 12, "c69Score": 9, "earlySlotBonusPct": 0,
             "defensiveCompetitorClaims": 0, "defensiveOwnClaims": 0, "preemptClaims": 0,
             "slotRemaining": 0},
            {"id": "tie-high", "mode": "air", "profitAnnual": 80, "revenueAnnual": 90,
             "fundScore": 12, "c69Score": 9, "earlySlotBonusPct": 0,
             "defensiveCompetitorClaims": 0, "defensiveOwnClaims": 0, "preemptClaims": 0,
             "slotRemaining": 9},
            {"id": "race", "mode": "air", "profitAnnual": 40, "revenueAnnual": 10,
             "fundScore": 1, "c69Score": 1, "earlySlotBonusPct": 0,
             "defensiveCompetitorClaims": 1, "defensiveOwnClaims": 0, "preemptClaims": 0,
             "slotRemaining": 1},
            {"id": "own", "mode": "air", "profitAnnual": 40, "revenueAnnual": 30,
             "fundScore": 50, "c69Score": 50, "earlySlotBonusPct": 0,
             "defensiveCompetitorClaims": 0, "defensiveOwnClaims": 1, "preemptClaims": 0,
             "slotRemaining": 1},
            {"id": "chain", "mode": "road", "profitAnnual": 5, "revenueAnnual": 5,
             "fundScore": 1, "c69Score": 1, "isChain": True, "slotRemaining": 0},
            {"id": "zero", "mode": "air", "profitAnnual": 70, "revenueAnnual": 70,
             "fundScore": 0, "c69Score": 0, "earlySlotBonusPct": 0,
             "defensiveCompetitorClaims": 0, "defensiveOwnClaims": 0, "preemptClaims": 0,
             "slotRemaining": 2},
        ]
        cases = (
            ("fundScore", True, True, True, True, 8),
            ("fundScore", False, True, True, False, 8),
            ("c69Score", True, False, False, False, 3),
            ("fundScore", True, True, False, True, 4),
        )
        for field, apply_early, air_early, preempt, chain, limit in cases:
            naive = insert_order(
                projects, field, limit, apply_early, air_early, preempt, chain, None
            )
            memo = RankMemo()
            cached = insert_order(
                projects, field, limit, apply_early, air_early, preempt, chain, memo
            )
            self.assertEqual(cached, naive, (field, apply_early, limit))
            self.assertGreater(memo.tier_misses, 0)
            # Reuse one memo across the whole insertion: hits must not change order.
            misses = memo.tier_misses
            again = insert_order(
                projects, field, limit, apply_early, air_early, preempt, chain, memo
            )
            self.assertEqual(again, naive)
            self.assertEqual(memo.tier_misses, misses)

        fund = insert_order(projects, "fundScore", 8, True, True, True, False, None)
        c69 = insert_order(projects, "c69Score", 8, True, True, True, False, None)
        self.assertNotEqual(fund, c69)
        memo = RankMemo()
        both = [
            insert_order(projects, field, 8, True, True, True, False, memo)
            for field in ("c69Score", "fundScore")
        ]
        self.assertEqual(both, [c69, fund])
        misses_after_two_fields = memo.score_misses
        insert_order(projects, "fundScore", 8, True, True, True, False, memo)
        self.assertEqual(memo.score_misses, misses_after_two_fields)

        score_before = memo.score_misses
        plain = projects[0]
        plain["fundScore"] = 1000
        naive = insert_order(projects, "fundScore", 8, True, True, True, False, None)
        cached = insert_order(projects, "fundScore", 8, True, True, True, False, memo)
        self.assertEqual(cached, naive)
        self.assertNotEqual(cached, fund)
        self.assertGreater(memo.score_misses, score_before)
        # Le tier C77 prime sur le score : un claim concurrent reste devant.
        self.assertEqual(cached[0], "race")
        self.assertLess(cached.index("plain"), cached.index("tie-high"))
        plain["fundScore"] = 10

        before = memo.tier_misses
        plain["slotRemaining"] = 0
        naive = insert_order(projects, "fundScore", 8, True, True, True, False, None)
        cached = insert_order(projects, "fundScore", 8, True, True, True, False, memo)
        self.assertEqual(cached, naive)
        self.assertEqual(memo.tier_misses, before)

        plain["defensiveCompetitorClaims"] = 1
        naive = insert_order(projects, "fundScore", 8, True, True, True, False, None)
        cached = insert_order(projects, "fundScore", 8, True, True, True, False, memo)
        self.assertEqual(cached, naive)
        self.assertGreater(memo.tier_misses, before)
        plain["defensiveCompetitorClaims"] = 0

        chain = projects[6]
        self.assertFalse(chain.get("isChain") is False)
        chain["isChain"] = False
        cold = RankMemo()
        insert_order([chain], "fundScore", 4, False, False, False, True, cold)
        chain["isChain"] = True
        naive = insert_order(projects, "fundScore", 8, False, False, False, True, None)
        cached = insert_order(projects, "fundScore", 8, False, False, False, True, cold)
        self.assertEqual(cached, naive)
        self.assertEqual(cached[0], "chain")

    def test_town_cache_is_pass_local_and_rank_survives_a_date_flush(self):
        world = TownWorld()
        world.closest = {10: 3, 11: 4, None: -1}
        world.valid = {3, 4}
        world.pop = {3: 800, 4: 100}
        memo = TownMemo()
        rank = memo.rank
        self.assertEqual(memo.closest(world, 10), 3)
        self.assertEqual(memo.town_valid(world, 3), True)
        self.assertEqual(memo.town_pop(world, 3), 800)
        self.assertEqual(
            (world.closest_calls, world.valid_calls, world.pop_calls), (1, 1, 1)
        )
        self.assertEqual(memo.closest(world, 10), 3)
        self.assertEqual(memo.town_valid(world, 3), True)
        self.assertEqual(memo.town_pop(world, 3), 800)
        self.assertEqual(
            (world.closest_calls, world.valid_calls, world.pop_calls), (1, 1, 1)
        )
        world.tick = 2
        self.assertEqual(memo.closest(world, 10), 3)
        self.assertEqual(world.closest_calls, 1)
        self.assertEqual(world.date_reads, 2)
        # Meme tick : un changement de date n'est pas observe.
        world.date = 130
        world.closest[10] = 9
        self.assertEqual(memo.closest(world, 10), 3)
        self.assertEqual(world.closest_calls, 1)
        self.assertEqual(world.date_reads, 2)
        # Tick suivant et date nouvelle : les cartes de ville sont vidées.
        world.tick = 3
        world.valid.add(9)
        world.pop[9] = 50
        self.assertEqual(memo.closest(world, 10), 9)
        self.assertEqual(world.closest_calls, 2)
        self.assertEqual(world.date_reads, 3)
        self.assertIs(memo.rank, rank)
        fresh = TownMemo()
        self.assertEqual(fresh.closest(world, 10), 9)
        self.assertEqual(world.closest_calls, 3)
        self.assertEqual(memo.closest(world, None), -1)
        self.assertEqual(memo.closest(world, None), -1)
        self.assertEqual(world.closest_calls, 5)

    def test_finance_shortcut_and_fit_skip_match_the_full_functions(self):
        air = {"mode": "air", "budgetCapital": 40000, "capital": 10000}
        water = {"mode": "water", "budgetCapital": 12000}
        fleet = {"mode": "fleet", "budgetCapital": 8000, "capital": 7000}
        rail = {
            "mode": "rail",
            "budgetCapital": 20000,
            "capital": 10000,
            "capitalIsActual": False,
        }
        road = {"mode": "road", "budgetCapital": 15000, "capital": 10000, "capitalIsActual": True}
        missing_mode = {"budgetCapital": 9000}
        missing_budget = {"mode": "air"}
        memo = FinanceMemo()
        for project in (air, water, fleet, missing_mode, missing_budget, None):
            self.assertEqual(memo.value(project), finance_capital(project))
        self.assertEqual(memo.full_calls, 3)
        self.assertEqual(memo.value(air), 40000)
        self.assertEqual(memo.full_calls, 3)
        rail_memo = FinanceMemo()
        self.assertEqual(rail_memo.value(rail), finance_capital(rail))
        self.assertEqual(rail_memo.value(rail), finance_capital(rail))
        self.assertEqual(rail_memo.full_calls, 1)
        rail["budgetCapital"] = 25000
        self.assertEqual(rail_memo.value(rail), finance_capital(rail))
        self.assertEqual(rail_memo.full_calls, 2)
        self.assertEqual(memo.value(road), finance_capital(road))
        road_project = {"mode": "road"}
        self.assertEqual(fit_memo(road_project, True), road_project)
        self.assertIs(fit_memo(road_project, False), road_project)
        fleet_project = {"mode": "fleet"}
        self.assertEqual(fit_memo(fleet_project, True)["id"], "fitted")
        self.assertIsNone(fit_memo(None, True))
        with self.assertRaises(KeyError):
            fit_memo({"budgetCapital": 1}, True)
        self.assertIn(
            'OpexProjectFitFleetToBudget(project, capitalBudget)', self.select
        )
        self.assertIn("OpexProjectFinanceCapital(project)", self.select)
        self.assertIn("OpexProjectFinanceCapital(p)", self.select)


if __name__ == "__main__":
    unittest.main()
