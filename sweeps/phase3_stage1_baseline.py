#!/usr/bin/env python3
"""Baseline de l'etage 1 du modele hurdle : probabilite de construction."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "phase2_hurdle_v2.csv"
OUTPUT_PATH = ROOT / "results" / "phase3_stage1_baseline.json"

TARGET_COLUMN = "built"
GROUP_COLUMN = "seed"
FAILURE_REASON_COLUMN = "failure_reason"
N_SPLITS = 5
RANDOM_STATE = 42
PERMUTATION_REPEATS = 30

# Ces douze variables sont les seules connues avant la construction retenues ici.
FEATURE_COLUMNS = [
    "distance_straight",
    "distance_manhattan",
    "pair_rank",
    "town_a_population",
    "town_b_population",
    "num_trains",
    "wagons_per_train",
    "convoy_capacity",
    "engine_rank",
    "engine_max_speed",
    "engine_power",
    "engine_running_cost",
]

# Liste explicite des exclusions de l'audit anti-fuite.  Elle est aussi testee
# contre la matrice finale de features juste avant l'apprentissage.
EXCLUDED_COLUMNS = [
    "construction_cost",
    "infra_cost",
    "vehicle_cost",
    "terrain_dh",
    "terrain_water",
    "terrain_unbuildable",
    "station_a_town_dist",
    "station_a_cargo_prod",
    "station_a_cargo_acc",
    "station_b_town_dist",
    "station_b_cargo_prod",
    "station_b_cargo_acc",
    "barrier_flag",
    "first_mutation_tick",
    "profit_ligne",
    "sum_profit_last_year",
    "amortization_annual",
    "vehicle_amortization_annual",
    "infra_amortization_annual",
    "n_lead_vehicles",
    "avg_max_age_years",
    "stagger_slot",
    "wagon_capacity",
    "line_index",
    "attempt_id",
    "estimated_cost",
]

METRICS = {
    "roc_auc": roc_auc_score,
    "accuracy": accuracy_score,
    "average_precision": average_precision_score,
}


def assert_feature_matrix_safe(columns: list[str]) -> None:
    """Garde-fou runtime : une fuite connue ne doit jamais revenir dans X."""
    leaked_columns = sorted(set(columns).intersection(EXCLUDED_COLUMNS))
    assert not leaked_columns, (
        "Fuite de donnees : colonnes exclues presentes dans la matrice de "
        f"features : {leaked_columns}"
    )
    assert columns == FEATURE_COLUMNS, (
        "La matrice de features ne contient pas exactement les 12 variables "
        f"autorisees : {columns}"
    )


def metric_summary(values: list[float]) -> dict[str, float | list[float]]:
    values_array = np.asarray(values, dtype=float)
    return {
        "mean": float(values_array.mean()),
        "std": float(values_array.std(ddof=1)),
        "folds": [float(value) for value in values_array],
    }


def format_mean_std(summary: dict[str, float | list[float]]) -> str:
    return f"{summary['mean']:.4f} +/- {summary['std']:.4f}"


def assert_all_finite(value: object, location: str = "resultat") -> None:
    """Refuse d'ecrire du JSON contenant NaN ou Infinity."""
    if isinstance(value, dict):
        for key, child in value.items():
            assert_all_finite(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_all_finite(child, f"{location}[{index}]")
    elif isinstance(value, float):
        if not np.isfinite(value):
            raise ValueError(f"Valeur non finie dans {location}: {value}")


def main() -> None:
    data = pd.read_csv(CSV_PATH)
    required_metadata = [TARGET_COLUMN, GROUP_COLUMN, FAILURE_REASON_COLUMN]
    missing_metadata = [column for column in required_metadata if column not in data.columns]
    if missing_metadata:
        raise ValueError(f"Colonnes de metadonnees obligatoires manquantes : {missing_metadata}")

    missing_features = [column for column in FEATURE_COLUMNS if column not in data.columns]
    if missing_features:
        raise ValueError(
            "Colonnes de features obligatoires manquantes ; le baseline ne peut pas "
            f"etre execute : {missing_features}"
        )

    total_rows = len(data)
    data = data.loc[data[FAILURE_REASON_COLUMN] != "PAIROOR"].copy()
    removed_pairoor_rows = total_rows - len(data)
    if (data[FAILURE_REASON_COLUMN] == "PAIROOR").any():
        raise AssertionError("Des lignes PAIROOR restent dans les donnees d'evaluation.")

    target = data[TARGET_COLUMN].astype(str).str.strip().str.lower().map(
        {"true": 1, "false": 0}
    )
    if target.isna().any():
        unexpected_values = sorted(data.loc[target.isna(), TARGET_COLUMN].astype(str).unique())
        raise ValueError(f"Valeurs inattendues dans {TARGET_COLUMN} : {unexpected_values}")
    target = target.astype(int)
    groups = data[GROUP_COLUMN]

    features = data.loc[:, FEATURE_COLUMNS].copy()
    assert_feature_matrix_safe(list(features.columns))
    if features.isna().any().any():
        nan_columns = features.columns[features.isna().any()].tolist()
        raise ValueError(f"Valeurs manquantes dans les features autorisees : {nan_columns}")

    cv = GroupKFold(n_splits=N_SPLITS)
    model_specs = {
        "dummy_most_frequent": {
            "label": "DummyClassifier (toujours classe majoritaire)",
            "estimator": DummyClassifier(strategy="most_frequent"),
            "columns": FEATURE_COLUMNS,
        },
        "logistic_distance_straight": {
            "label": "Regression logistique (distance_straight seule)",
            "estimator": Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("model", LogisticRegression(max_iter=2000, random_state=RANDOM_STATE)),
                ]
            ),
            "columns": ["distance_straight"],
        },
        "logistic_12_features": {
            "label": "Regression logistique (12 features)",
            "estimator": Pipeline(
                [
                    ("scaler", StandardScaler()),
                    ("model", LogisticRegression(max_iter=2000, random_state=RANDOM_STATE)),
                ]
            ),
            "columns": FEATURE_COLUMNS,
        },
        "hist_gradient_boosting_12_features": {
            "label": "HistGradientBoostingClassifier (12 features)",
            "estimator": HistGradientBoostingClassifier(max_iter=300, random_state=RANDOM_STATE),
            "columns": FEATURE_COLUMNS,
        },
    }

    fold_indices = list(cv.split(features, target, groups=groups))
    if len(fold_indices) != N_SPLITS:
        raise AssertionError(f"GroupKFold a produit {len(fold_indices)} plis au lieu de {N_SPLITS}.")

    scores: dict[str, dict[str, list[float]]] = {
        model_key: {metric_key: [] for metric_key in METRICS} for model_key in model_specs
    }
    fold_group_counts: list[dict[str, int]] = []
    for fold_number, (train_index, validation_index) in enumerate(fold_indices, start=1):
        validation_target = target.iloc[validation_index]
        if validation_target.nunique() != 2:
            raise ValueError(f"Le pli {fold_number} ne contient pas les deux classes.")
        fold_group_counts.append(
            {
                "fold": fold_number,
                "train_rows": int(len(train_index)),
                "validation_rows": int(len(validation_index)),
                "train_seeds": int(groups.iloc[train_index].nunique()),
                "validation_seeds": int(groups.iloc[validation_index].nunique()),
                "validation_built": int(validation_target.sum()),
                "validation_failed": int((1 - validation_target).sum()),
            }
        )
        for model_key, spec in model_specs.items():
            model = clone(spec["estimator"])
            selected_features = features.loc[:, spec["columns"]]
            model.fit(selected_features.iloc[train_index], target.iloc[train_index])
            positive_probability = model.predict_proba(selected_features.iloc[validation_index])[:, 1]
            predicted_class = model.predict(selected_features.iloc[validation_index])
            scores[model_key]["roc_auc"].append(
                float(roc_auc_score(validation_target, positive_probability))
            )
            scores[model_key]["accuracy"].append(
                float(accuracy_score(validation_target, predicted_class))
            )
            scores[model_key]["average_precision"].append(
                float(average_precision_score(validation_target, positive_probability))
            )

    model_results = {
        model_key: {
            "label": spec["label"],
            "features": spec["columns"],
            "metrics": {
                metric_key: metric_summary(scores[model_key][metric_key])
                for metric_key in METRICS
            },
        }
        for model_key, spec in model_specs.items()
    }
    best_model_key = max(
        model_specs, key=lambda key: model_results[key]["metrics"]["roc_auc"]["mean"]
    )

    # L'importance est calculee sur chaque validation fold avec un modele entraine
    # uniquement sur son train fold : aucune importance sur les donnees d'apprentissage.
    best_spec = model_specs[best_model_key]
    feature_importance_by_fold: dict[str, list[float]] = {
        feature: [] for feature in best_spec["columns"]
    }
    for train_index, validation_index in fold_indices:
        best_model = clone(best_spec["estimator"])
        best_features = features.loc[:, best_spec["columns"]]
        best_model.fit(best_features.iloc[train_index], target.iloc[train_index])
        permutation = permutation_importance(
            best_model,
            best_features.iloc[validation_index],
            target.iloc[validation_index],
            scoring="roc_auc",
            n_repeats=PERMUTATION_REPEATS,
            random_state=RANDOM_STATE,
            n_jobs=3,
        )
        for feature, importance in zip(best_spec["columns"], permutation.importances_mean):
            feature_importance_by_fold[feature].append(float(importance))

    feature_importance = [
        {
            "feature": feature,
            "mean": float(np.mean(fold_importances)),
            "std": float(np.std(fold_importances, ddof=1)),
            "folds": fold_importances,
        }
        for feature, fold_importances in feature_importance_by_fold.items()
    ]
    feature_importance.sort(key=lambda item: item["mean"], reverse=True)

    control_key = "logistic_distance_straight"
    full_feature_keys = ["logistic_12_features", "hist_gradient_boosting_12_features"]
    best_full_feature_key = max(
        full_feature_keys,
        key=lambda key: model_results[key]["metrics"]["roc_auc"]["mean"],
    )
    control_auc = scores[control_key]["roc_auc"]
    full_auc = scores[best_full_feature_key]["roc_auc"]
    auc_deltas = [full - control for full, control in zip(full_auc, control_auc)]
    mean_auc_delta = float(np.mean(auc_deltas))
    better_folds = int(sum(delta > 0 for delta in auc_deltas))
    # Definition explicite de « nettement » avant lecture des resultats.
    clear_advantage = mean_auc_delta >= 0.02 and better_folds >= 4
    if clear_advantage:
        hypothesis_conclusion = (
            "OUI : le meilleur modele a 12 features depasse nettement le controle "
            "distance_straight selon le seuil fixe (gain moyen AUC >= 0.02 et "
            "amelioration sur au moins 4 plis)."
        )
    else:
        hypothesis_conclusion = (
            "NON : le meilleur modele a 12 features ne depasse pas nettement le "
            "controle distance_straight selon le seuil fixe. Dans ce protocole, "
            "cela montre que l'etage 1 plafonne faute d'information sur le terrain."
        )

    results = {
        "dataset": {
            "csv": str(CSV_PATH.relative_to(ROOT)),
            "rows_before_pairoor_exclusion": int(total_rows),
            "rows_removed_pairoor": int(removed_pairoor_rows),
            "rows_after_pairoor_exclusion": int(len(data)),
            "n_seeds": int(groups.nunique()),
            "built": int(target.sum()),
            "failed": int((1 - target).sum()),
        },
        "feature_policy": {
            "features_used": FEATURE_COLUMNS,
            "excluded_columns": EXCLUDED_COLUMNS,
            "excluded_columns_present_in_csv": [
                column for column in EXCLUDED_COLUMNS if column in data.columns
            ],
            "runtime_feature_matrix_assertion": "No excluded column and exactly the 12 allowed features.",
        },
        "cross_validation": {
            "splitter": "GroupKFold",
            "n_splits": N_SPLITS,
            "group_column": GROUP_COLUMN,
            "folds": fold_group_counts,
            "standard_deviation_ddof": 1,
        },
        "models": model_results,
        "best_model_by_mean_roc_auc": {
            "key": best_model_key,
            "label": model_specs[best_model_key]["label"],
        },
        "validation_permutation_importance": {
            "model_key": best_model_key,
            "scoring": "roc_auc",
            "n_repeats": PERMUTATION_REPEATS,
            "features": feature_importance,
        },
        "hypothesis_distance_straight_vs_12_features": {
            "control_model_key": control_key,
            "best_12_feature_model_key": best_full_feature_key,
            "auc_delta_by_fold": auc_deltas,
            "mean_auc_delta": mean_auc_delta,
            "std_auc_delta": float(np.std(auc_deltas, ddof=1)),
            "better_folds": better_folds,
            "n_folds": N_SPLITS,
            "clear_advantage_rule": "mean AUC delta >= 0.02 and AUC improves on at least 4 of 5 folds",
            "clearly_better": clear_advantage,
            "conclusion": hypothesis_conclusion,
        },
    }
    assert_all_finite(results)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(results, output_file, indent=2, ensure_ascii=False, allow_nan=False)
        output_file.write("\n")

    print("=== Baseline étage 1 du modèle hurdle : prédire built ===")
    print(f"CSV : {CSV_PATH.relative_to(ROOT)}")
    print(
        f"Lignes : {total_rows} au départ ; {removed_pairoor_rows} PAIROOR exclues ; "
        f"{len(data)} conservées ({int(target.sum())} construites, {int((1 - target).sum())} échecs)."
    )
    print(
        f"Découpage : GroupKFold(n_splits={N_SPLITS}, groups={GROUP_COLUMN}) ; "
        f"{groups.nunique()} graines."
    )
    print("Features utilisées (12, avant construction uniquement) : " + ", ".join(FEATURE_COLUMNS))
    print("Garde-fou anti-fuite : assertion runtime passée ; aucune colonne exclue n'est dans X.")
    print("")
    print("Résultats inter-plis de validation (moyenne +/- écart-type, ddof=1) :")
    for model_key, model_result in model_results.items():
        print(f"- {model_result['label']} :")
        for metric_key, metric_label in (
            ("roc_auc", "AUC ROC"),
            ("accuracy", "Accuracy"),
            ("average_precision", "Average precision"),
        ):
            print(f"  {metric_label} : {format_mean_std(model_result['metrics'][metric_key])}")
        print("  Par pli (AUC ROC, Accuracy, Average precision) :")
        for fold_index in range(N_SPLITS):
            print(
                f"    pli {fold_index + 1}: "
                f"{scores[model_key]['roc_auc'][fold_index]:.4f}, "
                f"{scores[model_key]['accuracy'][fold_index]:.4f}, "
                f"{scores[model_key]['average_precision'][fold_index]:.4f}"
            )
    print("")
    print(
        "Meilleur modèle (AUC ROC moyenne) : "
        f"{model_specs[best_model_key]['label']}."
    )
    print("Importance par permutation sur les validations (baisse d'AUC ROC, moyenne +/- écart-type) :")
    for item in feature_importance:
        print(f"- {item['feature']} : {item['mean']:.4f} +/- {item['std']:.4f}")
    print("")
    hypothesis = results["hypothesis_distance_straight_vs_12_features"]
    print("Hypothèse : le meilleur modèle à 12 features est-il nettement meilleur que distance_straight seule ?")
    print(f"- Modèle à 12 features retenu : {model_specs[best_full_feature_key]['label']}")
    print(
        f"- Delta AUC moyen (12 features - contrôle) : {mean_auc_delta:.4f} +/- "
        f"{hypothesis['std_auc_delta']:.4f} ; amélioration sur {better_folds}/{N_SPLITS} plis."
    )
    print(f"- Règle de décision : {hypothesis['clear_advantage_rule']}.")
    print(f"- Conclusion : {hypothesis_conclusion}")
    print(f"JSON écrit : {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
