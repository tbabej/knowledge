import re
import vim

QUESTION_PREFIXES = ('Q', 'How', 'Explain', 'Define', 'List')

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
    def from_line(cls, number):
        match = re.search(NOTE_HEADLINE, vim.current.buffer[number])

        if not match:
            return None

        self = cls()
        self.data.update({
            'header_start': match.group('header_start'),
            'header_end': match.group('header_end'),
            'name': match.group('name'),
            'metadata': match.group('metadata').strip().split(),
        })

        return self


class WikiNote(object):

    def __init__(self, proxy):
        self.fields = dict()
        self.data = dict()
        self.proxy = proxy

    @classmethod
    def from_line(cls, number, proxy, tags=None):
        """
        This methods detects if a current line is a note-defining headline. If
        positive, it will try to parse the note data out of the block.
        """

        match = re.search(QUESTION, vim.current.buffer[number])

        if not match:
            return None

        self = cls(proxy)

        # If we have a match, determine if it's an existing note
        identifier = match.group('identifier')
        question = match.group('question').strip()

        tags = tags or []

        self.data.update({
            'id': identifier,
            'line': number,
            'tags': set(tags)
        })

        # Parse out the remaining question and answer parts
        questionlines = [question]
        answerlines = []
        parsing_question = True

        for line in vim.current.buffer[(number+1):]:
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

        return self

    def __repr__(self):
        return repr(self.fields)

    @property
    def created(self):
        return self.data.get('id') is not None

    def save(self):
        if self.data.get('id') is not None:
            return

        obtained_id = self.proxy.add_note(
            'TestDeck',
            '1',
            self.fields,
            tags=self.data['tags']
        )

        if obtained_id:
            self.data['id'] = obtained_id
            self.update_in_buffer()

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

        vim.current.buffer[self.data['line']] = line
