# RFC: Prediction Export Architecture

| Field | Value |
| --- | --- |
| Author | Kellen Swanson |
| Date | 2026-10-25 |
| Status | Proposed |
| Deciders | Team members |

## Problem and Context

Our project is to build a model using historical academic and institutional data to predict student success based on a multitude of factors. Since this project requires an NDA, I am unable to give specific data factors we are using, as that is sensitive information. My hard-to-reverse problem for this project is how the model will deliver its findings to users. For some background, we currently have not decided on what specific model type we will be using for this, as we are deciding between a random forest or an XGBoost model currently.

This decision will decide whether or not the architecture will serve inference dynamically through a live microservice endpoint, generate offline batch calculations stored directly in database structures, or rely on manual local execution scripts. This needs to happen this early in the project timeline because this could not only affect the model file type we use (`.joblib`, `.pkl`, or other option), but more importantly it would affect the structure in the data-to-output pipeline. This would change the fundamental schema of our software and could potentially change the format of our frontend. Thus, we need to decide how the model delivers its findings to the users.

---

## Options

* **Option A:** Use a real-time API to serve the model. Based on our research, this would likely use a combination of **FastAPI** and **Docker** to combine the data into a simple lightweight model to use on the frontend. The model would receive HTTP POST requests with the data payload, then deserialize the payload and return an immediate prediction.
* **Option B:** Run batch predictions directly using a Python script. This would load raw data tables, run batch predictions across target datasets, and write results back into dedicated prediction columns inside the primary database. Downstream views query these pre-calculated fields directly.
* **Option C:** Rely on developers running prediction scripts manually or executing inline Python routines at runtime whenever outputs are required.

---

## Analysis

### Option A: Real-Time API Microservice
Option A provides sub-second prediction latency for single-record lookups, making it ideal if downstream interfaces require interactive, on-demand scoring. However, this pattern introduces significant operational and architectural complexity: it requires containerizing the inference environment with Docker, configuring API routing via FastAPI, managing dependency serialization, and setting up endpoint health monitoring. From a maintainability perspective, any upstream feature changes require updates to both the API payload validation schemas (Pydantic) and client-side request handlers. From a security and cost standpoint, hosting an active HTTP service expands the system's network attack surface, requiring authentication layers to protect endpoints against unauthorized payload injection. Furthermore, an always-on API service incurs higher infrastructure compute costs compared to scheduled execution.

### Option B: Scheduled Batch Inference Pipeline
Option B decouples inference execution from live user requests by pre-computing predictions on a schedule (e.g., nightly background jobs triggered via Python scripts) and writing scores directly into primary database tables. For end-users, read latency is effectively reduced to zero because downstream dashboards query pre-scored database columns without invoking live ML models. Operational complexity is drastically reduced, as the system eliminates web service routing, active port exposures, and container orchestrations in favor of simple, version-controlled execution scripts. Maintainability is straightforward because the pipeline interfaces directly with our database models without requiring external network contracts. From a security perspective, this pattern is highly secure for sensitive student and institutional data; it keeps all execution internal to the database environment without exposing scoring endpoints over external networks. Infrastructure costs are minimal since compute resources spike briefly during batch execution and consume zero resources when idle. The primary trade-off is data freshness: predictions remain static between batch execution intervals.

### Option C: Manual/Ad-hoc Execution
Option C incurs zero initial development cost or architectural setup. However, it fails across every critical technical metric in production. Performance and latency are entirely unpredictable, as predictions rely on developers or end-users manually executing local Python scripts whenever updated outputs are required. System complexity degrades quickly into technical debt, resulting in duplicated code, unversioned local model files, and missing dependency boundaries. Maintainability is unmanageable over time due to a complete lack of execution triggers, automated testing, or deployment pipelines. From a security standpoint, running ad-hoc scripts on local developer machines poses severe risks to sensitive student data compliance (FERPA), increases the likelihood of credential leakage, and lacks audit trails or access controls.

---

## Recommendation and Verification Plan

We propose adopting **Option B (Scheduled Batch Inference Pipeline)** integrated directly with our core relational database, as pre-computing scores during scheduled background jobs eliminates runtime HTTP overhead, avoids blocking user interface threads, and best serves our analytical, report-driven deliverables. 

Under this workflow, serialized machine learning artifacts—specifically serialized `joblib` binaries for Random Forest models and native `.json` (or Universal Binary JSON `.ubj`) files for XGBoost models—will be loaded from a secure model registry by an automated Python task runner that reads feature records, computes predictions, and writes the output back into pre-indexed database table columns. 

### Verification Criteria
1. **Model Deserialization & Schema Testing:** Automated `pytest` suites will test model deserialization and schema shape alignment.
2. **Integration Testing:** End-to-end integration tests will validate write consistency to target database fields.
3. **Acceptance Criteria:** 100% of target records must be successfully scored and saved in under 60 seconds with zero unhandled pipeline exceptions or database lockups.

---

## Constraints

* **Open-Source Licensing:** This architectural decision is bound by strict open-source licensing, intellectual property guidelines, and partner confidentiality agreements surrounding student data. All core software dependencies supporting the batch inference pipeline—including `scikit-learn`, `xgboost`, `pandas`, `joblib`, and `SQLAlchemy`—operate under permissive open-source licenses (MIT, BSD 3-Clause, Apache 2.0), ensuring compliance without introducing copyleft or proprietary restrictions.
* **Data Privacy (FERPA):** Because the system ingests sensitive institutional and student performance data subject to strict privacy regulations like FERPA, Option B enforces a secure partner confidentiality boundary by executing all model scoring strictly within internal database execution environments, entirely avoiding the exposure of unencrypted student records or prediction features over external network endpoints.
* **Intellectual Property:** All developed pipeline code, database schemas, and trained model artifacts remain fully compliant with project partner agreements and institutional capstone intellectual property policies, ensuring clean code ownership without violating third-party data usage terms.

---

## Delegation and Validation

For this RFC, I handed my AI tool a project description to create a base knowledge about what we are doing for the project, as well as our current thoughts on the outlook of our project. From there, I went through each of the 5 previous headers (*Problem and context*, *Options*, *Analysis*, *Recommendation and verification plan*, and *Constraints*) and provided my exact thoughts based on the context for that part of the document. All of the ideas, options, recommendations, and constraints were provided myself; AI was only used to expand those into an in-depth document. From here, I then proofread everything and manually altered portions that felt either incorrect or unclear to the project.