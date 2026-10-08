"""Fail-closed, standard-library gates for preregistered same-source setting duels.

This verifies evidence consistency, not its authenticity against a malicious writer.
Only the final adoption gate can return ACCEPTE. Nothing edits an AI default.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import statistics

from campaign_freeze import effective_ai_settings, fingerprint_tree
from paired_statistics import bootstrap_mean_ci, exact_wilcoxon_signed_rank_p


SEEDS = [42, 100, 7, 999, 2026, 1, 17, 73, 314, 512, 1024, 1337,
         4096, 8191, 12345, 54321, 65537, 123456, 424242, 8675309]
SEEDS_40 = SEEDS + [423960, 613553, 515222, 781335, 375172, 999533, 442018,
                    746035, 455216, 230185, 706990, 983759, 802204, 232037,
                    723002, 313707, 701256, 292001, 841478, 59527]
PROFILES = {"smoke": (1, [42]), "gain_short": (3, SEEDS_40), "non_erosion": (10, SEEDS)}


def stages_for(spec):
    return tuple(PROFILES) if spec["category"] == "behavior" else ("smoke", "non_erosion")


def protocol_rule(stage):
    rule = dict(rule="non_erosion" if stage == "non_erosion" else "gain_short",
                primary_metric="profit_year", min_useful_primary_delta=None,
                min_useful_primary_delta_pct=4.0, value_guard_metric="company_value",
                value_guard_max_loss_pct=5.0, all_planned_pairs_required_for_verdict=True)
    if stage != "non_erosion":
        rule.update(required_seeds=40, required_years=3)
    return rule


COMPONENTS = {"selection", "rail_attempt", "road_planning", "road_build",
              "air_planning", "water_planning"}
ACCEPTED, REJECTED, INVALID, CONTINUE = "ACCEPTÉ", "REFUSÉ", "NON_VALIDÉ", "POURSUIVRE"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def read_json(path):
    def reject(value):
        raise ValueError(f"Constante JSON non finie : {value}")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Clé JSON dupliquée : {key}")
            result[key] = value
        return result

    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject,
                      object_pairs_hook=unique)


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def arm_settings(arm):
    require(isinstance(arm, str) and re.fullmatch(
        r"OpexAI\[[A-Za-z_][A-Za-z_0-9]*=-?\d+(?:,[A-Za-z_][A-Za-z_0-9]*=-?\d+)*\]", arm),
        "Les deux bras doivent expliciter leurs réglages")
    entries = [item.split("=") for item in arm[7:-1].split(",")]
    require(len({key for key, _ in entries}) == len(entries), "Réglage dupliqué")
    return {key: int(value) for key, value in entries}


def validate_spec(spec):
    require(isinstance(spec, dict), "Plan JSON objet requis")
    require(set(spec) == {"schema_version", "category", "reference", "variant", "exposure",
                          "opcode_component", "contract_tests", "budget_minutes", "rationale"},
            "Champs du plan inconnus ou manquants")
    require(type(spec["schema_version"]) is int and spec["schema_version"] == 2,
            "Plan V102 de schéma 2 requis ; schéma 1 historique non exécutable")
    require(spec["category"] in ("behavior", "opcodes"), "Catégorie invalide")
    ref, var = arm_settings(spec["reference"]), arm_settings(spec["variant"])
    require(ref.keys() == var.keys() and ref != var, "Mêmes clés explicites, valeurs distinctes requises")
    require(all(ref[k] != var[k] for k in ref), "Pas de réglage commun hors intervention")
    exposure = spec["exposure"]
    require(isinstance(exposure, dict) and set(exposure) == {"field", "minimum", "meaning"},
            "Exposition : field, minimum et meaning requis")
    require(isinstance(exposure["field"], str) and re.fullmatch(r"[A-Za-z_][\w.]*", exposure["field"]),
            "Chemin de compteur invalide")
    require(exposure["field"].split(".")[0] not in {
        "profit_year", "company_value", "profit", "money", "performance_history", "seed", "repeat"},
        "Une métrique économique/identité ne démontre pas l'exposition")
    require(number(exposure["minimum"]) and exposure["minimum"] > 0,
            "Exposition : minimum fini strictement positif requis")
    require(isinstance(exposure["meaning"], str) and bool(exposure["meaning"].strip()),
            "Décrire le lien entre compteur et mécanisme")
    require(isinstance(spec["rationale"], str) and bool(spec["rationale"].strip()), "Justification requise")
    require((spec["category"] == "behavior" and spec["opcode_component"] is None)
            or (spec["category"] == "opcodes" and spec["opcode_component"] in COMPONENTS),
            "Composant opcode observé requis uniquement pour la catégorie opcodes")
    tests = spec["contract_tests"]
    require(isinstance(tests, list) and tests and all(isinstance(t, str) and
            re.fullmatch(r"test_[A-Za-z0-9_]+", t) for t in tests), "Modules de contrats explicites requis")
    require(type(spec["budget_minutes"]) is int and 1 <= spec["budget_minutes"] <= 270,
            "Budget de parties : entier 1..270 minutes")
    return spec


def field(record, path):
    for key in path.split("."):
        require(isinstance(record, dict) and key in record, f"Compteur absent : {path}")
        record = record[key]
    require(number(record), f"Compteur non numérique : {path}")
    return record


def load_evidence(output, spec=None):
    """Verify adjacent artifacts; container /work paths are not host paths.

    Artifact downloads may be relocated without rewriting the hashed manifest.
    """
    output = Path(output)
    report = read_json(output)
    manifest_path = output.with_suffix(".manifest.json")
    require(digest(manifest_path) == report["manifest_sha256"], "Empreinte du manifeste incorrecte")
    manifest = read_json(manifest_path)
    bundle = output.with_name(output.stem + "_bundle")
    require(not bundle.is_symlink() and not any(p.is_symlink() for p in bundle.rglob("*")),
            "Lien symbolique dans le bundle")
    fingerprint = fingerprint_tree(bundle)
    require(bundle.is_dir() and fingerprint["file_count"] > 0, "Bundle absent/vide")
    require(fingerprint["sha256"] == manifest["source_bundle"]["sha256"]
            == report["source_bundle_sha256"] and
            fingerprint["file_count"] == manifest["source_bundle"]["file_count"], "Bundle altéré")
    for name, relative in (("OpexAI", "ai/OpexAI"), ("AAAHogEx", "ai/AAAHogEx-115"),
                           ("harness", "harness"), ("ai_libraries", "ai_libraries")):
        require(fingerprint_tree(bundle / relative) == manifest["sources"][name],
                f"Source figée incohérente : {name}")
    for policy in manifest["policies"]:
        settings = policy["settings"]
        require(settings == effective_ai_settings(bundle / "ai/OpexAI/info.nut",
                                                  tuple(settings["explicit"].items())),
                "Réglages effectifs différents des sources figées")
    require(manifest["adversary"]["settings"] == effective_ai_settings(
        bundle / "ai/AAAHogEx-115/info.nut", ()), "Réglages adverses incohérents")
    require(output.with_suffix(".jsonl").is_file(), "Checkpoints absents")
    require(output.with_name(output.stem + "_engine").is_dir(), "Logs moteur absents")
    verify_checkpoints(output, report, manifest, spec)
    return report, manifest


def verify_checkpoints(output, report, manifest, spec):
    """Stream raw monthly records; never accept an empty JSONL next to a healthy summary."""
    config = manifest["configuration"]
    dates = {f"{year}-{month:02d}-01" for year in range(config["starting_year"],
             config["starting_year"] + config["years"]) for month in range(1, 13)}
    summaries = {(r["game_id"], r["arm"]): r for r in report["summary"]}
    require(len(summaries) == len(report["summary"]), "Résumé dupliqué")
    seen = {key: set() for key in summaries}
    extra_date = f"{config['starting_year'] + config['years']}-01-01"
    pair_index = {(p["seed"], p["repeat"]): p for p in report["policy_comparison"]["per_pair"]}
    require(len(pair_index) == len(config["seeds"]), "Trajectoires annuelles absentes/dupliquées")
    with output.with_suffix(".jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            arm, seed, repeat = row["run"]
            key = (row["game_id"], arm)
            require(key in summaries, "Checkpoint d'une compagnie inattendue")
            summary = summaries[key]
            require(row["date"] in dates | {extra_date} and row["date"] not in seen[key],
                    "Checkpoint absent du protocole/dupliqué")
            seen[key].add(row["date"])
            require(seed == summary["seed"] and repeat == summary["repeat"] and
                    row["campaign_id"] == manifest["campaign_id"] and
                    row["duel_policy_id"] == summary["duel_policy_id"] and
                    row["source_bundle_sha256"] == manifest["source_bundle"]["sha256"],
                    "Identité de checkpoint incohérente")
            if arm == "OpexAI" and row["date"] == f"{config['starting_year'] + config['years'] - 1}-12-01":
                terminal = pair_index[(seed, repeat)]["annual_trajectory"][-1]
                require(terminal["year"] == config["starting_year"] + config["years"] - 1
                        and terminal["primary_metric"] == "profit_year"
                        and terminal[row["duel_policy_id"] + "_opex"] == row["profit_year"],
                        "Base annuelle du seuil différente du checkpoint terminal")
            if row["date"] == summary["last_date"]:
                for metric in ("profit_year", "company_value", "profit_year_coverage",
                               "profit_year_quarters_valid", "profit_year_quarters_available",
                               "observed_opcode_schema", "observed_opcode_components"):
                    require(row.get(metric) == summary.get(metric), f"Résumé différent du checkpoint : {metric}")
                if spec is not None and arm == "OpexAI" and row["duel_policy_id"] == "variant":
                    path = spec["exposure"]["field"]
                    require(field(row, path) == field(summary, path), "Preuve d'exposition incohérente")
    require(seen and all(dates <= found <= dates | {extra_date} for found in seen.values()),
            "Séquence mensuelle incomplète")
    require(all(summary["n_savegames"] == len(seen[key]) and summary["last_date"] == max(seen[key])
                for key, summary in summaries.items()), "Horizon résumé différent des checkpoints")
    logs = output.with_name(output.stem + "_engine")
    for game in report["games"]:
        name = (game.get("engine_log_path") or "").replace("\\", "/").split("/")[-1]
        require(name not in ("", ".", "..") and (logs / name).is_file(), "Log de partie absent")


def identity(manifest):
    """Stage-invariant inputs, excluding IDs, times and horizon/seed selections."""
    return {key: manifest[key] for key in (
        "git", "versions", "runtime", "sources", "policies", "adversary",
        "libraries", "company_slots")} | {
            "comparison": {k: v for k, v in manifest["comparison"].items() if k != "decision_rule"},
            "configuration_sha256": manifest["configuration"]["sha256"],
            "bundle_sha256": manifest["source_bundle"]["sha256"],
        }


def validate_protocol(spec, stage, report, manifest, expected_sha, campaign, previous):
    years, seeds = PROFILES[stage]
    require(manifest["git"]["sha"] == expected_sha and manifest["git"]["dirty"] is False,
            "SHA différent ou checkout modifié")
    require(manifest["campaign_id"] == report["campaign_id"] == campaign, "Mauvaise campagne")
    require(manifest["versions"] == {"openttd": "15.3", "opengfx": "7.1", "openttdlab": "0.0.75"},
            "Versions moteur différentes")
    runtime = manifest["runtime"]
    require(runtime["docker_image_id_verified"] is True and
            re.fullmatch(r"sha256:[0-9a-f]{64}", runtime["docker_image_id"]), "Image non identifiée")
    require(runtime["docker_cpus"] == 3 and runtime["docker_memory"] == "2g"
            and runtime["docker_memory_swap"] == "2g", "Limites Docker différentes")
    config = manifest["configuration"]
    require(config["starting_year"] == 1970, "Année de départ différente")
    require(hashlib.sha256(config["raw"].encode()).hexdigest() == config["sha256"],
            "Configuration altérée")
    require(config["parsed"]["game_creation"]["map_x"] == "8" and
            config["parsed"]["game_creation"]["map_y"] == "8", "Carte différente de 256×256")
    for source in (config, report):
        require(source["years"] == years and source["seeds"] == seeds and source["repeats"] == 1,
                "Horizon, graines ou répétitions différents du protocole")
    require(manifest["execution"]["mode"] == "frozen-subprocess", "Harnais non figé")
    opts = manifest["execution"]["options"]
    require(stage in stages_for(spec), "Étape incompatible avec la catégorie du plan")
    require(opts["max_workers"] == 2 and opts["decision_rule"] == protocol_rule(stage)["rule"]
            and opts["line_telemetry"] is False, "Options d'exécution différentes")
    require(opts["min_useful_primary_delta"] is None and opts["min_useful_primary_delta_pct"] == 4
            and opts["value_guard_max_loss_pct"] == 5,
            "Seuils d'exécution différents du plan V102")
    policies = manifest["policies"]
    require(len(policies) == 2 and {p["id"] for p in policies} == {"reference", "variant"},
            "Deux politiques explicites requises")
    for policy in policies:
        role = policy["id"]
        settings = policy["settings"]
        require(policy["role"] == role and policy["ai"] == "OpexAI" and policy["company_slot"] == 0,
                "Politique/slot incorrect")
        require(settings["explicit"] == arm_settings(spec[role]), "Bras différent du plan")
        expected = dict(settings["defaults"], **settings["explicit"])
        require(settings["effective"] == expected, "Réglages effectifs incohérents")
        if role == "reference":
            require(settings["effective"] == settings["defaults"], "Référence hors défaut")
    comparison = manifest["comparison"]
    differences = {k: {"reference": v, "candidate": arm_settings(spec["variant"])[k]}
                   for k, v in arm_settings(spec["reference"]).items()}
    require(comparison["reference_policy_id"] == "reference" and
            comparison["variant_policy_id"] == "variant" and
            comparison["effective_differences"] == differences and
            set(comparison["intervention_settings"]) == set(differences), "Intervention différente")
    rule = comparison["decision_rule"]
    require(rule == protocol_rule(stage),
            "Seuils/règle différents du protocole")
    if previous is not None:
        require(identity(manifest) == previous, "Sources/runtime/politiques différents entre étapes")
    require(report["failed_runs"] == [], "Échecs moteur/collecte")
    expected_games = {f"{campaign}:policy={p}:s{s}:r0": (p, s)
                      for p in ("reference", "variant") for s in seeds}
    for games in (manifest["games"], report["games"]):
        require(len(games) == len(expected_games) and
                {g["game_id"] for g in games} == set(expected_games), "Parties absentes, en trop ou dupliquées")
        for game in games:
            require((game["policy_id"], game["seed"]) == expected_games[game["game_id"]]
                    and game["repeat"] == 0, "Identité de partie incorrecte")
    require(all(g["game_ok"] is True for g in report["games"]), "Partie non saine")
    rows = {}
    for row in report["summary"]:
        key = (row["duel_policy_id"], row["seed"], row["arm"])
        require(key not in rows and row["repeat"] == 0, "Résumé dupliqué/répété")
        require(row["campaign_id"] == campaign and
                expected_games.get(row["game_id"]) == key[:2] and
                row["source_bundle_sha256"] == manifest["source_bundle"]["sha256"], "Provenance de ligne incorrecte")
        require(row["company_slot"] == {"OpexAI": 0, "AAAHogEx": 1}.get(row["arm"]), "Slot incorrect")
        require(row["run_ok"] is True and row["game_ok"] is True, "Compagnie non saine")
        require((row["last_date"], row["n_savegames"]) in
                ((f"{1969 + years}-12-01", 12 * years), (f"{1970 + years}-01-01", 12 * years + 1)),
                "Horizon/checkpoints incomplets")
        if stage != "smoke":
            require(row["profit_year_coverage"] == "complete" and
                    row["profit_year_quarters_valid"] == row["profit_year_quarters_available"] == 4,
                    "Quatre trimestres valides requis")
            require(number(row["profit_year"]) and number(row["company_value"]), "Métrique invalide")
        rows[key] = row
    require(set(rows) == {(p, s, a) for p in ("reference", "variant") for s in seeds
                          for a in ("OpexAI", "AAAHogEx")}, "Couverture des compagnies incorrecte")
    return rows


def economic_stats(rows, seeds):
    ref = [rows[("reference", s, "OpexAI")] for s in seeds]
    var = [rows[("variant", s, "OpexAI")] for s in seeds]
    require(all(r["company_value"] > 0 for r in ref), "Valeur de référence non positive")
    deltas = [v["profit_year"] - r["profit_year"] for r, v in zip(ref, var)]
    wins, losses = sum(d > 0 for d in deltas), sum(d < 0 for d in deltas)
    n = wins + losses
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / 2**n) if n else 1.0
    mean = statistics.mean(deltas)
    margin = {20: 2.093024, 40: 2.022691}[len(seeds)] * statistics.stdev(deltas) / math.sqrt(len(seeds))
    guard = 100 * (statistics.mean(r["company_value"] for r in var) /
                   statistics.mean(r["company_value"] for r in ref) - 1)
    return dict(mean=mean, median=statistics.median(deltas), wins=wins, losses=losses,
                ties=len(seeds) - n, sign_test_p=p, student_ci95=[mean - margin, mean + margin],
                value_change_pct=guard, wilcoxon_p=exact_wilcoxon_signed_rank_p(deltas),
                bootstrap_ci95=list(bootstrap_mean_ci(deltas)), bootstrap_resamples=20000, bootstrap_seed=0,
                reference_mean=statistics.mean(r["profit_year"] for r in ref),
                per_seed=[dict(seed=s, delta=d) for s, d in zip(seeds, deltas)])


def opcode_saving(rows, seeds, component):
    savings = []
    for seed in seeds:
        pair = []
        for policy in ("reference", "variant"):
            row = rows[(policy, seed, "OpexAI")]
            require(row["observed_opcode_schema"] == "h5.observed-v1", "Schéma opcode absent/incompatible")
            item = row["observed_opcode_components"][component]
            require(type(item["samples"]) is int and item["samples"] > 0 and
                    number(item["opcodes"]) and item["opcodes"] >= 0, "Mesure opcode absente/invalide")
            pair.append(item)
        ref, var = pair
        require(ref["samples"] == var["samples"] and ref["coverage"] == var["coverage"]
                and bool(ref["coverage"]), "Échantillonnage opcode non comparable")
        savings.append((ref["opcodes"] - var["opcodes"]) / ref["samples"])
    return statistics.mean(savings)


def evaluate(spec, stage, report, manifest, *, expected_sha, campaign, previous=None):
    result = dict(stage=stage, status=INVALID, proceed=False, reasons=[],
                  raw_harness_verdict=(report.get("policy_comparison") or {}).get("verdict"))
    try:
        validate_spec(spec)
        rows = validate_protocol(spec, stage, report, manifest, expected_sha, campaign, previous)
        result["identity"] = identity(manifest)
        exposure = spec["exposure"]
        seeds = PROFILES[stage][1]
        require(all(field(rows[("variant", s, "OpexAI")], exposure["field"]) >= exposure["minimum"]
                    for s in seeds), "Mécanisme non exposé sur toutes les graines candidates")
        if stage == "smoke":
            comparison = report["policy_comparison"]
            require(comparison["comparison_complete"] is True and comparison["verdict"] == "diagnostic_only"
                    and comparison["complete_pairs"] == comparison["planned_pairs"] == 1
                    and comparison["decision_rule"]["rule"] == "gain_short",
                    "Smoke incomplet ou règle incorrecte")
            if spec["category"] == "opcodes":
                saving = opcode_saving(rows, seeds, spec["opcode_component"])
                result["opcode_saving_per_sample"] = saving
                require(saving > 0, "Gain opcode préalable non établi")
            result.update(status=CONTINUE, proceed=True, reasons=["Smoke sain ; aucune qualification économique"])
            return result
        seeds = PROFILES[stage][1]
        comparison = report["policy_comparison"]
        require(comparison["reference_policy_id"] == "reference" and comparison["variant_policy_id"] == "variant"
            and comparison["primary_metric"] == "profit_year" and comparison["value_guard_metric"] == "company_value",
            "Comparaison ou métriques différentes du plan")
        require(comparison["comparison_complete"] is True and comparison["metric_coverage_complete"] is True
                and comparison["complete_pairs"] == comparison["planned_pairs"] == len(seeds),
                "Comparaison incomplète")
        require(comparison["adoption_sample_complete"] is True, "Échantillon inadmissible")
        require(comparison["decision_rule"]["rule"] == protocol_rule(stage)["rule"],
                "Règle du rapport différente de la porte")
        stats = economic_stats(rows, seeds)
        pairs = comparison["per_pair"]
        require(len(pairs) == len(seeds) and {p["seed"] for p in pairs} == set(seeds)
                and all(p["repeat"] == 0 for p in pairs), "Trajectoires terminales incorrectes")
        terminal_profits = []
        for pair in pairs:
            terminal = pair["annual_trajectory"][-1]
            require(terminal["year"] == 1969 + PROFILES[stage][0]
                    and terminal["primary_metric"] == "profit_year" and number(terminal["reference_opex"]),
                    "Profit terminal de référence absent/invalide")
            terminal_profits.append(terminal["reference_opex"])
        stats["reference_mean"] = statistics.mean(terminal_profits)
        for key, actual in (("reference_terminal_profit_mean", stats["reference_mean"]),
                            ("min_useful_primary_delta", .04 * stats["reference_mean"])):
            require(number(comparison["decision_rule"][key]) and
                    math.isclose(comparison["decision_rule"][key], actual, rel_tol=1e-10, abs_tol=.000001),
                    "Base ou seuil relatif incohérent")
        result["statistics"] = stats
        expected_report_rule = dict(rule=protocol_rule(stage)["rule"], required_pairs=len(seeds),
                                    required_years=PROFILES[stage][0], confidence_level=0.95,
                                    min_useful_primary_delta_pct=4.0, value_guard_max_loss_pct=5.0,
                                    bootstrap_resamples=20000, bootstrap_seed=0,
                                    all_planned_pairs_required_for_verdict=True)
        if stage == "gain_short":
            expected_report_rule["max_wilcoxon_p_exclusive"] = 0.05
        require(all(comparison["decision_rule"].get(k) == v for k, v in expected_report_rule.items()),
                "Critères statistiques du rapport différents de V102")
        # Check the harness aggregates against independently recomputed final-company data.
        aggregates = comparison["aggregates"]
        for reported, actual in ((aggregates["profit_year"]["policy_delta"]["mean"], stats["mean"]),
                                 (aggregates["company_value"]["policy_ratio"]["ratio_of_means_percent_change"],
                                  stats["value_change_pct"])):
            require(number(reported) and math.isclose(reported, actual, rel_tol=1e-10, abs_tol=0.000001),
                    "Agrégats du harnais incohérents")
        # The harness publishes and gates this ratio at six decimal places.
        guard = round(stats["value_change_pct"], 6) >= -5
        ordinary = (stats["reference_mean"] > 0 and stats["mean"] >= 0.04 * stats["reference_mean"]
                    and stats["wilcoxon_p"] is not None and stats["wilcoxon_p"] < 0.05
                    and stats["bootstrap_ci95"][0] > 0) if stage == "gain_short" else stats["bootstrap_ci95"][1] >= 0
        primary_report = aggregates["profit_year"]["policy_delta"]
        require(primary_report["bootstrap_resamples"] == 20000 and primary_report["bootstrap_seed"] == 0
                and len(primary_report["mean_bootstrap_95pct_ci"]) == 2
                and all(number(a) and math.isclose(a, b, rel_tol=1e-10, abs_tol=0.000001)
                        for a, b in zip(primary_report["mean_bootstrap_95pct_ci"], stats["bootstrap_ci95"])),
                "IC95 bootstrap absent ou incohérent")
        require(primary_report["wilcoxon_p"] == stats["wilcoxon_p"], "Wilcoxon absent ou incohérent")
        expected = ("pass" if ordinary and guard else "fail_primary_and_value_guard"
                    if not ordinary and not guard else "fail_primary" if not ordinary else "fail_value_guard")
        require(comparison["verdict"] == expected, "Verdict brut incohérent avec les critères recalculés")
        if spec["category"] == "behavior":
            primary = ordinary
        else:
            saving = opcode_saving(rows, seeds, spec["opcode_component"])
            result["opcode_saving_per_sample"] = saving
            primary = (saving > 0 and stats["student_ci95"][1] >= 0 and
                       (stats["sign_test_p"] >= 0.05 or stats["wins"] > stats["losses"]))
        passed = primary and guard
        result.update(status=(ACCEPTED if stage == "non_erosion" else CONTINUE) if passed else REJECTED,
                      proceed=passed, reasons=["Critères satisfaits" if passed else
                                              "Critères économiques/opcodes non satisfaits ; défaut inchangé"])
    except (KeyError, IndexError, TypeError, ValueError, OverflowError, ZeroDivisionError) as error:
        result.update(status=INVALID, proceed=False, reasons=[str(error)])
    return result
