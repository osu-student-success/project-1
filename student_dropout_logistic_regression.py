"""
Logistic regression model for predicting whether a student drops out.

Expected CSV target column: dropped_out
- 1 = dropped out
- 0 = did not drop out

Install dependencies:
    pip install pandas scikit-learn

Run:
    python student_dropout_logistic_regression.py
    python student_dropout_logistic_regression.py path/to/your_students.csv
"""

import argparse
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


TARGET = "dropped_out"
RANDOM_STATE = 42 #Allows me to run the program again and get the same train/test split


def main():
    parser = argparse.ArgumentParser(
        description="Train and evaluate a logistic regression dropout-risk model."
    )
    parser.add_argument(
        "csv_file",
        nargs="?",
        default="data/fake-students.csv",
        help="CSV dataset path (default: fake-students.csv)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=15,
        help="Number of important features to display (default: 15)",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Could not find {csv_path}. Put the CSV beside this script "
            "or pass its path as an argument."
        )

    data = pd.read_csv(csv_path)

    if TARGET not in data.columns:  # checks that the dropped_out feature is in the dataset
        raise ValueError(
            f"The dataset must contain a '{TARGET}' column. "
            f"Columns found: {', '.join(data.columns)}"
        )

    # Remove rows where the outcome is unknown.
    data = data.dropna(subset=[TARGET]).copy()

    # Convert the target to numeric 0/1.
    y = pd.to_numeric(data[TARGET], errors="raise").astype(int)
    if not set(y.unique()).issubset({0, 1}):
        raise ValueError(f"'{TARGET}' must contain only 0 and 1.")

    # student_id is an identifier, not a meaningful predictor.
    # The target is kept separate from the input features.
    excluded_columns = [TARGET]
    if "student_id" in data.columns:
        excluded_columns.append("student_id")

    X = data.drop(columns=excluded_columns)

    if y.nunique() != 2:
        raise ValueError("The target must contain both classes: 0 and 1.")

    # Identify numeric and categorical columns automatically.
    numeric_features = X.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_features = X.select_dtypes(exclude=["number", "bool"]).columns.tolist()

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),  #for missing values
            ("scaler", StandardScaler()), # puts numerical features on the same scale, GPA(0-4) vs number of credits(0-150)
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessing = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ],
        remainder="drop",
    )

    model = Pipeline(
        steps=[
            ("preprocessing", preprocessing),
            (
                "logistic_regression",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )

    # Keep the same proportion of dropout/non-dropout cases in each split.
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=RANDOM_STATE,
        stratify=y, # same proporation of students who dropped out in both train and test set
    )

    model.fit(X_train, y_train) # trains the model on logistic regression
    predictions = model.predict(X_test)

    print("\n=== Student Dropout Prediction Results ===")
    print(f"Rows in dataset: {len(data)}")
    print(f"Training rows:   {len(X_train)}")
    print(f"Testing rows:    {len(X_test)}")
    print(f"Dropouts (1):    {(y == 1).sum()}")
    print(f"Non-dropouts (0): {(y == 0).sum()}")
    print("\nTest-set metrics:")
    print(f"Accuracy:  {accuracy_score(y_test, predictions):.3f}")
    print(
        "Precision: "
        f"{precision_score(y_test, predictions, zero_division=0):.3f}"
    )
    print(f"Recall:    {recall_score(y_test, predictions, zero_division=0):.3f}")

    tn, fp, fn, tp = confusion_matrix(y_test, predictions, labels=[0, 1]).ravel()
    print("\nConfusion matrix counts (positive class = dropped out):")
    print(f"True negatives:  {tn}")
    print(f"False positives: {fp}")
    print(f"False negatives: {fn}")
    print(f"True positives:  {tp}")

    # Get the names created by preprocessing (including one-hot categories).
    feature_names = model.named_steps["preprocessing"].get_feature_names_out()
    coefficients = model.named_steps["logistic_regression"].coef_[0]

    importance = pd.DataFrame(
        {
            "feature": feature_names,
            "coefficient": coefficients,
            "absolute_importance": abs(coefficients),
        }
    ).sort_values("absolute_importance", ascending=False)

    print(f"\n=== Top {args.top} Most Important Features ===")
    print("Ranked by absolute logistic-regression coefficient.")
    print("Positive coefficient = associated with higher predicted dropout odds.")
    print("Negative coefficient = associated with lower predicted dropout odds.\n")

    for rank, row in enumerate(importance.head(args.top).itertuples(), start=1):
        direction = (
            "higher dropout odds"
            if row.coefficient > 0
            else "lower dropout odds"
            if row.coefficient < 0
            else "no direction"
        )
        print(
            f"{rank:2}. {row.feature}: "
            f"coefficient={row.coefficient:+.3f} "
            f"({direction})"
        )



if __name__ == "__main__":
    main()
