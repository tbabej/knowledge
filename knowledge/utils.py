import functools
import dataclasses
import glob
import os
import re
import subprocess


def string_to_args(line):
    output = []
    escape_global_chars = ('"', "'")
    line = line.strip()

    current_escape = None
    current_part = ''
    local_escape_pos = None

    for i in range(len(line)):
        char = line[i]
        ignored = False
        process_next_part = False

        # If previous char was \, add to current part no matter what
        if local_escape_pos == i - 1:
            local_escape_pos = None
        # If current char is \, use it as escape mark and ignore it
        elif char == '\\':
            local_escape_pos = i
            ignored = True
        # If current char is ' or ", open or close an escaped seq
        elif char in escape_global_chars:
            # First test if we're finishing an escaped sequence
            if current_escape == char:
                current_escape = None
                ignored = True
            # Do we have ' inside "" or " inside ''?
            elif current_escape is not None:
                pass
            # Opening ' or "
            else:
                current_escape = char
                ignored = True
        elif current_escape is not None:
            pass
        elif char == ' ':
            ignored = True
            process_next_part = True

        if not ignored:
            current_part += char

        if process_next_part and current_part:
            output.append(current_part)
            current_part = ''

    if current_part:
        output.append(current_part)

    return output

def string_to_kwargs(line):
    args = string_to_args(line)
    return args_to_kwargs(args)

def args_to_kwargs(args):
    output = dict()

    for arg in args:
        # If the argument contains :, then it's a key/value pair
        if ':' in arg and '::' not in arg:
            key, value = arg.split(':', 1)
            # Ignore anything which is not one-word string of alpha chars
            if key.isalpha():
                output[key] = value if value != "" else None
        # Tag addition
        elif arg.startswith('+'):
            value = arg[1:]
            output.setdefault('tags', []).append(value)
        else:
            output['deck'] = arg

    return output

def is_list_item(buffer_proxy, number):
    def is_list_indented_line(line):
        """
        Returns True, if it is sure that the current line belongs to a list
        item.
        Returns False, if it is sure that the current line does not belong to
        a list item.
        Returns None, if it cannot be determined from the information given
        on this line
        """
        if line.startswith('* '):
            return True
        elif line.startswith('  '):
            return None
        else:
            return False

    for line in reversed(buffer_proxy[:number+1]):
        # If we stumbled upon an empty line, and have not yet decided that this
        # indeed is a list item, then it is not
        if not line.strip():
            return False

        if is_list_indented_line(line) is None:
            # None means we couldn't tell from this line, let's continue
            continue
        else:
            # If we could tell from this line, pass it up
            return is_list_indented_line(line)


def run(args):
    child = subprocess.Popen(
        [str(arg) for arg in args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = child.communicate()
    code = child.returncode

    return stdout, stderr, code


def get_text_identifiers():
    """
    Detect all the Knowledge identifiers present in the directory.
    """

    REGEX = r'@(?P<identifier>[A-Za-z0-9]{11})'

    def find_matches():
        for path in glob.iglob('**/*.knw', recursive=True):
            with open(path, 'r') as f:
                yield from re.finditer(REGEX, f.read())

    data = [match.group('identifier') for match in find_matches()]
    return data


@dataclasses.dataclass
class LatexIcon:
    command: str
    fontsize: int = 20
    raise_mm: int = -3

# Font awesome indicators in text
ICON_INDICATORS = {
    re.compile(r'lstlisting'): LatexIcon(r'\faIcon{code}', fontsize=16, raise_mm=-2),
    re.compile(r'Git[^H]'):    LatexIcon(r'\faIcon{git-alt}'),
    re.compile(r'Java'):       LatexIcon(r'\faIcon{java}'),
    re.compile(r'Python'):     LatexIcon(r'\faIcon{python}', fontsize=21),
    re.compile(r'Linux'):      LatexIcon(r'\faIcon{linux}'),
    re.compile(r'NodeJS'):     LatexIcon(r'\faIcon{node-js}'),
    re.compile(r'Swift'):      LatexIcon(r'\faIcon{swift}'),
    re.compile(r'language=[Jj]ava'):   LatexIcon(r'\faIcon{java}'),
    re.compile(r'language=[Pp]ython'): LatexIcon(r'\faIcon{python}'),
}

def detect_icon(text):
    """
    Find a suitable font awesome icon for the text string. Defaults to
    faQuestion.
    """

    icon = LatexIcon(r'\faIcon{question}', fontsize=19)

    for regexp, value in ICON_INDICATORS.items():
        if regexp.search(text):
            icon = value

    return icon

def preserve_cwd(method):
    """
    Decorator that ensures the current working directory is not altered.
    """

    @functools.wraps(method)
    def wrapped_method(*args, **kwargs):
        old_cwd = os.getcwd()
        result = method(*args, **kwargs)
        os.chdir(old_cwd)
        return result

    return wrapped_method
