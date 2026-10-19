# FastAPI REST API

All endpoints are read-only and query precomputed Parquet through `GoldStore`/DuckDB. No route starts Spark. Missing Gold tables return empty `data`, `count: 0`, and `data_available: false`.

| Route | Result |
|---|---|
| `GET /api/health` | Process status, data mode, sample-data flag, and present Gold tables |
| `GET /api/overview` | Total events/sessions, most recent DAU, completed event count, completion rate, average buffer milliseconds |
| `GET /api/analytics/qos` | `qos_5min`, optional `device`, `start_date`, `end_date`; max 5,000 rows |
| `GET /api/analytics/content` | Content completion and catalogue metadata when present |
| `GET /api/analytics/devices` | Device session distribution, optional date filters |
| `GET /api/analytics/users` | Daily active-user series |
| `GET /api/users` | Distinct available user IDs |
| `GET /api/recommendations/{user_id}` | Precomputed slate; observed-title popularity fallback if available; otherwise unavailable status |

Table endpoints return `{ "data": [], "count": 0, "data_available": false, "sample_data": false }` when data is absent. Recommendation responses add `user_id` and `status` (`available`, `popularity_fallback`, or `unavailable`). A popularity fallback is ranked from observed `completion_by_title.views`; its normalized `score` is a relative view count, not a probability. `sample_data` is an explicit runtime flag (`STREAMPULSE_SAMPLE_DATA`), not an inference that arbitrary data is production or sample.

Interactive docs: `/docs`. CORS origins are set with comma-separated `STREAMPULSE_CORS_ORIGINS`. Only `GET` and preflight are enabled.