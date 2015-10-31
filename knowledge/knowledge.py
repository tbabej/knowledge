import os
import re
import sys
import vim

# Insert the knowledge on the python path
BASE_DIR = vim.eval("s:plugin_path")
sys.path.insert(0, os.path.join(BASE_DIR, 'knowledge'))

from proxy import AnkiProxy
from wikinote import WikiNote

proxy = AnkiProxy(os.path.expanduser('~/Documents/Anki/User 1/collection.anki2'))

def create_notes():
    """
    Loops over current buffer and adds any new notes to Anki.
    """

    for line_number in range(len(vim.current.buffer)):
        note = WikiNote.from_line(line_number, proxy)

        if note is None:
            continue

        if not note.created:
            note.save()
