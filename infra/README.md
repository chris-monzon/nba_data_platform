# infra/ — Terraform

Provisions the cloud foundation for the platform as code:

- **GCS bucket** `nba-data-architecture-lake` (`us-central1`) — the data lake. Locked down: uniform bucket-level access, public access prevention enforced, versioning on, Google-managed encryption.
- **BigQuery datasets** `nba_silver`, `nba_gold` (`us-central1`, must match the bucket).

External tables (defined in `transform/silver_tracking.sql`) read the bucket's Parquet in place.

## Reproduce

```bash
gcloud config set project nba-data-architecture   # point CLIs at the right project
cd infra
terraform init      # download the google provider
terraform plan      # preview changes
terraform apply     # create the resources
```

State is local (`terraform.tfstate`, gitignored). One operator provisions this; migrate to a remote GCS backend if infra work becomes shared.
