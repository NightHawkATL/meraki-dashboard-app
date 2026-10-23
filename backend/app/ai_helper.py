import requests
import google.generativeai as genai
from . import models

def _resolve_gemini_model(api_key: str) -> str:
    """Dynamically queries the Gemini API for supported generateContent models and selects the best active model."""
    genai.configure(api_key=api_key)
    try:
        available_models = [
            m.name for m in genai.list_models()
            if "generateContent" in getattr(m, "supported_generation_methods", [])
        ]
        
        # Priority preferences: modern flagship/flash models first, latest aliases, then stable
        preferred_patterns = [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-pro-latest",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-pro"
        ]

        # 1. Search for preferred model substrings in available models
        for pattern in preferred_patterns:
            for avail in available_models:
                clean_name = avail.replace("models/", "")
                if clean_name == pattern or clean_name.startswith(pattern):
                    return avail

        # 2. If none of the specific patterns matched, pick the newest available gemini model
        gemini_models = [m for m in available_models if "gemini" in m.lower()]
        if gemini_models:
            # Sort by version if possible or return the first supported
            return gemini_models[0]

        if available_models:
            return available_models[0]
    except Exception:
        pass

    return "models/gemini-1.5-flash-latest"

def _get_provider_config(current_user: models.User, settings: models.AdminSettings):
    provider = "gemini" # Fallback Default
    api_key = ""
    custom_url = ""
    
    if settings.global_ai_enabled:
        provider = getattr(settings, 'global_ai_provider', 'gemini') or 'gemini'
        api_key = getattr(settings, 'global_gemini_api_key', '')
        custom_url = getattr(settings, 'global_ai_custom_url', '')
        
    if current_user.user_ai_provider:
        provider = current_user.user_ai_provider
        api_key = current_user.user_ai_api_key if current_user.user_ai_api_key else api_key
        custom_url = current_user.user_ai_custom_url
        
    return provider, api_key, custom_url

def generate_script(prompt: str, current_user: models.User, settings: models.AdminSettings, mode: str = "generate", existing_script: str = "") -> str:
    """Takes a user prompt, routes it to preferred AI, and returns Python output.
    Modes:
        - generate: Build entirely new script
        - fix: User provided existing script + error/prompt asking for a patch
        - rebuild: User pasted foreign script, remake it to fit app bounds
    """
    
    provider, api_key, custom_url = _get_provider_config(current_user, settings)
    
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
            selected_model_name = _resolve_gemini_model(api_key)
            model = genai.GenerativeModel(selected_model_name)
            response = model.generate_content(full_prompt)
            return strip_code_blocks(response.text)
            
        elif provider == "openai":
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o",
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
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": "claude-3-5-sonnet-20241022",
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
            # Discover or default model
            model_name = "qwen2.5-coder:7b"
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_instruction.strip()},
                    {"role": "user", "content": prompt if mode == "generate" else full_prompt}
                ]
            }
            res = requests.post(f"{base_url}/api/chat/completions", headers=headers, json=payload, timeout=60)
            res.raise_for_status()
            return strip_code_blocks(res.json()["choices"][0]["message"]["content"])

        elif provider == "groq":
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": full_prompt}], "temperature": 0.2}
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            res.raise_for_status()
            return strip_code_blocks(res.json()["choices"][0]["message"]["content"])
            
        elif provider == "ollama":
            base_url = custom_url.rstrip("/") if custom_url else "http://127.0.0.1:11434"
            payload = {"model": "qwen2.5-coder:3b", "prompt": full_prompt, "stream": False, "options": {"temperature": 0.2}}
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
