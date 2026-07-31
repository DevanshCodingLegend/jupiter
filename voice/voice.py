import os
import time
import asyncio
import warnings
import traceback
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
warnings.filterwarnings("ignore")
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

JUPITER_VOICE = "en-GB-RyanNeural"
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 2.0
SPEECH_TMP = "D:\\Jupiter\\voice\\temp\\speech.mp3"
LISTEN_TMP = "D:\\Jupiter\\voice\\temp\\listen.wav"

os.makedirs("D:\\Jupiter\\voice\\temp", exist_ok=True)

whisper_model = None

def load_whisper():
    global whisper_model
    if whisper_model is not None:
        return
    print("Loading Whisper...")
    import whisper
    whisper_model = whisper.load_model("base")
    print("Whisper ready.")

async def _speak_async(text):
    import edge_tts
    import pygame
    clean = text.replace("**","").replace("*","").replace("#","").replace("`","").replace("—"," ").strip()
    if not clean:
        return
    communicate = edge_tts.Communicate(clean, JUPITER_VOICE)
    await communicate.save(SPEECH_TMP)
    if not os.path.exists(SPEECH_TMP):
        return
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.mixer.music.load(SPEECH_TMP)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.05)
    pygame.mixer.music.unload()
    pygame.mixer.quit()
    try:
        os.remove(SPEECH_TMP)
    except:
        pass

def speak(text):
    try:
        asyncio.run(_speak_async(text))
    except Exception as e:
        print(f"Speak error: {e}")

def record_until_silence():
    print("\nListening...")
    chunks = []
    silence_start = None
    recording = True
    speech_detected = False

    def callback(indata, frames, time_info, status):
        nonlocal silence_start, recording, speech_detected
        if not recording:
            return
        chunks.append(indata.copy())
        vol = float(np.sqrt(np.mean(indata**2)))
        if vol > SILENCE_THRESHOLD:
            speech_detected = True
            silence_start = None
        else:
            if speech_detected:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > SILENCE_DURATION:
                    recording = False

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback, dtype='float32', blocksize=1024):
            timeout = time.time() + 30
            while recording and time.time() < timeout:
                time.sleep(0.05)
    except Exception as e:
        print(f"Recording error: {e}")
        return None

    if not speech_detected or not chunks:
        return None

    return np.concatenate(chunks, axis=0)

def transcribe(audio_data):
    import whisper
    if whisper_model is None:
        load_whisper()
    try:
        if audio_data.ndim > 1:
            audio_data = audio_data[:, 0]
        audio_float = audio_data.astype(np.float32)
        if np.max(np.abs(audio_float)) > 1.0:
            audio_float = audio_float / 32767.0
        result = whisper_model.transcribe(audio_float, language="en", fp16=False)
        text = result["text"].strip()
        return text if text else None
    except Exception as e:
        print(f"Transcribe error: {e}")
        traceback.print_exc()
        return None

def listen():
    audio = record_until_silence()
    if audio is None:
        return None
    return transcribe(audio)

if __name__ == "__main__":
    load_whisper()
    speak("Jupiter voice systems online. I can hear and speak now, Devansh.")
    print("Say something:")
    text = listen()
    if text:
        print(f"You said: {text}")
        speak(f"I heard: {text}")
    else:
        print("Nothing detected.")