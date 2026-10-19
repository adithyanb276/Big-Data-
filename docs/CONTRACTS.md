# StreamPulse Data Contracts

The original root-level contract is retained at [../CONTRACTS.md](../CONTRACTS.md). Version 1.1 clarifies nullability, units, calculations, and output names.

## Contract A: Bronze Events

Required fields: `event_id:string`, `user_id:int64`, `movie_id:int64`, `session_id:string`, `event_type:string`, `position_ms:int64`, `duration_ms:int64`, `bitrate:double` (Kbps), `buffer_ms:int64`, `device:string`, `app_version:string`, `event_ts:timestamp`. Valid Silver records are non-null; positions and buffer durations are non-negative, duration is positive, and position does not exceed duration. `event_type` is one of `play`, `pause`, `seek`, `buffer`, `complete`. Bronze preserves invalid inputs for reporting.

## Contract B: Gold

- `recommendations`: `user_id:int64, rank:int32, movie_id:int64, score:double, recommendation_source:string`. Rank begins at 1. Source is `als` or `popularity`; score is a ranking strength, not a probability.
- `qos_5min`: `window_start:timestamp, device:string, completion_rate:double, rebuffer_ratio:double, avg_bitrate:double, error_rate:double`.
- `completion_by_title`: `movie_id:int64, views:int64, avg_completion:double, drop_off_point:double`.
- `device_distribution`: `date:date, device:string, sessions:int64, distribution:double`.
- `dau`: `date:date, daily_active_users:int64`.
- `churn_risk`: `user_id:int64, risk_score:double, risk_category:string, contributing_indicators:string`.
- `completion_funnel`: `movie_id:int64, plays:int64, pauses:int64, completions:int64`.
- `analytics_summary`: `total_events:int64, total_sessions:int64, active_users:int64, avg_buffer_ms:double, completion_rate:double`.

Five-minute QoS completion = complete event count / play event count (zero if no plays); rebuffer ratio = sum(buffer milliseconds) / sum(duration milliseconds); error rate = invalid Bronze rows / raw batch rows. Title completion is the average of each session's max playback fraction. Device distribution is that device's session count / all session counts on its date. DAU counts distinct users per event date. Churn is an unvalidated engagement heuristic. Spark micro-batches include late records when processed; no streaming watermark semantics are claimed.

Logical keys: event id; (`window_start`,`device`); movie id for title/funnel; (`date`,`device`); date for DAU; user id for churn; (`user_id`,`rank`) for recommendations.