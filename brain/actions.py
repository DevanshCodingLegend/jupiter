import os
import sys
import json
import warnings
warnings.filterwarnings("ignore")

from groq import Groq
from dotenv import load_dotenv
load_dotenv("D:\\Jupiter\\.env")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

ACTIONS = {
    "RESPOND": "Just respond conversationally, no system action needed",
    "OPEN_APP": "Open an application on the laptop",
    "CLOSE_APP": "Close an application",
    "SEARCH_WEB": "Search the web for something",
    "TAKE_SCREENSHOT": "Take a screenshot and analyze the screen",
    "GET_SYSTEM_INFO": "Get battery, CPU, RAM info",
    "TYPE_TEXT": "Type text on the keyboard",
    "PRESS_KEY": "Press a keyboard shortcut or key",
    "START_LECTURE": "Start recording and transcribing a lecture",
    "STOP_LECTURE": "Stop the lecture recording",
    "LIST_LECTURES": "List saved lecture notes",
    "READ_LECTURE": "Read a specific lecture summary",
    "STOP_LISTENING": "Jupiter should stop listening until told to resume",
    "START_LISTENING": "Jupiter should resume listening",
    "SET_VOLUME": "Change the system volume",
    "PLAY_MUSIC": "Play music on Spotify or YouTube",
    "STOP_MUSIC": "Stop music",
    "WRITE_EMAIL": "Draft and send an email",
    "SET_REMINDER": "Set a reminder for something",
    "CORRECT_SPELLING": "Devansh is correcting a spelling or name Jupiter got wrong",
    "OPEN_WEBSITE": "Open a specific website in browser",
    "SCROLL": "Scroll up or down on screen",
    "CLICK": "Click somewhere on screen",
    "SLEEP": "Jupiter should go to sleep / say goodbye",
    "BROWSER_NAVIGATE": "Navigate browser to a URL or website",
    "BROWSER_SWITCH_TAB": "Switch to an already open browser tab by name",
    "BROWSER_NEW_TAB": "Open a new browser tab",
    "BROWSER_CLOSE_TAB": "Close the current browser tab",
    "BROWSER_CLICK": "Click something on the current webpage",
    "BROWSER_TYPE": "Type something in the browser",
    "BROWSER_SCROLL": "Scroll up or down on current page",
    "BROWSER_READ": "Read the content of the current webpage",
    "BROWSER_SEARCH_PAGE": "Search for text within the current page",
}

def understand_intent(text, context="", screen_context=""):
    prompt = f"""You are Jupiter's intent parser. Analyze what Devansh said and return a JSON object.

What Devansh said: "{text}"

Recent context: {context}

What's on his screen: {screen_context or "Unknown"}

Return ONLY a JSON object with these fields:
{{
    "action": "one of the action types listed below",
    "confidence": 0.0 to 1.0,
    "parameters": {{
        "app_name": "if opening/closing an app",
        "query": "if searching or asking something", 
        "text": "if typing something",
        "key": "if pressing a key",
        "subject": "if starting a lecture",
        "volume": "0-100 if setting volume",
        "correction": "what the correct spelling/name is",
        "website": "URL or site name",
        "response_needed": true/false
    }},
    "should_speak": true/false,
    "reasoning": "brief explanation of why you chose this action"
}}

Available actions:
{json.dumps(ACTIONS, indent=2)}

Rules:
- If unsure between RESPOND and a system action, choose the system action if confidence > 0.7
- If Devansh is clearly talking to someone else or mumbling random things, return action RESPOND with response_needed false
- If it's a question or needs information, use RESPOND
- Be smart — "pull up youtube" means OPEN_WEBSITE with youtube.com
- "turn it down" means SET_VOLUME lower
- "take notes" in context of studying means START_LECTURE
- Return ONLY the JSON, no other text"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=512,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"Intent parse error: {e}")
        return {
            "action": "RESPOND",
            "confidence": 0.5,
            "parameters": {"response_needed": True},
            "should_speak": True,
            "reasoning": "fallback"
        }

def should_interrupt_speech(audio_volume, current_text_heard=""):
    if audio_volume > 0.04:
        return True
    if current_text_heard and len(current_text_heard.split()) > 2:
        return True
    return False

if __name__ == "__main__":
    result = understand_intent("open spotify and play something chill")
    print(json.dumps(result, indent=2))
    
    result = understand_intent("yo what time is my COMP1100 class tomorrow")
    print(json.dumps(result, indent=2))