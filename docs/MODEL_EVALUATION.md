# Recommendation Method and Evaluation

## Interactions

Each user/movie pair is aggregated. `complete` contributes 2.0; other viewing events contribute `position_ms / duration_ms`; the aggregate is floored at 0.001 to satisfy implicit ALS's non-negative positive-strength input. This is a heuristic interaction strength, not a rating or preference probability.

## Training and ranking

Spark MLlib `ALS` uses `implicitPrefs=true`, configurable `rank`, `regParam`, `alpha`, and `maxIter`. Interactions are randomly split 80/20 with a configurable seed. Training recommendations exclude known training pairs; users without ALS recommendations receive the most popular unseen items. The exported `recommendations` table includes rank, score, and `recommendation_source` (`als` or `popularity`). Scores from the two paths have different scales and must not be compared as probabilities.

## Metrics

Precision@K is relevant held-out items in top K divided by K, macro-averaged over evaluated users. NDCG@K discounts each relevant ranked item by `log2(rank + 1)` and normalizes by the ideal ranking, then macro-averages. The implementation computes metrics from held-out positives and model top-K results. The small unit test validates the metric arithmetic only; actual model metrics have not been measured in this environment because Java is unavailable. Do not report a benchmark until `model_evaluation.json` is produced from a successful full run.

## Known limitations

Random interaction splitting can put a user's same-title interaction in train and test when repeated events exist; interactions are aggregated before splitting, so each user/item pair is in one split. There is no temporal holdout or hyperparameter search. Cold users and sparse users require the documented popularity fallback. The synthetic domain does not establish real viewer preferences.