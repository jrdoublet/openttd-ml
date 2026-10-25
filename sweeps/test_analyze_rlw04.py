"""RLW-04: tests du decompte, de la reprise et des gardes d'integration."""

from __future__ import annotations

import gzip
from pathlib import Path
import re

from sweeps.analyze_rlw04 import main, markdown, parse_line, read_log, summarize


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def checked_pairs(coords, cap=128):
    """Specification de la rotation source et du quota par source (mode pax)."""
    seen = []
    n = len(coords)
    step = max(1, (n + cap - 1) // cap)
    for a in range(n):
        b = a % step if step > 1 else 0
        if b <= a:
            b += ((a - b) // step + 1) * step
        checks = 0
        while b < n and checks < cap:
            dist = abs(coords[a][0] - coords[b][0]) + abs(coords[a][1] - coords[b][1])
            seen.append((a, b, dist))
            b += step
            checks += 1
    return seen


def indexed_pairs(coords, cell=128, cap=128):
    """Oracle independant de l'index en Squirrel : aucune exclusion en bord de cellule."""
    buckets = {}
    for b, (x, y) in enumerate(coords):
        buckets.setdefault((x // cell, y // cell), []).append((b, x, y))
    pairs = []
    for a, (x, y) in enumerate(coords):
        checked = 0
        for cy in range(max(0, (y - 288) // cell), (y + 288) // cell + 1):
            for cx in range(max(0, (x - 288) // cell), (x + 288) // cell + 1):
                for b, bx, by in buckets.get((cx, cy), ()):
                    if b <= a:
                        continue
                    dist = abs(x - bx) + abs(y - by)
                    if 224 <= dist <= 288:
                        if checked >= cap:
                            break
                        pairs.append((a, b, dist))
                        checked += 1
    return pairs


def test_off_preserves_standard_pipeline_and_without_probe():
    text = source("rail_long_window_enumerator.nut")
    assert "RLW04_SHADOW <- false;" in source("globals_post.nut")
    assert "RLW03_SHADOW <- false;" in source("globals_post.nut")
    assert "if (RLW04_SHADOW) this._rlw04Step();" in source("main.nut")
    assert "if (RLW04_SHADOW)" in source("probes.nut")
    assert "function _rlw04Step();" in source("main.nut")
    assert source("main.nut").index("class OpexAI") < source("main.nut").index('require("rail_long_window_enumerator.nut")')
    for forbidden in ("OpexMakeCandidate(", "OpexBuildCandidates(", "OpexV276Publish(",
                      "OpexV276Request(", "AIList.Sort(", "BuildRail(",
                      "OpexApplyGeneratedModeProjects("):
        assert forbidden not in re.sub(r"/\*.*?\*/", "", text, flags=re.S), forbidden
    assert not re.search(r"\b(?:owner|this)\._projects\s*=(?!=)", text)
    assert "catalog.bounds.railMax =" not in text
    assert "RLW03_SHADOW" not in text


def test_band_256_square_complete_without_pairs_before_224():
    coords = [(i * 8, 0) for i in range(32)]
    visited = checked_pairs(coords)
    selected = [(a, b) for a, b, dist in visited if 224 <= dist <= 288]
    outside_201_223 = [(a, b) for a, b, dist in visited if 201 <= dist <= 223]
    assert len(selected) == 10
    assert len(outside_201_223) == 11
    assert len(set(selected)) == len(selected)
    assert all(coords[a][0] < coords[b][0] for a, b in selected)


def test_band_1024_square_and_sparse_per_source_bound():
    coords = [(i * 16, 0) for i in range(64)]
    visited = checked_pairs(coords)
    assert len([1 for _, _, d in visited if 224 <= d <= 288]) == 240
    assert len([1 for _, _, d in visited if 201 <= d <= 223]) == 51
    many = [(i, 0) for i in range(1000)]
    sparse = checked_pairs(many)
    assert len(sparse) <= 1000 * 128
    assert len({(a, b) for a, b, _ in sparse}) == len(sparse)
    assert all(a < b for a, b, _ in sparse)
    # Des sources eloignees ne sont pas exclues par un TopK global.
    assert any(a == 990 for a, _, _ in sparse)


def test_spatial_cell_edges_and_symmetric_pax_no_loss():
    coords = [(i * 16, 0) for i in range(64)] + [
        (127, 127), (128, 128), (224, 0), (288, 0),
        (511, 511), (799, 511), (1023, 1023), (735, 1023),
    ]
    expected = {(a, b, d) for a in range(len(coords)) for b in range(a + 1, len(coords))
                if 224 <= (d := abs(coords[a][0] - coords[b][0])
                                    + abs(coords[a][1] - coords[b][1])) <= 288}
    assert set(indexed_pairs(coords)) == expected
    assert len(indexed_pairs([(i * 8, 0) for i in range(32)])) == 10
    assert len(indexed_pairs([(i * 16, 0) for i in range(64)])) == 240


def test_every_cargo_rotates_and_state_is_resumeable():
    text = source("rail_long_window_enumerator.nut")
    assert "s.cursor++" in text
    assert "s.cursor = 0" in text
    assert "u.a++" in text
    assert "OpexRLW04NextCell(s, u)" in text
    assert "OpexRLW04IndexStep(s, u)" in text
    assert "RLW04_CELL = 128" in text
    assert "RLW04_INDEX_BATCH" in text and "RLW04_SCAN_BATCH" in text
    assert "RLW04_SOURCE_DEST_CAP = 128" in text
    assert "RLW04_PAIRS_PER_SLICE = 24" in text
    assert "RLW04_OPS_BUDGET = 1800" in text
    assert "AIController.GetTick() == mark.tick" in text
    assert "OpexRLW04Pair(s, u)" in text
    assert "s.towns[u.a]" in text and "s.towns[b]" in text
    assert "s.industries[s.producers[u.cargo][u.a]]" in text
    assert "s.producers[u.cargo]" in text
    assert "s.acceptors[u.cargo]" in text
    assert "s.townAcceptors[u.cargo]" in text
    assert "s.refreshes++" in text
    assert "s.observedTowns != this._catalog.towns" in text
    assert "s.observedIndustries != this._catalog.industries" in text
    assert "s.observedProducers != this._catalog.producers" in text
    assert "s.observedAcceptors != this._catalog.acceptors" in text
    assert "s.observedTownAcceptors != this._catalog.townAcceptors" in text
    assert len(re.findall(r"this\._rlw04State\s*=\s*OpexRLW04Init\(this\._catalog\)", text)) == 1
    assert "stale_restart" not in text
    assert "AITown.IsValidTown(src.id)" in text
    assert "AIIndustry.IsValidIndustry(src.id)" in text
    assert "s.pool =" not in source("persist.nut")


def test_slice_budget_admission_and_probe_instrumentation():
    """Guard the next pair and its tail before work, then instrument costs."""
    text = source("rail_long_window_enumerator.nut")
    constants = {name: int(re.search(rf"const {name}\s*=\s*(\d+);", text).group(1))
                 for name in ("RLW04_OPS_BUDGET", "RLW04_OPS_RESERVE",
                              "RLW04_WORK_FLOOR", "RLW04_SLICE_TAIL")}
    assert 0 < constants["RLW04_WORK_FLOOR"]
    assert 0 < constants["RLW04_SLICE_TAIL"]
    assert (constants["RLW04_WORK_FLOOR"] + constants["RLW04_SLICE_TAIL"]
            < constants["RLW04_OPS_BUDGET"] < constants["RLW04_OPS_RESERVE"])
    while_body = text.split("while (processed < RLW04_PAIRS_PER_SLICE", 1)[1].split("if (s.pendingUnits == 0)", 1)[0]
    assert "local usedBefore = OpexOpsMeasureEnd(mark)" in while_body
    assert "s.maxWorkOps > 850 ? 850 : s.maxWorkOps" in while_body
    assert "+ 140" in while_body
    assert "if (estimated < RLW04_WORK_FLOOR)" in while_body
    assert "usedBefore + estimated + RLW04_SLICE_TAIL > RLW04_OPS_BUDGET" in while_body
    assert "AIController.GetOpsTillSuspend()" in while_body
    assert "RLW04_OPS_RESERVE - RLW04_OPS_BUDGET" in while_body
    assert while_body.index("usedBefore + estimated + RLW04_SLICE_TAIL") < while_body.index("OpexRLW04Pair(s, u)")
    assert "local workMark = OpexOpsMeasureBegin()" in while_body
    assert "local workOps = OpexOpsMeasureEnd(workMark)" in while_body
    assert "workOps > s.maxWorkOps" in while_body
    assert "this._rlw04State.initOps = OpexOpsMeasureEnd(initMark)" in text
    assert "local beforeTail = OpexOpsMeasureEnd(mark)" in text
    assert "local tailOps = used - beforeTail" in text
    assert "tailOps > s.maxTailOps" in text
    assert "s.logOps += logUsed" in text
    assert "logUsed > s.maxLogOps" in text
    assert "fullOps > RLW04_OPS_BUDGET || AIController.GetTick() != mark.tick" in text
    assert '" max_work_ops=" + s.maxWorkOps' in text
    assert '" max_tail_ops=" + s.maxTailOps' in text
    assert '" init_ops=" + s.initOps' in text
    assert '" max_log_ops=" + s.maxLogOps' in text
    assert "const RLW04_MAX_SLICES_CALL = 5;" in text
    assert "slicesThisCall < RLW04_MAX_SLICES_CALL" in text
    assert "local mark = OpexOpsMeasureBegin()" in text.split("slicesThisCall < RLW04_MAX_SLICES_CALL", 1)[1]
    assert "local fullOps = OpexOpsMeasureEnd(mark)" in text
    assert "fullOps > RLW04_OPS_BUDGET" in text
    assert "s.skippedReserve++" in text
    assert "s.extraSlices++" in text
    assert "s.totalRefreshOps += refreshUsed" in text
    assert "s.pendingUnitLogs.remove(0)" in text
    assert "u.visited++" in text
    assert "s.totalVisited++" in text
    assert "s.totalWorkOps += workOps" in text
    assert "s.totalFullOps += fullOps" in text
    assert "s.totalEnumLogOps += enumOps" in text
    assert "s.progressCursor = (s.progressCursor + 1) % s.units.len()" in text
    assert "OpexRLW04ChoosePriority(s)" in text


def test_spatial_preselection_is_bounded_and_separate_from_api_checks():
    code = source("rail_long_window_enumerator.nut")
    body = code.split("function OpexRLW04Pair(s, u)", 1)[1].split("function OpexRLW04Log(", 1)[0]
    assert body.index("local dist = abs(rec.x - u.sourceX)") < body.index("OpexRLW04Sink(s, u, rec.b)")
    assert body.index("dist < RLW04_MIN || dist > RLW04_MAX") < body.index("AITown.IsValidTown(dst.id)")
    assert "if (u.family == \"pax\" && rec.b <= u.a) continue" in body
    assert "if (u.checkedSource >= RLW04_SOURCE_DEST_CAP)" in body
    assert "u.indexReady" in body
    assert "index_ops=" in code and "scan_ops=" in code


def test_parser_reads_gz_and_reports_explicit_off(tmp_path, capsys):
    log = tmp_path / "base_seed42_r0.log.gz"
    with gzip.open(log, "wt", encoding="utf-8") as f:
        f.write("OPEX 1972-1-3 RLW04_ENUM phase=slice slices=64 scanned=200 band224_288=30 outside201_223=4 stock_pax=20 stock_freight=10 ops=1000 max_ops=1400 ticks=0 overrun=0 budget=1800\n")
        f.write("OPEX 1972-2-4 RLW04_UNIT family=pax cargo=PASS checked=234 band224_288=20\n")
        f.write("OPEX 1972-5-5 RLW04_ENUM phase=done slices=92 scanned=740 band224_288=74 outside201_223=10 stock_pax=32 stock_freight=32 ops=850 max_ops=1700 ticks=0 overrun=0 budget=1800\n")
    assert parse_line("garbage") is None
    assert len(list(read_log(log))) == 3
    result = summarize([log])
    assert result["complete"] == 1
    assert result["files"][0]["outside201_223"] == 10
    assert result["files"][0]["max_ops"] == 1700
    assert main([str(log), "--format", "json", "--expect-off"]) == 2
    capsys.readouterr()
    no_events = tmp_path / "off_seed42_r0.log"
    no_events.write_text("OPEX 1972-1-3 PROJECT_CHOSEN kind=air\n", encoding="utf-8")
    assert main([str(no_events), "--expect-off"]) == 0


def test_stale_restart_counters_are_accumulated_not_overwritten(tmp_path):
    log = tmp_path / "on_1024.log"
    log.write_text("\n".join([
        "OPEX 1972-1-1 RLW04_ENUM phase=slice slices=2 scanned=10 band224_288=2 outside201_223=1 stock_pax=1 stock_freight=2 max_ops=1940 overrun=2 budget=1800",
        "OPEX 1972-1-2 RLW04_ENUM phase=stale_restart slices=3 scanned=20 band224_288=4 outside201_223=1 stock_pax=1 stock_freight=3 max_ops=2050 overrun=3 budget=1800",
        "OPEX 1972-2-1 RLW04_ENUM phase=slice slices=2 scanned=12 band224_288=2 outside201_223=0 stock_pax=0 stock_freight=1 max_ops=1990 overrun=2 budget=1800",
        "OPEX 1972-2-2 RLW04_ENUM phase=stale_restart slices=2 scanned=12 band224_288=2 outside201_223=0 stock_pax=0 stock_freight=1 max_ops=1990 overrun=2 budget=1800",
        "OPEX 1972-2-3 RLW04_ENUM phase=stale_restart slices=0 scanned=0 band224_288=0 outside201_223=0 stock_pax=0 stock_freight=0 max_ops=0 overrun=0 budget=1800",
    ]) + "\n", encoding="utf-8")
    row = summarize([log])["files"][0]
    assert row["stale_restarts"] == 3
    assert row["slices"] == 5
    assert row["scanned"] == 32
    assert row["band224_288"] == 6
    assert row["outside201_223"] == 1
    assert row["max_ops"] == 2050
    assert row["overrun"] == 5
    assert row["stock_freight"] == 3
    assert row["complete"] is False
    assert row["progress_regressions"] == 0
    assert row["refreshes"] == 0
    assert row["slice_budget_observed_ok"] is False


def test_refresh_preserves_cumulative_progress_without_duplicate_epoch(tmp_path):
    """A refresh is a checkpoint, not an epoch boundary or a completed pass."""
    log = tmp_path / "on_refresh.log"
    log.write_text("\n".join([
        "OPEX 1972-1-1 RLW04_ENUM phase=slice slices=2 scanned=12 band224_288=3 outside201_223=1 stock_pax=2 stock_freight=1 max_ops=1400 overrun=0 budget=1800",
        "OPEX 1972-1-2 RLW04_ENUM phase=refresh slices=2 scanned=12 band224_288=3 outside201_223=1 stock_pax=2 stock_freight=1 max_ops=1400 overrun=0 budget=1800",
        "OPEX 1972-1-3 RLW04_ENUM phase=slice slices=4 scanned=25 band224_288=6 outside201_223=2 stock_pax=4 stock_freight=2 max_ops=1690 overrun=0 budget=1800",
        "OPEX 1972-1-4 RLW04_UNIT family=pax cargo=PASS checked=25 band224_288=6",
        "OPEX 1972-1-5 RLW04_ENUM phase=done slices=6 scanned=30 band224_288=7 outside201_223=3 stock_pax=4 stock_freight=3 max_ops=1720 overrun=0 budget=1800",
    ]) + "\n", encoding="utf-8")
    row = summarize([log])["files"][0]
    assert row["stale_restarts"] == 0
    assert row["refreshes"] == 1
    assert row["progress_regressions"] == 0
    assert row["epochs"] == 1
    assert row["complete"] is True
    assert (row["slices"], row["scanned"], row["band224_288"], row["outside201_223"]) == (6, 30, 7, 3)
    assert row["units_logged"] == 1
    assert row["max_ops"] == 1720
    assert row["slice_budget_observed_ok"] is True
    rendered = markdown(summarize([log]))
    assert "Refresh | Reculs" in rendered
    assert "| oui |" in rendered


def test_refresh_counter_and_pending_unit_logs_are_cumulative(tmp_path):
    """Actual Squirrel schema emits refreshes=N, not phase=refresh."""
    log = tmp_path / "real_refresh_schema.log"
    log.write_text("\n".join([
        "OPEX 1972-1-1 RLW04_ENUM phase=slice slices=64 units=10 pending=10 refreshes=1 scanned=300 band224_288=12 outside201_223=7 stock_pax=4 stock_freight=8 max_ops=1600 overrun=0 budget=1800 max_work_ops=210 max_tail_ops=240 init_ops=120 max_log_ops=0",
        "OPEX 1972-2-2 RLW04_UNIT family=pax cargo=PASS checked=350 band224_288=16 invalid_sources=0",
        "OPEX 1972-2-4 RLW04_ENUM phase=slice slices=128 units=10 pending=9 refreshes=4 scanned=670 band224_288=26 outside201_223=12 stock_pax=12 stock_freight=14 max_ops=1680 overrun=0 budget=1800 max_work_ops=245 max_tail_ops=260 init_ops=120 max_log_ops=180",
        "OPEX 1972-3-1 RLW04_ENUM phase=done slices=150 units=10 pending=0 refreshes=7 scanned=750 band224_288=30 outside201_223=13 stock_pax=16 stock_freight=16 max_ops=1690 overrun=0 budget=1800 max_work_ops=250 max_tail_ops=280 init_ops=120 max_log_ops=190",
    ]) + "\n", encoding="utf-8")
    row = summarize([log])["files"][0]
    assert row["epochs"] == 1
    assert row["refreshes"] == 7
    assert row["pending"] == 0
    assert row["units"] == 10
    assert row["progress_regressions"] == 0
    assert row["complete"] is True
    assert row["scanned"] == 750
    assert row["slices"] == 150
    assert row["max_work_ops"] == 250
    assert row["max_tail_ops"] == 280
    assert row["init_ops"] == 120
    assert row["max_log_ops"] == 190
    assert row["slice_budget_observed_ok"] is True


def test_refresh_before_truncated_end_keeps_latest_progress(tmp_path):
    log = tmp_path / "incomplete.log"
    log.write_text("\n".join([
        "OPEX 1972-1-1 RLW04_ENUM phase=slice slices=4 scanned=60 band224_288=8 outside201_223=2 stock_pax=6 stock_freight=2 max_ops=1480 overrun=0 budget=1800",
        "OPEX 1972-1-2 RLW04_ENUM phase=refresh_keep slices=5 scanned=64 band224_288=9 outside201_223=2 stock_pax=6 stock_freight=3 max_ops=1600 overrun=0 budget=1800",
    ]) + "\n", encoding="utf-8")
    row = summarize([log])["files"][0]
    assert row["complete"] is False
    assert row["epochs"] == 1
    assert row["refreshes"] == 1
    assert row["scanned"] == 64
    assert row["slices"] == 5
    assert row["slice_budget_observed_ok"] is True


def test_progress_regression_after_refresh_is_visible_but_real_restart_resets_epoch(tmp_path):
    """Detect a cursor reset hidden under a refresh, even if counters later grow."""
    log = tmp_path / "unexpected_reset.log"
    log.write_text("\n".join([
        "OPEX 1972-1-1 RLW04_ENUM phase=slice slices=8 scanned=200 band224_288=12 outside201_223=7 max_ops=1500 overrun=0 budget=1800",
        "OPEX 1972-1-2 RLW04_ENUM phase=refresh slices=8 scanned=200 band224_288=12 outside201_223=7 max_ops=1500 overrun=0 budget=1800",
        "OPEX 1972-1-3 RLW04_ENUM phase=slice slices=1 scanned=16 band224_288=1 outside201_223=0 max_ops=1600 overrun=0 budget=1800",
        "OPEX 1972-1-4 RLW04_ENUM phase=stale_restart slices=2 scanned=21 band224_288=2 outside201_223=0 max_ops=1600 overrun=0 budget=1800",
        "OPEX 1972-1-5 RLW04_ENUM phase=slice slices=1 scanned=7 band224_288=0 outside201_223=0 max_ops=1650 overrun=0 budget=1800",
    ]) + "\n", encoding="utf-8")
    row = summarize([log])["files"][0]
    assert row["progress_regressions"] == 1
    assert row["stale_restarts"] == 1
    assert row["refreshes"] == 1
    assert row["epochs"] == 2
    assert row["scanned"] == 28


def test_budget_evidence_distinguishes_observed_failure_and_missing_value(tmp_path):
    bad = tmp_path / "overrun.log"
    unknown = tmp_path / "unknown.log"
    bad.write_text("OPEX 1972-1-1 RLW04_ENUM phase=done slices=4 scanned=100 band224_288=9 outside201_223=1 max_ops=1801 overrun=1 budget=1800\n", encoding="utf-8")
    unknown.write_text("OPEX 1972-1-1 RLW04_ENUM phase=done slices=4 scanned=100 band224_288=9 outside201_223=1 max_ops=1700\n", encoding="utf-8")
    report = summarize([bad, unknown])
    assert report["files"][0]["slice_budget_observed_ok"] is False
    assert report["files"][1]["slice_budget_observed_ok"] is None
    assert "| non |" in markdown(report)
    assert "| ? |" in markdown(report)


def test_cadence_from_real_calendar_and_full_budget_including_logs(tmp_path):
    path = tmp_path / "cadence.log"
    path.write_text("\n".join([
        "OPEX 1972-4-20 RLW04_ENUM phase=slice slices=16 scanned=48 visited=60 overrun=0 budget=1800 max_ops=1200 max_full_ops=1490 calls=100 low_reserve=80 multislice=3 extra_slices=6 init_ops=1200 max_refresh_ops=32 max_enum_log_ops=290",
        "OPEX 1972-12-14 RLW04_ENUM phase=slice slices=48 scanned=145 visited=150 overrun=0 budget=1800 max_ops=1230 max_full_ops=1500 calls=300 low_reserve=260 multislice=10 extra_slices=20 init_ops=1200 max_refresh_ops=34 max_enum_log_ops=310",
    ]) + "\n", encoding="utf-8")
    row = summarize([path])["files"][0]
    assert row["slices"] == 48 and row["scanned"] == 145
    assert row["months_since_first_year"] == 12
    assert row["slices_per_month"] == 4.0
    assert row["scanned_per_slice"] == 3.02
    assert row["calls"] == 300 and row["low_reserve"] == 260
    assert row["max_full_ops"] == 1500
    assert row["slice_budget_observed_ok"] is True
    assert "Tranches/mois" in markdown({"logs": 1, "with_shadow": 1, "complete": 0,
                                      "files": [row], "limitations": []})
    path.write_text(path.read_text(encoding="utf-8").replace("max_full_ops=1500", "max_full_ops=1810"), encoding="utf-8")
    assert summarize([path])["files"][0]["slice_budget_observed_ok"] is False


def test_cost_shares_and_round_robin_progress_samples(tmp_path):
    path = tmp_path / "costs.log"
    path.write_text("\n".join([
        "OPEX 1972-4-20 RLW04_ENUM phase=slice slices=16 scanned=45 visited=47 overrun=0 budget=1800 max_full_ops=1475 total_full_ops=20000 total_work_ops=4000 total_enum_log_ops=200 total_unit_log_ops=120 total_refresh_ops=25 unit_index=0 unit_family=pax unit_cargo=0 unit_source=2 unit_sources=500 unit_visited=30 unit_done=0",
        "OPEX 1972-5-20 RLW04_ENUM phase=slice slices=32 scanned=92 visited=95 overrun=0 budget=1800 max_full_ops=1475 total_full_ops=40000 total_work_ops=8000 total_enum_log_ops=400 total_unit_log_ops=120 total_refresh_ops=45 unit_index=1 unit_family=freight unit_cargo=4 unit_source=3 unit_sources=60 unit_visited=12 unit_done=0",
        "OPEX 1972-6-20 RLW04_ENUM phase=slice slices=48 scanned=136 visited=140 overrun=0 budget=1800 max_full_ops=1475 total_full_ops=60000 total_work_ops=12000 total_enum_log_ops=600 total_unit_log_ops=240 total_refresh_ops=45 unit_index=0 unit_family=pax unit_cargo=0 unit_source=10 unit_sources=500 unit_visited=90 unit_done=0",
    ]) + "\n", encoding="utf-8")
    row = summarize([path])["files"][0]
    assert row["total_full_ops"] == 60000
    assert row["work_share_pct"] == 20
    assert row["log_share_pct"] == 1.4
    assert len(row["cursor_samples"]) == 2
    assert row["cursor_samples"][0]["source"] == 10
    assert row["cursor_samples"][1]["source"] == 3
    assert row["unit_progress_regressions"] == 0


def test_individual_source_regression_is_detected(tmp_path):
    log = tmp_path / "source_regressed.log"
    log.write_text("\n".join([
        "OPEX 1972-1-1 RLW04_ENUM phase=slice slices=16 scanned=30 unit_index=2 unit_family=freight unit_cargo=4 unit_source=20 unit_sources=70 unit_visited=90 unit_done=0",
        "OPEX 1972-2-1 RLW04_ENUM phase=slice slices=32 scanned=60 unit_index=2 unit_family=freight unit_cargo=4 unit_source=10 unit_sources=70 unit_visited=95 unit_done=0",
    ]) + "\n", encoding="utf-8")
    assert summarize([log])["files"][0]["unit_progress_regressions"] == 1
