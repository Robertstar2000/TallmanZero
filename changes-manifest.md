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
- **Instance**: Pre-configured to connect to the internal Ollama server at `http://10.10.20.60:11434`.
- **Embeddings**: Use the real local `sentence-transformers/all-MiniLM-L6-v2` model for embeddings, with the Docker image preloading that cache so it does not fall back to a placeholder implementation.

## 5. Deployment & Stability
- **Docker Swarm Migration**: Configured `docker-compose-portainer.yml` with persistent NFS volume mounts for `usr/`, `webui/`, and `knowledge/`.
- **Stabilization & Cleanup**:
    - Removed redundant `python/` directory to prevent module shadowing.
    - Synchronized root-level code structure with official image expectations.
    - Resolved port 80 bind conflicts between `run_ui.py` and `run_tunnel.py`.
    - Isolated optional Browser Agent dependencies so the Docker Desktop UI can still boot when `browser_use` is not installed in the image.
- **Self-Registration Flow**:
    - Implemented `/signup` route in `helpers/ui_server.py`.
    - Created custom-branded `webui/signup.html` registration interface.
    - Integrated `auth.register_user` backend logic for new account creation.
