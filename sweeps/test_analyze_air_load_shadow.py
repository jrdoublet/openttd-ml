"""Fixtures synthétiques du contrat hebdomadaire AIR_LOAD7, sans lancer OpenTTD."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sweeps.analyze_air_load_shadow import (
    analyze,
    main,
    occupancy_stats,
    parse_flights,
    parse_log,
    pearson,
    reinforcement_events,
    render_markdown,
    station_diagnostics,
    stock_slope_per_week,
)


BASE = 722000


def sensor_record(week, *, line=3, fleet=2, a_load=90, b_load=20,
                  a_stock=10, b_stock=100, a_rating=50, b_rating=60,
                  a_mail_stock=5, b_mail_stock=20, extra="", flights=None):
    date = BASE + 7 * week
    if flights is None:
        flights = f"a:{a_load}:100:{100 + 7 * week}:24;b:{b_load}:100:200:30"
    return (
        f"[script-debug] OPEX 1970-1-1 AIR_LOAD7 date={date} line={line} "
        f"fleet={fleet} dist=150 neighbors=4 target=3 last_profit={1000 + 10 * week} "
        "running=2 observed=2 airport_a=small airport_b=large "
        "station_a=400 station_b=401 "
        f"a_pass_rating={a_rating} a_pass_wait={a_stock} "
        f"b_pass_rating={b_rating} b_pass_wait={b_stock} "
        f"a_mail_rating=80 a_mail_wait={a_mail_stock} "
        f"b_mail_rating=-1 b_mail_wait={b_mail_stock} "
        f"flights={flights} {extra}\n"
    )


def generate_diagnostic_records():
    return [
        sensor_record(i, a_load=90 + 2 * i, b_load=30 - 5 * i,
                      a_stock=10 + 15 * i, b_stock=100 - 10 * i,
                      a_rating=50 + 5 * i, b_rating=60 - 3 * i)
        for i in range(5)
    ]


def test_real_log_prefix_and_compact_flights_decoded():
    rows, counts, issues = parse_log([
        sensor_record(0, flights="a:70:100:10:24;b:30:60:-1:31;?:20:50:5:44")
    ], "run42.log")
    assert not issues
    assert counts["valid_snapshots"] == 1
    row = rows[0]
    assert (row["date"], row["line"], row["fleet"]) == (BASE, "3", 2)
    assert (row["stations"]["a"]["pass"]["rating"],
            row["stations"]["a"]["pass"]["stock"]) == (50, 10)
    assert row["stations"]["b"]["mail"]["rating"] is None
    assert row["observed"] == 2
    assert [f["direction"] for f in row["flights"]] == ["a", "b", "?"]
    assert row["flights"][0]["occupancy"] == .7
    assert row["flights"][1]["age_days"] is None
    assert row["flights"][2]["model"] == "44"


def test_empty_no_flights_is_different_from_missing_flights():
    row, counts, issues = parse_log([sensor_record(0, flights="-")])
    assert len(row) == 1
    assert not row[0]["flights"]
    assert counts["flights_decoded"] == 0
    missing = sensor_record(0).replace("flights=a:90:100:100:24;b:20:100:200:30", "")
    row, counts, issues = parse_log([missing])
    assert row == []
    assert counts["missing_or_invalid_required_field"] == 1


def test_bad_flight_does_not_destroy_other_valid_flights():
    flights, errors = parse_flights("a:30:40:0:4;b:200:100:12:6;x:1:10:3:2;?:0:20:1:-1")
    assert [f["direction"] for f in flights] == ["a", "?"]
    assert len(errors) == 2
    assert flights[-1]["model"] is None
    assert flights[0]["age_days"] == 0
    assert parse_flights("-") == ([], [])


def test_incomplete_flight_sample_is_excluded_not_treated_as_zero_load():
    corrupted = sensor_record(0, flights="a:90:100:10:4;b:broken:100:3:5")
    rows, counts, issues = parse_log([corrupted])
    assert len(rows) == 1
    assert rows[0]["flight_data_complete"] is False
    assert rows[0]["flights"] == []
    assert counts["snapshots_with_bad_flights"] == 1
    assert counts["flights_decoded"] == 0
    assert issues[0]["reason"].startswith("invalid_load_capacity")


def test_unknown_rating_and_profit_sentinels_do_not_form_fake_correlations():
    record = sensor_record(0, a_rating=101).replace("last_profit=1000", "last_profit=-1")
    rows, _, _ = parse_log([record])
    assert rows[0]["stations"]["a"]["pass"]["rating"] is None
    assert rows[0]["last_profit"] is None


def test_conflicting_duplicate_is_disqualified_and_identical_is_deduplicated():
    duplicate = sensor_record(0)
    rows, counts, _ = parse_log([duplicate, duplicate, sensor_record(1)])
    assert len(rows) == 2
    assert counts["identical_duplicates"] == 1
    conflict = sensor_record(0, a_load=50)
    rows, counts, issues = parse_log([duplicate, conflict, sensor_record(1)])
    assert len(rows) == 1
    assert rows[0]["date"] == BASE + 7
    assert counts["conflicting_duplicates"] == 1
    assert issues[0]["reason"] == "conflicting_duplicate_line_date"


def test_flight_distributions_are_capacity_weighted_and_empty_safe():
    flights, _ = parse_flights("a:50:100:50:2;b:9:10:60:4;a:10:10:70:4")
    stats = occupancy_stats(flights)
    assert stats["flights"] == 3
    assert stats["mean"] == pytest.approx(.8)
    assert stats["capacity_weighted"] == pytest.approx(69 / 120)
    assert stats["median"] == .9
    assert stats["p10"] == pytest.approx(.58)
    assert stats["histogram"]["90-100%"] == 2
    assert stats["models"] == {"2": 1, "4": 2}
    empty = occupancy_stats([])
    assert empty["capacity_weighted"] is None
    assert empty["median"] is None


def test_correlations_and_stock_slope_do_not_invent_missing_variation():
    corr = pearson([1, 2, 3, None], [10, 20, 30, 40])
    assert corr["n"] == 3
    assert corr["r"] == pytest.approx(1)
    assert pearson([1, 2], [2, 3])["r"] is None
    assert pearson([1, 1, 1], [2, 3, 4])["r"] is None
    assert stock_slope_per_week([(BASE, 10), (BASE + 7, 20),
                                 (BASE + 14, 30)]) == pytest.approx(10)
    assert stock_slope_per_week([(BASE, 10), (BASE + 7, 20)]) is None


def test_pressure_detects_both_undersupply_and_oversupply_without_causality():
    rows, _, _ = parse_log(generate_diagnostic_records())
    pressure = station_diagnostics(rows)
    assert pressure["a_pass"]["status"] == "underserved_suspected"
    assert pressure["a_pass"]["linked_weeks"] == 5
    assert pressure["a_pass"]["stock_slope_per_week"] == pytest.approx(15)
    assert pressure["a_pass"]["correlation"]["load_rating"]["r"] == pytest.approx(1)
    assert pressure["a_pass"]["correlation"]["load_stock"]["r"] == pytest.approx(1)
    assert pressure["b_pass"]["status"] == "overserved_suspected"
    assert pressure["b_pass"]["stock_slope_per_week"] == pytest.approx(-10)
    assert pressure["b_mail"]["correlation"]["load_rating"]["r"] is None
    assert pressure["b_mail"]["correlation"]["load_rating"]["n"] == 0
    assert pressure["b_mail"]["status"] == "pass_load_proxy_only"


def test_no_station_pressure_without_destination_flights_or_sufficient_history():
    lines = [sensor_record(i, flights="?:95:100:30:4") for i in range(5)]
    rows, _, _ = parse_log(lines)
    pressure = station_diagnostics(rows)
    assert all(p["status"] == "insufficient_data" for key, p in pressure.items()
               if key.endswith("_pass"))
    assert all(p["status"] == "pass_load_proxy_only" for key, p in pressure.items()
               if key.endswith("_mail"))
    assert all(p["linked_weeks"] == 0 for p in pressure.values())
    rows, _, _ = parse_log(generate_diagnostic_records()[:2])
    assert station_diagnostics(rows)["a_pass"]["status"] == "insufficient_data"


def test_positive_fleet_change_triggers_before_after_measures():
    lines = [
        sensor_record(i, fleet=2 if i < 4 else 3,
                      a_load=80 if i < 4 else 50,
                      b_load=80 if i < 4 else 50)
        for i in range(8)
    ]
    rows, _, _ = parse_log(lines)
    events = reinforcement_events(rows)
    assert len(events) == 1
    event = events[0]
    assert event["date"] == BASE + 28
    assert event["added"] == 1
    assert event["adequate_windows"] is True
    assert event["before"]["snapshots"] == 4
    assert event["after"]["snapshots"] == 4
    assert event["delta"]["occupancy"] == pytest.approx(-.3)
    assert event["delta"]["last_profit"] == pytest.approx(40)
    assert event["delta"]["fleet"] == 1


def test_explicit_reinforcement_date_within_sampling_interval():
    lines = [sensor_record(i, fleet=2, extra="reinforce=722025" if i == 4 else "")
             for i in range(8)]
    rows, _, _ = parse_log(lines)
    events = reinforcement_events(rows)
    assert len(events) == 1
    assert events[0]["date"] == BASE + 25
    assert events[0]["evidence"] == "explicit_timestamp"
    assert events[0]["added"] == 0
    assert events[0]["adequate_windows"]


def test_mixed_files_same_line_id_stay_independent(tmp_path):
    a = tmp_path / "seed42.log"
    b = tmp_path / "seed100.log"
    a.write_text("".join(generate_diagnostic_records()), encoding="utf-8")
    b.write_text(sensor_record(0, a_load=15), encoding="utf-8")
    result = analyze([a, b])
    assert result["counts"]["lines"] == 2
    assert result["counts"]["valid_snapshots"] == 6
    assert result["occupancy"]["flights"] == 12
    assert len(result["lines"][0]["station_pressure"]) == 4
    assert len(result["pressure_alerts"]) >= 2


def test_markdown_and_cli_output_json_are_parseable(tmp_path):
    logfile = tmp_path / "trace.log"
    logfile.write_text("".join(generate_diagnostic_records()), encoding="utf-8")
    result = analyze([logfile])
    markdown = render_markdown(result)
    assert "## Par ligne" in markdown
    assert "## Par direction" in markdown
    assert "## Renforts" in markdown
    assert "## Corrélations" in markdown
    assert "## Distribution" in markdown
    assert "underserved_suspected" in markdown
    result_json = tmp_path / "out.json"
    main([str(logfile), "--output", str(result_json)])
    structured = json.loads(result_json.read_text(encoding="utf-8"))
    assert structured["counts"]["lines"] == 1
    assert structured["lines"][0]["station_pressure"]["a_pass"]["correlation"]
    text = StringIO()
    with redirect_stdout(text):
        main([str(logfile), "--format", "markdown"])
    assert text.getvalue().startswith("# AIR_LOAD7")


@pytest.mark.parametrize("argv", [
    ["not_there.log"],
    ["irrelevant.log", "--high-load", "0.2", "--low-load", "0.4"],
    ["irrelevant.log", "--before-days", "0"],
])
def test_cli_input_validation(tmp_path, argv):
    with pytest.raises(SystemExit) as caught:
        main(argv)
    assert caught.value.code == 2
