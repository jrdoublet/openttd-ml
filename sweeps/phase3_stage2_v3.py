#!/usr/bin/env python3
"""Etage 2 v3 : valeur predictive de mesures connues apres pathfinding.

Le protocole de validation reste celui du baseline fige.  Cette experience ne
change donc ni les lignes, ni les graines, ni les plis : elle demande seulement
si les mesures v3 apportent du signal au-dela des 25 variables deja legitimes
apres le pathfinding.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Le contrat des 25 variables et l'audit des fuites viennent du protocole fige,
# afin qu'une modification de celui-ci ne puisse pas faire diverger v2 et v3.
from phase3_stage2_baseline import (  # noqa: E402
    EXCLUDED_COLUMNS,
    FEATURE_COLUMNS as BASE25,
    RANDOM_STATE,
    assert_feature_matrix_safe,
)


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "phase2_hurdle_v3.csv"
OUTPUT_PATH = ROOT / "results" / "phase3_stage2_v3.json"

TARGET_COLUMN = "profit_ligne"
GROUP_COLUMN = "seed"
FAILURE_REASON_COLUMN = "failure_reason"
N_SPLITS = 5
PERMUTATION_REPEATS = 30
V2_RIDGE_MAE = 1_232_664
V2_BOOSTING_MAE = 1_120_212

# Ces blocs sont tous observes apres la recherche du chemin, avant la premiere
# mutation.  Contrairement a l'etage 1, aucune absence ne revele ici un echec :
# nous ne gardons de toute facon que les lignes effectivement construites.
CORRIDOR = [
    "corridor_dh",
    "corridor_water",
    "corridor_unbuildable",
    "corridor_max_water_run",
    "corridor_max_uphill_step",
]
GARE_GEO = [
    "station_radius_a",
    "station_radius_b",
    "station_radius_max",
    "station_outward_a",
    "station_outward_b",
    "station_outward_min",
]
SONDE = [
    "probe_500_closed",
    "probe_500_frontier",
    "probe_500_cost",
    "probe_500_remaining",
    "probe_500_gained",
    "probe_500_progress_ratio_ppm",
    "probe_2000_closed",
    "probe_2000_frontier",
    "probe_2000_cost",
    "probe_2000_remaining",
    "probe_2000_gained",
    "probe_2000_progress_ratio_ppm",
    "probe_5000_closed",
    "probe_5000_frontier",
    "probe_5000_cost",
    "probe_5000_remaining",
    "probe_5000_gained",
    "probe_5000_progress_ratio_ppm",
]
PATHCOST = ["pathfinder_iterations_consumed"]
FEATURE_BLOCKS = {
    "CORRIDOR": CORRIDOR,
    "GARE_GEO": GARE_GEO,
    "SONDE": SONDE,
    "PATHCOST": PATHCOST,
}


def metric_summary(values: list[float]) -> dict[str, float | list[float]]:
    """Resume les plis, avec le meme ecart-type echantillonnal que v2."""
    values_array = np.asarray(values, dtype=float)
    return {
        "mean": float(values_array.mean()),
        "std": float(values_array.std(ddof=1)),
        "folds": [float(value) for value in values_array],
    }


def assert_columns_safe(columns: list[str], context: str) -> None:
    """Etend l'audit v2 aux projections v3 sans desserrer ses exclusions."""
    leaked_columns = sorted(set(columns).intersection(EXCLUDED_COLUMNS))
    assert not leaked_columns, (
        f"Fuite de donnees dans {context} : colonnes exclues dans X : {leaked_columns}"
    )
    assert len(columns) == len(set(columns)), f"Doublon de feature dans {context}: {columns}"


def assert_full_coverage(data: pd.DataFrame, columns: list[str], context: str) -> None:
    """Evite qu'un gain soit en fait cause par un changement d'echantillon."""
    missing = [column for column in columns if column not in data.columns]
    assert not missing, f"Colonnes absentes dans {context}: {missing}"
    incomplete = {
        column: int(data[column].notna().sum())
        for column in columns
        if int(data[column].notna().sum()) != len(data)
    }
    assert not incomplete, (
        f"Couverture incomplete dans {context}, attendu {len(data)}/{len(data)} : "
        f"{incomplete}"
    )


def assert_all_finite(value: object, location: str = "resultat") -> None:
    """Interdit un JSON qui cacherait un NaN produit dans un pli."""
    if isinstance(value, dict):
        for key, child in value.items():
            assert_all_finite(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_all_finite(child, f"{location}[{index}]")
    elif isinstance(value, float) and not np.isfinite(value):
        raise ValueError(f"Valeur non finie dans {location}: {value}")


def ridge_estimator() -> Pipeline:
    """La regularisation et l'echelle sont celles imposees par le baseline."""
    return Pipeline([("scaler", StandardScaler()), ("model", Ridge(alpha=1.0))])


def boosting_estimator() -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(max_iter=300, random_state=RANDOM_STATE)


def paired_delta(candidate_mae: list[float], base_mae: list[float]) -> dict[str, object]:
    """Signe annonce : candidat - BASE25, donc negatif = MAE amelioree."""
    differences = np.asarray(candidate_mae, dtype=float) - np.asarray(base_mae, dtype=float)
    assert len(differences) == N_SPLITS, "Comparaison non appariee: nombre de plis inattendu."
    return {
        "convention": "MAE candidat - MAE BASE25 ; negatif = amelioration du candidat.",
        "mae_delta_by_fold": [float(value) for value in differences],
        "mean": float(differences.mean()),
        "std": float(differences.std(ddof=1)),
        "improved_folds": int((differences < 0).sum()),
        "n_folds": N_SPLITS,
    }


def format_summary(summary: dict[str, object]) -> str:
    return f"{float(summary['mean']):.0f} +/- {float(summary['std']):.0f}"


def format_delta(delta: dict[str, object]) -> str:
    return (
        f"{float(delta['mean']):+.0f} +/- {float(delta['std']):.0f} de MAE, "
        f"{int(delta['improved_folds'])} plis sur {N_SPLITS}"
    )


def main() -> None:
    data = pd.read_csv(CSV_PATH)
    # Les deux ratios de BASE25 sont derives plus bas, comme dans le baseline;
    # seules les 23 variables brutes doivent donc exister dans le CSV.
    derived_base25 = {
        "cargo_production_per_convoy_capacity",
        "cargo_acceptance_per_convoy_capacity",
    }
    required = [
        TARGET_COLUMN, GROUP_COLUMN, FAILURE_REASON_COLUMN, "built",
        *(column for column in BASE25 if column not in derived_base25),
    ]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"Colonnes obligatoires manquantes : {missing}")

    total_rows = len(data)
    # OK est la definition operationnelle d'une ligne construite dans la
    # campagne. Ce filtre laisse les PAIROOR hors echantillon, puis l'assertion
    # le prouve explicitement au lieu de le supposer.
    data = data.loc[data[FAILURE_REASON_COLUMN] == "OK"].copy()
    assert len(data) == 1551, f"1551 lignes construites attendues, {len(data)} trouvees."
    assert not (data[FAILURE_REASON_COLUMN] == "PAIROOR").any(), (
        "Des PAIROOR restent parmi les lignes construites."
    )
    assert data[FAILURE_REASON_COLUMN].eq("OK").all(), "Des echecs restent dans l'etage 2."
    assert data["built"].astype(str).str.strip().str.lower().eq("true").all(), (
        "Les lignes OK doivent toutes etre construites."
    )
    assert (data["convoy_capacity"] > 0).all(), "convoy_capacity doit etre positif."

    # Les ratios font partie de BASE25 : on les regenere exactement comme la
    # baseline, plutot que de dependre d'une colonne materalisee dans le CSV.
    data["cargo_production_per_convoy_capacity"] = (
        data["station_a_cargo_prod"] + data["station_b_cargo_prod"]
    ) / data["convoy_capacity"]
    data["cargo_acceptance_per_convoy_capacity"] = (
        data["station_a_cargo_acc"] + data["station_b_cargo_acc"]
    ) / data["convoy_capacity"]

    # Cet appel est volontairement strict : BASE25 doit rester exactement la
    # matrice du protocole fige, avant d'autoriser les candidats v3 separement.
    assert_feature_matrix_safe(BASE25)
    assert_columns_safe(BASE25, "BASE25")
    for block_name, block_columns in FEATURE_BLOCKS.items():
        assert_columns_safe(block_columns, block_name)
        assert_full_coverage(data, block_columns, block_name)
    assert_full_coverage(data, BASE25, "BASE25")

    all_used_columns = BASE25 + [column for block in FEATURE_BLOCKS.values() for column in block]
    assert_columns_safe(all_used_columns, "matrice commune v3")
    assert_full_coverage(data, all_used_columns, "matrice commune v3")
    features = data.loc[:, all_used_columns].astype(float).copy()
    assert not features.isna().any().any(), "Des NA restent dans la matrice de features."
    target = data[TARGET_COLUMN].astype(float)
    assert target.notna().all(), f"Des NA restent dans {TARGET_COLUMN}."
    groups = data[GROUP_COLUMN]

    cv = GroupKFold(n_splits=N_SPLITS)
    fold_indices = list(cv.split(features, target, groups=groups))
    assert len(fold_indices) == N_SPLITS, "GroupKFold n'a pas produit cinq plis."
    validation_index_fingerprints = [tuple(int(value) for value in test) for _, test in fold_indices]
    assert len(set(validation_index_fingerprints)) == N_SPLITS, "Plis de validation non distincts."
    fold_group_counts = [
        {
            "fold": fold_number,
            "train_rows": int(len(train)),
            "validation_rows": int(len(test)),
            "train_seeds": int(groups.iloc[train].nunique()),
            "validation_seeds": int(groups.iloc[test].nunique()),
        }
        for fold_number, (train, test) in enumerate(fold_indices, start=1)
    ]

    # Les blocs seuls sont tous testes avec Ridge. Seuls BASE25 et le modele
    # complet recoivent aussi le boosting, comme le demande le protocole ; ce
    # n'est donc pas un raccourci de temps sur les comparaisons de blocs.
    model_specs: dict[str, dict[str, object]] = {
        "dummy_median": {
            "label": "DummyRegressor (mediane du train fold)",
            "estimator": DummyRegressor(strategy="median"), "columns": BASE25, "role": "floor",
        },
        "linear_distance_manhattan": {
            "label": "LinearRegression (distance_manhattan seule)",
            "estimator": LinearRegression(), "columns": ["distance_manhattan"], "role": "control",
        },
        "ridge_base25": {
            "label": "Ridge (alpha=1.0, BASE25)",
            "estimator": ridge_estimator(), "columns": BASE25, "role": "baseline",
        },
        "hist_gradient_boosting_base25": {
            "label": "HistGradientBoostingRegressor (BASE25)",
            "estimator": boosting_estimator(), "columns": BASE25, "role": "baseline",
        },
    }
    for block_name, block_columns in FEATURE_BLOCKS.items():
        key = f"ridge_base25_{block_name.lower()}"
        model_specs[key] = {
            "label": f"Ridge (alpha=1.0, BASE25 + {block_name})",
            "estimator": ridge_estimator(), "columns": BASE25 + block_columns, "role": "block",
            "block": block_name,
        }
    for model_key, spec in model_specs.items():
        columns = list(spec["columns"])
        assert_columns_safe(columns, model_key)
        assert_full_coverage(data, columns, model_key)

    scores: dict[str, dict[str, list[float]]] = {
        key: {"mae": [], "r2": []} for key in model_specs
    }
    for fold_number, (train_index, validation_index) in enumerate(fold_indices, start=1):
        for model_key, spec in model_specs.items():
            # Cette empreinte empêche qu'une future refactorisation introduise
            # un split local : tous les ecarts qui suivent sont vraiment apparies.
            assert tuple(int(value) for value in validation_index) == validation_index_fingerprints[fold_number - 1]
            selected = features.loc[:, list(spec["columns"])]
            model = clone(spec["estimator"])
            model.fit(selected.iloc[train_index], target.iloc[train_index])
            prediction = model.predict(selected.iloc[validation_index])
            scores[model_key]["mae"].append(float(mean_absolute_error(target.iloc[validation_index], prediction)))
            scores[model_key]["r2"].append(float(r2_score(target.iloc[validation_index], prediction)))

    base_mae = scores["ridge_base25"]["mae"]
    paired_block_deltas: dict[str, dict[str, object]] = {}
    winning_blocks: list[str] = []
    for block_name in FEATURE_BLOCKS:
        model_key = f"ridge_base25_{block_name.lower()}"
        delta = paired_delta(scores[model_key]["mae"], base_mae)
        paired_block_deltas[block_name] = {"model_key": model_key, **delta}
        if float(delta["mean"]) < 0:
            winning_blocks.append(block_name)

    complete_columns = BASE25 + [
        column for block_name in winning_blocks for column in FEATURE_BLOCKS[block_name]
    ]
    assert_columns_safe(complete_columns, "modele complet")
    assert_full_coverage(data, complete_columns, "modele complet")
    complete_label_suffix = " + ".join(winning_blocks) if winning_blocks else "aucun bloc gagnant"
    complete_specs = {
        "ridge_base25_winning_blocks": {
            "label": f"Ridge (alpha=1.0, BASE25 + {complete_label_suffix})",
            "estimator": ridge_estimator(), "columns": complete_columns, "role": "complete",
        },
        "hist_gradient_boosting_base25_winning_blocks": {
            "label": f"HistGradientBoostingRegressor (BASE25 + {complete_label_suffix})",
            "estimator": boosting_estimator(), "columns": complete_columns, "role": "complete",
        },
    }
    for model_key, spec in complete_specs.items():
        model_specs[model_key] = spec
        scores[model_key] = {"mae": [], "r2": []}
    for fold_number, (train_index, validation_index) in enumerate(fold_indices, start=1):
        for model_key, spec in complete_specs.items():
            assert tuple(int(value) for value in validation_index) == validation_index_fingerprints[fold_number - 1]
            selected = features.loc[:, list(spec["columns"])]
            model = clone(spec["estimator"])
            model.fit(selected.iloc[train_index], target.iloc[train_index])
            prediction = model.predict(selected.iloc[validation_index])
            scores[model_key]["mae"].append(float(mean_absolute_error(target.iloc[validation_index], prediction)))
            scores[model_key]["r2"].append(float(r2_score(target.iloc[validation_index], prediction)))

    model_results = {
        model_key: {
            "label": str(spec["label"]), "features": list(spec["columns"]), "role": str(spec["role"]),
            "metrics": {"mae": metric_summary(scores[model_key]["mae"]), "r2": metric_summary(scores[model_key]["r2"])},
        }
        for model_key, spec in model_specs.items()
    }

    # Les importances restent hors echantillon et avec les 30 repetitions du
    # protocole. Les quatre modeles de reference/complet rendent lisible ce que
    # le non-lineaire exploite eventuellement au-dela de Ridge.
    importance_model_keys = [
        "ridge_base25", "hist_gradient_boosting_base25",
        "ridge_base25_winning_blocks", "hist_gradient_boosting_base25_winning_blocks",
    ]
    importances: dict[str, object] = {}
    for model_key in importance_model_keys:
        spec = model_specs[model_key]
        selected = features.loc[:, list(spec["columns"])]
        by_feature: dict[str, list[float]] = {column: [] for column in selected.columns}
        for train_index, validation_index in fold_indices:
            model = clone(spec["estimator"])
            model.fit(selected.iloc[train_index], target.iloc[train_index])
            permutation = permutation_importance(
                model, selected.iloc[validation_index], target.iloc[validation_index],
                scoring="neg_mean_absolute_error", n_repeats=PERMUTATION_REPEATS,
                random_state=RANDOM_STATE, n_jobs=3,
            )
            for feature, importance in zip(selected.columns, permutation.importances_mean):
                by_feature[feature].append(float(importance))
        summary = [
            {"feature": feature, **metric_summary(values)}
            for feature, values in by_feature.items()
        ]
        summary.sort(key=lambda item: float(item["mean"]), reverse=True)
        importances[model_key] = {
            "scoring": "neg_mean_absolute_error",
            "interpretation": "Importance positive = hausse de MAE apres permutation.",
            "n_repeats": PERMUTATION_REPEATS, "features": summary,
        }

    ridge_v3 = model_results["ridge_base25"]["metrics"]["mae"]
    boosting_v3 = model_results["hist_gradient_boosting_base25"]["metrics"]["mae"]
    # Bornes volontairement larges : v3 a six profits differents, mais elles
    # detectent encore une cible ou une matrice completement mal cablee.
    assert 500_000 <= float(ridge_v3["mean"]) <= 2_000_000, "MAE Ridge BASE25 v3 hors fourchette de coherence large."
    assert 500_000 <= float(boosting_v3["mean"]) <= 2_000_000, "MAE boosting BASE25 v3 hors fourchette de coherence large."
    pathcost_profit_correlation = float(data[PATHCOST[0]].corr(target))

    results = {
        "dataset": {
            "csv": str(CSV_PATH.relative_to(ROOT)), "rows_before_ok_filter": int(total_rows),
            "rows_after_ok_filter": int(len(data)), "pairoor_rows_after_ok_filter": int(data[FAILURE_REASON_COLUMN].eq("PAIROOR").sum()),
            "n_seeds": int(groups.nunique()), "target": TARGET_COLUMN,
        },
        "feature_policy": {
            "decision_time": "Apres pathfinding, avant la premiere mutation.", "base25_imported_from": "sweeps/phase3_stage2_baseline.py",
            "base25": BASE25, "blocks": FEATURE_BLOCKS, "excluded_columns_imported_from_baseline": EXCLUDED_COLUMNS,
            "runtime_guards_exercised": {
                "baseline_assert_feature_matrix_safe": "BASE25 controle avec l'assertion stricte importee.",
                "no_excluded_columns": "Toutes les matrices candidates controlees contre EXCLUDED_COLUMNS importee.",
                "coverage": "Chaque feature utilisee couvre 1551/1551 lignes construites.",
                "pairoor": "0 PAIROOR apres restriction aux lignes construites.",
            },
        },
        "cross_validation": {
            "splitter": "GroupKFold", "n_splits": N_SPLITS, "group_column": GROUP_COLUMN,
            "random_state": RANDOM_STATE, "standard_deviation_ddof": 1, "folds": fold_group_counts,
            "paired_comparison": "Une seule liste de plis est reutilisee pour chaque modele.",
        },
        "models": model_results,
        "paired_mae_deltas_vs_ridge_base25": paired_block_deltas,
        "winning_blocks_by_ridge_mean_mae": winning_blocks,
        "complete_model": {"model_keys": list(complete_specs), "blocks": winning_blocks, "features": complete_columns},
        "base25_v3_vs_v2": {
            "ridge": {"v3_mae": ridge_v3, "v2_mae": V2_RIDGE_MAE, "v3_minus_v2": float(ridge_v3["mean"] - V2_RIDGE_MAE)},
            "hist_gradient_boosting": {"v3_mae": boosting_v3, "v2_mae": V2_BOOSTING_MAE, "v3_minus_v2": float(boosting_v3["mean"] - V2_BOOSTING_MAE)},
            "runtime_wiring_range_assertion": "500000 <= MAE moyenne v3 <= 2000000 pour Ridge et boosting.",
        },
        "validation_permutation_importance": importances,
        "analysis": {
            "corridor_vs_terrain": "Complete apres calcul; voir le resume stdout pour le delta apparie.",
            "sonde_cost_at_stage2": "Complete apres calcul; la recherche est deja terminee a cet instant.",
            "pathcost_profit": {"pearson_correlation_with_profit_ligne": pathcost_profit_correlation},
        },
    }
    # Les phrases d'analyse font partie du livrable JSON : elles lient les
    # conclusions au chiffre produit, pas seulement au raisonnement a priori.
    corridor = paired_block_deltas["CORRIDOR"]
    sonde = paired_block_deltas["SONDE"]
    pathcost = paired_block_deltas["PATHCOST"]
    results["analysis"]["corridor_vs_terrain"] = (
        "CORRIDOR est en concurrence avec les terrain_* deja dans BASE25, pas en remplacement : "
        f"Ridge BASE25+CORRIDOR donne {format_delta(corridor)} face a BASE25. "
        "Un delta negatif indique donc une information de corridor non deja resumee par terrain_* ."
    )
    results["analysis"]["sonde_cost_at_stage2"] = (
        "SONDE donne " + format_delta(sonde) + " face a BASE25. A l'etage 2 la decision est "
        "post-pathfinding : la recherche a deja ete payee, donc l'argument de cout qui l'excluait "
        "a l'etage 1 ne s'applique pas ici."
    )
    results["analysis"]["pathcost_profit"] = {
        "pearson_correlation_with_profit_ligne": pathcost_profit_correlation,
        "paired_ridge_delta": pathcost,
        "commentary": (
            f"PATHCOST (pathfinder_iterations_consumed) a une correlation de Pearson {pathcost_profit_correlation:+.3f} "
            "avec profit_ligne parmi les construites et donne " + format_delta(pathcost) +
            ". Il est legitimement connu apres pathfinding; sa forte correlation avec built (-0,699) "
            "ne suffit donc pas a elle seule a prouver une valeur pour le profit, que ce delta mesure directement."
        ),
    }
    assert_all_finite(results)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(results, output_file, indent=2, ensure_ascii=False, allow_nan=False)
        output_file.write("\n")

    print("=== Etage 2 v3 : profit_ligne sur les lignes construites ===")
    print(f"CSV : {CSV_PATH.relative_to(ROOT)}")
    print(f"Lignes : {total_rows} au depart ; {len(data)} OK/construites ; 0 PAIROOR apres filtre.")
    print(f"GroupKFold apparie : {N_SPLITS} plis, groupes {GROUP_COLUMN}, {groups.nunique()} graines ; RANDOM_STATE={RANDOM_STATE}.")
    print("Garde-fous passes : assertion BASE25 importee, exclusions, couverture 1551/1551 et cible finie.")
    print("MAE et R2 par pli (moyenne +/- ecart-type, ddof=1) :")
    for model_key, model_result in model_results.items():
        mae = model_result["metrics"]["mae"]
        r2 = model_result["metrics"]["r2"]
        print(f"- {model_result['label']} : MAE {format_summary(mae)} ({', '.join(f'{value:.0f}' for value in mae['folds'])}) ; R2 {format_summary(r2)} ({', '.join(f'{value:.4f}' for value in r2['folds'])})")
    print("Convention des ecarts apparies : MAE candidat - MAE Ridge BASE25 ; signe negatif = amelioration.")
    for block_name, delta in paired_block_deltas.items():
        print(f"- {block_name} : {format_delta(delta)}")
    print(f"Blocs gagnants (moyenne Ridge negative) : {', '.join(winning_blocks) if winning_blocks else 'aucun'}.")
    print("Controle de coherence BASE25 v2/v3 (fourchette large verifiee) :")
    print(f"- Ridge : v3 {ridge_v3['mean']:.0f} vs v2 {V2_RIDGE_MAE:.0f}, delta {ridge_v3['mean'] - V2_RIDGE_MAE:+.0f}.")
    print(f"- Boosting : v3 {boosting_v3['mean']:.0f} vs v2 {V2_BOOSTING_MAE:.0f}, delta {boosting_v3['mean'] - V2_BOOSTING_MAE:+.0f}.")
    print("Analyse :")
    print(f"- CORRIDOR vs terrain_* : {format_delta(corridor)}; terrain_* reste dans BASE25, le test est donc incremental.")
    print(f"- SONDE : {format_delta(sonde)}; apres pathfinding son cout est deja paye, contrairement a l'etage 1.")
    print(f"- PATHCOST : corr(profit_ligne)={pathcost_profit_correlation:+.3f}; {format_delta(pathcost)}; connu legitimement apres pathfinding.")
    print(f"Importances par permutation : 30 repetitions sur {', '.join(importance_model_keys)}.")
    print(f"JSON ecrit : {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
