#!/usr/bin/python
import threading

import PyQt5
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings


class OcclusionWindow(QWidget):
    """
    Widget displaying the browser with the SVGEditor.
    """

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """
        Setup occlusion window's interface.
        """

        self.setWindowTitle('Knowledge image occlusion')

        # Load the URL
        view = QWebEngineView()
        view.setUrl(QUrl("http://127.0.0.1:8747/svgedit/dist/editor/index.html"))
        view.showMaximized()

        lay = QVBoxLayout(self)
        lay.addWidget(view)


class OcclusionApplication:
    """
    Wrapper for the occlusion window.
    """

    def __init__(self):
        """
        Performs setup for the occlusion window and launches the mainloop.
        """

        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()

        app = QApplication([])

        # Configure the web engine settings
        settings = QWebEngineSettings.globalSettings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        # Initialize the window
        window = OcclusionWindow()
        window.show()

        # Start the mainloop
        app.exec_()

    @staticmethod
    def start_server():
        """
        Starts a simple HTTP server to serve the editor content.
        """

        import http.server

        server = http.server.HTTPServer(('127.0.0.1', 8747), http.server.SimpleHTTPRequestHandler)
        server.serve_forever()
