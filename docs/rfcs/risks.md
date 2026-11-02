# Risks

## How to read this file

- Each risk is written as a fact about the project as it stands today, not as a possibility. If the fact stops being true, move the row to the Closed section with the date and what changed.
- Rank is ordered by impact first, then likelihood. Ratings are High / Medium / Low.
- Trigger is the observable event that tells us the risk has materialized or is about to.
- Update this file at every checkpoint, even if the update is "no change."

## 1. Business Risks

| Rank | ID | Fact | Impact | Likelihood | Trigger | Response |
| --- | --- | --- | --- | --- | --- | --- |
| 3 | B-1 | No action has been defined for advisors to take on a High-risk score. A prediction without an agreed action cannot change retention. | High | High | Model reaches approval with no outreach plan | Get a named stakeholder to define the action and capacity (requirements open questions 5 and 8) before the first pilot |
| 6 | B-2 | The number of students advisors can contact per week (`k`) is unknown, so the main success metric (recall_k) has no value of `k`. | Medium | High | First evaluation is run without a fixed `k` | Fix `k` in config before any evaluation |
| 9 | B-3 | Nothing in the repo records who will use the scores, who is accountable for acting on them, or who may see student-level results. | Medium | Medium | A request for scores arrives from someone not on an access list | Define roles and access with the data manager (NFR-3) |
| 11 | B-4 | Retention gains cannot be attributed to the model without a comparison group; no pilot design exists. | Medium | Medium | A claim of "the model improved retention" is made | Keep causal claims out of reports; design a randomized pilot separately |

## 2. Technical Risks

| Rank | ID | Fact | Impact | Likelihood | Trigger | Response |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | T-1 | The label definition does not exist yet: "retained" and its edge cases (returned stop-outs, transfers, graduation, leave of absence) are unwritten. | High | High | First training run starts before `docs/label_rules.md` exists | Write and review label rules first (FR-3); no modeling until done |
| 2 | T-2 | It is unconfirmed whether source systems keep past record states. If they overwrite, every as-of date we do not snapshot is permanently lost. | High | Medium | Data manager confirms overwriting, or the first snapshot is missing a date | Start snapshot capture as soon as any real source is approved; confirm retention behavior in writing |
| 4 | T-3 | The data source for the model is not named in the repo. Whether it is institutional records, a public dataset, or synthetic data determines almost every other requirement. | High | High | First data pull is requested | Answer open question 3; record the answer here and in `requirements.md` |
| 5 | T-4 | Random Forest probabilities are uncalibrated by default, and risk-band thresholds (High/Medium/Low) are not yet chosen from data. Scores could be read as true probabilities. | Medium | High | Advisors or reports treat a score of 0.9 as "90% likely to leave" | Label scores as uncalibrated (FR-8); validate calibration before any probability is shown |
| 7 | T-5 | No leakage test exists yet. Without one, a feature built from data dated after the as-of date (for example, final grades posted after the cutoff) would inflate metrics undetected. | High | Medium | Metrics look unusually strong on first run | Implement `tests/test_leakage.py` before the first model run |
| 8 | T-6 | The size of the data is unknown. If few past cohorts or small programs exist, temporal evaluation and subgroup reports will have wide confidence intervals and may not support any conclusion. | Medium | Medium | Bootstrap intervals on the first evaluation overlap the baseline | Report intervals; state plainly when results are inconclusive; do not tune on the test cohort |
| 10 | T-7 | The explanation method is not chosen. A simple "global importance × encoded value" approach can mislabel protective factors as risk drivers. | Medium | Medium | A reviewer sees a high-attendance student with attendance listed as a risk factor | Implement and test direction-aware explanations (FR-10) before showing factors to staff |
| 12 | T-8 | No fairness or subgroup audit exists. Which groups may be audited, and whether any attributes may be inputs, is unresolved (requirements open question 6). | High | Medium | Subgroup recall gap is found after deployment instead of before | Resolve with compliance; generate subgroup report on every evaluation (FR-11) |
| 13 | T-9 | Hosting and access control are undecided. Without them, FR-13 (audit log) and NFR-3 (access control) have no mechanism. | Medium | Medium | Real data is requested before an environment exists | Make the hosting decision before first real ingestion |
| 14 | T-10 | Once outcomes are observed, feature distributions may drift between cohorts (policy, calendar, or population changes). No drift monitoring is planned yet. | Medium | Low | Performance on a new cohort falls well below the previous one | Add drift checks after the first two terms |

## 3. Team Risks

| Rank | ID | Fact | Impact | Likelihood | Trigger | Response |
| --- | --- | --- | --- | --- | --- | --- |
| 15 | M-1 | The repo does not record who owns each requirement, so work could be duplicated or dropped. | Medium | High | Two people work on the same component, or a requirement has no activity | Assign an owner to each FR/NFR in `requirements.md` |
| 16 | M-2 | Team size, weekly availability, and deadlines are not recorded in the repo. Plans cannot be checked against capacity. | Medium | Medium | A deadline is set without a capacity check | Fill in the Constraints section of `requirements.md` |
| 17 | M-3 | Domain knowledge of the student data (what each source field means, when it is populated) sits with people outside the repo, such as the data manager or registrar staff. | Medium | Medium | Feature definitions are written without confirming source semantics | Record a named contact for each source and review feature definitions with them |
| 18 | M-4 | These three documents were drafted with AI assistance and have not been validated by the team. Placeholders and assumptions may be wrong for this institution. | Medium | High | A decision is made on the strength of this draft alone | Review each document as a team and replace every bracketed placeholder or mark it as intentionally open |
| 19 | M-5 | If one person holds knowledge of the pseudonymization keys, snapshot procedures, or model approvals, their absence would stop the pipeline. No second person is named. | Medium | Low | A key person becomes unavailable | Name a backup for each of these and document the procedure |

## 4. External Prerequisites

As of 2026-11-01 the team reports no external prerequisites for this project.

| Prerequisite (approval, account, review, recruitment) | Requested by | Date requested | Needed by | Status | Last checked | Blocks |
| --- | --- | --- | --- | --- | --- | --- |
| *None at this time* | | | | | 2026-11-01 | |

### Things that would turn into prerequisites

These are not current prerequisites. They are conditions under which one would appear, so the team can notice early:

- Choosing a hosted service or third-party tool that will touch student data would require a security review and agreement covering that data.
- Advisor involvement in a pilot would require recruitment, time commitments, and agreement on the intervention.
- Adopting a new library or data source with its own license requires a license check.

## 5. Checkpoint Log

| Date | Changes | Updated by |
| --- | --- | --- |
| 2026-11-01 | Initial draft. | `Trey` |

## 6. Closed Risks

| ID | Closed on | What changed |
| --- | --- | --- |
| *(none yet)* | | |
