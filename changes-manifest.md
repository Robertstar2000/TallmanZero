# Tallman Zero - Changes Manifest

This document tracks the modifications made to the base Agent Zero platform to create **Tallman Zero**, a multi-user agentic workflow system for Tallman Equipment.

## 1. Multi-User Isolation
- **Refactored Database Schema**: Added `user_id` to chat session records to ensure data ownership.
- **WebSocket Security**: Updated `ws_manager.py` to filter message streams by `user_id`, preventing cross-user information leakage.
- **Session-Aware API**: Updated backend routes to strictly serve chat history and active logs based on the logged-in user.
- **Global Settings**: Maintained a shared configuration layer for system-wide settings while isolating individual user workflows.

## 2. Branding & UI Customization
- **Modified Landing / Authentication Page**: 
    - Replaced generic Agent Zero branding with **Tallman Zero**.
    - Added an "Agentic vs LLM" comparison section to educate users on the platform's value.
    - Restricted login to `@tallmanequipment.com` domains.
    - Customized "Outfit" and "Rubik" typography for a premium look.
- **Modified Authentication Layer**:
    - Implemented domain-strict validation in `api/api_auth.py`.
    - Integrated multi-user session awareness into the login flow.
    - Connected user-specific context to the authentication token for filesystem isolation.

## 3. Knowledge Base Integration
- **Persistent Data**: Integrated `TALLMAN_QA_data.txt` and `TallmanProductLinks.txt` into the global knowledge store.
- **System Integration**: Configured the agent to prioritize these documents when answering equipment-related queries.

## 4. Default LLM Configuration
- **Model**: Set **Ollama gemma4:31b** as the default system-wide model.
- **Context Length**: Configured to **100,000 tokens** to support extensive document processing and long-term reasoning.
- **Instance**: Pre-configured to connect to the internal Ollama server via `host.docker.internal:11434`.

## 5. Deployment & Stability
- **Docker Swarm Migration**: Configured `docker-compose-portainer.yml` with persistent NFS volume mounts for `usr/`, `webui/`, and `knowledge/`.
- **Stabilization & Cleanup**:
    - Removed redundant `python/` directory to prevent module shadowing.
    - Synchronized root-level code structure with official image expectations.
    - Resolved port 80 bind conflicts between `run_ui.py` and `run_tunnel.py`.
- **Self-Registration Flow**:
    - Implemented `/signup` route in `helpers/ui_server.py`.
    - Created custom-branded `webui/signup.html` registration interface.
    - Integrated `auth.register_user` backend logic for new account creation.

## 6. Hardening & Lockdown
- **Plugin Management Restriction**: Removed non-essential plugins. The environment is now strictly bundled with the `_browser_agent` (Playwright) and `_model_config` plugins to enforce controlled features.
- **Update Checks Disabled**: Hard-disabled auto-update checks in the backend and removed the configuration toggles from the settings UI, enforcing intentional version locking.
- **Direct Chat Initialization**: Bypassed the generic "Welcome Screen" and default plugin discovery banners to directly initiate a new chat on session load, streamlining the multi-user entrance flow.
- **Immutable Container State**: Configured `Dockerfile.tallman` to bake the `/usr` configuration directory (including `settings.json` and active models) strictly into the image.
