<!-- docs/rfcs/2026-11-22-model-inference-delivery-architecture.md -->

# RFC: Model Inference Delivery Architecture for Student Success Prediction

| Field | Value |
| --- | --- |
| Author | Kellen Swanson |
| Date | 2026-11-22 |
| Status | Undecided |
| Decision Date | N/A |
| Deciders | Project Team / Project Partner |
| Superseded By | N/A |

# RFC: Model Inference Delivery Architecture for Student Success Prediction

**Author:** Kellen Swanson  
**Date:** 11/22/26  
**Status:** Under Review  
**Decision Date:** N/A  
**Deciders:** Project Team and Partner  
**Superseded By:** N/A  

---

## Problem and Context

Our project builds a predictive model using historical academic and institutional data to estimate student success across multiple factors, serving the institutional partner, advisors, and downstream reporting or dashboard consumers. Because the project operates under a non-disclosure agreement (NDA) and handles sensitive student records, specific feature variables, institutional identifiers, and proprietary partner details are intentionally omitted from public or external descriptions. Within this system, the current decision governs the inference delivery layer—specifically how trained model outputs are computed, stored, and exposed to downstream views and reports—while model selection remains between a Random Forest model and an XGBoost model.

The team must decide whether inference will run dynamically through a live microservice endpoint, execute as scheduled batch jobs writing predictions into relational database columns, or rely on manual local script execution. Resolving this architectural question now is essential because the delivery mechanism constrains acceptable model serialization formats (such as `joblib`, `.pkl`, or XGBoost's `.json` and `ubj` formats) and shapes the end-to-end data-to-output pipeline, database schema, and frontend or reporting contract. Downstream frontend views and scheduled report deliverables depend on a stable prediction schema and predictable data availability intervals; locking in the delivery contract early prevents costly rework across database tables, query interfaces, and client code once downstream consumers begin integrating against output fields.

If the team does nothing at this stage, implementation risks diverging into ad-hoc local execution or premature API scaffolding before schema shapes, write semantics, and data freshness expectations are settled. Delaying the decision increases the likelihood of late-stage database schema migrations, mismatched frontend or reporting expectations, unversioned or drifting model artifacts, and potential compliance or handling missteps around sensitive student records.

---

## Options

### Option A: Real-Time Inference Microservice (FastAPI + Docker)
Option A serves predictions on demand via a live HTTP service (such as FastAPI packaged inside a Docker container) that receives incoming feature payloads, validates and deserializes inputs, executes model inference in memory, and returns predictions synchronously to callers or frontend services.

* **Benefits:** Provides low-latency, synchronous scoring for single-record or interactive on-demand queries, and encapsulates runtime dependencies inside a versioned container image.
* **Costs:** Introduces container build and deployment overhead, web routing, request/response schema validation (such as Pydantic models), service health monitoring, authentication and access controls, and continuous compute costs to keep the endpoint running, plus ongoing coordination across API contracts and client handlers whenever upstream features evolve.
* **When it would be the right choice:** When product requirements shift from scheduled report-driven views to interactive, real-time, single-record user workflows with strict low-latency response SLAs and approved network and hosting controls.

### Option B: Scheduled Batch Inference Writing to Primary Database
Option B runs scheduled background jobs (via automated Python scripts or a task runner) that load eligible target feature records, compute batch predictions from serialized model artifacts, and write results into dedicated, pre-indexed columns in the primary database so downstream views and reports can query pre-computed fields directly.

* **Benefits:** Eliminates live model invocation latency on user read paths, avoids web server routing and container orchestration overhead, keeps data processing within internal database and compute boundaries, and consumes minimal compute outside scheduled execution windows.
* **Costs:** Introduces staleness or freshness windows between scheduled batch runs and requires reliable scheduling, structured error handling, idempotent write logic, and careful database indexing and migration management.
* **When it would be the right choice:** When deliverables are report- or dashboard-driven, batch update intervals align with stakeholder freshness needs, and keeping sensitive student data execution inside controlled internal environments is prioritized over synchronous per-request inference.

### Option C: Do Nothing (Manual Local Script Execution)
Option C keeps current practices as-is—relying on developers or analysts to run local Python scripts manually or invoke ad-hoc inline routines whenever prediction outputs are needed.

* **Benefits:** Zero upfront engineering time or infrastructure setup cost during early experimentation.
* **Costs:** Unpredictable latency and availability, high likelihood of duplicated scoring logic, unversioned local model files, inconsistent local dependency environments, lack of execution audit trails, and severe operational and compliance risks when handling sensitive student records on local machines.
* **When it would be the right choice:** Only during brief, isolated, local exploratory prototyping or one-off offline analysis where outputs are not relied upon by production views, reports, or shared workflows.

---

## Analysis

* **Performance:** Option A is designed for low-latency synchronous responses on individual requests, whereas Option B shifts inference work into scheduled background runs so downstream queries read pre-computed database columns with minimal read overhead (Joblib Developers, n.d.; Scikit-learn Developers, n.d.). Option C has unpredictable turnaround because execution depends on manual intervention. Because our project's outputs center on reporting and dashboard views rather than interactive per-click scoring, writing predictions into indexed database columns supports fast reads while keeping batch execution bounded. Uncertainty remains around exact execution time scaling as dataset volume increases, so runtime must be measured against representative test records rather than assumed.
* **Complexity:** Option A adds Docker image management, HTTP routing, request payload validation, health checks, and synchronization between API schemas and downstream callers. Adding an event-driven queue such as Celery or Redis would similarly introduce message broker and worker management that is unnecessary when predictions are produced on a scheduled reporting cadence. Option B keeps the architecture straightforward by connecting scheduled Python execution directly to database tables, while still requiring dependable job triggers, logging, and schema alignment. Option C appears lightweight initially but accumulates brittle scripts, manual steps, and environment drift as the project grows.
* **Maintainability:** Under Option A, changes to model inputs or outputs require coordinated updates across preprocessing code, API validation schemas, and frontend or client request handling. Under Option B, batch scripts interact directly with database models and versioned artifacts, though database schema changes must stay coordinated with downstream views and queries (SQLAlchemy documentation / project schema conventions). Option C harms maintainability over time because ad-hoc scripts and local model files are harder to version, reproduce, and audit. In addition, `joblib` and `pickle`-based artifacts depend on compatible Python and library versions across environments, whereas XGBoost's native `.json` and `ubj` formats provide structured model serialization designed for XGBoost workflows (Scikit-learn Developers, n.d.; XGBoost Developers, n.d.).
* **Security:** Exposing a live HTTP inference endpoint under Option A expands the network attack surface and requires strict authentication, authorization, encrypted transport, and input validation to safeguard sensitive student records. Running ad-hoc scripts on local developer machines under Option C creates elevated exposure risks, potential credential sprawl, and weak auditability under FERPA and NDA obligations (U.S. Department of Education, n.d.). Option B keeps inference execution inside a controlled internal database and computes boundaries without exposing external scoring endpoints. Moreover, because `joblib` and `pickle` deserialization can execute arbitrary code if untrusted files are loaded, model artifacts must only be loaded from trusted, access-controlled storage (Joblib Developers, n.d.; Scikit-learn Developers, n.d.).
* **Cost:** Option A incurs ongoing compute and operational maintenance costs for an always-on service regardless of query traffic. Option B incurs compute primarily during scheduled batch runs and consumes no continuous web-serving compute while idle. Option C has no direct infrastructure cost up front, but carries substantial hidden costs in developer rework, debugging, and compliance or operational risk.

---

## Recommendation and Verification Plan

The technical trade-off analysis supports **Option B (Scheduled Batch Inference Writing to Primary Database)** as the recommended architecture. Pre-computing predictions during scheduled batch runs and storing them in dedicated, pre-indexed database columns fits report- and dashboard-driven deliverables, avoids always-on microservice overhead, keeps read queries fast for downstream consumers, and preserves internal data handling boundaries. For model artifacts, the pipeline will load serialized `joblib` binaries for Random Forest candidates or `.json`/`.ubj` artifacts for XGBoost candidates from a controlled location via an automated Python runner, ensuring consistent deserialization and clear write semantics before downstream views consume the results.

To verify that the decision works in practice and catch failures before or during rollout, the team will use the following checks:

* **Unit and Serialization Tests (`pytest`):** Verify that candidate Random Forest (`.joblib`) and XGBoost (`.json`/`.ubj`) model artifacts load cleanly in the target runtime environment and produce predictions matching expected input/output shapes and data types. Executed automatically via `pytest` prior to integration.
* **Integration and Write-Consistency Tests:** Run end-to-end pipeline tests against a test database to verify that batch runs write expected prediction values, nullability/types, and record associations into target database columns without schema mismatches or silent dropped/misaligned writes. Executed on pipeline changes and pre-release integration runs.
* **Performance and Lockup Acceptance Criteria:** Require 100% of target test records to be scored and persisted in under 60 seconds with zero unhandled exceptions or database lockups. Measured during test runs by recording start and completion timestamps around the batch job and checking test logs and database lock/error status, with a failing or timed-out run blocking release/adoption.

---

## Constraints

* **Data Privacy and Confidentiality (FERPA and NDA):** Student education records and institutional data are governed by FERPA and project NDA obligations (U.S. Department of Education, n.d.). This rules out exposing unauthenticated or external scoring endpoints and constrains inference to approved internal environments, while requiring write-consistency and error checks so batch runs do not fail partially or misroute sensitive outputs.
* **Open-Source Licensing:** Core software packages used for data handling, modeling, and persistence (such as `scikit-learn`, `xgboost`, `pandas`, `joblib`, and `SQLAlchemy`) rely on permissive open-source licenses (such as MIT, BSD-3-Clause, and Apache 2.0). These permissive licenses allow internal use and integration into project pipelines without imposing copyleft distribution obligations on project code.
* **Intellectual Property and Partner Terms:** Pipeline scripts, database schema changes, and trained model artifacts are subject to project partner agreements and institutional IP rules. This requires keeping scripts, schemas, and approved model artifacts versioned and stored within controlled project repositories and storage rather than scattered across unmanaged local folders.

---

## Delegation and Validation

For this RFC, I handed my AI tool a project description to create a base knowledge about what we are doing for the project, as well as our current thoughts on the outlook of our project. From there, I went through each of the 5 previous headers (Problem and context, Options, Analysis, Recommendation and verification plan, and constraints) and provided my exact thoughts based on the context for that part of the document. All of the ideas, options, recommendations, and constraints were provided myself, AI was only used to expand those into an in-depth document. From here, I then proofread everything and manually altered portions that felt either incorrect or unclear to the project.

To make relying on that expanded draft reasonable, I checked generated statements against concrete sources rather than taking them at face value. I compared architectural and workflow claims against our actual project requirements and partner expectations, verified technical details against official library and compliance documentation (such as model persistence docs, XGBoost serialization formats, open-source licenses, and FERPA guidance), and aligned the verification plan with the test and database checks we use in practice (such as `pytest` unit/serialization checks and database integration tests). Where AI phrasing overstated capabilities, introduced assumptions that did not match our setup, or sounded vague, I revised or removed it during proofreading.

I stopped to manually validate the output at specific high-stakes points where getting the wrong answer would be costly to undo. First, I checked the framing of the inference delivery options and database write path because changing how predictions are stored and served later would force schema changes, query updates, or rework on downstream views and reports once consumers build around them. Second, I verified the model serialization and security details—comparing `.joblib` and `pickle`-based persistence against XGBoost's `.json` and `ubj` formats because version mismatches or unsafe loading from untrusted paths can break pipelines or create security risks. Third, I audited the entire draft for NDA and FERPA boundaries to make sure no sensitive student data, restricted feature names, or unapproved external assumptions slipped into the text.

---

## Decision

A formal decision has not been made yet. Both the project team and project partner agree we are not at the correct point in our project timeline to formally make this decision. We are still in an exploratory phase analyzing dataset trends to inform model weighting—before locking in the inference delivery architecture, though a decision is expected soon once those findings stabilize.

---

## Revision Log

| Source | Feedback | Decision | Where or Why |
| :--- | :--- | :--- | :--- |
| Instructor: Alex Ulbrich | Include sources | Changed | **References:** Added a references list at the bottom of what was used in the research process. |
| Reviewer: Cyrus Ho | Adding when the frontend depends on model outputs would make the early timeline urgency clearer | Changed | **Problem and Context:** Added explanation that downstream frontend views and scheduled report deliverables depend on a stable prediction schema and predictable availability schedule before consumers integrate against output fields. |
| Reviewer: Cyrus Ho | Briefly note whether an event-driven queue (such as Celery or Redis) was considered alongside Option B to explain why scheduled batch scripts were preferred. | Changed | **Options and Analysis:** Added a note under Options and expanded the Complexity subsection in Analysis explaining that Celery/Redis message brokers and worker lifecycles add unnecessary operational overhead for a scheduled, report-driven cadence. |
| Reviewer: Cyrus Ho | Ensure the team can practically measure the 60-second scoring and persistence threshold during test runs. | Changed | **Recommendation and Verification Plan:** Specified under Performance and Lockup Acceptance Criteria that the 60-second threshold is measured by recording start and completion execution timestamps around the batch job while checking test logs and database lock/error status. |

---

## References

* Joblib Developers. (n.d.). *Serialization and memory-mapped loading*. Joblib Documentation. https://joblib.readthedocs.io/en/stable/user_guide/persistence.html
* Scikit-learn Developers. (n.d.). *Model persistence*. Scikit-learn Documentation. https://scikit-learn.org/0.19/modules/model_persistence.html
* U.S. Department of Education. (n.d.). *Family Educational Rights and Privacy Act (FERPA)*. Protecting Student Privacy. https://studentprivacy.ed.gov/ferpa
* XGBoost Developers. (n.d.). *Introduction to Model IO*. XGBoost Documentation. https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html
```[cite: 1, 2, 3, 4, 5, 6, 7]