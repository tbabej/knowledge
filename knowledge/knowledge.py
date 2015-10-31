import os
import re
import sys
import vim

# Insert the knowledge on the python path
BASE_DIR = vim.eval("s:plugin_path")
sys.path.insert(0, os.path.join(BASE_DIR, 'knowledge'))

from proxy import AnkiProxy
proxy = AnkiProxy(os.path.expanduser('~/Documents/Anki/User 1/collection.anki2'))

NOTE_HEADLINE = re.compile(
    '^'                    # Starts at the begging of the line
    '[=]+'                 # Heading begging
    '(?P<question>[^=\|\[\{]*)'  # Name of the viewport, all before the | sign
                             # Cannot include '[', '=', '|, and '{'
    '@'                   # Divider @
    '(?P<metadata>[^=@]*?)'       # Filter
    '\s*'                  # Any whitespace
    '[=]+'                 # Header ending
    )

class WikiNote(object):

    def __init__(self):
        self.data = dict()

    @classmethod
    def from_line(cls, number):
        """
        This methods detects if a current line is a note-defining headline. If
        positive, it will try to parse the note data out of the block.
        """

        match = re.search(NOTE_HEADLINE, vim.current.buffer[number])

        if not match:
            return None

        self = cls()

        # If we have a match, determine if it's an existing note
        metadata = match.group('metadata').strip()
        question = match.group('question').strip()

        # No ID in metadata means this is a new note
        attempt_to_add = not metadata

        # Parse out the answer
        answerlines = []
        for line in vim.current.buffer[(number+1):]:
            candidate = line.strip()

            # Consider new heading or --- as a end of the answer
            if candidate.startswith('=') or candidate.startswith('---'):
                break
            elif candidate:
                answerlines.append(candidate)

        self.data.update({
            'Front': question,
            'Back': '\n'.join(answerlines),
        })

        return self

    def __repr__(self):
        return repr(self.data)

    def save(self):
        proxy.add_note('TestDeck', 'Basic', self.data)
        proxy.collection.flush()
        proxy.collection.save()
        proxy.collection.close()
