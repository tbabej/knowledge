from __future__ import print_function
import sys


class VimPrettyException(Exception):
    pass


class KnowledgeException(VimPrettyException):
    pass


class FactNotFoundException(KnowledgeException):
    pass


# Handle error without traceback, if they're descendants of VimPrettyException
def pretty_exception_handler(original_function):
    """
    Wraps a given function object to catch and process all the
    VimPrettyExceptions encountered.
    """
    def wrapped_function(*args, **kwargs):
        try:
            original_function(*args, **kwargs)
        except VimPrettyException as e:
            print(str(e), file=sys.stderr)

    return wrapped_function
