#!/usr/bin/env python3
"""Lecteur de smoke diag_v233l.py pour analyser les journaux moteur arm_seedN_rN.log(.gz).

Rapporte par bras et par graine :
1. Lignes rail par cargo, et spécifiquement pour GOOD : distance, nombre de trains,
   double voie (V190 build_double) ou voie unique, replis fallback_single avec motif (TRK2FAIL, LOOPFAIL...).
2. ALERTE pour toute ligne en voie unique avec > 1 train, en croisant les événements
   d'ajout de train (V190 add_train, V284, renforts rail) et en citant les fichiers et lignes dans ai/OpexAI/*.nut.
3. Trains bloqués ou inutiles : données journalisées (LINE_REVENUE vehs/real_prof, profit
   véhicule nul ou négatif, attente wait_a). Champ absent = « non journalisé ».
4. Événements V233L_* s'ils existent (comptés par type, parsing clé=valeur).
5. Traces détaillées V233L :
   - Recherche de site (V233L_SITE, SITE_STEP, SITE_WAIT, SITE_PENDING, SITE_LIMIT, SITE_PLAN)
     par côté A/B : recherches, OK/budget/autres raisons, opcodes (médiane, max, cumul par paire), anneaux.
   - V233L_SITE_B_JOIN : tentatives, succès, échecs par raison, coût opcodes.
   - V233L_SITE_FUNNEL : parser tolérant, agrégats par raison et coût opcodes.
   - V233L_REJECT par raison.
6. Résumé comparatif lorsque deux journaux sont passés (référence et variante).
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
import os
from pathlib import Path
import re
import statistics
import sys
from typing import Any, Dict, List, Optional, Tuple


# Citations dans le code source OpexAI (fichier:ligne)
EVENT_CITATIONS = {
    'V190_build_double_builder': 'ai/OpexAI/builder_rail.nut:5752',
    'V190_build_double_task': 'ai/OpexAI/task_rail.nut:1281',
    'V190_fallback_single_broken': 'ai/OpexAI/builder_rail.nut:5658',
    'V190_fallback_single_rollback': 'ai/OpexAI/builder_rail.nut:5671',
    'V190_fallback_single_noplan': 'ai/OpexAI/builder_rail.nut:5682',
    'V190_fallback_single_task': 'ai/OpexAI/task_rail.nut:1286',
    'V190_add_train': 'ai/OpexAI/task_rail.nut:516',
    'RAIL_EXPAND_second_train': 'ai/OpexAI/task_rail.nut:395',
    'RAIL_EXPAND_clone': 'ai/OpexAI/task_rail.nut:517',
    'RAIL_EXPAND_double_track': 'ai/OpexAI/task_rail.nut:1377',
    'V284_done_train': 'ai/OpexAI/task_v284.nut:465',
}

RE_FILENAME = re.compile(
    r'(?:^|/)(?:(?P<policy>[\w\-]+)_)?(?P<arm>[a-zA-Z0-9_\-]+?)_seed(?P<seed>\d+)(?:_r(?P<repeat>\d+))?\.log(?:\.gz)?$'
)
RE_FIELDS = re.compile(r'(\w+)=([^\s]*)')
RE_V233L = re.compile(r'\b(V233L_[A-Z0-9_]+|SITE_FUNNEL)\b(?:\s+(.*))?')


def open_log_file(path: str | Path):
    path = Path(path)
    if path.suffix == '.gz':
        return gzip.open(path, 'rt', encoding='utf-8', errors='replace')
    return open(path, 'rt', encoding='utf-8', errors='replace')


def safe_int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    if isinstance(val, int):
        return val
    try:
        s = str(val).strip()
        if not s:
            return default
        return int(s)
    except (ValueError, TypeError):
        return default


def safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    try:
        s = str(val).strip()
        if not s:
            return default
        return float(s)
    except (ValueError, TypeError):
        return default


def parse_filename_meta(filename: str) -> Tuple[str, str, str]:
    """Extrait arm, seed, repeat d'un nom de fichier."""
    base = Path(filename).name
    # Strip extensions
    if base.endswith('.log.gz'):
        stem = base[:-7]
    elif base.endswith('.log'):
        stem = base[:-4]
    else:
        stem = base

    # Match _seed<digits>
    m_seed = re.search(r'_seed(\d+)', stem)
    if m_seed:
        seed = m_seed.group(1)
        arm = stem[:m_seed.start()]
        remainder = stem[m_seed.end():]
        m_r = re.search(r'_r(\d+)', remainder)
        repeat = m_r.group(1) if m_r else '0'
        return arm, seed, repeat

    return stem, 'unknown', '0'


def parse_kv_fields(text: str) -> Dict[str, str]:
    if not text:
        return {}
    return dict(RE_FIELDS.findall(text))


class DiagV233LLogParser:
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self.arm, self.seed, self.repeat = parse_filename_meta(str(self.filepath))

        # State
        self.lines: Dict[str, Dict[str, Any]] = {}
        self.pair_to_line: Dict[str, str] = {}  # "src->dst" -> line_id

        # Event counters
        self.v233l_events: Counter = Counter()
        self.v233l_details: List[Dict[str, Any]] = []

        # Vehicle level telemetry seen?
        self.has_vehicle_level_logs = False
        self.vehicle_records: List[Dict[str, Any]] = []

        # Detailed V233L tracking
        self.site_records: Dict[str, List[Dict[str, Any]]] = {'A': [], 'B': [], 'UNKNOWN': []}
        self.site_step_records: Dict[str, List[Dict[str, Any]]] = {'A': [], 'B': [], 'UNKNOWN': []}
        self.site_plans: Dict[str, List[Dict[str, Any]]] = {'A': [], 'B': [], 'UNKNOWN': []}
        self.site_waits: List[Dict[str, Any]] = []
        self.site_pendings: List[Dict[str, Any]] = []
        self.site_limits: List[Dict[str, Any]] = []

        self.site_b_join_records: List[Dict[str, Any]] = []
        self.site_funnel_records: List[Dict[str, Any]] = []
        self.v233l_rejects_by_reason: Counter = Counter()
        self.v233l_reject_records: List[Dict[str, Any]] = []

    def _ensure_line(self, line_id: str) -> Dict[str, Any]:
        if line_id not in self.lines:
            self.lines[line_id] = {
                'line_id': line_id,
                'cargo': 'UNKNOWN',
                'dist': None,
                'trains': 0,
                'wagons': None,
                'src': None,
                'dst': None,
                'double_track': False,
                'double_track_source': None,
                'fallback_single': None,
                'train_additions': [],
                'annual_revenues': [],
                'zero_or_negative_profit_years': [],
            }
        return self.lines[line_id]

    def parse(self) -> Dict[str, Any]:
        with open_log_file(self.filepath) as f:
            for raw_line in f:
                self._process_line(raw_line)
        return self.summarize()

    def _process_v233l_event(self, event_type: str, fields: Dict[str, str], date: str):
        if event_type == 'V233L_SITE':
            side = fields.get('side', 'UNKNOWN')
            src = fields.get('src')
            dst = fields.get('dst')
            pair = f"{src}->{dst}" if src and dst else 'UNKNOWN'
            reason = fields.get('reason', 'UNKNOWN')
            ops = safe_int(fields.get('ops'))
            ring = safe_int(fields.get('ring'))
            plans = safe_int(fields.get('plans'))
            length = safe_int(fields.get('length'))
            rec = {
                'side': side,
                'src': src,
                'dst': dst,
                'pair': pair,
                'reason': reason,
                'ops': ops,
                'ring': ring,
                'plans': plans,
                'length': length,
                'date': date,
                'fields': fields,
            }
            target = self.site_records.get(side, self.site_records['UNKNOWN'])
            target.append(rec)

        elif event_type == 'V233L_SITE_STEP':
            side = fields.get('side', 'UNKNOWN')
            src = fields.get('src')
            dst = fields.get('dst')
            pair = f"{src}->{dst}" if src and dst else 'UNKNOWN'
            station = fields.get('station', '')
            action = fields.get('action', '')
            reason = fields.get('reason', 'UNKNOWN')
            ops = safe_int(fields.get('ops'))
            total_ops = safe_int(fields.get('total_ops'))
            limit = safe_int(fields.get('limit'))
            slices = safe_int(fields.get('slices'))

            ring = 0
            if 'ring' in fields:
                ring = safe_int(fields['ring'])
            elif 'next' in fields:
                parts = fields['next'].split(':')
                ring = safe_int(parts[0])

            rec = {
                'side': side,
                'src': src,
                'dst': dst,
                'pair': pair,
                'station': station,
                'action': action,
                'reason': reason,
                'ops': ops,
                'total_ops': total_ops,
                'limit': limit,
                'slices': slices,
                'ring': ring,
                'date': date,
                'fields': fields,
            }
            target = self.site_step_records.get(side, self.site_step_records['UNKNOWN'])
            target.append(rec)

        elif event_type == 'V233L_SITE_WAIT':
            src = fields.get('src')
            dst = fields.get('dst')
            pair = f"{src}->{dst}" if src and dst else 'UNKNOWN'
            reason = fields.get('reason', 'SITE_PENDING')
            site_a = fields.get('site_a', '')
            site_b = fields.get('site_b', '')
            phase = fields.get('phase', '')
            rec = {
                'src': src,
                'dst': dst,
                'pair': pair,
                'reason': reason,
                'site_a': site_a,
                'site_b': site_b,
                'phase': phase,
                'date': date,
                'fields': fields,
            }
            self.site_waits.append(rec)
            if reason == 'SITE_PENDING' or 'PENDING' in reason:
                self.site_pendings.append(rec)

        elif event_type == 'V233L_SITE_PENDING':
            src = fields.get('src')
            dst = fields.get('dst')
            pair = f"{src}->{dst}" if src and dst else 'UNKNOWN'
            rec = {
                'src': src,
                'dst': dst,
                'pair': pair,
                'date': date,
                'fields': fields,
            }
            self.site_pendings.append(rec)

        elif event_type == 'V233L_SITE_LIMIT':
            src = fields.get('src')
            dst = fields.get('dst')
            pair = f"{src}->{dst}" if src and dst else 'UNKNOWN'
            rec = {
                'src': src,
                'dst': dst,
                'pair': pair,
                'date': date,
                'fields': fields,
            }
            self.site_limits.append(rec)

        elif event_type == 'V233L_SITE_PLAN':
            side = fields.get('side', 'UNKNOWN')
            src = fields.get('src')
            dst = fields.get('dst')
            pair = f"{src}->{dst}" if src and dst else 'UNKNOWN'
            anchor = safe_int(fields.get('anchor'))
            length = safe_int(fields.get('length'))
            cargo_value = safe_int(fields.get('cargo_value'))
            rec = {
                'side': side,
                'src': src,
                'dst': dst,
                'pair': pair,
                'anchor': anchor,
                'length': length,
                'cargo_value': cargo_value,
                'date': date,
                'fields': fields,
            }
            target = self.site_plans.get(side, self.site_plans['UNKNOWN'])
            target.append(rec)

        elif event_type == 'V233L_SITE_B_JOIN':
            src = fields.get('src')
            dst = fields.get('dst')
            pair = f"{src}->{dst}" if src and dst else 'UNKNOWN'
            phase = fields.get('phase', '')
            station = fields.get('station', '')
            reason = fields.get('reason', 'UNKNOWN')
            ok_raw = fields.get('ok', '0')
            ok = (ok_raw in ('1', 'true', 'True') or reason == 'OK')
            ops = safe_int(fields.get('ops'))
            scan_ops = safe_int(fields.get('scan_ops'))
            rec = {
                'src': src,
                'dst': dst,
                'pair': pair,
                'phase': phase,
                'station': station,
                'ok': ok,
                'reason': reason,
                'ops': ops,
                'scan_ops': scan_ops,
                'date': date,
                'fields': fields,
            }
            self.site_b_join_records.append(rec)

        elif event_type in ('V233L_SITE_FUNNEL', 'SITE_FUNNEL'):
            # Tolerant parsing:
            town = safe_int(fields['town']) if 'town' in fields and fields['town'] else None
            axis = safe_int(fields['axis']) if 'axis' in fields and fields['axis'] else None
            radius = safe_int(fields['radius']) if 'radius' in fields and fields['radius'] else None
            tiles = safe_int(fields['tiles']) if 'tiles' in fields and fields['tiles'] else None
            buildable = safe_int(fields['buildable']) if 'buildable' in fields and fields['buildable'] else None
            accepting = safe_int(fields['accepting']) if 'accepting' in fields and fields['accepting'] else None
            checked = safe_int(fields['checked']) if 'checked' in fields and fields['checked'] else None
            ok_raw = fields.get('ok', '0')
            ok = ok_raw in ('1', 'true', 'True', 'OK', 'ok')
            ops = safe_int(fields.get('ops', 0))
            reason = fields.get('reason', 'UNKNOWN') or 'UNKNOWN'
            rec = {
                'town': town,
                'axis': axis,
                'radius': radius,
                'tiles': tiles,
                'buildable': buildable,
                'accepting': accepting,
                'checked': checked,
                'ok': ok,
                'ops': ops,
                'reason': reason,
                'date': date,
                'fields': fields,
            }
            self.site_funnel_records.append(rec)

        elif event_type == 'V233L_REJECT':
            reason = fields.get('reason', 'UNKNOWN')
            self.v233l_rejects_by_reason[reason] += 1
            rec = {
                'reason': reason,
                'fields': fields,
                'date': date,
            }
            self.v233l_reject_records.append(rec)
            if reason == 'SITE_PENDING':
                self.site_pendings.append(rec)
            elif reason == 'SITE_LIMIT':
                self.site_limits.append(rec)

    def _process_line(self, raw_line: str):
        # Extract date if present
        date_m = re.search(r'OPEX\s+(\d{4}-\d+-\d+)', raw_line)
        date = date_m.group(1) if date_m else ''

        # 1. Look for V233L events anywhere
        m_v233l = RE_V233L.search(raw_line)
        if m_v233l:
            event_type = m_v233l.group(1)
            raw_fields = m_v233l.group(2) or ''
            fields = parse_kv_fields(raw_fields)
            self.v233l_events[event_type] += 1
            self.v233l_details.append({
                'event': event_type,
                'fields': fields,
                'raw': raw_line.strip()
            })
            self._process_v233l_event(event_type, fields, date)

        # 2. Extract OPEX events (usually logged by [0])
        if 'OPEX ' not in raw_line and 'LINE_REVENUE' not in raw_line and 'RAIL_BUILD' not in raw_line and 'V190' not in raw_line:
            return

        date_m_full = re.search(r'OPEX\s+(\d{4}-\d+-\d+)\s+([A-Z0-9_]+)\s*(.*)', raw_line)
        if not date_m_full:
            return

        date = date_m_full.group(1)
        event = date_m_full.group(2)
        body = date_m_full.group(3)
        fields = parse_kv_fields(body)

        # 3. Handle RAIL_BUILD
        if event == 'RAIL_BUILD':
            line_id = fields.get('line')
            if line_id:
                line_data = self._ensure_line(line_id)
                line_data['cargo'] = fields.get('cargo', line_data['cargo'])
                if 'dist' in fields:
                    line_data['dist'] = int(fields['dist'])
                if 'trains' in fields:
                    line_data['trains'] = max(line_data['trains'], int(fields['trains']))
                if 'wagons' in fields:
                    line_data['wagons'] = int(fields['wagons'])
                if 'src' in fields:
                    line_data['src'] = fields['src']
                if 'dst' in fields:
                    line_data['dst'] = fields['dst']
                if line_data['src'] and line_data['dst']:
                    pair = f"{line_data['src']}->{line_data['dst']}"
                    self.pair_to_line[pair] = line_id

        # 4. Handle V190 events
        elif event == 'V190':
            action = fields.get('action')
            line_ref = fields.get('line', '')
            trains_val = int(fields.get('trains', 0)) if 'trains' in fields else 0

            # Resolve line_id
            line_id = None
            if line_ref in self.lines:
                line_id = line_ref
            elif line_ref in self.pair_to_line:
                line_id = self.pair_to_line[line_ref]
            elif '->' in line_ref:
                line_id = line_ref

            if action == 'build_double':
                citation = EVENT_CITATIONS['V190_build_double_task'] if '->' not in line_ref else EVENT_CITATIONS['V190_build_double_builder']
                line_data = self._ensure_line(line_id or line_ref)
                line_data['double_track'] = True
                line_data['double_track_source'] = f"V190 build_double ({citation})"
                if trains_val > 0:
                    line_data['trains'] = max(line_data['trains'], trains_val)

            elif action == 'fallback_single':
                reason = fields.get('reason', 'UNKNOWN')
                step = fields.get('step', '-')
                skip = fields.get('skip', '-')
                citation = EVENT_CITATIONS['V190_fallback_single_task'] if '->' not in line_ref else EVENT_CITATIONS['V190_fallback_single_broken']
                line_data = self._ensure_line(line_id or line_ref)
                line_data['double_track'] = False
                line_data['fallback_single'] = {
                    'reason': reason,
                    'step': step,
                    'skip': skip,
                    'citation': citation,
                    'date': date
                }
                if trains_val > 0:
                    line_data['trains'] = max(line_data['trains'], trains_val)

            elif action == 'add_train':
                citation = EVENT_CITATIONS['V190_add_train']
                line_data = self._ensure_line(line_id or line_ref)
                if trains_val > 0:
                    line_data['trains'] = max(line_data['trains'], trains_val)
                line_data['train_additions'].append({
                    'action': 'V190 add_train',
                    'trains': line_data['trains'],
                    'date': date,
                    'citation': citation,
                    'fields': fields
                })

        # 5. Handle RAIL_EXPAND
        elif event == 'RAIL_EXPAND':
            action = fields.get('action')
            line_id = fields.get('line')
            if line_id:
                line_data = self._ensure_line(line_id)
                trains_val = int(fields.get('trains', 0)) if 'trains' in fields else 0
                if action == 'second_train':
                    citation = EVENT_CITATIONS['RAIL_EXPAND_second_train']
                    if trains_val > 0:
                        line_data['trains'] = max(line_data['trains'], trains_val)
                    line_data['train_additions'].append({
                        'action': 'RAIL_EXPAND second_train',
                        'trains': line_data['trains'],
                        'date': date,
                        'citation': citation,
                        'fields': fields
                    })
                elif action == 'clone':
                    citation = EVENT_CITATIONS['RAIL_EXPAND_clone']
                    if trains_val > 0:
                        line_data['trains'] = max(line_data['trains'], trains_val)
                    line_data['train_additions'].append({
                        'action': 'RAIL_EXPAND clone',
                        'trains': line_data['trains'],
                        'date': date,
                        'citation': citation,
                        'fields': fields
                    })
                elif action == 'double_track':
                    citation = EVENT_CITATIONS['RAIL_EXPAND_double_track']
                    ok = fields.get('ok') == '1'
                    if ok:
                        line_data['double_track'] = True
                        line_data['double_track_source'] = f"RAIL_EXPAND double_track ({citation})"
                        line_data['train_additions'].append({
                            'action': 'RAIL_EXPAND double_track (upgrade)',
                            'trains': line_data['trains'],
                            'date': date,
                            'citation': citation,
                            'fields': fields
                        })

        # 6. Handle V284
        elif event == 'V284':
            action = fields.get('action')
            line_id = fields.get('line')
            if action == 'done' and line_id:
                line_data = self._ensure_line(line_id)
                kind = fields.get('kind')
                if kind == 'train':
                    citation = EVENT_CITATIONS['V284_done_train']
                    trains_val = int(fields.get('trains', 0)) if 'trains' in fields else (line_data['trains'] + 1)
                    line_data['trains'] = max(line_data['trains'], trains_val)
                    line_data['train_additions'].append({
                        'action': 'V284 done (train)',
                        'trains': line_data['trains'],
                        'date': date,
                        'citation': citation,
                        'fields': fields
                    })

        # 7. Handle LINE_REVENUE
        elif event == 'LINE_REVENUE':
            line_id = fields.get('line')
            mode = fields.get('mode')
            if line_id and mode == 'rail':
                line_data = self._ensure_line(line_id)
                line_data['cargo'] = fields.get('cargo', line_data['cargo'])
                if 'dist' in fields and line_data['dist'] is None:
                    try:
                        line_data['dist'] = int(fields['dist'])
                    except ValueError:
                        pass

                vehs = int(fields.get('vehs', 0)) if 'vehs' in fields else 0
                if vehs > 0:
                    line_data['trains'] = max(line_data['trains'], vehs)

                if fields.get('double') == '1':
                    line_data['double_track'] = True
                    if not line_data['double_track_source']:
                        line_data['double_track_source'] = 'LINE_REVENUE double=1'

                year = fields.get('year', date[:4])
                real_prof_str = fields.get('real_prof')
                real_prof = float(real_prof_str) if real_prof_str is not None else None

                wait_a = fields.get('wait_a')

                rev_entry = {
                    'year': year,
                    'vehs': vehs,
                    'real_prof': real_prof,
                    'wait_a': wait_a if wait_a is not None else 'non journalisé',
                    'raw_fields': fields
                }
                line_data['annual_revenues'].append(rev_entry)

                if vehs >= 1 and real_prof is not None and real_prof <= 0.0:
                    line_data['zero_or_negative_profit_years'].append(rev_entry)

        # 8. Check for vehicle level telemetry (e.g. C54)
        elif event == 'C54' or 'phase=vehicle' in raw_line:
            self.has_vehicle_level_logs = True
            vid = fields.get('vid')
            prof_last = fields.get('profit_last')
            prof_this = fields.get('profit_this')
            in_depot = fields.get('in_depot')
            line_id = fields.get('line')
            self.vehicle_records.append({
                'vid': vid,
                'line': line_id,
                'profit_last': float(prof_last) if prof_last is not None else None,
                'profit_this': float(prof_this) if prof_this is not None else None,
                'in_depot': in_depot == '1' if in_depot is not None else False,
                'date': date
            })

    def summarize(self) -> Dict[str, Any]:
        # Merge pair_to_line entries if any "src->dst" keys exist in self.lines
        unresolved = [k for k in self.lines.keys() if '->' in k]
        for pair_key in unresolved:
            data = self.lines.pop(pair_key)
            target_id = self.pair_to_line.get(pair_key)
            if target_id and target_id in self.lines:
                target = self.lines[target_id]
                if data['double_track']:
                    target['double_track'] = True
                    target['double_track_source'] = data['double_track_source']
                if data['fallback_single']:
                    target['fallback_single'] = data['fallback_single']
                if data['trains'] > target['trains']:
                    target['trains'] = data['trains']
                target['train_additions'].extend(data['train_additions'])

        # Aggregate rail lines by cargo
        lines_by_cargo: Dict[str, int] = defaultdict(int)
        for l in self.lines.values():
            cargo = l['cargo']
            lines_by_cargo[cargo] += 1

        # GOOD rail lines detail
        good_lines = []
        for lid, l in sorted(self.lines.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
            if l['cargo'] == 'GOOD':
                good_lines.append({
                    'line_id': lid,
                    'dist': l['dist'],
                    'trains': l['trains'],
                    'double_track': l['double_track'],
                    'double_track_source': l['double_track_source'],
                    'fallback_single': l['fallback_single'],
                })

        # ALERT: Single track with > 1 train
        alerts = []
        for lid, l in sorted(self.lines.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
            if (not l['double_track']) and l['trains'] > 1:
                alerts.append({
                    'line_id': lid,
                    'cargo': l['cargo'],
                    'dist': l['dist'],
                    'trains': l['trains'],
                    'train_additions': l['train_additions'],
                    'fallback_single': l['fallback_single'],
                })

        # Blocked or useless trains
        blocked_lines = []
        for lid, l in sorted(self.lines.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
            if l['zero_or_negative_profit_years']:
                blocked_lines.append({
                    'line_id': lid,
                    'cargo': l['cargo'],
                    'trains': l['trains'],
                    'unprofitable_years': l['zero_or_negative_profit_years']
                })

        # Vehicle level summary
        vehicle_blocked = []
        if self.has_vehicle_level_logs:
            for vr in self.vehicle_records:
                if (vr['profit_last'] is not None and vr['profit_last'] <= 0) or vr['in_depot']:
                    vehicle_blocked.append(vr)
            vehicle_status = {
                'available': True,
                'blocked_or_idle_vehicles': vehicle_blocked
            }
        else:
            vehicle_status = {
                'available': False,
                'status': 'non journalisé'
            }

        # --- Detailed V233L Site Searches Summary ---
        site_search = {}
        all_search_ops = []
        pairs_cumul_total = defaultdict(int)

        for side in ('A', 'B'):
            records = self.site_records[side] if self.site_records[side] else self.site_step_records[side]
            searches_count = len(records)
            reasons_counter = Counter(r['reason'] for r in records)
            ok_count = reasons_counter.get('OK', 0)
            budget_count = reasons_counter.get('budget', 0)
            other_reasons = {k: v for k, v in reasons_counter.items() if k not in ('OK', 'budget')}
            other_reasons_count = sum(other_reasons.values())

            ops_list = [r['ops'] for r in records if 'ops' in r]
            all_search_ops.extend(ops_list)
            ops_median = float(statistics.median(ops_list)) if ops_list else 0.0
            ops_max = max(ops_list) if ops_list else 0
            ops_min = min(ops_list) if ops_list else 0
            ops_sum = sum(ops_list)

            by_pair = defaultdict(int)
            for r in records:
                p = r.get('pair') or (f"{r.get('src')}->{r.get('dst')}" if r.get('src') and r.get('dst') else 'UNKNOWN')
                op_val = r.get('ops', 0)
                by_pair[p] += op_val
                pairs_cumul_total[p] += op_val

            rings_list = [r['ring'] for r in records if r.get('ring') is not None and r.get('ring') > 0]
            rings_min = min(rings_list) if rings_list else 0
            rings_max = max(rings_list) if rings_list else 0
            rings_counts = dict(Counter(rings_list))

            plans_count = len(self.site_plans[side]) if self.site_plans[side] else sum(r.get('plans', 0) for r in records)
            step_count = len(self.site_step_records[side])
            wait_count = sum(1 for w in self.site_waits if w.get('site_' + side.lower()) in ('budget', 'OK'))

            site_search[side] = {
                'searches': searches_count,
                'reasons': dict(reasons_counter),
                'ok_count': ok_count,
                'budget_count': budget_count,
                'other_reasons': other_reasons,
                'other_reasons_count': other_reasons_count,
                'opcodes': {
                    'median': ops_median,
                    'max': ops_max,
                    'min': ops_min,
                    'sum': ops_sum,
                    'cumul_par_paire': dict(by_pair),
                },
                'rings': {
                    'min': rings_min,
                    'max': rings_max,
                    'counts': rings_counts,
                },
                'plans_count': plans_count,
                'step_count': step_count,
                'wait_count': wait_count,
            }

        site_search['total'] = {
            'searches': site_search['A']['searches'] + site_search['B']['searches'],
            'opcodes': {
                'median': float(statistics.median(all_search_ops)) if all_search_ops else 0.0,
                'max': max(all_search_ops) if all_search_ops else 0,
                'min': min(all_search_ops) if all_search_ops else 0,
                'sum': sum(all_search_ops),
                'cumul_par_paire': dict(pairs_cumul_total),
            },
        }

        # --- V233L_SITE_B_JOIN Summary ---
        join_attempts = len(self.site_b_join_records)
        join_successes = sum(1 for r in self.site_b_join_records if r['ok'])
        join_failures = join_attempts - join_successes
        join_failures_by_reason = dict(Counter(r['reason'] for r in self.site_b_join_records if not r['ok']))
        join_reasons = dict(Counter(r['reason'] for r in self.site_b_join_records))
        join_ops_list = [r['ops'] for r in self.site_b_join_records]
        join_scan_ops_list = [r['scan_ops'] for r in self.site_b_join_records if r.get('scan_ops')]

        site_b_join = {
            'attempts': join_attempts,
            'successes': join_successes,
            'failures': join_failures,
            'failures_by_reason': join_failures_by_reason,
            'reasons': join_reasons,
            'cost': {
                'total_ops': sum(join_ops_list),
                'median_ops': float(statistics.median(join_ops_list)) if join_ops_list else 0.0,
                'max_ops': max(join_ops_list) if join_ops_list else 0,
                'min_ops': min(join_ops_list) if join_ops_list else 0,
                'total_scan_ops': sum(join_scan_ops_list),
            }
        }

        # --- V233L_SITE_FUNNEL Summary ---
        funnel_count = len(self.site_funnel_records)
        funnel_ok = sum(1 for r in self.site_funnel_records if r['ok'])
        funnel_fail = funnel_count - funnel_ok
        funnel_reasons = dict(Counter(r['reason'] for r in self.site_funnel_records))
        funnel_ops_list = [r['ops'] for r in self.site_funnel_records if r.get('ops') is not None]

        cost_by_reason = {}
        reason_groups = defaultdict(list)
        for r in self.site_funnel_records:
            reason_groups[r['reason']].append(r['ops'])

        for r_name, ops_group in sorted(reason_groups.items()):
            cost_by_reason[r_name] = {
                'count': len(ops_group),
                'total_ops': sum(ops_group),
                'median_ops': float(statistics.median(ops_group)) if ops_group else 0.0,
                'mean_ops': round(sum(ops_group) / len(ops_group), 1) if ops_group else 0.0,
                'max_ops': max(ops_group) if ops_group else 0,
            }

        site_funnel = {
            'count': funnel_count,
            'successes': funnel_ok,
            'failures': funnel_fail,
            'by_reason': funnel_reasons,
            'cost': {
                'total_ops': sum(funnel_ops_list),
                'median_ops': float(statistics.median(funnel_ops_list)) if funnel_ops_list else 0.0,
                'max_ops': max(funnel_ops_list) if funnel_ops_list else 0,
                'min_ops': min(funnel_ops_list) if funnel_ops_list else 0,
            },
            'cost_by_reason': cost_by_reason,
            'aggregates': {
                'total_tiles': sum(r['tiles'] for r in self.site_funnel_records if r.get('tiles') is not None),
                'total_buildable': sum(r['buildable'] for r in self.site_funnel_records if r.get('buildable') is not None),
                'total_accepting': sum(r['accepting'] for r in self.site_funnel_records if r.get('accepting') is not None),
                'total_checked': sum(r['checked'] for r in self.site_funnel_records if r.get('checked') is not None),
            }
        }

        # --- V233L_REJECT Summary ---
        v233l_rejects = {
            'by_reason': dict(self.v233l_rejects_by_reason),
            'total': sum(self.v233l_rejects_by_reason.values()),
        }

        # Events breakdown for SITE family
        site_events_summary = {
            'V233L_SITE': self.v233l_events['V233L_SITE'],
            'V233L_SITE_STEP': self.v233l_events['V233L_SITE_STEP'],
            'V233L_SITE_WAIT': len(self.site_waits) or self.v233l_events['V233L_SITE_WAIT'],
            'V233L_SITE_PENDING': len(self.site_pendings) or self.v233l_events['V233L_SITE_PENDING'],
            'V233L_SITE_LIMIT': len(self.site_limits) or self.v233l_events['V233L_SITE_LIMIT'],
            'V233L_SITE_PLAN': self.v233l_events['V233L_SITE_PLAN'],
            'V233L_SITE_B_JOIN': len(self.site_b_join_records),
            'V233L_SITE_FUNNEL': len(self.site_funnel_records),
        }

        return {
            'arm': self.arm,
            'seed': self.seed,
            'repeat': self.repeat,
            'filepath': str(self.filepath),
            'rail_lines_total': len(self.lines),
            'lines_by_cargo': dict(lines_by_cargo),
            'good_lines': good_lines,
            'single_track_multi_train_alerts': alerts,
            'blocked_lines': blocked_lines,
            'vehicle_level_telemetry': vehicle_status,
            'v233l_events_count': dict(self.v233l_events),
            'v233l_events_total': sum(self.v233l_events.values()),
            'site_search': site_search,
            'site_b_join': site_b_join,
            'site_funnel': site_funnel,
            'v233l_rejects': v233l_rejects,
            'site_events_summary': site_events_summary,
        }


def compare_summaries(ref: Dict[str, Any], var: Dict[str, Any]) -> Dict[str, Any]:
    """Calcule le résumé comparatif entre deux journaux (référence et variante)."""
    # 1. Sites B trouvés
    ref_b_search_ok = ref.get('site_search', {}).get('B', {}).get('ok_count', 0)
    var_b_search_ok = var.get('site_search', {}).get('B', {}).get('ok_count', 0)
    ref_b_join_ok = ref.get('site_b_join', {}).get('successes', 0)
    var_b_join_ok = var.get('site_b_join', {}).get('successes', 0)

    ref_b_total = ref_b_search_ok + ref_b_join_ok
    var_b_total = var_b_search_ok + var_b_join_ok
    delta_b_total = var_b_total - ref_b_total

    # 2. Opcodes de recherche
    ref_ops_a = ref.get('site_search', {}).get('A', {}).get('opcodes', {}).get('sum', 0)
    var_ops_a = var.get('site_search', {}).get('A', {}).get('opcodes', {}).get('sum', 0)
    ref_ops_b = ref.get('site_search', {}).get('B', {}).get('opcodes', {}).get('sum', 0)
    var_ops_b = var.get('site_search', {}).get('B', {}).get('opcodes', {}).get('sum', 0)
    ref_ops_tot = ref_ops_a + ref_ops_b
    var_ops_tot = var_ops_a + var_ops_b

    # 3. Lignes rail GOOD posées
    ref_good = ref.get('good_lines', [])
    var_good = var.get('good_lines', [])
    ref_dt = sum(1 for l in ref_good if l.get('double_track'))
    var_dt = sum(1 for l in var_good if l.get('double_track'))

    # 4. V233L_REJECT par raison
    ref_rejects = ref.get('v233l_rejects', {}).get('by_reason', {})
    var_rejects = var.get('v233l_rejects', {}).get('by_reason', {})
    all_reasons = sorted(list(set(ref_rejects.keys()) | set(var_rejects.keys())))

    reject_comparison = {}
    for r in all_reasons:
        rc = ref_rejects.get(r, 0)
        vc = var_rejects.get(r, 0)
        reject_comparison[r] = {
            'reference': rc,
            'variant': vc,
            'delta': vc - rc,
        }

    ref_tot_rej = sum(ref_rejects.values())
    var_tot_rej = sum(var_rejects.values())

    return {
        'reference': {
            'filepath': ref.get('filepath', ''),
            'arm': ref.get('arm', 'reference'),
            'seed': ref.get('seed', 'unknown'),
            'repeat': ref.get('repeat', '0'),
        },
        'variant': {
            'filepath': var.get('filepath', ''),
            'arm': var.get('arm', 'variant'),
            'seed': var.get('seed', 'unknown'),
            'repeat': var.get('repeat', '0'),
        },
        'sites_b_found': {
            'reference': ref_b_total,
            'variant': var_b_total,
            'delta': delta_b_total,
            'ref_search_ok': ref_b_search_ok,
            'var_search_ok': var_b_search_ok,
            'ref_join_ok': ref_b_join_ok,
            'var_join_ok': var_b_join_ok,
        },
        'search_opcodes': {
            'side_a': {
                'reference': ref_ops_a,
                'variant': var_ops_a,
                'delta': var_ops_a - ref_ops_a,
            },
            'side_b': {
                'reference': ref_ops_b,
                'variant': var_ops_b,
                'delta': var_ops_b - ref_ops_b,
            },
            'total': {
                'reference': ref_ops_tot,
                'variant': var_ops_tot,
                'delta': var_ops_tot - ref_ops_tot,
            },
        },
        'good_lines': {
            'count': {
                'reference': len(ref_good),
                'variant': len(var_good),
                'delta': len(var_good) - len(ref_good),
            },
            'double_track_count': {
                'reference': ref_dt,
                'variant': var_dt,
                'delta': var_dt - ref_dt,
            },
            'reference_lines': [
                {'line_id': l['line_id'], 'dist': l['dist'], 'trains': l['trains'], 'double_track': l['double_track']}
                for l in ref_good
            ],
            'variant_lines': [
                {'line_id': l['line_id'], 'dist': l['dist'], 'trains': l['trains'], 'double_track': l['double_track']}
                for l in var_good
            ],
        },
        'v233l_reject_by_reason': {
            'by_reason': reject_comparison,
            'total': {
                'reference': ref_tot_rej,
                'variant': var_tot_rej,
                'delta': var_tot_rej - ref_tot_rej,
            },
        },
    }


def format_report_text(summary: Dict[str, Any]) -> str:
    lines = []
    header = f"=== Rapport Smoke Diag V233L : Bras {summary['arm']} | Graine {summary['seed']} (r{summary['repeat']}) ==="
    lines.append(header)
    lines.append(f"Fichier : {summary['filepath']}")
    lines.append("")

    # 1. Rail lines by cargo
    lines.append("1. Lignes rail par cargo :")
    lines_by_cargo = summary.get('lines_by_cargo', {})
    if not lines_by_cargo:
        lines.append("   (aucune ligne rail détectée)")
    else:
        for cargo, count in sorted(lines_by_cargo.items()):
            lines.append(f"   - {cargo:6s} : {count} ligne(s)")
    lines.append("")

    # GOOD lines detail
    lines.append("   Détail des lignes rail GOOD :")
    good_lines = summary.get('good_lines', [])
    if not good_lines:
        lines.append("   (aucune ligne rail GOOD)")
    else:
        for gl in good_lines:
            track_str = "DOUBLE VOIE" if gl['double_track'] else "VOIE UNIQUE"
            dist_str = f"{gl['dist']} tuiles" if gl['dist'] is not None else "dist non journalisée"
            fb_str = ""
            if gl['fallback_single']:
                fb = gl['fallback_single']
                fb_str = f" [Repli fallback_single: reason={fb['reason']}, step={fb['step']}, skip={fb['skip']} | {fb['citation']}]"
            lines.append(f"   * Ligne {gl['line_id']} : {dist_str}, {gl['trains']} train(s), {track_str}{fb_str}")
    lines.append("")

    # 2. Alerts: Single track > 1 train
    lines.append("2. Alertes voie unique > 1 train :")
    alerts = summary.get('single_track_multi_train_alerts', [])
    if not alerts:
        lines.append("   [OK] Aucune ligne en voie unique avec plusieurs trains.")
    else:
        for al in alerts:
            dist_str = f"{al['dist']} tuiles" if al['dist'] is not None else "dist=inconnue"
            lines.append(f"   [ALERTE] Ligne {al['line_id']} (cargo={al['cargo']}, {dist_str}) : VOIE UNIQUE avec {al['trains']} trains !")
            if al['fallback_single']:
                fb = al['fallback_single']
                lines.append(f"     Origine du repli : reason={fb['reason']} step={fb['step']} skip={fb['skip']} (source: {fb['citation']})")
            if al['train_additions']:
                lines.append("     Événements d'ajout de train identifiés :")
                for ev in al['train_additions']:
                    lines.append(f"       - Date {ev['date']} : {ev['action']} -> {ev['trains']} trains (référence code : {ev['citation']})")
            else:
                lines.append("     (aucun événement d'ajout explicite trouvé ; nombre de trains issu de RAIL_BUILD / LINE_REVENUE)")
    lines.append("")

    # 3. Blocked / useless trains
    lines.append("3. Trains bloqués ou inutiles :")
    blocked = summary.get('blocked_lines', [])
    if not blocked:
        lines.append("   [OK] Aucun train/ligne avec profit annuel nul ou négatif détecté dans LINE_REVENUE.")
    else:
        for bl in blocked:
            lines.append(f"   * Ligne {bl['line_id']} ({bl['cargo']}, {bl['trains']} trains) : profit nul ou négatif :")
            for entry in bl['unprofitable_years']:
                wait_val = entry['wait_a']
                wait_str = f"{wait_val} t" if wait_val != 'non journalisé' else 'non journalisé'
                lines.append(f"       - Année {entry['year']} : {entry['vehs']} véh., real_prof = {entry['real_prof']:.1f} £, attente (wait_a) = {wait_str}")

    v_tel = summary.get('vehicle_level_telemetry', {})
    if not v_tel.get('available'):
        lines.append("   * Statut individuel par véhicule (vid, profit individuel, au dépôt) : non journalisé")
    else:
        lines.append(f"   * Véhicules individuels bloqués/dépôt : {len(v_tel.get('blocked_or_idle_vehicles', []))} véhicule(s)")
    lines.append("")

    # 4. V233L_* events
    lines.append("4. Événements V233L_* :")
    v233l_counts = summary.get('v233l_events_count', {})
    if not v233l_counts:
        lines.append("   (aucun événement V233L_* journalisé)")
    else:
        for ev_name, count in sorted(v233l_counts.items()):
            lines.append(f"   - {ev_name} : {count}")
    lines.append("")

    # 5. Recherche de site V233L (SITE, SITE_STEP, SITE_WAIT...)
    lines.append("5. Recherche de site V233L (A/B) :")
    site_search = summary.get('site_search', {})
    for side in ('A', 'B'):
        sdata = site_search.get(side, {})
        searches = sdata.get('searches', 0)
        lines.append(f"   - Côté {side} : {searches} recherche(s)")
        if searches > 0:
            reasons = sdata.get('reasons', {})
            reasons_str = ", ".join(f"{k}={v}" for k, v in sorted(reasons.items()))
            lines.append(f"     * Motifs : {reasons_str}")
            opcodes = sdata.get('opcodes', {})
            lines.append(f"     * Opcodes : médiane = {opcodes.get('median', 0):.0f} ops, max = {opcodes.get('max', 0)} ops, total = {opcodes.get('sum', 0)} ops")
            rings = sdata.get('rings', {})
            rings_counts = rings.get('counts', {})
            rc_str = ", ".join(f"anneau {k}: {v}" for k, v in sorted(rings_counts.items())) if rings_counts else "aucun"
            lines.append(f"     * Anneaux atteints : min = {rings.get('min', 0)}, max = {rings.get('max', 0)} ({rc_str})")
            by_pair = opcodes.get('cumul_par_paire', {})
            if by_pair:
                sorted_pairs = sorted(by_pair.items(), key=lambda x: x[1], reverse=True)
                top_pairs = sorted_pairs[:5]
                pairs_str = ", ".join(f"{p}: {ops} ops" for p, ops in top_pairs)
                if len(sorted_pairs) > 5:
                    pairs_str += f", ... (+ {len(sorted_pairs) - 5} paires)"
                lines.append(f"     * Cumul par paire : {pairs_str}")

    tot_data = site_search.get('total', {})
    tot_ops = tot_data.get('opcodes', {}).get('sum', 0)
    lines.append(f"   * Total recherche : {tot_data.get('searches', 0)} recherches, {tot_ops} opcodes cumulés")
    site_evs = summary.get('site_events_summary', {})
    evs_list = [f"{k}={v}" for k, v in sorted(site_evs.items()) if v > 0]
    if evs_list:
        lines.append(f"   * Événements associés : {', '.join(evs_list)}")
    lines.append("")

    # 6. Jointure de site B (V233L_SITE_B_JOIN)
    lines.append("6. Jointure de site B (V233L_SITE_B_JOIN) :")
    join_data = summary.get('site_b_join', {})
    join_attempts = join_data.get('attempts', 0)
    if join_attempts == 0:
        lines.append("   (aucun événement V233L_SITE_B_JOIN journalisé)")
    else:
        lines.append(f"   - Tentatives : {join_attempts} (succès : {join_data.get('successes', 0)}, échecs : {join_data.get('failures', 0)})")
        fail_reasons = join_data.get('failures_by_reason', {})
        if fail_reasons:
            lines.append("   - Échecs par raison :")
            for rk, rv in sorted(fail_reasons.items()):
                lines.append(f"     * {rk} : {rv}")
        cost = join_data.get('cost', {})
        lines.append(f"   - Coût opcodes : total = {cost.get('total_ops', 0)} ops, médiane = {cost.get('median_ops', 0):.0f} ops, max = {cost.get('max_ops', 0)} ops (scan_ops cumulé = {cost.get('total_scan_ops', 0)} ops)")
    lines.append("")

    # 7. Entonnoir de site (V233L_SITE_FUNNEL)
    lines.append("7. Entonnoir de site (V233L_SITE_FUNNEL) :")
    funnel_data = summary.get('site_funnel', {})
    funnel_count = funnel_data.get('count', 0)
    if funnel_count == 0:
        lines.append("   (aucun événement V233L_SITE_FUNNEL journalisé)")
    else:
        lines.append(f"   - Événements : {funnel_count} (succès : {funnel_data.get('successes', 0)}, échecs : {funnel_data.get('failures', 0)})")
        cost_by_reason = funnel_data.get('cost_by_reason', {})
        if cost_by_reason:
            lines.append("   - Agrégats par motif et coût :")
            for rk, rinfo in sorted(cost_by_reason.items()):
                lines.append(f"     * {rk:16s} : {rinfo['count']:3d} occ. | ops total = {rinfo['total_ops']:6d}, moy = {rinfo['mean_ops']:.0f}, max = {rinfo['max_ops']}")
        fcost = funnel_data.get('cost', {})
        lines.append(f"   - Coût opcodes global : total = {fcost.get('total_ops', 0)} ops, médiane = {fcost.get('median_ops', 0):.0f} ops, max = {fcost.get('max_ops', 0)} ops")
    lines.append("")

    # 8. Refus V233L_REJECT par raison
    lines.append("8. Refus V233L_REJECT par motif :")
    rejects_data = summary.get('v233l_rejects', {})
    rej_by_reason = rejects_data.get('by_reason', {})
    if not rej_by_reason:
        lines.append("   (aucun refus V233L_REJECT journalisé)")
    else:
        for rk, rv in sorted(rej_by_reason.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"   - {rk:<28s} : {rv:4d}")
        lines.append(f"   * TOTAL refus V233L_REJECT : {rejects_data.get('total', 0)}")
    lines.append("=" * len(header))
    return "\n".join(lines)


def format_comparison_text(comp: Dict[str, Any]) -> str:
    lines = []
    ref_info = comp['reference']
    var_info = comp['variant']
    header = f"=== Résumé comparatif : Référence ({ref_info['arm']}) vs Variante ({var_info['arm']}) ==="
    lines.append(header)
    lines.append(f"Fichier Réf : {ref_info['filepath']}")
    lines.append(f"Fichier Var : {var_info['filepath']}")
    lines.append("")

    # 1. Sites B trouvés
    sb = comp['sites_b_found']
    lines.append("1. Sites B trouvés :")
    lines.append(f"   - Référence : {sb['reference']} ({sb['ref_search_ok']} scan OK, {sb['ref_join_ok']} jointure OK)")
    lines.append(f"   - Variante  : {sb['variant']} ({sb['var_search_ok']} scan OK, {sb['var_join_ok']} jointure OK)")
    lines.append(f"   - Delta     : {sb['delta']:+d}")
    lines.append("")

    # 2. Opcodes de recherche
    so = comp['search_opcodes']
    lines.append("2. Opcodes de recherche de site :")
    lines.append(f"   - Côté A : Réf = {so['side_a']['reference']:8d} ops | Var = {so['side_a']['variant']:8d} ops | Delta = {so['side_a']['delta']:+8d} ops")
    lines.append(f"   - Côté B : Réf = {so['side_b']['reference']:8d} ops | Var = {so['side_b']['variant']:8d} ops | Delta = {so['side_b']['delta']:+8d} ops")
    lines.append(f"   - Total  : Réf = {so['total']['reference']:8d} ops | Var = {so['total']['variant']:8d} ops | Delta = {so['total']['delta']:+8d} ops")
    lines.append("")

    # 3. Lignes rail GOOD posées
    gl = comp['good_lines']
    lines.append("3. Lignes rail GOOD posées :")
    lines.append(f"   - Nombre de lignes : Réf = {gl['count']['reference']}, Var = {gl['count']['variant']} (Delta: {gl['count']['delta']:+d})")
    lines.append(f"   - Double voie      : Réf = {gl['double_track_count']['reference']}, Var = {gl['double_track_count']['variant']} (Delta: {gl['double_track_count']['delta']:+d})")
    lines.append("   Détail Référence :")
    if not gl['reference_lines']:
        lines.append("     (aucune ligne rail GOOD)")
    else:
        for l in gl['reference_lines']:
            track_str = "DOUBLE VOIE" if l['double_track'] else "VOIE UNIQUE"
            dist_str = f"{l['dist']} tuiles" if l['dist'] is not None else "dist=inconnue"
            lines.append(f"     * Ligne {l['line_id']} : {dist_str}, {l['trains']} train(s), {track_str}")
    lines.append("   Détail Variante :")
    if not gl['variant_lines']:
        lines.append("     (aucune ligne rail GOOD)")
    else:
        for l in gl['variant_lines']:
            track_str = "DOUBLE VOIE" if l['double_track'] else "VOIE UNIQUE"
            dist_str = f"{l['dist']} tuiles" if l['dist'] is not None else "dist=inconnue"
            lines.append(f"     * Ligne {l['line_id']} : {dist_str}, {l['trains']} train(s), {track_str}")
    lines.append("")

    # 4. V233L_REJECT par raison
    rej = comp['v233l_reject_by_reason']
    lines.append("4. V233L_REJECT par raison :")
    lines.append(f"   {'Motif':<36s} {'Réf':>8s} {'Var':>8s} {'Delta':>8s}")
    lines.append("   " + "-" * 62)
    for r, rdata in sorted(rej['by_reason'].items()):
        lines.append(f"   {r:<36s} {rdata['reference']:8d} {rdata['variant']:8d} {rdata['delta']:+8d}")
    lines.append("   " + "-" * 62)
    tot = rej['total']
    lines.append(f"   {'TOTAL':<36s} {tot['reference']:8d} {tot['variant']:8d} {tot['delta']:+8d}")
    lines.append("=" * len(header))
    return "\n".join(lines)


def run_diag(paths: List[Path], output_json: bool = False, compare: bool = False) -> int:
    all_summaries = []

    # Expand directories
    expanded_files = []
    for p in paths:
        if p.is_dir():
            files = sorted(list(p.glob('*.log')) + list(p.glob('*.log.gz')))
            expanded_files.extend(files)
        elif p.is_file():
            expanded_files.append(p)
        else:
            print(f"Avertissement : chemin introuvable : {p}", file=sys.stderr)

    if not expanded_files:
        print("Erreur : aucun fichier journal .log ou .log.gz trouvé.", file=sys.stderr)
        return 1

    for fpath in expanded_files:
        parser = DiagV233LLogParser(fpath)
        summary = parser.parse()
        all_summaries.append(summary)
        if not output_json:
            print(format_report_text(summary))
            print("")

    comparison = None
    if len(all_summaries) == 2 or (compare and len(all_summaries) >= 2):
        comparison = compare_summaries(all_summaries[0], all_summaries[1])
        if not output_json:
            print(format_comparison_text(comparison))

    if output_json:
        if comparison is not None:
            output_payload = {
                'summaries': all_summaries,
                'comparison': comparison
            }
            print(json.dumps(output_payload, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(all_summaries, indent=2, ensure_ascii=False))

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Lecteur de smoke diag_v233l pour journaux moteur OpenTTD/OpexAI."
    )
    parser.add_argument(
        'paths',
        nargs='*',
        help="Chemin(s) vers des fichiers arm_seedN_rN.log(.gz) ou répertoire(s) de journaux moteur."
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help="Affiche le rapport au format JSON structuré."
    )
    parser.add_argument(
        '--compare',
        action='store_true',
        help="Active le résumé comparatif entre les deux premiers journaux analysés."
    )
    args = parser.parse_args()

    paths = [Path(p) for p in args.paths]
    if not paths:
        default_dir = Path("/home/deploy/projects/openttd-ml/results/v233_long_expo_5x10_20261025_engine")
        if default_dir.exists():
            paths = [default_dir]
        else:
            parser.print_help()
            sys.exit(1)

    sys.exit(run_diag(paths, output_json=args.json, compare=args.compare))


if __name__ == '__main__':
    main()
