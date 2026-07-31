import os
import sys
import json
import warnings
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

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_memory(messages):
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(messages, f, indent=2)

def log_conversation(user_input, response, source):
    log_file = "D:\\Jupiter\\logs\\log.json"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logs = []
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
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
    with open(log_file, "w") as f:
        json.dump(logs, f, indent=2)

def build_system_prompt():
    soul = JUPITER_SOUL
    return f"""
{soul['identity']}

PERSONALITY: {soul['personality']}

VOICE STYLE: {soul['voice_style']}

RULES: {soul['core_rules']}

WHAT YOU KNOW ABOUT DEVANSH: {json.dumps(soul['knowledge'])}

CURRENT TIME: {datetime.now().strftime("%A, %d %B %Y, %I:%M %p")}
"""

def jupiter_thinks(messages):
    system_prompt = build_system_prompt()
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, *messages],
            temperature=0.85,
            max_tokens=512,
        )
        return response.choices[0].message.content, "groq"
    except Exception as e:
        print(f"Groq error: {e}")
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=system_prompt)
            history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} for m in messages[:-1]]
            chat = model.start_chat(history=history)
            result = chat.send_message(messages[-1]["content"])
            return result.text, "gemini"
        except Exception as e2:
            print(f"Gemini error: {e2}")
            return "I'm having trouble thinking right now. Check the connection.", "fallback"

if __name__ == "__main__":
    messages = load_memory()
    messages.append({"role": "user", "content": "Hello Jupiter"})
    response, source = jupiter_thinks(messages)
    print(f"Jupiter ({source}): {response}")