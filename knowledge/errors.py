from __future__ import print_function
import sys


class VimPrettyException(Exception):
    pass


class KnowledgeException(VimPrettyException):
    pass


class FactNotFoundException(KnowledgeException):
    pass


# Handle error without traceback, if they're descendants of VimPrettyException
def output_exception(exception_type, value, tb):
    if any(['VimPretty' in t.__name__ for t in exception_type.mro()]):
        print(unicode(value), file=sys.stderr)
    else:
        sys.__excepthook__(exception_type, value, tb)

# Wrap the original except hook
sys.excepthook = output_exception
