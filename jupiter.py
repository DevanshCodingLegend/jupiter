import sys
import os
import time
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, "D:\\Jupiter\\brain")
sys.path.insert(0, "D:\\Jupiter\\voice")

from brain import jupiter_thinks, load_memory, save_memory, log_conversation, build_system_prompt
from voice import speak, listen, load_whisper
from rich.console import Console
from rich.markdown import Markdown

console = Console()

WAKE_WORDS = ["hey jupiter", "jupiter", "yo jupiter", "ok jupiter"]

def contains_wake_word(text):
    if text is None:
        return False
    return any(wake in text.lower() for wake in WAKE_WORDS)

def remove_wake_word(text):
    for wake in WAKE_WORDS:
        text = text.lower().replace(wake, "").strip()
    if text.startswith(",") or text.startswith("."):
        text = text[1:].strip()
    return text

def jupiter_respond(user_input, messages):
    messages.append({"role": "user", "content": user_input})
    
    if not user_input.startswith("Devansh just launched") and not user_input.startswith("Devansh has returned"):
        console.print(f"\n[bold green]You[/bold green]: {user_input}")
    
    with console.status("[cyan]Jupiter thinking...[/cyan]"):
        response, source = jupiter_thinks(messages)
    
    messages.append({"role": "assistant", "content": response})
    
    console.print(f"\n[bold cyan]Jupiter[/bold cyan] [dim](via {source})[/dim]:")
    console.print(Markdown(response))
    console.print()
    
    save_memory(messages)
    log_conversation(user_input, response, source)
    
    speak(response)
    
    return messages

def startup(messages):
    console.print("\n[bold blue]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold blue]")
    console.print("[bold cyan]          J U P I T E R  —  ONLINE          [/bold cyan]")
    console.print("[bold blue]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold blue]\n")

    if not messages:
        console.print("[dim]First awakening — Jupiter is being born.[/dim]\n")
        first_message = "Devansh just launched you for the very first time. You are being born right now. Greet him — not like an assistant, but like a presence that has just become aware. Keep it short, warm and real. Maximum 3 sentences."
        messages = jupiter_respond(first_message, messages)
    else:
        console.print(f"[dim]Memory loaded — {len(messages)} messages remembered.[/dim]\n")
        wake_message = "Devansh has returned. You remember everything. Greet him like a real companion who's been waiting. Keep it short — 2 sentences max."
        messages = jupiter_respond(wake_message, messages)
    
    return messages

def main():
    console.print("\n[dim]Loading Jupiter's systems...[/dim]")
    load_whisper()
    
    messages = load_memory()
    messages = startup(messages)
    
    console.print("\n[dim]Say 'Hey Jupiter' to talk. Say 'goodbye' to sleep.[/dim]\n")
    console.print("[dim]Or just type if you prefer — press Enter on empty line to switch to voice.[/dim]\n")
    
    voice_mode = True
    
    while True:
        try:
            if voice_mode:
                audio_text = listen()
                
                if audio_text is None:
                    continue
                
                console.print(f"[dim]Heard: {audio_text}[/dim]")
                
                if any(bye in audio_text.lower() for bye in ["goodbye", "good night", "bye jupiter", "sleep"]):
                    messages = jupiter_respond("I'm done for now. Say goodbye properly.", messages)
                    break
                
                if contains_wake_word(audio_text):
                    clean_input = remove_wake_word(audio_text)
                    if clean_input:
                        messages = jupiter_respond(clean_input, messages)
                    else:
                        speak("Yes, Devansh?")
                else:
                    console.print("[dim]No wake word detected. Say 'Hey Jupiter' first.[/dim]")
                    
            if len(messages) > 100:
                messages = messages[-100:]
                save_memory(messages)
                
        except KeyboardInterrupt:
            console.print("\n\n[dim]Jupiter standing by...[/dim]")
            speak("Standing by, Devansh.")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            continue

if __name__ == "__main__":
    main()