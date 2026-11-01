

# RFC: Splitting Classes into training and test sets



| Field | Value |
| --- | --- |
| Author | Owen Badzinski |
| Date | 2026-10-25 |
| Status | Proposed |
| Deciders | Team members |

## Problem and Context

The project that I am working on for this year focuses on predicting first-year student retention at Oregon State University using ML techniques. The goal is to determine whether information available during a student's first year can be used to predict whether they will return to OSU the following fall. This could help advisors and student-success staff identify students who may need additional support. During the fall term, we will focus on first-time, full-time students and use historical student records to develop and evaluate predictive models. During this project we will have to explore and prepare the data, then compare different models to determine how well they can predict retention. 

Part of this is determining how we are going to split which entering classes will be the ones to train the models and the one we set aside as the test class. We need to do this because when we are training a model we can not have it see the data in the test class in any way. If it does, the model could learn the patterns in the test class and would make the results of our model not truly accurate in predicting if a student is at risk. Because of this we need to make a decision before training the model because at that point it is irreversible. If we do not do anything about this we will not have a set of data that can truly see how accurate our models are.


## Options

### Option A: Make the latest class the test set with one validation class

Hold out the latest entering class with a full year of data as the final test set. Train on the earlier classes, and use one intermediate class for validation and tuning. The test class is not used until after we are done training the model and adjusting the parameters with the validation class.

Benefits:
Closely represents how the model would perform when predicting retention for a future group of students.
Provides a clear separation between older data used for developing the model and newer data used for final evaluation.
Helps reduce the risk of the model benefiting from information from the final test class during development.
Fits the project's goal of using historical data to predict outcomes for students not previously seen by the model.


Costs:
The latest eligible class may have fewer students or different characteristics than older classes, which could make the final results less stable.
If there are unusual circumstances affecting that particular entering class, the test results may not represent future classes well.
My team cannot use results from the test class to make decisions about the model before the final evaluation, which may require more planning and discipline during development.

This would be the right choice if we do not have enough time to train the models for multiple rounds with different validation classes or if we do not have a whole lot of historical classes.


### Option B: Make the latest class the test set with Rolling-Origin Validation

Keep the latest eligible entering class as the final test set, but use rolling-origin validation instead of one validation class. The model would be trained on earlier entering classes and validated on the next class, repeating this process across the available classes. The validation results would then be used to choose the model settings and flagging rule. The latest class would remain completely sealed and would only be used for the final evaluation.

Benefits:
Provides multiple validation results instead of relying on a single validation class.
Makes model and threshold choices less dependent on the results from one particular entering class.
Shows how consistently the model performs across different entering classes.

Costs: 
Requires more work to build and run the modeling pipeline.
Requires multiple training and validation runs.

This would be the right choice if we have several historical classes to use to train the model. This would also be ideal if we have enough time to train the models for multiple rounds with different validation classes.


### Option C: Do Nothing

Defer the final test split decision until the data becomes available and let the team decide which class to hold out after exploring the data. The team would continue with initial data exploration without formally sealing a test class.

Benefits:
Avoids committing to a test split before my team knows which entering classes have sufficient data.
Avoids spending time designing a split that may need to change once the actual data becomes available.
Keeps my team's options open while data access and eligibility remain uncertain.

Costs:
My team may explore all entering classes before choosing a test set, making it difficult to keep the final test data untouched.
Waiting too long could leave insufficient time to compare models and complete the final evaluation before the deadline.
My team may have to make a rushed decision later, when changing the test split would be more costly.

This may be the right choice when we don’t have access to the data yet. Deferring the decision may be reasonable temporarily, but we should set a deadline to select and seal the final test class before exploring patterns that could influence model development.


## Analysis


This option tests the model on the newest eligible class, making the results more representative of predicting retention for future students. However, a single validation class may not represent performance across different classes. According to the University of British Columbia, it states “We could reserve one fixed validation set, but the result may depend heavily on which examples happen to enter it”. This means that the model's result would be heavily impacted by the one validation class because we would be adjusting the hyperparameters of the model specifically based on the validation class. On the other hand it would be simple to implement, document, and reproduce. 
https://ubc-cs.github.io/cpsc330-book/book/03_ml-fundamentals.html

Option B: Make the latest class the test set with Rolling-Origin Validation
In this option we keep the latest class as the test set while using earlier classes for validation. Multiple validation classes provide more evidence of model stability across classes and reduce reliance on a single validation result. This does however require more pipeline development, experiment tracking, and model runs since you are training the model more times. According to scikit, it says when talking about rolling-origin validation, “Provides train/test indices to split time-ordered data, where other cross-validation methods are inappropriate, as they would lead to training on future data and evaluating on past data”. This means that Rolling-Origin validation only validates with future data which could be helpful with our project since we do not want to train our model with classes that are past the validation class. 

https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html

Option C: Do nothing

With this option we would be delaying the decision which allows my team to first see how many eligible students and entering classes are available. This is the simplest option initially because no additional split or validation process needs to be implemented. But according to our project charter and google for developers, we will have to do this step at some point since splitting up the data into training, validation, and test is important to figuring out how truly accurate the model is. This option provides flexibility while my team is still learning about the available data, but it creates the greatest risk to the independence of the final test. It is only reasonable as a temporary approach if the team does not yet have enough information to determine the eligible test class.

https://developers.google.com/machine-learning/crash-course/overfitting/dividing-datasets

## Recommendation and Verification Plan

My recommendation would be Option B: Make the latest eligible entering class the final test set and use rolling-origin validation. This allows my team to compare model performance across multiple entering classes rather than relying on a single validation class. Since the project aims to predict retention for future students, training on earlier classes and validating on later classes better reflects how the model would be used. The latest eligible class will remain separate from model selection, feature selection, and threshold tuning. My team will use the validation results to select a model before evaluating it on the final test class.

For determining how we will know it was the right choice we will want to be successful in these outcomes:

Data separation: The latest class remains untouched until final testing, preventing its outcomes from influencing model decisions.
Model comparison: Candidate models are evaluated across multiple chronological validation splits using the same evaluation metrics.
Performance: The selected model is compared against the agreed baseline using precision, recall, and outreach capacity, rather than accuracy alone.
Final testing: After selecting the model and threshold, my team evaluates the final model on the latest eligible class and documents its performance and limitations.


## Constraints

The biggest constraint with this decision is that we can not control how much data we can receive. We are limited to the amount of data we are approved to use by the University. So if we do not have enough data to do rolling-origin validation we may have to go to option A. We also need to make sure that student records remain in approved storage and must not be committed to Git or shared with unapproved AI tools. My team should use fake data for demonstrations and ensure that reporting does not expose identifiable student information.

## Delegation and Validation

To make this draft I used chatgpt and Claude. ChatGPT was used to help draft the sections. After it drafted each section I looked back on everything it wrote to make sure it was accurate with its sources and to my project and make edits when necessary. I gave ChatGPT an overview of what my project is so it can accurately write details about my project and understand the decision in regards to my project. I also did the same for Claude as well so it could accurately help generate possible options to help with this decision. I looked at each option and verified that what Claude was saying was accurate. I also made sure to click on any link that the AI tools generated to make sure that the source was real and reputable, and that the AI did not hallucinate any information and confirmed that the quotes it generated did exist in the sources it found by using ctrl F. When it came to the recommendation, I used my own judgement in thinking option B would be the best for my team and did not follow explicitly what the AI tool was the best option. Everything that was written in this document was checked by me to confirm that it was accurate information and accurate to my project by looking at our project charter. Before we implement any approach my team will review the options that we have and depending on how much data we have access to and will pick the option that fits the best for our situation and not rely specifically on what an AI tool says.

## Decision

Proposed