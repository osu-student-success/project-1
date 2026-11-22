from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
PREDICTIVE_PATH = DATA_DIR / "FAKE_Predictive_Modeling_By_Cohort.xlsx"
GRADES_PATH = DATA_DIR / "FAKE_Grades_by_cohort.xlsx"
# Set this when a financial-aid workbook is available. The fake extracts have none.
AID_PATH: Path | None = None
OUTPUT_PATH = DATA_DIR / "FAKE-combined-dataset.xlsx"

STUDENT_ID = "STUDENT_ID"
TERM = "PAST_TERM"
AID_TERM = "SFRSTCR_TERM_CODE"
DEGREE = "DEGREE_AWARDED_STATUS"
SHEET_NAME = "Combined"

# Term codes and ids are stored as text so Excel does not turn 201701 into 201701.0.
KEY_COLUMNS = {
    "COHORT",
    STUDENT_ID,
    TERM,
    "FIRST_TERM_OF_ATTENDANCE",
    "MIN_PAST_TERM",
    "MAX_PAST_TERM",
    "TRANSCRIPT_TERM",
    AID_TERM,
    "SUBJ_NUMBER",
}

NUMERIC_COLUMNS = [
    "CLASS_STANDING",
    "PRIMARY_MAJOR1",
    "TERM_OSU_QUALITY_POINTS",
    "TERM_OSU_GPA",
    "HIGH_SCHOOL_GPA",
    "ADMIT_COLLEGE",
    "ADMIT_MAJOR",
    "PRIMARY_COLLEGE",
    "STUDENT_LEVL",
    "UNMET_NEED_ROUNDED_1000",
]

COLUMN_ORDER = [
    "RETENTION_FLAG",
    "COHORT",
    STUDENT_ID,
    TERM,
    "FIRST_TERM_OF_ATTENDANCE",
    "ACAD_STAND_CODE_DESC",
    "STU_STATUS_CODE_DESC",
    "STU_TYPE_CODE_DESC",
    "ENROLLMENT_STATUS",
    "CLASS_STANDING",
    "PRIMARY_CAMPUS_CODE",
    "PRIMARY_MAJOR1",
    "TERM_OSU_QUALITY_POINTS",
    "TERM_OSU_GPA",
    "HIGH_SCHOOL_GPA",
    "ADMIT_TYPE_CODE_DESC",
    "ADMIT_COLLEGE",
    "ADMIT_MAJOR",
    DEGREE,
    "PRIMARY_COLLEGE",
    "MIN_PAST_TERM",
    "MAX_PAST_TERM",
    "TRANSCRIPT_TERM",
    "DEPT_CODE",
    "SUBJ_CODE",
    "SUBJ_NUMBER",
    "GRADE",
    "STUDENT_LEVL",
    AID_TERM,
    "UNMET_NEED_ROUNDED_1000",
    "FA_NEED_RANGE",
]


def as_text(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    return text.mask(text == "")


def as_key(series: pd.Series) -> pd.Series:
    # Excel stores whole-number ids and term codes as floats. "201701.0" -> "201701".
    return as_text(series).str.replace(r"\.0$", "", regex=True)


def normalize_header(name: object) -> str:
    text = str(name).strip()
    # Fake grades use Student_ID. The predictive file and the data dictionary use STUDENT_ID.
    if text.upper().replace(" ", "_") == STUDENT_ID:
        return STUDENT_ID
    return text


def clean_frame(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.copy()
    cleaned.columns = [normalize_header(column) for column in cleaned.columns]
    for column in cleaned.columns:
        if column in KEY_COLUMNS:
            cleaned[column] = as_key(cleaned[column])
        else:
            cleaned[column] = as_text(cleaned[column])
    return cleaned


def open_workbook(path: Path) -> tuple[pd.ExcelFile, Path | None]:
    try:
        return pd.ExcelFile(path), None
    except PermissionError:
        temporary = Path(tempfile.gettempdir()) / f"combiner-{path.name}"
        shutil.copy2(path, temporary)
        return pd.ExcelFile(temporary), temporary


def load_workbook(path: Path, cohort_from_sheet: bool) -> tuple[pd.DataFrame, list[str]]:
    workbook, temporary = open_workbook(path)
    frames: list[pd.DataFrame] = []
    skipped: list[str] = []
    try:
        for sheet in workbook.sheet_names:
            frame = pd.read_excel(workbook, sheet_name=sheet, dtype=str)
            frame.columns = [normalize_header(column) for column in frame.columns]
            if frame.empty or STUDENT_ID not in frame.columns:
                skipped.append(sheet)
                continue
            if cohort_from_sheet:
                frame.insert(0, "COHORT", sheet)
            frames.append(clean_frame(frame))
    finally:
        workbook.close()
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    if not frames:
        raise ValueError(f"{path.name} has no sheet with a {STUDENT_ID} column.")
    return pd.concat(frames, ignore_index=True), skipped


def drop_exact_duplicates(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    before = len(frame)
    deduped = frame.drop_duplicates()
    removed = before - len(deduped)
    print(f"{label}: {before} rows, {removed} exact duplicate rows removed")
    return deduped.reset_index(drop=True)


def combine_statuses(values: pd.Series) -> object:
    seen: list[str] = []
    for value in values:
        if pd.isna(value):
            continue
        text = str(value).strip()
        if text and text not in seen:
            seen.append(text)
    if not seen:
        return pd.NA
    if len(seen) == 1:
        return seen[0]
    return " | ".join(sorted(seen))


def collapse_degree_status(frame: pd.DataFrame) -> pd.DataFrame:
    """One predictive row per student-term. Degree status is the only column that repeats."""
    keys = [STUDENT_ID, TERM]
    if not frame.duplicated(keys).any():
        print("Predictive degree status: already one row per student and term")
        return frame

    statuses = (
        frame.groupby(keys, dropna=False)[DEGREE]
        .apply(combine_statuses)
        .reset_index()
    )
    base = frame.drop(columns=[DEGREE]).drop_duplicates(keys)
    collapsed = base.merge(statuses, on=keys, how="left")
    combined_cells = int(collapsed[DEGREE].astype("string").str.contains(r" \| ", na=False).sum())
    print(
        f"Predictive degree status: {len(frame)} rows collapsed to "
        f"{len(collapsed)} student-terms ({combined_cells} terms kept more than one status)"
    )
    return collapsed


def fill_student_constants(combined: pd.DataFrame, predictive: pd.DataFrame) -> list[str]:
    """Copy fields that never change for a student onto terms that came from another file."""
    constant_columns = []
    for column in predictive.columns:
        if column == STUDENT_ID or column not in combined.columns:
            continue
        counts = predictive.groupby(STUDENT_ID)[column].nunique(dropna=True)
        if len(counts) and int(counts.max()) <= 1:
            constant_columns.append(column)

    if not constant_columns:
        return []

    lookup = predictive.groupby(STUDENT_ID, sort=False)[constant_columns].first()
    for column in constant_columns:
        missing = combined[column].isna()
        if missing.any():
            combined.loc[missing, column] = combined.loc[missing, STUDENT_ID].map(lookup[column])
    return constant_columns


def next_fall(cohort: object) -> str | None:
    if pd.isna(cohort):
        return None
    text = str(cohort)
    if not text.isdigit():
        return None
    return str(int(text) + 100)


def add_retention_flag(frame: pd.DataFrame) -> pd.DataFrame:
    terms = frame.groupby(STUDENT_ID)[TERM].agg(lambda values: {value for value in values if pd.notna(value)})
    cohorts = frame.groupby(STUDENT_ID)["COHORT"].agg(
        lambda values: next((value for value in values if pd.notna(value)), pd.NA)
    )

    covered: dict[str, bool] = {}
    for student_id, cohort in cohorts.items():
        following = next_fall(cohort)
        if following is None:
            continue
        student_terms = terms.get(student_id, set())
        covered.setdefault(str(cohort), False)
        if any(term >= following for term in student_terms):
            covered[str(cohort)] = True

    flags: dict[object, object] = {}
    for student_id, cohort in cohorts.items():
        following = next_fall(cohort)
        if following is None or not covered.get(str(cohort), False):
            flags[student_id] = pd.NA
            continue
        flags[student_id] = 1 if following in terms.get(student_id, set()) else 0

    frame.insert(0, "RETENTION_FLAG", frame[STUDENT_ID].map(flags).astype("Int64"))
    return frame


def convert_numeric(frame: pd.DataFrame) -> None:
    # The extracts use the literal text "(null)" for a missing number.
    null_text = {"(null)", "null", "na", "n/a"}
    for column in NUMERIC_COLUMNS:
        if column not in frame.columns:
            continue
        series = frame[column]
        if pd.api.types.is_string_dtype(series) or series.dtype == object:
            series = series.mask(series.astype("string").str.strip().str.lower().isin(null_text))
        converted = pd.to_numeric(series, errors="coerce")
        lost = converted.isna() & series.notna()
        if lost.any():
            print(f"{column}: left as text ({int(lost.sum())} values are not numbers)")
            continue
        frame[column] = converted


def order_columns(frame: pd.DataFrame) -> pd.DataFrame:
    preferred = [column for column in COLUMN_ORDER if column in frame.columns]
    remainder = [column for column in frame.columns if column not in preferred]
    return frame[preferred + remainder]


def write_workbook(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.stem}.writing{path.suffix}")
    try:
        with pd.ExcelWriter(temporary, engine="xlsxwriter") as writer:
            frame.to_excel(writer, index=False, sheet_name=SHEET_NAME)
            sheet = writer.sheets[SHEET_NAME]
            last_row = len(frame)
            last_column = max(len(frame.columns) - 1, 0)
            sheet.autofilter(0, 0, last_row, last_column)
            sheet.freeze_panes(1, 0)
        try:
            temporary.replace(path)
        except PermissionError as error:
            raise SystemExit(
                f"Could not replace {path.name} because the file is open. "
                "Close it in Excel and run this script again."
            ) from error
    finally:
        temporary.unlink(missing_ok=True)


def print_retention(frame: pd.DataFrame) -> None:
    students = (
        frame.groupby(["COHORT", STUDENT_ID], dropna=False)["RETENTION_FLAG"]
        .first()
        .reset_index()
    )
    print("Fall-to-fall retention (blank means that cohort does not reach the next fall yet):")
    for cohort, group in students.groupby("COHORT", dropna=False):
        known = group["RETENTION_FLAG"].dropna()
        if known.empty:
            print(f"  {cohort}: {len(group)} students, not in the extract yet")
            continue
        retained = int(known.sum())
        print(f"  {cohort}: {len(group)} students, {retained} retained ({retained / len(known):.1%})")


def load_aid() -> pd.DataFrame | None:
    if AID_PATH is None or not AID_PATH.exists():
        print("Financial aid: no file, columns left off")
        return None
    aid, aid_skipped = load_workbook(AID_PATH, cohort_from_sheet=False)
    print(f"Financial-aid sheets skipped: {aid_skipped or 'none'}")
    aid = drop_exact_duplicates(aid, "Financial aid")
    if AID_TERM not in aid.columns:
        raise ValueError(f"{AID_PATH.name} has no {AID_TERM} column.")
    if aid.duplicated([STUDENT_ID, AID_TERM]).any():
        raise RuntimeError("Financial-aid rows are duplicated on student id and term.")
    aid[TERM] = aid[AID_TERM]
    aid["_fa_key"] = range(len(aid))
    return aid


def combine() -> pd.DataFrame:
    predictive, predictive_skipped = load_workbook(PREDICTIVE_PATH, cohort_from_sheet=True)
    grades, grades_skipped = load_workbook(GRADES_PATH, cohort_from_sheet=True)
    aid = load_aid()

    print(f"Predictive sheets used: {predictive['COHORT'].nunique()}  skipped: {predictive_skipped or 'none'}")
    print(f"Grade sheets used: {grades['COHORT'].nunique()}  skipped: {grades_skipped or 'none'}")

    predictive = drop_exact_duplicates(predictive, "Predictive")
    grades = drop_exact_duplicates(grades, "Grades")
    predictive = collapse_degree_status(predictive)

    if predictive.duplicated([STUDENT_ID, TERM]).any():
        raise RuntimeError("Predictive rows are still duplicated on student id and term.")

    grade_cohort = grades[[STUDENT_ID, "COHORT"]].drop_duplicates()
    grades = grades.drop(columns=["COHORT"])
    grades["_from_grades"] = 1
    predictive["_pred_key"] = range(len(predictive))

    combined = grades.merge(predictive, on=[STUDENT_ID, TERM], how="outer")
    grade_rows = int(combined["_from_grades"].fillna(0).sum())
    if grade_rows != len(grades):
        raise RuntimeError(
            f"Joining predictive rows duplicated grade records ({grade_rows} vs {len(grades)})."
        )

    if aid is not None:
        combined = combined.merge(aid, on=[STUDENT_ID, TERM], how="outer")
        grade_rows = int(combined["_from_grades"].fillna(0).sum())
        if grade_rows != len(grades):
            raise RuntimeError(
                f"Joining financial-aid rows duplicated grade records ({grade_rows} vs {len(grades)})."
            )
        if combined["_fa_key"].nunique(dropna=True) != len(aid):
            raise RuntimeError("Some financial-aid rows were lost in the join.")

    if combined["_pred_key"].nunique(dropna=True) != len(predictive):
        raise RuntimeError("Some predictive student-terms were lost in the join.")

    missing_cohort = combined["COHORT"].isna()
    if missing_cohort.any():
        cohort_lookup = grade_cohort.drop_duplicates(STUDENT_ID).set_index(STUDENT_ID)["COHORT"]
        combined.loc[missing_cohort, "COHORT"] = combined.loc[missing_cohort, STUDENT_ID].map(cohort_lookup)

    constant_columns = fill_student_constants(combined, predictive.drop(columns=["_pred_key"]))
    print("Student-level fields copied onto unmatched terms:", ", ".join(constant_columns) or "none")

    marker_columns = [column for column in ("_from_grades", "_pred_key", "_fa_key") if column in combined.columns]
    combined = combined.drop(columns=marker_columns)
    combined = add_retention_flag(combined)
    convert_numeric(combined)
    combined = order_columns(combined)
    combined = combined.sort_values(
        ["COHORT", STUDENT_ID, TERM, "SUBJ_CODE", "SUBJ_NUMBER", "GRADE"],
        kind="mergesort",
    ).reset_index(drop=True)

    print(
        f"Combined: {len(combined)} rows, {combined[STUDENT_ID].nunique()} students, "
        f"{combined[TERM].nunique(dropna=True)} terms"
    )
    print_retention(combined)
    return combined


def main() -> None:
    combined = combine()
    write_workbook(combined, OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
