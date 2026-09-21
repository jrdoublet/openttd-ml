#!/usr/bin/env python3
"""Etage 1 v3 : tester, a protocole fige, les nouvelles mesures de terrain.

La comparaison principale reste la regression logistique du baseline : c'est
la seule facon de savoir si une famille ajoute de l'information au 0,8567 v2,
plutot que de confondre ce test avec un changement de modele.
"""

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

# Reprise directe des constantes et du garde-fou du commit 732e6f1.  Son
# assertion d'egalite stricte reste executee pour BASE12 ; les blocs v3 ont en
# plus leur propre controle d'exclusion, car ils sont volontairement plus larges.
from phase3_stage1_baseline import (  # noqa: E402
    EXCLUDED_COLUMNS,
    FEATURE_COLUMNS as BASE12,
    RANDOM_STATE,
    assert_feature_matrix_safe,
)


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "phase2_hurdle_v3.csv"
OUTPUT_PATH = ROOT / "results" / "phase3_stage1_v3.json"

TARGET_COLUMN = "built"
GROUP_COLUMN = "seed"
FAILURE_REASON_COLUMN = "failure_reason"
N_SPLITS = 5
PERMUTATION_REPEATS = 30
V2_BASE12_AUC = 0.8567

# Ces mesures resumeraient le relief du corridor entier, sans le trou de
# couverture des anciennes variables terrain_* calculees seulement pour M.
CORRIDOR = [
    "corridor_dh",
    "corridor_water",
    "corridor_unbuildable",
    "corridor_max_water_run",
    "corridor_max_uphill_step",
]

# Les rayons et sorties sont disponibles pour chaque tentative. Les anciennes
# distances et cargaisons de gare restent exclues : elles fuient par absence.
GARE = [
    "station_radius_a",
    "station_radius_b",
    "station_radius_max",
    "station_outward_a",
    "station_outward_b",
    "station_outward_min",
]

# La sonde est une observation apres un premier effort de recherche ; elle ne
# doit donc jamais etre interpretee comme une prediction au tout debut.
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

# Ces neuf variables ne sont pas seulement exclues par principe : leur absence
# revele barrier_flag == M. Les garder ferait apprendre le mecanisme de mesure,
# pas la constructibilite.
ABSENCE_LEAK_COLUMNS = [
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

ALL_FEATURE_BLOCKS = {
    "BASE12": BASE12,
    "CORRIDOR": CORRIDOR,
    "GARE": GARE,
    "SONDE": SONDE,
}

METRICS = {
    "roc_auc": roc_auc_score,
    "accuracy": accuracy_score,
    "average_precision": average_precision_score,
}


def logistic_estimator() -> Pipeline:
    """Pipeline strictement identique au baseline fige."""
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=2000, random_state=RANDOM_STATE)),
        ]
    )


def assert_columns_safe(columns: list[str], context: str) -> None:
    """Etend le garde-fou v2 sans desserrer l'audit des fuites connues."""
    leaked_columns = sorted(set(columns).intersection(EXCLUDED_COLUMNS))
    assert not leaked_columns, (
        f"Fuite de donnees dans {context} : colonnes exclues presentes dans X : "
        f"{leaked_columns}"
    )
    assert len(columns) == len(set(columns)), f"Doublon de feature dans {context} : {columns}"


def assert_full_coverage(data: pd.DataFrame, columns: list[str], context: str) -> None:
    """Prouve que les gains ne proviennent pas d'un sous-ensemble de lignes."""
    missing_columns = [column for column in columns if column not in data.columns]
    assert not missing_columns, f"Colonnes absentes de {context} : {missing_columns}"
    incomplete = {
        column: int(data[column].notna().sum())
        for column in columns
        if int(data[column].notna().sum()) != len(data)
    }
    assert not incomplete, (
        f"Couverture incomplete dans {context} (attendu {len(data)}/{len(data)}) : "
        f"{incomplete}"
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


def format_paired_delta(delta: dict[str, float | list[float]]) -> str:
    sign = "+" if float(delta["mean"]) >= 0 else ""
    return (
        f"{sign}{float(delta['mean']):.4f} +/- {float(delta['std']):.4f} d'AUC, "
        f"{int(delta['better_folds'])} plis sur {N_SPLITS}"
    )


def assert_all_finite(value: object, location: str = "resultat") -> None:
    """Refuse un JSON silencieusement inutilisable avec NaN ou Infinity."""
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
    required_metadata = [TARGET_COLUMN, GROUP_COLUMN, FAILURE_REASON_COLUMN]
    missing_metadata = [column for column in required_metadata if column not in data.columns]
    if missing_metadata:
        raise ValueError(f"Colonnes de metadonnees obligatoires manquantes : {missing_metadata}")

    total_rows = len(data)
    data = data.loc[data[FAILURE_REASON_COLUMN] != "PAIROOR"].copy()
    removed_pairoor_rows = total_rows - len(data)
    assert len(data) == 1997, f"1997 lignes attendues apres exclusion PAIROOR, {len(data)} trouvees."
    assert not (data[FAILURE_REASON_COLUMN] == "PAIROOR").any(), (
        "Des lignes PAIROOR restent dans les donnees d'evaluation."
    )

    assert "barrier_flag" in data.columns, "barrier_flag manque pour le controle de fuite par absence."
    barrier_m = data["barrier_flag"].eq("M")
    assert int(barrier_m.sum()) == 1615, (
        f"1615 lignes barrier_flag == M attendues, {int(barrier_m.sum())} trouvees."
    )
    for column in ABSENCE_LEAK_COLUMNS:
        assert column in data.columns, f"Colonne de fuite par absence manquante : {column}"
        observed = data[column].notna()
        assert int(observed.sum()) == 1615 and observed.equals(barrier_m), (
            f"{column} devrait couvrir exactement les 1615 lignes barrier_flag == M "
            "et aucune autre."
        )

    # Le garde-fou original est intentionnellement appele tel quel sur BASE12.
    assert_feature_matrix_safe(BASE12)
    assert_columns_safe(BASE12, "BASE12")
    for block_name, block_columns in ALL_FEATURE_BLOCKS.items():
        assert_columns_safe(block_columns, block_name)
        assert_full_coverage(data, block_columns, block_name)

    all_used_columns = [column for block in ALL_FEATURE_BLOCKS.values() for column in block]
    station_plans = ["station_plans_a", "station_plans_b"]
    assert not set(station_plans).intersection(all_used_columns), (
        "station_plans_a et station_plans_b sont satures et ne doivent pas etre utilises."
    )
    for column in station_plans:
        assert column in data.columns, f"Colonne de controle absente : {column}"
        assert data[column].nunique(dropna=False) == 1, (
            f"{column} devrait etre constante (saturation a 12), "
            f"mais a {data[column].nunique(dropna=False)} valeurs."
        )

    target = data[TARGET_COLUMN].astype(str).str.strip().str.lower().map({"true": 1, "false": 0})
    if target.isna().any():
        unexpected_values = sorted(data.loc[target.isna(), TARGET_COLUMN].astype(str).unique())
        raise ValueError(f"Valeurs inattendues dans {TARGET_COLUMN} : {unexpected_values}")
    target = target.astype(int)
    groups = data[GROUP_COLUMN]

    # Une matrice commune conserve exactement les memes lignes pour tous les
    # candidats. Chaque spec n'en prend qu'une projection par colonnes.
    features = data.loc[:, all_used_columns].copy()
    assert_columns_safe(list(features.columns), "matrice commune v3")
    assert not features.isna().any().any(), "Des valeurs manquantes restent dans la matrice v3."

    model_specs = {
        "dummy_most_frequent": {
            "label": "DummyClassifier (toujours classe majoritaire)",
            "estimator": DummyClassifier(strategy="most_frequent"),
            "columns": BASE12,
            "role": "controle",
        },
        "logistic_distance_straight": {
            "label": "Regression logistique (distance_straight seule)",
            "estimator": logistic_estimator(),
            "columns": ["distance_straight"],
            "role": "controle",
        },
        "logistic_base12": {
            "label": "Regression logistique (BASE12)",
            "estimator": logistic_estimator(),
            "columns": BASE12,
            "role": "baseline",
        },
        "hist_gradient_boosting_base12": {
            "label": "HistGradientBoostingClassifier (BASE12)",
            "estimator": HistGradientBoostingClassifier(max_iter=300, random_state=RANDOM_STATE),
            "columns": BASE12,
            "role": "controle_modele",
        },
        "logistic_base12_corridor": {
            "label": "Regression logistique (BASE12 + CORRIDOR)",
            "estimator": logistic_estimator(),
            "columns": BASE12 + CORRIDOR,
            "role": "candidat",
        },
        "logistic_base12_gare": {
            "label": "Regression logistique (BASE12 + GARE)",
            "estimator": logistic_estimator(),
            "columns": BASE12 + GARE,
            "role": "candidat",
        },
        "logistic_base12_corridor_gare": {
            "label": "Regression logistique (BASE12 + CORRIDOR + GARE)",
            "estimator": logistic_estimator(),
            "columns": BASE12 + CORRIDOR + GARE,
            "role": "candidat",
        },
        "logistic_base12_corridor_gare_sonde": {
            "label": "Regression logistique (BASE12 + CORRIDOR + GARE + SONDE)",
            "estimator": logistic_estimator(),
            "columns": BASE12 + CORRIDOR + GARE + SONDE,
            "role": "sonde",
        },
    }
    for model_key, spec in model_specs.items():
        assert_columns_safe(spec["columns"], model_key)
        assert_full_coverage(data, spec["columns"], model_key)

    cv = GroupKFold(n_splits=N_SPLITS)
    fold_indices = list(cv.split(features, target, groups=groups))
    assert len(fold_indices) == N_SPLITS, (
        f"GroupKFold a produit {len(fold_indices)} plis au lieu de {N_SPLITS}."
    )
    # Ces empreintes rendent explicite le pre-requis de comparaison appariee.
    fold_validation_indices = [tuple(int(index) for index in validation) for _, validation in fold_indices]
    assert len(set(fold_validation_indices)) == N_SPLITS, "Les validations GroupKFold ne sont pas distinctes."

    scores: dict[str, dict[str, list[float]]] = {
        key: {metric_key: [] for metric_key in METRICS} for key in model_specs
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
            # Chaque passage reutilise strictement les memes indices, sans split
            # local : un delta par pli est donc bien un delta apparie.
            assert tuple(int(index) for index in validation_index) == fold_validation_indices[fold_number - 1], (
                f"Indices de validation non apparies pour {model_key}, pli {fold_number}."
            )
            selected_features = features.loc[:, spec["columns"]]
            model = clone(spec["estimator"])
            model.fit(selected_features.iloc[train_index], target.iloc[train_index])
            positive_probability = model.predict_proba(selected_features.iloc[validation_index])[:, 1]
            predicted_class = model.predict(selected_features.iloc[validation_index])
            scores[model_key]["roc_auc"].append(float(roc_auc_score(validation_target, positive_probability)))
            scores[model_key]["accuracy"].append(float(accuracy_score(validation_target, predicted_class)))
            scores[model_key]["average_precision"].append(
                float(average_precision_score(validation_target, positive_probability))
            )

    model_results = {
        model_key: {
            "label": spec["label"],
            "features": spec["columns"],
            "role": spec["role"],
            "metrics": {
                metric_key: metric_summary(scores[model_key][metric_key])
                for metric_key in METRICS
            },
        }
        for model_key, spec in model_specs.items()
    }

    base_key = "logistic_base12"
    paired_keys = [
        "logistic_distance_straight",
        "logistic_base12_corridor",
        "logistic_base12_gare",
        "logistic_base12_corridor_gare",
        "logistic_base12_corridor_gare_sonde",
    ]
    paired_deltas: dict[str, dict[str, float | int | list[float]]] = {}
    base_auc = np.asarray(scores[base_key]["roc_auc"], dtype=float)
    for model_key in paired_keys:
        candidate_auc = np.asarray(scores[model_key]["roc_auc"], dtype=float)
        assert len(candidate_auc) == len(base_auc) == N_SPLITS, (
            f"Nombre de plis non apparie entre {model_key} et {base_key}."
        )
        differences = candidate_auc - base_auc
        paired_deltas[model_key] = {
            "reference_model_key": base_key,
            "auc_delta_by_fold": differences.tolist(),
            "mean": float(differences.mean()),
            "std": float(differences.std(ddof=1)),
            "better_folds": int((differences > 0).sum()),
            "n_folds": N_SPLITS,
        }

    # Comme dans le baseline, l'importance est mesuree hors echantillon. On la
    # limite au meilleur candidat sans sonde : la sonde repond a une autre
    # question temporelle et ne doit pas orienter le resultat principal.
    primary_keys = [key for key, spec in model_specs.items() if spec["role"] in {"baseline", "candidat"}]
    best_primary_key = max(
        primary_keys, key=lambda key: model_results[key]["metrics"]["roc_auc"]["mean"]
    )
    best_spec = model_specs[best_primary_key]
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

    base12_auc_summary = model_results[base_key]["metrics"]["roc_auc"]
    base12_v3_delta = float(base12_auc_summary["mean"] - V2_BASE12_AUC)
    assert 0.80 <= float(base12_auc_summary["mean"]) <= 0.90, (
        "AUC BASE12-v3 hors de la fourchette de cablage large [0.80, 0.90] : "
        f"{base12_auc_summary['mean']:.4f}"
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
            "base12": BASE12,
            "corridor": CORRIDOR,
            "gare": GARE,
            "sonde": SONDE,
            "excluded_columns": EXCLUDED_COLUMNS,
            "runtime_guards_exercised": {
                "baseline_assert_feature_matrix_safe": "BASE12 verified with frozen baseline assertion.",
                "excluded_columns": "Every effective model matrix checked against EXCLUDED_COLUMNS.",
                "absence_leaks": (
                    "The 6 station and 3 terrain excluded columns verified present only on "
                    "the 1615 barrier_flag == M rows."
                ),
                "full_coverage": "Every effective model feature checked at 1997/1997 rows.",
                "station_plans_constant_and_unused": "station_plans_a/b verified constant and absent from all feature lists.",
            },
        },
        "cross_validation": {
            "splitter": "GroupKFold",
            "n_splits": N_SPLITS,
            "group_column": GROUP_COLUMN,
            "random_state": RANDOM_STATE,
            "paired_comparison": (
                "One shared GroupKFold split list; every model uses the identical train and "
                "validation indices for every fold."
            ),
            "validation_index_sizes": [len(indices) for indices in fold_validation_indices],
            "folds": fold_group_counts,
            "standard_deviation_ddof": 1,
        },
        "models": model_results,
        "paired_auc_deltas_vs_logistic_base12": paired_deltas,
        "base12_v3_vs_v2": {
            "v3_auc": base12_auc_summary,
            "v2_auc": V2_BASE12_AUC,
            "v3_minus_v2": base12_v3_delta,
            "runtime_wiring_range_assertion": "0.80 <= BASE12 v3 mean AUC <= 0.90",
        },
        "validation_permutation_importance": {
            "model_key": best_primary_key,
            "scoring": "roc_auc",
            "n_repeats": PERMUTATION_REPEATS,
            "features": feature_importance,
        },
        "sonde_interpretation": {
            "model_key": "logistic_base12_corridor_gare_sonde",
            "cost": "La sonde exige deja environ 1,7 % du budget de recherche.",
            "scope": "Predire apres un debut d'effort, pas predire avant tout effort.",
        },
    }
    assert_all_finite(results)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(results, output_file, indent=2, ensure_ascii=False, allow_nan=False)
        output_file.write("\n")

    print("=== Etage 1 v3 du modele hurdle : nouvelles familles de features ===")
    print(f"CSV : {CSV_PATH.relative_to(ROOT)}")
    print(
        f"Lignes : {total_rows} au depart ; {removed_pairoor_rows} PAIROOR exclues ; "
        f"{len(data)} conservees ({int(target.sum())} construites, {int((1 - target).sum())} echecs)."
    )
    print(
        f"Decoupage apparie : GroupKFold(n_splits={N_SPLITS}, groups={GROUP_COLUMN}) ; "
        f"{groups.nunique()} graines ; memes indices pour tous les modeles."
    )
    print(
        "Garde-fous runtime passes : exclusions, fuite par absence 1615/1997, "
        "couverture 1997/1997, station_plans constants et inutilises."
    )
    print("")
    print("AUC ROC par pli (moyenne +/- ecart-type, ddof=1) :")
    for model_key, model_result in model_results.items():
        auc = model_result["metrics"]["roc_auc"]
        folds = ", ".join(f"{value:.4f}" for value in auc["folds"])
        print(f"- {model_result['label']} : {format_mean_std(auc)} ({folds})")
    print("")
    print("Ecarts apparies a Regression logistique (BASE12) :")
    for model_key in paired_keys:
        print(f"- {model_results[model_key]['label']} : {format_paired_delta(paired_deltas[model_key])}")
    print("")
    print(
        f"Controle de coherence BASE12 : v3 = {base12_auc_summary['mean']:.4f} ; "
        f"v2 = {V2_BASE12_AUC:.4f} ; delta v3-v2 = {base12_v3_delta:+.4f}."
    )
    sonde_delta = paired_deltas["logistic_base12_corridor_gare_sonde"]
    print(
        "SONDE (rapporte a part) : "
        f"{format_paired_delta(sonde_delta)}. La sonde exige deja environ 1,7 % du budget "
        "de recherche : elle predit apres un debut d'effort, pas avant tout effort."
    )
    print("Importance par permutation sur validations (30 repetitions) : " + model_results[best_primary_key]["label"])
    for item in feature_importance:
        print(f"- {item['feature']} : {item['mean']:.4f} +/- {item['std']:.4f}")
    print(f"JSON ecrit : {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
