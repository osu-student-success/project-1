# AGENTS.md

## 1. Project Overview

This repository contains an ML student success intelligence model developed in partnership with the Oregon State University College of Engineering.

The model uses historical academic and institutional data to identify factors associated with student outcomes, predict academic risk, and provide useful insights to advisors and administrators.

The project may include:

- Data processing and engineering.
- Exploratory data analysis (EDA).
- Machine learning models for predicting student outcomes.
- Model evaluation and performance comparisons.
- Explainability and interpretability tools, including SHAP.
- Data visualizations and interactive dashboards.
- Decision-support functionality for advisors and administrators.

The goal is to develop a useful, reliable, and understandable model that supports student success.

## 2. Project Documentation

Before making changes, consult the relevant project documentation.

| Document | Purpose |
|---|---|
| `README.md` | Project overview, installation, and basic usage instructions. |
| `CONTRIBUTING.md` | Development setup, local checks, branching, commits, pull requests, and Definition of Done. |
| `docs/requirements.md` | Functional and non-functional requirements and expected system behavior. |
| `docs/` | Additional technical documentation, design decisions, and project documentation. |

These documents are the authoritative sources for project-specific instructions.

Do not independently redefine requirements, contribution policies, or technical decisions that are already documented.

If documentation is missing, incomplete, or contradictory, ask for clarification rather than inventing project decisions.

## 3. General Instructions

When working in this repository:

1. Understand the existing project structure before making changes.
2. Follow the established coding conventions and patterns already used in the repository.
3. Prefer simple, readable, and maintainable implementations over unnecessary complexity.
4. Avoid introducing new dependencies unless they provide a clear benefit.
5. Keep changes focused on the requested task.
6. Do not modify unrelated files or functionality.
7. Write code that can be tested and maintained by other team members.
8. Update relevant documentation when functionality, requirements, or development instructions change.
9. Do not assume a feature is required unless it is documented or explicitly requested.
10. Explain important implementation decisions and any assumptions made.

## 4. Working with Data

This project involves institutional and academic data. Data confidentiality and responsible handling are essential.

AI tools and contributors must follow these rules:

- Never expose, reproduce, or unnecessarily inspect confidential partner data.
- Never commit actual student records or personally identifiable information.
- Do not include confidential data in prompts, logs, screenshots, test fixtures, or documentation.
- Use synthetic, anonymized, or approved sample data when developing and testing functionality.
- Do not upload partner-provided datasets to external services or AI tools unless explicitly authorized.
- Do not assume that removing student names makes a dataset anonymous.
- Follow the partner's data-access, storage, and confidentiality requirements.

If a task requires access to sensitive data or clarification about permitted data use, stop and ask the project team.

## 5. Machine Learning and Data Analysis

When working on machine learning or data analysis components:

- Prevent data leakage between training, validation, and test datasets.
- Follow the project's documented data-splitting strategy.
- Do not use held-out test data to select models, tune hyperparameters, or choose decision thresholds.
- Document preprocessing steps and model assumptions.
- Use appropriate evaluation metrics rather than relying only on accuracy.
- Make experiments reproducible whenever possible.
- Clearly distinguish correlation from causation.
- Avoid presenting model predictions as definitive conclusions about individual students.
- Document important limitations and potential sources of bias.

Model changes should include appropriate tests or evaluation results demonstrating their effect.

Refer to the project requirements and technical design documents for the approved modeling and evaluation approach.

## 6. Testing and Code Quality

Follow the checks and standards documented in `CONTRIBUTING.md`.

Before considering a change complete:

- Run the relevant tests.
- Check for linting and formatting issues.
- Verify that existing functionality has not been broken.
- Add or update tests when introducing new functionality.
- Update documentation when necessary.

If a required command or automated check has not yet been implemented, do not claim that it passed. Explain which checks were performed and which remain unavailable.

Do not remove tests or weaken validation simply to make a change pass.

## 7. AI Tool Behavior

AI coding assistants should act as contributors to the project, not as decision-makers.

When generating or modifying code:

- Do not invent requirements, data schemas, API contracts, or repository structure.
- Ask questions when important implementation details are unclear.
- Explain assumptions before making changes that could affect other components.
- Do not silently change established technical decisions.
- Do not introduce unnecessary abstractions or overly complicated solutions.
- Keep generated code understandable to student developers who will maintain it.
- Identify generated code and recommendations that require human verification.
- Never claim to have run tests, commands, or checks that were not actually executed.

AI tools may assist with research, implementation, debugging, documentation, and testing. Team members remain responsible for reviewing and approving all generated work.

## 8. Project Decisions and Scope

Project requirements and technical decisions should follow the processes established by the team.

- Refer to `docs/requirements.md` before implementing new functionality.
- Use documented design decisions and RFCs when making significant technical changes.
- Do not independently change project scope or partner expectations.
- Raise conflicts between implementation requests and existing requirements with the project team.
- Document significant decisions so future contributors understand their reasoning.

If an implementation request conflicts with existing documentation, identify the conflict and request clarification before proceeding.

## 9. Final Expectations

The objective is to produce software that is reliable, maintainable, understandable, and useful to the project partner.

Prioritize correctness, data confidentiality, reproducibility, and clear documentation over quickly producing code.

All changes must follow the repository's contribution process and Definition of Done in `CONTRIBUTING.md`.
