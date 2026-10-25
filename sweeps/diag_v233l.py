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
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
import os
from pathlib import Path
import re
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
RE_FIELDS = re.compile(r'(\w+)=([^\s]+)')
RE_V233L = re.compile(r'\b(V233L_[A-Z0-9_]+)\b(?:\s+(.*))?')


def open_log_file(path: str | Path):
    path = Path(path)
    if path.suffix == '.gz':
        return gzip.open(path, 'rt', encoding='utf-8', errors='replace')
    return open(path, 'rt', encoding='utf-8', errors='replace')


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

    def _process_line(self, raw_line: str):
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

        # 2. Extract OPEX events (usually logged by [0])
        if 'OPEX ' not in raw_line and 'LINE_REVENUE' not in raw_line and 'RAIL_BUILD' not in raw_line and 'V190' not in raw_line:
            return

        date_m = re.search(r'OPEX\s+(\d{4}-\d+-\d+)\s+([A-Z0-9_]+)\s*(.*)', raw_line)
        if not date_m:
            return

        date = date_m.group(1)
        event = date_m.group(2)
        body = date_m.group(3)
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
                # Store pending association
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
                
                # Check waiting
                wait_a = fields.get('wait_a')  # None if absent
                
                rev_entry = {
                    'year': year,
                    'vehs': vehs,
                    'real_prof': real_prof,
                    'wait_a': wait_a if wait_a is not None else 'non journalisé',
                    'raw_fields': fields
                }
                line_data['annual_revenues'].append(rev_entry)

                # Flag useless / blocked trains (vehs >= 1 and real_prof <= 0)
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
    lines.append("=" * len(header))
    return "\n".join(lines)


def run_diag(paths: List[Path], output_json: bool = False) -> int:
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

    if output_json:
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
    args = parser.parse_args()

    paths = [Path(p) for p in args.paths]
    if not paths:
        # Default fallback check
        default_dir = Path("/home/deploy/projects/openttd-ml/results/v233_long_expo_5x10_20261025_engine")
        if default_dir.exists():
            paths = [default_dir]
        else:
            parser.print_help()
            sys.exit(1)

    sys.exit(run_diag(paths, output_json=args.json))


if __name__ == '__main__':
    main()
