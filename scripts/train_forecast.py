"""Step 7 - Weekly demand forecasting with strict time-based splits.

Target: units sold per ISO week (Monday start) for the whole business and for the three largest
region groups. Models: naive, seasonal naive (lag 52), linear regression, random forest, XGBoost
and Holt's damped-trend exponential smoothing (statsmodels).

Protocol (no shuffling anywhere):
  train = all weeks before the validation window
  validation = 12 weeks  -> models fitted on train, used to SELECT the model
  test = last 12 complete weeks -> models refitted on train+validation, used to REPORT error
Predictions are one-step-ahead: each week is predicted with the actual values of earlier weeks.
"""

import json
import warnings

import duckdb
import joblib
import numpy as np
import pandas as pd
from common import ARTIFACTS_DIR, DB_PATH, MODELS_DIR, SEED
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from xgboost import XGBRegressor

VAL_WEEKS = 12
TEST_WEEKS = 12
HORIZON = 8
SERIES = ["All regions", "United Kingdom", "Western Europe", "Ireland & Channel Is."]
FEATURES = ["lag_1", "lag_2", "lag_3", "lag_4", "roll_mean_4", "week_sin", "week_cos", "holiday_days", "is_pre_christmas"]
ML_MODELS = {
    "Linear Regression": lambda: make_pipeline(StandardScaler(), LinearRegression()),
    "Random Forest": lambda: RandomForestRegressor(n_estimators=300, min_samples_leaf=2, random_state=SEED),
    "XGBoost": lambda: XGBRegressor(n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9, random_state=SEED),
}
ALL_MODELS = ["Naive", "Seasonal Naive", *ML_MODELS, "Exponential Smoothing"]


def load_weekly(con: duckdb.DuckDBPyConnection, group: str) -> pd.DataFrame:
    where = "" if group == "All regions" else "WHERE r.region_group = ?"
    params = [] if group == "All regions" else [group]
    weekly = con.execute(
        f"""
        SELECT c.week_start, SUM(s.quantity) AS units
        FROM sales s JOIN calendar c USING(date) JOIN regions r USING(region_id) {where}
        GROUP BY 1 ORDER BY 1""",
        params,
    ).df()
    cal = con.execute("""SELECT week_start, SUM(holiday_flag::INT) AS holiday_days,
                         MAX(is_pre_christmas::INT) AS is_pre_christmas FROM calendar GROUP BY 1""").df()
    max_date = con.execute("SELECT MAX(date) FROM sales").fetchone()[0]
    weeks = pd.DataFrame({"week_start": pd.date_range(weekly.week_start.min(), weekly.week_start.max(), freq="W-MON")})
    df = weeks.merge(weekly, how="left").merge(cal, how="left").fillna({"units": 0})
    # Drop the last week if it is incomplete (the dataset ends mid-week).
    if pd.Timestamp(max_date) < df.week_start.iloc[-1] + pd.Timedelta(days=6):
        df = df.iloc[:-1]
    return df.reset_index(drop=True)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for k in (1, 2, 3, 4, 52):
        df[f"lag_{k}"] = df["units"].shift(k)
    df["roll_mean_4"] = df["units"].shift(1).rolling(4).mean()
    woy = df["week_start"].dt.isocalendar().week.astype(int)
    df["week_sin"] = np.sin(2 * np.pi * woy / 52)
    df["week_cos"] = np.cos(2 * np.pi * woy / 52)
    return df


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    err = y - p
    nonzero = y > 0
    mape = float(np.mean(np.abs(err[nonzero] / y[nonzero])) * 100) if nonzero.any() else None
    return {
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "mape": mape,
        "mape_excluded_zero_weeks": int((~nonzero).sum()),
    }


def predict_window(df: pd.DataFrame, fit_idx: np.ndarray, pred_idx: np.ndarray) -> tuple[dict, dict]:
    """Fit every model on fit_idx rows and predict pred_idx rows one step ahead."""
    preds, fitted = {}, {}
    y = df["units"].to_numpy(dtype=float)
    preds["Naive"] = df.loc[pred_idx, "lag_1"].to_numpy()
    preds["Seasonal Naive"] = df.loc[pred_idx, "lag_52"].fillna(df.loc[pred_idx, "lag_1"]).to_numpy()
    train = df.loc[fit_idx].dropna(subset=FEATURES)
    for name, factory in ML_MODELS.items():
        model = factory().fit(train[FEATURES], train["units"])
        preds[name] = np.clip(model.predict(df.loc[pred_idx, FEATURES]), 0, None)
        fitted[name] = model
    ets = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in pred_idx:
            m = ExponentialSmoothing(y[:i], trend="add", damped_trend=True).fit()
            ets.append(max(float(m.forecast(1)[0]), 0.0))
    preds["Exponential Smoothing"] = np.array(ets)
    return preds, fitted


def future_forecast(df: pd.DataFrame, model_name: str, fitted, horizon: int) -> list[dict]:
    """Recursive multi-step forecast: each predicted week becomes a lag for the next one."""
    hist = df[["week_start", "units", "holiday_days", "is_pre_christmas"]].copy()
    cal_future = df.attrs["calendar_future"]
    out = []
    for h in range(1, horizon + 1):
        week = hist.week_start.iloc[-1] + pd.Timedelta(weeks=1)
        extra = cal_future.get(week, {"holiday_days": 0, "is_pre_christmas": 0})
        row = pd.DataFrame([{"week_start": week, "units": np.nan, **extra}])
        tmp = add_features(pd.concat([hist, row], ignore_index=True))
        last = tmp.iloc[[-1]]
        if model_name == "Naive":
            value = float(last["lag_1"].iat[0])
        elif model_name == "Seasonal Naive":
            value = float(last["lag_52"].fillna(last["lag_1"]).iat[0])
        elif model_name == "Exponential Smoothing":
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m = ExponentialSmoothing(hist["units"].to_numpy(float), trend="add", damped_trend=True).fit()
            value = float(m.forecast(1)[0])
        else:
            value = float(fitted.predict(last[FEATURES])[0])
        value = max(value, 0.0)
        out.append({"week_start": str(week.date()), "forecast": round(value, 1), "step": h})
        hist = pd.concat([hist, row.assign(units=value)], ignore_index=True)
    return out


def recursive_backtest(df: pd.DataFrame, fitted: dict, test_idx: np.ndarray) -> dict:
    """Stricter check: forecast the whole test window from its origin (end of validation) recursively,
    so weeks 2..12 use earlier *predictions* as lags instead of actual values."""
    origin = df.iloc[: test_idx[0]].copy()
    origin.attrs = df.attrs
    y = df["units"].to_numpy(float)[test_idx]
    out = {}
    for m in ALL_MODELS:
        path = future_forecast(origin, m, fitted.get(m), len(test_idx))
        out[m] = metrics(y, np.array([p["forecast"] for p in path]))
    return out


def run_series(con, group: str) -> dict:
    df = add_features(load_weekly(con, group))
    cal = con.execute("""SELECT week_start, SUM(holiday_flag::INT) AS holiday_days,
                         MAX(is_pre_christmas::INT) AS is_pre_christmas FROM calendar GROUP BY 1""").df()
    df.attrs["calendar_future"] = {
        r.week_start: {"holiday_days": int(r.holiday_days), "is_pre_christmas": int(r.is_pre_christmas)} for r in cal.itertuples()
    }
    n = len(df)
    test_idx = np.arange(n - TEST_WEEKS, n)
    val_idx = np.arange(n - TEST_WEEKS - VAL_WEEKS, n - TEST_WEEKS)
    train_idx = np.arange(0, n - TEST_WEEKS - VAL_WEEKS)
    y = df["units"].to_numpy(float)

    val_preds, _ = predict_window(df, train_idx, val_idx)
    test_preds, fitted = predict_window(df, np.concatenate([train_idx, val_idx]), test_idx)
    val_metrics = {m: metrics(y[val_idx], val_preds[m]) for m in ALL_MODELS}
    recursive_metrics = recursive_backtest(df, fitted, test_idx)
    test_metrics = {m: metrics(y[test_idx], test_preds[m]) for m in ALL_MODELS}
    selected = min(ALL_MODELS, key=lambda m: val_metrics[m]["mae"])
    best_test = min(ALL_MODELS, key=lambda m: test_metrics[m]["mae"])

    # Refit the selected model on all data for the future forecast.
    final_model = None
    if selected in ML_MODELS:
        full = df.dropna(subset=FEATURES)
        final_model = ML_MODELS[selected]().fit(full[FEATURES], full["units"])
        MODELS_DIR.mkdir(exist_ok=True)
        joblib.dump(final_model, MODELS_DIR / f"forecast_{group.lower().replace(' ', '_').replace('&', 'and').replace('.', '')}.joblib")
    future = future_forecast(df, selected, final_model, HORIZON)
    resid_sd = float(np.std(y[test_idx] - test_preds[selected], ddof=1))
    for f in future:  # approximate band from test residual spread; widens with sqrt(step)
        half = 1.96 * resid_sd * np.sqrt(f["step"])
        f["lower"] = round(max(f["forecast"] - half, 0), 1)
        f["upper"] = round(f["forecast"] + half, 1)

    history = []
    for i, row in df.iterrows():
        split = "train" if i in train_idx else "validation" if i in val_idx else "test"
        item = {"week_start": str(row.week_start.date()), "actual": float(row.units), "split": split}
        if split == "test":
            item.update({m: round(float(test_preds[m][list(test_idx).index(i)]), 1) for m in ALL_MODELS})
        if split == "validation":
            item.update({m: round(float(val_preds[m][list(val_idx).index(i)]), 1) for m in ALL_MODELS})
        history.append(item)

    importance = None
    if "Random Forest" in fitted:
        importance = dict(
            sorted(zip(FEATURES, fitted["Random Forest"].feature_importances_.round(4).tolist(), strict=False), key=lambda kv: -kv[1])
        )
    span = lambda idx: {"start": str(df.week_start.iloc[idx[0]].date()), "end": str(df.week_start.iloc[idx[-1]].date()), "weeks": len(idx)}
    return {
        "series": group,
        "target": "units per week",
        "n_weeks": n,
        "periods": {"train": span(train_idx), "validation": span(val_idx), "test": span(test_idx)},
        "horizon_weeks": HORIZON,
        "features": FEATURES,
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
        "test_metrics_recursive": recursive_metrics,
        "evaluation_note": "test_metrics are one-step-ahead (each week predicted with actual earlier weeks). "
        "test_metrics_recursive forecast all 12 test weeks from the end of validation, feeding predictions back as lags.",
        "selected_model": selected,
        "lowest_test_mae_model": best_test,
        "history": history,
        "future": future,
        "rf_feature_importance": importance,
        "interval_note": "Approximate 95% band = forecast +/- 1.96 x test residual SD x sqrt(step). Not a calibrated interval.",
    }


def main() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    results = {g: run_series(con, g) for g in SERIES}
    con.close()
    (ARTIFACTS_DIR / "forecast_results.json").write_text(json.dumps(results, indent=2))
    for g, r in results.items():
        print(
            f"[forecast] {g}: selected={r['selected_model']} test MAE="
            + ", ".join(f"{m}:{v['mae']:.0f}" for m, v in r["test_metrics"].items())
        )


if __name__ == "__main__":
    main()
