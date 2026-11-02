from __future__ import annotations

import math
import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DEFAULT_PATH = ROOT / "data" / "fake-students.csv"
ROW_COUNT = 210

MAJORS = [
    "Biology",
    "Business",
    "Chemistry",
    "Communications",
    "Computer Science",
    "Economics",
    "Education",
    "Engineering",
    "English",
    "History",
    "Mathematics",
    "Nursing",
    "Political Science",
    "Psychology",
]

MINORS = [
    "None",
    "Art",
    "Business",
    "Creative Writing",
    "Data Science",
    "Mathematics",
    "Music",
    "Philosophy",
    "Psychology",
    "Sociology",
    "Spanish",
    "Statistics",
]

HOMETOWNS = [
    "Ann Arbor, MI",
    "Austin, TX",
    "Boise, ID",
    "Chicago, IL",
    "Cleveland, OH",
    "Columbus, OH",
    "Denver, CO",
    "Detroit, MI",
    "Flint, MI",
    "Grand Rapids, MI",
    "Indianapolis, IN",
    "Lansing, MI",
    "Madison, WI",
    "Milwaukee, WI",
    "Minneapolis, MN",
    "Phoenix, AZ",
    "Pittsburgh, PA",
    "Toledo, OH",
]

# Small shifts so major is a weak signal, not the whole story.
MAJOR_RISK = {
    "Chemistry": 0.08,
    "Computer Science": 0.12,
    "Education": -0.15,
    "Engineering": 0.25,
    "Mathematics": 0.10,
    "Nursing": -0.20,
    "Psychology": 0.05,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-value))


def _term_credits(rng: random.Random, gpa: float, classes_dropped: int, winter: bool) -> int:
    mean = 9 + gpa * 1.8 - classes_dropped * 0.35
    if winter:
        mean -= 1
    credits = int(round(rng.gauss(mean, 2.0)))
    return int(_clamp(credits, 0, 18))


def _dropout_probability(student: dict) -> float:
    credits = student["credits_fall"] + student["credits_winter"] + student["credits_spring"]
    score = -1.55
    score += (2.6 - student["gpa"]) * 1.45
    score += (40 - credits) * 0.07
    score += student["classes_dropped"] * 0.28
    score += 0.45 if student["changed_major"] else 0
    score += 0.12 if student["changed_minor"] else 0
    score += -0.25 if student["fafsa"] else 0.15
    score += -0.10 if student["parents_graduated_college"] else 0.30
    score += student["hours_worked_per_week"] * 0.03
    score += -0.15 if student["lives_on_campus"] else 0.10
    score += MAJOR_RISK.get(student["major"], 0)
    score += student["_noise"]
    return _sigmoid(score)


def generate(path: Path = DEFAULT_PATH, row_count: int = ROW_COUNT, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []

    for offset in range(row_count):
        major = rng.choice(MAJORS)
        if rng.random() < 0.62:
            minor_choices = [minor for minor in MINORS if minor not in {"None", major}]
            minor = rng.choice(minor_choices)
            changed_minor = int(rng.random() < 0.22)
        else:
            minor = "None"
            changed_minor = 0

        classes_dropped = rng.choices(
            [0, 1, 2, 3, 4, 5, 6],
            weights=[30, 28, 18, 12, 7, 3, 2],
        )[0]
        gpa = rng.gauss(3.05, 0.55) - 0.15 * classes_dropped + rng.gauss(0, 0.08)
        gpa = round(_clamp(gpa, 0.50, 4.00), 2)

        parents_graduated = int(rng.random() < 0.48)
        if rng.random() < 0.38:
            hours_worked = 0
        else:
            center = 10 if parents_graduated else 16
            hours_worked = int(round(_clamp(rng.gauss(center, 7), 0, 35)))

        student = {
            "student_id": 1001 + offset,
            "gpa": gpa,
            "credits_fall": _term_credits(rng, gpa, classes_dropped, winter=False),
            "credits_winter": _term_credits(rng, gpa, classes_dropped, winter=True),
            "credits_spring": _term_credits(rng, gpa, classes_dropped, winter=False),
            "hometown": rng.choice(HOMETOWNS),
            "fafsa": int(rng.random() < 0.68),
            "parents_graduated_college": parents_graduated,
            "major": major,
            "minor": minor,
            "changed_major": int(rng.random() < 0.28),
            "changed_minor": changed_minor,
            "classes_dropped": classes_dropped,
            "hours_worked_per_week": hours_worked,
            "lives_on_campus": int(rng.random() < 0.60),
            "_noise": rng.gauss(0, 0.45),
        }
        student["dropped_out"] = int(rng.random() < _dropout_probability(student))
        del student["_noise"]
        rows.append(student)

    frame = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


def main() -> None:
    frame = generate()
    dropped = int(frame["dropped_out"].sum())
    print(f"Wrote {len(frame)} students to {DEFAULT_PATH}")
    print(f"Dropped out: {dropped} ({dropped / len(frame):.1%})")
    print(f"Mean GPA: {frame['gpa'].mean():.2f}")
    print(f"Mean classes dropped: {frame['classes_dropped'].mean():.2f}")


if __name__ == "__main__":
    main()
