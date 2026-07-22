import requests
import google.generativeai as genai
from . import models

def generate_script(prompt: str, current_user: models.User, settings: models.AdminSettings) -> str:
    """Takes a user prompt and routes it to their preferred AI provider, returning the python script."""
    
    # 1. Determine which Provider to use
    provider = "gemini" # Fallback Default
    api_key = ""
    custom_url = ""
    
    # Override with global if enabled & set
    if settings.global_ai_enabled and settings.global_gemini_api_key:
        api_key = settings.global_gemini_api_key
        
    # Override with explicit user settings if they have configured it
    if current_user.user_ai_provider:
        provider = current_user.user_ai_provider
        api_key = current_user.user_ai_api_key if current_user.user_ai_api_key else api_key
        custom_url = current_user.user_ai_custom_url
        
    # Validation gates before we invoke external providers
    if provider == "gemini" and not api_key:
        return "# Error: No Gemini API Key configured. Please check your Personal or Global AI settings."
    if provider == "groq" and not api_key:
        return "# Error: No Groq API Key configured. Please append it in your Personal Settings."

    # --- INSTRUCT THE MODEL ON EXPECTATIONS ---
    system_instruction = """
    You are an expert Cisco Meraki Python programmer. Write a Python script based on the user's prompt.
    RULES:
    1. Only return the raw python code. Do NOT wrap it in ```python blocks. Do not add conversational text like 'Here is your script'.
    2. Assume the script will be executed directly. Do NOT write argparse arguments or CLI inputs.
    3. Use the `meraki` sdk by default (e.g. `import meraki`).
    4. If the script iterates things, print them out using standard `print()`.
    5. Always assume the api key can be pulled from `os.environ.get('MERAKI_DASHBOARD_API_KEY')`.
    """
    
    full_prompt = f"{system_instruction}\n\nUSER PROMPT:\n{prompt}"
    
    try:
        if provider == "gemini":
            genai.configure(api_key=api_key)
            # Use the fast, free tier model
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(full_prompt)
            return strip_code_blocks(response.text)
            
        elif provider == "groq":
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama3-70b-8192",
                "messages": [{"role": "user", "content": full_prompt}],
                "temperature": 0.2
            }
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            res.raise_for_status()
            return strip_code_blocks(res.json()["choices"][0]["message"]["content"])
            
        elif provider == "ollama":
            base_url = custom_url.rstrip("/") if custom_url else "http://127.0.0.1:11434"
            payload = {
                "model": "llama3", # Assuming a standard base
                "prompt": full_prompt,
                "stream": False,
                "options": {"temperature": 0.2}
            }
            res = requests.post(f"{base_url}/api/generate", json=payload, timeout=60)
            res.raise_for_status()
            return strip_code_blocks(res.json()["response"])
            
    except Exception as e:
        return f"# Critical AI Engine Error ({provider}):\n# {str(e)}"
        
    return "# Error: Unknown or unsupported AI Provider."
    
def strip_code_blocks(text: str) -> str:
    """Removes the markdown ```python and ``` block wrappers if models return them."""
    if text.startswith("```python\n"):
        text = text[10:]
    if text.startswith("```\n"):
        text = text[4:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
