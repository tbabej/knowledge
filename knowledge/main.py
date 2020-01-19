from __future__ import print_function
import contextlib
import datetime
import functools
import operator
import os
import re
import shlex
import subprocess
import sys
import tempfile
import uuid
import vim
from pathlib import Path


import basehash
import yaml

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
            k.utils.get_current_line_number(),
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
def close_questions():
    """
    Loops over the current buffer and closes any SRSQuestion regions.
    """

    buffer_proxy = BufferProxy(vim.current.buffer)
    buffer_proxy.obtain()

    for number in range(len(buffer_proxy)):
        if re.search(k.regexp.QUESTION, buffer_proxy[number]) is not None:
            k.utils.close_fold(number)

@k.errors.pretty_exception_handler
def paste_image():
    """
    Takes an image from the clipboard, pastes it into the .media directory
    and inserts a link to it into the buffer.
    """

    translator = basehash.base(k.constants.ALPHABET)
    identifier = translator.encode(uuid.uuid4().int >> 34).zfill(16)

    file_basedir = os.path.dirname(k.utils.get_absolute_filepath())
    filepath = os.path.join(
        file_basedir,
        '.media',
        identifier + '.png'
    )

    # Create the .media directory
    media_basedir = os.path.dirname(filepath)
    if not os.path.exists(media_basedir):
        os.mkdir(media_basedir)

    if sys.platform == 'linux':
        command = 'xclip -selection clipboard -t image/png -o'
    elif sys.platform == 'darwin':
        command = f'pngpaste {filepath}'

    stdout, stderr, code = k.utils.run(shlex.split(command))

    if code != 0:
        raise k.errors.KnowledgeException(f"Image could not be pasted: {stderr}")

    # For linux, the output is on stdout so we need to write out the file
    if sys.platform == 'linux':
        with open(filepath, 'wb') as f:
            f.write(stdout)

    column = k.utils.get_current_column_number()
    vim_file_link = ''.join([
        '{{file:',
        os.path.relpath(filepath, start=file_basedir),
        '}}'
    ])

    modified_line = ''.join([
        vim.current.line[:(column+1)],
        vim_file_link,
        vim.current.line[(column+1):]
    ])

    vim.current.line = modified_line
    vim.current.window.cursor = vim.current.window.cursor[0], column + len(vim_file_link)


def convert_to_pdf():
    lines = vim.current.buffer[:]
    data = {}

    # Detect YAML preamble if present
    if lines[0].strip() == '---' and lines.index('...') != -1:
        preamble = lines[:lines.index('...') + 1]
        data.update(yaml.safe_load('\n'.join(preamble)))
        lines = lines[lines.index('...') + 1:]

    # Detect author and last commit date if in a git repository
    try:
        cmd_result = k.utils.run(['git', 'show', 'HEAD', '-s', '--pretty=format:%an:%at'])
        author, timestamp = cmd_result[0].decode('utf-8').split(':')
        data['author'] = author
        data['date'] = datetime.datetime.fromtimestamp(int(timestamp))
    except Exception:
        pass

    # Generate the preamble
    preamble = '\n'.join([
       '---',
       f'title: "{data.get("title", "Title missing")}"',
       f'author: [{data.get("author")}]',
       f'date: "{data.get("date", datetime.date.today()).strftime("%Y-%m-%d")}"',
       'lang: "en"',
       'page-background: "/home/tbabej/background1.pdf"',
       'page-background-opacity: 0.1',
       'caption-justification: "centering"',
       'footnotes-pretty: true',
       'classoption: [oneside]',
       'header-includes:',
       '- |',
       '  ```{=latex}',
       r'  \usepackage{awesomebox}',
       r'  \usepackage{sectsty}',
       r'  \newcounter{question}[section]',
       r'  \addtocounter{section}{1}',
       r'  \sectionfont{\fontsize{21}{24}\selectfont\centering}',
       r'  \subsectionfont{\fontsize{15}{18}\selectfont\centering}',
       r'  \subsubsectionfont{\fontsize{12}{15}\selectfont\centering}',
       r'  \newenvironment{questionblock}[0]{',
       r'      \begingroup',
       r'      \setlength{\aweboxleftmargin}{0.09\linewidth}',
       r'      \setlength{\aweboxcontentwidth}{0.91\linewidth}',
       r'      \setlength{\aweboxsignraise}{1mm}',
       r'      \definecolor{abvrulecolor}{RGB}{221,221,216}',
       r'      \addtocounter{question}{1}',
       r'      \begin{awesomeblock}[abvrulecolor][][\textbf{Question \thesection.\thequestion}]{2pt}{\fontsize{20}{2}\selectfont\faQuestion}{violet}',
       r'  }{',
       r'      \end{awesomeblock}',
       r'      \endgroup',
       r'  }',
       '  ```',
       '...'
    ])

    substitutions = [
        lambda l: re.sub(k.regexp.NOTE_HEADLINE['markdown'], r'\1\2', l),
        lambda l: re.sub(k.regexp.CLOSE_IDENTIFIER, r'', l),
        lambda l: re.sub(r':\[', r'[', l),
    ]

    for substitution in substitutions:
        lines = [substitution(line) for line in lines]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(preamble + '\n\n' + '\n'.join(lines))
        f.flush()
        output = subprocess.check_output([
            'pandoc',
            f.name,
            '-f', 'markdown',
            '-o', 'output.pdf',
            '--template', 'eisvogel',
            '--listings'
        ])
        print(output)
