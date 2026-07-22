## Why
- The AI functionality needed to be separated from the primary dashboard to provide a dedicated, focused environment for prompt engineering and script fixing.
- We needed to support alternative AI providers (Local Ollama, Groq) globally alongside the existing Gemini integration.

## What changed
- Created `ai_studio.html` utilizing HTMX to dynamically switch between "Generate", "Rebuild", and "Fix" functionality tabs.
- Updated `ai_helper.py` to accept a `mode` parameter for context-aware generation routing and parameter injection.
- Cleaned `dashboard.html` by removing the legacy embedded AI form.
- Updated database `models.py` and `settings.html` to support global AI configurations (Provider overrides and Custom URLs).
- Appended the `/ai-studio` routing into `ui.py` and the navigation sidebar in `app_layout.html`.

## Why this approach
- HTMX provides clean, dynamic tab interaction without requiring heavy frontend JavaScript frameworks or full page refreshes.
- Direct POST processing in the forms enables the backend to easily distinguish between `prompt` and `existing_script` payloads based purely on CSS visibility states.
- Clean isolation between execution tasks (Dashboard) and creation tasks (AI Studio) ensures the app remains scalable.

## Scope
- Affects frontend templates (`app_layout.html`, `dashboard.html`, `ai_studio.html`, `settings.html`).
- Modifies backend routes (`scripts.py`, `ui.py`, `admin.py`) and global settings models (`models.py`).
- Alters the core generation logic (`ai_helper.py`).
