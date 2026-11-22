from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MultipleLocator

ROOT = Path(__file__).resolve().parent
#DATA_PATH = ROOT / "data" / "NDA" / "combined-dataset.xlsx"
DATA_PATH = ROOT / "data" / "FAKE-combined-dataset.xlsx"
OUTPUT_DIR = ROOT / "outputs"

# ENGR 100H is the honors section of ENGR 100 and is counted with it.
COURSES = (
    ("MTH", ("251",), "MTH 251"),
    ("MTH", ("252",), "MTH 252"),
    ("CH", ("201",), "CH 201"),
    ("ENGR", ("100", "100H"), "ENGR 100"),
)

# Letter grades first, then other marks that show up on these transcripts.
GRADE_ORDER = [
    "A",
    "A-",
    "B+",
    "B",
    "B-",
    "C+",
    "C",
    "C-",
    "D+",
    "D",
    "D-",
    "F",
    "S",
    "P",
    "U",
    "P N",
    "D N",
    "W",
]

COLUMNS = [
    "RETENTION_FLAG",
    "STUDENT_ID",
    "SUBJ_CODE",
    "SUBJ_NUMBER",
    "GRADE",
    "TRANSCRIPT_TERM",
    "PAST_TERM",
]

BAR_COLOR = "#1F4E79"
NOT_RETAINED = "0"


def as_key(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    return text.str.replace(r"\.0$", "", regex=True)


def open_workbook(path: Path) -> tuple[pd.ExcelFile, Path | None]:
    try:
        return pd.ExcelFile(path), None
    except PermissionError:
        temporary = Path(tempfile.gettempdir()) / f"grade-charts-{path.name}"
        shutil.copy2(path, temporary)
        return pd.ExcelFile(temporary), temporary


def load_rows(path: Path) -> pd.DataFrame:
    workbook, temporary = open_workbook(path)
    try:
        frame = pd.read_excel(workbook, dtype=str, usecols=COLUMNS)
    finally:
        workbook.close()
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    frame["SUBJ_CODE"] = as_key(frame["SUBJ_CODE"]).str.upper()
    frame["SUBJ_NUMBER"] = as_key(frame["SUBJ_NUMBER"])
    frame["GRADE"] = as_key(frame["GRADE"])
    frame["RETENTION_FLAG"] = as_key(frame["RETENTION_FLAG"])
    frame["STUDENT_ID"] = as_key(frame["STUDENT_ID"])
    frame["TRANSCRIPT_TERM"] = as_key(frame["TRANSCRIPT_TERM"])
    frame["PAST_TERM"] = as_key(frame["PAST_TERM"])
    return frame


def first_attempt(rows: pd.DataFrame) -> pd.DataFrame:
    """One row per student: the earliest transcript grade in this course."""
    graded = rows[rows["GRADE"].notna()].copy()
    graded["_term"] = graded["TRANSCRIPT_TERM"].fillna(graded["PAST_TERM"]).fillna("999999")
    graded = graded.sort_values(["STUDENT_ID", "_term"], kind="mergesort")
    return graded.drop_duplicates("STUDENT_ID", keep="first")


def grade_key(grade: str) -> tuple[int, str]:
    if grade in GRADE_ORDER:
        return GRADE_ORDER.index(grade), grade
    return len(GRADE_ORDER), grade


def summarize(attempts: pd.DataFrame) -> pd.DataFrame:
    known = attempts[attempts["RETENTION_FLAG"].isin(["0", "1"])]
    if known.empty:
        return pd.DataFrame(columns=["grade", "students", "not_retained", "percent"])

    grouped = (
        known.groupby("GRADE", dropna=False)
        .agg(
            students=("STUDENT_ID", "nunique"),
            not_retained=("RETENTION_FLAG", lambda flags: int((flags == NOT_RETAINED).sum())),
        )
        .reset_index()
        .rename(columns={"GRADE": "grade"})
    )
    grouped["percent"] = grouped["not_retained"] / grouped["students"] * 100
    grouped["_order"] = grouped["grade"].map(lambda grade: grade_key(str(grade)))
    grouped = grouped.sort_values("_order").drop(columns="_order").reset_index(drop=True)
    return grouped


def course_rows_for(rows: pd.DataFrame, code: str, numbers: tuple[str, ...]) -> pd.DataFrame:
    return rows[(rows["SUBJ_CODE"] == code) & (rows["SUBJ_NUMBER"].isin(numbers))]


def draw(course_name: str, summary: pd.DataFrame, destination: Path) -> None:
    grades = summary["grade"].astype(str).tolist()
    counts = summary["not_retained"].astype(int).tolist()
    students = summary["students"].astype(int).tolist()
    percents = summary["percent"].tolist()

    figure, axis = plt.subplots(figsize=(12.5, 7.2))
    positions = list(range(len(grades)))
    bars = axis.bar(positions, counts, color=BAR_COLOR, width=0.72, zorder=2)
    axis.bar_label(bars, labels=[f"{count:,}" for count in counts], padding=3, fontsize=8)

    axis.set_xticks(positions)
    axis.set_xticklabels(
        [f"{grade}\n{percent:.0f}%\n{student:,}" for grade, percent, student in zip(grades, percents, students)],
        fontsize=8,
    )
    axis.set_xlim(-0.6, len(grades) - 0.4)
    peak = max(counts) if counts else 0
    axis.set_ylim(0, peak * 1.2 + 1)
    axis.set_ylabel("Students not retained")
    axis.yaxis.grid(True, linestyle="--", linewidth=0.6, color="#D0D5DD", zorder=0)
    axis.set_axisbelow(True)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.tick_params(axis="x", length=0, pad=4)

    students_total = int(summary["students"].sum())
    not_retained_total = int(summary["not_retained"].sum())
    figure.subplots_adjust(top=0.78, bottom=0.24, left=0.08, right=0.98)
    figure.text(
        0.08,
        0.95,
        f"{course_name}: students not retained, by grade",
        fontsize=15,
        ha="left",
        va="top",
        color="#101828",
    )
    figure.text(
        0.08,
        0.905,
        (
            f"{not_retained_total:,} of {students_total:,} students with a known fall-to-fall outcome "
            "were not retained. Each student is counted once, using their first grade in the course."
        ),
        fontsize=9,
        ha="left",
        va="top",
        color="#344054",
    )
    figure.text(
        0.53,
        0.075,
        "Under each grade: percent not retained, then the number of students who received that grade.",
        fontsize=8,
        ha="center",
        va="top",
        color="#475467",
    )
    figure.text(
        0.08,
        0.018,
        (
            "Not retained means no enrollment in the fall one year after entry. "
            "Students whose next fall is not in the extract yet are excluded. "
            + (
                "ENGR 100H is included with ENGR 100."
                if course_name == "ENGR 100"
                else "Honors (H) and Z sections are separate course numbers and are not included."
            )
        ),
        fontsize=7.5,
        ha="left",
        va="bottom",
        color="#667085",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, format="pdf")
    plt.close(figure)


def slug(course_name: str) -> str:
    return course_name.lower().replace(" ", "-")


def course_attempts(rows: pd.DataFrame) -> pd.DataFrame:
    """First grade in each tracked course, one row per student and course."""
    frames: list[pd.DataFrame] = []
    for code, numbers, course_name in COURSES:
        matched = course_rows_for(rows, code, numbers)
        attempts = first_attempt(matched)
        attempts = attempts.loc[:, ["STUDENT_ID", "RETENTION_FLAG", "GRADE"]].copy()
        attempts["COURSE"] = course_name
        frames.append(attempts)
    return pd.concat(frames, ignore_index=True)


def students_in_multiple(attempts: pd.DataFrame) -> pd.DataFrame:
    """Students with a known outcome who took at least two of the tracked courses."""
    known = attempts[attempts["RETENTION_FLAG"].isin(["0", "1"])].copy()
    course_counts = known.groupby("STUDENT_ID")["COURSE"].nunique()
    keep = course_counts[course_counts >= 2].index
    return known[known["STUDENT_ID"].isin(keep)].copy()


def performance_by_course(group: pd.DataFrame, grades: list[str]) -> list[tuple[str, pd.DataFrame]]:
    panels: list[tuple[str, pd.DataFrame]] = []
    for _, _, course_name in COURSES:
        course = group[group["COURSE"] == course_name]
        total = int(course["STUDENT_ID"].nunique())
        counts = course.groupby("GRADE")["STUDENT_ID"].nunique()
        summary = pd.DataFrame({"grade": grades})
        summary["students"] = summary["grade"].map(counts).fillna(0).astype(int)
        summary["percent"] = (summary["students"] / total * 100) if total else 0.0
        panels.append((course_name, summary))
    return panels


def draw_performance(
    heading: str,
    detail: str,
    panels: list[tuple[str, pd.DataFrame]],
    grades: list[str],
    destination: Path,
) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(16.5, 11.2), sharex=False, sharey=True)
    positions = list(range(len(grades)))
    for axis, (course_name, summary) in zip(axes.ravel(), panels):
        percents = summary["percent"].tolist()
        counts = summary["students"].astype(int).tolist()
        course_total = int(summary["students"].sum())
        bars = axis.bar(positions, percents, color=BAR_COLOR, width=0.74, zorder=2)
        axis.bar_label(
            bars,
            labels=[f"{count:,}" if percent >= 8 else "" for count, percent in zip(counts, percents)],
            padding=2,
            fontsize=7,
        )
        axis.set_title(f"{course_name}    {course_total:,} students", loc="left", fontsize=12, pad=8)
        axis.set_xlim(-0.6, len(grades) - 0.4)
        axis.set_ylim(0, 100)
        axis.set_xticks(positions)
        axis.set_xticklabels(grades, fontsize=8)
        axis.yaxis.set_major_locator(MultipleLocator(20))
        axis.yaxis.set_major_formatter(lambda value, _position: f"{value:.0f}%")
        axis.yaxis.grid(True, linestyle="--", linewidth=0.6, color="#D0D5DD", zorder=0)
        axis.set_axisbelow(True)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.tick_params(axis="x", length=0, pad=2, labelsize=8)
        axis.tick_params(axis="y", labelsize=8)

    for axis in axes[:, 0]:
        axis.set_ylabel("Share of students in the course")

    figure.subplots_adjust(top=0.86, bottom=0.08, left=0.06, right=0.98, hspace=0.38, wspace=0.16)
    figure.text(0.06, 0.965, heading, fontsize=16, ha="left", va="top", color="#101828")
    figure.text(0.06, 0.925, detail, fontsize=9, ha="left", va="top", color="#344054")
    figure.text(
        0.06,
        0.015,
        (
            "Both charts use the same 0–100% scale. Numbers appear on bars that are at least 8% of the course. "
            "Each student is counted once per course, using their first grade, and appears in every course they took. "
            "ENGR 100 includes ENGR 100H. Other honors and Z sections are not included."
        ),
        fontsize=7.5,
        ha="left",
        va="bottom",
        color="#667085",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, format="pdf")
    plt.close(figure)


def grades_in_use(group: pd.DataFrame) -> list[str]:
    present = {str(grade) for grade in group["GRADE"].dropna().unique()}
    ordered = [grade for grade in GRADE_ORDER if grade in present]
    extra = sorted(present - set(GRADE_ORDER))
    return ordered + extra


def main() -> None:
    rows = load_rows(DATA_PATH)
    print(f"Loaded {len(rows):,} course rows. Aggregate counts only:")
    for code, numbers, course_name in COURSES:
        course_rows = course_rows_for(rows, code, numbers)
        attempts = first_attempt(course_rows)
        known = attempts["RETENTION_FLAG"].isin(["0", "1"])
        summary = summarize(attempts)
        destination = OUTPUT_DIR / f"{slug(course_name)}-not-retained-by-grade.pdf"
        draw(course_name, summary, destination)
        print(
            f"{course_name}: {len(course_rows):,} rows, {attempts['STUDENT_ID'].nunique():,} students, "
            f"{int((~known).sum()):,} excluded (retention not known yet)"
        )
        if numbers == ("100", "100H"):
            honors = first_attempt(course_rows_for(rows, code, ("100H",)))
            regular = first_attempt(course_rows_for(rows, code, ("100",)))
            both = len(set(honors["STUDENT_ID"]) & set(regular["STUDENT_ID"]))
            print(
                f"  includes ENGR 100H: {honors['STUDENT_ID'].nunique():,} students, "
                f"{both:,} also have an ENGR 100 grade and are counted once"
            )
        for record in summary.itertuples(index=False):
            print(
                f"  {record.grade}: {int(record.not_retained):,} not retained "
                f"of {int(record.students):,} ({record.percent:.1f}%)"
            )
        print(f"  wrote {destination}")

    multi = students_in_multiple(course_attempts(rows))
    flag_counts = multi.groupby("STUDENT_ID")["RETENTION_FLAG"].nunique()
    conflicts = int((flag_counts > 1).sum())
    if conflicts:
        multi = multi[~multi["STUDENT_ID"].isin(flag_counts[flag_counts > 1].index)]
        print(f"Excluded {conflicts:,} students with conflicting retention flags")

    grades = grades_in_use(multi)
    course_counts = multi.groupby("STUDENT_ID")["COURSE"].nunique()
    mix = ", ".join(
        f"{int(count):,} took {int(number)}"
        for number, count in course_counts.value_counts().sort_index().items()
    )
    print(
        f"Students in at least two of the four courses: {multi['STUDENT_ID'].nunique():,} "
        f"({mix})"
    )
    for flag, heading, filename in (
        ("1", "Retained students who took at least two of these courses", "multi-course-retained-by-grade.pdf"),
        ("0", "Students not retained who took at least two of these courses", "multi-course-not-retained-by-grade.pdf"),
    ):
        group = multi[multi["RETENTION_FLAG"] == flag]
        panels = performance_by_course(group, grades)
        group_counts = group.groupby("STUDENT_ID")["COURSE"].nunique()
        words = {2: "two", 3: "three", 4: "four"}
        mix_parts = [
            f"{int(count):,} took {words.get(int(number), str(int(number)))}"
            for number, count in group_counts.value_counts().sort_index().items()
        ]
        if len(mix_parts) > 1:
            mix = ", ".join(mix_parts[:-1]) + f", and {mix_parts[-1]}"
        else:
            mix = mix_parts[0] if mix_parts else "none"
        detail = (
            f"{group['STUDENT_ID'].nunique():,} students in MTH 251, MTH 252, CH 201, and ENGR 100, including ENGR 100H "
            f"({mix} of those courses)."
        )
        destination = OUTPUT_DIR / filename
        draw_performance(heading, detail, panels, grades, destination)
        print(f"{heading}: {group['STUDENT_ID'].nunique():,} students ({mix})")
        for course_name, summary in panels:
            print(f"  {course_name}: {int(summary['students'].sum()):,} students")
            for record in summary.itertuples(index=False):
                if int(record.students) == 0:
                    continue
                print(f"    {record.grade}: {int(record.students):,} ({record.percent:.1f}%)")
        print(f"  wrote {destination}")


if __name__ == "__main__":
    main()
