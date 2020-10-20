#!/usr/bin/python
import os
import pathlib
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlencode

import imagesize
import PyQt5
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEngineProfile

from knowledge import config, constants, regexp


class OcclusionWindow(QWidget):
    """
    Widget displaying the browser with the SVGEditor.
    """

    def __init__(self, svg_filepath):
        super().__init__()
        self.value = None
        self.svg_filepath = svg_filepath
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

        # Determine the dimensions of the image
        width, height = imagesize.get('background.png')

        editor_options = {
            'showRulers': 'false',
            'initTool': 'rect',
            'initStroke[color]': '292828',
            'initStroke[width]': '3',
            'initFill[color]': 'ffedaf',
            'dimensions': f'{width},{height}',
            'bkgd_url': '../background.png',
        }

        # Load the SVG content, if exists
        if os.path.exists(self.svg_filepath):
            with open(self.svg_filepath, 'r') as f:
                editor_options['source'] = f'data:image/svg+xml;utf8,{f.read()}'

        # Open the SVG editor
        editor_url = f"http://localhost:8747/editor/index.html?{urlencode(editor_options)}"
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

    def __init__(self, svg_filepath):
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
        self.window = OcclusionWindow(svg_filepath)
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

        # Create a temporary directory and change our working directory
        tmpdir = Path(tempfile.mkdtemp(prefix='knowledge-occ-'))
        os.chdir(tmpdir)

        # Setup content for the server
        media_file_path = Path(config.DATA_FOLDER) / 'media' / media_file
        editor_path = constants.PLUGIN_ROOT_DIR / 'svgedit/dist/editor'
        os.symlink(media_file_path, 'background.png')
        os.symlink(editor_path, 'editor')

        occlusions_dir = Path(config.DATA_FOLDER) / 'occlusions'
        occlusions_dir.mkdir(exist_ok=True)

        svg_filepath = regexp.EXTENSION.sub('.svg', str(occlusions_dir / media_file))
        instance = cls(svg_filepath)

        with open(svg_filepath, 'w') as f:
            f.write(instance.window.value)

        # Convert the SVG to PNG
        subprocess.run([
            'convert',
            '-transparent', 'white',
            svg_filepath,
            regexp.EXTENSION.sub('.png', svg_filepath)
        ])
