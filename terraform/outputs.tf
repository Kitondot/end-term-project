output "postgres_container" {
  description = "PostgreSQL container ID"
  value       = docker_container.postgres.id
}

output "prometheus_url" {
  description = "Prometheus URL"
  value       = "http://localhost:${var.prometheus_port}"
}

output "grafana_url" {
  description = "Grafana URL"
  value       = "http://localhost:${var.grafana_port}"
}

output "network_name" {
  description = "Created network name"
  value       = docker_network.app_network.name
}