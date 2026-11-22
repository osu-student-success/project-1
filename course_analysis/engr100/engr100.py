#!/usr/bin/env python3
"""
ENGR 100: how many FTFT-in-CoE students took it, and how many were retained vs not retained.

Step 1: run retention_coe.py first (it writes <out>/<sheet>/student_outcomes.csv).
Step 2: python engr100.py "Grades by cohort.xlsx" --outcomes-dir retention_coe_output
            [--out-dir engr100_output] [--subj ENGR] [--number 100]
            [--any-term] [--id-col STUDENT_ID] [--sheet 202401] [--term-col TRANSCRIPT_TERM]

"Took ENGR 100" = the student has at least one grade record with SUBJ_CODE == ENGR and
SUBJ_NUMBER == 100 (a withdrawal W still counts as having enrolled; those are also counted
separately). By default only records from the first-year window are used: the cohort's entry term
up to, but not including, the next fall. --any-term counts a record from any term.

Rates: Retained / Not retained are % of students who took the course AND have a known outcome.
Unknown-outcome students (next fall not observable) are shown separately and left out.
"""
import argparse
import re
from pathlib import Path

import pandas as pd


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


def pct(n, d):
    return f"{n} ({100 * n / d:.1f}%)" if d else f"{n} (n/a)"


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
    return o.drop_duplicates("SID")


def analyze(df, out, args, name, out_dir):
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
    n_course_rows = int(is_course.sum())

    m = df[is_course].merge(out[["SID", "Cohort", "Group"]], on="SID", how="left")
    not_ftft = m[m["Cohort"].isna()]
    m = m[m["Cohort"].notna()].copy()
    m["Cohort"] = m["Cohort"].astype(int)
    m["NEXT"] = (m["Cohort"] // 100 + 1) * 100 + 1
    in_window = (m["TERM"] >= m["Cohort"]) & (m["TERM"] < m["NEXT"])
    outside = m[~in_window]
    if not args.any_term:
        m = m[in_window]
    m["W"] = m["GRADE"].str.upper().isin({"W", "WD"})

    print(f"{args.subj.upper()} {args.number} records in sheet: {n_course_rows}")
    print(f"  records for students not in the FTFT-in-CoE outcomes (excluded): {len(not_ftft)}"
          f" ({not_ftft['SID'].nunique()} students)")
    print(f"  records outside the first-year window "
          f"({'kept, --any-term' if args.any_term else 'excluded'}): {len(outside)}")

    rows = []
    for c in sorted(set(m["Cohort"])):
        oc = out[out["Cohort"] == c]
        mc = m[m["Cohort"] == c]
        took = mc.groupby("SID").agg(Group=("Group", "first"), W=("W", "any")).reset_index()
        n_all, n_took = len(oc), len(took)
        unk = int((took["Group"] == "Unknown").sum())
        ret = int((took["Group"] == "Retained").sum())
        nr = int((took["Group"] == "Not retained").sum())
        known = ret + nr
        print(f"\nCohort {c}")
        print(f"  FTFT-in-CoE students (all outcomes):        {n_all}")
        print(f"  Took {args.subj.upper()} {args.number}:                        {pct(n_took, n_all)} of cohort")
        print(f"    with a withdrawal (W) in the course:      {int(took['W'].sum())}")
        print(f"    Unknown outcome (excluded from rates):    {unk}")
        print(f"    Known-outcome denominator:                {known}")
        print(f"    Retained:                                 {pct(ret, known)}")
        print(f"    Not retained:                             {pct(nr, known)}")
        rows.append({"Cohort": c, "FTFT in CoE (all)": n_all, "Took course": n_took,
                     "Took course (% of cohort)": f"{100 * n_took / n_all:.1f}%" if n_all else "n/a",
                     "Withdrew (W)": int(took["W"].sum()), "Unknown outcome": unk,
                     "Known-outcome denominator": known,
                     "Retained": ret, "Retained %": f"{100 * ret / known:.1f}%" if known else "n/a",
                     "Not retained": nr, "Not retained %": f"{100 * nr / known:.1f}%" if known else "n/a"})
    if not rows:
        print("\nNo FTFT-in-CoE students with this course were found in this sheet.")
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_dir / "engr100_summary.csv", index=False)
    return rows


def plot(rows, args):
    """Stacked bar per cohort: retained vs not retained among students who took the course."""
    try:
        import matplotlib
        if args.no_show:
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\nTo get the plot, run: pip install matplotlib")
        return
    df = pd.DataFrame(rows).sort_values("Cohort").reset_index(drop=True)
    labels = [f"{r['Cohort']}\n(known n={r['Known-outcome denominator']}, unknown {r['Unknown outcome']})"
              for _, r in df.iterrows()]
    fig, ax = plt.subplots(figsize=(max(7, 1.8 * len(df) + 2), 5.5))
    x = list(range(len(df)))
    ax.bar(x, df["Retained"], color="#2e7d32", label="Retained")
    ax.bar(x, df["Not retained"], bottom=df["Retained"], color="#c62828", label="Not retained")
    for i, r in df.iterrows():
        k = r["Retained"] + r["Not retained"]
        if not k:
            continue
        if r["Retained"]:
            ax.text(i, r["Retained"] / 2, f"{r['Retained']}\n{100 * r['Retained'] / k:.0f}%",
                    ha="center", va="center", color="white", fontweight="bold")
        if r["Not retained"]:
            ax.text(i, r["Retained"] + r["Not retained"] / 2,
                    f"{r['Not retained']}\n{100 * r['Not retained'] / k:.0f}%",
                    ha="center", va="center", color="white", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel(f"Students who took {args.subj.upper()} 100")
    ax.set_xlabel("Cohort")
    ax.set_title(f"{args.subj.upper()} 100: retained vs not retained, by cohort\n"
                 "(percent of students with a known outcome; unknown outcomes excluded)")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    png = Path(args.out_dir) / "engr100_retention.png"
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
    ap.add_argument("--any-term", action="store_true",
                    help="Count records from any term, not just the first-year window")
    ap.add_argument("--id-col")
    ap.add_argument("--sheet", help="Run only this sheet (default: every sheet, one at a time)")
    ap.add_argument("--out-dir", default="engr100_output")
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

    all_rows = []
    for name, d in sheets.items():
        print("\n" + "=" * 70 + f"\nSHEET: {name}\n" + "=" * 70)
        folder = Path(args.out_dir) / re.sub(r"[^\w.-]+", "_", str(name))
        all_rows += analyze(clean(d), out, args, name, folder)
    if all_rows:
        plot(all_rows, args)


if __name__ == "__main__":
    main()
