import cv2
import mediapipe as mp
import numpy as np
import threading
import time
import json
import os
import warnings
warnings.filterwarnings("ignore")

# MediaPipe solutions
mp_face = mp.solutions.face_detection
mp_hands = mp.solutions.hands
mp_face_mesh = mp.solutions.face_mesh
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

class JupiterEyes:
    def __init__(self):
        self.cap = None
        self.running = False
        self.thread = None
        
        # State
        self.face_detected = False
        self.face_present = False
        self.hands_detected = []
        self.gesture = None
        self.mood = "neutral"
        self.looking_at_screen = False
        self.attention_level = "focused"
        
        # Screen context
        self.screen_context = ""
        self.screen_thread = None
        
        # Callbacks
        self.on_gesture = None
        self.on_mood_change = None
        self.on_presence_change = None
        
        # MediaPipe models
        self.face_detector = mp_face.FaceDetection(
            model_selection=0,
            min_detection_confidence=0.7
        )
        self.hands_detector = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Gesture history for smoothing
        self.gesture_history = []
        self.last_gesture_time = 0
        self.gesture_cooldown = 1.0
        
        # Presence tracking
        self.last_seen = None
        self.absence_threshold = 5.0
        
        print("Jupiter Eyes initialized.")

    def detect_gesture(self, hand_landmarks, hand_label):
        lm = hand_landmarks.landmark
        
        # Finger tip and pip indices
        tips = [4, 8, 12, 16, 20]
        pips = [3, 6, 10, 14, 18]
        
        fingers_up = []
        
        # Thumb
        if hand_label == "Right":
            fingers_up.append(1 if lm[4].x < lm[3].x else 0)
        else:
            fingers_up.append(1 if lm[4].x > lm[3].x else 0)
        
        # Other fingers
        for tip, pip in zip(tips[1:], pips[1:]):
            fingers_up.append(1 if lm[tip].y < lm[pip].y else 0)
        
        count = sum(fingers_up)
        
        # Gesture recognition
        if count == 0:
            return "fist"
        elif count == 5:
            return "open_hand"
        elif fingers_up == [0, 1, 0, 0, 0]:
            return "point"
        elif fingers_up == [0, 1, 1, 0, 0]:
            return "peace"
        elif fingers_up == [1, 1, 0, 0, 0]:
            return "gun"
        elif fingers_up == [1, 0, 0, 0, 1]:
            return "rock"
        elif count == 1 and fingers_up[4] == 1:
            return "pinky"
        elif fingers_up == [1, 1, 1, 0, 0]:
            return "three"
        elif count == 4 and fingers_up[0] == 0:
            return "four"
        elif fingers_up == [1, 0, 0, 0, 0]:
            return "thumbs_up" if lm[4].y < lm[3].y else "thumbs_down"
        else:
            return f"{count}_fingers"

    def detect_mood_from_landmarks(self, face_landmarks, frame_shape):
        if not face_landmarks:
            return "neutral"
        
        try:
            lm = face_landmarks.landmark
            h, w = frame_shape[:2]
            
            # Mouth corners
            left_mouth = lm[61]
            right_mouth = lm[291]
            top_lip = lm[13]
            bottom_lip = lm[14]
            
            mouth_width = abs(right_mouth.x - left_mouth.x)
            mouth_height = abs(bottom_lip.y - top_lip.y)
            
            # Eye openness
            left_eye_top = lm[159]
            left_eye_bottom = lm[145]
            eye_height = abs(left_eye_top.y - left_eye_bottom.y)
            
            # Eyebrows
            left_brow = lm[70]
            left_eye_center = lm[33]
            brow_distance = abs(left_brow.y - left_eye_center.y)
            
            # Simple heuristics
            if mouth_height > 0.03 and mouth_width > 0.06:
                return "happy"
            elif brow_distance < 0.02:
                return "focused"
            elif eye_height < 0.015:
                return "tired"
            elif mouth_height < 0.01 and brow_distance > 0.04:
                return "surprised"
            else:
                return "neutral"
                
        except:
            return "neutral"

    def detect_attention(self, face_landmarks):
        if not face_landmarks:
            return "away"
        
        try:
            lm = face_landmarks.landmark
            
            nose = lm[1]
            left_eye = lm[33]
            right_eye = lm[263]
            
            eye_center_x = (left_eye.x + right_eye.x) / 2
            nose_offset = nose.x - eye_center_x
            
            if abs(nose_offset) < 0.05:
                return "focused"
            elif abs(nose_offset) < 0.15:
                return "glancing"
            else:
                return "away"
        except:
            return "unknown"

    def process_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        
        # Face detection
        face_results = self.face_detector.process(rgb)
        face_mesh_results = self.face_mesh.process(rgb)
        hand_results = self.hands_detector.process(rgb)
        
        rgb.flags.writeable = True
        
        # Update face presence
        prev_present = self.face_present
        self.face_present = bool(face_results.detections)
        
        if self.face_present:
            self.last_seen = time.time()
        
        if prev_present != self.face_present and self.on_presence_change:
            self.on_presence_change(self.face_present)
        
        # Mood and attention from face mesh
        if face_mesh_results.multi_face_landmarks:
            face_lm = face_mesh_results.multi_face_landmarks[0]
            new_mood = self.detect_mood_from_landmarks(face_lm, frame.shape)
            self.attention_level = self.detect_attention(face_lm)
            
            if new_mood != self.mood:
                self.mood = new_mood
                if self.on_mood_change:
                    self.on_mood_change(new_mood)
        
        # Hand gesture detection
        gestures_this_frame = []
        if hand_results.multi_hand_landmarks:
            for hand_lm, handedness in zip(
                hand_results.multi_hand_landmarks,
                hand_results.multi_handedness
            ):
                label = handedness.classification[0].label
                gesture = self.detect_gesture(hand_lm, label)
                gestures_this_frame.append(gesture)
        
        # Gesture smoothing and cooldown
        if gestures_this_frame:
            self.gesture_history.append(gestures_this_frame[0])
            if len(self.gesture_history) > 5:
                self.gesture_history.pop(0)
            
            if self.gesture_history:
                stable = max(set(self.gesture_history), key=self.gesture_history.count)
                now = time.time()
                if (stable != self.gesture and
                    stable != "open_hand" and
                    now - self.last_gesture_time > self.gesture_cooldown):
                    
                    self.gesture = stable
                    self.last_gesture_time = now
                    if self.on_gesture:
                        self.on_gesture(stable)
        else:
            self.gesture_history = []
            self.gesture = None
        
        return frame

    def camera_loop(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        if not self.cap.isOpened():
            print("Camera not available.")
            return
        
        print("Camera active — Jupiter can see you.")
        frame_skip = 0
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            frame_skip += 1
            if frame_skip % 2 != 0:
                continue
            
            try:
                self.process_frame(frame)
            except Exception as e:
                pass
            
            time.sleep(0.033)
        
        self.cap.release()

    def screen_vision_loop(self):
        import mss
        from PIL import Image
        import google.generativeai as genai
        from dotenv import load_dotenv
        load_dotenv("D:\\Jupiter\\.env")
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        print("Screen vision active.")
        
        while self.running:
            try:
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    screenshot = sct.grab(monitor)
                    img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                    img = img.resize((1280, 720))
                
                result = model.generate_content([
                    img,
                    "Describe what's on this screen in 2 sentences max. What app is open and what is the person doing? Be concise."
                ])
                
                self.screen_context = result.text.strip()
                
            except Exception as e:
                pass
            
            time.sleep(15)

    def get_state(self):
        return {
            "face_present": self.face_present,
            "mood": self.mood,
            "attention": self.attention_level,
            "gesture": self.gesture,
            "screen": self.screen_context,
            "last_seen_seconds_ago": round(time.time() - self.last_seen, 1) if self.last_seen else None
        }

    def start(self):
        self.running = True
        
        self.thread = threading.Thread(target=self.camera_loop, daemon=True)
        self.thread.start()
        
        self.screen_thread = threading.Thread(target=self.screen_vision_loop, daemon=True)
        self.screen_thread.start()

    def stop(self):
        self.running = False

eyes = None

def start_eyes(on_gesture=None, on_mood=None, on_presence=None):
    global eyes
    eyes = JupiterEyes()
    eyes.on_gesture = on_gesture
    eyes.on_mood_change = on_mood
    eyes.on_presence_change = on_presence
    eyes.start()
    return eyes

def get_eye_state():
    if eyes:
        return eyes.get_state()
    return {}

def get_screen_context():
    if eyes:
        return eyes.screen_context
    return ""

if __name__ == "__main__":
    def on_gesture(g):
        print(f"Gesture: {g}")
    def on_mood(m):
        print(f"Mood: {m}")
    def on_presence(p):
        print(f"Present: {p}")
    
    e = start_eyes(on_gesture, on_mood, on_presence)
    print("Eyes running. Press Ctrl+C to stop.")
    try:
        while True:
            state = get_eye_state()
            print(f"\rMood: {state.get('mood')} | Attention: {state.get('attention')} | Gesture: {state.get('gesture')}    ", end="")
            time.sleep(0.5)
    except KeyboardInterrupt:
        e.stop()