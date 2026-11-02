from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent


def _load_sibling(filename: str):
    path = ROOT / filename
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_model = _load_sibling("dropout-model.py")
DEFAULT_DATA = _model.DEFAULT_DATA
DEFAULT_MODEL = _model.DEFAULT_MODEL
FEATURES = _model.FEATURES
ID_COLUMN = _model.ID_COLUMN
dropout_percent = _model.dropout_percent
load_pipeline = _model.load_pipeline
load_students = _model.load_students


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
