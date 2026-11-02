from __future__ import annotations

import sys

import pandas as pd

from dropout_model import (
    DEFAULT_DATA,
    DEFAULT_MODEL,
    FEATURES,
    ID_COLUMN,
    dropout_percent,
    load_pipeline,
    load_students,
)


def read_student_id() -> int:
    if len(sys.argv) > 1:
        raw = sys.argv[1]
    else:
        raw = input("Student ID: ")

    try:
        return int(raw.strip())
    except ValueError:
        raise SystemExit(f"Student ID must be a number. Got: {raw!r}")


def find_student(students: pd.DataFrame, student_id: int) -> pd.Series:
    matches = students[students[ID_COLUMN] == student_id]
    if matches.empty:
        raise SystemExit(f"No student with ID {student_id} in {DEFAULT_DATA.name}.")
    return matches.iloc[0]


def main() -> None:
    student_id = read_student_id()
    students = load_students(DEFAULT_DATA)
    student = find_student(students, student_id)
    pipeline = load_pipeline(DEFAULT_MODEL, DEFAULT_DATA)
    percent = dropout_percent(pipeline, student[FEATURES].to_dict())
    print(f"Student {student_id}: {percent:.1f}% likelihood of dropping out")


if __name__ == "__main__":
    main()
