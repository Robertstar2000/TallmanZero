# TallmanZero - Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Docker Desktop Installation](#docker-desktop-installation)
4. [Docker Swarm Installation](#docker-swarm-installation)
5. [Configuration](#configuration)
6. [Troubleshooting](#troubleshooting)

---

## Overview

TallmanZero uses the official pre-built Docker image `agent0ai/agent-zero:latest` for both development and production deployments. No building required!

### Deployment Options

| Environment | Compose File | Use Case | Access URL |
|-------------|--------------|----------|------------|
| **Docker Desktop** | `docker-compose.yml` | Local development | http://localhost:50001 |
| **Docker Swarm** | `docker-compose-swarm.yml` | Production cluster | https://agentzero.swarm.tallmanequipment.com |

### Master Registry

**Docker Hub**: https://hub.docker.com/r/agent0ai/agent-zero

**GitHub**: https://github.com/agent0ai/agent-zero

---

## Quick Start

### Docker Desktop (One Command!)

```powershell
# Pull and run TallmanZero
docker run -d -p 50001:80 -v agent-zero-data:/a0 --name agent-zero agent0ai/agent-zero:latest

# Open in browser
start http://localhost:50001
```

### Docker Swarm (Production)

```bash
# SSH to Swarm manager and deploy
ssh 10.10.20.36
cd /var/data/config
make deploy STACK=agentzero
```

---

## Docker Desktop Installation

### Prerequisites

- **Docker Desktop** installed and running
  - [Download for Windows](https://www.docker.com/products/docker-desktop/)
  - [Download for Mac](https://www.docker.com/products/docker-desktop/)
- At least **4GB RAM** allocated to Docker

### Method 1: Using Docker Compose (Recommended)

1. **Navigate to the project directory:**

   ```powershell
   cd C:\Users\rober\TallmanAgentZero\agent-zero
   ```

2. **Start TallmanZero:**

   ```powershell
   docker-compose up -d
   ```

3. **Verify it's running:**

   ```powershell
   docker ps
   ```

4. **Access the Web UI:**

   Open http://localhost:50001 in your browser

5. **View logs (optional):**

   ```powershell
   docker-compose logs -f agent-zero
   ```

### Method 2: Using Docker Run

```powershell
# Pull the latest image
docker pull agent0ai/agent-zero:latest

# Run with persistent data
docker run -d `
  --name agent-zero `
  -p 50001:80 `
  -v agent-zero-data:/a0 `
  --restart unless-stopped `
  agent0ai/agent-zero:latest

# Access at http://localhost:50001
```

### Stopping and Removing

```powershell
# Stop the container
docker-compose down

# Stop and remove data (clean slate)
docker-compose down -v
```

### Updating to Latest Version

```powershell
# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d
```

---

## Docker Swarm Installation

### Prerequisites

- Access to the Tallman Docker Swarm cluster
- SSH access to a manager node (10.10.20.36, 10.10.20.61, or 10.10.20.63)
- DNS configured for the application domain

### Cluster Infrastructure

| Component | Address |
|-----------|---------|
| Manager Node 1 | 10.10.20.36 |
| Manager Node 2 | 10.10.20.61 |
| Manager Node 3 | 10.10.20.63 |
| Storage Server (NFS) | 10.10.20.64 |
| Virtual IP (Keepalived) | 10.10.20.65 |

### Deployment Steps

1. **SSH to a manager node:**

   ```bash
   ssh 10.10.20.36
   ```

2. **Create the data directory:**

   ```bash
   sudo mkdir -p /var/data/agentzero/data
   sudo chmod 755 /var/data/agentzero
   ```

3. **Copy the Swarm compose file:**

   ```bash
   # From your local machine, copy the file:
   scp docker-compose-swarm.yml 10.10.20.36:/var/data/config/docker-compose-agentzero.yaml
   
   # Or on the server, create it directly
   cd /var/data/config
   nano docker-compose-agentzero.yaml
   # Paste the contents of docker-compose-swarm.yml
   ```

4. **Configure DNS:**

   Point `agentzero.swarm.tallmanequipment.com` to `10.10.20.65` in AWS Route 53.

5. **Deploy the stack:**

   ```bash
   cd /var/data/config
   make deploy STACK=agentzero
   ```

6. **Verify deployment:**

   ```bash
   # Check service status
   docker stack services agentzero
   
   # View logs
   docker service logs agentzero_agent-zero
   ```

7. **Access the application:**

   Open https://agentzero.swarm.tallmanequipment.com

### Stack Management Commands

| Command | Description |
|---------|-------------|
| `make deploy STACK=agentzero` | Deploy or update the stack |
| `make update STACK=agentzero` | Force redeploy with latest image |
| `make destroy STACK=agentzero` | Remove the stack |
| `docker stack services agentzero` | View service status |
| `docker service logs agentzero_agent-zero` | View logs |

### Updating the Application

```bash
# Pull latest image on all nodes
docker pull agent0ai/agent-zero:latest

# Force update the service
make update STACK=agentzero
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TZ` | Timezone | `America/New_York` |

### Data Persistence

| Environment | Volume/Mount | Purpose |
|-------------|--------------|---------|
| Docker Desktop | `agent-zero-data:/a0` | All application data |
| Docker Swarm | `/var/data/agentzero/data:/a0` | NFS shared storage |

### Backup

**Docker Desktop:**
```powershell
# Create backup
docker run --rm -v agent-zero-data:/data -v ${PWD}:/backup alpine tar cvf /backup/agent-zero-backup.tar /data
```

**Docker Swarm:**
```bash
# Backup NFS data
tar -czvf /var/data/backups/agentzero-$(date +%Y%m%d).tar.gz /var/data/agentzero/
```

---

## Troubleshooting

### Docker Desktop Issues

**Container won't start:**
```powershell
# Check for port conflicts
netstat -ano | findstr :50001

# View container logs
docker logs agent-zero

# Remove and recreate
docker-compose down
docker-compose up -d
```

**"Cannot connect to Docker daemon":**
- Ensure Docker Desktop is running
- Restart Docker Desktop if needed

**Image pull fails:**
```powershell
# Check Docker Hub connectivity
docker pull hello-world

# Login if needed
docker login
```

### Docker Swarm Issues

**Service won't start:**
```bash
# Check detailed status
docker service ps agentzero_agent-zero --no-trunc

# View logs
docker service logs agentzero_agent-zero
```

**Can't access via domain:**

1. Verify DNS: `nslookup agentzero.swarm.tallmanequipment.com`
2. Check Traefik: `docker service logs infra_traefik`
3. Verify network: `docker network ls | grep agentzero`

**NFS mount issues:**
```bash
# Check mount
df -h | grep /var/data

# Remount
sudo mount -a
```

### Common Fixes

| Issue | Solution |
|-------|----------|
| Port 50001 in use | Change port in docker-compose.yml or stop conflicting service |
| Out of disk space | `docker system prune -a` |
| Container keeps restarting | Check logs: `docker logs agent-zero` |
| Old image running | Pull and restart: `docker-compose pull && docker-compose up -d` |

---

## Network Access Points

### Docker Desktop (Local)

| Service | URL |
|---------|-----|
| Web UI | http://localhost:50001 |

### Docker Swarm (Production)

| Service | URL |
|---------|-----|
| TallmanZero | https://agentzero.swarm.tallmanequipment.com |
| Traefik Dashboard | https://traefik.swarm.tallmanequipment.com |
| Portainer | https://portainer.swarm.tallmanequipment.com |

---

## Related Documentation

- [Swarm Platform Guide](./swarm.md) - Full Docker Swarm platform documentation
- [TallmanZero Docs](./docs/README.md) - Application usage and development
- [Enterprise Skills](./.agent/skills/enterprise-app-foundation/SKILL.md) - Architecture patterns

---

*Last Updated: January 2026*
