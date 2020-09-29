"""
A module containing knowledge-relevant regular expressions.
"""

import re

from knowledge import config


QUESTION = re.compile(
    r'^'                                    # Starts at the begging
    r'(?P<question>({prefixes})[^\[\]]+?)'  # Using an allowed prefix
    r'('
      r'\s+'                                # Followed by any whitespace
      r'@(?P<identifier>.*)'                # With opt. identifier marked by @
    r')?'
    r'\s*'
    r'$'                                    # Matches on whole line
    .format(prefixes='|'.join(config.QUESTION_PREFIXES))
)

# Marks do not start on a 4-space indented lines, and are not preceded by
# a another '{' or ':' (wikilinks)
CLOSE_MARK = re.compile(r'(^(?!    ).*\s\{[^\{]+)|(^\{[^\{]+)', re.MULTILINE)
CLOSE_IDENTIFIER = re.compile(r'\s@(?P<identifier>[A-Za-z0-9]{11})\s*$', re.MULTILINE)

NOTE_HEADLINE = {
    'default': re.compile(
        r'^'                       # Starts at the begging of the line
        r'(?P<header_start>[=]+)'  # Heading beggining
        r'(?P<name>[^=\|\[]*)'     # Name of the viewport, all before the @ sign
        r'@'                       # Divider @
        r'(?P<metadata>[^=@]*?)'   # Metadata string
        r'\s*'                     # Any whitespace
        r'([=]+)'                  # Heading ending
    ),
    'markdown': re.compile(
        r'^'                       # Starts at the begging of the line
        r'(?P<header_start>[#]+)'  # Heading beggining
        r'(?P<name>[^#\|\[]*)'     # Name of the viewport, all before the @ sign
        r'@'                       # Divider @
        r'(?P<metadata>[^=@]*?)'   # Metadata string
        r'\s*'                     # Any whitespace
        r'$'                       # End of the line
    ),
}

NUMLIST_MARK = re.compile(r'^(\d+\.)+ ')
EXTENSION = re.compile(r'\.[^/]+$')
IMAGE = re.compile(r'!(?P<size>[LMS])?\[(?P<label>.+)\]\(media:(?P<filename>[^\)]+)\)(\{(?P<format>[^\}]+)\})?')
