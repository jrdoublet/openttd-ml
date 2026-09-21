#!/usr/bin/env python3
"""Baseline de l'etage 2 du modele hurdle : predire profit_ligne si construite.

Instant de decision : apres le pathfinding et avant la premiere mutation.  A la
difference de l'etage 1, les informations de gares et de terrain sont donc
autorisees : l'IA connait alors le chemin et les plans de gare, sans avoir
encore construit quoi que ce soit.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "phase2_hurdle_v2.csv"
OUTPUT_PATH = ROOT / "results" / "phase3_stage2_baseline.json"

TARGET_COLUMN = "profit_ligne"
GROUP_COLUMN = "seed"
FAILURE_REASON_COLUMN = "failure_reason"
N_SPLITS = 5
RANDOM_STATE = 42
PERMUTATION_REPEATS = 30

# Les variables brutes connues a l'instant de decision retenu.  C'est
# volontairement plus large que l'etage 1 : les mesures de gare et de terrain
# sont connues apres pathfinding, mais avant toute pose ou achat.
BASE_FEATURE_COLUMNS = [
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
    "engine_price",
    "engine_running_cost",
    "estimated_cost",
    "station_a_town_dist",
    "station_b_town_dist",
    "station_a_cargo_prod",
    "station_a_cargo_acc",
    "station_b_cargo_prod",
    "station_b_cargo_acc",
    "terrain_dh",
    "terrain_water",
    "terrain_unbuildable",
]

# Le profit depend du remplissage, rapport demande/capacite.  Production et
# acceptation sont deux proxies distincts de la demande ; les deux ratios sont
# donc testes, puis retires ensemble dans une ablation pour ne pas les tenir
# pour acquis. convoy_capacity est strictement positif dans les donnees OK.
RATIO_FEATURE_COLUMNS = [
    "cargo_production_per_convoy_capacity",
    "cargo_acceptance_per_convoy_capacity",
]
FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + RATIO_FEATURE_COLUMNS

# Liste explicite des exclusions de l'audit anti-fuite. Elle est aussi testee
# contre X juste avant l'apprentissage. town_a et town_b ne sont pas des
# features demandees : ce sont des identifiants de villes, non generalisables.
EXCLUDED_COLUMNS = [
    "attempt_id",
    "line_index",
    "town_a",
    "town_b",
    "stagger_slot",
    "wagon_capacity",
    "built",
    "stage",
    "failure_reason",
    "barrier_flag",
    "first_mutation_tick",
    "profit_ligne",
    "sum_profit_last_year",
    "amortization_annual",
    "vehicle_amortization_annual",
    "infra_amortization_annual",
    "construction_cost",
    "infra_cost",
    "vehicle_cost",
    "n_lead_vehicles",
    "avg_max_age_years",
]


def assert_feature_matrix_safe(columns: list[str]) -> None:
    """Garde-fou runtime : une fuite connue ne doit jamais revenir dans X."""
    leaked_columns = sorted(set(columns).intersection(EXCLUDED_COLUMNS))
    assert not leaked_columns, (
        "Fuite de donnees : colonnes exclues presentes dans la matrice de "
        f"features : {leaked_columns}"
    )
    assert columns == FEATURE_COLUMNS, (
        "La matrice de features ne contient pas exactement les 25 variables "
        f"autorisees : {columns}"
    )


def metric_summary(values: list[float]) -> dict[str, float | list[float]]:
    values_array = np.asarray(values, dtype=float)
    return {
        "mean": float(values_array.mean()),
        "std": float(values_array.std(ddof=1)),
        "median": float(np.median(values_array)),
        "folds": [float(value) for value in values_array],
    }


def format_mean_std(summary: dict[str, float | list[float]]) -> str:
    return f"{summary['mean']:.0f} +/- {summary['std']:.0f}"


def signed_sqrt(values: np.ndarray) -> np.ndarray:
    """Transformation monotone et reversible, compatible avec les profits negatifs."""
    return np.sign(values) * np.sqrt(np.abs(values))


def inverse_signed_sqrt(values: np.ndarray) -> np.ndarray:
    return np.sign(values) * np.square(values)


def with_target_transform(estimator: object, use_signed_sqrt: bool) -> object:
    if not use_signed_sqrt:
        return estimator
    return TransformedTargetRegressor(
        regressor=estimator,
        func=signed_sqrt,
        inverse_func=inverse_signed_sqrt,
        check_inverse=False,
    )


def make_model_specs() -> dict[str, dict[str, object]]:
    """Modeles fixes de baseline, sans recherche d'hyperparametres."""
    full_specs: dict[str, dict[str, object]] = {}
    control_specs: dict[str, dict[str, object]] = {}
    estimator_factories = {
        "linear": lambda: Pipeline(
            [("scaler", StandardScaler()), ("model", LinearRegression())]
        ),
        "ridge": lambda: Pipeline(
            [("scaler", StandardScaler()), ("model", Ridge(alpha=1.0))]
        ),
        "hist_gradient_boosting": lambda: HistGradientBoostingRegressor(
            max_iter=300, random_state=RANDOM_STATE
        ),
    }
    labels = {
        "linear": "Regression lineaire",
        "ridge": "Ridge (alpha=1.0)",
        "hist_gradient_boosting": "HistGradientBoostingRegressor",
    }
    for family, factory in estimator_factories.items():
        for transform_key, use_transform, transform_label in (
            ("raw", False, "cible brute"),
            ("signed_sqrt", True, "cible racine signee"),
        ):
            full_key = f"{family}_25_features_{transform_key}"
            full_specs[full_key] = {
                "label": f"{labels[family]} (25 features, {transform_label})",
                "estimator": with_target_transform(factory(), use_transform),
                "columns": FEATURE_COLUMNS,
                "family": family,
                "target_transform": transform_key,
            }
            control_key = f"{family}_distance_manhattan_{transform_key}"
            control_specs[control_key] = {
                "label": f"{labels[family]} (distance_manhattan seule, {transform_label})",
                "estimator": with_target_transform(factory(), use_transform),
                "columns": ["distance_manhattan"],
                "family": family,
                "target_transform": transform_key,
            }
    return {
        "dummy_median": {
            "label": "DummyRegressor (mediane du train fold)",
            "estimator": DummyRegressor(strategy="median"),
            "columns": FEATURE_COLUMNS,
            "family": "dummy",
            "target_transform": "none",
        },
        **full_specs,
        **control_specs,
    }


def assert_all_finite(value: object, location: str = "resultat") -> None:
    """Refuse d'ecrire du JSON contenant NaN ou Infinity."""
    if isinstance(value, dict):
        for key, child in value.items():
            assert_all_finite(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_all_finite(child, f"{location}[{index}]")
    elif isinstance(value, float) and not np.isfinite(value):
        raise ValueError(f"Valeur non finie dans {location}: {value}")


def main() -> None:
    data = pd.read_csv(CSV_PATH)
    required_columns = [TARGET_COLUMN, GROUP_COLUMN, FAILURE_REASON_COLUMN, *BASE_FEATURE_COLUMNS]
    missing_columns = [column for column in required_columns if column not in data.columns]
    if missing_columns:
        raise ValueError(f"Colonnes obligatoires manquantes : {missing_columns}")

    total_rows = len(data)
    data = data.loc[data[FAILURE_REASON_COLUMN] == "OK"].copy()
    if len(data) != 1551:
        raise AssertionError(f"1551 lignes OK attendues, {len(data)} trouvees.")
    if not (data[FAILURE_REASON_COLUMN] == "OK").all():
        raise AssertionError("Des lignes non construites restent dans les donnees d'etage 2.")
    if not data["built"].astype(str).str.strip().str.lower().eq("true").all():
        raise AssertionError("Toutes les lignes OK doivent etre construites (built == true).")
    if (data["convoy_capacity"] <= 0).any():
        raise ValueError("convoy_capacity doit etre strictement positif pour les ratios.")

    data["cargo_production_per_convoy_capacity"] = (
        data["station_a_cargo_prod"] + data["station_b_cargo_prod"]
    ) / data["convoy_capacity"]
    data["cargo_acceptance_per_convoy_capacity"] = (
        data["station_a_cargo_acc"] + data["station_b_cargo_acc"]
    ) / data["convoy_capacity"]

    target = data[TARGET_COLUMN].astype(float)
    groups = data[GROUP_COLUMN]
    features = data.loc[:, FEATURE_COLUMNS].copy()
    assert_feature_matrix_safe(list(features.columns))
    if features.isna().any().any():
        nan_columns = features.columns[features.isna().any()].tolist()
        raise ValueError(f"Valeurs manquantes dans les features autorisees : {nan_columns}")
    if target.isna().any():
        raise ValueError(f"Valeurs manquantes dans {TARGET_COLUMN}.")

    cv = GroupKFold(n_splits=N_SPLITS)
    model_specs = make_model_specs()
    fold_indices = list(cv.split(features, target, groups=groups))
    if len(fold_indices) != N_SPLITS:
        raise AssertionError(f"GroupKFold a produit {len(fold_indices)} plis au lieu de {N_SPLITS}.")

    scores: dict[str, dict[str, list[float]]] = {
        key: {"mae": [], "r2": []} for key in model_specs
    }
    fold_group_counts: list[dict[str, int]] = []
    for fold_number, (train_index, validation_index) in enumerate(fold_indices, start=1):
        fold_group_counts.append(
            {
                "fold": fold_number,
                "train_rows": int(len(train_index)),
                "validation_rows": int(len(validation_index)),
                "train_seeds": int(groups.iloc[train_index].nunique()),
                "validation_seeds": int(groups.iloc[validation_index].nunique()),
            }
        )
        for model_key, spec in model_specs.items():
            selected_features = features.loc[:, spec["columns"]]
            model = clone(spec["estimator"])
            model.fit(selected_features.iloc[train_index], target.iloc[train_index])
            prediction = model.predict(selected_features.iloc[validation_index])
            scores[model_key]["mae"].append(
                float(mean_absolute_error(target.iloc[validation_index], prediction))
            )
            scores[model_key]["r2"].append(
                float(r2_score(target.iloc[validation_index], prediction))
            )

    dummy_mae = np.asarray(scores["dummy_median"]["mae"], dtype=float)
    model_results: dict[str, dict[str, object]] = {}
    for model_key, spec in model_specs.items():
        mae_reduction = 1.0 - np.asarray(scores[model_key]["mae"], dtype=float) / dummy_mae
        model_results[model_key] = {
            "label": spec["label"],
            "features": spec["columns"],
            "family": spec["family"],
            "target_transform": spec["target_transform"],
            "metrics": {
                "mae": metric_summary(scores[model_key]["mae"]),
                "r2": metric_summary(scores[model_key]["r2"]),
                "mae_reduction_vs_dummy_median": metric_summary(mae_reduction.tolist()),
            },
        }

    full_model_keys = [key for key in model_specs if "_25_features_" in key]
    control_model_keys = [key for key in model_specs if "_distance_manhattan_" in key]
    best_full_model_key = min(
        full_model_keys, key=lambda key: model_results[key]["metrics"]["mae"]["mean"]
    )
    best_control_model_key = min(
        control_model_keys, key=lambda key: model_results[key]["metrics"]["mae"]["mean"]
    )

    # Importance uniquement sur les validations, avec la perte de score
    # neg_mean_absolute_error : une importance positive augmente donc la MAE.
    best_spec = model_specs[best_full_model_key]
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
            scoring="neg_mean_absolute_error",
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

    # Ablation appariee des deux ratios sur le meilleur modele complet : meme
    # famille, meme transformation et memes plis pour isoler leur apport.
    ablation_columns = [column for column in FEATURE_COLUMNS if column not in RATIO_FEATURE_COLUMNS]
    ratio_ablation_mae: list[float] = []
    ratio_ablation_r2: list[float] = []
    for train_index, validation_index in fold_indices:
        ablation_model = clone(best_spec["estimator"])
        ablation_features = features.loc[:, ablation_columns]
        ablation_model.fit(ablation_features.iloc[train_index], target.iloc[train_index])
        prediction = ablation_model.predict(ablation_features.iloc[validation_index])
        ratio_ablation_mae.append(
            float(mean_absolute_error(target.iloc[validation_index], prediction))
        )
        ratio_ablation_r2.append(float(r2_score(target.iloc[validation_index], prediction)))
    full_mae = np.asarray(scores[best_full_model_key]["mae"], dtype=float)
    ablation_mae = np.asarray(ratio_ablation_mae, dtype=float)
    ratio_mae_gain = ablation_mae - full_mae

    control_mae = np.asarray(scores[best_control_model_key]["mae"], dtype=float)
    full_vs_control_gain = control_mae - full_mae
    full_vs_control_relative_gain = full_vs_control_gain / control_mae

    results = {
        "dataset": {
            "csv": str(CSV_PATH.relative_to(ROOT)),
            "rows_before_ok_filter": int(total_rows),
            "rows_after_ok_filter": int(len(data)),
            "n_seeds": int(groups.nunique()),
            "target": TARGET_COLUMN,
            "target_summary": {
                "min": float(target.min()),
                "q1": float(target.quantile(0.25)),
                "median": float(target.median()),
                "q3": float(target.quantile(0.75)),
                "max": float(target.max()),
                "mean": float(target.mean()),
                "std": float(target.std(ddof=1)),
                "negative_rows": int((target < 0).sum()),
            },
        },
        "feature_policy": {
            "decision_time": "Apres pathfinding, avant la premiere mutation.",
            "difference_from_stage1": (
                "Les features de gares et de terrain sont autorisees car connues "
                "apres pathfinding mais avant construction."
            ),
            "base_features_used": BASE_FEATURE_COLUMNS,
            "derived_features_used": RATIO_FEATURE_COLUMNS,
            "derived_feature_rationale": (
                "Production et acceptation totales divisees par convoy_capacity, "
                "pour rendre observable un proxy de demande/capacite."
            ),
            "excluded_columns": EXCLUDED_COLUMNS,
            "excluded_columns_present_in_csv": [
                column for column in EXCLUDED_COLUMNS if column in data.columns
            ],
            "runtime_feature_matrix_assertion": (
                "No excluded column and exactly the 23 base plus 2 derived allowed features."
            ),
        },
        "target_transform": {
            "raw": "Aucune transformation.",
            "signed_sqrt": (
                "sign(y) * sqrt(abs(y)), inverse sign(z) * z**2 ; attenue "
                "l'asymetrie tout en gardant les 17.5% environ de profits negatifs."
            ),
        },
        "cross_validation": {
            "splitter": "GroupKFold",
            "n_splits": N_SPLITS,
            "group_column": GROUP_COLUMN,
            "folds": fold_group_counts,
            "standard_deviation_ddof": 1,
        },
        "models": model_results,
        "best_full_model_by_mean_mae": {
            "key": best_full_model_key,
            "label": model_specs[best_full_model_key]["label"],
        },
        "best_distance_manhattan_control_by_mean_mae": {
            "key": best_control_model_key,
            "label": model_specs[best_control_model_key]["label"],
        },
        "validation_permutation_importance": {
            "model_key": best_full_model_key,
            "scoring": "neg_mean_absolute_error",
            "interpretation": "Importance positive = hausse de MAE apres permutation.",
            "n_repeats": PERMUTATION_REPEATS,
            "features": feature_importance,
        },
        "hypothesis_demand_capacity_ratios": {
            "evaluated_on_model_key": best_full_model_key,
            "ablation_features": ablation_columns,
            "full_model_mae": metric_summary(full_mae.tolist()),
            "without_ratios_mae": metric_summary(ratio_ablation_mae),
            "mae_gain_by_fold_without_minus_with_ratios": ratio_mae_gain.tolist(),
            "mae_gain": metric_summary(ratio_mae_gain.tolist()),
            "relative_mae_gain_vs_without_ratios": metric_summary(
                (ratio_mae_gain / ablation_mae).tolist()
            ),
            "without_ratios_r2": metric_summary(ratio_ablation_r2),
        },
        "hypothesis_full_features_vs_distance_manhattan": {
            "full_model_key": best_full_model_key,
            "control_model_key": best_control_model_key,
            "full_model_mae": metric_summary(full_mae.tolist()),
            "control_mae": metric_summary(control_mae.tolist()),
            "mae_gain_by_fold_control_minus_full": full_vs_control_gain.tolist(),
            "mae_gain": metric_summary(full_vs_control_gain.tolist()),
            "relative_mae_gain_vs_control": metric_summary(full_vs_control_relative_gain.tolist()),
            "better_folds": int((full_vs_control_gain > 0).sum()),
            "n_folds": N_SPLITS,
            "interpretation": "Un gain positif signifie que le modele complet a une MAE plus faible.",
        },
    }
    assert_all_finite(results)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(results, output_file, indent=2, ensure_ascii=False, allow_nan=False)
        output_file.write("\n")

    print("=== Baseline étage 2 du modèle hurdle : prédire profit_ligne si construite ===")
    print(f"CSV : {CSV_PATH.relative_to(ROOT)}")
    print(f"Lignes : {total_rows} au départ ; {len(data)} OK (construites) conservées.")
    print(
        f"Découpage : GroupKFold(n_splits={N_SPLITS}, groups={GROUP_COLUMN}) ; "
        f"{groups.nunique()} graines."
    )
    print("Instant de décision : après pathfinding, avant première mutation.")
    print(
        "Features : 23 brutes (dont gares/terrain post-pathfinding) + 2 ratios "
        "demande/capacité."
    )
    print("Garde-fou anti-fuite : assertion runtime passée ; aucune colonne exclue n'est dans X.")
    print("")
    print("Résultats inter-plis de validation (moyenne +/- écart-type, ddof=1) :")
    for model_key, model_result in model_results.items():
        metrics = model_result["metrics"]
        print(f"- {model_result['label']} :")
        print(f"  MAE : {format_mean_std(metrics['mae'])} ; médiane plis {metrics['mae']['median']:.0f}")
        print(f"  R² : {metrics['r2']['mean']:.4f} +/- {metrics['r2']['std']:.4f}")
        print(
            "  Réduction MAE vs Dummy médiane : "
            f"{metrics['mae_reduction_vs_dummy_median']['mean'] * 100:.2f}% +/- "
            f"{metrics['mae_reduction_vs_dummy_median']['std'] * 100:.2f}%"
        )
        print("  Par pli (MAE, R²) :")
        for fold_index in range(N_SPLITS):
            print(
                f"    pli {fold_index + 1}: {scores[model_key]['mae'][fold_index]:.0f}, "
                f"{scores[model_key]['r2'][fold_index]:.4f}"
            )
    print("")
    print(f"Meilleur modèle complet (MAE moyenne) : {model_specs[best_full_model_key]['label']}.")
    print("Importance par permutation sur les validations (hausse de MAE, moyenne +/- écart-type) :")
    for item in feature_importance:
        print(f"- {item['feature']} : {item['mean']:.0f} +/- {item['std']:.0f}")
    print("")
    ratio_hypothesis = results["hypothesis_demand_capacity_ratios"]
    print("Hypothèse : les ratios demande/capacité apportent-ils quelque chose ?")
    print(f"- Modèle évalué : {model_specs[best_full_model_key]['label']}")
    print(
        f"- MAE avec ratios : {ratio_hypothesis['full_model_mae']['mean']:.0f} +/- "
        f"{ratio_hypothesis['full_model_mae']['std']:.0f} ; sans ratios : "
        f"{ratio_hypothesis['without_ratios_mae']['mean']:.0f} +/- "
        f"{ratio_hypothesis['without_ratios_mae']['std']:.0f}."
    )
    print(
        f"- Gain MAE (sans - avec) : {ratio_hypothesis['mae_gain']['mean']:.0f} +/- "
        f"{ratio_hypothesis['mae_gain']['std']:.0f}, soit "
        f"{ratio_hypothesis['relative_mae_gain_vs_without_ratios']['mean'] * 100:.2f}% "
        "du modèle sans ratios."
    )
    print("")
    comparison = results["hypothesis_full_features_vs_distance_manhattan"]
    print("Comparaison explicite : modèle complet vs contrôle distance_manhattan seule")
    print(f"- Modèle complet : {model_specs[best_full_model_key]['label']}")
    print(f"- Contrôle : {model_specs[best_control_model_key]['label']}")
    print(
        f"- MAE complète : {comparison['full_model_mae']['mean']:.0f} +/- "
        f"{comparison['full_model_mae']['std']:.0f} ; contrôle : "
        f"{comparison['control_mae']['mean']:.0f} +/- {comparison['control_mae']['std']:.0f}."
    )
    print(
        f"- Gain MAE (contrôle - complet) : {comparison['mae_gain']['mean']:.0f} +/- "
        f"{comparison['mae_gain']['std']:.0f}, soit "
        f"{comparison['relative_mae_gain_vs_control']['mean'] * 100:.2f}% ; "
        f"meilleur sur {comparison['better_folds']}/{N_SPLITS} plis."
    )
    print(f"JSON écrit : {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
