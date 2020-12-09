"""
This module collects all the config variables sourced from vim.
"""

from knowledge import vimutils
import vim
import os

SRS_PROVIDER = vimutils.decode_bytes(vim.vars.get('knowledge_srs_provider'))
SRS_DB = vimutils.decode_bytes(vim.vars.get('knowledge_srs_db'))
DB_FILE = vimutils.decode_bytes(vim.vars.get(
    'knowledge_db_file',
    os.path.expanduser("~/.knowledge.db")
))
DATA_FOLDER = vimutils.decode_bytes(vim.vars.get(
    'knowledge_data_folder',
    os.path.join(vim.eval("vimwiki#vars#get_wikilocal('path')"), '.data')
))

QUESTION_OMITTED_PREFIXES = vimutils.decode_bytes(vim.vars.get(
    'knowledge_omitted_prefixes',
    ('Q:',)
))

QUESTION_PREFIXES = vimutils.decode_bytes(vim.vars.get(
    'knowledge_question_prefixes',
    ('Q:', 'How:', 'Explain:', 'Define:', 'List:', 'Prove:', 'Derive:')
))

GLUED_LATEX_COMMANDS = vimutils.decode_bytes(vim.vars.get('knowledge_glued_latex_commands', []))
PDF_UNDERLINE_CLOZE = vimutils.decode_bytes(vim.vars.get('knowledge_pdf_underline_cloze', 1))
