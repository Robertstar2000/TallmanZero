#!/bin/bash
# =============================================================================
# Agent Zero - Docker Entrypoint Script
# =============================================================================
# This script handles runtime bootstrapping for both Docker Desktop and
# Docker Swarm deployments. It performs environment synchronization,
# initialization tasks, and starts the main application.
#
# Usage: Called automatically as container entrypoint
# =============================================================================

set -e

echo "=========================================="
echo "Agent Zero Container Initialization"
echo "=========================================="
echo "Timestamp: $(date)"
echo "Environment: ${NODE_ENV:-development}"
echo "Branch: ${BRANCH:-main}"
echo ""

# -----------------------------------------------------------------------------
# Environment Detection
# -----------------------------------------------------------------------------
if [ -n "$POSTGRES_HOST" ]; then
    echo "[ENV] Running in SWARM/PRODUCTION mode (PostgreSQL detected)"
    DEPLOYMENT_MODE="swarm"
else
    echo "[ENV] Running in LOCAL/DEVELOPMENT mode (SQLite)"
    DEPLOYMENT_MODE="local"
fi

# -----------------------------------------------------------------------------
# Directory Initialization
# -----------------------------------------------------------------------------
echo "[INIT] Ensuring required directories exist..."

# Create data directories if they don't exist
mkdir -p /a0/logs
mkdir -p /a0/memory
mkdir -p /a0/knowledge
mkdir -p /a0/projects
mkdir -p /a0/tmp

# Set permissions
chmod -R 755 /a0

echo "[INIT] Data directory structure verified at /a0"

# -----------------------------------------------------------------------------
# Configuration Synchronization
# -----------------------------------------------------------------------------
if [ -f "/app/agent-zero/conf/config.json" ]; then
    echo "[CONFIG] Custom configuration found, using it..."
else
    echo "[CONFIG] No custom configuration, using defaults..."
fi

# -----------------------------------------------------------------------------
# Environment-Specific Setup
# -----------------------------------------------------------------------------
if [ "$DEPLOYMENT_MODE" = "swarm" ]; then
    echo "[SWARM] Performing production initialization..."
    
    # Wait for database availability (if PostgreSQL is configured)
    if [ -n "$POSTGRES_HOST" ]; then
        echo "[SWARM] Waiting for PostgreSQL at $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
        max_retries=30
        retry_count=0
        
        while ! nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}" 2>/dev/null; do
            retry_count=$((retry_count + 1))
            if [ $retry_count -ge $max_retries ]; then
                echo "[ERROR] PostgreSQL not available after $max_retries attempts"
                break
            fi
            echo "[SWARM] Waiting for database... (attempt $retry_count/$max_retries)"
            sleep 2
        done
        
        if [ $retry_count -lt $max_retries ]; then
            echo "[SWARM] PostgreSQL is available!"
        fi
    fi
    
    # Log swarm-specific information
    echo "[SWARM] Container ID: $(hostname)"
    echo "[SWARM] Node: ${NODE_NAME:-unknown}"
    
else
    echo "[LOCAL] Performing development initialization..."
    
    # Development-specific tasks
    if [ -d "/app/agent-zero" ]; then
        echo "[LOCAL] Source code mounted at /app/agent-zero"
    fi
fi

# -----------------------------------------------------------------------------
# Health Check Verification
# -----------------------------------------------------------------------------
echo "[INIT] Initialization complete. Starting health check verification..."

# Create a simple health marker
echo "$(date): Container initialized successfully" >> /a0/logs/startup.log

# -----------------------------------------------------------------------------
# Start Main Application
# -----------------------------------------------------------------------------
echo ""
echo "=========================================="
echo "Starting Agent Zero Application"
echo "=========================================="
echo ""

# Execute the original entrypoint or command
if [ -f "/exe/initialize.sh" ]; then
    exec /exe/initialize.sh "$@"
elif [ -n "$1" ]; then
    exec "$@"
else
    echo "[ERROR] No entrypoint command found!"
    exit 1
fi
