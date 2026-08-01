import os
import sys
import time
import json
import threading
import warnings
import numpy as np
import sounddevice as sd
warnings.filterwarnings("ignore")

from datetime import datetime
from dotenv import load_dotenv
load_dotenv("D:\\Jupiter\\.env")

SAMPLE_RATE = 16000
LECTURE_DIR = "D:\\Jupiter\\memory\\lectures"
os.makedirs(LECTURE_DIR, exist_ok=True)

recording = threading.Event()
whisper_model = None

def load_whisper():
    global whisper_model
    if whisper_model:
        return
    import whisper
    whisper_model = whisper.load_model("base")

def record_chunk(duration=30):
    chunks = []
    def callback(indata, frames, time_info, status):
        chunks.append(indata.copy())
    
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                       callback=callback, dtype='float32'):
        time.sleep(duration)
    
    if not chunks:
        return None
    return np.concatenate(chunks, axis=0)

def transcribe_chunk(audio):
    if not whisper_model:
        load_whisper()
    try:
        if audio.ndim > 1:
            audio = audio[:, 0]
        audio = audio.astype(np.float32)
        result = whisper_model.transcribe(audio, language="en", fp16=False)
        return result["text"].strip()
    except:
        return ""

def summarize_lecture(transcript, subject=""):
    from groq import Groq
    import os
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    prompt = f"""You are Jupiter, Devansh's AI companion. He just attended a lecture{' on ' + subject if subject else ''}.
    
Here is the transcript:
{transcript}

Create a comprehensive study summary with:
1. **Key Concepts** — main ideas covered
2. **Important Details** — facts, formulas, definitions
3. **Examples Used** — any examples from the lecture
4. **Key Takeaways** — what to remember
5. **Study Questions** — 3-5 questions to test understanding

Be thorough but clear. This will help Devansh study."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048
    )
    return response.choices[0].message.content

def start_lecture(subject=""):
    load_whisper()
    recording.set()
    
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    safe_subject = subject.replace(" ", "_") if subject else "lecture"
    session_file = os.path.join(LECTURE_DIR, f"{date_str}_{safe_subject}.json")
    
    session = {
        "subject": subject,
        "date": datetime.now().isoformat(),
        "transcript": "",
        "summary": "",
        "chunks": []
    }
    
    print(f"\nLecture recording started. Subject: {subject or 'Unknown'}")
    print("Say 'Jupiter stop lecture' to end.\n")
    
    full_transcript = ""
    chunk_num = 0
    
    while recording.is_set():
        chunk_num += 1
        print(f"Recording chunk {chunk_num}...")
        audio = record_chunk(duration=30)
        
        if audio is None:
            continue
        
        text = transcribe_chunk(audio)
        if text:
            full_transcript += f" {text}"
            session["chunks"].append({
                "chunk": chunk_num,
                "text": text,
                "time": datetime.now().isoformat()
            })
            
            with open(session_file, "w") as f:
                session["transcript"] = full_transcript.strip()
                json.dump(session, f, indent=2)
            
            print(f"Chunk {chunk_num}: {text[:80]}...")
    
    print("\nGenerating lecture summary...")
    summary = summarize_lecture(full_transcript, subject)
    session["summary"] = summary
    
    with open(session_file, "w") as f:
        json.dump(session, f, indent=2)
    
    summary_file = os.path.join(LECTURE_DIR, f"{date_str}_{safe_subject}_SUMMARY.md")
    with open(summary_file, "w") as f:
        f.write(f"# {subject} — Lecture Notes\n")
        f.write(f"**Date:** {datetime.now().strftime('%A, %d %B %Y')}\n\n")
        f.write(summary)
    
    print(f"\nLecture saved: {session_file}")
    print(f"Summary saved: {summary_file}")
    
    return summary

def stop_lecture():
    recording.clear()
    print("Lecture recording stopped.")

def list_lectures():
    files = [f for f in os.listdir(LECTURE_DIR) if f.endswith("_SUMMARY.md")]
    return sorted(files, reverse=True)

def get_lecture_summary(filename):
    path = os.path.join(LECTURE_DIR, filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    return None

if __name__ == "__main__":
    print("Testing lecture mode...")
    start_lecture("Test Lecture")