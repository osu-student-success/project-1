from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parent
DEFAULT_DATA = ROOT / "data" / "FAKE-combined-dataset.xlsx"
DEFAULT_MODEL = ROOT / "models" / "retention-rf-fake-combined.joblib"
OUTPUT_DIR = ROOT / "outputs"

# 1 means the student enrolled in the fall one year after entry.
TARGET = "not_retained"
ID_COLUMN = "STUDENT_ID"
SHEET_NAME = "Combined"

CATEGORICAL = [
    "admit_type",
    "campus",
    "admit_college",
    "first_term_standing",
    "enrollment_status",
    "student_type",
]
NUMERIC = [
    "high_school_gpa",
    "first_term_gpa",
    "first_year_gpa",
    "first_term_quality_points",
    "first_term_dfw",
    "first_year_dfw_rate",
]
FEATURES = CATEGORICAL + NUMERIC

# Letter grades that count as a D, F, or withdrawal in the entry year.
DFW_GRADES = {"D+", "D", "D-", "F", "W", "NP"}
GRADE_ORDER = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F", "W"]

FEATURE_LABELS = {
    "high_school_gpa": "High school GPA",
    "first_term_gpa": "First-term GPA",
    "first_year_gpa": "First-year GPA",
    "first_term_quality_points": "First-term quality points",
    "first_term_dfw": "D, F, or W grades in the first term",
    "first_year_dfw_rate": "First-year D/F/W share",
    "admit_type": "Admit type",
    "campus": "Campus",
    "admit_college": "Admit college",
    "first_term_standing": "First-term academic standing",
    "enrollment_status": "First-term enrollment",
    "student_type": "Student type",
}

# Example profiles use the same fields as the training table. They are not rows from the file.
SCENARIOS = {
    "Strong first term": {
        "admit_type": "Domestic Student",
        "campus": "C",
        "admit_college": "16",
        "first_term_standing": "Good Standing",
        "enrollment_status": "F",
        "student_type": "Freshman < 24 hours",
        "high_school_gpa": 3.85,
        "first_term_gpa": 3.70,
        "first_year_gpa": 3.65,
        "first_term_quality_points": 52,
        "first_term_dfw": 0,
        "first_year_dfw_rate": 0.0,
    },
    "At-risk first term": {
        "admit_type": "Domestic Student",
        "campus": "C",
        "admit_college": "16",
        "first_term_standing": "Academic Probation",
        "enrollment_status": "F",
        "student_type": "Freshman < 24 hours",
        "high_school_gpa": 3.05,
        "first_term_gpa": 1.40,
        "first_year_gpa": 1.55,
        "first_term_quality_points": 14,
        "first_term_dfw": 2,
        "first_year_dfw_rate": 0.5,
    },
}

HS_BINS = [0, 3.2, 3.5, 3.8, 4.01]
HS_LABELS = ["Under 3.2", "3.2–3.4", "3.5–3.7", "3.8–4.0"]
TERM_BINS = [-0.01, 2.0, 2.5, 3.0, 3.5, 4.01]
TERM_LABELS = ["Under 2.0", "2.0–2.4", "2.5–2.9", "3.0–3.4", "3.5–4.0"]

NAVY = "#1F4E79"
INK = "#101828"
MUTED = "#344054"
GRID = "#D0D5DD"
FOOTNOTE = "#667085"
MIN_HEATMAP_STUDENTS = 5
MIN_COURSE_STUDENTS = 40

USECOLS = [
    "RETENTION_FLAG",
    "COHORT",
    "STUDENT_ID",
    "PAST_TERM",
    "ACAD_STAND_CODE_DESC",
    "STU_TYPE_CODE_DESC",
    "ENROLLMENT_STATUS",
    "PRIMARY_CAMPUS_CODE",
    "TERM_OSU_QUALITY_POINTS",
    "TERM_OSU_GPA",
    "HIGH_SCHOOL_GPA",
    "ADMIT_TYPE_CODE_DESC",
    "ADMIT_COLLEGE",
    "SUBJ_CODE",
    "SUBJ_NUMBER",
    "GRADE",
]


def as_text(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    return text.str.replace(r"\.0$", "", regex=True)


def cohort_label(value: object) -> str:
    text = str(int(value))
    return f"Fall {text[:4]}"


def open_workbook(path: Path) -> tuple[pd.ExcelFile, Path | None]:
    try:
        return pd.ExcelFile(path), None
    except PermissionError:
        temporary = Path(tempfile.gettempdir()) / f"retention-model-{path.name}"
        shutil.copy2(path, temporary)
        return pd.ExcelFile(temporary), temporary


def load_course_rows(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"Dataset not found: {path}")

    workbook, temporary = open_workbook(path)
    try:
        sheet = SHEET_NAME if SHEET_NAME in workbook.sheet_names else workbook.sheet_names[0]
        frame = pd.read_excel(workbook, sheet_name=sheet, usecols=USECOLS)
    finally:
        workbook.close()
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    missing = [column for column in USECOLS if column not in frame.columns]
    if missing:
        raise SystemExit(f"Dataset is missing columns: {', '.join(missing)}")

    frame[ID_COLUMN] = as_text(frame[ID_COLUMN])
    frame["SUBJ_CODE"] = as_text(frame["SUBJ_CODE"]).str.upper()
    frame["SUBJ_NUMBER"] = as_text(frame["SUBJ_NUMBER"])
    frame["GRADE"] = as_text(frame["GRADE"])
    for column in (
        "ACAD_STAND_CODE_DESC",
        "STU_TYPE_CODE_DESC",
        "ENROLLMENT_STATUS",
        "PRIMARY_CAMPUS_CODE",
        "ADMIT_TYPE_CODE_DESC",
    ):
        frame[column] = as_text(frame[column])
    for column in (
        "RETENTION_FLAG",
        "COHORT",
        "PAST_TERM",
        "ADMIT_COLLEGE",
        "TERM_OSU_GPA",
        "TERM_OSU_QUALITY_POINTS",
        "HIGH_SCHOOL_GPA",
    ):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def student_table(rows: pd.DataFrame) -> pd.DataFrame:
    """One row per student, using only the fall, winter, and spring of the entry year."""
    entry_year = rows[rows["PAST_TERM"].between(rows["COHORT"], rows["COHORT"] + 2)].copy()
    if entry_year.empty:
        raise SystemExit("No entry-year course rows found in the dataset.")

    students = (
        rows.groupby(ID_COLUMN, sort=False)
        .agg(
            cohort=("COHORT", "first"),
            retained=("RETENTION_FLAG", "first"),
            high_school_gpa=("HIGH_SCHOOL_GPA", "first"),
            admit_type=("ADMIT_TYPE_CODE_DESC", "first"),
            admit_college=("ADMIT_COLLEGE", "first"),
        )
        .reset_index()
    )
    known = students["retained"].isin([0, 1])
    students = students.loc[known].copy()
    students["not_retained"] = (students["retained"] == 0).astype(int)
    students["admit_college"] = as_text(students["admit_college"])

    terms = (
        entry_year.groupby([ID_COLUMN, "PAST_TERM"], as_index=False)
        .agg(
            term_gpa=("TERM_OSU_GPA", "first"),
            quality_points=("TERM_OSU_QUALITY_POINTS", "first"),
            standing=("ACAD_STAND_CODE_DESC", "first"),
            enrollment_status=("ENROLLMENT_STATUS", "first"),
            campus=("PRIMARY_CAMPUS_CODE", "first"),
            student_type=("STU_TYPE_CODE_DESC", "first"),
            cohort=("COHORT", "first"),
        )
    )
    first_term = terms[terms["PAST_TERM"] == terms["cohort"]][
        [ID_COLUMN, "term_gpa", "quality_points", "standing", "enrollment_status", "campus", "student_type"]
    ].rename(
        columns={
            "term_gpa": "first_term_gpa",
            "quality_points": "first_term_quality_points",
            "standing": "first_term_standing",
        }
    )
    year_gpa = terms.groupby(ID_COLUMN)["term_gpa"].mean().rename("first_year_gpa")
    first_term_rows = entry_year[entry_year["PAST_TERM"] == entry_year["COHORT"]]
    dfw = (
        first_term_rows[first_term_rows["GRADE"].isin(DFW_GRADES)]
        .groupby(ID_COLUMN)
        .size()
        .rename("first_term_dfw")
    )
    year_courses = entry_year.groupby(ID_COLUMN).size()
    year_dfw = (
        entry_year[entry_year["GRADE"].isin(DFW_GRADES)]
        .groupby(ID_COLUMN)
        .size()
        .reindex(year_courses.index)
        .fillna(0)
    )
    dfw_rate = (year_dfw / year_courses).rename("first_year_dfw_rate")

    students = students.merge(first_term, on=ID_COLUMN, how="left")
    students = students.merge(year_gpa, on=ID_COLUMN, how="left")
    students = students.merge(dfw, on=ID_COLUMN, how="left")
    students = students.merge(dfw_rate, on=ID_COLUMN, how="left")
    students["first_term_dfw"] = students["first_term_dfw"].fillna(0).astype(int)
    students["first_year_dfw_rate"] = students["first_year_dfw_rate"].fillna(0)
    return students.reset_index(drop=True)


def feature_frame(students: pd.DataFrame) -> pd.DataFrame:
    frame = students.loc[:, FEATURES].copy()
    for column in CATEGORICAL:
        frame[column] = frame[column].astype(object)
        frame.loc[frame[column].isna(), column] = np.nan
    return frame


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categories",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                CATEGORICAL,
            ),
            (
                "numbers",
                SimpleImputer(strategy="median"),
                NUMERIC,
            ),
        ]
    )
    forest = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline([("preprocess", preprocessor), ("forest", forest)])


def train(data_path: Path, model_path: Path) -> tuple[Pipeline, dict, pd.DataFrame, pd.DataFrame]:
    rows = load_course_rows(data_path)
    students = student_table(rows)
    features = feature_frame(students)
    target = students[TARGET].astype(int)

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
        "students": int(len(students)),
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "retention_rate": float(students["retained"].mean()),
        "not_retained_rate": float(target.mean()),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, predictions)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "report": classification_report(
            y_test,
            predictions,
            target_names=["retained", "not retained"],
            digits=2,
            zero_division=0,
        ),
    }

    held_out = students.loc[x_test.index].copy()
    held_out["not_retained_likelihood_pct"] = (probabilities * 100).round(1)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": pipeline,
            "features": FEATURES,
            "categorical": CATEGORICAL,
            "numeric": NUMERIC,
            "target": TARGET,
        },
        model_path,
    )
    return pipeline, metrics, held_out, rows


def load_pipeline(model_path: Path, data_path: Path) -> Pipeline:
    if not model_path.exists():
        print(f"No saved model at {model_path}. Training one first.")
        pipeline, _, _, _ = train(data_path, model_path)
        return pipeline

    payload = joblib.load(model_path)
    return payload["pipeline"]


def risk_percent(pipeline: Pipeline, student: dict | pd.Series) -> float:
    if isinstance(student, pd.Series):
        payload = student.to_dict()
    else:
        payload = student
    missing = [feature for feature in FEATURES if feature not in payload]
    if missing:
        raise SystemExit(f"Student record is missing: {', '.join(missing)}")

    row = pd.DataFrame([{feature: payload[feature] for feature in FEATURES}])
    for column in CATEGORICAL:
        row[column] = row[column].astype(object)
    probability = float(pipeline.predict_proba(row)[0, 1])
    return round(probability * 100, 1)


def grouped_importances(pipeline: Pipeline) -> list[tuple[str, float]]:
    preprocessor = pipeline.named_steps["preprocess"]
    forest = pipeline.named_steps["forest"]
    scores: dict[str, float] = {feature: 0.0 for feature in FEATURES}
    for name, score in zip(preprocessor.get_feature_names_out(), forest.feature_importances_):
        raw = str(name).split("__", 1)[-1]
        source = raw
        for feature in FEATURES:
            if raw == feature or raw.startswith(f"{feature}_"):
                source = feature
                break
        scores[source] = scores.get(source, 0.0) + float(score)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [(feature, score) for feature, score in ranked if score > 0]


def _footer(figure: plt.Figure, text: str) -> None:
    figure.text(0.08, 0.02, text, fontsize=7.5, ha="left", va="bottom", color=FOOTNOTE)


def draw_cohort_chart(students: pd.DataFrame, destination: Path) -> None:
    summary = (
        students.groupby("cohort", dropna=False)
        .agg(students=(ID_COLUMN, "size"), retained=("retained", "sum"))
        .reset_index()
        .sort_values("cohort")
    )
    summary["rate"] = summary["retained"] / summary["students"]
    labels = [cohort_label(value) for value in summary["cohort"]]
    rates = summary["rate"].mul(100).tolist()

    figure, axis = plt.subplots(figsize=(9.2, 5.6))
    positions = list(range(len(labels)))
    bars = axis.bar(positions, rates, color=NAVY, width=0.68, zorder=2)
    axis.bar_label(
        bars,
        labels=[f"{rate:.0f}%\n{int(count)}" for rate, count in zip(rates, summary["students"])],
        padding=4,
        fontsize=9,
    )
    axis.set_xticks(positions)
    axis.set_xticklabels(labels)
    axis.set_ylim(0, 108)
    axis.set_yticks([0, 20, 40, 60, 80, 100])
    axis.set_ylabel("Retained")
    axis.yaxis.set_major_formatter(lambda value, _position: f"{value:.0f}%")
    axis.yaxis.grid(True, linestyle="--", linewidth=0.6, color=GRID, zorder=0)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.tick_params(axis="x", length=0)
    axis.set_axisbelow(True)

    retained = int(students["retained"].sum())
    total = int(len(students))
    figure.subplots_adjust(top=0.82, bottom=0.16, left=0.10, right=0.98)
    figure.text(0.10, 0.94, "Fall-to-fall retention by cohort", fontsize=15, ha="left", va="top", color=INK)
    figure.text(
        0.10,
        0.885,
        f"{retained:,} of {total:,} students ({retained / total:.1%}) enrolled in the fall one year after entry.",
        fontsize=9,
        ha="left",
        va="top",
        color=MUTED,
    )
    _footer(
        figure,
        "Each bar is one entry cohort. The number under the percent is the student count. Fake combined dataset.",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=140)
    plt.close(figure)


def _heatmap(
    rates: pd.DataFrame,
    counts: pd.DataFrame,
    title: str,
    subtitle: str,
    footnote: str,
    destination: Path,
    xlabel: str,
    ylabel: str,
    vmin: float,
) -> None:
    values = rates.to_numpy(dtype=float)
    shown = values.copy()
    shown[counts.to_numpy() < MIN_HEATMAP_STUDENTS] = np.nan

    figure_width = max(8.4, 1.15 * rates.shape[1] + 3.2)
    figure_height = max(5.2, 0.72 * rates.shape[0] + 2.6)
    figure, axis = plt.subplots(figsize=(figure_width, figure_height))
    image = axis.imshow(shown, cmap="Blues", norm=Normalize(vmin=vmin, vmax=1.0), aspect="auto")
    colorbar = figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    colorbar.set_label("Retention rate")
    colorbar.ax.yaxis.set_major_formatter(lambda value, _position: f"{value:.0%}")

    axis.set_xticks(range(rates.shape[1]))
    axis.set_xticklabels(list(rates.columns), fontsize=8)
    axis.set_yticks(range(rates.shape[0]))
    axis.set_yticklabels(list(rates.index), fontsize=8)
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.tick_params(length=0)

    darkest = 0.78
    for row_index in range(rates.shape[0]):
        for column_index in range(rates.shape[1]):
            count = int(counts.iloc[row_index, column_index])
            if count == 0:
                continue
            rate = values[row_index, column_index]
            if count < MIN_HEATMAP_STUDENTS:
                label = str(count)
                color = "#98A2B3"
            else:
                label = f"{rate:.0%}\n{count}"
                color = "white" if rate >= darkest else INK
            axis.text(column_index, row_index, label, ha="center", va="center", fontsize=8, color=color)

    figure.subplots_adjust(top=0.84, bottom=0.16, left=0.18, right=0.92)
    figure.text(0.125, 0.95, title, fontsize=15, ha="left", va="top", color=INK)
    figure.text(0.125, 0.90, subtitle, fontsize=9, ha="left", va="top", color=MUTED)
    _footer(figure, footnote)
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=140)
    plt.close(figure)


def draw_gpa_heatmap(students: pd.DataFrame, destination: Path) -> pd.DataFrame:
    known = students.dropna(subset=["high_school_gpa", "first_term_gpa"]).copy()
    known["hs_band"] = pd.cut(
        known["high_school_gpa"],
        bins=HS_BINS,
        labels=HS_LABELS,
        right=False,
        include_lowest=True,
    )
    known["term_band"] = pd.cut(
        known["first_term_gpa"],
        bins=TERM_BINS,
        labels=TERM_LABELS,
        right=False,
        include_lowest=True,
    )
    grouped = (
        known.groupby(["term_band", "hs_band"], observed=False)
        .agg(students=(ID_COLUMN, "size"), retained=("retained", "sum"))
        .reset_index()
    )
    grouped["rate"] = grouped["retained"] / grouped["students"].where(grouped["students"] > 0)
    rates = grouped.pivot(index="term_band", columns="hs_band", values="rate").reindex(
        index=TERM_LABELS, columns=HS_LABELS
    )
    counts = grouped.pivot(index="term_band", columns="hs_band", values="students").reindex(
        index=TERM_LABELS, columns=HS_LABELS
    ).fillna(0)
    omitted = int(len(students) - len(known))
    _heatmap(
        rates,
        counts,
        "Retention by high school GPA and first-term GPA",
        "Each cell is the share retained. The second line is the number of students.",
        (
            f"Cells with fewer than {MIN_HEATMAP_STUDENTS} students are shown as a count only. "
            f"{omitted} students are missing a GPA and are left out. Fake combined dataset."
        ),
        destination,
        "High school GPA",
        "First-term GPA",
        vmin=0.60,
    )
    return grouped


def draw_course_heatmap(rows: pd.DataFrame, destination: Path) -> pd.DataFrame:
    entry_year = rows[rows["PAST_TERM"].between(rows["COHORT"], rows["COHORT"] + 2)].copy()
    entry_year = entry_year[entry_year["RETENTION_FLAG"].isin([0, 1]) & entry_year["GRADE"].notna()]
    entry_year["course"] = entry_year["SUBJ_CODE"] + " " + entry_year["SUBJ_NUMBER"]
    entry_year = entry_year.sort_values([ID_COLUMN, "course", "PAST_TERM"], kind="mergesort")
    first = entry_year.drop_duplicates([ID_COLUMN, "course"], keep="first")

    course_sizes = first.groupby("course")[ID_COLUMN].nunique().sort_values(ascending=False)
    selected = course_sizes[course_sizes >= MIN_COURSE_STUDENTS].head(8).index.tolist()
    selected = sorted(selected, key=lambda name: (name.split()[0], name.split()[-1]))
    grades = [grade for grade in GRADE_ORDER if grade in set(first["GRADE"])]
    first = first[first["course"].isin(selected) & first["GRADE"].isin(grades)]

    grouped = (
        first.groupby(["course", "GRADE"], dropna=False)
        .agg(students=(ID_COLUMN, "nunique"), retained=("RETENTION_FLAG", "sum"))
        .reset_index()
    )
    grouped["rate"] = grouped["retained"] / grouped["students"]
    rates = grouped.pivot(index="course", columns="GRADE", values="rate").reindex(index=selected, columns=grades)
    counts = (
        grouped.pivot(index="course", columns="GRADE", values="students")
        .reindex(index=selected, columns=grades)
        .fillna(0)
    )
    _heatmap(
        rates,
        counts,
        "Retention by first grade in the entry year",
        "Each student is counted once per course, using the earliest grade in that entry year.",
        (
            f"The eight courses with at least {MIN_COURSE_STUDENTS} students are shown. "
            f"Cells with fewer than {MIN_HEATMAP_STUDENTS} students are a count only. Fake combined dataset."
        ),
        destination,
        "First grade",
        "Course",
        vmin=0.25,
    )
    return grouped


def draw_importance_chart(pipeline: Pipeline, destination: Path) -> None:
    ranked = grouped_importances(pipeline)
    labels = [FEATURE_LABELS.get(name, name) for name, _score in ranked][::-1]
    scores = [score for _name, score in ranked][::-1]

    figure, axis = plt.subplots(figsize=(9.2, 5.8))
    axis.barh(labels, scores, color=NAVY, zorder=2)
    axis.set_xlabel("Share of the model's splits")
    axis.set_xlim(0, max(scores) * 1.18 if scores else 1)
    axis.xaxis.set_major_formatter(lambda value, _position: f"{value:.0%}")
    axis.xaxis.grid(True, linestyle="--", linewidth=0.6, color=GRID, zorder=0)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.tick_params(axis="y", length=0)
    axis.set_axisbelow(True)
    for position, score in enumerate(scores):
        label = f"{score:.0%}" if score >= 0.01 else "<1%"
        axis.text(score + max(scores) * 0.02, position, label, va="center", fontsize=8, color=MUTED)

    figure.subplots_adjust(top=0.84, bottom=0.16, left=0.32, right=0.96)
    figure.text(0.32, 0.94, "What the model uses", fontsize=15, ha="left", va="top", color=INK)
    figure.text(
        0.32,
        0.885,
        "Grouped importance from the random forest. Higher means the feature was used in more splits.",
        fontsize=9,
        ha="left",
        va="top",
        color=MUTED,
    )
    _footer(
        figure,
        "Uses entry-term academics, first-year GPA, and the share of D, F, or W grades. Fake combined dataset.",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=140)
    plt.close(figure)


def write_charts(students: pd.DataFrame, rows: pd.DataFrame, pipeline: Pipeline) -> list[Path]:
    destinations = {
        "cohort": OUTPUT_DIR / "retention-by-cohort.png",
        "gpa": OUTPUT_DIR / "retention-gpa-heatmap.png",
        "course": OUTPUT_DIR / "retention-course-grade-heatmap.png",
        "importance": OUTPUT_DIR / "retention-feature-importance.png",
    }
    draw_cohort_chart(students, destinations["cohort"])
    draw_gpa_heatmap(students, destinations["gpa"])
    draw_course_heatmap(rows, destinations["course"])
    draw_importance_chart(pipeline, destinations["importance"])
    return list(destinations.values())


def print_retention_summary(students: pd.DataFrame) -> None:
    retained = int(students["retained"].sum())
    total = int(len(students))
    print(f"Fall-to-fall retention: {retained} of {total} students ({retained / total:.1%})")
    for cohort, group in students.groupby("cohort", sort=True):
        kept = int(group["retained"].sum())
        print(f"  {cohort_label(cohort)}: {kept} of {len(group)} ({kept / len(group):.1%})")


def print_training_report(metrics: dict, pipeline: Pipeline, held_out: pd.DataFrame) -> None:
    print(
        f"Students: {metrics['students']}  |  trained on {metrics['train_rows']}  |  "
        f"tested on {metrics['test_rows']}"
    )
    print(f"Retention rate: {metrics['retention_rate']:.1%}")
    print(f"Held-out accuracy: {metrics['accuracy']:.1%}")
    print(f"Held-out balanced accuracy: {metrics['balanced_accuracy']:.1%}")
    print(f"Held-out ROC-AUC: {metrics['roc_auc']:.3f}")
    print(
        "A 50% cutoff predicts that a student does not return. "
        "On this file the grade gaps are small, so most scores stay below that cutoff."
    )
    print("\nClassification report (positive class = not retained):")
    print(metrics["report"].rstrip())

    print("\nStrongest features:")
    for name, score in grouped_importances(pipeline):
        print(f"  {FEATURE_LABELS.get(name, name):<40} {score:.3f}")

    print("\nExample profiles:")
    for label, student in SCENARIOS.items():
        percent = risk_percent(pipeline, student)
        print(f"  {label}: {percent:.1f}% likelihood of not returning")

    ranked = held_out.sort_values("not_retained_likelihood_pct", ascending=False)
    print("\nHighest held-out likelihoods of not returning:")
    _print_held_out(ranked.head(3))
    print("Lowest held-out likelihoods of not returning:")
    _print_held_out(ranked.tail(3))


def _print_held_out(frame: pd.DataFrame) -> None:
    for _, row in frame.iterrows():
        outcome = "not retained" if row["not_retained"] else "retained"
        gpa = row["first_term_gpa"]
        gpa_text = f"{gpa:.2f}" if pd.notna(gpa) else "n/a"
        print(
            f"  {row[ID_COLUMN]}: {row['not_retained_likelihood_pct']:.1f}%  "
            f"first-term GPA {gpa_text}, {int(row['first_term_dfw'])} first-term D/F/W, actual {outcome}"
        )


def score_student(data_path: Path, model_path: Path, student_id: str) -> None:
    rows = load_course_rows(data_path)
    students = student_table(rows)
    key = student_id.strip().upper()
    matches = students[students[ID_COLUMN].str.upper() == key]
    if matches.empty:
        raise SystemExit(f"No student with ID {student_id} in {data_path.name}.")

    pipeline = load_pipeline(model_path, data_path)
    student = matches.iloc[0]
    percent = risk_percent(pipeline, student)
    outcome = "retained" if int(student["retained"]) == 1 else "not retained"
    print(f"Student {student[ID_COLUMN]}: {percent:.1f}% likelihood of not returning next fall")
    print(f"Actual fall-to-fall outcome in the file: {outcome}")


def student_from_json(payload: str) -> dict:
    student = json.loads(payload)
    missing = [feature for feature in FEATURES if feature not in student]
    if missing:
        raise SystemExit(f"JSON is missing: {', '.join(missing)}")
    return student


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Estimate fall-to-fall retention risk from the fake combined dataset."
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Path to the combined workbook.")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="Where to save or load the model.")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("train", help="Train on the workbook and write retention charts.")

    predict = subparsers.add_parser("predict", help="Score one student from the workbook or a JSON profile.")
    predict.add_argument("--student-id", help="Student id from the combined workbook.")
    predict.add_argument("--json", help="Feature values as one JSON object.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "predict":
        if args.json:
            pipeline = load_pipeline(args.model, args.data)
            percent = risk_percent(pipeline, student_from_json(args.json))
            print(f"Likelihood of not returning: {percent:.1f}%")
            return
        if not args.student_id:
            raise SystemExit("Predict needs --student-id or --json.")
        score_student(args.data, args.model, args.student_id)
        return

    pipeline, metrics, held_out, rows = train(args.data, args.model)
    students = student_table(rows)
    print_retention_summary(students)
    print()
    print_training_report(metrics, pipeline, held_out)
    charts = write_charts(students, rows, pipeline)
    print(f"\nSaved model to {args.model}")
    for chart in charts:
        print(f"Saved chart to {chart}")


if __name__ == "__main__":
    main()
