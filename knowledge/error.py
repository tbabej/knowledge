class VimPrettyException(Exception):
    pass

class KnowledgeException(VimPrettyException):
    pass

class FactNotFoundException(KnowledgeException):
    pass
