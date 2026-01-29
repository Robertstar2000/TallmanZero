# =============================================================================
# Agent Zero - Local Development Makefile
# =============================================================================
# This Makefile provides convenient commands for local Docker development.
# For Swarm deployment, use the Makefile at /var/data/config/
#
# Usage:
#   make help      - Show available commands
#   make build     - Build Docker images
#   make dev       - Start development environment
#   make stop      - Stop all containers
# =============================================================================

.PHONY: help build dev stop logs clean rebuild shell test

# Default target
help:
	@echo "==========================================="
	@echo "Agent Zero - Development Commands"
	@echo "==========================================="
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Development:"
	@echo "  build      Build Docker images"
	@echo "  dev        Start development environment"
	@echo "  stop       Stop all containers"
	@echo "  logs       View container logs"
	@echo "  shell      Open shell in container"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean      Remove containers and volumes"
	@echo "  rebuild    Clean rebuild (removes all data)"
	@echo "  prune      Remove unused Docker resources"
	@echo ""
	@echo "Testing:"
	@echo "  test       Run tests"
	@echo "  lint       Run linter"
	@echo ""
	@echo "Deployment Info:"
	@echo "  info       Show deployment information"
	@echo ""

# -----------------------------------------------------------------------------
# Development Commands
# -----------------------------------------------------------------------------

# Build Docker images
build:
	@echo "Building Docker images..."
	docker-compose build

# Start development environment
dev:
	@echo "Starting development environment..."
	docker-compose up --build

# Start in background
dev-bg:
	@echo "Starting development environment in background..."
	docker-compose up -d --build
	@echo ""
	@echo "Agent Zero is running at: http://localhost:50001"
	@echo "View logs with: make logs"

# Stop all containers
stop:
	@echo "Stopping containers..."
	docker-compose down

# View logs
logs:
	docker-compose logs -f agent-zero

# Open shell in container
shell:
	docker-compose exec agent-zero /bin/bash

# -----------------------------------------------------------------------------
# Maintenance Commands
# -----------------------------------------------------------------------------

# Remove containers and volumes
clean:
	@echo "Stopping and removing containers..."
	docker-compose down -v
	@echo "Removing orphan containers..."
	docker-compose down --remove-orphans

# Full rebuild (removes all data)
rebuild: clean
	@echo "Rebuilding from scratch..."
	docker-compose build --no-cache
	docker-compose up -d
	@echo ""
	@echo "Rebuild complete. Access at: http://localhost:50001"

# Remove unused Docker resources
prune:
	@echo "Pruning unused Docker resources..."
	docker system prune -f
	docker volume prune -f

# -----------------------------------------------------------------------------
# Testing Commands
# -----------------------------------------------------------------------------

test:
	@echo "Running tests..."
	docker-compose exec agent-zero python -m pytest tests/

lint:
	@echo "Running linter..."
	docker-compose exec agent-zero python -m flake8 .

# -----------------------------------------------------------------------------
# Information Commands
# -----------------------------------------------------------------------------

info:
	@echo "==========================================="
	@echo "Agent Zero - Deployment Information"
	@echo "==========================================="
	@echo ""
	@echo "Local Development:"
	@echo "  Compose File: docker-compose.yml"
	@echo "  Web UI:       http://localhost:50001"
	@echo "  SSH:          localhost:50022"
	@echo ""
	@echo "Docker Swarm Production:"
	@echo "  Compose File: docker-compose-swarm.yml"
	@echo "  Web UI:       https://agentzero.swarm.tallmanequipment.com"
	@echo "  Cluster VIP:  10.10.20.65"
	@echo ""
	@echo "Documentation:"
	@echo "  DEPLOYMENT.md - Full deployment guide"
	@echo "  swarm.md     - Swarm platform docs"
	@echo ""

# -----------------------------------------------------------------------------
# Swarm Deployment (for reference - use on Swarm nodes)
# -----------------------------------------------------------------------------

# Note: These commands are meant to be run on a Swarm manager node
# They are included here for reference only

swarm-deploy:
	@echo "NOTE: Run this on a Swarm manager node (10.10.20.36)"
	@echo "  ssh 10.10.20.36"
	@echo "  cd /var/data/config"
	@echo "  make deploy STACK=agentzero"

swarm-status:
	@echo "NOTE: Run this on a Swarm manager node"
	@echo "  docker stack services agentzero"
	@echo "  docker service logs agentzero_agent-zero"
