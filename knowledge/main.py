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
KNOWLEDGE_BASE_DIR = vim.eval("s:knowledge_plugin_path")
sys.path.insert(0, KNOWLEDGE_BASE_DIR)

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
    interactive = True

    # Detect YAML preamble if present
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

    # Generate the preamble
    preamble = '\n'.join([
       '---',
       f'title: "{data.get("title", default_title)}"',
       f'author: [{data.get("author", "")}]',
       f'date: "{data.get("date", datetime.date.today()).strftime("%Y-%m-%d")}"',
       'lang: "en"',
       f'page-background: "{data.get("background", default_background)}"',
       'page-background-opacity: 0.1',
       'caption-justification: "centering"',
       r'code-block-font-size: \scriptsize',
       'footnotes-pretty: true',
       'classoption: [oneside]',
       r'header-center: \knowledgeControls',
       'header-includes:',
       '- |',
       '  ```{=latex}',
       r'  \definecolor{default-linkcolor}{HTML}{0052A5}',
       r'  \hypersetup{colorlinks=true,linkcolor=default-linkcolor,filecolor=default-linkcolor}',
       r'  \usepackage{awesomebox}',
       r'  \usepackage{sectsty}',
       r'  \usepackage{ocgx2}',
       r'  \usepackage{etoolbox}',
       r'  \usepackage{transparent}',
       r'  \def\allocgs{}',
       r'  \newcommand{\printocg}[1]{#1 }',
       r'  \newcounter{questioncounter}[section]',
       r'  \newcounter{enumcounter}[section]',
       r'  \newcounter{clozecounter}[section]',
       r'  \newtoggle{interactive}',
       r'  \toggletrue{interactive}' if interactive else r'  \togglefalse{interactive}',
       r'  \addtocounter{section}{1}',
       r'  \newcommand{\knowledgeControls}[0]{',
       r'      \iftoggle{interactive}{',
       r'          \fontsize{8}{2}\selectfont',
       r'          \transparent{0.6}',
       r'          \showocg{\forlistloop{\printocg}{\allocgs}}{\faClipboardCheck \kern2pt show} {\fontsize{9}{2}\selectfont /}',
       r'          \hideocg{\forlistloop{\printocg}{\allocgs}}{\kern1pt \faEyeSlash \kern1pt hide}',
       r'          \global\def\allocgs{}',
       r'      }{}',
       r'  }',
       r'  \newlength{\dotslength}',
       r'  \settowidth{\dotslength}{~...}',
       r'  \sectionfont{\fontsize{21}{24}\selectfont\centering}',
       r'  \subsectionfont{\fontsize{15}{18}\selectfont\centering}',
       r'  \subsubsectionfont{\fontsize{12}{15}\selectfont\centering}',
       r'  \newcommand{\knowledgeCloze}[1]{',
       r'      \addtocounter{clozecounter}{1}',
       r'      \listxadd{\allocgs}{C\thesection.\theclozecounter}',  # Expandable (listXadd) version extremely important here
       r'      \iftoggle{interactive}{',
       r'          \begin{ocmd}[D\thesection.\theclozecounter]{\AnyOff{C\thesection.\theclozecounter}}\switchocg{C\thesection.\theclozecounter}{...}\end{ocmd}',
       r'          \begin{ocg}{AnsC\thesection.\theclozecounter}{C\thesection.\theclozecounter}{0}',
       r'          \kern-\dotslength#1',
       r'          \end{ocg}',
       r'      }{#1}',
       r'  }',
       r'  \newcommand{\knowledgeEnum}[1]{',
       r'      \tightlist',  # Redundant, but works
       r'      \addtocounter{enumcounter}{1}',
       r'      \listxadd{\allocgs}{E\thesection.\theenumcounter}',  # Expandable (listXadd) version extremely important here
       r'      \iftoggle{interactive}{',
       r'          \switchocg{E\thesection.\theenumcounter}{\hskip -2em ~~~}',
       r'          \begin{ocg}{AnsE\thesection.\theenumcounter}{E\thesection.\theenumcounter}{0}',
       r'          \hskip 1em #1',
       r'          \end{ocg}',
       r'      }{',
       r'          #1'
       r'      }',
       r'  }',
       r'  \newenvironment{knowledgeQuestion}[4]{',
       r'      \begingroup',
       r'      \vskip -3.5mm',
       r'      \setlength{\aweboxleftmargin}{0.08\linewidth}',
       r'      \setlength{\aweboxcontentwidth}{0.92\linewidth}',
       r'      \setlength{\aweboxsignraise}{#4 mm}',
       r'      \definecolor{abvrulecolor}{RGB}{221,221,216}',
       r'      \addtocounter{questioncounter}{1}',
       r'      \listxadd{\allocgs}{Q\thesection.\thequestioncounter}',
       r'      \begin{awesomeblock}[abvrulecolor]{2pt}{\fontsize{#3}{2}\selectfont #2}{violet}',
       r'      \iftoggle{interactive}{',
       r'          \switchocg{Q\thesection.\thequestioncounter}{\textbf{Q \thesection.\thequestioncounter.} \textit{#1}} \newline',
       r'          \begin{ocg}{AnsQ\thesection.\thequestioncounter}{Q\thesection.\thequestioncounter}{0}',
       r'      }{',
       r'          \textbf{Q \thesection.\thequestioncounter.} \textit{#1} \newline',
       r'      }',
       r'  }{',
       r'      \iftoggle{interactive}{\end{ocg}}{}',
       r'      \end{awesomeblock}',
       r'      \endgroup',
       r'      \vskip -3.5mm',
       r'  }',
       '  ```',
       '...'
       '',  # Followed by a post-amble (dumped after \begin{document})
       r'',
       r'\lstdefinestyle{knowledge_text_override}{',
       r'    language         = python,',
       r'    basicstyle       = \color{listing-text-color}\linespread{1.0}\fontsize{8}{10}\selectfont\ttfamily{},',
       r'    xleftmargin      = 5em,',
       r'    framexleftmargin = 0.4em,',
       r'    aboveskip        = 0.8em,',
       r'    belowskip        = 0.4em,',
       r'    xrightmargin     = 5em,',
       r'}',
       r'\lstdefinestyle{knowledge_question_override}{',
       r'    language         = python,',
       r'    basicstyle       = \color{listing-text-color}\linespread{1.0}\fontsize{8}{10}\selectfont\ttfamily{},',
       r'    xleftmargin      = 0.7em,',
       r'    framexleftmargin = 0.4em,',
       r'    xrightmargin     = 6em,',
       r'    aboveskip        = -0.7em,',
       r'    belowskip        = -2em,',
       r'    abovecaptionskip = -1em,',
       r'    belowcaptionskip = -1em,',
       r'}',
       r'\lstdefinestyle{knowledge_text}{style=eisvogel_listing_style,style=knowledge_text_override}',
       r'\lstdefinestyle{knowledge_question}{style=eisvogel_listing_style,style=knowledge_question_override}',
       r'\lstset{style=knowledge_text}',
       r''
    ])

    text_substitutions = [
        # Add extra line to have lists recognized as md lists
        lambda t: re.sub(r':\s*\n\* ', ':\n\n* ', t),
        # Add extra line to have enumerations recognized
        lambda t: re.sub(r':\s*\n(\d+)\. ', r':\n\n\1. ', t),
        # Markup clozes as italics
        lambda t: re.sub(r'\{(?P<cloze>[^\{\}]+)\}', r'\\knowledgeCloze{\g<cloze>}', t, flags=re.MULTILINE),
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

    # Perform substitutions (removing identifiers and other syntactic sugar)
    substitutions = [
        lambda l: re.sub(k.regexp.NOTE_HEADLINE['markdown'], r'\1\2', l),
        lambda l: re.sub(k.regexp.CLOSE_IDENTIFIER, r'', l),
        lambda l: re.sub(r':\[', r'[', l),
        lambda l: re.sub(r'^- ([^\`]*)\`([^\`]+)\`([^\`]*)$', r'- \1\\passthrough{\\lstinline[style=knowledge_question]!\2!}\3', l),
        lambda l: re.sub(r'^(?P<number>\d+)\. (?P<content>.+)', r'\g<number>. \\knowledgeEnum{\g<content>}', l),
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
            icon = k.utils.detect_icon('\n'.join(lines[start:end+1]))
            lines[start] += f"{{{icon.command}}}{{{icon.fontsize}}}{{{icon.raise_mm}}}"
            lines[end-1] += '\n\\end{knowledgeQuestion}'

    tmpdir = Path(tempfile.mkdtemp(prefix='knowledge-'))
    pandoc_data_dir = os.path.join(KNOWLEDGE_BASE_DIR, 'latex/')
    output_filepath = str(tmpdir / k.regexp.EXTENSION.sub('.pdf', filename))

    with open(tmpdir / 'source.md', 'w') as f:
        f.write(preamble + '\n\n' + '\n'.join(lines))
        f.flush()
        output = subprocess.check_output([
            'pandoc',
            f.name,
            '-f', 'markdown',
            '-o', output_filepath,
            '--data-dir', pandoc_data_dir,
            '--template', 'eisvogel',
            '--listings'
        ])

    subprocess.call(['xdg-open', output_filepath])
