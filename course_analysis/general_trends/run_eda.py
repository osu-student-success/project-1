"""Run data loading, schema/profile checks, and grain/duplicate diagnostics."""
# Note will not run without 'data_private' folder containing the data Excel files

from common import *

ctx = build_base()
pm, grades, fa, conv = ctx["pm"], ctx["grades"], ctx["fa"], ctx["conv"]
tables = {}

profile = pd.DataFrame([
    dict(dataset=k, rows=len(d), unique_students=d.STUDENT_ID.nunique(),
         blank_id_rows=int(d.STUDENT_ID.isna().sum()), workbooks=d.SOURCE_FILE.nunique(),
         sheets=d[["SOURCE_FILE", "SHEET"]].drop_duplicates().shape[0])
    for k, d in {"pm": pm, "grades": grades, "fa": fa}.items()])
tables["profile"] = profile
print("\nDATA PROFILE")
print(profile.to_string(index=False))
print("\nConversion issues")
issues = conv[(conv.blank_cells > 0) | (conv.text_tokens_to_missing > 0) | (conv.unparseable_to_missing > 0)]
print(issues.to_string(index=False) if len(issues) else "No conversion issues found.")

entry_preview = pm[pm.PAST_TERM == pm.FIRST_TERM_OF_ATTENDANCE]
for col in ["STU_TYPE_CODE_DESC", "ENROLLMENT_STATUS", "ADMIT_TYPE_CODE_DESC"]:
    print(f"\nEntry-term rows by {col}:")
    print(entry_preview[col].value_counts(dropna=False).to_string())
print("\nTerm-code suffix profile")
print((pm.PAST_TERM % 100).value_counts(dropna=False).sort_index().to_string())
print("Term codes not matching", TERM_PATTERN, ":",
      int((~pm.PAST_TERM.astype("string").str.match(TERM_PATTERN).fillna(True)).sum()))

def grain_report(df, name, keys_list):
    base = df.drop(columns=["SOURCE_FILE", "SHEET"])
    rows = []
    for keys in keys_list:
        g = df.groupby(keys, dropna=False).size()
        rows.append(dict(dataset=name, key=" + ".join(keys), rows=len(df),
                         distinct_keys=len(g), rows_beyond_first=int((g - 1).sum()),
                         max_rows_per_key=int(g.max())))
    out = pd.DataFrame(rows)
    out["exact_duplicate_rows_ignoring_sheet"] = int(base.duplicated().sum())
    return out

grain = pd.concat([
    grain_report(pm, "pm", [["STUDENT_ID"], ["STUDENT_ID", "PAST_TERM"]]),
    grain_report(grades, "grades", [["STUDENT_ID"], ["STUDENT_ID", "PAST_TERM"],
        ["STUDENT_ID", "TRANSCRIPT_TERM", "SUBJ_CODE", "SUBJ_NUMBER"]]),
    grain_report(fa, "fa", [["STUDENT_ID"], ["STUDENT_ID", "SFRSTCR_TERM_CODE"],
        ["STUDENT_ID", "SFRSTCR_TERM_CODE", "STUDENT_LEVL"]])
], ignore_index=True)
tables["grain"] = grain
print("\nGRAIN / DUPLICATE REPORT")
print(grain.to_string(index=False))
export_tables(tables, "01_profile_grain")


"""Build the FTFT roster and report cohort coverage across PM, grades, and FA."""

ctx = build_base()
pm, grades, fa = ctx["pm"], ctx["grades"], ctx["fa"]
roster, waterfall, student_status = ctx["roster"], ctx["waterfall"], ctx["student_status"]
cohort_counts = ctx["cohort_counts"]

print("\nEXCLUSION WATERFALL")
print(waterfall.to_string(index=False))
print(f"\nFTFT roster: {len(roster):,} students across {roster.COHORT.nunique()} cohorts")
print("\nCOHORT COUNTS AND FILE COVERAGE")
print(cohort_counts.to_string())

def sheet_vs_cohort(df):
    m = df[["STUDENT_ID", "SOURCE_FILE", "SHEET"]].dropna(subset=["STUDENT_ID"]).drop_duplicates()
    multi = int((m.groupby("STUDENT_ID").size() > 1).sum())
    m = m.merge(roster[["STUDENT_ID", "COHORT"]], on="STUDENT_ID", how="left", validate="many_to_one")
    return pd.crosstab([m.SOURCE_FILE, m.SHEET], m.COHORT.astype("string").fillna("not in roster")), multi

for name, df in {"pm":pm, "grades":grades, "fa":fa}.items():
    ct, multi = sheet_vs_cohort(df)
    tables[f"sheet_vs_cohort_{name}"] = ct
    print(f"\n{name.upper()} sheet vs cohort (students appearing in multiple sheets: {multi})")
    print(ct.to_string())

fig, ax = plt.subplots(figsize=(9, 4.5))
cohort_counts.drop(index="TOTAL")[["pm_ftft","in_grades","in_fa","in_all_three"]].plot(
    kind="bar", ax=ax, width=0.8)
ax.set_xlabel("Entering cohort")
ax.set_ylabel("Unique FTFT students")
ax.set_title("FTFT roster size and coverage in grades and FA")
plt.xticks(rotation=0); plt.tight_layout()
fig.savefig(FIG_DIR / "cohort_counts.png", dpi=150); plt.close(fig)

# Population accounting: show the starting PM population split into the
# final roster and students excluded. Duplicate rows are reported separately
# because they are records, not additional unique students.
initial_population = int(waterfall["after"].dropna().iloc[0])
final_population = int(len(roster))
excluded_students = initial_population - final_population
excluded_pct = (100 * excluded_students / initial_population) if initial_population else 0

# The duplicate-entry-term note is informational and should not be added to
# the number of excluded students.
duplicate_rows_dropped = 0
duplicate_notes = waterfall[waterfall["rule"].astype(str).str.contains(
    "duplicate entry-term rows dropped", case=False, na=False
)]
if not duplicate_notes.empty:
    import re
    match = re.search(r"(\d[\d,]*)\s+duplicate entry-term rows dropped",
                      str(duplicate_notes.iloc[0]["rule"]), flags=re.IGNORECASE)
    if match:
        duplicate_rows_dropped = int(match.group(1).replace(",", ""))

fig, ax = plt.subplots(figsize=(10, 3.8))
ax.barh(["PM population"], [final_population], color="tab:green",
        label=f"Retained in FTFT roster ({final_population:,})")
ax.barh(["PM population"], [excluded_students], left=[final_population],
        color="tab:red", label=f"Excluded ({excluded_students:,})")
ax.set_xlim(0, max(initial_population * 1.08, 1))
ax.set_xlabel("Unique students")
ax.set_title("PM population: initial students, exclusions, and final roster")
ax.text(final_population / 2, 0, f"{final_population:,}\nRetained",
        ha="center", va="center", color="white", fontweight="bold")
if excluded_students > 0:
    ax.text(final_population + excluded_students / 2, 0,
            f"{excluded_students:,}\nExcluded",
            ha="center", va="center", color="white", fontweight="bold")
ax.text(0.99, 0.88,
        f"Initial unique students: {initial_population:,}\n"
        f"Excluded: {excluded_pct:.1f}%\n"
        f"Final FTFT roster: {final_population:,}\n"
        f"Duplicate entry-term rows dropped: {duplicate_rows_dropped:,} (rows; not students)",
        transform=ax.transAxes, ha="right", va="top", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.45", facecolor="white", alpha=0.9))
ax.set_yticks([])
ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.48), ncol=2, frameon=False)
fig.tight_layout()
fig.savefig(FIG_DIR / "exclusion_waterfall.png", dpi=150, bbox_inches="tight")
plt.close(fig)
export_tables(tables, "02_roster_coverage")


"""Quantify join inflation and create one-row-per-student aggregate checks."""

ctx = build_base()
roster, pm_ft, grades_ft, fa_ft = ctx["roster"], ctx["pm_ft"], ctx["grades_ft"], ctx["fa_ft"]
grades_agg, fa_agg = ctx["grades_agg"], ctx["fa_agg"]
tables = {}

def join_inflation_report(left, right, on, how="left", label=""):
    L = left.groupby(on, dropna=False).size().rename("l")
    R = right.groupby(on, dropna=False).size().rename("r")
    both = L.to_frame().join(R, how="left")
    r = both.r.fillna(0)
    predicted = (both.l * (r.clip(lower=1) if how == "left" else r)).sum()
    return dict(join=label, keys=" + ".join(on), how=how, left_rows=len(left), right_rows=len(right),
        max_right_rows_per_key=int(R.max()), predicted_rows=int(predicted),
        inflation_factor=round(predicted / len(left), 2) if len(left) else np.nan)

reports = [
    join_inflation_report(pm_ft, grades_ft, ["STUDENT_ID"], label="PM x grades, naive student join"),
    join_inflation_report(pm_ft, grades_ft, ["STUDENT_ID","PAST_TERM"], label="PM x grades on student + PAST_TERM"),
    join_inflation_report(pm_ft, fa_ft, ["STUDENT_ID"], label="PM x FA, naive student join"),
    join_inflation_report(roster, grades_ft, ["STUDENT_ID"], label="Roster x grades, naive"),
    join_inflation_report(roster, fa_ft, ["STUDENT_ID"], label="Roster x FA, naive"),
    join_inflation_report(roster, grades_agg, ["STUDENT_ID"], label="Roster x grades aggregate"),
    join_inflation_report(roster, fa_agg, ["STUDENT_ID"], label="Roster x FA aggregate"),
]
join_report = pd.DataFrame(reports)
tables["join_inflation_report"] = join_report
print(join_report.to_string(index=False))
student_table = ctx["student_table"]
assert len(student_table) == len(roster) and student_table.STUDENT_ID.is_unique
print(f"\nOK: student-level aggregate table has {len(student_table):,} unique roster rows.")
export_tables(tables, "03_join_audit")


"""Audit missing values overall, by cohort, and by source population."""
ctx = build_base()
globals().update(ctx)
tables = {}

cohort_map = roster.set_index("STUDENT_ID").COHORT


def missing_overall(df, name, label):
    cols = SCHEMA[name]["str_cols"] + SCHEMA[name]["int_cols"] + SCHEMA[name]["float_cols"]
    n = len(df)
    out = pd.DataFrame({"n_rows": n, "n_missing": df[cols].isna().sum(), })
    out["pct_missing"] = (100 * out.n_missing / n).round(2)
    conv_cols = ["blank_cells", "text_tokens_to_missing", "unparseable_to_missing"]
    if label == "all rows as loaded":                 # conversion counts are file-wide, so only attach them here
        out = out.join(conv[conv.dataset == name].set_index("column")[conv_cols])
    else:
        for c in conv_cols:
            out[c] = np.nan
    out.insert(0, "population", label)
    return out


def missing_by_cohort(df, name, only_roster):
    cols = SCHEMA[name]["str_cols"] + SCHEMA[name]["int_cols"] + SCHEMA[name]["float_cols"]
    coh = df.STUDENT_ID.map(cohort_map).astype("string")
    if not only_roster:
        coh = coh.fillna("NOT IN ROSTER")
    miss = df[cols].isna()
    keep = coh.notna()
    pct = (miss[keep].groupby(coh[keep]).mean() * 100).T.round(2)
    cnt = miss[keep].groupby(coh[keep]).sum().T
    pct["ALL"] = (100 * miss[keep].mean()).round(2)
    cnt["ALL"] = miss[keep].sum()
    return pct, cnt


def heatmap(tbl, title, fname, color_cap=30.0):
    """Cell text shows the true %; the color scale is capped so near-100% structural blanks
    (e.g. DEGREE_AWARDED_STATUS) do not hide differences in the other columns."""
    vals = tbl.values.astype(float)
    fig, ax = plt.subplots(figsize=(1.0 * tbl.shape[1] + 4, 0.38 * tbl.shape[0] + 2))
    vmax = min(color_cap, max(1.0, np.nanmax(vals)))
    im = ax.imshow(vals, aspect="auto", vmin=0, vmax=vmax)
    ax.set_xticks(range(tbl.shape[1]), labels=[str(c) for c in tbl.columns], rotation=45, ha="right")
    ax.set_yticks(range(tbl.shape[0]), labels=list(tbl.index))
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            ax.text(j, i, f"{vals[i, j]:.1f}", ha="center", va="center", fontsize=8,
                    color="white" if vals[i, j] < vmax * 0.6 else "black")
    fig.colorbar(im, ax=ax, label=f"% of rows missing (color capped at {vmax:.0f}%)")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(FIG_DIR / fname, dpi=150)
    plt.show()


subsets = {"pm": (pm, pm_ft), "grades": (grades, grades_ft), "fa": (fa, fa_ft)}
for name, (all_df, ft_df) in subsets.items():
    both = pd.concat([missing_overall(all_df, name, "all rows as loaded"),
                      missing_overall(ft_df, name, "FTFT roster rows only")])
    tables[f"missing_overall_{name}"] = both
    print(f"\n=== {name.upper()}: missing counts and percentages, overall ===")
    display(both)
    pct, cnt = missing_by_cohort(ft_df, name, only_roster=True)
    tables[f"missing_by_cohort_pct_{name}"] = pct
    tables[f"count_miss_n_by_cohort_{name}"] = cnt
    print(f"\n=== {name.upper()}: % of FTFT-roster rows missing, by cohort ===")
    display(pct)
    heatmap(pct, f"{name.upper()}: % missing by cohort (FTFT roster rows)", f"missing_by_cohort_{name}.png")


def missing_patterns(df, cols, top=8):
    vc = df[cols].isna().value_counts().head(top)
    return pd.DataFrame([dict(columns_missing_together=", ".join(c for c, f in zip(cols, idx) if f) or "(complete row)",
                              rows=int(n), pct_of_rows=round(100 * n / len(df), 2)) for idx, n in vc.items()])


print("\nMost common missingness patterns, grades (FTFT rows):")
display(missing_patterns(grades_ft, ["DEPT_CODE", "SUBJ_CODE", "SUBJ_NUMBER", "GRADE"]))
print("Most common missingness patterns, FA (FTFT rows):")
display(missing_patterns(fa_ft, ["Pell", "FA_NEED_RANGE", "UNMET_NEED_ROUNDED_1000"]))

# Possible placeholder zeros in GPA columns (zero can be legitimate for TERM_GPA; review, do not auto-clean)
zeros = pd.DataFrame({c: [int((pm_ft[c] == 0).sum()), round(100 * float((pm_ft[c] == 0).mean()), 2)]
                      for c in ["HIGH_SCHOOL_GPA", "TERM_GPA", "TERM_QUALITY_POINTS"]},
                     index=["rows_equal_to_0", "pct_of_rows"]).T
tables["possible_placeholder_zeros"] = zeros
print("\nExact zeros in numeric columns (PM, FTFT rows):")
display(zeros)

export_tables(tables, "04_missingness")


"""Analyze retention/stop-out outcomes and compare missingness/value patterns."""
ctx = build_base()
globals().update(ctx)
tables = {}

max_obs = int(pm.PAST_TERM.max())
st = student_table.copy()
st["target_term"] = st.COHORT + RETENTION_OFFSET
st["outcome_observable"] = (st.target_term <= max_obs).fillna(False).astype(bool)

right = (pm_ft[["STUDENT_ID", "PAST_TERM", "ENROLLMENT_STATUS"]]
         .rename(columns={"PAST_TERM": "target_term", "ENROLLMENT_STATUS": "target_enroll_status"})
         .assign(_present=True)
         .drop_duplicates(["STUDENT_ID", "target_term"]))
st = st.merge(right, on=["STUDENT_ID", "target_term"], how="left", validate="one_to_one")
present = st._present.fillna(False).astype(bool)
if ENROLLED_VALUES_AT_TARGET is not None:
    present = present & st.target_enroll_status.isin(ENROLLED_VALUES_AT_TARGET)
deg = pm_ft.assign(_d=pm_ft.DEGREE_AWARDED_STATUS.notna()).groupby("STUDENT_ID")._d.max()
st["degree_any"] = st.STUDENT_ID.map(deg).fillna(False).astype(bool)

obs = st.outcome_observable.to_numpy()
ret = present.to_numpy()
dg = st.degree_any.to_numpy()
st["outcome"] = np.select([~obs, obs & ret, obs & ~ret & ~dg, obs & ~ret & dg],
                          ["Not yet observable", "Retained", "Stop-out", "Not retained, degree recorded"],
                          default="?")
assert len(st) == len(roster) and st.STUDENT_ID.is_unique

outcome_counts = pd.crosstab(st.COHORT, st.outcome)
decided = outcome_counts.reindex(columns=["Retained", "Stop-out"], fill_value=0)
outcome_counts["retention_rate_pct"] = (100 * decided["Retained"] / decided.sum(axis=1).replace(0, np.nan)).round(1)
tables["count_outcomes_by_cohort"] = outcome_counts
print(f"Latest term present in PM file: {max_obs}")
display(outcome_counts)

ax = outcome_counts.drop(columns="retention_rate_pct").plot(kind="bar", stacked=True, figsize=(9, 4.5))
ax.set_xlabel("Entering cohort")
ax.set_ylabel("FTFT students")
ax.set_title("Outcome by cohort (under the configured retention definition)")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(FIG_DIR / "outcomes_by_cohort.png", dpi=150)
plt.show()

# --- Leakage check: do MIN/MAX_PAST_TERM encode the outcome? ---
chk = st[st.outcome.isin(["Retained", "Stop-out"])].copy()
chk["MAX_PAST_TERM >= target_term"] = chk.MAX_PAST_TERM >= chk.target_term
leak = pd.crosstab(chk.outcome, chk["MAX_PAST_TERM >= target_term"], normalize="index").round(3)
tables["leak_check_max_past_term"] = leak
print("\nShare of students with MAX_PAST_TERM >= the retention target term, by outcome:")
display(leak)
if True in leak.columns and "Retained" in leak.index and "Stop-out" in leak.index:
    if leak.loc["Retained", True] > 0.9 and leak.loc["Stop-out", True] < 0.1:
        print("WARNING: MAX_PAST_TERM separates retained from stop-out almost perfectly. It describes the student's "
              "last observed term, so it encodes the outcome. Do NOT use it (or MIN/MAX_PAST_TERM) as a model input.")

# --- Missingness differences: retained vs stop-out (entry-term row + coverage in other files) ---
SKIP = ["STUDENT_ID", "COHORT", "PAST_TERM", "FIRST_TERM_OF_ATTENDANCE", "MIN_PAST_TERM", "MAX_PAST_TERM",
        "DEGREE_AWARDED_STATUS"]
pm_cols = [c for c in SCHEMA["pm"]["str_cols"] + SCHEMA["pm"]["int_cols"] + SCHEMA["pm"]["float_cols"] if c not in SKIP]
ind = st[pm_cols].isna().astype(float)
ind["NO_GRADE_ROWS_IN_ENTRY_TERM"] = (~st.has_grades_entry).astype(float)
ind["NO_FA_ROWS_IN_ENTRY_TERM"] = (~st.has_fa_entry).astype(float)
for lbl, col, flag in [("GRADES (entry term): any row missing GRADE", "ge_missing_grade", "has_grades_entry"),
                       ("GRADES (entry term): any row missing DEPT_CODE", "ge_missing_dept", "has_grades_entry"),
                       ("GRADES (entry term): any row missing SUBJ_NUMBER", "ge_missing_subjnum", "has_grades_entry"),
                       ("FA (entry term): any row missing Pell", "fe_pell_missing_rows", "has_fa_entry")]:
    ind[lbl] = np.where(st[flag], (st[col].fillna(0) > 0).astype(float), np.nan)   # NaN = not applicable


def bh(p):
    p = np.asarray(p, float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(q, 1)
    return out


def compare_missing(ind, grp, a="Retained", b="Stop-out"):
    rows = []
    for c in ind.columns:
        x = ind[c]
        xa = x[x.notna() & (grp == a)].astype(bool)
        xb = x[x.notna() & (grp == b)].astype(bool)
        if len(xa) == 0 or len(xb) == 0:
            continue
        _, p = stats.fisher_exact([[xa.sum(), len(xa) - xa.sum()], [xb.sum(), len(xb) - xb.sum()]])
        rows.append(dict(indicator=c, n_retained=len(xa), n_stopout=len(xb),
                         pct_missing_retained=round(100 * xa.mean(), 2), pct_missing_stopout=round(100 * xb.mean(), 2),
                         diff_pp=round(100 * (xb.mean() - xa.mean()), 2), p_value=p))
    out = pd.DataFrame(rows)
    if len(out):
        out["q_value_BH"] = bh(out.p_value)
    return out


cmp_ = compare_missing(ind, st.outcome)
cmp_ = cmp_.reindex(cmp_.diff_pp.abs().sort_values(ascending=False).index)
tables["missing_retained_vs_stopout"] = cmp_
print("\nMissingness, stop-out minus retained (percentage points). q_value_BH controls the false-discovery rate "
      "across all indicators; small samples will give large p-values even for big differences:")
display(cmp_)

plot = cmp_[cmp_.diff_pp.abs() > 0].head(15)
if len(plot):
    fig, ax = plt.subplots(figsize=(9, 0.4 * len(plot) + 1.8))
    colors = ["tab:red" if q < 0.05 else "lightgray" for q in plot.q_value_BH]
    ax.barh(plot.indicator[::-1], plot.diff_pp[::-1], color=colors[::-1])
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Stop-out minus retained, % points missing  (red = q < 0.05)")
    ax.set_title("Missingness: stop-out vs retained")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "missingness_by_outcome.png", dpi=150)
    plt.show()

# Same comparison within each observable cohort (guards against a cohort mix driving the pooled result)
by_cohort = {}
for c, sub in st[st.outcome.isin(["Retained", "Stop-out"])].groupby("COHORT"):
    r = compare_missing(ind.loc[sub.index], sub.outcome)
    if len(r):
        by_cohort[c] = r.set_index("indicator").diff_pp
diff_by_cohort = pd.DataFrame(by_cohort)
tables["missing_diff_pp_by_cohort"] = diff_by_cohort
print("\nStop-out minus retained, % points missing, within each cohort (consistent sign = more convincing):")
display(diff_by_cohort.loc[cmp_.indicator.head(10).tolist()].round(1) if len(cmp_) else diff_by_cohort)

# --- Observed values: do the groups differ in what IS recorded? ---
NUMERIC_COMPARE = ["HIGH_SCHOOL_GPA", "TERM_GPA", "CLASS_STANDING"]     # TERM_GPA here is the entry-term GPA
CATEGORICAL_COMPARE = ["STU_TYPE_CODE_DESC", "ADMIT_TYPE_CODE_DESC", "PRIMARY_CAMPUS_CODE", "ACAD_STAND_CODE_DESC"]
two = st[st.outcome.isin(["Retained", "Stop-out"])]
rows = []
for c in NUMERIC_COMPARE:
    a = two.loc[two.outcome == "Retained", c].astype(float).dropna()
    b = two.loc[two.outcome == "Stop-out", c].astype(float).dropna()
    if len(a) and len(b):
        u, p = stats.mannwhitneyu(a, b)
        rows.append(dict(column=c, median_retained=a.median(), median_stopout=b.median(), n_retained=len(a),
                         n_stopout=len(b), rank_biserial=round(2 * u / (len(a) * len(b)) - 1, 3), p_value=p))
numeric_cmp = pd.DataFrame(rows)
tables["numeric_retained_vs_stopout"] = numeric_cmp
print("\nNumeric columns (rank-biserial: + means retained tend to be higher). TERM_GPA is the FIRST-term GPA, "
      "known only at the end of the term, so it is not available for early prediction:")
display(numeric_cmp)

for c in CATEGORICAL_COMPARE:
    ct = pd.crosstab(two[c].fillna("(missing)"), two.outcome)
    if ct.shape[0] > 1 and ct.shape[1] == 2:
        _, p, _, _ = stats.chi2_contingency(ct)
        share = (100 * ct / ct.sum()).round(1)
        share["p_value (whole column)"] = round(p, 4)
        tables[f"categorical_{c}"] = share
        print(f"\n{c}: column % within each outcome group")
        display(share)

export_tables(tables, "05_retention")
