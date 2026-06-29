variable "project_id" {
  description = "GCP project ID."
  type        = string
  default     = "nba-data-architecture"
}

variable "region" {
  description = "Region for the lake bucket AND BigQuery datasets. They must match for external tables to read the bucket."
  type        = string
  default     = "us-central1" # US Midwest (Council Bluffs, Iowa)
}

variable "bucket_name" {
  description = "Globally-unique name for the GCS data-lake bucket."
  type        = string
  default     = "nba-data-architecture-lake"
}
