"""
A module containing knowledge-relevant regular expressions.
"""

import re
import vim


QUESTION_PREFIXES = vim.vars.get(
    'knowledge_question_prefixes',
    ('Q:', 'How:', 'Explain:', 'Define:', 'List:', 'Prove:')
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

# Marks do not start on a 4-space indented lines, and are not preceded by a '* '
CLOSE_MARK = re.compile('^(?!    ).*(?<!(\* ))\[.+')
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
