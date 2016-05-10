import re
import vim

import utils

QUESTION_PREFIXES = vim.vars.get(
    'knowledge_question_prefixes',
    ('Q:', 'How:', 'Explain:', 'Define:', 'List:', 'Prove:')
)

QUESTION_OMITTED_PREFIXES = vim.vars.get(
    'knowledge_omitted_prefixes',
    ('Q:',)
)

QUESTION = re.compile(
    '^'                                    # Starts at the begging
    '(?P<question>({prefixes})[^\[\]]+?)'  # Using an allowed prefix
    '('
      '\s+'                                # Followed by any whitespace
      '@(?P<identifier>.*)'                # With opt. identifier marked by @
    ')?'
    '\s*'
    '$'                                    # Matches on whole line
    .format(prefixes='|'.join(QUESTION_PREFIXES))
)

CLOSE_MARK = re.compile('[^\[](?<!\* )\[[^\[]+')
CLOSE_IDENTIFIER = re.compile('\s@(?P<identifier>.*)\s*$', re.MULTILINE)

NOTE_HEADLINE = re.compile(
    '^'                       # Starts at the begging of the line
    '(?P<header_start>[=]+)'  # Heading beggining
    '(?P<name>[^=\|\[]*)'     # Name of the viewport, all before the | sign
    '@'                       # Divider @
    '(?P<metadata>[^=@]*?)'   # Metadata string
    '\s*'                     # Any whitespace
    '(?P<header_end>[=]+)'    # Heading ending
)


class Header(object):

    def __init__(self):
        self.data = dict()

    @classmethod
    def from_line(cls, buffer_proxy, number):
        match = re.search(NOTE_HEADLINE, buffer_proxy[number])

        if not match:
            return None, 1

        self = cls()
        self.data.update({
            'header_start': match.group('header_start'),
            'header_end': match.group('header_end'),
            'name': match.group('name'),
        })

        # Update the header data from the hidden config string
        metadata = match.group('metadata').strip()
        self.data.update(utils.string_to_kwargs(metadata))

        return self, 1


class WikiNote(object):

    def __init__(self, buffer_proxy, proxy):
        self.fields = dict()
        self.data = dict()
        self.buffer_proxy = buffer_proxy
        self.proxy = proxy

    @classmethod
    def from_line(cls, buffer_proxy, number, proxy, tags=None, model=None, deck=None):
        """
        This methods detects if a current line is a note-defining headline. If
        positive, it will try to parse the note data out of the block.
        """

        basic_question = re.search(QUESTION, buffer_proxy[number])
        close_mark_present = re.search(CLOSE_MARK, buffer_proxy[number])

        if not close_mark_present and not basic_question:
            return None, 1

        self = cls(buffer_proxy, proxy)

        tags = tags or []
        deck = deck or proxy.DEFAULT_DECK

        if close_mark_present:
            model = model or proxy.CLOSE_MODEL
        else:
            model = model or proxy.DEFAULT_MODEL

        self.data.update({
            'line': number,
            'tags': set(tags),
            'model': model,
            'deck': deck,
        })

        if close_mark_present:
            line_shift = self.parse_close()
        elif basic_question:
            line_shift = self.parse_basic(basic_question)

        return self, line_shift

    def parse_basic(self, match):
        # If we have a match, determine if it's an existing note
        self.data['id'] = match.group('identifier')
        question = match.group('question').strip()

        # Strip the question prefixes that should be ignored
        for prefix in QUESTION_OMITTED_PREFIXES:
            if question.startswith(prefix):
                question = question.lstrip(prefix).strip()
                self.data['stripped_prefix'] = prefix
                break

        # Parse out the remaining question and answer parts
        questionlines = [question]
        answerlines = []
        parsing_question = True

        for line in self.buffer_proxy[(self.data['line']+1):]:
            candidate = line.strip()

            # Empty line finishes the parsing
            if not candidate:
                break

            # First line starting with '- ' denotes start of the answer
            if candidate.startswith('- '):
                answerlines.append(candidate[2:])
                parsing_question = False
            elif parsing_question:
                questionlines.append(candidate)

        self.fields.update({
            'Front': '\n'.join(questionlines),
            'Back': '\n'.join(answerlines),
        })

        return len(questionlines) + len(answerlines)

    def parse_close(self):
        lines = []

        # First, let's add upper part of the paragraph
        lines_included_upwards = 0

        for line in reversed(self.buffer_proxy[:(self.data['line'])]):
            candidate = line.strip()

            # Empty line finishes the parsing
            if not candidate:
                break
            else:
                lines_included_upwards += 1
                lines.append(line)

        # Now the lower part of the paragraph
        lines_inspected_forward = 0

        for line in self.buffer_proxy[(self.data['line']):]:
            lines_inspected_forward += 1
            candidate = line.strip()

            # Empty line finishes the parsing
            if not candidate:
                break
            else:
                lines.append(line)

        # If anything was in the upper part of the paragraph, shift the
        # marked line for this note
        self.data['line'] = self.data['line'] - lines_included_upwards

        # Look for the identifier on any line
        textlines = '\n'.join(lines)
        match = re.search(CLOSE_IDENTIFIER, textlines)
        if match:
            # If present, do not include it in the field, and save it
            textlines = re.sub(CLOSE_IDENTIFIER, '', textlines)
            self.data['id'] = match.group('identifier')

        self.fields.update({
            'Text': textlines
        })

        return lines_inspected_forward

    def __repr__(self):
        return repr(self.fields)

    @property
    def created(self):
        return self.data.get('id') is not None

    def save(self):
        if self.data.get('id') is not None:
            self._update()
            return

        obtained_id = self.proxy.add_note(
            fields=self.fields,
            deck=self.data['deck'],
            model=self.data['model'],
            tags=self.data['tags'],
        )

        if obtained_id:
            self.data['id'] = obtained_id
            self.update_in_buffer()

    def _update(self):
        self.proxy.update_note(
            identifier=self.data['id'],
            fields=self.fields,
            deck=self.data['deck'],
            model=self.data['model'],
            tags=self.data['tags']
        )
        self.update_in_buffer()

    def update_in_buffer(self):
        """
        Updates the representation of the note in the buffer.
        Note: Currently only affects the first line.
        """

        # Get first line of the question
        question = self.fields.get('Front') or self.fields.get('Text')
        lines = question.splitlines()

        identifier = self.data.get('id')

        # Add the prefix to the questionline, if necessary
        prefix = self.data.get('stripped_prefix')
        if prefix is not None:
            lines[0] = '{0} {1}'.format(prefix, lines[0])

        if identifier is not None:
            lines[0] = '{0} @{1}'.format(lines[0], identifier)

        # Update all the lines over which the question spans
        position = self.data['line']
        self.buffer_proxy[position:position+len(lines)] = lines
