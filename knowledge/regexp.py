"""
A module containing knowledge-relevant regular expressions.
"""

import re

from knowledge import config


QUESTION = re.compile(
    '^'                                    # Starts at the begging
    '(?P<question>({prefixes})[^\[\]]+?)'  # Using an allowed prefix
    '('
      '\s+'                                # Followed by any whitespace
      '@(?P<identifier>.*)'                # With opt. identifier marked by @
    ')?'
    '\s*'
    '$'                                    # Matches on whole line
    .format(prefixes='|'.join(config.QUESTION_PREFIXES))
)

# Marks do not start on a 4-space indented lines, and are not preceded by a '* '
CLOSE_MARK = re.compile('^(?!    ).*(?<!(\* ))(?<!\[)\[.+')
CLOSE_IDENTIFIER = re.compile('\s@(?P<identifier>.*)\s*$', re.MULTILINE)

NOTE_HEADLINE = {
    'default': re.compile(
        '^'                       # Starts at the begging of the line
        '(?P<header_start>[=]+)'  # Heading beggining
        '(?P<name>[^=\|\[]*)'     # Name of the viewport, all before the @ sign
        '@'                       # Divider @
        '(?P<metadata>[^=@]*?)'   # Metadata string
        '\s*'                     # Any whitespace
        '([=]+)'                  # Heading ending
    ),
    'markdown': re.compile(
        '^'                       # Starts at the begging of the line
        '(?P<header_start>[#]+)'  # Heading beggining
        '(?P<name>[^#\|\[]*)'     # Name of the viewport, all before the @ sign
        '@'                       # Divider @
        '(?P<metadata>[^=@]*?)'   # Metadata string
        '\s*'                     # Any whitespace
        '$'                       # End of the line
    ),
}

NUMLIST_MARK = re.compile(r'^(\d+\.)+ ')
