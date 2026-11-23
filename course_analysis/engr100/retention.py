#!/usr/bin/env python3
"""
First-year retention by cohort (retention only), one sheet at a time.

Usage:
    python retention.py "Predictive Modeling By Cohort.xlsx" [--out-dir out]
        [--id-col STUDENT_ID] [--sheet 202401] [--last-term 202503]

Definitions
  Cohort term : FIRST_TERM_OF_ATTENDANCE (e.g. 202401 = Fall 2024).
  FTFT        : student has a row where PAST_TERM == cohort term AND
                STU_STATUS_CODE_DESC == "New Student" AND ENROLLMENT_STATUS == "F".
  Next fall   : the following year's Fall term (202401 -> 202501).
  Retained    : an FTFT student has any row with PAST_TERM == next fall.
  Not retained: an FTFT student has no row with PAST_TERM == next fall.
  Unknown     : next fall is later than the last term in the sheet, so it cannot be
                observed. Shown separately; no retained/not-retained rates are computed.
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


def analyze(df, args, name, out_dir):
    ID = find_id_col(df, args.id_col)
    need = ["PAST_TERM", "FIRST_TERM_OF_ATTENDANCE", "STU_STATUS_CODE_DESC", "ENROLLMENT_STATUS", ID]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise SystemExit(f"Sheet '{name}' is missing columns {missing}. Found: {list(df.columns)}")

    df = df.copy()
    df["TERM"] = pd.to_numeric(df["PAST_TERM"], errors="coerce")
    df["FIRST"] = pd.to_numeric(df["FIRST_TERM_OF_ATTENDANCE"], errors="coerce")
    n_rows = len(df)
    df = df[(df[ID] != "") & df["TERM"].notna() & df["FIRST"].notna()].copy()
    dropped = n_rows - len(df)
    df["TERM"] = df["TERM"].astype(int)
    df["FIRST"] = df["FIRST"].astype(int)
    df["STATUS"] = df["STU_STATUS_CODE_DESC"].str.upper()
    df["ENR"] = df["ENROLLMENT_STATUS"].str.upper()

    last_term = args.last_term or int(df["TERM"].max())
    print(f"Rows read: {n_rows}   rows dropped (missing ID / PAST_TERM / FIRST_TERM): {dropped}")
    print(f"Last term in sheet: {last_term}")

    entry = df[df["TERM"] == df["FIRST"]]
    summary, students = [], []
    for first, g in entry.groupby("FIRST"):
        ftft = g[(g["STATUS"] == "NEW STUDENT") & (g["ENR"] == "F")]
        ftft_ids = set(ftft[ID])
        entry_ids = set(g[ID])
        no_entry = df.loc[df["FIRST"] == first, ID].nunique() - len(entry_ids)
        next_fall = (first // 100 + 1) * 100 + 1

        row = {"Sheet": name, "Cohort": first, "Next fall": next_fall,
               "Students with entry-term row": len(entry_ids),
               "Not FTFT (not New Student + F)": len(entry_ids - ftft_ids),
               "No entry-term row (excluded)": no_entry,
               "FTFT (denominator)": len(ftft_ids)}
        if next_fall > last_term:
            row.update({"Retained": "n/a", "Not retained": "n/a",
                        "Unknown (next fall not in data)": len(ftft_ids)})
            kept = None
        else:
            present = set(df.loc[df["TERM"] == next_fall, ID])
            kept = ftft_ids & present
            row.update({"Retained": pct(len(kept), len(ftft_ids)),
                        "Not retained": pct(len(ftft_ids) - len(kept), len(ftft_ids)),
                        "Unknown (next fall not in data)": 0})
        summary.append(row)
        for sid in sorted(ftft_ids):
            students.append({"Sheet": name, "Cohort": first, ID: sid,
                             "Outcome": "Unknown" if kept is None else
                             ("Retained" if sid in kept else "Not retained")})
        if first % 100 != 1:
            print(f"WARNING: cohort {first} is not a Fall term; next fall taken as {next_fall}.")

    out = pd.DataFrame(summary)
    print(out.T.to_string(header=False) if len(out) == 1 else out.to_string(index=False))
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_dir / "retention_summary.csv", index=False)
    pd.DataFrame(students).to_csv(out_dir / "student_outcomes.csv", index=False)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("data")
    ap.add_argument("--id-col")
    ap.add_argument("--sheet", help="Run only this sheet (default: every sheet, one at a time)")
    ap.add_argument("--last-term", type=int,
                    help="Last term with complete data (default: max PAST_TERM in each sheet)")
    ap.add_argument("--out-dir", default="retention_output")
    args = ap.parse_args()

    p = Path(args.data)
    if p.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        sheets = pd.read_excel(p, sheet_name=args.sheet if args.sheet else None, dtype=str)
        if isinstance(sheets, pd.DataFrame):
            sheets = {args.sheet: sheets}
    else:
        sheets = {p.stem: pd.read_csv(p, dtype=str)}

    for name, d in sheets.items():
        print("\n" + "=" * 70 + f"\nSHEET: {name}\n" + "=" * 70)
        folder = Path(args.out_dir) / re.sub(r"[^\w.-]+", "_", str(name))
        analyze(clean(d), args, name, folder)


if __name__ == "__main__":
    main()
