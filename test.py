import warnings
import sys
import os
import traceback
warnings.filterwarnings = lambda *a, **k: None

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox --disable-gpu"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    print("WebEngine imported ok")

    import importlib.util
    spec = importlib.util.spec_from_file_location("jupiter_window", "D:\\Jupiter\\gui\\jupiter_window.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    JupiterWindow = mod.JupiterWindow
    print("window class ok")

    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    print("app ok")

    window = JupiterWindow()
    print("window created ok")

    window.show()
    print("window shown — GUI should be visible now")

    app.exec()

except Exception as e:
    print(traceback.format_exc())
    input("Press Enter to close...")