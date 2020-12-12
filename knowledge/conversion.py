"""
Module that implements conversion of the knowledge documents into various
formats.
"""

import datetime
import os
import re
import tempfile
import subprocess
import hashlib
import shutil
from pathlib import Path

import knowledge as k
import knowledge.regexp
import knowledge.utils
import knowledge.paths


KNOWLEDGE_BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def convert_to_pdf(filepath, lines, interactive=False):
    """
    Converts to PDF format.
    """

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
    full_path = os.path.abspath(filepath)
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
        # Inline todos are surrounded by blank lines
        lambda t: re.sub(r'\n\s*\n\s*TODO:\s*(?P<content>[^\n]+)\n\s*\n', r'\n\n\\inlinetodo{\g<content>}\n\n', t),
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

    def process_picture(line):
        """
        Process the Markdown styled picture and set the expected width.
        """

        match = re.match(k.regexp.IMAGE, line)
        if not match:
            return line

        # Determine the right width size
        if match.group('size') == 'L':
            width = r"width=0.95\textwidth"
        elif match.group('size') == 'M':
            width = r"width=0.50\textwidth"
        elif match.group('size') == 'S':
            width = r"width=0.25\textwidth"
        else:
            width = r"width=0.75\textwidth"

        formatting = match.group('format') or ''

        # Append width into the formatting string
        if formatting and 'width' not in formatting:
            formatting = f"{formatting},{width}"
        else:
            formatting = width

        media_filepath = k.paths.MEDIA_DIR / match.group('filename')
        occlusion_filepath = k.paths.OCCLUSIONS_DIR / match.group('filename')

        return rf"\knowledgeFigure{{{str(media_filepath)}}}{{{str(occlusion_filepath) if interactive and occlusion_filepath.exists() else ''}}}{{{formatting}}}{{{match.group('label')}}}"

    # Perform substitutions (removing identifiers and other syntactic sugar)
    substitutions = [
        lambda l: re.sub(k.regexp.NOTE_HEADLINE['markdown'], r'\1\2', l),
        lambda l: re.sub(k.regexp.CLOSE_IDENTIFIER, r'', l),
        lambda l: re.sub(r'\s*#((?P<source>[A-Z]):)?[0-9a-fA-F]{8}\s*$', '', l),
        lambda l: re.sub(r'^(?P<header_start>[#]+)([^#\|\[\{]*)(\|(\|)?[^#\|]*)$', r'\1\2', l),
        lambda l: re.sub(r':\[', r'[', l),
        lambda l: re.sub(r'^- ([^\`]*)\`([^\`]+)\`([^\`]*)$', r'- \1\\passthrough{\\lstinline[style=knowledge_question]!\2!}\3', l),
        lambda l: re.sub(r'^(?P<number>\d+)\. (?P<content>.+)', r'\g<number>. \\knowledgeEnum{\g<content>}', l),
        lambda l: re.sub(r'TODO:\s*(?P<content>.+)$', r'\\margintodo{\g<content>}', l),
        lambda l: re.sub(k.regexp.SIMPLE_URL, r'[\g<domain>](\g<proto>\g<domain>\g<resource>)', l),
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

    tmpdir = Path(tempfile.mkdtemp(prefix='knowledge-pdf-'))
    pandoc_data_dir = os.path.join(KNOWLEDGE_BASE_DIR, 'latex/')
    output_filepath = str(tmpdir / k.regexp.EXTENSION.sub('.tex', filename))

    # Ensure bibliography file exists
    k.paths.BIBLIOGRAPHY_PATH.touch()

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
            '--bibliography', str(k.paths.BIBLIOGRAPHY_PATH),
            '--listings'
        ])

    # Ensure cache folder exists
    k.paths.CACHE_DIR.mkdir(exist_ok=True, parents=True)

    # Preamble compilation only works in non-interactive mode
    if not interactive:
        # Precompile the cached preamble, if does not exist
        preamble_hash = hashlib.sha256(preamble.encode('utf-8')).hexdigest()[:20]
        cached_preamble = k.paths.CACHE_DIR / f"preamble_{preamble_hash}.fmt"

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
            '-interaction=batchmode',
            '-draftmode' if not interactive else '',
            output_filepath
        ],
        cwd=str(tmpdir)
    )
    subprocess.check_output(
        [
            'pdflatex',
            '-interaction=batchmode',
            output_filepath
        ],
        cwd=str(tmpdir)
    )

    # Launch the PDF viewer
    subprocess.Popen(
        [
            'xdg-open',
            k.regexp.EXTENSION.sub('.pdf', output_filepath)
        ],
        start_new_session=True
    )
