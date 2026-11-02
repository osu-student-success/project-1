# Requirements


## 1. Problem Statement

Our institution loses students between terms. Advisors currently have no systematic way to know which students are most likely not to re-enroll, early enough in a term to contact them. This project builds a model that, at a fixed point in the term, estimates each student's probability of not re-enrolling in the next term, so advisors can prioritize outreach.

The model family for this phase is a Random Forest classifier.

Two properties make this problem easy to get wrong, and the requirements below are shaped around them:

- **The outcome is observed only once per term.** A model can look excellent on a label we construct ourselves (for example, from survey answers or grade thresholds) without telling us anything about real departures. The label must come from observed re-enrollment.
- **Source systems tend to overwrite history.** If we do not obtain dated student data captures, we cannot later reproduce what the model would have seen on a given date, and cannot evaluate without leakage.

## 2. Functional Requirements

Each requirement has an ID. Where behavior is not obvious, an acceptance criterion (AC) is given. Test paths are proposed. When a requirement is finished, replace its AC with the name of the CI test that proves it.

| ID | Requirement | Acceptance criterion / CI test |
| --- | --- | --- |
| FR-1 | Ingest source extracts into immutable, dated data captures, keyed by `(term, as_of_date)`. | Re-running ingestion for an existing key fails with an error and changes nothing. Each data capture stores a content hash. *Proposed test:* `tests/test_data_captures.py` |
| FR-2 | Pseudonymize student identifiers at ingestion. Raw identifiers never reach feature tables, model artifacts, logs, or outputs. | A test scans feature tables, model artifacts, and logs for any column or value from the identifier list and fails if found. *Proposed test:* `tests/test_no_raw_ids.py` |
| FR-3 | Build the label (`not_retained`) from observed re-enrollment at the next term enrollment date, following written label rules. | The label rules document lists each edge case (returned stop-outs, transfers, graduation, approved leave of absence, deceased/withdrawn-by-institution). Each has a fixture record with an expected label. *Proposed test:* `tests/test_label_rules.py` |
| FR-4 | Build features using only data present in the current data capture at or before the as-of date. | Every feature declares its source table and timestamp column. The build fails if any value's timestamp is later than the as-of date. *Proposed test:* `tests/test_leakage.py` |
| FR-5 | Train a Random Forest using a temporal split: train on earlier cohorts, test on a later cohort. | No student or term appears in both train and test. Fixed random seeds: identical inputs produce identical metrics. *Proposed test:* `tests/test_temporal_split.py` |
| FR-6 | Every evaluation report includes two baselines on the same test cohort: last year's retention rate by program, and a logistic regression on a small set of core features. | Report fails to generate if either baseline is missing. |
| FR-7 | Evaluation reports precision, recall, accuracy, and a F1-Score, each with bootstrap confidence intervals. | Metrics are computed on the held-out cohort only. |
| FR-8 | Convert probabilities into risk levels (High / Medium / Low) using thresholds that are chosen on validation data and recorded in config. | Thresholds are not hard-coded. The config records which data and commit they were chosen from. Level precision/recall is reported on the held-out cohort. Probabilities are labeled "uncalibrated" in outputs unless a calibration step has been validated. |
| FR-9 | Score a cohort at a given as-of date and write an output table. | Output has the columns in `design.md` 4.3. Every row carries a model version and data capture ID. |
| FR-10 | Provide a per-student explanation (top contributing factors) that respects the direction of each factor's effect. | A synthetic student whose only change is higher attendance must not receive a higher attendance contribution to risk. *Proposed test:* `tests/test_explanation_direction.py` |
| FR-11 | Produce a subgroup report: recall and false-negative rate by `[permitted groups]`. | Report is generated on every evaluation. The maximum acceptable gap is set in config, and the evaluation flags a breach. |
| FR-12 | Record every training and scoring run in a run registry: code commit, data capture IDs, config, hyperparameters, metrics. | A scoring run refuses to start without a registry record for the model it uses. |
| FR-13 | Keep an audit log of runs and of reads of student-level outputs: who, when, what. | `[Depends on hosting decision: see design.md 7]` |

## 3. Non-Functional Requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| NFR-1 | **Reproducibility.** Any past result can be rebuilt from its registry record. | Re-running a registered run from its data capture IDs and commit reproduces its metrics exactly. Checked each term. |
| NFR-2 | **Privacy.** Deidentified student data in the repository, CI logs, or issue tracker. | A pre-commit/CI check blocks files matching `[data file patterns]`. |
| NFR-3 | **Least-privilege access.** Student-level outputs are visible only to roles that need them. | `[Roles and mechanism TBD]` |
| NFR-4 | **Performance.** Scoring a full cohort completes within 30 minutes. | Timed in CI on a synthetic cohort of the target size. |
| NFR-5 | **Maintainability.** Lint, type checks, and tests run on every pull request. | CI is required to pass before merge. |
| NFR-6 | **Observability.** Failed, late, or empty runs are visible without reading logs. | A run that produces zero rows, or a schema mismatch, fails loudly. |
| NFR-7 | **Data retention.** Data captures and outputs have a deletion schedule. | `[Schedule from compliance]` a scheduled job enforces it. |
| NFR-8 | **Portability.** Runs on Python 3.15 with pinned dependencies. | Lockfile committed; CI installs from it. |

## 4. Constraints

These are limits imposed on us, not choices we made.

- **Student records law and policy** FERPA governs how data can be stored, accessed, and disclosed, including to third-party tools.
- **Outcomes arrive once per term.** Each new labeled cohort takes a full term or year to appear, so we cannot iterate on labels quickly.
- **Source systems may overwrite history.** Whether past states are recoverable is unconfirmed (see Open Questions). If not, the data capture history begins only on the first day.
- **Small samples are likely.** Per-program or per-term subsets may contain few students, which limits what subgroup and temporal evaluation can show.
- **Real student data cannot be shared with outside tools or put in the repository** (see NFR-2).
- **Team capacity:** team size of 4, 2-3 weekly hours per person, along with weekly deadlines for capstone class.
- **External prerequisites:** none required as of 2026-11-01 (see `risks.md` 4).

## 5. Success Metrics

Targets in brackets are to be agreed before the first evaluation run, so they cannot be tuned to the results.

| Metric | Target |
| --- | --- |
| F1-Score vs. best baseline on held-out cohort | Beats both baselines by at least .05, with confidence intervals that exclude zero difference |
| Reproducibility | 100% of registered runs reproduce exactly |
| Leakage tests | 0 failures in CI |
| Data capture coverage | A data capture exists for every scheduled as-of date in the term |

## 6. Non-Goals

- Real-time or event-driven scoring.
- Automatic or continuous retraining.
- Delivering or managing interventions, or claiming that predictions improve retention. That needs a separate controlled pilot.
- Model families other than Random Forest in this phase (the baselines in FR-6 are comparison points only).
- Any label built from survey answers, grade thresholds, or other rules applied to the model's own inputs.

## 7. Open Questions

| # | Question | Needed for | Status |
| --- | --- | --- | --- |
| 1 | What is the exact definition of "retained" (term-to-term, year-to-year, completion), and the rules for each edge case in FR-3? | FR-3 | Open |
| 2 | Which week of the term is the as-of date? Are several as-of dates needed? | FR-1, FR-4 | Open |
| 3 | Do source systems retain historical states, or overwrite them? | FR-1 | Open |
| 4 | How many students can advisors realistically contact per week (`k`)? | FR-7, success metrics | Open |
| 5 | Which subgroups may legally and ethically be used for auditing, and may any be model inputs? | FR-11 | Open |
| 6 | Where will the pipeline run and store data captures? | NFR-3, NFR-7, FR-13 | Open |
| 7 | What action will advisors take on a High-risk score? | Success of the project | Open |
