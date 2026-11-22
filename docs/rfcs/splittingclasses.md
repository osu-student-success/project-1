# RFC Final Draft

## Problem and context

This project focuses on predicting first-year student retention at Oregon State University using machine learning. The goal is to determine whether information available during a student's first year can predict whether they will return to OSU the following fall. This could help advisors and student-success staff identify students who may need additional support. During the fall term, we will focus on first-time, full-time students and use historical student records to develop and evaluate predictive models.

An important part of this project is deciding how to split entering classes into training, validation, and test data. The final test class must remain separate from model development, including training, feature selection, and model tuning. Using test data during development could make the final evaluation unreliable. We need to establish this separation before training models to avoid compromising the test data and preserve an independent evaluation of performance on unseen students.

The stakes of this decision are important because predictions could influence how advisors prioritize their time and resources. For example, advisors could use the model to identify students who may not return and connect them with tutoring, academic advising, financial resources, or other university services. Holding out the latest eligible entering class for final testing allows us to evaluate how well the model predicts retention for an entirely new class of students. This is important because poor predictions could lead advisors to spend time contacting students who do not need support (false positives) or miss students who would benefit from additional help (false negatives). We need to make this decision soon, before model development begins, so the team can establish the class boundaries and avoid using information from the final test class when selecting or adjusting models. Ultimately, the goal is to ensure that the model's performance is reliable enough to inform student-support decisions while supporting, rather than replacing, advisor judgment.

## Options

### Option A: Use the Latest Class as the Test Set with One Validation Class

Hold out the latest entering class with a full year of available data as the final test set. Train the models using the earlier entering classes and use one intermediate class for validation and model tuning. The test class will remain untouched until model training and parameter adjustments are complete. It will only be used for the final evaluation.

**Benefits:**

- Evaluates the model on a newer entering class, better representing how it may perform on future students.
- Keeps the final test class separate from model development, reducing the risk of data leakage.

**Costs:**

- Results may be less stable if the validation or test class has unusual characteristics or differs from other classes.
- Using only one validation class provides limited evidence of how consistently the model performs across entering classes.

**When to Choose This Option:**

This would be the right choice if we do not have enough time or historical data to train and evaluate models across multiple validation classes. It is also a simpler approach that requires fewer training runs and less computational effort.

### Option B: Use the Latest Class as the Test Set with Rolling-Origin Validation

Keep the latest eligible entering class as the final test set and use rolling-origin validation on earlier classes. In each round, train on all eligible classes before the validation class and evaluate on the next class. As the process repeats, the previous validation class is added to the training data, creating an expanding training window. The validation results will help the team compare models and select an appropriate flagging threshold. The latest class will remain untouched until final testing.

**Benefits:**

- Provides multiple validation results instead of relying on a single validation class.
- Makes model and threshold choices less dependent on the results from one particular entering class.
- Provides a better understanding of how well the model generalizes to different groups of students over time.

**Costs:**

- Requires more work to build and run the modeling pipeline.
- Requires multiple training and validation runs, increasing the time and computational resources needed.
- Earlier validation rounds may have fewer entering classes available for training, which could make some results less stable.

**When to Choose This Option:**

This would be the right choice if we have several historical entering classes available to train and validate the models. It would also be ideal if we have enough time to run multiple rounds of training and validation. This approach would allow us to compare model performance across different entering classes before making our final decisions.

### Option C: Use K-Fold Cross-Validation with the Latest Class as the Test Set

Keep the latest eligible entering class as the final test set, but use K-fold cross-validation on the remaining historical classes for model training and validation. The historical data would be divided into K groups (folds). The model would be trained on K-1 folds and validated on the remaining fold. This process would repeat until every fold has been used for validation. The validation results would then be averaged and used to compare models and select the best model settings. The latest eligible entering class would remain completely separate and would only be used for the final evaluation.

**Benefits:**

- Provides multiple validation results instead of relying on a single validation class.
- Allows every historical class to be used for both training and validation across different rounds.
- Can help reduce the impact of an unusually strong or weak validation group when comparing models.

**Costs:**

- The model could train on newer entering classes and validate on older classes, which does not accurately represent how our model would be used to predict future student retention.
- Requires multiple training and validation runs, increasing development time and computational effort.
- Averaging results across folds could hide differences in model performance between older and newer entering classes.

**When to Choose This Option:**

This approach would be more appropriate if the entering classes are relatively similar and we do not need to preserve their chronological order during validation. However, because our project focuses on predicting retention for future entering classes, standard K-fold cross-validation may not be the best fit. If we want to preserve chronological order, rolling-origin validation (Option B) would be a better choice.

### Option D: Do Nothing

Defer the final test split decision until the data becomes available and allow the team to decide which entering class to hold out after exploring the available data. The team would continue with initial data exploration without formally selecting and sealing a final test class.

**Benefits:**

- Allows the team to examine data availability before committing to a specific split.
- Avoids designing a split that may need to change once data access is confirmed.

**Costs:**

- Exploring all classes before selecting a test set could compromise its independence.
- Delaying the decision could leave insufficient time for model development and evaluation.

**When to Choose This Option:**

This may be a reasonable choice if we do not have access to the data yet and cannot determine which entering classes will be available. However, deferring the decision should only be temporary. We should establish a deadline for selecting and sealing the final test class before exploring patterns that could influence model development or evaluation.

## Analysis

### Option A: Make the Latest Class the Test Set with One Validation Class

This option provides a realistic final evaluation by testing the model on the newest eligible entering class. However, using only one validation class may make model selection overly dependent on that class's characteristics. The University of British Columbia (n.d.) explains that results from a single validation set can depend heavily on which examples it contains. For our project, this means that an unusually strong or weak entering class could influence which model and threshold we select. Although this approach is simpler to implement and requires fewer training runs, it provides limited evidence of how consistently the model performs across different cohorts.

### Option B: Make the Latest Class the Test Set with Rolling-Origin Validation

This option keeps the latest eligible entering class separate for final testing while using earlier cohorts for rolling-origin validation. Having multiple validation results provides more evidence of model stability across different groups of students. According to the scikit-learn documentation (n.d.), its TimeSeriesSplit method is designed for time-ordered data because other cross-validation methods can result in training on future data and evaluating on past data. This is important for our project because we want to simulate predicting retention for future entering classes. Training on earlier cohorts and validating on the next available cohort better reflects this goal.

Our project currently has nine historical cohorts spanning 2017–2026. This provides multiple cohorts that could potentially be used for training and validation while reserving the latest eligible cohort for final testing. However, the number of usable cohorts may be lower depending on data completeness and eligibility requirements. Each validation round also requires another model training and evaluation run, increasing development time and pipeline complexity. Despite this additional work, rolling-origin validation would allow us to compare performance across multiple cohorts rather than relying on one validation result. We will need to confirm that the available data supports enough validation rounds to make this approach worthwhile.

### Option C: K-Fold Cross-Validation

K-fold cross-validation would also provide multiple validation results, but standard K-fold does not necessarily preserve the chronological order of entering classes. Scikit-learn (n.d.) explains that traditional cross-validation methods assume observations are independent and identically distributed. With time-dependent data, this can result in training on future observations and evaluating on past observations. This is a concern because our project aims to predict retention for future entering classes.

Although we have nine historical cohorts available, using standard K-fold could mix older and newer cohorts across training and validation. Additionally, splitting individual student records rather than entire cohorts could place students from the same entering class in both sets. This would make it harder to evaluate how well the model generalizes to an entirely new cohort. K-fold offers multiple validation results, but rolling-origin validation is a better fit because it preserves the chronological order that matters to our project.

### Option D: Do Nothing

Deferring the decision would allow our team to examine the available data before choosing a final test cohort. This provides flexibility, especially because we still need to confirm which of the nine historical cohorts have complete and eligible data. However, Google for Developers (n.d.) explains that separating data into training, validation, and test sets is important for developing and evaluating machine learning models. If we explore all cohorts before selecting a test set, information from the eventual test cohort could influence model development and compromise the independence of the final evaluation.

This option may be reasonable temporarily while our team confirms data availability, but it should not become a long-term approach. We should establish the final test cohort before making modeling decisions that could be influenced by its outcomes. Delaying this decision also reduces the time available for implementation, validation, and final testing.

## Recommendation and Verification Plan

My recommendation is Option B: use the latest eligible entering class as the final test set and apply rolling-origin validation to earlier classes. This approach provides multiple validation results while preserving chronological order, making it a better fit for predicting retention among future students. Our team will know that the decision worked by evaluating the following criteria:

- **Data Separation:** The latest eligible entering class must remain untouched during model development, including training, feature selection, model selection, and threshold tuning. It will only be used for final testing.
- **Data Leakage Check:** Implement an automated check that compares unique student record identifiers across the development and final test sets. The check must fail if any student record appears in both. This will help ensure that records are not accidentally shared between development and final testing.
- **Performance Target:** Set a preliminary target of at least 70% recall across the validation cohorts. This means the model should correctly identify at least 70% of students who do not return to OSU. We will also establish a precision baseline and evaluate the number of students flagged to determine whether the model's predictions are manageable for advisors. The team will confirm these targets based on validation results and available outreach capacity.
- **Model Comparison:** Evaluate all candidate models using the same evaluation metrics across multiple chronological validation splits. Document their recall, precision, and overall performance to determine which model performs most consistently across cohorts.
- **Final Testing:** After selecting the model and threshold using validation results, evaluate the final model on the latest eligible entering class. Report its performance, including recall and precision, and determine whether it meets the established performance target. The test results will not be used to make further model adjustments.

## Constraints

The biggest constraint with this decision is that we cannot control how much data we receive. We are limited to the data that the University approves us to access and use. If we do not receive enough complete and eligible entering classes to support rolling-origin validation, we may need to use Option A instead.

Another important constraint is protecting student information. Student records must remain in approved storage and must not be committed to Git or shared with unapproved AI tools. This means that data preparation, validation, and testing must follow the University's data access and storage requirements. When checking for data leakage between development and test sets, we must use approved student identifiers rather than exposing personal information. My team should also use fake data for demonstrations and ensure that reports and visualizations do not expose identifiable student information.

## Delegation and validation

I used ChatGPT and Claude to help develop this draft. ChatGPT assisted with drafting individual sections, while Claude helped generate potential options. I provided both tools with background information about the project to make their suggestions relevant. I reviewed their responses for accuracy and consistency with our project goals, checked the provided links, and used Ctrl+F to verify that any quoted material appeared in the cited sources.

I made the final recommendation based on my own judgment rather than automatically accepting either tool's suggestions. I paid particular attention to the data-splitting approach because an incorrect split could cause data leakage and produce misleading model performance results. I also reviewed the explanations of validation methods and performance metrics to ensure the technical reasoning was accurate. Finally, I compared the document against our project charter to ensure the proposed approach aligned with our team's goals. Before implementation, the team will review the available data and agree on the final approach.

## Decision

- **Status:** Proposed
- **Date:** November 16, 2026
- **Decision Chair:** Owen Badzinski
- **Proposed Decision:** Option B – Use the latest eligible entering class as the final test set with rolling-origin validation using an expanding training window.
- **Approval:** The team will review the proposed options, consider the amount of historical data available, and agree on the final approach before implementation. Once the team reaches an agreement, the decision status will be updated to accepted or rejected. Agreement will be reached around week 9 or 10 after we clean the data and start constructing the model.

## References

Google for Developers. (n.d.). Datasets: Dividing the original dataset. Machine Learning Crash Course. Retrieved November 17, 2026, from https://developers.google.com/machine-learning/crash-course/overfitting/dividing-datasets

scikit-learn developers. (n.d.). 3.1. Cross-validation: Evaluating estimator performance. scikit-learn. Retrieved November 17, 2026, from https://scikit-learn.org/stable/modules/cross_validation.html

scikit-learn developers. (n.d.). TimeSeriesSplit. scikit-learn. Retrieved November 17, 2026, from https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html

University of British Columbia. (n.d.). Chapter 3: Machine learning fundamentals. CPSC 330: Applied Machine Learning. Retrieved November 17, 2026, from https://ubc-cs.github.io/cpsc330-book/book/03_ml-fundamentals.html
