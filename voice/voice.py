import os
import sys
import time
import asyncio
import warnings
import threading
import numpy as np
import sounddevice as sd
import queue
import io
import wave
import tempfile
warnings.filterwarnings("ignore")
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from dotenv import load_dotenv
load_dotenv("D:\\Jupiter\\.env")

from groq import Groq
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

JUPITER_VOICE = "en-GB-RyanNeural"
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.008
SILENCE_DURATION = 1.5
INTERRUPT_THRESHOLD = 0.035
SPEECH_TMP = "D:\\Jupiter\\voice\\temp\\speech.mp3"

os.makedirs("D:\\Jupiter\\voice\\temp", exist_ok=True)

is_speaking = threading.Event()
interrupt_flag = threading.Event()
mic_audio_queue = queue.Queue()

local_whisper = None

def load_whisper():
    global local_whisper
    if local_whisper is not None:
        return
    print("Loading faster-whisper fallback...")
    try:
        from faster_whisper import WhisperModel
        local_whisper = WhisperModel("base", device="cpu", compute_type="int8")
        print("Local whisper ready.")
    except Exception as e:
        print(f"Local whisper failed: {e}")

def transcribe_with_groq(audio_bytes):
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
            with wave.open(f, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_bytes)
        
        with open(tmp_path, "rb") as audio_file:
            result = groq_client.audio.transcriptions.create(
                file=("audio.wav", audio_file, "audio/wav"),
                model="whisper-large-v3-turbo",
                language="en",
                response_format="text",
                prompt="Jupiter, Devansh, ANU, Canberra, Australia, COMP1100, Haskell, Python"
            )
        
        try:
            os.remove(tmp_path)
        except:
            pass

        if isinstance(result, str):
            return result.strip()
        return result.text.strip() if hasattr(result, 'text') else str(result).strip()
        
    except Exception as e:
        print(f"Groq transcription error: {e}")
        return None

def transcribe_local(audio_float):
    global local_whisper
    if local_whisper is None:
        load_whisper()
    if local_whisper is None:
        return None
    try:
        segments, _ = local_whisper.transcribe(
            audio_float,
            language="en",
            beam_size=5,
            initial_prompt="Jupiter, Devansh, ANU, Canberra, Australia"
        )
        text = " ".join(s.text for s in segments).strip()
        return text if text else None
    except Exception as e:
        print(f"Local transcription error: {e}")
        return None

def audio_to_bytes(audio_float):
    audio_int16 = (audio_float * 32767).astype(np.int16)
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_int16.tobytes())
    return buffer.getvalue()

def transcribe(audio_data):
    if audio_data.ndim > 1:
        audio_data = audio_data[:, 0]
    audio_float = audio_data.astype(np.float32)
    if np.max(np.abs(audio_float)) > 1.0:
        audio_float = audio_float / 32767.0

    audio_bytes = audio_to_bytes(audio_float)
    result = transcribe_with_groq(audio_bytes)
    
    if not result:
        print("Falling back to local whisper...")
        result = transcribe_local(audio_float)
    
    return result

async def _speak_async(text):
    import edge_tts
    import pygame

    clean = (text
        .replace("**", "").replace("*", "")
        .replace("#", "").replace("`", "")
        .replace("—", " ").replace("–", " ")
        .strip()
    )
    if not clean:
        return

    interrupt_flag.clear()
    is_speaking.set()

    try:
        communicate = edge_tts.Communicate(clean, JUPITER_VOICE)
        await communicate.save(SPEECH_TMP)

        if not os.path.exists(SPEECH_TMP):
            return

        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.music.load(SPEECH_TMP)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            if interrupt_flag.is_set():
                pygame.mixer.music.stop()
                break
            time.sleep(0.05)

        pygame.mixer.music.unload()
        pygame.mixer.quit()

        try:
            os.remove(SPEECH_TMP)
        except:
            pass

    except Exception as e:
        print(f"Speak error: {e}")
    finally:
        is_speaking.clear()
        interrupt_flag.clear()

def speak(text):
    try:
        asyncio.run(_speak_async(text))
    except Exception as e:
        print(f"Speak error: {e}")

def mic_stream_callback(indata, frames, time_info, status):
    mic_audio_queue.put(indata.copy())
    if is_speaking.is_set():
        vol = float(np.sqrt(np.mean(indata**2)))
        if vol > INTERRUPT_THRESHOLD:
            interrupt_flag.set()

def start_mic_stream():
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        callback=mic_stream_callback,
        dtype='float32',
        blocksize=1024
    )
    stream.start()
    return stream

def should_respond(text):
    if not text or len(text.strip()) < 2:
        return False

    text_lower = text.lower().strip()

    ignore = ["uh", "um", "hmm", "hm", "ah", "oh"]
    if text_lower in ignore:
        return False

    if len(text.split()) >= 3:
        return True

    if text.strip().endswith("?"):
        return True

    triggers = [
        "jupiter", "hey", "what", "how", "why", "when", "where", "who",
        "can you", "could you", "help", "open", "close", "play", "stop",
        "search", "find", "show", "tell", "need", "want", "think",
    ]
    return any(t in text_lower for t in triggers)

def listen(mic_stream=None, timeout=30):
    chunks = []
    silence_start = None
    speech_detected = False
    start_time = time.time()

    while not mic_audio_queue.empty():
        mic_audio_queue.get_nowait()

    while True:
        if time.time() - start_time > timeout:
            break

        try:
            chunk = mic_audio_queue.get(timeout=0.1)
        except:
            continue

        if is_speaking.is_set():
            silence_start = None
            speech_detected = False
            chunks = []
            continue

        chunks.append(chunk)
        vol = float(np.sqrt(np.mean(chunk**2)))

        if vol > SILENCE_THRESHOLD:
            speech_detected = True
            silence_start = None
        else:
            if speech_detected:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > SILENCE_DURATION:
                    break

    if not speech_detected or not chunks:
        return None

    audio = np.concatenate(chunks, axis=0)
    return transcribe(audio)

if __name__ == "__main__":
    load_whisper()
    speak("Voice upgrade complete. I now use Groq's Whisper for much better accuracy.")
    print("Say something:")
    stream = start_mic_stream()
    text = listen(stream)
    if text:
        print(f"You said: {text}")
        speak(f"I heard: {text}")
    stream.stop()