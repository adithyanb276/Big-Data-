# Data Contracts (the APIs between us)

These are **frozen in Week 1**. Build against them. Any change = announce + version bump.

## Contract A — Bronze event record  (Fidal → Lubaba)

One row per telemetry event, stored as Parquet in `s3://streampulse-lake/bronze/events/dt=.../hr=.../`.

| Field | Type | Notes |
|---|---|---|
| `event_id` | string (uuid) | Primary key; Silver deduplicates on this |
| `user_id` | long | ~10k users |
| `movie_id` | long | ~1k titles |
| `session_id` | string | Groups events into a viewing session |
| `event_type` | string | `play` \| `pause` \| `seek` \| `buffer` \| `complete` |
| `position_ms` | long | Playback position |
| `duration_ms` | long | Total title length → completion % |
| `bitrate` | long | QoS input |
| `buffer_ms` | long | Rebuffering time (QoS) |
| `device` | string | e.g. `web`, `ios`, `android`, `tv` |
| `app_version` | string | Dimensional attribute |
| `event_ts` | timestamp | Event time; basis for windows + partitions |

## Contract B — Gold outputs  (Lubaba → Adithyan)

**`recommendations`** — top-N per user, ready to render as a slate:

| Field | Type | Notes |
|---|---|---|
| `user_id` | long | |
| `rank` | int | 1..N |
| `movie_id` | long | |
| `score` | double | ALS predicted score |

**Analytics tables** consumed by the Executive Portal:

- `qos_5min` — `window_start, device, completion_rate, rebuffer_ratio, avg_bitrate, error_rate`
- `completion_by_title` — `movie_id, views, avg_completion, drop_off_point`
- `device_distribution` — `date, device, sessions`
- `dau` — `date, active_users`
- `churn_risk` — `user_id, risk_score`

## Version

- v1 — initial freeze (2026-10-12). Update this line on any change.
