# CONTRIBUTING.md

## 1. Development Setup

Before contributing, make sure you have access to the project repository and the development tools required by the component you are working on.

Our project is an AI-powered student success intelligence platform. It uses historical institutional and academic data to identify factors associated with student outcomes, predict academic risk, and provide useful insights through visualizations and decision-support tools.

### Requirements

- Git
- Access to the project repository
- Python (for data processing and machine learning components)
- Any additional dependencies documented by the component you are working on

The exact Python version, package manager, and additional development dependencies will be documented once the development environment is finalized.


### Getting Started

Follow the setup instructions in the project's `README.md` for the standard installation and startup process.

If you encounter setup problems, document the issue and ask the team for assistance.

## 2. Local Checks

Before opening a pull request, contributors should run the available checks to make sure their changes do not introduce problems.

The following commands are the planned standard interface for local checks:

| Check | Command | Purpose |
|---|---|---|
| Tests | `make test` | Run the project's automated test suite. |
| Lint | `make lint` | Identify code quality and style issues. |


**Implementation status:** These commands will be added as the project's development tooling is established.

The same checks will run through GitHub Actions before a pull request can be merged.

Until these checks are implemented, contributors should manually verify their changes and document any testing performed in their pull requests.

## 3. Branches and Commits

### Default Branch

The default branch is `main`.

All completed and reviewed work should eventually be merged into `main`. Contributors should not commit directly to this branch.

### Branch Naming

Create a separate branch for each feature, bug fix, or documentation change.

Use the following naming convention:

- `feature/<short-description>` — New features.
- `fix/<short-description>` — Bug fixes.
- `docs/<short-description>` — Documentation changes.
- `test/<short-description>` — Test additions or modifications.
- `refactor/<short-description>` — Code restructuring without changing functionality.

Examples:

- `feature/student-risk-prediction`
- `fix/data-cleaning-error`
- `docs/update-readme`
- `test/model-evaluation`

Use lowercase letters and hyphens to separate words.

### Commit Messages

Follow the Conventional Commits format:

`<type>: <short description>`

Common types include:

- `feat` — New functionality.
- `fix` — Bug fixes.
- `docs` — Documentation changes.
- `test` — Test additions or modifications.
- `refactor` — Code restructuring.
- `chore` — Maintenance and configuration changes.

Examples:

- `feat: add student risk prediction`
- `fix: handle missing enrollment values`
- `docs: update development setup instructions`
- `test: add model evaluation tests`

Commit messages should be concise and describe what the change accomplishes.

## 4. Pull Requests and Review

All code and documentation changes must be submitted through a GitHub pull request.

### Pull Request Requirements

Every pull request should include:

1. **Description:** Explain what the change does and why it is needed.
2. **Related issue:** Link the issue or task associated with the change, if applicable.
3. **Testing:** Describe the tests performed and their results.
4. **Documentation:** Identify any documentation that was updated.

Keep pull requests focused on a single feature, fix, or related set of changes. Avoid combining unrelated work into one pull request.

### Review Process

- At least **one approval** from another team member is required before merging.
- Contributors should not approve their own pull requests.
- Pull requests should receive an initial review within **two business days**.
- Reviewers should check functionality, code quality, tests, documentation, and potential security concerns.
- Requested changes must be addressed before approval and merging.
- The author is responsible for resolving review comments and requesting another review when necessary.

### Merging

Once the required approval is received and all required CI checks pass, the pull request can be merged.

Do not merge pull requests with failing required CI checks or unresolved blocking review comments.

## 5. Definition of Done

A contribution is considered complete when it meets the following requirements.

| Requirement | Completion Criteria | Enforcement |
|---|---|---|
| Functionality | The change works as intended and meets its associated requirements. | Manual review and automated tests. |
| Testing | Relevant automated tests pass. New functionality includes appropriate tests. | `make test` and GitHub Actions test job. |
| Code Review | At least one other team member approves the pull request. | GitHub branch protection rules. |
| CI | All required continuous integration checks pass. | GitHub Actions required status checks. |

### Planned Implementation

Some of these checks may not exist during the initial development stages. The following implementation plan establishes how they will be introduced.

| Gate | Implementation | Target Sprint | Owner |
|---|---|---|---|
| Automated testing | Establish test suite and `make test` command. Add GitHub Actions test job. | Sprint 2 | Testing lead |
| Linting | Configure linting tool and `make lint` command. Add CI job. | Sprint 2 | Code quality lead |
| Formatting | Configure formatter and `make format-check` command. Add CI job. | Sprint 2 | Code quality lead |
| Pull request approval | Require one approval before merging through GitHub branch protection. | Sprint 2 | Repository administrator |
| Documentation | Establish documentation review as part of the pull request template and review process. | Sprint 2 | Documentation lead |
| Security | Add dependency and secret scanning through GitHub Actions. Add `make security` command. | Sprint 3 | Security lead |
| Required CI checks | Configure GitHub Actions to run all required checks and block merging when they fail. | Sprint 3 | Repository administrator |

Until each gate is implemented, the team is responsible for manually following the corresponding requirement.

The team shares responsibility for maintaining the Definition of Done. Completing a task does not automatically mean it is ready to merge.

## 6. Where Other Work Lives

Not all project work needs to become a pull request.

| Work Type | Location | Acceptance |
|---|---|---|
| Bugs and feature requests | GitHub Issues | Anyone on the team. |
| Technical decisions and design proposals | Repository `docs/` directory, using design documents or RFCs when appropriate. | Team review and agreement. |
| Project requirements | `docs/requirements.md` | Team, with partner feedback when requirements affect partner expectations. |
| Meeting notes and action items | Team's shared project workspace. | Note taker for team during meetings. |
| Partner feedback and requested changes | Documented in GitHub Issues or the requirements document after partner meetings. | Team coordinates confirmation with the partner at meetings. |

Significant changes to project requirements or technical decisions should be documented so that future contributors can understand why decisions were made.

Changes to partner expectations should be confirmed with the partner before the team treats them as finalized requirements.

## 7. Getting Help

For questions or problems during development:

- **Code and implementation questions:** Ask in the team's discord.
- **Bugs and technical issues:** Open a GitHub Issue with a description of the problem and steps to reproduce it. Let the team know in discord.
- **Git and development environment problems:** Ask the team for assistance in discord.

Team members should aim to respond to questions within **one business day**.

If a question is blocking development, clearly identify it as blocking so the team can prioritize a response.

When asking for help, include relevant error messages, screenshots, commands, and steps already attempted. Never include passwords, API keys, or confidential partner data in public issues or messages.

---

## Maintaining This Document

This document should be updated whenever the team's development workflow, tooling, or contribution policies change.

Changes to branching rules, review requirements, CI checks, and development commands should be reflected here so that the documentation remains consistent with the actual repository configuration.

When introducing a new tool or workflow, document the required commands and setup instructions before expecting other contributors to use it.
