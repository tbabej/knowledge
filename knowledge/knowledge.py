import os
import re
import sys
import vim

# Insert the knowledge on the python path
BASE_DIR = vim.eval("s:plugin_path")
sys.path.insert(0, os.path.join(BASE_DIR, 'knowledge'))

from proxy import AnkiProxy
proxy = AnkiProxy(os.path.expanduser('~/Documents/Anki/User 1/collection.anki2'))
