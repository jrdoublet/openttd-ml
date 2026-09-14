"""C66.2 — Santé du moteur, des compagnies et activité de l'IA, sans les confondre.

Le duel 1v1 partage un stdout OpenTTD. Un marqueur fatal lu sans identifiant de script
impute l'erreur au joueur 0 et déclare l'adversaire sain. Ce module :

- conserve le journal une fois par partie (chemin, pas une copie par compagnie) ;
- attribue les erreurs NoAI via `[script:N] [company]` et le manifeste des places ;
- laisse « non attribué » si le moteur ne permet pas de trancher ;
- contrôle compagnies attendues, doublons de checkpoints et horizon réel
  (janvier de la dernière année ne prouve pas l'année) ;
- distingue moteur/timeout, données manquantes, NoAI attribué, faillite, fin
  complète et suspicion de stagnation ;
- la faillite reste une issue économique (gardée dans les moyennes) ;
- l'absence de construction n'est pas un gel si la valeur continue de bouger.
"""
from __future__ import annotations

from collections import defaultdict
import functools
import inspect
from pathlib import Path
import re

SCHEMA_VERSION = "1.0.0"

SCRIPT_LINE_RE = re.compile(r"\[script:(\d+)\]\s*\[(\d+)\]\s*\[(\w)\]\s*(.*)$")
FATAL_MARKERS = (
    "Your script made an error",
    "The script died unexpectedly",
)
ENGINE_MARKERS = (
    "Fatal error",
    "Segmentation fault",
    "Aborted (core dumped)",
)

DUEL_SLOT_MAP = {
    0: {"company_id": 0, "name": "OpexAI"},
    1: {"company_id": 1, "name": "AAAHogEx"},
}

STATUSES = (
    "engine_error",
    "missing_data",
    "duplicate_checkpoint",
    "noai_error",
    "horizon_truncated",
    "bankrupt",
    "stagnation_suspect",
    "complete",
)

# Plus le rang est petit, plus le statut est grave pour game_ok.
_STATUS_RANK = {name: index for index, name in enumerate(STATUSES)}

COLLECTION_FAILURES = frozenset((
    "engine_error", "missing_data", "duplicate_checkpoint", "noai_error", "horizon_truncated",
))
ECONOMIC_OUTCOMES = frozenset(("complete", "bankrupt", "stagnation_suspect"))
ACTIVITY_RECENT_STEPS = 3
DEFAULT_ENGINE_TIMEOUT_SEC = 1800


def expected_last_year(starting_year, years):
    return int(starting_year) + int(years) - 1


def expected_last_checkpoint(starting_year, years, cadence="monthly"):
    """Dernier checkpoint qui prouve l'année finale, selon la cadence mensuelle 1er du mois.

    `starting_year + years - 1` en année seule accepte un 1974-01-01 pour un 5 ans
    commencé en 1970. Il faut au moins le 1er décembre de cette année.
    """
    if cadence != "monthly":
        raise ValueError(f"cadence inconnue: {cadence}")
    return f"{expected_last_year(starting_year, years):04d}-12-01"


def parse_date(value):
    text = str(value or "")
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def checkpoint_reaches(last_date, needed):
    last = parse_date(last_date)
    want = parse_date(needed)
    if last is None or want is None:
        return False
    return last >= want


def _output_text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def engine_failure_from_records(records):
    """Crash/timeout capturé par le wrapper, même sans marqueur dans le journal."""
    for record in records or ():
        fail = record.get("engine_failure")
        if not isinstance(fail, dict) or not fail:
            continue
        kind = fail.get("kind") or "nonzero_exit"
        if kind == "timeout":
            return "timeout"
        returncode = fail.get("returncode")
        if returncode is not None:
            return f"nonzero_exit:{returncode}"
        return "nonzero_exit"
    return None


def engine_failure_row(experiment, output, *, kind, returncode=None, date="1970-01-01"):
    """Ligne brute openttdlab-like pour `keep()` après un crash ou un timeout."""
    return {
        "experiment": experiment or {},
        "date": date,
        "output": _output_text(output),
        "chunks": {},
        "error": True,
        "engine_failure": {"kind": kind, "returncode": returncode},
    }


def capture_engine_failure(exc, experiment, result_processor):
    """Transforme CalledProcessError/TimeoutExpired en lignes keep(), sans abort de campagne."""
    import subprocess
    if isinstance(exc, subprocess.TimeoutExpired):
        kind = "timeout"
        output = exc.output
        returncode = None
    elif isinstance(exc, subprocess.CalledProcessError):
        kind = "nonzero_exit"
        output = exc.output
        returncode = exc.returncode
    else:
        kind = "engine_exception"
        output = str(exc)
        returncode = None
    row = engine_failure_row(experiment, output, kind=kind, returncode=returncode)
    processed = result_processor(row)
    if processed is None:
        return ()
    if isinstance(processed, (list, tuple)):
        return tuple(processed)
    return (processed,)


def _preserve_signature(wrapper, original):
    """`inspect.signature` doit encore voir run_dir/i/final_screenshot_directory."""
    functools.update_wrapper(wrapper, original)
    wrapper.__signature__ = inspect.signature(original)
    return wrapper


def wrap_engine_failure_capture(original):
    """Enveloppe `_run_experiment` en conservant sa signature pour le wrapper suivant."""
    if getattr(original, "_opex_engine_failure_capture", False):
        return original
    import subprocess

    signature = inspect.signature(original)

    def wrapped(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        try:
            return original(*args, **kwargs)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            from dill import dumps, loads
            experiment = loads(bound.arguments["experiment"])
            processor = loads(bound.arguments["result_processor"])
            rows = capture_engine_failure(exc, experiment, processor)
            return dumps(list(rows))

    wrapped._opex_engine_failure_capture = True
    return _preserve_signature(wrapped, original)


def enable_engine_failure_capture(timeout_sec=DEFAULT_ENGINE_TIMEOUT_SEC):
    """Intercepte un crash/timeout d'OpenTTD dans le worker et rend des lignes engine_error.

    Doit être appelé AVANT `enable_savegame_cleanup` : le rmtree final a alors encore
    le répertoire d'expérience si un salvage ultérieur est ajouté, et le catch entoure
    `check_output` plutôt que le nettoyage. La signature de `_run_experiment` est
    conservée, sinon le cleanup ne retrouve plus `run_dir`/`i`.
    """
    import openttdlab

    real_check = openttdlab.subprocess.check_output
    if not getattr(real_check, "_opex_engine_timeout", False):
        def check_output_with_timeout(*args, **kwargs):
            if timeout_sec:
                kwargs.setdefault("timeout", timeout_sec)
            return real_check(*args, **kwargs)

        check_output_with_timeout._opex_engine_timeout = True
        openttdlab.subprocess.check_output = check_output_with_timeout

    openttdlab._run_experiment = wrap_engine_failure_capture(openttdlab._run_experiment)


def write_engine_log(path, output):
    """Écrit le stdout du moteur une seule fois par partie (écrase la copie mensuelle)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output or "")
    return str(path)


def engine_log_path_for(log_dir, seed, repeat=0):
    return Path(log_dir) / f"seed{seed}_r{repeat}.log"


def _marker_in(text):
    text = text or ""
    for marker in FATAL_MARKERS:
        if marker in text:
            return marker
    return None


def _engine_marker(text):
    text = text or ""
    for marker in ENGINE_MARKERS:
        if marker in text:
            return marker
    return None


def parse_script_errors(output, slot_map=None):
    """Découpe le journal en erreurs attribuées ou non attribuées.

    `slot_map` relie l'index de script OpenTTD (ordre des `ais`) à `{company_id, name}`.
    Un id de script inconnu, un company id qui contredit le manifeste, ou un marqueur
    sans `[script:N] [C]` restent `unattributed` — jamais joueur 0 par défaut.
    """
    slot_map = slot_map or DUEL_SLOT_MAP
    attributed = []
    unattributed = []
    engine = _engine_marker(output)

    for raw in (output or "").splitlines():
        marker = _marker_in(raw)
        if marker is None:
            continue
        match = SCRIPT_LINE_RE.search(raw)
        if not match:
            unattributed.append({
                "script_id": None,
                "company_id": None,
                "marker": marker,
                "excerpt": raw.strip()[:240],
                "attributed_to": None,
                "attribution": "unattributed",
            })
            continue
        script_id = int(match.group(1))
        company_id = int(match.group(2))
        slot = slot_map.get(script_id)
        if slot is None or int(slot["company_id"]) != company_id:
            unattributed.append({
                "script_id": script_id,
                "company_id": company_id,
                "marker": marker,
                "excerpt": raw.strip()[:240],
                "attributed_to": None,
                "attribution": "unattributed",
            })
            continue
        attributed.append({
            "script_id": script_id,
            "company_id": company_id,
            "marker": marker,
            "excerpt": raw.strip()[:240],
            "attributed_to": slot["name"],
            "attribution": "script+company",
        })

    if engine and not attributed and not unattributed:
        unattributed.append({
            "script_id": None,
            "company_id": None,
            "marker": engine,
            "excerpt": engine,
            "attributed_to": None,
            "attribution": "unattributed",
        })

    return {
        "attributed": attributed,
        "unattributed": unattributed,
        "engine_marker": engine,
        "schema_version": SCHEMA_VERSION,
    }


def inspect_checkpoints(records, expected_companies=None):
    """Doublons (même compagnie, même date) et compagnies absentes du lot."""
    expected_companies = tuple(expected_companies or ())
    by_key = defaultdict(list)
    names_seen = set()
    for record in records:
        run = record.get("run") or []
        if len(run) < 1:
            continue
        name = run[0]
        names_seen.add(name)
        by_key[(name, record.get("date"))].append(record)
    duplicates = [
        {"arm": name, "date": date, "n": len(group)}
        for (name, date), group in sorted(by_key.items())
        if len(group) > 1
    ]
    missing = [name for name in expected_companies if name not in names_seen]
    return {
        "duplicates": duplicates,
        "missing_companies": missing,
        "companies_seen": sorted(names_seen),
    }


def activity_from_series(series):
    """Signal d'activité à partir des observations déjà dans les checkpoints.

    Une flotte/réseau inchangé n'est pas un gel si la valeur bouge encore
    (les véhicules peuvent gagner sans que le contrôleur construise).
    """
    ordered = sorted(series, key=lambda row: str(row.get("date", "")))
    empty = {
        "signal": "no_signal",
        "n_checkpoints": len(ordered),
        "fleet_changes": 0,
        "network_changes": 0,
        "value_changes": 0,
        "months_since_fleet_or_network_change": None,
        "months_since_value_change": None,
    }
    if len(ordered) < 2:
        return empty

    def _num(*values):
        for value in values:
            if isinstance(value, (int, float)):
                return value
        return None

    fleet_changes = 0
    network_changes = 0
    value_changes = 0
    last_expand = 0
    last_value = 0
    for index, (prev, cur) in enumerate(zip(ordered, ordered[1:]), start=1):
        prev_fleet = _num(prev.get("primary_vehicles"), prev.get("n_vehicles"))
        cur_fleet = _num(cur.get("primary_vehicles"), cur.get("n_vehicles"))
        prev_net = _num(prev.get("n_stations"))
        cur_net = _num(cur.get("n_stations"))
        prev_val = _num(prev.get("company_value"))
        cur_val = _num(cur.get("company_value"))
        if prev_fleet is not None and cur_fleet is not None and prev_fleet != cur_fleet:
            fleet_changes += 1
            last_expand = index
        if prev_net is not None and cur_net is not None and prev_net != cur_net:
            network_changes += 1
            last_expand = index
        if prev_val is not None and cur_val is not None and prev_val != cur_val:
            value_changes += 1
            last_value = index

    n_steps = len(ordered) - 1
    since_expand = n_steps - last_expand
    since_value = n_steps - last_value
    recent_expand = since_expand <= ACTIVITY_RECENT_STEPS
    recent_value = since_value <= ACTIVITY_RECENT_STEPS
    if (fleet_changes or network_changes) and recent_expand:
        signal = "active"
    elif value_changes and recent_value:
        signal = "earning_without_expansion"
    else:
        signal = "no_signal"

    return {
        "signal": signal,
        "n_checkpoints": len(ordered),
        "fleet_changes": fleet_changes,
        "network_changes": network_changes,
        "value_changes": value_changes,
        "months_since_fleet_or_network_change": since_expand,
        "months_since_value_change": since_value,
    }


def _run_name(record):
    run = record.get("run") or []
    return run[0] if run else None


def _last_of(series):
    if not series:
        return None
    return sorted(series, key=lambda row: str(row.get("date", "")))[-1]


def classify_company(
    series,
    *,
    name,
    parsed_errors,
    expected_checkpoint,
    checkpoint_report,
    engine_error=None,
):
    """Statut d'UNE compagnie. La faillite n'est pas une erreur de collecte."""
    last = _last_of(series)
    activity = activity_from_series(series)
    last_date = last.get("date") if last else None
    horizon_ok = checkpoint_reaches(last_date, expected_checkpoint) if last else False
    last_present = False if last is None else bool(last.get("company_present", True))
    present = bool(series) and last_present
    bankrupt = False
    if last is not None:
        months = last.get("months_of_bankruptcy") or 0
        bankrupt = months > 0
        if not last_present:
            prior = [
                row for row in series
                if row.get("date") != last_date and row.get("company_present", True)
            ]
            if prior:
                months = (_last_of(prior) or {}).get("months_of_bankruptcy") or 0
                bankrupt = months > 0 or bankrupt

    attributed = [item for item in parsed_errors["attributed"] if item["attributed_to"] == name]
    unattributed = parsed_errors["unattributed"]
    duplicates = [item for item in checkpoint_report["duplicates"] if item["arm"] == name]
    missing = name in checkpoint_report["missing_companies"]

    status = "complete"
    failure_reason = None
    if engine_error:
        status = "engine_error"
        failure_reason = f"engine_error: {engine_error}"
    elif missing or not series:
        status = "missing_data"
        failure_reason = f"missing_data: company {name} absent"
    elif not last_present and not bankrupt:
        status = "missing_data"
        failure_reason = (
            f"missing_data: company {name} absent at last checkpoint {last_date}"
        )
    elif duplicates:
        status = "duplicate_checkpoint"
        failure_reason = (
            f"duplicate_checkpoint: {duplicates[0]['arm']} {duplicates[0]['date']} "
            f"n={duplicates[0]['n']}"
        )
    elif attributed:
        status = "noai_error"
        failure_reason = f"noai_error[{name}]: {attributed[0]['marker']}"
    elif unattributed:
        status = "noai_error"
        failure_reason = f"unattributed_noai_error: {unattributed[0]['marker']}"
    elif not horizon_ok:
        status = "horizon_truncated"
        failure_reason = (
            f"horizon_truncated: last checkpoint {last_date or 'unknown'} "
            f"< expected {expected_checkpoint}"
        )
    elif bankrupt:
        status = "bankrupt"
    elif (
        activity["signal"] == "no_signal"
        and horizon_ok
        and activity["n_checkpoints"] >= 6
    ):
        status = "stagnation_suspect"
        failure_reason = None

    include = status in ECONOMIC_OUTCOMES
    return {
        "arm": name,
        "status": status,
        "run_ok": include,
        "include_in_economic_stats": include,
        "failure_reason": failure_reason,
        "horizon_complete": horizon_ok,
        "last_date": last_date,
        "activity": activity,
        "script_errors": attributed,
        "company_present": present,
        "bankrupt": bankrupt,
    }


def assess_game(
    records,
    *,
    starting_year=1970,
    years=5,
    expected_companies=("OpexAI", "AAAHogEx"),
    slot_map=None,
    engine_log=None,
    engine_log_path=None,
):
    """Évalue une partie partagée : moteur, chaque compagnie, horizon, activité."""
    slot_map = slot_map or DUEL_SLOT_MAP
    expected_companies = tuple(expected_companies)
    needed = expected_last_checkpoint(starting_year, years)
    if engine_log is None and engine_log_path:
        try:
            engine_log = Path(engine_log_path).read_text()
        except OSError:
            engine_log = None
    parsed = parse_script_errors(engine_log or "", slot_map=slot_map)
    engine_error = engine_failure_from_records(records)
    if engine_error is None:
        engine_error = parsed["engine_marker"]
    if engine_error is None and engine_log_path and engine_log is None:
        engine_error = f"missing_engine_log:{engine_log_path}"

    report = inspect_checkpoints(records, expected_companies=expected_companies)
    by_arm = defaultdict(list)
    for record in records:
        name = _run_name(record)
        if name:
            by_arm[name].append(record)

    companies = {}
    for name in expected_companies:
        companies[name] = classify_company(
            by_arm.get(name, []),
            name=name,
            parsed_errors=parsed,
            expected_checkpoint=needed,
            checkpoint_report=report,
            engine_error=engine_error,
        )

    statuses = [payload["status"] for payload in companies.values()]
    if engine_error:
        game_status = "engine_error"
    elif parsed["unattributed"] and all(
        payload["status"] == "noai_error" and not payload["script_errors"]
        for payload in companies.values()
    ):
        game_status = "noai_error"
    elif report["missing_companies"]:
        game_status = "missing_data"
    elif report["duplicates"]:
        game_status = "duplicate_checkpoint"
    else:
        game_status = min(statuses, key=lambda item: _STATUS_RANK[item])

    game_ok = (
        game_status in ECONOMIC_OUTCOMES
        and all(payload["include_in_economic_stats"] for payload in companies.values())
        and not parsed["unattributed"]
        and engine_error is None
        and not report["missing_companies"]
        and not report["duplicates"]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "engine_log_path": engine_log_path,
        "expected_last_year": expected_last_year(starting_year, years),
        "expected_last_checkpoint": needed,
        "game_ok": game_ok,
        "game_status": game_status,
        "engine_error": engine_error,
        "unattributed_errors": parsed["unattributed"],
        "checkpoint_report": report,
        "companies": companies,
    }


def _status_from_summarise_reason(reason):
    text = reason or ""
    if text.startswith("physical_decode_failure"):
        return "missing_data"
    if text.startswith("incomplete_run"):
        return "horizon_truncated"
    if text.startswith("engine_error"):
        return "engine_error"
    return "missing_data"


def annotate_summary(summary, records, assessment):
    """Enrichit les lignes summarise() sans réhabiliter un échec de collecte."""
    annotated = []
    for record in summary:
        health = assessment["companies"].get(record["arm"], {})
        updated = dict(record)
        preexisting_ok = record.get("run_ok") is not False
        preexisting_reason = record.get("failure_reason")
        health_ok = health.get("run_ok", True)
        health_status = health.get("status")
        health_reason = health.get("failure_reason")

        run_ok = preexisting_ok and bool(health_ok)
        if not preexisting_ok:
            reason = preexisting_reason
            if health_reason and health_reason != preexisting_reason:
                reason = f"{preexisting_reason}; {health_reason}"
            if health_status in ECONOMIC_OUTCOMES or health_status is None:
                status = _status_from_summarise_reason(preexisting_reason)
            else:
                status = health_status
        else:
            reason = health_reason
            status = health_status

        updated["status"] = status
        updated["horizon_complete"] = health.get("horizon_complete")
        updated["expected_last_checkpoint"] = assessment["expected_last_checkpoint"]
        updated["activity"] = health.get("activity")
        updated["engine_log_path"] = assessment.get("engine_log_path")
        updated["script_errors"] = health.get("script_errors") or []
        updated["unattributed_errors"] = assessment.get("unattributed_errors") or []
        updated["run_ok"] = run_ok
        updated["include_in_economic_stats"] = run_ok and status in ECONOMIC_OUTCOMES
        updated["failure_reason"] = reason
        updated.pop("openttd_output", None)
        annotated.append(updated)

    game_ok = bool(assessment.get("game_ok")) and all(
        record.get("run_ok") and record.get("status") in ECONOMIC_OUTCOMES
        for record in annotated
    )
    game_status = assessment.get("game_status")
    if annotated and not game_ok:
        game_status = min(
            (record.get("status") or "missing_data" for record in annotated),
            key=lambda item: _STATUS_RANK.get(item, len(_STATUS_RANK)),
        )
    for record in annotated:
        record["game_ok"] = game_ok
        record["game_status"] = game_status
    return annotated


def reconcile_assessment(assessment, annotated):
    """Aligne l'évaluation de partie sur le fail-closed déjà posé dans summary[]."""
    by_arm = {record["arm"]: record for record in annotated}
    companies = {}
    for name, payload in (assessment.get("companies") or {}).items():
        updated = dict(payload)
        line = by_arm.get(name)
        if line:
            updated["status"] = line.get("status", updated.get("status"))
            updated["run_ok"] = line.get("run_ok", updated.get("run_ok"))
            updated["failure_reason"] = line.get("failure_reason")
            updated["include_in_economic_stats"] = line.get(
                "include_in_economic_stats", updated.get("include_in_economic_stats"),
            )
        companies[name] = updated
    reconciled = dict(assessment)
    reconciled["companies"] = companies
    if annotated:
        reconciled["game_ok"] = annotated[0]["game_ok"]
        reconciled["game_status"] = annotated[0]["game_status"]
    return reconciled
