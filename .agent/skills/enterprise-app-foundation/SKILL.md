---
name: enterprise-app-foundation
description: A high-performance blueprint for distributed applications requiring dual-persistence, secure identity governance, and fault-tolerant AI orchestration.
---

# Enterprise Application Foundation (Technical Deep Dive)

This skill provides the architectural substrate for rebuilding industrial-grade distributed systems from a blank slate.

## 🏗️ 1. Infrastructure: Distributed Persistence Nexus

Implement a **Dialect-Agnostic Proxy** to support both local development and cluster-scale deployment.

### Persistence Logic Pattern
```python
import os
import sqlite3
import psycopg2
from typing import Any, List, Optional, Callable
from abc import ABC, abstractmethod

class DatabaseProxy(ABC):
    """Abstract database proxy for dialect-agnostic persistence."""
    
    @abstractmethod
    def query(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        pass
    
    @abstractmethod
    def run(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        pass
    
    @abstractmethod
    def get(self, sql: str, params: Optional[List[Any]] = None) -> Optional[dict]:
        pass
    
    @abstractmethod
    def all(self, sql: str, params: Optional[List[Any]] = None) -> List[dict]:
        pass
    
    @abstractmethod
    def transaction(self, fn: Callable) -> Any:
        pass


# Dialect Detection
is_postgres = bool(os.environ.get('POSTGRES_HOST'))

def translate_params(sql: str) -> str:
    """Convert ? placeholders to $1, $2, etc. for PostgreSQL."""
    index = 0
    result = []
    for char in sql:
        if char == '?':
            index += 1
            result.append(f'${index}')
        else:
            result.append(char)
    return ''.join(result)


class SQLiteProxy(DatabaseProxy):
    """SQLite implementation for local development."""
    
    def __init__(self, db_path: str = 'data.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
    
    def query(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        cursor = self.conn.cursor()
        cursor.execute(sql, params or [])
        self.conn.commit()
        return cursor
    
    def get(self, sql: str, params: Optional[List[Any]] = None) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute(sql, params or [])
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def all(self, sql: str, params: Optional[List[Any]] = None) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute(sql, params or [])
        return [dict(row) for row in cursor.fetchall()]


class PostgresProxy(DatabaseProxy):
    """PostgreSQL implementation for production/Swarm deployment."""
    
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.environ.get('POSTGRES_HOST'),
            port=os.environ.get('POSTGRES_PORT', 5432),
            database=os.environ.get('POSTGRES_DB'),
            user=os.environ.get('POSTGRES_USER'),
            password=os.environ.get('POSTGRES_PASSWORD')
        )
    
    def query(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        sql = translate_params(sql)
        cursor = self.conn.cursor()
        cursor.execute(sql, params or [])
        self.conn.commit()
        return cursor


# Factory function
def get_database() -> DatabaseProxy:
    """Get the appropriate database proxy based on environment."""
    if is_postgres:
        return PostgresProxy()
    return SQLiteProxy()
```

### Swarm-Ready Docker Configuration
- **Postgres Nexus**: Image `postgres:15-alpine`.
- **Sequential Schema Protocol**: Postgres drivers often fail on multi-statement strings. Always `.split(';')` and execute sequentially during `init_db()`.
- **Relational Integrity**: Use `ON UPDATE CASCADE` for all identity references to allow seamless migration of technician IDs without violating foreign keys.
- **Fault-Tolerant Seeding**: Wrap dependent record insertions (Mentorship, User Badges) in diagnostic `try-except` blocks. This ensures that a single foreign key mismatch does not crash the entire orchestration, allowing the core infrastructure (Courses, Modules, Lessons, Quizzes) to be established.

---

## 🛡️ 2. Security: Identity Governance & Access Resilience

Stateless security optimized for multi-node deployments where shared memory is unavailable.

### The "Nuclear Governance" Override
Always implement a hard-coded memory override for the project's **Industrial Master** email. This ensures that even if database seeding fails or a technician record is stuck in a legacy "Hold" state, the master can still log in to fix the system.

```python
# Pattern in login route
MASTER_EMAIL = 'master@domain.com'

def authenticate_user(email: str, password: str) -> dict:
    """Authenticate user with Nuclear Governance override."""
    email = email.strip().lower()
    
    # Fetch user from database
    user = db.get("SELECT * FROM users WHERE email = ?", [email])
    
    if not user:
        raise AuthenticationError("User not found")
    
    # Nuclear Governance Override - Industrial Master always has access
    if email == MASTER_EMAIL.lower():
        user['status'] = 'active'  # In-memory override
        user['roles'] = '["Admin"]'
    
    # Verify password
    if not verify_password(password, user['password_hash']):
        raise AuthenticationError("Invalid password")
    
    # Check status (after potential override)
    if user['status'] != 'active':
        raise AuthenticationError(f"Account status: {user['status']}")
    
    return user
```

### Identity Sync Best Practices
- **Conflict Strategy**: Always synchronize personnel records based on **Email** (`ON CONFLICT(email)`), as `user_id` can drift between manual signups and automated seeds.
- **Priority Seeding**: Always seed the `Users` table (Identity Nexus) BEFORE any dependent tables (Logs, Enrollments) to prevent relational link failures.
- **Input Normalization**: Always `.strip()` and `.lower()` email addresses during both Signup and Login to ensure identity audits are resilient to typo-driven lockouts.

---

## 🛠️ 5. Docker Desktop: Advanced Build & Maintenance (Compiled)

This skill optimizes Docker for development environments and eliminates common binary architectural failures.

### The "Zero-Crash" Build Protocol:
1. **Model Portability**: Always use pure-Python libraries where possible. Native binaries compiled on Windows hosts may crash with `Exec format error` when mounted into Linux containers.
2. **Anonymous Volume Shadowing**: In your `docker-compose.yml`, mount your project root but **shadow** the virtual environment folder:
   ```yaml
   volumes:
     - .:/app
     - /app/.venv  # Forces usage of container-built Python packages
   ```
3. **Bootstrapping Entrypoints**: Use a `docker-entrypoint.sh` to handle automated seeding (`python seed.py`) and environment synchronization on every boot.

```python
# docker-entrypoint.py - Alternative Python entrypoint
import os
import subprocess
import sys

def main():
    """Container initialization and bootstrapping."""
    print("=" * 50)
    print("Agent Zero Container Initialization")
    print("=" * 50)
    
    # Environment detection
    is_swarm = bool(os.environ.get('POSTGRES_HOST'))
    env_mode = "SWARM/PRODUCTION" if is_swarm else "LOCAL/DEVELOPMENT"
    print(f"[ENV] Running in {env_mode} mode")
    
    # Ensure directories exist
    dirs = ['/a0/logs', '/a0/memory', '/a0/knowledge', '/a0/projects']
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    
    # Wait for database if in Swarm mode
    if is_swarm:
        wait_for_database()
    
    # Run database migrations
    print("[INIT] Running database migrations...")
    subprocess.run([sys.executable, 'migrate.py'], check=True)
    
    # Start main application
    print("[INIT] Starting main application...")
    os.execvp(sys.executable, [sys.executable, 'run_ui.py'])


def wait_for_database(max_retries: int = 30):
    """Wait for PostgreSQL to be available."""
    import socket
    host = os.environ.get('POSTGRES_HOST')
    port = int(os.environ.get('POSTGRES_PORT', 5432))
    
    for i in range(max_retries):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((host, port))
            sock.close()
            print(f"[SWARM] PostgreSQL is available!")
            return
        except socket.error:
            print(f"[SWARM] Waiting for database... ({i+1}/{max_retries})")
            import time
            time.sleep(2)
    
    print("[ERROR] Database not available after max retries")


if __name__ == '__main__':
    main()
```

---

## 🤖 3. AI: Resilient Multi-Model Orchestration

A critical layer for automating complex logic while maintaining enterprise-level uptime.

### The "Industrial Retry" Algorithm
Implement a global wrapper for AI SDKs (Google Generative AI, OpenAI, etc.).

```python
import time
import random
from typing import Callable, Any, Optional
from functools import wraps

def industrial_retry(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Industrial-grade retry decorator with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts (5-7 recommended)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries - 1:
                        # Exponential backoff with jitter
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        jitter = random.uniform(0, delay * 0.1)
                        sleep_time = delay + jitter
                        
                        print(f"[RETRY] Attempt {attempt + 1}/{max_retries} failed: {e}")
                        print(f"[RETRY] Retrying in {sleep_time:.2f}s...")
                        time.sleep(sleep_time)
            
            raise last_exception
        return wrapper
    return decorator


# Usage with AI models
@industrial_retry(max_retries=7, base_delay=2.0)
def generate_with_gemini(prompt: str, model: str = "gemini-2.0-flash") -> str:
    """Generate content with Gemini, with industrial retry."""
    import google.generativeai as genai
    
    model_instance = genai.GenerativeModel(model)
    response = model_instance.generate_content(prompt)
    return response.text


# Model configuration
AI_MODELS = {
    'reasoning': 'gemini-2.0-flash',      # High-performance reasoning
    'vision': 'gemini-2.0-flash',          # Visual synthesis
    'embedding': 'text-embedding-004'      # Vector embeddings
}
```

- **Retries**: 5-7 attempts with exponential backoff.
- **Models**: High-performance reasoning via `gemini-2.0-flash` and visual synthesis capabilities.

---

---
---

## 🌐 6. Docker Swarm: Industrial Orchestration Platform

This governs the production-grade deployment across the Tallman multi-node cluster.

### Cluster Infrastructure
- **High Availability Nexus**: 3 Manager Nodes (10.10.20.36, .61, .63) orchestrated by **Keepalived** for a Virtual IP (10.10.20.65) failover.
- **Shared Persistence**: Centralized NFS storage server (10.10.20.64) mounted at `/var/data` on all nodes. All application volumes must reside here for cross-node portability.
- **Automated Ingress**: **Traefik** handles routing and SSL (Let's Encrypt) via AWS Route 53 DNS validation.

### Stack Deployment Protocol
Always use the standardized **Makefile** at `/var/data/config/` for registry operations.
- `make deploy STACK=<name>`: Initialize/Update stack.
- `make update STACK=<name>`: Force redeploy with latest images.
- `make list`: Audit all active industrial stacks.

### Network Isolation Protocol
For security compliance, every stack must implement a dual-network architecture:
1. **`<stackname>_traefik`**: An overlay network for external Traefik routing.
2. **`<stackname>_internal`**: An overlay network for inter-container communication (e.g., App to DB), isolated from the ingress.

---

## 🛠️ Re-Implementation Workflow
1. **Bootstrap**: Initialize `requirements.txt` with `flask`, `psycopg2-binary`, `python-dotenv`, `pyjwt`, `bcrypt`.
2. **Persistence**: Build `db.py` with sequential schema execution and CASCADE support.
3. **Identity**: Create authentication routes with Governance Overrides and Email-First sync logic.
4. **Orchestration**: Define the `docker-compose.yml` (without version tag) using `python:3.11-slim-bookworm`.
5. **Entrypoint**: Create and `chmod +x` a `docker-entrypoint.sh` for runtime bootstrapping.
6. **Production Sync**: Move deployment manifests to `/var/data/config/` on the Swarm Master and execute `make deploy`.
7. **Documentation Protocol**: Update `README.md` to explicitly state the **Verified Deployment Paths** (Local Developer vs. Industrial Swarm), **Persistence Compliance** standards, the **Master Registry** (the application's specific repository URL), and the **Network Access Points** (IP and Port addresses specific to the application) immediately following the platform introduction.
