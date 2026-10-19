# Separate Frontend and Backend Deployment

Deployment is prepared, not executed. Static hosting, backend compute, persistent disks, Spark/Databricks, S3, network transfer, and storage may incur charges. Review current provider pricing before provisioning; this project creates no cloud resources.

## Frontend on Vercel

1. Import the repository and set the Vercel project root to `frontend/`.
2. `frontend/vercel.json` configures the Vite build, `dist` output, and SPA fallback.
3. Set `VITE_API_BASE_URL` to the public HTTPS FastAPI origin without a trailing slash, then deploy. No AWS credentials or data paths belong in the browser bundle.

## Backend on Render

1. Create a Render Blueprint from root `render.yaml` or configure a Python service with the same build and start commands. It uses `requirements-api.txt`, a deliberately slim serving environment without Spark.
2. Set `STREAMPULSE_CORS_ORIGINS` to the exact deployed frontend origin.
3. Attach persistent disk storage. Place the complete Gold Parquet tree and `movie_catalogue.parquet` at `STREAMPULSE_GOLD_DIR` and `STREAMPULSE_CATALOGUE_PATH`.
4. Configure `/api/health` as the health check. HTTP 200 with `status: degraded` means the process is live but Gold files are absent.

The persistent disk and continuously running web process generally require a paid plan; pricing varies by region, memory, storage, traffic, and provider plan. FastAPI's DuckDB queries use local files; they do not fetch Gold from S3. A separate batch/operations process must run Spark/ALS and publish Gold outputs to persistent backend storage. Keep Spark jobs out of API requests. Large recommendation training needs separately provisioned batch compute or Databricks and can incur significant charges.

## Optional AWS

S3 Bronze ingestion remains optional; see [AWS_SETUP.md](AWS_SETUP.md). Use scoped workload roles for Bronze writes and separate processing/publishing access. Keep secrets in the deployment secret manager. The current API does not query S3 directly; secure batch processing must sync Gold data onto backend storage. Local mode remains credential-free.# Separate Frontend and Backend Deployment

Deployment is prepared, not executed. These providers and persistent storage can incur charges; review their current pricing before provisioning. No resources have been created.

## Frontend: Vercel static site

1. Import the repository and set the project root to `frontend/`; `frontend/vercel.json` configures Vite build output and SPA fallback.
2. Set `VITE_API_BASE_URL` to the public HTTPS URL of the FastAPI service, without a trailing slash.
3. Deploy the static build. No AWS credentials or local data path is present in the client bundle.

## Backend: Render web service

1. Create a Render Blueprint from `render.yaml` or configure a Python web service with its build/start commands and health check.
2. Supply `STREAMPULSE_CORS_ORIGINS` as the exact deployed frontend origin (comma-separated only for explicitly trusted origins).
3. Attach persistent disk storage. Copy/sync `data/gold/` and `movie_catalogue.parquet` into the configured disk paths before marking the service ready.
4. Check `https://<api-host>/api/health`; `status: degraded` means the process is alive but Gold datasets are not present.

The persistent disk is part of the Render deployment configuration and usually requires a paid service tier; pricing depends on provider, region, storage, traffic, and current plans. This repository does not sync Gold data from S3 at runtime. The batch job/team must export Gold Parquet and publish it to backend persistent storage, or implement a separately secured sync job. Do not run PySpark/ALS in request handlers. For larger Spark jobs, use an appropriately provisioned batch/Databricks environment and include its compute/storage costs in the project budget.

## Optional AWS data flow

S3 Bronze ingestion is optional and documented in [AWS_SETUP.md](AWS_SETUP.md). The API's DuckDB reader currently expects local Gold paths; it does not accept bucket credentials or query S3 directly. A production setup can run Spark in an authorized batch environment, write Gold outputs, then sync those outputs to the backend disk. IAM roles should be scoped separately for ingestion, processing, and serving; keep all credentials in the hosting secret manager. S3, Spark/Databricks, Render persistent disks, networking, and egress may incur charges. Local development remains credential-free.