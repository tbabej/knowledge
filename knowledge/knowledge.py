import os
import re
import sys
import vim

# Insert the knowledge on the python path
BASE_DIR = vim.eval("s:plugin_path")
sys.path.insert(0, os.path.join(BASE_DIR, 'knowledge'))

from proxy import AnkiProxy
from wikinote import WikiNote

#proxy = AnkiProxy(os.path.expanduser('~/Documents/Anki/User 1/collection.anki2'))
proxy = MnemosyneProxy()


class HeaderStack(object):
    """
    A stack that keeps track of the metadata defined by the header
    hierarchy.
    """

    def __init__(self):
        self.headers = dict()

    def push(self, header):
        pushed_level = len(header.data['header_start'])

        # Pop any headers on the lower levels
        kept_levels = {
            key: self.headers[key]
            for key in self.headers.keys()
            if key < pushed_level
        }
        self.headers = kept_levels

        # Set the currently pushed level
        self.headers[pushed_level] = header

    def get(self):
        return set(self.headers.values())



def create_notes():
    """
    Loops over current buffer and adds any new notes to Anki.
    """

    stack = HeaderStack()

    for line_number in range(len(vim.current.buffer)):
        note = WikiNote.from_line(line_number, proxy, tags=stack.get())

        if note is None:
            header = Header.from_line(line_number)
            if header is not None:
                stack.push(header)

        elif not note.created:
            note.save()
