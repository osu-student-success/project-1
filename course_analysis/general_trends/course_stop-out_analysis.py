# Note will not run without 'data_private' folder containing the data Excel files

from pathlib import Path
import re
import warnings

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns


PROJECT_DIR = Path(__file__).resolve().parent

DATA_DIR = PROJECT_DIR / "data_private"

OUTPUT_DIR = PROJECT_DIR / "eda_outputs" / "course_analysis"
FIG_DIR = OUTPUT_DIR / "figures"

PM_PATTERN = "Predictive Modeling By Cohort*.xlsx"
GRADES_PATTERN = "grades_by_cohort*.xlsx"

MIN_FOLLOWUP_TERMS = 2

MIN_COURSE_ENROLLMENT = 30

# Maximum number of courses displayed in ranking charts.
TOP_N_COURSES = 20

INCLUDE_MISSING_GRADES = True

def load_excel_files(folder, pattern):
    """
    Load all matching Excel workbooks and all their worksheets.

    Supports:
        - One workbook with multiple cohort sheets.
        - Multiple cohort workbooks.
    """

    files = sorted(folder.glob(pattern))

    if not files:
        raise FileNotFoundError(
            f"No files found matching {pattern} in {folder}"
        )

    frames = []

    for file in files:
        print(f"Loading: {file.name}")

        sheets = pd.read_excel(
            file,
            sheet_name=None,
            dtype={"STUDENT_ID": "string"}
        )

        for sheet_name, frame in sheets.items():
            frame.columns = frame.columns.astype(str).str.strip()

            frame["_SOURCE_FILE"] = file.name
            frame["_SOURCE_SHEET"] = sheet_name

            frames.append(frame)

    return pd.concat(frames, ignore_index=True)


def clean_student_ids(df):
    df = df.copy()

    df["STUDENT_ID"] = (
        df["STUDENT_ID"]
        .astype("string")
        .str.strip()
    )

    df.loc[
        df["STUDENT_ID"].isin(["", "nan", "None"]),
        "STUDENT_ID"
    ] = pd.NA

    return df


def clean_term_column(df, column):
    df = df.copy()

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )

    return df


def save_figure(filename):
    path = FIG_DIR / filename

    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()

    print(f"Saved figure: {path}")

def main():

    FIG_DIR.mkdir(parents=True, exist_ok=True)

    print("\nLoading PM data...")
    pm = load_excel_files(DATA_DIR, PM_PATTERN)

    print("\nLoading grades data...")
    grades = load_excel_files(DATA_DIR, GRADES_PATTERN)

    required_pm = [
        "STUDENT_ID",
        "PAST_TERM",
        "FIRST_TERM_OF_ATTENDANCE",
        "STU_TYPE_CODE_DESC",
    ]

    required_grades = [
        "STUDENT_ID",
        "TRANSCRIPT_TERM",
        "SUBJ_CODE",
        "SUBJ_NUMBER",
        "GRADE",
    ]

    for column in required_pm:
        if column not in pm.columns:
            raise ValueError(
                f"Missing PM column: {column}"
            )

    for column in required_grades:
        if column not in grades.columns:
            raise ValueError(
                f"Missing grades column: {column}"
            )


    pm = clean_student_ids(pm)
    grades = clean_student_ids(grades)

    pm = clean_term_column(pm, "PAST_TERM")
    grades = clean_term_column(
        grades, "TRANSCRIPT_TERM"
    )

    pm = pm.dropna(
        subset=["STUDENT_ID", "PAST_TERM"]
    )

    grades = grades.dropna(
        subset=[
            "STUDENT_ID",
            "TRANSCRIPT_TERM",
            "SUBJ_CODE",
        ]
    )

    grades["SUBJ_CODE"] = (
        grades["SUBJ_CODE"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    grades["SUBJ_NUMBER"] = (
        grades["SUBJ_NUMBER"]
        .astype("string")
        .str.strip()
    )

    grades["GRADE"] = (
        grades["GRADE"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    grades.loc[
        grades["SUBJ_NUMBER"].isin(["", "nan", "None"]),
        "SUBJ_NUMBER"
    ] = pd.NA

    grades.loc[
        grades["GRADE"].isin(["", "NAN", "NONE"]),
        "GRADE"
    ] = pd.NA

    ftft_pattern = (
        r"^Freshman\s*(<\s*24\s*hours|- Early Admit)$"
    )

    pm["STU_TYPE_CODE_DESC"] = (
        pm["STU_TYPE_CODE_DESC"]
        .astype("string")
        .str.strip()
    )

    pm = pm[
        pm["STU_TYPE_CODE_DESC"].str.contains(
            ftft_pattern,
            case=False,
            regex=True,
            na=False
        )
    ].copy()

    print(
        f"\nPM FTFT rows: {len(pm):,}"
    )

    # Retain one row per student and enrollment term.
    pm = pm.drop_duplicates(
        subset=["STUDENT_ID", "PAST_TERM"]
    )

    student_terms = (
        pm.groupby("STUDENT_ID")["PAST_TERM"]
        .apply(lambda x: sorted(set(x.dropna())))
        .to_dict()
    )

    observed_terms = sorted(
        pm["PAST_TERM"].dropna().unique()
    )

    if len(observed_terms) <= MIN_FOLLOWUP_TERMS:
        raise ValueError(
            "Not enough distinct enrollment terms for "
            "the configured follow-up requirement."
        )

    grades = grades[
        grades["STUDENT_ID"].isin(
            pm["STUDENT_ID"].unique()
        )
    ].copy()

    grades["COURSE"] = (
        grades["SUBJ_CODE"].fillna("UNKNOWN")
        + " "
        + grades["SUBJ_NUMBER"].fillna("UNKNOWN")
    )

    grades["COURSE"] = grades["COURSE"].str.strip()

    grades["TERM_IN_PM_CALENDAR"] = (
        grades["TRANSCRIPT_TERM"].isin(observed_terms)
    )

    grades = grades[
        grades["TERM_IN_PM_CALENDAR"]
    ].copy()

    cohort_lookup = (
        pm.sort_values("PAST_TERM")
        .drop_duplicates("STUDENT_ID")
        [["STUDENT_ID", "FIRST_TERM_OF_ATTENDANCE"]]
    )

    grades = grades.merge(
        cohort_lookup,
        on="STUDENT_ID",
        how="inner",
        validate="many_to_one"
    )


    def evaluate_course_attempt(row):

        student_id = row["STUDENT_ID"]
        course_term = row["TRANSCRIPT_TERM"]

        terms = student_terms.get(student_id, [])

        later_terms = [
            term for term in terms
            if term > course_term
        ]

        available_followup = [
            term for term in observed_terms
            if term > course_term
        ]

        if len(available_followup) < MIN_FOLLOWUP_TERMS:
            return pd.Series({
                "RETURNED": np.nan,
                "FOLLOWUP_TERMS": len(available_followup),
            })

        returned = len(later_terms) > 0

        return pd.Series({
            "RETURNED": int(returned),
            "FOLLOWUP_TERMS": len(available_followup),
        })

    print("\nCalculating student return status...")

    status = grades.apply(
        evaluate_course_attempt,
        axis=1
    )

    grades = pd.concat(
        [grades, status],
        axis=1
    )

    grades = grades.dropna(
        subset=["RETURNED"]
    ).copy()

    grades["RETURNED"] = grades["RETURNED"].astype(int)

    grades["NOT_RETURNED"] = (
        1 - grades["RETURNED"]
    )

    if not INCLUDE_MISSING_GRADES:
        grades = grades.dropna(subset=["GRADE"])


    grades = grades.drop_duplicates(
        subset=[
            "STUDENT_ID",
            "TRANSCRIPT_TERM",
            "COURSE",
        ]
    )

    print(
        f"Course attempts analyzed: {len(grades):,}"
    )

    if grades.empty:
        raise ValueError(
            "No eligible course attempts remain. "
            "Check the term alignment and follow-up settings."
        )


    course_summary = (
    grades.groupby(
        ["COURSE", "SUBJ_CODE", "SUBJ_NUMBER"],
        dropna=False
    )
    .agg(
        STUDENTS=("STUDENT_ID", "nunique"),
        ATTEMPTS=("STUDENT_ID", "size"),
        RETURNED=("RETURNED", "sum"),
        NOT_RETURNED=("NOT_RETURNED", "sum"),
    )
    .reset_index()
    )

    course_summary["NONRETURN_RATE"] = (
        course_summary["NOT_RETURNED"]
        / course_summary["ATTEMPTS"]
        * 100
    )

    course_summary["RETURN_RATE"] = (
        course_summary["RETURNED"]
        / course_summary["ATTEMPTS"]
        * 100
    )

    eligible_courses = course_summary[
        course_summary["STUDENTS"] >= MIN_COURSE_ENROLLMENT
    ].copy()


    # FIGURE 1: HIGHEST NON-RETURN COURSES
    top_courses = (
        eligible_courses
        .sort_values(
            ["NONRETURN_RATE", "STUDENTS"],
            ascending=[False, False]
        )
        .head(TOP_N_COURSES)
        .sort_values("NONRETURN_RATE")
    )

    plt.figure(figsize=(12, 8))

    plt.barh(
        top_courses["COURSE"],
        top_courses["NONRETURN_RATE"]
    )

    plt.xlabel("Student Stop-Out (%)")
    plt.ylabel("Course")
    plt.title(
        "Courses with the Highest Student Stop-Out Rates"
    )

    save_figure(
        "highest_stop-out_courses.png"
    )


    # FIGURE 2: COURSE ENROLLMENT VS NON-RETURN
    plt.figure(figsize=(10, 7))

    plt.scatter(
        eligible_courses["ATTEMPTS"],
        eligible_courses["NONRETURN_RATE"],
        alpha=0.65
    )

    plt.xlabel("Number of student-course attempts")
    plt.ylabel("Attempts followed by Stop-Out (%)")
    plt.title(
        "Course Enrollment vs. Subsequent Stop-Out Rate"
    )

    plt.grid(alpha=0.25)

    # FIGURE 3: DEPARTMENT NON-RETURN RATES
    department_summary = (
        grades.groupby("SUBJ_CODE")
        .agg(
            STUDENTS=("STUDENT_ID", "nunique"),
            NOT_RETURNED=("NOT_RETURNED", "sum"),
        )
        .reset_index()
    )

    department_summary["NONRETURN_RATE"] = (
        department_summary["NOT_RETURNED"]
        / department_summary["STUDENTS"]
        * 100
    )

    department_summary = department_summary[
        department_summary["STUDENTS"]
        >= MIN_COURSE_ENROLLMENT
    ]

    department_summary = (
        department_summary
        .nlargest(20, "STUDENTS")
    )

    department_summary = department_summary.sort_values("NONRETURN_RATE")

    plt.figure(figsize=(11, 8))

    plt.barh(
        department_summary["SUBJ_CODE"],
        department_summary["NONRETURN_RATE"]
    )

    plt.xlabel("Student Stop-Out (%)")
    plt.ylabel("Department / Subject")
    plt.title(
        "Student Stop-Out Rates by Department"
    )

    save_figure(
        "department_nonreturn_rates.png"
    )


    # FIGURE 4: GRADE VS RETURN
    grade_order = [
        "A", "A-", "B+", "B", "B-", "C+", "C",
        "C-", "D+", "D", "D-", "F", "W", "WF",
        "I", "P", "NP"
    ]

    grade_summary = (
        grades.dropna(subset=["GRADE"])
        .groupby("GRADE")
        .agg(
            STUDENTS=("STUDENT_ID", "nunique"),
            NONRETURN_RATE=("NOT_RETURNED", "mean"),
        )
        .reset_index()
    )

    grade_summary["NONRETURN_RATE"] *= 100

    grade_summary = grade_summary[
        grade_summary["STUDENTS"]
        >= MIN_COURSE_ENROLLMENT
    ].copy()

    grade_summary["GRADE_ORDER"] = (
        grade_summary["GRADE"].apply(
            lambda x: (
                grade_order.index(x)
                if x in grade_order
                else len(grade_order)
            )
        )
    )

    grade_summary = grade_summary.sort_values(
        "GRADE_ORDER"
    )

    plt.figure(figsize=(11, 6))

    plt.bar(
        grade_summary["GRADE"],
        grade_summary["NONRETURN_RATE"]
    )

    plt.xlabel("Course grade")
    plt.ylabel("Student Stop-Out (%)")
    plt.title(
        "Student Stop-Out Rate by Course Grade"
    )

    save_figure(
        "grade_vs_return.png"
    )


    # FIGURE 5: COURSE NON-RETURN BY COHORT
    MIN_COHORT_COURSE_ENROLLMENT = 5
    cohort_course = (
    grades.groupby(
        ["COURSE", "FIRST_TERM_OF_ATTENDANCE"]
    )
    .agg(
        STUDENTS=("STUDENT_ID", "nunique"),
        NONRETURN_RATE=("NOT_RETURNED", "mean"),
    )
    .reset_index()
    )

    cohort_course = cohort_course[
        cohort_course["STUDENTS"]
        >= MIN_COHORT_COURSE_ENROLLMENT
    ].copy()

    selected_courses = (
        eligible_courses
        .nlargest(10, "NONRETURN_RATE")["COURSE"]
    )

    cohort_course = cohort_course[
        cohort_course["COURSE"].isin(selected_courses)
    ]

    if not cohort_course.empty:

        pivot = cohort_course.pivot(
            index="COURSE",
            columns="FIRST_TERM_OF_ATTENDANCE",
            values="NONRETURN_RATE"
        ) * 100

        plt.figure(figsize=(14, 8))

        sns.heatmap(
            pivot,
            annot=True,
            fmt=".1f",
            cmap="YlOrRd",
            linewidths=0.5,
            cbar_kws={
                "label": "Subsequent stop-out rate (%)"
            }
        )

        plt.title(
            "Course Stop-Out Rates by Entering Cohort"
        )

        plt.xlabel("Entering cohort")
        plt.ylabel("Course")

        save_figure(
            "course_stop-out_by_cohort.png"
        )

    else:
        print(
            "WARNING: Graph 05 was not generated. "
            "No course/cohort combinations met the "
            "minimum enrollment requirement."
        )


    # FIGURE 6: COURSES WITH MOST NON-RETURNING STUDENTS
    highest_counts = (
        eligible_courses
        .nlargest(TOP_N_COURSES, "NOT_RETURNED")
        .sort_values("NOT_RETURNED")
    )

    plt.figure(figsize=(12, 8))

    plt.barh(
        highest_counts["COURSE"],
        highest_counts["NOT_RETURNED"]
    )

    plt.xlabel("Number of student Stop-Outs")
    plt.ylabel("Course")
    plt.title(
        "Courses Associated with the Most Stop-Out Students"
    )

    save_figure(
        "courses_with_most_stop-out_students.png"
    )


    print("\n" + "=" * 60)
    print("COURSE NON-RETURN ANALYSIS COMPLETE")
    print("=" * 60)

    print(
        f"\nUnique students analyzed: "
        f"{grades['STUDENT_ID'].nunique():,}"
    )

    print(
        f"Unique courses analyzed: "
        f"{grades['COURSE'].nunique():,}"
    )

    print(
        f"Course attempts analyzed: "
        f"{len(grades):,}"
    )

    print(
        f"Overall stop-out rate: "
        f"{grades['NOT_RETURNED'].mean() * 100:.1f}%"
    )

    print(
        f"\nFigures saved to: {FIG_DIR.resolve()}"
    )


if __name__ == "__main__":
    main()
