import sys
import os
import warnings
warnings.filterwarnings("ignore")

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox --disable-gpu"
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QUrl, QPoint, pyqtSignal
from PyQt6.QtGui import QColor


class JupiterWindow(QMainWindow):
    close_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setWindowTitle("JUPITER")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setStyleSheet("QMainWindow { background-color: rgb(0, 5, 15); }")

        screen = QApplication.primaryScreen().geometry()
        w, h = 420, 580
        x = screen.width() - w - 20
        y = screen.height() - h - 60
        self.setGeometry(x, y, w, h)

        self.browser = QWebEngineView(self)
        from PyQt6.QtWebEngineCore import QWebEngineSettings
        self.browser.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.browser.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        self.browser.page().setBackgroundColor(QColor(0, 5, 15))
        self.setCentralWidget(self.browser)

        gui_path = "D:/Jupiter/gui/jupiter_gui.html"
        self.browser.setUrl(QUrl.fromLocalFile(os.path.abspath(gui_path)))
        self.browser.loadFinished.connect(self.on_loaded)

        self.drag_pos = QPoint()
        self.dragging = False

    def on_loaded(self, ok):
        if ok:
            print("Jupiter GUI online.")
            self.browser.page().urlChanged.connect(self.handle_url)
        else:
            print("GUI failed to load.")

    def handle_url(self, url):
        if url.scheme() == "jupiter" and url.host() == "close":
            self.hide()

    def run_js(self, js):
        try:
            self.browser.page().runJavaScript(js)
        except Exception as e:
            print(f"JS error: {e}")

    def set_listening(self):
        self.run_js("window.jupiterSetListening()")

    def set_thinking(self):
        self.run_js("window.jupiterSetThinking()")

    def set_speaking(self):
        self.run_js("window.jupiterSetSpeaking()")

    def set_idle(self):
        self.run_js("window.jupiterSetIdle()")

    def show_user(self, text):
        safe = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
        self.run_js(f"window.jupiterShowUser('{safe}')")

    def show_response(self, text):
        safe = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
        self.run_js(f"window.jupiterShowResponse('{safe}')")

    def set_memory_count(self, count):
        self.run_js(f"window.jupiterSetMemory({count})")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()
            self.dragging = True

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.drag_pos
            self.move(self.pos() + delta)
            self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = JupiterWindow()
    window.show()
    sys.exit(app.exec())