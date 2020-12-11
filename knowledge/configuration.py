"""
This module collects all the config variables sourced from vim.
"""

import os
import sys


try:
    import vim
    from knowledge import vimutils
except ImportError:
    pass


class Configuration:
    """
    Object containing configuration variables.
    """

    def __init__(self):
        self.SRS_PROVIDER = self._get_config_var('knowledge_srs_provider', None)
        self.SRS_DB = self._get_config_var('knowledge_srs_db', None)
        self.DB_FILE = self._get_config_var(
            'knowledge_db_file',
            os.path.expanduser("~/.knowledge.db")
        )

        self.DATA_FOLDER = self._get_config_var(
            'knowledge_data_folder',
            os.path.join(self.wiki_root, '.data')
        )

        self.QUESTION_OMITTED_PREFIXES = self._get_config_var(
            'knowledge_omitted_prefixes',
            ('Q:',)
        )

        self.QUESTION_PREFIXES = self._get_config_var(
            'knowledge_question_prefixes',
            ('Q:', 'How:', 'Explain:', 'Define:', 'List:', 'Prove:', 'Derive:')
        )

        self.GLUED_LATEX_COMMANDS = self._get_config_var('knowledge_glued_latex_commands', [])
        self.PDF_UNDERLINE_CLOZE = self._get_config_var('knowledge_pdf_underline_cloze', 1)

    @staticmethod
    def _get_config_var(key, default):
        if 'vim' in sys.modules:
            return vimutils.decode_bytes(vim.vars.get(key, default))
        else:
            return os.environ.get(key.upper(), default)

    @property
    def wiki_root(self):
        if 'vim' in sys.modules:
            return vim.eval("vimwiki#vars#get_wikilocal('path')")
        else:
            return os.getenv("KNOWLEDGE_WIKI_ROOT")
