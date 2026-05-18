variable "docker_host" {
  description = "Docker host"
  type        = string
  default     = "npipe:////./pipe/docker_engine"
}

variable "network_name" {
  description = "Docker network name"
  type        = string
  default     = "tf-app-net"
}

variable "db_user" {
  description = "PostgreSQL username"
  type        = string
  default     = "tfuser"
}

variable "db_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
  default     = "tfpassword"
}

variable "postgres_port" {
  description = "PostgreSQL external port"
  type        = number
  default     = 5433
}

variable "prometheus_port" {
  description = "Prometheus external port"
  type        = number
  default     = 9091
}

variable "grafana_port" {
  description = "Grafana external port"
  type        = number
  default     = 3001
}

variable "grafana_user" {
  description = "Grafana admin username"
  type        = string
  default     = "admin"
}

variable "grafana_password" {
  description = "Grafana admin password"
  type        = string
  sensitive   = true
  default     = "grafana123"
}