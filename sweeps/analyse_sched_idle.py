#!/usr/bin/env python3
"""Analyseur V95 item 1 : tours de file selectionnes vs no-op.

Lit les lignes `SCHED_IDLE` emises sous probe_scheduler=1.
Les jours de jeu et les ticks viennent des horodatages de chaque evenement.

`--selftest` exerce l'accumulateur Python et les invariants statistiques.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENT_RE = re.compile(
    r"OPEX (\d+)-(\d+)-(\d+) (SCHED_IDLE(?:_YEAR|_MONTH|_REASON|_PROJ)?)\s*(.*)$",
    re.M,
)
C39_RE = re.compile(r"OPEX (\d+)-\d+-\d+ C39_PASS_CLOCK\s*(.*)$", re.M)
FIELD_RE = re.compile(r"(\w+)=(\S+)")

PREDICTABLE_REASONS = frozenset({
    "report_same_year",
    "repay_same_month",
    "catalog_fresh",
    "catalog_c78_partial_pending",
    "catalog_c78_slice_incomplete",
    "task_disabled",
    "air_disabled",
    "expand_disabled",
    "town_growth_disabled",
    "projects_invalidated",
    "projects_null",
})

DID_WORK_MEANING = {
    "catalog": "reselection, regeneration, ou tranche AIR C78 appliquee (ran == true)",
    "report": "publication annuelle de debut d'annee (_lastReportYear != year)",
    "repay": "remboursement partiel ou total du pret (curLoan < preLoan)",
    "scrap": "vehicule vendu ou ligne fermee/retiree (curVehs < preVehs || curLines < preLines)",
    "expand": "2e train ou wagon ajoute, expansion ou recherche A* demarree (curVehs > preVehs || railExp || railSearch)",
    "refleet": "nouveau vehicule achete et ajoute a une ligne existante (curVehs > preVehs)",
    "town_growth": "travailleur urbain demarre, vehicule/gare/ligne urbaine construite",
    "air_fleet": "injection de projets de flotte dans le vivier ou achat de nouvel avion",
    "projects": (
        "projects_useful (construction lancee/achevee, A* demarre/consomme, "
        "reactif C83 consomme, abandon traite)"
    ),
    "air": "construction aerienne hors portefeuille (auto-desactivee sous AIR_PORTFOLIO)",
}


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_fields(rest):
    return {key: value for key, value in FIELD_RE.findall(rest or "")}


def parse_sched_idle_output(output, seed=None):
    events = []
    months = []
    years = []
    reasons = []
    proj_years = []
    for year, month, day, kind, rest in EVENT_RE.findall(output or ""):
        fields = parse_fields(rest)
        date = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        rec = {
            "kind": kind, "date": date, "year": int(year), "month": int(month),
            "day": int(day), **fields,
        }
        if seed is not None:
            rec["seed"] = seed
        if kind == "SCHED_IDLE":
            rec["t"] = fields.get("t")
            rec["w"] = _to_int(fields.get("w"))
            rec["r"] = fields.get("r")
            rec["cls"] = fields.get("cls")
            rec["op"] = _to_int(fields.get("op"))
            rec["d"] = _to_int(fields.get("d"))
            rec["tk"] = _to_int(fields.get("tk"))
            rec["ad"] = _to_int(fields.get("ad"), -1)
            rec["at"] = _to_int(fields.get("at"), -1)
            rec["gap_d"] = _to_int(fields.get("gap_d"), _to_int(fields.get("gap"), -1)) if ("gap_d" in fields or "gap" in fields) else None
            rec["gap_tk"] = _to_int(fields.get("gap_tk"), -1) if "gap_tk" in fields else None
            rec["bg"] = _to_int(fields.get("bg"), -1) if "bg" in fields else None
            rec["bgw"] = _to_int(fields.get("bgw"), -1) if "bgw" in fields else None
            events.append(rec)
        elif kind == "SCHED_IDLE_MONTH":
            rec["year"] = _to_int(fields.get("year"), int(year))
            rec["month"] = _to_int(fields.get("month"), int(month))
            rec["sel"] = _to_int(fields.get("sel"))
            rec["work"] = _to_int(fields.get("work"))
            rec["noop"] = _to_int(fields.get("noop"))
            rec["pred"] = _to_int(fields.get("pred"))
            rec["after"] = _to_int(fields.get("after"))
            rec["op"] = _to_int(fields.get("op"))
            rec["d"] = _to_int(fields.get("d"))
            rec["tk"] = _to_int(fields.get("tk"))
            months.append(rec)
        elif kind == "SCHED_IDLE_REASON":
            rec["n"] = _to_int(fields.get("n"))
            rec["year"] = _to_int(fields.get("year"), int(year))
            if "month" in fields:
                rec["month"] = _to_int(fields.get("month"))
            reasons.append(rec)
        elif kind == "SCHED_IDLE_PROJ":
            rec["year"] = _to_int(fields.get("year"), int(year))
            if "month" in fields:
                rec["month"] = _to_int(fields.get("month"))
            rec["useful_gaps"] = _to_int(fields.get("useful_gaps"))
            proj_years.append(rec)
    c39 = []
    for year, rest in C39_RE.findall(output or ""):
        fields = parse_fields(rest)
        key = fields.get("key") or ""
        task = key.split("|", 1)[0] if key else ""
        c39.append({
            "year": int(year),
            "task": task,
            "key": key,
            "passes": _to_int(fields.get("passes")),
            "days": _to_int(fields.get("days")),
            "ticks": _to_int(fields.get("ticks")),
            "ops": _to_int(fields.get("ops")),
        })
    return {
        "events": events,
        "months": months,
        "years": years,
        "reasons": reasons,
        "proj_years": proj_years,
        "c39": c39,
    }


def _percentile(sorted_values, p):
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * p
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return sorted_values[int(k)]
    return sorted_values[lo] * (hi - k) + sorted_values[hi] * (k - lo)


def _stats(values):
    values = [v for v in values if v is not None]
    if not values:
        return {
            "n": 0, "sum": 0, "mean": None, "median": None, "p90": None,
            "min": None, "max": None,
        }
    ordered = sorted(values)
    mean_val = statistics.mean(ordered)
    med_val = statistics.median(ordered)
    p90_val = _percentile(ordered, 0.9)
    min_val = ordered[0]
    max_val = ordered[-1]
    if min_val >= 0 and len(ordered) > 0:
        assert med_val <= max_val + 1e-9, f"median {med_val} > max {max_val}"
        assert mean_val >= 0.5 * med_val - 1e-9, f"mean {mean_val} < 0.5 * median {med_val}"
    return {
        "n": len(ordered),
        "sum": sum(ordered),
        "mean": mean_val,
        "median": med_val,
        "p90": p90_val,
        "min": min_val,
        "max": max_val,
    }


class SchedIdleTracker:
    """Replica Python du ledger Squirrel, pour tests deterministes hors partie."""

    def __init__(self):
        self.last_work_date = {}
        self.last_work_tick = {}
        self.by_task = defaultdict(lambda: {
            "selected": 0, "did_work": 0, "noop": 0, "ops": 0, "days": 0, "ticks": 0,
            "pred": 0, "after": 0,
        })
        self.reasons = Counter()
        self.projects_last_date = None
        self.projects_last_tick = None
        self.since_sel = 0
        self.since_work = 0
        self.events = []
        self._frame = None
        self.projects_gaps = []

    def on_selected(self, task, date, tick):
        age_days = (date - self.last_work_date[task]) if task in self.last_work_date else -1
        age_ticks = (tick - self.last_work_tick[task]) if task in self.last_work_tick else -1
        self._frame = {
            "name": task,
            "date": date,
            "tick": tick,
            "age_days": age_days,
            "age_ticks": age_ticks,
            "did_work": False,
            "reason": None,
            "skip_class": "after",
            "examined": 0,
            "sub_field": "none",
        }

    def note(self, did_work, reason, skip_class, examined=0, sub_field="none"):
        if self._frame is None:
            return
        self._frame["did_work"] = bool(did_work)
        self._frame["reason"] = reason
        self._frame["skip_class"] = skip_class
        self._frame["examined"] = examined
        self._frame["sub_field"] = sub_field

    def note_work(self, reason=None, sub_field="none"):
        if self._frame is None:
            return
        self._frame["did_work"] = True
        if reason is not None:
            self._frame["reason"] = reason
            self._frame["skip_class"] = "work"
        self._frame["sub_field"] = sub_field

    def finish(self, date, tick, ops, days, ticks, ran=False):
        frame = self._frame
        if frame is None:
            return None
        self._frame = None
        did_work = frame["did_work"]
        reason = frame["reason"]
        skip_class = frame["skip_class"]
        if reason is None:
            if did_work:
                reason = "unspecified_work"
                skip_class = "work"
            elif ran:
                reason = "task_returned_true"
                did_work = True
                skip_class = "work"
            else:
                reason = "unspecified_noop"
                skip_class = "after"
        if did_work:
            skip_class = "work"
        elif skip_class == "work":
            skip_class = "after"
        task = frame["name"]
        entry = self.by_task[task]
        entry["selected"] += 1
        entry["ops"] += ops
        entry["days"] += days
        entry["ticks"] += ticks
        if did_work:
            entry["did_work"] += 1
            self.last_work_date[task] = date
            self.last_work_tick[task] = tick
        else:
            entry["noop"] += 1
            if skip_class == "pred":
                entry["pred"] += 1
            else:
                entry["after"] += 1
        self.reasons[(task, reason)] += 1
        gap_d = gap_tk = bg = bgw = None
        if task == "projects":
            if did_work:
                gap_d = (date - self.projects_last_date) if self.projects_last_date is not None else -1
                gap_tk = (tick - self.projects_last_tick) if self.projects_last_tick is not None else -1
                bg = self.since_sel
                bgw = self.since_work
                if self.projects_last_date is not None and gap_d >= 0:
                    self.projects_gaps.append({
                        "gap_d": gap_d, "gap_tk": gap_tk, "bg": bg, "bgw": bgw,
                    })
                self.projects_last_date = date
                self.projects_last_tick = tick
                self.since_sel = 0
                self.since_work = 0
            else:
                self.since_sel += 1
        else:
            self.since_sel += 1
            if did_work:
                self.since_work += 1
        rec = {
            "t": task,
            "w": 1 if did_work else 0,
            "r": reason,
            "cls": skip_class,
            "sub": frame["sub_field"],
            "op": ops,
            "d": days,
            "tk": ticks,
            "ad": frame["age_days"],
            "at": frame["age_ticks"],
            "exam": frame["examined"],
            "date": date,
            "year": 1970,
            "month": 1,
            "day": 1,
            "gap_d": gap_d,
            "gap_tk": gap_tk,
            "bg": bg,
            "bgw": bgw,
        }
        self.events.append(rec)
        return rec


def summarize_events(events, seed_series=None, baseline_series=None):
    """Calcule toutes les distributions et tableaux a partir des echantillons individuels."""
    if not events:
        return {
            "complete_years": [],
            "coverage_by_seed_year": {},
            "seed_year_breakdown": [],
            "by_task": [],
            "reasons": [],
            "years": {},
            "projects_bg_mean": None,
            "projects_bg_median": None,
            "projects_bg_p90": None,
            "projects_gap_days_mean": None,
            "projects_gap_days_median": None,
            "projects_gap_days_p90": None,
            "projects_gap_ticks_mean": None,
            "projects_gap_ticks_median": None,
            "projects_gap_ticks_p90": None,
            "projects_useful_intervals": 0,
            "noop_share_of_selections": None,
            "pred_share_of_selections": None,
            "pred_share_of_noops": None,
            "total_selected": 0,
            "total_did_work": 0,
            "total_noop": 0,
            "total_pred": 0,
            "total_after": 0,
            "skip_not_due_candidates": [],
            "perturbation": [],
            "source": "events",
        }

    # 1. Couverture mensuelle par (graine, annee)
    months_by_seed_year = defaultdict(lambda: defaultdict(set))
    all_seeds = set()
    for ev in events:
        s = ev.get("seed", 0)
        y = ev.get("year", 0)
        m = ev.get("month", 0)
        if y > 0 and 1 <= m <= 12:
            months_by_seed_year[s][y].add(m)
            all_seeds.add(s)

    if not all_seeds:
        all_seeds.add(0)

    years_seen = sorted({y for s in months_by_seed_year for y in months_by_seed_year[s]})
    complete_years = []
    coverage_by_seed_year = {}
    for y in years_seen:
        all_12 = True
        for s in sorted(all_seeds):
            c = len(months_by_seed_year[s][y])
            coverage_by_seed_year[(s, y)] = f"{c}/12"
            if c < 12:
                all_12 = False
        if all_12:
            complete_years.append(y)

    valid_complete_years_set = set(complete_years)

    # 2. Validation stricte de chaque event : classe work <==> did_work
    for ev in events:
        w = ev.get("w")
        cls_val = ev.get("cls")
        t = ev.get("t")
        r = ev.get("r")
        assert w in (0, 1), f"Invalid w={w} for task {t}"
        assert (w == 1) == (cls_val == "work"), (
            f"Class {cls_val} mismatch with did_work {w} for task {t}, reason {r}"
        )
        if w == 0:
            assert cls_val in ("pred", "after"), f"No-op class must be pred or after, got {cls_val}"
            if r in PREDICTABLE_REASONS:
                assert cls_val == "pred", f"Predictable reason {r} must be cls=pred, got {cls_val}"

    # 3. seed_year_breakdown (toutes les annees observees)
    seed_year_breakdown = []
    evs_by_seed_year = defaultdict(list)
    for ev in events:
        s = ev.get("seed", 0)
        y = ev.get("year", 0)
        evs_by_seed_year[(s, y)].append(ev)

    for (s, y) in sorted(evs_by_seed_year.keys()):
        sy_evs = evs_by_seed_year[(s, y)]
        sel = len(sy_evs)
        work = sum(1 for e in sy_evs if e["w"] == 1)
        noop = sum(1 for e in sy_evs if e["w"] == 0)
        pred = sum(1 for e in sy_evs if e["cls"] == "pred")
        after = sum(1 for e in sy_evs if e["cls"] == "after")
        cov = coverage_by_seed_year.get((s, y), "0/12")
        seed_year_breakdown.append({
            "seed": s,
            "year": y,
            "coverage": cov,
            "selected": sel,
            "did_work": work,
            "noop": noop,
            "noop_rate": (noop / sel) if sel else None,
            "pred": pred,
            "after": after,
        })

    # Filtrer les events sur les annees completes
    comp_evs = [e for e in events if e.get("year") in valid_complete_years_set]

    # 4. Synthese par annee (annees completes)
    years_stats = {}
    evs_by_year = defaultdict(list)
    for ev in comp_evs:
        evs_by_year[ev["year"]].append(ev)

    for y in complete_years:
        y_evs = evs_by_year[y]
        sel = len(y_evs)
        work = sum(1 for e in y_evs if e["w"] == 1)
        noop = sum(1 for e in y_evs if e["w"] == 0)
        pred = sum(1 for e in y_evs if e["cls"] == "pred")
        after = sum(1 for e in y_evs if e["cls"] == "after")
        years_stats[y] = {
            "selected": sel,
            "did_work": work,
            "noop": noop,
            "noop_rate": (noop / sel) if sel else None,
            "pred": pred,
            "after": after,
            "coverage": "12/12",
        }

    # 5. Synthese par tache (annees completes)
    evs_by_task = defaultdict(list)
    for ev in comp_evs:
        evs_by_task[ev["t"]].append(ev)

    by_task = []
    for task in sorted(evs_by_task.keys()):
        t_evs = evs_by_task[task]
        sel = len(t_evs)
        work = sum(1 for e in t_evs if e["w"] == 1)
        noop = sum(1 for e in t_evs if e["w"] == 0)
        pred = sum(1 for e in t_evs if e["cls"] == "pred")
        after = sum(1 for e in t_evs if e["cls"] == "after")

        ops_st = _stats([e["op"] for e in t_evs])
        days_st = _stats([e["d"] for e in t_evs])
        ticks_st = _stats([e["tk"] for e in t_evs])

        age_d_st = _stats([e["ad"] for e in t_evs if e["w"] == 1 and e.get("ad", -1) >= 0])
        age_tk_st = _stats([e["at"] for e in t_evs if e["w"] == 1 and e.get("at", -1) >= 0])

        by_task.append({
            "task": task,
            "selected": sel,
            "did_work": work,
            "noop": noop,
            "noop_rate": (noop / sel) if sel else None,
            "pred": pred,
            "after": after,
            "ops_sum": ops_st["sum"],
            "ops_mean": ops_st["mean"],
            "ops_median": ops_st["median"],
            "ops_p90": ops_st["p90"],
            "ops_max": ops_st["max"],
            "days_sum": days_st["sum"],
            "days_mean": days_st["mean"],
            "days_median": days_st["median"],
            "days_p90": days_st["p90"],
            "days_max": days_st["max"],
            "ticks_sum": ticks_st["sum"],
            "ticks_mean": ticks_st["mean"],
            "ticks_median": ticks_st["median"],
            "ticks_p90": ticks_st["p90"],
            "ticks_max": ticks_st["max"],
            "age_days_mean": age_d_st["mean"],
            "age_days_median": age_d_st["median"],
            "age_days_p90": age_d_st["p90"],
            "age_ticks_median": age_tk_st["median"],
            "age_ticks_p90": age_tk_st["p90"],
            "did_work_meaning": DID_WORK_MEANING.get(task, "non specifie"),
        })

    # 6. Synthese par (tache, raison) (annees completes)
    evs_by_tr = defaultdict(list)
    for ev in comp_evs:
        evs_by_tr[(ev["t"], ev["r"])].append(ev)

    reasons = []
    for (task, reason), tr_evs in sorted(evs_by_tr.items(), key=lambda item: len(item[1]), reverse=True):
        n = len(tr_evs)
        cls_val = tr_evs[0]["cls"]
        ops_st = _stats([e["op"] for e in tr_evs])
        days_st = _stats([e["d"] for e in tr_evs])
        ticks_st = _stats([e["tk"] for e in tr_evs])
        task_sel = len(evs_by_task[task])

        reasons.append({
            "task": task,
            "reason": reason,
            "skip_class": cls_val,
            "n": n,
            "share_of_task": (n / task_sel) if task_sel else None,
            "ops_sum": ops_st["sum"],
            "ops_mean": ops_st["mean"],
            "ops_median": ops_st["median"],
            "ops_p90": ops_st["p90"],
            "ops_max": ops_st["max"],
            "days_sum": days_st["sum"],
            "days_mean": days_st["mean"],
            "days_median": days_st["median"],
            "days_p90": days_st["p90"],
            "days_max": days_st["max"],
            "ticks_sum": ticks_st["sum"],
            "ticks_mean": ticks_st["mean"],
            "ticks_median": ticks_st["median"],
            "ticks_p90": ticks_st["p90"],
            "ticks_max": ticks_st["max"],
        })

    # 7. Cadence projects utiles (annees completes)
    useful_proj = [
        e for e in comp_evs
        if e["t"] == "projects" and e["w"] == 1
        and e.get("gap_d") is not None and e.get("gap_d") >= 0
    ]
    bg_st = _stats([e["bg"] for e in useful_proj if e.get("bg") is not None and e.get("bg") >= 0])
    bgw_st = _stats([e["bgw"] for e in useful_proj if e.get("bgw") is not None and e.get("bgw") >= 0])
    gap_d_st = _stats([e["gap_d"] for e in useful_proj])
    gap_tk_st = _stats([e["gap_tk"] for e in useful_proj if e.get("gap_tk") is not None and e.get("gap_tk") >= 0])

    # 8. Candidats skip-not-due justifies (cls == "pred")
    candidates_detail = []
    pred_reasons = [r for r in reasons if r["skip_class"] == "pred"]
    for r in sorted(pred_reasons, key=lambda x: (x["days_sum"], x["ops_sum"]), reverse=True):
        enjeu = "opcodes & jours" if (r["days_mean"] is not None and r["days_mean"] > 0.05) else (
            "opcodes seuls (~200 ops, 0 tick)" if (r["ticks_mean"] is not None and r["ticks_mean"] == 0) else "opcodes & ticks"
        )
        candidates_detail.append({
            "task": r["task"],
            "reason": r["reason"],
            "count": r["n"],
            "ops_sum": r["ops_sum"],
            "ops_mean": r["ops_mean"],
            "ops_median": r["ops_median"],
            "ops_p90": r["ops_p90"],
            "days_sum": r["days_sum"],
            "days_mean": r["days_mean"],
            "ticks_mean": r["ticks_mean"],
            "enjeu": enjeu,
        })

    # 9. Verification stricte de coherence des totaux
    total_sel = len(comp_evs)
    total_work = sum(1 for e in comp_evs if e["w"] == 1)
    total_noop = sum(1 for e in comp_evs if e["w"] == 0)
    total_pred = sum(1 for e in comp_evs if e["cls"] == "pred")
    total_after = sum(1 for e in comp_evs if e["cls"] == "after")

    task_sel = sum(r["selected"] for r in by_task)
    task_work = sum(r["did_work"] for r in by_task)
    task_noop = sum(r["noop"] for r in by_task)
    task_pred = sum(r["pred"] for r in by_task)
    task_after = sum(r["after"] for r in by_task)

    year_sel = sum(v["selected"] for v in years_stats.values())
    year_work = sum(v["did_work"] for v in years_stats.values())
    year_noop = sum(v["noop"] for v in years_stats.values())
    year_pred = sum(v["pred"] for v in years_stats.values())
    year_after = sum(v["after"] for v in years_stats.values())

    reason_n = sum(r["n"] for r in reasons)
    reason_work = sum(r["n"] for r in reasons if r["skip_class"] == "work")
    reason_pred = sum(r["n"] for r in reasons if r["skip_class"] == "pred")
    reason_after = sum(r["n"] for r in reasons if r["skip_class"] == "after")

    sy_comp = [sy for sy in seed_year_breakdown if sy["year"] in valid_complete_years_set]
    sy_sel = sum(sy["selected"] for sy in sy_comp)
    sy_work = sum(sy["did_work"] for sy in sy_comp)
    sy_noop = sum(sy["noop"] for sy in sy_comp)
    sy_pred = sum(sy["pred"] for sy in sy_comp)
    sy_after = sum(sy["after"] for sy in sy_comp)

    if not (total_sel == task_sel == year_sel == reason_n == sy_sel):
        raise AssertionError(
            f"Incoherent totals for selected: total={total_sel}, by_task={task_sel}, "
            f"years={year_sel}, reasons={reason_n}, seed_years={sy_sel}"
        )
    if not (total_work == task_work == year_work == reason_work == sy_work):
        raise AssertionError(
            f"Incoherent totals for work: total={total_work}, by_task={task_work}, "
            f"years={year_work}, reasons={reason_work}, seed_years={sy_work}"
        )
    if not (total_noop == task_noop == year_noop == (reason_pred + reason_after) == sy_noop):
        raise AssertionError(
            f"Incoherent totals for noop: total={total_noop}, by_task={task_noop}, "
            f"years={year_noop}, reasons={reason_pred + reason_after}, seed_years={sy_noop}"
        )
    if not (total_pred == task_pred == year_pred == reason_pred == sy_pred):
        raise AssertionError(
            f"Incoherent totals for pred: total={total_pred}, by_task={task_pred}, "
            f"years={year_pred}, reasons={reason_pred}, seed_years={sy_pred}"
        )
    if not (total_after == task_after == year_after == reason_after == sy_after):
        raise AssertionError(
            f"Incoherent totals for after: total={total_after}, by_task={task_after}, "
            f"years={year_after}, reasons={reason_after}, seed_years={sy_after}"
        )

    # 10. Perturbation (si reference fournie)
    perturbation = []
    if baseline_series and seed_series:
        base_by_seed = {r.get("seed"): r for r in baseline_series}
        for var_row in seed_series:
            seed = var_row.get("seed")
            base_row = base_by_seed.get(seed)
            if not base_row:
                continue
            b_val = base_row.get("company_value", 0)
            v_val = var_row.get("company_value", 0)
            b_prof = base_row.get("profit_year", 0)
            v_prof = var_row.get("profit_year", 0)
            b_veh = base_row.get("n_vehicles", 0)
            v_veh = var_row.get("n_vehicles", 0)
            b_st = base_row.get("n_stations", 0)
            v_st = var_row.get("n_stations", 0)
            val_delta = v_val - b_val
            val_pct = (val_delta / b_val * 100.0) if b_val else 0.0
            prof_delta = v_prof - b_prof
            prof_pct = (prof_delta / b_prof * 100.0) if b_prof else 0.0
            perturbation.append({
                "seed": seed,
                "base_val": b_val, "var_val": v_val, "val_delta": val_delta, "val_pct": val_pct,
                "base_prof": b_prof, "var_prof": v_prof, "prof_delta": prof_delta, "prof_pct": prof_pct,
                "base_veh": b_veh, "var_veh": v_veh, "veh_delta": v_veh - b_veh,
                "base_st": b_st, "var_st": v_st, "st_delta": v_st - b_st,
            })

    return {
        "complete_years": complete_years,
        "coverage_by_seed_year": {f"s{s}_y{y}": c for (s, y), c in coverage_by_seed_year.items()},
        "seed_year_breakdown": seed_year_breakdown,
        "by_task": by_task,
        "reasons": reasons,
        "cls": {
            "pred": total_pred,
            "after": total_after,
            "work": total_work,
        },
        "years": years_stats,
        "projects_bg_mean": bg_st["mean"],
        "projects_bg_median": bg_st["median"],
        "projects_bg_p90": bg_st["p90"],
        "projects_gap_days_mean": gap_d_st["mean"],
        "projects_gap_days_median": gap_d_st["median"],
        "projects_gap_days_p90": gap_d_st["p90"],
        "projects_gap_ticks_mean": gap_tk_st["mean"],
        "projects_gap_ticks_median": gap_tk_st["median"],
        "projects_gap_ticks_p90": gap_tk_st["p90"],
        "projects_useful_intervals": len(useful_proj),
        "noop_share_of_selections": (total_noop / total_sel) if total_sel else None,
        "pred_share_of_selections": (total_pred / total_sel) if total_sel else None,
        "pred_share_of_noops": (total_pred / total_noop) if total_noop else None,
        "total_selected": total_sel,
        "total_did_work": total_work,
        "total_noop": total_noop,
        "total_pred": total_pred,
        "total_after": total_after,
        "skip_not_due_candidates": candidates_detail,
        "perturbation": perturbation,
        "source": "events",
    }


summarize_monthly = summarize_events
summarize_annual = summarize_events


def format_report(summary):
    lines = ["# Scheduler idle tours (V95 item 1 — synthese v3)", ""]

    lines.append("## Definitions de did_work par dispatcher")
    lines.append("| tache | definition de `did_work == true` |")
    lines.append("|---|---|")
    for t, meaning in DID_WORK_MEANING.items():
        lines.append(f"| {t} | {meaning} |")
    lines.append("")

    lines.append("## Par tache (annees completes 1970–1972)")
    lines.append(
        "| tache | sel | work | noop | noop% | pred | after | ops tot | ops moy | ops med | jours tot | jours moy | age d med | age d p90 | age tk med |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in summary["by_task"]:
        rate = "" if row["noop_rate"] is None else f"{100 * row['noop_rate']:.1f}%"
        ops_moy = "" if row["ops_mean"] is None else f"{row['ops_mean']:.0f}"
        ops_med = "" if row["ops_median"] is None else f"{row['ops_median']:.0f}"
        days_moy = "" if row["days_mean"] is None else f"{row['days_mean']:.2f}"
        age_med = "" if row["age_days_median"] is None else f"{row['age_days_median']:.1f}"
        age_p90 = "" if row["age_days_p90"] is None else f"{row['age_days_p90']:.1f}"
        age_tk = "" if row.get("age_ticks_median") is None else f"{row['age_ticks_median']:.0f}"
        lines.append(
            f"| {row['task']} | {row['selected']} | {row['did_work']} | {row['noop']} | "
            f"{rate} | {row['pred']} | {row['after']} | {row['ops_sum']} | {ops_moy} | {ops_med} | "
            f"{row['days_sum']} | {days_moy} | {age_med} | {age_p90} | {age_tk} |"
        )
    lines.append("")

    lines.append("## Par couple (tache, raison) (annees completes 1970–1972)")
    lines.append(
        "| tache | raison | classe | n | % tache | ops tot | ops moy | ops med | ops p90 | jours moy | ticks moy | ticks med |"
    )
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in summary["reasons"]:
        share = "" if row["share_of_task"] is None else f"{100 * row['share_of_task']:.1f}%"
        ops_moy = "" if row["ops_mean"] is None else f"{row['ops_mean']:.0f}"
        ops_med = "" if row["ops_median"] is None else f"{row['ops_median']:.0f}"
        ops_p90 = "" if row["ops_p90"] is None else f"{row['ops_p90']:.0f}"
        days_moy = "" if row["days_mean"] is None else f"{row['days_mean']:.2f}"
        ticks_moy = "" if row["ticks_mean"] is None else f"{row['ticks_mean']:.1f}"
        ticks_med = "" if row["ticks_median"] is None else f"{row['ticks_median']:.0f}"
        lines.append(
            f"| {row['task']} | {row['reason']} | {row['skip_class']} | {row['n']} | "
            f"{share} | {row['ops_sum']} | {ops_moy} | {ops_med} | {ops_p90} | "
            f"{days_moy} | {ticks_moy} | {ticks_med} |"
        )
    lines.append("")

    lines.append("## Couverture et repartition par graine × annee")
    lines.append("| graine | annee | couv | sel | work | noop | noop% | pred | after |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for sy in summary.get("seed_year_breakdown", []):
        rate = "" if sy["noop_rate"] is None else f"{100 * sy['noop_rate']:.1f}%"
        lines.append(
            f"| {sy['seed']} | {sy['year']} | {sy['coverage']} | {sy['selected']} | "
            f"{sy['did_work']} | {sy['noop']} | {rate} | {sy['pred']} | {sy['after']} |"
        )
    lines.append("")

    lines.append("## Synthese globale et cadence projects (annees completes 1970–1972)")
    share = summary.get("noop_share_of_selections")
    pred = summary.get("pred_share_of_noops")
    lines.append(
        f"- Selections totales: {summary.get('total_selected')} "
        f"(work: {summary.get('total_did_work')}, noop: {summary.get('total_noop')}, "
        f"pred: {summary.get('total_pred')}, after: {summary.get('total_after')})."
    )
    lines.append(
        f"- Part des selections en no-op: "
        f"{'n/a' if share is None else f'{100 * share:.1f}%'} "
        f"(pred parmi no-op: {'n/a' if pred is None else f'{100 * pred:.1f}%'})."
    )
    bg_moy = f"{summary.get('projects_bg_mean'):.1f}" if summary.get('projects_bg_mean') is not None else "n/a"
    lines.append(
        f"- Taches d'arriere-plan traversees entre deux `projects` utiles: "
        f"moyenne={bg_moy} mediane={summary.get('projects_bg_median')} "
        f"p90={summary.get('projects_bg_p90')} (n={summary.get('projects_useful_intervals')})."
    )
    gap_d_moy = f"{summary.get('projects_gap_days_mean'):.1f}" if summary.get('projects_gap_days_mean') is not None else "n/a"
    lines.append(
        f"- Delai en jours entre `projects` utiles: "
        f"moyenne={gap_d_moy} mediane={summary.get('projects_gap_days_median')} "
        f"p90={summary.get('projects_gap_days_p90')}."
    )
    gap_tk_moy = f"{summary.get('projects_gap_ticks_mean'):.1f}" if summary.get('projects_gap_ticks_mean') is not None else "n/a"
    lines.append(
        f"- Delai en ticks entre `projects` utiles: "
        f"moyenne={gap_tk_moy} mediane={summary.get('projects_gap_ticks_median')} "
        f"p90={summary.get('projects_gap_ticks_p90')}."
    )
    lines.append("")

    if summary.get("perturbation"):
        lines.append("## Perturbation probe_scheduler=1 vs reference probe_scheduler=0")
        lines.append("| graine | val ref | val sonde | delta val (%) | profit ref | profit sonde | delta prof (%) | veh ref | veh sonde | st ref | st sonde |")
        lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for p in summary["perturbation"]:
            lines.append(
                f"| {p['seed']} | {p['base_val']} | {p['var_val']} | {p['val_delta']} ({p['val_pct']:+.1f}%) | "
                f"{p['base_prof']} | {p['var_prof']} | {p['prof_delta']} ({p['prof_pct']:+.1f}%) | "
                f"{p['base_veh']} | {p['var_veh']} ({p['veh_delta']:+d}) | "
                f"{p['base_st']} | {p['var_st']} ({p['st_delta']:+d}) |"
            )
        lines.append("")

    lines.append("## Candidats skip-not-due justifies (cls=pred)")
    lines.append("| tache | raison | n | ops moy/tour | ops med/tour | jours moy/tour | ticks moy/tour | ops tot | jours tot | enjeu |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for cand in summary.get("skip_not_due_candidates", []):
        ops_moy = f"{cand['ops_mean']:.0f}" if cand.get("ops_mean") is not None else "n/a"
        ops_med = f"{cand['ops_median']:.0f}" if cand.get("ops_median") is not None else "n/a"
        days_moy = f"{cand['days_mean']:.2f}" if cand.get("days_mean") is not None else "n/a"
        ticks_moy = f"{cand['ticks_mean']:.1f}" if cand.get("ticks_mean") is not None else "n/a"
        lines.append(
            f"| {cand['task']} | {cand['reason']} | {cand['count']} | {ops_moy} | {ops_med} | "
            f"{days_moy} | {ticks_moy} | {cand['ops_sum']} | {cand['days_sum']} | {cand['enjeu']} |"
        )
    lines.append("")

    return "\n".join(lines) + "\n"


def _selftest():
    tr = SchedIdleTracker()
    tr.on_selected("report", 10, 100)
    tr.note(False, "report_same_year", "pred")
    rec = tr.finish(10, 101, ops=12, days=0, ticks=1)
    assert rec["w"] == 0 and rec["r"] == "report_same_year"
    assert tr.by_task["report"]["selected"] == 1

    tr.on_selected("projects", 20, 200)
    tr.note(True, "projects_useful", "work", 1, "built")
    rec = tr.finish(20, 210, 100, 0, 10)
    assert rec["bg"] == 1

    tr.on_selected("expand", 21, 211)
    tr.note(False, "expand_no_work", "after")
    tr.finish(21, 212, 10, 0, 1)

    tr.on_selected("projects", 30, 300)
    tr.note(True, "projects_useful", "work", 1, "rail_search_started")
    rec = tr.finish(30, 301, 100, 0, 1)
    assert rec["bg"] == 1 and rec["gap_d"] == 10

    # Tests des distributions et proprietes mathematiques
    st = _stats([0, 0, 0, 100])
    assert st["mean"] == 25.0 and st["median"] == 0.0
    assert st["mean"] >= 0.5 * st["median"]
    assert st["median"] <= st["max"]

    st2 = _stats([10, 20, 30, 40, 50])
    assert st2["mean"] == 30.0 and st2["median"] == 30.0
    assert st2["mean"] >= 0.5 * st2["median"]

    log = (
        "OPEX 1970-1-5 SCHED_IDLE t=report w=0 r=report_same_year cls=pred op=12 d=0 tk=1 ad=-1 at=-1\n"
        "OPEX 1970-1-6 SCHED_IDLE t=catalog w=0 r=catalog_fresh cls=pred op=20 d=0 tk=1 ad=-1 at=-1\n"
        "OPEX 1970-1-7 SCHED_IDLE t=projects w=1 r=projects_useful cls=work op=2000 d=1 tk=10 ad=-1 at=-1 gap_d=-1 gap_tk=-1 bg=0 bgw=0\n"
        "OPEX 1970-2-10 SCHED_IDLE t=projects w=1 r=projects_useful cls=work op=1500 d=1 tk=8 ad=34 at=500 gap_d=34 gap_tk=500 bg=5 bgw=1\n"
    )
    parsed = parse_sched_idle_output(log)
    assert len(parsed["events"]) == 4
    assert parsed["events"][0]["t"] == "report"
    assert parsed["events"][0]["cls"] == "pred"
    assert parsed["events"][2]["cls"] == "work"
    print("selftest ok")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", help="JSON banc ou journaux bruts")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--json-out", help="Ecrire le resume JSON")
    args = parser.parse_args(argv)
    if args.selftest:
        _selftest()
        return 0
    if not args.inputs:
        parser.error("fournir des fichiers ou --selftest")
    chunks = []
    series = []
    for path in args.inputs:
        text = Path(path).read_text(encoding="utf-8")
        if path.endswith(".json"):
            data = json.loads(text)
            rows = data.get("series") or data.get("rows") or []
            if isinstance(data, list):
                rows = data
            for r in rows:
                series.append(r)
                chunks.append(r.get("openttd_output") or r.get("output") or "")
        else:
            chunks.append(text)
    parsed = parse_sched_idle_output("\n".join(chunks))
    summary = summarize_events(parsed["events"], seed_series=series)
    text = format_report(summary)
    sys.stdout.write(text)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
