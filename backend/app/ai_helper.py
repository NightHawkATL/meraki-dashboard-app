import requests
import google.generativeai as genai
from . import models

def fetch_available_models(provider: str, api_key: str = "", custom_url: str = "") -> list[dict]:
    """Dynamically queries the provider for available models based on credentials."""
    models_out = []
    
    if provider == "gemini":
        if api_key:
            # 1. Try REST endpoint
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                resp = requests.get(url, timeout=8)
                if resp.ok:
                    data = resp.json()
                    for m in data.get("models", []):
                        methods = m.get("supportedGenerationMethods", []) or []
                        if "generateContent" in methods:
                            model_id = m.get("name", "")
                            display = m.get("displayName") or model_id.replace("models/", "")
                            models_out.append({"id": model_id, "name": f"{display} ({model_id})"})
            except Exception as e:
                print(f"Gemini REST models fetch error: {e}")

            # 2. Try SDK list_models fallback
            if not models_out:
                try:
                    genai.configure(api_key=api_key)
                    for m in genai.list_models():
                        if "generateContent" in getattr(m, "supported_generation_methods", []):
                            model_id = m.name
                            display = getattr(m, "display_name", "") or model_id.replace("models/", "")
                            models_out.append({"id": model_id, "name": f"{display} ({model_id})"})
                except Exception as e:
                    print(f"Gemini SDK models fetch error: {e}")

        # If not fetched via API, supply current standard Gemini models
        if not models_out:
            fallback_models = [
                ("models/gemini-2.5-flash", "Gemini 2.5 Flash"),
                ("models/gemini-2.5-pro", "Gemini 2.5 Pro"),
                ("models/gemini-2.0-flash", "Gemini 2.0 Flash"),
                ("models/gemini-2.0-flash-lite", "Gemini 2.0 Flash Lite"),
                ("models/gemini-1.5-flash", "Gemini 1.5 Flash"),
                ("models/gemini-1.5-pro", "Gemini 1.5 Pro"),
            ]
            for m_id, m_name in fallback_models:
                models_out.append({"id": m_id, "name": f"{m_name} ({m_id})"})

    elif provider == "openai":
        if api_key:
            try:
                resp = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=8)
                if resp.ok:
                    for m in resp.json().get("data", []):
                        m_id = m.get("id", "")
                        if m_id.startswith(("gpt-", "o1", "o3", "chatgpt-")):
                            models_out.append({"id": m_id, "name": m_id})
                    models_out.sort(key=lambda x: x["id"], reverse=True)
            except Exception:
                pass
        if not models_out:
            for m_id in ["gpt-4o", "gpt-4o-mini", "o1-mini", "o1-preview", "gpt-4-turbo"]:
                models_out.append({"id": m_id, "name": m_id})

    elif provider == "anthropic":
        models_out = [
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet (Latest)"},
            {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus"},
            {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet"}
        ]

    elif provider == "groq":
        if api_key:
            try:
                resp = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=8)
                if resp.ok:
                    for m in resp.json().get("data", []):
                        m_id = m.get("id", "")
                        models_out.append({"id": m_id, "name": m_id})
            except Exception:
                pass
        if not models_out:
            for m_id in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]:
                models_out.append({"id": m_id, "name": m_id})

    elif provider in ("ollama", "openwebui"):
        base_url = (custom_url or "http://127.0.0.1:11434").rstrip("/")
        if provider == "ollama":
            try:
                resp = requests.get(f"{base_url}/api/tags", timeout=5)
                if resp.ok:
                    for m in resp.json().get("models", []):
                        m_name = m.get("name", "")
                        models_out.append({"id": m_name, "name": m_name})
            except Exception:
                pass
            if not models_out:
                for m_id in ["qwen2.5-coder:7b", "qwen2.5-coder:3b", "llama3.2", "codellama"]:
                    models_out.append({"id": m_id, "name": m_id})
        else:
            try:
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                resp = requests.get(f"{base_url}/api/models", headers=headers, timeout=5)
                if resp.ok:
                    for m in resp.json().get("data", []):
                        m_id = m.get("id", "")
                        models_out.append({"id": m_id, "name": m_id})
            except Exception:
                pass
            if not models_out:
                for m_id in ["qwen2.5-coder:7b", "llama3.3"]:
                    models_out.append({"id": m_id, "name": m_id})

    return models_out

def _resolve_gemini_model(api_key: str, configured_model: str = "") -> str:
    """Returns the user/admin configured model if provided, or resolves dynamically from available models."""
    if configured_model:
        return configured_model

    models = fetch_available_models("gemini", api_key)
    if models:
        return models[0]["id"]
    return "models/gemini-2.0-flash"

def _get_provider_config(current_user: models.User, settings: models.AdminSettings):
    provider = "gemini" # Fallback Default
    api_key = ""
    custom_url = ""
    configured_model = ""
    
    if settings and settings.global_ai_enabled:
        provider = getattr(settings, 'global_ai_provider', 'gemini') or 'gemini'
        api_key = getattr(settings, 'global_gemini_api_key', '') or ''
        custom_url = getattr(settings, 'global_ai_custom_url', '') or ''
        configured_model = getattr(settings, 'global_ai_model', '') or ''
        
    if current_user and current_user.user_ai_provider:
        provider = current_user.user_ai_provider
        api_key = current_user.user_ai_api_key if current_user.user_ai_api_key else api_key
        custom_url = current_user.user_ai_custom_url if current_user.user_ai_custom_url else custom_url
        if getattr(current_user, 'user_ai_model', None):
            configured_model = current_user.user_ai_model
        
    return provider, api_key, custom_url, configured_model

def generate_script(
    prompt: str,
    current_user: models.User,
    settings: models.AdminSettings,
    mode: str = "generate",
    existing_script: str = "",
    model_override: str = None
) -> str:
    """Takes a user prompt, routes it to preferred AI, and returns Python output."""
    
    provider, api_key, custom_url, configured_model = _get_provider_config(current_user, settings)
    active_model = model_override or configured_model
    
    if provider == "gemini" and not api_key:
        return "# Error: No Gemini API Key configured. Please check your Personal or Global AI settings."
    if provider == "openai" and not api_key:
        return "# Error: No OpenAI API Key configured. Please append it in your Personal or Global AI Settings."
    if provider == "anthropic" and not api_key:
        return "# Error: No Anthropic API Key configured. Please append it in your Personal or Global AI Settings."
    if provider == "groq" and not api_key:
        return "# Error: No Groq API Key configured. Please append it in your Personal Settings."
    if provider == "openwebui" and not custom_url:
        return "# Error: No OpenWebUI URL configured. Please append it in your Settings."

    system_instruction = """
    You are an expert Cisco Meraki Python programmer building scripts for an internal dashboard platform.
    RULES:
    1. Only return the raw python code. Do NOT wrap it in ```python blocks. Do not add conversational text.
    2. Assume the script will be executed directly via exec() behind an API endpoint.
    3. Use the `meraki` sdk by default (`import meraki`).
    4. If the script queries for items, print them to standard out (`print()`) so the UI can capture the logs.
    5. The dashboard provides global os.environ.get('MERAKI_DASHBOARD_API_KEY') for auth. Use it.
    6. DYNAMIC VARIABLES: If the user requests targeting specific devices/networks (e.g. 'bounce ports on these switches'), inserting placeholders like `TARGET_SERIALS = ["{{SERIAL_1}}", "{{SERIAL_2}}"]` is acceptable if you cannot inherently know the serials. The UI will later prompt the user to fill those in if it detects {{...}}.
    """
    
    if mode == "generate":
        full_prompt = f"{system_instruction}\n\nTASK: Generate a new script.\nUSER PROMPT:\n{prompt}"
    elif mode == "fix":
        full_prompt = f"{system_instruction}\n\nTASK: Fix the provided script based on the error/prompt provided.\n\nUSER PROMPT / ERROR:\n{prompt}\n\nEXISTING SCRIPT:\n{existing_script}"
    elif mode == "rebuild":
        full_prompt = f"{system_instruction}\n\nTASK: Rebuild the provided foreign script to strictly enforce the RULES above so it runs safely inside our dashboard. Keep the underlying logic/goal identical.\n\nFOREIGN SCRIPT:\n{existing_script}\n\nOPTIONAL USER PROMPT:\n{prompt}"
    else:
        full_prompt = f"{system_instruction}\n\nUSER PROMPT:\n{prompt}"
        
    try:
        if provider == "gemini":
            target_model = _resolve_gemini_model(api_key, active_model)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(target_model)
            response = model.generate_content(full_prompt)
            return strip_code_blocks(response.text)
            
        elif provider == "openai":
            target_model = active_model or "gpt-4o"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": target_model,
                "messages": [
                    {"role": "system", "content": system_instruction.strip()},
                    {"role": "user", "content": prompt if mode == "generate" else full_prompt}
                ],
                "temperature": 0.2
            }
            res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=45)
            res.raise_for_status()
            return strip_code_blocks(res.json()["choices"][0]["message"]["content"])

        elif provider == "anthropic":
            target_model = active_model or "claude-3-5-sonnet-20241022"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": target_model,
                "max_tokens": 4096,
                "system": system_instruction.strip(),
                "messages": [
                    {"role": "user", "content": prompt if mode == "generate" else full_prompt}
                ]
            }
            res = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=45)
            res.raise_for_status()
            data = res.json()
            reply_text = "".join([c.get("text", "") for c in data.get("content", [])])
            return strip_code_blocks(reply_text)

        elif provider == "openwebui":
            base_url = custom_url.rstrip("/")
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            target_model = active_model or "qwen2.5-coder:7b"
            payload = {
                "model": target_model,
                "messages": [
                    {"role": "system", "content": system_instruction.strip()},
                    {"role": "user", "content": prompt if mode == "generate" else full_prompt}
                ]
            }
            res = requests.post(f"{base_url}/api/chat/completions", headers=headers, json=payload, timeout=60)
            res.raise_for_status()
            return strip_code_blocks(res.json()["choices"][0]["message"]["content"])

        elif provider == "groq":
            target_model = active_model or "llama-3.3-70b-versatile"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": target_model, "messages": [{"role": "user", "content": full_prompt}], "temperature": 0.2}
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            res.raise_for_status()
            return strip_code_blocks(res.json()["choices"][0]["message"]["content"])
            
        elif provider == "ollama":
            base_url = custom_url.rstrip("/") if custom_url else "http://127.0.0.1:11434"
            target_model = active_model or "qwen2.5-coder:3b"
            payload = {"model": target_model, "prompt": full_prompt, "stream": False, "options": {"temperature": 0.2}}
            res = requests.post(f"{base_url}/api/generate", json=payload, timeout=60)
            res.raise_for_status()
            return strip_code_blocks(res.json()["response"])
            
    except Exception as e:
        return f"# Critical AI Engine Error ({provider}):\n# {str(e)}"
        
    return "# Error: Unknown or unsupported AI Provider."
    
def strip_code_blocks(text: str) -> str:
    if text.startswith("```python\n"):
        text = text[10:]
    if text.startswith("```json\n"):
        text = text[8:]
    if text.startswith("```\n"):
        text = text[4:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
