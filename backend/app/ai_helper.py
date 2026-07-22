import requests
import google.generativeai as genai
from . import models

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
    if provider == "groq" and not api_key:
        return "# Error: No Groq API Key configured. Please append it in your Personal Settings."

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
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(full_prompt)
            return strip_code_blocks(response.text)
            
        elif provider == "groq":
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {"model": "llama3-70b-8192", "messages": [{"role": "user", "content": full_prompt}], "temperature": 0.2}
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            res.raise_for_status()
            return strip_code_blocks(res.json()["choices"][0]["message"]["content"])
            
        elif provider == "ollama":
            base_url = custom_url.rstrip("/") if custom_url else "http://127.0.0.1:11434"
            payload = {"model": "qwen2.5-coder:7b", "prompt": full_prompt, "stream": False, "options": {"temperature": 0.2}}
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
