# Tallman Zero - Changes Manifest

This document tracks the modifications made to the base Agent Zero platform to create **Tallman Zero**, a multi-user agentic workflow system for Tallman Equipment.

## 1. Multi-User Isolation
- **Refactored Database Schema**: Added `user_id` to chat session records to ensure data ownership, including database-level cleanup of `user_contexts` upon chat deletion.
- **WebSocket Security**: Updated `_10_state_sync.py` and `ws_manager.py` to trust the server-side security context instead of client payloads, preventing cross-user leakage.
- **Session-Aware API**: Added strict `AgentContext` ownership validation to `chat_remove.py`, `chat_export.py`, and `chat_load.py` endpoints to prevent unauthorized access.
- **Global Settings**: Maintained a shared configuration layer for system-wide settings while isolating individual user workflows.

## 2. Branding & UI Customization
- **Modified Landing / Authentication Page**: 
    - Replaced generic Agent Zero branding with **Tallman Zero** and removed all generic graphical logos from the login and signup flows.
    - Added an "Agentic vs LLM" comparison section to educate users on the platform's value.
    - Restricted login to `@tallmanequipment.com` domains.
    - Customized "Outfit" and "Rubik" typography for a premium look.
- **Application Rebranding**:
    - Replaced the primary sidebar application SVG logo with a properly styled textual **TALLMAN ZERO** mark.
    - Updated browser tab `<title>` tags across the UI to "Tallman Zero".
- **Modified Authentication Layer**:
    - Implemented domain-strict validation in `api/api_auth.py`.
    - Integrated multi-user session awareness into the login flow.
    - Connected user-specific context to the authentication token for filesystem isolation.

## 3. Knowledge Base Integration
- **Persistent Data**: Integrated `TALLMAN_QA_data.txt` and `TallmanProductLinks.txt` into the global knowledge store.
- **System Integration**: Configured the agent to prioritize these documents when answering equipment-related queries.

## 4. Default LLM Configuration
- **Model**: Hardcoded **Ollama gemma4:31b** as the immutable system-wide model for both Main and Utility tasks.
- **Context Length**: Configured to **100,000 tokens** to support extensive document processing and long-term reasoning.
- **Instance**: Hardcoded to connect strictly to the internal Ollama server via `http://10.10.20.60:11434`.
- **UI Lockdown**: Completely removed the per-chat model switcher interface and disabled the "Models" configuration tab in Agent Settings. The `allow_chat_override` flag was disabled to prevent user overrides.

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
- **Update Capabilities Removed**: Hard-disabled auto-update checks and entirely removed the "Self Update" section from the Backup settings UI. The former "Update" tab was renamed to "Backup".
- **Direct Chat Initialization**: Bypassed the generic "Welcome Screen" and default plugin discovery banners to directly initiate a new chat on session load, streamlining the multi-user entrance flow.
- **Immutable Container State**: Configured `Dockerfile.tallman` to bake the `/usr` configuration directory (including `settings.json` and active models) strictly into the image.
