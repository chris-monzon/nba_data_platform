output "bucket_url" {
  description = "gs:// URL of the data-lake bucket."
  value       = google_storage_bucket.lake.url
}

output "silver_dataset" {
  description = "Silver dataset id."
  value       = google_bigquery_dataset.silver.dataset_id
}

output "gold_dataset" {
  description = "Gold dataset id."
  value       = google_bigquery_dataset.gold.dataset_id
}
