"""Price trend prediction — a statistical estimate over a listing's own
historical price points, never a guarantee. Below a minimum number of data
points it returns an explicit "insufficient data" result instead of
extrapolating from too little history to mean anything.

Model selection: fits both a simple linear trend and a small
RandomForestRegressor, validates each against the most recent real price
point, and keeps whichever had lower error — the brief's "picked by
validation error" design, done as a bake-off between a linear and a
non-linear learner rather than committing to one model.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sqlalchemy.orm import Session

from app.database.models import PriceHistory, ProductListing
from app.schemas.price import PricePredictionOut
from app.services.price_service import get_listing_price_series

MIN_DATA_POINTS = 5


def predict_listing_price(db: Session, listing: ProductListing) -> PricePredictionOut:
    series = get_listing_price_series(db, listing.id)
    days_of_history = _days_span(series)

    if len(series) < MIN_DATA_POINTS:
        return PricePredictionOut(
            listing_id=listing.id,
            retailer=listing.retailer,
            currency=listing.currency,
            current_price=listing.current_price,
            predicted_price=None,
            predicted_range_low=None,
            predicted_range_high=None,
            trend="INSUFFICIENT_DATA",
            confidence=None,
            days_of_history=days_of_history,
        )

    X, y, days = _build_features(series)
    model, validation_mae = _select_best_model(X, y)

    next_day = np.array([[days[-1] + 1]])
    predicted_price = max(0.0, float(model.predict(next_day)[0]))

    current_price = series[-1].price
    margin = max(validation_mae, current_price * 0.02)  # never a zero-width range
    range_low = round(max(0.0, predicted_price - margin), 2)
    range_high = round(predicted_price + margin, 2)

    if predicted_price < current_price * 0.98:
        trend = "DOWN"
    elif predicted_price > current_price * 1.02:
        trend = "UP"
    else:
        trend = "STABLE"

    relative_error = (validation_mae / current_price) if current_price else 1.0
    confidence = round(max(0.0, min(1.0, 1 - relative_error)), 2)

    return PricePredictionOut(
        listing_id=listing.id,
        retailer=listing.retailer,
        currency=listing.currency,
        current_price=current_price,
        predicted_price=round(predicted_price, 2),
        predicted_range_low=range_low,
        predicted_range_high=range_high,
        trend=trend,
        confidence=confidence,
        days_of_history=days_of_history,
    )


def _build_features(series: list[PriceHistory]) -> tuple[np.ndarray, np.ndarray, list[float]]:
    first_ts = series[0].collected_at
    days = [(row.collected_at - first_ts).total_seconds() / 86400 for row in series]
    X = np.array(days).reshape(-1, 1)
    y = np.array([row.price for row in series])
    return X, y, days


def _select_best_model(X: np.ndarray, y: np.ndarray):
    """Holds out the most recent point, trains both candidate models on
    everything before it, and keeps whichever predicts that held-out point
    more accurately — then refits the winner on the full series."""
    candidates = {
        "linear": LinearRegression(),
        "forest": RandomForestRegressor(n_estimators=100, max_depth=4, random_state=42),
    }

    X_train, y_train = X[:-1], y[:-1]
    X_val, y_val = X[-1:], y[-1:]

    best_name, best_mae = "linear", float("inf")
    for name, candidate in candidates.items():
        candidate.fit(X_train, y_train)
        prediction = candidate.predict(X_val)
        mae = float(mean_absolute_error(y_val, prediction))
        if mae < best_mae:
            best_name, best_mae = name, mae

    final_model = type(candidates[best_name])(**candidates[best_name].get_params())
    final_model.fit(X, y)
    return final_model, best_mae


def _days_span(series: list[PriceHistory]) -> int:
    if len(series) < 2:
        return 0
    return int((series[-1].collected_at - series[0].collected_at).total_seconds() // 86400)
