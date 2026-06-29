terraform {
  required_version = ">= 1.9"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  # State is local + gitignored: a single operator provisions this PoC, so a
  # remote backend's only benefit (multi-operator locking) doesn't apply yet.
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Data lake: holds bronze JSON + silver Parquet. BigQuery external tables read
# the silver/ prefix in place (zero-copy), so this bucket is the source of truth.
resource "google_storage_bucket" "lake" {
  name     = var.bucket_name
  project  = var.project_id
  location = var.region

  uniform_bucket_level_access = true       # IAM-only access; no legacy object ACLs
  public_access_prevention    = "enforced" # bucket can never be made public

  versioning {
    enabled = true # retain prior versions on overwrite/delete
  }

  # No encryption block => Google-managed AES-256 at rest (default). CMEK is
  # deliberately omitted: the data is public NBA tracking, not sensitive.

  # force_destroy stays false: `terraform destroy` will refuse a non-empty
  # bucket, guarding against an accidental data wipe.

  labels = {
    managed_by = "terraform"
    project    = "nba-data-architecture"
    layer      = "lake"
  }
}

# Datasets MUST share the bucket's location for external tables to read it.
resource "google_bigquery_dataset" "silver" {
  dataset_id  = "nba_silver"
  project     = var.project_id
  location    = var.region
  description = "Silver layer: conformed tracking + PBP as external tables over GCS Parquet."

  labels = {
    managed_by = "terraform"
    layer      = "silver"
  }
}

resource "google_bigquery_dataset" "gold" {
  dataset_id  = "nba_gold"
  project     = var.project_id
  location    = var.region
  description = "Gold layer: denormalized serving marts (events_with_location)."

  labels = {
    managed_by = "terraform"
    layer      = "gold"
  }
}
