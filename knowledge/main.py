from __future__ import print_function
import contextlib
import datetime
import functools
import hashlib
import operator
import os
import re
import shlex
import shutil
import subprocess
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
            k.utils.close_fold(number)

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
    media_basedir = Path(k.config.DATA_FOLDER) / 'media'
    media_basedir.mkdir(exist_ok=True)

    filepath = media_basedir / (identifier + '.png')

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
    column = k.utils.get_current_column_number()
    vim_file_link = f'![image](media:{identifier + ".png"})'

    modified_line = ''.join([
        vim.current.line[:(column+1)],
        vim_file_link,
        vim.current.line[(column+1):]
    ])

    vim.current.line = modified_line
    vim.current.window.cursor = vim.current.window.cursor[0], column + len(vim_file_link)


def convert_to_pdf(interactive=False):
    lines = vim.current.buffer[:]
    data = {}

    # Detect YAML preamble if present
    import yaml  # lazy import
    if lines[0].strip() == '---' and lines.index('...') != -1:
        preamble = lines[:lines.index('...') + 1]
        data.update(yaml.safe_load('\n'.join(preamble)))
        lines = lines[lines.index('...') + 1:]

    text = '\n'.join(lines)

    # Determine the path to the default background
    default_background = os.path.join(KNOWLEDGE_BASE_DIR, 'latex/backgrounds/default-background.pdf')

    # Detect author and last commit date if in a git repository
    full_path = k.utils.get_absolute_filepath()
    parent_dir = os.path.dirname(full_path)
    filename = os.path.basename(full_path)

    try:
        output = subprocess.check_output(
            ['git', 'log', '-n', '1', '-s', '--pretty=format:%an:%at', filename],
            cwd=parent_dir
        )

        # If this particular file is not git-tracked, fall back to the latest
        # commit overall
        if not output:
            output = subprocess.check_output(
                ['git', 'show', 'HEAD', '-s', '--pretty=format:%an:%at'],
                cwd=parent_dir
            )

        author, timestamp = output.decode('utf-8').split(':')
        data['author'] = author
        data['date'] = datetime.datetime.fromtimestamp(int(timestamp))
    except Exception:
        pass

    # Determine a default title
    default_title = f"Notes on {k.regexp.EXTENSION.sub('', filename).replace('_', ' ')}"
    underline = k.config.PDF_UNDERLINE_CLOZE

    # Generate the preamble
    preamble = '\n'.join([
       '---',
       f'title: "{data.get("title", default_title)}"',
       f'author: [{data.get("author", "")}]',
       f'date: "{data.get("date", datetime.date.today()).strftime("%Y-%m-%d")}"',
       'lang: "en"',
       f'page-background: "{data.get("background", default_background)}"',
       'page-background-opacity: 0.05',
       'caption-justification: "centering"',
       r'code-block-font-size: \scriptsize',
       'footnotes-pretty: true',
       'classoption: [oneside]',
       f'knowledge-interactive: {"true" if interactive else "false"}',
       f'knowledge-underline: {"true" if underline else "false"}',
       r'header-center: \knowledgeControls',
       'reference-section-title: Sources',
       'link-citations: true',
       '...',
       ''
    ])

    def outside_math(x, method):
        """
        Apply method only to the substrings of x that are not in the "math mode".
        """

        return '$$'.join([
            '$'.join([
                method(inner) if inner_index % 2 == 0 and outer_index % 2 == 0 else inner
                for inner_index, inner in enumerate(re.split(r'\$', part))
            ])
            for outer_index, part in enumerate(re.split(r'\$\$', x))
        ])

    text_substitutions = [
        # Add extra line to have lists recognized as md lists
        lambda t: re.sub(r':\s*\n\* ', ':\n\n* ', t),
        # Add extra line to have enumerations recognized
        lambda t: re.sub(r':\s*\n(\d+)\. ', r':\n\n\1. ', t),
        # Markup clozes as underlined OCGs
        lambda x: outside_math(x, lambda t: re.sub(r'(^|\s)\{(?P<cloze>[^\{\}:]+)\}', r' \\knowledgeCloze{\g<cloze>}{}', t, flags=re.MULTILINE)),
        lambda x: outside_math(x, lambda t: re.sub(r'(^|\s)\{(?P<cloze>[^\{\}:]+)( )?:( )?(?P<hint>[^\{\}]+)\}', r' \\knowledgeCloze{\g<cloze>}{\g<hint>}', t, flags=re.MULTILINE)),
        # Convert code blocks to lstlisting in a given language, because pandoc cannot do it with "- " prefix
        lambda l: re.sub(r'\n- \`\`\`(\w*)\s*\n(- [^\`]+\n)+- \`\`\`', r'\n- \\begin{lstlisting}[style=knowledge_question,language=\1]\n\2- \\end{lstlisting}', l),
    ]

    # Find verbosity blocks
    lines = text.splitlines()
    fences = [0] + [i for i in range(len(lines)) if lines[i].startswith('```')] + [len(lines)]

    process = True
    processed_text_parts = []
    for i in range(len(fences) - 1):
        block_start = fences[i]
        block_end = fences[i + 1]
        part = '\n'.join(lines[block_start:block_end])

        if process:
            for substitution in text_substitutions:
                part = substitution(part)

        processed_text_parts.append(part)
        process = not process

    text = '\n'.join(processed_text_parts)
    lines = text.splitlines()

    # Determine the folder of the file
    data_folder = Path(k.config.DATA_FOLDER)
    media_folder = data_folder / 'media'

    # Ensure the folder structure exists
    data_folder.mkdir(exist_ok=True)
    media_folder.mkdir(exist_ok=True)

    def process_picture(line):
        """
        Process the Markdown styled picture and set the expected width.
        """

        match = re.match(k.regexp.IMAGE, line)
        if not match:
            return line

        # Determine the right width size
        if match.group('size') == 'L':
            width = "width=95%"
        elif match.group('size') == 'M':
            width = "width=50%"
        elif match.group('size') == 'S':
            width = "width=25%"
        else:
            width = "width=75%"

        formatting = match.group('format') or ''

        # Append width into the formatting string
        if formatting and 'width' not in formatting:
            formatting = f"{formatting} {width}"
        else:
            formatting = width

        return rf"![{match.group('label')}]({str(media_folder)}/{match.group('filename')}){{{formatting}}}"

    # Perform substitutions (removing identifiers and other syntactic sugar)
    substitutions = [
        lambda l: re.sub(k.regexp.NOTE_HEADLINE['markdown'], r'\1\2', l),
        lambda l: re.sub(k.regexp.CLOSE_IDENTIFIER, r'', l),
        lambda l: re.sub(r'\s*#((?P<source>[A-Z]):)?[0-9a-fA-F]{8}\s*$', '', l),
        lambda l: re.sub(r'^(?P<header_start>[#]+)([^#\|\[\{]*)(\|(\|)?[^#\|]*)$', r'\1\2', l),
        lambda l: re.sub(r':\[', r'[', l),
        lambda l: re.sub(r'^- ([^\`]*)\`([^\`]+)\`([^\`]*)$', r'- \1\\passthrough{\\lstinline[style=knowledge_question]!\2!}\3', l),
        lambda l: re.sub(r'^(?P<number>\d+)\. (?P<content>.+)', r'\g<number>. \\knowledgeEnum{\g<content>}', l),
        lambda l: process_picture(l),
    ]

    for substitution in substitutions:
        lines = [substitution(line) for line in lines]

    # Detect and reformat question blocks
    for start in range(len(lines)):
        if k.regexp.QUESTION.match(lines[start]):
            for end in range(start + 1, len(lines)):
                if not lines[end].startswith('- '):
                    lines[start] = f'\\begin{{knowledgeQuestion}}{{{lines[start].replace("Q: ", "")}}}'
                    break
                else:
                    lines[end] = lines[end][2:]
            else:
                # If we did not break, the question extends until the end of
                # the file, and we need to wrap up
                lines[start] = f'\\begin{{knowledgeQuestion}}{{{lines[start].replace("Q: ", "")}}}'

            icon = k.utils.detect_icon('\n'.join(lines[start:end+1]))
            lines[start] += f"{{{icon.command}}}{{{icon.fontsize}}}{{{icon.raise_mm}}}"
            lines[end-1] += '\n\\end{knowledgeQuestion}'

    tmpdir = Path(tempfile.mkdtemp(prefix='knowledge-'))
    pandoc_data_dir = os.path.join(KNOWLEDGE_BASE_DIR, 'latex/')
    output_filepath = str(tmpdir / k.regexp.EXTENSION.sub('.tex', filename))

    # Ensure bibliography file exists
    bibliography_path = data_folder / 'sources.bib'
    bibliography_path.touch()

    # Convert the markdown file to tex source
    with open(tmpdir / 'source.md', 'w') as f:
        f.write(preamble + '\n\n' + '\n'.join(lines))
        f.flush()
        output = subprocess.check_output([
            'pandoc',
            f.name,
            '-f', 'markdown',
            '-o', output_filepath,
            '--data-dir', pandoc_data_dir,
            '--template', 'knowledge-basic',
            '--filter', 'pandoc-citeproc',
            '--bibliography', str(bibliography_path),
            '--listings'
        ])

    # Ensure cache folder exists
    cache_folder = data_folder / 'cache'
    cache_folder.mkdir(exist_ok=True)

    # Precompile the cached preamble, if does not exist
    preamble_hash = hashlib.sha256(preamble.encode('utf-8')).hexdigest()[:20]
    cached_preamble = cache_folder / f"preamble_{preamble_hash}.fmt"

    if not cached_preamble.exists():
        subprocess.check_output(
            [
                'pdftex',
                '-ini',
                f'-jobname="{cached_preamble.name.split(".")[0]}"',
                '&pdflatex',
                'mylatexformat.ltx',
                output_filepath
            ],
            cwd=str(tmpdir)
        )
        shutil.copy(tmpdir / cached_preamble.name, cached_preamble)
    else:
        shutil.copy(cached_preamble, tmpdir / cached_preamble.name)

    # Insert the precompiled preamble reference
    with open(output_filepath, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(f'%&{cached_preamble.name.split(".")[0]}\n{content}')

    # Compile the latex source
    subprocess.check_output(
        [
            'pdflatex',
            '-draftmode',
            output_filepath
        ],
        cwd=str(tmpdir)
    )
    subprocess.check_output(
        [
            'pdflatex',
            '-output-directory', str(tmpdir),
            output_filepath
        ],
        cwd=str(tmpdir)
    )

    # Launch the PDF viewer
    subprocess.call(['xdg-open', k.regexp.EXTENSION.sub('.pdf', output_filepath)])
