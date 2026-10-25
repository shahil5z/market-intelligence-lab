# PROJECT-CONTEXT

**What:** Market Intelligence Lab: a student data science portfolio project (EDA, demand forecasting, statistical testing, segmentation, anomaly detection, optional AI explanations).
**Data:** UCI Online Retail II (CC BY 4.0) + seeded synthetic campaigns/pack size/market type (always labelled).
**Status:** Phase 1 complete locally. Not deployed and no remote.

## Layout
- `scripts/`: data pipeline (`run_pipeline.py` runs every step)
- `backend/app/`: FastAPI. All SQL lives in `db.py`; services in `services/`; routes in `api/routes.py`
- `frontend/`: Next.js app router, one folder per page, shared UI in `components/ui.tsx`
- `models/`: JSON results (committed) + joblib models (ignored)
- `docs/`: data dictionary, generated data-quality report

## Rules
- Every number in the UI comes from the API; no hard-coded results.
- Synthetic data is labelled wherever it appears. No company branding.
- Secrets come only from the environment; `.env` and `forblog.md` are gitignored.
- Mark anything unverified NOT VERIFIED / NOT TESTED.

## Key decisions
- Weekly units as the forecast target; selection on validation MAE; one-step-ahead test.
- k=4 for K-Means (best k≥3 by silhouette) for actionability.
- Weekly robust MAD z-score for anomalies (a daily version was too noisy).
- AI layer explains computed JSON only. The rule-based fallback is used when no key is set.
