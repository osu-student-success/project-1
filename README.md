# Project 1 - Building the Model

This project estimates how likely a college student is to drop out. It trains a random forest on student records and prints that likelihood as a percentage.

## Data status

The code currently runs on fake data. `data/students.csv` is a generated sample of about 210 students, created so the pipeline can be built and tested before the real dataset arrives.

We are under NDA. The real student data has not been received yet. Do not treat the current CSV, model scores, or results as real student outcomes.

## Run it

From this folder, with the virtual environment already set up:

```powershell
.\.venv\Scripts\python.exe generate_dataset.py
.\.venv\Scripts\python.exe dropout_model.py
.\.venv\Scripts\python.exe predict_student.py 1001
```

`generate_dataset.py` rewrites the fake CSV. `dropout_model.py` trains the random forest and saves it to `models/dropout_rf.joblib`. `predict_student.py` takes a student ID, reads that row from the CSV, and prints a dropout percentage. Run it with no ID to type one at the prompt.

Once the real data is available, we will replace the fake CSV and retrain. Until then, every result comes from the generated sample.
