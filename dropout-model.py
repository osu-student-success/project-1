from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = ROOT / "models" / "dropout-rf-fakedata.joblib"


def _load_sibling(filename: str):
    path = ROOT / filename
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_dataset = _load_sibling("generate-dataset.py")
DEFAULT_DATA = _dataset.DEFAULT_PATH
generate = _dataset.generate

TARGET = "dropped_out"
ID_COLUMN = "student_id"
CATEGORICAL = ["hometown", "major", "minor"]
NUMERIC = [
    "gpa",
    "credits_fall",
    "credits_winter",
    "credits_spring",
    "fafsa",
    "parents_graduated_college",
    "changed_major",
    "changed_minor",
    "classes_dropped",
    "hours_worked_per_week",
    "lives_on_campus",
]
FEATURES = CATEGORICAL + NUMERIC

SCENARIOS = {
    "Strong freshman": {
        "gpa": 3.82,
        "credits_fall": 16,
        "credits_winter": 15,
        "credits_spring": 16,
        "hometown": "Ann Arbor, MI",
        "fafsa": 1,
        "parents_graduated_college": 1,
        "major": "Computer Science",
        "minor": "Mathematics",
        "changed_major": 0,
        "changed_minor": 0,
        "classes_dropped": 0,
        "hours_worked_per_week": 6,
        "lives_on_campus": 1,
    },
    "At-risk freshman": {
        "gpa": 1.74,
        "credits_fall": 11,
        "credits_winter": 6,
        "credits_spring": 8,
        "hometown": "Flint, MI",
        "fafsa": 0,
        "parents_graduated_college": 0,
        "major": "Engineering",
        "minor": "None",
        "changed_major": 1,
        "changed_minor": 0,
        "classes_dropped": 4,
        "hours_worked_per_week": 28,
        "lives_on_campus": 0,
    },
}


def load_students(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"No dataset at {path}. Generating one.")
        generate(path)

    frame = pd.read_csv(path)
    missing = [column for column in FEATURES + [TARGET] if column not in frame.columns]
    if missing:
        missing_list = ", ".join(missing)
        raise SystemExit(f"Dataset is missing columns: {missing_list}")
    return frame


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categories",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL,
            ),
            ("numbers", "passthrough", NUMERIC),
        ]
    )
    forest = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline([("preprocess", preprocessor), ("forest", forest)])


def train(data_path: Path, model_path: Path) -> tuple[Pipeline, dict, pd.DataFrame]:
    frame = load_students(data_path)
    features = frame[FEATURES]
    target = frame[TARGET].astype(int)

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.2,
        random_state=42,
        stratify=target,
    )

    pipeline = build_pipeline()
    pipeline.fit(x_train, y_train)

    probabilities = pipeline.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    metrics = {
        "rows": int(len(frame)),
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "dropout_rate": float(target.mean()),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "report": classification_report(
            y_test,
            predictions,
            target_names=["stayed", "dropped out"],
            digits=2,
        ),
    }

    held_out = x_test.copy()
    held_out[ID_COLUMN] = frame.loc[x_test.index, ID_COLUMN].to_numpy()
    held_out["actual_dropped_out"] = y_test.to_numpy()
    held_out["dropout_likelihood_pct"] = (probabilities * 100).round(1)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipeline, "features": FEATURES}, model_path)
    return pipeline, metrics, held_out


def load_pipeline(model_path: Path, data_path: Path) -> Pipeline:
    if not model_path.exists():
        print(f"No saved model at {model_path}. Training one first.")
        pipeline, _, _ = train(data_path, model_path)
        return pipeline

    payload = joblib.load(model_path)
    return payload["pipeline"]


def dropout_percent(pipeline: Pipeline, student: dict) -> float:
    missing = [feature for feature in FEATURES if feature not in student]
    if missing:
        missing_list = ", ".join(missing)
        raise SystemExit(f"Student record is missing: {missing_list}")

    row = pd.DataFrame([{feature: student[feature] for feature in FEATURES}])
    # A lone missing minor would otherwise become a numeric column and break encoding.
    for column in CATEGORICAL:
        row[column] = row[column].astype(object)
    probability = float(pipeline.predict_proba(row)[0, 1])
    return round(probability * 100, 1)


def top_importances(pipeline: Pipeline, limit: int = 8) -> list[tuple[str, float]]:
    preprocessor = pipeline.named_steps["preprocess"]
    forest = pipeline.named_steps["forest"]
    names = preprocessor.get_feature_names_out()
    ranked = sorted(
        zip(names, forest.feature_importances_),
        key=lambda item: item[1],
        reverse=True,
    )
    cleaned = []
    for name, score in ranked[:limit]:
        label = str(name).split("__", 1)[-1]
        cleaned.append((label, float(score)))
    return cleaned


def print_training_report(metrics: dict, pipeline: Pipeline, held_out: pd.DataFrame) -> None:
    print(f"Students: {metrics['rows']}  |  trained on {metrics['train_rows']}  |  tested on {metrics['test_rows']}")
    print(f"Dataset dropout rate: {metrics['dropout_rate']:.1%}")
    print(f"Held-out accuracy: {metrics['accuracy']:.1%}")
    print(f"Held-out ROC-AUC: {metrics['roc_auc']:.3f}")
    print("\nClassification report:")
    print(metrics["report"].rstrip())

    print("\nStrongest features:")
    for name, score in top_importances(pipeline):
        print(f"  {name:<32} {score:.3f}")

    print("\nExample students:")
    for label, student in SCENARIOS.items():
        percent = dropout_percent(pipeline, student)
        print(f"  {label}: {percent:.1f}% likelihood of dropping out")

    ranked = held_out.sort_values("dropout_likelihood_pct", ascending=False)
    print("\nHighest held-out likelihoods:")
    _print_held_out(ranked.head(3))
    print("Lowest held-out likelihoods:")
    _print_held_out(ranked.tail(3))


def _print_held_out(frame: pd.DataFrame) -> None:
    for _, row in frame.iterrows():
        outcome = "dropped out" if row["actual_dropped_out"] else "stayed"
        print(
            f"  id {int(row[ID_COLUMN])}: {row['dropout_likelihood_pct']:.1f}%  "
            f"GPA {row['gpa']:.2f}, {int(row['classes_dropped'])} classes dropped, "
            f"actual {outcome}"
        )


def parse_bool(value: str) -> int:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return 1
    if normalized in {"0", "false", "no", "n"}:
        return 0
    raise argparse.ArgumentTypeError("expected true/false, yes/no, or 1/0")


def student_from_args(args: argparse.Namespace) -> dict:
    if args.json:
        payload = json.loads(args.json)
        for column in NUMERIC:
            if column in payload and column != "gpa":
                payload[column] = int(payload[column])
        return payload

    student = {
        "gpa": args.gpa,
        "credits_fall": args.credits_fall,
        "credits_winter": args.credits_winter,
        "credits_spring": args.credits_spring,
        "hometown": args.hometown,
        "fafsa": args.fafsa,
        "parents_graduated_college": args.parents_graduated,
        "major": args.major,
        "minor": args.minor,
        "changed_major": args.changed_major,
        "changed_minor": args.changed_minor,
        "classes_dropped": args.classes_dropped,
        "hours_worked_per_week": args.hours_worked,
        "lives_on_campus": args.lives_on_campus,
    }
    missing = [name for name, value in student.items() if value is None]
    if missing:
        missing_list = ", ".join(missing)
        raise SystemExit(f"Predict needs every student field. Missing: {missing_list}")
    return student


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Estimate college dropout likelihood with a random forest.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Path to the student CSV.")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="Where to save or load the model.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("train", help="Generate data if needed, train, and print example percentages.")

    predict = subparsers.add_parser("predict", help="Score one student and print a dropout percentage.")
    predict.add_argument("--json", help="Student features as one JSON object.")
    predict.add_argument("--gpa", type=float)
    predict.add_argument("--credits-fall", type=int)
    predict.add_argument("--credits-winter", type=int)
    predict.add_argument("--credits-spring", type=int)
    predict.add_argument("--hometown")
    predict.add_argument("--fafsa", type=parse_bool)
    predict.add_argument("--parents-graduated", type=parse_bool)
    predict.add_argument("--major")
    predict.add_argument("--minor")
    predict.add_argument("--changed-major", type=parse_bool)
    predict.add_argument("--changed-minor", type=parse_bool)
    predict.add_argument("--classes-dropped", type=int)
    predict.add_argument("--hours-worked", type=int)
    predict.add_argument("--lives-on-campus", type=parse_bool)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "predict":
        pipeline = load_pipeline(args.model, args.data)
        student = student_from_args(args)
        percent = dropout_percent(pipeline, student)
        print(f"Dropout likelihood: {percent:.1f}%")
        return

    pipeline, metrics, held_out = train(args.data, args.model)
    print_training_report(metrics, pipeline, held_out)
    print(f"\nSaved model to {args.model}")


if __name__ == "__main__":
    main()
