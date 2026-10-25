# PROJECT-CONTEXT

**What:** Market Intelligence Lab: a student data science portfolio project (EDA, demand forecasting, statistical testing, segmentation, anomaly detection, optional AI explanations).
**Data:** UCI Online Retail II (CC BY 4.0) + seeded synthetic campaigns/pack size/market type (always labelled).
**Status:** Phase 2. Live: frontend https://market-intelligence-lab.vercel.app (Vercel project `market-intelligence-lab`), API https://mil-api-shahils-projects-e75357dc.vercel.app (project `mil-api`). Repo target: github.com/shahil5z/market-intelligence-lab.

## Layout
- `scripts/`: data pipeline (`run_pipeline.py` runs every step)
- `backend/app/`: FastAPI. All SQL lives in `db.py`; services in `services/`; routes in `api/routes.py`
- `frontend/`: Next.js app router, one folder per page, shared UI in `components/ui.tsx`
- `backend/artifacts/`: model JSON + `mil.duckdb.gz` (committed, shipped with the API; unpacked to tmp and opened read-only). `models/` holds joblib files (ignored)
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
- Forecast is reported both one-step and 12-week recursive; campaign p-values get Holm + BH.
- Deploy: two Vercel projects. Backend env: OPENAI_API_KEY (server-side only), OPENAI_MODEL, FRONTEND_URL, FRONTEND_ORIGINS. Frontend env: NEXT_PUBLIC_API_URL. CORS is an explicit allow-list; '*' raises at startup.
- No pyproject.toml in backend/ (Vercel picks it over requirements.txt). Lint/test config lives in ruff.toml / pytest.ini.
- Known gap: the live OPENAI_API_KEY is invalid, so the fallback is shown. Fix it in the Vercel dashboard, then redeploy.
