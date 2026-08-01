import os
import sys
import json
import time
import threading
import warnings
warnings.filterwarnings("ignore")

import logging
logging.getLogger('werkzeug').disabled = True

from flask import Flask, jsonify

app = Flask(__name__)
app.logger.disabled = True

state = {
    "listening": False,
    "thinking": False,
    "jupiter_speaking": False,
    "user_text": "",
    "response_text": "",
    "memory_count": 0,
    "face_present": False,
    "mood": "neutral",
    "attention": "unknown",
    "gesture": None,
    "screen_context": "",
}

state_lock = threading.Lock()

@app.route('/state')
def get_state():
    with state_lock:
        return jsonify(state)

@app.route('/ping')
def ping():
    return 'ok'

def update_state(**kwargs):
    with state_lock:
        state.update(kwargs)

def run_server():
    app.run(host='localhost', port=5000, debug=False, use_reloader=False)

def start_server():
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(0.8)
    print("State server online.")
    return thread

if __name__ == "__main__":
    run_server()