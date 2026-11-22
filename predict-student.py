from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

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


def read_student_id() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1].strip()
    return input("Student ID: ").strip()


def main() -> None:
    student_id = read_student_id()
    if not student_id:
        raise SystemExit("Enter a student ID from the fake combined workbook.")
    _model.score_student(_model.DEFAULT_DATA, _model.DEFAULT_MODEL, student_id)


if __name__ == "__main__":
    main()
