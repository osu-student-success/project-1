import os, hashlib, hmac, secrets, warnings, re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

try:
    from IPython.display import display
except ImportError:       
    display = print

pd.set_option("display.max_columns", 60)
pd.set_option("display.width", 170)
pd.set_option("display.max_rows", 200)

# ----------------------------------------------------------------------------------------
# Where things live. Keep DATA_DIR and OUT_DIR out of git.
DATA_DIR = Path("data_private")
OUT_DIR = Path("eda_outputs")
FIG_DIR = OUT_DIR / "figures"
USE_CACHE = False
SAVE_TABLES = False         

# Global patterns relative to DATA_DIR. Each may match one workbook
# or several workbooks. All sheets in every matched file are read.
FILES = {
    "pm": "Predictive Modeling By Cohort*.xlsx",
    "grades": "grades_by_cohort*.xlsx",
    "fa": "cohort FA need*.xlsx",
}

# Column types, from the skeletons you gave. Integers are read as text first, then converted.
SCHEMA = {
    "pm": dict(
        str_cols=["STUDENT_ID", "ACAD_STAND_CODE_DESC", "STU_STATUS_CODE_DESC", "STU_TYPE_CODE_DESC",
                  "ENROLLMENT_STATUS", "PRIMARY_CAMPUS_CODE", "ADMIT_TYPE_CODE_DESC", "DEGREE_AWARDED_STATUS"],
        int_cols=["PAST_TERM", "FIRST_TERM_OF_ATTENDANCE", "CLASS_STANDING", "PRIMARY_MAJOR1", "ADMIT_COLLEGE",
                  "ADMIT_MAJOR", "PRIMARY_COLLEGE", "MIN_PAST_TERM", "MAX_PAST_TERM"],
        float_cols=["TERM_QUALITY_POINTS", "TERM_GPA", "HIGH_SCHOOL_GPA"]),
    "grades": dict(
        str_cols=["STUDENT_ID", "DEPT_CODE", "SUBJ_CODE", "SUBJ_NUMBER", "GRADE"],
        int_cols=["PAST_TERM", "TRANSCRIPT_TERM"], float_cols=[]),
    "fa": dict(
        str_cols=["STUDENT_ID", "Pell", "FA_NEED_RANGE"],
        int_cols=["STUDENT_LEVL", "SFRSTCR_TERM_CODE", "UNMET_NEED_ROUNDED_1000"], float_cols=[]),
}

# Text that means "missing" even though the cell is not empty (compared lowercased, trimmed).
# Pandas' own NA list is switched off on read so these are counted here instead of vanishing silently.
MISSING_TOKENS = {"na", "n/a", "#n/a", "null", "none", "nan", "-", "--", ".", "?", "unknown"}
# Empty or whitespace-only cells are always treated as missing and counted separately.

TERM_PATTERN = r"^\d{6}$"

FTFT_CRITERIA = [
    {"column": "STU_TYPE_CODE_DESC", "regex": r"^Freshman\s*(<\s*24\s*hours|- Early Admit)$"},
]
CONFLICTING_FIRST_TERM = "exclude"     
REQUIRE_ENTRY_TERM_ROW = True          
COHORTS_OF_INTEREST = None             

RETENTION_OFFSET = 100
ENROLLED_VALUES_AT_TARGET = None      

MIN_CELL = 10                          # warn when an exported count is below this (small-cell risk)

# Salted hashing of IDs in anything exported.
_SALT = os.environ.get("STUDENT_ID_SALT")
if not _SALT:
    _SALT = secrets.token_hex(16)
    print("STUDENT_ID_SALT is not set: using a random per-session salt (exported hashes will not match across runs).")


def pseudo(x):
    return hmac.new(_SALT.encode(), str(x).encode(), hashlib.sha256).hexdigest()[:12]


OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)
tables = {}            

def _norm(c):
    return str(c).strip().upper().replace(" ", "_")


def _to_float(s):
    t = s.astype("string").str.replace(",", "", regex=False).str.replace(r"^\$", "", regex=True)
    return pd.to_numeric(t.astype(object).where(t.notna(), np.nan), errors="coerce").astype("float64")


def _type_columns(raw, name):
    spec = SCHEMA[name]
    out, rep = {}, []
    for c in spec["str_cols"] + spec["int_cols"] + spec["float_cols"]:
        s = raw[c].astype("string").str.strip()
        blank = (s.isna() | (s == "")).fillna(True).astype(bool)
        tok = (s.str.lower().isin(MISSING_TOKENS).fillna(False).astype(bool)) & ~blank
        n_blank, n_tok = int(blank.sum()), int(tok.sum())
        s = s.mask(blank | tok)
        n_bad = 0
        if c in spec["str_cols"]:
            if c == "STUDENT_ID":
                s = s.str.replace(r"\.0+$", "", regex=True)    
            out[c] = s
        else:
            x = _to_float(s)
            n_bad = int((x.isna() & s.notna()).sum())
            if c in spec["int_cols"]:
                frac = x.notna() & (x % 1 != 0)
                n_bad += int(frac.sum())
                x = x.where(~frac).round().astype("Int64")
            out[c] = x
        rep.append(dict(dataset=name, column=c, blank_cells=n_blank, text_tokens_to_missing=n_tok,
                        unparseable_to_missing=n_bad))
    typed = pd.DataFrame(out)
    typed["SOURCE_FILE"] = raw["SOURCE_FILE"].values
    typed["SHEET"] = raw["SHEET"].values
    return typed, pd.DataFrame(rep)


def load_dataset(name):
    spec = SCHEMA[name]
    required = spec["str_cols"] + spec["int_cols"] + spec["float_cols"]
    files = sorted(DATA_DIR.glob(FILES[name]))
    if not files:
        raise FileNotFoundError(f"[{name}] no files match {DATA_DIR / FILES[name]}")
    cfg = hashlib.md5(repr((SCHEMA[name], sorted(MISSING_TOKENS))).encode()).hexdigest()[:8]   
    cache = OUT_DIR / "cache" / f"{name}_{cfg}.pkl"
    if USE_CACHE and cache.exists() and cache.stat().st_mtime > max(f.stat().st_mtime for f in files):
        return pd.read_pickle(cache)
    lookup = {_norm(c): c for c in required}
    frames = []
    for f in files:
        for sheet, df in pd.read_excel(f, sheet_name=None, dtype=str, keep_default_na=False, na_values=[]).items():
            df = df.rename(columns={c: lookup[_norm(c)] for c in df.columns if _norm(c) in lookup})
            found = [c for c in required if c in df.columns]
            if len(found) < len(required) / 2:
                print(f"[{name}] skipping {f.name} / {sheet}: only {len(found)} of {len(required)} expected columns")
                continue
            absent = [c for c in required if c not in df.columns]
            if absent:
                print(f"[{name}] {f.name} / {sheet}: expected columns absent (filled as missing): {absent}")
                for c in absent:
                    df[c] = np.nan
            df = df[required].copy()
            df["SOURCE_FILE"], df["SHEET"] = f.name, str(sheet)
            frames.append(df)
    raw = pd.concat(frames, ignore_index=True)
    result = _type_columns(raw, name)
    if USE_CACHE:
        cache.parent.mkdir(parents=True, exist_ok=True)
        pd.to_pickle(result, cache)
    return result


def build_roster(pm):
    steps, excluded = [], {}
    p = pm[pm.STUDENT_ID.notna()].copy()
    n_blank = int(pm.STUDENT_ID.isna().sum())
    stu = pd.DataFrame(index=pd.Index(p.STUDENT_ID.unique(), name="STUDENT_ID"))
    reason = pd.Series(pd.NA, index=stu.index, dtype="object")
    steps.append(dict(step="0", rule=f"Unique STUDENT_IDs in PM file ({n_blank} rows with blank ID ignored)",
                      before=np.nan, removed=np.nan, after=len(stu)))

    def apply(keep_mask, step, rule):
        nonlocal stu
        keep_mask = keep_mask.reindex(stu.index).fillna(False).astype(bool)
        gone = stu.index[~keep_mask]
        reason.loc[gone] = f"{step}: {rule}"
        excluded[f"{step}: {rule}"] = [pseudo(i) for i in gone]
        steps.append(dict(step=step, rule=rule, before=len(stu), removed=len(gone), after=int(keep_mask.sum())))
        stu = stu[keep_mask]

    g = p.groupby("STUDENT_ID")["FIRST_TERM_OF_ATTENDANCE"]
    stu["n_first_terms"] = g.nunique(dropna=True)
    stu["first_term"] = g.min()

    ok = stu.first_term.notna() & stu.first_term.astype("string").str.match(TERM_PATTERN).fillna(False)
    apply(ok, "1", "FIRST_TERM_OF_ATTENDANCE present and well-formed")

    conflict = stu.n_first_terms > 1
    if CONFLICTING_FIRST_TERM == "exclude":
        apply(~conflict, "2", "Single FIRST_TERM_OF_ATTENDANCE across the student's rows")
    else:
        steps.append(dict(step="2", rule=f"Conflicting first terms kept using the earliest ({int(conflict.sum())} students)",
                          before=len(stu), removed=0, after=len(stu)))

    p = p[p.STUDENT_ID.isin(stu.index)].join(stu.first_term.rename("_ft"), on="STUDENT_ID")
    entry = p[(p.PAST_TERM == p._ft).fillna(False)]
    n_dup_entry = len(entry) - entry.STUDENT_ID.nunique()
    entry = entry.sort_values(["STUDENT_ID", "SOURCE_FILE", "SHEET"]).drop_duplicates("STUDENT_ID", keep="first")
    if REQUIRE_ENTRY_TERM_ROW:
        apply(pd.Series(stu.index.isin(entry.STUDENT_ID), index=stu.index), "3", "Has a PM row at the entry term")
    if n_dup_entry:
        steps.append(dict(step="3b", rule=f"NOTE: {n_dup_entry} duplicate entry-term rows dropped (first kept)",
                          before=np.nan, removed=np.nan, after=np.nan))

    entry_by_id = entry.set_index("STUDENT_ID")
    if not FTFT_CRITERIA:
        print("WARNING: FTFT_CRITERIA is empty. No FTFT filter applied.")
    for i, crit in enumerate(FTFT_CRITERIA, start=1):
        s = entry_by_id[crit["column"]]
        if "regex" in crit:
            m = s.astype("string").str.contains(crit["regex"], case=False, regex=True, na=False)
            label = f"{crit['column']} matches /{crit['regex']}/"
        else:
            m = s.isin(crit["values"])
            label = f"{crit['column']} in {crit['values']}"
        apply(m, f"4.{i}", label)
    if not any(c["column"] == "ENROLLMENT_STATUS" for c in FTFT_CRITERIA):
        print("NOTE: no full-time criterion configured; the roster is 'first-time', full-time is NOT verified.")

    if COHORTS_OF_INTEREST is not None:
        apply(stu.first_term.isin(COHORTS_OF_INTEREST), "5", f"Cohort in {COHORTS_OF_INTEREST}")

    roster = entry_by_id.loc[entry_by_id.index.isin(stu.index)].copy()
    roster["COHORT"] = stu.first_term.reindex(roster.index).astype("Int64")
    roster = roster.reset_index()
    status = reason.fillna("FTFT roster")
    # all PM students, whether kept or not, with their first term (used for per-cohort exclusion counts)
    first_all = p.groupby("STUDENT_ID")["_ft"].min()
    return roster, pd.DataFrame(steps), excluded, status, first_all


def load_all():
    """Load the three workbooks and return typed data plus conversion audit."""
    loaded = {k: load_dataset(k) for k in FILES}
    pm, grades, fa = loaded["pm"][0], loaded["grades"][0], loaded["fa"][0]
    conv = pd.concat([loaded[k][1] for k in loaded], ignore_index=True)
    return pm, grades, fa, conv


def build_base():
    """Build the shared roster and student-level aggregates used by analysis scripts."""
    pm, grades, fa, conv = load_all()
    roster, waterfall, excluded_ids, student_status, first_all = build_roster(pm)
    assert roster.STUDENT_ID.is_unique

    ids_g = pd.Series(grades.STUDENT_ID.dropna().unique(), name="STUDENT_ID")
    ids_f = pd.Series(fa.STUDENT_ID.dropna().unique(), name="STUDENT_ID")
    roster = roster.copy()
    roster["in_grades"] = roster.STUDENT_ID.isin(ids_g)
    roster["in_fa"] = roster.STUDENT_ID.isin(ids_f)
    roster["in_all_three"] = roster.in_grades & roster.in_fa
    cohort_counts = roster.groupby("COHORT").agg(
        pm_ftft=("STUDENT_ID", "nunique"), in_grades=("in_grades", "sum"),
        in_fa=("in_fa", "sum"), in_all_three=("in_all_three", "sum"))
    cohort_counts["grades_coverage_pct"] = (100 * cohort_counts.in_grades / cohort_counts.pm_ftft).round(1)
    cohort_counts["fa_coverage_pct"] = (100 * cohort_counts.in_fa / cohort_counts.pm_ftft).round(1)
    totals = cohort_counts[["pm_ftft", "in_grades", "in_fa", "in_all_three"]].sum()
    total_row = pd.DataFrame([{
        **totals.to_dict(),
        "grades_coverage_pct": round(100 * totals.in_grades / totals.pm_ftft, 1),
        "fa_coverage_pct": round(100 * totals.in_fa / totals.pm_ftft, 1)
    }], index=["TOTAL"])
    cohort_counts = pd.concat([cohort_counts, total_row])

    roster_ids = set(roster.STUDENT_ID)
    pm_ft = pm[pm.STUDENT_ID.isin(roster_ids)].copy()
    grades_ft = grades[grades.STUDENT_ID.isin(roster_ids)].copy()
    fa_ft = fa[fa.STUDENT_ID.isin(roster_ids)].copy()

    course_key = grades_ft.SUBJ_CODE.fillna("?") + "-" + grades_ft.SUBJ_NUMBER.fillna("?")
    grades_agg = (grades_ft.assign(
        course_key=course_key,
        m_grade=grades_ft.GRADE.isna().astype(int),
        m_dept=grades_ft.DEPT_CODE.isna().astype(int),
        m_subjnum=grades_ft.SUBJ_NUMBER.isna().astype(int))
        .groupby("STUDENT_ID")
        .agg(gr_rows=("GRADE", "size"), gr_terms=("TRANSCRIPT_TERM", "nunique"),
             gr_courses=("course_key", "nunique"), gr_missing_grade=("m_grade", "sum"),
             gr_missing_dept=("m_dept", "sum"), gr_missing_subjnum=("m_subjnum", "sum"))
        .reset_index())
    fa_agg = (fa_ft.assign(pell_missing=fa_ft.Pell.isna().astype(int))
        .groupby("STUDENT_ID")
        .agg(fa_rows=("STUDENT_ID", "size"), fa_terms=("SFRSTCR_TERM_CODE", "nunique"),
             fa_pell_missing_rows=("pell_missing", "sum"),
             fa_unmet_need_max=("UNMET_NEED_ROUNDED_1000", "max"))
        .reset_index())

    cohort_of = roster.set_index("STUDENT_ID").COHORT
    g_in = (grades_ft.TRANSCRIPT_TERM == grades_ft.STUDENT_ID.map(cohort_of)).fillna(False).astype(bool)
    f_in = (fa_ft.SFRSTCR_TERM_CODE == fa_ft.STUDENT_ID.map(cohort_of)).fillna(False).astype(bool)
    grades_e, fa_e = grades_ft[g_in], fa_ft[f_in]
    grades_e_agg = (grades_e.assign(
        m_grade=grades_e.GRADE.isna().astype(int), m_dept=grades_e.DEPT_CODE.isna().astype(int),
        m_subjnum=grades_e.SUBJ_NUMBER.isna().astype(int))
        .groupby("STUDENT_ID")
        .agg(ge_rows=("GRADE", "size"), ge_missing_grade=("m_grade", "sum"),
             ge_missing_dept=("m_dept", "sum"), ge_missing_subjnum=("m_subjnum", "sum"))
        .reset_index())
    fa_e_agg = (fa_e.assign(pell_missing=fa_e.Pell.isna().astype(int))
        .groupby("STUDENT_ID")
        .agg(fe_rows=("STUDENT_ID", "size"), fe_pell_missing_rows=("pell_missing", "sum"))
        .reset_index())

    student_table = (roster
        .merge(grades_agg, on="STUDENT_ID", how="left", validate="one_to_one")
        .merge(fa_agg, on="STUDENT_ID", how="left", validate="one_to_one")
        .merge(grades_e_agg, on="STUDENT_ID", how="left", validate="one_to_one")
        .merge(fa_e_agg, on="STUDENT_ID", how="left", validate="one_to_one"))
    student_table["has_grades"] = student_table.gr_rows.notna()
    student_table["has_fa"] = student_table.fa_rows.notna()
    student_table["has_grades_entry"] = student_table.ge_rows.notna()
    student_table["has_fa_entry"] = student_table.fe_rows.notna()
    assert len(student_table) == len(roster) and student_table.STUDENT_ID.is_unique
    return locals()


def save_table(df, filename, index=True):
    if not SAVE_TABLES:
        return

    path = OUT_DIR / filename
    df.to_csv(path, index=index)
    print(f"Saved: {path.resolve()}")


def export_tables(tables, prefix):
    """Export result tables only when SAVE_TABLES is enabled."""
    if not SAVE_TABLES:
        return

    exported = 0

    for name, frame in tables.items():
        if isinstance(frame, pd.DataFrame):
            safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
            frame.to_csv(OUT_DIR / f"{prefix}_{safe}.csv", index=True)
            exported += 1

    print(f"Exported {exported} table(s) to {OUT_DIR.resolve()}")