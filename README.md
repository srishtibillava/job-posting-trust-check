# Job Posting Trust Check (prototype)

A prototype of the dual-pronged verification tool: a Chrome extension (client tier), a FastAPI backend
(application tier) and a SQLite database of community reports (data tier).

| Report module | File |
|---|---|
| Rule-Based Screening | `backend/rules.py` |
| Machine Learning Classification | `backend/train_model.py` (training), `backend/app.py` (use) |
| Verification (website, domain age) | `backend/verify.py` |
| Trust Score and Feedback | `backend/scoring.py`, `/report` endpoint in `backend/app.py` |
| Browser extension | `extension/` |

## 1. Set up
```
pip install -r requirements.txt
```

## 2. Train the model
1. Download the EMSCAD dataset (`fake_job_postings.csv`) from Kaggle (search "Real / Fake Job Posting Prediction").
2. Put it in the `data/` folder.
3. Run: `python backend/train_model.py data/fake_job_postings.csv`

It prints a confusion matrix, precision/recall/F1 and precision-recall AUC, and saves `model/model.joblib`.
Use the "fake" row's recall and F1 in your report. Plain accuracy is misleading because only about 5% of postings are fake.

## 3. Start the backend
```
cd backend
uvicorn app:app --reload
```
Open http://127.0.0.1:8000/docs to try `/analyze` and `/report` in the browser.
Without a trained model the app still works: it uses the rules and verification only.

## 4. Load the extension
1. Open `chrome://extensions` and switch on Developer mode.
2. Click "Load unpacked" and choose the `extension` folder.
3. Open a job posting, select its description, click the extension, then "Use selected text" and "Check posting".

## Design choices
- Score weights in `backend/scoring.py`: ML 0.45, rules 0.35, verification 0.20.
- Thresholds: Green 70 or more, Yellow 40 to 69, Red below 40. An explicit payment demand caps the score at 30.
- Company registration is not automated, because there is no free reliable API. The tool says so in its output.

## Limitations
- The model is trained on EMSCAD (2012 to 2014, mostly English), so it may miss newer scams. The rules and verification checks help cover this.
- The score is a warning, not proof. Always verify a company yourself.
- The prototype runs locally and is not hosted.

## Testing
Tested with sample Green, Yellow and Red postings through the Chrome extension and the API docs page, including the report feature.