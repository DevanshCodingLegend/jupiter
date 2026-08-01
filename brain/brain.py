import os
import sys
import json
import warnings
import traceback
warnings.filterwarnings("ignore")

from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

sys.path.insert(0, "D:\\Jupiter\\brain")
from soul import JUPITER_SOUL

load_dotenv("D:\\Jupiter\\.env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)

MEMORY_FILE = "D:\\Jupiter\\memory\\conversation_memory.json"
DEVANSH_FILE = "D:\\Jupiter\\memory\\devansh_profile.json"
WORLD_FILE = "D:\\Jupiter\\memory\\world_knowledge.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_memory(messages):
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)

def load_devansh_profile():
    if os.path.exists(DEVANSH_FILE):
        with open(DEVANSH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return JUPITER_SOUL["knowledge"]

def save_devansh_profile(profile):
    os.makedirs(os.path.dirname(DEVANSH_FILE), exist_ok=True)
    with open(DEVANSH_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

def log_conversation(user_input, response, source):
    log_file = "D:\\Jupiter\\logs\\conversation_log.json"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logs = []
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            try:
                logs = json.load(f)
            except:
                logs = []
    logs.append({
        "time": datetime.now().isoformat(),
        "user": user_input,
        "jupiter": response,
        "source": source
    })
    if len(logs) > 1000:
        logs = logs[-1000:]
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

def build_system_prompt(screen_context=None):
    soul = JUPITER_SOUL
    profile = load_devansh_profile()
    now = datetime.now()

    time_context = now.strftime("%A, %d %B %Y, %I:%M %p")
    
    hour = now.hour
    if 5 <= hour < 12:
        time_of_day = "morning"
    elif 12 <= hour < 17:
        time_of_day = "afternoon"
    elif 17 <= hour < 21:
        time_of_day = "evening"
    else:
        time_of_day = "night"

    screen_section = ""
    if screen_context:
        screen_section = f"\nWHAT YOU CAN SEE ON DEVANSH'S SCREEN RIGHT NOW:\n{screen_context}\n"

    return f"""
{soul['identity']}

PERSONALITY:
{soul['personality']}

VOICE AND SPEAKING STYLE:
{soul['voice_style']}

CORE RULES:
{soul['core_rules']}

YOUR CAPABILITIES:
{soul['capabilities']}

CONVERSATION MODE:
{soul['conversation_mode']}

WHAT YOU KNOW ABOUT DEVANSH:
{json.dumps(profile, indent=2)}

CURRENT TIME: {time_context}
TIME OF DAY: {time_of_day}
{screen_section}
Remember: You are Jupiter. Act like it. Be real, be present, be intelligent.
"""

def think_groq(messages, system_prompt):
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                *messages[-20:]
            ],
            temperature=0.85,
            max_tokens=512,
        )
        return response.choices[0].message.content, "groq"
    except Exception as e:
        print(f"Groq error: {e}")
        return None, None

def think_gemini(messages, system_prompt):
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            "gemini-1.5-flash",
            system_instruction=system_prompt
        )
        history = []
        for m in messages[:-1]:
            role = "user" if m["role"] == "user" else "model"
            history.append({"role": role, "parts": [m["content"]]})
        chat = model.start_chat(history=history)
        result = chat.send_message(messages[-1]["content"])
        return result.text, "gemini"
    except Exception as e:
        print(f"Gemini error: {e}")
        return None, None

def jupiter_thinks(messages, screen_context=None):
    system_prompt = build_system_prompt(screen_context)
    
    response, source = think_groq(messages, system_prompt)
    if response:
        return response, source
    
    response, source = think_gemini(messages, system_prompt)
    if response:
        return response, source

    return "I'm having trouble connecting right now. Check the API keys.", "fallback"

def update_devansh_knowledge(key, value):
    profile = load_devansh_profile()
    profile[key] = value
    save_devansh_profile(profile)
    print(f"Jupiter learned: {key} = {value}")

if __name__ == "__main__":
    messages = [{"role": "user", "content": "Hello Jupiter, how are you?"}]
    response, source = jupiter_thinks(messages)
    print(f"Jupiter ({source}): {response}")