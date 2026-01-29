# Tallman Chat Swarm Platform

## Table of Contents

1. [Overview](#overview)
2. [Key Concepts](#key-concepts)
3. [Infrastructure Components](#infrastructure-components)
4. [Initial Deployment](#initial-deployment)
5. [Daily Operations](#daily-operations)
6. [Deploying New Applications](#deploying-new-applications)
7. [Network Isolation Strategy](#network-isolation-strategy)
8. [Troubleshooting](#troubleshooting)

## Overview

This platform provides a container orchestration system for running applications in isolated, portable environments called "containers." Think of containers as lightweight virtual machines that package an application with everything it needs to run.

### What This Platform Provides

*   **High Availability**: 3 Docker nodes work together so if one fails, applications keep running
*   **Automatic Routing**: Traefik automatically directs web traffic to the right applications
*   **SSL Certificates**: Automatic HTTPS certificates from Let's Encrypt
*   **Easy Management**: Portainer provides a web interface for managing containers
*   **Shared Storage**: Centralized storage server accessible from all nodes

### Infrastructure Summary

*   **3 Docker Swarm Nodes** (10.10.20.36, 10.10.20.61, 10.10.20.63)
*   **1 Storage Server** (10.10.20.64)
*   **1 Virtual IP** (10.10.20.65) - Shared address that automatically moves if a node fails

## Key Concepts

### Containers

Containers are isolated packages that include an application and all its dependencies. They're like shipping containers for software - standardized, portable, and isolated from each other.

### Docker Swarm

Docker Swarm is the orchestration system that manages containers across multiple servers (nodes). It handles:

*   Distributing containers across nodes
*   Restarting failed containers
*   Load balancing traffic
*   Managing updates

### Stacks

A "stack" is a group of related containers that work together to provide a service. For example, a web application stack might include:

*   A web server container
*   A database container
*   A cache container

### Networks

Networks allow containers to communicate with each other. Containers on the same network can talk to each other, while containers on different networks are isolated.

### Services

A service is a container (or group of identical containers) running in the swarm. The swarm ensures the service stays running and can scale it to multiple copies.

## Infrastructure Components

### 1. Traefik (Ingress Controller)

**What it does:** Traefik is the "front door" for all web traffic. It automatically routes incoming requests to the correct application.

**Key Features:**

*   Automatically discovers new applications deployed to the swarm
*   Obtains and renews SSL certificates from Let's Encrypt
*   Routes traffic based on domain names (e.g., app1.swarm.tallmanequipment.com → App 1)
*   Uses AWS Route 53 for DNS validation (no need to open port 80 for validation)

**Access:** https://traefik.swarm.tallmanequipment.com

**Configuration:** `/var/data/config/traefik.toml`

### 2. Portainer (Management Interface)

**What it does:** Portainer provides a web-based interface for managing the Docker Swarm without using command-line tools.

**Key Features:**

*   View all running containers and services
*   Deploy new stacks through a web interface
*   View logs and container statistics
*   Manage networks, volumes, and configurations

**Access:** https://portainer.swarm.tallmanequipment.com

**Data Location:** `/var/data/portainer`

### 3. Keepalived (High Availability)

**What it does:** Keepalived manages the Virtual IP (10.10.20.65) that provides a single entry point to the cluster. If the primary node fails, another node automatically takes over the IP.

**How it works:**

*   Node 1 is the primary (priority 100)
*   Node 2 is first backup (priority 90)
*   Node 3 is second backup (priority 80)
*   The node with the highest priority that's online gets the Virtual IP

### 4. NFS Storage Server

**What it does:** Provides shared storage accessible from all Docker nodes. This ensures data persists even if containers move between nodes.

**Mount Point:** `/var/data` (on all nodes)

**What's stored here:**

*   Application data
*   Configuration files
*   Traefik certificates
*   Portainer data
*   Stack deployment files

## Initial Deployment

The initial deployment is automated using Ansible. While this is mostly used as a reference for the as-built environment, it may not represent future builds exactly as they need to be (for example, SSH keys are added for "gonzalo", which is my user during deployment).

The `deployment-playbook.yml` handles:

*   **User Setup**: Creates admin user with SSH key access
*   **Storage Server Setup**: Configures NFS server and exports `/var/data`
*   **Docker Node Setup**:
    *   Installs Docker and dependencies
    *   Mounts NFS storage
    *   Configures Keepalived for Virtual IP
*   **Swarm Initialization**: Creates the Docker Swarm cluster with all nodes as managers
*   **Infrastructure Deployment**: Deploys Traefik and Portainer

### Running the Deployment

```bash
ansible-playbook -i inventory.ini deployment-playbook.yml
```

### Post-Deployment Steps

1.  **Deploy Infrastructure Stack**:

    ```bash
    ssh 10.10.20.36    # or 61 or 63
    cd /var/data/config
    make deploy STACK=infra
    ```

2.  **Configure DNS**: Point these domains to 10.10.20.65:

    *   `traefik.swarm.tallmanequipment.com`
    *   `portainer.swarm.tallmanequipment.com`
    *   Any future domains that will be hosted in the environment

3.  **Access Portainer**: Visit https://portainer.swarm.tallmanequipment.com and use the credentials provided at handoff.

## Daily Operations

### Checking Cluster Status

View all nodes:

```bash
docker node ls
```

Expected output shows 3 nodes with "Ready" status and "Reachable" availability.

View all stacks:

```bash
docker stack ls
```

View services in a stack:

```bash
docker stack services <stack-name>
```

View service logs:

```bash
docker service logs <service-name>
```

### Using the Makefile

The Makefile in `/var/data/config/` simplifies stack management:

Deploy all stacks:

```bash
make deploy
```

Deploy specific stack:

```bash
make deploy STACK=infra
```

Update stack (redeploy with latest images):

```bash
make update STACK=infra
```

Remove stack:

```bash
make destroy STACK=infra
```

List available stacks:

```bash
make list
```

### Updating the Platform

To update all nodes with security patches:

```bash
ansible-playbook -i inventory.ini update-playbook.yml
```

### Rebooting Nodes

To safely reboot all nodes:

```bash
ansible-playbook -i inventory.ini reboot-playbook.yml
```

## Deploying New Applications

### Method 1: Using Portainer

1.  **Access Portainer**: https://portainer.swarm.tallmanequipment.com
2.  **Navigate to Stacks**: Click "Stacks" in the left menu
3.  **Add New Stack**: Click "+ Add stack"
4.  **Configure Stack**:
    *   Name: Choose a descriptive name (e.g., wordpress)
    *   Build method: Select "Web editor"
    *   Paste your `docker-compose.yaml` content
5.  **Deploy**: Click "Deploy the stack"

### Method 2: Using Command Line

1.  Create compose file:

    ```bash
    ssh 10.10.20.36   (or any node really)
    cd /var/data/config
    nano docker-compose-myapp.yaml
    ```

2.  Deploy using Makefile:

    ```bash
    make deploy STACK=myapp
    ```

### Example: Deploying a Web Application

Here's a complete example for deploying a simple web application:

**File**: `/var/data/config/docker-compose-webapp.yaml`

```yaml
version: '3.8'

networks:
  webapp_network:
    driver: overlay
    attachable: true
  traefik:
    external: true
    name: infra_traefik

services:
  web:
    image: nginx:latest
    networks:
      - webapp_network
      - traefik
    volumes:
      - /var/data/webapp/html:/usr/share/nginx/html:ro
    deploy:
      replicas: 2
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.webapp.rule=Host(`webapp.swarm.tallmanequipment.com`)"
        - "traefik.http.routers.webapp.entrypoints=https"
        - "traefik.http.routers.webapp.tls.certresolver=letsencrypt"
        - "traefik.http.services.webapp.loadbalancer.server.port=80"
        - "traefik.swarm.network=infra_traefik"
```

**Deploy**:

```bash
make deploy STACK=webapp
```

#### Understanding Traefik Labels

Traefik uses Docker labels to automatically configure routing:

*   `traefik.enable=true`: Tells Traefik to route traffic to this service
*   `traefik.http.routers.webapp.rule=Host(...)`: Domain name for this service
*   `traefik.http.routers.webapp.entrypoints=https`: Use HTTPS
*   `traefik.http.routers.webapp.tls.certresolver=letsencrypt`: Get SSL certificate
*   `traefik.http.services.webapp.loadbalancer.server.port=80`: Container's internal port
*   `traefik.swarm.network=infra_traefik`: Network where Traefik can reach the service

## Network Isolation Strategy

### Current Setup

Currently, all applications would connect to a single shared network (`infra_traefik`) to communicate with Traefik. This means:

*   All containers can potentially communicate with each other
*   Less isolation between different applications
*   Simpler configuration

### Recommended Future Approach: Dedicated Networks

For better security and isolation, each stack should have its own dedicated network for Traefik communication.

#### Benefits of Network Isolation

*   **Security**: Applications can't access each other's containers
*   **Stability**: Issues in one application won't affect others
*   **Compliance**: Better meets security requirements for sensitive data
*   **Troubleshooting**: Easier to diagnose network issues

### Implementation Example

**Current approach** (all stacks share one network):

```yaml
networks:
  traefik:
    external: true
    name: infra_traefik  # Shared by all stacks

services:
  myapp:
    networks:
      - traefik
```

**Recommended approach** (each stack has its own Traefik network):

```yaml
networks:
  traefik_myapp:
    driver: overlay
    attachable: true
  myapp_internal:
    driver: overlay
    attachable: true

services:
  myapp:
    networks:
      - traefik_myapp  # Dedicated network for Traefik communication
      - myapp_internal  # Private network for app components
    deploy:
      labels:
        - "traefik.swarm.network=mystack_traefik_myapp"
```

### Migration Steps

To migrate existing stacks to isolated networks:

1.  Update Traefik configuration to connect to multiple networks:

    ```yaml
    services:
      traefik:
        networks:
          - traefik
          - traefik_app1
          - traefik_app2
    ```

2.  Update each application stack to use its own network:
    *   Create a dedicated `traefik_<stackname>` network
    *   Update the `traefik.swarm.network` label
    *   Keep internal networks for inter-container communication
3.  Redeploy stacks one at a time to avoid downtime

### Network Naming Convention

Recommended naming pattern:

*   `<stackname>_traefik` - For Traefik communication
*   `<stackname>_internal` - For internal app communication
*   `<stackname>_database` - For database communication (if needed)

Example for a WordPress stack:

```yaml
networks:
  wordpress_traefik:
    driver: overlay
  wordpress_internal:
    driver: overlay

services:
  wordpress:
    networks:
      - wordpress_traefik  # Exposed to Traefik
      - wordpress_internal  # Can talk to database
    deploy:
      labels:
        - "traefik.swarm.network=wordpress_wordpress_traefik"
  
  database:
    networks:
      - wordpress_internal  # Only accessible to WordPress, not exposed
```

## Troubleshooting

### Service Won't Start

Check service status:

```bash
docker service ps <service-name> --no-trunc
```

This shows why a service failed to start (missing image, configuration errors, etc.).

View service logs:

```bash
docker service logs <service-name>
```

### Can't Access Application via Domain

Checklist:

1.  DNS points to 10.10.20.65
2.  Service has correct Traefik labels
3.  Service is connected to the correct network
4.  Service is running: `docker service ls`

Check Traefik logs:

```bash
docker service logs infra_traefik
```

Verify Traefik can see the service: Visit https://traefik.swarm.tallmanequipment.com and check the dashboard.

### Node is Down

Check node status:

```bash
docker node ls
```

If a node shows "Down":

1.  SSH to the node and check Docker: `systemctl status docker`
2.  Check system logs: `journalctl -u docker -n 50`
3.  Restart Docker if needed: `systemctl restart docker`

The swarm will automatically reschedule containers from the failed node.

### Virtual IP Not Working

Check Keepalived status on each node:

```bash
systemctl status keepalived
ip addr show eth0
```

The node with the Virtual IP (10.10.20.65) should show it in the output.

Check Keepalived logs:

```bash
journalctl -u keepalived -n 50
```

### Storage Issues

Check NFS mount on Docker nodes:

```bash
df -h | grep /var/data
```

Remount if needed:

```bash
sudo mount -a
```

Check NFS exports on storage server:

```bash
showmount -e localhost
```

### Certificate Issues

Check certificate file:

```bash
ls -la /var/data/traefik/certificates/acme.json
```

This file should exist and have 600 permissions.

Force certificate renewal (ONLY AS LAST RESORT): Delete the certificate file and restart Traefik:

```bash
rm /var/data/traefik/certificates/acme.json
docker service update --force infra_traefik
```

### Viewing All Container Logs

For a specific service:

```bash
docker service logs -f <service-name>
```

For all services in a stack:

```bash
docker stack services <stack-name> --format "{{.Name}}" | xargs -I {} docker service logs {}
```

## Best Practices

### Security

*   **Never commit credentials**: Use Docker secrets or environment variables. An exception for this was made with the Route 53 Access/Secret keys as it has limited permissions on the hosted zone, but should still be kept private.
*   **Use private networks**: Keep databases and internal services off the Traefik network
*   **Regular updates**: Run `update-playbook.yml` monthly for security patches
*   **Monitor logs**: Check Traefik logs regularly for suspicious activity

### Reliability

*   **Use health checks**: Define health checks in your compose files
*   **Set resource limits**: Prevent one service from consuming all resources
*   **Use multiple replicas**: For critical services, run 2+ replicas
*   **Test before deploying**: Test compose files in a development environment

### Storage

*   **Use NFS for shared data**: Data that needs to be accessible from any node
*   **Use volumes for local data**: Data that doesn't need to be shared
*   **Regular backups**: Back up `/var/data` regularly
*   **Monitor disk space**: Keep an eye on storage server capacity

### Networking

*   **Isolate stacks**: Use dedicated networks for each stack (see Network Isolation Strategy)
*   **Use internal networks**: For services that don't need external access
*   **Document network topology**: Keep track of which services connect to which networks

## Quick Reference

### Common Commands

```bash
# List all nodes
docker node ls

# List all stacks
docker stack ls

# List services in a stack
docker stack services <stack-name>

# View service details
docker service inspect <service-name>

# View service logs
docker service logs <service-name>

# Scale a service
docker service scale <service-name>=<replicas>

# Update a service
docker service update <service-name>

# Remove a stack
docker stack rm <stack-name>
```

### Important Locations

*   Configuration files: `/var/data/config/`
*   Traefik certificates: `/var/data/traefik/certificates/`
*   Traefik logs: `/var/data/traefik/logs/`
*   Portainer data: `/var/data/portainer/`
*   Application data: `/var/data/<app-name>/`

### Important URLs

*   Traefik Dashboard: https://traefik.swarm.tallmanequipment.com
*   Portainer: https://portainer.swarm.tallmanequipment.com

### Support Contacts

*   **AWS Route 53**: For DNS and certificate validation
*   **Let's Encrypt**: For SSL certificates (automatic)
*   **Docker Documentation**: https://docs.docker.com/

## Appendix: File Reference

### inventory.ini

Defines the servers in the cluster:

*   3 Docker nodes (10.10.20.36, 10.10.20.61, 10.10.20.63)
*   1 Storage server (10.10.20.64)

### deployment-playbook.yml

Ansible playbook that performs initial setup:

*   Creates admin user
*   Configures NFS storage
*   Installs Docker
*   Initializes Docker Swarm
*   Configures Keepalived

### docker-compose-infra.yaml

Defines the infrastructure stack:

*   Traefik (ingress controller)
*   Portainer (management interface)
*   Portainer Agent (runs on all nodes)

### traefik.toml

Traefik configuration:

*   Enables dashboard
*   Configures Let's Encrypt with Route 53
*   Sets up HTTP to HTTPS redirect
*   Defines logging

### keepalived.conf.j2

Template for Keepalived configuration:

*   Manages Virtual IP (10.10.20.65)
*   Sets priorities for each node

### Makefile

Simplifies stack deployment:

*   `make deploy` - Deploy stacks
*   `make update` - Update and restart stacks
*   `make destroy` - Remove stacks
*   `make list` - List available stacks
