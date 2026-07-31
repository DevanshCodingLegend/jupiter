import sys
import os
import warnings
import threading
import time
import importlib.util
warnings.filterwarnings("ignore")

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox --disable-gpu"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

from PyQt6.QtWebEngineWidgets import QWebEngineView

sys.path.insert(0, "D:\\Jupiter\\brain")
sys.path.insert(0, "D:\\Jupiter\\voice")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, pyqtSignal, QObject

from brain import jupiter_thinks, load_memory, save_memory, log_conversation
from voice import speak, listen, load_whisper

spec = importlib.util.spec_from_file_location(
    "jupiter_window", "D:\\Jupiter\\gui\\jupiter_window.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
JupiterWindow = mod.JupiterWindow

WAKE_WORDS = ["hey jupiter", "jupiter", "yo jupiter", "ok jupiter"]


def contains_wake_word(text):
    if text is None:
        return False
    return any(w in text.lower() for w in WAKE_WORDS)


def remove_wake_word(text):
    t = text.lower()
    for w in WAKE_WORDS:
        t = t.replace(w, "").strip()
    return t.lstrip(",.").strip()


class JupiterCore(QObject):
    sig_listening = pyqtSignal()
    sig_thinking = pyqtSignal()
    sig_speaking = pyqtSignal()
    sig_idle = pyqtSignal()
    sig_user = pyqtSignal(str)
    sig_response = pyqtSignal(str)
    sig_memory = pyqtSignal(int)

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.messages = load_memory()
        self.running = True

        self.sig_listening.connect(window.set_listening)
        self.sig_thinking.connect(window.set_thinking)
        self.sig_speaking.connect(window.set_speaking)
        self.sig_idle.connect(window.set_idle)
        self.sig_user.connect(window.show_user)
        self.sig_response.connect(window.show_response)
        self.sig_memory.connect(window.set_memory_count)

    def respond(self, user_input):
        self.sig_user.emit(user_input)
        self.sig_thinking.emit()
        self.messages.append({"role": "user", "content": user_input})
        response, source = jupiter_thinks(self.messages)
        self.messages.append({"role": "assistant", "content": response})
        save_memory(self.messages)
        log_conversation(user_input, response, source)
        self.sig_memory.emit(len(self.messages))
        self.sig_response.emit(response)
        self.sig_speaking.emit()
        speak(response)
        self.sig_idle.emit()

    def run(self):
        load_whisper()
        time.sleep(2)

        if not self.messages:
            self.respond("Devansh just launched you for the first time with your holographic GUI. Greet him — short, warm, real. 2 sentences max.")
        else:
            self.respond("Devansh is back. Greet him in 1 sentence.")

        while self.running:
            try:
                self.sig_listening.emit()
                text = listen()

                if text is None:
                    self.sig_idle.emit()
                    continue

                print(f"Heard: {text}")

                if any(b in text.lower() for b in ["goodbye", "good night", "bye jupiter", "sleep"]):
                    self.respond("Devansh is leaving. Say goodbye warmly in 1 sentence.")
                    self.running = False
                    break

                if contains_wake_word(text):
                    clean = remove_wake_word(text)
                    if clean:
                        self.respond(clean)
                    else:
                        self.sig_speaking.emit()
                        speak("Yes, Devansh?")
                        self.sig_idle.emit()
                else:
                    self.sig_idle.emit()

                if len(self.messages) > 100:
                    self.messages = self.messages[-100:]
                    save_memory(self.messages)

            except Exception as e:
                print(f"Error: {e}")
                self.sig_idle.emit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Jupiter")

    window = JupiterWindow()
    window.show()

    core = JupiterCore(window)
    thread = threading.Thread(target=core.run, daemon=True)
    QTimer.singleShot(1000, thread.start)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()