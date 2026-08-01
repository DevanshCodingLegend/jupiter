import sys
import os
import warnings
import threading
import time
import json
import subprocess
warnings.filterwarnings("ignore")

sys.path.insert(0, "D:\\Jupiter\\brain")
sys.path.insert(0, "D:\\Jupiter\\voice")
sys.path.insert(0, "D:\\Jupiter\\eyes")
sys.path.insert(0, "D:\\Jupiter\\system")

from rich.console import Console
from rich.markdown import Markdown

from brain import jupiter_thinks, load_memory, save_memory, log_conversation
from voice import speak as _speak, listen, load_whisper, start_mic_stream, is_speaking, interrupt_flag
from actions import understand_intent
from state_server import update_state, start_server

console = Console()

listening_active = True
lecture_mode = False
corrections = {}
recent_context = []
eyes_state = {}

def load_corrections():
    global corrections
    path = "D:\\Jupiter\\memory\\corrections.json"
    if os.path.exists(path):
        with open(path) as f:
            corrections = json.load(f)

def save_correction(wrong, correct):
    corrections[wrong.lower()] = correct
    with open("D:\\Jupiter\\memory\\corrections.json", "w") as f:
        json.dump(corrections, f, indent=2)

def apply_corrections(text):
    for wrong, correct in corrections.items():
        text = text.lower().replace(wrong, correct)
    return text

def speak(text):
    update_state(jupiter_speaking=True, response_text=text)
    _speak(text)
    update_state(jupiter_speaking=False)

def jupiter_respond(user_input, messages, silent=False):
    user_input = apply_corrections(user_input)
    recent_context.append(user_input)
    if len(recent_context) > 10:
        recent_context.pop(0)

    if not silent:
        update_state(user_text=user_input, thinking=True, listening=False)

    messages.append({"role": "user", "content": user_input})

    context_parts = []
    if eyes_state.get("mood"):
        context_parts.append(f"Devansh mood: {eyes_state['mood']}")
    if eyes_state.get("attention"):
        context_parts.append(f"Attention: {eyes_state['attention']}")
    if eyes_state.get("gesture"):
        context_parts.append(f"Gesture: {eyes_state['gesture']}")
    if eyes_state.get("screen"):
        context_parts.append(f"Screen: {eyes_state['screen']}")

    screen_context = ". ".join(context_parts) if context_parts else None

    with console.status("[cyan]Jupiter...[/cyan]"):
        response, source = jupiter_thinks(messages, screen_context=screen_context)

    messages.append({"role": "assistant", "content": response})
    save_memory(messages)
    log_conversation(user_input, response, source)

    update_state(thinking=False, response_text=response, memory_count=len(messages))

    console.print(f"\n[bold cyan]Jupiter[/bold cyan] [dim]({source})[/dim]:")
    console.print(Markdown(response))
    console.print()

    if not silent:
        speak(response)
    return messages

def execute_action(intent, text, messages):
    global listening_active, lecture_mode
    
    from control import (open_app, open_url, open_url_new_tab, close_app,
                         type_text, press_key, hotkey, take_screenshot,
                         get_system_info, search_web, scroll_page,
                         set_volume, play_spotify, play_youtube, CHROME)

    action = intent.get("action", "RESPOND")
    params = intent.get("parameters", {})

    try:
        if action == "RESPOND":
            if params.get("response_needed", True):
                messages = jupiter_respond(text, messages)

        elif action == "OPEN_APP":
            app = params.get("app_name", "").strip()
            
            # Check if it's actually a website
            websites = ["youtube", "google", "claude", "chatgpt", "instagram", 
                       "twitter", "x.com", "github", "spotify", "netflix",
                       "reddit", "whatsapp", "discord", "gmail"]
            
            website_urls = {
                "youtube": "https://youtube.com",
                "google": "https://google.com", 
                "claude": "https://claude.ai",
                "chatgpt": "https://chatgpt.com",
                "instagram": "https://instagram.com",
                "twitter": "https://twitter.com",
                "x": "https://x.com",
                "github": "https://github.com",
                "netflix": "https://netflix.com",
                "reddit": "https://reddit.com",
                "whatsapp": "https://web.whatsapp.com",
                "gmail": "https://mail.google.com",
            }
            
            app_lower = app.lower()
            if app_lower in website_urls:
                open_url(website_urls[app_lower])
                speak(f"Opening {app}.")
            else:
                result = open_app(app)
                speak(result)

        elif action == "OPEN_WEBSITE":
            url = params.get("website", params.get("query", text))
            
            website_urls = {
                "youtube": "https://youtube.com",
                "google": "https://google.com",
                "claude": "https://claude.ai",
                "chatgpt": "https://chatgpt.com",
                "instagram": "https://instagram.com",
                "twitter": "https://twitter.com",
                "github": "https://github.com",
                "netflix": "https://netflix.com",
                "reddit": "https://reddit.com",
                "whatsapp": "https://web.whatsapp.com",
                "gmail": "https://mail.google.com",
                "spotify": "https://open.spotify.com",
            }
            
            url_lower = url.lower().strip()
            if url_lower in website_urls:
                url = website_urls[url_lower]
            
            open_url(url)
            speak(f"On it.")

        elif action == "CLOSE_APP":
            app = params.get("app_name", "")
            result = close_app(app)
            speak(result)

        elif action == "SEARCH_WEB":
            query = params.get("query", text)
            search_web(query)
            speak(f"Searching for {query}.")

        elif action == "TAKE_SCREENSHOT":
            path = take_screenshot()
            ctx = eyes_state.get("screen", "")
            messages = jupiter_respond(
                f"Devansh asked what's on screen. Screen context: {ctx}. Tell him what you see naturally.",
                messages
            )

        elif action == "GET_SYSTEM_INFO":
            info = get_system_info()
            msg = f"CPU {info['cpu_percent']}%, RAM {info['ram_used_gb']}GB of {info['ram_total_gb']}GB"
            if "battery_percent" in info:
                msg += f", battery {info['battery_percent']}% {'charging' if info['plugged_in'] else 'on battery'}"
            msg += f", active window is {info['active_window']}"
            messages = jupiter_respond(
                f"System info data: {msg}. Tell Devansh naturally in 1 sentence.", messages
            )

        elif action == "TYPE_TEXT":
            t = params.get("text", params.get("query", ""))
            type_text(t)
            speak("Done.")

        elif action == "PRESS_KEY":
            key = params.get("key", "")
            if "+" in key:
                keys = key.split("+")
                hotkey(*keys)
            else:
                press_key(key)

        elif action == "SET_VOLUME":
            try:
                vol = int(params.get("volume", 50))
            except:
                vol = 50
            set_volume(vol)
            speak(f"Volume at {vol}.")

        elif action == "PLAY_MUSIC":
            query = params.get("query", "")
            source_pref = params.get("source", "spotify")
            if "youtube" in text.lower():
                play_youtube(query)
            else:
                play_spotify(query)
            speak(f"Playing {query + ' ' if query else ''}now.")

        elif action == "STOP_MUSIC":
            pyautogui = __import__('pyautogui')
            pyautogui.press('volumemute')
            speak("Stopped.")

        elif action == "BROWSER_NAVIGATE":
            url = params.get("website", params.get("query", ""))
            open_url(url)
            speak("Done.")

        elif action == "BROWSER_SWITCH_TAB":
            # Use keyboard shortcut to cycle tabs
            tab_name = params.get("query", params.get("app_name", ""))
            try:
                from browser import switch_to_tab
                result = switch_to_tab(tab_name)
                speak(f"Switched to {tab_name}.")
            except:
                hotkey('ctrl', 'tab')
                speak(f"Switched tab.")

        elif action == "BROWSER_NEW_TAB":
            url = params.get("website", "")
            hotkey('ctrl', 't')
            if url:
                time.sleep(0.5)
                open_url(url)
            speak("New tab.")

        elif action == "BROWSER_CLOSE_TAB":
            hotkey('ctrl', 'w')
            speak("Tab closed.")

        elif action == "BROWSER_CLICK":
            target = params.get("query", params.get("text", ""))
            try:
                from browser import click
                click(target)
            except:
                speak(f"I'll try clicking {target}.")
                import pyautogui as pg
                pg.hotkey('ctrl', 'f')
                time.sleep(0.3)
                pg.typewrite(target, interval=0.05)

        elif action == "BROWSER_TYPE":
            t = params.get("text", params.get("query", ""))
            enter = "enter" in text.lower() or "search" in text.lower() or "send" in text.lower()
            type_text(t)
            if enter:
                press_key('enter')
            speak("Done.")

        elif action == "BROWSER_SCROLL":
            if "up" in text.lower():
                scroll_page("up")
            else:
                scroll_page("down")

        elif action == "BROWSER_READ":
            try:
                from browser import get_page_content
                content = get_page_content()
                messages = jupiter_respond(
                    f"Read this page content and summarize it for Devansh: {content[:2000]}",
                    messages
                )
            except:
                speak("I can't read that page right now.")

        elif action == "START_LECTURE":
            subject = params.get("subject", "")
            speak(f"Lecture mode on{', ' + subject if subject else ''}. Taking notes.")
            from lecturer import start_lecture
            lecture_mode = True
            threading.Thread(target=lambda: start_lecture(subject), daemon=True).start()

        elif action == "STOP_LECTURE":
            if lecture_mode:
                from lecturer import stop_lecture
                stop_lecture()
                lecture_mode = False
                speak("Lecture saved and summarized.")
            else:
                speak("No lecture recording.")

        elif action == "LIST_LECTURES":
            from lecturer import list_lectures
            lectures = list_lectures()
            if lectures:
                speak(f"You have {len(lectures)} lectures. Latest: {lectures[0].replace('_',' ').replace('.md','')}")
            else:
                speak("No lectures yet.")

        elif action == "STOP_LISTENING":
            listening_active = False
            update_state(listening=False)
            speak("Going quiet.")

        elif action == "START_LISTENING":
            listening_active = True
            speak("Back.")

        elif action == "CORRECT_SPELLING":
            correction = params.get("correction", "")
            if correction:
                save_correction(text.split()[-1], correction)
                speak("Got it.")
            else:
                speak("What's correct?")

        elif action == "WRITE_EMAIL":
            messages = jupiter_respond(
                f"Devansh wants to write an email: {text}. Help him draft it, ask for details if needed.",
                messages
            )

        elif action == "SET_REMINDER":
            messages = jupiter_respond(
                f"Devansh wants a reminder: {text}. Acknowledge and confirm time.",
                messages
            )

        elif action == "SLEEP":
            messages = jupiter_respond(
                "Devansh is saying goodbye. Warm, personal, 1 sentence.", messages
            )
            return messages, True

        else:
            messages = jupiter_respond(text, messages)

    except Exception as e:
        console.print(f"[red]Action error ({action}): {e}[/red]")
        import traceback
        traceback.print_exc()
        messages = jupiter_respond(text, messages)

    return messages, False

def print_banner():
    console.print("\n[bold blue]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold blue]")
    console.print("[bold cyan]             J U P I T E R  —  ONLINE             [/bold cyan]")
    console.print("[bold blue]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold blue]\n")

def main():
    global listening_active, eyes_state

    print_banner()
    console.print("[dim]Loading systems...[/dim]")

    start_server()

    load_whisper()

    mic_stream = start_mic_stream()
    console.print("[dim]Mic always on.[/dim]")

    try:
        from vision import start_eyes, get_eye_state

        def on_gesture(g):
            eyes_state["gesture"] = g
            update_state(gesture=g)
            if g == "thumbs_up":
                threading.Thread(target=lambda: speak("Nice."), daemon=True).start()
            elif g == "peace":
                threading.Thread(target=lambda: speak("Peace."), daemon=True).start()

        def on_mood(m):
            eyes_state["mood"] = m
            update_state(mood=m)
            if m == "tired":
                threading.Thread(
                    target=lambda: speak("You look tired Devansh. Take a break."),
                    daemon=True
                ).start()

        def on_presence(p):
            eyes_state["face_present"] = p
            update_state(face_present=p)

        start_eyes(on_gesture=on_gesture, on_mood=on_mood, on_presence=on_presence)
        console.print("[dim]Camera active.[/dim]")

        def eyes_loop():
            from vision import get_eye_state
            while True:
                try:
                    s = get_eye_state()
                    eyes_state.update(s)
                    update_state(
                        face_present=s.get("face_present", False),
                        mood=s.get("mood", "neutral"),
                        attention=s.get("attention", "unknown"),
                        gesture=s.get("gesture"),
                        screen_context=s.get("screen", "")
                    )
                except:
                    pass
                time.sleep(1)

        threading.Thread(target=eyes_loop, daemon=True).start()

    except Exception as ex:
        console.print(f"[dim]Vision unavailable: {ex}[/dim]")

    load_corrections()

    # Launch Electron GUI
    try:
        subprocess.Popen(
            "npm start",
            cwd="D:\\Jupiter\\gui",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        console.print("[dim]GUI launching...[/dim]")
        time.sleep(2)
    except Exception as ex:
        console.print(f"[dim]GUI error: {ex}[/dim]")

    messages = load_memory()

    if not messages:
        messages = jupiter_respond(
            "Devansh just launched you fully upgraded with camera, screen vision, "
            "browser control, GUI. Greet him — real, short, excited. 2 sentences max.",
            messages
        )
    else:
        messages = jupiter_respond("Devansh is back. 1 sentence.", messages)

    console.print("[dim]Always listening.[/dim]\n")

    while True:
        try:
            update_state(listening=True)
            text = listen(mic_stream=mic_stream, timeout=30)
            update_state(listening=False)

            if text is None:
                continue

            text = text.strip()
            if not text or len(text) < 2:
                continue

            console.print(f"[dim]→ {text}[/dim]")

            if not listening_active:
                if any(w in text.lower() for w in ["jupiter", "hey", "wake up", "come back"]):
                    listening_active = True
                    speak("Back.")
                continue

            if any(b in text.lower() for b in ["goodbye jupiter", "bye jupiter", "good night jupiter"]):
                messages = jupiter_respond("Devansh saying goodbye. 1 warm sentence.", messages)
                break

            context = " | ".join(recent_context[-3:]) if recent_context else ""
            screen = eyes_state.get("screen", "")

            intent = understand_intent(text, context=context, screen_context=screen)
            console.print(f"[dim]Intent: {intent.get('action')} ({intent.get('confidence', 0):.0%})[/dim]")

            messages, should_exit = execute_action(intent, text, messages)

            if should_exit:
                break

            if len(messages) > 100:
                messages = messages[-100:]
                save_memory(messages)

        except KeyboardInterrupt:
            console.print("\n[dim]Shutting down...[/dim]")
            speak("Shutting down. See you soon Devansh.")
            try:
                mic_stream.stop()
            except:
                pass
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            import traceback
            traceback.print_exc()
            continue

if __name__ == "__main__":
    main()