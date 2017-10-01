from __future__ import print_function
import contextlib
import functools
import operator
import os
import re
import shlex
import sys
import uuid
import vim

import basehash

# Insert the knowledge on the python path
BASE_DIR = vim.eval("s:plugin_path")
sys.path.insert(0, BASE_DIR)

# Different vim plugins share python namespace, avoid imports
# using common names such as 'errors' or 'utils' using shortname
# for the whole module
import knowledge as k

from knowledge.proxy import AnkiProxy, MnemosyneProxy
from knowledge.wikinote import WikiNote, Header


def get_proxy():
    if k.config.SRS_PROVIDER == 'Anki':
        return AnkiProxy(k.config.DATA_DIR)
    elif k.config.SRS_PROVIDER == 'Mnemosyne':
        return MnemosyneProxy(k.config.DATA_DIR)
    elif k.config.SRS_PROVIDER is None:
        raise k.errors.KnowledgeException(
            "Variable knowledge_srs_provider has to have "
            "one of the following values: Anki, Mnemosyne"
        )
    else:
        raise k.errors.KnowledgeException(
            "SRS provider '{0}' is not supported."
            .format(config.SRS_PROVIDER)
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
    def heading(self):
        keys = sorted(self.headers.keys(), reverse=True)
        for key in keys:
            return self.headers[key].data['name']

    @property
    def tags(self):
        tag_sets = [
            set(header.data.get('tags', []))
            for header in self.headers.values()
        ]

        return functools.reduce(operator.or_, tag_sets, set())

    @property
    def deck(self):
        keys = sorted(self.headers.keys(), reverse=True)
        deck = ''

        for key in keys:
            current_deck = self.headers[key].data.get('deck')
            if current_deck is not None:
                deck = current_deck + deck

                if not current_deck.startswith('.'):
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
        self.data = [line for line in self.object[:]]

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


@contextlib.contextmanager
def autodeleted_proxy():
    proxy = get_proxy()
    try:
        yield proxy
    finally:
        proxy.cleanup()
        del proxy


@k.errors.pretty_exception_handler
def create_notes(update=False):
    """
    Loops over current buffer and adds any new notes to Anki.
    """

    with autodeleted_proxy() as srs_proxy:
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
                heading=stack.heading,
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


@k.errors.pretty_exception_handler
def close_questions():
    """
    Loops over the current buffer and closes any SRSQuestion regions.
    """

    buffer_proxy = BufferProxy(vim.current.buffer)
    buffer_proxy.obtain()

    for number in range(len(buffer_proxy)):
        if re.search(regexp.QUESTION, buffer_proxy[number]) is not None:
            utils.close_fold(number)
