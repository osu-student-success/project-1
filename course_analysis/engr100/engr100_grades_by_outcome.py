#!/usr/bin/env python3
"""
ENGR 100: grades earned by RETAINED vs NOT RETAINED students, by cohort (table + plot).

Step 1: run retention_coe.py first (it writes <out>/<sheet>/student_outcomes.csv).
Step 2: python engr100_grades_by_outcome.py "Grades by cohort.xlsx" --outcomes-dir retention_coe_output
            [--out-dir engr100_outcome_output] [--subj ENGR] [--number 100]
            [--percent] [--any-term] [--no-show] [--id-col STUDENT_ID] [--sheet 202401]
            [--term-col TRANSCRIPT_TERM]

Who is counted: FTFT-in-CoE students (from retention_coe.py) with at least one grade record in
the course, in the first-year window (cohort entry term up to, but not including, the next fall;
--any-term uses all terms).
  Retained     : retained in CoE the next fall.
  Not retained : not retained (other college at OSU, or no next-fall row).
  Unknown      : next fall not observable -> left out of the comparison, counted separately.

One grade per student: if a student has several records in the course (a withdrawal then a retake,
or a repeat), the grade from their LATEST term is used. Withdrawals (W) and other non-letter
grades (P, NP, I, ...) are shown as their own grades.

Plot: grouped bars per cohort, counts by default. The two groups usually differ in size, so
--percent plots each grade as a % of that group's students instead (denominators in the table).
"""
import argparse
import re
from pathlib import Path

import pandas as pd

ORDER = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F",
         "P", "S", "NP", "N", "U", "W", "WD", "I", "IP", "X", "AU"]
GROUPS = ["Retained", "Not retained"]
COLORS = {"Retained": "#2e7d32", "Not retained": "#c62828"}


def clean(df):
    df.columns = [str(c).strip().upper().replace(" ", "_").rstrip("?") for c in df.columns]
    for c in df.columns:
        df[c] = df[c].fillna("").astype(str).str.strip()
    return df


def find_id_col(df, requested):
    if requested:
        return requested.strip().upper().replace(" ", "_")
    for c in ("STUDENT_ID", "STU_ID", "ID", "STUDENT"):
        if c in df.columns:
            return c
    raise SystemExit(f"Could not find a student ID column; pass --id-col. Columns: {list(df.columns)}")


def load_outcomes(folder):
    parts = []
    for f in sorted(Path(folder).glob("*/student_outcomes.csv")):
        try:
            d = pd.read_csv(f, dtype=str)
        except pd.errors.EmptyDataError:
            continue
        id_cols = [c for c in d.columns if c not in ("Sheet", "Cohort", "Outcome")]
        if d.empty or not id_cols:
            continue
        parts.append(d.rename(columns={id_cols[0]: "SID"})[["SID", "Cohort", "Outcome"]])
    if not parts:
        raise SystemExit(f"No student_outcomes.csv files found under '{folder}'. "
                         "Run retention_coe.py first, or pass --outcomes-dir.")
    o = pd.concat(parts, ignore_index=True)
    o["SID"] = o["SID"].str.strip()
    o["Cohort"] = o["Cohort"].astype(int)
    o["Group"] = o["Outcome"].map(lambda x: "Retained" if x == "Retained"
                                  else "Not retained" if str(x).startswith("Not retained") else "Unknown")
    return o.drop_duplicates("SID")[["SID", "Cohort", "Group"]]


def analyze(df, out, args, name):
    """Return one row per student: Cohort, Group, SID, GRADE (latest record in the course)."""
    ID = find_id_col(df, args.id_col)
    need = [ID, args.term_col, "SUBJ_CODE", "SUBJ_NUMBER", "GRADE"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise SystemExit(f"Sheet '{name}' is missing columns {missing}. Found: {list(df.columns)}")

    df = df.rename(columns={ID: "SID"}).copy()
    df["TERM"] = pd.to_numeric(df[args.term_col], errors="coerce")
    df = df[(df["SID"] != "") & df["TERM"].notna()].copy()
    df["TERM"] = df["TERM"].astype(int)
    num = df["SUBJ_NUMBER"].str.upper().str.replace(r"\.0$", "", regex=True)
    is_course = (df["SUBJ_CODE"].str.upper() == "ENGR") & (num == "100")
    n_course = int(is_course.sum())

    m = df[is_course].merge(out, on="SID", how="left")
    not_ftft = m[m["Cohort"].isna()]
    m = m[m["Cohort"].notna()].copy()
    m["Cohort"] = m["Cohort"].astype(int)
    m["NEXT"] = (m["Cohort"] // 100 + 1) * 100 + 1
    in_window = (m["TERM"] >= m["Cohort"]) & (m["TERM"] < m["NEXT"])
    outside = int((~in_window).sum())
    if not args.any_term:
        m = m[in_window]
    m["GRADE"] = m["GRADE"].str.upper().replace({"": "(blank)"})

    print(f"{args.subj.upper()} {args.number} records in sheet: {n_course}")
    print(f"  records for students not in the FTFT-in-CoE outcomes (excluded): {len(not_ftft)}"
          f" ({not_ftft['SID'].nunique()} students)")
    print(f"  records outside the first-year window ({'kept, --any-term' if args.any_term else 'excluded'}): {outside}")
    print(f"  students with more than one record in the course (latest term's grade used): "
          f"{int((m.groupby('SID').size() > 1).sum())}")

    return m.sort_values("TERM", kind="stable").drop_duplicates("SID", keep="last")[
        ["Cohort", "Group", "SID", "GRADE"]]


def grade_order(grades):
    present = set(grades)
    return [g for g in ORDER if g in present] + sorted(present - set(ORDER))


def plot(known, grades, args, out_dir):
    try:
        import matplotlib
        if args.no_show:
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\nTo get the plot, run: pip install matplotlib")
        return
    cohorts = sorted(known["Cohort"].unique())
    n = len(cohorts)
    ncols = min(2, n)
    nrows = -(-n // ncols)
    fig, axes = plt.subplots(nrows, ncols, sharey=True, squeeze=False,
                             figsize=(max(7, 0.7 * len(grades) * ncols + 1.5), 3.8 * nrows + 1.0))
    w = 0.4
    for k, c in enumerate(cohorts):
        ax = axes[k // ncols][k % ncols]
        title = f"Cohort {c}"
        for j, g in enumerate(GROUPS):
            sub = known[(known["Cohort"] == c) & (known["Group"] == g)]
            counts = sub["GRADE"].value_counts().reindex(grades, fill_value=0)
            vals = (100 * counts / len(sub)).tolist() if (args.percent and len(sub)) else counts.tolist()
            xs = [i + (j - 0.5) * w for i in range(len(grades))]
            ax.bar(xs, vals, width=w, color=COLORS[g], label=g)
            for x, v, cnt in zip(xs, vals, counts.tolist()):
                if cnt:
                    ax.text(x, v, f"{v:.0f}%" if args.percent else str(cnt),
                            ha="center", va="bottom", fontsize=7)
            title += f"   {g} n={len(sub)}"
        ax.set_title(title, fontsize=10)
        ax.set_xticks(range(len(grades)))
        ax.set_xticklabels(grades, rotation=90, fontsize=8)
        ax.spines[["top", "right"]].set_visible(False)
        if k % ncols == 0:
            ax.set_ylabel("% of group's students" if args.percent else "Students")
    for k in range(n, nrows * ncols):
        axes[k // ncols][k % ncols].set_visible(False)
    h, l = axes[0][0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper right", frameon=False)
    fig.suptitle(f"{args.subj.upper()} 100: grades of retained vs not retained students")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / ("engr100_grades_by_outcome_percent.png" if args.percent
                     else "engr100_grades_by_outcome.png")
    fig.savefig(png, dpi=150)
    print(f"\nPlot saved to {png}")
    if not args.no_show:
        plt.show()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("data", help="Grades workbook (one sheet per cohort)")
    ap.add_argument("--outcomes-dir", default="retention_coe_output")
    ap.add_argument("--subj", default="ENGR")
    ap.add_argument("--number", default="100")
    ap.add_argument("--term-col", default="TRANSCRIPT_TERM")
    ap.add_argument("--percent", action="store_true",
                    help="Plot each grade as a percent of its group's students instead of counts")
    ap.add_argument("--any-term", action="store_true",
                    help="Count records from any term, not just the first-year window")
    ap.add_argument("--id-col")
    ap.add_argument("--sheet", help="Run only this sheet (default: every sheet, one at a time)")
    ap.add_argument("--out-dir", default="engr100_outcome_output")
    ap.add_argument("--no-show", action="store_true", help="Save the plot PNG without opening a window")
    args = ap.parse_args()
    args.term_col = args.term_col.strip().upper().replace(" ", "_")

    out = load_outcomes(args.outcomes_dir)
    p = Path(args.data)
    if p.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        sheets = pd.read_excel(p, sheet_name=args.sheet if args.sheet else None, dtype=str)
        if isinstance(sheets, pd.DataFrame):
            sheets = {args.sheet: sheets}
    else:
        sheets = {p.stem: pd.read_csv(p, dtype=str)}

    parts = []
    for name, d in sheets.items():
        print("\n" + "=" * 70 + f"\nSHEET: {name}\n" + "=" * 70)
        res = analyze(clean(d), out, args, name)
        for c, g in res.groupby("Cohort"):
            kn = g[g["Group"].isin(GROUPS)]
            nr = {x: int((kn["Group"] == x).sum()) for x in GROUPS}
            print(f"\nCohort {c}: {len(g)} students took {args.subj.upper()} {args.number}; "
                  f"Unknown outcome (excluded): {int((g['Group'] == 'Unknown').sum())}")
            print(f"  Denominators: Retained n={nr['Retained']}, Not retained n={nr['Not retained']}")
            print(f"  {'Grade':>7}  {'Retained n (%)':>16}  {'Not retained n (%)':>20}")
            vc = {x: kn.loc[kn["Group"] == x, "GRADE"].value_counts() for x in GROUPS}
            for gr in grade_order(kn["GRADE"]):
                cells = []
                for x in GROUPS:
                    n_ = int(vc[x].get(gr, 0))
                    cells.append(f"{n_} ({100 * n_ / nr[x]:.1f}%)" if nr[x] else f"{n_} (n/a)")
                print(f"  {gr:>7}  {cells[0]:>16}  {cells[1]:>20}")
        parts.append(res)

    allr = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    known = allr[allr["Group"].isin(GROUPS)] if not allr.empty else allr
    if known.empty:
        print("\nNo retained / not-retained FTFT-in-CoE students with this course were found.")
        return
    grades = grade_order(known["GRADE"])
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for (c, g), sub in known.groupby(["Cohort", "Group"]):
        vc = sub["GRADE"].value_counts()
        for gr in grades:
            rows.append({"Cohort": c, "Group": g, "Grade": gr, "Students": int(vc.get(gr, 0)),
                         "Group denominator": len(sub),
                         "Percent of group": round(100 * vc.get(gr, 0) / len(sub), 1)})
    pd.DataFrame(rows).to_csv(out_dir / "grade_counts_by_cohort_outcome.csv", index=False)
    plot(known, grades, args, out_dir)


if __name__ == "__main__":
    main()
