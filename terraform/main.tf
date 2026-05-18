terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {
  host = "npipe:////./pipe/docker_engine"
}

resource "docker_network" "app_network" {
  name = var.network_name
}

resource "docker_image" "postgres" {
  name         = "postgres:15-alpine"
  keep_locally = false
}

resource "docker_container" "postgres" {
  image   = docker_image.postgres.image_id
  name    = "tf-postgres"
  restart = "always"

  env = [
    "POSTGRES_USER=${var.db_user}",
    "POSTGRES_PASSWORD=${var.db_password}",
    "POSTGRES_DB=maindb"
  ]

  ports {
    internal = 5432
    external = var.postgres_port
  }

  networks_advanced {
    name = docker_network.app_network.name
  }
}

resource "docker_image" "prometheus" {
  name         = "prom/prometheus:latest"
  keep_locally = false
}

resource "docker_container" "prometheus" {
  image   = docker_image.prometheus.image_id
  name    = "tf-prometheus"
  restart = "always"

  ports {
    internal = 9090
    external = var.prometheus_port
  }

  networks_advanced {
    name = docker_network.app_network.name
  }
}

resource "docker_image" "grafana" {
  name         = "grafana/grafana:latest"
  keep_locally = false
}

resource "docker_container" "grafana" {
  image   = docker_image.grafana.image_id
  name    = "tf-grafana"
  restart = "always"

  env = [
    "GF_SECURITY_ADMIN_USER=${var.grafana_user}",
    "GF_SECURITY_ADMIN_PASSWORD=${var.grafana_password}"
  ]

  ports {
    internal = 3000
    external = var.grafana_port
  }

  networks_advanced {
    name = docker_network.app_network.name
  }

  depends_on = [docker_container.prometheus]
}