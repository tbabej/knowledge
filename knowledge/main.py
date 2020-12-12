from __future__ import print_function
import contextlib
import datetime
import functools
import hashlib
import multiprocessing
import operator
import os
import re
import shlex
import sys
import tempfile
import uuid
import vim
from pathlib import Path

# Insert the knowledge on the python path
KNOWLEDGE_BASE_DIR = vim.eval("s:knowledge_plugin_path")
sys.path.insert(0, KNOWLEDGE_BASE_DIR)

# Different vim plugins share python namespace, avoid imports
# using common names such as 'errors' or 'utils' using shortname
# for the whole module
import knowledge as k
# TODO: Make these imports lazy
import knowledge.regexp
import knowledge.backend
import knowledge.conversion

from knowledge.proxy import AnkiProxy, MnemosyneProxy
from knowledge.wikinote import WikiNote, Header


def get_proxy():
    if k.config.SRS_PROVIDER == 'Anki':
        return AnkiProxy(k.config.SRS_DB)
    elif k.config.SRS_PROVIDER == 'Mnemosyne':
        return MnemosyneProxy(os.path.dirname(k.config.SRS_DB))
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
            if model is not None: return model

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
def create_notes():
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
            else:
                note.save()

            line_number += processed

        # Make sure changes are saved in the db
        srs_proxy.commit()

        # Display the changes in the buffer
        buffer_proxy.push()


@k.errors.pretty_exception_handler
def note_info():
    buffer_proxy = BufferProxy(vim.current.buffer)
    buffer_proxy.obtain()

    with autodeleted_proxy() as srs_proxy:
        note, processed = WikiNote.from_line(
            buffer_proxy,
            k.vimutils.get_current_line_number(),
            srs_proxy,
            heading=None,
            tags=None,
            deck=None,
            model=None,
        )

        data = srs_proxy.note_info(note.proxy_id)

    content = f"""
    Added:        {data['added'].strftime('%Y-%m-%d')}
    First review: {data['first_review'].strftime('%Y-%m-%d') if data['first_review'] else 'N/A'}
    Last review:  {data['last_review'].strftime('%Y-%m-%d') if data['last_review'] else 'N/A'}
    Due:          {data['due'].strftime('%Y-%m-%d') if data['due'] else 'N/A'}
    Interval:     {data['interval'] if data['interval'] else 'N/A'}
    Ease:         {data['ease']}%
    Reviews:      {data['reviews']}
    Lapses:       {data['lapses']}
    Average time: {data['average_time']}
    Total time:   {data['total_time']}
    Card type:    {data['card_type']}
    Note type:    {data['note_type']}
    Deck:         {data['deck']}
    Note ID:      {data['note_id']}
    Card ID:      {data['card_id']}
    """

    print(content)


@k.errors.pretty_exception_handler
def diagnose():
    """
    Run a set of diagnostics procedures to ensure health of the knowledge base.
    """

    # Check 1: Discover "stale" cards in the SRS application
    note_ids_in_repo = set([
        k.backend.get(identifier)
        for identifier in k.utils.get_text_identifiers()
    ])

    with autodeleted_proxy() as srs_proxy:
        note_ids_in_srs = srs_proxy.get_identifiers()

    print(f"IDs detected in repo: {len(note_ids_in_repo)}")
    print(f"IDs detected in srs: {len(note_ids_in_srs)}")
    print(f"IDs redundant: {note_ids_in_srs - note_ids_in_repo}")


@k.errors.pretty_exception_handler
def close_questions():
    """
    Loops over the current buffer and closes any SRSQuestion regions.
    """

    buffer_proxy = BufferProxy(vim.current.buffer)
    buffer_proxy.obtain()

    for number in range(len(buffer_proxy)):
        if re.search(k.regexp.QUESTION, buffer_proxy[number]) is not None:
            k.vimutils.close_fold(number)


@k.errors.pretty_exception_handler
def occlude_image():
    match = re.search(k.regexp.IMAGE, vim.current.line)
    if match is not None:
        import knowledge.occlusion
        process = multiprocessing.Process(
            target=k.occlusion.OcclusionApplication.run,
            args=(match.group('filename'),),
            daemon=True
        )
        process.start()
    else:
        raise k.errors.KnowledgeException("No image detected on this line")

@k.errors.pretty_exception_handler
def paste_image():
    """
    Takes an image from the clipboard, pastes it into the media directory
    and inserts a link to it into the buffer.
    """

    import basehash
    translator = basehash.base(k.constants.ALPHABET)
    identifier = translator.encode(uuid.uuid4().int >> 34).zfill(16)

    # Create the media directory if does not exist
    k.paths.MEDIA_DIR.mkdir(exist_ok=True, parents=True)

    filepath = k.paths.MEDIA_DIR / (identifier + '.png')

    if sys.platform == 'linux':
        command = 'xclip -selection clipboard -t image/png -o'
    elif sys.platform == 'darwin':
        command = f'pngpaste {str(filepath)}'

    stdout, stderr, code = k.utils.run(shlex.split(command))

    if code != 0:
        raise k.errors.KnowledgeException(f"Image could not be pasted: {stderr}")

    # For linux, the output is on stdout so we need to write out the file
    if sys.platform == 'linux':
        with open(filepath, 'wb') as f:
            f.write(stdout)

    # Modify the current line in place
    column = k.vimutils.get_current_column_number()
    vim_file_link = f'![image](media:{identifier + ".png"})'

    modified_line = ''.join([
        vim.current.line[:(column+1)],
        vim_file_link,
        vim.current.line[(column+1):]
    ])

    vim.current.line = modified_line
    vim.current.window.cursor = vim.current.window.cursor[0], column + len(vim_file_link)


@k.errors.pretty_exception_handler
def add_citation():
    """
    Takes a citation reference from the clipboard and adds it into the sources
    file and adds a citation mark in the text.
    """

    # Optimizing runtime speed via local imports
    import pyperclip
    import requests_html

    import bibtexparser
    from bibtexparser.bwriter import BibTexWriter
    from bibtexparser.bibdatabase import BibDatabase

    # Obtain the URL from the clipboard and generate ID number from the hash
    url = pyperclip.paste().strip()
    hash_id = int(hashlib.sha256(url.encode('utf-8')).hexdigest(), 16) % 1000
    entry_id = f"source{hash_id}"

    # Detect if the source is already present in the bibliography
    k.paths.BIBLIOGRAPHY_PATH.touch()
    with open(k.paths.BIBLIOGRAPHY_PATH, 'r') as f:
        citations_db = bibtexparser.load(f)

    duplicates = [e for e in citations_db.entries if e.get('url') == url]

    if not duplicates:
        session = requests_html.HTMLSession()
        title = session.get(url).html.find('title', first=True).text

        # Generate the citation entry and add it into the sources.bib
        citations_db.entries.append({
            'ENTRYTYPE': 'misc',
            'ID': entry_id,
            'title': title,
            'url': url
        })

        with open(k.paths.BIBLIOGRAPHY_PATH, 'a') as f:
            f.write(BibTexWriter().write(citations_db))
    else:
        entry_id = duplicates[0].get('ID')

    # Add the citation into the text
    line = vim.current.line

    cloze_identifier = k.regexp.CLOSE_IDENTIFIER.search(line)
    if cloze_identifier is None:
        vim.current.line = f"{line} [@{entry_id}]"
    else:
        stripped_line = k.regexp.CLOSE_IDENTIFIER.sub('', line)
        vim.current.line = f"{stripped_line} [@{entry_id}] {cloze_identifier.group()}"


def convert_to_pdf(interactive=False):
    lines = vim.current.buffer[:]
    full_path = k.vimutils.get_absolute_filepath()
    k.conversion.convert_to_pdf(full_path, lines, interactive)
