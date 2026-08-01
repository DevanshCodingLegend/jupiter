import os
import sys
import time
import subprocess
import warnings
import psutil
warnings.filterwarnings("ignore")

import pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

# Find Chrome path automatically
def get_chrome_path():
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return "chrome"

CHROME = get_chrome_path()

APP_MAP = {
    "chrome": CHROME,
    "google chrome": CHROME,
    "browser": CHROME,
    "spotify": os.path.expanduser(r"~\AppData\Roaming\Spotify\Spotify.exe"),
    "vscode": r"C:\Users\devan\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "vs code": r"C:\Users\devan\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "visual studio code": r"C:\Users\devan\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "terminal": "wt.exe",
    "powershell": "powershell.exe",
    "discord": os.path.expanduser(r"~\AppData\Local\Discord\app-*\Discord.exe"),
}

def open_app(app_name):
    app_lower = app_name.lower().strip()
    
    # Direct map
    if app_lower in APP_MAP:
        path = APP_MAP[app_lower]
        try:
            subprocess.Popen([path], shell=False)
            return f"Opening {app_name}."
        except:
            try:
                subprocess.Popen(path, shell=True)
                return f"Opening {app_name}."
            except Exception as e:
                return f"Couldn't open {app_name}: {e}"
    
    # Try directly
    try:
        subprocess.Popen(app_name, shell=True)
        return f"Opening {app_name}."
    except Exception as e:
        return f"Couldn't open {app_name}: {e}"

def open_url(url):
    if not url.startswith("http"):
        if "." in url:
            url = f"https://{url}"
        else:
            url = f"https://www.google.com/search?q={url.replace(' ', '+')}"
    try:
        subprocess.Popen([CHROME, url])
        return f"Opening {url}"
    except:
        os.startfile(url)
        return f"Opening {url}"

def open_url_new_tab(url):
    if not url.startswith("http"):
        if "." in url:
            url = f"https://{url}"
        else:
            url = f"https://www.google.com/search?q={url.replace(' ', '+')}"
    try:
        subprocess.Popen([CHROME, "--new-tab", url])
        return f"Opening {url} in new tab"
    except:
        os.startfile(url)
        return f"Opening {url}"

def close_app(app_name):
    killed = []
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            if app_name.lower() in proc.info['name'].lower():
                proc.kill()
                killed.append(proc.info['name'])
        except:
            pass
    return f"Closed {', '.join(killed)}." if killed else f"No process found for {app_name}."

def type_text(text):
    time.sleep(0.3)
    pyautogui.typewrite(text, interval=0.04)
    return f"Typed: {text}"

def press_key(key):
    pyautogui.press(key)
    return f"Pressed {key}."

def hotkey(*keys):
    pyautogui.hotkey(*keys)
    return f"Pressed {'+'.join(keys)}."

def take_screenshot():
    import mss
    from PIL import Image
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        img = img.resize((1280, 720))
        path = "D:\\Jupiter\\memory\\screen.jpg"
        img.save(path, "JPEG", quality=60)
        return path

def get_active_window_title():
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value
    except:
        return "Unknown"

def get_system_info():
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    battery = psutil.sensors_battery()
    info = {
        "cpu_percent": cpu,
        "ram_used_gb": round(ram.used / (1024**3), 1),
        "ram_total_gb": round(ram.total / (1024**3), 1),
        "ram_percent": ram.percent,
        "active_window": get_active_window_title(),
    }
    if battery:
        info["battery_percent"] = battery.percent
        info["plugged_in"] = battery.power_plugged
    return info

def search_web(query):
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    open_url(url)
    return f"Searching for: {query}"

def scroll_page(direction="down", amount=3):
    if direction == "down":
        pyautogui.scroll(-amount * 100)
    else:
        pyautogui.scroll(amount * 100)

def click_at(x, y):
    pyautogui.click(x, y)

def right_click_at(x, y):
    pyautogui.rightClick(x, y)

def move_mouse(x, y):
    pyautogui.moveTo(x, y, duration=0.2)

def set_volume(level):
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level / 100, None)
        return f"Volume set to {level}%"
    except:
        for _ in range(50):
            pyautogui.press('volumedown')
        for _ in range(int(level / 2)):
            pyautogui.press('volumeup')
        return f"Volume adjusted."

def play_spotify(query=""):
    spotify_path = os.path.expanduser(r"~\AppData\Roaming\Spotify\Spotify.exe")
    if query:
        url = f"https://open.spotify.com/search/{query.replace(' ', '%20')}"
        open_url(url)
    elif os.path.exists(spotify_path):
        subprocess.Popen([spotify_path])
    else:
        open_url("https://open.spotify.com")

def play_youtube(query=""):
    if query:
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    else:
        url = "https://www.youtube.com"
    open_url(url)

if __name__ == "__main__":
    print(get_chrome_path())
    print(get_system_info())