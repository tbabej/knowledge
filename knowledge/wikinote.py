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
    '\s*'                                  # Followed by any whitespace
    '(\['
      '(?P<identifier>.*)'                 # With opt. identifier in []
    '\])?'
    '\s*'
    '$'                                    # Matches on whole line
    .format(prefixes='|'.join(QUESTION_PREFIXES))
)

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

        return self


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

        match = re.search(QUESTION, buffer_proxy[number])

        if not match:
            return None, 1

        self = cls(buffer_proxy, proxy)

        # If we have a match, determine if it's an existing note
        identifier = match.group('identifier')
        question = match.group('question').strip()

        # Strip the question prefixes that should be ignored
        for prefix in QUESTION_OMITTED_PREFIXES:
            if question.startswith(prefix):
                question = question.lstrip(prefix).strip()

        tags = tags or []
        model = model or proxy.DEFAULT_MODEL
        deck = deck or proxy.DEFAULT_DECK

        self.data.update({
            'id': identifier,
            'line': number,
            'tags': set(tags),
            'model': model,
            'deck': deck,
        })

        # Parse out the remaining question and answer parts
        questionlines = [question]
        answerlines = []
        parsing_question = True

        for line in self.buffer_proxy[(number+1):]:
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

        return self, len(questionlines) + len(answerlines)

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

    def update_in_buffer(self):
        """
        Updates the representation of the note in the buffer.
        Note: Currently only affects the first line.
        """

        questionline = self.fields.get('Front').splitlines()[0]
        identifier = self.data.get('id')

        if identifier is not None:
            line = '{0} [{1}]'.format(questionline, identifier)
        else:
            line = questionline

        self.buffer_proxy[self.data['line']] = line
