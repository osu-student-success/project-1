RFC: Choosing Between Random Forest and XGBoost for Student Dropout Prediction   
Author: Jackson Marcum 

Course: CS 461 Senior Software Engineering Project 

Date: November 22, 2026 

Status: Proposed \- Open for Team Review 

**1\. Problem and Context**   
Our senior project focuses on using machine learning to predict which college students may be at risk of dropping out. The goal is to help universities identify students who may be struggling so they can provide support before those students decide to leave school.   
A machine learning model is the mathematical approach that learns patterns from past examples and uses them to make predictions about new cases. For our project, that means learning from permitted student information to estimate which students might be at risk of leaving school. Choosing the model is more than picking a name from a list. The choice influences which patterns the system can learn, what settings we need to adjust, and how clearly we can explain the results to a university staff member. This explanation is important because someone reading our RFC may not already know how machine learning works.   
Right now, our group has only been assigned research. We have been finding and reviewing papers about different machine learning models, but we have not started coding, training, or testing anything yet. One decision we will eventually need to make is whether Random Forest or XGBoost would be a better model for our project. These are not the only models that exist, but they are two tree-based approaches discussed in our research that give us a practical comparison between a relatively straightforward starting point and a more heavily tuned alternative.   
This decision is important because the model we choose will affect how we develop and test our project. Switching models later could require changes to our training process, evaluation methods, and how we explain predictions. If we do not decide on an approach before development, we could spend extra time changing things later. A change could also mean rewriting training code, repeating evaluations, or revisiting results that have already been shared with our project partner. That is why this decision is consequential, even though it is not impossible to reverse. It would be easier to reconsider if we keep our data preparation and evaluation process consistent between models. 

The stakes are not just technical. Missing a student who needs support could mean losing an opportunity to reach out, while identifying too many students incorrectly could waste staff time or create unnecessary concern. Our project should help people make better decisions, not make automatic judgments about students. Since we have not received final data or operating requirements, this RFC recommends a starting approach instead of claiming that a model is already selected or that we know how well it will perform. 

**2\. Options**  
**Option 1: Continue Researching Without Choosing a Model** 

Our first option is to continue researching different models without choosing one yet. Since we are still early in the project, this would give us more time to understand their strengths and weaknesses. The downside is that we would not have a starting point once development begins. This could slow down our progress and make it harder to compare results.   
It might be the right choice if we still do not know what information we are allowed to use, what counts as a dropout, or what resources will be available. However, waiting indefinitely would leave the team without a plan for building a baseline. If we continue researching, we should still set a point at which we revisit the decision before development begins. 

**Option 2: Random Forest** 

Random Forest uses multiple decision trees to make predictions based on patterns in data. It is commonly used for classification problems and can work with different types of student information. One paper I researched, Predictive Analytics Study to Determine Undergraduate Students at Risk of Dropout, used Random Forest to predict student dropouts. The researchers found that adjusting the prediction threshold improved the model’s ability to identify students who were at risk. Random Forest could be a good starting point because it can recognize complicated patterns without requiring as much tuning as some other models. However, it can still be difficult to explain exactly why it makes certain predictions.   
Its main cost would be the time needed to prepare data correctly, train a model, choose a prediction threshold, and review errors. The advantage is that it could provide a useful baseline before the group attempts more complicated methods. Random Forest would be the right choice if its results meet the partner’s needs and the extra work required by another model would not provide a meaningful improvement. Using many decision trees does not automatically make the results transparent, so we would still need to investigate how the features affect predictions. 

**Option 3: XGBoost** 

XGBoost is another machine learning model that uses decision trees, but it builds them in a way that focuses on correcting errors from previous trees. In the paper A Modular and Explainable Machine Learning Pipeline for Student Dropout Prediction in Higher Education, researchers compared nine different models. XGBoost performed the best with an AUC of 0.993 and a recall of 94.4%. These results show that XGBoost could be useful for our project. However, it may require more tuning and could make development more complicated.   
Choosing XGBoost first would make sense if our partner values the potential for improved predictions enough to justify additional configuration and testing time. The team would need to review more tuning settings and document them so the results could be reproduced. The published study gives us a reason to test XGBoost, but it does not prove that it will outperform Random Forest on our data. The number of students, available features, and definition of dropout could be different.   
Other credible models should not be ignored. K-nearest neighbors, Naive Bayes, and logistic regression are possible alternatives, and the XGBoost paper itself compared several different algorithms. We are focusing this RFC on Random Forest and XGBoost because both have support in the research our team has reviewed and because they create a useful comparison of two approaches based on decision trees. If development time allows, logistic regression could also serve as a simple extra benchmark. If our partner’s requirements make one of these alternatives more appropriate, our team should reconsider the shortlist. 

**3\. Technical Analysis** 

Based on the research we have completed, I think the biggest factors in choosing between these models are prediction performance, complexity, and how easy the results are to understand. Prediction performance is important because we want to identify students who may actually drop out. However, accuracy alone does not tell us how well a model works. One paper we reviewed had 14,495 students, but only 8.5% dropped out. This made it harder for the model to correctly identify those students. Because of this, I think our group should pay attention to precision, recall, and F1-score. Recall is important because we do not want to miss students who may need help. Precision is also important because we do not want to incorrectly identify too many students as being at risk.   
This imbalance makes the tradeoff more important. A model that almost always predicts students will stay enrolled might appear accurate but would fail at the main purpose of the project. Recall tells us the proportion of students who actually dropped out that the model identified. Precision tells us how many students flagged as at risk were correctly identified. F1-score helps summarize the balance between those two measures. We should also compare ROC-AUC and look at the actual numbers of false positives and false negatives, rather than judging performance from one score alone. Which error is more costly depends partly on how much support capacity the university has.   
Random Forest has the advantage of being relatively easy to use and requiring less tuning. XGBoost may provide better performance, but it could require more time to configure and test. Another important factor is explainability. In the XGBoost study I researched, the researchers used SHAP to help explain which features influenced the predictions. This could be useful because universities should understand why students are being identified as at risk. Since our group has not started development, we do not know which model will perform better with our own data. The results from the papers give us useful information, but they do not guarantee that we will get the same results. 

**4\. Recommendation and Verification Plan** 

Based on our research, I recommend that our group start with Random Forest as our initial model and compare it against XGBoost once we begin development. I think Random Forest would be a good starting point because it is relatively simple to implement and does not require as much tuning. This would allow us to establish a baseline before trying a more complicated approach. This is only my recommendation based on our research so far. Our group has not officially selected a model or started testing anything yet. Once we begin development, I think we should use the same training and testing data for both models. We should compare their precision, recall, F1-score, and ROC-AUC to see which one performs better.  
Before testing, the group should agree with our partner on the definition of dropout, which data can be used, and what level of performance would actually be useful. We should separate training, validation, and testing data so that the final test results are not used to choose model settings. Both models should be trained and evaluated with the same eligible information. Any cleaning or balancing of the data should be learned from training data only. We should record the data version, software settings, and random seeds so another teammate could repeat our work. This will help make the comparison fair instead of giving one model an advantage. 

To verify our decision, I would suggest the following requirements: 

• Both models should use the same dataset and testing process. 

• We should compare how many at-risk students each model correctly identifies.  
 • We should review false positives and false negatives. 

• We should compare how much tuning and training time each model requires. 

• We should document our results so we can repeat the tests. 

• We should review the proposed prediction threshold using validation data before final testing.  
 • We should check that the model uses only approved information available at prediction time. 

Our acceptance criteria should be agreed on before we see final test results. For example, the partner should define a minimum acceptable recall, how many false alerts staff could reasonably review, and whether added complexity is worth a small improvement. We cannot responsibly give exact targets yet because those requirements have not been provided. A model would fail the plan if it cannot meet the agreed standards, uses data it is not permitted to use, or produces results the group cannot reproduce. We should also check results across student groups where the data and permission allow it, since overall performance could hide large differences.   
If XGBoost performs noticeably better, we could consider switching to it. Otherwise, Random Forest may be the better option because it would be easier to maintain. We should document the results in a comparison table that includes each model, the dataset and settings used, performance metrics, and any limitations. If neither model meets the partner’s agreed standards, the team should revisit the data, problem definition, or other model options rather than forcing a selection. The final decision should be reviewed by the team and partner before the model is used to support any real students. 

**5\. Constraints**   
One major concern with our project is student privacy. The papers we researched used information such as grades, attendance, and demographics to predict student dropouts. If our group eventually uses student records, we will need to make sure we have permission to access that information and that it is properly protected. We also need to consider any restrictions on the datasets we use.   
For student records, the partner would need to identify which data may be accessed, where they may be stored, and who can see them. If the records are protected educational information, the university will need to determine the applicable privacy and confidentiality requirements, including any relevant FERPA obligations. Our team should not upload restricted data to public repositories or outside AI tools without explicit permission. These restrictions could change the model inputs or even where we can train and test our models. If some information cannot be used, we should evaluate both models under the same limits.   
Another concern is bias. Several papers mentioned that models trained using historical student data may not work equally well for every student population. A model that performs well at one university might not perform the same way at another. We also need to consider the time and resources available to our group. Since we are still in the research phase, we have not determined what computing resources or datasets will be available for development.   
Finally, we will need to review the licenses of any datasets and software libraries we use and follow any confidentiality requirements from our project partner. We should also check whether any library or dataset license limits redistribution of code, trained models, or reports. If the partner has rules about intellectual property or outside services, those rules must be reviewed before our team shares results or deploys anything. The recommendation is only valid if it can be implemented within these restrictions. 

**6\. Delegation and Validation** 

So far, our group has mainly focused on researching different machine learning models and reviewing their results. We have not started building or testing our own models. For this RFC, I used ChatGPT to help organize the research and compare Random Forest and XGBoost. The information about model performance came from the papers our group collected, but the recommendation is based on what I think would be the best starting point for our project. Before making a final decision, I would need to verify the research findings and discuss the recommendation with my teammates. Once development begins, any AI-assisted code or suggestions should be reviewed and tested by our group. We should make sure we understand how the models work and verify the results ourselves rather than relying only on AI-generated information.   
For the final draft, I also used ChatGPT to help reorganize a few explanations and turn the feedback into clearer revisions. I did not have AI create experimental data, run training, or invent benchmark results. The most important possible errors would be misstating numbers from the papers, giving an unfair comparison, or presenting assumptions about our partner as confirmed requirements. Those points need to be checked against the cited articles and with the team before anyone uses this RFC as an implementation plan. Any model code written with AI assistance later would need to pass our own tests and review. 

**Decision**   
Status: Proposed \- Open for Team Review. I recommend starting with Random Forest as the baseline and comparing it with XGBoost under the same approved testing conditions. The group has not officially accepted this choice, and no models have been trained yet. We should revisit the recommendation after reviewing our data, results, and project partner’s requirements. 

**References**  
1\. Bettahi, Abdelkarim, et al. “A Modular and Explainable Machine Learning Pipeline for Student Dropout Prediction in Higher Education.” Algorithms, vol. 18, no. 10, MDPI AG, Oct. 2025, p. 662, [https\://doi.org/10.3390/a18100662](https://doi.org/10.3390/a18100662). Accessed 25 Oct. 2026\. 

2\. Gonzalez-Nucamendi, Andres, et al. “Predictive Analytics Study to Determine Undergraduate Students at Risk of Dropout.” Frontiers in Education, vol. 8, Frontiers Media SA, Oct. 2023, 

[https\://doi.org/10.3389/feduc.2023.1244686](https://doi.org/10.3389/feduc.2023.1244686) Accessed 25 Oct. 2026\. 

3\. Matti Vaarma, and Hongxiu Li. “Predicting Student Dropouts With Machine Learning: An Empirical Study in Finnish Higher Education.” Technology in Society, vol. 76, Elsevier BV, Feb. 2024, pp. 102474–74, [https\://doi.org/10.1016/j.techsoc.2024.102474](https://doi.org/10.1016/j.techsoc.2024.102474). Accessed 25 Oct. 2026\. 

**Revision Log** 

| Source  | Feedback  | Decision  | Where or why |
| :---- | :---- | :---- | :---- |
| Ayowade Owojori  | Explain why Random Forest and XGBoost were the main options and consider other algorithms. | Changed  | Sections 1 and 2 explain the shortlist and mention k-nearest neighbors, Naive Bayes, and logistic regression. |
| Ayowade Owojori  | The existing verification steps should show which model performs better. | Kept / clarified  | Section 4 preserves the comparison and adds more specific acceptance and failure conditions. |
| Jackson Maffei  | Explain what a machine learning model is and why model choice matters for a newcomer. | Changed  | Section 1 adds a plain-language definition and connects model choice to training and evaluation. |
| Jackson Maffei  | The verification approach should detect failure. | Kept / clarified  | Section 4 keeps the testing plan and explains how the group would record and review results. |

