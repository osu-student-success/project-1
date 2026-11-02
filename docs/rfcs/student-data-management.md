
# RFC: The hosting and management of student data


| Field | Value |
| --- | --- |
| Author | Trey Trejo |
| Date | 2026-10-25 |
| Status | Proposed |
| Decision Date | 2026-11-7 |
| Deciders | Project 1 team members |
| Superseded By | N/A |

## Problem and Context
A main issue to solve is figuring out what type of backend architecture is best suited for our Machine Learning at-risk student prediction project. A few issues include deciding where student data will live, how features interact from it, and how predictions get outputted as. Student information systems usually overwrite records, such as a grade or enrollment status. If we do not capture the state of the data as of each cutoff date, we cannot later rebuild what the model would have seen, so we cannot train or evaluate without leakage. Every term we run without capturing these types of data is history we would permanently lack. Moving identifiable student records between environments means getting updated permissions to view and process data.
The papers I reviewed were not able to show how to resolve the issue of student data permissions. They do not say much about authentication or access control. The systematic review found only 20 of 100 studies addressed ethical issues, and 14 verified on a second dataset, so there is little published operational evidence to lean on. If we do nothing, we will probably end up with a decision to have no periodic data captures and no access controls.

### Papers Researched:
#### https://www.mdpi.com/2071-1050/15/19/14512 
#### https://link.gale.com/apps/doc/A900730484/AONE?u=s8405248&sid=bookmark-AONE&xid=3e056271
#### https://link.gale.com/apps/doc/A903350091/AONE?u=s8405248&sid=bookmark-AONE&xid=96233cc7


## Options

At least three options, **including "do nothing"**. Give each option a short name, an account of its real costs, and the condition under which it would be the right choice. An option with no such condition is a strawman, and a strawman weakens the whole document.
## Option A: Data capturing from inside an institution controlled environment
Data is copied on a schedule from the Student Information System into the school’s own infrastructure. At each configured cutoff, an immutable version of data capture is written. Features are built only from those captures. AI models are stored in a registry with the code version, data capture ID, and metrics. A scheduled job scores each cohort and writes results to a table.
#### Benefits: Full control over where captured data is held and internal access, giving us reproducible training. 
#### Costs: Since we would also own the operations of patching data and backups, it would have to be monitored. The setup would be slower than a hosted tool. 
This is the right choice when the data is identifiable, the institution restricts where records can go, and predictions are used for periodic outreach.
## Option B: Managed platform in a vendor or cloud environment
Student data is sent to a hosted platform that handles storage, training, and serving. 
#### Benefits: fastest to set up with built-in monitoring and scaling. 
#### Costs: since the data leaves the institution’s boundary, it would need a data processing agreement, a security review, and clear terms on what the vendor may use data for. 
This is the right choice if the institution already has an approved vendor and a signed agreement covering student education records.
## Option C: Lightweight static model app 
A saved model file is loaded by a small web app, and advisors upload CSVs to obtain prediction scores. 
#### Benefits: It is fast to build and easy to demonstrate. 
#### Costs: no previously captured history for the AI model to train off of, uploaded records have no defined storage or retention, authentication and audit logging would need to be added, and a model never retrained will become less accurate as cohorts change. 
This is the right choice for a demo on synthetic or public data.
## Option D: Do Nothing
Analysts keep exporting CSVs and manually running notebooks. The cost is low at first, the first time anyone wants to reproduce a past result the data has already changed, when predictions reach advisors there would be no access control or audit trail, and the compliance review would have no documented data flow. By then the missing data capture history cannot be recovered. This is acceptable only if we commit that no output reaches staff or students.

## Analysis
The data capture and hosting issues are not easily replaceable when compared to the model of ML used so spending more time on those two would save the project a lot of resources. From the research I have gathered, the compute time to train the ML model should not be a constraint for our team. Through the data of around 400 students, it took a GPU under 5 minutes to train. I also have personally fine-tuned models myself and can confirm that at worst, training a model on a very large dataset could be done overnight on a capable GPU. We do not know the institution’s IT capacity to host data, how long source systems keep history, how many students are in scope, or the timing that advisors need to see results.

## Recommendation and Verification Plan

Which option you propose and why it wins the analysis above. Then, concretely: how will the team know it worked? List the tests, metrics, or acceptance criteria that would detect failure, and when they will be checked.
### My Recommendation
I would like to propose Option A, with having periodic data captures started immediately before any model work, because lost history is the only part of this decision that cannot be brought back. Scoring would be a scheduled batch throughout the term, or after each term. Real-time scoring would be deferred until a batch shows value. Retraining would be manual or scheduled and reviewed, never automatic.
We will know it works through these checks:
Preventing any point in time leakage in CI by having an automated test fail the build if any feature is computed from a source later than its data capture’s cutoff.
Verifying with automated and manual tests, the modelers cannot see direct identifiers that advisors see for their assigned students, and that unauthorized users get denied. Checked before any staff access and at each role change. And having every read of student-level scores be logged with user and time. 
Restoring the data captures stored from backup and rolling the scoring job back to the previous model version. We would have this run before launch and once per term.
Running one term then comparing the predictions to observed outcomes which would be checked at the end of that term.

## Constraints
FERPA governs storage, access, and any disclosure to vendors. Our legal basis, data retention schedule, and student notice should be confirmed with Oregon State University before data capturing begins.
If any hosted service, library, or pretrained component is used, verify its license and confirm in writing that student data is not used for the vendor’s own training.
Student data captures hold sensitive history, so they need a defined deletion schedule that does not conflict with the need to reproduce past results.

## Delegation and Validation
### What was handed to AI tools 
The recommended decision of Option A was made in partnership with Claude AI’s assessment. 
### What checks made that reasonable 
CI tests and review gates are not yet implemented but planned to be at the end of this week.
### Where I stopped and validated myself
Because the perioidic data capture and hosting decisions are hard to reverse, I suggest personally verifying the source systems’ retention behavior, the data flow diagram against what IT will actually provide, and the access control rules with a real test account for each role.

## Decision

Proposed, until Project 1 team decides. Then accepted, rejected, or superseded by 2026-11-7.

