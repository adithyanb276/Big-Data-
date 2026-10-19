# Optional AWS S3 Setup

Cloud mode uploads generated Parquet partitions to an existing bucket. It does not create buckets, IAM policies, or other resources. AWS usage is not required locally and was not tested against a live account.

1. An administrator provisions a private S3 bucket with encryption, public access blocked, and lifecycle/cost controls appropriate to the capstone.
2. Assign the workload an IAM role where possible. Otherwise supply temporary credentials through the AWS credential chain, never through committed `.env` or source code.
3. Scope access to the exact bucket and `bronze/events/*` prefix. Minimum operations for the current uploader are `s3:PutObject` and `s3:GetObject`/`s3:HeadObject` for idempotency checks. Add KMS permissions only if the bucket uses a customer-managed key.
4. Set `STREAMPULSE_MODE=cloud`, `STREAMPULSE_S3_BUCKET`, `STREAMPULSE_S3_PREFIX=bronze/events`, and `AWS_DEFAULT_REGION` in the runtime environment.
5. Check `aws sts get-caller-identity` and a small authorized upload before running bulk data.

S3 keys use `bronze/events/dt=YYYY-MM-DD/hr=HH/<content-derived-id>.parquet`; a JSON sidecar records batch identity and record count. SDK retries use exponential backoff. No public ACL is applied. Review organization policies and expected storage/request charges before use. Cloud integration and IAM behavior are unverified until tested in the team's account.