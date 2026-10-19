# Data Contracts (the APIs between us)

These are **frozen in Week 1**. Build against them. Any change = announce + version bump.

## Contract A — Bronze event record  (Fidal → Lubaba)

One row per telemetry event, stored as Parquet in `s3://streampulse-lake/bronze/events/dt=.../hr=.../`.

| Field | Type | Notes |
|---|---|---|
| `event_id` | string | Required stable identifier; Silver deduplicates on this |
| `user_id` | long | ~10k users |
| `movie_id` | long | ~1k titles |
| `session_id` | string | Groups events into a viewing session |
| `event_type` | string | `play` \| `pause` \| `seek` \| `buffer` \| `complete` |
| `position_ms` | long | Milliseconds; non-negative and no greater than duration |
| `duration_ms` | long | Milliseconds; positive title length |
| `bitrate` | double | Kbps; non-negative QoS input |
| `buffer_ms` | long | Rebuffering time (QoS) |
| `device` | string | e.g. `web`, `ios`, `android`, `tv` |
| `app_version` | string | Dimensional attribute |
| `event_ts` | timestamp | Event time; basis for windows + partitions |

All fields are non-null in valid Silver rows. Bronze preserves input, including intentionally malformed/missing values used for quality tests. Supported event types: `play`, `pause`, `seek`, `buffer`, `complete`.

## Contract B — Gold outputs  (Lubaba → Adithyan)

**`recommendations`** — top-N per user, ready to render as a slate:

| Field | Type | Notes |
|---|---|---|
| `user_id` | long | |
| `rank` | int | 1..N |
| `movie_id` | long | |
| `score` | double | ALS predicted score |
| `recommendation_source` | string | `als` or `popularity`; identifies cold-start fallback |

**Analytics tables** consumed by the Executive Portal:

- `qos_5min` — `window_start, device, completion_rate, rebuffer_ratio, avg_bitrate, error_rate`
- `completion_by_title` — `movie_id, views, avg_completion, drop_off_point`
- `device_distribution` — `date, device, sessions, distribution` (device sessions / all sessions that date)
- `dau` — `date, daily_active_users`
- `churn_risk` — `user_id, risk_score, risk_category, contributing_indicators`
- `completion_funnel` — `movie_id, plays, pauses, completions`
- `analytics_summary` — `total_events, total_sessions, active_users, completion_rate`

Metric definitions: `qos_5min.completion_rate` = complete events / play events (zero if no plays); `rebuffer_ratio` = summed buffer milliseconds / summed duration milliseconds; `avg_bitrate` is Kbps; `error_rate` = invalid raw rows / raw rows in the batch. Title completion is mean per-session maximum `position_ms / duration_ms`; drop-off point is mean `1 - completion_fraction`. Invalid rows are excluded from Silver and retained in quality counts. Late records are included when their micro-batch is processed; no continuous-stream watermark behavior is claimed. Completion funnel counts events, not unique sessions.

Uniqueness: `event_id` in Silver; (`window_start`, `device`) for QoS; `movie_id` for title completion and funnel; (`date`, `device`) for device distribution; `date` for DAU; `user_id` for churn; (`user_id`, `rank`) for recommendations. Churn risk is a heuristic, not a cancellation probability. ALS score is a ranking score, not a probability.

## Version

- v1.1 — 2026-10-19. Clarified units, quality handling, metric definitions, and Gold fields while preserving responsibilities and core fields.
