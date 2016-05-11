from __future__ import print_function
import operator
import os
import re
import sys
import vim

# Insert the knowledge on the python path
BASE_DIR = vim.eval("s:plugin_path")
sys.path.insert(0, BASE_DIR)

from knowledge import coverage
from knowledge import error
from knowledge.proxy import AnkiProxy, MnemosyneProxy
from knowledge.wikinote import WikiNote, Header

SRS_PROVIDER = vim.vars.get('knowledge_srs_provider')
DATA_DIR = vim.vars.get('knowledge_data_dir')


def get_proxy():
    if SRS_PROVIDER == 'Anki':
        return AnkiProxy(DATA_DIR)
    elif SRS_PROVIDER == 'Mnemosyne':
        return MnemosyneProxy(DATA_DIR)
    elif SRS_PROVIDER is None:
        raise error.KnowledgeException(
            "Variable knowledge_srs_provider has to have "
            "one of the following values: Anki, Mnemosyne"
        )
    else:
        raise error.KnowledgeException(
            "SRS provider '{0}' is not supported."
            .format(SRS_PROVIDER)
        )


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

    @property
    def tags(self):
        tag_sets = [
            set(header.data.get('tags', []))
            for header in self.headers.values()
        ]

        return reduce(operator.or_, tag_sets, set())

    @property
    def deck(self):
        keys = sorted(self.headers.keys(), reverse=True)
        for key in keys:
            deck = self.headers[key].data.get('deck')
            if deck is not None:
                return deck

    @property
    def model(self):
        keys = sorted(self.headers.keys(), reverse=True)
        for key in keys:
            model = self.headers[key].data.get('model')
            if model is not None:
                return model


class BufferProxy(object):

    def __init__(self, buffer_object):
        self.object = buffer_object

    def obtain(self):
        self.data = self.object[:]

    def push(self):
        self.object[:] = self.data

    def __getitem__(self, index):
        return self.data[index]

    def __setitem__(self, index, lines):
        self.data[index] = lines

    def __iter__(self):
        for line in self.data:
            yield line

    def __len__(self):
        return len(self.data)


def create_notes(update=False):
    """
    Loops over current buffer and adds any new notes to Anki.
    """

    srs_proxy = get_proxy()
    buffer_proxy = BufferProxy(vim.current.buffer)
    buffer_proxy.obtain()
    stack = HeaderStack()

    # Process each line, skipping over the lines
    # that can be ignored
    line_number = 0
    while line_number < len(buffer_proxy):
        note, processed = WikiNote.from_line(
            buffer_proxy,
            line_number,
            srs_proxy,
            tags=stack.tags,
            deck=stack.deck,
            model=stack.model,
        )

        if note is None:
            header, processed = Header.from_line(buffer_proxy, line_number)
            if header is not None:
                stack.push(header)

        elif not note.created or update:
            note.save()

        line_number += processed

    # Make sure changes are saved in the db
    srs_proxy.commit()

    # Display the changes in the buffer
    buffer_proxy.push()
