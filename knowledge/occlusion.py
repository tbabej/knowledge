#!/usr/bin/python
import os
import pathlib
import threading
import time
from pathlib import Path
from urllib.parse import urlencode

import PyQt5
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEngineProfile

from knowledge import config


class OcclusionWindow(QWidget):
    """
    Widget displaying the browser with the SVGEditor.
    """

    def __init__(self):
        super().__init__()
        self.value = None
        self.init_ui()

    def init_ui(self):
        """
        Setup occlusion window's interface.
        """

        self.setWindowTitle('Knowledge image occlusion')

        # Load the URL
        view = QWebEngineView()
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpCacheType(QWebEngineProfile.NoCache)

        # Open the SVG editor
        editor_url = "http://localhost:8747/svgedit/dist/editor/index.html?{options}".format(
            options=urlencode({
                'showRulers': 'false',
                'initTool': 'rect',
                'initStroke[color]': '292828',
                'initStroke[width]': '3',
                'initFill[color]': 'ffedaf',
                'dimensions': '940,411',
                'bkgd_url': 'background.png'
            })
        )

        view.setUrl(QUrl(editor_url))
        view.showMaximized()

        self.view = view

        layout = QVBoxLayout(self)
        layout.addWidget(view)

    def save_svg(self, value):
        self.value = value

    def closeEvent(self, event):
        page = self.view.page()
        page.runJavaScript(
            'window.editor.canvas.getSvgString();',
            self.save_svg
        )
        time.sleep(0.1)  # necessary for callback to have time to execute
        event.accept()


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
        settings.setAttribute(QWebEngineSettings.ShowScrollBars, False)

        # Initialize the window
        self.window = OcclusionWindow()
        self.window.show()

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

    @classmethod
    def run(cls, media_file: str):
        """
        Change the working directory of the process and launch the application.
        """

        workdir = str(pathlib.Path(__file__).absolute().parent.parent)
        os.chdir(workdir)
        instance = cls()

        occlusions_dir = Path(config.DATA_FOLDER) / 'occlusions'
        occlusions_dir.mkdir(exist_ok=True)

        with open(str(occlusions_dir / media_file) + '.svg', 'w') as f:
            f.write(instance.window.value)
