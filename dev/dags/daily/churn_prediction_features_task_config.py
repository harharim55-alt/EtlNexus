"""Churn Prediction Features — Daily ML feature engineering."""

needs = ["customer_360_enrichment"]
prefers = ["mixpanel_user_events"]
writes_to = [
    "churn_prediction_features",
    "churn_prediction_features_health_scores",
    "churn_prediction_features_segments",
    "churn_prediction_features_weekly",
]
